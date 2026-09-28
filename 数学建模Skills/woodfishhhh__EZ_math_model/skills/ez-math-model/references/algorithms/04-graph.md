# 04 图论与网络分析

> 最短路径 / 最小生成树 / 网络流 / 关键路径 / 匹配 / 中心性的"教材级"参考。

## 概述

图论问题的核心是用 **顶点 + 边 + 权重** 抽象现实关系，再用算法求解最短路径、
最小生成树、最大流、最优匹配等问题。流程：

```
现实问题
   ↓ 1. 抽象建模（顶点 = 节点；边 = 关系；权重 = 距离 / 容量 / 成本）
   ↓ 2. 选数据结构（邻接表 / 邻接矩阵 / 边列表）
   ↓ 3. 选算法（按问题类型）
   ↓ 4. 求解 + 验证
   ↓ 5. 可视化（节点 + 边 + 颜色编码）
```

## 数据结构选型

| 数据结构 | 空间 | 邻居查询 | 适用 |
|---|---|---|---|
| 邻接矩阵 | $O(V^2)$ | $O(1)$ | 稠密图、V < 1000 |
| 邻接表 | $O(V+E)$ | $O(\deg)$ | 稀疏图、大规模 |
| 边列表 | $O(E)$ | $O(E)$ | Kruskal、Bellman-Ford |
| CSR（Compressed Sparse Row） | $O(V+E)$ | $O(\deg)$ | 大稀疏图，scipy.sparse 支持 |

Python 实战：网络小用 `networkx`（邻接表自动），大稀疏图用 `scipy.sparse.csgraph`。

---

## 1. Dijkstra（单源最短路径）

### 何时选

- 边权**非负**
- 单一起点，到全图（或到指定终点）

### 核心公式

设 $d(v)$ 是起点到 $v$ 的最短距离：

$$
d(v) = \min_{(u,v) \in E} (d(u) + w(u,v))
$$

迭代时维护"未确定集 $Q$"：每次取 $Q$ 中 $d$ 最小的顶点 $u$，将其确定，
然后**松弛**所有出边 $(u, v)$。

### 复杂度

| 实现 | 时间 |
|---|---|
| 朴素（数组找最小） | $O(V^2)$ |
| 二叉堆 | $O((V+E) \log V)$ |
| Fibonacci 堆 | $O(E + V \log V)$ |

### 关键参数

无超参，仅选数据结构（堆 vs 数组）。

### 常见坑

- 边权有负值 → Dijkstra 不适用，必须 Bellman-Ford / SPFA。
- 稀疏图用邻接矩阵 → 退化成 $O(V^2)$。
- 起点未初始化 $d(\text{start}) = 0$ → 错。
- 多源最短路径直接跑 V 次 Dijkstra：稠密图改 Floyd 更省事。

### 验证

- 与 Bellman-Ford 在小图上比对
- 验证三角不等式：$d(v) \le d(u) + w(u,v)$ 对所有边成立

### Python 入口

```python
import heapq
from collections import defaultdict
from typing import Hashable

def dijkstra(graph: dict[Hashable, list[tuple[Hashable, float]]], src) -> dict:
    """graph[u] = [(v, w), ...]"""
    dist = defaultdict(lambda: float('inf'))
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, w in graph[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dict(dist)
```

`networkx` 接口：

```python
import networkx as nx
G = nx.DiGraph()
G.add_weighted_edges_from([(1, 2, 5), (2, 3, 2), (1, 3, 9)])
dist = nx.single_source_dijkstra_path_length(G, source=1)
path = nx.shortest_path(G, 1, 3, weight='weight', method='dijkstra')
```

`scipy.sparse.csgraph`（大图首选）：

```python
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
csr = csr_matrix(adj_matrix)
dist, predecessors = dijkstra(csr, indices=src, return_predecessors=True)
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Dijkstra, E.W. | A note on two problems in connexion with graphs | Numerische Mathematik | 1959 |

---

## 2. Bellman-Ford（含负权）

### 何时选

- 边权可负，但**无负权环**
- 需要检测负权环

### 核心思路

```
初始化 dist[src] = 0，其他 = ∞
重复 V-1 次：
    对每条边 (u, v, w)：
        if dist[u] + w < dist[v]:
            dist[v] = dist[u] + w
