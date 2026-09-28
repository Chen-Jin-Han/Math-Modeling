"""
时间序列分析工具箱
==================
包含：移动平均法、指数平滑法（一/二/三次）、趋势外推预测、自适应滤波

竞赛中常用于：数据预处理、趋势预测、异常值平滑、信号去噪

参考：Algorithms_MathModels/TimeSeries时间序列函数/
      HuangCongQing/Algorithms_MathModels（MATLAB实现转Python）
"""

import numpy as np
from typing import Dict


# ============================================================
# 1. 移动平均法
# ============================================================
def simple_moving_average(data: np.ndarray, window: int = 5) -> np.ndarray:
    """
    简单移动平均 (SMA)

    对时间序列取窗口内算术平均，平滑短期波动、揭示趋势。

    Parameters
    ----------
    data : np.ndarray, shape (n,)
        原始时间序列
    window : int
        窗口大小

    Returns
    -------
    np.ndarray: 移动平均序列（前 window-1 个为 NaN）
    """
    data = np.asarray(data, dtype=float).ravel()
    result = np.full_like(data, np.nan)
    for i in range(window - 1, len(data)):
        result[i] = np.mean(data[i - window + 1:i + 1])
    return result


def weighted_moving_average(data: np.ndarray, weights: np.ndarray | None = None) -> np.ndarray:
    """
    加权移动平均 (WMA)

    近期数据赋予更高权重，对趋势变化更敏感。

    Parameters
    ----------
    data : np.ndarray, shape (n,)
        原始时间序列
    weights : np.ndarray or None
        权重（长度 = 窗口大小），默认线性递增权重

    Returns
    -------
    np.ndarray: 加权移动平均序列
    """
    data = np.asarray(data, dtype=float).ravel()
    if weights is None:
        window = 3
        weights = np.arange(1, window + 1, dtype=float)
    else:
        weights = np.asarray(weights, dtype=float)
        window = len(weights)

    weights = weights / weights.sum()
    result = np.full_like(data, np.nan)
    for i in range(window - 1, len(data)):
        result[i] = np.dot(data[i - window + 1:i + 1], weights)
    return result


def trend_moving_average(data: np.ndarray, window: int = 5) -> Dict:
    """
    趋势移动平均

    在移动平均基础上再做一次移动平均（双重移动平均），
    用于提取趋势成分并做线性外推预测。

    Parameters
    ----------
    data : np.ndarray, shape (n,)
        原始时间序列
    window : int
        窗口大小

    Returns
    -------
    dict:
        - ma1: 一次移动平均
        - ma2: 二次移动平均
        - trend: 趋势估计（斜率）
        - forecast_next: 下一步预测值
    """
    data = np.asarray(data, dtype=float).ravel()
    ma1 = simple_moving_average(data, window)
    ma2 = simple_moving_average(ma1, window)

    # 趋势斜率: at = 2*MA1(t) - MA2(t), bt = 2/(n-1) * (MA1(t) - MA2(t))
    valid = ~(np.isnan(ma1) | np.isnan(ma2))
    if valid.sum() == 0:
        return {'ma1': ma1, 'ma2': ma2, 'trend': np.nan, 'forecast_next': np.nan}

    last_idx = np.where(valid)[0][-1]
    at = 2 * ma1[last_idx] - ma2[last_idx]
    bt = 2 / (window - 1) * (ma1[last_idx] - ma2[last_idx])
    forecast_next = at + bt

    return {
        'ma1': ma1,
        'ma2': ma2,
        'trend': bt,
        'forecast_next': forecast_next,
        'at': at,
    }


# ============================================================
# 2. 一次指数平滑 (SES)
# ============================================================
def single_exponential_smoothing(
    data: np.ndarray,
    alpha: float = 0.3,
    forecast_periods: int = 0,
) -> Dict:
    """
    一次指数平滑 (Simple Exponential Smoothing)

    S_t = alpha * y_t + (1 - alpha) * S_{t-1}

    适用于无明显趋势和季节性的平稳序列。

    Parameters
    ----------
    data : np.ndarray, shape (n,)
        原始时间序列
    alpha : float
        平滑系数 (0,1)，越大对近期变化越敏感
    forecast_periods : int
        向前预测步数（0 = 不预测）

    Returns
    -------
    dict:
        - smoothed: 平滑序列
        - forecast: 预测值列表
        - alpha: 使用的平滑系数
    """
    data = np.asarray(data, dtype=float).ravel()
    n = len(data)
    s = np.zeros(n)
    s[0] = data[0]
    for t in range(1, n):
        s[t] = alpha * data[t] + (1 - alpha) * s[t - 1]

    forecast = []
    last = s[-1]
    for _ in range(forecast_periods):
        forecast.append(last)  # 一次平滑的预测值 = 最后一个平滑值

    return {
        'smoothed': s,
        'forecast': np.array(forecast),
        'alpha': alpha,
    }


