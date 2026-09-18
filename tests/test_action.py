import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from action_entry import arguments


class ActionTests(unittest.TestCase):
    def test_defaults_respect_repository_config(self):
        for environment in [{}, {"PREFLIGHT_EXCLUDE": ""}, {"PREFLIGHT_EXCLUDE": " \n\t\r\n "}]:
            with self.subTest(environment=environment):
                self.assertEqual(arguments(environment), ["--format", "text", "--", "."])

    def test_multiline_exclusions_trim_whitespace_and_skip_empty_lines(self):
        environment = {"PREFLIGHT_EXCLUDE": "\n  docs/generated/** \r\n\t\r\n archive/**\t\n"}
        self.assertEqual(arguments(environment),
                         ["--format", "text", "--exclude=docs/generated/**", "--exclude=archive/**",
                          "--", "."])

    def test_exclusion_patterns_are_single_literal_arguments(self):
        patterns = ["--drafts/**", "docs with spaces/**", "$(echo nope)/**", "*.md; echo nope"]
        self.assertEqual(arguments({"PREFLIGHT_EXCLUDE": "\n".join(patterns)}),
                         ["--format", "text", *("--exclude=" + pattern for pattern in patterns),
                          "--", "."])

    def test_arguments_with_spaces_or_shell_syntax_remain_literal(self):
        root = "--version; $(echo nope)/project with spaces"
        output = "reports/a b.json"
        self.assertEqual(arguments({"PREFLIGHT_ROOT": root, "PREFLIGHT_OUTPUT": output,
                                    "PREFLIGHT_FAIL_ON": "warning", "PREFLIGHT_NO_HYGIENE": "true"}),
                         ["--format", "text", "--fail-on", "warning", "--output", output,
                          "--no-hygiene", "--", root])

    def test_invalid_boolean_fails_instead_of_silently_ignoring(self):
        with self.assertRaisesRegex(ValueError, "true or false"):
            arguments({"PREFLIGHT_NO_HYGIENE": "yes"})

    def test_action_exclusions_combine_with_repository_config_end_to_end(self):
        source_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "project with spaces"
            root.mkdir()

            def write(relative, content):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            write("README.md", "# Project\n")
            for directory in ["generated", "archived notes", "--drafts", "$(echo nope)"]:
                write(f"{directory}/stale.md", "[Broken](missing.md)\n")
            write("docs/guide.md", "[Broken](missing.md)\n[Outside](../../outside.md)\n")
            configuration = ('[preflight]\nexclude = ["generated/**"]\n'
                             'ignore_rules = ["LINK004"]\nfail_on = "none"\n')
            write(".maintainer-preflight.toml", configuration)
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith("PREFLIGHT_")}
            environment.update({
                "PYTHONPATH": str(source_root),
                "PYTHONIOENCODING": "utf-8",
                "PREFLIGHT_ROOT": str(root),
                "PREFLIGHT_FORMAT": "json",
                "PREFLIGHT_EXCLUDE": " archived notes/** \r\n\n--drafts/**\n $(echo nope)/**\n",
            })

            def invoke():
                return subprocess.run(
                    [sys.executable, str(source_root / "action_entry.py")],
                    cwd=workspace, env=environment, capture_output=True,
                    text=True, encoding="utf-8", timeout=15, check=False,
                )

            result = invoke()
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(result.stderr, "")
            report = json.loads(result.stdout)
            self.assertEqual(report["markdown_files"], 2)
            self.assertEqual(report["ignored_findings"], 1)
            link_findings = [item for item in report["findings"]
                             if item["rule_id"].startswith("LINK")]
            self.assertEqual([(item["rule_id"], item["path"]) for item in link_findings],
                             [("LINK001", "docs/guide.md")])
            self.assertIn("DOC002", [item["rule_id"] for item in report["findings"]])

            environment.update({"PREFLIGHT_NO_HYGIENE": "true", "PREFLIGHT_FAIL_ON": "error"})
            links_only = invoke()
            self.assertEqual(links_only.returncode, 1, links_only.stderr + links_only.stdout)
            self.assertEqual(links_only.stderr, "")
            self.assertEqual(json.loads(links_only.stdout)["findings"], link_findings)
            self.assertEqual((root / ".maintainer-preflight.toml").read_text(encoding="utf-8"),
                             configuration)
