---
name: cumcm-b
description: 数学建模国赛 B 题（优化/运筹/规划）解题方法。当题目涉及资源调度、路径规划、最优决策、选址、排班、分配、组合优化、生产决策、线性/整数/非线性/动态/多目标规划、图论、排队论时使用。核心套路：定义决策变量 → 构建目标函数 → 梳理约束 → 判定模型类型 → 求解 → 灵敏度分析。内含完整遗传/退火/粒子群代码与常见问题模式。
---

# 数模国赛 B 题：优化 / 运筹 / 规划

B 题核心是**运筹优化**：在可行域里找"最好"的方案。注意近年 B/C 边界模糊（2024 B=生产决策、C=农作物种植都是优化+不确定性），所以 B 题方法也可能出现在 C 题里，反之亦然。

---

## 一、通用解题流程（6 步）

1. **审题**：反复精读，明确"要决定什么"（决策变量的来源）
2. **定义决策变量**：题目要你"决定"的东西 → `x`（选不选、放几个、走哪条、何时开始、测不测……）
3. **构建目标函数**：最大利润 / 最小成本 / 最短时间 / 最小风险 / 最大收益
4. **梳理约束条件**：所有限制翻译成等式/不等式（资源上限、需求下限、逻辑关系、整数要求、0-1 互斥）
5. **判定模型类型**：线性？整数？0-1？非线性？动态？多目标？随机？
6. **选择算法求解 + 灵敏度分析**

---

## 二、规划模型五大家族

### 1. 线性规划（LP）
目标与约束都线性，最优解在可行域顶点。
```python
from scipy.optimize import linprog
res = linprog(c, A_ub=A, b_ub=b, bounds=[(0, None)]*n, method="highs")
x_opt, f_opt = res.x, res.fun
```

### 2. 整数规划（IP）/ 0-1 规划
决策变量取整数；**整数最优解不能由实数解简单取整**。0-1：变量 ∈ {0,1}。
```python
from scipy.optimize import milp, LinearConstraint, Bounds
import numpy as np
res = milp(c=c, integrality=np.ones(n),        # 1=整数
           constraints=LinearConstraint(A, ub=b), bounds=Bounds(0, 1))
```
更灵活的建模用 `pulp`（支持 0-1、混合整数、多目标转单目标）：
```python
import pulp
prob = pulp.LpProblem("p", pulp.LpMinimize)
x = [pulp.LpVariable(f"x{i}", cat="Binary") for i in range(n)]  # Binary/Integer/Continuous
prob += pulp.lpSum(c[i]*x[i] for i in range(n))                  # 目标
prob += pulp.lpSum(a[i]*x[i] for i in range(n)) <= b             # 约束
prob.solve()
```

### 3. 非线性规划（NLP）
目标或约束含非线性，**无通用解法**。
```python
from scipy.optimize import minimize
res = minimize(f, x0, method="SLSQP", constraints=cons, bounds=bnds)  # 带约束
res = minimize(f, x0, method="L-BFGS-B", bounds=bnds)                 # 带界
```

### 4. 动态规划（DP）
按时间/阶段划分的多阶段决策；核心是**状态转移方程 + 最优子结构**。
```python
dp = [0]*(n+1)
for j in range(1, n+1):
    dp[j] = max(dp[i] + cost(i, j) for i in range(j))   # 一维，前缀和可优化 O(N²)→O(N)
# 多阶段二维：dp[k][j] = min_i dp[k-1][i] + (j-i)*R(...)
```

### 5. 多目标规划
转化为单目标：加权法 `min Σ w_k f_k(x)`；序贯法（先优化第一目标，再在其最优集里优化第二）；ε-约束法（其余目标转约束）。

---

## 三、现代优化算法（完整可运行代码）

**原则：能精确解（LP/IP/DP）就别用启发式；启发式用于规模大/非凸/NP 难，且要跑多次取最好并说明随机性。**

