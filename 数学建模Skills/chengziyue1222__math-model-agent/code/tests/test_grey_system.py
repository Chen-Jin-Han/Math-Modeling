"""灰色系统理论测试"""
import numpy as np
from algorithms.grey_system import gm11_predict, grey_correlation, grey_correlation_rank


class TestGM11:
    """GM(1,1) 灰色预测测试"""

    def test_linear_data(self):
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
        result = gm11_predict(data, predict_count=3)
        assert 'predicted' in result
        assert len(result['predicted']) == 3

    def test_exponential_growth(self):
        data = np.array([10, 11, 12.1, 13.3, 14.6, 16.1], dtype=float)
        result = gm11_predict(data, predict_count=2)
        assert result['predicted'][0] > data[-1]

    def test_return_fields(self):
        data = np.array([1, 2, 3, 4, 5], dtype=float)
        result = gm11_predict(data, predict_count=2)
        assert 'predicted' in result
        assert 'fitted' in result
        assert 'a' in result
        assert 'b' in result

    def test_short_data(self):
        data = np.array([1, 2, 3, 4], dtype=float)
        result = gm11_predict(data, predict_count=1)
        assert len(result['predicted']) == 1

    def test_fitted_close_to_actual(self):
        data = np.array([100, 110, 121, 133, 146], dtype=float)
        result = gm11_predict(data, predict_count=0)
        fitted = result['fitted']
        for i in range(len(data)):
            assert abs(fitted[i] - data[i]) / data[i] < 0.15


class TestGreyCorrelation:
    """灰色关联分析测试"""

    def test_identical_series(self):
        ref = np.array([1, 2, 3, 4, 5], dtype=float)
        comp = np.array([[1, 2, 3, 4, 5]], dtype=float)
        result = grey_correlation(ref, comp)
        assert result[0] > 0.99

    def test_correlated_data(self):
        ref = np.array([1, 2, 3, 4, 5], dtype=float)
        comp = np.array([
            [1.1, 2.1, 3.1, 4.1, 5.1],
            [5, 4, 3, 2, 1],
        ], dtype=float)
        result = grey_correlation(ref, comp)
        assert result[0] > result[1]

    def test_return_type(self):
        ref = np.array([1, 2, 3], dtype=float)
        comp = np.array([[1, 2, 3]], dtype=float)
        result = grey_correlation(ref, comp)
        assert isinstance(result, np.ndarray)
        assert len(result) == 1

    def test_range(self):
        ref = np.random.rand(10)
        comp = np.random.rand(5, 10)
        result = grey_correlation(ref, comp)
        assert np.all(result >= 0)
        assert np.all(result <= 1)

    def test_ranking(self):
        ref = np.array([1, 2, 3, 4, 5], dtype=float)
        comp = np.array([
            [1.1, 2.1, 3.1, 4.1, 5.1],
            [1.5, 2.5, 3.5, 4.5, 5.5],
            [5, 4, 3, 2, 1],
        ], dtype=float)
        ranks = grey_correlation_rank(ref, comp)
        assert ranks[0] < ranks[2]  # 近似排前面
