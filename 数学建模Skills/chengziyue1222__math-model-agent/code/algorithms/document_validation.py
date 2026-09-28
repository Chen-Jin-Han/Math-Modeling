"""Rule-pack consumers for paper structure, layout evidence, figures and tables.

These checks report evidence and uncertainty.  They do not turn an unavailable
visual measurement into a pass.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .production_guards import GateIssue


def issue(rule_id: str, observed: str, expected: str, remediation: str, *paths: str, severity: str = "error") -> GateIssue:
    return GateIssue(rule_id, "fail", severity, list(paths), observed, expected, remediation)


def inspect_pdf_layout(pdf_path: str | Path, *, expected_a4: bool = True) -> dict[str, Any]:
    """Extract inspectable page geometry, font use, text sizes, and whitespace."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover
        return {"status": "blocked", "issues": [issue("TEST-PDF-001", str(exc), "PyMuPDF", "install PyMuPDF").__dict__]}
    path = Path(pdf_path)
    reported_path = path.name
    try:
        reported_path = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        pass
    document = fitz.open(path)
    report: dict[str, Any] = {"pdf": reported_path, "page_count": document.page_count, "pages": [], "fonts": {}, "issues": [], "manual_review_required": []}
    fonts: Counter[str] = Counter()
    sizes: Counter[float] = Counter()
    for number, page in enumerate(document, 1):
        rect = page.rect
        blocks = page.get_text("dict").get("blocks", [])
        text_spans = [span for block in blocks if block.get("type") == 0 for line in block.get("lines", []) for span in line.get("spans", [])]
        for span in text_spans:
            fonts[str(span.get("font", "unknown"))] += len(str(span.get("text", "")))
            sizes[round(float(span.get("size", 0)), 1)] += len(str(span.get("text", "")))
        bboxes = [span["bbox"] for span in text_spans if span.get("text", "").strip()]
        margins = None
        if bboxes:
            left, top = min(box[0] for box in bboxes), min(box[1] for box in bboxes)
            right, bottom = max(box[2] for box in bboxes), max(box[3] for box in bboxes)
            margins = {"left_pt": round(left, 1), "right_pt": round(rect.width-right, 1), "top_pt": round(top, 1), "bottom_pt": round(rect.height-bottom, 1)}
            if min(margins.values()) < 8:
                report["issues"].append(issue("LAYOUT-MARGIN-001", json.dumps(margins), "no text within 8 pt of media edge", "adjust page geometry", reported_path).__dict__)
        page_info = {"page": number, "width_pt": round(rect.width, 2), "height_pt": round(rect.height, 2), "rotation": page.rotation, "text_chars": sum(len(str(s.get("text", ""))) for s in text_spans), "margins": margins}
        report["pages"].append(page_info)
        if margins and margins["bottom_pt"] > 430 and page_info["text_chars"] < 220:
            report["issues"].append(issue("LAYOUT-DENSITY-001", f"page {number} sparse: {page_info['text_chars']} chars, bottom margin {margins['bottom_pt']} pt", "review sparse page for intentional section break or missing content", "record manual disposition or revise layout", reported_path, severity="warning").__dict__)
        if expected_a4 and (abs(rect.width-595.28)>1 or abs(rect.height-841.89)>1 or page.rotation != 0):
            report["issues"].append(issue("LAYOUT-PAGE-001", json.dumps(page_info), "A4 portrait", "render with configured A4 profile", reported_path).__dict__)
        if page_info["text_chars"] < 10:
            report["issues"].append(issue("PDF-PREFLIGHT-004", f"page {number} has little text", "nonblank page", "inspect or remove page", reported_path, severity="warning").__dict__)
    document.close()
    report["fonts"] = dict(fonts.most_common())
    report["font_sizes"] = dict(sizes.most_common())
    if not fonts:
        report["manual_review_required"].append("image-only PDF has no inspectable text-font evidence")
    report["manual_review_required"] += ["table clipping", "caption separation", "code line wrapping", "font substitution semantic review"]
    report["status"] = "fail" if any(row["severity"] == "error" for row in report["issues"]) else "pass"
    return report


