"""API boundary tests; Core decisions remain delegated to Nova Core."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from nova_api.adapters import demo_case
from nova_api.app import create_app
from nova_api.models import DiagnosisRequest
from nova_api.services import DiagnosisApiService, TraceabilityFailure
from nova_core.service import CampusLoadDiagnosisService


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("NOVA_API_KEY", "fixture-key")
    return TestClient(create_app(DiagnosisApiService(tmp_path / "runs")))


def _demo(case_id: str = "CASE-DEMO-001") -> dict[str, object]:
    return {"request_id": "REQ-1", "domain": "campus_load_forecast", "mode": "diagnose", "input_type": "demo_case", "case_id": case_id}


def test_health_and_protocol_are_public(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    assert client.get("/health").json()["protocol_version"] == "0.2"
    assert "ROLLING_VALIDATION_CHALLENGE" in client.get("/v1/protocol").json()["experiments"]


def test_auth_validation_and_truth_fields_fail_closed(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    assert client.post("/v1/diagnosis/run", json=_demo()).status_code == 401
    assert client.post("/v1/diagnosis/run", json=_demo(), headers={"X-Nova-API-Key": "wrong"}).status_code == 401
    injected = {**_demo(), "ground_truth": {"expected_gate": "BLOCKED"}}
    response = client.post("/v1/diagnosis/run", json=injected, headers={"X-Nova-API-Key": "fixture-key"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_demo_fault_run_retrieval_and_traceability(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch); headers = {"X-Nova-API-Key": "fixture-key"}
    response = client.post("/v1/diagnosis/run", json=_demo("CASE-DEMO-002"), headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["gate"]["decision"] == "BLOCKED"
    assert payload["traceability"]["valid"] is True
    fetched = client.get(f"/v1/diagnosis/runs/{payload['run_id']}?full=true", headers=headers)
    assert fetched.status_code == 200 and fetched.json()["tool_results"]
    assert client.get("/v1/diagnosis/runs/not-a-run", headers=headers).status_code == 404


def test_api_matches_direct_core_for_same_demo(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch); headers = {"X-Nova-API-Key": "fixture-key"}
    api = client.post("/v1/diagnosis/run", json=_demo("CASE-DEMO-003"), headers=headers).json()
    direct = CampusLoadDiagnosisService().diagnose(demo_case("CASE-DEMO-003"), output_root=tmp_path / "direct")
    assert api["gate"]["decision"] == direct.gate_decisions[-1].decision.value
    assert api["experiments"] == [item.experiment_type.value for item in direct.experiments_executed]
    assert [item["direction"] for item in api["key_evidence"]] == [item.direction.value for item in direct.evidence]


def test_core_and_traceability_failures_do_not_return_ready(tmp_path: Path, monkeypatch) -> None:
    class BrokenService:
        def run(self, _: DiagnosisRequest):
            raise TraceabilityFailure("tampered hash")

        def get(self, *_: object, **__: object):
            return None

    monkeypatch.setenv("NOVA_API_KEY", "fixture-key")
    client = TestClient(create_app(BrokenService()))
    response = client.post("/v1/diagnosis/run", json=_demo(), headers={"X-Nova-API-Key": "fixture-key"})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "TRACEABILITY_FAILED"
