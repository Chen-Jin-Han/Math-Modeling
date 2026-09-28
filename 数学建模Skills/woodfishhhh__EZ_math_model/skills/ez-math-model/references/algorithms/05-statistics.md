# 05 统计分析与数据处理

> EDA / 假设检验 / 相关性 / 聚类 / 降维 / 因子分析的"教材级"参考。

## 概述

统计分析是建模题的"侦察兵"：在选模型之前先**看清数据**。流程：

```
原始数据
   ↓ 1. 描述性统计（位置、离散、形状）
   ↓ 2. 缺失值 + 异常值处理
   ↓ 3. 分布检验 + 相关性 + 协方差
   ↓ 4. 假设检验（差异 / 独立 / 拟合优度）
   ↓ 5. 聚类 / 降维 / 主题提取
   ↓ 6. 可视化（直方 / 箱线 / 散点 / 热力 / Q-Q）
```

## 1. 描述性统计

### 位置度量

| 量 | 公式 | 适用 |
|---|---|---|
| 均值 | $\bar x = \frac{1}{n} \sum x_i$ | 近正态分布 |
| 中位数 | 排序后中间值 | 对异常值鲁棒 |
| 众数 | 出现频率最高 | 离散 / 类别 |
| 几何均值 | $(\prod x_i)^{1/n}$ | 比率 / 增长率 |
| 调和均值 | $n / \sum (1/x_i)$ | 速率 / 比率倒数 |

### 离散度量

| 量 | 公式 | 适用 |
|---|---|---|
| 方差 | $s^2 = \frac{1}{n-1} \sum (x_i - \bar x)^2$ | 通用 |
| 标准差 | $s = \sqrt{s^2}$ | 与原数据同量纲 |
| 变异系数 | $\text{CV} = s / \bar x$ | 跨样本可比 |
| IQR | $Q_3 - Q_1$ | 鲁棒离散度 |
| MAD | $\text{med}(\|x_i - \text{med}\|)$ | 鲁棒离散度 |

### 形状度量

- **偏度** $\gamma_1 = \frac{1}{n} \sum (x_i - \bar x)^3 / s^3$：
  $> 0$ 右偏，$< 0$ 左偏，$\approx 0$ 对称。
- **峰度** $\gamma_2 = \frac{1}{n} \sum (x_i - \bar x)^4 / s^4 - 3$：
  $> 0$ 尖峰，$< 0$ 平峰。

### Python 入口

```python
import pandas as pd
df.describe(percentiles=[.05, .25, .5, .75, .95])
print(df.skew(), df.kurt())
```

---

## 2. 缺失值处理

### 缺失机制（必须先判断）

| 机制 | 含义 | 处理 |
|---|---|---|
| MCAR（Missing Completely at Random） | 缺失与任何变量都无关 | 删除 / 简单填充都可 |
| MAR（Missing at Random） | 缺失只与已观测变量有关 | 多重插补 / 模型预测填充 |
| MNAR（Missing Not at Random） | 缺失与未观测变量有关 | 必须建模缺失机制（最难） |

**判定**：用 Little's MCAR test 或对比"缺失行 vs 完整行"在其他变量上的分布。

### 处理策略

| 缺失率 | 推荐 | 备注 |
|---|---|---|
| < 5% | 删除该行 / 中位数 / 众数 | 快速 |
| 5%-30% | KNN 填充 / 多重插补（MICE） | 平衡 |
| > 30% | 删字段 / 加缺失指示位 | 保留信息 |
| 时序 | 前向填充 / 线性插值 / Kalman 滤波 | 时间相关 |

### 填充实现

```python
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer  # MICE

# 中位数（鲁棒）
imp = SimpleImputer(strategy='median')

# KNN（适合中等缺失）
imp = KNNImputer(n_neighbors=5)

# MICE（最强）
imp = IterativeImputer(max_iter=10, random_state=42)

# 关键纪律：fit only on train
imp.fit(X_train)
X_train_imp = imp.transform(X_train)
X_test_imp = imp.transform(X_test)
```

### 常见坑

- 在切分前填充 → **数据泄露**。
- 用全局均值填，再做特征工程 → 仍然泄露。

