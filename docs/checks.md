# Check reference

Preflight reports a stable rule identifier, severity, and explanation for each finding. Use identifiers in `ignore_rules` when a check does not apply to your project. Ignoring a rule suppresses its findings; it does not fix the underlying problem.

## Documentation links

| Rule | Severity | Meaning | Typical fix |
| --- | --- | --- | --- |
| `LINK001` | Error | A local link target does not exist. | Update the destination or restore the missing file. |
| `LINK002` | Error | A link's heading anchor does not exist in the target Markdown file. | Update the fragment to match the current heading. |
| `LINK003` | Error | A path uses different casing from the file or directory on disk. | Match every path component's exact case. |
| `LINK004` | Error | A local link resolves outside the audit root. | Link within the checkout or audit the appropriate common root. |
| `LINK005` | Warning | A Markdown file cannot be safely read or parsed within the work limit. | Check permissions and UTF-8 encoding, or simplify pathological markup. |
| `LINK006` | Warning | A Markdown file exceeds the 1 MiB size limit and was skipped. | Split the document or deliberately exclude generated content. |

Relative paths are interpreted from the document containing the link. A path beginning with `/` is interpreted from the audit root. A fragment-only link refers to the current document. Heading anchors use GitHub-style normalization, including duplicate-heading suffixes. Exact filename case matters even on a case-insensitive filesystem because the same repository may be served or tested on a case-sensitive system.

The checker supports common inline links, image destinations, single-line reference definitions, ATX and setext Markdown headings, and explicit HTML `id` or `name` anchors. Links in fenced code blocks, inline code, and HTML comments are ignored. It skips external destinations instead of checking their availability. Anchors are checked in Markdown targets only, and a directory link does not implicitly select that directory's README. A local destination that exists can still be unusable in a particular site generator or rendered environment.

This is a conservative parser, not a complete implementation of CommonMark or GitHub's renderer. Complex nested syntax, HTML-generated headings, custom heading IDs, template variables, and site-specific routes may not behave as they do in your published documentation. Minimize a false positive and report it with a regression example.

## Repository essentials

| Rule | Severity | Meaning |
| --- | --- | --- |
| `DOC001` | Error | No recognized README was found. |
| `DOC002` | Warning | No recognized license file was found. |
| `DOC003` | Warning | No recognized contribution guide was found. |
| `DOC004` | Warning | No recognized security policy was found. |
| `DOC005` | Note | No recognized changelog was found. |
| `TEST001` | Warning | No recognized test source file was found. |
| `CI001` | Warning | No recognized continuous-integration configuration was found. |

These checks look for conventional regular files, ignoring symbolic links and common generated or vendored directories. README, contribution guide, security policy, license, and changelog files can live in the root, `docs`, `doc`, or `.github` directory. Recognized documentation extensions include Markdown, reStructuredText, text, AsciiDoc, and extensionless names. License detection also recognizes names such as `COPYING`, `LICENCE`, and `LICENSE-MIT`.

Test evidence includes source files in conventional test directories and filenames such as `test_example.py`, `example_test.go`, and `example.test.ts`. An empty `tests` directory does not qualify. CI evidence includes GitHub workflow YAML and conventional configuration for several other providers; an externally configured CI service may require suppressing `CI001`.

The checks do not read legal terms, run tests, validate CI configuration, or evaluate how a project is maintained. If your repository uses an unusual layout, suppress the relevant rule after reviewing the finding. Use `--no-hygiene` to disable all repository presence checks while retaining link checks.

## Incomplete inspection

| Rule | Severity | Meaning |
| --- | --- | --- |
| `SCAN001` | Warning | Repository presence inspection was incomplete because a traversal limit or read error was encountered. |

Repository presence inspection stops at 50,000 entries or a directory depth of 16. Review `SCAN001` before treating missing-file findings as definitive. A failure that prevents the main Markdown scan from completing returns exit code `2` instead of a normal successful audit.

## Choosing a threshold

The default `error` threshold is useful for catching broken links and a missing README. Use `warning` when all warning-level repository checks are appropriate for your project. Use `none` to collect a report without causing a failure because of findings. Notes remain informational at every threshold.

See [configuration](configuration.md) for exclusions and command-line precedence, or return to the [README](../README.md).
