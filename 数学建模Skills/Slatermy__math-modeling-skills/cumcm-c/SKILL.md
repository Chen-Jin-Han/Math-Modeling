---
name: cumcm-c
description: 数学建模国赛 C 题（数据分析/统计/机器学习/评价/优化决策）解题方法。当题目给大量数据表，需要描述统计、相关分析、回归、分类、聚类、时间序列预测、评价排序（AHP/TOPSIS/熵权）、特征工程、模型评估，或含不确定性的优化决策时使用。核心流程：数据理解清洗 → EDA → 结构识别 → 建模求解 → 决策优化 → 稳健性分析。内含 2025 NIPT 完整案例与实战坑位。
---

# 数模国赛 C 题：数据分析 / 统计 / 机器学习 / 优化决策

C 题近年以**数据驱动**为主，但注意边界会变：**2024 C 题（农作物种植策略）实为优化+不确定性**，2025 C 题（NIPT）是统计+分类。所以 C 题要同时掌握：数据清洗、EDA、回归/分类/聚类/时序、评价模型、以及含不确定性的优化决策（可借 `cumcm-b` 的方法）。

---

## 一、通用解题流程（6 步）

1. **数据理解**：读题 + 数据字典，搞清每张表/字段含义；明确目标 Y 与特征 X
2. **数据清洗**：缺失、异常、类型转换、编码、标准化
3. **EDA 探索**：描述统计 + 可视化（分布/相关/趋势/组间差异）
4. **结构识别 + 建模**：按问题类型选模型，**先变量筛选/特征选择**
5. **求解 + 决策/优化**：预测/分类结果，或代入优化模型做决策
6. **稳健性分析**：交叉验证、Bootstrap、敏感性、方法对比

> 铁律：先拆问题再建模，禁止"看到数据先跑十个算法"。每问拆成：研究对象/输入/输出/困难/约束/指标/与上一问继承关系。

---

## 二、数据预处理

```python
import pandas as pd, numpy as np
df = pd.read_excel("xxx.xlsx", sheet_name="xxx")

df.isna().sum()                       # 缺失分布
df.dropna(subset=["Y"])               # 目标缺失删行
df["col"] = df["col"].fillna(df["col"].median())   # 特征缺失填中位数

def to_num(x):                        # 文本混数字(如 '≥3')
    if pd.isna(x): return np.nan
    if isinstance(x, (int, float)): return float(x)
    d = "".join(c for c in str(x) if c.isdigit())
    return float(d) if d else np.nan

df["cat"] = df["cat"].astype("category").cat.codes
from sklearn.preprocessing import StandardScaler
```

**变量类型决定方法**：连续↔连续用 Pearson；定类/计数/非正态用 **Spearman**；定类差异性用**卡方检验**。

---

## 三、模型速查（按问题类型选）

| 问题类型 | 首选 | 备选 |
|---|---|---|
| 描述画像 | 描述统计+可视化+聚类 | K-means、层次聚类 |
| 相关/关系 | Pearson/Spearman、多元回归 | 岭回归、LASSO |
| 关系建模(非线性/交互/重复测量) | 多项式回归、线性混合效应 | XGBoost 回归 |
| 分类判别 | 逻辑回归(可解释)、随机森林 | XGBoost、SVM、决策树 |
| 时间序列预测 | ARIMA、指数平滑 | 灰色预测、LSTM、Prophet |
| 评价排序 | AHP、TOPSIS、熵权法 | 模糊综合评价、CRITIC |
| 降维 | PCA | LDA |
| 决策优化(含不确定性) | 动态规划、LP/MIP、随机规划 | 遗传算法、蒙特卡洛模拟 |

优先级：解释力 > 可复现性 > 精度 > 新颖度。**基础方法出瓶颈再上复杂模型。**

---

## 四、核心模型完整代码

### 1. 相关分析
```python
from scipy.stats import pearsonr, spearmanr, chi2_contingency
r, p = spearmanr(df["a"], df["b"])   # 秩相关
r, p = pearsonr(df["x"], df["y"])    # 线性相关
chi2, p, *_ = chi2_contingency(pd.crosstab(df["c1"], df["c2"]))
```

