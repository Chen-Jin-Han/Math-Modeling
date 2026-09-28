"""Property, boundary, and differential tests for competition-critical algorithms."""

import networkx as nx
import numpy as np
import pytest
from scipy.optimize import linear_sum_assignment

from algorithms.graph_theory import (
    critical_path,
    dijkstra,
    euler_path,
    floyd,
    floyd_get_path,
    graph_coloring,
    hungarian_matching,
    max_flow,
    min_cost_flow,
    prim_mst,
)
from algorithms.image_processing import image_segmentation, morphological_ops, noise_filter
from algorithms.metaheuristic import artificial_fish_swarm
from algorithms.monte_carlo import (
    monte_carlo_integration,
    monte_carlo_optimization,
    monte_carlo_simulation,
    queuing_mmsk,
)


def _random_weighted_graph(seed: int, n: int = 8):
    rng = np.random.default_rng(seed)
    graph = nx.gnp_random_graph(n, 0.45, seed=seed)
    for u, v in graph.edges:
        graph[u][v]["weight"] = int(rng.integers(1, 20))
    matrix = np.full((n, n), np.inf)
    np.fill_diagonal(matrix, 0.0)
    for u, v, data in graph.edges(data=True):
        matrix[u, v] = matrix[v, u] = data["weight"]
    return graph, matrix


@pytest.mark.parametrize("seed", range(5))
def test_shortest_paths_match_networkx(seed):
    graph, matrix = _random_weighted_graph(seed)
    actual, _ = dijkstra(matrix, 0)
    expected = nx.single_source_dijkstra_path_length(graph, 0, weight="weight")
    for vertex in range(len(matrix)):
        assert actual[vertex] == pytest.approx(expected.get(vertex, np.inf))

    all_pairs = floyd(matrix)
    nx_pairs = dict(nx.all_pairs_dijkstra_path_length(graph, weight="weight"))
    for source in range(len(matrix)):
        for target in range(len(matrix)):
            assert all_pairs[source, target] == pytest.approx(
                nx_pairs.get(source, {}).get(target, np.inf)
            )


def test_floyd_path_reconstruction_and_unreachable_boundary():
    matrix = np.array(
        [[0, 2, 10, np.inf], [2, 0, 3, np.inf], [10, 3, 0, np.inf], [np.inf] * 4]
    )
    matrix[3, 3] = 0
    distances, next_node = floyd(matrix, return_next=True)
    assert distances[0, 2] == 5
    assert floyd_get_path(next_node, 0, 2) == [0, 1, 2]
    assert floyd_get_path(next_node, 0, 3) == []


@pytest.mark.parametrize("seed", range(3))
def test_mst_and_max_flow_match_networkx(seed):
    graph, matrix = _random_weighted_graph(seed + 20)
    if nx.is_connected(graph):
        _, actual_weight = prim_mst(matrix)
        expected_weight = nx.minimum_spanning_tree(graph, weight="weight").size(weight="weight")
        assert actual_weight == pytest.approx(expected_weight)

    rng = np.random.default_rng(seed)
    capacity = np.zeros((6, 6), dtype=float)
    flow_graph = nx.DiGraph()
    for u in range(5):
        for v in range(u + 1, 6):
            if rng.random() < 0.5 or v == u + 1:
                value = int(rng.integers(1, 10))
                capacity[u, v] = value
                flow_graph.add_edge(u, v, capacity=value)
    actual_flow, matrix_flow = max_flow(capacity, 0, 5, return_matrix=True)
    assert actual_flow == pytest.approx(nx.maximum_flow_value(flow_graph, 0, 5))
    assert np.all(matrix_flow <= capacity)


def test_critical_path_times_and_slack_properties():
    activities = [
        {"name": "A", "duration": 3, "predecessors": []},
        {"name": "B", "duration": 2, "predecessors": ["A"]},
        {"name": "C", "duration": 4, "predecessors": ["A"]},
        {"name": "D", "duration": 1, "predecessors": ["B", "C"]},
    ]
    result = critical_path(activities)
    assert result["project_duration"] == 8
    assert result["critical_path"] == ["A", "C", "D"]
    assert np.all(result["total_float"] >= 0)
    assert result["total_float"][1] == 2