### 遗传算法 GA（离散 + 连续通用）
```python
import numpy as np

def genetic_algorithm(fitness, n_vars, n_pop=100, n_gen=200,
                      bounds=(0, 1), integer=False, p_cross=0.8, p_mut=0.1):
    """fitness: 越大越好(求最小传-f)；integer=True 表离散决策变量"""
    lo, hi = bounds
    rng = np.random.default_rng(42)
    pop = rng.integers(lo, hi+1, (n_pop, n_vars)) if integer \
          else rng.uniform(lo, hi, (n_pop, n_vars))
    for _ in range(n_gen):
        fit = np.array([fitness(ind) for ind in pop])
        prob = fit - fit.min() + 1e-9; prob /= prob.sum()     # 轮盘赌
        parents = pop[rng.choice(n_pop, n_pop, p=prob)]
        child = parents.copy()
        for i in range(0, n_pop, 2):
            if rng.random() < p_cross:
                k = rng.integers(1, n_vars)
                child[i, k:], child[i+1, k:] = child[i+1, k:].copy(), child[i, k:].copy()
        mask = rng.random((n_pop, n_vars)) < p_mut
        child[mask] = rng.integers(lo, hi+1, mask.sum()) if integer \
                      else rng.uniform(lo, hi, mask.sum())
        pop = child
    fit = np.array([fitness(ind) for ind in pop])
    return pop[np.argmax(fit)], fit.max()
```

### 模拟退火 SA（连续优化，跳出局部最优）
```python
def simulated_annealing(f, x0, bounds, T0=1000., T_min=1e-3, alpha=0.95, n_iter=200):
    """f: 求最小；bounds: [(lo,hi),...]"""
    rng = np.random.default_rng(42)
    lo = np.array([b[0] for b in bounds]); hi = np.array([b[1] for b in bounds])
    x = np.array(x0, float); T = T0
    best_x, best_f = x.copy(), f(x)
    while T > T_min:
        for _ in range(n_iter):
            xn = np.clip(x + rng.normal(0, T/100, x.shape), lo, hi)
            d = f(xn) - f(x)
            if d < 0 or rng.random() < np.exp(-d/T):   # 接受劣解概率
                x = xn
                if f(x) < best_f: best_x, best_f = x.copy(), f(x)
        T *= alpha
    return best_x, best_f
```

### 粒子群 PSO（连续优化，收敛快）
```python
def pso(f, n_vars, bounds, n_p=50, n_iter=200, w=0.7, c1=1.5, c2=1.5):
    rng = np.random.default_rng(42)
    lo = np.array([b[0] for b in bounds]); hi = np.array([b[1] for b in bounds])
    X = rng.uniform(lo, hi, (n_p, n_vars)); V = rng.uniform(-1, 1, (n_p, n_vars))
    pb = X.copy(); pbf = np.array([f(x) for x in X])
    gb = pb[np.argmin(pbf)]; gbf = pbf.min()
    for _ in range(n_iter):
        V = w*V + c1*rng.random((n_p,n_vars))*(pb-X) + c2*rng.random((n_p,n_vars))*(gb-X)
        X = np.clip(X + V, lo, hi)
        fv = np.array([f(x) for x in X])
        m = fv < pbf; pb[m] = X[m]; pbf[m] = fv[m]
        if fv.min() < gbf: gbf = fv.min(); gb = X[np.argmin(fv)]
    return gb, gbf
```

> 也可直接用 `scipy.optimize.dual_annealing`（退火）、`differential_evolution`（差分进化）。

---

## 四、常见 B 题问题模式（建模公式速查）

| 问题模式 | 决策变量 | 目标 | 典型约束 | 解法 |
|---|---|---|---|---|
| 选址 p-median | x_ij 是否服务，y_j 是否建 | min ΣΣ d_ij x_ij | Σx_ij=1，Σy_j=p | 整数规划 / 启发式 |
| 覆盖选址 | y_j 是否建 | max 覆盖需求 / min 建点数 | 覆盖半径约束 | 0-1 规划 |
| TSP 旅行商 | x_ij 是否走 i→j | min Σ d_ij x_ij | 每点进出各一次，消子环 | 精确(小)/遗传·蚁群 |
| VRP 车辆路径 | x_ijv 车辆 v 走 i→j | min 总里程 | 容量、时间窗、车辆数 | 启发式/邻域搜索 |
| 指派/分配 | x_ij 0-1 | min Σ c_ij x_ij | 每行每列恰一个 1 | 匈牙利 `linear_sum_assignment` |
| 背包 | x_i 是否选 | max Σ v_i x_i | Σ w_i x_i ≤ W | DP / 分枝定界 |
| 生产计划/调度 | x 产量、开工顺序 | max 利润 / min 时间 | 产能、工序先后、库存 | LP/MIP/DP/仿真 |
| 抽样检验方案 | 样本量 n、判拒数 c | min 成本 | 二类错误率 α/β | 假设检验 + 二项/正态 |

**2024 B 题（生产过程决策）套路**：抽样检验（正态/二项分布定 n 与 c）→ 期望利润模型（0-1 决策变量：是否检测零配件/成品、是否拆解不合格品）→ 动态规划/线性规划/仿真求最优。

---

## 五、图论与网络（路径/网络类）

