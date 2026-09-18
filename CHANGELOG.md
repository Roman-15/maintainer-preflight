# Changelog

Changes intended for users are recorded here. Releases are distributed from this repository; the package is not currently published to a package registry.

## Unreleased

### Added

- Repeatable `--exclude PATTERN` CLI option for temporary path exclusions that supplement repository configuration without changing it.

## 0.1.0 - 2026-09-16

### Added

- Offline checks for local Markdown link targets, heading anchors, filename casing, and paths outside the audit root.
- Repository presence checks for a README, license, contribution guide, security policy, changelog, tests, and continuous integration.
- Text, Markdown, JSON, and SARIF report formats.
- TOML configuration, rule exclusions, path exclusions, and configurable failure thresholds.
- A reusable GitHub Action with configurable audit path, failure threshold, report format, report file, and optional link-only mode. Action setup can download Python; audits run offline.
- Contributor guidance, security reporting policy, and documented check limitations.
