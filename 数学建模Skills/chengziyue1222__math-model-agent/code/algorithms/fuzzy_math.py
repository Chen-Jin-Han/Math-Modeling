"""
模糊数学工具箱
==============
包含：模糊综合评价、多层次模糊评价、模糊聚类、隶属函数、模糊模式识别

参考：Algorithms_MathModels/FuzzyMathematicalModel模糊数学模型/
"""

import numpy as np
from typing import Tuple, Dict, List, Optional


# ============================================================
# 1. 常用隶属函数
# ============================================================
def trimf(x: np.ndarray, params: Tuple[float, float, float]) -> np.ndarray:
    """三角形隶属函数"""
    a, b, c = params
    return np.maximum(0, np.minimum((x - a) / (b - a + 1e-10), (c - x) / (c - b + 1e-10)))


def trapmf(x: np.ndarray, params: Tuple[float, float, float, float]) -> np.ndarray:
    """梯形隶属函数"""
    a, b, c, d = params
    return np.maximum(0, np.minimum(np.minimum((x - a) / (b - a + 1e-10), 1), (d - x) / (d - c + 1e-10)))


def gaussmf(x: np.ndarray, *args) -> np.ndarray:
    """高斯隶属函数。支持 gaussmf(x, mu, sigma) 或 gaussmf(x, (mu, sigma))。"""
    if len(args) == 1:
        mu, sigma = args[0]
    elif len(args) == 2:
        mu, sigma = args
    else:
        raise TypeError("gaussmf 需要 (mu, sigma) 或 ((mu, sigma),) 参数")
    return np.exp(-0.5 * ((x - mu) / sigma) ** 2)


# ============================================================
# 2. 模糊综合评价 (一级)
# ============================================================
def fuzzy_comprehensive_evaluation(weights: np.ndarray,
                                   R: np.ndarray = None,
                                   comment_set: Optional[List[str]] = None,
                                   return_dict: bool = False,
                                   verbose: bool = False) -> Dict:
    """
    一级模糊综合评价

    Parameters
    ----------
    weights : np.ndarray
        因素权重向量 (m,), 和为1；若 R 为 None 则 weights 实为评价矩阵
    R : np.ndarray, optional
        评价矩阵 (m, n), m个因素, n个评语等级
    comment_set : list, optional
        评语集, 如 ["优秀", "良好", "中等", "较差"]
    return_dict : bool
        返回完整 dict；False 时返回归一化评价向量
    verbose : bool
        是否打印结果

    Returns
    -------
    dict or np.ndarray : 综合评价结果
    """
    # 兼容 fuzzy_comprehensive_evaluation(R, weights) 调用顺序
    if R is None:
        raise ValueError("需要提供评价矩阵 R")
    a, b = np.asarray(weights, dtype=float), np.asarray(R, dtype=float)
    if a.ndim == 2 and b.ndim == 1:
        R, weights = a, b
    else:
        weights, R = a, b

    # 归一化权重
    weights = weights / weights.sum()

    # 模糊合成 (加权平均型)
    B = weights @ R

    # 归一化
    B_norm = B / B.sum() if B.sum() > 0 else B

    # 最大隶属度原则
    max_idx = np.argmax(B_norm)

    if comment_set is None:
        comment_set = [f"等级{i+1}" for i in range(len(B))]

    result = {
        'B': B,
        'B_normalized': B_norm,
        'max_grade': comment_set[max_idx],
        'max_membership': B_norm[max_idx],
        'comment_set': comment_set
    }

    if verbose:
        print("=" * 50)
        print("模糊综合评价结果")
        print("=" * 50)
        for i, (comment, val) in enumerate(zip(comment_set, B_norm)):
            bar = "█" * int(val * 40)
            print(f"  {comment}: {val:.4f} {bar}")
        print(f"  → 评价等级: {result['max_grade']}")

    if return_dict:
        return result
    return B_norm


# ============================================================
# 3. 多层次模糊综合评价
# ============================================================
def multi_level_fuzzy_evaluation(weights_list: List[np.ndarray],
                                 R_list: List[np.ndarray],
                                 comment_set: Optional[List[str]] = None) -> Dict:
    """
    多层次模糊综合评价 (二级及以上)

    Parameters
    ----------
    weights_list : list of np.ndarray
        各层权重: [准则层权重, 子准则层权重1, ...]
    R_list : list of np.ndarray
        各子因素的评价矩阵列表
    comment_set : list, optional
        评语集

    Returns
    -------
    dict : 最终评价结果
    """
    # 先对每个子因素集做一级评价
    B_list = []
    for weights, R in zip(weights_list[1:], R_list):
        w = weights / weights.sum()
        B = w @ R
        B_list.append(B)

    # 二级评价
    R_top = np.array(B_list)
    w_top = weights_list[0] / weights_list[0].sum()
    B_final = w_top @ R_top
    B_final_norm = B_final / B_final.sum() if B_final.sum() > 0 else B_final

    if comment_set is None:
        comment_set = [f"等级{i+1}" for i in range(len(B_final))]

    max_idx = np.argmax(B_final_norm)

    return {
        'B_final': B_final,
        'B_final_normalized': B_final_norm,
        'max_grade': comment_set[max_idx],
        'max_membership': B_final_norm[max_idx],
        'B_sub': B_list,
        'comment_set': comment_set
    }