| 问题 | 算法 | 库 |
|---|---|---|
| 最短路径 | Dijkstra / Floyd | `scipy.sparse.csgraph.shortest_path` |
| 最小生成树 | Prim / Kruskal | `scipy.sparse.csgraph.minimum_spanning_tree` |
| 最大流 | Ford-Fulkerson / Dinic | `networkx.maximum_flow` |
| 二分图匹配/指派 | 匈牙利 | `scipy.optimize.linear_sum_assignment` |
| TSP 近似 | Christofides | `networkx.approximation.traveling_salesman_problem` |

---

## 六、排队论（服务系统类）

- 记号 `M/M/1`、`M/M/c`；利用率 ρ = λ/(cμ)，**必须 ρ<1 才稳定**
- 利特尔定律 `L = λW`；队长、等待时间、系统容量
- 适用：分诊、窗口服务、呼叫中心、交通流

---

## 七、灵敏度分析（B 题必考）

1. 约束右端项 b 扰动 → 看最优值变化（影子价格 = 边际价值）
2. 目标系数 c 扰动 → 看最优解是否切换
3. 关键参数（速率/概率/容量/成本）±10% 上下浮动 → 结论是否稳健
4. 启发式算法的参数（种群、迭代、温度）扰动 → 收敛稳定性
5. 结论落点："在 XX 范围内方案稳定；某参数超 YY 时方案改变"

---

## 八、工具库速查

| 需求 | 库 |
|---|---|
| 线性/整数规划 | `scipy.optimize.linprog` / `milp` / `pulp` |
| 非线性优化 | `scipy.optimize.minimize` |
| 全局/启发式 | `dual_annealing` / `differential_evolution` / 自写 GA·SA·PSO |
| 图论 | `networkx` / `scipy.sparse.csgraph` |
| 专业求解器（规模大） | OR-Tools、Gurobi、CPLEX（可选，非必需） |

---

## 九、蒙特卡洛模拟与随机规划（不确定性建模）

B 题高频考点：价格、需求、次品率、气候等存在**随机性**时如何建模与求解。核心两招：**蒙特卡洛模拟（MC）** 与 **随机规划（SP）**。

### 1. 蒙特卡洛模拟（MC）
思想：用大量随机抽样估计期望/概率/分布，代替解析积分。三步：定义输入分布 → 抽样 → 统计输出。

```python
import numpy as np
rng = np.random.default_rng(42)

# (a) 估计期望/概率（含置信区间）
def f(x): return np.sqrt(np.maximum(x, 0))
n = 100000
x = rng.normal(0, 1, n)          # 输入分布
est = f(x).mean()
se = f(x).std(ddof=1) / np.sqrt(n)
print(f"E[f(X)] = {est:.4f}  (95%CI {est-1.96*se:.4f} ~ {est+1.96*se:.4f})")

# (b) 利润/风险模拟（输入有分布 → 输出是分布）
def sim_profit(p_mu, p_sd, d_mu, d_sd, unit_cost, fixed_cost, n=100000):
    price  = rng.normal(p_mu, p_sd, n)
    demand = rng.normal(d_mu, d_sd, n)
    return (price - unit_cost) * demand - fixed_cost
p = sim_profit(5, 1, 1000, 200, 2, 500)
print(f"期望利润 {p.mean():.1f} | 亏损概率 {(p<0).mean():.1%} | 5%分位(VaR) {np.percentile(p,5):.1f}")
```
> **输出要报告分布**（均值、分位数、亏损概率、置信区间），不是单个点估计——这是风险分析的核心，也是与"单参数±10%"式敏感性分析的区别。

### 2. 随机规划（SP）
面对随机量 ξ，三种模型：

| 模型 | 形式 | 适用 |
|---|---|---|
| 期望值模型 | min E[f(x,ξ)] | 追求长期平均最优 |
| 机会约束 | P(g(x,ξ)≤0) ≥ α | 约束要以高概率满足 |
| 两阶段 | min c'x + E[Q(x,ξ)] | 先定 x，看到 ξ 后补救 |

**期望值模型 + 样本平均近似（SAA）**：
```python
from scipy.optimize import minimize
scenarios = rng.normal(5, 1, 1000)            # 抽 N 个场景近似随机量
def f(x, xi): return (x - xi)**2 + 0.1*x**2
def saa(x): return np.mean([f(x, s) for s in scenarios])
res = minimize(saa, x0=0, method="BFGS")
print(f"x* = {res.x[0]:.3f}, 期望目标 {res.fun:.3f}")
```
> SAA：把随机问题用 N 个抽样场景近似成确定性优化，N 越大越精确。

