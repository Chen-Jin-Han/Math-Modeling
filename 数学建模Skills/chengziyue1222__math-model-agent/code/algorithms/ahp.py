"""
AHP 层次分析法 (Analytic Hierarchy Process)
============================================
通过构造判断矩阵，将定性决策转化为定量权重排序。

包含函数:
- ahp_weight: 计算权重向量 + 一致性检验 (CR < 0.1)
- consistency_check: 单独检验判断矩阵一致性
- hierarchical_ahp: 多层次 AHP 综合权重

竞赛场景:
- 多准则决策（选址、评价、方案优选）
- 与 TOPSIS 结合: ahp_topsis（见 evaluation.py）
- 与模糊评价结合: fuzzy_comprehensive_evaluation（见 fuzzy_math.py）

参考: Algorithms_MathModels/AHP层次分析法/
"""

import numpy as np
from typing import Tuple, List, Dict


# ============================================================
# 1. 随机一致性指标 RI 表 (1-15 阶)
# ============================================================
RI_TABLE = {
    1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12,
    6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49,
    11: 1.51, 12: 1.54, 13: 1.56, 14: 1.58, 15: 1.59
}


def ahp_weight(A: np.ndarray) -> Tuple[np.ndarray, float, float, bool]:
    """
    计算 AHP 权重向量

    Parameters
    ----------
    A : np.ndarray
        n×n 判断矩阵 (正互反矩阵, a_ji = 1/a_ij)

    Returns
    -------
    w : np.ndarray
        归一化权重向量 (和为1)
    lambda_max : float
        最大特征值
    CR : float
        一致性比率
    passed : bool
        一致性是否通过 (CR < 0.1)
    """
    n = A.shape[0]
    assert A.shape[0] == A.shape[1], "判断矩阵必须是方阵"

    # 单位矩阵：各准则同等重要，权重均匀
    if np.allclose(A, np.eye(n)):
        w = np.ones(n) / n
        lambda_max = float(n)
        CR = 0.0
        return w, lambda_max, CR, True

    # 求特征值和特征向量
    eigvals, eigvecs = np.linalg.eig(A)
    # 取实部最大特征值
    real_mask = np.abs(eigvals.imag) < 1e-10
    real_eigvals = eigvals[real_mask].real
    lambda_max = np.max(real_eigvals)

    # 对应特征向量
    idx = np.argmax(eigvals.real)
    w = eigvecs[:, idx].real
    w = w / w.sum()  # 归一化

    # 一致性检验
    CI = (lambda_max - n) / (n - 1) if n > 1 else 0
    RI = RI_TABLE.get(n, 1.59)
    CR = CI / RI if RI > 0 else 0
    passed = CR < 0.1

    return w, lambda_max, CR, passed


def consistency_check(A: np.ndarray, verbose: bool = True) -> Dict:
    """
    完整的一致性检验报告

    Parameters
    ----------
    A : np.ndarray
        判断矩阵
    verbose : bool
        是否打印详细信息

    Returns
    -------
    dict : 包含权重、最大特征值、CI、CR、是否通过
    """
    n = A.shape[0]
    w, lambda_max, CR, passed = ahp_weight(A)

    CI = (lambda_max - n) / (n - 1) if n > 1 else 0
    RI = RI_TABLE.get(n, 1.59)

    result = {
        'weights': w,
        'lambda_max': lambda_max,
        'CI': CI,
        'RI': RI,
        'CR': CR,
        'passed': passed,
        'n': n
    }

    if verbose:
        print("=" * 50)
        print("AHP 一致性检验报告")
        print("=" * 50)
        print(f"矩阵阶数 n = {n}")
        print(f"最大特征值 λ_max = {lambda_max:.4f}")
        print(f"一致性指标 CI = {CI:.4f}")
        print(f"随机一致性指标 RI = {RI:.4f}")
        print(f"一致性比率 CR = {CR:.4f}")
        print(f"一致性检验: {'✅ 通过 (CR < 0.1)' if passed else '❌ 未通过 (CR ≥ 0.1)'}")
        print("-" * 50)
        print("权重向量:")
        for i, wi in enumerate(w):
            print(f"  w{i+1} = {wi:.4f}")
        print("=" * 50)

    return result


