"""Machine-validatable protocol models for an evidence-gated diagnosis run."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar, Mapping

from .enums import ClaimStatus, EvidenceDirection, ExperimentType, GapStatus, GateDecisionValue, RiskSeverity, ToolStatus


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProtocolValidationError(ValueError):
    """Raised when a protocol object lacks a traceability-critical field."""


def _normalize(value: Any) -> Any:
    if hasattr(value, "value") and value.__class__.__module__ == "nova_core.enums":
        return value.value
    if dataclasses.is_dataclass(value):
        return _normalize(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


@dataclass
class ProtocolModel:
    schema_name: ClassVar[str]
    schema_fields: ClassVar[dict[str, dict[str, Any]]]

    def __post_init__(self) -> None:
        for name, definition in self.schema_fields.items():
            if definition.get("required") and getattr(self, name) in (None, ""):
                raise ProtocolValidationError(f"{self.schema_name}.{name} is required")

    def to_dict(self) -> dict[str, Any]:
        return _normalize(dataclasses.asdict(self))

    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": cls.schema_name,
            "type": "object",
            "properties": {name: {key: value for key, value in spec.items() if key != "required"} for name, spec in cls.schema_fields.items()},
            "required": [name for name, spec in cls.schema_fields.items() if spec.get("required")],
            "additionalProperties": False,
        }


@dataclass
class Claim(ProtocolModel):
    claim_id: str; claim_type: str; statement: str; target: str; metric: str; threshold: float; scope: str; source: str; importance: int; status: ClaimStatus = ClaimStatus.PROPOSED
    schema_name = "Claim"
    schema_fields = {"claim_id": {"type": "string", "required": True}, "claim_type": {"type": "string", "required": True}, "statement": {"type": "string", "required": True}, "target": {"type": "string", "required": True}, "metric": {"type": "string", "required": True}, "threshold": {"type": "number", "required": True}, "scope": {"type": "string", "required": True}, "source": {"type": "string", "required": True}, "importance": {"type": "integer", "minimum": 1, "required": True}, "status": {"type": "string", "enum": [item.value for item in ClaimStatus]}}


@dataclass
class Risk(ProtocolModel):
    risk_id: str; claim_id: str; risk_type: str; description: str; severity: RiskSeverity; decision_impact: int; likelihood: int; priority: int
    schema_name = "Risk"
    schema_fields = {"risk_id": {"type": "string", "required": True}, "claim_id": {"type": "string", "required": True}, "risk_type": {"type": "string", "required": True}, "description": {"type": "string", "required": True}, "severity": {"type": "string", "enum": [item.value for item in RiskSeverity], "required": True}, "decision_impact": {"type": "integer", "minimum": 1, "required": True}, "likelihood": {"type": "integer", "minimum": 1, "required": True}, "priority": {"type": "integer", "minimum": 1, "required": True}}


@dataclass
class EvidenceGap(ProtocolModel):
    gap_id: str; claim_id: str; risk_id: str; missing_evidence: str; why_needed: str; priority: int; status: GapStatus = GapStatus.OPEN
    schema_name = "EvidenceGap"
    schema_fields = {"gap_id": {"type": "string", "required": True}, "claim_id": {"type": "string", "required": True}, "risk_id": {"type": "string", "required": True}, "missing_evidence": {"type": "string", "required": True}, "why_needed": {"type": "string", "required": True}, "priority": {"type": "integer", "minimum": 1, "required": True}, "status": {"type": "string", "enum": [item.value for item in GapStatus]}}


@dataclass
class ExperimentSpec(ProtocolModel):
    experiment_id: str; experiment_type: ExperimentType; target_gap_ids: list[str]; description: str; required_inputs: list[str]; estimated_cost: float; expected_information_gain: float; executor: str; parameters: dict[str, Any] = field(default_factory=dict)
    schema_name = "ExperimentSpec"
    schema_fields = {"experiment_id": {"type": "string", "required": True}, "experiment_type": {"type": "string", "enum": [item.value for item in ExperimentType], "required": True}, "target_gap_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "required": True}, "description": {"type": "string", "required": True}, "required_inputs": {"type": "array", "items": {"type": "string"}, "required": True}, "estimated_cost": {"type": "number", "exclusiveMinimum": 0, "required": True}, "expected_information_gain": {"type": "number", "minimum": 0, "required": True}, "executor": {"type": "string", "required": True}, "parameters": {"type": "object"}}


@dataclass
class ToolResult(ProtocolModel):
    tool_result_id: str; experiment_id: str; executor: str; status: ToolStatus; started_at: str; finished_at: str; inputs: dict[str, Any]; parameters: dict[str, Any]; outputs: dict[str, Any]; metrics: dict[str, float]; artifacts: list[str]; warnings: list[str]; errors: list[str]; run_id: str; input_hash: str; output_hash: str
    schema_name = "ToolResult"
    schema_fields = {"tool_result_id": {"type": "string", "required": True}, "experiment_id": {"type": "string", "required": True}, "executor": {"type": "string", "required": True}, "status": {"type": "string", "enum": [item.value for item in ToolStatus], "required": True}, "started_at": {"type": "string", "format": "date-time", "required": True}, "finished_at": {"type": "string", "format": "date-time", "required": True}, "inputs": {"type": "object", "required": True}, "parameters": {"type": "object", "required": True}, "outputs": {"type": "object", "required": True}, "metrics": {"type": "object", "required": True}, "artifacts": {"type": "array", "items": {"type": "string"}, "required": True}, "warnings": {"type": "array", "items": {"type": "string"}, "required": True}, "errors": {"type": "array", "items": {"type": "string"}, "required": True}, "run_id": {"type": "string", "required": True}, "input_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$", "required": True}, "output_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$", "required": True}}


@dataclass
class Evidence(ProtocolModel):
    evidence_id: str; claim_id: str; risk_id: str; experiment_id: str; tool_result_id: str; evidence_type: str; observation: str; metric: str; value: float | None; baseline: float | None; delta: float | None; direction: EvidenceDirection; confidence: float; limitations: list[str]; source_pointer: str; source_hash: str; created_at: str = field(default_factory=utc_now)
    schema_name = "Evidence"
    schema_fields = {"evidence_id": {"type": "string", "required": True}, "claim_id": {"type": "string", "required": True}, "risk_id": {"type": "string", "required": True}, "experiment_id": {"type": "string", "required": True}, "tool_result_id": {"type": "string", "required": True}, "evidence_type": {"type": "string", "required": True}, "observation": {"type": "string", "required": True}, "metric": {"type": "string", "required": True}, "value": {"type": ["number", "null"]}, "baseline": {"type": ["number", "null"]}, "delta": {"type": ["number", "null"]}, "direction": {"type": "string", "enum": [item.value for item in EvidenceDirection], "required": True}, "confidence": {"type": "number", "minimum": 0, "maximum": 1, "required": True}, "limitations": {"type": "array", "items": {"type": "string"}, "required": True}, "source_pointer": {"type": "string", "required": True}, "source_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$", "required": True}, "created_at": {"type": "string", "format": "date-time", "required": True}}


@dataclass
class GateDecision(ProtocolModel):
    gate_id: str; claim_id: str; decision: GateDecisionValue; reason: str; triggered_rules: list[str]; supporting_evidence_ids: list[str]; blocking_evidence_ids: list[str]; remaining_gaps: list[str]; confidence: float; created_at: str = field(default_factory=utc_now)
    schema_name = "GateDecision"
    schema_fields = {"gate_id": {"type": "string", "required": True}, "claim_id": {"type": "string", "required": True}, "decision": {"type": "string", "enum": [item.value for item in GateDecisionValue], "required": True}, "reason": {"type": "string", "required": True}, "triggered_rules": {"type": "array", "items": {"type": "string"}, "required": True}, "supporting_evidence_ids": {"type": "array", "items": {"type": "string"}, "required": True}, "blocking_evidence_ids": {"type": "array", "items": {"type": "string"}, "required": True}, "remaining_gaps": {"type": "array", "items": {"type": "string"}, "required": True}, "confidence": {"type": "number", "minimum": 0, "maximum": 1, "required": True}, "created_at": {"type": "string", "format": "date-time", "required": True}}


@dataclass
class DiagnosisRun(ProtocolModel):
    run_id: str; decision_contract: dict[str, Any]; claims: list[Claim]; risks: list[Risk]; evidence_gaps: list[EvidenceGap]; experiments_considered: list[ExperimentSpec]; experiments_executed: list[ExperimentSpec]; tool_results: list[ToolResult]; evidence: list[Evidence]; gate_decisions: list[GateDecision]; status: str; started_at: str; finished_at: str; manifest: dict[str, Any]; stop_reason: str; selection_trace: list[dict[str, Any]] = field(default_factory=list)
    schema_name = "DiagnosisRun"
    schema_fields = {"run_id": {"type": "string", "required": True}, "decision_contract": {"type": "object", "required": True}, "claims": {"type": "array", "required": True}, "risks": {"type": "array", "required": True}, "evidence_gaps": {"type": "array", "required": True}, "experiments_considered": {"type": "array", "required": True}, "experiments_executed": {"type": "array", "required": True}, "tool_results": {"type": "array", "required": True}, "evidence": {"type": "array", "required": True}, "gate_decisions": {"type": "array", "required": True}, "status": {"type": "string", "required": True}, "started_at": {"type": "string", "format": "date-time", "required": True}, "finished_at": {"type": "string", "format": "date-time", "required": True}, "manifest": {"type": "object", "required": True}, "stop_reason": {"type": "string", "required": True}, "selection_trace": {"type": "array"}}


def canonical_hash(value: Mapping[str, Any]) -> str:
    payload = json.dumps(_normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def export_protocol_schemas() -> dict[str, Any]:
    models = (Claim, Risk, EvidenceGap, ExperimentSpec, ToolResult, Evidence, GateDecision, DiagnosisRun)
    return {model.schema_name: model.json_schema() for model in models}