def test_min_cost_flow_matches_network_simplex():
    capacity = np.array(
        [[0, 4, 3, 0], [0, 0, 2, 4], [0, 0, 0, 5], [0, 0, 0, 0]], dtype=float
    )
    costs = np.array(
        [[0, 2, 5, 0], [0, 0, 1, 4], [0, 0, 0, 1], [0, 0, 0, 0]], dtype=float
    )
    supply = np.array([5, 0, 0, -5], dtype=float)
    actual = min_cost_flow(capacity, costs, supply=supply)
    graph = nx.DiGraph()
    for node, value in enumerate(supply):
        graph.add_node(node, demand=-int(value))
    for u, v in np.argwhere(capacity > 0):
        graph.add_edge(u, v, capacity=int(capacity[u, v]), weight=int(costs[u, v]))
    expected_cost, _ = nx.network_simplex(graph)
    assert actual["success"] is True
    assert actual["total_cost"] == pytest.approx(expected_cost)


def test_min_cost_max_flow_source_sink_mode_and_invalid_inputs():
    capacity = np.array([[0, 3, 2], [0, 0, 4], [0, 0, 0]], dtype=float)
    cost = np.array([[0, 2, 5], [0, 0, 1], [0, 0, 0]], dtype=float)
    result = min_cost_flow(capacity, cost, source=0, sink=2)
    assert result["max_flow"] == 5
    assert result["total_cost"] == 19
    with pytest.raises(ValueError, match="方阵"):
        min_cost_flow(np.ones((2, 3)), np.ones((2, 3)), supply=np.zeros(2))
    with pytest.raises(ValueError, match="形状"):
        min_cost_flow(np.eye(2), np.eye(3), supply=np.zeros(2))
    with pytest.raises(ValueError, match="负值"):
        min_cost_flow(-np.eye(2), np.eye(2), supply=np.zeros(2))
    with pytest.raises(ValueError, match="同时指定"):
        min_cost_flow(np.eye(2), np.eye(2), source=0)
    with pytest.raises(ValueError, match="必须提供"):
        min_cost_flow(np.eye(2), np.eye(2))
    with pytest.raises(ValueError, match="长度"):
        min_cost_flow(np.eye(2), np.eye(2), supply=np.zeros(3))
    with pytest.raises(ValueError, match="平衡"):
        min_cost_flow(np.eye(2), np.eye(2), supply=np.ones(2))


def test_coloring_euler_and_assignment_invariants():
    cycle = nx.cycle_graph(6)
    adjacency = nx.to_numpy_array(cycle, dtype=int)
    coloring = graph_coloring(adjacency, method="greedy")
    assert coloring["n_colors"] == 2
    assert all(coloring["coloring"][u] != coloring["coloring"][v] for u, v in cycle.edges)
    circuit = euler_path(adjacency)
    traversed = [frozenset(edge) for edge in zip(circuit["path"], circuit["path"][1:])]
    assert circuit["type"] == "circuit"
    assert len(traversed) == cycle.number_of_edges()
    assert set(traversed) == {frozenset(edge) for edge in cycle.edges}

    path_graph = nx.to_numpy_array(nx.path_graph(4), dtype=int)
    path = euler_path(path_graph, start=2)
    assert path["type"] == "path"
    assert path["path"][0] in {0, 3}
    assert euler_path(nx.to_numpy_array(nx.star_graph(4), dtype=int))["exists"] is False
    disconnected = np.zeros((6, 6), dtype=int)
    disconnected[0, 1] = disconnected[1, 0] = 1
    disconnected[2, 3] = disconnected[3, 2] = 1
    assert euler_path(disconnected)["exists"] is False

    costs = np.array([[9, 2, 7], [6, 4, 3], [5, 8, 1]], dtype=float)
    assignment = hungarian_matching(costs)
    rows, cols = linear_sum_assignment(costs)
    assert assignment["total_cost"] == costs[rows, cols].sum()
    assert sorted(assignment["matching"]) == [0, 1, 2]
    with pytest.raises(ValueError, match="方阵"):
        graph_coloring(np.ones((2, 3)))
    with pytest.raises(ValueError, match="method"):
        graph_coloring(np.eye(2), method="random")


