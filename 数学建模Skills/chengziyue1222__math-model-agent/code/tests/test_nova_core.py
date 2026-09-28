"""Integration tests for the deterministic Nova Core campus-load MVP."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from nova_core.diagnosis import validate_evidence_trace
from nova_core.enums import ExperimentType, GateDecisionValue
from nova_core.rule_inventory import build_rule_inventory
from nova_core.service import CampusLoadDiagnosisService, CampusLoadInput
from scripts.run_manifest import validate_manifest


def _series(seed: int = 7) -> tuple[list[float], list[float]]:
    generator = np.random.default_rng(seed)
    hours = np.arange(72)
    actual = 65 + 17 * np.sin(hours * 2 * np.pi / 24) + generator.normal(0, 0.7, 72)
    predicted = actual + generator.normal(0, 1.0, 72)
    return actual.tolist(), predicted.tolist()


def _run(tmp_path: Path, **kwargs: object):
    actual, predicted = _series()
    request = CampusLoadInput(actual, predicted, **kwargs)
    return CampusLoadDiagnosisService().diagnose(request, output_root=tmp_path)


def test_case_leakage_selects_time_split_and_blocks(tmp_path: Path) -> None:
    run = _run(tmp_path, split_strategy="random")
    assert run.experiments_executed[0].experiment_type == ExperimentType.TIME_SPLIT_AUDIT
    assert run.gate_decisions[-1].decision == GateDecisionValue.BLOCKED
    assert run.stop_reason == "GATE_ALREADY_DECIDABLE"


def test_case_feature_leakage_selects_challenge_and_blocks(tmp_path: Path) -> None:
    run = _run(tmp_path, feature_origin_offsets=[0, 1])
    assert run.experiments_executed[0].experiment_type == ExperimentType.LEAKAGE_CHALLENGE
    assert run.gate_decisions[-1].decision == GateDecisionValue.BLOCKED


def test_case_peak_failure_selects_high_load_and_blocks(tmp_path: Path) -> None:
    actual, predicted = _series()
    values = np.asarray(actual)
    predicted = np.asarray(predicted)
    predicted[values >= np.quantile(values, 0.8)] -= 16
    request = CampusLoadInput(actual, predicted.tolist(), high_load_watch=True)
    run = CampusLoadDiagnosisService().diagnose(request, output_root=tmp_path)
    assert run.experiments_executed[0].experiment_type == ExperimentType.HIGH_LOAD_SUBSET_EVALUATION
    assert run.gate_decisions[-1].decision == GateDecisionValue.BLOCKED


def test_case_clean_runs_real_experiments_and_is_not_blocked(tmp_path: Path) -> None:
    run = _run(tmp_path)
    assert run.gate_decisions[-1].decision == GateDecisionValue.READY_FOR_REVIEW
    assert run.experiments_executed[0].experiment_type == ExperimentType.BASELINE_COMPARISON
    assert all(result.status.value == "SUCCEEDED" for result in run.tool_results)
    assert validate_manifest(run.manifest, next(tmp_path.iterdir()).parent, verify_files=True) == []


def test_evidence_trace_detects_tampered_tool_result(tmp_path: Path) -> None:
    run = _run(tmp_path)
    evidence, result = run.evidence[0], run.tool_results[0]
    assert validate_evidence_trace(evidence, result) == []
    result.metrics["mae_improvement"] += 100
    assert "ToolResult output hash mismatch" in validate_evidence_trace(evidence, result)


def test_gate_is_traceable_and_run_json_is_saved(tmp_path: Path) -> None:
    run = _run(tmp_path, split_strategy="random")
    gate = run.gate_decisions[-1]
    assert gate.claim_id == run.claims[0].claim_id
    assert gate.blocking_evidence_ids == [run.evidence[0].evidence_id]
    assert "VAL-GATE-012" in gate.triggered_rules
    saved = next(tmp_path.rglob("diagnosis_run.json"))
    payload = json.loads(saved.read_text(encoding="utf-8"))
    assert payload["tool_results"][0]["output_hash"] == run.tool_results[0].output_hash


def test_rule_inventory_resolves_152_vs_139() -> None:
    root = Path(__file__).resolve().parents[2]
    inventory = build_rule_inventory(root / "docs/reverse_engineering/skill_rule_pack_v1", root / "config/rule_implementation_registry.yaml")
    assert inventory["manifest_declared_total"] == 152
    assert inventory["yaml_rule_count"] == 139
    assert inventory["markdown_rule_count"] == 13
    assert inventory["parsed_total"] == 152