### 2. 线性混合效应模型（重复测量/分组数据，C 题高频）
```python
from statsmodels.regression.mixed_linear_model import MixedLM
res = MixedLM.from_formula(
    "Y ~ x1 + I(x1**2) + x2", data=df, groups=df["个体代码"], re_formula="1"
).fit(method="bfgs", maxiter=3000)
print(res.summary())   # 系数、p值、方差分量、ICC
```
何时用：同一对象多次测量时，普通回归会低估标准误、误判显著性，必须加随机截距。

### 3. 逻辑回归（分类，可解释首选）
```python
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
clf = Pipeline([("s", StandardScaler()),
                ("c", LogisticRegression(max_iter=2000, class_weight="balanced"))])
clf.fit(X, y); p = clf.predict_proba(X_test)[:, 1]
```

### 4. 随机森林 / XGBoost / SVM（精度更高，做对比）
```python
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.svm import SVC
rf = RandomForestClassifier(n_estimators=500, class_weight="balanced", random_state=42)
xgb = XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.05,
                    scale_pos_weight=(y==0).sum()/y.sum(), random_state=42)  # 不平衡权重
svm = SVC(kernel="rbf", probability=True, class_weight="balanced")
```

### 5. 聚类
```python
from sklearn.cluster import KMeans
from scipy.cluster.hierarchy import dendrogram, linkage
kmeans = KMeans(n_clusters=k, random_state=42).fit(X_scaled)
# 选 k：肘部法(惯性下降拐点) 或 轮廓系数 silhouette_score
```

### 6. 时间序列
```python
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller   # 平稳性 ADF 检验
model = ARIMA(series, order=(p, d, q)).fit()
forecast = model.forecast(steps=n)
```
灰色预测 GM(1,1)（小样本、贫信息）：
```python
def gm11(x0, n_pred=1):
    x0 = np.array(x0, float); x1 = x0.cumsum()
    z1 = 0.5*(x1[1:] + x1[:-1])
    B = np.column_stack([-z1, np.ones_like(z1)]); Y = x0[1:]
    a, b = np.linalg.lstsq(B, Y, rcond=None)[0]
    x1_hat = [(x0[0]-b/a)*np.exp(-a*k)+b/a for k in range(len(x0)+n_pred)]
    return np.diff(np.array([0.0]+x1_hat))   # 还原得到预测
```

### 7. 降维 PCA
```python
from sklearn.decomposition import PCA
pca = PCA(n_components=0.95)   # 保留 95% 方差
X_pca = pca.fit_transform(X_scaled)
```

---

## 五、评价模型（AHP / TOPSIS / 熵权法）完整代码

### 层次分析法 AHP（主观权重）
```python
import numpy as np
def ahp(A):
    """A 为成对比较判断矩阵(正互反)，返回权重 w + 一致性比率 CR(需<0.1)"""
    n = A.shape[0]
    vals, vecs = np.linalg.eig(A)
    idx = vals.real.argmax(); max_eig = vals.real[idx]
    w = np.abs(vecs[:, idx].real); w /= w.sum()
    RI = {1:0,2:0,3:0.58,4:0.90,5:1.12,6:1.24,7:1.32,8:1.41,9:1.45}
    CR = ((max_eig-n)/(n-1)) / RI[n]
    return w, CR
# 用法：判断矩阵用 1~9 标度(1同等,3稍重要,5明显,7强烈,9极端)，CR<0.1 才通过
```

### 熵权法（客观权重，由数据离散度定权）
```python
def entropy_weight(X):
    X = np.array(X, float)
    Xn = (X - X.min(0)) / (X.max(0) - X.min(0) + 1e-12)   # 正向归一化
    P = Xn / Xn.sum(0); P = np.where(P == 0, 1e-12, P)
    e = -(P*np.log(P)).sum(0) / np.log(len(X))            # 熵值
    d = 1 - e                                             # 差异系数
    return d / d.sum()
```

