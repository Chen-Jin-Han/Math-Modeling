"""
蒙特卡罗算法 (Monte Carlo)
===========================
随机模拟、概率估算、风险分析、排队论仿真。

包含函数:
- monte_carlo_integration: 蒙特卡罗数值积分
- monte_carlo_pi: 蒙特卡罗估算 π
- monte_carlo_optimization: 蒙特卡罗随机搜索优化
- monte_carlo_simulation: 通用蒙特卡罗仿真（指定分布）
- queuing_simulation: 排队论蒙特卡罗仿真 (M/M/c)
- queuing_mmsk: M/M/S/k 有限容量排队论（解析解 + 仿真验证）
- random_walk: 随机游走模拟

竞赛场景:
- 复杂积分近似求解
- 风险分析、可靠性评估
- 排队系统设计（银行、医院、呼叫中心）
- 随机过程模拟

参考: ravenxrz/Mathematical-Modeling/queuing_theory/
"""

from __future__ import annotations

import numpy as np
from typing import Callable, Optional
from dataclasses import dataclass, field


@dataclass
class MCResult:
    """蒙特卡罗模拟结果"""
    estimate: float
    std_error: float
    ci_lower: float
    ci_upper: float
    n_samples: int
    all_samples: Optional[np.ndarray] = field(default=None, repr=False)

    def summary(self) -> str:
        return (
            f"估计值: {self.estimate:.6f}\n"
            f"标准误: {self.std_error:.6f}\n"
            f"95%置信区间: [{self.ci_lower:.6f}, {self.ci_upper:.6f}]\n"
            f"样本数: {self.n_samples}"
        )


def monte_carlo_integration(
    f: Callable[[np.ndarray], np.ndarray],
    a: np.ndarray,
    b: np.ndarray,
    n_samples: int = 100000,
    seed: int | None = None,
    vectorized: bool = True,
) -> MCResult:
    """蒙特卡罗数值积分

    估算 ∫f(x)dx 在 [a, b] 区间上的积分值。

    Args:
        f: 被积函数。
            - vectorized=True 时：接受 (n, d) 数组，返回 (n,) 数组（推荐）
            - vectorized=False 时：接受 (d,) 数组，返回标量
        a: 积分下限（标量或向量）
        b: 积分上限（标量或向量）
        n_samples: 采样点数
        seed: 随机种子
        vectorized: 是否使用向量化计算（快 10-100x）

    Returns:
        MCResult 包含积分估计值

    Examples:
        >>> import numpy as np
        >>> # 向量化模式（推荐）：f 接受 (n,d) 数组
        >>> result = monte_carlo_integration(lambda x: np.sin(x[:, 0]), 0, np.pi, 100000)
        >>> print(f"∫sin(x)dx ≈ {result.estimate:.4f}")  # ≈ 2.0
    """
    rng = np.random.default_rng(seed)
    a = np.atleast_1d(np.asarray(a, dtype=float))
    b = np.atleast_1d(np.asarray(b, dtype=float))
    dim = len(a)

    # 生成均匀随机点
    points = rng.uniform(a, b, size=(n_samples, dim))

    # 计算函数值：向量化 vs 逐点
    if vectorized and dim == 1:
        # 1D: f 接受 (n,) 数组，返回 (n,) 数组
        try:
            values = np.asarray(f(points[:, 0]), dtype=float)
            if values.shape != (n_samples,):
                raise ValueError("shape mismatch")
        except Exception:
            values = np.array([f(p[0]) for p in points])
    elif vectorized:
        # 多维: f 接受 (n, d) 数组，返回 (n,) 数组
        try:
            values = np.asarray(f(points), dtype=float)
            if values.shape != (n_samples,):
                raise ValueError("shape mismatch")
        except Exception:
            values = np.array([f(p) for p in points])
    else:
        values = np.array([f(p) for p in points])

    # 积分 = 体积 * 平均函数值
    volume = np.prod(b - a)
    mean_val = np.mean(values)
    std_error = np.std(values) / np.sqrt(n_samples)

    estimate = volume * mean_val
    ci_lower = volume * (mean_val - 1.96 * std_error)
    ci_upper = volume * (mean_val + 1.96 * std_error)

    return MCResult(
        estimate=estimate,
        std_error=volume * std_error,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        n_samples=n_samples,
    )


