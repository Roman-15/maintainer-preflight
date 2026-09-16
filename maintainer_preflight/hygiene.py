"""Conservative, presence-only repository documentation, test, and CI checks.

These checks do not establish a license's legal sufficiency, test coverage, or
the safety or quality of CI. Repository code and configuration are never run.
Symlinks are skipped, and scans exclude common generated/vendor directories.
"""

from collections import deque
import os
from pathlib import Path, PurePosixPath
import stat

from .models import Finding


MAX_ENTRIES = 50_000
MAX_DEPTH = 16
_IGNORED_DIRS = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "env", "envs", ".env",
    "node_modules", "vendor", "vendors", "third_party", "third-party",
    "dist", "build", "target", "out", "coverage", "htmlcov",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".nox", ".next", ".nuxt", ".cache", "site-packages", ".gradle",
})
_DOC_DIRS = {(), ("docs",), ("doc",), (".github",)}
_DOC_EXTENSIONS = {"", ".md", ".markdown", ".rst", ".txt", ".adoc", ".asciidoc"}
_SOURCE_EXTENSIONS = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".go", ".rs",
    ".rb", ".java", ".kt", ".kts", ".scala", ".php", ".cs", ".cpp", ".c",
    ".cc", ".cxx", ".swift", ".exs", ".jl", ".r", ".lua", ".dart",
    ".sh", ".ps1",
}