# ============================================================
# 3. 二次指数平滑 (Holt's Linear)
# ============================================================
def double_exponential_smoothing(
    data: np.ndarray,
    alpha: float = 0.3,
    beta: float = 0.1,
    forecast_periods: int = 5,
) -> Dict:
    """
    二次指数平滑 (Holt's Linear Trend Method)

    水平: L_t = alpha * y_t + (1 - alpha) * (L_{t-1} + T_{t-1})
    趋势: T_t = beta * (L_t - L_{t-1}) + (1 - beta) * T_{t-1}
    预测: F_{t+m} = L_t + m * T_t

    适用于有线性趋势但无季节性的序列。

    Parameters
    ----------
    data : np.ndarray
        原始时间序列
    alpha : float
        水平平滑系数
    beta : float
        趋势平滑系数
    forecast_periods : int
        向前预测步数

    Returns
    -------
    dict:
        - level: 水平分量
        - trend: 趋势分量
        - fitted: 拟合值
        - forecast: 预测值
    """
    data = np.asarray(data, dtype=float).ravel()
    n = len(data)
    L = np.zeros(n)
    T = np.zeros(n)

    # 初始化
    L[0] = data[0]
    T[0] = data[1] - data[0] if n > 1 else 0

    for t in range(1, n):
        L[t] = alpha * data[t] + (1 - alpha) * (L[t - 1] + T[t - 1])
        T[t] = beta * (L[t] - L[t - 1]) + (1 - beta) * T[t - 1]

    fitted = L + T  # 一步预测
    forecast = np.array([L[-1] + (m + 1) * T[-1] for m in range(forecast_periods)])

    return {
        'level': L,
        'trend': T,
        'fitted': fitted,
        'forecast': forecast,
        'alpha': alpha,
        'beta': beta,
    }


# ============================================================
# 4. 三次指数平滑 (Holt-Winters)
# ============================================================
def triple_exponential_smoothing(
    data: np.ndarray,
    alpha: float = 0.3,
    beta: float = 0.1,
    gamma: float = 0.1,
    season_length: int = 12,
    forecast_periods: int = 12,
    method: str = 'additive',
) -> Dict:
    """
    三次指数平滑 (Holt-Winters 季节性方法)

    支持加法和乘法季节性模型。

    加法模型: y_t = L_t + T_t + S_t
    乘法模型: y_t = L_t * T_t * S_t

    适用于有趋势和季节性的序列。

    Parameters
    ----------
    data : np.ndarray
        原始时间序列（至少 2 个完整季节周期）
    alpha, beta, gamma : float
        水平、趋势、季节平滑系数
    season_length : int
        季节周期长度（月度=12，季度=4）
    forecast_periods : int
        向前预测步数
    method : str
        'additive'（加法）或 'multiplicative'（乘法）

    Returns
    -------
    dict:
        - level, trend, seasonal: 三个分量
        - fitted: 拟合值
        - forecast: 预测值
    """
    data = np.asarray(data, dtype=float).ravel()
    n = len(data)
    s_len = season_length

    L = np.zeros(n)
    T = np.zeros(n)
    S = np.zeros(n)

    # 初始化：用第一个季节周期
    L[s_len - 1] = np.mean(data[:s_len])
    T[s_len - 1] = (np.mean(data[s_len:2 * s_len]) - np.mean(data[:s_len])) / s_len if n >= 2 * s_len else 0

    if method == 'additive':
        for i in range(s_len):
            S[i] = data[i] - L[s_len - 1]
    else:
        for i in range(s_len):
            S[i] = data[i] / L[s_len - 1] if L[s_len - 1] != 0 else 1.0

    # 递推
    for t in range(s_len, n):
        if method == 'additive':
            L[t] = alpha * (data[t] - S[t - s_len]) + (1 - alpha) * (L[t - 1] + T[t - 1])
            T[t] = beta * (L[t] - L[t - 1]) + (1 - beta) * T[t - 1]
            S[t] = gamma * (data[t] - L[t]) + (1 - gamma) * S[t - s_len]
        else:
            L[t] = alpha * (data[t] / S[t - s_len]) + (1 - alpha) * (L[t - 1] + T[t - 1])
            T[t] = beta * (L[t] - L[t - 1]) + (1 - beta) * T[t - 1]
            S[t] = gamma * (data[t] / L[t]) + (1 - gamma) * S[t - s_len] if L[t] != 0 else S[t - s_len]

    # 拟合
    if method == 'additive':
        fitted = L + T + S
    else:
        fitted = (L + T) * S

    # 预测
    forecast = np.zeros(forecast_periods)
    for m in range(forecast_periods):
        season_idx = (n - s_len + (m % s_len))
        if method == 'additive':
            forecast[m] = L[-1] + (m + 1) * T[-1] + S[season_idx]
        else:
            forecast[m] = (L[-1] + (m + 1) * T[-1]) * S[season_idx]

    return {
        'level': L,
        'trend': T,
        'seasonal': S,
        'fitted': fitted,
        'forecast': forecast,
        'alpha': alpha,
        'beta': beta,
        'gamma': gamma,
    }


