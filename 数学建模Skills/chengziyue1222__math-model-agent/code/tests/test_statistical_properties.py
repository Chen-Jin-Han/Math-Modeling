"""Properties and reference comparisons for forecasting and statistical models."""

import numpy as np
import pytest
from scipy.special import expit

from algorithms.fuzzy_math import (
    fuzzy_cmeans,
    fuzzy_comprehensive_evaluation,
    fuzzy_pattern_recognition,
    multi_level_fuzzy_evaluation,
)
from algorithms.grey_system import (
    gm21_predict,
    grey_auto_predict,
    grey_clustering,
    verhulst_predict,
)
from algorithms.regression import (
    linear_regression,
    logistic_regression,
    nonlinear_regression,
    ridge_regression,
    stepwise_regression,
)
from algorithms.time_series import (
    adaptive_filter,
    gompertz_curve,
    logistic_curve,
    modified_exponential_curve,
    trend_moving_average,
    triple_exponential_smoothing,
    weighted_moving_average,
)


def test_linear_and_ridge_regression_match_closed_form_properties():
    rng = np.random.default_rng(42)
    x = rng.normal(size=(80, 3))
    y = 1.5 + x @ np.array([2.0, -3.0, 0.5])
    ordinary = linear_regression(x, y)
    expected = np.linalg.lstsq(np.column_stack((np.ones(len(x)), x)), y, rcond=None)[0]
    np.testing.assert_allclose(ordinary["coefficients"], expected, atol=1e-10)
    assert ordinary["R2"] == pytest.approx(1.0)
    no_intercept = linear_regression(x, x @ np.array([2.0, -3.0, 0.5]), add_intercept=False)
    np.testing.assert_allclose(no_intercept["coefficients"], [2.0, -3.0, 0.5], atol=1e-10)

    x_with_constant = np.column_stack((x[:, 0], np.ones(len(x))))
    ridge = ridge_regression(x_with_constant, y, alpha=2.0)
    assert np.isfinite(ridge["coefficients"]).all()
    assert ridge["R2"] > 0.25


def test_stepwise_selects_signal_and_handles_no_selected_features(capsys):
    rng = np.random.default_rng(3)
    x = rng.normal(size=(120, 3))
    y = 4 * x[:, 0] + rng.normal(scale=0.1, size=120)
    selected = stepwise_regression(x, y, feature_names=["signal", "n1", "n2"])
    assert selected["selected_features"][0] == "signal"
    empty = stepwise_regression(x, np.ones(120), threshold_enter=0.0)
    assert empty["selected_indices"] == []
    assert "逐步回归结果" in capsys.readouterr().out


def test_nonlinear_regression_recovers_parameters_and_prediction():
    x = np.linspace(0, 3, 40)
    model = lambda values, a, b: a * np.exp(b * values)
    y = model(x, 2.5, 0.4)
    result = nonlinear_regression(x, y, model, p0=np.array([2.0, 0.3]), bounds=(0, np.inf))
    np.testing.assert_allclose(result["parameters"], [2.5, 0.4], rtol=1e-5)
    prediction_points = np.array([0.0, 1.0])
    np.testing.assert_allclose(
        result["predict"](prediction_points), model(prediction_points, 2.5, 0.4)
    )
    assert result["R2"] == pytest.approx(1.0)


def test_logistic_regression_probabilities_classes_and_constant_column():
    x1 = np.linspace(-4, 4, 100)
    x = np.column_stack((x1, np.ones_like(x1)))
    y = (expit(2 * x1) >= 0.5).astype(int)
    result = logistic_regression(
        x, y, X_new=np.array([[-3, 1], [3, 1]]), max_iter=3000, lr=0.2
    )
    assert result["accuracy"] > 0.98
    assert result["new_predictions"].tolist() == [0, 1]
    classes, probabilities = result["predict"](np.array([[-2, 1], [2, 1]]))
    assert classes.tolist() == [0, 1]
    assert np.all((probabilities >= 0) & (probabilities <= 1))


def test_trend_moving_average_short_and_linear_series():
    short = trend_moving_average([1, 2, 3], window=3)
    assert np.isnan(short["forecast_next"])
    linear = trend_moving_average(np.arange(1, 15), window=3)
    assert linear["trend"] == pytest.approx(1.0)
    assert linear["forecast_next"] == pytest.approx(15.0)
    default_weights = weighted_moving_average([1, 2, 3, 4])
    assert default_weights[-1] == pytest.approx(20 / 6)


