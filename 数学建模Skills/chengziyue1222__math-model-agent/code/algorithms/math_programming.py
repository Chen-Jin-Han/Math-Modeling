"""
数学规划工具箱
==============
包含：线性规划、整数规划、目标规划、非线性规划

基于 scipy.optimize 实现，竞赛中常用于资源分配、生产计划、运输调度。

参考：Algorithms_MathModels/LinearProgramming/
      Algorithms_MathModels/IntegerProgramming/
      Algorithms_MathModels/NonLinearProgramming/
      Algorithms_MathModels/GoalProgramming/
"""

import numpy as np
from typing import Dict, Callable
from scipy.optimize import linprog, milp, LinearConstraint, Bounds, minimize


# ============================================================
# 1. 线性规划
# ============================================================
def linear_programming(
    c: np.ndarray,
    A_ub: np.ndarray | None = None,
    b_ub: np.ndarray | None = None,
    A_eq: np.ndarray | None = None,
    b_eq: np.ndarray | None = None,
    bounds: list | None = None,
    maximize: bool = False,
) -> Dict:
    """
    线性规划 (LP)

    标准形式（最小化）：min c^T x, s.t. A_ub x <= b_ub, A_eq x = b_eq, lb <= x <= ub

    竞赛中常用于：运输问题、指派问题、生产计划、投资组合。

    Parameters
    ----------
    c : np.ndarray, shape (n,)
        目标函数系数
    A_ub : np.ndarray or None
        不等式约束系数矩阵 (m, n)，每行一个约束
    b_ub : np.ndarray or None
        不等式约束右端向量
    A_eq : np.ndarray or None
        等式约束系数矩阵
    b_eq : np.ndarray or None
        等式约束右端向量
    bounds : list of tuples or None
        各变量的 (lower, upper) 界，默认 (0, None)
    maximize : bool
        True 时最大化（自动取反 c）

    Returns
    -------
    dict:
        - x: 最优解
        - fun: 最优目标值
        - success: 是否成功
        - message: 求解信息

    示例
    ----
    >>> # max z = 3x1 + 5x2, s.t. x1 <= 4, 2x2 <= 12, 3x1+5x2 <= 40
    >>> result = linear_programming(
    ...     c=[3, 5], A_ub=[[1,0],[0,2],[3,5]], b_ub=[4,12,40],
    ...     maximize=True
    ... )
    """
    c = np.asarray(c, dtype=float)
    if maximize:
        c = -c

    bounds_list = bounds if bounds is not None else [(0, None)] * len(c)

    result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds_list)
    opt_val = -result.fun if maximize else result.fun

    return {
        'x': result.x,
        'fun': opt_val,
        'success': result.success,
        'message': result.message,
        'maximize': maximize,
    }


# ============================================================
# 2. 整数规划
# ============================================================
def integer_programming(
    c: np.ndarray,
    A_ub: np.ndarray | None = None,
    b_ub: np.ndarray | None = None,
    A_eq: np.ndarray | None = None,
    b_eq: np.ndarray | None = None,
    bounds: list | None = None,
    integrality: np.ndarray | None = None,
    maximize: bool = False,
) -> Dict:
    """
    混合整数线性规划 (MILP)

    部分或全部变量要求取整数值。
    竞赛中常用于：选址问题、排班问题、背包问题、指派问题。

    Parameters
    ----------
    c : np.ndarray
        目标函数系数
    A_ub, b_ub : 不等式约束
    A_eq, b_eq : 等式约束
    bounds : list of tuples
        变量界
    integrality : np.ndarray or None
        各变量的整数性约束：
        0=连续，1=整数，2=半整数。None = 全部整数
    maximize : bool
        是否最大化

    Returns
    -------
    dict: x, fun, success, message
    """

    c = np.asarray(c, dtype=float)
    if maximize:
        c = -c

    n = len(c)
    if integrality is None:
        integrality = np.ones(n)

    constraints = []
    if A_ub is not None:
        constraints.append(LinearConstraint(np.asarray(A_ub), -np.inf, np.asarray(b_ub)))
    if A_eq is not None:
        constraints.append(LinearConstraint(np.asarray(A_eq), np.asarray(b_eq), np.asarray(b_eq)))

    if bounds is not None:
        lb = [b[0] if b[0] is not None else 0 for b in bounds]
        ub = [b[1] if b[1] is not None else np.inf for b in bounds]
        bounds_obj = Bounds(lb, ub)
    else:
        bounds_obj = Bounds(0, np.inf)

    result = milp(c, constraints=constraints, integrality=integrality, bounds=bounds_obj)
    opt_val = -result.fun if maximize else result.fun

    return {
        'x': result.x,
        'fun': opt_val,
        'success': result.success,
        'message': result.message if hasattr(result, 'message') else str(result.status),
    }


