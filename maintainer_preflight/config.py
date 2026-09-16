"""Strict, small configuration without executing project code."""

from dataclasses import dataclass
from pathlib import Path
import stat
import tomllib

RULES = {
    "LINK001": "Missing local link target",
    "LINK002": "Missing heading or HTML anchor",
    "LINK003": "Link path case mismatch",
    "LINK004": "Link leaves repository",
    "LINK005": "Unreadable Markdown document",
    "LINK006": "Oversized Markdown document",
    "DOC001": "Missing README",
    "DOC002": "Missing license file",
    "DOC003": "Missing contributor guide",
    "DOC004": "Missing security policy",
    "DOC005": "Missing changelog",
    "TEST001": "No test evidence",
    "CI001": "No CI configuration",
    "SCAN001": "Incomplete repository inspection",
}


class ConfigurationError(ValueError):
    """A user-correctable invocation or configuration error."""


@dataclass(frozen=True)
class Config:
    exclude: tuple[str, ...] = ()
    ignore_rules: tuple[str, ...] = ()
    fail_on: str = "error"


def load_config(root: Path, explicit: Path | None = None) -> Config:
    path = explicit if explicit is not None else root / ".maintainer-preflight.toml"
    if path.is_symlink():
        raise ConfigurationError(f"Configuration must not be a symlink: {path}")
    if explicit is None and not path.exists():
        return Config()
    try:
        metadata = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(metadata.st_mode) or (
                getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
            raise ConfigurationError(f"Configuration must be a regular file: {path}")
        if metadata.st_size > 65536:
            raise ConfigurationError("Configuration exceeds the 64 KiB limit")
        with path.open("rb") as handle:
            content = handle.read(65537)
        if len(content) > 65536:
            raise ConfigurationError("Configuration exceeds the 64 KiB limit")
        data = tomllib.loads(content.decode("utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationError(f"Cannot read configuration {path}: {exc}") from exc
    if set(data) != {"preflight"} or not isinstance(data["preflight"], dict):
        raise ConfigurationError("Configuration requires only a [preflight] table")
    options = data["preflight"]
    unknown = set(options) - {"exclude", "ignore_rules", "fail_on"}
    if unknown:
        raise ConfigurationError("Unknown configuration keys: " + ", ".join(sorted(unknown)))
    for key in ("exclude", "ignore_rules"):
        value = options.get(key, [])
        if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
            raise ConfigurationError(f"{key} must be an array of non-empty strings")
    unknown_rules = set(options.get("ignore_rules", [])) - set(RULES)
    if unknown_rules:
        raise ConfigurationError("Unknown rule IDs: " + ", ".join(sorted(unknown_rules)))
    threshold = options.get("fail_on", "error")
    if threshold not in ("error", "warning", "none"):
        raise ConfigurationError("fail_on must be error, warning, or none")
    return Config(tuple(options.get("exclude", [])), tuple(options.get("ignore_rules", [])), threshold)
