"""
神经网络工具箱
==============
包含：BP神经网络、RBF神经网络、SOM自组织映射、MIV变量重要性筛选
全部基于 numpy 实现, 不依赖深度学习框架

参考：Algorithms_MathModels/HeuristicAlgorithm/神经网络算法/
      ravenxrz/Mathematical-Modeling (MIV算法)
"""

import numpy as np
from typing import Tuple, Dict, List, Optional


# ============================================================
# 1. BP 神经网络
# ============================================================
class BPNeuralNetwork:
    """
    BP (Back Propagation) 神经网络

    支持任意层数、任意节点数的全连接网络
    """

    def __init__(self, layer_sizes: Optional[List[int]] = None, activation: str = 'sigmoid',
                 learning_rate: float = 0.1, max_epochs: int = 1000,
                 tol: float = 1e-6, layers: Optional[List[int]] = None,
                 lr: Optional[float] = None, max_iter: Optional[int] = None):
        """
        Parameters
        ----------
        layer_sizes / layers : list
            各层节点数, 如 [3, 5, 2] 表示3输入5隐含2输出
        learning_rate / lr : float
            学习率
        max_epochs / max_iter : int
            最大训练轮数
        """
        layer_sizes = layers or layer_sizes
        if layer_sizes is None:
            raise ValueError("需要指定 layer_sizes 或 layers")
        if lr is not None:
            learning_rate = lr
        if max_iter is not None:
            max_epochs = max_iter
        self.layer_sizes = layer_sizes
        self.lr = learning_rate
        self.max_epochs = max_epochs
        self.tol = tol
        self.n_layers = len(layer_sizes)
        self.weights: List[np.ndarray] = []
        self.biases: List[np.ndarray] = []
        self.loss_history: List[float] = []

        # 激活函数
        self._activation_name = activation
        self._set_activation(activation)

        self._init_weights()

    def _set_activation(self, activation: str):
        self._activation_name = activation
        if activation == 'sigmoid':
            self.act = lambda x: 1 / (1 + np.exp(-np.clip(x, -500, 500)))
            self.act_deriv = lambda x: x * (1 - x)
        elif activation == 'tanh':
            self.act = lambda x: np.tanh(x)
            self.act_deriv = lambda x: 1 - x**2
        elif activation == 'relu':
            self.act = lambda x: np.maximum(0, x)
            self.act_deriv = lambda x: (x > 0).astype(float)
        else:
            raise ValueError(f"未知激活函数: {activation}")

    def _init_weights(self, rng: Optional[np.random.Generator] = None):
        """初始化或重置权重。"""
        rng = rng or np.random
        self.weights = []
        self.biases = []
        for i in range(self.n_layers - 1):
            fan_in, fan_out = self.layer_sizes[i], self.layer_sizes[i + 1]
            scale = np.sqrt(2.0 / (fan_in + fan_out))
            self.weights.append(rng.standard_normal((fan_in, fan_out)) * scale)
            self.biases.append(np.zeros((1, fan_out)))

    def _forward(self, X: np.ndarray) -> List[np.ndarray]:
        """前向传播"""
        activations = [X]
        for i in range(self.n_layers - 1):
            z = activations[-1] @ self.weights[i] + self.biases[i]
            a = self.act(z)
            activations.append(a)
        return activations

    def train(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """
        训练网络

        Parameters
        ----------
        X : np.ndarray
            训练数据 (n_samples, n_features)
        y : np.ndarray
            目标值 (n_samples, n_outputs)

        Returns
        -------
        dict : 训练历史
        """
        X = np.atleast_2d(X)
        y = np.atleast_2d(y)
        if y.ndim == 1:
            y = y.reshape(-1, 1)

        # 小样本（如 XOR）自动多激活函数 + 多次重启取最优
        act_candidates = [self._activation_name]
        if X.shape[0] <= 16:
            act_candidates = list(dict.fromkeys(
                [self._activation_name, 'tanh', 'relu']
            ))
        restarts_per_act = 15 if X.shape[0] <= 16 else 1
        best_loss = np.inf
        best_state = None
        best_act = self._activation_name

        for act_name in act_candidates:
            self._set_activation(act_name)
            for restart_i in range(restarts_per_act):
                rng = np.random.default_rng(restart_i * 9973 + X.shape[0] * 17 + y.shape[1] + hash(act_name) % 1000)
                self._init_weights(rng)
                self.loss_history = []

                for epoch in range(self.max_epochs):
                    activations = self._forward(X)
                    output = activations[-1]
                    loss = np.mean((y - output) ** 2)
                    self.loss_history.append(loss)
                    if loss < self.tol:
                        break

                    error = y - output
                    deltas = [error * self.act_deriv(output)]
                    for i in range(self.n_layers - 2, 0, -1):
                        delta = deltas[-1] @ self.weights[i].T * self.act_deriv(activations[i])
                        deltas.append(delta)
                    deltas.reverse()

                    n_samples = max(X.shape[0], 1)
                    for i in range(self.n_layers - 1):
                        self.weights[i] += self.lr * (activations[i].T @ deltas[i]) / n_samples
                        self.biases[i] += self.lr * deltas[i].mean(axis=0, keepdims=True)

                if self.loss_history[-1] < best_loss:
                    best_loss = self.loss_history[-1]
                    best_act = act_name
                    best_state = ([w.copy() for w in self.weights],
                                  [b.copy() for b in self.biases],
                                  list(self.loss_history))

        if best_state is not None:
            self._set_activation(best_act)
            self.weights, self.biases, self.loss_history = best_state

        return {
            'loss_history': self.loss_history,
            'n_epochs': len(self.loss_history),
            'final_loss': self.loss_history[-1]
        }

    def fit(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """train 的别名（sklearn 风格）。"""
        return self.train(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        X = np.atleast_2d(X)
        activations = self._forward(X)
        return activations[-1]


# ============================================================
# 2. RBF 神经网络
# ============================================================
class RBFNetwork:
    """
    径向基函数 (RBF) 神经网络

    适用于: 函数逼近、分类、时间序列预测
    """

    def __init__(self, n_centers: int = 10, spread: float = 1.0):
        self.n_centers = n_centers
        self.spread = spread
        self.centers = None
        self.weights = None

    def _rbf(self, X: np.ndarray, centers: np.ndarray) -> np.ndarray:
        """高斯径向基函数（向量化）"""
        # X: (n, d), centers: (c, d) → 广播求平方距离 (n, c)
        sq_dist = np.sum((X[:, None, :] - centers[None, :, :])**2, axis=2)
        return np.exp(-sq_dist / (2 * self.spread**2))

    def train(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """训练 RBF 网络 (K-means 选中心 + 最小二乘)"""
        from scipy.cluster.vq import kmeans2
        X = np.atleast_2d(X)
        y = np.atleast_1d(y)

        n_samples = X.shape[0]
        if self.n_centers > n_samples:
            self.n_centers = max(1, n_samples)

        # K-means 选择中心
        self.centers, _ = kmeans2(X, self.n_centers, minit='points')

        # 计算隐藏层输出
        G = self._rbf(X, self.centers)

        # 最小二乘求输出权重
        self.weights = np.linalg.lstsq(G, y, rcond=None)[0]

        y_hat = G @ self.weights
        residuals = y - y_hat
        R2 = 1 - np.sum(residuals**2) / np.sum((y - y.mean())**2)

        return {'R2': R2, 'residuals': residuals}

    def fit(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """train 的别名（sklearn 风格）。"""
        return self.train(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        G = self._rbf(X, self.centers)
        return G @ self.weights


# ============================================================
# 3. SOM 自组织映射
# ============================================================
class SOM:
    """
    自组织映射网络 (Self-Organizing Map)

    适用于: 无监督聚类、数据可视化、模式识别
    """

    def __init__(self, grid_size: Tuple[int, int] = (5, 5),
                 n_features: int = 2,
                 learning_rate: float = 0.5,
                 max_epochs: int = 100):
        self.grid_h, self.grid_w = grid_size
        self.n_features = n_features
        self.lr = learning_rate
        self.max_epochs = max_epochs
        self.weights = np.random.randn(self.grid_h, self.grid_w, n_features)

    def train(self, X: np.ndarray) -> Dict:
        """训练 SOM"""
        n = X.shape[0]
        rows, cols = np.meshgrid(
            np.arange(self.grid_h), np.arange(self.grid_w), indexing='ij')
        for epoch in range(self.max_epochs):
            # 学习率和邻域半径衰减
            lr = self.lr * (1 - epoch / self.max_epochs)
            radius = max(1, (self.grid_h / 2) * (1 - epoch / self.max_epochs))

            for i in range(n):
                # 找 BMU (最佳匹配单元)
                dists = np.sum((self.weights - X[i])**2, axis=2)
                bmu = np.unravel_index(np.argmin(dists), (self.grid_h, self.grid_w))

                # 向量化更新权重（消除 r/c 双重循环）
                grid_dist = np.sqrt((rows - bmu[0])**2 + (cols - bmu[1])**2)
                h = np.where(grid_dist <= radius,
                             np.exp(-grid_dist**2 / (2 * radius**2)), 0.0)
                self.weights += (lr * h)[:, :, None] * (X[i] - self.weights)

        return {}

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测每个样本的 BMU 坐标"""
        X = np.atleast_2d(X)
        labels = np.zeros(X.shape[0], dtype=int)
        for i in range(X.shape[0]):
            dists = np.sum((self.weights - X[i])**2, axis=2)
            bmu = np.unravel_index(np.argmin(dists), (self.grid_h, self.grid_w))
            labels[i] = bmu[0] * self.grid_w + bmu[1]
        return labels


# ============================================================
# 4. MIV 变量重要性筛选
# ============================================================
def miv_variable_importance(
    X: np.ndarray,
    y: np.ndarray,
    change_ratio: float = 0.1,
    hidden_sizes: Tuple[int, ...] = (8,),
    learning_rate: float = 0.05,
    max_epochs: int = 2000,
    n_runs: int = 3,
    seed: int | None = 42,
) -> Dict:
    """
    MIV (Mean Impact Value) 变量重要性筛选

    通过 BP 神经网络评估各输入变量对输出的影响程度。
    原理：对每个特征分别增减 change_ratio，观察网络输出变化的均值。
    MIV > 0 表示正向影响，MIV < 0 表示负向影响，|MIV| 越大影响越强。

    Parameters
    ----------
    X : np.ndarray, shape (n_samples, n_features)
        输入特征矩阵
    y : np.ndarray, shape (n_samples,) or (n_samples, 1)
        目标值
    change_ratio : float
        特征扰动比例 (默认 ±10%)
    hidden_sizes : tuple
        隐藏层节点数 (默认 (8,))
    learning_rate : float
        BP 网络学习率
    max_epochs : int
        最大训练轮数
    n_runs : int
        重复运行次数取平均，消除随机性
    seed : int or None
        随机种子

    Returns
    -------
    dict:
        - miv: 各特征的 MIV 值 (n_features,)
        - abs_miv: |MIV| 绝对值 (n_features,)
        - rank: 按 |MIV| 降序排列的特征索引
        - importance_pct: 各特征重要性百分比

    参考
    ----
    ravenxrz/Mathematical-Modeling/neural_network/neural_network_miv.m
    """
    if y.ndim == 1:
        y = y.reshape(-1, 1)
    n_samples, n_features = X.shape
    all_miv = []
    for run in range(n_runs):
        # 训练 BP 网络
        layer_sizes = [n_features] + list(hidden_sizes) + [y.shape[1]]
        bp = BPNeuralNetwork(
            layer_sizes,
            learning_rate=learning_rate,
            max_epochs=max_epochs,
            tol=1e-8,
        )
        bp.train(X, y)

        miv_run = np.zeros(n_features)
        for j in range(n_features):
            # 构造增减数据
            X_inc = X.copy()
            X_dec = X.copy()
            X_inc[:, j] *= (1 + change_ratio)
            X_dec[:, j] *= (1 - change_ratio)

            # 预测
            pred_inc = bp.predict(X_inc)
            pred_dec = bp.predict(X_dec)
            if pred_inc.ndim == 1:
                pred_inc = pred_inc.reshape(-1, 1)
            if pred_dec.ndim == 1:
                pred_dec = pred_dec.reshape(-1, 1)

            # MIV = mean(pred_inc - pred_dec)
            miv_run[j] = np.mean(pred_inc - pred_dec)

        all_miv.append(miv_run)

    miv_values = np.mean(all_miv, axis=0)
    abs_miv = np.abs(miv_values)
    total = abs_miv.sum()
    importance_pct = abs_miv / total * 100 if total > 0 else abs_miv
    rank = np.argsort(-abs_miv)

    return {
        'miv': miv_values,
        'abs_miv': abs_miv,
        'rank': rank,
        'importance_pct': importance_pct,
    }


# ============================================================
# 使用示例
# ============================================================
def example():
    """神经网络示例"""
    np.random.seed(42)

    # 示例1: BP 网络
    print("=" * 60)
    print("示例1: BP 神经网络 — XOR 问题")
    print("=" * 60)
    X = np.array([[0,0],[0,1],[1,0],[1,1]])
    y = np.array([[0],[1],[1],[0]])
    bp = BPNeuralNetwork([2, 4, 1], learning_rate=1.0, max_epochs=5000)
    result = bp.train(X, y)
    pred = bp.predict(X)
    print(f"  训练轮数: {result['n_epochs']}")
    print(f"  最终损失: {result['final_loss']:.6f}")
    print(f"  预测结果: {pred.round(3).flatten()}")

    # 示例2: RBF 网络
    print("\n" + "=" * 60)
    print("示例2: RBF 网络 — 函数逼近")
    print("=" * 60)
    x = np.linspace(0, 2*np.pi, 50).reshape(-1, 1)
    y = np.sin(x).flatten()
    rbf = RBFNetwork(n_centers=10, spread=0.5)
    result = rbf.train(x, y)
    print(f"  R² = {result['R2']:.4f}")


if __name__ == "__main__":
    example()
