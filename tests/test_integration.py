"""End-to-end command-line workflows with real temporary repositories."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / "project"
        self.root.mkdir()
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = str(SOURCE_ROOT)
        self.env["PYTHONIOENCODING"] = "utf-8"

    def write(self, relative, content="# Example\n"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def complete(self):
        for name in ["README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md",
                     "CHANGELOG.md", "tests/test_project.py", ".github/workflows/check.yml"]:
            self.write(name)

    def run_cli(self, *arguments, root=None):
        return subprocess.run(
            [sys.executable, "-m", "maintainer_preflight", str(root or self.root), *arguments],
            cwd=self.workspace, env=self.env, capture_output=True,
            text=True, encoding="utf-8", timeout=15, check=False,
        )

    def json_result(self, *arguments, expected=0):
        result = self.run_cli("--format", "json", *arguments)
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_new_repository_reports_actionable_hygiene_gaps(self):
        report = self.json_result(expected=1)
        self.assertEqual(report["repository"], "project")
        self.assertEqual(report["markdown_files"], 0)
        self.assertEqual(report["counts"], {"error": 1, "warning": 5, "note": 1})
        self.assertEqual(next(item["path"] for item in report["findings"]
                              if item["rule_id"] == "DOC001"), "README.md")
        self.assertTrue(all(item["suggestion"] for item in report["findings"]))

    def test_documentation_fix_changes_failure_to_success(self):
        self.complete()
        self.write("README.md", "# Project\n\n[Getting started](docs/guide.md#installation)\n")
        broken = self.json_result(expected=1)
        self.assertEqual([item["rule_id"] for item in broken["findings"]], ["LINK001"])
        self.assertEqual(broken["findings"][0]["line"], 3)
        self.write("docs/guide.md", "# Guide\n\n## Installation\n\nInstall the tool.\n")
        fixed = self.json_result()
        self.assertEqual(fixed["findings"], [])

    def test_fail_thresholds_change_exit_status_not_findings(self):
        self.write("README.md")
        default = self.json_result()
        warning = self.json_result("--fail-on", "warning", expected=1)
        none = self.json_result("--fail-on", "none")
        self.assertEqual(default, warning)
        self.assertEqual(default, none)
        self.assertGreater(default["counts"]["warning"], 0)

    def test_command_line_threshold_overrides_configuration(self):
        self.write("README.md", "[Broken](missing.md)\n")
        self.write(".maintainer-preflight.toml", '[preflight]\nfail_on = "none"\n')
        accepted = self.json_result()
        rejected = self.json_result("--fail-on", "error", expected=1)
        self.assertEqual(accepted, rejected)

    def test_configured_warning_threshold(self):
        self.write("README.md")
        self.write(".maintainer-preflight.toml", '[preflight]\nfail_on = "warning"\n')
        self.json_result(expected=1)
        self.json_result("--fail-on", "error")

    def test_no_hygiene_still_checks_document_links(self):
        self.assertEqual(self.json_result("--no-hygiene")["findings"], [])
        self.write("README.md", "[Broken](missing.md)\n")
        report = self.json_result("--no-hygiene", expected=1)
        self.assertEqual([item["rule_id"] for item in report["findings"]], ["LINK001"])

    def test_excluded_generated_documents_are_not_link_checked(self):
        self.write("README.md", "[Guide](docs/guide.md)\n")
        self.write("docs/guide.md")
        self.write("docs/generated/stale.md", "[Broken](absent.md)\n")
        self.write(".maintainer-preflight.toml", '[preflight]\nexclude = ["docs/generated/**"]\n')
        report = self.json_result("--no-hygiene")
        self.assertEqual(report["markdown_files"], 2)
        self.assertEqual(report["findings"], [])

    def test_dependency_and_build_documents_are_ignored_by_default(self):
        self.write("README.md")
        for directory in [".git", "vendor", "node_modules", ".venv", "build"]:
            self.write(f"{directory}/broken.md", "[Broken](absent.md)\n")
        report = self.json_result("--no-hygiene")
        self.assertEqual(report["markdown_files"], 1)
        self.assertEqual(report["findings"], [])

    def test_rule_suppression_is_counted_and_preserves_other_findings(self):
        self.write("README.md", "[Broken](missing.md)\n[Outside](../outside.md)\n")
        self.write(".maintainer-preflight.toml", '[preflight]\nignore_rules = ["LINK001"]\n')
        report = self.json_result("--no-hygiene", "--fail-on", "none")
        self.assertEqual(report["ignored_findings"], 1)
        self.assertEqual([item["rule_id"] for item in report["findings"]], ["LINK004"])

    def test_explicit_config_replaces_automatic_config(self):
        self.write("README.md")
        self.write(".maintainer-preflight.toml", "invalid = [toml\n")
        custom = self.workspace / "config" / "selected.toml"
        custom.parent.mkdir()
        custom.write_text('[preflight]\nfail_on = "none"\n', encoding="utf-8")
        self.json_result("--config", "config/selected.toml")

    def test_invalid_configuration_fails_cleanly(self):
        configurations = {
            "syntax": "[preflight\n",
            "missing_table": 'fail_on = "none"\n',
            "unknown_table": "[preflight]\n[unrelated]\n",
            "unknown_key": "[preflight]\nunknown = true\n",
            "wrong_exclude_type": '[preflight]\nexclude = "docs/**"\n',
            "empty_exclude": '[preflight]\nexclude = [""]\n',
            "nonstring_rule": "[preflight]\nignore_rules = [true]\n",
            "unknown_rule": '[preflight]\nignore_rules = ["TYPO001"]\n',
            "invalid_threshold": '[preflight]\nfail_on = "critical"\n',
            "wrong_threshold_type": '[preflight]\nfail_on = ["error"]\n',
        }
        for label, content in configurations.items():
            with self.subTest(label=label):
                self.write(".maintainer-preflight.toml", content)
                result = self.run_cli("--format", "json")
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("maintainer-preflight:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_missing_explicit_config_and_invalid_repository_fail_cleanly(self):
        for options, root in [(("--config", "missing.toml"), self.root),
                              ((), self.workspace / "missing-repository"),
                              ((), self.write("ordinary-file.txt"))]:
            with self.subTest(options=options, root=root):
                result = self.run_cli(*options, root=root)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("Traceback", result.stderr)

    def test_oversized_configuration_is_rejected(self):
        self.write(".maintainer-preflight.toml", "[preflight]\n#" + "x" * 65_536)
        result = self.run_cli("--format", "json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("64 KiB", result.stderr)

    def test_invalid_utf8_configuration_fails_cleanly(self):
        (self.root / ".maintainer-preflight.toml").write_bytes(b"[preflight]\n#\xff\xfe\n")
        result = self.run_cli("--format", "json")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Traceback", result.stderr)

    def test_directory_configuration_is_rejected(self):
        (self.root / ".maintainer-preflight.toml").mkdir()
        result = self.run_cli("--format", "json")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_dangling_configuration_symlink_is_rejected(self):
        try:
            (self.root / ".maintainer-preflight.toml").symlink_to(self.workspace / "absent.toml")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        result = self.run_cli("--no-hygiene", "--format", "json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlink", result.stderr)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO fixture requires POSIX")
    def test_fifo_configuration_fails_without_blocking(self):
        os.mkfifo(self.root / ".maintainer-preflight.toml")
        result = self.run_cli("--format", "json")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_deep_repository_fails_cleanly_but_excluded_subtree_is_skipped(self):
        relative = "/".join(["deep"] + ["d"] * 65 + ["document.md"])
        self.write(relative)
        result = self.run_cli("--no-hygiene")
        self.assertEqual(result.returncode, 2)
        self.assertIn("scan limit", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.write(".maintainer-preflight.toml", '[preflight]\nexclude = ["deep"]\n')
        report = self.json_result("--no-hygiene")
        self.assertEqual(report["markdown_files"], 0)

    def test_output_file_is_utf8_and_replaces_existing_report(self):
        self.write("README.md", "[Missing](caf%C3%A9.md)\n")
        destination = self.workspace / "reports" / "audit.json"
        first = self.run_cli("--no-hygiene", "--format", "json", "--output", str(destination))
        self.assertEqual(first.returncode, 1, first.stderr)
        self.assertEqual(first.stdout, "")
        self.assertEqual(len(json.loads(destination.read_text(encoding="utf-8"))["findings"]), 1)
        self.write("café.md")
        second = self.run_cli("--no-hygiene", "--format", "json", "--output", str(destination))
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(destination.read_text(encoding="utf-8"))["findings"], [])
        self.assertEqual(sorted(path.name for path in destination.parent.iterdir()), ["audit.json"])
        self.assertTrue(destination.read_bytes().endswith(b"\n"))

    def test_unwritable_output_target_reports_error_and_cleans_temporary_file(self):
        self.write("README.md")
        directory = self.workspace / "reports"
        directory.mkdir()
        result = self.run_cli("--no-hygiene", "--output", str(directory))
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(list(self.workspace.glob(".preflight-*.tmp")), [])

    def test_report_is_deterministic_with_relative_paths(self):
        self.write("docs/zeta.md", "[Z](missing-z.md)\n")
        self.write("docs/alpha.md", "[A](missing-a.md)\n")
        first = self.run_cli("--no-hygiene", "--format", "json")
        second = self.run_cli("--no-hygiene", "--format", "json")
        self.assertEqual(first.returncode, 1)
        self.assertEqual(first.stdout, second.stdout)
        report = json.loads(first.stdout)
        self.assertEqual([item["path"] for item in report["findings"]],
                         ["docs/alpha.md", "docs/zeta.md"])
        self.assertNotIn(str(self.workspace), first.stdout)

    def test_sarif_has_resolvable_rule_indices_and_encoded_source_locations(self):
        self.write("docs/a b.md", "# Document\n[Broken](missing.md)\n")
        result = self.run_cli("--format", "sarif")
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["version"], "2.1.0")
        run = report["runs"][0]
        rules = run["tool"]["driver"]["rules"]
        for finding in run["results"]:
            self.assertEqual(rules[finding["ruleIndex"]]["id"], finding["ruleId"])
            self.assertIn(finding["level"], {"error", "warning", "note"})
        broken = next(item for item in run["results"] if item["ruleId"] == "LINK001")
        physical = broken["locations"][0]["physicalLocation"]
        self.assertEqual(physical["artifactLocation"]["uri"], "docs/a%20b.md")
        self.assertEqual(physical["region"]["startLine"], 2)
        missing_readme = next(item for item in run["results"] if item["ruleId"] == "DOC001")
        self.assertNotIn("locations", missing_readme)

    def test_text_and_markdown_reports_include_suggestions(self):
        self.write("README.md", "[Broken](missing.md)\n")
        for format_name in ["text", "markdown"]:
            with self.subTest(format_name=format_name):
                result = self.run_cli("--no-hygiene", "--format", format_name)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("LINK001", result.stdout)
                self.assertIn("README.md:1", result.stdout)
                self.assertIn("Correct the path", result.stdout)

    def test_markdown_report_treats_embedded_image_syntax_as_literal_text(self):
        self.write("README.md", "[Broken](<![x](https://example.invalid/pixel.png)>)\n")
        result = self.run_cli("--no-hygiene", "--format", "markdown")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("LINK001", result.stdout)
        self.assertIn("https://example.invalid/pixel.png", result.stdout)
        self.assertNotIn("![x](", result.stdout)

    def test_text_report_does_not_emit_repository_supplied_terminal_escapes(self):
        self.write("README.md", "[Broken](<file\x1b[31m.md>)\n")
        result = self.run_cli("--no-hygiene", "--format", "text")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("LINK001", result.stdout)
        self.assertIn("file", result.stdout)
        self.assertNotIn("\x1b", result.stdout)

    def test_external_directory_and_file_symlinks_are_not_scanned(self):
        external = self.workspace / "outside"
        external.mkdir()
        (external / "external.md").write_text("[Broken](missing.md)\n", encoding="utf-8")
        self.write("README.md")
        try:
            (self.root / "linked").symlink_to(external, target_is_directory=True)
            (self.root / "external.md").symlink_to(external / "external.md")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        report = self.json_result("--no-hygiene")
        self.assertEqual(report["markdown_files"], 1)
        self.assertEqual(report["findings"], [])

    @unittest.skipUnless(os.name == "nt", "Junction fixture requires Windows")
    def test_windows_junction_is_not_scanned_and_link_through_it_is_rejected(self):
        import _winapi

        create_junction = getattr(_winapi, "CreateJunction", None)
        if create_junction is None:
            self.skipTest("This Python runtime cannot create a junction fixture")
        external = self.workspace / "outside"
        external.mkdir()
        (external / "external.md").write_text("[Broken](missing.md)\n", encoding="utf-8")
        junction = self.root / "linked"
        try:
            create_junction(str(external), str(junction))
        except OSError as exc:
            self.skipTest(f"Junction creation unavailable: {exc}")
        self.addCleanup(junction.rmdir)
        self.write("README.md")
        report = self.json_result("--no-hygiene")
        self.assertEqual(report["markdown_files"], 1)
        self.assertEqual(report["findings"], [])
        self.write("README.md", "[External](linked/external.md#heading)\n")
        report = self.json_result("--no-hygiene", expected=1)
        self.assertEqual([finding["rule_id"] for finding in report["findings"]], ["LINK004"])


if __name__ == "__main__":
    unittest.main()