再循环一次：若仍能松弛 → 存在负权环
```

### 复杂度

$O(VE)$。

### 关键参数

无。可加 SPFA 优化（队列实现）：平均 $O(E)$，最坏 $O(VE)$。

### 常见坑

- 检测到负权环不报警 → 必须显式检查第 V 次迭代是否还能松弛。
- 负权图错用 Dijkstra → 结果错误（Dijkstra 不能处理负权）。

### Python 入口

```python
def bellman_ford(edges, V, src):
    """edges = [(u, v, w), ...]"""
    dist = [float('inf')] * V
    dist[src] = 0
    for _ in range(V - 1):
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    # 检测负权环
    for u, v, w in edges:
        if dist[u] + w < dist[v]:
            raise ValueError("negative cycle detected")
    return dist
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Bellman, R. | On a routing problem | Quarterly of Applied Mathematics | 1958 |
| Ford, L.R. | Network Flow Theory | RAND Corp Paper | 1956 |

---

## 3. Floyd-Warshall（全源最短路）

### 何时选

- 节点 < 500，需要任意两点距离
- 边权可负（但无负权环）

### 核心三重循环

```
for k in V:
    for i in V:
        for j in V:
            d[i][j] = min(d[i][j], d[i][k] + d[k][j])
```

### 复杂度

$O(V^3)$，空间 $O(V^2)$。V > 500 应转分块 / Johnson 算法。

### 常见坑

- 三重循环 k 必须是**最外层**（否则错）。
- 大图导致 $V^3$ 爆炸 → 改稀疏 + 多次 Dijkstra（Johnson）。

### Python 入口

```python
def floyd_warshall(W):
    """W: V×V 邻接矩阵；不存在边用 inf"""
    V = len(W)
    d = [row[:] for row in W]
    for k in range(V):
        for i in range(V):
            for j in range(V):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return d
```

`scipy.sparse.csgraph.floyd_warshall` 是 C 实现，推荐用。

---

## 4. A*（启发式最短路）

### 何时选

- 起点终点固定
- 有合理启发函数 $h(n)$（地理距离 / 曼哈顿 / 欧氏）

### 核心思路

维护开放表 OPEN，按 $f(n) = g(n) + h(n)$ 排序：
- $g(n)$：起点到 $n$ 的实际代价
- $h(n)$：$n$ 到终点的启发估计

### 启发函数约束

- **可采纳性（Admissibility）**：$h(n) \le h^*(n)$（永不高估真实剩余距离）
- **一致性（Consistency）**：$h(u) \le w(u,v) + h(v)$

满足可采纳性 → A* 找到最优解；一致性 → 不需要重开已闭合节点。

### 常见坑

- 启发函数过乐观 → 失最优。
- 启发函数过保守（h ≡ 0） → 退化为 Dijkstra。
- 网格地图用欧氏距离 + 8 方向 → 可采纳但不一致；改用曼哈顿。

### Python 入口

```python
import heapq
from typing import Callable

def astar(start, goal, neighbors: Callable, h: Callable, w: Callable):
    open_set = [(h(start), start)]
    g = {start: 0}
    came_from = {}
    while open_set:
        _, u = heapq.heappop(open_set)
        if u == goal:
            path = [goal]
            while path[-1] in came_from:
                path.append(came_from[path[-1]])
            return path[::-1], g[goal]
        for v in neighbors(u):
            tentative_g = g[u] + w(u, v)
            if tentative_g < g.get(v, float('inf')):
                came_from[v] = u
                g[v] = tentative_g
                heapq.heappush(open_set, (tentative_g + h(v), v))
    return None, float('inf')
```

`networkx.astar_path`、`pyastar2d`（网格专用）。

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Hart, P.E.; Nilsson, N.J.; Raphael, B. | A Formal Basis for the Heuristic Determination of Minimum Cost Paths | IEEE Trans. SSC | 1968 |

---

## 5. 最小生成树（MST）

