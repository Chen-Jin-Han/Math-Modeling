import numpy as np

from algorithms.time_series import (
    double_exponential_smoothing,
    simple_moving_average,
    single_exponential_smoothing,
    weighted_moving_average,
)


def test_simple_moving_average_alignment():
    result = simple_moving_average([1, 2, 3, 4, 5], window=3)
    assert np.isnan(result[:2]).all()
    assert np.allclose(result[2:], [2, 3, 4])


def test_weighted_moving_average_uses_recent_weights():
    result = weighted_moving_average([1, 2, 3, 4], weights=[1, 2, 3])
    assert np.isnan(result[:2]).all()
    assert np.isclose(result[2], 14 / 6)
    assert np.isclose(result[3], 20 / 6)


def test_single_exponential_smoothing_constant_series():
    result = single_exponential_smoothing([5, 5, 5], alpha=0.4, forecast_periods=2)
    assert np.allclose(result["smoothed"], [5, 5, 5])
    assert np.allclose(result["forecast"], [5, 5])


def test_double_exponential_smoothing_linear_forecast():
    result = double_exponential_smoothing(
        [1, 2, 3, 4, 5], alpha=1.0, beta=1.0, forecast_periods=2
    )
    assert np.allclose(result["forecast"], [6, 7])
