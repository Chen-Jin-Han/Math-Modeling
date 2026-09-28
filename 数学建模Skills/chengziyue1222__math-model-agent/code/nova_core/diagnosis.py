"""Selection, evidence conversion, traceability checks, and deterministic gates."""

from __future__ import annotations

from typing import Any

from .enums import EvidenceDirection, GapStatus, GateDecisionValue, RiskSeverity, ToolStatus
from .models import Claim, Evidence, EvidenceGap, ExperimentSpec, GateDecision, Risk, ToolResult, canonical_hash


_SEVERITY_WEIGHT = {RiskSeverity.LOW: 1, RiskSeverity.MEDIUM: 2, RiskSeverity.HIGH: 3, RiskSeverity.CRITICAL: 4}


class ExperimentSelector:
    """Selects the highest-value open-gap experiment, rather than a fixed checklist."""

    def select(self, candidates: list[ExperimentSpec], gaps: list[EvidenceGap], risks: list[Risk], existing: list[Evidence]) -> tuple[ExperimentSpec | None, dict[str, Any]]:
        open_gaps = {gap.gap_id: gap for gap in gaps if gap.status == GapStatus.OPEN}
        risk_by_id = {risk.risk_id: risk for risk in risks}
        covered = {evidence.experiment_id for evidence in existing}
        scored: list[tuple[float, ExperimentSpec, dict[str, Any]]] = []
        for candidate in candidates:
            required = candidate.parameters.get("requires_evidence_from")
            if candidate.experiment_id in covered or (required and required not in covered) or not any(item in open_gaps for item in candidate.target_gap_ids):
                continue
            gap = open_gaps[next(item for item in candidate.target_gap_ids if item in open_gaps)]
            risk = risk_by_id[gap.risk_id]
            factors = {"gap_priority": gap.priority, "risk_severity": _SEVERITY_WEIGHT[risk.severity], "expected_information_gain": candidate.expected_information_gain, "estimated_cost": candidate.estimated_cost}
            score = factors["gap_priority"] * factors["risk_severity"] * factors["expected_information_gain"] / factors["estimated_cost"]
            scored.append((score, candidate, factors))
        if not scored:
            return None, {"selection_reason": "No executable experiment targets an open evidence gap.", "candidates": []}
        score, selected, factors = max(scored, key=lambda row: (row[0], row[1].experiment_type.value))
        return selected, {"selection_score": round(score, 4), "selection_factors": factors, "selection_reason": f"Selected {selected.experiment_type.value}: highest priority × severity × information-gain / cost score among open gaps.", "candidates": [{"experiment_id": item.experiment_id, "score": round(value, 4)} for value, item, _ in sorted(scored, reverse=True, key=lambda row: row[0])]}


