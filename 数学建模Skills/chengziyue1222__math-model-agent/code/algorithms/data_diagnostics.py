"""Reusable diagnostics for entity-by-time modeling data."""

from __future__ import annotations

from typing import Any

import numpy as np


def panel_diagnostics(values: Any, *, holdout_periods: int = 24) -> dict[str, Any]:
    """Quantify sparsity, dependence, serial structure, and a time-ordered holdout slice."""
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] < 1 or matrix.shape[1] < 2:
        raise ValueError("panel values must be a non-empty entity-by-time matrix")
    if not np.isfinite(matrix).all():
        raise ValueError("panel values must be finite")
    if holdout_periods < 1 or holdout_periods >= matrix.shape[1]:
        raise ValueError("holdout_periods must leave at least one training period")

    lag_correlations = []
    for row in matrix:
        left, right = row[:-1], row[1:]
        if np.std(left) > 0 and np.std(right) > 0:
            lag_correlations.append(float(np.corrcoef(left, right)[0, 1]))

    active = matrix[np.any(matrix != 0, axis=1)]
    cross_dependence = 0.0
    if active.shape[0] > 1:
        corr = np.corrcoef(active)
        upper = np.abs(corr[np.triu_indices_from(corr, k=1)])
        finite = upper[np.isfinite(upper)]
        cross_dependence = float(np.mean(finite)) if finite.size else 0.0

    train, holdout = matrix[:, :-holdout_periods], matrix[:, -holdout_periods:]
    return {
        "entities": int(matrix.shape[0]),
        "periods": int(matrix.shape[1]),
        "zero_fraction": float(np.mean(matrix == 0)),
        "active_entity_fraction": float(np.mean(np.any(matrix != 0, axis=1))),
        "median_lag1_autocorrelation": float(np.median(lag_correlations)) if lag_correlations else None,
        "mean_absolute_cross_entity_correlation": cross_dependence,
        "holdout": {
            "periods": int(holdout_periods),
            "train_zero_fraction": float(np.mean(train == 0)),
            "holdout_zero_fraction": float(np.mean(holdout == 0)),
            "train_mean": float(np.mean(train)),
            "holdout_mean": float(np.mean(holdout)),
        },
    }
