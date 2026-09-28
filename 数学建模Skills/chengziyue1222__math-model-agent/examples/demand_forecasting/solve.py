"""Run a leakage-safe seasonal demand forecast with a baseline comparison."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
import numpy as np

from examples._common import write_json, write_manifest


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _design_matrix(indices: np.ndarray) -> np.ndarray:
    months = indices % 12
    month_effects = np.column_stack([(months == month).astype(float) for month in range(1, 12)])
    return np.column_stack((np.ones(len(indices)), indices, month_effects))


def run(project_root: Path) -> dict:
    root = project_root.resolve()
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    with (root / "data" / "monthly_demand.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    labels = [row["month"] for row in rows]
    demand = np.array([float(row["demand"]) for row in rows])
    train_months = int(config["train_months"])
    horizon = int(config["forecast_horizon"])
    if train_months < 12 or len(demand) != train_months + horizon or horizon != 12:
        raise ValueError("example requires at least 12 training months and a 12-month holdout")

    train_index = np.arange(train_months)
    test_index = np.arange(train_months, len(demand))
    coefficients = np.linalg.lstsq(_design_matrix(train_index), demand[:train_months], rcond=None)[0]
    predicted = _design_matrix(test_index) @ coefficients
    actual = demand[train_months:]
    baseline = demand[train_months - 12 : train_months]
    error = predicted - actual
    baseline_error = baseline - actual
    mae = float(np.mean(np.abs(error)))
    baseline_mae = float(np.mean(np.abs(baseline_error)))
    rmse = float(np.sqrt(np.mean(error**2)))
    mape = float(np.mean(np.abs(error / actual)) * 100)
    improvement = float((baseline_mae - mae) / baseline_mae * 100)
    if not mae < baseline_mae:
        raise RuntimeError("forecast must outperform the declared seasonal-naive baseline")

    results = {
        "model": "linear-trend-month-effects",
        "model_version": config["model_version"],
        "train_months": train_months,
        "holdout_months": horizon,
        "coefficients": coefficients.tolist(),
        "holdout": [
            {
                "month": label,
                "actual": float(observed),
                "prediction": float(forecast),
                "seasonal_naive": float(naive),
            }
            for label, observed, forecast, naive in zip(
                labels[train_months:], actual, predicted, baseline
            )
        ],
        "metrics": {
            "mae": mae,
            "rmse": rmse,
            "mape_percent": mape,
            "baseline_mae": baseline_mae,
            "mae_improvement_percent": improvement,
        },
    }
    validation = {
        "passed": True,
        "checks": {
            "holdout_not_used_for_fit": True,
            "forecast_count": len(predicted) == horizon,
            "all_predictions_finite": bool(np.isfinite(predicted).all()),
            "beats_seasonal_naive_mae": mae < baseline_mae,
        },
    }
    write_json(root / "results" / "results.json", results)
    write_json(root / "reports" / "validation.json", validation)

    figure_path = root / "figures" / "holdout_forecast.svg"
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    x = np.arange(len(demand))
    ax.plot(x, demand, color="#334155", marker="o", markersize=3, label="Observed")
    ax.plot(test_index, baseline, "--", color="#D97706", label="Seasonal naive")
    ax.plot(test_index, predicted, color="#0072B2", marker="s", markersize=3, label="Model")
    ax.axvline(train_months - 0.5, color="#64748B", linewidth=1, linestyle=":")
    ax.set(xlabel="Month index", ylabel="Demand", title="Holdout demand forecast")
    ax.legend(frameon=False, ncol=3)
    fig.tight_layout()
    fig.savefig(figure_path, format="svg")
    plt.close(fig)

    specification = {
        "run_id": "demand-forecast-v1",
        "problem": {
            "competition": "workflow-demo",
            "year": 2026,
            "code": "prediction",
            "title": "Monthly demand forecasting",
            "source": "data/monthly_demand.csv",
        },
        "stage": "validation",
        "status": "succeeded",
        "data_inputs": ["data/monthly_demand.csv", "config.json"],
        "model": {
            "name": "linear-trend-month-effects",
            "version": config["model_version"],
            "assumptions_path": "assumptions.md",
            "parameter_source": "config.json",
        },
        "execution": {
            "command": ["python", "-m", "examples.demand_forecasting.solve"],
            "deterministic": True,
            "random_seeds": {},
        },
        "parameters": config,
        "metrics": {
            "holdout_mae": {"value": mae, "unit": "demand units", "split": "holdout"},
            "baseline_mae": {
                "value": baseline_mae,
                "unit": "demand units",
                "split": "holdout",
            },
            "mae_improvement": {"value": improvement, "unit": "%", "split": "holdout"},
        },
        "failed_runs": [],
        "artifacts": [
            {"path": "results/results.json", "role": "machine-readable-results"},
            {"path": "reports/validation.json", "role": "validation-report"},
            {"path": "figures/holdout_forecast.svg", "role": "diagnostic-figure"},
        ],
        "limitations": [
            "Synthetic data demonstrate the workflow and do not represent a real market.",
            "Month effects are assumed stable across the forecast horizon.",
        ],
    }
    write_manifest(root, specification)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    results = run(args.project_root)
    print(json.dumps(results["metrics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
