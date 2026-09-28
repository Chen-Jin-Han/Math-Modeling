"""
图论工具箱
==========
包含：Dijkstra最短路径、Floyd最短路径、最小生成树、最大流、关键路径(PERT)、
     最小费用流、图的染色、Euler/Hamilton路径、二分图匹配（匈牙利算法）

参考：Algorithms_MathModels/GraphTheory(图论)/
      HuangCongQing/Algorithms_MathModels/GraphTheory/detailed/
"""

import numpy as np
from typing import Tuple, Dict, List, Optional, Union


def _to_adj_matrix(graph: Union[np.ndarray, List], n: Optional[int] = None) -> np.ndarray:
    """将邻接矩阵或邻接表统一转换为邻接矩阵。"""
    if isinstance(graph, np.ndarray):
        return graph.astype(float)
    if not graph:
        raise ValueError("图不能为空")
    # 邻接表: [[(j, w), ...], ...]
    if graph and isinstance(graph[0], (list, tuple)) and graph[0] and isinstance(graph[0][0], tuple):
        if n is None:
            n = len(graph)
        mat = np.full((n, n), np.inf)
        for i in range(n):
            mat[i, i] = 0
            for edge in graph[i]:
                j, w = edge
                mat[i, j] = float(w)
        return mat
    # 邻接矩阵: [[0, 1, inf], ...]
    return np.array(graph, dtype=float)