def validate_paper_structure(source: str, *, dependency_analysis: dict[str, Any] | None = None, abstract_page_count: int | None = None) -> list[GateIssue]:
    """Check required structural evidence without forcing a unified-model section."""
    rules: list[tuple[str, tuple[str, ...]]] = [
        ("STRUCT-RESTATEMENT-001", ("问题重述", "Problem Restatement")),
        ("STRUCT-ANALYSIS-001", ("问题分析", "Problem Analysis")),
        ("STRUCT-ASSUMPTION-001", ("模型假设", "统一模型与假设", "Assumptions")),
        ("STRUCT-SYMBOL-001", ("符号说明", "Notation")),
        ("STRUCT-VALIDATION-001", ("模型检验", "Validation")),
        ("STRUCT-EVALUATION-001", ("模型评价", "模型检验与评价", "Evaluation")),
        ("STRUCT-REF-001", ("参考文献", "References")),
        ("STRUCT-APPENDIX-001", ("附录", "Appendix")),
    ]
    issues = [issue(rule_id, "section absent", "required section", "add the section", "paper_source") for rule_id, labels in rules if not any(label.lower() in source.lower() for label in labels)]
    if not re.search(r"摘要|Abstract", source, re.I):
        issues.append(issue("STRUCT-ABSTRACT-001", "abstract absent", "one abstract with method/result/validation", "add evidence-backed abstract", "paper_source"))
    if not re.search(r"关键词|Keywords?", source, re.I):
        issues.append(issue("STRUCT-KEYWORD-001", "keywords absent", "4-7 keywords", "add keyword line", "paper_source"))
    if abstract_page_count is not None and abstract_page_count != 1:
        issues.append(issue("STRUCT-ABSTRACT-001", f"abstract spans {abstract_page_count} pages", "one page", "adjust abstract layout", "PDF"))
    shared = bool((dependency_analysis or {}).get("shared_kernel_required"))
    unified = bool(re.search(r"统一模型|Unified Model", source, re.I))
    if shared and not unified:
        issues.append(issue("STRUCT-UNIFIED-001", "dependency analysis requires shared kernel", "unified-model section", "add shared model", "paper_source"))
    if not shared and unified:
        issues.append(issue("STRUCT-UNIFIED-001", "unified model present without dependency trigger", "no forced unified section", "remove or justify it", "paper_source", severity="warning"))
    return issues


def select_figure_grammar(problem_signals: Iterable[str], grammar: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select only figure recommendations whose problem signal is explicitly present."""
    signals = " ".join(problem_signals)
    return [{"problem_signal": row["problem_signal"], "recommended_figure": row["recommended_figure"], "must_show": row.get("must_show", [])} for row in grammar if row.get("problem_signal") in signals]


def validate_cross_artifact_values(verified: dict[str, Any], displays: Iterable[dict[str, Any]]) -> list[GateIssue]:
    """Compare raw and displayed values using declared decimal precision."""
    issues: list[GateIssue] = []
    for item in displays:
        quantity = str(item.get("quantity_id", ""))
        if quantity not in verified:
            issues.append(issue("TEST-NUM-001", f"unknown {quantity}", "registered quantity", "register source value", str(item.get("artifact", ""))))
            continue
        decimals = item.get("decimals")
        if not isinstance(decimals, int) or decimals < 0:
            issues.append(issue("NUM-PRECISION-001", f"invalid display precision for {quantity}", "non-negative decimals", "declare precision", str(item.get("artifact", ""))))
            continue
        expected = round(float(verified[quantity]), decimals)
        if abs(float(item.get("value")) - expected) > 0.5 * 10 ** (-decimals):
            issues.append(issue("REJECT-001", f"{quantity}={item.get('value')}", f"rounded {expected}", "regenerate display from verified result", str(item.get("artifact", ""))))
    return issues


def render_three_line_table(headers: list[str], rows: list[list[str]], caption: str, label: str) -> str:
    """Produce a booktabs table from structured values; no raw numeric copying."""
    if not headers or any(len(row) != len(headers) for row in rows):
        raise ValueError("rows must match headers")
    cols = "l" * len(headers)
    body = " \\\\n".join(" & ".join(row) + r" \\" for row in rows)
    return "\n".join([r"\begin{table}[htbp]", r"\centering", f"\\caption{{{caption}}}", f"\\label{{{label}}}", f"\\begin{{tabular}}{{{cols}}}", r"\toprule", " & ".join(headers) + r" \\", r"\midrule", body, r"\bottomrule", r"\end{tabular}", r"\end{table}"])
