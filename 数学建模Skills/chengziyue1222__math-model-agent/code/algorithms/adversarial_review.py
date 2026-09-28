"""Problem-agnostic semantic gates for adversarial modeling-paper review."""
from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def _registrations(value: Any, key: str) -> list[dict[str, Any]]:
    rows = value.get(key, []) if isinstance(value, dict) else value if isinstance(value, list) else []
    return [row for row in rows if isinstance(row, dict)]


def _first_named_json(root: Path, filename: str) -> Any:
    candidates = sorted(root.rglob(filename))
    return _load_json(candidates[0]) if candidates else None


def _question_rows(contract: Any) -> list[dict[str, Any]]:
    if not isinstance(contract, dict):
        return []
    for key in ("questions", "subproblems", "decisions"):
        rows = contract.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def _present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _independent_review_passed(root: Path, paper: Path) -> bool:
    """Accept a separately-produced, hash-bound second-pass review only."""
    candidate = root / "reports" / "independent_review.json"
    review = _load_json(candidate)
    if not isinstance(review, dict) or review.get("status") != "PASS":
        return False
    if review.get("reviewed_path") != str(paper.relative_to(root)).replace("\\", "/"):
        return False
    if review.get("manuscript_sha256") != hashlib.sha256(paper.read_bytes()).hexdigest():
        return False
    if not str(review.get("reviewer", "")).startswith("deterministic_second_pass_content_review_"):
        return False
    for path_key, hash_key in (
        ("decision_contract_path", "decision_contract_sha256"),
        ("quality_validation_path", "quality_validation_sha256"),
    ):
        relative = review.get(path_key)
        if not isinstance(relative, str):
            return False
        artifact = root / relative
        if not artifact.is_file() or review.get(hash_key) != hashlib.sha256(artifact.read_bytes()).hexdigest():
            return False
    checks = review.get("checks")
    if not isinstance(checks, list):
        return False
    by_id = {check.get("id"): check for check in checks if isinstance(check, dict)}
    required = {
        "limitations_disclosed",
        "contract_artifacts_exist",
        "question_sections_present",
        "declared_quality_discussed",
        "quality_artifact_structured",
    }
    return required <= set(by_id) and all(by_id[check_id].get("passed") is True for check_id in required)


def _contains_any(value: Any, tokens: tuple[str, ...]) -> bool:
    serialized = json.dumps(value, ensure_ascii=False).lower() if value is not None else ""
    return any(token in serialized for token in tokens)


def _decision_contract_issues(root: Path) -> list[dict[str, str]]:
    """Check only declared requirements; avoid guessing a problem's intended model."""
    contract = _first_named_json(root, "decision_contract.json")
    if contract is None:
        return []
    quality = _first_named_json(root, "quality_validation.json")
    specification = _first_named_json(root, "model_specification.json")
    issues: list[dict[str, str]] = []
    for index, question in enumerate(_question_rows(contract), start=1):
        label = str(question.get("id") or question.get("question_id") or f"question-{index}")
        requirements = question.get("quality_requirements", question)
        if not isinstance(requirements, dict):
            requirements = question
        if not _present(question.get("result_artifact")):
            issues.append({"gate": "evidence", "code": "question_output_evidence_missing", "severity": "blocking", "message": f"{label} has no registered executable result artifact in the decision contract"})
        if not _present(question.get("validation_artifact")):
            issues.append({"gate": "validation", "code": "question_validation_evidence_missing", "severity": "blocking", "message": f"{label} has no registered validation artifact in the decision contract"})
        if requirements.get("requires_dynamic_state") and not _contains_any(specification, ("state_variable", "state transition", "state_transition", "inventory_balance", "balance_constraint")):
            issues.append({"gate": "mathematics", "code": "multi_period_state_missing", "severity": "blocking", "message": f"{label} declares a multi-period state requirement but the model specification lacks a registered state/balance formulation"})
        if requirements.get("requires_uncertainty"):
            uncertainty = quality.get("uncertainty") if isinstance(quality, dict) else None
            valid_mode = isinstance(uncertainty, dict) and str(uncertainty.get("mode", "")).lower() not in {"", "deterministic", "none"}
            has_provenance = isinstance(uncertainty, dict) and _present(uncertainty.get("scenario_source"))
            has_validation = isinstance(uncertainty, dict) and _present(uncertainty.get("holdout_or_stress_evidence"))
            if not (valid_mode and has_provenance and has_validation):
                issues.append({"gate": "validation", "code": "uncertainty_evidence_missing", "severity": "blocking", "message": f"{label} declares uncertainty but quality validation lacks mode, scenario provenance, or holdout/stress evidence"})
        if requirements.get("requires_tradeoff"):
            tradeoff = quality.get("multiobjective") if isinstance(quality, dict) else None
            strategy = str(tradeoff.get("strategy", "")).lower() if isinstance(tradeoff, dict) else ""
            evidence = tradeoff.get("tradeoff_evidence") if isinstance(tradeoff, dict) else None
            if strategy not in {"pareto", "epsilon_constraint", "lexicographic", "weighted_sum_with_sensitivity"} or not _present(evidence):
                issues.append({"gate": "validation", "code": "tradeoff_evidence_missing", "severity": "blocking", "message": f"{label} declares competing objectives but lacks an explicit trade-off strategy and evidence"})
        if requirements.get("requires_baseline"):
            baseline = quality.get("baseline_comparison") if isinstance(quality, dict) else None
            valid = isinstance(baseline, dict) and baseline.get("shared_inputs") is True and _present(baseline.get("metrics"))
            if not valid:
                issues.append({"gate": "validation", "code": "baseline_comparison_missing", "severity": "blocking", "message": f"{label} declares a baseline requirement but quality validation lacks same-input comparison metrics"})
    return issues