---

## 3. 异常值检测

### 单变量

| 方法 | 阈值 | 适用 |
|---|---|---|
| IQR | 在 $[Q_1 - 1.5 \cdot IQR, Q_3 + 1.5 \cdot IQR]$ 外 | 鲁棒、通用 |
| Z-score | $\|z\| > 3$ | 近正态 |
| Modified Z-score | $\|0.6745 (x - \text{med}) / \text{MAD}\| > 3.5$ | 异常值多时 |

### 多变量

| 方法 | 思路 | 适用 |
|---|---|---|
| Isolation Forest | 随机划分树，异常点路径短 | 高维、大样本 |
| Local Outlier Factor | 局部密度比 | 局部异常 |
| One-Class SVM | 学正常样本的边界 | 小样本 |
| 马氏距离 | 协方差归一化 | 多元正态 |

### Python 入口

```python
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

iso = IsolationForest(contamination=0.05, random_state=42)
labels = iso.fit_predict(X)  # 1 正常 / -1 异常

lof = LocalOutlierFactor(n_neighbors=20)
labels = lof.fit_predict(X)
```

### 重要提醒

**物理常量题**：题目给的是确定参数（H=200mm 等），**不要**做"异常值清洗"。
评委会扣模板化分。

---

## 4. 假设检验

### 决策树

```
比较 1 个均值与定值
  数据正态 → 单样本 t 检验
  否则 → Wilcoxon 符号秩检验

比较 2 个均值
  独立样本：
    正态 + 方差齐 → 独立 t
    正态 + 方差不齐 → Welch t
    非正态 → Mann-Whitney U
  配对样本：
    正态 → 配对 t
    非正态 → Wilcoxon 符号秩

比较多组均值
  正态 + 方差齐 → 单因素 ANOVA
  正态 + 方差不齐 → Welch ANOVA
  非正态 → Kruskal-Wallis

方差齐性
  Levene / Bartlett

正态性
  n < 50 → Shapiro-Wilk
  n 大 → Kolmogorov-Smirnov

独立性（两个分类变量）
  期望频数 ≥ 5 → 卡方检验
  否则 → Fisher 精确检验
```

### Python 入口

```python
from scipy import stats

# 单样本 t
stats.ttest_1samp(x, popmean=100)

# 独立 t
stats.ttest_ind(a, b, equal_var=False)  # Welch

# 配对 t
stats.ttest_rel(before, after)

# Mann-Whitney
stats.mannwhitneyu(a, b)

# 单因素 ANOVA
stats.f_oneway(g1, g2, g3)

# Levene 方差齐
stats.levene(g1, g2, g3)

# Shapiro-Wilk 正态性
stats.shapiro(x)

# 卡方独立
stats.chi2_contingency(table)
```

### 多重比较校正

| 方法 | 控制 | 保守程度 |
|---|---|---|
| Bonferroni | FWER | 最保守 |
| Holm | FWER | 中等 |
| Benjamini-Hochberg（FDR） | FDR | 最宽松 |

```python
from statsmodels.stats.multitest import multipletests
rejected, p_corrected, _, _ = multipletests(p_values, alpha=0.05, method='fdr_bh')
```

### 常见坑

- 多次比较未校正 → 假阳性爆炸（5 次比较，至少 1 次错的概率 ~23%）。
- 大样本下 $p$ 值天然显著 → 报告**效应量**（Cohen's d / r²）。
- 把 $p$ 当效应大小 → 错。

---

## 5. 相关性分析

| 类型 | 算法 | 适用 |
|---|---|---|
| 线性 | Pearson $r$ | 双变量近正态 |
| 单调 | Spearman $\rho$ | 顺序关系 |
| 单调（基于秩） | Kendall $\tau$ | 小样本 |
| 类别 | Cramér's V | 列联表 |
| 控制变量后线性 | 偏相关 | 多变量 |

### Python 入口

```python
import scipy.stats as st
import pandas as pd

r, p = st.pearsonr(x, y)
rho, p = st.spearmanr(x, y)
tau, p = st.kendalltau(x, y)

# 相关矩阵 + 热力图
corr = df.corr(method='spearman')
import seaborn as sns
sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', center=0)
```