### TOPSIS（逼近理想解排序，常与熵权法结合）
```python
def topsis(X, w=None, benefit=None):
    """X: m方案×n指标; w: 权重; benefit: 各指标是否越大越好(正向)"""
    X = np.array(X, float)
    if w is None: w = np.ones(X.shape[1])
    if benefit is None: benefit = np.ones(X.shape[1], bool)
    for j in range(X.shape[1]):
        if not benefit[j]: X[:, j] = X[:, j].max() - X[:, j]   # 负向指标正向化
    Z = X / np.sqrt((X**2).sum(0)) * w
    best, worst = Z.max(0), Z.min(0)
    d_b = np.sqrt(((Z-best)**2).sum(1)); d_w = np.sqrt(((Z-worst)**2).sum(1))
    return d_w / (d_b + d_w)    # 贴近度，越大越优
```

---

## 六、模型评估（必做，得分点）

```python
from sklearn.model_selection import cross_val_score, GroupKFold, KFold
from sklearn.metrics import (roc_auc_score, confusion_matrix, f1_score,
                             r2_score, mean_squared_error)

# 回归
r2 = r2_score(y, yhat); rmse = np.sqrt(mean_squared_error(y, yhat))

# 分类（不平衡务必看 AUC/灵敏度/特异度，别只看准确率）
auc = roc_auc_score(y, proba)
tn, fp, fn, tp = confusion_matrix(y, yhat).ravel()
sens = tp/(tp+fn); spec = tn/(tn+fp); f1 = f1_score(y, yhat)
```

**Bootstrap 置信区间**（稳健性加分项）：
```python
rng = np.random.default_rng(42)
stats = []
for _ in range(1000):
    idx = rng.integers(0, len(y), len(y))   # 有放回重采样
    stats.append(roc_auc_score(y[idx], proba[idx]))
print(f"AUC 95%CI: [{np.percentile(stats, 2.5):.3f}, {np.percentile(stats, 97.5):.3f}]")
```

**关键点**：
- 重复测量/分组数据用 **GroupKFold**（按个体分组）防泄漏
- 不平衡：`class_weight="balanced"` / XGBoost `scale_pos_weight`，看 AUC/F1 而非 accuracy

---

## 七、特征工程与变量筛选（拉开差距的关键）

1. **单变量判别力排序**：各特征与 Y 的相关系数 / 单特征 AUC 从高到低
2. **共线性检查**：两两相关热力图（|r|>0.7 警惕，如体重 vs BMI 留一个）
3. **前向/后向选择**：从最强特征出发，逐个加入能显著提升 AUC 的
4. **坑**：特征不是越多越好——噪音特征拖累模型。2025 C 题全 17 特征 AUC=0.762，前向筛到 5 个升到 0.815。

---

## 八、端到端 pipeline 模板（C 题通用骨架）

```python
# 1 数据
df = pd.read_excel("数据.xlsx", sheet_name="sheet")
# 2 清洗（缺失/类型/编码）
# 3 EDA：df.describe()、df.corr()、热力图、组间均值对比
# 4 变量筛选（Spearman 相关矩阵 + 前向选择）
# 5 建模 + GroupKFold 评估（AUC/RMSE + Bootstrap 置信区间）
# 6 敏感性分析（关键参数扰动 / 方法对比）
# 7 出图（调用 dataviz skill）+ 结论表
```

---

## 九、近年 C 题案例

### 2025 NIPT（时点选择与胎儿异常判定）——本 skill 家族实战案例
- **问题一** Y浓度 vs 孕周关系：线性混合效应模型（随机截距），孕周_c + 孕周_c² + BMI_c + 年龄_c + 身高_c；ICC≈0.74 说明必须用随机效应
- **问题二** BMI 分组最佳时点：动态规划 `dp[k][j]=min_i dp[k-1][i]+(j-i)·R(t*)`，达标概率用正态 CDF
- **问题三** 多因素+检测误差：变量筛选先行（Spearman 热力图，剔除怀孕/生产次数、体重）；误差传播 σ_total²=σ_u²+σ²+σ_err²
- **问题四** 女胎异常判定：关键发现——单个染色体 Z 值几乎不区分（对应 Z 值 |Z|>3 命中 0/64），必须多特征分类；最强特征 X染色体浓度；逻辑回归+前向选择 5 特征 AUC=0.815
- **共同坑**：辛普森悖论（重复测量反转相关方向）、特征堆砌、不平衡看 AUC 不看 accuracy、GroupKFold 防泄漏

