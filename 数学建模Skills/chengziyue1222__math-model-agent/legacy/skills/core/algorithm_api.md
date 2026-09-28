# Algorithm API Reference

> 算法库统一 API 速查。代码位于 `code/algorithms/`，导入方式：

```python
import sys
sys.path.insert(0, 'code')
from algorithms import gm11_predict, topsis, genetic_algorithm
```

---

## 快速选型表

| 问题类型 | 首选函数 | 模块 |
|---------|---------|------|
| 小样本预测 | `gm11_predict` | grey_system |
| 多准则权重 | `ahp_weight` | ahp |
| 方案排序 | `topsis` | evaluation |
| 线性规划 | `linear_programming` | math_programming |
| 非线性优化 | `genetic_algorithm`, `particle_swarm` | metaheuristic |
| 最短路径 | `dijkstra`, `floyd` | graph_theory |
| 数值积分 | `monte_carlo_integration` | monte_carlo |
| 数据拟合 | `linear_regression`, `polynomial_regression` | regression |
| 插值补全 | `cubic_spline_interp` | interpolation |
| 图像边缘 | `edge_detection` | image_processing |

---

## 1. 决策与评价

### AHP 层次分析法
```python
from algorithms import ahp_weight, consistency_check

A = np.array([[1, 3, 5], [1/3, 1, 3], [1/5, 1/3, 1]])
w, lambda_max, CR, passed = ahp_weight(A)
report = consistency_check(A, verbose=False)
```

### TOPSIS 综合评价
```python
from algorithms import topsis, entropy_weight

data = np.array([[80, 70], [90, 60], [75, 85]])  # (方案数, 指标数)
weights = entropy_weight(data)
result = topsis(data, weights, positive_indicators=[True, False])
# result.scores, result.ranks
```

### 模糊综合评价
```python
from algorithms.fuzzy_math import fuzzy_comprehensive_evaluation

R = np.array([[0.7, 0.3], [0.6, 0.4]])  # 评价矩阵
weights = np.array([0.6, 0.4])
grades = fuzzy_comprehensive_evaluation(R, weights)  # 返回归一化等级向量
```

---

## 2. 预测与回归

### GM(1,1) 灰色预测
```python
from algorithms import gm11_predict

data = np.array([10, 12, 14, 16, 18], dtype=float)
result = gm11_predict(data, predict_count=3)
# result['predicted'], result['fitted'], result['a'], result['b'], result['grade']
```

### 线性回归
```python
from algorithms import linear_regression

x = np.array([1, 2, 3, 4, 5], dtype=float)
y = 2 * x + 1
result = linear_regression(x, y)
# result['slope'], result['intercept'], result['r2']
```

---

## 3. 优化与规划

### 遗传算法 / 粒子群
```python
from algorithms import genetic_algorithm, particle_swarm

def sphere(X):  # X: (pop, n_vars)
    return np.sum(X**2, axis=1)

bounds = (np.array([-5, -5]), np.array([5, 5]))
r = genetic_algorithm(sphere, 2, bounds, pop_size=50, max_gen=100, vectorized=True)
# r['x'], r['f']
```

### 线性规划
```python
from algorithms import linear_programming

result = linear_programming(
    c=[-4, -3], A_ub=[[2, 1], [1, 1]], b_ub=[10, 8],
    bounds=[(0, None), (0, None)]
)
```

---

## 4. 图论

```python
from algorithms import dijkstra, floyd, prim_mst, max_flow, get_path

# 邻接表或邻接矩阵均可
G = [[(1, 1), (2, 4)], [(0, 1), (2, 2)], [(0, 4), (1, 2)]]
dist, prev = dijkstra(G, source=0)
path = get_path(prev, target=2)

dist_matrix = floyd(G)  # 全源最短路径
mst_edges, total = prim_mst(G)
flow = max_flow(capacity_matrix, source=0, sink=3)
```

---

## 5. 蒙特卡罗

```python
from algorithms import monte_carlo_integration, queuing_simulation

result = monte_carlo_integration(lambda x: np.sin(x), 0, np.pi, n_samples=10000)
# result.estimate, result.std_error

q = queuing_simulation(arrival_rate=4, service_rate=5, n_servers=1, n_customers=1000)
```

---

## 6. 元胞自动机

```python
from algorithms import GameOfLife, ElementaryCA

gol = GameOfLife(rows=20, cols=20)
gol.grid[5, 4:7] = 1
gol.evolve(steps=10)

ca = ElementaryCA(rule=30, size=101)
ca.initialize(center=True)
ca.evolve(steps=50)
history = ca.history  # (steps+1, size)
```

---

## 7. 图像处理

```python
from algorithms import edge_detection, image_segmentation, noise_filter

edges = edge_detection(image, method='canny', threshold=0.3)
mask = image_segmentation(image, method='otsu')
clean = noise_filter(image, method='gaussian', kernel_size=3)
```

---

## 8. 科研图表与论文检查

```python
from algorithms import TaylorDiagram, TaylorPoint, check_paper

td = TaylorDiagram()
td.add_point(TaylorPoint('Model A', std_ratio=1.1, corr=0.95, rmse=0.3))
report = check_paper('paper.tex')
```

---

## 输入格式约定

| 函数 | 输入格式 | 返回值 |
|------|---------|--------|
| `dijkstra` | 邻接矩阵或邻接表 | `(dist, prev)` |
| `floyd` | 邻接矩阵或邻接表 | `dist` 矩阵 |
| `gm11_predict` | 1D 非负序列 | dict，含 `predicted`/`fitted` |
| `topsis` | `(n, m)` 决策矩阵 | `TOPSISResult` dataclass |
| `linear_regression` | 1D/2D X + 1D y | dict，一元时含 `slope`/`r2` |
| `fuzzy_comprehensive_evaluation` | `(R, weights)` 或 `(weights, R)` | 默认返回等级向量 |

---

## 相关 Skill

- 模型选择 → `model_selector.md`
- 建模流程 → `modeling_pipeline.md`
- MATLAB 对照 → `python_mapping.md`
- 扩展模型 → `model_library_extended.md`