### 关键规则

**相关 ≠ 因果**。论文里要明确：
> While a strong correlation $(r = 0.85, p < 0.01)$ is observed, this does
> not establish causation. Alternative explanations include {confounder X}
> and {reverse causality}.

需要因果时用 DID / 工具变量 / RCT。

---

## 6. 聚类

### K-Means

**何时选**：大样本、簇近似球形、簇间方差相近。

**核心**：
$$
\min \sum_{k} \sum_{x \in C_k} \|x - \mu_k\|^2
$$

**关键参数**：
- `n_clusters` $k$：用肘部法 / 轮廓系数 / Gap statistic 选
- `n_init`：默认 10，多次随机初始化取最好

**坑**：
- 不标准化 → 高方差特征主导
- 离群值拉走质心 → 改用 K-Medoids
- $k$ 取值不写理由 → 论文必扣

```python
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# 肘部法 + 轮廓系数
inertias = []; silhouettes = []
for k in range(2, 11):
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    inertias.append(km.inertia_)
    silhouettes.append(silhouette_score(X, km.labels_))
```

### 层次聚类

**连接方式**：
- Single（最近邻）：链式效应
- Complete（最远邻）：紧凑簇
- Average：折中
- Ward：方差最小（**推荐**）

```python
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster

Z = linkage(X, method='ward')
dendrogram(Z, truncate_mode='lastp', p=20)
labels = fcluster(Z, t=5, criterion='maxclust')
```

### DBSCAN

**何时选**：簇形状不规则、需识别噪声、不预设 $k$。

**关键参数**：
- `eps`：邻域半径，用 k-distance plot 选
- `min_samples`：核心点的最小邻居数（默认 = $2 \cdot \dim$）

**坑**：高维"距离失效"；密度不均匀的簇难处理。

```python
from sklearn.cluster import DBSCAN
db = DBSCAN(eps=0.5, min_samples=5).fit(X)
# -1 表示噪声
```

### GMM（高斯混合）

**何时选**：簇近似椭圆、需软分配 / 概率。

```python
from sklearn.mixture import GaussianMixture
gmm = GaussianMixture(n_components=3, covariance_type='full').fit(X)
proba = gmm.predict_proba(X)
```

### 选型对照

| 数据特征 | 首选 |
|---|---|
| 大样本、球形 | K-Means |
| 中等样本、想看树状图 | 层次聚类（Ward） |
| 不规则形状、有噪声 | DBSCAN |
| 椭圆形、需概率 | GMM |
| 流式 / 大数据 | MiniBatchKMeans |

---

## 7. 降维

### PCA

**核心**：找方差最大的正交方向；前 $k$ 个主成分保留方差比例 ≥ 85%。

```python
from sklearn.decomposition import PCA
pca = PCA(n_components=0.95)  # 累计 95% 方差
Z = pca.fit_transform(X_scaled)
print(pca.explained_variance_ratio_)
```

**坑**：
- 不标准化 → 大量纲特征主导
- 用于树模型反而降效（树自带特征选择）
- 主成分对应的物理含义难解释 → 论文中要花笔墨翻译

### 因子分析

**何时**：背后有潜在因子，关心载荷的解释性。

**前置检查**：KMO（Kaiser-Meyer-Olkin） ≥ 0.6；Bartlett 检验 $p < 0.05$。

```python
from factor_analyzer import FactorAnalyzer, calculate_kmo, calculate_bartlett_sphericity
kmo_all, kmo_model = calculate_kmo(df)
chi_square, p_value = calculate_bartlett_sphericity(df)

fa = FactorAnalyzer(n_factors=3, rotation='varimax')
fa.fit(df)
loadings = fa.loadings_
```

### 典型相关分析（CCA）

**何时**：研究两组变量整体相关。

```python
from sklearn.cross_decomposition import CCA
cca = CCA(n_components=2)
X_c, Y_c = cca.fit_transform(X, Y)
```

### t-SNE / UMAP

