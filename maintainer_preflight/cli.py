"""Command-line entry point."""

import argparse
import os
from pathlib import Path
import sys
import tempfile

from . import __version__
from .config import ConfigurationError, load_config
from .reporters import render
from .scanner import audit


def _write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=".preflight-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check local Markdown links and maintainer files without network access.")
    parser.add_argument("path", nargs="?", default=".", help="repository directory (default: current directory)")
    parser.add_argument("--format", choices=("text", "json", "markdown", "sarif"), default="text")
    parser.add_argument("--output", type=Path, help="write report atomically to this file instead of stdout")
    parser.add_argument("--fail-on", choices=("error", "warning", "none"), help="exit threshold (default: error)")
    parser.add_argument("--config", type=Path, help="explicit TOML config (default: repository's .maintainer-preflight.toml)")
    parser.add_argument("--no-hygiene", action="store_true", help="check Markdown links only")
    parser.add_argument("--version", action="version", version=f"maintainer-preflight {__version__}")
    args = parser.parse_args(argv)
    try:
        root = Path(args.path).resolve(strict=True)
        if not root.is_dir():
            raise ConfigurationError(f"Repository path is not a directory: {args.path}")
        config = load_config(root, args.config)
        report = audit(root, config, hygiene=not args.no_hygiene)
        content = render(report, args.format)
        if args.output is not None:
            _write_output(args.output, content)
        else:
            sys.stdout.write(content)
        return int(report.fails(args.fail_on or config.fail_on))
    except (ConfigurationError, OSError, UnicodeError) as exc:
        print(f"maintainer-preflight: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
