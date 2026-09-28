"""元胞自动机测试"""
import numpy as np
from algorithms.cellular_automata import ElementaryCA, GameOfLife


class TestElementaryCA:
    """一维元胞自动机测试"""

    def test_rule_30(self):
        """Rule 30 应产生非平凡图案"""
        ca = ElementaryCA(rule=30, size=101)
        ca.initialize(center=True)
        ca.evolve(steps=50)
        assert ca.history.shape == (51, 101)
        assert np.sum(ca.history) > 0

    def test_rule_110(self):
        """Rule 110 是图灵完备的"""
        ca = ElementaryCA(rule=110, size=100)
        ca.initialize(random=True, seed=42)
        ca.evolve(steps=100)
        assert ca.history.shape == (101, 100)

    def test_rule_0(self):
        """Rule 0: 全部变为0"""
        ca = ElementaryCA(rule=0, size=50)
        ca.initialize(center=True)
        ca.evolve(steps=10)
        assert np.sum(ca.history[-1]) == 0

    def test_rule_255(self):
        """Rule 255: 全部变为1"""
        ca = ElementaryCA(rule=255, size=50)
        ca.initialize(center=True)
        ca.evolve(steps=10)
        assert np.all(ca.history[-1] == 1)

    def test_random_init(self):
        """随机初始化"""
        ca = ElementaryCA(rule=30, size=50)
        ca.initialize(random=True, seed=42)
        assert np.sum(ca.history[0]) > 0


class TestGameOfLife:
    """生命游戏测试"""

    def test_still_life_block(self):
        """2x2 方块是静物"""
        gol = GameOfLife(rows=10, cols=10)
        gol.grid[4:6, 4:6] = 1
        gol.evolve(steps=10)
        assert np.array_equal(gol.grid[4:6, 4:6], np.ones((2, 2), dtype=int))

    def test_blinker(self):
        """闪烁器（周期2）"""
        gol = GameOfLife(rows=10, cols=10)
        gol.grid[5, 4:7] = 1  # 水平线
        gol.evolve(steps=1)
        # 应变为垂直线
        assert gol.grid[4:7, 5].sum() == 3

    def test_empty_stays_empty(self):
        """空网格保持为空"""
        gol = GameOfLife(rows=10, cols=10)
        gol.evolve(steps=10)
        assert np.sum(gol.grid) == 0

    def test_output_shape(self):
        gol = GameOfLife(rows=20, cols=20)
        gol.evolve(steps=5)
        assert gol.grid.shape == (20, 20)

    def test_glider(self):
        """滑翔机应移动"""
        gol = GameOfLife(rows=20, cols=20)
        # 标准滑翔机
        gol.grid[1, 2] = 1
        gol.grid[2, 3] = 1
        gol.grid[3, 1:4] = 1
        initial_sum = np.sum(gol.grid)
        gol.evolve(steps=4)
        # 滑翔机应保持相同数量的活细胞
        assert np.sum(gol.grid) == initial_sum
