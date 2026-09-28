"""Executable evidence, consistency, workflow, and PDF guards for paper delivery."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class GateIssue:
    rule_id: str
    status: str
    severity: str
    affected_artifacts: list[str]
    observed: str
    expected: str
    remediation: str


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _issue(rule_id: str, observed: str, expected: str, remediation: str, *artifacts: str, severity: str = "error") -> GateIssue:
    return GateIssue(rule_id, "fail", severity, list(artifacts), observed, expected, remediation)


def validate_artifact_registry(root: str | Path, registry: dict[str, Any]) -> list[GateIssue]:
    """Enforce verified, hash-backed results and one source for each published value."""
    base = Path(root)
    issues: list[GateIssue] = []
    artifacts = registry.get("artifacts", [])
    if not isinstance(artifacts, list):
        return [_issue("VAL-GATE-012", "artifacts is not a list", "a list of registered artifacts", "write a machine-readable registry")]
    seen_values: dict[str, Any] = {}
    for item in artifacts:
        if not isinstance(item, dict):
            issues.append(_issue("VAL-GATE-012", "invalid artifact record", "mapping", "replace the invalid record"))
            continue
        relative = str(item.get("path", ""))
        path = base / relative
        if not path.is_file():
            issues.append(_issue("VAL-GATE-012", "missing artifact", "existing artifact", "rerun the producing stage", relative))
        elif item.get("sha256") != _digest(path):
            issues.append(_issue("VAL-GATE-012", "artifact hash mismatch", "registered SHA-256", "re-register after validation", relative))
        if item.get("role") == "result" and item.get("verification_status") != "verified":
            issues.append(_issue("VAL-GATE-006", str(item.get("verification_status")), "verified result", "run validation before publishing", relative))
        for name, value in (item.get("published_values") or {}).items():
            if name in seen_values and seen_values[name] != value:
                issues.append(_issue("VAL-GATE-012", f"{name} has conflicting values", "one registered value", "remove copied or stale value", relative))
            seen_values[name] = value
    return issues


def validate_figure_registry(root: str | Path, figures: Iterable[dict[str, Any]]) -> list[GateIssue]:
    base, issues = Path(root), []
    for figure in figures:
        figure_id = str(figure.get("figure_id", "unknown"))
        missing = [key for key in ("claim", "evidence_role", "source_artifact", "path") if not figure.get(key)]
        if missing:
            issues.append(_issue("FIG-GRAMMAR-001", f"missing {', '.join(missing)}", "claim, role, source, and path", "complete figure registry", figure_id))
            continue
        if not (base / str(figure["path"])).is_file() or not (base / str(figure["source_artifact"])).is_file():
            issues.append(_issue("FIG-GRAMMAR-007", "figure or source is missing", "existing registered source", "regenerate figure from registered result", figure_id))
        if not figure.get("caption"):
            issues.append(_issue("FIG-GRAMMAR-002", "caption missing", "caption and surrounding analysis", "add caption and analysis", figure_id, severity="warning"))
    return issues


def validate_table_registry(tables: Iterable[dict[str, Any]]) -> list[GateIssue]:
    issues: list[GateIssue] = []
    for table in tables:
        table_id = str(table.get("table_id", "unknown"))
        if not table.get("source_artifact"):
            issues.append(_issue("TABLE-SOURCE-001", "source_artifact missing", "structured result source", "register the generating result artifact", table_id))
        if table.get("title_position") != "above":
            issues.append(_issue("TABLE-STYLE-001", str(table.get("title_position")), "title above table", "use the paper template table wrapper", table_id))
        if table.get("vertical_rules"):
            issues.append(_issue("TABLE-STYLE-001", "vertical rules enabled", "three-line/no vertical rules", "remove vertical rules", table_id, severity="warning"))
        values = table.get("displayed_values", {})
        if isinstance(values, dict):
            for variable, rendered in values.items():
                digits = {len(part.split(".", 1)[1]) if "." in part else 0 for part in map(str, rendered if isinstance(rendered, list) else [rendered])}
                if len(digits) > 1:
                    issues.append(_issue("TABLE-NUM-001", f"inconsistent decimals for {variable}", "one display precision per variable", "format values via a shared rounding policy", table_id))
    return issues


def validate_writing(text: str) -> list[GateIssue]:
    """Flag unsupported strong claims only when no nearby evidence marker exists."""
    issues: list[GateIssue] = []
    for match in re.finditer(r"显著|精确|最优|稳健|证明|significant|precise|optimal|robust", text, re.I):
        window = text[max(0, match.start() - 180): match.end() + 180]
        if not re.search(r"\[claim:[^\]]+\]|VAL-GATE-\d+|图\s*\d|表\s*\d|Figure\s*\d|Table\s*\d|p\s*[<=>]", window, re.I):
            issues.append(_issue("WRITE-SIGNIFICANT-001", match.group(), "nearby registered evidence", "add evidence or soften the claim", "paper_source", severity="warning"))
    return issues


def validate_transition(current: str, next_state: str, ordered_states: list[str]) -> list[GateIssue]:
    if current not in ordered_states or next_state not in ordered_states:
        return [_issue("WF-STATE-001", f"{current}->{next_state}", "known workflow states", "use configured workflow state")]
    if next_state == "failed" or ordered_states.index(next_state) == ordered_states.index(current) + 1:
        return []
    return [_issue("WF-STATE-001", f"illegal transition {current}->{next_state}", "next sequential state", "complete current gate before advancing")]


def preflight_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Run deterministic checks and label visual-only checks for manual review."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - environment dependent
        return {"status": "blocked", "issues": [asdict(_issue("TEST-PDF-001", str(exc), "PyMuPDF available", "install PyMuPDF"))]}
    path = Path(pdf_path)
    reported_path = path.name
    try:
        reported_path = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        pass
    issues: list[GateIssue] = []
    if not path.is_file():
        return {"status": "fail", "issues": [asdict(_issue("TEST-PDF-001", "PDF missing", "readable PDF", "render the document", reported_path))]}
    document = fitz.open(path)
    pages = []
    if not document.page_count:
            issues.append(_issue("TEST-PDF-001", "0 pages", "at least 1 page", "render a nonempty document", reported_path))
    for number, page in enumerate(document, start=1):
        rect = page.rect
        page_info = {"page": number, "width_pt": round(rect.width, 2), "height_pt": round(rect.height, 2), "rotation": page.rotation, "text_chars": len(page.get_text().strip())}
        pages.append(page_info)
        if abs(rect.width - 595.28) > 1 or abs(rect.height - 841.89) > 1 or page.rotation != 0:
            issues.append(_issue("TEST-PDF-001", json.dumps(page_info), "A4 portrait (595±1 × 842±1, rotation 0)", "use A4 portrait template", reported_path))
        if page_info["text_chars"] < 10:
            issues.append(_issue("PDF-PREFLIGHT-004", f"page {number} has little extractable text", "nonblank page", "inspect rendered page", reported_path, severity="warning"))
    document.close()
    status = "pass" if not any(issue.severity == "error" for issue in issues) else "fail"
    return {"status": status, "pdf": reported_path, "page_count": len(pages), "pages": pages, "issues": [asdict(issue) for issue in issues], "manual_review_required": ["overflow/cropping", "font substitution", "caption separation", "table and code clipping"]}
