"""CLI runner and artifact writer for the reproducible P0 benchmark."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .baselines import STRATEGY_NAMES, run_strategy
from .generators import generate_suite
from .metrics import annotate, failure_records, selection_matrix, summarize
from .report import build_report


def _json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _figures(records: list[dict[str, Any]], output: Path) -> list[str]:
    import matplotlib.pyplot as plt

    output.mkdir(parents=True, exist_ok=True)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        if row["strategy_result"]["execution_status"] == "EXECUTED":
            groups[row["strategy"]].append(row)
    names = list(groups)
    def values(field: str) -> list[float]:
        return [sum(float(row["evaluation"].get(field, 0)) for row in groups[name]) / len(groups[name]) for name in names]
    files: list[str] = []
    def bar(filename: str, title: str, vals: list[float], ylabel: str) -> None:
        fig, axis = plt.subplots(figsize=(7, 4)); axis.bar(names, vals, color="#277da1"); axis.set_title(title); axis.set_ylabel(ylabel); axis.tick_params(axis="x", rotation=22); fig.tight_layout(); fig.savefig(output / filename, dpi=150); plt.close(fig); files.append(filename)
    bar("01_gate_accuracy.png", "Gate Accuracy", values("correct_gate"), "rate")
    bar("02_average_experiments.png", "Average Experiment Count", [sum(len(row["strategy_result"]["selected_experiments"]) for row in groups[name]) / len(groups[name]) for name in names], "count")
    bar("03_average_decision_cost.png", "Average Decision Cost", [sum(row["strategy_result"]["estimated_cost"] for row in groups[name]) / len(groups[name]) for name in names], "estimated cost")
    nova_faults = sorted({row["ground_truth"]["fault_type"] for row in groups.get("nova", [])})
    nova_top1 = [sum(row["evaluation"]["first_experiment_hit"] for row in groups["nova"] if row["ground_truth"]["fault_type"] == fault) / max(1, sum(row["ground_truth"]["fault_type"] == fault for row in groups["nova"])) for fault in nova_faults]
    fig, axis = plt.subplots(figsize=(8, 4)); axis.bar(nova_faults, nova_top1, color="#43aa8b"); axis.set_title("Nova Top-1 Selection Accuracy by Fault"); axis.set_ylabel("rate"); axis.tick_params(axis="x", rotation=28); fig.tight_layout(); fig.savefig(output / "04_nova_top1_by_fault.png", dpi=150); plt.close(fig); files.append("04_nova_top1_by_fault.png")
    bar("05_false_block_rate.png", "Clean False Block Rate", [sum(row["evaluation"]["false_block"] for row in groups[name]) / max(1, sum(row["ground_truth"]["fault_type"] == "CLEAN" for row in groups[name])) for name in names], "rate")
    fig, axis = plt.subplots(figsize=(7, 4))
    for name in ("nova", "fixed-all"):
        if name in groups:
            axis.hist([len(row["strategy_result"]["selected_experiments"]) for row in groups[name]], bins=range(0, 6), alpha=.55, label=name, align="left")
    axis.set_title("Experiments to Gate: Nova vs Fixed Run All"); axis.set_xlabel("experiment count"); axis.set_ylabel("cases"); axis.legend(); fig.tight_layout(); fig.savefig(output / "06_experiment_count_distribution.png", dpi=150); plt.close(fig); files.append("06_experiment_count_distribution.png")
    return files


def _reproducibility(cases: list[Any], strategies: list[str]) -> dict[str, Any]:
    checks = []
    for case in cases[: min(7, len(cases))]:
        for strategy in [item for item in strategies if item != "llm-only"]:
            first, second = run_strategy(case, strategy), run_strategy(case, strategy)
            checks.append(first.gate == second.gate and [item.experiment_type.value for item in first.selected_experiments] == [item.experiment_type.value for item in second.selected_experiments] and [item.direction.value for item in first.evidence] == [item.direction.value for item in second.evidence])
    return {"cases_checked": min(7, len(cases)), "strategy_runs_checked": len(checks), "logical_result_match_rate": sum(checks) / len(checks) if checks else None}


def run_benchmark(*, seed: int = 20260810, cases: int = 84, output: str | Path = "artifacts/nova_eval_v0_1", baselines: Iterable[str] = ("nova", "fixed-early-stop", "fixed-all", "surface-metric"), partition: str = "hidden") -> dict[str, Any]:
    """Run all requested strategies against an independently generated partition."""
    strategies = list(baselines)
    if strategies == ["all"]:
        strategies = ["nova", "fixed-early-stop", "fixed-all", "surface-metric"]
    unknown = sorted(set(strategies) - set(STRATEGY_NAMES))
    if unknown:
        raise ValueError(f"Unknown baselines: {unknown}")
    output_path = Path(output).resolve(); output_path.mkdir(parents=True, exist_ok=True)
    suite = generate_suite(seed, cases_per_family=max(1, (cases + 6) // 7), include_partitions=(partition,))
    raw: list[dict[str, Any]] = []
    for case in suite:
        for strategy in strategies:
            run = run_strategy(case, strategy)
            raw.append({"case_id": case.case_id, "partition": case.partition, "seed": case.seed, "strategy": strategy, "ground_truth": case.ground_truth.to_dict(), "strategy_result": run.to_dict()})
    annotate(raw)
    case_manifest = [case.manifest_record() for case in suite]
    summary, failures, matrix = summarize(raw), failure_records(raw), selection_matrix(raw)
    manifest = {"benchmark": "nova_eval_v0_1", "seed": seed, "requested_cases": cases, "generated_cases": len(suite), "partition": partition, "strategies": strategies, "python": sys.version, "platform": platform.platform(), "case_manifest_hash": _hash(case_manifest), "protocol_version": "nova_core_v0_1", "rule_pack_reference": "VAL-GATE-002, VAL-GATE-006, VAL-GATE-012", "experiment_registry_hash": _hash(["TIME_SPLIT_AUDIT", "LEAKAGE_CHALLENGE", "HIGH_LOAD_SUBSET_EVALUATION", "BASELINE_COMPARISON"]), "configuration_hash": _hash({"seed": seed, "cases": cases, "strategies": strategies, "partition": partition}), "reproducibility_check": _reproducibility(suite, strategies)}
    challenge_summary = output_path / "challenge_set" / "metric_summary.json"
    if partition != "challenge" and challenge_summary.exists():
        manifest["challenge_set_summary"] = json.loads(challenge_summary.read_text(encoding="utf-8")).get("strategies", {}).get("nova", {})
    _json(output_path / "benchmark_manifest.json", manifest); _json(output_path / "case_manifest.json", case_manifest); _json(output_path / "raw_results.json", raw); _json(output_path / "metric_summary.json", summary); _json(output_path / "failures.json", failures)
    flat = [{"case_id": row["case_id"], "partition": row["partition"], "strategy": row["strategy"], "fault_type": row["ground_truth"]["fault_type"], "expected_gate": row["ground_truth"]["expected_gate"], "predicted_gate": row["strategy_result"]["gate"], "correct_gate": row["evaluation"]["correct_gate"], "experiment_count": row["evaluation"]["experiment_count"], "estimated_cost": row["strategy_result"]["estimated_cost"], "duration_seconds": row["strategy_result"]["duration_seconds"], "first_experiment": (row["strategy_result"]["selected_experiments"] or ["NONE"])[0], "first_experiment_hit": row["evaluation"]["first_experiment_hit"], "evidence_traceable": row["evaluation"]["evidence_traceable"], "gate_traceable": row["evaluation"]["gate_traceable"], "stop_reason": row["strategy_result"]["stop_reason"]} for row in raw]
    _csv(output_path / "case_results.csv", flat); _csv(output_path / "selection_matrix.csv", matrix)
    confusion = [{"strategy": strategy, **data["confusion_matrix"]} for strategy, data in summary["strategies"].items()]
    _csv(output_path / "gate_confusion_matrix.csv", confusion)
    figure_files = _figures(raw, output_path / "figures")
    manifest["figures"] = figure_files; _json(output_path / "benchmark_manifest.json", manifest)
    (output_path / "report.txt").write_text(build_report(summary, failures, manifest), encoding="utf-8")
    return {"output": str(output_path), "manifest": manifest, "summary": summary, "failures": failures}