def monte_carlo_pi(n_samples: int = 100000, seed: int | None = None) -> MCResult:
    """蒙特卡罗估算π值

    通过随机投点法估算圆周率。

    Args:
        n_samples: 采样点数
        seed: 随机种子

    Returns:
        MCResult 包含π的估计值
    """
    rng = np.random.default_rng(seed)
    x = rng.uniform(-1, 1, n_samples)
    y = rng.uniform(-1, 1, n_samples)

    inside = (x**2 + y**2) <= 1.0
    pi_estimates = 4.0 * np.cumsum(inside) / np.arange(1, n_samples + 1)

    estimate = pi_estimates[-1]
    std_error = np.sqrt(estimate * (4 - estimate) / n_samples)

    return MCResult(
        estimate=estimate,
        std_error=std_error,
        ci_lower=estimate - 1.96 * std_error,
        ci_upper=estimate + 1.96 * std_error,
        n_samples=n_samples,
        all_samples=pi_estimates,
    )


def monte_carlo_optimization(
    objective: Callable[[np.ndarray], float],
    bounds: list[tuple[float, float]],
    n_samples: int = 100000,
    minimize: bool = True,
    seed: int | None = None,
    vectorized: bool = True,
) -> tuple[np.ndarray, float, MCResult]:
    """蒙特卡罗随机搜索优化

    通过随机采样寻找最优解，适用于无梯度、非凸优化问题。

    Args:
        objective: 目标函数。
            - vectorized=True 时：接受 (n, d) 数组，返回 (n,) 数组（推荐）
            - vectorized=False 时：接受 (d,) 数组，返回标量
        bounds: 各变量的上下界 [(lo, hi), ...]
        n_samples: 采样点数
        minimize: True为最小化，False为最大化
        seed: 随机种子
        vectorized: 是否使用向量化计算

    Returns:
        (最优解, 最优值, MCResult)

    Examples:
        >>> # 向量化模式
        >>> def sphere_batch(X): return np.sum(X**2, axis=1)
        >>> best_x, best_val, result = monte_carlo_optimization(
        ...     sphere_batch, [(-5, 5), (-5, 5)], 100000
        ... )
    """
    rng = np.random.default_rng(seed)
    dim = len(bounds)
    lower = np.array([b[0] for b in bounds])
    upper = np.array([b[1] for b in bounds])

    # 生成随机点
    points = rng.uniform(lower, upper, size=(n_samples, dim))

    # 计算目标值：向量化 vs 逐点
    if vectorized:
        try:
            values = np.asarray(objective(points), dtype=float)
            if values.shape != (n_samples,):
                raise ValueError("shape mismatch")
        except Exception:
            values = np.array([objective(p) for p in points])
    else:
        values = np.array([objective(p) for p in points])

    if minimize:
        best_idx = np.argmin(values)
    else:
        best_idx = np.argmax(values)

    best_x = points[best_idx]
    best_val = values[best_idx]

    return best_x, best_val, MCResult(
        estimate=best_val,
        std_error=np.std(values) / np.sqrt(n_samples),
        ci_lower=np.percentile(values, 2.5),
        ci_upper=np.percentile(values, 97.5),
        n_samples=n_samples,
    )


