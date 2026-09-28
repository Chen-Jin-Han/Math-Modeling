"""Registry and real Python executors for the campus-load diagnosis MVP."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

from algorithms.data_diagnostics import panel_diagnostics
from algorithms.process_forecasting import regression_scores

from .enums import ExperimentType, ToolStatus
from .models import ExperimentSpec, ToolResult, canonical_hash, utc_now


def mean_absolute_percentage_error(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Calculate MAPE from arrays while excluding zero-denominator observations."""
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    nonzero = np.abs(actual) > 1e-9
    return float(np.mean(np.abs((actual[nonzero] - predicted[nonzero]) / actual[nonzero])) * 100) if np.any(nonzero) else float("nan")


class ExperimentRegistry:
    """Small, executable registry; experiments are selected from open evidence gaps."""

    _DEFINITIONS = {
        ExperimentType.TIME_SPLIT_AUDIT: ("Audit chronological partitioning with existing panel diagnostics.", ("actual_load", "split_strategy"), 1.0, 0.95),
        ExperimentType.LEAKAGE_CHALLENGE: ("Challenge future-feature provenance and recompute forecast errors.", ("actual_load", "predicted_load", "feature_origin_offsets"), 1.5, 0.98),
        ExperimentType.HIGH_LOAD_SUBSET_EVALUATION: ("Compare all-period and high-load error on the same forecasts.", ("actual_load", "predicted_load"), 1.2, 0.90),
        ExperimentType.BASELINE_COMPARISON: ("Compare supplied forecasts to a causal persistence baseline.", ("actual_load", "predicted_load"), 1.0, 0.70),
        ExperimentType.ROLLING_VALIDATION_CHALLENGE: ("Audit error stability across chronological validation folds.", ("rolling_fold_errors",), 0.6, 0.82),
        ExperimentType.PEAK_STABILITY_CHALLENGE: ("Challenge high-load stability across validation folds after a rolling audit.", ("rolling_peak_errors",), 1.4, 0.92),
    }

    def candidates(self, gaps: list[Any]) -> list[ExperimentSpec]:
        open_ids = {gap.gap_id: gap for gap in gaps if gap.status.value == "OPEN"}
        gap_by_type = {gap.risk_id.split("-", 1)[-1]: gap.gap_id for gap in open_ids.values()}
        mapping = {
            ExperimentType.TIME_SPLIT_AUDIT: "TIME_SPLIT",
            ExperimentType.LEAKAGE_CHALLENGE: "FEATURE_LEAKAGE",
            ExperimentType.HIGH_LOAD_SUBSET_EVALUATION: "HIGH_LOAD",
            ExperimentType.BASELINE_COMPARISON: "BASELINE",
            ExperimentType.ROLLING_VALIDATION_CHALLENGE: "ROLLING_VALIDATION",
            ExperimentType.PEAK_STABILITY_CHALLENGE: "ROLLING_VALIDATION",
        }
        items: list[ExperimentSpec] = []
        for kind, risk_key in mapping.items():
            if risk_key not in gap_by_type:
                continue
            description, inputs, cost, gain = self._DEFINITIONS[kind]
            items.append(ExperimentSpec(
                experiment_id=f"EXP-{kind.value}", experiment_type=kind,
                target_gap_ids=[gap_by_type[risk_key]], description=description,
                required_inputs=list(inputs), estimated_cost=cost, expected_information_gain=gain,
                executor="nova_core.experiments.execute", parameters={"high_load_quantile": 0.8, **({"requires_evidence_from": "EXP-ROLLING_VALIDATION_CHALLENGE"} if kind == ExperimentType.PEAK_STABILITY_CHALLENGE else {})},
            ))
        return items