### 何时选

连通无向图，求权重最小的覆盖所有顶点的树。

**典型场景**：管线铺设、电网设计、网络拓扑。

### Kruskal 算法

```
排序所有边按权重升序
初始化并查集
for (u, v, w) in 排序后的边:
    if find(u) != find(v):
        union(u, v)
        加入 MST
```

复杂度：$O(E \log E)$，主要在排序。

### Prim 算法

```
任选起点
维护"已加入 MST 的顶点集合 S"
重复 V-1 次：
    取 S 边界上的最小权边 (u, v)，将 v 加入 S
```

复杂度：堆实现 $O(E \log V)$。

### 选择

- 边稀疏 → Kruskal
- 边稠密 → Prim
- 在线流式 → Prim

### 常见坑

- 图不连通 → 只能得到生成森林。
- 用 BFS / DFS 当 MST → 错；那是任意生成树，不是最小。

### Python 入口

```python
import networkx as nx
G = nx.Graph()
G.add_weighted_edges_from(edges)
T = nx.minimum_spanning_tree(G, algorithm='kruskal')
print(T.edges(data=True))
```

或 `scipy.sparse.csgraph.minimum_spanning_tree`。

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Kruskal, J.B. | On the shortest spanning subtree of a graph | Proc. AMS | 1956 |
| Prim, R.C. | Shortest connection networks | Bell System Tech. J. | 1957 |

---

## 6. 网络最大流 / 最小费用最大流

### 何时选

源汇网络中传输最大量；或最小成本。

**典型场景**：物流分配、二分图匹配、项目调度、电力网络。

### 算法

| 算法 | 复杂度 | 备注 |
|---|---|---|
| Ford-Fulkerson | $O(E \cdot \text{maxflow})$ | 用 DFS 找增广路；理论非多项式 |
| Edmonds-Karp | $O(VE^2)$ | FF 的 BFS 版本，多项式 |
| Dinic | $O(V^2E)$ | 分层图 + 阻塞流 |
| Push-Relabel | $O(V^2\sqrt{E})$ | 实战常用 |

### 关键约束

- 容量必须**非负**。
- 多源多汇要加超级源 / 超级汇。
- 浮点容量易累积误差，关键场景用整数。

### Python 入口

```python
import networkx as nx
G = nx.DiGraph()
G.add_edge('s', 'a', capacity=10)
G.add_edge('s', 'b', capacity=5)
G.add_edge('a', 'b', capacity=15)
G.add_edge('a', 't', capacity=10)
G.add_edge('b', 't', capacity=10)
flow_value, flow_dict = nx.maximum_flow(G, 's', 't')

# 最小费用最大流
G2 = nx.DiGraph()
G2.add_edge('s', 'a', capacity=10, weight=2)
mincostFlow = nx.max_flow_min_cost(G2, 's', 't')
mincost = nx.cost_of_flow(G2, mincostFlow)
```

### 二分图匹配（最大流的特例）

```python
G = nx.Graph()
G.add_nodes_from(left, bipartite=0)
G.add_nodes_from(right, bipartite=1)
G.add_edges_from(edges)
matching = nx.bipartite.maximum_matching(G)
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Ford, L.R. & Fulkerson, D.R. | Maximal flow through a network | Canadian J. Math. | 1956 |
| Edmonds, J. & Karp, R.M. | Theoretical improvements in algorithmic efficiency for network flow problems | J. ACM | 1972 |
| Dinic, E.A. | Algorithm for solution of a problem of maximum flow in a network with power estimation | Soviet Math. Dokl. | 1970 |

---

## 7. 关键路径 / PERT-CPM

### 何时选

项目调度，求**最长完成时间路径**与关键活动。

### 核心思路

```
1. 拓扑排序所有活动（必须 DAG）
2. 正向：算每个活动的最早开始 ES 与最早完成 EF
3. 反向：算最晚开始 LS 与最晚完成 LF
4. 浮动时间 = LS - ES = LF - EF
5. 浮动时间 = 0 的活动 → 关键活动
```

### 关键参数

无超参。

### 常见坑

- 图必须是 DAG，存在环就报错。
- 活动时间为负或 0 要单独处理。
- 不写"关键路径不止一条"的可能性 → 论文不严谨。

### Python 入口

```python
import networkx as nx
G = nx.DiGraph()
G.add_weighted_edges_from([
    ('start', 'A', 3), ('start', 'B', 2),
    ('A', 'C', 5), ('B', 'C', 4),
    ('C', 'end', 1),
])
critical_path = nx.dag_longest_path(G, weight='weight')
critical_length = nx.dag_longest_path_length(G, weight='weight')
```

---

## 8. 二分图匹配

### 何时选

两类节点配对、寻找最大匹配 / 最优分配。

**典型场景**：任务分配、资源调度、稳定婚姻。

### 算法

| 算法 | 用途 | 复杂度 |
|---|---|---|
| 匈牙利算法（增广路） | 最大匹配 | $O(VE)$ |
| KM 算法 | 加权完美匹配（最小化总成本） | $O(V^3)$ |
| Gale-Shapley | 稳定婚姻 | $O(V^2)$ |

### Python 入口（KM）

```python
import numpy as np
from scipy.optimize import linear_sum_assignment