def semantic_issues(project_root: str | Path, paper_path: str | Path) -> list[dict[str, str]]:
    """Return blocking and warning semantic findings without relying on a problem ID."""
    root, paper = Path(project_root), Path(paper_path)
    text = paper.read_text(encoding="utf-8") if paper.is_file() else ""
    issues: list[dict[str, str]] = []
    issues.extend(_decision_contract_issues(root))
    spec = (paper.parent / "paper-spec.yaml").read_text(encoding="utf-8") if (paper.parent / "paper-spec.yaml").is_file() else ""
    required_count = re.search(r"required_supplier_count\s*:\s*(\d+)", spec)
    if required_count:
        required = int(required_count.group(1))
        identifiers = set(re.findall(r"\bS\d{3}\b", text, re.I))
        if len(identifiers) < required:
            issues.append({"gate": "evidence", "code": "required_list_incomplete", "severity": "blocking", "message": f"paper lists {len(identifiers)} of required {required} suppliers"})

    if re.search(r"(?:一体化\s*鲁棒|integrated\s+robust)", text, re.I):
        specs = list(root.rglob("model_specification.json"))
        payload = _load_json(specs[0]) if specs else None
        method = json.dumps(payload, ensure_ascii=False).lower() if payload is not None else ""
        if any(token in method for token in ("decomposition", "sequential", "stagewise", "分解", "分阶段")):
            issues.append({"gate": "mathematics", "code": "model_claim_code_mismatch", "severity": "blocking", "message": "paper claims integrated robust optimization but the registered specification declares decomposition"})

    result_files = list(root.rglob("result_object.json"))
    result = _load_json(result_files[0]) if result_files else None
    solution = result.get("solution", {}) if isinstance(result, dict) else {}
    supplier_count = solution.get("supplier_count") if isinstance(solution, dict) else None
    if isinstance(supplier_count, (int, float)) and supplier_count >= 150 and not re.search(r"(?:实施|管理复杂|implementation|management complexity)", text, re.I):
        issues.append({"gate": "validation", "code": "implementation_risk_undiscussed", "severity": "blocking", "message": f"recommendation uses {supplier_count} suppliers without an implementation-complexity discussion"})
    if re.search(r"(?:24\s*weeks?|24\s*周).{0,100}(?:identical|完全相同|unchanged)", text, re.I | re.S) and not re.search(r"(?:切换成本|contract cost|switching cost)", text, re.I):
        issues.append({"gate": "validation", "code": "static_plan_without_switching_cost", "severity": "warning", "message": "static multi-week plan omits switching or contract-cost discussion"})

    formulas = _registrations(_load_json(paper.parent / "formula-registry.json"), "formulas")
    for index, formula in enumerate(formulas):
        required = {"latex", "variables", "units", "code_function", "parameter_source", "result_id"}
        missing = sorted(name for name in required if not formula.get(name))
        if missing:
            issues.append({"gate": "mathematics", "code": "formula_registry_incomplete", "severity": "blocking", "message": f"formula registry item {index} is missing {', '.join(missing)}"})
    tables = _registrations(_load_json(paper.parent / "table-registry.json"), "tables")
    for index, table in enumerate(tables):
        required = {"data_file", "row_filter", "column_filter", "generation_script", "sha256", "claim_ids"}
        missing = sorted(name for name in required if not table.get(name))
        if missing:
            issues.append({"gate": "figures_tables", "code": "table_registry_incomplete", "severity": "blocking", "message": f"table registry item {index} is missing {', '.join(missing)}"})
    figures = _registrations(_load_json(paper.parent / "figure-registry.json"), "figures")
    for index, figure in enumerate(figures):
        required = {"path", "sha256", "data_file", "data_sha256", "metadata", "inserted_in_body"}
        missing = sorted(name for name in required if not figure.get(name))
        if missing:
            issues.append({"gate": "figures_tables", "code": "figure_registry_incomplete", "severity": "blocking", "message": f"figure registry item {index} is missing {', '.join(missing)}"})
            continue
        figure_path = root / str(figure["path"])
        if not figure_path.is_file() or hashlib.sha256(figure_path.read_bytes()).hexdigest() != figure["sha256"]:
            issues.append({"gate": "figures_tables", "code": "figure_hash_mismatch", "severity": "blocking", "message": f"figure registry item {index} has stale rendered output"})
        if figure.get("data_file") or figure.get("data_sha256"):
            data_path = root / str(figure.get("data_file", ""))
            if not data_path.is_file() or hashlib.sha256(data_path.read_bytes()).hexdigest() != figure.get("data_sha256"):
                issues.append({"gate": "figures_tables", "code": "figure_source_hash_mismatch", "severity": "blocking", "message": f"figure registry item {index} has stale source data"})
    contract = _first_named_json(root, "decision_contract.json")
    questions = max(len(_question_rows(contract)), len(re.findall(r"(?:问题[一二三四五六七八九十]|\bQ[1-9]\b)", text)))
    if questions >= 4 and not issues and not _independent_review_passed(root, paper):
        issues.append({"gate": "validation", "code": "REVIEW_SUSPICIOUSLY_SHALLOW", "severity": "blocking", "message": "complex paper produced no semantic findings; run an independent second review"})
    return issues
