# Security policy

## Reporting a vulnerability

If this repository has GitHub private vulnerability reporting enabled, use **Security → Report a vulnerability** on its GitHub page. Include affected versions, reproduction steps, expected impact, and a minimal example without private data.

If that option is unavailable, open a public issue asking the maintainer for a private reporting channel. Do not include exploit details, secrets, or sensitive attachments in that issue. Wait for a private channel before sending the report.

There is currently one maintainer and no guaranteed response time. Please avoid public disclosure of a previously unknown vulnerability until there has been a reasonable opportunity to investigate it.

## Supported code

Security fixes target the latest source on the default branch. Older snapshots do not have a separate maintenance commitment. This policy will be updated if versioned maintenance branches are introduced.

## Audit boundaries

Preflight reads repository files to inspect documentation and repository structure. It does not run repository code or make network requests during an audit. File discovery skips symbolic links and Windows reparse points; a documentation link may resolve through a symbolic link only when its target stays within the audit root. Markdown reads have a size limit. Report output can contain local paths and snippets of link destinations, so review reports before sharing them publicly.

Preflight is not a vulnerability scanner, secret scanner, malware detector, or sandbox. The presence of a security policy or test directory does not establish that a repository is safe.
