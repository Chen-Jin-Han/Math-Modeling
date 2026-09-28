# 01 优化算法

> 线性 / 整数 / 非线性 / 多目标 / 序贯决策的"教材级"参考。

## 概述

优化问题的标准形：

$$
\min_{x \in \mathcal{X}} \; f(x) \quad \text{s.t.} \; g_i(x) \le 0,\, h_j(x) = 0
$$

按变量类型与约束形式分为：LP / IP / QP / NLP / MIP / DP / 启发式（GA/SA/PSO）/
多目标（NSGA-II）。

**工程优化铁律**（极易扣分）：
- 每个变量必须有物理上下界。
- 论文中必须包含"无约束最优 vs 物理约束最优"对比段。
- 缩尺模型不能给出超出模型尺寸的解。

---

## 1. 线性规划（LP）

### 何时选

目标与约束都是线性、变量连续。

### 标准形

$$
\min \; c^\top x \quad \text{s.t.} \; A x \le b, \; A_{eq} x = b_{eq}, \; x \ge 0
$$

### 核心算法

- **单纯形法（Simplex）**：在顶点间移动找最优。
- **内点法（Interior Point）**：在可行域内部沿中心路径走。
- 大规模稀疏问题用内点法；中小规模单纯形够。

### 关键参数

无超参，只有求解器选项：`time_limit`、`mip_gap`（IP 专用）。

### 常见坑

- 变量本应整数却设为连续 → 改 IP / MIP。
- 约束方向写反（≤ vs ≥） → 影响可行域。
- 单位不一致导致系数尺度悬殊 → 数值不稳，先归一化。

### 验证

- 对偶价格的实际意义（影子价格）
- 灵敏度区间（系数 / 右端项变化范围内最优解结构不变）

### Python 入口

```python
import scipy.optimize as opt

# min c^T x  s.t. A_ub x <= b_ub, A_eq x = b_eq, bounds
res = opt.linprog(
    c=[1, 2],
    A_ub=[[1, 1]], b_ub=[10],
    A_eq=[[2, 1]], b_eq=[7],
    bounds=[(0, None), (0, None)],
    method='highs',
)
print(res.x, res.fun)
```

复杂建模用 PuLP 或 cvxpy：

```python
import pulp
prob = pulp.LpProblem("ex", pulp.LpMinimize)
x1 = pulp.LpVariable("x1", lowBound=0)
x2 = pulp.LpVariable("x2", lowBound=0)
prob += x1 + 2 * x2
prob += x1 + x2 <= 10
prob.solve()
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Dantzig, G.B. | Linear Programming and Extensions | Princeton University Press | 1963 |
| Bertsimas, D. & Tsitsiklis, J.N. | Introduction to Linear Optimization | Athena Scientific | 1997 |

---

## 2. 整数 / 0-1 规划（IP / BIP / MIP）

### 何时选

决策变量必须取整或 0/1（选 / 不选、装 / 不装、分配次数）。

### 核心算法

- **分支定界**（Branch and Bound）：松弛为 LP，遇分数变量分支为两个子问题。
- **割平面法**（Cutting Plane）：给松弛 LP 添加割平面收紧。
- 现代求解器（Gurobi / CPLEX / CBC）混合上述方法。

### 关键参数

- `mip_gap`：可接受的最优性差距（默认 1%）。
- `time_limit`：求解时间上限。
- Big-M 取值：尽量小（过大导致松弛差、求解慢）。

### 常见坑

- 变量数 × 状态数爆炸 → 加对称破除约束、Big-M 收紧。
- 用 Big-M 线性化非线性 → Big-M 太宽时松弛差。
- 不设 time_limit 导致永不退出。

### Python 入口

```python
import pulp

prob = pulp.LpProblem("knapsack", pulp.LpMaximize)
x = [pulp.LpVariable(f"x_{i}", cat='Binary') for i in range(n)]
prob += pulp.lpSum(values[i] * x[i] for i in range(n))
prob += pulp.lpSum(weights[i] * x[i] for i in range(n)) <= capacity
prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=60))
```

scipy ≥ 1.9 内置 `scipy.optimize.milp`：

```python
from scipy.optimize import milp, Bounds, LinearConstraint
res = milp(c=-np.array(values),
           constraints=LinearConstraint(np.array([weights]), -np.inf, capacity),
           integrality=np.ones(n),
           bounds=Bounds(0, 1))
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Land, A.H. & Doig, A.G. | An automatic method of solving discrete programming problems | Econometrica | 1960 |
| Wolsey, L.A. | Integer Programming | Wiley | 1998 |

---

## 3. 动态规划（DP）

### 何时选

序贯决策、阶段独立、有最优子结构 + 无后效性。

### 核心三要素

