"""Core invocation and filesystem-backed completed-run retrieval."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from nova_core.service import CampusLoadDiagnosisService

from .adapters import response_summary, to_core_input, verify_traceability
from .models import DiagnosisRequest


class TraceabilityFailure(RuntimeError):
    pass


class DiagnosisApiService:
    def __init__(self, artifact_root: str | Path | None = None) -> None:
        self.artifact_root = Path(artifact_root or os.environ.get("NOVA_API_ARTIFACT_ROOT", "artifacts/nova_api_v0_1/runs")).resolve()

    def run(self, request: DiagnosisRequest) -> dict[str, Any]:
        core_run = CampusLoadDiagnosisService().diagnose(to_core_input(request), output_root=self.artifact_root)
        errors = verify_traceability(core_run)
        if errors:
            raise TraceabilityFailure("; ".join(errors))
        return response_summary(core_run)

    def get(self, run_id: str, *, full: bool) -> dict[str, Any] | None:
        path = self.artifact_root / run_id / "diagnosis_run.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if full:
            return payload
        gate = payload["gate_decisions"][-1]
        return {"run_id": payload["run_id"], "status": "COMPLETED", "gate": {"decision": gate["decision"], "reason": gate["reason"], "triggered_rules": gate["triggered_rules"]}, "experiments": [item["experiment_type"] for item in payload["experiments_executed"]], "stop_reason": payload["stop_reason"], "traceability": {"valid": True}}
