from __future__ import annotations

import pytest

from algorithms.modeling_quality import (
    compare_policy_metrics,
    lexicographic_order,
    service_level_metrics,
    validate_state_balance,
)


def test_state_balance_detects_floor_and_observation_residual() -> None:
    result = validate_state_balance(
        10,
        [4, 1],
        [3, 8],
        observed_end_states=[11, 5],
        lower_bound=4,
    )
    assert result["end_states"] == [11.0, 4.0]
    assert result["balance_passed"] is False
    assert result["floor_passed"] is True
    assert result["passed"] is False


def test_service_metrics_expose_worst_period_and_attainment_rate() -> None:
    result = service_level_metrics([100, 50, 120], 100)
    assert result["mean_service_level"] == pytest.approx(0.9)
    assert result["minimum_service_level"] == pytest.approx(0.5)
    assert result["target_attainment_rate"] == pytest.approx(2 / 3)


def test_policy_comparison_requires_shared_evaluation_inputs() -> None:
    with pytest.raises(ValueError, match="shared inputs"):
        compare_policy_metrics({"cost": 5}, {"cost": 4}, shared_inputs=False)
    result = compare_policy_metrics(
        {"cost": 5, "service": 0.8},
        {"cost": 4, "service": 0.9},
        shared_inputs=True,
        lower_is_better={"cost"},
    )
    assert result["metrics"]["cost"]["improved"] is True
    assert result["metrics"]["service"]["improved"] is True


def test_lexicographic_order_respects_declared_priority() -> None:
    ranked = lexicographic_order(
        [{"name": "a", "risk": 2, "cost": 1}, {"name": "b", "risk": 1, "cost": 8}],
        [("risk", "min"), ("cost", "min")],
    )
    assert [item["name"] for item in ranked] == ["b", "a"]
    assert [item["lexicographic_rank"] for item in ranked] == [1, 2]