class EvidenceBuilder:
    """Converts canonical ToolResult facts to Evidence; experiments do not write prose evidence."""

    def build(self, claim: Claim, risk: Risk, spec: ExperimentSpec, result: ToolResult) -> Evidence:
        if result.status == ToolStatus.FAILED:
            return self._evidence(claim, risk, spec, result, "execution_status", 0.0, None, None, EvidenceDirection.INCONCLUSIVE, "Experiment failed; the required evidence remains unavailable.", ["executor failure"])
        metrics, outputs = result.metrics, result.outputs
        if spec.experiment_type.value == "TIME_SPLIT_AUDIT":
            chronological = bool(outputs["chronological"])
            return self._evidence(claim, risk, spec, result, "chronological_split", float(chronological), 1.0, float(chronological) - 1.0, EvidenceDirection.SUPPORTS if chronological else EvidenceDirection.REFUTES, "Chronological split verified." if chronological else "Declared split is not chronological; future information may contaminate validation.", [])
        if spec.experiment_type.value == "LEAKAGE_CHALLENGE":
            count = metrics["future_feature_count"]
            suspicious = bool(outputs["suspicious_accuracy"])
            direction = EvidenceDirection.REFUTES if count > 0 or suspicious else EvidenceDirection.SUPPORTS
            observation = "Future-origin features were detected." if count > 0 else ("Near-perfect error is suspicious and requires provenance review." if suspicious else "No future-origin feature offset was detected and errors were recomputed.")
            return self._evidence(claim, risk, spec, result, "future_feature_count", count, 0.0, count, direction, observation, ["Offset audit only covers declared feature provenance."])
        if spec.experiment_type.value == "HIGH_LOAD_SUBSET_EVALUATION":
            ratio = metrics["high_to_overall_mae_ratio"]
            direction = EvidenceDirection.REFUTES if ratio > 1.75 else EvidenceDirection.SUPPORTS
            return self._evidence(claim, risk, spec, result, "high_to_overall_mae_ratio", ratio, 1.0, ratio - 1.0, direction, "High-load error materially exceeds overall error." if direction == EvidenceDirection.REFUTES else "High-load error remains proportionate to overall error.", ["High-load threshold is an empirical 80th percentile in v0.1."])
        if spec.experiment_type.value in {"ROLLING_VALIDATION_CHALLENGE", "PEAK_STABILITY_CHALLENGE"}:
            ratio = metrics["stability_ratio"]
            direction = EvidenceDirection.REFUTES if ratio > 1.75 else (EvidenceDirection.INCONCLUSIVE if ratio > 1.25 else EvidenceDirection.SUPPORTS)
            observation = "Fold stability crosses the declared failure threshold." if direction == EvidenceDirection.REFUTES else ("Fold stability is concerning but does not cross the declared failure threshold." if direction == EvidenceDirection.INCONCLUSIVE else "Fold stability remains proportionate.")
            return self._evidence(claim, risk, spec, result, "stability_ratio", ratio, 1.0, ratio - 1.0, direction, observation, ["Inconclusive stability evidence leaves its gap open for a prerequisite-aware follow-up experiment."])
        improvement = metrics["mae_improvement"]
        direction = EvidenceDirection.SUPPORTS if improvement > 0 else EvidenceDirection.REFUTES
        return self._evidence(claim, risk, spec, result, "mae_improvement", improvement, 0.0, improvement, direction, "Forecast improves on a causal persistence baseline." if improvement > 0 else "Forecast does not improve on the causal persistence baseline; VAL-GATE-012 preserves this weak-baseline failure as blocking evidence.", ["v0.2 semantics: this comparison is a single causal baseline, not a statistical superiority claim."])

    @staticmethod
    def _evidence(claim: Claim, risk: Risk, spec: ExperimentSpec, result: ToolResult, metric: str, value: float, baseline: float | None, delta: float | None, direction: EvidenceDirection, observation: str, limitations: list[str]) -> Evidence:
        return Evidence(evidence_id=f"EV-{result.tool_result_id}", claim_id=claim.claim_id, risk_id=risk.risk_id, experiment_id=spec.experiment_id, tool_result_id=result.tool_result_id, evidence_type=spec.experiment_type.value, observation=observation, metric=metric, value=value, baseline=baseline, delta=delta, direction=direction, confidence=0.95 if direction != EvidenceDirection.INCONCLUSIVE else 0.0, limitations=limitations, source_pointer=f"tool_results/{result.tool_result_id}.json#/metrics/{metric}", source_hash=result.output_hash)


def validate_evidence_trace(evidence: Evidence, result: ToolResult) -> list[str]:
    """Verify the Evidence source pointer and canonical ToolResult output hash."""
    errors: list[str] = []
    if evidence.tool_result_id != result.tool_result_id:
        errors.append("tool_result_id does not resolve")
    if evidence.experiment_id != result.experiment_id:
        errors.append("experiment_id does not resolve")
    if evidence.source_hash != canonical_hash({"outputs": result.outputs, "metrics": result.metrics, "status": result.status.value}):
        errors.append("ToolResult output hash mismatch")
    pointer_metric = evidence.source_pointer.rsplit("/", 1)[-1]
    if pointer_metric != evidence.metric or pointer_metric not in result.metrics:
        errors.append("source_pointer does not resolve to ToolResult.metrics")
    return errors


class GateEngine:
    """Applies existing Rule Pack IDs deterministically to evidence and open gaps."""

    def decide(self, claim: Claim, gaps: list[EvidenceGap], evidence: list[Evidence]) -> GateDecision:
        blocking = [item for item in evidence if item.direction == EvidenceDirection.REFUTES]
        open_gaps = [item.gap_id for item in gaps if item.status == GapStatus.OPEN]
        supporting = [item.evidence_id for item in evidence if item.direction == EvidenceDirection.SUPPORTS]
        if blocking:
            return GateDecision(gate_id="VAL-GATE-012", claim_id=claim.claim_id, decision=GateDecisionValue.BLOCKED, reason="Blocking evidence was preserved rather than converted into a success claim.", triggered_rules=["VAL-GATE-002", "VAL-GATE-012"], supporting_evidence_ids=supporting, blocking_evidence_ids=[item.evidence_id for item in blocking], remaining_gaps=open_gaps, confidence=max(item.confidence for item in blocking))
        if open_gaps:
            return GateDecision(gate_id="VAL-GATE-002", claim_id=claim.claim_id, decision=GateDecisionValue.NEEDS_REVIEW, reason="No blocking evidence exists, but required evidence gaps remain open.", triggered_rules=["VAL-GATE-002"], supporting_evidence_ids=supporting, blocking_evidence_ids=[], remaining_gaps=open_gaps, confidence=0.0)
        return GateDecision(gate_id="VAL-GATE-006", claim_id=claim.claim_id, decision=GateDecisionValue.READY_FOR_REVIEW, reason="All v0.1 evidence gaps were closed by successful, traceable experiments; human review remains required.", triggered_rules=["VAL-GATE-002", "VAL-GATE-006"], supporting_evidence_ids=supporting, blocking_evidence_ids=[], remaining_gaps=[], confidence=min((item.confidence for item in evidence), default=0.0))