def test_morphology_set_inclusion_and_segmentation_boundaries():
    image = np.zeros((9, 9), dtype=np.uint8)
    image[4, 4] = 255
    dilated = morphological_ops(image, "dilate", kernel_size=3)
    eroded = morphological_ops(dilated, "erode", kernel_size=3)
    opened = morphological_ops(dilated, "open", kernel_size=3)
    closed = morphological_ops(image, "close", kernel_size=3)
    assert np.count_nonzero(dilated) >= np.count_nonzero(image)
    assert np.count_nonzero(eroded) <= np.count_nonzero(dilated)
    assert np.array_equal(opened, dilated)
    assert closed.shape == image.shape
    watershed = image_segmentation(dilated, method="watershed")
    assert watershed.shape == image.shape
    with pytest.raises(ValueError, match="未知滤波方法"):
        noise_filter(image, method="invalid")
    with pytest.raises(ValueError, match="未知分割方法"):
        image_segmentation(image, method="invalid")


def test_artificial_fish_is_reproducible_bounded_and_supports_maximize():
    bounds = (np.array([-2.0, -2.0]), np.array([2.0, 2.0]))
    np.random.seed(123)
    first = artificial_fish_swarm(
        lambda x: np.sum(x**2), 2, bounds, n_fish=12, max_iter=10
    )
    np.random.seed(123)
    second = artificial_fish_swarm(
        lambda x: np.sum(x**2), 2, bounds, n_fish=12, max_iter=10
    )
    np.testing.assert_allclose(first["x"], second["x"])
    assert first["f"] == pytest.approx(second["f"])
    assert np.all(first["x"] >= bounds[0]) and np.all(first["x"] <= bounds[1])
    np.random.seed(321)
    maximized = artificial_fish_swarm(
        lambda x: -np.sum(x**2), 2, bounds, n_fish=12, max_iter=10, maximize=True
    )
    assert maximized["f"] <= 0


def test_monte_carlo_fallbacks_vector_outputs_and_queue_properties():
    scalar_only = lambda x: float(x**2)
    integral = monte_carlo_integration(scalar_only, 0, 1, 2000, seed=7)
    assert integral.estimate == pytest.approx(1 / 3, abs=0.03)
    _, optimum, _ = monte_carlo_optimization(
        lambda x: float(np.sum(x**2)), [(-1, 1), (-1, 1)], 2000, seed=7
    )
    assert optimum < 0.01
    simulation = monte_carlo_simulation(
        lambda x: np.array([x[0], x[0] ** 2]),
        [lambda: np.random.normal()],
        n_samples=200,
        seed=7,
        vectorized_model=lambda values: np.column_stack((values[:, 0], values[:, 0] ** 2)),
    )
    assert set(simulation) == {"output_0", "output_1"}

    mm1 = queuing_mmsk(0.5, 1.0, n_servers=1, n_customers=3000, seed=7)
    assert mm1["avg_wait_time"] == pytest.approx(1.0)
    assert mm1["avg_system_length"] == pytest.approx(1.0)
    finite = queuing_mmsk(2.0, 1.0, n_servers=2, capacity=4, n_customers=3000, seed=7)
    assert 0 < finite["pk"] < 1
    assert finite["n_rejected"] > 0
    rho_one = queuing_mmsk(2.0, 1.0, n_servers=2, capacity=4, n_customers=500, seed=8)
    assert np.isfinite(rho_one["p0"])
    unstable = queuing_mmsk(3.0, 1.0, n_servers=2, n_customers=500, seed=9)
    assert np.isinf(unstable["avg_wait_time"])