- **状态**：描述当前阶段的最少信息（如剩余资源、当前位置）。
- **转移**：从 $f(s)$ 到 $f(s')$ 的递推方程。
- **边界**：起始状态的初值、终止条件。

### 经典问题

| 问题 | 状态 | 转移 |
|---|---|---|
| 背包 | $f(i, w)$：前 i 物品、容量 w 下最大价值 | $f(i,w) = \max(f(i-1,w), f(i-1,w-w_i)+v_i)$ |
| 最长公共子序列 | $f(i, j)$：A[1..i] 与 B[1..j] 的 LCS 长度 | 见教材 |
| 最短路 | $f(v)$：到 v 的最短距离 | $f(v) = \min_u (f(u) + w_{uv})$ |
| 最优二叉搜索树 | $f(i, j)$ | 区间 DP |

### 关键参数

- 状态空间大小：$|S|$ 决定时间空间复杂度。
- 转移次数：每个状态尝试多少种动作。

### 常见坑

- 状态空间爆炸（>10⁸） → 考虑近似 DP / RL / 贪心。
- 未论证"无后效性" → 论文易被挑战。
- 边界条件初始化错误。

### 验证

- 用小规模穷举核对最优值。
- 检查边界条件是否覆盖所有"特殊起点"。

### Python 入口

```python
# 0-1 背包
def knapsack(weights, values, W):
    n = len(weights)
    dp = [[0] * (W + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(W + 1):
            dp[i][w] = dp[i-1][w]
            if weights[i-1] <= w:
                dp[i][w] = max(dp[i][w], dp[i-1][w-weights[i-1]] + values[i-1])
    return dp[n][W]
```

记忆化搜索（递归 + cache）也是常见实现：

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def f(i, w):
    if i == 0 or w == 0: return 0
    if weights[i-1] > w: return f(i-1, w)
    return max(f(i-1, w), f(i-1, w-weights[i-1]) + values[i-1])
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Bellman, R. | Dynamic Programming | Princeton | 1957 |
| Bertsekas, D.P. | Dynamic Programming and Optimal Control | Athena Scientific | 2017 |

---

## 4. 遗传算法（GA）

### 何时选

解空间复杂、目标不可导、约束难表达，规模又不至于太大。

### 核心流程

```
初始化种群（随机或启发式）
while not 终止:
    评估适应度
    选择（轮盘赌 / 锦标赛）
    交叉（单点 / 多点 / 算术）
    变异（高斯 / 翻转）
    精英保留
返回最优个体
```

### 关键参数

| 参数 | 范围 | 备注 |
|---|---|---|
| 种群规模 N | 50-200 | 大问题用 200+ |
| 交叉率 pc | 0.7-0.9 | |
| 变异率 pm | 0.01-0.1 | 实数编码常用 1/n |
| 代数 G | 100-500 | 设早停 |
| 精英比例 | 0.05-0.10 | |

### 常见坑

- 早熟收敛 → 精英保留 + 多样性维护（拥挤距离 / 共享适应度）。
- 编码不当 → 连续问题用实数编码，组合问题用排列编码。
- 把 GA 当万金油 → 先试 LP / 梯度法。
- 没多次重复种子 → 随机性导致结果不稳定。

### 验证

- 多种子 ≥ 5 次取均值与方差
- 与简单基线（贪心 / 随机搜索）对比
- 收敛曲线（best fitness vs generation）

### Python 入口

```python
import numpy as np
from mealpy.swarm_based import HHO  # 哈里斯鹰
from mealpy.evolutionary_based import GA

problem = {
    "obj_func": lambda x: (x[0]-1)**2 + (x[1]-2)**2,
    "bounds": [[(-10, 10)], [(-10, 10)]],
    "minmax": "min",
}
model = GA.BaseGA(epoch=100, pop_size=50, pc=0.85, pm=0.05)
best = model.solve(problem)
print(best.solution, best.target.fitness)
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Holland, J.H. | Adaptation in Natural and Artificial Systems | MIT Press | 1975 |
| Goldberg, D.E. | Genetic Algorithms in Search, Optimization, and Machine Learning | Addison-Wesley | 1989 |

---

## 5. 模拟退火（SA, Kirkpatrick 1983）

### 何时选

单目标连续 / 离散，能接受随机性，调参经验少。

### 核心思路

```
T = T0
当前解 s0
while T > T_min:
    内循环 K 次:
        s' = 邻域(s0)
        ΔE = f(s') - f(s0)
        if ΔE < 0:
            s0 = s'
        else:
            以概率 exp(-ΔE / T) 接受 s'
    T = α × T  (α ≈ 0.95-0.99)
```

### 关键参数

| 参数 | 推荐 |
|---|---|
| 初始温度 T0 | 由"接受率"反推（初始接受率 ≈ 0.8） |
| 终止温度 T_min | T0 × 1e-3 |
| 冷却系数 α | 0.95-0.99 |
| 内循环步数 K | 30-100 |

### 常见坑

- 冷却太快变贪心；太慢算力浪费。
- ΔE 没有归一化导致温度系数失效。
- 邻域定义不合理（步长过大 / 过小）。

### Python 入口

```python
from scipy.optimize import dual_annealing

result = dual_annealing(
    func=lambda x: (x[0]-1)**2 + (x[1]-2)**2,
    bounds=[(-10, 10), (-10, 10)],
    seed=42,
)
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Kirkpatrick, S., Gelatt, C.D. & Vecchi, M.P. | Optimization by Simulated Annealing | Science | 1983 |

---

## 6. 粒子群（PSO, Kennedy & Eberhart 1995）

### 何时选

连续优化、目标平滑、维度中等。

### 速度更新公式

$$
v_{t+1} = w v_t + c_1 r_1 (p_{best} - x_t) + c_2 r_2 (g_{best} - x_t), \quad
x_{t+1} = x_t + v_{t+1}
$$

### 关键参数

| 参数 | 推荐 |
|---|---|
| 粒子数 | 30-100 |
| 惯性 w | 0.4-0.9（线性递减） |
| c1, c2 | ≈ 2 |

### 常见坑

- 高维易陷局部最优 → 用变体（CLPSO / SPSO）。
- 离散问题需特殊编码。

### Python 入口

```python
import pyswarms as ps
options = {'c1': 2.0, 'c2': 2.0, 'w': 0.7}
optimizer = ps.single.GlobalBestPSO(
    n_particles=50, dimensions=2, options=options,
    bounds=([-10, -10], [10, 10])
)
cost, pos = optimizer.optimize(lambda X: ((X-np.array([1,2]))**2).sum(axis=1), iters=200)
```

---

## 7. NSGA-II（多目标，Deb 2002）

### 何时选

多个目标存在冲突，需要 Pareto 前沿。

### 核心思路

```
1. 非支配排序：按支配关系把种群分层 F1, F2, ...
2. 拥挤距离：同层内按邻居距离排序，距离大者优先（保多样性）
3. 选择：先按 rank 升序，rank 同看 crowding 降序
4. 交叉 + 变异
```

### 关键参数

| 参数 | 推荐 |
|---|---|
| 种群规模 | 100-200 |
| 代数 | 200-500 |

### 常见坑

- 目标量纲不同 → 先归一化。
- Pareto 前沿稀疏 → 增大种群、用 NSGA-III / MOEA/D。

### 验证指标

- HV（Hypervolume）：Pareto 前沿覆盖空间体积
- IGD（Inverted Generational Distance）：与真前沿距离
- 与加权和法对比

### Python 入口

```python
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.problems import get_problem

problem = get_problem("zdt1")
algo = NSGA2(pop_size=100)
res = minimize(problem, algo, ('n_gen', 200), seed=42, verbose=False)
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Deb, K. et al. | A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II | IEEE Trans. Evol. Comput. | 2002 |

---

## 8. 工程优化铁律（极易扣分）

### 设计变量必须有上下界

每个优化变量必须写：
- 来源（几何 / 物理 / 题目要求三选一）
- 数值（min, max）
- 单位

### 缩尺模型陷阱

- 桌面模型高度仅几百毫米 → 给绳长 / 杆长加几何上界。
- 转速优化到 0 → 加下界（设备需要正常运行）。
- 选材优化把质量做成连续变量 → 离散化为标准件型号。

### 论文必写段

```
求解步骤先求无约束最优 X = {value}，但该解在 {几何 / 物理 / 题目} 中违反
{具体约束}，因此引入约束 {表达式}，约束下最优解 Y = {value}，在 {指标} 上
比无约束解 {影响分析}。
```

这种工程思维会被评委加分。

---

## 选型对照表

| 问题特征 | 首选 | 备选 |
|---|---|---|
| 线性 + 连续 | LP | 二次规划 (QP) |
| 线性 + 整数 | IP / MIP | DP（小规模） |
| 非线性 + 平滑 | scipy.optimize.minimize | PSO |
| 非线性 + 不平滑 / 不可导 | GA / SA | DE / PSO |
| 多目标 | NSGA-II | 加权和 / ε-约束 |
| 高维大规模 | LP / IP（专业求解器） | DE |
| 序贯决策 | DP | RL（仅大规模时） |
| 黑盒目标（评估贵） | 贝叶斯优化 | 高斯过程 |

## 评估指标速查

| 类型 | 指标 |
|---|---|
| 单目标 | 最优值 / 收敛代数 / 鲁棒性（多种子方差） |
| 多目标 | HV / IGD / Pareto 前沿点数 |
| 整数规划 | mip_gap / 求解时间 |

## 可视化建议

| 内容 | 推荐图 |
|---|---|
| 收敛曲线 | best fitness vs generation |
| 多种子鲁棒性 | 折线 + 阴影置信带 |
| 二维 / 三维问题 | 等高线 + 最优点标注 |
| 多目标 Pareto | 散点（前沿）+ 标注关键点 |
| 灵敏度 | 参数 ±20% 时最优值变化曲线 |

## 常见全栈错误

| ❌ 错误 | ✅ 正确 |
|---|---|
| 优化变量无上下界 | bounds 必填，写来源 |
| 把整数问题写成 LP | IP / MIP |
| GA 跑一次就报最优 | ≥ 5 种子取均值 + 方差 |
| Big-M 取 1e9 | 收紧到题目规模上限的 2-3 倍 |
| 未做无约束 vs 约束对比 | 必须对比并 print |
| 多目标用加权和（权重凭直觉） | NSGA-II + Pareto 前沿 |