# ============================================================
# 5. 趋势外推预测
# ============================================================
def gompertz_curve(
    t: np.ndarray,
    y: np.ndarray,
    t_predict: np.ndarray | None = None,
) -> Dict:
    """
    Gompertz 增长曲线预测

    y = a * exp(-b * exp(-c * t))

    适用于 S 形增长曲线（初期慢→中期快→后期饱和），
    常用于人口预测、产品销量预测、技术扩散。

    Parameters
    ----------
    t : np.ndarray
        时间自变量
    y : np.ndarray
        观测值
    t_predict : np.ndarray or None
        待预测的时间点

    Returns
    -------
    dict:
        - params: (a, b, c) 参数
        - y_hat: 拟合值
        - y_predict: 预测值
        - R2: 拟合优度
    """
    from scipy.optimize import curve_fit

    t = np.asarray(t, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()

    def gompertz(x, a, b, c):
        return a * np.exp(-b * np.exp(-c * x))

    # 初始参数估计
    a0 = np.max(y) * 1.1
    p0 = [a0, 1.0, 0.1]

    popt, pcov = curve_fit(gompertz, t, y, p0=p0, maxfev=10000)
    y_hat = gompertz(t, *popt)

    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    result = {
        'params': popt,
        'param_names': ['a (饱和值)', 'b (位置参数)', 'c (增长速率)'],
        'y_hat': y_hat,
        'R2': r2,
        'y_predict': None,
    }

    if t_predict is not None:
        result['y_predict'] = gompertz(np.asarray(t_predict), *popt)

    return result


def logistic_curve(
    t: np.ndarray,
    y: np.ndarray,
    t_predict: np.ndarray | None = None,
) -> Dict:
    """
    Logistic 增长曲线预测

    y = a / (1 + b * exp(-c * t))

    经典 S 形增长模型，比 Gompertz 更对称。
    常用于人口增长、传染病传播、市场渗透。

    Parameters
    ----------
    t, y : np.ndarray
        时间和观测值
    t_predict : np.ndarray or None
        待预测的时间点

    Returns
    -------
    dict: params, y_hat, y_predict, R2
    """
    from scipy.optimize import curve_fit

    t = np.asarray(t, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()

    def logistic(x, a, b, c):
        return a / (1 + b * np.exp(-c * x))

    a0 = np.max(y) * 1.1
    p0 = [a0, 1.0, 0.1]

    popt, pcov = curve_fit(logistic, t, y, p0=p0, maxfev=10000)
    y_hat = logistic(t, *popt)

    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    result = {
        'params': popt,
        'param_names': ['a (容量上限)', 'b (初始值参数)', 'c (增长速率)'],
        'y_hat': y_hat,
        'R2': r2,
        'y_predict': None,
    }

    if t_predict is not None:
        result['y_predict'] = logistic(np.asarray(t_predict), *popt)

    return result


def modified_exponential_curve(
    t: np.ndarray,
    y: np.ndarray,
    t_predict: np.ndarray | None = None,
) -> Dict:
    """
    修正指数曲线预测

    y = a + b * exp(c * t)

    适用于指数增长或衰减的趋势（无饱和效应）。

    Parameters
    ----------
    t, y : np.ndarray
        时间和观测值
    t_predict : np.ndarray or None
        待预测的时间点

    Returns
    -------
    dict: params, y_hat, y_predict, R2
    """
    from scipy.optimize import curve_fit

    t = np.asarray(t, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()

    def mod_exp(x, a, b, c):
        return a + b * np.exp(c * x)

    p0 = [np.min(y), 1.0, 0.01]
    popt, pcov = curve_fit(mod_exp, t, y, p0=p0, maxfev=10000)
    y_hat = mod_exp(t, *popt)

    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    result = {
        'params': popt,
        'param_names': ['a (基线)', 'b (振幅)', 'c (速率)'],
        'y_hat': y_hat,
        'R2': r2,
        'y_predict': None,
    }

    if t_predict is not None:
        result['y_predict'] = mod_exp(np.asarray(t_predict), *popt)

    return result


# ============================================================
# 6. 自适应滤波法
# ============================================================
def adaptive_filter(
    data: np.ndarray,
    window: int = 5,
    learning_rate: float = 0.01,
    n_epochs: int = 100,
    forecast_periods: int = 1,
) -> Dict:
    """
    自适应滤波法（LMS 算法）

    根据预测误差自动调整滤波器权重，适合非平稳时间序列。
    原理：w(t+1) = w(t) + 2*mu*e(t)*x(t)，其中 e(t)=y(t)-y_hat(t)

    竞赛中常用于：噪声数据的趋势预测、信号去噪。

    Parameters
    ----------
    data : np.ndarray, shape (n,)
        原始时间序列
    window : int
        滤波器窗口长度（使用前 window 个值预测下一个）
    learning_rate : float
        学习率 mu（越大收敛越快但可能震荡）
    n_epochs : int
        训练轮数（遍历完整序列的次数）
    forecast_periods : int
        向前预测步数

    Returns
    -------
    dict:
        - weights: 最终权重
        - predictions: 拟合值
        - errors: 预测误差
        - forecast: 预测值
        - mse: 均方误差

    参考
    ----
    HuangCongQing/Algorithms_MathModels/TimeSeries/自适应滤波法/main.m
    """
    data = np.asarray(data, dtype=float).ravel()
    n = len(data)

    # 数据标准化（防止溢出）
    mu_data = np.mean(data)
    sigma_data = np.std(data)
    if sigma_data == 0:
        sigma_data = 1.0
    data_norm = (data - mu_data) / sigma_data

    # 初始化权重
    weights = np.ones(window) / window

    # 训练（归一化数据上）
    for epoch in range(n_epochs):
        for t in range(window, n):
            x = data_norm[t - window:t][::-1]
            y_hat = np.dot(weights, x)
            e = data_norm[t] - y_hat
            # LMS 权重更新（带裁剪防溢出）
            update = 2 * learning_rate * e * x
            weights = np.clip(weights + update, -10, 10)

    # 最终拟合
    predictions = np.full(n, np.nan)
    errors = np.full(n, np.nan)
    for t in range(window, n):
        x = data_norm[t - window:t][::-1]
        pred_norm = np.dot(weights, x)
        predictions[t] = pred_norm * sigma_data + mu_data
        errors[t] = data[t] - predictions[t]

    # 预测
    forecast = np.zeros(forecast_periods)
    recent = list(data_norm[-window:][::-1])
    for i in range(forecast_periods):
        x = np.array(recent[:window])
        pred_norm = np.dot(weights, x)
        forecast[i] = pred_norm * sigma_data + mu_data
        recent.insert(0, pred_norm)

    mse = np.nanmean(errors[window:] ** 2)

    return {
        'weights': weights,
        'predictions': predictions,
        'errors': errors,
        'forecast': forecast,
        'mse': mse,
    }


# ============================================================
# 使用示例
# ============================================================
def example():
    """时间序列分析示例"""
    np.random.seed(42)

    # 示例1: 移动平均
    print("=" * 60)
    print("示例1: 移动平均法")
    print("=" * 60)
    t = np.arange(30)
    y = 2 + 0.1 * t + np.random.randn(30) * 0.5
    sma = simple_moving_average(y, window=5)
    print(f"  原始序列最后5个: {y[-5:].round(2)}")
    print(f"  SMA(5) 最后5个: {sma[-5:].round(2)}")

    # 示例2: 二次指数平滑
    print("\n" + "=" * 60)
    print("示例2: 二次指数平滑 (Holt)")
    print("=" * 60)
    result = double_exponential_smoothing(y, alpha=0.3, beta=0.1, forecast_periods=5)
    print(f"  最后水平: {result['level'][-1]:.3f}")
    print(f"  最后趋势: {result['trend'][-1]:.3f}")
    print(f"  未来5步预测: {result['forecast'].round(3)}")

    # 示例3: Gompertz 曲线
    print("\n" + "=" * 60)
    print("示例3: Gompertz 增长曲线")
    print("=" * 60)
    t_g = np.arange(1, 21)
    y_g = 100 * np.exp(-3 * np.exp(-0.15 * t_g)) + np.random.randn(20) * 2
    r = gompertz_curve(t_g, y_g, t_predict=np.array([21, 22, 23]))
    print(f"  参数 a={r['params'][0]:.2f}, b={r['params'][1]:.2f}, c={r['params'][2]:.4f}")
    print(f"  R² = {r['R2']:.4f}")
    print(f"  预测 t=21,22,23: {r['y_predict'].round(2)}")


if __name__ == "__main__":
    example()