class ExperimentExecutor:
    """Executes registry entries with repository algorithms; never fabricates outcomes."""

    def __init__(self) -> None:
        self._executors: dict[ExperimentType, Callable[[dict[str, Any], dict[str, Any]], tuple[dict[str, Any], dict[str, float], list[str]]]] = {
            ExperimentType.TIME_SPLIT_AUDIT: self._time_split_audit,
            ExperimentType.LEAKAGE_CHALLENGE: self._leakage_challenge,
            ExperimentType.HIGH_LOAD_SUBSET_EVALUATION: self._high_load_subset,
            ExperimentType.BASELINE_COMPARISON: self._baseline_comparison,
            ExperimentType.ROLLING_VALIDATION_CHALLENGE: self._rolling_validation,
            ExperimentType.PEAK_STABILITY_CHALLENGE: self._peak_stability,
        }

    def execute(self, spec: ExperimentSpec, context: dict[str, Any], *, run_id: str) -> ToolResult:
        started = utc_now()
        inputs = {key: context.get(key) for key in spec.required_inputs}
        try:
            outputs, metrics, warnings = self._executors[spec.experiment_type](context, spec.parameters)
            status, errors = ToolStatus.SUCCEEDED, []
        except Exception as exc:  # Failure is data, not a pass.
            outputs, metrics, warnings, status, errors = {}, {}, [], ToolStatus.FAILED, [f"{type(exc).__name__}: {exc}"]
        finished = utc_now()
        output_hash = canonical_hash({"outputs": outputs, "metrics": metrics, "status": status.value})
        return ToolResult(
            tool_result_id=f"TR-{run_id}-{spec.experiment_type.value}", experiment_id=spec.experiment_id,
            executor=spec.executor, status=status, started_at=started, finished_at=finished,
            inputs=inputs, parameters=spec.parameters, outputs=outputs, metrics=metrics,
            artifacts=[], warnings=warnings, errors=errors, run_id=run_id,
            input_hash=canonical_hash(inputs), output_hash=output_hash,
        )

    @staticmethod
    def _arrays(context: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
        actual = np.asarray(context["actual_load"], dtype=float)
        predicted = np.asarray(context["predicted_load"], dtype=float)
        if actual.ndim != 1 or predicted.ndim != 1 or actual.size < 24 or actual.shape != predicted.shape:
            raise ValueError("actual_load and predicted_load must be equal one-dimensional arrays of at least 24 periods")
        return actual, predicted

    def _time_split_audit(self, context: dict[str, Any], _: dict[str, Any]) -> tuple[dict[str, Any], dict[str, float], list[str]]:
        actual, _ = self._arrays(context)
        panel = panel_diagnostics(actual.reshape(1, -1), holdout_periods=min(24, actual.size // 3))
        chronological = context.get("split_strategy") == "chronological"
        return {"split_strategy": context.get("split_strategy"), "chronological": chronological, "panel_diagnostics": panel}, {"chronological_split": float(chronological)}, []

    def _leakage_challenge(self, context: dict[str, Any], _: dict[str, Any]) -> tuple[dict[str, Any], dict[str, float], list[str]]:
        actual, predicted = self._arrays(context)
        offsets = [int(value) for value in context.get("feature_origin_offsets", [])]
        future_offsets = [value for value in offsets if value > 0]
        scores = regression_scores(actual[:, None], predicted[:, None])
        mape = mean_absolute_percentage_error(actual, predicted)
        suspicious_accuracy = scores["mean_mae"] < max(float(np.std(actual)) * 0.01, 0.05)
        return {"future_feature_offsets": future_offsets, "scores": scores, "mape": mape, "suspicious_accuracy": suspicious_accuracy}, {"future_feature_count": float(len(future_offsets)), "mean_mae": scores["mean_mae"], "mape": mape}, []

    def _high_load_subset(self, context: dict[str, Any], parameters: dict[str, Any]) -> tuple[dict[str, Any], dict[str, float], list[str]]:
        actual, predicted = self._arrays(context)
        threshold = float(np.quantile(actual, float(parameters.get("high_load_quantile", 0.8))))
        subset = actual >= threshold
        overall = regression_scores(actual[:, None], predicted[:, None])
        high = regression_scores(actual[subset, None], predicted[subset, None])
        ratio = high["mean_mae"] / max(overall["mean_mae"], 1e-12)
        return {"high_load_threshold": threshold, "high_load_count": int(np.sum(subset)), "overall": overall, "high_load": high}, {"overall_mae": overall["mean_mae"], "high_load_mae": high["mean_mae"], "high_to_overall_mae_ratio": ratio}, []

    def _baseline_comparison(self, context: dict[str, Any], _: dict[str, Any]) -> tuple[dict[str, Any], dict[str, float], list[str]]:
        actual, predicted = self._arrays(context)
        baseline = np.concatenate(([actual[0]], actual[:-1]))
        model_scores = regression_scores(actual[1:, None], predicted[1:, None])
        baseline_scores = regression_scores(actual[1:, None], baseline[1:, None])
        improvement = baseline_scores["mean_mae"] - model_scores["mean_mae"]
        return {"model": model_scores, "persistence_baseline": baseline_scores}, {"model_mae": model_scores["mean_mae"], "baseline_mae": baseline_scores["mean_mae"], "mae_improvement": improvement}, []

    @staticmethod
    def _stability(values: Any, label: str) -> tuple[dict[str, Any], dict[str, float], list[str]]:
        errors = np.asarray(values, dtype=float)
        if errors.ndim != 1 or errors.size < 3 or np.any(errors <= 0):
            raise ValueError(f"{label} must contain at least three positive fold errors")
        ratio = float(np.max(errors) / max(np.mean(errors), 1e-12))
        return {"fold_errors": errors.tolist()}, {"stability_ratio": ratio, "mean_fold_error": float(np.mean(errors))}, []

    def _rolling_validation(self, context: dict[str, Any], _: dict[str, Any]) -> tuple[dict[str, Any], dict[str, float], list[str]]:
        return self._stability(context.get("rolling_fold_errors", []), "rolling_fold_errors")

    def _peak_stability(self, context: dict[str, Any], _: dict[str, Any]) -> tuple[dict[str, Any], dict[str, float], list[str]]:
        return self._stability(context.get("rolling_peak_errors", []), "rolling_peak_errors")
