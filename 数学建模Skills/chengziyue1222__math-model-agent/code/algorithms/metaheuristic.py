"""
智能优化算法工具箱
==================
包含：遗传算法(GA)、粒子群算法(PSO)、模拟退火(SA)、蚁群算法(ACO)、鱼群算法(AFSA)

参考：Algorithms_MathModels/HeuristicAlgorithm/ + MATLAB智能算法30个案例分析/
"""

import numpy as np
from typing import Tuple, Dict, Callable


# ============================================================
# 1. 遗传算法 (GA)
# ============================================================
def genetic_algorithm(fitness_func: Callable,
                      n_vars: int,
                      bounds: Tuple[np.ndarray, np.ndarray],
                      pop_size: int = 50,
                      max_gen: int = 200,
                      crossover_rate: float = 0.8,
                      mutation_rate: float = 0.1,
                      maximize: bool = False,
                      vectorized: bool = True) -> Dict:
    """
    遗传算法

    Parameters
    ----------
    fitness_func : callable
        适应度函数。
        - vectorized=True: f(pop) -> (pop_size,) 数组，接受 (pop_size, n_vars) 矩阵（推荐）
        - vectorized=False: f(x) -> float，接受 (n_vars,) 向量
    n_vars : int
        变量个数
    bounds : tuple of np.ndarray
        变量上下界 (lower, upper)
    pop_size : int
        种群大小
    max_gen : int
        最大代数
    crossover_rate : float
        交叉概率
    mutation_rate : float
        变异概率
    maximize : bool
        是否最大化 (默认最小化)
    vectorized : bool
        是否使用向量化适应度评估（快 10-50x）

    Returns
    -------
    dict : 最优解、最优值、收敛曲线
    """
    lower, upper = np.asarray(bounds[0], dtype=float), np.asarray(bounds[1], dtype=float)

    # 初始化种群
    pop = np.random.uniform(lower, upper, (pop_size, n_vars))
    best_x = pop[0].copy()
    best_f = -np.inf if maximize else np.inf
    convergence = []

    def _eval_fitness(pop_arr):
        """批量评估适应度"""
        if vectorized:
            try:
                vals = np.asarray(fitness_func(pop_arr), dtype=float)
                if vals.shape == (pop_size,):
                    return vals
            except Exception:
                pass
        # fallback: 逐个评估
        return np.array([fitness_func(ind) for ind in pop_arr])

    for gen in range(max_gen):
        # 计算适应度（向量化）
        raw_fitness = _eval_fitness(pop)
        selection_fitness = -raw_fitness if maximize else raw_fitness

        # 记录最优
        best_idx = int(np.argmax(raw_fitness) if maximize else np.argmin(raw_fitness))
        candidate_f = float(raw_fitness[best_idx])
        if (maximize and candidate_f > best_f) or (not maximize and candidate_f < best_f):
            best_f = candidate_f
            best_x = pop[best_idx].copy()
        convergence.append(best_f)

        # 锦标赛选择（向量化）
        idx1 = np.random.randint(0, pop_size, pop_size)
        idx2 = np.random.randint(0, pop_size, pop_size)
        mask = selection_fitness[idx1] < selection_fitness[idx2]
        winners = np.where(mask[:, None], pop[idx1], pop[idx2])
        pop = winners.copy()

        # 交叉 (SBX)（向量化）
        n_pairs = pop_size // 2
        do_crossover = np.random.rand(n_pairs) < crossover_rate
        pair_indices = np.arange(0, pop_size - 1, 2)
        alpha = np.random.uniform(-0.5, 1.5, (n_pairs, n_vars))
        p1 = pop[pair_indices]
        p2 = pop[pair_indices + 1]
        c1 = 0.5 * ((1 + alpha) * p1 + (1 - alpha) * p2)
        c2 = 0.5 * ((1 - alpha) * p1 + (1 + alpha) * p2)
        # 只对满足交叉条件的对执行
        mask_c = do_crossover[:, None]
        pop[pair_indices] = np.where(mask_c, np.clip(c1, lower, upper), p1)
        pop[pair_indices + 1] = np.where(mask_c, np.clip(c2, lower, upper), p2)

        # 变异（向量化）
        do_mutate = np.random.rand(pop_size) < mutation_rate
        if np.any(do_mutate):
            mut_idx = np.random.randint(0, n_vars, np.sum(do_mutate))
            mut_vals = np.random.uniform(lower[mut_idx], upper[mut_idx])
            rows = np.arange(pop_size)[do_mutate]
            pop[rows, mut_idx] = mut_vals

    return {
        'x': best_x,
        'f': best_f,
        'convergence': convergence,
        'n_generations': max_gen
    }


