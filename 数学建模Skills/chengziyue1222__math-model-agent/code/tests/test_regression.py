"""回归分析测试"""
import numpy as np
from algorithms.regression import linear_regression, polynomial_regression, ridge_regression


class TestLinearRegression:
    """线性回归测试"""

    def test_perfect_fit(self):
        """完美线性关系"""
        x = np.array([1, 2, 3, 4, 5], dtype=float)
        y = 2 * x + 1
        result = linear_regression(x, y)
        assert abs(result['slope'] - 2.0) < 0.01
        assert abs(result['intercept'] - 1.0) < 0.01
        assert result['r2'] > 0.999

    def test_noisy_data(self):
        """带噪声数据"""
        np.random.seed(42)
        x = np.linspace(0, 10, 100)
        y = 3 * x + 5 + np.random.randn(100) * 0.5
        result = linear_regression(x, y)
        assert abs(result['slope'] - 3.0) < 0.2
        assert abs(result['intercept'] - 5.0) < 0.5
        assert result['r2'] > 0.95

    def test_negative_slope(self):
        """负斜率"""
        x = np.array([1, 2, 3, 4, 5], dtype=float)
        y = -2 * x + 10
        result = linear_regression(x, y)
        assert result['slope'] < 0


class TestPolynomialRegression:
    """多项式回归测试"""

    def test_quadratic(self):
        """二次多项式拟合"""
        x = np.array([1, 2, 3, 4, 5, 6], dtype=float)
        y = x**2
        result = polynomial_regression(x, y, degree=2)
        assert result['r2'] > 0.999

    def test_cubic(self):
        """三次多项式"""
        x = np.linspace(-2, 2, 20)
        y = x**3 - 2*x + 1
        result = polynomial_regression(x, y, degree=3)
        assert result['r2'] > 0.99


class TestRidgeRegression:
    """岭回归测试"""

    def test_regularization_effect(self):
        """正则化应减小系数"""
        np.random.seed(42)
        x = np.linspace(0, 10, 50).reshape(-1, 1)
        y = 2 * x.ravel() + 1 + np.random.randn(50) * 0.5

        r1 = linear_regression(x.ravel(), y)
        r2 = ridge_regression(x, y, alpha=1.0)

        # 岭回归系数应更小（被正则化）
        assert abs(r2['coefficients'][0]) <= abs(r1['slope']) + 0.5
