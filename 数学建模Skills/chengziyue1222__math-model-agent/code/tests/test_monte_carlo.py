"""蒙特卡罗算法模块测试"""
import numpy as np
from algorithms.monte_carlo import (
    monte_carlo_integration,
    monte_carlo_pi,
    monte_carlo_optimization,
    monte_carlo_simulation,
    queuing_simulation,
    random_walk,
    MCResult,
)


class TestMCResult:
    """MCResult 数据类测试"""

    def test_summary_output(self):
        r = MCResult(estimate=2.0, std_error=0.01, ci_lower=1.98, ci_upper=2.02, n_samples=10000)
        s = r.summary()
        assert "2.0" in s
        assert "10000" in s


class TestMonteCarloIntegration:
    """蒙特卡罗数值积分测试"""

    def test_sin_integral(self):
        """∫sin(x)dx from 0 to π = 2"""
        result = monte_carlo_integration(lambda x: np.sin(x), 0, np.pi, 100000, seed=42)
        assert abs(result.estimate - 2.0) < 0.05

    def test_linear_integral(self):
        """∫x dx from 0 to 1 = 0.5"""
        result = monte_carlo_integration(lambda x: x, 0, 1, 100000, seed=42)
        assert abs(result.estimate - 0.5) < 0.02

    def test_constant_integral(self):
        """∫3 dx from 0 to 2 = 6"""
        result = monte_carlo_integration(lambda x: np.full_like(x, 3.0), 0, 2, 50000, seed=42)
        assert abs(result.estimate - 6.0) < 0.1

    def test_2d_integral(self):
        """二重积分 ∫∫(x+y) dxdy, x∈[0,1], y∈[0,1] = 1.0"""
        def f_2d(points):
            return points[:, 0] + points[:, 1]
        result = monte_carlo_integration(f_2d, [0, 0], [1, 1], 100000, seed=42)
        assert abs(result.estimate - 1.0) < 0.05

    def test_confidence_interval(self):
        """95% 置信区间应包含真实值"""
        result = monte_carlo_integration(lambda x: np.sin(x), 0, np.pi, 100000, seed=42)
        assert result.ci_lower < 2.0 < result.ci_upper

    def test_more_samples_better(self):
        """更多样本应有更小的标准误"""
        r1 = monte_carlo_integration(lambda x: np.sin(x), 0, np.pi, 1000, seed=42)
        r2 = monte_carlo_integration(lambda x: np.sin(x), 0, np.pi, 100000, seed=42)
        assert r2.std_error < r1.std_error


class TestMonteCarloPi:
    """蒙特卡罗估算π测试"""

    def test_pi_approximation(self):
        result = monte_carlo_pi(100000, seed=42)
        assert abs(result.estimate - np.pi) < 0.05

    def test_more_samples_closer(self):
        r1 = monte_carlo_pi(1000, seed=42)
        r2 = monte_carlo_pi(100000, seed=42)
        assert abs(r2.estimate - np.pi) < abs(r1.estimate - np.pi) + 0.1


class TestMonteCarloOptimization:
    """蒙特卡罗优化测试"""

    def test_sphere_minimization(self):
        """最小化 x^2 + y^2 应接近原点"""
        def sphere_batch(X): return np.sum(X**2, axis=1)
        best_x, best_val, _ = monte_carlo_optimization(
            sphere_batch, [(-5, 5), (-5, 5)], 100000, seed=42
        )
        assert best_val < 0.1
        assert np.linalg.norm(best_x) < 0.5

    def test_maximization(self):
        """最大化 -x^2 应接近 0"""
        def neg_sq_batch(X): return -X[:, 0]**2
        _, best_val, _ = monte_carlo_optimization(
            neg_sq_batch, [(-5, 5)], 100000, minimize=False, seed=42
        )
        assert best_val > -0.1


class TestMonteCarloSimulation:
    def test_seed_controls_legacy_numpy_samplers(self):
        sampler = lambda: np.random.uniform(-1.0, 1.0)
        first = monte_carlo_simulation(lambda x: x[0], [sampler], 1000, seed=123)
        second = monte_carlo_simulation(lambda x: x[0], [sampler], 1000, seed=123)

        assert first == second

    def test_seed_does_not_change_callers_random_state(self):
        np.random.seed(2026)
        expected = np.random.random(3)
        np.random.seed(2026)

        monte_carlo_simulation(
            lambda x: x[0], [lambda: np.random.normal()], 20, seed=99
        )
        actual = np.random.random(3)

        np.testing.assert_allclose(actual, expected)


class TestQueuingSimulation:
    """排队论仿真测试"""

    def test_m_m_1_stable(self):
        """M/M/1 稳定状态 (ρ<1) 应有有限等待时间"""
        result = queuing_simulation(0.5, 1.0, 10000, n_servers=1, seed=42)
        assert result['avg_wait_time'] < 10
        assert result['utilization'] == 0.5

    def test_m_m_c_utilization(self):
        """M/M/c 利用率应正确"""
        result = queuing_simulation(2.0, 1.0, 1000, n_servers=3, seed=42)
        assert abs(result['utilization'] - 2/3) < 0.01


class TestRandomWalk:
    """随机游走测试"""

    def test_1d_walk(self):
        result = random_walk(1000, dim=1, seed=42)
        assert result['trajectories'].shape == (1, 1001, 1)
        assert result['mean_final_distance'] > 0

    def test_2d_walk(self):
        result = random_walk(500, dim=2, n_walkers=10, seed=42)
        assert result['trajectories'].shape == (10, 501, 2)

    def test_msd_increases(self):
        """均方位移应随时间增加"""
        result = random_walk(1000, dim=1, seed=42)
        msd = result['msd']
        assert msd[-1] > msd[0]
