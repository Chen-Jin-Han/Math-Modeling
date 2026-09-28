# 06 综合类算法

> 蒙特卡洛 / 排队论 / 博弈论 / 元胞自动机 / 马尔可夫 / 微分方程 / 风险度量
> 的"教材级"参考。这一类是数学建模赛题的"压舱石"，几乎每年都至少出现一种。

## 1. 蒙特卡洛模拟（MC）

### 何时选

- 解析解难求 / 不存在
- 有随机性（参数不确定 / 输入分布已知）
- 需要分布、期望、分位数、稀有事件概率

### 核心思路

```
1. 给输入参数定分布（先验 / 历史数据 / 文献）
2. 抽样 N 次（默认 N ≥ 10000）
3. 对每次抽样跑模型 → 得 N 个输出
4. 统计：均值、方差、CDF、分位数（含 95% 置信区间）
```

### 收敛速度

误差 $\sim 1/\sqrt{N}$，与维度无关（这是 MC 的核心优势）。
要把误差减半需要 4 倍样本量。

### 方差缩减技术

| 技术 | 适用 | 减少方差 |
|---|---|---|
| 控制变量 | 已知相关变量的解析期望 | 显著 |
| 重要性采样 | 抽稀有事件 | 巨大 |
| 分层采样 | 输入有自然分层 | 中等 |
| 对偶变量 | 对称分布 | 50% |
| 拉丁超立方 | 多维参数空间 | 中等 |

### 关键参数

- `N` 样本数（默认 1e4，关键场景 1e6）
- 输入分布（正态 / lognormal / Beta / 自定义）
- 随机种子（**必固定**确保可复现）

### 常见坑

- $N$ 不够 → 必须报置信区间。
- 没固定 `random_state` → 论文不可复现。
- 分布假设不当（金融用正态忽略尖峰厚尾） → 改用 t 分布 / GARCH / 历史模拟。
- 用 MC 解能解析的题 → 评委觉得偷懒。

### Python 入口

```python
import numpy as np

def monte_carlo_var(returns_distribution, n_sims=100000, alpha=0.05, seed=42):
    """计算 VaR / CVaR"""
    rng = np.random.default_rng(seed)
    samples = returns_distribution(rng, n_sims)
    var = np.quantile(samples, alpha)        # VaR
    cvar = samples[samples <= var].mean()     # CVaR / Expected Shortfall
    se = samples.std(ddof=1) / np.sqrt(n_sims)
    return {"VaR": var, "CVaR": cvar, "se": se}

# 用法
def returns(rng, n):
    return rng.standard_t(df=5, size=n) * 0.02 - 0.001  # 厚尾收益率

result = monte_carlo_var(returns, n_sims=100000)
print(result)
```

### 验证

- 解析解可比时（小算例）必比对。
- 多 $N$（1e3, 1e4, 1e5）画收敛曲线 → 论文必备。
- 多种子（≥ 5）报均值 + 标准差。

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Metropolis, N. & Ulam, S. | The Monte Carlo Method | J. ASA | 1949 |
| Robert, C.P. & Casella, G. | Monte Carlo Statistical Methods | Springer | 2004 |

---

## 2. 排队论

### 何时选

服务系统瓶颈分析、排队等待时间、资源利用率。

### Kendall 记号 A/S/c/K/N/D

- A：到达分布（M = 泊松，G = 一般）
- S：服务分布
- c：服务台数
- K：系统容量上限
- N：客户源大小
- D：服务规则（FCFS、LCFS、SIRO、PR）

省略后三项默认 ∞ / FCFS。

### M/M/1 公式速查

| 量 | 公式 |
|---|---|
| 利用率 | $\rho = \lambda / \mu$ |
| 系统中平均人数 | $L = \rho / (1 - \rho)$ |
| 队列中平均人数 | $L_q = \rho^2 / (1 - \rho)$ |
| 平均逗留时间 | $W = L / \lambda = 1 / (\mu - \lambda)$ |
| 平均排队时间 | $W_q = L_q / \lambda$ |
| 服务台空闲概率 | $P_0 = 1 - \rho$ |

**前提**：$\rho < 1$（否则系统不稳，队列趋向无穷）。

### M/M/c 公式

```
P_0 = 1 / [Σ_{n=0}^{c-1} (cρ)^n / n! + (cρ)^c / (c!(1-ρ))]
L_q = (cρ)^c ρ / (c! (1-ρ)^2) × P_0   ← Erlang C 公式
W_q = L_q / λ
W = W_q + 1/μ
L = λW
```

