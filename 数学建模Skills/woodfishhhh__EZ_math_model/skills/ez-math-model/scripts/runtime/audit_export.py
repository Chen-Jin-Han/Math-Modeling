#!/usr/bin/env python3
"""Post-export object audit for EZ Math Model DOCX/PDF deliverables."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any


PASS = "pass"
WARN = "warn"
FAIL = "fail"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except FileNotFoundError:
        return ""


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(read_text(path))
    except Exception:
        return default


def add_gate(gates: list[dict[str, Any]], item: str, status: str, detail: str, evidence: Any = None) -> None:
    gates.append({"item": item, "status": status, "detail": detail, "evidence": evidence})


def markdown_image_refs(text: str) -> list[str]:
    return [m.group(2).strip() for m in re.finditer(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", text)]


def markdown_formula_counts(text: str) -> dict[str, int]:
    block = len(re.findall(r"(?ms)^\s*\$\$\s*\n.*?\n\s*\$\$\s*$", text))
    all_dollars = len(re.findall(r"(?<!\\)\$", text))
    return {"block_formula_count": block, "dollar_delimiter_count": all_dollars}


def markdown_table_count(lines: list[str]) -> int:
    separator_re = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
    return sum(1 for i in range(len(lines) - 1) if "|" in lines[i] and separator_re.match(lines[i + 1] or ""))


def inspect_docx(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "exists": path.exists(),
        "readable": False,
        "formula_object_count": 0,
        "embedded_image_count": 0,
        "table_object_count": 0,
        "latex_fallback_count": 0,
        "error": "",
    }
    if not path.exists():
        result["error"] = "docx_missing"
        return result
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            document_xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
            result["readable"] = True
            result["formula_object_count"] = document_xml.count("<m:oMath") + document_xml.count("<m:oMathPara")
            result["embedded_image_count"] = len([name for name in names if name.startswith("word/media/")])
            result["table_object_count"] = document_xml.count("<w:tbl")
            result["latex_fallback_count"] = len(re.findall(r"\$[^$]{1,300}\$", document_xml))
    except Exception as exc:
        result["error"] = str(exc)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--paper-output", required=True)
    parser.add_argument("--export-report")
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    args = parser.parse_args()

    workdir = Path(args.workdir).resolve()
    paper_output = Path(args.paper_output).resolve()
    export_report_path = Path(args.export_report).resolve() if args.export_report else workdir / "export_report.json"
    export_report = read_json(export_report_path, {})
    run_state = read_json(workdir / "run_state.json", {})
    run_mode = str(run_state.get("run_mode", "unknown"))
    formal = run_mode == "formal"

    paper_md = paper_output / "paper.md"
    paper_text = read_text(paper_md if paper_md.exists() else workdir / "paper.md")
    image_refs = markdown_image_refs(paper_text)
    formula_counts = markdown_formula_counts(paper_text)
    table_count = markdown_table_count(paper_text.splitlines())

    docx_path = paper_output / "paper.docx"
    pdf_path = paper_output / "paper.pdf"
    txt_path = paper_output / "paper.txt"
    docx = inspect_docx(docx_path)
    pdf_exists = pdf_path.exists()
    pdf_size = pdf_path.stat().st_size if pdf_exists else 0
    pdf_fallback = bool(export_report.get("pdf_fallback"))
    pdf_readability = export_report.get("pdf_readability", "unknown")

    gates: list[dict[str, Any]] = []
    add_gate(
        gates,
        "paper_formats_present",
        PASS if paper_md.exists() and txt_path.exists() and docx_path.exists() and pdf_exists else FAIL,
        f"md={paper_md.exists()}; txt={txt_path.exists()}; docx={docx_path.exists()}; pdf={pdf_exists}; pdf_size={pdf_size}",
        str(paper_output),
    )

    add_gate(
        gates,
        "docx_readable",
        PASS if docx["readable"] else FAIL,
        f"readable={docx['readable']}; error={docx['error']}",
        str(docx_path),
    )

    image_status = PASS
    if image_refs and docx["embedded_image_count"] < len(image_refs):
        image_status = FAIL
    add_gate(
        gates,
        "docx_embedded_images",
        image_status,
        f"markdown_image_refs={len(image_refs)}; embedded_image_count={docx['embedded_image_count']}",
        image_refs,
    )

    formula_status = PASS
    block_formula_count = formula_counts["block_formula_count"]
    if block_formula_count and docx["formula_object_count"] == 0:
        formula_status = FAIL
    elif block_formula_count and docx["formula_object_count"] < block_formula_count:
        formula_status = WARN
    if docx["latex_fallback_count"] > 0 and formal:
        formula_status = FAIL if formula_status != FAIL else FAIL
    add_gate(
        gates,
        "docx_formula_objects",
        formula_status,
        f"markdown_block_formulas={block_formula_count}; formula_object_count={docx['formula_object_count']}; latex_fallback_count={docx['latex_fallback_count']}",
        str(docx_path),
    )

    table_status = PASS
    if table_count and docx["table_object_count"] < table_count:
        table_status = WARN if not formal else FAIL
    add_gate(
        gates,
        "docx_table_objects",
        table_status,
        f"markdown_tables={table_count}; docx_table_objects={docx['table_object_count']}",
        str(docx_path),
    )

    pdf_status = PASS
    pdf_detail = f"exists={pdf_exists}; size={pdf_size}; pdf_fallback={pdf_fallback}; pdf_readability={pdf_readability}"
    if not pdf_exists or pdf_size < 1024:
        pdf_status = FAIL
    elif pdf_fallback or pdf_readability in {"placeholder", "failed_or_placeholder"}:
        pdf_status = WARN
    add_gate(gates, "pdf_readability", pdf_status, pdf_detail, str(pdf_path))

    status_counts = {PASS: 0, WARN: 0, FAIL: 0}
    for gate in gates:
        status_counts[gate["status"]] += 1
    blocking = formal and status_counts[FAIL] > 0
    quality_ceiling = "fail" if blocking else ("provisional_pass" if status_counts[WARN] else "pass")
    report = {
        "workdir": str(workdir),
        "paper_output": str(paper_output),
        "run_mode": run_mode,
        "blocking": blocking,
        "quality_ceiling": quality_ceiling,
        "status_counts": status_counts,
        "metrics": {
            "markdown_image_refs": len(image_refs),
            "markdown_block_formulas": block_formula_count,
            "markdown_tables": table_count,
            "docx_formula_objects_count": docx["formula_object_count"],
            "docx_latex_fallback_count": docx["latex_fallback_count"],
            "embedded_image_count": docx["embedded_image_count"],
            "docx_table_count": docx["table_object_count"],
            "pdf_fallback": pdf_fallback,
            "pdf_readability": pdf_readability,
        },
        "gates": gates,
    }

    output_json = Path(args.output_json).resolve() if args.output_json else workdir / "export_audit.json"
    output_md = Path(args.output_md).resolve() if args.output_md else workdir / "export_audit.md"
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 导出对象审查报告",
        "",
        f"- run_mode: `{run_mode}`",
        f"- blocking: `{str(blocking).lower()}`",
        f"- pass/warn/fail: `{status_counts[PASS]}/{status_counts[WARN]}/{status_counts[FAIL]}`",
        f"- quality_ceiling: `{quality_ceiling}`",
        "",
        "| 检查项 | 状态 | 详情 |",
        "|---|---|---|",
    ]
    label = {PASS: "通过", WARN: "警告", FAIL: "失败"}
    for gate in gates:
        detail = str(gate["detail"]).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {gate['item']} | {label[gate['status']]} | {detail} |")
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 2 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
