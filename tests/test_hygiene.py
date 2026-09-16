"""Behavioral checks for presence-only repository hygiene inspection."""

from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from maintainer_preflight.hygiene import check_hygiene


class HygieneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, relative, content="example\n"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def ids(self):
        return {finding.rule_id for finding in check_hygiene(self.root)}

    def complete(self):
        for relative in ["README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md",
                         "CHANGELOG.md", "tests/test_project.py", ".github/workflows/check.yml"]:
            self.write(relative)

    def test_empty_repository_reports_all_expected_gaps(self):
        findings = check_hygiene(self.root)
        self.assertEqual({f.rule_id for f in findings},
                         {"DOC001", "DOC002", "DOC003", "DOC004", "DOC005", "TEST001", "CI001"})
        self.assertEqual(next(f.severity for f in findings if f.rule_id == "DOC001"), "error")
        self.assertEqual(next(f.severity for f in findings if f.rule_id == "DOC005"), "note")
        self.assertTrue(all(f.line == 1 and not Path(f.path).is_absolute() and "\\" not in f.path
                            for f in findings))

    def test_conventional_repository_has_no_hygiene_findings(self):
        self.complete()
        self.assertEqual(check_hygiene(self.root), [])

    def test_alternative_locations_names_and_case(self):
        for relative in [".github/ReadMe.rst", "COPYING.txt", "docs/CONTRIBUTING.md",
                         ".github/SECURITY.MD", "docs/NEWS", "src/core_test.go", ".gitlab-ci.yml"]:
            self.write(relative)
        self.assertEqual(check_hygiene(self.root), [])

    def test_generated_and_vendor_files_do_not_count(self):
        for directory in ["node_modules", "vendor", "vendors", "env", ".venv", "build", ".git"]:
            for relative in ["README.md", "LICENSE", "tests/test_something.py", ".github/workflows/ci.yml"]:
                self.write(f"{directory}/{relative}")
        self.assertEqual(self.ids(), {"DOC001", "DOC002", "DOC003", "DOC004", "DOC005", "TEST001", "CI001"})

    def test_empty_tests_directory_and_unrelated_names_are_not_evidence(self):
        (self.root / "tests").mkdir()
        self.write("tests/README.md")
        self.write("contest.py")
        self.write("latest.js")
        self.write(".github/actions/example/action.yml")
        self.assertTrue({"TEST001", "CI001"}.issubset(self.ids()))

    def test_test_framework_conventions(self):
        for name in ["pkg/check.test.ts", "pkg/check.spec.jsx", "lib/test_helpers.py",
                     "src/ParserTest.java", "spec/parser_spec.rb", "tests/integration.rs"]:
            with self.subTest(name=name):
                self.write(name)
                self.assertNotIn("TEST001", self.ids())
                (self.root / name).unlink()

    def test_multiple_ci_providers(self):
        for name in [".circleci/config.yml", "azure-pipelines.yml", "Jenkinsfile",
                     ".buildkite/pipeline.yaml", "bitbucket-pipelines.yml", ".travis.yml"]:
            with self.subTest(name=name):
                self.write(name)
                self.assertNotIn("CI001", self.ids())
                (self.root / name).unlink()

    def test_nested_workflow_in_unrelated_project_is_not_root_ci(self):
        self.write("examples/demo/.github/workflows/example.yml")
        self.assertIn("CI001", self.ids())

    def test_multi_license_filename(self):
        self.write("LICENSE-MIT")
        self.assertNotIn("DOC002", self.ids())

    def test_presence_checks_do_not_execute_repository_code(self):
        self.complete()
        self.write("tests/test_project.py", "raise RuntimeError('must never execute')\n")
        self.write(".github/workflows/check.yml", "not even yaml [\n")
        self.assertEqual(check_hygiene(self.root), [])

    def test_entry_bound_reports_incomplete_scan(self):
        self.write("a.txt")
        self.write("b.txt")
        with patch("maintainer_preflight.hygiene.MAX_ENTRIES", 1):
            self.assertIn("SCAN001", self.ids())

    def test_depth_bound_reports_incomplete_scan(self):
        self.write("deep/nested/tests/test_hidden.py")
        with patch("maintainer_preflight.hygiene.MAX_DEPTH", 1):
            self.assertTrue({"SCAN001", "TEST001"}.issubset(self.ids()))

    def test_unreadable_scan_reports_incomplete(self):
        with patch("maintainer_preflight.hygiene.os.scandir", side_effect=PermissionError):
            self.assertIn("SCAN001", self.ids())

    def test_windows_junctions_are_not_traversed(self):
        entry = MagicMock()
        entry.name = "external"
        entry.is_symlink.return_value = False
        entry.stat.return_value = SimpleNamespace(st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
        scan = MagicMock()
        scan.__enter__.return_value = iter([entry])
        with patch("maintainer_preflight.hygiene.os.scandir", return_value=scan) as scandir:
            with patch("maintainer_preflight.hygiene.os.name", "nt"):
                self.assertIn("TEST001", self.ids())
        scandir.assert_called_once_with(self.root)
        entry.is_dir.assert_not_called()

    def test_symlinks_do_not_count_or_escape_root(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external)
            (target / "test_external.py").write_text("example", encoding="utf-8")
            (target / "README.md").write_text("example", encoding="utf-8")
            try:
                (self.root / "linked").symlink_to(target, target_is_directory=True)
                (self.root / "README.md").symlink_to(target / "README.md")
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"Symlink creation unavailable: {exc}")
            self.assertTrue({"DOC001", "TEST001"}.issubset(self.ids()))


if __name__ == "__main__":
    unittest.main()