### M/G/1（Pollaczek-Khinchine）

```
L_q = ρ^2 (1 + Cs^2) / (2(1-ρ))
```

其中 $Cs = \sigma_s / E(S)$ 是服务时间的变异系数。

### 常见坑

- $\rho \ge 1$ 排队趋于无穷 → 必须扩容 / 限容。
- 假设泊松到达却不做检验 → 必做 $\chi^2$ / K-S。
- 从平均等待时间直接得"99% 分位数"是错的（Little 定律不给分位数）。

### Python 入口（仿真）

```python
import simpy
import random

def customer(env, name, server, service_time):
    arrival = env.now
    with server.request() as req:
        yield req
        wait = env.now - arrival
        yield env.timeout(random.expovariate(1.0 / service_time))
        # 记录 wait

def source(env, server, mean_inter, mean_service, max_n=1000):
    for i in range(max_n):
        yield env.timeout(random.expovariate(1.0 / mean_inter))
        env.process(customer(env, i, server, mean_service))

env = simpy.Environment()
server = simpy.Resource(env, capacity=1)  # M/M/1
env.process(source(env, server, mean_inter=10, mean_service=8))
env.run(until=10000)
```

公式手算用 `numpy` 即可；`pyqueue` 也可。

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Erlang, A.K. | The Theory of Probabilities and Telephone Conversations | Nyt Tidsskrift Matematik | 1909 |
| Little, J.D.C. | A proof for the queuing formula L = λW | Operations Research | 1961 |

---

## 3. 博弈论

### 类型

| 类型 | 特征 | 求解 |
|---|---|---|
| 零和 | 二人，一方收益 = 另一方损失 | minimax / LP |
| 非零和 | 多人，可合作 | 纳什均衡 |
| Stackelberg | 有领导 / 跟随 | 反向归纳 |
| 演化博弈 | 群体 / 选择动力学 | 复制者方程 |
| 合作博弈 | 联盟可分配收益 | Shapley 值 / 核 |

### 纳什均衡（混合策略）

二玩家零和：

```
玩家 1 选 i 的混合概率 p_i，玩家 2 选 j 的概率 q_j
玩家 1 最大化期望收益：max p^T A q
鞍点条件：min q max p p^T A q
转化为 LP 求解
```

### Stackelberg

```
反向归纳：
1. 跟随者最优响应 R(s_L) = arg max u_F(s_L, s_F)
2. 领导者最优策略 s_L* = arg max u_L(s_L, R(s_L))
```

### 演化博弈（复制者动力学）

$$
\dot x_i = x_i (f_i(x) - \bar f(x))
$$

其中 $f_i$ 是策略 $i$ 的适应度，$\bar f$ 是群体平均适应度。

### Shapley 值

每个玩家在所有可能联盟中的"边际贡献"平均：

$$
\phi_i(v) = \sum_{S \subseteq N \setminus \{i\}} \frac{|S|! (n-|S|-1)!}{n!} (v(S \cup \{i\}) - v(S))
$$

### Python 入口

```python
import nashpy as nash
import numpy as np

# 二人零和
A = np.array([[3, -1], [-1, 1]])  # 玩家 1 的收益矩阵
game = nash.Game(A)
equilibria = list(game.support_enumeration())
for eq in equilibria:
    print(eq)

# 复制者方程
def replicator(t, x, payoff):
    f = payoff @ x
    return x * (f - x @ f)

from scipy.integrate import solve_ivp
sol = solve_ivp(replicator, [0, 50], y0=[0.4, 0.3, 0.3],
                args=(payoff_matrix,), dense_output=True)
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| von Neumann, J. & Morgenstern, O. | Theory of Games and Economic Behavior | Princeton | 1944 |
| Nash, J.F. | Equilibrium points in n-person games | PNAS | 1950 |

---

## 4. 马尔可夫链

### 何时选

状态转移、无后效性、稳态分布。

**典型**：用户行为、信用评级转移、天气、PageRank、HMM。

### 核心

转移矩阵 $P_{ij} = \Pr(X_{t+1} = j \mid X_t = i)$。

- **n 步转移**：$P^n$
- **稳态分布** $\pi$：$\pi P = \pi$，$\sum \pi_i = 1$（左特征向量）
- **遍历性**：不可约 + 非周期 → 唯一稳态

### 估计转移概率

频率法 + 拉普拉斯平滑：

```
P_ij = (count(i → j) + α) / (count(i) + α × |S|)
```

$\alpha = 1$ 时为 add-one 平滑。

### Python 入口

```python
import numpy as np

