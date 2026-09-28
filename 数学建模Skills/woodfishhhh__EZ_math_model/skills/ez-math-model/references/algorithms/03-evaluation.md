# 03 评价类算法

> 权重确定 / 方案排序 / 模糊评价 / 效率评价的"教材级"参考。
> 本文档目标：让 modeler 不读教材就能完成方案；让 coder 能找到可落地的
> Python 入口；让 writer 能从这里抄公式与文献。

## 概述

评价类问题的核心是把"多维度指标"压缩为"可比较的标量"。流程：

```
原始指标矩阵 X (n 方案 × m 指标)
   ↓ 1. 指标方向化（成本型 → 效益型 / 区间型 → 偏离度型）
   ↓ 2. 量纲统一（标准化 / 极差化 / 向量归一）
   ↓ 3. 权重确定（主观 AHP / 客观 熵权 / 主客观结合）
   ↓ 4. 综合评价（TOPSIS / 模糊综合 / 灰色关联 / DEA）
   ↓ 5. 排序与解释（含敏感性分析）
```

## 通用预处理

### 指标方向化

| 类型 | 示例 | 处理 |
|---|---|---|
| 效益型（越大越好） | 收益、命中率 | 不变 |
| 成本型（越小越好） | 成本、错误率 | $x'_{ij} = \max_i(x_{ij}) - x_{ij}$ 或 $1/x_{ij}$ |
| 区间型（在区间内越好） | 体温 36.0-37.0 | $x'_{ij} = 1 - \frac{\max(a-x, x-b, 0)}{\max(a-x_{\min}, x_{\max}-b)}$ |
| 中间型（取定值最好） | pH = 7 | $x'_{ij} = 1 - \frac{|x_{ij} - x^*|}{\max_i|x_{ij} - x^*|}$ |

### 标准化方法

| 方法 | 公式 | 适用 |
|---|---|---|
| Z-score | $z = (x - \mu) / \sigma$ | 近似正态，对异常值敏感 |
| Min-Max | $z = (x - \min) / (\max - \min)$ | 神经网络输入、距离类算法 |
| Robust | $z = (x - \text{median}) / \text{IQR}$ | 含异常值 |
| 向量归一 | $z_{ij} = x_{ij} / \sqrt{\sum_i x_{ij}^2}$ | TOPSIS 标配 |
| Log1p | $z = \ln(1+x)$ | 右偏 / 长尾 |

---

## 1. 层次分析法（AHP, Saaty 1980）

### 何时选

决策准则有层次结构、专家意见可获取、需要主观权重。**典型场景**：方案选优、
风险评估、人员评价、政策对比。

### 核心思路

```
1. 建立层次结构（目标层 → 准则层 → 方案层）
2. 构造判断矩阵 A_{n×n}：a_{ij} ∈ {1/9, 1/8, ..., 1, 2, ..., 8, 9}
3. 计算权重向量 w：求 A 的最大特征值 λ_max 对应的特征向量
4. 一致性检验：CI = (λ_max - n) / (n - 1)，CR = CI / RI
   - CR < 0.1 → 通过
   - 否则修正判断矩阵
5. 综合排序：方案得分 = ∑ 权重 × 指标值
```

### Saaty 1-9 标度

| 标度 | 含义 |
|---|---|
| 1 | 同等重要 |
| 3 | 稍微重要 |
| 5 | 明显重要 |
| 7 | 强烈重要 |
| 9 | 极端重要 |
| 2,4,6,8 | 上述相邻判断的中间值 |
| 倒数 | 反向比较 |

### RI 表（随机一致性指标）

| n | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| RI | 0 | 0 | 0.58 | 0.90 | 1.12 | 1.24 | 1.32 | 1.41 | 1.45 | 1.49 |

### 关键参数

- **判断矩阵规模**：n ≤ 9（超过应分层）
- **专家人数**：≥ 3（单专家易主观）
- **聚合方式**：算术平均 / 几何平均 / Borda 计数