def build_judgment_matrix(n: int, scale_func=None) -> np.ndarray:
    """
    交互式构建判断矩阵

    Parameters
    ----------
    n : int
        因素个数
    scale_func : callable, optional
        自定义评分函数，默认使用 1-9 标度

    Returns
    -------
    A : np.ndarray
        n×n 判断矩阵
    """
    A = np.ones((n, n))
    print(f"请依次输入 {n*(n-1)//2} 个比较值 (1-9 标度):")
    print("  1 = 同等重要, 3 = 稍微重要, 5 = 明显重要")
    print("  7 = 强烈重要, 9 = 极端重要, 2/4/6/8 = 中间值")
    print("  若 i 不如 j 重要，输入倒数 (如 1/3)")

    for i in range(n):
        for j in range(i + 1, n):
            while True:
                try:
                    val = float(input(f"  因素{i+1} vs 因素{j+1}: "))
                    A[i][j] = val
                    A[j][i] = 1.0 / val
                    break
                except (ValueError, ZeroDivisionError):
                    print("  输入无效，请重新输入")

    return A


def hierarchical_ahp(goal_weights: np.ndarray,
                     criteria_weights: List[np.ndarray],
                     alternatives: List[np.ndarray]) -> np.ndarray:
    """
    层次分析法 — 多层次综合排序

    Parameters
    ----------
    goal_weights : np.ndarray
        准则层对目标层的权重 (m,)
    criteria_weights : list of np.ndarray
        每个准则下方案层的权重列表, 每个 (n,)
    alternatives : list of np.ndarray
        同 criteria_weights, 也可以直接传方案层权重

    Returns
    -------
    scores : np.ndarray
        各方案的综合得分 (n,)
    """
    # 构造方案层权重矩阵: (m, n) — m个准则, n个方案
    W = np.array(criteria_weights)  # (m, n)
    # 综合得分 = 准则权重 @ 方案权重矩阵
    scores = goal_weights @ W
    return scores


# ============================================================
# 使用示例
# ============================================================
def example():
    """AHP 完整示例: 旅游目的地选择"""
    print("=" * 60)
    print("示例：选择最佳旅游目的地")
    print("=" * 60)

    # 准则层：景色、费用、居住、饮食、旅途
    criteria_names = ["景色", "费用", "居住", "饮食", "旅途"]
    A_criteria = np.array([
        [1,   1/2,  4,   3,   3  ],
        [2,   1,    7,   5,   5  ],
        [1/4, 1/7,  1,   1/2, 1/3],
        [1/3, 1/5,  2,   1,   1  ],
        [1/3, 1/5,  3,   1,   1  ],
    ])

    print("\n【准则层判断矩阵】")
    result = consistency_check(A_criteria)

    # 方案层对每个准则的判断矩阵
    alt_names = ["桂林", "北戴河", "张家界"]
    A_alt_scenery = np.array([  # 景色
        [1, 2, 5],
        [1/2, 1, 2],
        [1/5, 1/2, 1]
    ])
    A_alt_cost = np.array([  # 费用
        [1, 1/3, 1/8],
        [3, 1, 1/3],
        [8, 3, 1]
    ])
    A_alt_stay = np.array([  # 居住
        [1, 1, 3],
        [1, 1, 3],
        [1/3, 1/3, 1]
    ])
    A_alt_food = np.array([  # 饮食
        [1, 3, 4],
        [1/3, 1, 1],
        [1/4, 1, 1]
    ])
    A_alt_travel = np.array([  # 旅途
        [1, 1, 1/4],
        [1, 1, 1/4],
        [4, 4, 1]
    ])

    alt_matrices = [A_alt_scenery, A_alt_cost, A_alt_stay, A_alt_food, A_alt_travel]

    print("\n【方案层判断矩阵 + 一致性检验】")
    alt_weights = []
    for name, A_alt in zip(criteria_names, alt_matrices):
        print(f"\n--- {name}准则下 ---")
        w, lmax, CR, passed = ahp_weight(A_alt)
        alt_weights.append(w)
        print(f"  权重: {[f'{x:.3f}' for x in w]}, CR={CR:.4f} {'✅' if passed else '❌'}")

    # 综合排序
    scores = hierarchical_ahp(result['weights'], alt_weights)
    print("\n【综合排序结果】")
    ranking = np.argsort(-scores)
    for rank, idx in enumerate(ranking):
        print(f"  第{rank+1}名: {alt_names[idx]} (得分: {scores[idx]:.4f})")

    return scores


if __name__ == "__main__":
    example()
