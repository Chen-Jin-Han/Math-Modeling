"""
回归分析工具箱
==============
包含：线性回归、多项式回归、逐步回归、岭回归、Lasso回归、非线性回归、Logistic回归

参考：Algorithms_MathModels/RegressionAnalysis回归分析/
      ravenxrz/Mathematical-Modeling/forecast/Logistic/
"""

import numpy as np
from typing import Tuple, Dict, Optional, List, Callable


# ============================================================
# 1. 多元线性回归
# ============================================================
def linear_regression(X: np.ndarray, y: np.ndarray,
                      add_intercept: bool = True) -> Dict:
    """
    多元线性回归 (最小二乘法)

    Parameters
    ----------
    X : np.ndarray
        自变量矩阵 (n, p)
    y : np.ndarray
        因变量 (n,)
    add_intercept : bool
        是否添加截距项

    Returns
    -------
    dict : 系数、R²、调整R²、F统计量、残差等
    """
    X, y = np.asarray(X, dtype=float), np.asarray(y, dtype=float)
    univariate = X.ndim == 1
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    n, p = X.shape

    if add_intercept:
        X = np.column_stack([np.ones(n), X])

    # 最小二乘
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    y_hat = X @ beta
    residuals = y - y_hat

    # 统计量
    SSR = np.sum((y_hat - y.mean())**2)
    SSE = np.sum(residuals**2)
    SST = np.sum((y - y.mean())**2)
    R2 = SSR / SST if SST > 0 else 0
    p_eff = X.shape[1] - 1  # 不含截距
    R2_adj = 1 - (1 - R2) * (n - 1) / (n - p_eff - 1) if n > p_eff + 1 else R2
    F = (SSR / p_eff) / (SSE / (n - p_eff - 1)) if n > p_eff + 1 else np.inf

    result = {
        'coefficients': beta,
        'y_hat': y_hat,
        'residuals': residuals,
        'R2': R2, 'R2_adj': R2_adj,
        'F': F, 'SSE': SSE, 'SSR': SSR, 'SST': SST,
        'n': n, 'p': p_eff,
    }
    if univariate and p == 1:
        result['slope'] = float(beta[-1]) if add_intercept else float(beta[0])
        result['intercept'] = float(beta[0]) if add_intercept else 0.0
        result['r2'] = R2
    return result


# ============================================================
# 2. 多项式回归
# ============================================================
def polynomial_regression(x: np.ndarray, y: np.ndarray, degree: int = 2) -> Dict:
    """
    多项式回归

    Parameters
    ----------
    x, y : np.ndarray
        数据
    degree : int
        多项式阶数

    Returns
    -------
    dict : 系数、预测值、R²
    """
    coeffs = np.polyfit(x, y, degree)
    y_hat = np.polyval(coeffs, x)
    residuals = y - y_hat
    R2 = 1 - np.sum(residuals**2) / np.sum((y - y.mean())**2)

    return {
        'coefficients': coeffs,
        'y_hat': y_hat,
        'residuals': residuals,
        'R2': R2,
        'r2': R2,
        'degree': degree,
        'predict': lambda x_new: np.polyval(coeffs, x_new)
    }