### 常见坑

- 不做一致性检验 → 必须 CR < 0.1。
- 准则维度 > 9 → 必须分层细化。
- 单专家打分 → 至少 3 专家或加敏感性。
- 判断矩阵元素来源不明 → 论文中要写"基于 X 文献 / Y 专家德尔菲"。

### 验证

- CR < 0.1（硬门）
- 把权重做 ±20% 扰动，看排序是否稳定（敏感性分析章节用得上）
- 与 AHP 群决策结果对比

### Python 入口

```python
import numpy as np

def ahp_weights(A: np.ndarray) -> tuple[np.ndarray, float]:
    """A 是 n×n 判断矩阵，返回 (权重向量, CR)"""
    n = A.shape[0]
    eigvals, eigvecs = np.linalg.eig(A)
    max_idx = np.argmax(eigvals.real)
    w = np.abs(eigvecs[:, max_idx].real)
    w = w / w.sum()
    lam_max = eigvals[max_idx].real
    CI = (lam_max - n) / (n - 1) if n > 1 else 0
    RI = [0, 0, 0.58, 0.90, 1.12, 1.24, 1.32, 1.41, 1.45, 1.49]
    CR = CI / RI[n-1] if n > 2 and RI[n-1] > 0 else 0
    return w, CR

# 用法
A = np.array([[1, 3, 5], [1/3, 1, 2], [1/5, 1/2, 1]])
w, CR = ahp_weights(A)
print(f"权重: {w}, CR: {CR:.4f}")
assert CR < 0.1, "AHP 一致性检验未通过"
```

可用库：`numpy`（手写 50 行）、`pyahp`、`scikit-criteria`。

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Saaty, T.L. | The Analytic Hierarchy Process | McGraw-Hill | 1980 |
| Saaty, T.L. | Decision making with the analytic hierarchy process | Int. J. Services Sciences | 2008 |

---

## 2. 熵权法（Entropy Weight）

### 何时选

有客观数据矩阵 X（n 方案 × m 指标）；需要客观权重；指标越离散越重要。

### 核心思路

```
1. 标准化 → P_{ij} = x'_{ij} / ∑_i x'_{ij}
2. 熵：e_j = -k ∑_i P_{ij} ln(P_{ij})，k = 1/ln(n)
3. 差异系数：g_j = 1 - e_j
4. 权重：w_j = g_j / ∑_j g_j
```

含义：某指标各方案取值越分散（熵越小），该指标在比较中越有分辨力，权重越大。

### 关键参数

- 归一化方式（min-max / Z-score）：通常 min-max。
- $P_{ij} = 0$ 时令 $P_{ij} \ln P_{ij} = 0$（约定）。

### 常见坑

- 数据全相同的指标 → 熵 = 1，权重 = 0，该指标在评价中被自动忽略。需检查是否本意。
- 极端值放大方差 → 先做异常值处理或用 Z-score。
- 成本型指标当效益型 → 必须按方向预处理（见通用预处理）。

### Python 入口

```python
import numpy as np

def entropy_weight(X: np.ndarray) -> np.ndarray:
    """X 是 n×m 标准化后的指标矩阵，返回 m 维权重"""
    n, m = X.shape
    P = X / X.sum(axis=0, keepdims=True)
    P = np.where(P > 0, P, 1e-12)  # 避免 ln(0)
    e = -np.sum(P * np.log(P), axis=0) / np.log(n)
    g = 1 - e
    return g / g.sum()
```

### 与 AHP 结合

主客观加权融合：$w_j = \alpha \cdot w^{AHP}_j + (1 - \alpha) \cdot w^{Entropy}_j$，
$\alpha \in [0, 1]$，常取 0.5；论文中应做 $\alpha$ 敏感性分析。

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Shannon, C.E. | A mathematical theory of communication | Bell System Tech. J. | 1948 |
| 程启月 | 评价指标客观赋权方法研究 | 数学的实践与认识 | 2010 |

---

## 3. TOPSIS（Hwang & Yoon 1981）