def monte_carlo_simulation(
    model: Callable[[np.ndarray], np.ndarray],
    input_distributions: list[Callable[[], float]],
    n_samples: int = 10000,
    seed: int | None = None,
    vectorized_model: Callable[[np.ndarray], np.ndarray] | None = None,
) -> dict:
    """通用蒙特卡罗仿真

    对任意模型进行蒙特卡罗仿真，分析输出的统计特性。

    Args:
        model: 仿真模型，接受 (d,) 输入数组，返回标量或数组
        input_distributions: 输入随机变量的采样函数列表
        n_samples: 仿真次数
        seed: 随机种子
        vectorized_model: 向量化版本模型，接受 (n, d) 输入，返回 (n,) 输出。
            提供此参数可大幅加速仿真（快 10-100x）。

    Returns:
        字典包含输出的均值、标准差、分位数等统计量

    Examples:
        >>> # 仿真投资组合收益
        >>> def portfolio(weights):
        ...     returns = np.random.normal([0.08, 0.12], [0.15, 0.25])
        ...     return np.dot(weights, returns)
        >>> result = monte_carlo_simulation(
        ...     portfolio, [lambda: np.random.uniform(0, 1) for _ in range(2)],
        ...     n_samples=10000
        ... )
    """
    def _simulate() -> np.ndarray:
        selected_vectorized_model = vectorized_model

        # 尝试向量化模式
        if selected_vectorized_model is not None:
            try:
                all_inputs = np.column_stack([
                    np.array([dist() for _ in range(n_samples)])
                    for dist in input_distributions
                ])
                batch_outputs = np.asarray(selected_vectorized_model(all_inputs))
                if batch_outputs.shape[0] != n_samples:
                    raise ValueError("vectorized_model 的输出行数必须等于 n_samples")
                return batch_outputs
            except Exception:
                # 兼容不支持批量输入的模型，回退到逐点模式。
                pass

        point_outputs = []
        for _ in range(n_samples):
            inputs = np.array([dist() for dist in input_distributions])
            point_outputs.append(model(inputs))
        return np.asarray(point_outputs)

    # input_distributions 的既有 API 是零参数 callable，许多调用方内部使用
    # np.random。临时设置并恢复全局状态，既保证 seed 可复现，也不污染调用方。
    legacy_state = np.random.get_state() if seed is not None else None
    try:
        if seed is not None:
            np.random.seed(seed)
        outputs = _simulate()
    finally:
        if legacy_state is not None:
            np.random.set_state(legacy_state)

    if outputs.ndim == 1:
        outputs = outputs.reshape(-1, 1)

    results = {}
    for i in range(outputs.shape[1]):
        col = outputs[:, i]
        results[f"output_{i}"] = {
            "mean": float(np.mean(col)),
            "std": float(np.std(col)),
            "min": float(np.min(col)),
            "max": float(np.max(col)),
            "q25": float(np.percentile(col, 25)),
            "q50": float(np.percentile(col, 50)),
            "q75": float(np.percentile(col, 75)),
            "q5": float(np.percentile(col, 5)),
            "q95": float(np.percentile(col, 95)),
        }

    return results


def queuing_simulation(
    arrival_rate: float,
    service_rate: float,
    n_customers: int = 10000,
    n_servers: int = 1,
    seed: int | None = None,
) -> dict:
    """排队论蒙特卡罗仿真 (M/M/c 模型)

    Args:
        arrival_rate: 到达率 λ
        service_rate: 服务率 μ
        n_customers: 仿真顾客数
        n_servers: 服务台数量 c
        seed: 随机种子

    Returns:
        字典包含平均等待时间、平均队列长度等指标
    """
    rng = np.random.default_rng(seed)

    # 生成到达间隔和服务时间
    inter_arrival = rng.exponential(1.0 / arrival_rate, n_customers)
    service_times = rng.exponential(1.0 / service_rate, n_customers)

    # 到达时间
    arrival_times = np.cumsum(inter_arrival)

    # 初始化
    departure_times = np.zeros(n_customers)
    wait_times = np.zeros(n_customers)
    server_free_at = np.zeros(n_servers)

    for i in range(n_customers):
        # 找到最早空闲的服务台
        server_idx = np.argmin(server_free_at)
        start_service = max(arrival_times[i], server_free_at[server_idx])
        wait_times[i] = start_service - arrival_times[i]
        departure_times[i] = start_service + service_times[i]
        server_free_at[server_idx] = departure_times[i]

    sojourn_times = departure_times - arrival_times

    # 理论值 (M/M/1 或 M/M/c)
    rho = arrival_rate / (n_servers * service_rate)

    return {
        "avg_wait_time": float(np.mean(wait_times)),
        "avg_sojourn_time": float(np.mean(sojourn_times)),
        "avg_queue_length": float(np.mean(wait_times > 0)),
        "utilization": float(rho),
        "max_wait_time": float(np.max(wait_times)),
        "p_wait": float(np.mean(wait_times > 0)),
        "n_customers": n_customers,
    }


