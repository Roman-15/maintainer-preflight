"""Pass action inputs as literal CLI arguments, never shell commands."""

import os
import sys

from maintainer_preflight.cli import main


def arguments(environment: dict[str, str]) -> list[str]:
    args = ["--format", environment.get("PREFLIGHT_FORMAT", "text")]
    for variable, flag in (("PREFLIGHT_FAIL_ON", "--fail-on"), ("PREFLIGHT_OUTPUT", "--output")):
        if environment.get(variable):
            args.extend([flag, environment[variable]])
    for line in environment.get("PREFLIGHT_EXCLUDE", "").splitlines():
        pattern = line.strip()
        if pattern:
            # Bind values to the option so leading '-' characters stay literal.
            args.append(f"--exclude={pattern}")
    no_hygiene = environment.get("PREFLIGHT_NO_HYGIENE", "false").lower()
    if no_hygiene not in {"true", "false"}:
        raise ValueError("no-hygiene must be true or false")
    if no_hygiene == "true":
        args.append("--no-hygiene")
    # A root beginning with '-' is data, not a second command-line option.
    args.extend(["--", environment.get("PREFLIGHT_ROOT", ".")])
    return args


if __name__ == "__main__":
    try:
        result = main(arguments(dict(os.environ)))
    except ValueError as exc:
        print(f"maintainer-preflight action: {exc}", file=sys.stderr)
        result = 2
    raise SystemExit(result)
