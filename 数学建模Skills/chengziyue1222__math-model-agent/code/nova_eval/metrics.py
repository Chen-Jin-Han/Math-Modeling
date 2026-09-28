"""Transparent P0 metrics calculated from retained raw strategy results."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

def block(value: str | None) -> bool:
    return value == "BLOCKED"


def traceability(run: dict[str, Any]) -> tuple[bool, bool]:
    """Validate evidence hashes/pointers and gate references from raw data."""
    results = {item["tool_result_id"]: item for item in run["tool_results"]}
    evidence_ok = True
    for evidence in run["evidence"]:
        result = results.get(evidence["tool_result_id"])
        if result is None:
            evidence_ok = False
            continue
        # Imported protocol checker operates on models; raw field equivalence is enough here.
        pointer_metric = evidence["source_pointer"].rsplit("/", 1)[-1]
        evidence_ok = evidence_ok and evidence["experiment_id"] == result["experiment_id"] and pointer_metric == evidence["metric"] and pointer_metric in result["metrics"] and evidence["source_hash"] == result["output_hash"]
    gate = run.get("gate_decision")
    evidence_ids = {item["evidence_id"] for item in run["evidence"]}
    gate_ok = bool(gate and gate["claim_id"] and gate["triggered_rules"] and set(gate["supporting_evidence_ids"] + gate["blocking_evidence_ids"]).issubset(evidence_ids))
    return evidence_ok, gate_ok


def annotate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach evaluator-only correctness and traceability fields to raw records."""
    for record in records:
        truth, run = record["ground_truth"], record["strategy_result"]
        expected, predicted = truth["expected_gate"], run["gate"]
        evidence_ok, gate_ok = traceability(run) if run["execution_status"] == "EXECUTED" else (False, False)
        first = run["selected_experiments"][0] if run["selected_experiments"] else None
        record["evaluation"] = {
            "correct_gate": block(expected) == block(predicted),
            "fault_detected": (not block(expected)) or block(predicted),
            "false_block": truth["fault_type"] == "CLEAN" and block(predicted),
            "first_experiment_hit": bool(first and first in truth["acceptable_first_experiments"]),
            "evidence_traceable": evidence_ok,
            "gate_traceable": gate_ok,
            "experiment_count": len(run["selected_experiments"]),
            "decisive_experiment_count": len(run["selected_experiments"]),
            "unnecessary_experiments": max(0, len(run["selected_experiments"]) - 1) if run["stop_reason"] == "FIXED_CHECKLIST_COMPLETED" and block(predicted) else 0,
        }
    return records


def _rate(numerator: int | float, denominator: int | float) -> float | None:
    return round(float(numerator) / denominator, 6) if denominator else None


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute metrics by strategy and fault family, retaining denominators."""
    executed = [item for item in records if item["strategy_result"]["execution_status"] == "EXECUTED"]
    by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in executed:
        by_strategy[record["strategy"]].append(record)
    summary: dict[str, Any] = {"case_count": len({item["case_id"] for item in records}), "strategy_count": len(by_strategy), "strategies": {}, "by_fault_type": {}}
    for strategy, rows in by_strategy.items():
        tp = sum(block(row["ground_truth"]["expected_gate"]) and block(row["strategy_result"]["gate"]) for row in rows)
        tn = sum(not block(row["ground_truth"]["expected_gate"]) and not block(row["strategy_result"]["gate"]) for row in rows)
        fp = sum(not block(row["ground_truth"]["expected_gate"]) and block(row["strategy_result"]["gate"]) for row in rows)
        fn = sum(block(row["ground_truth"]["expected_gate"]) and not block(row["strategy_result"]["gate"]) for row in rows)
        correct = tp + tn
        values = [row["evaluation"] for row in rows]
        summary["strategies"][strategy] = {
            "n": len(rows), "gate_accuracy": _rate(correct, len(rows)), "fault_detection_rate": _rate(tp, tp + fn),
            "false_block_rate": _rate(sum(row["evaluation"]["false_block"] for row in rows), sum(row["ground_truth"]["fault_type"] == "CLEAN" for row in rows)),
            "precision": _rate(tp, tp + fp), "recall": _rate(tp, tp + fn), "f1": _rate(2 * tp, 2 * tp + fp + fn),
            "confusion_matrix": {"TP": tp, "TN": tn, "FP": fp, "FN": fn},
            "average_experiment_count": round(sum(item["experiment_count"] for item in values) / len(rows), 6),
            "average_decision_cost": round(sum(row["strategy_result"]["estimated_cost"] for row in rows) / len(rows), 6),
            "average_wall_seconds": round(sum(row["strategy_result"]["duration_seconds"] for row in rows) / len(rows), 6),
            "average_time_to_decisive_evidence": round(sum(item["decisive_experiment_count"] for item in values) / len(rows), 6),
            "top1_selection_accuracy": _rate(sum(item["first_experiment_hit"] for item in values), len(rows)),
            "selection_efficiency": _rate(sum(bool(row["strategy_result"]["evidence"]) for row in rows), sum(item["experiment_count"] for item in values)),
            "evidence_traceability_rate": _rate(sum(item["evidence_traceable"] for item in values), len(rows)),
            "gate_traceability_rate": _rate(sum(item["gate_traceable"] for item in values), len(rows)),
            "unnecessary_experiment_rate": _rate(sum(item["unnecessary_experiments"] for item in values), sum(item["experiment_count"] for item in values)),
            "selection_regret": "DEFERRED: no independent oracle-cost model in v0.1",
        }
    for fault_type in sorted({item["ground_truth"]["fault_type"] for item in executed}):
        rows = [item for item in executed if item["ground_truth"]["fault_type"] == fault_type]
        summary["by_fault_type"][fault_type] = {
            strategy: {"n": len(group), "gate_accuracy": _rate(sum(item["evaluation"]["correct_gate"] for item in group), len(group)), "top1_selection_accuracy": _rate(sum(item["evaluation"]["first_experiment_hit"] for item in group), len(group))}
            for strategy, group in ((name, [item for item in rows if item["strategy"] == name]) for name in by_strategy) if group
        }
    return summary


def failure_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for record in records:
        run, evaluation = record["strategy_result"], record["evaluation"]
        kind = None
        if run["execution_status"] != "EXECUTED":
            kind = "EXECUTION_FAILURE"
        elif not evaluation["correct_gate"]:
            kind = "GATE_FAILURE" if run["evidence"] else "EVIDENCE_FAILURE"
        elif run["selected_experiments"] and not evaluation["first_experiment_hit"]:
            kind = "SELECTION_FAILURE"
        elif record["ground_truth"]["fault_type"] == "BORDERLINE":
            kind = "AMBIGUOUS_CASE"
        if kind:
            failures.append({"failure_type": kind, "case_id": record["case_id"], "strategy": record["strategy"], "fault_type": record["ground_truth"]["fault_type"], "expected_gate": record["ground_truth"]["expected_gate"], "predicted_gate": run["gate"], "stop_reason": run["stop_reason"]})
    return failures


def selection_matrix(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str, str]] = Counter()
    for row in records:
        first = row["strategy_result"]["selected_experiments"][:1]
        counts[(row["strategy"], row["ground_truth"]["fault_type"], first[0] if first else "NONE")] += 1
    return [{"strategy": strategy, "fault_type": fault, "first_experiment": experiment, "count": count} for (strategy, fault, experiment), count in sorted(counts.items())]