def _files(root: Path) -> tuple[list[PurePosixPath], set[str]]:
    """Walk at most MAX_ENTRIES entries and MAX_DEPTH nested directories."""
    paths: list[PurePosixPath] = []
    limitations: set[str] = set()
    pending = deque([(root, PurePosixPath("."), 0)])
    examined = 0
    while pending:
        directory, relative, depth = pending.popleft()
        try:
            with os.scandir(directory) as entries:
                batch = []
                for entry in entries:
                    if examined >= MAX_ENTRIES:
                        limitations.add("entry limit reached")
                        break
                    examined += 1
                    batch.append(entry)
                for entry in sorted(batch, key=lambda item: item.name.casefold()):
                    try:
                        # Do not even resolve links: no outside target is inspected.
                        if entry.is_symlink():
                            continue
                        # Windows junctions can redirect traversal without
                        # being classified as symlinks on Python 3.11.
                        if (os.name == "nt" and
                                getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
                                & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                            continue
                        rel = relative / entry.name
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name.casefold() in _IGNORED_DIRS:
                                continue
                            if depth >= MAX_DEPTH:
                                limitations.add("directory depth limit reached")
                            else:
                                pending.append((Path(entry.path), rel, depth + 1))
                        elif entry.is_file(follow_symlinks=False):
                            paths.append(rel)
                    except OSError:
                        limitations.add("one or more entries could not be inspected")
        except OSError:
            limitations.add("one or more directories could not be read")
        if examined >= MAX_ENTRIES:
            if pending:
                limitations.add("entry limit reached")
            break
    return paths, limitations


def _document(path: PurePosixPath, names: set[str]) -> bool:
    lowered = PurePosixPath(path.as_posix().casefold())
    if lowered.parts[:-1] not in _DOC_DIRS:
        return False
    return lowered.stem in names and lowered.suffix in _DOC_EXTENSIONS


def _license(path: PurePosixPath) -> bool:
    if _document(path, {"license", "licence", "copying", "unlicense"}):
        return True
    lowered = PurePosixPath(path.as_posix().casefold())
    # Common multi-license repositories use LICENSE-MIT / LICENSE-APACHE.
    return (lowered.parts[:-1] in _DOC_DIRS
            and lowered.name.startswith(("license-", "licence-", "copying-"))
            and lowered.suffix in _DOC_EXTENSIONS)


def _test_evidence(path: PurePosixPath) -> bool:
    lowered = PurePosixPath(path.as_posix().casefold())
    if lowered.suffix not in _SOURCE_EXTENSIONS:
        return False
    if any(part in {"test", "tests", "spec", "specs", "__tests__"}
           for part in lowered.parts[:-1]):
        return True
    stem = lowered.stem
    if (stem in {"test", "tests"} or stem.startswith("test_")
            or stem.endswith(("_test", "_tests", "_spec", ".test", ".spec"))):
        return True
    # Camel-case test classes are conventional in JVM/.NET/PHP projects.
    return (lowered.suffix in {".java", ".kt", ".scala", ".cs", ".php"}
            and path.stem.endswith(("Test", "Tests", "Spec")))


def _ci_evidence(path: PurePosixPath) -> bool:
    lowered = PurePosixPath(path.as_posix().casefold())
    if len(lowered.parts) == 1:
        return lowered.name in {
            ".gitlab-ci.yml", ".gitlab-ci.yaml", ".travis.yml", ".travis.yaml",
            "azure-pipelines.yml", "azure-pipelines.yaml", "jenkinsfile",
            "bitbucket-pipelines.yml", "bitbucket-pipelines.yaml",
            ".drone.yml", ".drone.yaml", ".woodpecker.yml", ".woodpecker.yaml",
            ".cirrus.yml", ".cirrus.yaml", "appveyor.yml", ".appveyor.yml",
        }
    if (lowered.parts[:-1] == (".github", "workflows")
            and lowered.suffix in {".yml", ".yaml"}):
        return True
    if lowered.as_posix() in {
        ".circleci/config.yml", ".circleci/config.yaml",
        ".buildkite/pipeline.yml", ".buildkite/pipeline.yaml",
    }:
        return True
    return (lowered.parts[0] == ".woodpecker"
            and lowered.suffix in {".yml", ".yaml"})


def check_hygiene(root: Path) -> list[Finding]:
    """Report missing conventional files; findings do not certify readiness.

    Only regular files count as evidence. Empty directories and generated or
    vendored files do not count. Missing-file paths suggest a conventional
    location, and their line number is 1 because there is no existing line.
    """
    paths, limitations = _files(root)
    rules = [
        ("DOC001", "error", "README.md", any(_document(p, {"readme"}) for p in paths),
         "No README detected in the root, docs, doc, or .github directory.",
         "Add a README explaining the project, installation, and basic usage."),
        ("DOC002", "warning", "LICENSE", any(_license(p) for p in paths),
         "No conventional license file detected (file presence only; no legal assessment).",
         "Choose appropriate license terms and add a LICENSE or COPYING file."),
        ("DOC003", "warning", "CONTRIBUTING.md", any(_document(p, {"contributing"}) for p in paths),
         "No contributing guide detected.",
         "Document setup, checks, and how contributors can propose changes."),
        ("DOC004", "warning", "SECURITY.md", any(_document(p, {"security"}) for p in paths),
         "No security policy file detected.",
         "Explain supported versions and how to report a vulnerability privately."),
        ("DOC005", "note", "CHANGELOG.md", any(_document(p, {"changelog", "changes", "history", "news", "release_notes", "release-notes"}) for p in paths),
         "No conventional changelog file detected.",
         "Record user-visible changes in a changelog or release notes file."),
        ("TEST001", "warning", "tests", any(_test_evidence(p) for p in paths),
         "No conventional test source files detected (presence only; tests were not run).",
         "Add meaningful tests, or document a test layout this scanner does not recognize."),
        ("CI001", "warning", ".github/workflows", any(_ci_evidence(p) for p in paths),
         "No recognized CI configuration detected (presence only; CI quality is not assessed).",
         "Add CI for the project's checks, or document an externally configured CI service."),
    ]
    findings = [Finding(rule_id, severity, path, 1, message, suggestion)
                for rule_id, severity, path, present, message, suggestion in rules if not present]
    if limitations:
        findings.append(Finding(
            "SCAN001", "warning", ".", 1,
            "Repository hygiene scan was incomplete: " + "; ".join(sorted(limitations)) + ".",
            "Review missing-file findings manually; files beyond scan limits may exist.",
        ))
    return findings