def queuing_mmsk(
    arrival_rate: float,
    service_rate: float,
    n_servers: int = 1,
    capacity: int | None = None,
    n_customers: int = 100000,
    seed: int | None = None,
) -> dict:
    """
    M/M/S/k 排队论模型（有限容量 / 有限等待空间）

    解析计算 + 蒙特卡罗仿真双重验证。
    M/M/S/k: S 个服务台，系统总容量为 k（含正在服务的），
    到达过程为泊松过程，服务时间服从指数分布。

    当 k=None 时退化为 M/M/S（无限容量）。
    当 S=1, k=None 时退化为 M/M/1。

    Parameters
    ----------
    arrival_rate : float
        到达率 λ（单位时间平均到达数）
    service_rate : float
        服务率 μ（单位时间每个服务台平均服务数）
    n_servers : int
        服务台数量 S
    capacity : int or None
        系统总容量 k（含服务中的）。None 表示无限容量
    n_customers : int
        仿真顾客数
    seed : int or None
        随机种子

    Returns
    -------
    dict:
        - rho: 服务强度 ρ = λ/(S·μ)
        - p0: 系统空闲概率
        - pk: 顾客被拒/损失概率（仅有限容量）
        - avg_queue_length: 平均队列长度 Lq
        - avg_system_length: 平均系统中顾客数 L
        - avg_wait_time: 平均等待时间 Wq
        - avg_sojourn_time: 平均逗留时间 W
        - utilization: 服务台利用率
        - sim_*: 仿真对应指标

    参考
    ----
    ravenxrz/Mathematical-Modeling/queuing_theory/MMSkteam.m
    """
    lam = arrival_rate
    mu = service_rate
    S = n_servers
    rho = lam / (S * mu)

    # ============ 解析解 ============
    # 先计算 p0（系统空闲概率）
    def _factorial(n):
        r = 1
        for i in range(2, n + 1):
            r *= i
        return r

    if capacity is not None:
        k = capacity
        # M/M/S/k 解析解
        a = lam / mu  # 话务强度

        # p0
        sum1 = sum((a ** n) / _factorial(n) for n in range(S))
        if abs(rho - 1.0) < 1e-10:
            sum2 = ((a ** S) / _factorial(S)) * (k - S + 1)
        else:
            sum2 = ((a ** S) / _factorial(S)) * (1 - rho ** (k - S + 1)) / (1 - rho)
        p0 = 1.0 / (sum1 + sum2)

        # pn
        def pn(n):
            if n < S:
                return (a ** n) / _factorial(n) * p0
            else:
                return (a ** n) / (_factorial(S) * (S ** (n - S))) * p0

        pk = pn(k)
        avg_L = sum(n * pn(n) for n in range(k + 1))
        avg_Lq = sum((n - S) * pn(n) for n in range(S, k + 1))
        avg_Lq = max(0, avg_Lq)

        effective_lambda = lam * (1 - pk)
        avg_W = avg_L / effective_lambda if effective_lambda > 0 else 0
        avg_Wq = avg_Lq / effective_lambda if effective_lambda > 0 else 0
        utilization = 1 - p0

    else:
        # M/M/S 无限容量
        a = lam / mu
        sum1 = sum((a ** n) / _factorial(n) for n in range(S))
        sum2 = ((a ** S) / _factorial(S)) * (1 / (1 - rho)) if rho < 1 else 0
        p0 = 1.0 / (sum1 + sum2) if (sum1 + sum2) > 0 else 0

        # Erlang C 公式
        pc = ((a ** S) / _factorial(S)) * (1 / (1 - rho)) * p0 if rho < 1 else 1.0

        avg_Wq = pc / (S * mu - lam) if (S * mu - lam) > 0 else float('inf')
        avg_W = avg_Wq + 1 / mu
        avg_Lq = lam * avg_Wq
        avg_L = lam * avg_W
        pk = 0.0  # 无限容量无损失
        utilization = rho

    # ============ 蒙特卡罗仿真 ============
    rng = np.random.default_rng(seed)
    inter_arrival = rng.exponential(1.0 / lam, n_customers)
    service_times = rng.exponential(1.0 / mu, n_customers)
    arrival_times = np.cumsum(inter_arrival)

    departure_times = []
    wait_times = []
    rejected = 0
    server_free_at = np.zeros(S)
    queue = []  # (start_service_time, departure_time)

    for i in range(n_customers):
        at = arrival_times[i]

        # 清理已离开的
        queue = [(s, d) for s, d in queue if d > at]

        if capacity is not None and len(queue) >= capacity:
            rejected += 1
            continue

        # 找最早空闲服务台
        server_idx = np.argmin(server_free_at)
        start = max(at, server_free_at[server_idx])
        wait = start - at
        dep = start + service_times[i]

        wait_times.append(wait)
        departure_times.append(dep)
        server_free_at[server_idx] = dep
        queue.append((start, dep))

    sim_wq = np.mean(wait_times) if wait_times else 0
    sim_w = sim_wq + 1 / mu
    sim_pk = rejected / n_customers if n_customers > 0 else 0
    # 利用率 = 总服务时间 / (服务台数 × 总仿真时长)
    total_busy = float(np.sum(service_times[:len(departure_times)]))
    total_time = float(max(departure_times)) if departure_times else 0.0
    sim_util = total_busy / (S * total_time) if total_time > 0 else 0.0

    return {
        'rho': rho,
        'p0': p0,
        'pk': pk,
        'avg_queue_length': avg_Lq,
        'avg_system_length': avg_L,
        'avg_wait_time': avg_Wq,
        'avg_sojourn_time': avg_W,
        'utilization': utilization,
        'sim_avg_wait_time': float(sim_wq),
        'sim_avg_sojourn_time': float(sim_w),
        'sim_pk': float(sim_pk),
        'sim_utilization': float(sim_util),
        'n_customers': n_customers,
        'n_rejected': rejected,
    }