# ============================================================
# 3. 目标规划
# ============================================================
def goal_programming(
    targets: np.ndarray,
    A: np.ndarray,
    b: np.ndarray | None = None,
    priority_weights: np.ndarray | None = None,
    bounds: list | None = None,
) -> Dict:
    """
    目标规划 (Goal Programming)

    多目标问题转化为最小化偏差之和：
    min sum(w_i * (d_i+ + d_i-))
    s.t. A x + d_i- - d_i+ = targets_i

    Parameters
    ----------
    targets : np.ndarray, shape (k,)
        各目标的目标值
    A : np.ndarray, shape (k, n)
        目标约束系数矩阵
    b : np.ndarray or None
        右端约束（不含偏差变量）
    priority_weights : np.ndarray or None
        各目标的优先级权重（默认等权）
    bounds : list of tuples
        决策变量界

    Returns
    -------
    dict:
        - x: 决策变量最优解
        - deviations: 各目标的正负偏差 (d_minus, d_plus)
        - total_deviation: 总偏差
        - target_values: 各目标实际达到值
    """
    targets = np.asarray(targets, dtype=float).ravel()
    A = np.asarray(A, dtype=float)
    k = len(targets)
    n_vars = A.shape[1]

    if priority_weights is None:
        priority_weights = np.ones(k)

    # 构造 LP: min sum(w * (d+ + d-))
    # 决策变量: [x(n), d+(k), d-(k)]
    c = np.concatenate([np.zeros(n_vars), priority_weights, priority_weights])

    # 约束: A x + d- - d+ = targets  =>  [A, -I, I] [x, d+, d-]^T = targets
    A_eq = np.hstack([A, -np.eye(k), np.eye(k)])
    b_eq = targets

    bounds_list = bounds if bounds is not None else [(0, None)] * n_vars
    bounds_list = bounds_list + [(0, None)] * (2 * k)  # 偏差变量非负

    result = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds_list)

    x = result.x[:n_vars]
    d_plus = result.x[n_vars:n_vars + k]
    d_minus = result.x[n_vars + k:]
    target_values = A @ x

    return {
        'x': x,
        'deviations': {'d_minus': d_minus, 'd_plus': d_plus},
        'total_deviation': result.fun,
        'target_values': target_values,
        'targets': targets,
        'success': result.success,
    }


# ============================================================
# 4. 非线性规划
# ============================================================
def nonlinear_programming(
    objective: Callable,
    x0: np.ndarray,
    constraints: list | None = None,
    bounds: list | None = None,
    method: str = 'SLSQP',
    maximize: bool = False,
    options: dict | None = None,
) -> Dict:
    """
    非线性规划 (NLP)

    使用 scipy.optimize.minimize 求解。

    Parameters
    ----------
    objective : callable
        目标函数 f(x) -> float
    x0 : np.ndarray
        初始猜测值
    constraints : list of dicts or None
        约束条件，格式：
        - {'type': 'eq', 'fun': f}     等式约束 f(x)=0
        - {'type': 'ineq', 'fun': f}   不等式约束 f(x)>=0
    bounds : list of tuples or None
        变量界 [(lb, ub), ...]
    method : str
        求解方法：'SLSQP', 'COBYLA', 'trust-constr' 等
    maximize : bool
        是否最大化
    options : dict or None
        传给 minimize 的额外选项

    Returns
    -------
    dict:
        - x: 最优解
        - fun: 最优目标值
        - success: 是否收敛
        - message: 求解信息
        - nit: 迭代次数
    """
    if options is None:
        options = {'maxiter': 1000}

    def obj(x):
        val = objective(x)
        return -val if maximize else val

    result = minimize(obj, x0, method=method, bounds=bounds,
                      constraints=constraints or [], options=options)
    opt_val = -result.fun if maximize else result.fun

    return {
        'x': result.x,
        'fun': opt_val,
        'success': result.success,
        'message': result.message,
        'nit': result.nit if hasattr(result, 'nit') else None,
    }


# ============================================================
# 使用示例
# ============================================================
def example():
    """数学规划示例"""
    # 示例1: 线性规划
    print("=" * 60)
    print("示例1: 线性规划 — 资源分配")
    print("=" * 60)
    # max z = 3x1 + 5x2
    # s.t. x1 <= 4, 2x2 <= 12, 3x1+5x2 <= 40
    r = linear_programming(
        c=[3, 5],
        A_ub=[[1, 0], [0, 2], [3, 5]],
        b_ub=[4, 12, 40],
        maximize=True,
    )
    print(f"  最优解: x1={r['x'][0]:.2f}, x2={r['x'][1]:.2f}")
    print(f"  最优值: {r['fun']:.2f}")

    # 示例2: 整数规划
    print("\n" + "=" * 60)
    print("示例2: 整数规划 — 0-1背包")
    print("=" * 60)
    # max 6x1 + 5x2 + 4x3, s.t. 2x1+3x2+4x3 <= 7, xi in {0,1}
    r = integer_programming(
        c=[6, 5, 4],
        A_ub=[[2, 3, 4]],
        b_ub=[7],
        bounds=[(0, 1)] * 3,
        maximize=True,
    )
    print(f"  最优解: {r['x'].round(0).astype(int)}")
    print(f"  最优值: {r['fun']:.0f}")

    # 示例3: 非线性规划
    print("\n" + "=" * 60)
    print("示例3: 非线性规划 — Rosenbrock")
    print("=" * 60)
    rosen = lambda x: (1 - x[0])**2 + 100 * (x[1] - x[0]**2)**2
    r = nonlinear_programming(rosen, x0=[-1, 1])
    print(f"  最优解: x={r['x'].round(4)}")
    print(f"  最优值: {r['fun']:.6f}")


if __name__ == "__main__":
    example()
