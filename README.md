# Maintainer Preflight

Catch broken local documentation links and missing repository essentials before a pull request lands.

Maintainer Preflight is a small, offline command-line tool for open-source maintainers. It checks Markdown links against the files and headings in your checkout, then looks for a README, license, contribution guide, security policy, changelog, tests, and continuous integration.

- Runs on Python 3.11 or later with no runtime dependencies.
- Checks local file links, heading anchors, and filename casing.
- Produces text, Markdown, JSON, or SARIF reports.
- Supports repository configuration and adjustable failure thresholds.
- Makes no network requests and does not execute repository code.

## Quick start

From a local clone of this repository:

```sh
python -m pip install .
maintainer-preflight .
```

You can also run from the source checkout without installing:

```sh
python -m maintainer_preflight .
```

Pass another checkout to audit it:

```sh
maintainer-preflight ../my-project
```

This project is not currently published to a package registry. The install command above installs the local source.

## What it catches

A README can link to a file that was renamed, use the wrong filename case, or point to a heading that no longer exists. These mistakes often survive local preview and only become obvious after someone follows the link.

Preflight resolves relative links from the Markdown file containing them. It also checks same-page anchors, reference-style links, images with local destinations, and links between Markdown files. HTTP, HTTPS, email, and other external destinations are skipped.

The repository checks identify missing entry points for contributors. They check for the presence of conventional files; they do not evaluate license terms, the effectiveness of tests, or the quality of a security policy. An empty test directory does not count as test evidence.

See the [check reference](docs/checks.md) for rule identifiers, severity, and limitations.

For example, a README that links to a missing file, the wrong filename case, and a removed heading produces findings like these:

```text
README.md:1: error LINK001 Local link target does not exist: docs/missing.md
  Fix: Correct the path or add the missing file.
README.md:2: error LINK003 Link filename case differs from the repository: docs/guide.md
  Fix: Match the exact filename case: docs/Guide.md
README.md:3: error LINK002 Markdown anchor does not exist: docs/Guide.md#setup
  Fix: Use an existing heading slug or an explicit HTML id in the target document.
```

## Useful commands

```sh
# Fail on errors or warnings.
maintainer-preflight . --fail-on warning

# Check documentation links without repository presence checks.
maintainer-preflight . --no-hygiene

# Skip generated documents for one run, keeping configured exclusions.
maintainer-preflight . --exclude "docs/generated/**" --exclude "reports/**"

# Save a report for another tool or for review.
maintainer-preflight . --format json --output preflight.json
maintainer-preflight . --format markdown --output preflight-report.md
maintainer-preflight . --format sarif --output preflight.sarif

# Report findings without failing the command because of their severity.
maintainer-preflight . --fail-on none
```

Use `maintainer-preflight --help` for the complete command interface. Output files are written only when requested with `--output`; the audit does not repair or rewrite source files.

Exit codes are `0` when no finding reaches the selected threshold, `1` when findings reach it, and `2` when the command cannot complete because of an invocation, configuration, or scan error.

## Configuration

Add `.maintainer-preflight.toml` at the root of the repository you want to audit:

```toml
[preflight]
exclude = ["docs/generated/**"]
ignore_rules = ["DOC005"]
fail_on = "error"
```

Use `--config path/to/settings.toml` to select a different configuration file. A command-line `--fail-on` value takes precedence over the configuration. Repeat `--exclude "pattern"` to add temporary path exclusions without changing the configuration file. See [configuration](docs/configuration.md) for examples and scope.

## Continuous integration

Add this workflow to `.github/workflows/preflight.yml` in a repository you want to check:

```yaml
name: Maintainer Preflight

on: [push, pull_request]

permissions:
  contents: read

jobs:
  preflight:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
      - uses: Roman-15/maintainer-preflight@v0.2.0
```

The action checks the checked-out repository and reads its `.maintainer-preflight.toml` when present. For production workflows, pin the Preflight action to the full commit SHA of the reviewed release. Action setup may download Python; the audit itself runs offline and does not execute code from the repository being checked.

Optional action inputs:

| Input | Default | Purpose |
| --- | --- | --- |
| `path` | `.` | Repository directory relative to the workflow workspace. |
| `fail-on` | Empty | Override the configured threshold with `error`, `warning`, or `none`; empty respects repository configuration. |
| `format` | `text` | Report as `text`, `json`, `markdown`, or `sarif`. |
| `output` | Empty | Save the report to a file instead of standard output. |
| `no-hygiene` | `false` | Set to `true` to check links without repository presence checks. |
| `exclude` | Empty | Additional repository-relative patterns, one per line; appends to configured exclusions. |

For example, add `with: {fail-on: warning}` to the Preflight step to fail on warnings as well as errors. Report creation and upload are separate steps; selecting SARIF output alone does not upload it to GitHub code scanning.

To skip generated documentation for a particular workflow:

```yaml
- uses: Roman-15/maintainer-preflight@v0.2.0
  with:
    exclude: |
      docs/generated/**
      reports/**
```

Write one pattern per line without shell quotes. Blank lines and surrounding whitespace are ignored; spaces within a pattern are preserved. These patterns supplement the repository configuration for this audit and do not alter the configuration file. Exclusions affect Markdown scanning, including in the action; repository presence checks still run.

When checking a local checkout of this tool in another CI system, run the following after Python setup:

```sh
python -m pip install .
maintainer-preflight . --fail-on error
```

To use that installation for another project, pass the other project's path to `maintainer-preflight`.

## Scope and limits

Preflight scans `.md` and `.markdown` files recursively. Common build, dependency, and cache directories are excluded by default, file discovery skips symbolic links, and Markdown files larger than 1 MiB are skipped with a warning. A documentation link can resolve through a symbolic link within the audit root; links outside the root are rejected. Preflight intentionally uses a conservative Markdown parser rather than a full CommonMark renderer. Static-site extensions, custom heading IDs, and renderer-specific routes may need exclusions or a separate checker.

The tool does not test remote URLs, install dependencies, execute tests, scan secrets, assess vulnerabilities, or certify a repository as secure. A clean report means that the enabled checks found no issues in the scanned content.

## Development

```sh
python -m unittest discover -s tests -v
python -m maintainer_preflight . --fail-on warning
```

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change. Report security concerns according to [SECURITY.md](SECURITY.md). Planned improvements are in the [roadmap](docs/roadmap.md), and release notes are in the [changelog](CHANGELOG.md).

Maintained by [Roman-15](https://github.com/Roman-15). Released under the [MIT license](LICENSE).
