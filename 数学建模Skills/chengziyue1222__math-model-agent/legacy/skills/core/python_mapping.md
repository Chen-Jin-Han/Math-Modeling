# Python Mapping Guide

> Matlab → Python 工程化映射。基于《数学建模算法与应用》中涉及的Matlab方法。

---

## 工程目录结构

```
project/
├── data/              # 原始数据
│   ├── raw/           # 原始数据文件
│   └── cleaned/       # 清洗后数据
├── src/               # 源代码
│   ├── preprocess.py  # 数据预处理
│   ├── model.py       # 模型定义
│   ├── solver.py      # 求解器
│   └── visualize.py   # 可视化
├── model/             # 模型输出
│   ├── results.json   # 求解结果
│   └── params.json    # 模型参数
├── report/            # 报告输出
│   ├── figures/       # 图表
│   └── tables/        # 表格
└── main.py            # 主入口
```

---

## 核心库对照表

| Matlab功能 | Python替代 | 本项目算法库 |
|-----------|-----------|-------------|
| linprog | scipy.optimize.linprog | `linear_programming()` |
| fmincon | scipy.optimize.minimize | `nonlinear_programming()` |
| intlinprog | pulp.LpProblem | `integer_programming()` |
| ode45 | scipy.integrate.solve_ivp | scipy 直接调用 |
| GM(1,1) | — | `gm11_predict()` |
| TOPSIS | — | `topsis()` |
| 遗传算法 | — | `genetic_algorithm()` |
| Dijkstra | — | `dijkstra()` |
| kmeans | sklearn.cluster.KMeans | `fuzzy_cmeans()` |
| pca | sklearn.decomposition.PCA | `pca()` |
| regress | sklearn.linear_model | `linear_regression()` |
| plot/mesh | matplotlib.pyplot | `sci_figures` 模块 |

完整 API 见 `algorithm_api.md`

---

## 常用算法（使用算法库）

> 以下示例均来自 `code/algorithms/`，无需手写实现。

### 1. 线性规划

```python
from algorithms import linear_programming

result = linear_programming(
    c=[-4, -3],
    A_ub=[[2, 1], [1, 1], [0, 1]],
    b_ub=[10, 8, 7],
    bounds=[(0, None), (0, None)]
)
print(f"最优解: x={result['x']}, 最优值: {-result['fun']}")
```

### 2. 非线性规划

```python
from algorithms import nonlinear_programming

result = nonlinear_programming(
    objective=lambda x: -(4*x[0] + 3*x[1]),
    x0=[0, 0],
    bounds=[(0, None), (0, None)],
    constraints=[{'type': 'ineq', 'fun': lambda x: 10 - 2*x[0] - x[1]}]
)
```

### 3. 整数规划

```python
from algorithms import integer_programming

result = integer_programming(
    c=[4, 3], A_ub=[[2, 1], [1, 1]], b_ub=[10, 8],
    bounds=[(0, None), (0, None)], var_types=['Integer', 'Integer']
)
```

### 4. 常微分方程数值解

```python
from scipy.integrate import solve_ivp
import numpy as np

def ode_system(t, y):
    x, v = y
    return [v, -k/m * x - c/m * v + F(t)/m]

sol = solve_ivp(ode_system, (0, 10), [0, 0], t_eval=np.linspace(0, 10, 1000))
```

### 5. 灰色预测 GM(1,1)

```python
from algorithms import gm11_predict
import numpy as np

x0 = np.array([10, 12, 14, 16, 18], dtype=float)
result = gm11_predict(x0, predict_count=3)
print(result['predicted'], result['grade'])
```

### 6. TOPSIS评价法

```python
from algorithms import topsis, entropy_weight
import numpy as np

matrix = np.array([[80, 70], [90, 60], [75, 85]])
weights = entropy_weight(matrix)
result = topsis(matrix, weights, positive_indicators=[True, False])
print(result.scores, result.ranks)
```

### 7. 层次聚类

```python
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
import matplotlib.pyplot as plt

Z = linkage(data, method='ward')
labels = fcluster(Z, 3, criterion='maxclust')
```

### 8. 遗传算法

```python
from algorithms import genetic_algorithm
import numpy as np

def sphere(X):
    return np.sum(X**2, axis=1)

bounds = (np.array([-5, -5]), np.array([5, 5]))
r = genetic_algorithm(sphere, 2, bounds, pop_size=50, max_gen=100, vectorized=True)
print(f"最优解: x={r['x']}, f={r['f']}")
```

---

## 可视化模板

```python
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei']  # 中文显示
matplotlib.rcParams['axes.unicode_minus'] = False

def setup_academic_style():
    """设置学术图表风格"""
    plt.rcParams.update({
        'font.size': 10.5,
        'axes.labelsize': 10.5,
        'axes.titlesize': 12,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 9,
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'figure.figsize': (8, 6),
        'axes.grid': True,
        'grid.alpha': 0.3,
    })
```
