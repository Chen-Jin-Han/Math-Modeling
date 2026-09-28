"""Closed vocabularies for the Nova Core v0.1 diagnosis protocol."""

from enum import Enum


class ClaimStatus(str, Enum):
    PROPOSED = "PROPOSED"
    UNDER_DIAGNOSIS = "UNDER_DIAGNOSIS"
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GapStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    BLOCKED = "BLOCKED"


class ToolStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class EvidenceDirection(str, Enum):
    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    WEAKENS = "WEAKENS"
    INCONCLUSIVE = "INCONCLUSIVE"


class GateDecisionValue(str, Enum):
    """Normalized values for Rule Pack blocked / needs_review semantics."""

    BLOCKED = "BLOCKED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"


class ExperimentType(str, Enum):
    TIME_SPLIT_AUDIT = "TIME_SPLIT_AUDIT"
    LEAKAGE_CHALLENGE = "LEAKAGE_CHALLENGE"
    HIGH_LOAD_SUBSET_EVALUATION = "HIGH_LOAD_SUBSET_EVALUATION"
    BASELINE_COMPARISON = "BASELINE_COMPARISON"
    ROLLING_VALIDATION_CHALLENGE = "ROLLING_VALIDATION_CHALLENGE"
    PEAK_STABILITY_CHALLENGE = "PEAK_STABILITY_CHALLENGE"