# ============================================================
# 3. 岭回归 (Ridge)
# ============================================================
def ridge_regression(X: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> Dict:
    """
    岭回归 (L2 正则化)

    适用场景: 多重共线性、特征数接近样本数

    Parameters
    ----------
    X : np.ndarray
        自变量 (n, p)
    y : np.ndarray
        因变量 (n,)
    alpha : float
        正则化参数 (λ)

    Returns
    -------
    dict : 系数、R² 等
    """
    X, y = np.asarray(X, dtype=float), np.asarray(y, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    n, p = X.shape

    # 标准化
    X_mean, X_std = X.mean(axis=0), X.std(axis=0)
    X_std[X_std == 0] = 1
    X_norm = (X - X_mean) / X_std
    y_mean = y.mean()
    y_center = y - y_mean

    # 岭回归: β = (X'X + αI)^(-1) X'y
    I = np.eye(p)
    beta = np.linalg.solve(X_norm.T @ X_norm + alpha * I, X_norm.T @ y_center)

    # 还原到原始尺度
    beta_orig = beta / X_std
    intercept = y_mean - X_mean @ beta_orig

    y_hat = X @ beta_orig + intercept
    residuals = y - y_hat
    R2 = 1 - np.sum(residuals**2) / np.sum((y - y.mean())**2)

    return {
        'coefficients': beta_orig,
        'intercept': intercept,
        'y_hat': y_hat,
        'residuals': residuals,
        'R2': R2,
        'alpha': alpha
    }


# ============================================================
# 4. 逐步回归
# ============================================================
def stepwise_regression(X: np.ndarray, y: np.ndarray,
                        feature_names: Optional[List[str]] = None,
                        method: str = 'forward',
                        threshold_enter: float = 0.05,
                        threshold_remove: float = 0.10) -> Dict:
    """
    逐步回归 (前向/后向/双向)

    Parameters
    ----------
    X : np.ndarray
        自变量 (n, p)
    y : np.ndarray
        因变量 (n,)
    feature_names : list, optional
        特征名称
    method : str
        'forward', 'backward', 'both'
    threshold_enter : float
        进入阈值 (F检验 p值)
    threshold_remove : float
        剔除阈值

    Returns
    -------
    dict : 选中的特征、系数、R²
    """
    from scipy import stats

    X, y = np.asarray(X, dtype=float), np.asarray(y, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    n, p = X.shape

    if feature_names is None:
        feature_names = [f"X{i+1}" for i in range(p)]

    selected = []
    remaining = list(range(p))

    def _fit_and_score(cols):
        if not cols:
            return np.inf, 0
        Xi = np.column_stack([np.ones(n), X[:, cols]])
        beta = np.linalg.lstsq(Xi, y, rcond=None)[0]
        y_hat = Xi @ beta
        SSE = np.sum((y - y_hat)**2)
        SST = np.sum((y - y.mean())**2)
        R2 = 1 - SSE / SST
        return SSE, R2

    if method in ('forward', 'both'):
        while remaining:
            best_pval, best_col = 1.0, -1
            for col in remaining:
                trial = selected + [col]
                Xi = np.column_stack([np.ones(n), X[:, trial]])
                beta = np.linalg.lstsq(Xi, y, rcond=None)[0]
                y_hat = Xi @ beta
                residuals = y - y_hat
                MSE = np.sum(residuals**2) / (n - len(trial) - 1)
                se = np.sqrt(MSE * np.linalg.inv(Xi.T @ Xi).diagonal())[-1]
                t_stat = beta[-1] / se if se > 0 else 0
                pval = 2 * (1 - stats.t.cdf(abs(t_stat), n - len(trial) - 1))
                if pval < best_pval:
                    best_pval, best_col = pval, col

            if best_pval < threshold_enter and best_col >= 0:
                selected.append(best_col)
                remaining.remove(best_col)
            else:
                break

    _, R2 = _fit_and_score(selected)

    print("=" * 50)
    print(f"逐步回归结果 ({method})")
    print("=" * 50)
    print(f"选中特征: {[feature_names[i] for i in selected]}")
    print(f"R² = {R2:.4f}")

    return {
        'selected_features': [feature_names[i] for i in selected],
        'selected_indices': selected,
        'R2': R2
    }


# ============================================================
# 5. 非线性回归
# ============================================================
def nonlinear_regression(x: np.ndarray, y: np.ndarray,
                         model_func: Callable,
                         p0: np.ndarray,
                         bounds: Optional[Tuple] = None) -> Dict:
    """
    非线性最小二乘回归

    Parameters
    ----------
    x, y : np.ndarray
        数据
    model_func : callable
        模型函数 f(x, *params) -> y
    p0 : np.ndarray
        初始参数
    bounds : tuple, optional
        参数边界 (lower, upper)

    Returns
    -------
    dict : 最优参数、R²、残差
    """
    from scipy.optimize import curve_fit

    popt, pcov = curve_fit(model_func, x, y, p0=p0, bounds=bounds, maxfev=10000)
    y_hat = model_func(x, *popt)
    residuals = y - y_hat
    R2 = 1 - np.sum(residuals**2) / np.sum((y - y.mean())**2)
    perr = np.sqrt(np.diag(pcov))

    return {
        'parameters': popt,
        'std_errors': perr,
        'covariance': pcov,
        'y_hat': y_hat,
        'residuals': residuals,
        'R2': R2,
        'predict': lambda x_new: model_func(x_new, *popt)
    }


# ============================================================
# 7. Logistic 回归（二分类）
# ============================================================
def logistic_regression(
    X: np.ndarray,
    y: np.ndarray,
    X_new: np.ndarray | None = None,
    threshold: float = 0.5,
    max_iter: int = 100,
    lr: float = 0.01,
    tol: float = 1e-6,
) -> Dict:
    """
    Logistic 回归（二分类）

    使用梯度下降法求解。适用于因变量为 0/1 二分类的场景。

    Parameters
    ----------
    X : np.ndarray, shape (n_samples, n_features)
        自变量矩阵（不含常数项，函数自动添加截距）
    y : np.ndarray, shape (n_samples,)
        因变量（0 或 1）
    X_new : np.ndarray or None
        待预测的新数据（不含常数项）
    threshold : float
        分类阈值（默认 0.5）
    max_iter : int
        最大迭代次数
    lr : float
        学习率
    tol : float
        收敛阈值

    Returns
    -------
    dict:
        - coefficients: 回归系数 [截距, b1, b2, ...]
        - probabilities: 训练集预测概率
        - predictions: 训练集预测类别 (0/1)
        - accuracy: 训练集准确率
        - new_predictions: X_new 的预测类别（如提供）
        - new_probabilities: X_new 的预测概率（如提供）
        - predict: 可调用的预测函数 predict(X) -> (classes, probs)

    示例
    ----
    >>> result = logistic_regression(X_train, y_train, X_test)
    >>> print(result['accuracy'])
    >>> print(result['new_predictions'])
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    n, p = X.shape

    # 标准化（提升梯度下降稳定性）
    mu = X.mean(axis=0)
    sigma = X.std(axis=0)
    sigma[sigma == 0] = 1.0
    X_std = (X - mu) / sigma

    # 添加截距
    X_aug = np.column_stack([np.ones(n), X_std])

    # sigmoid
    def sigmoid(z):
        z = np.clip(z, -500, 500)
        return 1.0 / (1.0 + np.exp(-z))

    # 梯度下降
    w = np.zeros(p + 1)
    for iteration in range(max_iter):
        z = X_aug @ w
        h = sigmoid(z)
        grad = X_aug.T @ (h - y) / n
        w_new = w - lr * grad
        if np.max(np.abs(w_new - w)) < tol:
            w = w_new
            break
        w = w_new

    # 训练集预测
    probs = sigmoid(X_aug @ w)
    preds = (probs >= threshold).astype(int)
    accuracy = np.mean(preds == y)

    # 系数还原到原始尺度
    # 标准化后: z = b0 + b1*(x1-mu1)/sig1 + ...
    # 原始尺度: z = (b0 - sum(bi*mu_i/sig_i)) + b1/sig_i * x_i
    coef_original = np.zeros(p + 1)
    coef_original[0] = w[0] - np.sum(w[1:] * mu / sigma)
    coef_original[1:] = w[1:] / sigma

    result = {
        'coefficients': coef_original,
        'probabilities': probs,
        'predictions': preds,
        'accuracy': accuracy,
        'new_predictions': None,
        'new_probabilities': None,
        'predict': None,
    }

    # 预测函数
    def predict_func(X_pred):
        X_pred = np.asarray(X_pred, dtype=float)
        X_pred_std = (X_pred - mu) / sigma
        X_pred_aug = np.column_stack([np.ones(X_pred.shape[0]), X_pred_std])
        p_vals = sigmoid(X_pred_aug @ w)
        c_vals = (p_vals >= threshold).astype(int)
        return c_vals, p_vals

    result['predict'] = predict_func

    # 新数据预测
    if X_new is not None:
        c, p_vals = predict_func(X_new)
        result['new_predictions'] = c
        result['new_probabilities'] = p_vals

    return result


# ============================================================
# 使用示例
# ============================================================
def example():
    """回归分析示例"""
    np.random.seed(42)

    # 示例1: 多元线性回归
    print("=" * 60)
    print("示例1: 多元线性回归")
    print("=" * 60)
    n = 50
    X = np.random.randn(n, 3)
    y = 2 + 3*X[:, 0] - 1.5*X[:, 1] + 0.5*X[:, 2] + np.random.randn(n)*0.5
    result = linear_regression(X, y)
    print(f"系数: {result['coefficients'].round(3)}")
    print(f"R² = {result['R2']:.4f}, R²_adj = {result['R2_adj']:.4f}")

    # 示例2: 多项式回归
    print("\n" + "=" * 60)
    print("示例2: 多项式回归 (阶数对比)")
    print("=" * 60)
    x = np.linspace(0, 2*np.pi, 30)
    y = np.sin(x) + np.random.randn(30)*0.1
    for deg in [1, 3, 5, 7]:
        r = polynomial_regression(x, y, degree=deg)
        print(f"  {deg}次多项式: R² = {r['R2']:.4f}")

    # 示例3: 非线性回归
    print("\n" + "=" * 60)
    print("示例3: 非线性回归 (指数衰减)")
    print("=" * 60)
    x = np.linspace(0, 5, 50)
    y = 3 * np.exp(-0.5 * x) + 1 + np.random.randn(50)*0.1
    model = lambda x, a, b, c: a * np.exp(-b * x) + c
    r = nonlinear_regression(x, y, model, p0=[1, 1, 0])
    print(f"参数: a={r['parameters'][0]:.3f}, b={r['parameters'][1]:.3f}, c={r['parameters'][2]:.3f}")
    print(f"R² = {r['R2']:.4f}")


if __name__ == "__main__":
    example()