# ============================================================
# 1. Dijkstra 最短路径
# ============================================================
def dijkstra(graph: Union[np.ndarray, List], source: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Dijkstra 最短路径算法

    Parameters
    ----------
    graph : np.ndarray or list
        邻接矩阵 (n, n) 或邻接表 [[(j, w), ...], ...]
    source : int
        源节点 (0-indexed)

    Returns
    -------
    dist : np.ndarray
        从源到各点的最短距离
    prev : np.ndarray
        前驱节点 (用于重建路径)
    """
    adj_matrix = _to_adj_matrix(graph)
    n = adj_matrix.shape[0]
    dist = np.full(n, np.inf)
    prev = np.full(n, -1, dtype=int)
    visited = np.zeros(n, bool)
    dist[source] = 0

    for _ in range(n):
        # 找未访问的最小距离节点
        min_d = np.inf
        u = -1
        for i in range(n):
            if not visited[i] and dist[i] < min_d:
                min_d = dist[i]
                u = i
        if u == -1:
            break
        visited[u] = True
        for v in range(n):
            if not visited[v] and adj_matrix[u, v] < np.inf:
                new_dist = dist[u] + adj_matrix[u, v]
                if new_dist < dist[v]:
                    dist[v] = new_dist
                    prev[v] = u

    return dist, prev


def get_path(prev: np.ndarray, target: int) -> List[int]:
    """从 prev 数组重建路径"""
    path = []
    while target != -1:
        path.append(target)
        target = prev[target]
    return path[::-1]


# ============================================================
# 2. Floyd 最短路径 (所有节点对)
# ============================================================
def floyd(graph: Union[np.ndarray, List], return_next: bool = False):
    """
    Floyd-Warshall 全源最短路径

    Parameters
    ----------
    graph : np.ndarray or list
        邻接矩阵 (n, n) 或邻接表
    return_next : bool
        是否同时返回路径重建矩阵

    Returns
    -------
    dist : np.ndarray
        最短距离矩阵 (n, n)
    next_node : np.ndarray, optional
        路径重建矩阵 (仅 return_next=True)
    """
    adj_matrix = _to_adj_matrix(graph)
    n = adj_matrix.shape[0]
    dist = adj_matrix.copy()
    next_node = np.full((n, n), -1, dtype=int)

    for i in range(n):
        for j in range(n):
            if i != j and dist[i, j] < np.inf:
                next_node[i, j] = j

    for k in range(n):
        for i in range(n):
            for j in range(n):
                if dist[i, k] + dist[k, j] < dist[i, j]:
                    dist[i, j] = dist[i, k] + dist[k, j]
                    next_node[i, j] = next_node[i, k]

    if return_next:
        return dist, next_node
    return dist


def floyd_get_path(next_node: np.ndarray, i: int, j: int) -> List[int]:
    """Floyd 路径重建"""
    if next_node[i, j] == -1:
        return []
    path = [i]
    while i != j:
        i = next_node[i, j]
        path.append(i)
    return path


# ============================================================
# 3. 最小生成树 (Prim / Kruskal)
# ============================================================
def prim_mst(graph: Union[np.ndarray, List]) -> Tuple[List[Tuple], float]:
    """
    Prim 最小生成树

    Parameters
    ----------
    graph : np.ndarray or list
        邻接矩阵 (n, n) 或邻接表, inf 表示无边

    Returns
    -------
    edges : list of (u, v, weight)
        最小生成树的边
    total_weight : float
        总权重
    """
    adj_matrix = _to_adj_matrix(graph)
    n = adj_matrix.shape[0]
    in_mst = np.zeros(n, bool)
    key = np.full(n, np.inf)
    parent = np.full(n, -1, dtype=int)
    key[0] = 0

    edges = []
    total = 0.0

    for _ in range(n):
        u = -1
        for i in range(n):
            if not in_mst[i] and (u == -1 or key[i] < key[u]):
                u = i
        if u == -1:
            break
        in_mst[u] = True
        if parent[u] != -1:
            edges.append((parent[u], u, adj_matrix[parent[u], u]))
            total += adj_matrix[parent[u], u]

        for v in range(n):
            if not in_mst[v] and adj_matrix[u, v] < key[v]:
                key[v] = adj_matrix[u, v]
                parent[v] = u

    return edges, total


# ============================================================
# 4. 最大流 (Ford-Fulkerson)
# ============================================================
def max_flow(capacity: Union[np.ndarray, List], source: int, sink: int,
             return_matrix: bool = False):
    """
    Ford-Fulkerson 最大流算法 (BFS 增广路径)

    Parameters
    ----------
    capacity : np.ndarray or list
        容量矩阵 (n, n)
    source : int
        源节点
    sink : int
        汇节点
    return_matrix : bool
        是否同时返回流量分配矩阵

    Returns
    -------
    max_flow_value : float
        最大流量
    flow_matrix : np.ndarray, optional
        流量分配矩阵 (仅 return_matrix=True)
    """
    capacity = _to_adj_matrix(capacity)
    n = capacity.shape[0]
    flow = np.zeros((n, n))
    residual = capacity.copy()

    max_flow_val = 0

    while True:
        # BFS 找增广路径
        parent = np.full(n, -1, dtype=int)
        queue = [source]
        parent[source] = source

        while queue and parent[sink] == -1:
            u = queue.pop(0)
            for v in range(n):
                if parent[v] == -1 and residual[u, v] > 0:
                    parent[v] = u
                    queue.append(v)

        if parent[sink] == -1:
            break

        # 找瓶颈
        path_flow = np.inf
        v = sink
        while v != source:
            u = parent[v]
            path_flow = min(path_flow, residual[u, v])
            v = u

        # 更新残余图和流量
        v = sink
        while v != source:
            u = parent[v]
            residual[u, v] -= path_flow
            residual[v, u] += path_flow
            flow[u, v] += path_flow
            v = u

        max_flow_val += path_flow

    if return_matrix:
        return max_flow_val, flow
    return max_flow_val


# ============================================================
# 5. 关键路径 (PERT)
# ============================================================
def critical_path(activities: List[Dict]) -> Dict:
    """
    关键路径法 (CPM/PERT)

    Parameters
    ----------
    activities : list of dict
        每个活动包含: 'name', 'duration', 'predecessors'
        predecessors 是前驱活动名称列表

    Returns
    -------
    dict : 关键路径、总工期、各活动的时间参数
    """
    # 构建图
    names = [a['name'] for a in activities]
    n = len(names)
    name_to_idx = {name: i for i, name in enumerate(names)}

    duration = np.array([a['duration'] for a in activities])
    successors = [[] for _ in range(n)]
    in_degree = np.zeros(n, int)

    for i, a in enumerate(activities):
        for pred in a.get('predecessors', []):
            j = name_to_idx[pred]
            successors[j].append(i)
            in_degree[i] += 1

    # 正推: 最早开始/完成
    ES = np.zeros(n)  # Earliest Start
    EF = np.zeros(n)  # Earliest Finish
    order = []
    queue = [i for i in range(n) if in_degree[i] == 0]

    while queue:
        u = queue.pop(0)
        order.append(u)
        EF[u] = ES[u] + duration[u]
        for v in successors[u]:
            ES[v] = max(ES[v], EF[u])
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    # 逆推: 最晚开始/完成
    project_duration = max(EF)
    LS = np.full(n, project_duration)  # Latest Start
    LF = np.full(n, project_duration)  # Latest Finish

    for u in reversed(order):
        LF[u] = min([LS[v] for v in successors[u]], default=project_duration)
        LS[u] = LF[u] - duration[u]

    # 总浮动时间
    TF = LS - ES  # Total Float
    critical = np.abs(TF) < 1e-10

    return {
        'project_duration': project_duration,
        'ES': ES, 'EF': EF, 'LS': LS, 'LF': LF,
        'total_float': TF,
        'critical': critical,
        'critical_path': [names[i] for i in range(n) if critical[i]],
        'names': names
    }


# ============================================================
# 6. 最小费用流
# ============================================================
def min_cost_flow(
    capacity: np.ndarray,
    cost: np.ndarray,
    supply: np.ndarray | None = None,
    source: int | None = None,
    sink: int | None = None,
) -> Dict:
    """
    最小费用最大流（Successive Shortest Path / SPFA 实现）

    在满足流量约束的前提下，使总运输费用最小。
    竞赛中常用于：运输调度、物流配送、资源分配。

    Parameters
    ----------
    capacity : np.ndarray, shape (n, n)
        容量矩阵，capacity[i][j] = i→j 的最大流量
    cost : np.ndarray, shape (n, n)
        单位流量费用矩阵，cost[i][j] = i→j 的单位运费
    supply : np.ndarray, shape (n,)
        供给/需求向量：正=供给节点，负=需求节点，0=转运节点
        或者：指定 source/sink 时，supply 为各节点的净流量
    source : int or None
        源点（与 supply 二选一）
    sink : int or None
        汇点（与 supply 二选一）

    Returns
    -------
    dict:
        - flow: 流量矩阵
        - total_cost: 总费用
        - max_flow: 总流量
    """
    capacity = np.asarray(capacity, dtype=float)
    cost = np.asarray(cost, dtype=float)
    if capacity.ndim != 2 or capacity.shape[0] != capacity.shape[1]:
        raise ValueError("capacity 必须是方阵")
    if cost.shape != capacity.shape:
        raise ValueError("cost 必须与 capacity 形状相同")
    if np.any(capacity < 0):
        raise ValueError("capacity 不能包含负值")
    if (source is None) != (sink is None):
        raise ValueError("source 和 sink 必须同时指定")
    if source is None and supply is None:
        raise ValueError("必须提供 supply，或同时提供 source 和 sink")

    n = capacity.shape[0]
    cap = capacity.copy()
    cst = cost.copy()
    flow_mat = np.zeros((n, n))

    # 构造供给向量
    if source is not None and sink is not None:
        # 不指定具体供给量，最大化从 source 到 sink 的流量
        # 使用 SPFA 找增广路
        total_flow = 0
        total_cost_val = 0
        while True:
            # SPFA 找最短增广路（考虑费用）
            dist = np.full(n, np.inf)
            prev = np.full(n, -1, dtype=int)
            in_queue = np.zeros(n, dtype=bool)
            dist[source] = 0
            queue = [source]
            in_queue[source] = True

            while queue:
                u = queue.pop(0)
                in_queue[u] = False
                for v in range(n):
                    if cap[u][v] > 0:
                        nd = dist[u] + cst[u][v]
                        if nd < dist[v]:
                            dist[v] = nd
                            prev[v] = u
                            if not in_queue[v]:
                                queue.append(v)
                                in_queue[v] = True
                    # 反向边（退流）
                    if flow_mat[v][u] > 0:
                        nd = dist[u] - cst[v][u]
                        if nd < dist[v]:
                            dist[v] = nd
                            prev[v] = u
                            if not in_queue[v]:
                                queue.append(v)
                                in_queue[v] = True

            if dist[sink] == np.inf:
                break

            # 找瓶颈
            path_flow = np.inf
            v = sink
            while v != source:
                u = prev[v]
                if cap[u][v] > 0:
                    path_flow = min(path_flow, cap[u][v])
                else:
                    path_flow = min(path_flow, flow_mat[v][u])
                v = u

            # 更新流量
            v = sink
            while v != source:
                u = prev[v]
                if cap[u][v] > 0:
                    cap[u][v] -= path_flow
                    flow_mat[u][v] += path_flow
                    total_cost_val += path_flow * cst[u][v]
                else:
                    flow_mat[v][u] -= path_flow
                    cap[v][u] += path_flow
                    total_cost_val -= path_flow * cst[v][u]
                v = u

            total_flow += path_flow

        return {
            'flow': flow_mat,
            'total_cost': total_cost_val,
            'max_flow': total_flow,
            'success': True,
            'message': '最小费用最大流求解成功',
        }
    else:
        # 使用 supply 向量的通用最小费用流
        # 简化实现：转化为 LP 求解
        from scipy.optimize import linprog
        n_edges = 0
        edges = []
        for i in range(n):
            for j in range(n):
                if cap[i][j] > 0:
                    edges.append((i, j))
                    n_edges += 1

        supply = np.asarray(supply, dtype=float)
        if supply.shape != (n,):
            raise ValueError(f"supply 必须是长度为 {n} 的一维数组")
        if not np.isclose(supply.sum(), 0.0):
            raise ValueError("supply 的总供给与总需求必须平衡（和为 0）")

        c = [cst[i][j] for i, j in edges]
        # 等式约束：每个节点的流入-流出 = supply
        A_eq = np.zeros((n, n_edges))
        for idx, (i, j) in enumerate(edges):
            A_eq[i][idx] = -1  # 流出
            A_eq[j][idx] = 1   # 流入
        b_eq = -supply
        bounds = [(0, cap[i][j]) for i, j in edges]

        result = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds)
        flow = np.zeros((n, n))
        if not result.success:
            return {
                'flow': flow,
                'total_cost': np.inf,
                'max_flow': 0.0,
                'success': False,
                'message': result.message,
            }
        for idx, (i, j) in enumerate(edges):
            flow[i][j] = result.x[idx]

        return {
            'flow': flow,
            'total_cost': float(result.fun),
            'max_flow': float(supply[supply > 0].sum()),
            'success': True,
            'message': result.message,
        }


# ============================================================
# 7. 图的染色
# ============================================================
def graph_coloring(adj_matrix: np.ndarray, method: str = 'greedy') -> Dict:
    """
    图的染色（着色）问题

    用最少的颜色给图的顶点着色，使得相邻顶点颜色不同。
    竞赛中常用于：排课问题、频率分配、地图着色。

    Parameters
    ----------
    adj_matrix : np.ndarray, shape (n, n)
        邻接矩阵（无向图）
    method : str
        'greedy' 贪心算法（快速近似）或 'exact' 精确算法（小规模）

    Returns
    -------
    dict:
        - coloring: 各顶点的颜色编号 (0, 1, 2, ...)
        - n_colors: 使用的颜色数（色数上界）
        - color_groups: 同色顶点分组
    """
    adj_matrix = np.asarray(adj_matrix)
    if adj_matrix.ndim != 2 or adj_matrix.shape[0] != adj_matrix.shape[1]:
        raise ValueError("adj_matrix 必须是方阵")
    if method not in {'greedy', 'exact'}:
        raise ValueError("method 必须是 'greedy' 或 'exact'")

    n = adj_matrix.shape[0]
    adj = np.maximum(adj_matrix, adj_matrix.T) > 0
    np.fill_diagonal(adj, False)

    if method == 'greedy':
        # 贪心算法：按度数降序排列，依次选最小可用颜色
        degrees = adj.sum(axis=1)
        order = np.argsort(-degrees)
        coloring = np.full(n, -1)

        for v in order:
            # 找邻接节点已用颜色
            used = set()
            for u in range(n):
                if adj[v][u] and coloring[u] >= 0:
                    used.add(coloring[u])
            # 选最小可用颜色
            c = 0
            while c in used:
                c += 1
            coloring[v] = c

    else:
        # 逐步尝试 k 色可行性，第一个可行的 k 即为色数。
        order = np.argsort(-adj.sum(axis=1))
        coloring = np.full(n, -1, dtype=int)

        def backtrack(position: int, n_allowed_colors: int) -> bool:
            if position == n:
                return True
            vertex = int(order[position])
            neighbor_colors = {
                int(coloring[u]) for u in range(n) if adj[vertex, u] and coloring[u] >= 0
            }
            for color in range(n_allowed_colors):
                if color in neighbor_colors:
                    continue
                coloring[vertex] = color
                if backtrack(position + 1, n_allowed_colors):
                    return True
                coloring[vertex] = -1
            return False

        for n_allowed_colors in range(1, n + 1):
            coloring.fill(-1)
            if backtrack(0, n_allowed_colors):
                break

    n_colors = int(coloring.max()) + 1
    color_groups = [[] for _ in range(n_colors)]
    for v in range(n):
        color_groups[coloring[v]].append(v)

    return {
        'coloring': coloring,
        'n_colors': n_colors,
        'color_groups': color_groups,
    }


# ============================================================
# 8. Euler 路径/回路
# ============================================================
def euler_path(adj_matrix: np.ndarray, start: int = 0) -> Dict:
    """
    Euler 路径/回路（Fleury 算法）

    找到经过图中每条边恰好一次的路径。
    - Euler 回路：所有顶点度数为偶
    - Euler 路径：恰好 2 个顶点度数为奇

    竞赛中常用于：一笔画问题、邮递员问题。

    Parameters
    ----------
    adj_matrix : np.ndarray, shape (n, n)
        邻接矩阵（无向图）
    start : int
        起始节点

    Returns
    -------
    dict:
        - path: Euler 路径/回路（节点序列）
        - type: 'circuit'（回路）或 'path'（路径）或 'none'（不存在）
        - exists: 是否存在 Euler 路径/回路
    """
    n = adj_matrix.shape[0]
    adj = adj_matrix.astype(float).copy()
    # 确保对称
    adj = np.maximum(adj, adj.T)

    # 检查度数
    degrees = (adj > 0).sum(axis=1)
    odd_vertices = np.where(degrees % 2 == 1)[0]

    if len(odd_vertices) == 0:
        euler_type = 'circuit'
    elif len(odd_vertices) == 2:
        euler_type = 'path'
        start = odd_vertices[0]  # 从奇度点出发
    else:
        return {'path': [], 'type': 'none', 'exists': False}

    # 检查连通性（简化：只检查有边的节点）
    visited_check = set()
    stack_check = [start]
    adj_bool = adj > 0
    while stack_check:
        u = stack_check.pop()
        if u in visited_check:
            continue
        visited_check.add(u)
        for v in range(n):
            if adj_bool[u][v] and v not in visited_check:
                stack_check.append(v)

    # 所有有边的节点都应可达
    has_edge = set(np.where(degrees > 0)[0])
    if not has_edge.issubset(visited_check):
        return {'path': [], 'type': 'none', 'exists': False}

    # Hierholzer 算法（比 Fleury 更高效）
    adj_copy = adj.copy()
    path = []
    stack = [start]

    while stack:
        v = stack[-1]
        # 找一条未走过的边
        found = False
        for u in range(n):
            if adj_copy[v][u] > 0:
                adj_copy[v][u] -= 1
                adj_copy[u][v] -= 1
                stack.append(u)
                found = True
                break
        if not found:
            path.append(stack.pop())

    path.reverse()

    return {
        'path': path,
        'type': euler_type,
        'exists': True,
    }


# ============================================================
# 9. 二分图匹配（匈牙利算法）
# ============================================================
def hungarian_matching(cost_matrix: np.ndarray) -> Dict:
    """
    匈牙利算法（Kuhn-Munkres）

    求解二分图的最优（最小权）完美匹配。
    竞赛中常用于：指派问题、任务分配、最优匹配。

    Parameters
    ----------
    cost_matrix : np.ndarray, shape (n, n)
        代价矩阵（方阵），cost[i][j] = 工人 i 做任务 j 的代价

    Returns
    -------
    dict:
        - matching: 匹配结果，matching[i] = j 表示工人 i 匹配任务 j
        - total_cost: 总代价
        - row_ind, col_ind: 行列索引（scipy 格式）
    """
    from scipy.optimize import linear_sum_assignment

    cost = np.asarray(cost_matrix, dtype=float)
    row_ind, col_ind = linear_sum_assignment(cost)
    total_cost = cost[row_ind, col_ind].sum()

    matching = np.zeros(len(cost), dtype=int)
    matching[row_ind] = col_ind

    return {
        'matching': matching,
        'total_cost': total_cost,
        'row_ind': row_ind,
        'col_ind': col_ind,
    }


# ============================================================
# 使用示例
# ============================================================
def example():
    """图论示例"""
    # 示例1: Dijkstra
    print("=" * 60)
    print("示例1: Dijkstra 最短路径")
    print("=" * 60)
    INF = np.inf
    adj = np.array([
        [0,   10,  INF, INF, 5],
        [INF, 0,   1,   INF, 2],
        [INF, INF, 0,   4,   INF],
        [7,   INF, INF, 0,   INF],
        [INF, 3,   9,   2,   0],
    ])
    dist, prev = dijkstra(adj, 0)
    for i in range(5):
        path = get_path(prev, i)
        print(f"  0 → {i}: 距离={dist[i]:.0f}, 路径={'→'.join(map(str, path))}")

    # 示例2: 最大流
    print("\n" + "=" * 60)
    print("示例2: 最大流")
    print("=" * 60)
    cap = np.array([
        [0, 16, 13, 0, 0, 0],
        [0, 0, 10, 12, 0, 0],
        [0, 4, 0, 0, 14, 0],
        [0, 0, 9, 0, 0, 20],
        [0, 0, 0, 7, 0, 4],
        [0, 0, 0, 0, 0, 0],
    ])
    mf, flow = max_flow(cap, 0, 5)
    print(f"  最大流量: {mf}")

    # 示例3: 关键路径
    print("\n" + "=" * 60)
    print("示例3: 关键路径 (PERT)")
    print("=" * 60)
    activities = [
        {'name': 'A', 'duration': 4, 'predecessors': []},
        {'name': 'B', 'duration': 3, 'predecessors': []},
        {'name': 'C', 'duration': 2, 'predecessors': ['A']},
        {'name': 'D', 'duration': 5, 'predecessors': ['A']},
        {'name': 'E', 'duration': 3, 'predecessors': ['B', 'C']},
        {'name': 'F', 'duration': 2, 'predecessors': ['D', 'E']},
    ]
    result = critical_path(activities)
    print(f"  总工期: {result['project_duration']}")
    print(f"  关键路径: {' → '.join(result['critical_path'])}")


if __name__ == "__main__":
    example()