### 何时选

方案排序，权重已知（来自 AHP / 熵权 / 经验）。

### 核心思路

```
1. 加权标准化：V_{ij} = w_j × z_{ij}（z 为向量归一化后的值）
2. 正理想解 V^+：每列最大值组成的向量
   负理想解 V^-：每列最小值组成的向量
3. 距离：
     d_i^+ = sqrt( ∑_j (V_{ij} - V_j^+)^2 )
     d_i^- = sqrt( ∑_j (V_{ij} - V_j^-)^2 )
4. 相对接近度：C_i = d_i^- / (d_i^+ + d_i^-)
5. 按 C_i 降序排序
```

### 常见坑

- 不区分效益型 / 成本型指标 → 必须分别处理（见通用预处理）。
- 指标尺度悬殊 → 必须先归一化。
- 与 PCA 联用顺序错 → 一般先 PCA 降维再 TOPSIS。
- 仅用最近邻一项 d^+ 排序 → 错（TOPSIS 必须正负理想解都用）。

### Python 入口

```python
import numpy as np

def topsis(X: np.ndarray, w: np.ndarray, benefit: list[bool]) -> np.ndarray:
    """X: n×m 原始指标矩阵；w: m 维权重；benefit[j]=True 表示效益型"""
    # 1. 方向化（成本型取负，便于统一）
    Xd = np.where(np.array(benefit), X, X.max(axis=0) - X)
    # 2. 向量归一化
    Z = Xd / np.sqrt((Xd ** 2).sum(axis=0))
    # 3. 加权
    V = Z * w
    # 4. 理想解
    Vp = V.max(axis=0); Vn = V.min(axis=0)
    # 5. 距离
    dp = np.sqrt(((V - Vp) ** 2).sum(axis=1))
    dn = np.sqrt(((V - Vn) ** 2).sum(axis=1))
    # 6. 相对接近度
    return dn / (dp + dn + 1e-12)

# 用法
X = np.array([[80, 0.4], [70, 0.3], [90, 0.5]])  # 3 方案 × 2 指标
w = np.array([0.6, 0.4])
benefit = [True, False]  # 第 1 个是效益型，第 2 个是成本型
C = topsis(X, w, benefit)
print(f"排序: {np.argsort(-C) + 1}, 接近度: {C}")
```

可用库：`scikit-criteria`、`pymcdm`。

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Hwang, C.L. & Yoon, K. | Multiple Attribute Decision Making | Springer-Verlag | 1981 |
| Behzadian, M. et al. | A state-of the-art survey of TOPSIS applications | Expert Systems with Applications | 2012 |

---

## 4. 模糊综合评价

### 何时选

指标含模糊语义（"好 / 较好 / 一般 / 差"），无法直接量化。

### 核心思路

```
1. 因素集 U = {u_1, ..., u_m}；评语集 V = {v_1, ..., v_p}
2. 隶属度矩阵 R = [r_{ij}]_{m×p}，r_{ij} 表示因素 i 对评语 j 的隶属度
3. 权重 W = (w_1, ..., w_m)
4. 综合评价 B = W ∘ R（模糊合成算子，常用 max-min 或 加权和）
5. 按 B 中最大值或加权得分排序
```

### 隶属函数选型

| 形状 | 适用 | 典型公式 |
|---|---|---|
| 三角 | 简单、对称 | $\mu(x) = \max(0, 1 - \|x - c\|/d)$ |
| 梯形 | 区间型 | 在 $[a,b]$ 内为 1，两侧线性下降 |
| 高斯 | 平滑、长尾 | $\mu(x) = \exp(-(x-c)^2 / 2\sigma^2)$ |

### 常见坑

- 隶属函数选择主观 → 论文中需要写依据（专家德尔菲 / 数据拟合）。
- 多级评价矩阵维度爆炸 → 用层次模糊综合评价。

### Python 入口

