"""Campus-building 24-hour load forecasting diagnosis service for Nova Core v0.1."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.run_manifest import build_manifest

from .diagnosis import EvidenceBuilder, ExperimentSelector, GateEngine
from .enums import ClaimStatus, EvidenceDirection, GapStatus, RiskSeverity
from .experiments import ExperimentExecutor, ExperimentRegistry
from .models import Claim, DiagnosisRun, EvidenceGap, Risk, ToolResult, export_protocol_schemas, utc_now


@dataclass(frozen=True)
class CampusLoadInput:
    """Explicit model context; no scenario label is used by the production decision logic."""

    actual_load: list[float]
    predicted_load: list[float]
    split_strategy: str = "chronological"
    feature_origin_offsets: list[int] | None = None
    high_load_watch: bool = False
    rolling_fold_errors: list[float] | None = None
    rolling_peak_errors: list[float] | None = None
    decision_contract: dict[str, Any] | None = None

    def context(self) -> dict[str, Any]:
        return {
            "actual_load": self.actual_load,
            "predicted_load": self.predicted_load,
            "split_strategy": self.split_strategy,
            "feature_origin_offsets": self.feature_origin_offsets or [],
            "high_load_watch": self.high_load_watch,
            "rolling_fold_errors": self.rolling_fold_errors or [],
            "rolling_peak_errors": self.rolling_peak_errors or [],
        }


class CampusLoadDiagnosisService:
    """Coordinates dynamic selection through GateDecision with a bounded evidence budget."""

    MAX_EXPERIMENTS = 3

    def __init__(self) -> None:
        self.registry = ExperimentRegistry()
        self.selector = ExperimentSelector()
        self.executor = ExperimentExecutor()
        self.evidence_builder = EvidenceBuilder()
        self.gate_engine = GateEngine()

    def diagnose(self, request: CampusLoadInput, *, output_root: str | Path) -> DiagnosisRun:
        started, run_id = utc_now(), f"campus-load-{uuid.uuid4().hex[:12]}"
        root = Path(output_root).resolve() / run_id
        (root / "tool_results").mkdir(parents=True, exist_ok=True)
        (root / "evidence").mkdir(parents=True, exist_ok=True)
        context = request.context()
        (root / "inputs.json").write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        schemas = export_protocol_schemas()
        (root / "protocol_schemas.json").write_text(json.dumps(schemas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        claim = Claim("CLAIM-CAMPUS-LOAD-READINESS", "FORECAST_DECISION_READINESS", "The current forecast model has sufficient trustworthy evidence for future 24-hour campus high-load risk support.", "campus building future 24-hour load", "MAE", 0.0, "MVP synthetic or supplied load series", "CampusLoadDiagnosisService", 1, ClaimStatus.UNDER_DIAGNOSIS)
        contract = request.decision_contract or {"claim_id": claim.claim_id, "target": claim.target, "horizon_hours": 24, "mode": "MVP"}
        risks, gaps = self._initial_risks_and_gaps(claim, context)
        considered = self.registry.candidates(gaps)
        executed, results, evidence, selection_trace = [], [], [], []
        stop_reason = "NO_EXECUTABLE_HIGH_VALUE_EXPERIMENT"
        for _ in range(self.MAX_EXPERIMENTS):
            selected, selection = self.selector.select(considered, gaps, risks, evidence)
            selection_trace.append(selection)
            if selected is None:
                stop_reason = "ALL_REQUIRED_GAPS_CLOSED"
                break
            executed.append(selected)
            result = self.executor.execute(selected, context, run_id=run_id)
            result.artifacts.append(f"tool_results/{result.tool_result_id}.json")
            self._write_json(root / result.artifacts[0], result.to_dict())
            results.append(result)
            risk = next(item for item in risks if any(gap.gap_id in selected.target_gap_ids and gap.risk_id == item.risk_id for gap in gaps))
            item = self.evidence_builder.build(claim, risk, selected, result)
            self._write_json(root / "evidence" / f"{item.evidence_id}.json", item.to_dict())
            evidence.append(item)
            for index, gap in enumerate(gaps):
                if gap.gap_id in selected.target_gap_ids:
                    status = GapStatus.BLOCKED if item.direction == EvidenceDirection.REFUTES else (GapStatus.OPEN if item.direction == EvidenceDirection.INCONCLUSIVE else GapStatus.CLOSED)
                    gaps[index] = EvidenceGap(**{**gap.to_dict(), "status": status})
            provisional = self.gate_engine.decide(claim, gaps, evidence)
            if provisional.decision.value == "BLOCKED":
                stop_reason = "GATE_ALREADY_DECIDABLE"
                break
        else:
            stop_reason = "EXPERIMENT_BUDGET_REACHED"
        gate = self.gate_engine.decide(claim, gaps, evidence)
        status = gate.decision.value
        finished = utc_now()
        pending = DiagnosisRun(run_id, contract, [claim], risks, gaps, considered, executed, results, evidence, [gate], status, started, finished, {}, stop_reason, selection_trace)
        self._write_json(root / "diagnosis_run.json", pending.to_dict())
        manifest = self._manifest(root, run_id, status, results, contract)
        self._write_json(root / "manifest.json", manifest)
        final = DiagnosisRun(run_id, contract, [claim], risks, gaps, considered, executed, results, evidence, [gate], status, started, finished, manifest, stop_reason, selection_trace)
        self._write_json(root / "diagnosis_run.json", final.to_dict())
        self._write_summary(root / "summary.txt", final)
        return final

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _initial_risks_and_gaps(self, claim: Claim, context: dict[str, Any]) -> tuple[list[Risk], list[EvidenceGap]]:
        definitions = [
            ("TIME_SPLIT", context["split_strategy"] != "chronological", RiskSeverity.CRITICAL, 100, "Time split may expose future information."),
            ("FEATURE_LEAKAGE", any(item > 0 for item in context["feature_origin_offsets"]), RiskSeverity.CRITICAL, 95, "Feature provenance may use information after the forecast origin."),
            ("HIGH_LOAD", bool(context["high_load_watch"]), RiskSeverity.HIGH, 90, "Average performance may hide high-load failure."),
            ("BASELINE", True, RiskSeverity.MEDIUM, 20, "Forecast has not yet been compared to a causal baseline."),
            ("ROLLING_VALIDATION", bool(context.get("rolling_fold_errors")), RiskSeverity.HIGH, 85, "Rolling-validation stability requires executable evidence."),
        ]
        if not any(item[0] == "HIGH_LOAD" and item[1] for item in definitions):
            definitions.append(("HIGH_LOAD", True, RiskSeverity.MEDIUM, 10, "High-load error has not yet been measured."))
        risks, gaps = [], []
        for key, enabled, severity, priority, description in definitions:
            if not enabled:
                continue
            risk = Risk(f"RISK-{key}", claim.claim_id, key, description, severity, 5, 5 if severity == RiskSeverity.CRITICAL else 3, priority)
            risks.append(risk)
            gaps.append(EvidenceGap(f"GAP-{key}", claim.claim_id, risk.risk_id, f"Missing executable evidence for {key}.", description, priority))
        return risks, gaps

    @staticmethod
    def _manifest(root: Path, run_id: str, status: str, results: list[ToolResult], contract: dict[str, Any]) -> dict[str, Any]:
        try:
            base = root.parent
            spec = {
                "run_id": run_id, "problem": {"competition": "Nova Core", "year": 2026, "code": "CAMPUS-LOAD", "title": "Campus Building 24h Load Forecast", "source": "nova_core_v0_1"}, "stage": "validation", "status": "succeeded" if status != "BLOCKED" else "partial", "data_inputs": [{"path": str((root / "inputs.json").relative_to(base)).replace("\\", "/")}], "model": {"name": "campus-load-diagnosis", "version": "0.1", "parameter_source": "DiagnosisRun.decision_contract"}, "execution": {"command": ["python", "-m", "nova_core"], "deterministic": True, "random_seeds": {}}, "parameters": {**contract, "tool_result_metrics": {item.experiment_id: item.metrics for item in results}}, "metrics": {"executed_experiment_count": {"value": len(results), "unit": "count", "split": "diagnosis_run"}}, "failed_runs": [{"run_id": item.tool_result_id, "reason": "; ".join(item.errors) or "executor failed"} for item in results if item.status.value == "FAILED"], "artifacts": [{"path": str(path.relative_to(base)).replace("\\", "/"), "role": "nova_diagnosis_artifact"} for path in root.rglob("*.json") if path.name not in {"diagnosis_run.json", "manifest.json"}], "limitations": ["MVP only supports campus load forecasting diagnostics."],
            }
            return build_manifest(spec, base)
        except (ValueError, FileNotFoundError) as exc:
            return {"status": "partial", "run_id": run_id, "reason": f"run_manifest validation failed: {exc}", "tool_result_output_hashes": {item.tool_result_id: item.output_hash for item in results}}

    @staticmethod
    def _write_summary(path: Path, run: DiagnosisRun) -> None:
        gate = run.gate_decisions[-1]
        lines = [f"run_id: {run.run_id}", f"claim: {run.claims[0].statement}", f"gate: {gate.decision.value}", f"stop_reason: {run.stop_reason}", "experiments:"]
        lines.extend(f"- {item.experiment_type.value}" for item in run.experiments_executed)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