# ============================================================
# 2. 粒子群算法 (PSO)
# ============================================================
def particle_swarm(fitness_func: Callable,
                   n_vars: int,
                   bounds: Tuple[np.ndarray, np.ndarray],
                   n_particles: int = 30,
                   max_iter: int = 200,
                   w: float = 0.7,
                   c1: float = 1.5,
                   c2: float = 1.5,
                   maximize: bool = False,
                   vectorized: bool = True) -> Dict:
    """
    粒子群优化算法 (PSO)

    Parameters
    ----------
    fitness_func : callable
        适应度函数。
        - vectorized=True: f(pos) -> (n_particles,) 数组（推荐）
        - vectorized=False: f(x) -> float
    n_vars : int
        变量个数
    bounds : tuple of np.ndarray
        变量上下界
    n_particles : int
        粒子数
    max_iter : int
        最大迭代次数
    w : float
        惯性权重
    c1, c2 : float
        学习因子
    maximize : bool
        是否最大化
    vectorized : bool
        是否使用向量化适应度评估

    Returns
    -------
    dict : 全局最优解、最优值、收敛曲线
    """
    lower, upper = np.asarray(bounds[0], dtype=float), np.asarray(bounds[1], dtype=float)

    def _eval_fitness(pos_arr):
        """批量评估适应度"""
        if vectorized:
            try:
                vals = np.asarray(fitness_func(pos_arr), dtype=float)
                if vals.shape == (n_particles,):
                    return vals
            except Exception:
                pass
        return np.array([fitness_func(p) for p in pos_arr])

    # 初始化
    pos = np.random.uniform(lower, upper, (n_particles, n_vars))
    vel = np.random.uniform(-(upper-lower)*0.1, (upper-lower)*0.1, (n_particles, n_vars))

    p_best = pos.copy()
    p_best_f = _eval_fitness(pos)
    g_best_idx = np.argmax(p_best_f) if maximize else np.argmin(p_best_f)
    g_best = p_best[g_best_idx].copy()
    g_best_f = float(p_best_f[g_best_idx])

    convergence = []
    w_start, w_end = w, 0.4

    for it in range(max_iter):
        # 向量化评估
        cur_f = _eval_fitness(pos)

        # 更新个体最优（向量化）
        if maximize:
            improve = cur_f > p_best_f
        else:
            improve = cur_f < p_best_f
        p_best_f = np.where(improve, cur_f, p_best_f)
        p_best = np.where(improve[:, None], pos, p_best)

        # 更新全局最优
        best_idx = np.argmax(p_best_f) if maximize else np.argmin(p_best_f)
        if (maximize and p_best_f[best_idx] > g_best_f) or \
           (not maximize and p_best_f[best_idx] < g_best_f):
            g_best_f = float(p_best_f[best_idx])
            g_best = p_best[best_idx].copy()

        convergence.append(g_best_f)

        # 线性递减惯性权重
        w_cur = w_start - (w_start - w_end) * (it / max_iter)

        # 更新速度和位置（向量化）
        r1 = np.random.rand(n_particles, n_vars)
        r2 = np.random.rand(n_particles, n_vars)
        vel = w_cur * vel + c1 * r1 * (p_best - pos) + c2 * r2 * (g_best - pos)
        pos = pos + vel
        pos = np.clip(pos, lower, upper)

    return {
        'x': g_best,
        'f': g_best_f,
        'convergence': convergence,
        'n_iterations': max_iter
    }