# 估计 + 稳态
def fit_markov(seq, smoothing=1.0):
    states = sorted(set(seq))
    s2i = {s: i for i, s in enumerate(states)}
    n = len(states)
    counts = np.full((n, n), smoothing)
    for a, b in zip(seq[:-1], seq[1:]):
        counts[s2i[a], s2i[b]] += 1
    P = counts / counts.sum(axis=1, keepdims=True)
    return states, P

def stationary(P):
    # 解 πP = π
    eigvals, eigvecs = np.linalg.eig(P.T)
    idx = np.argmin(np.abs(eigvals - 1))
    pi = np.abs(eigvecs[:, idx].real)
    return pi / pi.sum()
```

### HMM（隐马尔可夫）

观测序列 + 隐状态：用 Baum-Welch 学习参数；Viterbi 求最优状态序列。

```python
from hmmlearn import hmm
model = hmm.GaussianHMM(n_components=3, covariance_type='diag')
model.fit(observations)
hidden_states = model.predict(observations)
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Markov, A.A. | Investigation of a remarkable case of dependent trials | 1906 | 1906 |
| Rabiner, L.R. | A tutorial on HMMs | Proc. IEEE | 1989 |

---

## 5. 元胞自动机（CA）

### 何时选

空间扩散、传染病、森林火灾、城市生长、生物种群。

### 三要素

- **网格**：1D（一维元胞）/ 2D（最常用）/ 3D
- **邻域**：冯诺依曼（4 邻）/ 摩尔（8 邻）
- **规则**：当前细胞下一时刻状态 = $f$(当前 + 邻居状态)

### 经典示例：Conway 生命游戏（B3/S23）

```
活细胞 + 邻居 = 2 或 3 → 存活
活细胞 + 邻居 ≠ 2,3 → 死亡
死细胞 + 邻居 = 3 → 复活
```

### 网格 SIR 传染病

```
S（易感） → I（感染）：以概率 β × 邻居感染数 / 邻居总数 转化
I → R（康复）：以概率 γ 转化
```

### 边界条件

- 周期性（toroidal）：右边界 → 左边界
- 反射（neumann）：边界处镜像
- 吸收（dirichlet）：固定值（如 0）

### Python 入口

```python
import numpy as np
from scipy.signal import convolve2d

def life_step(grid):
    kernel = np.array([[1,1,1],[1,0,1],[1,1,1]])
    nb = convolve2d(grid, kernel, mode='same', boundary='wrap')
    return ((grid == 1) & ((nb == 2) | (nb == 3))) | ((grid == 0) & (nb == 3))

grid = np.random.choice([0, 1], size=(50, 50), p=[0.7, 0.3])
for _ in range(100):
    grid = life_step(grid).astype(int)
```

### 常见坑

- 网格分辨率太低 → 离散误差掩盖现象
- 规则太死板（确定性） → 加入噪声 / 随机扰动
- 大网格 + 长时间 → 计算爆炸；用 numba / GPU

---

## 6. 微分方程建模

### 6.1 常微分方程（ODE）

经典模型：

| 模型 | 方程 |
|---|---|
| 人口增长（Logistic） | $\dot N = r N (1 - N/K)$ |
| 捕食（Lotka-Volterra） | $\dot x = ax - bxy$, $\dot y = -cy + dxy$ |
| 传染病 SIR | $\dot S = -\beta SI$, $\dot I = \beta SI - \gamma I$, $\dot R = \gamma I$ |
| 化学反应 | $\dot c_i = \sum_j \nu_{ij} r_j$ |
| 单摆 | $\ddot \theta + (g/L) \sin\theta = 0$ |

### Python 入口

```python
from scipy.integrate import solve_ivp
import numpy as np

def sir(t, y, beta, gamma):
    S, I, R = y
    return [-beta*S*I, beta*S*I - gamma*I, gamma*I]

sol = solve_ivp(sir, [0, 160], y0=[0.99, 0.01, 0],
                args=(0.3, 0.1), method='RK45', dense_output=True,
                t_eval=np.linspace(0, 160, 200))
```

**method 选择**：
- 非刚性：`RK45`（默认，4-5 阶 Runge-Kutta）
- 刚性：`BDF` / `LSODA`（自适应）
- 高精度：`DOP853`

