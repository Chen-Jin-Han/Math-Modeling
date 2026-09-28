"""AHP 层次分析法测试"""
import numpy as np
from algorithms.ahp import ahp_weight, consistency_check


class TestAHPWeight:
    """ahp_weight 函数测试"""

    def test_3x3_consistent_matrix(self):
        """一致性矩阵应通过 CR 检验"""
        A = np.array([
            [1, 3, 5],
            [1/3, 1, 3],
            [1/5, 1/3, 1]
        ])
        w, lambda_max, CR, passed = ahp_weight(A)
        assert passed, f"CR={CR:.4f} should be < 0.1"
        assert len(w) == 3
        assert abs(sum(w) - 1.0) < 1e-10, "权重和应为1"
        assert w[0] > w[1] > w[2], "权重应递减"

    def test_identity_matrix(self):
        """单位矩阵权重应均匀分布"""
        A = np.eye(4)
        w, lambda_max, CR, passed = ahp_weight(A)
        np.testing.assert_allclose(w, [0.25, 0.25, 0.25, 0.25], atol=1e-10)
        assert abs(lambda_max - 4.0) < 1e-10
        assert CR < 1e-10

    def test_inconsistent_matrix_fails(self):
        """严重不一致矩阵应不通过 CR 检验"""
        A = np.array([
            [1, 9, 9],
            [1/9, 1, 1/9],
            [1/9, 9, 1]
        ])
        w, lambda_max, CR, passed = ahp_weight(A)
        assert not passed, "严重不一致矩阵不应通过"

    def test_2x2_matrix(self):
        """2阶矩阵 CR 恒为0"""
        A = np.array([[1, 5], [1/5, 1]])
        w, lambda_max, CR, passed = ahp_weight(A)
        assert passed
        assert abs(CR) < 1e-10

    def test_reciprocal_property(self):
        """正互反矩阵性质：a_ji = 1/a_ij"""
        A = np.array([
            [1, 2, 4],
            [1/2, 1, 2],
            [1/4, 1/2, 1]
        ])
        w, _, CR, passed = ahp_weight(A)
        assert passed
        assert w[0] > w[1] > w[2]


class TestConsistencyCheck:
    """consistency_check 函数测试"""

    def test_returns_all_fields(self):
        """返回值应包含所有必要字段"""
        A = np.array([
            [1, 3, 5],
            [1/3, 1, 3],
            [1/5, 1/3, 1]
        ])
        result = consistency_check(A, verbose=False)
        assert 'weights' in result
        assert 'lambda_max' in result
        assert 'CI' in result
        assert 'CR' in result
        assert 'passed' in result

    def test_verbose_output(self, capsys):
        """verbose=True 应有输出"""
        A = np.eye(3)
        consistency_check(A, verbose=True)
        captured = capsys.readouterr()
        assert len(captured.out) > 0
