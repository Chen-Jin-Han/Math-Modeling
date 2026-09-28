"""P0 evaluation guards: reproducibility, fairness, and leakage prevention."""

from __future__ import annotations

import json
from pathlib import Path

from nova_eval.baselines import run_strategy
from nova_eval.generators import generate_suite
from nova_eval.metrics import annotate, summarize
from nova_eval.runner import run_benchmark


def test_generator_is_seed_reproducible_and_ids_are_neutral() -> None:
    first = generate_suite(44, cases_per_family=1)
    second = generate_suite(44, cases_per_family=1)
    assert [item.manifest_record() for item in first] == [item.manifest_record() for item in second]
    assert all(item.case_id.startswith("CASE-H-") for item in first)
    assert all(fault.lower() not in item.case_id.lower() for item in first for fault in ("leakage", "peak", "clean"))


def test_ground_truth_does_not_cross_the_core_input_boundary() -> None:
    case = generate_suite(45, cases_per_family=1)[0]
    core_input = case.core_input()
    assert "ground_truth" not in vars(core_input)
    assert "expected_gate" not in vars(core_input)
    assert "fault_type" not in vars(core_input)


def test_production_core_has_no_evaluation_dependency() -> None:
    root = Path(__file__).resolve().parents[2]
    source = "\n".join(path.read_text(encoding="utf-8") for path in (root / "code" / "nova_core").glob("*.py"))
    assert "nova_eval" not in source


def test_fixed_and_dynamic_use_shared_real_executor() -> None:
    case = next(item for item in generate_suite(46, cases_per_family=1) if item.ground_truth.fault_type == "CLEAN")
    dynamic, fixed = run_strategy(case, "nova"), run_strategy(case, "fixed-all")
    assert all(item.executor == "nova_core.experiments.execute" for item in dynamic.tool_results + fixed.tool_results)
    assert fixed.selected_experiments[0].experiment_type.value == "HIGH_LOAD_SUBSET_EVALUATION"
    assert dynamic.selection_trace[0]["selection_reason"].startswith("Selected")


def test_metric_confusion_matrix_counts_clean_false_block() -> None:
    case = next(item for item in generate_suite(47, cases_per_family=1) if item.ground_truth.fault_type == "CLEAN")
    result = run_strategy(case, "surface-metric").to_dict()
    result["gate"] = "BLOCKED"
    rows = annotate([{"case_id": case.case_id, "strategy": "surface-metric", "ground_truth": case.ground_truth.to_dict(), "strategy_result": result}])
    summary = summarize(rows)["strategies"]["surface-metric"]
    assert summary["confusion_matrix"]["FP"] == 1
    assert summary["false_block_rate"] == 1.0


def test_small_benchmark_writes_machine_readable_outputs_and_is_reproducible(tmp_path: Path) -> None:
    output = tmp_path / "eval"
    result = run_benchmark(seed=48, cases=7, output=output)
    required = {"benchmark_manifest.json", "case_manifest.json", "raw_results.json", "case_results.csv", "metric_summary.json", "selection_matrix.csv", "gate_confusion_matrix.csv", "failures.json", "report.txt"}
    assert required.issubset({path.name for path in output.iterdir()})
    assert len(list((output / "figures").glob("*.png"))) >= 5
    manifest = json.loads((output / "benchmark_manifest.json").read_text(encoding="utf-8"))
    assert manifest["reproducibility_check"]["logical_result_match_rate"] == 1.0
    assert result["summary"]["case_count"] == 7
