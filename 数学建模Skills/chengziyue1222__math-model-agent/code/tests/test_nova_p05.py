"""P0.5 semantic audit and multi-stage selection regression tests."""

from __future__ import annotations

import json
from pathlib import Path

from nova_core.enums import GateDecisionValue
from nova_eval.baselines import run_strategy
from nova_eval.p05 import run_p05, v02_cases


def test_p05_freezes_v01_and_records_unspecified_rule_gap(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    run_p05(root, tmp_path, execute_final=False)
    frozen = json.loads((tmp_path / "frozen_v0_1_manifest.json").read_text(encoding="utf-8"))
    audit = json.loads((tmp_path / "gate_semantics_audit.json").read_text(encoding="utf-8"))
    assert frozen["status"] == "FROZEN_REFERENCE"
    assert frozen["assets"]["v0_1_raw_results"]
    borderline = next(item for item in audit if item["condition"] == "Evidence close to a numerical threshold")
    assert borderline["expected_gate"] == "UNSPECIFIED"


def test_multistage_case_updates_evidence_then_selects_followup() -> None:
    case = next(item for item in v02_cases(per_family=1) if item.ground_truth.fault_type == "AMBIGUOUS_MULTI_STAGE")
    run = run_strategy(case, "nova")
    assert [item.experiment_type.value for item in run.selected_experiments] == ["ROLLING_VALIDATION_CHALLENGE", "PEAK_STABILITY_CHALLENGE"]
    assert [item.direction.value for item in run.evidence] == ["INCONCLUSIVE", "REFUTES"]
    assert run.gate == GateDecisionValue.BLOCKED
    assert len(run.selection_trace) == 2
