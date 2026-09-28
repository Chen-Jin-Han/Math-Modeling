"""Problem adapter: map the chemical-process brief to generic temporal models."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT / "code") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "code"))

from algorithms.modeling_contracts import validate_decision_contract


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(root: Path) -> None:
    results, reports = root / "results", root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    candidates = {
        "candidates": [
            {"name": "contemporaneous ridge regression", "use": "Q1 transparent no-delay baseline"},
            {"name": "random-forest regression", "use": "Q1 nonlinear current-input alternative"},
            {"name": "causal-window random-forest classifier", "use": "Q2 future-window alert probability"},
            {"name": "conditional random-forest regressor", "use": "Q3 earliest violation time after a predicted event"},
        ],
        "selection_rule": "select by chronological validation score; preserve a mean/constant baseline on the same split",
    }
    decision = {
        "questions": [
            {"id": "Q1", "result_artifact": "results/q1_predictions.csv", "validation_artifact": "results/q1_metrics.json", "requires_baseline": True},
            {"id": "Q2", "result_artifact": "results/q2_alert_predictions.csv", "validation_artifact": "results/q2_metrics.json", "requires_tradeoff": True, "requires_uncertainty": True},
            {"id": "Q3", "result_artifact": "results/q3_time_predictions.csv", "validation_artifact": "results/q3_metrics.json", "requires_uncertainty": True},
        ],
        "requirements": {"baseline_comparison_required": True, "uncertainty_analysis_required": True, "tradeoff_analysis_required": True},
        "decision_scope": "time-ordered prediction; process-control intervention requires operating bounds and causal validation not supplied in the attachment",
    }
    errors = validate_decision_contract(decision)
    if errors:
        raise ValueError(errors)
    plan = {"selected_models": {"Q1": "validation-selected current-input regressor", "Q2": "causal-window random-forest classifier", "Q3": "event-conditional random-forest timing regressor"}, "split": "chronological 60%/20%/20% origins with 10--70-step future labels", "history": 30, "horizon": [10, 70]}
    dump(results / "candidate_models.json", candidates)
    dump(results / "selected_model_plan.json", plan)
    dump(results / "decision_contract.json", decision)
    (reports / "problem_decomposition.md").write_text(
        "# Problem decomposition\n\nQ1 is contemporaneous two-output regression; Q2 is a causal future-window alert; Q3 estimates the earliest alert time conditional on an event.\n",
        encoding="utf-8",
    )
    dump(root / "config" / "baseline_plan.json", {"Q1": "train-mean two-output predictor", "Q2": "majority alert label", "Q3": "train-event median delay", "evaluation": "same chronological partitions as selected models"})
    dump(reports / "risk_register.json", {"status": "OPEN_LIMITATIONS", "risks": ["The official table supplies associations, not intervention-ready causal effects.", "Thresholds are selected on validation data and require post-deployment monitoring.", "IID bootstrap describes held-out-origin variation, not a calibrated event probability."]})
    (reports / "model_selection_report.md").parent.mkdir(parents=True, exist_ok=True)
    (reports / "model_selection_report.md").write_text("# Model selection\n\nQ1 compares same-time regressors against a mean baseline. Q2 and Q3 use only causal 30-step histories and chronological validation; no future target values enter their features.\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, required=True)
    main(parser.parse_args().root)
