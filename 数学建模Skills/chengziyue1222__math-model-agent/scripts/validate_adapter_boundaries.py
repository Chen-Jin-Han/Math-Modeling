#!/usr/bin/env python3
"""Fail when topic adapters absorb orchestration, provenance, or final-delivery duties."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ADAPTER_RULES = {
    "skills/select-model/scripts/plan_problem.py": {
        "requires": ("validate_decision_contract",),
    },
    "skills/analyze-model-data/scripts/analyze_excel_inputs.py": {
        "requires": ("panel_diagnostics",),
    },
    "skills/solve-model/scripts/solve_supplier_chain.py": {
        "requires": ("validate_state_balance", "compare_policy_metrics", "service_level_metrics"),
    },
    "skills/make-model-figures/scripts/render_supplier_figures.py": {
        "requires": ("export_publication_figure",),
    },
    "skills/write-model-paper/scripts/write_supplier_competition_paper.py": {
        "requires": ("validate_layout",),
        "writer": True,
    },
    "skills/select-model/scripts/plan_chemical_process.py": {
        "requires": ("validate_decision_contract",),
    },
    "skills/solve-model/scripts/solve_process_forecast.py": {
        "requires": ("causal_features", "chronological_partitions", "future_event_targets", "bootstrap_interval"),
    },
    "skills/make-model-figures/scripts/render_process_figures.py": {
        "requires": ("export_publication_figure",),
    },
    "skills/write-model-paper/scripts/write_process_competition_paper.py": {
        "requires": ("validate_layout",),
        "writer": True,
    },
}
FORBIDDEN_COMMON = (
    "skill_runtime",
    "run_standard_skill",
    "project_state",
    "skill-runs.jsonl",
    "artifact-producers.json",
    "paper_review_report",
    "submission_readiness",
)
FINAL_RENDER_TOKENS = ("xelatex", "pdflatex", "lualatex", "tectonic")


def validate_adapter_boundaries(repository_root: str | Path) -> list[dict[str, Any]]:
    root = Path(repository_root).resolve()
    findings: list[dict[str, Any]] = []
    for relative, rule in ADAPTER_RULES.items():
        path = root / relative
        if not path.is_file():
            findings.append({"path": relative, "code": "ADAPTER_MISSING"})
            continue
        text = path.read_text(encoding="utf-8")
        lines = len(text.splitlines())
        if lines > 500:
            findings.append({"path": relative, "code": "ADAPTER_TOO_LARGE", "lines": lines, "limit": 500})
        lowered = text.lower()
        for token in FORBIDDEN_COMMON:
            if token.lower() in lowered:
                findings.append({"path": relative, "code": "ADAPTER_ORCHESTRATION_BYPASS", "token": token})
        for token in FINAL_RENDER_TOKENS:
            if token in lowered:
                findings.append({"path": relative, "code": "ADAPTER_FINAL_RENDER_BYPASS", "token": token})
        if not rule.get("writer"):
            if "main.pdf" in lowered or "main.docx" in lowered:
                findings.append({"path": relative, "code": "ADAPTER_FINAL_DELIVERY_REFERENCE"})
            if re.search(r"main\s*[+]\s*['\"]\.(?:md|tex)|main\.(?:md|tex)", text, re.I):
                findings.append({"path": relative, "code": "ADAPTER_MANUSCRIPT_WRITE"})
            if "pandoc" in lowered:
                findings.append({"path": relative, "code": "ADAPTER_DOCUMENT_CONVERSION"})
        for required in rule.get("requires", ()):
            if required not in text:
                findings.append({"path": relative, "code": "ADAPTER_GENERIC_DELEGATION_MISSING", "symbol": required})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    findings = validate_adapter_boundaries(args.repository_root)
    report = {"status": "PASS" if not findings else "FAIL", "findings": findings}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