# ============================================================
# 4. 模糊聚类
# ============================================================
def fuzzy_cmeans(X: np.ndarray, c: int, m: float = 2.0,
                 max_iter: int = 100, tol: float = 1e-6) -> Dict:
    """
    模糊 C 均值聚类 (FCM)

    Parameters
    ----------
    X : np.ndarray
        数据矩阵 (n, p)
    c : int
        聚类数
    m : float
        模糊指数 (m > 1, 通常取 2)
    max_iter : int
        最大迭代次数
    tol : float
        收敛阈值

    Returns
    -------
    dict : 聚类中心、隶属度矩阵、目标函数
    """
    n, p = X.shape
    U = np.random.rand(n, c)
    U = U / U.sum(axis=1, keepdims=True)

    J_history = []

    for iteration in range(max_iter):
        # 更新聚类中心
        Um = U ** m
        centers = (Um.T @ X) / Um.sum(axis=0)[:, None]

        # 更新隶属度
        dist = np.zeros((n, c))
        for k in range(c):
            diff = X - centers[k]
            dist[:, k] = np.sqrt(np.sum(diff**2, axis=1) + 1e-10)

        # 避免除零
        dist = np.maximum(dist, 1e-10)
        for i in range(n):
            for k in range(c):
                U[i, k] = 1.0 / sum((dist[i, k] / dist[i, j]) ** (2/(m-1)) for j in range(c))

        # 目标函数
        J = np.sum((U ** m) * (dist ** 2))
        J_history.append(J)

        if iteration > 0 and abs(J_history[-1] - J_history[-2]) < tol:
            break

    labels = np.argmax(U, axis=1)

    return {
        'centers': centers,
        'membership': U,
        'labels': labels,
        'J_history': J_history,
        'n_iter': len(J_history)
    }


# ============================================================
# 5. 模糊模式识别
# ============================================================
def fuzzy_pattern_recognition(samples: np.ndarray,
                              patterns: np.ndarray,
                              m: float = 2.0) -> Dict:
    """
    模糊模式识别 (择近原则)

    Parameters
    ----------
    samples : np.ndarray
        待识别样本 (n, p)
    patterns : np.ndarray
        已知模式 (c, p)
    m : float
        模糊指数

    Returns
    -------
    dict : 识别结果
    """
    n = samples.shape[0]
    c = patterns.shape[0]

    # 计算贴近度 (格贴近度)
    closeness = np.zeros((n, c))
    for i in range(n):
        for j in range(c):
            # 内积
            inner = np.max(np.minimum(samples[i], patterns[j]))
            # 外积
            outer = np.min(np.maximum(samples[i], patterns[j]))
            closeness[i, j] = 0.5 * (inner + (1 - outer))

    labels = np.argmax(closeness, axis=1)

    return {
        'labels': labels,
        'closeness': closeness
    }


# ============================================================
# 使用示例
# ============================================================
def example():
    """模糊数学示例"""
    # 示例1: 模糊综合评价
    print("=" * 60)
    print("示例1: 教学质量模糊综合评价")
    print("=" * 60)
    weights = np.array([0.3, 0.25, 0.25, 0.2])
    R = np.array([
        [0.4, 0.3, 0.2, 0.1],  # 教学态度
        [0.3, 0.4, 0.2, 0.1],  # 教学内容
        [0.2, 0.3, 0.3, 0.2],  # 教学方法
        [0.3, 0.3, 0.3, 0.1],  # 教学效果
    ])
    comment_set = ["优秀", "良好", "中等", "较差"]
    fuzzy_comprehensive_evaluation(weights, R, comment_set, return_dict=True, verbose=True)

    # 示例2: 模糊 C 均值聚类
    print("\n" + "=" * 60)
    print("示例2: 模糊 C 均值聚类")
    print("=" * 60)
    np.random.seed(42)
    X = np.vstack([
        np.random.randn(20, 2) + [2, 2],
        np.random.randn(20, 2) + [6, 6],
        np.random.randn(20, 2) + [2, 6],
    ])
    result = fuzzy_cmeans(X, c=3)
    print(f"  聚类中心:\n{result['centers'].round(2)}")
    print(f"  迭代次数: {result['n_iter']}")
    print(f"  最终目标函数: {result['J_history'][-1]:.4f}")


if __name__ == "__main__":
    example()
