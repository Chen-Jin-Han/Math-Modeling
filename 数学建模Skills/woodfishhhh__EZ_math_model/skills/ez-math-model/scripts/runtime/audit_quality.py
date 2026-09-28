#!/usr/bin/env python3
"""Deterministic pre-export quality gate for EZ Math Model papers."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
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


def list_files(path: Path, suffixes: tuple[str, ...] | None = None) -> list[Path]:
    if not path.exists():
        return []
    files = [p for p in path.rglob("*") if p.is_file()]
    if suffixes:
        files = [p for p in files if p.suffix.lower() in suffixes]
    return sorted(files)


def add_gate(gates: list[dict[str, Any]], gate: str, item: str, status: str, detail: str, evidence: Any = None) -> None:
    gates.append(
        {
            "gate": gate,
            "item": item,
            "status": status,
            "detail": detail,
            "evidence": evidence,
        }
    )


def parse_chart_manifest(path: Path) -> list[dict[str, Any]]:
    raw = read_json(path, [])
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        for key in ("charts", "figures", "items"):
            if isinstance(raw.get(key), list):
                return [x for x in raw[key] if isinstance(x, dict)]
        if "figure" in raw:
            return [raw]
    return []


def markdown_image_refs(text: str) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for match in re.finditer(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", text):
        refs.append({"alt": match.group(1).strip(), "path": match.group(2).strip(), "line": str(text[: match.start()].count("\n") + 1)})
    return refs


def markdown_tables(lines: list[str]) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    i = 0
    separator_re = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
    while i < len(lines) - 1:
        if "|" in lines[i] and separator_re.match(lines[i + 1] or ""):
            start = i
            block = [lines[i], lines[i + 1]]
            i += 2
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                block.append(lines[i])
                i += 1
            tables.append({"start_line": start + 1, "lines": block})
        else:
            i += 1
    return tables


def split_cells(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def count_sentences(text: str) -> int:
    return len(re.findall(r"[。！？.!?]", text))


def count_markdown_formula_blocks(text: str) -> int:
    return len(re.findall(r"(?ms)^\s*\$\$\s*\n.*?\n\s*\$\$\s*$", text))


def has_balanced_math(text: str) -> bool:
    dollars = re.findall(r"(?<!\\)\$", text)
    return len(dollars) % 2 == 0


def scan_synthetic(paths: list[Path]) -> list[str]:
    hits: list[str] = []
    for path in paths:
        text = read_text(path)
        if re.search(r"synthetic\s*[:=]\s*(true|1)", text, re.I):
            hits.append(str(path))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    args = parser.parse_args()

    workdir = Path(args.workdir).resolve()
    run_state = read_json(workdir / "run_state.json", {})
    intake = read_json(workdir / "intake.json", {})
    paper_path = workdir / "paper.md"
    paper = read_text(paper_path)
    paper_lines = paper.splitlines()
    run_mode = str(run_state.get("run_mode", "unknown"))
    formal = run_mode == "formal"
    gates: list[dict[str, Any]] = []

    setup_status = str(run_state.get("setup_status", "unknown"))
    add_gate(
        gates,
        "content_gate",
        "setup_status",
        PASS if setup_status == "user_confirmed" else WARN,
        f"setup_status={setup_status}; non-confirmed setup caps final quality at provisional_pass.",
        "run_state.json",
    )

    missing_inputs = run_state.get("missing_inputs", [])
    run_ok = run_mode in {"formal", "demo", "blocked"} and not (formal and missing_inputs)
    add_gate(
        gates,
        "content_gate",
        "run_mode",
        PASS if run_ok else FAIL,
        f"run_mode={run_mode}; missing_inputs={missing_inputs}",
        "run_state.json",
    )

    ques_count = int(intake.get("ques_count") or 0)
    short_questions = []
    for i in range(1, ques_count + 1):
        q = str(intake.get(f"ques{i}", ""))
        if len(q.strip()) < 30:
            short_questions.append(f"ques{i}")
    add_gate(
        gates,
        "content_gate",
        "problem_intake",
        PASS if ques_count > 0 and not short_questions else FAIL,
        f"ques_count={ques_count}; short_questions={short_questions}",
        "intake.json",
    )

    modeling_plan = read_text(workdir / "modeling_plan.md")
    missing_sections = []
    for i in range(1, ques_count + 1):
        if not re.search(rf"(问题\s*{i}|第\s*{i}\s*问|ques\s*{i}|q\s*{i})", modeling_plan, re.I):
            missing_sections.append(f"q{i}")
    add_gate(
        gates,
        "content_gate",
        "modeling_plan_sections",
        PASS if ques_count > 0 and not missing_sections else FAIL,
        f"missing_sections={missing_sections}",
        "modeling_plan.md",
    )

    execution_log = read_text(workdir / "execution_log.md")
    task_rows = re.findall(r"^\|\s*([^|\n]+?)\s*\|\s*([^|\n]+?)\s*\|", execution_log, re.M)
    statuses = [status.strip().lower() for _, status in task_rows if status.strip().lower() not in {"状态", "---"}]
    ok_count = sum(1 for status in statuses if status == "ok")
    ratio = ok_count / len(statuses) if statuses else 0
    add_gate(
        gates,
        "content_gate",
        "code_execution",
        PASS if ratio >= 0.5 else FAIL,
        f"ok={ok_count}; total={len(statuses)}; ok_ratio={ratio:.2f}",
        "execution_log.md",
    )

    result_files = list_files(workdir / "results", (".csv", ".json"))
    synthetic_hits = scan_synthetic(result_files)
    result_status = PASS if result_files and not (formal and synthetic_hits) else FAIL
    add_gate(
        gates,
        "content_gate",
        "result_files",
        result_status,
        f"result_files={len(result_files)}; synthetic_hits={synthetic_hits}",
        [str(p.relative_to(workdir)) for p in result_files[:20]],
    )

    manifest_path = workdir / "figures" / "chart_manifest.json"
    charts = parse_chart_manifest(manifest_path)
    chart_by_name: dict[str, dict[str, Any]] = {}
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for item in charts:
        name = str(item.get("figure", "")).replace("\\", "/").split("/")[-1]
        if name:
            chart_by_name[name] = item
        status = str(item.get("status", "")).lower()
        usable = bool(item.get("usable_in_paper", False))
        if usable or status == "accepted":
            accepted.append(item)
        if status in {"rejected", "skipped"} or usable is False:
            rejected.append(item)

    pngs = list_files(workdir / "figures", (".png", ".jpg", ".jpeg"))
    unregistered_pngs = [p.name for p in pngs if p.name not in chart_by_name]
    missing_accepted_files = []
    semantic_missing = []
    bad_semantics = []
    required_fields = {"chart_type", "x_label", "y_label", "unit", "caption_intent", "source_hash"}
    for item in accepted:
        fig = str(item.get("figure", ""))
        fig_name = fig.replace("\\", "/").split("/")[-1]
        if fig_name and not (workdir / "figures" / fig_name).exists():
            missing_accepted_files.append(fig_name)
        missing_fields = sorted(field for field in required_fields if not str(item.get(field, "")).strip())
        if missing_fields:
            semantic_missing.append({fig_name: missing_fields})
        if item.get("all_zero") or item.get("all_equal") or (formal and item.get("synthetic")):
            bad_semantics.append(fig_name)
    chart_status = PASS
    if unregistered_pngs or missing_accepted_files or bad_semantics or (formal and semantic_missing):
        chart_status = FAIL
    elif semantic_missing:
        chart_status = WARN
    add_gate(
        gates,
        "chart_gate",
        "chart_manifest",
        chart_status,
        f"charts={len(charts)}; accepted={len(accepted)}; rejected_or_skipped={len(rejected)}; unregistered_pngs={unregistered_pngs}; missing_accepted_files={missing_accepted_files}; semantic_missing={semantic_missing}; bad_semantics={bad_semantics}",
        "figures/chart_manifest.json",
    )

    image_refs = markdown_image_refs(paper)
    bad_image_refs = []
    missing_referenced_files = []
    for ref in image_refs:
        raw_path = ref["path"].replace("\\", "/")
        name = raw_path.split("/")[-1]
        chart = chart_by_name.get(name)
        if not raw_path.startswith("figures/"):
            bad_image_refs.append({"line": ref["line"], "path": ref["path"], "reason": "path_must_start_with_figures/"})
        if not (workdir / raw_path).exists():
            missing_referenced_files.append({"line": ref["line"], "path": ref["path"]})
        if not chart or not (chart.get("usable_in_paper") or str(chart.get("status", "")).lower() == "accepted"):
            bad_image_refs.append({"line": ref["line"], "path": ref["path"], "reason": "not_accepted_in_manifest"})
    accepted_names = {str(item.get("figure", "")).replace("\\", "/").split("/")[-1] for item in accepted}
    referenced_names = {ref["path"].replace("\\", "/").split("/")[-1] for ref in image_refs}
    unreferenced_accepted = sorted(name for name in accepted_names if name and name not in referenced_names)
    add_gate(
        gates,
        "chart_gate",
        "paper_image_references",
        PASS if image_refs and not bad_image_refs and not missing_referenced_files and not unreferenced_accepted else FAIL,
        f"image_refs={len(image_refs)}; bad_refs={bad_image_refs}; missing_files={missing_referenced_files}; unreferenced_accepted={unreferenced_accepted}",
        [{"line": ref["line"], "path": ref["path"]} for ref in image_refs],
    )

    weak_explanations = []
    for ref in image_refs:
        line_index = int(ref["line"]) - 1
        start = max(0, line_index - 4)
        end = min(len(paper_lines), line_index + 5)
        context = "\n".join(line for i, line in enumerate(paper_lines[start:end], start) if i != line_index)
        if count_sentences(context) < 3 or not re.search(r"\d", context):
            weak_explanations.append({"line": ref["line"], "path": ref["path"], "sentences": count_sentences(context), "has_number": bool(re.search(r"\d", context))})
    add_gate(
        gates,
        "chart_gate",
        "figure_text_binding",
        PASS if not weak_explanations else FAIL,
        f"weak_explanations={weak_explanations}",
        "paper.md",
    )

    zh_sections = ["摘要", "问题重述", "问题分析", "模型假设", "符号说明", "模型的建立与求解", "敏感性分析", "模型评价", "参考文献"]
    missing_paper_sections = [section for section in zh_sections if section not in paper]
    add_gate(
        gates,
        "content_gate",
        "paper_sections",
        PASS if not missing_paper_sections else FAIL,
        f"missing_sections={missing_paper_sections}",
        "paper.md",
    )

    brace_refs = re.findall(r"\{\[\^(\d+)\][^}]*\}", paper)
    duplicate_refs = sorted({ref for ref in brace_refs if brace_refs.count(ref) > 1})
    add_gate(
        gates,
        "content_gate",
        "references",
        PASS if len(set(brace_refs)) >= 3 and not duplicate_refs else WARN,
        f"unique_references={len(set(brace_refs))}; duplicate_reference_definitions={duplicate_refs}",
        "paper.md",
    )

    formula_blocks = count_markdown_formula_blocks(paper)
    formula_issues = []
    if not has_balanced_math(paper):
        formula_issues.append("unbalanced_dollar_delimiters")
    for match in re.finditer(r"(?ms)\$\$.*?\$\$", paper):
        before = paper[max(0, match.start() - 2) : match.start()]
        after = paper[match.end() : match.end() + 2]
        if "\n" not in before or "\n" not in after:
            formula_issues.append(f"block_formula_not_standalone_at_line_{paper[: match.start()].count(chr(10)) + 1}")
        after_lines = paper[match.end() :].splitlines()[0:6]
        if not re.search(r"(其中|参数|来源|表示|where|parameter|source|denote)", "\n".join(after_lines), re.I):
            formula_issues.append(f"missing_parameter_explanation_after_line_{paper[: match.start()].count(chr(10)) + 1}")
    add_gate(
        gates,
        "formula_gate",
        "formula_syntax_and_explanation",
        PASS if not formula_issues else FAIL,
        f"formula_blocks={formula_blocks}; issues={formula_issues}",
        "paper.md",
    )

    table_issues = []
    tables = markdown_tables(paper_lines)
    for table in tables:
        cells = split_cells(table["lines"][0])
        data_rows = table["lines"][2:]
        if len(data_rows) < 2:
            table_issues.append({"line": table["start_line"], "reason": "less_than_two_data_rows"})
        if len(cells) != len(set(cells)):
            table_issues.append({"line": table["start_line"], "reason": "duplicate_headers"})
        if any(not cell for cell in cells):
            table_issues.append({"line": table["start_line"], "reason": "empty_header"})
        if not any(("单位" in cell or "(" in cell or "（" in cell or "unit" in cell.lower()) for cell in cells):
            table_issues.append({"line": table["start_line"], "reason": "missing_unit_or_unit_column"})
    add_gate(
        gates,
        "table_gate",
        "markdown_tables",
        PASS if not table_issues else FAIL,
        f"tables={len(tables)}; issues={table_issues}",
        "paper.md",
    )

    residue_patterns = [r"\{(?!\[\^)[^}\n]+\}", "写作指引", "Interpretation 1", "Same structure"]
    residue_hits = []
    for pattern in residue_patterns:
        if re.search(pattern, paper):
            residue_hits.append(pattern)
    engineering_patterns = ["summary.json", "execution_log", "run_state.json", "artifact_manifest", "runtime/", "output/"]
    engineering_hits = [pattern for pattern in engineering_patterns if pattern in paper]
    add_gate(
        gates,
        "content_gate",
        "template_residue_and_engineering_leakage",
        PASS if not residue_hits and not engineering_hits else FAIL,
        f"template_residue={residue_hits}; engineering_hits={engineering_hits}",
        "paper.md",
    )

    status_counts = {PASS: 0, WARN: 0, FAIL: 0}
    for gate in gates:
        status_counts[gate["status"]] += 1
    blocking = formal and status_counts[FAIL] > 0
    report = {
        "workdir": str(workdir),
        "run_mode": run_mode,
        "blocking": blocking,
        "status_counts": status_counts,
        "quality_ceiling": "fail" if blocking else ("provisional_pass" if status_counts[WARN] else "pass"),
        "gates": gates,
    }

    output_json = Path(args.output_json).resolve() if args.output_json else workdir / "quality_report.json"
    output_md = Path(args.output_md).resolve() if args.output_md else workdir / "quality_report.md"
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 质量审查报告",
        "",
        f"- run_mode: `{run_mode}`",
        f"- blocking: `{str(blocking).lower()}`",
        f"- pass/warn/fail: `{status_counts[PASS]}/{status_counts[WARN]}/{status_counts[FAIL]}`",
        f"- quality_ceiling: `{report['quality_ceiling']}`",
        "",
        "| gate | 检查项 | 状态 | 详情 |",
        "|---|---|---|---|",
    ]
    label = {PASS: "通过", WARN: "警告", FAIL: "失败"}
    for gate in gates:
        detail = str(gate["detail"]).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {gate['gate']} | {gate['item']} | {label[gate['status']]} | {detail} |")
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 2 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