```python
import numpy as np

def fuzzy_eval(W: np.ndarray, R: np.ndarray, op: str = 'weighted') -> np.ndarray:
    """W: m 维权重；R: m×p 隶属度矩阵；op ∈ {'max-min', 'weighted'}"""
    if op == 'weighted':
        return W @ R
    # max-min
    return np.array([np.max(np.minimum(W, R[:, j])) for j in range(R.shape[1])])
```

可用库：`scikit-fuzzy`。

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Zadeh, L.A. | Fuzzy sets | Information and Control | 1965 |
| 谢季坚, 刘承平 | 模糊数学方法及其应用 | 华中科技大学出版社 | 2006 |

---

## 5. 灰色关联分析（GRA, Deng 1982）

### 何时选

样本少（< 30）、指标多、想看哪些因素和母序列最相关。

### 核心思路

```
1. 选参考序列 X_0（理想 / 标杆 / 最优）
2. 比较序列 X_i (i=1..n)
3. 无量纲化：均值化 / 初值化 / 极差化
4. 关联系数：
     ξ_i(k) = (Δ_min + ρ Δ_max) / (Δ_i(k) + ρ Δ_max)
   其中 Δ_i(k) = |X_0(k) - X_i(k)|，ρ 为分辨系数（默认 0.5）
5. 关联度：γ_i = (1/N) ∑_k ξ_i(k)
```

### 关键参数

- **分辨系数 ρ**：默认 0.5；论文应做敏感性。
- **无量纲化方式**：均值化对均值敏感、极差化对极值敏感。

### 常见坑

- 不做无量纲化 → 量纲影响关联度。
- ρ 取值争议 → 写明并做敏感性。

### Python 入口

```python
import numpy as np

def grey_relation(X0: np.ndarray, X: np.ndarray, rho: float = 0.5) -> np.ndarray:
    """X0: 参考序列 (k,)；X: 比较序列 (n, k)"""
    # 均值化
    X0n = X0 / X0.mean()
    Xn = X / X.mean(axis=1, keepdims=True)
    diff = np.abs(X0n - Xn)
    dmin, dmax = diff.min(), diff.max()
    xi = (dmin + rho * dmax) / (diff + rho * dmax)
    return xi.mean(axis=1)
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| 邓聚龙 | 灰色系统基本方法 | 华中工学院出版社 | 1987 |
| 刘思峰等 | 灰色系统理论及其应用 | 科学出版社 | 2017 |

---

## 6. PCA-TOPSIS

### 何时选

指标多且高度相关，单纯 TOPSIS 受共线性影响。

### 核心思路

```
1. PCA 提取主成分（解释方差累计 ≥ 85%）
2. 主成分作为新指标矩阵
3. 主成分方差贡献率作为权重
4. 喂入 TOPSIS
```

### 常见坑

- 主成分对应物理含义难解释 → 论文里要花笔墨翻译回原指标。
- 解释方差 < 80% 时仍用主成分 → 信息损失大。

### Python 入口

```python
from sklearn.decomposition import PCA
import numpy as np

def pca_topsis(X: np.ndarray, var_threshold: float = 0.85):
    pca = PCA(n_components=var_threshold)
    Z = pca.fit_transform(X)
    w = pca.explained_variance_ratio_ / pca.explained_variance_ratio_.sum()
    benefit = [True] * Z.shape[1]
    return topsis(Z, w, benefit)
```

---

## 7. 数据包络分析（DEA, Charnes & Cooper 1978）

### 何时选

多输入多输出，比较"效率"，无明确权重。

### 核心思路（CCR 模型）

对每个 DMU $k$ 求解：

$$
\max \theta_k = \frac{\sum_r u_r y_{rk}}{\sum_i v_i x_{ik}} \quad
\text{s.t.} \; \frac{\sum_r u_r y_{rj}}{\sum_i v_i x_{ij}} \le 1, \forall j
$$

Charnes-Cooper 变换为 LP；BCC 模型加规模可变性约束。

### 关键参数

- 规模收益（CRS / VRS）。
- DMU 数量 ≥ 3 × (输入数 + 输出数)。

### 常见坑

- 输入输出方向不一致（输入越小越好，输出越大越好） → 必须保证。
- 异常值会扭曲前沿 → 先剔除离群点。

### Python 入口

```python
import pulp