### 2024 农作物种植策略（优化+不确定性）
- 以利润最大化为目标，线性/整数规划；约束含地块、轮作（避免重茬）、销售量
- 不确定性（价格、气候）用**蒙特卡洛模拟 / 随机规划**
- 作物互补替代用相关性/协整分析；求解可用遗传算法（多矩阵染色体编码）

### 2023 蔬菜定价补货（完整数据 pipeline，逐问拆解）
- **问题1** 销量分布+关联：描述统计（饼图/箱线图/直方图，销量右偏长尾）+ 皮尔逊相关 + Apriori 关联规则
- **问题2** 定价关系+预测：岭回归（解决共线）+ 需求价格弹性 (ΔQ/Q)/(ΔP/P) + ARIMA 预测 7 天销量/售价/成本
- **问题3** 补货+自动定价：遗传算法（决策变量=补货量+售价，收益为适应度，ARIMA 预测值初始化）
- **问题4** 数据收集因素：AHP（季节性/趋势/天气/节假日/竞争/供应链），一致性检验 CR<0.1
- **主线**：描述 → 关系 → 预测 → 决策 → 评价，体现"预测→决策"衔接

### 2022 玻璃成分鉴别（定类变量 + 分类聚类，逐问拆解）
- **问题1** 成分分布+风化关系：描述统计 + 卡方检验（风化 vs 类型/颜色等定类变量）
- **问题2** 类型分类：逻辑回归/决策树/SVM（可解释优先），先特征筛选再分类，混淆矩阵+交叉验证评估
- **问题3** 亚类划分：K-means/层次聚类，每类单独聚类，标准化后聚类，肘部法/轮廓系数定 k
- **问题4** 敏感性+关联：调参数看稳定性 + 成分间皮尔逊相关矩阵
- **主线**：**定类变量用卡方/斯皮尔曼，不能用皮尔逊**（高频扣分点）

---

## 十、不确定性建模（蒙特卡洛 + 随机规划）

C 题高频考点：价格、销量、需求、气候、次品率等存在**随机性**。两大招：**蒙特卡洛模拟（MC）** 与 **随机规划（SP）**。

### 1. 蒙特卡洛模拟（MC）
思想：随机抽样估计期望/概率/分布，代替解析积分。三步：定义输入分布 → 抽样 → 统计输出。

```python
import numpy as np
rng = np.random.default_rng(42)

# (a) 估计期望/概率（含置信区间）
def f(x): return np.sqrt(np.maximum(x, 0))
n = 100000
x = rng.normal(0, 1, n)
est = f(x).mean(); se = f(x).std(ddof=1)/np.sqrt(n)
print(f"E[f(X)] = {est:.4f}  (95%CI {est-1.96*se:.4f} ~ {est+1.96*se:.4f})")

# (b) 利润/风险模拟（输入有分布 → 输出是分布）
def sim_profit(p_mu, p_sd, d_mu, d_sd, unit_cost, fixed_cost, n=100000):
    price = rng.normal(p_mu, p_sd, n); demand = rng.normal(d_mu, d_sd, n)
    return (price - unit_cost) * demand - fixed_cost
p = sim_profit(5, 1, 1000, 200, 2, 500)
print(f"期望利润 {p.mean():.1f} | 亏损概率 {(p<0).mean():.1%} | 5%分位(VaR) {np.percentile(p,5):.1f}")
```
> **输出要报告分布**（均值、分位数、亏损概率、置信区间），不是单点估计。这比"单参数±10%"式的敏感性分析更贴近真实不确定性。

