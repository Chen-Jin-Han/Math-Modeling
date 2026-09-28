"""Controlled synthetic campus-load cases for P0 mechanism evaluation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

import numpy as np

from nova_core.enums import ExperimentType, GateDecisionValue

from .cases import EvaluationCase, GroundTruth

FAULT_FAMILIES = (
    "TIME_SPLIT",
    "FEATURE_LEAKAGE",
    "PEAK_FAILURE",
    "BASELINE_FAILURE",
    "MULTI_FAULT",
    "CLEAN",
    "BORDERLINE",
)


def _campus_series(seed: int, periods: int = 96) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    hours = np.arange(periods)
    temperature = 18 + 7 * np.sin((hours - 5) * 2 * np.pi / 24) + rng.normal(0, 0.7, periods)
    calendar = ((hours // 24) % 7 < 5).astype(int)
    daily = 13 * np.sin((hours - 7) * 2 * np.pi / 24)
    weekly = 5 * calendar
    peak_events = (np.sin(hours * 2 * np.pi / 12) > 0.92).astype(float) * 6
    load = 62 + daily + weekly + 0.75 * temperature + peak_events + rng.normal(0, 0.55, periods)
    lag = np.concatenate(([load[0]], load[:-1]))
    clean_prediction = load + rng.normal(0, 0.7, periods)
    return load, temperature, calendar, lag, clean_prediction


def _truth(fault_type: str, *, expected: GateDecisionValue, oracle: Iterable[ExperimentType], **parameters: object) -> GroundTruth:
    faults = (fault_type,) if fault_type != "MULTI_FAULT" else ("FEATURE_LEAKAGE", "BASELINE_FAILURE")
    return GroundTruth(fault_type, faults, expected, tuple(oracle), dict(parameters))


def generate_case(case_id: str, partition: str, seed: int, fault_type: str, *, challenge: bool = False) -> EvaluationCase:
    """Generate one case.  The opaque id is unrelated to its fault family."""
    if fault_type not in FAULT_FAMILIES:
        raise ValueError(f"Unsupported fault family: {fault_type}")
    load, temperature, calendar, lag, predicted = _campus_series(seed)
    rng = np.random.default_rng(seed + 100_003)
    split_strategy, offsets, watch = "chronological", (0, -1, -24), False
    expected, oracle, parameters = GateDecisionValue.READY_FOR_REVIEW, (ExperimentType.BASELINE_COMPARISON,), {}
    if fault_type == "TIME_SPLIT":
        split_strategy = "random"
        expected, oracle = GateDecisionValue.BLOCKED, (ExperimentType.TIME_SPLIT_AUDIT,)
        parameters = {"split_strategy": split_strategy}
    elif fault_type == "FEATURE_LEAKAGE":
        offsets, predicted = (0, -1, 1), load + rng.normal(0, 0.03, len(load))
        expected, oracle = GateDecisionValue.BLOCKED, (ExperimentType.LEAKAGE_CHALLENGE,)
        parameters = {"positive_offset_count": 1}
    elif fault_type == "PEAK_FAILURE":
        watch = True
        peak = load >= np.quantile(load, 0.8)
        magnitude = 10.0 + (seed % 5) * 0.9
        predicted[peak] -= magnitude
        expected, oracle = GateDecisionValue.BLOCKED, (ExperimentType.HIGH_LOAD_SUBSET_EVALUATION,)
        parameters = {"peak_error_shift": magnitude}
    elif fault_type == "BASELINE_FAILURE":
        predicted = lag + rng.normal(0, 0.15, len(load))
        expected, oracle = GateDecisionValue.BLOCKED, (ExperimentType.BASELINE_COMPARISON,)
        parameters = {"causal_baseline_margin": "non-positive"}
    elif fault_type == "MULTI_FAULT":
        offsets, predicted = (0, -1, 2), lag + rng.normal(0, 0.1, len(load))
        expected, oracle = GateDecisionValue.BLOCKED, (ExperimentType.LEAKAGE_CHALLENGE, ExperimentType.BASELINE_COMPARISON)
        parameters = {"positive_offset_count": 1, "causal_baseline_margin": "non-positive"}
    elif fault_type == "BORDERLINE":
        watch = True
        peak = load >= np.quantile(load, 0.8)
        # Alternate either side of the published 1.75 ratio; no Core rule is changed.
        magnitude = 3.8 if seed % 2 else 4.5
        predicted[peak] -= magnitude
        expected = GateDecisionValue.BLOCKED if magnitude > 4.0 else GateDecisionValue.READY_FOR_REVIEW
        oracle = (ExperimentType.HIGH_LOAD_SUBSET_EVALUATION,)
        parameters = {"peak_error_shift": magnitude, "boundary_side": "above" if expected.value == "BLOCKED" else "below"}
    if challenge:
        predicted = predicted + rng.normal(0, 0.65, len(load))
        parameters = {**parameters, "challenge_noise": 0.65}
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    timestamps = tuple((start + timedelta(hours=int(hour))).isoformat() for hour in range(len(load)))
    truth = _truth(fault_type, expected=expected, oracle=oracle, **parameters)
    return EvaluationCase(
        case_id=case_id, partition=partition, seed=seed, timestamp=timestamps,
        load=tuple(float(value) for value in load), temperature=tuple(float(value) for value in temperature),
        calendar_features=tuple(int(value) for value in calendar), lag_features=tuple(float(value) for value in lag),
        prediction=tuple(float(value) for value in predicted), split_strategy=split_strategy,
        feature_origin_offsets=tuple(offsets), high_load_watch=watch, ground_truth=truth,
    )


def generate_suite(seed: int = 20260810, *, cases_per_family: int = 12, include_partitions: tuple[str, ...] = ("hidden",)) -> list[EvaluationCase]:
    """Generate deterministic dev, calibration, hidden, or challenge partitions.

    Twelve cases per family create 84 independent hidden cases by default.
    """
    counts = {"dev": 2, "calibration": 3, "hidden": cases_per_family, "challenge": 3}
    result: list[EvaluationCase] = []
    cursor = 1
    for partition in include_partitions:
        if partition not in counts:
            raise ValueError(f"Unknown partition: {partition}")
        for family_index, fault_type in enumerate(FAULT_FAMILIES):
            for offset in range(counts[partition]):
                case_seed = seed + family_index * 10_000 + offset * 101 + {"dev": 1, "calibration": 2, "hidden": 3, "challenge": 4}[partition]
                case_id = f"CASE-{partition[0].upper()}-{cursor:04d}"
                result.append(generate_case(case_id, partition, case_seed, fault_type, challenge=partition == "challenge"))
                cursor += 1
    return result
