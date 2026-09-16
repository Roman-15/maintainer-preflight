"""Stable reports for people, CI and code scanning tools."""

import json
from urllib.parse import quote

from . import __version__
from .config import RULES
from .scanner import Report


def render(report: Report, format_name: str) -> str:
    return {"text": text_report, "json": json_report, "markdown": markdown_report,
            "sarif": sarif_report}[format_name](report)


def text_report(report: Report) -> str:
    lines = [f"Maintainer Preflight {__version__} | {_plain(report.repository)}",
             f"Scanned {report.markdown_files} Markdown file(s)."]
    for item in report.findings:
        lines.extend([f"{_plain(item.path)}:{item.line}: {item.severity} {item.rule_id} {_plain(item.message)}",
                      f"  Fix: {_plain(item.suggestion)}"])
    counts = report.counts
    lines.append(f"{counts['error']} error(s), {counts['warning']} warning(s), {counts['note']} note(s); "
                 f"{report.ignored_findings} finding(s) ignored by configuration.")
    return "\n".join(lines) + "\n"


def json_report(report: Report) -> str:
    return json.dumps({"schema_version": 1, "tool": "maintainer-preflight", "version": __version__,
                       "repository": report.repository, "markdown_files": report.markdown_files,
                       "counts": report.counts, "ignored_findings": report.ignored_findings,
                       "findings": [f.to_dict() for f in report.findings]}, indent=2, ensure_ascii=False) + "\n"


def _plain(value: str) -> str:
    return "".join(f"\\x{ord(char):02x}" if ord(char) < 32 or ord(char) == 127 else char for char in value)


def _cell(value: str) -> str:
    # Findings include repository-controlled text: keep Markdown/image syntax inert.
    entities = {"&": "&amp;", "<": "&lt;", ">": "&gt;", "|": "&#124;", "`": "&#96;",
                "[": "&#91;", "]": "&#93;", "\\": "&#92;", "*": "&#42;", "_": "&#95;"}
    return "".join(entities.get(char, char) for char in _plain(value))


def markdown_report(report: Report) -> str:
    lines = ["# Maintainer Preflight", "", f"Repository: {_cell(report.repository)}. "
             f"Scanned {report.markdown_files} Markdown file(s).", "",
             "| Severity | Rule | Location | Finding | Suggested fix |",
             "| --- | --- | --- | --- | --- |"]
    for item in report.findings:
        lines.append("| " + " | ".join(_cell(value) for value in
                     (item.severity, item.rule_id, f"{item.path}:{item.line}", item.message, item.suggestion)) + " |")
    if not report.findings:
        lines.extend(["", "No findings from the enabled checks."])
    lines.extend(["", f"Errors: {report.counts['error']}. Warnings: {report.counts['warning']}. "
                  f"Notes: {report.counts['note']}. Ignored: {report.ignored_findings}.", ""])
    return "\n".join(lines)


def sarif_report(report: Report) -> str:
    rule_ids = sorted({f.rule_id for f in report.findings})
    results = []
    for item in report.findings:
        result = {"ruleId": item.rule_id, "ruleIndex": rule_ids.index(item.rule_id),
                  "level": item.severity, "message": {"text": item.message + " Fix: " + item.suggestion}}
        # Missing-file hygiene checks concern the repository rather than an existing code location.
        if item.rule_id.startswith("LINK"):
            result["locations"] = [{"physicalLocation": {
                "artifactLocation": {"uri": quote(item.path, safe="/"), "uriBaseId": "%SRCROOT%"},
                "region": {"startLine": max(1, item.line)},
            }}]
        results.append(result)
    return json.dumps({"$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0",
                       "runs": [{"tool": {"driver": {"name": "maintainer-preflight", "version": __version__,
                           "rules": [{"id": rule, "shortDescription": {"text": RULES.get(rule, rule)}}
                                     for rule in rule_ids]}}, "results": results}]}, indent=2, ensure_ascii=False) + "\n"
