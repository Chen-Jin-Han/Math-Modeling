"""神经网络模块测试"""
import numpy as np
from algorithms.neural_network import BPNeuralNetwork, RBFNetwork


class TestBPNeuralNetwork:
    """BP 神经网络测试"""

    def test_xor_problem(self):
        """XOR 问题"""
        X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
        y = np.array([[0], [1], [1], [0]], dtype=float)
        nn = BPNeuralNetwork(layers=[2, 8, 1], lr=0.5, max_iter=1000)
        nn.fit(X, y)
        predictions = nn.predict(X)
        assert np.mean(np.abs(predictions - y)) < 0.3

    def test_simple_function(self):
        """简单函数拟合"""
        np.random.seed(42)
        X = np.random.rand(50, 2)
        y = (X[:, 0] + X[:, 1]).reshape(-1, 1)
        nn = BPNeuralNetwork(layers=[2, 10, 1], lr=0.3, max_iter=500)
        nn.fit(X, y)
        pred = nn.predict(X[:5])
        assert np.mean(np.abs(pred - y[:5])) < 0.5

    def test_predict_shape(self):
        X = np.array([[0, 0], [1, 1]], dtype=float)
        y = np.array([[0], [1]], dtype=float)
        nn = BPNeuralNetwork(layers=[2, 4, 1], max_iter=100)
        nn.fit(X, y)
        pred = nn.predict(X)
        assert pred.shape == (2, 1)

    def test_convergence(self):
        """损失应下降"""
        np.random.seed(42)
        X = np.random.rand(20, 2)
        y = X[:, 0:1]
        nn = BPNeuralNetwork(layers=[2, 5, 1], lr=0.1, max_iter=200)
        nn.fit(X, y)
        assert nn.loss_history[-1] < nn.loss_history[0]

    def test_binary_classification(self):
        """二分类"""
        X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
        y = np.array([[0], [1], [1], [1]], dtype=float)
        nn = BPNeuralNetwork(layers=[2, 4, 1], lr=0.5, max_iter=500)
        nn.fit(X, y)
        pred = nn.predict(X)
        assert np.mean(np.abs(pred - y)) < 0.3


class TestRBFNetwork:
    """RBF 网络测试"""

    def test_interpolation(self):
        X = np.array([[0], [1], [2], [3]], dtype=float)
        y = np.array([0, 1, 4, 9], dtype=float)
        net = RBFNetwork()
        net.fit(X, y)
        pred = net.predict(X)
        np.testing.assert_allclose(pred, y, atol=0.5)

    def test_predict_shape(self):
        X = np.array([[0], [1], [2]], dtype=float)
        y = np.array([0, 1, 4], dtype=float)
        net = RBFNetwork()
        net.fit(X, y)
        pred = net.predict(X)
        assert len(pred) == 3

    def test_linear_data(self):
        X = np.array([[0], [1], [2], [3]], dtype=float)
        y = np.array([0, 1, 2, 3], dtype=float)
        net = RBFNetwork()
        net.fit(X, y)
        pred = net.predict(np.array([[1.5]]))
        assert abs(pred[0] - 1.5) < 0.5

    def test_quadratic_data(self):
        X = np.array([[0], [1], [2], [3], [4]], dtype=float)
        y = X[:, 0]**2
        net = RBFNetwork()
        net.fit(X, y)
        pred = net.predict(np.array([[2.5]]))
        assert abs(pred[0] - 6.25) < 1.0

    def test_2d_input(self):
        X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
        y = np.array([0, 1, 1, 2], dtype=float)
        net = RBFNetwork()
        net.fit(X, y)
        pred = net.predict(X)
        assert len(pred) == 4
