"""Repository discovery, bounded without following symlinks."""

from dataclasses import dataclass
from collections import deque
from fnmatch import fnmatchcase
import os
from pathlib import Path
import stat

from .config import Config, ConfigurationError
from .models import Finding

IGNORED_DIRS = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "vendor", "vendors",
    "dist", "build", "__pycache__", ".tox", ".nox", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".next", "coverage", "site-packages",
})


@dataclass(frozen=True)
class Report:
    repository: str
    markdown_files: int
    findings: tuple[Finding, ...]
    ignored_findings: int

    @property
    def counts(self) -> dict[str, int]:
        return {level: sum(f.severity == level for f in self.findings)
                for level in ("error", "warning", "note")}

    def fails(self, threshold: str) -> bool:
        levels = {"error": {"error"}, "warning": {"error", "warning"}, "none": set()}[threshold]
        return any(f.severity in levels for f in self.findings)


def discover_markdown(root: Path, config: Config) -> list[Path]:
    found: list[Path] = []
    examined = 0

    def excluded(path: Path) -> bool:
        relative = path.relative_to(root).as_posix()
        return any(fnmatchcase(relative, pattern) for pattern in config.exclude)

    pending = deque([(root, 0)])
    while pending:
        directory, depth = pending.popleft()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    examined += 1
                    if examined > 100000:
                        raise ConfigurationError("Repository exceeds the 100,000-entry scan limit")
                    path = Path(entry.path)
                    if entry.is_symlink() or (os.name == "nt" and
                            getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
                            & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                        continue
                    if excluded(path):
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name.lower() in IGNORED_DIRS:
                            continue
                        if depth >= 64:
                            raise ConfigurationError("Repository exceeds the 64-level directory scan limit")
                        pending.append((path, depth + 1))
                    elif entry.is_file(follow_symlinks=False) and path.suffix.lower() in {".md", ".markdown"}:
                        found.append(path)
                        if len(found) > 10000:
                            raise ConfigurationError("Repository exceeds the 10,000-Markdown-file scan limit")
        except OSError as exc:
            raise ConfigurationError(f"Cannot traverse repository: {exc}") from exc
    return sorted(found, key=lambda p: p.relative_to(root).as_posix())


def audit(root: Path, config: Config, *, hygiene: bool = True) -> Report:
    from .hygiene import check_hygiene
    from .links import check_links

    files = discover_markdown(root, config)
    findings = check_links(root, files)
    if hygiene:
        findings.extend(check_hygiene(root))
    selected = [f for f in findings if f.rule_id not in config.ignore_rules]
    selected.sort(key=lambda f: (f.path, f.line, f.rule_id, f.message))
    return Report(root.name, len(files), tuple(selected), len(findings) - len(selected))
