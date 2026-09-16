# Contributing

Useful bug reports, focused patches, documentation improvements, and real repository examples are welcome. The current maintainer is [Roman-15](https://github.com/Roman-15).

## Report a problem

Open an issue with the command you ran, Python and operating-system versions, actual output, and expected behavior. For a Markdown parsing problem, include the smallest document and directory layout that reproduce it. Remove private paths, tokens, and confidential content before posting.

Use the [security policy](SECURITY.md) for security-sensitive reports.

## Work locally

Python 3.11 or later is required. There are no runtime dependencies.

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
python -m maintainer_preflight . --fail-on warning
```

Run these commands from the repository root. The module invocation also works directly from the source checkout without installation.

## Send a patch

1. Open an issue first for a new rule, dependency, or substantial change in behavior so its scope can be discussed.
2. Create a branch with one focused improvement.
3. Add a regression test for a behavior change or bug fix. Use temporary directories for repository fixtures and avoid network access.
4. Update the relevant documentation and add a note to the unreleased section of [CHANGELOG.md](CHANGELOG.md).
5. Run the tests and Preflight, then open a pull request describing the problem, change, and validation.

Documentation corrections can be proposed directly. Keep a pull request small enough to review independently. Passing checks do not guarantee acceptance; a change must also fit the project's scope.

## Design principles

- Keep audits offline and predictable. Never execute code from the repository being audited.
- Prefer the Python standard library and clear error messages.
- Preserve stable rule identifiers when their meaning has not changed.
- Make reports useful on Windows, macOS, and Linux, including paths with spaces and Unicode characters.
- Document parser limits and ambiguous Markdown behavior instead of silently promising full renderer compatibility.
- Add checks for concrete maintenance problems; avoid scores that imply a project is healthy merely because files exist.

Treat other participants respectfully and focus review comments on the work. Contributions are made under the repository's [MIT license](LICENSE).
