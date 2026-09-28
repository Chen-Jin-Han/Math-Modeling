"""Fair strategies that all use the Nova Core executor when they execute tests."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

import numpy as np

from nova_core.diagnosis import EvidenceBuilder, ExperimentSelector, GateEngine
from nova_core.enums import EvidenceDirection, ExperimentType, GapStatus, GateDecisionValue
from nova_core.experiments import ExperimentExecutor, ExperimentRegistry
from nova_core.models import Claim, Evidence, EvidenceGap, ExperimentSpec, GateDecision, Risk
from nova_core.service import CampusLoadDiagnosisService

from .cases import EvaluationCase

STRATEGY_NAMES = ("nova", "fixed-early-stop", "fixed-all", "surface-metric", "llm-only")
_FIXED_ORDER = (
    ExperimentType.TIME_SPLIT_AUDIT,
    ExperimentType.LEAKAGE_CHALLENGE,
    ExperimentType.HIGH_LOAD_SUBSET_EVALUATION,
    ExperimentType.BASELINE_COMPARISON,
    ExperimentType.ROLLING_VALIDATION_CHALLENGE,
    ExperimentType.PEAK_STABILITY_CHALLENGE,
)


@dataclass
class StrategyRun:
    strategy: str
    case_id: str
    gate: GateDecisionValue | None
    selected_experiments: list[ExperimentSpec]
    tool_results: list[Any]
    evidence: list[Evidence]
    gate_decision: GateDecision | None
    selection_trace: list[dict[str, Any]]
    stop_reason: str
    duration_seconds: float
    execution_status: str = "EXECUTED"

    @property
    def estimated_cost(self) -> float:
        return float(sum(item.estimated_cost for item in self.selected_experiments))

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "case_id": self.case_id,
            "gate": self.gate.value if self.gate else None,
            "selected_experiments": [item.experiment_type.value for item in self.selected_experiments],
            "tool_results": [item.to_dict() for item in self.tool_results],
            "evidence": [item.to_dict() for item in self.evidence],
            "gate_decision": self.gate_decision.to_dict() if self.gate_decision else None,
            "selection_trace": self.selection_trace,
            "stop_reason": self.stop_reason,
            "duration_seconds": self.duration_seconds,
            "estimated_cost": self.estimated_cost,
            "execution_status": self.execution_status,
        }


def _claim() -> Claim:
    # Deliberately mirrors only the public production claim, never evaluator labels.
    return Claim("CLAIM-CAMPUS-LOAD-READINESS", "FORECAST_DECISION_READINESS", "The current forecast model has sufficient trustworthy evidence for future 24-hour campus high-load risk support.", "campus building future 24-hour load", "MAE", 0.0, "P0 synthetic controlled benchmark", "nova_eval shared executor", 1)


def _prepare(case: EvaluationCase) -> tuple[dict[str, Any], Claim, list[Risk], list[EvidenceGap], list[ExperimentSpec]]:
    context = case.core_input().context()
    service = CampusLoadDiagnosisService()
    claim = _claim()
    risks, gaps = service._initial_risks_and_gaps(claim, context)
    return context, claim, risks, gaps, ExperimentRegistry().candidates(gaps)


def _close(gaps: list[EvidenceGap], spec: ExperimentSpec, evidence: Evidence) -> list[EvidenceGap]:
    result: list[EvidenceGap] = []
    for gap in gaps:
        if gap.gap_id in spec.target_gap_ids:
            status = GapStatus.BLOCKED if evidence.direction == EvidenceDirection.REFUTES else (GapStatus.OPEN if evidence.direction == EvidenceDirection.INCONCLUSIVE else GapStatus.CLOSED)
            result.append(EvidenceGap(**{**gap.to_dict(), "status": status}))
        else:
            result.append(gap)
    return result


def _execute(case: EvaluationCase, strategy: str, *, fixed: bool, run_all: bool) -> StrategyRun:
    started = time.perf_counter()
    context, claim, risks, gaps, candidates = _prepare(case)
    executor, builder, gate_engine, selector = ExperimentExecutor(), EvidenceBuilder(), GateEngine(), ExperimentSelector()
    executed: list[ExperimentSpec] = []
    results: list[Any] = []
    evidence: list[Evidence] = []
    trace: list[dict[str, Any]] = []
    ordered = sorted(candidates, key=lambda item: _FIXED_ORDER.index(item.experiment_type))
    stop_reason = "ALL_REQUIRED_GAPS_CLOSED"
    iterations = len(ordered) if fixed and run_all else CampusLoadDiagnosisService.MAX_EXPERIMENTS
    for _ in range(iterations):
        if fixed:
            selected = next((item for item in ordered if item.experiment_id not in {done.experiment_id for done in executed}), None)
            trace.append({"selection_reason": "Fixed checklist order.", "selected_experiment": selected.experiment_type.value if selected else None})
        else:
            selected, selection = selector.select(candidates, gaps, risks, evidence)
            trace.append(selection)
        if selected is None:
            break
        executed.append(selected)
        result = executor.execute(selected, context, run_id=f"eval-{case.case_id}-{uuid.uuid4().hex[:8]}")
        results.append(result)
        risk = next(item for item in risks if any(gap.gap_id in selected.target_gap_ids and gap.risk_id == item.risk_id for gap in gaps))
        item = builder.build(claim, risk, selected, result)
        evidence.append(item)
        gaps = _close(gaps, selected, item)
        provisional = gate_engine.decide(claim, gaps, evidence)
        if provisional.decision == GateDecisionValue.BLOCKED and not run_all:
            stop_reason = "GATE_ALREADY_DECIDABLE"
            break
    else:
        stop_reason = "FIXED_CHECKLIST_COMPLETED" if run_all else "EXPERIMENT_BUDGET_REACHED"
    gate = gate_engine.decide(claim, gaps, evidence)
    return StrategyRun(strategy, case.case_id, gate.decision, executed, results, evidence, gate, trace, stop_reason, time.perf_counter() - started)


def _surface_metric(case: EvaluationCase) -> StrategyRun:
    """Runnable no-tool comparator; this is explicitly not an LLM baseline."""
    started = time.perf_counter()
    actual, predicted = np.asarray(case.load), np.asarray(case.prediction)
    mape = float(np.mean(np.abs((actual - predicted) / np.maximum(np.abs(actual), 1e-9))) * 100)
    gate = GateDecisionValue.READY_FOR_REVIEW if mape <= 12.0 else GateDecisionValue.BLOCKED
    return StrategyRun("surface-metric", case.case_id, gate, [], [], [], None, [{"surface_mape": mape, "threshold": 12.0}], "SURFACE_METRIC_DECISION", time.perf_counter() - started)


def _llm_not_executed(case: EvaluationCase) -> StrategyRun:
    return StrategyRun("llm-only", case.case_id, None, [], [], [], None, [], "NOT_EXECUTED_NO_PROVIDER", 0.0, "NOT_EXECUTED_NO_PROVIDER")


def run_strategy(case: EvaluationCase, strategy: str) -> StrategyRun:
    """Run a named strategy without exposing ``case.ground_truth`` to Core code."""
    if strategy == "nova":
        return _execute(case, strategy, fixed=False, run_all=False)
    if strategy == "fixed-early-stop":
        return _execute(case, strategy, fixed=True, run_all=False)
    if strategy == "fixed-all":
        return _execute(case, strategy, fixed=True, run_all=True)
    if strategy == "surface-metric":
        return _surface_metric(case)
    if strategy == "llm-only":
        return _llm_not_executed(case)
    raise ValueError(f"Unknown strategy: {strategy}. Choose from {', '.join(STRATEGY_NAMES)}")
