"""
灰色系统完整工具箱
==================
包含：GM(1,1) 预测、灰色关联分析、灰色聚类、GM(2,1)、Verhulst 模型

参考：Algorithms_MathModels/GreySystem灰色系统/
"""

import numpy as np
from typing import List, Dict, Optional


# ============================================================
# 1. GM(1,1) 灰色预测
# ============================================================
def gm11_predict(x0: np.ndarray, predict_n: int = 5, predict_count: Optional[int] = None) -> Dict:
    """
    GM(1,1) 灰色预测模型

    Parameters
    ----------
    x0 : np.ndarray
        原始序列 (非负, 长度 >= 4)
    predict_n : int
        预测步数
    predict_count : int, optional
        predict_n 的别名（兼容旧接口）

    Returns
    -------
    dict : 包含预测值、参数、精度检验
    """
    if predict_count is not None:
        predict_n = predict_count
    x0 = np.array(x0, dtype=float)
    n = len(x0)

    # 1. 级比检验
    lambda_k = x0[:-1] / x0[1:]
    lambda_min, lambda_max = lambda_k.min(), lambda_k.max()
    exp_range = (np.exp(-2/(n+1)), np.exp(2/(n+1)))
    ratio_ok = exp_range[0] <= lambda_min and lambda_max <= exp_range[1]

    # 2. 一次累加生成 (1-AGO)
    x1 = np.cumsum(x0)

    # 3. 紧邻均值生成
    z1 = 0.5 * (x1[:-1] + x1[1:])

    # 4. 最小二乘法求参数 a, b
    B = np.column_stack([-z1, np.ones(n-1)])
    Y = x0[1:]
    params = np.linalg.lstsq(B, Y, rcond=None)[0]
    a, b = params[0], params[1]

    # 5. 时间响应函数
    # x1_hat(k+1) = (x0(1) - b/a) * exp(-a*k) + b/a
    c = x0[0] - b / a
    x1_hat = np.zeros(n + predict_n)
    for k in range(n + predict_n):
        x1_hat[k] = c * np.exp(-a * k) + b / a

    # 6. 还原预测值
    x0_hat = np.zeros(n + predict_n)
    x0_hat[0] = x0[0]
    for k in range(1, n + predict_n):
        x0_hat[k] = x1_hat[k] - x1_hat[k-1]

    # 7. 残差检验
    residuals = x0 - x0_hat[:n]
    relative_errors = np.abs(residuals) / x0

    # 8. 后验差比检验
    S1 = np.std(x0, ddof=1)
    S2 = np.std(residuals, ddof=1)
    C = S2 / S1  # 后验差比值
    P = np.mean(np.abs(residuals - residuals.mean()) < 0.6745 * S1)  # 小误差概率

    # 精度等级
    if C < 0.35 and P > 0.95:
        grade = "好"
    elif C < 0.5 and P > 0.8:
        grade = "合格"
    elif C < 0.65 and P > 0.7:
        grade = "勉强合格"
    else:
        grade = "不合格"

    return {
        'x0_hat': x0_hat,
        'x1_hat': x1_hat,
        'a': a, 'b': b,
        'residuals': residuals,
        'relative_errors': relative_errors,
        'mean_error': np.mean(relative_errors),
        'C': C, 'P': P, 'grade': grade,
        'ratio_check': ratio_ok,
        'lambda_range': (lambda_min, lambda_max),
        'exp_range': exp_range,
        'predictions': x0_hat[n:],
        'predicted': x0_hat[n:],
        'fitted': x0_hat[:n],
    }


# ============================================================
# 2. 灰色关联分析
# ============================================================
def grey_correlation(reference: np.ndarray,
                     compare: np.ndarray,
                     rho: float = 0.5) -> np.ndarray:
    """
    灰色关联度分析

    Parameters
    ----------
    reference : np.ndarray
        参考序列 (m×p), m个指标, p个时间点
    compare : np.ndarray
        比较序列 (n×p), n个比较对象
    rho : float
        分辨系数, 通常取 0.5

    Returns
    -------
    r : np.ndarray
        关联度向量 (n,), 值越大关联越强
    """
    reference = np.atleast_1d(reference).astype(float)
    compare = np.atleast_1d(compare).astype(float)
    if reference.ndim == 1:
        reference = reference.reshape(1, -1)
    if compare.ndim == 1:
        compare = compare.reshape(1, -1)

    # 无量纲化 (初值化)
    ref_norm = reference / reference[:, 0:1]
    cmp_norm = compare / compare[:, 0:1]

    m1 = ref_norm.shape[0]
    m2 = cmp_norm.shape[0]
    r = np.zeros(m2)

    for i in range(m1):
        # 计算差值矩阵
        delta = np.abs(cmp_norm - ref_norm[i])
        delta_min = delta.min()
        delta_max = delta.max()

        # 关联系数
        if delta_max == 0:
            xi = np.ones_like(delta)
        else:
            xi = (delta_min + rho * delta_max) / (delta + rho * delta_max)
        r += xi.mean(axis=1)

    r = r / m1  # 平均关联度
    return r


