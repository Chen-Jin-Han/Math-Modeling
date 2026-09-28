"""插值拟合测试"""
import numpy as np
from algorithms.interpolation import (
    lagrange_interp,
    newton_interp,
    cubic_spline_interp,
)


class TestLagrangeInterpolation:
    """Lagrange 插值测试"""

    def test_exact_at_nodes(self):
        x = np.array([0, 1, 2, 3], dtype=float)
        y = np.array([1, 4, 9, 16], dtype=float)
        for xi, yi in zip(x, y):
            result = lagrange_interp(x, y, xi)
            assert abs(result - yi) < 1e-10

    def test_polynomial_recovery(self):
        x = np.array([0, 1, 2], dtype=float)
        y = x**2 + 2*x + 1
        result = lagrange_interp(x, y, 0.5)
        expected = 0.25 + 1 + 1
        assert abs(result - expected) < 1e-10

    def test_linear_data(self):
        x = np.array([0, 1], dtype=float)
        y = np.array([0, 2], dtype=float)
        result = lagrange_interp(x, y, 0.5)
        assert abs(result - 1.0) < 1e-10

    def test_constant_data(self):
        x = np.array([0, 1, 2], dtype=float)
        y = np.array([5, 5, 5], dtype=float)
        result = lagrange_interp(x, y, 1.5)
        assert abs(result - 5.0) < 1e-10

    def test_many_nodes(self):
        x = np.linspace(0, 1, 10)
        y = np.sin(x)
        result = lagrange_interp(x, y, 0.5)
        assert abs(result - np.sin(0.5)) < 0.01


class TestNewtonInterpolation:
    """Newton 插值测试"""

    def test_exact_at_nodes(self):
        x = np.array([0, 1, 2, 3], dtype=float)
        y = np.array([1, 4, 9, 16], dtype=float)
        for xi, yi in zip(x, y):
            result = newton_interp(x, y, xi)
            assert abs(result - yi) < 1e-10

    def test_quadratic(self):
        x = np.array([0, 1, 2], dtype=float)
        y = np.array([1, 2, 5], dtype=float)  # x^2 + 1
        result = newton_interp(x, y, 1.5)
        expected = 1.5**2 + 1  # 3.25
        assert abs(result - expected) < 1e-10

    def test_matches_lagrange(self):
        x = np.array([0, 1, 2, 3], dtype=float)
        y = np.array([1, 4, 9, 16], dtype=float)
        x_test = 1.5
        r1 = lagrange_interp(x, y, x_test)
        r2 = newton_interp(x, y, x_test)
        assert abs(r1 - r2) < 1e-10

    def test_two_nodes(self):
        x = np.array([0, 1], dtype=float)
        y = np.array([3, 7], dtype=float)
        result = newton_interp(x, y, 0.5)
        assert abs(result - 5.0) < 1e-10

    def test_return_scalar(self):
        x = np.array([0, 1, 2], dtype=float)
        y = np.array([0, 1, 4], dtype=float)
        result = newton_interp(x, y, 1.0)
        assert isinstance(result, (float, np.floating))


class TestCubicSpline:
    """样条插值测试"""

    def test_smoothness(self):
        x = np.array([0, 1, 2, 3, 4], dtype=float)
        y = np.array([0, 1, 0, 1, 0], dtype=float)
        x_new = np.linspace(0, 4, 100)
        result = cubic_spline_interp(x, y, x_new)
        assert len(result) == 100

    def test_exact_at_nodes(self):
        x = np.array([0, 1, 2, 3], dtype=float)
        y = np.array([1, 3, 2, 4], dtype=float)
        result = cubic_spline_interp(x, y, x)
        np.testing.assert_allclose(result, y, atol=1e-10)

    def test_interpolation_shape(self):
        x = np.array([0, 1, 2], dtype=float)
        y = np.array([0, 1, 0], dtype=float)
        x_new = np.linspace(0, 2, 50)
        result = cubic_spline_interp(x, y, x_new)
        assert len(result) == 50

    def test_constant_data(self):
        x = np.array([0, 1, 2, 3], dtype=float)
        y = np.array([5, 5, 5, 5], dtype=float)
        x_new = np.array([0.5, 1.5, 2.5])
        result = cubic_spline_interp(x, y, x_new)
        np.testing.assert_allclose(result, [5, 5, 5], atol=1e-10)

    def test_monotone_data(self):
        x = np.array([0, 1, 2, 3], dtype=float)
        y = np.array([0, 1, 2, 3], dtype=float)
        x_new = np.array([0.5, 1.5, 2.5])
        result = cubic_spline_interp(x, y, x_new)
        # 应单调递增
        assert result[0] < result[1] < result[2]