**不确定性传播（敏感性分析的随机版）**：输入参数各自服从分布 → 抽样 → 输出分布 → 判断结论稳健性。适合回答"价格和气候同时波动时，最优种植策略会不会翻车"这类问题。

### 2. 随机规划（SP）
面对随机量 ξ，三种模型：

| 模型 | 形式 | 适用 |
|---|---|---|
| 期望值模型 | min E[f(x,ξ)] | 长期平均最优 |
| 机会约束 | P(g(x,ξ)≤0) ≥ α | 约束高概率满足 |
| 两阶段 | min c'x + E[Q(x,ξ)] | 先定 x，见 ξ 后补救 |

**期望值模型 + 样本平均近似（SAA）**：
```python
from scipy.optimize import minimize
scenarios = rng.normal(5, 1, 1000)        # N 个场景近似随机量
def f(x, xi): return (x - xi)**2 + 0.1*x**2
def saa(x): return np.mean([f(x, s) for s in scenarios])
res = minimize(saa, x0=0, method="BFGS")
print(f"x* = {res.x[0]:.3f}, 期望目标 {res.fun:.3f}")
```

**两阶段（报童问题特例）**：
```python
def two_stage(x, scenarios, c0, cu, co):
    cost = c0 * x
    for s in scenarios:
        cost += (cu*(s-x) if s > x else co*(x-s))   # 缺货/积压
    return cost / len(scenarios)
# 搜索 x 使期望两阶段成本最小
```

### 3. 模拟优化（仿真 + 优化结合）
解析目标写不出时，对每个候选决策做 MC 仿真求期望再搜索最优。典型：2024 C 农作物种植（遗传算法 + MC 评风险）、2020 B 沙漠游戏（DP + 蒙特卡洛）。

---

## 十一、常见坑位（实战总结）

1. 变量类型搞错（定类用 Pearson）
2. 重复测量没处理，直接普通回归
3. 特征堆砌（17 特征不如 5 个精选）
4. 不平衡只看准确率
5. 交叉验证泄漏（分组数据没按组拆）
6. 共线变量都留（体重+BMI）
7. 只画图不给数值、不做显著性、不做敏感性
8. 辛普森悖论：相关方向被重复测量反转
9. AHP 判断矩阵不做一致性检验（CR≥0.1 还硬用）
10. 评价指标方向搞反（负向指标没正向化）

---

## 十二、离线自足提示

numpy/scipy/pandas/sklearn/statsmodels/matplotlib 覆盖 95% 需求。XGBoost 若未装可用 `pip install xgboost`（比赛前装好）。遇到问题对照本 skill 模型速查表选方法，代码模板改字段名即用。

---

## 十三、模型选择决策规则（借鉴补充）

> 方法论思路借鉴自 [skillforCUMCM/math-modeling-skill-pro](https://github.com/skillforCUMCM/math-modeling-skill-pro)（专有许可，仅借鉴通用建模方法论思路，已重写），结合数据题特点整理。

1. **小样本不碰深度学习**：样本量远小于特征数时，深度网络/Transformer 只会过拟合；先用线性/广义线性/树模型。
2. **不无脑堆评价模型**：AHP+熵权+CRITIC+PCA+TOPSIS 一起上而没有各自独立角色，是典型堆砌。先想清每个模型解决什么，重复的删掉。
3. **相关性 ≠ 因果**：相关热图/回归系数只能支持"关联"，不能直接写成"导致/影响"的因果结论，除非有识别假设。
4. **分类不平衡看 PR-AUC/召回/特异度**，不是 accuracy。
5. **预测进优化/评价时传播不确定性**：传分位数/情景集，不只传点预测，否则下游决策不可信。
6. **三方案对照**：A=朴素/线性/等权（基线），B=树模型+SHAP/完整特征筛选（主力），C=混合效应/随机约束/机理-数据混合等创新（有消融才上）。

**验证要点**（数据题）：先定切分和指标再训练（防选择偏差）；时间序列用滚动窗不随机打乱；分组数据用 GroupKFold；候选多时用嵌套验证；报基线对比 + 置信区间 + 误差/失败情景。