**何时**：高维数据可视化（**仅可视化**，不做下游建模）。

| 算法 | 关键参数 | 备注 |
|---|---|---|
| t-SNE | `perplexity` 5-50 | 距离不可解释 |
| UMAP | `n_neighbors`、`min_dist` | 比 t-SNE 快、保全局结构 |

```python
from sklearn.manifold import TSNE
tsne = TSNE(n_components=2, perplexity=30, random_state=42)
Z = tsne.fit_transform(X)

import umap
um = umap.UMAP(n_neighbors=15, min_dist=0.1, random_state=42)
Z = um.fit_transform(X)
```

---

## 8. 非负矩阵分解（NMF）

### 何时

数据非负、希望分解出可解释的部分（主题、成分）。

**典型场景**：文本主题提取、图像分解、推荐系统。

$$
X \approx W H, \quad W, H \ge 0
$$

```python
from sklearn.decomposition import NMF
nmf = NMF(n_components=10, init='nndsvd', random_state=42)
W = nmf.fit_transform(X)
H = nmf.components_
```

LDA（Latent Dirichlet Allocation）是文本主题的概率模型版：

```python
from sklearn.decomposition import LatentDirichletAllocation
lda = LatentDirichletAllocation(n_components=10, random_state=42)
lda.fit(X_tfidf)
```

---

## 选型对照表

| 任务 | 首选 | 备选 |
|---|---|---|
| 缺失值少（<5%） | 中位数 / 众数 | 删除 |
| 缺失值中（5-30%） | KNN | MICE |
| 异常值（单变量） | IQR | Modified Z-score |
| 异常值（多变量） | Isolation Forest | LOF |
| 两组均值（正态） | t 检验 | - |
| 两组均值（非正态） | Mann-Whitney | - |
| 多组均值 | ANOVA | Kruskal-Wallis |
| 相关性 | Pearson / Spearman | Kendall |
| 大样本聚类 | K-Means | MiniBatchKMeans |
| 不规则聚类 | DBSCAN | OPTICS |
| 高维降维 | PCA | 因子分析 |
| 可视化降维 | UMAP | t-SNE |
| 主题提取 | NMF | LDA |

## 可视化建议

| 内容 | 推荐图 |
|---|---|
| 单变量分布 | 直方图 + KDE 曲线 |
| 单变量与众数 | 小提琴图 |
| 双变量关系 | 散点 + 回归线 + r 值 |
| 多变量相关 | 热力图（颜色 + 数值） |
| 缺失模式 | missingno 矩阵 / 条形图 |
| 聚类结果 | 散点（颜色 = 簇）+ 簇中心 |
| 降维结果 | t-SNE / UMAP 散点 |
| Q-Q 图 | scipy.stats.probplot |

## 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Tukey, J.W. | Exploratory Data Analysis | Addison-Wesley | 1977 |
| Pearson, K. | On lines and planes of closest fit (PCA) | Phil. Mag. | 1901 |
| MacQueen, J. | Some Methods for Classification and Analysis of Multivariate Observations (K-Means) | Berkeley Symp. | 1967 |
| Ester, M. et al. | A density-based algorithm for discovering clusters (DBSCAN) | KDD | 1996 |
| Lee, D.D. & Seung, H.S. | Learning the parts of objects by NMF | Nature | 1999 |
| McInnes, L. & Healy, J. | UMAP | arXiv | 2018 |

## 常见全栈错误

| ❌ 错误 | ✅ 正确 |
|---|---|
| 切分前填充缺失值 | 切分后用 SimpleImputer 在训练集 fit |
| 物理常量题做异常值清洗 | 跳过描述性统计，写量纲检查 |
| 多次假设检验未校正 | 用 Bonferroni / FDR |
| 大样本下 $p$ 显著就报"有效应" | 必报效应量（Cohen's d / r²） |
| 把 t-SNE 距离当真距离 | 仅作可视化 |
| K-Means $k$ 凭直觉选 | 肘部法 + 轮廓系数 + Gap statistic |
| 不标准化就 PCA | 必须先标准化 |
| 相关系数当因果证据 | 写明"correlation ≠ causation" |
