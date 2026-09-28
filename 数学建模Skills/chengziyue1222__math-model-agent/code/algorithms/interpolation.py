"""
插值方法工具箱
==============
包含：拉格朗日插值、牛顿插值、分段线性插值、三次样条插值、二维插值

参考：Algorithms_MathModels/Interpolation/
"""

import numpy as np
from typing import Optional, Callable, Dict


# ============================================================
# 1. 拉格朗日插值
# ============================================================
def lagrange_interp(x: np.ndarray, y: np.ndarray, x_new: np.ndarray) -> np.ndarray:
    """
    拉格朗日插值多项式

    Parameters
    ----------
    x : np.ndarray
        已知节点 (n,)
    y : np.ndarray
        已知函数值 (n,)
    x_new : np.ndarray
        待插值点

    Returns
    -------
    y_new : np.ndarray
        插值结果
    """
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    n = len(x)
    x_new = np.atleast_1d(x_new)
    y_new = np.zeros_like(x_new, dtype=float)

    for k in range(n):
        # L_k(x) = Π_{j≠k} (x - x_j) / (x_k - x_j)
        Lk = np.ones_like(x_new)
        for j in range(n):
            if j != k:
                Lk *= (x_new - x[j]) / (x[k] - x[j])
        y_new += y[k] * Lk

    return y_new


# ============================================================
# 2. 牛顿插值
# ============================================================
def newton_divided_diff(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """计算牛顿均差表"""
    n = len(x)
    dd = np.zeros((n, n))
    dd[:, 0] = y
    for j in range(1, n):
        for i in range(n - j):
            dd[i, j] = (dd[i+1, j-1] - dd[i, j-1]) / (x[i+j] - x[i])
    return dd


def newton_interp(x: np.ndarray, y: np.ndarray, x_new: np.ndarray) -> np.ndarray:
    """
    牛顿插值多项式

    Parameters
    ----------
    x, y : np.ndarray
        已知节点和函数值
    x_new : np.ndarray
        待插值点

    Returns
    -------
    y_new : np.ndarray
        插值结果
    """
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    dd = newton_divided_diff(x, y)
    n = len(x)
    scalar = np.isscalar(x_new)
    x_new = np.atleast_1d(x_new)

    y_new = np.full_like(x_new, dd[0, 0], dtype=float)
    for k in range(1, n):
        term = dd[0, k]
        for j in range(k):
            term *= (x_new - x[j])
        y_new += term

    return float(y_new[0]) if scalar else y_new


# ============================================================
# 3. 分段线性插值
# ============================================================
def piecewise_linear_interp(x: np.ndarray, y: np.ndarray, x_new: np.ndarray) -> np.ndarray:
    """
    分段线性插值

    比全局多项式插值更稳定, 不会出现龙格现象
    """
    return np.interp(x_new, x, y)


# ============================================================
# 4. 三次样条插值
# ============================================================
def cubic_spline_interp(x: np.ndarray, y: np.ndarray, x_new: np.ndarray,
                        bc_type: str = 'natural') -> np.ndarray:
    """
    三次样条插值

    Parameters
    ----------
    x, y : np.ndarray
        已知节点和函数值
    x_new : np.ndarray
        待插值点
    bc_type : str
        边界条件: 'natural'(自然), 'clamped'(夹持)

    Returns
    -------
    y_new : np.ndarray
        插值结果
    """
    from scipy.interpolate import CubicSpline
    cs = CubicSpline(x, y, bc_type=bc_type)
    return cs(x_new)


# ============================================================
# 5. 二维插值
# ============================================================
def interp2d(x: np.ndarray, y: np.ndarray, z: np.ndarray,
             x_new: np.ndarray, y_new: np.ndarray,
             method: str = 'cubic') -> np.ndarray:
    """
    二维插值

    Parameters
    ----------
    x, y : np.ndarray
        网格坐标 (1D)
    z : np.ndarray
        网格函数值 (len(y), len(x))
    x_new, y_new : np.ndarray
        待插值点
    method : str
        插值方法: 'linear', 'cubic', 'nearest'

    Returns
    -------
    z_new : np.ndarray
        插值结果
    """
    from scipy.interpolate import RectBivariateSpline
    interp_func = RectBivariateSpline(y, x, z, kx=3 if method == 'cubic' else 1,
                                       ky=3 if method == 'cubic' else 1)
    return interp_func(y_new, x_new, grid=False)


# ============================================================
# 6. 插值方法对比
# ============================================================
def compare_methods(x: np.ndarray, y: np.ndarray, x_fine: np.ndarray,
                    true_func: Optional[Callable] = None) -> Dict:
    """
    对比不同插值方法的效果

    Returns
    -------
    dict : 各方法的插值结果和误差
    """
    methods = {
        '拉格朗日': lagrange_interp(x, y, x_fine),
        '牛顿': newton_interp(x, y, x_fine),
        '分段线性': piecewise_linear_interp(x, y, x_fine),
        '三次样条': cubic_spline_interp(x, y, x_fine),
    }

    results = {'methods': methods}

    if true_func is not None:
        y_true = true_func(x_fine)
        print("=" * 60)
        print("插值方法对比")
        print("=" * 60)
        for name, y_pred in methods.items():
            rmse = np.sqrt(np.mean((y_pred - y_true)**2))
            max_err = np.max(np.abs(y_pred - y_true))
            print(f"  {name:8s}: RMSE = {rmse:.6f}, 最大误差 = {max_err:.6f}")
            results[name] = {'rmse': rmse, 'max_error': max_err}

    return results


# ============================================================
# 使用示例
# ============================================================
def example():
    """插值方法示例"""
    print("=" * 60)
    print("示例: Runge 函数插值对比")
    print("=" * 60)

    # Runge 函数: f(x) = 1/(1+25x²), 容易出现龙格现象
    f = lambda x: 1 / (1 + 25 * x**2)

    # 等距节点
    x_nodes = np.linspace(-1, 1, 11)
    y_nodes = f(x_nodes)

    x_fine = np.linspace(-1, 1, 200)
    compare_methods(x_nodes, y_nodes, x_fine, true_func=f)


if __name__ == "__main__":
    example()