### 6.2 偏微分方程（PDE）

经典：

| 方程 | 含义 |
|---|---|
| 扩散 | $\partial_t u = D \nabla^2 u$ |
| 波动 | $\partial_{tt} u = c^2 \nabla^2 u$ |
| 热传导 | $\partial_t T = \alpha \nabla^2 T + Q$ |

**求解**：FDM（有限差分） / FEM（有限元） / FVM（有限体积）。

**坑**：CFL 条件（$c \Delta t / \Delta x \le 1$），违反则数值发散。

### Python 入口

```python
# 1D 扩散方程，简单显式 FDM
import numpy as np
nx, nt = 100, 1000
dx, dt = 0.01, 1e-5
D = 1.0
u = np.zeros(nx); u[40:60] = 1.0
for _ in range(nt):
    u[1:-1] += D * dt / dx**2 * (u[2:] - 2*u[1:-1] + u[:-2])
```

复杂场景用 `fipy`、`fenics`、`py-pde`。

### 6.3 参数估计（反问题）

观测数据反推 ODE / PDE 参数：

```python
from scipy.optimize import minimize

def loss(params):
    sol = solve_ivp(sir, [0, T], y0, args=tuple(params), t_eval=t_obs)
    return np.sum((sol.y[1] - I_obs)**2)

result = minimize(loss, x0=[0.3, 0.1], method='Nelder-Mead')
```

贝叶斯版本用 `pymc` / `emcee`。

---

## 7. 风险度量

| 指标 | 含义 | 公式 |
|---|---|---|
| VaR | 给定置信度下最大损失 | $\Pr(L > \text{VaR}) = \alpha$ |
| CVaR / ES | 超 VaR 的条件期望 | $\mathbb{E}[L \mid L > \text{VaR}]$ |
| 夏普比 | 单位风险的超额收益 | $(R - R_f) / \sigma$ |
| 最大回撤 | 历史最大累积损失 | $\max_t (\text{peak}_t - \text{value}_t) / \text{peak}_t$ |
| 索提诺比 | 下行风险版夏普比 | 用下行方差代替总方差 |

### 关键性质

- VaR 不是 coherent risk measure（缺次可加性）。
- CVaR 满足次可加性，**金融监管已转向 CVaR**。

```python
import numpy as np

def calc_risk(returns, alpha=0.05):
    var = np.quantile(returns, alpha)
    cvar = returns[returns <= var].mean()
    sharpe = returns.mean() / returns.std() * np.sqrt(252)  # 年化
    cum = (1 + returns).cumprod()
    peak = np.maximum.accumulate(cum)
    mdd = ((peak - cum) / peak).max()
    return {"VaR": var, "CVaR": cvar, "Sharpe": sharpe, "MaxDD": mdd}
```

---

## 选型对照表

| 题型 | 首选 |
|---|---|
| 不确定性 / 风险 | 蒙特卡洛 |
| 服务系统 | M/M/c |
| 多方决策 | Nash / Stackelberg |
| 状态转移 | 马尔可夫链 |
| 空间扩散 | 元胞自动机 |
| 连续动力学 | ODE / PDE |
| 风险量化 | CVaR > VaR |

## 可视化建议

| 内容 | 推荐图 |
|---|---|
| MC 收敛 | 不同 N 的均值 ± 标准误 |
| MC 分布 | 直方图 + KDE + VaR 阈值线 |
| 排队稳态 | 利用率 vs 队列长度的曲线 |
| 博弈均衡 | 策略空间的 vector field（演化博弈） |
| 马尔可夫稳态 | 条形图（各状态稳态概率） |
| CA 演化 | 时序网格快照（`imshow` 多帧） |
| ODE 解 | 折线图 + 多解叠加 + 相图 |
| 风险 | 累积分布 + VaR / CVaR 标注 |

## 常见全栈错误

| ❌ 错误 | ✅ 正确 |
|---|---|
| MC 不报置信区间 | 必报均值 ± SE |
| 排队 ρ ≥ 1 仍报稳态 | 不稳；扩容或限容 |
| ODE 刚性方程用 RK45 | 改 BDF / LSODA |
| CA 边界处理错误 | 明确周期 / 反射 / 吸收 |
| HMM 不报对数似然 | 必须报，便于模型选择 |
| VaR 当 coherent 用 | 改用 CVaR |
| 解析可解题硬上 MC | 评委扣"偷懒分" |
