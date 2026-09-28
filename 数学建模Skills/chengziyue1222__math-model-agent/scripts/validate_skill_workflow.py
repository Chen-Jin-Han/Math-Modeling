#!/usr/bin/env python3
"""Detect workflow bypasses and validate registered producer provenance."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.skill_runtime import ALLOWED_EXTERNAL_PRODUCERS, STANDARD_SKILLS, validate_skill_run
from scripts.validate_adapter_boundaries import validate_adapter_boundaries


OFFICIAL_PRODUCERS = {
    "data_audit": "analyze-model-data",
    "model_selection_report": "select-model",
    "result_object": "solve-model",
    "formal_figure": "make-model-figures",
    "main_markdown": "write-model-paper",
    "main_tex": "write-model-paper",
    "main_pdf": "compile-latex",
    "main_docx": "paper-docx",
    "latex_compile_report": "compile-latex",
    "docx_render_report": "paper-docx",
    "visual_layout_audit": "paper-render-audit",
    "independent_content_review": "review-model-paper",
    "review_hash_binding": "review-model-paper",
    "submission_readiness": "review-model-paper",
    "paper_review_report": "review-model-paper",
}
FORMAL_ARTIFACTS = {
    "paper/main.md": "main_markdown",
    "paper/main.tex": "main_tex",
    "paper/main.pdf": "main_pdf",
    "paper/main.docx": "main_docx",
    "reports/latex_compile_report.json": "latex_compile_report",
    "reports/docx_render_report.json": "docx_render_report",
    "reports/visual_layout_audit.json": "visual_layout_audit",
    "reports/independent_review.json": "independent_content_review",
    "reports/review_hash_binding.json": "review_hash_binding",
    "reports/submission_readiness.json": "submission_readiness",
}
SUSPICIOUS = (
    ("direct_main_tex_write", re.compile(r"(?:write_text|open)\([^\n]{0,160}main\.tex|main\.tex[^\n]{0,160}(?:write_text|open)", re.I)),
    ("direct_latex_compile", re.compile(r"(?:xelatex|pdflatex|pandoc)\b", re.I)),
    ("manual_skill_trace", re.compile(r"(?:skill-runs\.jsonl|skill_execution_trace\.md)", re.I)),
    ("embedded_long_paper", re.compile(r"(?:'''|\"\"\")[\s\S]{8000,}?(?:'''|\"\"\")")),
)
COMPILERS = {"xelatex", "pdflatex", "lualatex", "tectonic", "pandoc"}


def _constant_value(node: ast.AST, environment: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return environment.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _constant_value(node.left, environment), _constant_value(node.right, environment)
        if isinstance(left, str) and isinstance(right, str):
            return left + right
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left, right = _constant_value(node.left, environment), _constant_value(node.right, environment)
        if isinstance(left, str) and isinstance(right, str):
            return f"{left.rstrip('/')}/{right.lstrip('/')}"
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [_constant_value(item, environment) for item in node.elts]
        return values if all(value is not None for value in values) else None
    if isinstance(node, ast.JoinedStr):
        parts = [_constant_value(value, environment) for value in node.values]
        return "".join(str(value) for value in parts) if all(value is not None for value in parts) else None
    if isinstance(node, ast.FormattedValue):
        return _constant_value(node.value, environment)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in {"Path", "str"} and node.args:
            return _constant_value(node.args[0], environment)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "join" and node.args:
            separator = _constant_value(node.func.value, environment)
            values = _constant_value(node.args[0], environment)
            if isinstance(separator, str) and isinstance(values, list) and all(isinstance(item, str) for item in values):
                return separator.join(values)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "join":
            values = [_constant_value(arg, environment) for arg in node.args]
            if values and all(isinstance(item, str) for item in values):
                return "/".join(values)
    return None


def _ast_bypass_findings(path: Path, text: str) -> list[dict[str, str]]:
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return [{"code": "BYPASS_DETECTED", "rule": "python_ast_unparseable"}]
    environment: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value_node = node.value
            value = _constant_value(value_node, environment) if value_node is not None else None
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and value is not None:
                    environment[target.id] = value

    findings: list[dict[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) >= 8_000:
            findings.append({"code": "BYPASS_DETECTED", "rule": "embedded_long_content"})
        if not isinstance(node, ast.Call):
            continue
        function_name = ""
        if isinstance(node.func, ast.Name):
            function_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            function_name = node.func.attr
        if function_name in {"write_text", "write_bytes"} and isinstance(node.func, ast.Attribute):
            target = _constant_value(node.func.value, environment)
            if isinstance(target, str) and target.replace("\\", "/").lower().endswith(("main.tex", "main.md")):
                findings.append({"code": "BYPASS_DETECTED", "rule": "ast_direct_manuscript_write"})
        if function_name == "open" and node.args:
            target = _constant_value(node.args[0], environment)
            mode = _constant_value(node.args[1], environment) if len(node.args) > 1 else "r"
            if isinstance(target, str) and isinstance(mode, str) and any(flag in mode for flag in "wax"):
                if target.replace("\\", "/").lower().endswith(("main.tex", "main.md")):
                    findings.append({"code": "BYPASS_DETECTED", "rule": "ast_direct_manuscript_write"})
        if function_name in {"run", "Popen", "call", "check_call", "check_output"} and node.args:
            command = _constant_value(node.args[0], environment)
            serialized = " ".join(command) if isinstance(command, list) else str(command or "")
            if any(compiler in serialized.lower() for compiler in COMPILERS):
                findings.append({"code": "BYPASS_DETECTED", "rule": "ast_direct_document_tool"})
        if function_name in {"b64decode", "decodebytes"}:
            findings.append({"code": "BYPASS_DETECTED", "rule": "encoded_content_payload"})
    unique = {(item["code"], item["rule"]): item for item in findings}
    return list(unique.values())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scan_project_scripts(project_root: str | Path) -> list[dict[str, str]]:
    root = Path(project_root).resolve()
    findings = []
    ignored = {".git", ".venv", "venv", "__pycache__", "node_modules", "mutation_tests"}
    for path in root.rglob("*.py"):
        if any(part in ignored for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        for finding in _ast_bypass_findings(path, text):
            findings.append({**finding, "path": str(path.relative_to(root)).replace("\\", "/")})
        for code, pattern in SUSPICIOUS:
            if pattern.search(text):
                findings.append({"code": "BYPASS_DETECTED", "rule": code, "path": str(path.relative_to(root)).replace("\\", "/")})
    return findings


def validate_producers(project_root: str | Path, *, profile: str = "audit") -> list[str]:
    root = Path(project_root).resolve()
    if profile != "audit":
        return []
    registry_path = root / "manifests" / "artifact-producers.json"
    if not registry_path.is_file():
        errors = ["producer_registry_missing"]
        errors.extend(
            f"formal_artifact_unregistered: {relative}"
            for relative in FORMAL_ARTIFACTS
            if (root / relative).is_file()
        )
        return errors
    try:
        records = json.loads(registry_path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        return [f"producer_registry_invalid: {exc}"]
    if not isinstance(records, list):
        return ["producer_registry_invalid: root must be an array"]
    errors = []
    by_path = {
        str(record.get("path", "")).replace("\\", "/"): record
        for record in records
        if isinstance(record, dict)
    }
    for record in records:
        if not isinstance(record, dict):
            errors.append("producer_record_invalid")
            continue
        path = root / str(record.get("path", ""))
        role = str(record.get("role", ""))
        expected = OFFICIAL_PRODUCERS.get(role)
        actual = str(record.get("producer_name", ""))
        if expected and actual != expected:
            errors.append(f"producer_mismatch: {record.get('path')} expects {expected}, got {actual}")
        if not path.is_file() or record.get("output_sha256") != _sha256(path):
            errors.append(f"producer_output_hash_mismatch: {record.get('path')}")
        if actual not in STANDARD_SKILLS and actual not in ALLOWED_EXTERNAL_PRODUCERS:
            errors.append(f"producer_not_allowed: {actual}")
    for relative, role in FORMAL_ARTIFACTS.items():
        if not (root / relative).is_file():
            continue
        record = by_path.get(relative)
        if record is None:
            errors.append(f"formal_artifact_unregistered: {relative}")
        elif record.get("role") != role:
            errors.append(f"formal_artifact_role_mismatch: {relative} expects {role}")
    return errors


def validate_review_binding(project_root: str | Path) -> list[str]:
    """Invalidate a completed review when any hash-bound artifact has drifted."""
    root = Path(project_root).resolve()
    binding_path = root / "reports" / "review_hash_binding.json"
    if not binding_path.is_file():
        return []
    try:
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        return [f"review_binding_invalid: {exc}"]
    artifacts = binding.get("artifacts") if isinstance(binding, dict) else None
    if not isinstance(artifacts, dict):
        return ["review_binding_invalid: artifacts must be an object"]
    errors = []
    for role, record in artifacts.items():
        if not isinstance(record, dict):
            errors.append(f"review_binding_record_invalid: {role}")
            continue
        relative = str(record.get("path", ""))
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            errors.append(f"review_binding_path_escape: {role}")
            continue
        if not path.is_file() or record.get("sha256") != _sha256(path):
            errors.append(f"review_binding_hash_mismatch: {role}")
    return errors


def validate_workflow(
    project_root: str | Path,
    project_id: str,
    *,
    require_all_skills: bool = True,
    repository_root: str | Path | None = None,
    profile: str = "competition",
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    repo = Path(repository_root).resolve() if repository_root else Path(__file__).resolve().parents[1]
    required = list(STANDARD_SKILLS) if require_all_skills and profile == "audit" else []
    trace_errors = validate_skill_run(
        root,
        project_id=project_id,
        required_skills=required,
        profile=profile,
    )
    bypass = scan_project_scripts(root)
    producer_errors = validate_producers(root, profile=profile)
    review_binding_errors = validate_review_binding(root) if profile == "audit" else []
    adapter_findings = validate_adapter_boundaries(repo)
    return {
        "project_id": project_id,
        "profile": profile,
        "status": "PASS" if not trace_errors and not bypass and not producer_errors and not review_binding_errors and not adapter_findings else "FAIL",
        "trace_errors": trace_errors,
        "bypass_findings": bypass,
        "producer_errors": producer_errors,
        "review_binding_errors": review_binding_errors,
        "adapter_findings": adapter_findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--allow-partial-skills", action="store_true")
    parser.add_argument("--repository-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--profile", choices=("rapid", "competition", "audit"), default="competition")
    args = parser.parse_args(argv)
    result = validate_workflow(
        args.project_root,
        args.project_id,
        require_all_skills=not args.allow_partial_skills,
        repository_root=args.repository_root,
        profile=args.profile,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
