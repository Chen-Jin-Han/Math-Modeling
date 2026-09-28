"""模糊数学测试"""
import numpy as np
import pytest
from algorithms.fuzzy_math import (
    gaussmf,
    trimf,
    trapmf,
    fuzzy_comprehensive_evaluation,
)


class TestMembershipFunctions:
    """隶属函数测试"""

    def test_gauss_peak_at_center(self):
        x = np.linspace(-5, 5, 100)
        y = gaussmf(x, 0, 1)
        assert y[50] == pytest.approx(1.0, abs=0.01)

    def test_triangle_peak(self):
        x = np.array([0, 1, 2, 3, 4], dtype=float)
        y = trimf(x, [0, 1, 2])
        assert y[1] == pytest.approx(1.0, abs=0.01)

    def test_trapezoid_flat_top(self):
        x = np.array([0, 1, 2, 3, 4, 5], dtype=float)
        y = trapmf(x, [1, 2, 3, 4])
        assert y[2] == pytest.approx(1.0, abs=0.01)
        assert y[3] == pytest.approx(1.0, abs=0.01)

    def test_boundary_zero(self):
        x = np.array([-10, 10], dtype=float)
        y = gaussmf(x, 0, 1)
        assert y[0] < 0.01
        assert y[1] < 0.01

    def test_membership_range(self):
        x = np.linspace(-10, 10, 1000)
        y = gaussmf(x, 0, 2)
        assert np.all(y >= 0)
        assert np.all(y <= 1)


class TestFuzzyComprehensiveEvaluation:
    """模糊综合评价测试"""

    def test_basic_evaluation(self):
        R = np.array([
            [0.7, 0.3],
            [0.6, 0.4],
            [0.8, 0.2],
        ])
        weights = np.array([0.5, 0.3, 0.2])
        result = fuzzy_comprehensive_evaluation(R, weights)
        assert len(result) == 2  # 2个等级

    def test_single_factor(self):
        R = np.array([[0.6, 0.4]])
        weights = np.array([1.0])
        result = fuzzy_comprehensive_evaluation(R, weights)
        np.testing.assert_allclose(result, [0.6, 0.4], atol=0.01)

    def test_result_sums_to_one(self):
        R = np.array([[0.3, 0.7], [0.5, 0.5], [0.2, 0.8]])
        weights = np.array([0.4, 0.3, 0.3])
        result = fuzzy_comprehensive_evaluation(R, weights)
        assert abs(sum(result) - 1.0) < 0.01

    def test_equal_weights(self):
        R = np.array([[0.5, 0.5], [0.5, 0.5]])
        weights = np.array([0.5, 0.5])
        result = fuzzy_comprehensive_evaluation(R, weights)
        np.testing.assert_allclose(result, [0.5, 0.5], atol=0.01)

    def test_dominant_factor(self):
        """权重集中在第一个因素"""
        R = np.array([[1.0, 0.0], [0.0, 1.0]])
        weights = np.array([0.99, 0.01])
        result = fuzzy_comprehensive_evaluation(R, weights)
        assert result[0] > result[1]
