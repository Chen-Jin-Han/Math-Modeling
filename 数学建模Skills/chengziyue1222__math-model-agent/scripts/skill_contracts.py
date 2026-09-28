#!/usr/bin/env python3
"""Validate profile-aware input/output contracts for the eight standard Skills."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "1.4"
PROFILES = ("rapid", "competition", "audit")

COMMON_CONTRACTS: dict[str, dict[str, tuple[Any, ...]]] = {
    "run-modeling-project": {
        "inputs": ("project_config", "skill_trace"),
        "outputs": ("project_state", "stage_gate", "handoff"),
    },
    "select-model": {
        "inputs": ("official_problem", "data_dictionary", "constraint_summary", "project_goal"),
        "outputs": (
            "problem_decomposition", "candidate_models", "baseline_plan", "selected_model_plan",
            "decision_contract", "risk_register", "model_selection_report",
        ),
    },
    "analyze-model-data": {
        "inputs": ("raw_data", "data_dictionary", "official_problem"),
        "outputs": (
            "data_profile", "data_quality_report", "cleaning_actions", "eda_findings",
            "leakage_report", "processed_data_manifest", "data_analysis",
        ),
    },
    "research-model-literature": {
        "inputs": ("model_problem", "selected_model", "citation_requirements", "source_candidates"),
        "outputs": (
            "search_queries", "search_results", "selected_sources", "rejected_sources", "retrieval_log",
            "metadata_verification", "relevance_evidence", "literature_evidence", "references_bib", "bib_validation",
        ),
    },
    "solve-model": {
        "inputs": ("selected_model_plan", "decision_contract", "data_analysis", "model_config", "baseline_plan"),
        "outputs": ("model_specification", "result_object", "solver_validation", "quality_validation"),
    },
    "make-model-figures": {
        "inputs": ("result_object", "quality_validation", "claim_registry", "figure_plan"),
        "outputs": ("figure_registry", "figure_audit_report"),
    },
    "write-model-paper": {
        "inputs": (
            "paper_spec", "evidence_index", "decision_contract", "quality_validation",
            "figure_registry", "table_registry", "references_bib", "result_object",
        ),
        "outputs": (
            "main_markdown", "main_tex", "paper_generation_report", "claim_usage_report",
            "cumcm_layout_validation", "render_request",
        ),
    },
    "review-model-paper": {
        "inputs": (
            "manuscript", "official_problem", "decision_contract", "quality_validation", "result_object",
            "project_manifest", "cumcm_layout_validation", "visual_layout_audit", "support_archive",
            "support_manifest", "reproduction_report", "submission_preflight",
        ),
        "one_of_inputs": (("main_pdf", "main_docx"),),
        "outputs": ("paper_review_report", "submission_readiness"),
    },
}


def _audit_contracts() -> dict[str, dict[str, tuple[Any, ...]]]:
    contracts = {
        skill: {direction: tuple(roles) for direction, roles in contract.items()}
        for skill, contract in COMMON_CONTRACTS.items()
    }
    contracts["write-model-paper"]["inputs"] += ("claim_registry", "formula_registry")
    contracts["review-model-paper"] = {
        "inputs": (
            "manuscript", "main_pdf", "main_docx", "official_problem", "decision_contract",
            "quality_validation", "result_object", "claim_registry", "figure_registry", "table_registry",
            "references_bib", "project_manifest", "cumcm_layout_validation", "latex_compile_report",
            "docx_render_report", "visual_layout_audit", "support_archive", "support_manifest",
            "reproduction_report", "submission_preflight",
        ),
        "outputs": (
            "paper_review_report", "independent_content_review", "review_hash_binding", "submission_readiness",
        ),
    }
    return contracts


PROFILE_CONTRACTS = {
    "rapid": {skill: {"inputs": (), "outputs": ()} for skill in COMMON_CONTRACTS},
    "competition": COMMON_CONTRACTS,
    "audit": _audit_contracts(),
}
CONTRACTS = PROFILE_CONTRACTS["competition"]

LEGACY_CONTRACTS_1_3 = {
    **COMMON_CONTRACTS,
    "write-model-paper": {
        "inputs": (
            "paper_spec", "evidence_index", "decision_contract", "quality_validation", "claim_registry",
            "formula_registry", "figure_registry", "table_registry", "references_bib", "result_object",
        ),
        "outputs": (
            "main_markdown", "main_tex", "paper_generation_report", "claim_usage_report",
            "cumcm_layout_validation", "render_request",
        ),
    },
    "review-model-paper": {
        "inputs": (
            "manuscript", "main_pdf", "main_docx", "official_problem", "decision_contract",
            "quality_validation", "result_object", "claim_registry", "figure_registry", "table_registry",
            "references_bib", "project_manifest", "cumcm_layout_validation", "latex_compile_report",
            "docx_render_report", "visual_layout_audit",
        ),
        "outputs": (
            "paper_review_report", "independent_content_review", "review_hash_binding", "submission_readiness",
        ),
    },
}
LEGACY_CONTRACTS_1_2 = {
    **LEGACY_CONTRACTS_1_3,
    "research-model-literature": {
        "inputs": ("model_problem", "selected_model", "citation_requirements", "source_candidates"),
        "outputs": (
            "search_queries", "search_results", "selected_sources", "rejected_sources",
            "literature_evidence", "references_bib", "bib_validation",
        ),
    },
    "write-model-paper": {
        "inputs": LEGACY_CONTRACTS_1_3["write-model-paper"]["inputs"],
        "outputs": ("main_markdown", "main_tex", "paper_generation_report", "claim_usage_report"),
    },
    "review-model-paper": {
        "inputs": (
            "manuscript", "official_problem", "decision_contract", "quality_validation", "result_object",
            "claim_registry", "figure_registry", "table_registry", "references_bib", "project_manifest",
        ),
        "outputs": ("paper_review_report",),
    },
}
LEGACY_CONTRACTS_1_1 = {
    **LEGACY_CONTRACTS_1_2,
    "research-model-literature": {
        "inputs": ("model_problem", "selected_model", "citation_requirements"),
        "outputs": LEGACY_CONTRACTS_1_2["research-model-literature"]["outputs"],
    },
}


def contract_for(
    skill: str,
    *,
    version: str = CONTRACT_VERSION,
    profile: str = "competition",
) -> dict[str, tuple[Any, ...]]:
    if version == "1.1":
        contracts = LEGACY_CONTRACTS_1_1
    elif version == "1.2":
        contracts = LEGACY_CONTRACTS_1_2
    elif version == "1.3":
        contracts = LEGACY_CONTRACTS_1_3
    else:
        if profile not in PROFILE_CONTRACTS:
            raise ValueError(f"unknown workflow profile: {profile}")
        contracts = PROFILE_CONTRACTS[profile]
    try:
        return contracts[skill]
    except KeyError as exc:
        raise ValueError(f"unknown standard skill: {skill}") from exc


def _roles(records: Any) -> set[str]:
    return {str(item.get("role")) for item in records if isinstance(item, dict) and item.get("role")}


def validate_records(
    skill: str,
    inputs: Any,
    outputs: Any,
    *,
    contract_version: str = CONTRACT_VERSION,
    profile: str = "competition",
) -> list[str]:
    contract = contract_for(skill, version=contract_version, profile=profile)
    supplied_inputs, supplied_outputs = _roles(inputs), _roles(outputs)
    errors: list[str] = []
    for direction, required, supplied in (
        ("input", contract.get("inputs", ()), supplied_inputs),
        ("output", contract.get("outputs", ()), supplied_outputs),
    ):
        missing = sorted(set(required) - supplied)
        if missing:
            errors.append(f"{skill} missing {direction} roles: {', '.join(missing)}")
    for alternatives in contract.get("one_of_inputs", ()):
        if not supplied_inputs.intersection(alternatives):
            errors.append(f"{skill} requires one input role from: {', '.join(alternatives)}")
    return errors


def validate_terminal_run(run: dict[str, Any]) -> list[str]:
    if run.get("status") != "PASS":
        return [f"run {run.get('run_id')} is not a successful terminal run"]
    return validate_records(
        str(run.get("skill", "")),
        run.get("inputs", []),
        run.get("outputs", []),
        contract_version=str(run.get("contract_version", "1.1")),
        profile=str(run.get("profile", "competition")),
    )


def export_contracts(profile: str = "competition") -> dict[str, Any]:
    return {"contract_version": CONTRACT_VERSION, "profile": profile, "skills": PROFILE_CONTRACTS[profile]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path)
    parser.add_argument("--skill", choices=sorted(CONTRACTS))
    parser.add_argument("--profile", choices=PROFILES, default="competition")
    parser.add_argument("--run", type=Path)
    args = parser.parse_args(argv)
    if args.export:
        args.export.parent.mkdir(parents=True, exist_ok=True)
        args.export.write_text(json.dumps(export_contracts(args.profile), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.run:
        run = json.loads(args.run.read_text(encoding="utf-8"))
        errors = validate_terminal_run(run)
    elif args.skill:
        print(json.dumps({"skill": args.skill, "profile": args.profile, **contract_for(args.skill, profile=args.profile)}, ensure_ascii=False, indent=2))
        return 0
    else:
        print(json.dumps(export_contracts(args.profile), ensure_ascii=False, indent=2))
        return 0
    if errors:
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print("skill contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