# ============================================================
# 3. 模拟退火 (SA)
# ============================================================
def simulated_annealing(fitness_func: Callable,
                        x0: np.ndarray,
                        bounds: Tuple[np.ndarray, np.ndarray],
                        T0: float = 100,
                        T_min: float = 1e-8,
                        alpha: float = 0.95,
                        max_iter: int = 1000,
                        step_size: float = 0.1,
                        maximize: bool = False) -> Dict:
    """
    模拟退火算法

    Parameters
    ----------
    fitness_func : callable
        目标函数
    x0 : np.ndarray
        初始解
    bounds : tuple of np.ndarray
        变量上下界
    T0 : float
        初始温度
    T_min : float
        终止温度
    alpha : float
        降温系数
    max_iter : int
        每个温度下的迭代次数
    step_size : float
        邻域扰动步长
    maximize : bool
        是否最大化

    Returns
    -------
    dict : 最优解、最优值、温度变化曲线
    """
    lower, upper = np.asarray(bounds[0]), np.asarray(bounds[1])
    x = np.asarray(x0, dtype=float)
    f = fitness_func(x)
    best_x, best_f = x.copy(), f
    T = T0
    T_history, f_history = [], []

    while T > T_min:
        for _ in range(max_iter):
            # 邻域扰动
            x_new = x + np.random.uniform(-step_size, step_size, len(x))
            x_new = np.clip(x_new, lower, upper)
            f_new = fitness_func(x_new)

            # 接受准则
            delta = f_new - f
            if maximize:
                delta = -delta
            if delta < 0 or np.random.rand() < np.exp(-delta / T):
                x, f = x_new, f_new
                if (maximize and f > best_f) or (not maximize and f < best_f):
                    best_x, best_f = x.copy(), f

        T_history.append(T)
        f_history.append(best_f)
        T *= alpha

    return {
        'x': best_x,
        'f': best_f,
        'T_history': T_history,
        'f_history': f_history
    }


# ============================================================
# 4. 蚁群算法 (ACO) — TSP
# ============================================================
def ant_colony_tsp(dist_matrix: np.ndarray,
                   n_ants: int = 20,
                   max_iter: int = 100,
                   alpha: float = 1.0,
                   beta: float = 2.0,
                   rho: float = 0.5,
                   Q: float = 100) -> Dict:
    """
    蚁群算法求解 TSP

    Parameters
    ----------
    dist_matrix : np.ndarray
        距离矩阵 (n, n)
    n_ants : int
        蚂蚁数量
    max_iter : int
        最大迭代次数
    alpha : float
        信息素重要程度
    beta : float
        启发式因子重要程度
    rho : float
        信息素挥发系数
    Q : float
        信息素增强系数

    Returns
    -------
    dict : 最优路径、最短距离、收敛曲线
    """
    n = dist_matrix.shape[0]
    tau = np.ones((n, n))  # 信息素
    eta = 1 / (dist_matrix + np.eye(n) * 1e-10)  # 启发式信息
    np.fill_diagonal(eta, 0)

    best_path = None
    best_dist = np.inf
    convergence = []

    for it in range(max_iter):
        paths = []
        path_dists = []

        for ant in range(n_ants):
            visited = [np.random.randint(n)]
            for _ in range(n - 1):
                u = visited[-1]
                # 向量化：用 mask 屏蔽已访问城市，避免 O(n) 内层循环
                prob = (tau[u] ** alpha) * (eta[u] ** beta)
                prob[visited] = 0.0
                prob = prob / prob.sum()
                next_city = np.random.choice(n, p=prob)
                visited.append(next_city)

            # 计算路径长度
            d = sum(dist_matrix[visited[i], visited[(i+1) % n]] for i in range(n))
            paths.append(visited)
            path_dists.append(d)

            if d < best_dist:
                best_dist = d
                best_path = visited.copy()

        convergence.append(best_dist)

        # 更新信息素
        tau *= (1 - rho)
        for path, d in zip(paths, path_dists):
            for i in range(n):
                u, v = path[i], path[(i+1) % n]
                tau[u, v] += Q / d
                tau[v, u] += Q / d

    return {
        'path': best_path,
        'distance': best_dist,
        'convergence': convergence
    }