def grey_correlation_rank(reference: np.ndarray,
                          compare: np.ndarray,
                          names: Optional[List[str]] = None,
                          rho: float = 0.5,
                          verbose: bool = False) -> np.ndarray:
    """
    灰色关联分析 + 排序

    Returns
    -------
    ranking : np.ndarray
        按关联度降序排列的对象索引
    """
    r = grey_correlation(reference, compare, rho)
    ranking = np.argsort(-r)

    if verbose and names is not None:
        print("=" * 50)
        print("灰色关联分析结果")
        print("=" * 50)
        for rank, idx in enumerate(ranking):
            print(f"  第{rank+1}名: {names[idx]} (关联度: {r[idx]:.4f})")

    return ranking


# ============================================================
# 3. 灰色聚类
# ============================================================
def grey_clustering(data: np.ndarray,
                    thresholds: np.ndarray,
                    whitenization_functions: Optional[List] = None) -> np.ndarray:
    """
    灰色聚类 (三角白化权函数)

    Parameters
    ----------
    data : np.ndarray
        数据矩阵 (n_objects, n_indicators)
    thresholds : np.ndarray
        各灰类的阈值 (n_classes, n_indicators)
    whitenization_functions : list, optional
        自定义白化权函数列表

    Returns
    -------
    labels : np.ndarray
        聚类标签 (n_objects,)
    """
    n_objects, n_indicators = data.shape
    n_classes = thresholds.shape[0]

    # 计算白化权函数值
    sigma = np.zeros((n_objects, n_classes))

    for k in range(n_classes):
        for j in range(n_indicators):
            lam = thresholds[k, j]  # 阈值
            for i in range(n_objects):
                x = data[i, j]
                if k == 0:
                    # 第1灰类: 偏小型
                    if x <= lam:
                        sigma[i, k] += 1.0
                    elif k + 1 < n_classes:
                        sigma[i, k] += max(0, (thresholds[k+1, j] - x) / (thresholds[k+1, j] - lam))
                elif k == n_classes - 1:
                    # 最后灰类: 偏大型
                    if x >= lam:
                        sigma[i, k] += 1.0
                    else:
                        sigma[i, k] += max(0, (x - thresholds[k-1, j]) / (lam - thresholds[k-1, j]))
                else:
                    # 中间灰类: 三角形
                    if thresholds[k-1, j] <= x <= lam:
                        sigma[i, k] += (x - thresholds[k-1, j]) / (lam - thresholds[k-1, j])
                    elif lam < x <= thresholds[k+1, j]:
                        sigma[i, k] += (thresholds[k+1, j] - x) / (thresholds[k+1, j] - lam)

    # 归一化
    sigma_sum = sigma.sum(axis=1, keepdims=True)
    sigma_norm = sigma / sigma_sum

    labels = np.argmax(sigma_norm, axis=1)
    return labels


# ============================================================
# 4. GM(2,1) 模型
# ============================================================
def gm21_predict(x0: np.ndarray, predict_n: int = 5) -> Dict:
    """
    GM(2,1) 灰色预测模型 (二阶微分方程)

    适用场景：数据波动较大, GM(1,1) 效果不好时
    """
    x0 = np.array(x0, dtype=float)
    n = len(x0)

    # 1-AGO
    x1 = np.cumsum(x0)
    # 1-IAGO
    alpha_x0 = np.diff(x0)

    # 紧邻均值
    z1 = 0.5 * (x1[:-1] + x1[1:])

    # 最小二乘: d²x1/dt² + a1*dx1/dt + a2*x1 = b
    B = np.column_stack([-x0[1:], -z1, np.ones(n-1)])
    Y = alpha_x0
    params = np.linalg.lstsq(B, Y, rcond=None)[0]
    a1, a2, b = params

    # 求解二阶微分方程 (数值解)
    from scipy.integrate import solve_ivp
    def ode(t, y):
        return [y[1], -a1*y[1] - a2*y[0] + b]

    t_span = (0, n + predict_n - 1)
    t_eval = np.arange(n + predict_n)
    sol = solve_ivp(ode, t_span, [x0[0], x0[0]], t_eval=t_eval, method='RK45')
    x1_hat = sol.y[0]

    # 还原
    x0_hat = np.zeros(n + predict_n)
    x0_hat[0] = x0[0]
    x0_hat[1:] = np.diff(x1_hat)

    # 残差
    residuals = x0 - x0_hat[:n]

    return {
        'x0_hat': x0_hat,
        'a1': a1, 'a2': a2, 'b': b,
        'residuals': residuals,
        'predictions': x0_hat[n:]
    }


