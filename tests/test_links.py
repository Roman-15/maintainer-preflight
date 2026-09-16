from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from maintainer_preflight.links import MAX_MARKDOWN_BYTES, check_links


class LinkChecksTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, relative, text=""):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def check(self, text, relative="README.md"):
        source = self.write(relative, text)
        return check_links(self.root, [source])

    def test_missing_links_and_images_have_source_lines(self):
        findings = self.check("# Project\n\n[Manual](docs/manual.md)\n![Logo](logo.png)\n")
        self.assertEqual([(f.rule_id, f.path, f.line, f.severity) for f in findings], [
            ("LINK001", "README.md", 3, "error"),
            ("LINK001", "README.md", 4, "error"),
        ])

    def test_valid_relative_root_directory_and_query_links(self):
        self.write("guide.md", "# Guide\n")
        self.write("docs/image.png", "image")
        findings = self.check("[Relative](../guide.md?raw=1#guide)\n[Root](/guide.md#guide)\n![Image](image.png)\n[Directory](../docs/)\n", "docs/index.md")
        self.assertEqual(findings, [])

    def test_same_document_and_duplicate_heading_anchors(self):
        findings = self.check("# Hello\n# Hello\n# Hello-1\n[First](#hello) [Second](#hello-1) [Third](#hello-1-1)\n[Absent](#hello-2)\n")
        self.assertEqual([(f.rule_id, f.line) for f in findings], [("LINK002", 5)])

    def test_unicode_encoding_inline_formatting_and_setext_anchors(self):
        self.write("hello world.md", "# Café, *world*!\n\nSetext title\n============\n\n## Use `run()` and [links](https://example.com) ##\n")
        findings = self.check("[Unicode](hello%20world.md#caf%C3%A9-world)\n[Setext](<hello world.md#setext-title>)\n[Code](hello%20world.md#use-run-and-links)\n")
        self.assertEqual(findings, [])

    def test_explicit_html_anchors_are_case_sensitive(self):
        findings = self.check("<a id='Custom-ID'></a>\n<a name=legacy></a>\n<div id=\"a&amp;b\"></div>\n[One](#Custom-ID) [Two](#legacy) [Three](#a%26b)\n[Wrong](#custom-id)\n")
        self.assertEqual([(f.rule_id, f.line) for f in findings], [("LINK002", 5)])

    def test_code_fences_inline_code_and_comments_are_ignored(self):
        findings = self.check("```markdown\n[missing](not-here.md)\n# Fake\n```\n~~~\n![Missing](missing.png)\n~~~\n`[missing](not-here.md)` and ``[missing](not-here.md) ` hi``\n<!--\n[missing](not-here.md)\n# Also fake\n-->\n[Missing anchor](#fake)\n")
        self.assertEqual([(f.rule_id, f.line) for f in findings], [("LINK002", 13)])

    def test_quoted_fences_and_unclosed_fence(self):
        findings = self.check("> ```\n> [example](absent.md)\n> ```\n[real](missing.md)\n```\n[example](absent.md)\n")
        self.assertEqual([(f.rule_id, f.line) for f in findings], [("LINK001", 4)])

    def test_comment_marker_in_fence_does_not_hide_later_links(self):
        findings = self.check("```html\n<!--\n```\n[real](missing.md)\n")
        self.assertEqual([(f.rule_id, f.line) for f in findings], [("LINK001", 4)])

    def test_mismatched_code_fence_does_not_close_block(self):
        self.assertEqual(self.check("````\n```\n[missing](missing.md)\n````\n"), [])

    def test_reference_full_collapsed_and_shortcut_links(self):
        self.write("guide.md", "# Guide\n")
        findings = self.check("[Full][ MY reference ]\n[Collapsed][]\n[Shortcut]\n![Picture][image]\n\n[my reference]: guide.md#guide \"A title\"\n[collapsed]: guide.md#missing\n[shortcut]: guide.md\n[image]: missing.png\n[unused]: ignored.md\n")
        self.assertEqual([(f.rule_id, f.line) for f in findings], [("LINK002", 2), ("LINK001", 4)])

    def test_first_reference_definition_wins_and_undefined_is_literal(self):
        self.write("present.md")
        self.assertEqual(self.check("[OK][id] [Undefined][nope]\n\n[id]: present.md\n[id]: absent.md\n"), [])

    def test_balanced_parentheses_angle_paths_and_titles(self):
        self.write("file(one).md", "# A\n")
        self.write("a b.md")
        findings = self.check("[One](file(one).md#a \"A title (extra)\")\n[Two](<a b.md> 'Other title')\n[Three](file\\(one\\).md (Parenthesized title))\n")
        self.assertEqual(findings, [])

    def test_linked_image_checks_both_destinations(self):
        findings = self.check("[![Badge](missing.svg)](missing.md)\n")
        self.assertEqual(len(findings), 2)
        self.assertEqual({f.rule_id for f in findings}, {"LINK001"})
        self.assertTrue(any("missing.svg" in f.message for f in findings))
        self.assertTrue(any("missing.md" in f.message for f in findings))

    def test_linked_reference_image_uses_outer_definitions(self):
        findings = self.check("[![Badge][badge]](https://example.com)\n\n[badge]: missing.svg\n")
        self.assertEqual([f.rule_id for f in findings], ["LINK001"])
        self.assertIn("missing.svg", findings[0].message)

    def test_external_schemes_and_protocol_relative_links_not_fetched(self):
        findings = self.check("[Web](https://example.com/no-page#no-anchor)\n[Mail](mailto:person@example.com)\n[Tel](tel:+123)\n[Custom](custom+app:resource)\n[Relative protocol](//example.com/missing)\n![Data](data:image/png;base64,abc)\n")
        self.assertEqual(findings, [])

    def test_non_markdown_anchor_and_empty_fragment_not_validated(self):
        self.write("code.py", "print('hello')\n")
        self.assertEqual(self.check("[Code](code.py#L100) [Top](#) [Empty]()\n"), [])

    def test_case_mismatch_detected_for_file_and_directory(self):
        self.write("Docs/Guide.md", "# Guide\n")
        findings = self.check("[Manual](docs/guide.md#guide)\n")
        self.assertEqual([f.rule_id for f in findings], ["LINK003"])
        self.assertIn("Docs/Guide.md", findings[0].suggestion)

    def test_case_mismatch_still_checks_anchor(self):
        self.write("Guide.md", "# Guide\n")
        findings = self.check("[Manual](guide.md#missing)\n")
        self.assertEqual([f.rule_id for f in findings], ["LINK003", "LINK002"])

    def test_parent_escape_is_rejected_without_reading_target(self):
        findings = self.check("[Outside](../secret.md#secret)\n[Encoded](%2e%2e/secret.md)\n", "README.md")
        self.assertEqual([f.rule_id for f in findings], ["LINK004", "LINK004"])

    def test_encoded_hash_is_part_of_filename(self):
        self.write("hash#name.md", "# Content\n")
        self.assertEqual(self.check("[Hash](hash%23name.md#content)\n"), [])

    def test_invalid_utf8_source_is_warning(self):
        source = self.root / "README.md"
        source.write_bytes(b"\xff\xfe")
        findings = check_links(self.root, [source])
        self.assertEqual([(f.rule_id, f.severity, f.path) for f in findings], [("LINK005", "warning", "README.md")])

    def test_unreadable_file_is_warning(self):
        source = self.write("README.md", "# Title\n")
        with patch.object(Path, "open", side_effect=PermissionError("denied")):
            findings = check_links(self.root, [source])
        self.assertEqual([f.rule_id for f in findings], ["LINK005"])

    def test_special_file_is_rejected_before_open(self):
        source = self.write("README.md")
        original_stat = Path.stat

        def special_stat(path, *args, **kwargs):
            if path == source:
                return SimpleNamespace(st_mode=stat.S_IFIFO)
            return original_stat(path, *args, **kwargs)

        with patch.object(Path, "stat", special_stat), patch.object(Path, "open", side_effect=AssertionError("Must not open a FIFO/device")):
            findings = check_links(self.root, [source])
        self.assertEqual([f.rule_id for f in findings], ["LINK005"])

    def test_large_markdown_is_skipped_with_warning(self):
        source = self.root / "README.md"
        source.write_bytes(b"a" * (MAX_MARKDOWN_BYTES + 1))
        findings = check_links(self.root, [source])
        self.assertEqual([(f.rule_id, f.severity) for f in findings], [("LINK006", "warning")])

    def test_invalid_linked_document_warned_once_and_no_fake_anchor_errors(self):
        target = self.root / "broken.md"
        target.write_bytes(b"\xff")
        findings = self.check("[One](broken.md#one) [Two](broken.md#two)\n")
        self.assertEqual([(f.rule_id, f.path) for f in findings], [("LINK005", "broken.md")])

    def test_symlink_outside_repository_rejected(self):
        with tempfile.TemporaryDirectory() as external:
            outside = Path(external) / "private.md"
            outside.write_text("# Private\n", encoding="utf-8")
            linked = self.root / "linked.md"
            try:
                linked.symlink_to(outside)
            except OSError:
                self.skipTest("Symbolic links are unavailable for this account")
            findings = self.check("[Private](linked.md#private)\n")
            self.assertEqual([f.rule_id for f in findings], ["LINK004"])

    def test_selected_external_symlink_is_never_read(self):
        with tempfile.TemporaryDirectory() as external:
            outside = Path(external) / "private.md"
            outside.write_text("# Private\n", encoding="utf-8")
            linked = self.root / "linked.md"
            try:
                linked.symlink_to(outside)
            except OSError:
                self.skipTest("Symbolic links are unavailable for this account")
            with patch.object(Path, "open", side_effect=AssertionError("Must not open external file")):
                findings = check_links(self.root, [linked])
            self.assertEqual([f.rule_id for f in findings], ["LINK004"])

    def test_resolved_junction_escape_never_reads_or_enumerates_outside(self):
        with tempfile.TemporaryDirectory() as external:
            outside = Path(external).resolve()
            source = self.write("README.md", "[Private](Junction/private.md#private)\n")
            self.write("Junction/private.md", "# Not the target\n")
            original_resolve = Path.resolve
            original_open = Path.open
            original_iterdir = Path.iterdir

            def resolve_redirect(path, *args, **kwargs):
                if "Junction" in path.parts:
                    offset = path.parts.index("Junction")
                    return outside.joinpath(*path.parts[offset + 1:])
                return original_resolve(path, *args, **kwargs)

            def open_guard(path, *args, **kwargs):
                self.assertNotIn("Junction", path.parts)
                self.assertTrue(path.is_relative_to(self.root))
                return original_open(path, *args, **kwargs)

            def iterdir_guard(path):
                self.assertNotIn("Junction", path.parts)
                self.assertTrue(path.is_relative_to(self.root))
                return original_iterdir(path)

            with patch.object(Path, "resolve", resolve_redirect), patch.object(Path, "open", open_guard), patch.object(Path, "iterdir", iterdir_guard):
                findings = check_links(self.root, [source])
            self.assertEqual([f.rule_id for f in findings], ["LINK004"])

    def test_selected_path_resolved_outside_is_not_opened(self):
        with tempfile.TemporaryDirectory() as external:
            outside = Path(external).resolve() / "private.md"
            source = self.write("linked.md")
            original_resolve = Path.resolve

            def resolve_redirect(path, *args, **kwargs):
                return outside if path == source else original_resolve(path, *args, **kwargs)

            with patch.object(Path, "resolve", resolve_redirect), patch.object(Path, "open", side_effect=AssertionError("Must not open outside root")):
                findings = check_links(self.root, [source])
            self.assertEqual([f.rule_id for f in findings], ["LINK004"])

    def test_nul_percent_malformed_and_encoded_drive_paths_do_not_crash(self):
        findings = self.check("[Nul](bad%00.md) [Percent](%zz.md) [Drive](C%3A/Windows/secret.md)\n")
        self.assertEqual(len(findings), 3)
        self.assertTrue(all(f.rule_id in {"LINK001", "LINK004"} for f in findings))

    def test_utf8_bom_is_supported(self):
        source = self.root / "README.md"
        source.write_bytes(b"\xef\xbb\xbf# Title\n[Title](#title)\n")
        self.assertEqual(check_links(self.root, [source]), [])

    def test_escaped_literal_link_is_not_checked(self):
        self.assertEqual(self.check(r"\[literal](missing.md)"), [])

    def test_missing_target_does_not_also_report_missing_anchor(self):
        self.assertEqual([f.rule_id for f in self.check("[Missing](none.md#nope)\n")], ["LINK001"])

    def test_maximum_size_unmatched_brackets_are_bounded(self):
        self.assertEqual(self.check("[" * MAX_MARKDOWN_BYTES), [])

    def test_deeply_nested_link_labels_do_not_recurse(self):
        text = "[" * 3000 + "label" + "](https://example.com)" * 3000
        findings = self.check(text)
        self.assertTrue(all(f.rule_id == "LINK005" for f in findings))

    def test_repeated_unclosed_destinations_hit_work_budget(self):
        findings = self.check("[a](" * 20_000)
        self.assertEqual([f.rule_id for f in findings], ["LINK005"])
        self.assertIn("complexity", findings[0].message)

    def test_unmatched_backtick_runs_are_indexed_once(self):
        text = " ".join("`" * count for count in range(1, 1000))
        self.assertEqual(self.check(text), [])

    def test_malformed_html_and_heading_brackets_do_not_backtrack(self):
        findings = self.check("# " + "[" * 100_000 + "\n" + "<a" * 200_000)
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