def dea_ccr(X: np.ndarray, Y: np.ndarray) -> list[float]:
    """X: n×m 输入；Y: n×s 输出。返回每个 DMU 的效率分数"""
    n, m = X.shape; _, s = Y.shape
    eff = []
    for k in range(n):
        prob = pulp.LpProblem(f"dea_{k}", pulp.LpMaximize)
        u = [pulp.LpVariable(f"u_{r}", lowBound=0) for r in range(s)]
        v = [pulp.LpVariable(f"v_{i}", lowBound=0) for i in range(m)]
        prob += pulp.lpSum(u[r] * Y[k, r] for r in range(s))
        prob += pulp.lpSum(v[i] * X[k, i] for i in range(m)) == 1
        for j in range(n):
            prob += pulp.lpSum(u[r] * Y[j, r] for r in range(s)) <= \
                    pulp.lpSum(v[i] * X[j, i] for i in range(m))
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        eff.append(pulp.value(prob.objective))
    return eff
```

可用库：`pulp` + 自建 LP；`pyDEA`。

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Charnes, A.; Cooper, W.W. | Measuring the efficiency of decision making units | EJOR | 1978 |
| Banker, R.D.; Charnes, A.; Cooper, W.W. | Some models for estimating technical and scale inefficiencies | Management Science | 1984 |

---

## 高分组合方案

| 场景 | 组合 | 实施要点 |
|---|---|---|
| 主客观结合定权 | AHP + 熵权 | 取算术或几何平均；做 α 敏感性 |
| 评价 + 排序 | (AHP + 熵权) + TOPSIS | 先组合权重再 TOPSIS |
| 高相关性指标 | PCA → TOPSIS | PCA 解释方差 ≥ 85% |
| 不同领域专家分歧 | 模糊德尔菲 → AHP | 先模糊化达成专家共识 |
| 效率评估 | DEA + 灰色关联 | DEA 算效率；GRA 验证稳定性 |
| 小样本评价 | GRA + AHP | 数据 < 30 时优先 |

## 选型对照表

| 需求 | 首选 | 备选 |
|---|---|---|
| 仅定权重（主观） | AHP | 群组 AHP |
| 仅定权重（客观） | 熵权法 | 标准差法 / CV 法 |
| 方案排序 | TOPSIS | VIKOR |
| 模糊语义评价 | 模糊综合评价 | 模糊 TOPSIS |
| 高相关指标排序 | PCA-TOPSIS | 因子分析 + TOPSIS |
| 效率评价 | DEA | SFA（随机前沿） |
| 因素相关分析（小样本） | GRA | Spearman 相关 |

## 可视化建议

| 步骤 | 推荐图 |
|---|---|
| 权重构成 | 水平条形图（横向更宽） |
| 方案排序 | 水平条形图 + 标注接近度数值 |
| 敏感性 | 折线图 + 阴影置信带（参数 ±20%） |
| 主成分 | 累计方差碎石图 + biplot |
| 模糊隶属度 | 雷达图（每个方案一条线） |
| 关联度 | 热力图（方案 × 指标） |
| DEA 前沿 | 散点图 + 前沿曲线 |

## 常见全栈错误

| ❌ 错误 | ✅ 正确 |
|---|---|
| 直接对原始矩阵 TOPSIS | 先方向化 + 归一化 |
| 单方法（仅 AHP）出排序 | AHP 定权 + TOPSIS / VIKOR 排序 |
| 不做 CR 检验直接用 AHP 权重 | CR < 0.1 才采用，否则修正判断矩阵 |
| 熵权法不预处理就跑 | 先方向化 + 归一化 |
| 评价后不做敏感性 | 权重 ±20% 看排序变化 |
