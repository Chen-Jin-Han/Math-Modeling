"""Evaluator-only case and ground-truth models.

This module is intentionally outside :mod:`nova_core`.  Only ``core_input`` is
ever supplied to the production service or its selection and gate components.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nova_core.enums import ExperimentType, GateDecisionValue
from nova_core.service import CampusLoadInput


@dataclass(frozen=True)
class GroundTruth:
    """Private evaluator oracle; never part of a production input."""

    fault_type: str
    faults: tuple[str, ...]
    expected_gate: GateDecisionValue
    acceptable_first_experiments: tuple[ExperimentType, ...]
    fault_parameters: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "fault_type": self.fault_type,
            "faults": list(self.faults),
            "expected_gate": self.expected_gate.value,
            "acceptable_first_experiments": [item.value for item in self.acceptable_first_experiments],
            "fault_parameters": self.fault_parameters,
        }


@dataclass(frozen=True)
class EvaluationCase:
    """A neutral-id case with contextual input separated from evaluator truth."""

    case_id: str
    partition: str
    seed: int
    timestamp: tuple[str, ...]
    load: tuple[float, ...]
    temperature: tuple[float, ...]
    calendar_features: tuple[int, ...]
    lag_features: tuple[float, ...]
    prediction: tuple[float, ...]
    split_strategy: str
    feature_origin_offsets: tuple[int, ...]
    high_load_watch: bool
    ground_truth: GroundTruth
    rolling_fold_errors: tuple[float, ...] = ()
    rolling_peak_errors: tuple[float, ...] = ()

    def core_input(self) -> CampusLoadInput:
        """Return the only object that may cross the evaluation/production boundary."""
        return CampusLoadInput(
            actual_load=list(self.load),
            predicted_load=list(self.prediction),
            split_strategy=self.split_strategy,
            feature_origin_offsets=list(self.feature_origin_offsets),
            high_load_watch=self.high_load_watch,
            rolling_fold_errors=list(self.rolling_fold_errors),
            rolling_peak_errors=list(self.rolling_peak_errors),
            decision_contract={"case_reference": self.case_id, "horizon_hours": 24, "mode": "P0_EVALUATION"},
        )

    def manifest_record(self) -> dict[str, Any]:
        """Private evaluation manifest record, including the oracle by design."""
        return {
            "case_id": self.case_id,
            "partition": self.partition,
            "seed": self.seed,
            "input_summary": {
                "period_count": len(self.load),
                "split_strategy": self.split_strategy,
                "feature_origin_offsets": list(self.feature_origin_offsets),
                "high_load_watch": self.high_load_watch,
                "rolling_fold_errors": list(self.rolling_fold_errors),
                "rolling_peak_errors": list(self.rolling_peak_errors),
            },
            "ground_truth": self.ground_truth.to_dict(),
        }