def random_walk(
    n_steps: int = 1000,
    dim: int = 1,
    step_size: float = 1.0,
    n_walkers: int = 1,
    seed: int | None = None,
) -> dict:
    """随机游走模拟

    Args:
        n_steps: 步数
        dim: 维度 (1D/2D/3D)
        step_size: 步长
        n_walkers: 游走者数量
        seed: 随机种子

    Returns:
        字典包含轨迹、最终距离、均方位移等
    """
    rng = np.random.default_rng(seed)

    # 生成步进方向
    steps = rng.standard_normal((n_walkers, n_steps, dim))
    steps = steps / np.linalg.norm(steps, axis=-1, keepdims=True) * step_size

    # 计算轨迹
    trajectories = np.cumsum(steps, axis=1)
    # 在开头插入原点
    origin = np.zeros((n_walkers, 1, dim))
    trajectories = np.concatenate([origin, trajectories], axis=1)

    # 最终距离
    final_distances = np.linalg.norm(trajectories[:, -1, :], axis=-1)

    # 均方位移 MSD = <|r(t) - r(0)|^2>
    displacements = trajectories[:, 1:, :] - trajectories[:, 0:1, :]
    msd = np.mean(np.sum(displacements**2, axis=-1), axis=0)

    return {
        "trajectories": trajectories,
        "final_distances": final_distances,
        "mean_final_distance": float(np.mean(final_distances)),
        "msd": msd,
        "n_steps": n_steps,
        "dim": dim,
    }
