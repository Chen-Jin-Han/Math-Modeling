"""Run Nova API or export its generated contract artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn

from .app import create_app
from .benchmark import measure


def export_contract(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    app = create_app(); openapi = app.openapi()
    (output / "openapi.json").write_text(json.dumps(openapi, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    request = {"request_id": "REQ-DEMO-001", "domain": "campus_load_forecast", "mode": "diagnose", "input_type": "demo_case", "case_id": "CASE-DEMO-002", "decision_context": {"forecast_horizon_hours": 24, "decision_use": "high_load_risk_assessment"}}
    (output / "request_examples.json").write_text(json.dumps({"demo_leakage": request, "file_reference": {"input_type": "file_reference", "file_reference": {"file_id": "pending"}, "status": "FILE_REFERENCE_ADAPTER_PENDING_TENCENT_INTEGRATION"}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    response = {"run_id": "generated-at-runtime", "status": "COMPLETED", "gate": {"decision": "BLOCKED", "triggered_rules": ["VAL-GATE-002", "VAL-GATE-012"]}, "traceability": {"valid": True}}
    (output / "response_examples.json").write_text(json.dumps(response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tool = {"name": "NovaCore可信诊断", "method": "POST", "endpoint": "/v1/diagnosis/run", "authentication": {"header": "X-Nova-API-Key", "value_source": "NOVA_API_KEY"}, "input_schema_ref": "openapi.json#/paths/~1v1~1diagnosis~1run/post/requestBody", "output": "Compact traceable diagnosis summary; use GET /v1/diagnosis/runs/{run_id}?full=true for full result.", "timeout_seconds": "SET_FROM_LOCAL_PERFORMANCE_MEASUREMENT"}
    (output / "tencent_tool_contract.json").write_text(json.dumps(tool, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "tencent_tool_setup.txt").write_text("Tool name: NovaCore可信诊断\nMethod: POST\nEndpoint: <base-url>/v1/diagnosis/run\nAuthentication: X-Nova-API-Key: <NOVA_API_KEY>\nDo not configure a placeholder public URL. Set timeout from performance.json after local measurement.\n", encoding="utf-8")
    (output / "deployment_requirements.txt").write_text("Python >=3.10\nWorking directory: repository root\nEnvironment: NOVA_API_KEY (required), NOVA_API_ARTIFACT_ROOT (optional)\nStart: python -m nova_api --host 0.0.0.0 --port 8000\nHealth: GET /health\nPublic HTTPS and Tencent deployment are intentionally not configured in v0.1.\n", encoding="utf-8")
    (output / "env.example").write_text("NOVA_API_KEY=replace-with-a-long-random-secret\nNOVA_API_ARTIFACT_ROOT=artifacts/nova_api_v0_1/runs\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m nova_api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--export-contract", type=Path)
    parser.add_argument("--measure-url")
    parser.add_argument("--measure-key")
    parser.add_argument("--measure-output", type=Path, default=Path("artifacts/nova_api_v0_1"))
    args = parser.parse_args()
    if args.export_contract:
        export_contract(args.export_contract)
        return 0
    if args.measure_url:
        if not args.measure_key:
            parser.error("--measure-key is required with --measure-url")
        print(json.dumps(measure(args.measure_url, args.measure_key, args.measure_output), ensure_ascii=False, indent=2))
        return 0
    uvicorn.run("nova_api.app:app", host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
