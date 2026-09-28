"""One-way conversion from public DTOs to Core inputs and verified summaries."""

from __future__ import annotations

from typing import Any

import numpy as np

from nova_core.diagnosis import validate_evidence_trace
from nova_core.service import CampusLoadInput

from .models import DiagnosisRequest


def demo_case(case_id: str) -> CampusLoadInput:
    """Deterministic API fixtures; opaque identifiers carry no evaluator labels."""
    generator = np.random.default_rng(20260810)
    hours = np.arange(72)
    actual = 65 + 16 * np.sin(hours * 2 * np.pi / 24) + generator.normal(0, 1.2, size=72)
    predicted = actual + generator.normal(0, 1.6, size=72)
    if case_id == "CASE-DEMO-002":
        return CampusLoadInput(actual.tolist(), actual.tolist(), feature_origin_offsets=[0, 1])
    if case_id == "CASE-DEMO-003":
        return CampusLoadInput(actual.tolist(), actual.tolist(), split_strategy="random")
    if case_id == "CASE-DEMO-001":
        return CampusLoadInput(actual.tolist(), predicted.tolist())
    raise ValueError("Unknown demo case; supported IDs are CASE-DEMO-001, CASE-DEMO-002, CASE-DEMO-003")


def to_core_input(request: DiagnosisRequest) -> CampusLoadInput:
    if request.input_type == "demo_case":
        return demo_case(request.case_id or "")
    if request.input_type != "structured_data" or request.data is None:
        raise ValueError("FILE_REFERENCE_ADAPTER_PENDING_TENCENT_INTEGRATION")
    data = request.data
    return CampusLoadInput(
        actual_load=data.actual_load,
        predicted_load=data.predicted_load,
        split_strategy=data.split_strategy,
        feature_origin_offsets=data.feature_origin_offsets,
        high_load_watch=data.high_load_watch,
        rolling_fold_errors=data.rolling_fold_errors,
        rolling_peak_errors=data.rolling_peak_errors,
        decision_contract={"request_id": request.request_id, "forecast_horizon_hours": request.decision_context.forecast_horizon_hours, "decision_use": request.decision_context.decision_use, "mode": "API_V0_1"},
    )


def verify_traceability(run: Any) -> list[str]:
    result_by_id = {item.tool_result_id: item for item in run.tool_results}
    errors = []
    for evidence in run.evidence:
        result = result_by_id.get(evidence.tool_result_id)
        if result is None:
            errors.append("Evidence references missing ToolResult")
        else:
            errors.extend(validate_evidence_trace(evidence, result))
    evidence_ids = {item.evidence_id for item in run.evidence}
    gate = run.gate_decisions[-1]
    if not gate.claim_id or not gate.triggered_rules:
        errors.append("Gate missing claim or rule trace")
    if not set(gate.supporting_evidence_ids + gate.blocking_evidence_ids).issubset(evidence_ids):
        errors.append("Gate references missing evidence")
    return errors


def response_summary(run: Any) -> dict[str, Any]:
    gate = run.gate_decisions[-1]
    return {
        "run_id": run.run_id,
        "status": "COMPLETED",
        "claim": {"claim_id": run.claims[0].claim_id, "statement": run.claims[0].statement},
        "gate": {"decision": gate.decision.value, "reason": gate.reason, "triggered_rules": gate.triggered_rules, "confidence": gate.confidence},
        "summary": f"Gate {gate.decision.value}; executed {len(run.experiments_executed)} traceable experiment(s).",
        "selection_trace_summary": [{"selection_reason": item.get("selection_reason"), "selection_score": item.get("selection_score")} for item in run.selection_trace],
        "key_evidence": [{"evidence_id": item.evidence_id, "direction": item.direction.value, "observation": item.observation, "tool_result_id": item.tool_result_id, "source_pointer": item.source_pointer} for item in run.evidence],
        "experiments": [item.experiment_type.value for item in run.experiments_executed],
        "remaining_gaps": gate.remaining_gaps,
        "stop_reason": run.stop_reason,
        "traceability": {"valid": True, "evidence_count": len(run.evidence), "tool_result_count": len(run.tool_results)},
        "artifacts": {"manifest_hashes": {item.tool_result_id: item.output_hash for item in run.tool_results}},
    }
