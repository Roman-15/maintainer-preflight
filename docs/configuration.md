# Configuration

## Command interface

```text
maintainer-preflight [path]
  [--format text|json|markdown|sarif]
  [--output path]
  [--fail-on error|warning|none]
  [--no-hygiene]
  [--config path]
  [--version]
```

The optional audit path defaults to the current directory. The equivalent source-checkout command is `python -m maintainer_preflight`.

| Option | Purpose |
| --- | --- |
| `--format` | Choose the report representation. The default is `text`. |
| `--output` | Write the report to a file instead of standard output. |
| `--fail-on` | Choose which findings cause the command to fail. |
| `--no-hygiene` | Disable repository presence checks; keep Markdown link checks. |
| `--config` | Load the given TOML configuration instead of automatic discovery. |
| `--version` | Print the installed version and exit. |
| `--help` | Show command-line usage. |

`error` fails on errors, `warning` fails on errors or warnings, and `none` does not fail because of findings. Configuration or invocation errors still indicate an unsuccessful run.

| Exit code | Meaning |
| --- | --- |
| `0` | The audit completed and no finding reached the selected threshold. |
| `1` | The audit completed with one or more findings at or above the threshold. |
| `2` | The command could not complete because of an invocation, configuration, or scan error. |

## Repository settings

By default, Preflight reads `.maintainer-preflight.toml` from the audit root when it exists:

```toml
[preflight]
exclude = ["docs/generated/**", "fixtures/**"]
ignore_rules = ["DOC005"]
fail_on = "error"
```

| Setting | Value | Purpose |
| --- | --- | --- |
| `exclude` | Array of path patterns | Omit matching paths from the scan. |
| `ignore_rules` | Array of rule identifiers | Suppress selected findings. |
| `fail_on` | `"error"`, `"warning"`, or `"none"` | Set the failure threshold. |

Write exclusion patterns relative to the audit root with forward slashes. Matching uses Python's `fnmatch` pattern syntax on repository-relative file and directory paths; these patterns are not expanded by the shell. For example, `docs/generated/**` excludes the contents of that directory. Excluding a document means its outgoing links are not audited; it is not evidence that the document's links are correct.

Path exclusions apply to Markdown scanning. They do not make an existing link target count as missing and do not change repository presence checks.

Use exact identifiers from the [check reference](checks.md), such as `DOC005`. Prefer narrow path exclusions or specific rule suppressions over disabling checks you still want to rely on.

Configuration is validated strictly: unknown keys, unknown rule identifiers, incorrect value types, and invalid thresholds are errors. The file must contain only a `[preflight]` table, be at most 64 KiB, and be a regular UTF-8 file. Symbolic links, Windows reparse points, directories, and special files are rejected.

## Precedence

1. `--config` selects one explicit configuration file; it replaces automatic `.maintainer-preflight.toml` discovery rather than merging the two.
2. Without `--config`, the file at the audit root is loaded if present.
3. `--fail-on` overrides the selected configuration's `fail_on` value.
4. Settings that are not specified use their built-in defaults.

An explicit configuration path is interpreted from the current working directory. Exclusion patterns inside that file still apply to the audit root.

```sh
maintainer-preflight ../library --config config/library.toml --fail-on warning
```

The command above audits `../library`, loads `config/library.toml`, and fails on warnings or errors regardless of that file's threshold.

## Scan and report boundaries

Preflight scans `.md` and `.markdown` files. Discovery skips symbolic-link files and directories, including Windows reparse points. A link in an audited document may still resolve to a symbolic-link target inside the audit root; targets outside the root are rejected. Excluded Markdown files can also be read to verify anchors in incoming links, while their own outgoing links remain excluded from the scan.

The Markdown size limit is 1 MiB; skipped oversized files produce `LINK006` unless that rule is suppressed. A scan exceeding 10,000 Markdown files, 100,000 entries, or a directory depth of 64 stops with exit code `2` rather than silently returning a partial result.

Markdown scanning ignores directories with the following names by default (case-insensitively):

```text
.git .hg .svn .venv venv env node_modules vendor vendors dist build
__pycache__ .tox .nox .mypy_cache .pytest_cache .ruff_cache .next
coverage site-packages
```

Add explicit exclusions for other generated content in your repository.

The command can save text, Markdown, JSON, and SARIF reports. Treat report files as artifacts and keep generated Markdown reports outside the content you routinely scan, or exclude them explicitly. Review reports for private paths before sharing them.

Return to the [README](../README.md).
