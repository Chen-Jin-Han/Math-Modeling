"""Reusable leakage-safe tools for multivariate process forecasting and alerting."""

from __future__ import annotations

from typing import Any

import numpy as np


def chronological_partitions(n: int, *, horizon: int, history: int, train_fraction: float = 0.6, validation_fraction: float = 0.2) -> dict[str, np.ndarray]:
    """Return non-overlapping forecast-origin indices with a future-label horizon."""
    if n <= history + horizon + 30:
        raise ValueError("series is too short for requested history and horizon")
    origins = np.arange(history, n - horizon)
    train_stop = int(len(origins) * train_fraction)
    validation_stop = int(len(origins) * (train_fraction + validation_fraction))
    return {
        "train": origins[:train_stop],
        "validation": origins[train_stop:validation_stop],
        "test": origins[validation_stop:],
    }


def causal_features(inputs: np.ndarray, outputs: np.ndarray, origins: np.ndarray, *, history: int) -> np.ndarray:
    """Construct features using only values available at each forecast origin."""
    x = np.asarray(inputs, dtype=float)
    y = np.asarray(outputs, dtype=float)
    if x.ndim != 2 or y.ndim != 2 or len(x) != len(y):
        raise ValueError("inputs and outputs must be equal-length two-dimensional arrays")
    rows = []
    for t in np.asarray(origins, dtype=int):
        if t < history or t >= len(x):
            raise ValueError("forecast origin is outside causal feature window")
        x_window = x[t - history + 1 : t + 1]
        y_window = y[t - history + 1 : t + 1]
        slope_x = (x_window[-1] - x_window[0]) / max(history - 1, 1)
        slope_y = (y_window[-1] - y_window[0]) / max(history - 1, 1)
        rows.append(
            np.concatenate(
                [
                    x[t], y[t],
                    x_window.mean(axis=0), x_window.std(axis=0), slope_x,
                    y_window.mean(axis=0), y_window.std(axis=0), slope_y,
                ]
            )
        )
    return np.asarray(rows, dtype=float)


def future_event_targets(outputs: np.ndarray, origins: np.ndarray, thresholds: np.ndarray, *, start: int, end: int) -> tuple[np.ndarray, np.ndarray]:
    """Label whether either pollutant exceeds a threshold and its earliest offset."""
    y = np.asarray(outputs, dtype=float)
    thresholds = np.asarray(thresholds, dtype=float)
    labels, delays = [], []
    for t in np.asarray(origins, dtype=int):
        future = y[t + start : t + end + 1]
        violations = np.any(future > thresholds, axis=1)
        positions = np.flatnonzero(violations)
        labels.append(int(positions.size > 0))
        delays.append(float(start + positions[0]) if positions.size else np.nan)
    return np.asarray(labels, dtype=int), np.asarray(delays, dtype=float)


def regression_scores(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    """Return common deterministic multi-output regression scores."""
    observed, fitted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    error = observed - fitted
    rmse_by_output = np.sqrt(np.mean(error**2, axis=0))
    mae_by_output = np.mean(np.abs(error), axis=0)
    denominator = np.sum((observed - observed.mean(axis=0)) ** 2, axis=0)
    r2_by_output = 1 - np.sum(error**2, axis=0) / np.where(denominator > 1e-12, denominator, np.nan)
    return {
        "rmse_by_output": [float(value) for value in rmse_by_output],
        "mae_by_output": [float(value) for value in mae_by_output],
        "r2_by_output": [float(value) for value in r2_by_output],
        "mean_rmse": float(np.mean(rmse_by_output)),
        "mean_mae": float(np.mean(mae_by_output)),
    }


def bootstrap_interval(values: np.ndarray, *, seed: int, draws: int = 200) -> dict[str, Any]:
    """Bootstrap a mean metric; this quantifies split-sample variability only."""
    sample = np.asarray(values, dtype=float).ravel()
    if sample.size == 0:
        raise ValueError("cannot bootstrap an empty sample")
    generator = np.random.default_rng(seed)
    means = np.array([generator.choice(sample, size=sample.size, replace=True).mean() for _ in range(draws)])
    return {
        "mode": "iid_bootstrap_metric",
        "draws": int(draws),
        "seed": int(seed),
        "mean": float(sample.mean()),
        "ci95": [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))],
        "scenario_source": "chronological held-out forecast origins; IID resampling of their per-origin metric",
        "holdout_or_stress_evidence": "results/bootstrap_metrics.json",
    }
