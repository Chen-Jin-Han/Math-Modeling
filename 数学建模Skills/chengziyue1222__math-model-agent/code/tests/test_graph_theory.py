"""图论算法测试"""
import numpy as np
import pytest
from algorithms.graph_theory import (
    dijkstra,
    floyd,
    get_path,
    graph_coloring,
    max_flow,
    min_cost_flow,
    prim_mst,
)


class TestDijkstra:
    """Dijkstra 最短路径测试"""

    def test_simple_graph(self):
        G = [
            [(1, 1), (2, 4)],
            [(0, 1), (2, 2), (3, 6)],
            [(0, 4), (1, 2), (3, 3)],
            [(1, 6), (2, 3)],
        ]
        dist, prev = dijkstra(G, 0)
        assert dist[3] == 6  # 0->1->2->3 = 1+2+3

    def test_direct_path(self):
        G = [
            [(1, 5)],
            [(0, 5), (2, 3)],
            [(1, 3)],
        ]
        dist, prev = dijkstra(G, 0)
        assert dist[0] == 0
        assert dist[1] == 5
        assert dist[2] == 8

    def test_disconnected(self):
        G = [
            [(1, 1)],
            [(0, 1)],
            [(3, 1)],
            [(2, 1)],
        ]
        dist, prev = dijkstra(G, 0)
        assert dist[2] == float('inf')

    def test_self_distance_zero(self):
        G = [[(1, 1)], [(0, 1)]]
        dist, _ = dijkstra(G, 0)
        assert dist[0] == 0

    def test_path_reconstruction(self):
        G = [
            [(1, 1), (2, 10)],
            [(0, 1), (2, 2)],
            [(0, 10), (1, 2)],
        ]
        dist, prev = dijkstra(G, 0)
        path = get_path(prev, 2)
        assert path == [0, 1, 2]


class TestFloyd:
    """Floyd 全源最短路径测试"""

    def test_all_pairs(self):
        n = 3
        INF = float('inf')
        G = [[INF]*n for _ in range(n)]
        for i in range(n): G[i][i] = 0
        G[0][1] = 1; G[1][0] = 1
        G[1][2] = 2; G[2][1] = 2
        G[0][2] = 4; G[2][0] = 4
        dist = floyd(G)
        assert dist[0][2] == 3  # 0->1->2

    def test_diagonal_zero(self):
        G = [[0, 1], [1, 0]]
        dist = floyd(G)
        assert dist[0][0] == 0
        assert dist[1][1] == 0

    def test_symmetric(self):
        n = 3
        INF = float('inf')
        G = [[INF]*n for _ in range(n)]
        for i in range(n): G[i][i] = 0
        G[0][1] = 5; G[1][0] = 5
        G[1][2] = 3; G[2][1] = 3
        dist = floyd(G)
        assert dist[0][2] == dist[2][0]


class TestPrimMST:
    """Prim 最小生成树测试"""

    def test_mst_weight(self):
        G = [
            [(1, 1), (2, 4)],
            [(0, 1), (2, 2), (3, 6)],
            [(0, 4), (1, 2), (3, 3)],
            [(1, 6), (2, 3)],
        ]
        mst_edges, total = prim_mst(G)
        assert total == 6  # 1+2+3

    def test_mst_edges_count(self):
        G = [
            [(1, 1)],
            [(0, 1), (2, 2)],
            [(1, 2), (3, 3)],
            [(2, 3)],
        ]
        mst_edges, total = prim_mst(G)
        assert len(mst_edges) == 3  # n-1


class TestMaxFlow:
    """最大流测试"""

    def test_simple_flow(self):
        n = 4
        cap = [[0]*n for _ in range(n)]
        cap[0][1] = 10; cap[0][2] = 10
        cap[1][2] = 2; cap[1][3] = 10
        cap[2][3] = 10
        flow = max_flow(cap, 0, 3)
        assert flow == 20

    def test_bottleneck(self):
        n = 3
        cap = [[0]*n for _ in range(n)]
        cap[0][1] = 5
        cap[1][2] = 3
        flow = max_flow(cap, 0, 2)
        assert flow == 3


class TestMinCostFlow:
    def test_supply_sign_and_total_flow(self):
        capacity = np.array([[0.0, 5.0], [0.0, 0.0]])
        cost = np.array([[0.0, 2.0], [0.0, 0.0]])

        result = min_cost_flow(capacity, cost, supply=np.array([5.0, -5.0]))

        assert result['success'] is True
        assert result['flow'][0, 1] == pytest.approx(5.0)
        assert result['total_cost'] == pytest.approx(10.0)
        assert result['max_flow'] == pytest.approx(5.0)

    def test_infeasible_supply_returns_failure(self):
        capacity = np.array([[0.0, 4.0], [0.0, 0.0]])
        cost = np.array([[0.0, 2.0], [0.0, 0.0]])

        result = min_cost_flow(capacity, cost, supply=np.array([5.0, -5.0]))

        assert result['success'] is False
        assert np.isinf(result['total_cost'])


class TestGraphColoring:
    def test_exact_finds_two_colors_for_crown_graph(self):
        # K3,3 去掉一组完美匹配；按自然顶点顺序贪心可用 3 色，但色数为 2。
        adj = np.zeros((6, 6), dtype=int)
        for left in range(3):
            for right in range(3):
                if left != right:
                    adj[2 * left, 2 * right + 1] = 1
                    adj[2 * right + 1, 2 * left] = 1

        result = graph_coloring(adj, method='exact')

        assert result['n_colors'] == 2
        for u, v in np.argwhere(adj):
            assert result['coloring'][u] != result['coloring'][v]
