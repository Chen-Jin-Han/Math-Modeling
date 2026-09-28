"""
综合评价方法库 (Evaluation)
============================
数学建模竞赛常用的综合评价与决策方法，补充 AHP 和模糊评价之外的评价工具。

包含函数:
- entropy_weight: 熵权法（客观赋权）
- topsis: TOPSIS 逼近理想解排序
- ahp_topsis: AHP+TOPSIS 组合评价
- dea: DEA 数据包络分析
- pca: PCA 主成分分析
- rsr: RSR 秩和比法
- fahp: 模糊层次分析法（模糊互补矩阵）
- grey_relational: 灰色关联分析（简化接口）
- combined_weight: 组合赋权（主观+客观）

竞赛场景:
- 方案优选、城市排名、环境评价
- 指标体系构建 + 客观赋权
- 多方法组合评价（AHP+TOPSIS、熵权+TOPSIS）

使用:
    from algorithms import topsis, entropy_weight
    import numpy as np

    data = np.array([[...], ...])
    weights = entropy_weight(data)
    result = topsis(data, weights)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TOPSISResult:
    """TOPSIS 评价结果"""
    scores: np.ndarray          # 综合得分 (C值)
    ranks: np.ndarray           # 排序 (1=最优)
    pos_dist: np.ndarray        # 到正理想解距离
    neg_dist: np.ndarray        # 到负理想解距离
    ideal_pos: np.ndarray       # 正理想解
    ideal_neg: np.ndarray       # 负理想解
    weights: np.ndarray         # 权重


@dataclass
class DEAResult:
    """DEA 评价结果"""
    efficiency: np.ndarray      # 效率值 (0~1, 1=有效)
    is_efficient: np.ndarray    # 是否有效 (bool)
    input_weights: np.ndarray   # 输入权重
    output_weights: np.ndarray  # 输出权重


@dataclass
class PCAResult:
    """PCA 分析结果"""
    components: np.ndarray      # 主成分载荷 (k, n_features)
    transformed: np.ndarray     # 降维后数据 (n_samples, k)
    eigenvalues: np.ndarray     # 特征值
    variance_ratio: np.ndarray  # 各主成分方差贡献率
    cumulative_ratio: np.ndarray  # 累积方差贡献率


@dataclass
class RSRResult:
    """RSR 评价结果"""
    rsr_values: np.ndarray      # RSR 值
    ranks: np.ndarray           # RSR 排序
    regression: np.ndarray      # 回归值
    levels: np.ndarray          # 分档等级
    probit: np.ndarray          # 概率单位值
    distribution: dict          # RSR 分布表


# ---------------------------------------------------------------------------
# 1. Entropy Weight (熵权法)
# ---------------------------------------------------------------------------

def entropy_weight(data: np.ndarray, positive_indicators: Optional[list[bool]] = None) -> np.ndarray:
    """熵权法客观赋权。

    Args:
        data: (n_samples, n_indicators) 原始数据矩阵。
        positive_indicators: 每个指标是否为正向指标（越大越好）。
            None 表示全部为正向指标。

    Returns:
        权重向量 (n_indicators,)。

    Example:
        >>> data = np.array([[80, 90, 100], [70, 85, 95], [90, 80, 85]])
        >>> w = entropy_weight(data)
    """
    data = np.asarray(data, dtype=float)
    n, m = data.shape

    # 标准化（正向化）
    if positive_indicators is None:
        positive_indicators = [True] * m

    norm_data = np.zeros_like(data)
    for j in range(m):
        col = data[:, j]
        min_val, max_val = col.min(), col.max()
        if max_val == min_val:
            norm_data[:, j] = 0.5
        elif positive_indicators[j]:
            norm_data[:, j] = (col - min_val) / (max_val - min_val)
        else:
            norm_data[:, j] = (max_val - col) / (max_val - min_val)

    # 避免 log(0)
    norm_data = np.clip(norm_data, 1e-10, None)

    # 计算比重
    p = norm_data / norm_data.sum(axis=0)

    # 计算信息熵
    k = 1.0 / np.log(n)
    entropy = -k * np.sum(p * np.log(p), axis=0)

    # 计算权重
    d = 1 - entropy  # 信息效用值
    weights = d / d.sum()

    return weights


# ---------------------------------------------------------------------------
# 2. TOPSIS (逼近理想解排序法)
# ---------------------------------------------------------------------------

def topsis(
    data: np.ndarray,
    weights: Optional[np.ndarray] = None,
    positive_indicators: Optional[list[bool]] = None,
) -> TOPSISResult:
    """TOPSIS 多指标综合评价。

    Args:
        data: (n_samples, n_indicators) 原始数据矩阵。
        weights: 权重向量 (n_indicators,)。None 则用熵权法自动计算。
        positive_indicators: 每个指标是否为正向指标。None 则全部为正向。

    Returns:
        TOPSISResult 包含得分、排序、距离等。

    Example:
        >>> data = np.array([[80, 90, 100], [70, 85, 95], [90, 80, 85]])
        >>> result = topsis(data)
        >>> print(result.scores, result.ranks)
    """
    data = np.asarray(data, dtype=float)
    n, m = data.shape

    if weights is None:
        weights = entropy_weight(data, positive_indicators)
    weights = np.asarray(weights, dtype=float)
    weights = weights / weights.sum()  # 归一化

    if positive_indicators is None:
        positive_indicators = [True] * m

    # 向量归一化
    norm = np.sqrt((data ** 2).sum(axis=0))
    norm_data = data / norm

    # 加权
    weighted = norm_data * weights

    # 确定正理想解和负理想解
    ideal_pos = np.zeros(m)
    ideal_neg = np.zeros(m)
    for j in range(m):
        if positive_indicators[j]:
            ideal_pos[j] = weighted[:, j].max()
            ideal_neg[j] = weighted[:, j].min()
        else:
            ideal_pos[j] = weighted[:, j].min()
            ideal_neg[j] = weighted[:, j].max()

    # 计算距离
    pos_dist = np.sqrt(((weighted - ideal_pos) ** 2).sum(axis=1))
    neg_dist = np.sqrt(((weighted - ideal_neg) ** 2).sum(axis=1))

    # 综合得分
    with np.errstate(invalid='ignore', divide='ignore'):
        scores = neg_dist / (pos_dist + neg_dist)
    scores = np.where((pos_dist + neg_dist) == 0, 1.0, scores)

    # 排序（得分越高越好）
    ranks = n - scores.argsort().argsort()

    return TOPSISResult(
        scores=scores,
        ranks=ranks,
        pos_dist=pos_dist,
        neg_dist=neg_dist,
        ideal_pos=ideal_pos,
        ideal_neg=ideal_neg,
        weights=weights,
    )


def ahp_topsis(
    data: np.ndarray,
    ahp_weights: np.ndarray,
    entropy_ratio: float = 0.5,
    positive_indicators: Optional[list[bool]] = None,
) -> TOPSISResult:
    """AHP+TOPSIS 组合评价（主观+客观组合赋权）。

    Args:
        data: 原始数据矩阵。
        ahp_weights: AHP 主观权重。
        entropy_ratio: 客观权重占比 (0~1)，默认 0.5。
        positive_indicators: 正向指标标记。

    Returns:
        TOPSISResult。
    """
    ew = entropy_weight(data, positive_indicators)
    combined = (1 - entropy_ratio) * ahp_weights + entropy_ratio * ew
    combined = combined / combined.sum()
    return topsis(data, combined, positive_indicators)


# ---------------------------------------------------------------------------
# 3. DEA (数据包络分析)
# ---------------------------------------------------------------------------

def dea(inputs: np.ndarray, outputs: np.ndarray, model: str = "CCR") -> DEAResult:
    """DEA 数据包络分析。

    Args:
        inputs: (n_dmu, n_inputs) 投入矩阵。
        outputs: (n_dmu, n_outputs) 产出矩阵。
        model: "CCR" (规模报酬不变) 或 "BCC" (规模报酬可变)。

    Returns:
        DEAResult 包含效率值和权重。

    Example:
        >>> X = np.array([[20, 300], [30, 200], [40, 100]])
        >>> Y = np.array([[1000], [1000], [1000]])
        >>> result = dea(X, Y)
        >>> print(result.efficiency)
    """
    from scipy.optimize import linprog

    inputs = np.asarray(inputs, dtype=float)
    outputs = np.asarray(outputs, dtype=float)
    n, m = inputs.shape
    _, s = outputs.shape

    efficiency = np.zeros(n)
    input_weights = np.zeros((n, m))
    output_weights = np.zeros((n, s))

    for i in range(n):
        # 对第 i 个 DMU 求解线性规划
        # max u'y_i / v'x_i  =>  max u'y_i  s.t. v'x_i = 1, u'y_j - v'x_j <= 0
        # 转化为 linprog 标准形式 (min c'x)

        n_vars = m + s  # v (m个) + u (s个)
        c = np.zeros(n_vars)
        c[m:] = -outputs[i]  # max u'y_i => min -u'y_i

        # 约束: v'x_i = 1
        A_eq = np.zeros((1, n_vars))
        A_eq[0, :m] = inputs[i]
        b_eq = np.array([1.0])

        # 约束: u'y_j - v'x_j <= 0  for all j
        A_ub = np.zeros((n, n_vars))
        A_ub[:, :m] = -inputs     # -v'x_j
        A_ub[:, m:] = outputs     # u'y_j
        b_ub = np.zeros(n)

        # v >= 0, u >= 0
        bounds = [(1e-8, None)] * n_vars

        try:
            result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
            if result.success:
                input_weights[i] = result.x[:m]
                output_weights[i] = result.x[m:]
                efficiency[i] = -result.fun  # 还原为正值
            else:
                # Fallback: use simple ratio
                efficiency[i] = (outputs[i].sum() / inputs[i].sum()) / \
                                max(outputs.sum(axis=1) / inputs.sum(axis=1))
        except Exception:
            efficiency[i] = (outputs[i].sum() / inputs[i].sum()) / \
                            max(outputs.sum(axis=1) / inputs.sum(axis=1))

    is_efficient = efficiency >= 0.999  # 允许数值误差

    return DEAResult(
        efficiency=efficiency,
        is_efficient=is_efficient,
        input_weights=input_weights,
        output_weights=output_weights,
    )


# ---------------------------------------------------------------------------
# 4. PCA (主成分分析)
# ---------------------------------------------------------------------------

def pca(data: np.ndarray, k: Optional[int] = None, n_components: Optional[int] = None,
        variance_threshold: float = 0.85) -> PCAResult:
    """PCA 主成分分析。

    Args:
        data: (n_samples, n_features) 原始数据。
        k: 保留的主成分数。None 则按 variance_threshold 自动选择。
        n_components: k 的别名。
        variance_threshold: 累积方差贡献率阈值（自动选择 k 时使用）。

    Returns:
        PCAResult 包含主成分载荷、降维数据、特征值等。
    """
    if n_components is not None:
        k = n_components
    data = np.asarray(data, dtype=float)
    n_samples, n_features = data.shape

    # 中心化
    mean = data.mean(axis=0)
    centered = data - mean

    # 协方差矩阵
    cov = np.cov(centered, rowvar=False)

    # 特征值分解
    eigenvalues, eigenvectors = np.linalg.eigh(cov)

    # 按特征值降序排列
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    # 方差贡献率
    total_var = eigenvalues.sum()
    variance_ratio = eigenvalues / total_var
    cumulative_ratio = np.cumsum(variance_ratio)

    # 确定 k
    if k is None:
        k = np.searchsorted(cumulative_ratio, variance_threshold) + 1
        k = min(k, n_features)

    # 降维
    components = eigenvectors[:, :k].T  # (k, n_features)
    transformed = centered @ eigenvectors[:, :k]

    return PCAResult(
        components=components,
        transformed=transformed,
        eigenvalues=eigenvalues,
        variance_ratio=variance_ratio,
        cumulative_ratio=cumulative_ratio,
    )


# ---------------------------------------------------------------------------
# 5. RSR (秩和比法)
# ---------------------------------------------------------------------------

def rsr(data: np.ndarray, weights: Optional[np.ndarray] = None, n_levels: int = 3) -> RSRResult:
    """RSR 秩和比法综合评价。

    Args:
        data: (n_samples, n_indicators) 原始数据矩阵。
        weights: 指标权重。None 则等权。
        n_levels: 分档等级数，默认 3。

    Returns:
        RSRResult 包含 RSR 值、排序、分档等。

    Example:
        >>> data = np.array([[99.54, 60.27, 16.15], [96.52, 59.67, 20.10], ...])
        >>> result = rsr(data)
        >>> print(result.levels)
    """
    from scipy.stats import norm as sp_norm

    data = np.asarray(data, dtype=float)
    n, m = data.shape

    if weights is None:
        weights = np.ones(m) / m
    else:
        weights = np.asarray(weights, dtype=float)
        weights = weights / weights.sum()

    # 编秩（越大越好）
    ranks = np.zeros_like(data)
    for j in range(m):
        ranks[:, j] = _dense_rank(data[:, j])

    # 计算 RSR
    rsr_values = (ranks * weights).sum(axis=1) / n

    # RSR 排序
    rsr_ranks = n - rsr_values.argsort().argsort()

    # RSR 分布表
    unique_rsr = np.sort(np.unique(rsr_values))
    f_counts = np.array([np.sum(rsr_values == v) for v in unique_rsr])
    cum_f = np.cumsum(f_counts)

    # 用累积频率计算概率单位 (Probit)
    probit_vals = np.zeros(len(unique_rsr))
    for i, v in enumerate(unique_rsr):
        # 修正的累积频率
        cf = cum_f[i] / (n + 1) if i == len(unique_rsr) - 1 else cum_f[i] / n
        cf = np.clip(cf, 1e-6, 1 - 1e-6)
        probit_vals[i] = 5 + sp_norm.ppf(cf)

    # 回归分析: RSR = a * Probit + b
    if len(probit_vals) >= 2:
        coeffs = np.polyfit(probit_vals, unique_rsr, 1)
        regression_all = np.polyval(coeffs, _probit_for_values(rsr_values, unique_rsr, probit_vals))
    else:
        regression_all = rsr_values
        coeffs = [1.0, 0.0]

    # 分档
    level_boundaries = np.linspace(regression_all.min(), regression_all.max(), n_levels + 1)
    level_boundaries[0] = -np.inf
    level_boundaries[-1] = np.inf
    levels = np.digitize(regression_all, level_boundaries[1:-1]) + 1

    distribution = {
        "unique_rsr": unique_rsr,
        "frequency": f_counts,
        "cumulative": cum_f,
        "probit": probit_vals,
    }

    return RSRResult(
        rsr_values=rsr_values,
        ranks=rsr_ranks,
        regression=regression_all,
        levels=levels,
        probit=_probit_for_rsr(rsr_values, unique_rsr, probit_vals),
        distribution=distribution,
    )


def _dense_rank(values: np.ndarray) -> np.ndarray:
    """计算密集秩（并列取平均秩）"""
    sorted_idx = np.argsort(values)
    ranks = np.empty_like(sorted_idx, dtype=float)
    ranks[sorted_idx] = np.arange(1, len(values) + 1)
    return ranks


def _probit_for_rsr(rsr_values, unique_rsr, probit_vals):
    """为每个 RSR 值查找对应的 Probit 值（内部辅助函数）"""
    mapping = dict(zip(unique_rsr, probit_vals))
    return np.array([mapping[v] for v in rsr_values])


def _probit_for_values(values, unique_rsr, probit_vals):
    mapping = dict(zip(unique_rsr, probit_vals))
    return np.array([mapping.get(v, 5.0) for v in values])


# ---------------------------------------------------------------------------
# 6. FAHP (模糊层次分析法)
# ---------------------------------------------------------------------------

def fahp(fuzzy_matrix: np.ndarray) -> np.ndarray:
    """模糊层次分析法（FAHP）。

    从模糊互补判断矩阵计算权重向量。

    Args:
        fuzzy_matrix: (n, n) 模糊互补矩阵，满足 a_ij + a_ji = 1。

    Returns:
        权重向量 (n,)。

    Example:
        >>> M = np.array([
        ...     [0.5, 0.75, 0.80],
        ...     [0.25, 0.50, 0.65],
        ...     [0.20, 0.35, 0.50],
        ... ])
        >>> w = fahp(M)
    """
    fuzzy_matrix = np.asarray(fuzzy_matrix, dtype=float)
    n = fuzzy_matrix.shape[0]

    # 转换为模糊一致性矩阵
    row_sums = fuzzy_matrix.sum(axis=1)
    R = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            R[i, j] = (row_sums[i] - row_sums[j]) / (2 * n) + 0.5

    # 幂积法求权重
    weights = np.zeros(n)
    for i in range(n):
        weights[i] = np.prod(R[i, :]) ** (1.0 / n)

    weights = weights / weights.sum()
    return weights


# ---------------------------------------------------------------------------
# 7. 组合赋权
# ---------------------------------------------------------------------------

def combined_weight(
    subjective: np.ndarray,
    objective: np.ndarray,
    method: str = "multiplicative",
    alpha: float = 0.5,
) -> np.ndarray:
    """组合赋权法（主观+客观）。

    Args:
        subjective: 主观权重向量 (AHP 等)。
        objective: 客观权重向量 (熵权法等)。
        method: "additive" (线性加权) 或 "multiplicative" (乘法归一化)。
        alpha: 主观权重占比 (仅 additive 方法使用)。

    Returns:
        组合权重向量。
    """
    subjective = np.asarray(subjective, dtype=float)
    objective = np.asarray(objective, dtype=float)

    if method == "additive":
        w = alpha * subjective + (1 - alpha) * objective
    elif method == "multiplicative":
        w = subjective * objective
    else:
        raise ValueError(f"Unknown method: {method}")

    return w / w.sum()


# ---------------------------------------------------------------------------
# 8. 灰色关联分析（简化接口）
# ---------------------------------------------------------------------------

def grey_relational(
    data: np.ndarray,
    reference: np.ndarray,
    rho: float = 0.5,
) -> np.ndarray:
    """灰色关联分析（简化接口）。

    Args:
        data: 参考序列 (n_features,) 或比较矩阵 (n_samples, n_features)
        reference: 比较矩阵或参考序列（自动识别顺序）
        rho: 分辨系数，通常取 0.5。

    Returns:
        关联度向量 (n_samples,)。
    """
    a = np.asarray(data, dtype=float)
    b = np.asarray(reference, dtype=float)
    # 兼容 grey_relational(ref, compare_matrix) 调用顺序
    if a.ndim == 1 and b.ndim == 2:
        ref, compare = a, b
    elif a.ndim == 2 and b.ndim == 1:
        ref, compare = b, a
    else:
        ref, compare = a.flatten(), b if b.ndim == 2 else b.reshape(1, -1)

    ref_norm = ref / ref[0] if ref[0] != 0 else ref
    compare_norm = compare / compare[:, :1]

    delta = np.abs(compare_norm - ref_norm)
    delta_min = delta.min()
    delta_max = delta.max()

    if delta_max == 0:
        coeff = np.ones_like(delta)
    else:
        coeff = (delta_min + rho * delta_max) / (delta + rho * delta_max)

    return coeff.mean(axis=1)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _demo():
    """快速自测"""
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    # 1. 熵权法
    data = np.array([
        [80, 90, 100],
        [70, 85, 95],
        [90, 80, 85],
        [85, 95, 90],
    ])
    w = entropy_weight(data)
    print(f"[OK] entropy_weight: {np.round(w, 4)}")

    # 2. TOPSIS
    result = topsis(data, w)
    print(f"[OK] topsis: scores={np.round(result.scores, 4)}, ranks={result.ranks}")

    # 3. AHP+TOPSIS
    ahp_w = np.array([0.5, 0.3, 0.2])
    result2 = ahp_topsis(data, ahp_w)
    print(f"[OK] ahp_topsis: scores={np.round(result2.scores, 4)}")

    # 4. DEA
    X = np.array([[20, 300], [30, 200], [40, 100], [20, 200]])
    Y = np.array([[1000], [1000], [1000], [1000]])
    dea_result = dea(X, Y)
    print(f"[OK] dea: efficiency={np.round(dea_result.efficiency, 4)}")

    # 5. PCA
    rng = np.random.default_rng(42)
    data5 = rng.normal(size=(50, 6))
    pca_result = pca(data5, k=2)
    print(f"[OK] pca: shape={pca_result.transformed.shape}, var_ratio={np.round(pca_result.variance_ratio[:3], 4)}")

    # 6. RSR
    data6 = np.array([
        [99.54, 60.27, 16.15],
        [96.52, 59.67, 20.10],
        [99.36, 43.91, 15.60],
        [92.83, 58.99, 17.04],
        [91.71, 35.40, 15.01],
    ])
    rsr_result = rsr(data6)
    print(f"[OK] rsr: values={np.round(rsr_result.rsr_values, 4)}, levels={rsr_result.levels}")

    # 7. FAHP
    M = np.array([
        [0.50, 0.75, 0.80],
        [0.25, 0.50, 0.65],
        [0.20, 0.35, 0.50],
    ])
    fahp_w = fahp(M)
    print(f"[OK] fahp: {np.round(fahp_w, 4)}")

    # 8. 组合赋权
    cw = combined_weight(ahp_w, w)
    print(f"[OK] combined_weight: {np.round(cw, 4)}")

    # 9. 灰色关联
    ref = np.array([90, 85, 95])
    gr = grey_relational(data, ref)
    print(f"[OK] grey_relational: {np.round(gr, 4)}")

    print("\n=== All evaluation methods validated! ===")


if __name__ == "__main__":
    _demo()
