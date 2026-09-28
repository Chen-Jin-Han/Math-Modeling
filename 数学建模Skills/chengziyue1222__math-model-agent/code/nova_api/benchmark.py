"""Small real-HTTP latency measurement for Tencent Tool timeout selection."""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from statistics import median
from typing import Any


def _post(base_url: str, key: str, case_id: str) -> float:
    payload = json.dumps({"request_id": f"PERF-{case_id}", "domain": "campus_load_forecast", "mode": "diagnose", "input_type": "demo_case", "case_id": case_id}).encode("utf-8")
    request = urllib.request.Request(f"{base_url.rstrip('/')}/v1/diagnosis/run", data=payload, method="POST", headers={"Content-Type": "application/json", "X-Nova-API-Key": key})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        json.loads(response.read().decode("utf-8"))
    return (time.perf_counter() - started) * 1000


def measure(base_url: str, key: str, output: str | Path, *, repetitions: int = 10) -> dict[str, Any]:
    samples = {"clean": [_post(base_url, key, "CASE-DEMO-001") for _ in range(repetitions)], "fault": [_post(base_url, key, "CASE-DEMO-002") for _ in range(repetitions)]}
    combined = sorted(samples["clean"] + samples["fault"])
    p95 = combined[max(0, int(len(combined) * .95) - 1)]
    payload = {"transport": "real_loopback_http", "repetitions_per_case": repetitions, "milliseconds": {name: {"p50": round(median(values), 3), "p95": round(sorted(values)[max(0, int(len(values) * .95) - 1)], 3), "max": round(max(values), 3), "samples": [round(value, 3) for value in values]} for name, values in samples.items()}, "combined": {"p50": round(median(combined), 3), "p95": round(p95, 3), "max": round(max(combined), 3)}, "recommended_timeout_seconds": max(1, int((p95 / 1000) * 4 + 1))}
    output_path = Path(output); output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "performance.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    contract = output_path / "tencent_tool_contract.json"
    if contract.exists():
        data = json.loads(contract.read_text(encoding="utf-8")); data["timeout_seconds"] = payload["recommended_timeout_seconds"]
        contract.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
