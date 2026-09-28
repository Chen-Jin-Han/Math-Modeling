"""智能优化算法测试"""
import numpy as np
import pytest
from algorithms.metaheuristic import (
    genetic_algorithm,
    particle_swarm,
    simulated_annealing,
    ant_colony_tsp,
)


# 标准测试函数
def sphere(x):
    return np.sum(x**2)

def sphere_batch(X):
    return np.sum(X**2, axis=1)


class TestGeneticAlgorithm:
    """遗传算法测试"""

    def test_sphere_convergence(self):
        """GA 应能收敛到 sphere 函数全局最优"""
        bounds = (np.array([-5.0, -5.0]), np.array([5.0, 5.0]))
        r = genetic_algorithm(sphere_batch, 2, bounds, pop_size=50, max_gen=200, vectorized=True)
        assert r['f'] < 0.01, f"GA sphere result: {r['f']}"

    def test_vectorized_matches_scalar(self):
        """向量化和标量模式结果应相近"""
        bounds = (np.array([-5.0, -5.0]), np.array([5.0, 5.0]))
        np.random.seed(42)
        r1 = genetic_algorithm(sphere, 2, bounds, pop_size=30, max_gen=100, vectorized=False)
        np.random.seed(42)
        r2 = genetic_algorithm(sphere_batch, 2, bounds, pop_size=30, max_gen=100, vectorized=True)
        # 两者都应收敛到接近 0
        assert r1['f'] < 1.0
        assert r2['f'] < 1.0

    def test_maximize_mode(self):
        """最大化模式"""
        def neg_sphere_batch(X): return -np.sum(X**2, axis=1)
        bounds = (np.array([-5.0, -5.0]), np.array([5.0, 5.0]))
        r = genetic_algorithm(neg_sphere_batch, 2, bounds, pop_size=30, max_gen=100,
                             maximize=True, vectorized=True)
        assert r['f'] > -1.0  # 最大化 -sphere，应接近 0
        assert r['f'] == pytest.approx(float(neg_sphere_batch(r['x'][None, :])[0]))
        assert r['convergence'][-1] == pytest.approx(r['f'])

    def test_convergence_curve_length(self):
        """收敛曲线长度应等于代数"""
        bounds = (np.array([-5.0]), np.array([5.0]))
        r = genetic_algorithm(sphere_batch, 1, bounds, pop_size=20, max_gen=50, vectorized=True)
        assert len(r['convergence']) == 50

    def test_high_dimensional(self):
        """高维问题"""
        n = 10
        bounds = (np.full(n, -5.0), np.full(n, 5.0))
        r = genetic_algorithm(sphere_batch, n, bounds, pop_size=100, max_gen=300, vectorized=True)
        assert r['f'] < 1.0


class TestParticleSwarm:
    """粒子群算法测试"""

    def test_sphere_convergence(self):
        bounds = (np.array([-5.0, -5.0]), np.array([5.0, 5.0]))
        r = particle_swarm(sphere_batch, 2, bounds, n_particles=30, max_iter=200, vectorized=True)
        assert r['f'] < 0.001, f"PSO sphere result: {r['f']}"

    def test_vectorized_matches_scalar(self):
        bounds = (np.array([-5.0, -5.0]), np.array([5.0, 5.0]))
        np.random.seed(42)
        r1 = particle_swarm(sphere, 2, bounds, n_particles=30, max_iter=100, vectorized=False)
        np.random.seed(42)
        r2 = particle_swarm(sphere_batch, 2, bounds, n_particles=30, max_iter=100, vectorized=True)
        assert r1['f'] < 0.1
        assert r2['f'] < 0.1

    def test_convergence_curve(self):
        bounds = (np.array([-5.0]), np.array([5.0]))
        r = particle_swarm(sphere_batch, 1, bounds, n_particles=20, max_iter=50, vectorized=True)
        assert len(r['convergence']) == 50


class TestSimulatedAnnealing:
    """模拟退火测试"""

    def test_sphere_convergence(self):
        bounds = (np.array([-5.0, -5.0]), np.array([5.0, 5.0]))
        r = simulated_annealing(sphere, np.array([3.0, 3.0]), bounds, T0=100, max_iter=100)
        assert r['f'] < 0.1, f"SA sphere result: {r['f']}"

    def test_1d_problem(self):
        bounds = (np.array([-10.0]), np.array([10.0]))
        r = simulated_annealing(lambda x: x[0]**2, np.array([5.0]), bounds)
        assert r['f'] < 0.1


class TestAntColonyTSP:
    """蚁群算法 TSP 测试"""

    def test_4_cities(self):
        """4 城市 TSP"""
        dist = np.array([
            [0, 1, 2, 3],
            [1, 0, 1, 2],
            [2, 1, 0, 1],
            [3, 2, 1, 0],
        ], dtype=float)
        r = ant_colony_tsp(dist, n_ants=10, max_iter=50)
        assert r['distance'] < 10  # 4 城市最短路径应 < 10
        assert len(r['path']) == 4

    def test_symmetric_tsp(self):
        """对称 TSP，路径长度应合理"""
        np.random.seed(42)
        n = 8
        coords = np.random.rand(n, 2) * 100
        dist = np.sqrt(((coords[:, None] - coords[None, :]) ** 2).sum(axis=2))
        r = ant_colony_tsp(dist, n_ants=20, max_iter=100)
        # 贪心下界
        greedy = sum(np.min(dist[i][dist[i] > 0]) for i in range(n))
        assert r['distance'] < greedy * 3  # ACO 应不差于贪心的 3 倍