# ============================================================
# 5. Verhulst 模型 (S 型增长)
# ============================================================
def verhulst_predict(x0: np.ndarray, predict_n: int = 5) -> Dict:
    """
    Verhulst 灰色预测模型

    适用场景：S 型增长数据 (如人口增长、产品生命周期)
    """
    x0 = np.array(x0, dtype=float)
    n = len(x0)

    x1 = np.cumsum(x0)
    z1 = 0.5 * (x1[:-1] + x1[1:])

    # dx1/dt + a*x1 = b*x1²
    B = np.column_stack([-z1, z1**2])
    Y = x0[1:]
    params = np.linalg.lstsq(B, Y, rcond=None)[0]
    a, b = params

    # 时间响应
    c = (a * x0[0]) / (b * x0[0] + (a - b * x0[0]) * np.exp(a * np.arange(n + predict_n)))
    x1_hat = c
    x0_hat = np.zeros(n + predict_n)
    x0_hat[0] = x0[0]
    x0_hat[1:] = np.diff(x1_hat)

    residuals = x0 - x0_hat[:n]

    return {
        'x0_hat': x0_hat,
        'a': a, 'b': b,
        'residuals': residuals,
        'predictions': x0_hat[n:]
    }


# ============================================================
# 6. 灰色预测模型自动选择
# ============================================================
def grey_auto_predict(x0: np.ndarray, predict_n: int = 5) -> Dict:
    """
    自动选择最优灰色预测模型

    依次尝试 GM(1,1)、GM(2,1)、Verhulst，选残差最小的
    """
    models = {}
    results = {}

    # GM(1,1)
    try:
        r = gm11_predict(x0, predict_n)
        models['GM(1,1)'] = r['mean_error']
        results['GM(1,1)'] = r
    except Exception:
        pass

    # GM(2,1)
    try:
        r = gm21_predict(x0, predict_n)
        models['GM(2,1)'] = np.mean(np.abs(r['residuals']) / x0)
        results['GM(2,1)'] = r
    except Exception:
        pass

    # Verhulst
    try:
        r = verhulst_predict(x0, predict_n)
        models['Verhulst'] = np.mean(np.abs(r['residuals']) / x0)
        results['Verhulst'] = r
    except Exception:
        pass

    best = min(models, key=models.get)

    print("=" * 50)
    print("灰色预测模型自动选择")
    print("=" * 50)
    for name, err in sorted(models.items(), key=lambda x: x[1]):
        marker = " ← 最优" if name == best else ""
        print(f"  {name}: 平均相对误差 = {err:.4f}{marker}")

    return {'best_model': best, 'results': results, 'errors': models}


# ============================================================
# 使用示例
# ============================================================
def example():
    """灰色系统完整示例"""
    # 示例1: GM(1,1) 预测
    print("\n" + "=" * 60)
    print("示例1: GM(1,1) 灰色预测")
    print("=" * 60)
    x0 = np.array([390.6, 412, 320, 559.2, 380.8, 542.4, 553, 310, 561, 300, 632, 540])
    result = gm11_predict(x0, predict_n=3)
    print(f"原始数据: {x0}")
    print(f"拟合值:   {result['x0_hat'][:len(x0)].round(1)}")
    print(f"预测值:   {result['predictions'].round(1)}")
    print(f"后验差比 C = {result['C']:.4f}, 小误差概率 P = {result['P']:.4f}")
    print(f"精度等级: {result['grade']}")

    # 示例2: 灰色关联分析
    print("\n" + "=" * 60)
    print("示例2: 灰色关联分析")
    print("=" * 60)
    ref = np.array([1.2, 1.5, 1.8, 2.1, 2.5])
    cmp = np.array([
        [1.0, 1.3, 1.6, 1.9, 2.3],
        [0.8, 1.1, 1.4, 1.7, 2.0],
        [1.5, 1.8, 2.0, 2.3, 2.8],
    ])
    grey_correlation_rank(ref, cmp, names=["方案A", "方案B", "方案C"])

    # 示例3: 模型自动选择
    print("\n" + "=" * 60)
    print("示例3: 灰色预测模型自动选择")
    print("=" * 60)
    x0_s = np.array([100, 150, 220, 300, 380, 450, 500, 530, 550])
    auto = grey_auto_predict(x0_s, predict_n=3)
    print(f"最优模型: {auto['best_model']}")


if __name__ == "__main__":
    example()
