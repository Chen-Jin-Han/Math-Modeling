"""Fail closed on 2026 CUMCM layout rules and repository style defaults."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


MAX_PAPER_BYTES = 20 * 1024 * 1024
MAX_BODY_PAGES = 30
REQUIRED = {
    "A4 margins": ("left=2.5cm", "right=2.5cm", "top=2.5cm", "bottom=2.8cm"),
    "Song/Hei fonts": ("SimSun", "SimHei"),
    "paragraph spacing": (r"\setlength{\parindent}{2em}", r"\linespread{1.65}"),
    "heading hierarchy": (r"\titleformat{\section}", r"\titleformat{\subsection}", r"\fontsize{15pt}{22pt}"),
    "float and three-line tables": (r"\setlength{\floatsep}", r"\toprule", r"\midrule", r"\bottomrule"),
    "abstract first page": (r"\PaperTitle", "摘\\quad 要", r"\pagenumbering{arabic}\setcounter{page}{1}"),
    "no running header": (r"\pagestyle{plain}",),
    "caption, bibliography, code appendix": (
        r"\@makecaption",
        r"\begin{thebibliography}",
        r"\begin{pycode}",
        "numbers=left",
        "numbersep=7pt",
    ),
}
FORBIDDEN = {
    "contents page": (r"\tableofcontents", r"\contentsname", r"\setcounter{tocdepth}", "{tocloft}"),
}


def _display_path(path: Path, project_root: Path | None) -> str:
    resolved = path.resolve()
    roots = [project_root.resolve()] if project_root else [Path.cwd().resolve()]
    for root in roots:
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            continue
    return path.name


def _static_checks(text: str) -> dict[str, dict[str, Any]]:
    checks: dict[str, dict[str, Any]] = {}
    for name, tokens in REQUIRED.items():
        missing = [token for token in tokens if token not in text]
        checks[name] = {"passed": not missing, "missing_tokens": missing}
    for name, tokens in FORBIDDEN.items():
        found = [token for token in tokens if token in text]
        checks[name] = {"passed": not found, "forbidden_tokens": found}

    numbering = r"\pagenumbering{arabic}\setcounter{page}{1}"
    abstract_pos = text.find("摘\\quad 要")
    number_pos = text.find(numbering)
    restatement_pos = text.find(r"\section{问题重述}")
    checks["continuous page numbering"] = {
        "passed": number_pos >= 0 and number_pos < abstract_pos < restatement_pos and text.count(r"\setcounter{page}{1}") == 1,
        "observed_page_one_resets": text.count(r"\setcounter{page}{1}"),
    }
    between = text[abstract_pos:restatement_pos] if 0 <= abstract_pos < restatement_pos else ""
    checks["restatement follows abstract"] = {
        "passed": bool(between) and between.count(r"\newpage") == 1 and r"\tableofcontents" not in between,
        "page_breaks_between": between.count(r"\newpage"),
    }
    return checks


def _footer_page_number(page: Any) -> int | None:
    candidates: list[tuple[float, int]] = []
    center = page.rect.width / 2
    for word in page.get_text("words"):
        x0, y0, x1, _y1, token = word[:5]
        token = str(token).strip()
        if y0 >= page.rect.height * 0.82 and re.fullmatch(r"\d+", token):
            candidates.append((abs(((x0 + x1) / 2) - center), int(token)))
    return min(candidates)[1] if candidates else None


def inspect_pdf(pdf_path: Path, *, project_root: Path | None = None) -> dict[str, Any]:
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - environment dependent
        return {"status": "BLOCKED", "errors": [f"PyMuPDF unavailable: {exc}"]}

    errors: list[str] = []
    warnings: list[str] = []
    if not pdf_path.is_file():
        return {"status": "FAIL", "errors": ["paper PDF is missing"]}
    size = pdf_path.stat().st_size
    if size > MAX_PAPER_BYTES:
        errors.append(f"paper exceeds 20 MiB: {size} bytes")

    document = fitz.open(pdf_path)
    page_texts = [page.get_text("text") for page in document]
    if not page_texts:
        errors.append("paper PDF has no pages")
    abstract_pages = [index + 1 for index, value in enumerate(page_texts) if re.search(r"摘\s*要|Abstract", value, re.I)]
    if not abstract_pages or abstract_pages[0] != 1:
        errors.append(f"abstract is not on electronic page 1: {abstract_pages or 'not found'}")
    contents_pages = [index + 1 for index, value in enumerate(page_texts) if re.search(r"(?m)^\s*(目录|Contents)\s*$", value, re.I)]
    if contents_pages:
        errors.append(f"contents page is forbidden: pages {contents_pages}")

    appendix_pages = [index + 1 for index, value in enumerate(page_texts) if re.search(r"附\s*录|Appendix", value, re.I)]
    pages_before_appendix = appendix_pages[0] - 1 if appendix_pages else None
    body_pages_before_appendix = appendix_pages[0] - 2 if appendix_pages else None
    if body_pages_before_appendix is None:
        errors.append("appendix start was not found")
    elif body_pages_before_appendix > MAX_BODY_PAGES:
        errors.append(
            f"body contains {body_pages_before_appendix} pages before the appendix; "
            "the abstract page is excluded and the maximum body length is 30"
        )

    observed_numbers = [_footer_page_number(page) for page in document]
    expected_numbers = list(range(1, len(document) + 1))
    if observed_numbers != expected_numbers:
        errors.append(f"page numbering is missing, reset, or discontinuous: {observed_numbers}")
    if len(page_texts) >= 2 and "问题重述" not in page_texts[1] and "Problem Restatement" not in page_texts[1]:
        warnings.append("problem restatement was not detected on electronic page 2; inspect the transition")
    document.close()
    return {
        "status": "FAIL" if errors else "PASS",
        "pdf": _display_path(pdf_path, project_root),
        "bytes": size,
        "page_count": len(page_texts),
        "abstract_page": abstract_pages[0] if abstract_pages else None,
        "appendix_page": appendix_pages[0] if appendix_pages else None,
        "pages_before_appendix": pages_before_appendix,
        "body_pages_before_appendix": body_pages_before_appendix,
        "page_numbers": observed_numbers,
        "errors": errors,
        "warnings": warnings,
    }


def validate_layout(
    tex_path: Path,
    pdf_path: Path | None = None,
    *,
    project_root: Path | None = None,
) -> dict[str, object]:
    text = tex_path.read_text(encoding="utf-8")
    checks = _static_checks(text)
    pdf = inspect_pdf(pdf_path, project_root=project_root) if pdf_path else None
    failed = any(not check["passed"] for check in checks.values()) or bool(pdf and pdf["status"] != "PASS")
    return {
        "status": "FAIL" if failed else "PASS",
        "profile": "cumcm_modeling_paper_2026",
        "authority": {
            "official": "A4, margins, abstract/page numbering, no contents, body length, delivery limits",
            "repository_defaults": "fonts, line spacing, heading and caption styling",
        },
        "tex_path": _display_path(tex_path, project_root),
        "checks": checks,
        "pdf_checks": pdf,
    }


def main(
    tex_path: Path,
    report_path: Path | None = None,
    pdf_path: Path | None = None,
    project_root: Path | None = None,
) -> int:
    report = validate_layout(tex_path, pdf_path, project_root=project_root)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report["status"] != "PASS":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    print(f"PASS strict_cumcm_layout {report['tex_path']}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tex", required=True, type=Path)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    raise SystemExit(main(args.tex, args.report, args.pdf, args.project_root))