@pytest.mark.parametrize("method", ["additive", "multiplicative"])
def test_holt_winters_preserves_seasonal_forecast(method):
    base = np.array([10.0, 12.0, 14.0, 16.0])
    if method == "additive":
        data = np.tile(base, 5) + np.repeat(np.arange(5), 4)
    else:
        data = np.tile(base, 5) * np.repeat(1 + np.arange(5) * 0.02, 4)
    result = triple_exponential_smoothing(
        data,
        alpha=0.4,
        beta=0.2,
        gamma=0.3,
        season_length=4,
        forecast_periods=4,
        method=method,
    )
    assert result["forecast"].shape == (4,)
    assert np.isfinite(result["forecast"]).all()
    assert np.ptp(result["forecast"]) > 1


def test_growth_curves_recover_noise_free_synthetic_data():
    t = np.linspace(0, 12, 40)
    future = np.array([13.0, 14.0])
    gompertz_y = 90 * np.exp(-2.2 * np.exp(-0.35 * t))
    gompertz = gompertz_curve(t, gompertz_y, future)
    assert gompertz["R2"] > 0.999999
    assert gompertz["y_predict"].shape == (2,)

    logistic_y = 100 / (1 + 8 * np.exp(-0.45 * t))
    logistic = logistic_curve(t, logistic_y, future)
    assert logistic["R2"] > 0.999999
    assert logistic["y_predict"][1] > logistic["y_predict"][0]

    exponential_y = 5 + 2 * np.exp(0.08 * t)
    exponential = modified_exponential_curve(t, exponential_y, future)
    assert exponential["R2"] > 0.999999
    assert exponential["y_predict"].shape == (2,)


def test_adaptive_filter_is_finite_for_signal_and_constant_series():
    signal = np.sin(np.linspace(0, 8, 60)) + np.linspace(0, 1, 60)
    result = adaptive_filter(
        signal, window=5, learning_rate=0.005, n_epochs=20, forecast_periods=3
    )
    assert np.isfinite(result["weights"]).all()
    assert np.isfinite(result["forecast"]).all()
    assert result["mse"] >= 0
    constant = adaptive_filter(np.ones(20) * 7, window=3, n_epochs=2, forecast_periods=2)
    np.testing.assert_allclose(constant["forecast"], [7, 7])


def test_grey_clustering_models_and_auto_selection(capsys):
    data = np.array([[1.0, 1.2], [5.0, 4.5], [9.0, 8.5]])
    thresholds = np.array([[2.0, 2.0], [5.0, 5.0], [8.0, 8.0]])
    labels = grey_clustering(data, thresholds)
    assert labels.tolist() == [0, 1, 2]

    series = np.array([10.0, 12.0, 15.0, 19.0, 24.0, 30.0])
    gm21 = gm21_predict(series, predict_n=2)
    verhulst = verhulst_predict(series, predict_n=2)
    assert len(gm21["predictions"]) == 2
    assert len(verhulst["predictions"]) == 2
    automatic = grey_auto_predict(series, predict_n=2)
    assert automatic["best_model"] in automatic["results"]
    assert automatic["errors"]
    assert "灰色预测模型自动选择" in capsys.readouterr().out


def test_multilevel_fuzzy_evaluation_probability_invariants():
    weights = [np.array([0.6, 0.4]), np.array([0.7, 0.3]), np.array([0.2, 0.8])]
    matrices = [
        np.array([[0.8, 0.2], [0.5, 0.5]]),
        np.array([[0.3, 0.7], [0.1, 0.9]]),
    ]
    result = multi_level_fuzzy_evaluation(weights, matrices, ["good", "bad"])
    assert result["B_final_normalized"].sum() == pytest.approx(1.0)
    assert result["max_grade"] in {"good", "bad"}
    direct = fuzzy_comprehensive_evaluation(
        matrices[0], weights[1], comment_set=["good", "bad"], return_dict=True
    )
    assert direct["max_grade"] == "good"


def test_fuzzy_cmeans_and_pattern_recognition_are_reproducible():
    points = np.array([[0, 0], [0.1, 0], [5, 5], [5.1, 5]], dtype=float)
    np.random.seed(12)
    first = fuzzy_cmeans(points, c=2, max_iter=100)
    np.random.seed(12)
    second = fuzzy_cmeans(points, c=2, max_iter=100)
    np.testing.assert_allclose(first["membership"], second["membership"])
    np.testing.assert_allclose(first["membership"].sum(axis=1), 1.0)
    assert first["J_history"][-1] <= first["J_history"][0]

    samples = np.array([[0.9, 0.1], [0.1, 0.9]])
    patterns = np.array([[1.0, 0.0], [0.0, 1.0]])
    recognition = fuzzy_pattern_recognition(samples, patterns)
    assert recognition["labels"].tolist() == [0, 1]
    assert recognition["closeness"].shape == (2, 2)