**机会约束**（MC 检验违反概率）：`violation = np.mean([g(x,s)>0 for s in scenarios])`，要求 ≤ 1-α。

**两阶段（报童问题是特例）**：
```python
def two_stage(x, scenarios, c0, cu, co):
    cost = c0 * x
    for s in scenarios:
        cost += (cu*(s-x) if s > x else co*(x-s))   # 缺货/积压单位成本
    return cost / len(scenarios)
# 搜索 x 使期望两阶段成本最小
```

### 3. 模拟优化（仿真 + 优化结合）
解析目标写不出、只能靠仿真评估时：对每个候选决策做 MC 仿真求期望，再搜索最优。
```python
def mc_eval(strategy, n=5000):
    return np.mean([simulate(strategy) for _ in range(n)])
best = min(candidates, key=mc_eval)   # 候选策略里选期望最优
```
典型：2020 B 沙漠游戏（DP + 蒙特卡洛）、2024 B 生产决策（仿真建模）、2024 C 农作物（遗传算法 + MC 评风险）。

---

## 十、历年真题逐问拆解（练手模板）

> 逐问拆解万能模板：**研究对象 → 输入 → 输出 → 难点 → 模型 → 算法 → 与上问关系**。七问问完，建模方向基本就定了。

### 2024 B 题 · 生产过程决策
**问题1 设计抽样检测方案（判断次品率是否超标称值）**
- 对象：一批零配件次品率 p；输入：标称值 p0、两类错误容忍度；输出：样本量 n + 判拒数 c
- 模型：假设检验，次品数 `X~Binomial(n,p)`，`H0: p≤p0`，拒绝域 `X≥c`
- 算法：正态近似求 n、c，或序贯抽样（边抽边判更省样本）；画 OC 曲线（各 p 下的接受概率）

**问题2 是否检测零配件/成品、是否拆解不合格品**
- 决策变量：0-1（检测零配件？检测成品？拆解？调换？）
- 模型：期望利润模型（全概率/决策树），期望利润 = Σ 各分支利润×概率
- 算法：0-1 整数规划 / 枚举 / 动态规划；本质是"检测成本 vs 漏检期望损失"的经济阈值

**问题3 多工序多零配件综合最优**
- 模型：多阶段 DP（阶段=工序，状态=次品/库存）或混合整数规划
- 难点：状态爆炸 → 蒙特卡洛仿真近似
- 关键：问题3 是问题2 的推广，论文要体现继承关系

---

## 十一、常见坑位

1. 整数规划当线性规划解再取整（会不可行/次优）
2. 多目标没有权重/优先级说明
3. 漏约束（非负、整数、逻辑互斥）
4. 启发式只跑一次、不说明随机性、不验证收敛
5. 排队论 ρ ≥ 1 没发现（系统发散）
6. 动态规划没写清楚状态定义和状态转移方程
7. 只给最优值不给最优方案（决策变量取值必须列出）
8. 蒙特卡洛模拟没有设置足够样本、没给置信区间

---

## 十二、模型选择决策规则（借鉴补充）

> 方法论思路借鉴自 [skillforCUMCM/math-modeling-skill-pro](https://github.com/skillforCUMCM/math-modeling-skill-pro)（专有许可，仅借鉴通用建模方法论思路，已重写），结合优化题特点整理。

1. **先写出优化模型再谈算法**：决策变量 / 目标 / 约束没写清之前，不用任何元启发式（GA/SA/PSO）——否则只是"盲搜"。
2. **能精确解就别用启发式**：LP/IP/DP 能解就用精确解；启发式只用于规模大/非凸/NP 难，且要**多随机种子 + 报分布 + 小规模精确对照**，不能只报单次最好值。
3. **小样本优化不用深度学习**，除非数据量明确支持。
4. **相关性 ≠ 因果**：不把相关系数高的变量直接写成因果机制或决策依据。
5. **不只用一次参数扰动就宣称稳健**：给出"可行率 / 最坏分位数 / 排名翻转率 / 决策后悔值 / 稳定区间"。
6. **三方案对照**：A=现状方案/线性松弛/贪心（基线），B=结构化改进+完整灵敏度（主力），C=随机约束/动态权重/网络依赖等创新（有消融才上）。论文里体现"为何从 A 升到 B"。

**验证五层**（优化题）：①可行性（逐条算约束余量）②正确性（小规模枚举/精确解对照）③最优性（LP/MILP 报 gap；启发式只称"当前最好"）④算法性（多种子/收敛轨迹/耗时）⑤决策性（样本外情景的目标/后悔值/失效率）。