# cost_matrix[i][j] = 把 worker i 分配给 task j 的成本
cost = np.array([[4, 1, 3], [2, 0, 5], [3, 2, 2]])
row_ind, col_ind = linear_sum_assignment(cost)
print(f"分配: {list(zip(row_ind, col_ind))}, 总成本: {cost[row_ind, col_ind].sum()}")
```

`networkx.bipartite.matching` 提供匈牙利算法。

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Kuhn, H.W. | The Hungarian method for the assignment problem | Naval Research Logistics Quarterly | 1955 |
| Gale, D. & Shapley, L.S. | College Admissions and the Stability of Marriage | American Math. Monthly | 1962 |

---

## 9. 中心性指标

衡量节点在网络中的"重要性"，给排名 / 影响力分析用。

| 指标 | 含义 | 公式 / 算法 | 用途 |
|---|---|---|---|
| 度中心性 | 邻居数 | $C_D(v) = \deg(v) / (V-1)$ | 局部影响 |
| 介数中心性 | 经过该点的最短路占比 | $C_B(v) = \sum_{s \ne v \ne t} \sigma_{st}(v) / \sigma_{st}$ | 桥梁性 |
| 接近中心性 | 到所有点的平均距离倒数 | $C_C(v) = (V-1) / \sum_u d(v, u)$ | 接近度 |
| 特征向量中心性 | 邻居重要性的加权 | $\mathbf{x} = \lambda^{-1} A \mathbf{x}$ | 全局影响 |
| PageRank | 概率游走稳态 | $\mathbf{r} = (1-\alpha)/V \cdot \mathbf{1} + \alpha M^\top \mathbf{r}$ | 重要性排名 |

### Python 入口

```python
import networkx as nx

centrality_measures = {
    'degree': nx.degree_centrality(G),
    'betweenness': nx.betweenness_centrality(G),
    'closeness': nx.closeness_centrality(G),
    'eigenvector': nx.eigenvector_centrality_numpy(G),
    'pagerank': nx.pagerank(G, alpha=0.85),
}
```

### 选择建议

| 场景 | 推荐指标 |
|---|---|
| 找网络枢纽 | 介数 / 度 |
| 找最具影响力者 | 特征向量 / PageRank |
| 找信息传播最快的节点 | 接近 |
| 大网络 | PageRank（数值稳定）|

---

## 10. 社区发现

### 算法

| 算法 | 思路 | 复杂度 |
|---|---|---|
| Louvain | 模块度 Q 最大化（贪心） | $O(N \log N)$ |
| Leiden | Louvain 改进，保证连通性 | $O(N \log N)$ |
| Girvan-Newman | 反复移除高介数边 | $O(VE^2)$ |
| 谱聚类 | 拉普拉斯矩阵特征向量 + K-Means | $O(V^3)$ |
| Label Propagation | 标签消息传递 | $O(E \cdot \text{iter})$ |

### Python 入口

```python
import networkx as nx
import community as community_louvain  # python-louvain
partition = community_louvain.best_partition(G)
modularity = community_louvain.modularity(partition, G)

