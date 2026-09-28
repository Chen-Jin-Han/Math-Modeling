"""CLI for the deterministic Nova Core campus-load diagnosis MVP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .rule_inventory import build_rule_inventory
from .service import CampusLoadDiagnosisService, CampusLoadInput


def _fixture(name: str) -> CampusLoadInput:
    generator = np.random.default_rng(20260810)
    hours = np.arange(72)
    actual = 65 + 16 * np.sin(hours * 2 * np.pi / 24) + generator.normal(0, 1.2, size=72)
    predicted = actual + generator.normal(0, 1.6, size=72)
    if name == "time-split-leakage":
        return CampusLoadInput(actual.tolist(), actual.tolist(), split_strategy="random")
    if name == "feature-leakage":
        return CampusLoadInput(actual.tolist(), actual.tolist(), feature_origin_offsets=[0, 1])
    if name == "peak-failure":
        predicted = predicted.copy(); predicted[actual >= np.quantile(actual, 0.8)] -= 14
        return CampusLoadInput(actual.tolist(), predicted.tolist(), high_load_watch=True)
    return CampusLoadInput(actual.tolist(), predicted.tolist())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run-case")
    run.add_argument("case", choices=("time-split-leakage", "feature-leakage", "peak-failure", "clean"))
    run.add_argument("--output-root", type=Path, default=Path("artifacts/nova_core_v0_1/runs"))
    inventory = sub.add_parser("rule-inventory")
    inventory.add_argument("--output-root", type=Path, default=Path("artifacts/nova_core_v0_1"))
    args = parser.parse_args()
    if args.command == "run-case":
        result = CampusLoadDiagnosisService().diagnose(_fixture(args.case), output_root=args.output_root)
        print(json.dumps({"run_id": result.run_id, "gate": result.gate_decisions[-1].decision.value, "stop_reason": result.stop_reason, "first_experiment": result.experiments_executed[0].experiment_type.value}, ensure_ascii=False))
        return 0
    root = Path(__file__).resolve().parents[2]
    result = build_rule_inventory(root / "docs/reverse_engineering/skill_rule_pack_v1", root / "config/rule_implementation_registry.yaml")
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "rule_inventory.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_root / "rule_inventory_summary.txt").write_text(f"manifest={result['manifest_declared_total']} parsed={result['parsed_total']} yaml={result['yaml_rule_count']} markdown={result['markdown_rule_count']}\n{result['explanation']}\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("manifest_declared_total", "parsed_total", "yaml_rule_count", "markdown_rule_count")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