# ============================================================
# 5. 鱼群算法 (AFSA)
# ============================================================
def artificial_fish_swarm(fitness_func: Callable,
                          n_vars: int,
                          bounds: Tuple[np.ndarray, np.ndarray],
                          n_fish: int = 30,
                          max_iter: int = 100,
                          visual: float = 1.0,
                          step: float = 0.5,
                          delta: float = 0.6,
                          maximize: bool = False) -> Dict:
    """
    人工鱼群算法

    Parameters
    ----------
    fitness_func : callable
        适应度函数
    n_vars : int
        变量个数
    bounds : tuple of np.ndarray
        变量上下界
    n_fish : int
        鱼群数量
    max_iter : int
        最大迭代次数
    visual : float
        视野范围
    step : float
        移动步长
    delta : float
        拥挤度因子
    maximize : bool
        是否最大化

    Returns
    -------
    dict : 最优解、最优值、收敛曲线
    """
    lower, upper = np.asarray(bounds[0]), np.asarray(bounds[1])

    # 初始化鱼群
    fish = np.random.uniform(lower, upper, (n_fish, n_vars))
    fitness = np.array([fitness_func(f) for f in fish])

    best_idx = np.argmax(fitness) if maximize else np.argmin(fitness)
    best_x = fish[best_idx].copy()
    best_f = fitness[best_idx]
    convergence = []

    for it in range(max_iter):
        for i in range(n_fish):
            # 觅食行为
            x_new = fish[i] + step * np.random.randn(n_vars)
            x_new = np.clip(x_new, lower, upper)
            f_new = fitness_func(x_new)

            if (maximize and f_new > fitness[i]) or (not maximize and f_new < fitness[i]):
                fish[i] = x_new
                fitness[i] = f_new

            # 聚群行为
            neighbors = []
            for j in range(n_fish):
                if np.linalg.norm(fish[j] - fish[i]) < visual:
                    neighbors.append(j)

            if neighbors:
                center = fish[neighbors].mean(axis=0)
                f_center = fitness_func(center)
                n_neighbors = len(neighbors)
                if (maximize and f_center > fitness[i] and f_center / n_neighbors > fitness[i] / n_fish * delta) or \
                   (not maximize and f_center < fitness[i] and f_center / n_neighbors < fitness[i] / n_fish * delta):
                    fish[i] = center
                    fitness[i] = f_center

        # 更新全局最优
        cur_idx = np.argmax(fitness) if maximize else np.argmin(fitness)
        if (maximize and fitness[cur_idx] > best_f) or \
           (not maximize and fitness[cur_idx] < best_f):
            best_f = fitness[cur_idx]
            best_x = fish[cur_idx].copy()

        convergence.append(best_f)

    return {
        'x': best_x,
        'f': best_f,
        'convergence': convergence
    }


# ============================================================
# 使用示例
# ============================================================
def example():
    """智能优化算法示例"""
    # Rastrigin 函数 (多峰, 全局最优在原点, 最小值为 0)
    def rastrigin(x):
        A = 10
        return A * len(x) + sum(xi**2 - A * np.cos(2*np.pi*xi) for xi in x)

    n_vars = 5
    bounds = (np.full(n_vars, -5.12), np.full(n_vars, 5.12))

    # GA（默认 minimize）
    print("=" * 60)
    print("示例1: 遗传算法 — Rastrigin 函数")
    print("=" * 60)
    r = genetic_algorithm(rastrigin, n_vars, bounds)
    print(f"  最优值: {r['f']:.4f}, 最优解: {r['x'].round(4)}")

    # PSO（默认 minimize）
    print("\n" + "=" * 60)
    print("示例2: 粒子群算法 — Rastrigin 函数")
    print("=" * 60)
    r = particle_swarm(rastrigin, n_vars, bounds)
    print(f"  最优值: {r['f']:.4f}, 最优解: {r['x'].round(4)}")

    # SA（默认 minimize）
    print("\n" + "=" * 60)
    print("示例3: 模拟退火 — Rastrigin 函数")
    print("=" * 60)
    r = simulated_annealing(rastrigin, np.zeros(n_vars), bounds)
    print(f"  最优值: {r['f']:.4f}, 最优解: {r['x'].round(4)}")


if __name__ == "__main__":
    example()
