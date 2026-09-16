# Roadmap

The first version focuses on a small set of offline checks that maintainers can understand and run locally. The items below are planned work, not shipped features or delivery commitments.

## Near-term improvements

- Exercise the checker against a varied set of public repositories, with permission where changes are proposed, and turn confirmed false positives into small regression fixtures.
- Expand Markdown coverage where a concrete document demonstrates a gap, especially escaped delimiters, mixed HTML, Unicode anchors, and renderer differences.
- Improve explanations for unusual repository layouts and make default exclusions easier to inspect.
- Validate SARIF output with real code-scanning consumers and document an integration based on those results.
- Establish a repeatable release process before publishing versioned packages.

## Evidence of usefulness

Progress should be demonstrated with public, verifiable work: reproducible issues, reviewed fixes, release notes, and examples of maintainers choosing to use the tool. Track which reported problems were confirmed, which fixes were accepted, and where the checker produces false positives.

Document external integrations when maintainers consent to being listed, and link to the underlying repository or maintainer report so readers can verify the example.

## Longer-term questions

- Would a baseline file help established repositories adopt checks gradually without hiding newly introduced problems?
- Which additional repository checks produce actionable findings without making unsupported quality or security claims?
- Does remote-link checking belong in a separate optional tool with its own network, caching, and rate-limit controls?

Suggestions should include a concrete maintenance problem and an example repository layout. See [CONTRIBUTING.md](../CONTRIBUTING.md) for how to propose a change.
