import unittest

from action_entry import arguments


class ActionTests(unittest.TestCase):
    def test_defaults_respect_repository_config(self):
        self.assertEqual(arguments({}), ["--format", "text", "--", "."])

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
