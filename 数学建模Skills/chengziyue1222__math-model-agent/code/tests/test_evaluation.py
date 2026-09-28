"""综合评价方法测试"""
import numpy as np
from algorithms.evaluation import (
    entropy_weight,
    topsis,
    dea,
    pca,
    rsr,
    grey_relational,
)


class TestEntropyWeight:
    """熵权法测试"""

    def test_uniform_data(self):
        """均匀数据权重应接近均匀"""
        data = np.array([[1, 1], [1, 1], [1, 1]], dtype=float)
        w = entropy_weight(data)
        np.testing.assert_allclose(w, [0.5, 0.5], atol=0.1)

    def test_varied_data(self):
        """变化大的指标权重更大"""
        data = np.array([
            [1, 100],
            [1, 200],
            [1, 300],
            [1, 400],
        ], dtype=float)
        w = entropy_weight(data)
        assert w[1] > w[0]

    def test_weights_sum_to_one(self):
        data = np.random.rand(10, 5)
        w = entropy_weight(data)
        assert abs(sum(w) - 1.0) < 1e-10

    def test_non_negative(self):
        data = np.random.rand(20, 4)
        w = entropy_weight(data)
        assert np.all(w >= 0)

    def test_single_indicator(self):
        """单指标权重应为1"""
        data = np.array([[1], [2], [3]], dtype=float)
        w = entropy_weight(data)
        assert abs(w[0] - 1.0) < 1e-10


class TestTOPSIS:
    """TOPSIS 评价测试"""

    def test_simple_ranking(self):
        data = np.array([[1, 2], [3, 4], [5, 6]], dtype=float)
        weights = np.array([0.5, 0.5])
        benefit = np.array([True, True])
        result = topsis(data, weights, benefit)
        assert result.ranks[2] == 1  # 第3行最优

    def test_benefit_vs_cost(self):
        data = np.array([[10, 1], [5, 5], [1, 10]], dtype=float)
        weights = np.array([0.5, 0.5])
        r1 = topsis(data, weights, np.array([True, True]))
        r2 = topsis(data, weights, np.array([True, False]))
        assert not np.array_equal(r1.ranks, r2.ranks)

    def test_scores_between_0_1(self):
        data = np.random.rand(20, 5)
        weights = np.ones(5) / 5
        benefit = np.ones(5, dtype=bool)
        result = topsis(data, weights, benefit)
        assert np.all(result.scores >= 0)
        assert np.all(result.scores <= 1)

    def test_return_fields(self):
        data = np.array([[1, 2], [3, 4]], dtype=float)
        result = topsis(data, np.array([0.5, 0.5]), np.array([True, True]))
        assert hasattr(result, 'scores')
        assert hasattr(result, 'ranks')
        assert hasattr(result, 'ideal_pos')

    def test_equal_alternatives(self):
        """相同方案得分应相同"""
        data = np.array([[1, 2], [1, 2]], dtype=float)
        result = topsis(data, np.array([0.5, 0.5]), np.array([True, True]))
        assert abs(result.scores[0] - result.scores[1]) < 1e-10


class TestDEA:
    """DEA 数据包络分析测试"""

    def test_efficiency_range(self):
        inputs = np.random.rand(10, 3) + 0.1
        outputs = np.random.rand(10, 2) + 0.1
        result = dea(inputs, outputs)
        assert np.all(result.efficiency >= 0)
        assert np.all(result.efficiency <= 1 + 1e-10)

    def test_efficient_unit(self):
        inputs = np.array([[1], [2]], dtype=float)
        outputs = np.array([[2], [3]], dtype=float)
        result = dea(inputs, outputs)
        assert result.efficiency[0] >= result.efficiency[1]

    def test_return_fields(self):
        inputs = np.array([[1], [2]], dtype=float)
        outputs = np.array([[2], [3]], dtype=float)
        result = dea(inputs, outputs)
        assert hasattr(result, 'efficiency')
        assert hasattr(result, 'is_efficient')


class TestPCA:
    """PCA 主成分分析测试"""

    def test_variance_explained(self):
        data = np.random.rand(50, 5)
        result = pca(data)
        assert abs(sum(result.variance_ratio) - 1.0) < 1e-10

    def test_dimension_reduction(self):
        data = np.random.rand(50, 5)
        result = pca(data, n_components=2)
        assert result.transformed.shape == (50, 2)

    def test_correlated_data(self):
        x = np.linspace(0, 1, 100)
        noise = np.random.RandomState(0).randn(100) * 1e-4
        data = np.column_stack([x, x + noise])
        result = pca(data)
        assert result.variance_ratio[0] > 0.8

    def test_return_fields(self):
        data = np.random.rand(20, 3)
        result = pca(data)
        assert hasattr(result, 'components')
        assert hasattr(result, 'eigenvalues')
        assert hasattr(result, 'variance_ratio')


class TestRSR:
    """RSR 秩和比法测试"""

    def test_basic_rsr(self):
        data = np.array([[80, 90, 70], [60, 70, 80], [90, 80, 90]], dtype=float)
        result = rsr(data)
        assert len(result.rsr_values) == 3

    def test_rsr_range(self):
        data = np.random.rand(20, 5) * 100
        result = rsr(data)
        assert np.all(result.rsr_values >= 0)
        assert np.all(result.rsr_values <= 1 + 1e-10)

    def test_best_rank(self):
        """全最优方案应排第一"""
        data = np.array([
            [100, 100, 100],
            [50, 50, 50],
            [0, 0, 0],
        ], dtype=float)
        result = rsr(data)
        assert result.ranks[0] == 1


class TestGreyRelational:
    """灰色关联分析测试"""

    def test_identical_series(self):
        ref = np.array([1, 2, 3, 4, 5], dtype=float)
        comp = np.array([[1, 2, 3, 4, 5]], dtype=float)
        result = grey_relational(ref, comp)
        assert result[0] > 0.99

    def test_correlated_data(self):
        ref = np.array([1, 2, 3, 4, 5], dtype=float)
        comp = np.array([
            [1.1, 2.1, 3.1, 4.1, 5.1],
            [5, 4, 3, 2, 1],
        ], dtype=float)
        result = grey_relational(ref, comp)
        assert result[0] > result[1]