# Leiden（更稳）
import igraph as ig
import leidenalg
g = ig.Graph.from_networkx(G)
partition = leidenalg.find_partition(g, leidenalg.ModularityVertexPartition)
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Blondel, V.D.; Guillaume, J.L.; Lambiotte, R.; Lefebvre, E. | Fast unfolding of communities in large networks (Louvain) | J. Stat. Mech. | 2008 |
| Traag, V.A.; Waltman, L.; van Eck, N.J. | From Louvain to Leiden | Scientific Reports | 2019 |

---

## 11. 欧拉 / 哈密顿路径

### 欧拉回路

每条边走且只走一次。**存在条件**：
- 无向图：所有顶点度数为偶（欧拉回路）/ 恰 2 个奇度顶点（欧拉路径）
- 有向图：所有顶点入度 = 出度（回路）/ 1 个起点入-出= -1 与 1 个终点入-出= 1（路径）

复杂度：$O(V+E)$（Hierholzer 算法）。

### 哈密顿路径

每个顶点走且只走一次。**NP-hard**，规模大需启发式（GA / SA）。

特例 TSP（旅行商问题）：动态规划 $O(2^V V^2)$ 适合 V ≤ 20；近似算法（Christofides 1.5-近似）适合大规模。

### Python 入口

```python
import networkx as nx
# 欧拉回路
if nx.is_eulerian(G):
    circuit = list(nx.eulerian_circuit(G))

# TSP（精确，小规模）
from networkx.algorithms.approximation import traveling_salesman_problem
tour = traveling_salesman_problem(G, cycle=True)  # 近似，启发式
```

`python-tsp` 提供精确 + 启发式 TSP 求解器。

---

## 选型对照表

| 需求 | 算法 |
|---|---|
| 单源非负最短路 | Dijkstra |
| 单源含负权 | Bellman-Ford / SPFA |
| 全源（小图） | Floyd-Warshall |
| 全源（大稀疏） | Johnson |
| 启发式 | A* |
| 最小生成树 | Kruskal（稀疏） / Prim（稠密） |
| 最大流 | Dinic / Edmonds-Karp |
| 最小费用流 | SSP / Min-Cost-Flow |
| 项目调度 | CPM |
| 任务分配 | KM 算法 / 匈牙利 |
| 节点重要性 | PageRank / Betweenness |
| 社区发现 | Louvain / Leiden |
| TSP / 哈密顿 | DP（小） / GA / SA / Christofides（大） |

## 可视化建议

| 内容 | 推荐 |
|---|---|
| 网络结构 | spring layout（力导向） + 节点大小 = 度 |
| 最短路径 | 高亮路径上的边 |
| 社区分组 | 节点颜色 = 社区 ID |
| 流量大小 | 边粗细 = 流量 |
| 中心性 | 节点大小 = 中心性 |
| 关键路径 | 红色高亮关键活动 |

```python
import matplotlib.pyplot as plt
import networkx as nx
pos = nx.spring_layout(G, seed=42)
nx.draw_networkx(G, pos, node_color=[partition[n] for n in G.nodes()],
                 node_size=[300 * pagerank[n] for n in G.nodes()],
                 width=[d['weight'] for _, _, d in G.edges(data=True)],
                 cmap=plt.cm.tab20, with_labels=True)
plt.axis('off')
plt.savefig('figures/fig_network.png', dpi=300, bbox_inches='tight')
```

## 常见全栈错误

| ❌ 错误 | ✅ 正确 |
|---|---|
| 负权图用 Dijkstra | 改 Bellman-Ford |
| 大稀疏图用邻接矩阵 | 用邻接表 / CSR |
| Floyd k 循环不在最外 | 必须最外 |
| TSP 用回溯（V > 20） | 用启发式（GA / SA / Christofides） |
| 不连通图找 MST | 报错或返回生成森林 |
| 启发函数高估剩余距离 | A* 失最优 |
| 模块度 = 0 当作"无社区" | Q < 0.3 才算无明显社区 |
