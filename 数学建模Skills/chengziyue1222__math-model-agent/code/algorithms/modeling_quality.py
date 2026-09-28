"""Reusable quality checks for dynamic, comparative, and multi-objective models."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import numpy as np


def validate_state_balance(
    initial_state: float,
    inflows: Sequence[float],
    outflows: Sequence[float],
    *,
    observed_end_states: Sequence[float] | None = None,
    lower_bound: float | None = None,
    atol: float = 1e-8,
) -> dict[str, Any]:
    """Reconstruct a one-dimensional state balance and audit residuals/floors."""
    incoming = np.asarray(inflows, dtype=float)
    outgoing = np.asarray(outflows, dtype=float)
    if incoming.ndim != 1 or outgoing.ndim != 1 or incoming.shape != outgoing.shape:
        raise ValueError("inflows and outflows must be finite one-dimensional arrays of equal length")
    if not np.isfinite(initial_state) or not np.isfinite(incoming).all() or not np.isfinite(outgoing).all():
        raise ValueError("state-balance inputs must be finite")
    if atol < 0:
        raise ValueError("atol must be non-negative")

    starts = np.empty(incoming.size, dtype=float)
    ends = np.empty(incoming.size, dtype=float)
    state = float(initial_state)
    for index, (inflow, outflow) in enumerate(zip(incoming, outgoing, strict=True)):
        starts[index] = state
        state = state + float(inflow) - float(outflow)
        ends[index] = state

    residuals = np.zeros_like(ends)
    if observed_end_states is not None:
        observed = np.asarray(observed_end_states, dtype=float)
        if observed.shape != ends.shape or not np.isfinite(observed).all():
            raise ValueError("observed_end_states must be finite and match the reconstructed horizon")
        residuals = observed - ends

    minimum = float(np.min(ends)) if ends.size else float(initial_state)
    floor_passed = lower_bound is None or minimum >= float(lower_bound) - atol
    balance_passed = bool(np.max(np.abs(residuals), initial=0.0) <= atol)
    return {
        "periods": int(ends.size),
        "initial_state": float(initial_state),
        "start_states": starts.tolist(),
        "end_states": ends.tolist(),
        "residuals": residuals.tolist(),
        "max_abs_residual": float(np.max(np.abs(residuals), initial=0.0)),
        "minimum_end_state": minimum,
        "lower_bound": None if lower_bound is None else float(lower_bound),
        "balance_passed": balance_passed,
        "floor_passed": bool(floor_passed),
        "passed": bool(balance_passed and floor_passed),
    }


def service_level_metrics(achieved: Sequence[float], target: Sequence[float] | float) -> dict[str, Any]:
    """Summarize per-period target attainment without hiding the worst periods."""
    actual = np.asarray(achieved, dtype=float)
    targets = np.asarray(target, dtype=float)
    if targets.ndim == 0:
        targets = np.full(actual.shape, float(targets))
    if actual.ndim != 1 or targets.shape != actual.shape:
        raise ValueError("achieved and target must resolve to equal one-dimensional arrays")
    if not np.isfinite(actual).all() or not np.isfinite(targets).all() or np.any(targets <= 0):
        raise ValueError("service-level inputs must be finite and targets must be positive")
    ratios = actual / targets
    return {
        "periods": int(ratios.size),
        "mean_service_level": float(np.mean(ratios)) if ratios.size else 0.0,
        "minimum_service_level": float(np.min(ratios)) if ratios.size else 0.0,
        "q05_service_level": float(np.quantile(ratios, 0.05)) if ratios.size else 0.0,
        "target_attainment_rate": float(np.mean(ratios >= 1.0)) if ratios.size else 0.0,
        "service_levels": ratios.tolist(),
    }


def compare_policy_metrics(
    baseline: Mapping[str, float],
    candidate: Mapping[str, float],
    *,
    shared_inputs: bool,
    lower_is_better: Iterable[str] = (),
) -> dict[str, Any]:
    """Compare policies only when metrics share a declared experimental basis."""
    if not shared_inputs:
        raise ValueError("policy comparison requires shared inputs and evaluation conditions")
    common = sorted(set(baseline) & set(candidate))
    if not common:
        raise ValueError("baseline and candidate have no common metrics")
    lower = set(lower_is_better)
    metrics: dict[str, Any] = {}
    for name in common:
        base, cand = float(baseline[name]), float(candidate[name])
        if not np.isfinite(base) or not np.isfinite(cand):
            raise ValueError(f"policy metric {name!r} must be finite")
        delta = cand - base
        relative = None if abs(base) < 1e-15 else delta / abs(base)
        improved = delta < 0 if name in lower else delta > 0
        metrics[name] = {
            "baseline": base,
            "candidate": cand,
            "delta": delta,
            "relative_delta": relative,
            "direction": "min" if name in lower else "max",
            "improved": bool(improved),
        }
    return {"shared_inputs": True, "metrics": metrics}


def lexicographic_order(
    records: Sequence[Mapping[str, Any]],
    objectives: Sequence[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Return records with deterministic ranks under declared lexicographic objectives."""
    if not objectives:
        raise ValueError("at least one lexicographic objective is required")
    for _, direction in objectives:
        if direction not in {"min", "max"}:
            raise ValueError("objective direction must be 'min' or 'max'")

    def key(item: Mapping[str, Any]) -> tuple[float, ...]:
        values: list[float] = []
        for name, direction in objectives:
            value = float(item[name])
            if not np.isfinite(value):
                raise ValueError(f"objective {name!r} must be finite")
            values.append(value if direction == "min" else -value)
        return tuple(values)

    ordered = sorted((dict(record) for record in records), key=key)
    return [{**record, "lexicographic_rank": rank} for rank, record in enumerate(ordered, start=1)]
