---
name: sci-figures
description: 科研图表模板库 — 11 种 Nature/Science 风格高质量可视化模板，适用于数学建模论文
---

# 科研图表模板库

来源: [MathModelAgent](https://github.com/jihe520/MathModelAgent) 的 `mathmodel-figure-templates` skill。

## 模板列表

| ID | 类名 | 用途 | 适用场景 |
|----|------|------|----------|
| taylor | `TaylorDiagram` | 多模型评价泰勒图 | 模型对比：标准差 vs 相关系数 |
| raincloud | `PairedRaincloud` | 配对云雨图 | 前后对比/实验组对照组 |
| roc | `CvRocCurve` | 交叉验证 ROC 曲线 | 分类模型评价，带置信区间 |
| pairgrid | `CorrelationPairgrid` | 散点+直方图+相关矩阵 | 数据探索，变量相关性 |
| pred-marginal | `PredictionMarginal` | 预测值-真实值边缘分布 | 回归模型评价（4 模型对比） |
| surface | `HyperparamSurface` | 超参数优化 3D 曲面 | TPE/Bayesian 优化可视化 |
| corr-violin | `CorrSplitViolin` | 相关矩阵+半边小提琴 | 特征分析+训练/测试分布 |
| circular-heatmap | `CircularHeatmap` | 分组环形热图 | 多维分组数据热力图 |
| combo | `ComboComparison` | 堆叠+云雨+箱线组合 | 城市/区域多指标对比 |
| chord | `ChordDiagram` | Nature 和弦图 | 实体间关系/流量可视化 |
| shap | `ShapBeeswarm` | SHAP 柱状+蜂群图 | 机器学习可解释性 |

## 决策规则

```
IF 需要对比多个模型的预测精度
  AND 关注标准差和相关系数两个维度
THEN 使用 TaylorDiagram

IF 需要展示实验前后/处理前后的分布变化
THEN 使用 PairedRaincloud

IF 需要展示分类模型的 ROC 曲线
  AND 有多折交叉验证结果
THEN 使用 CvRocCurve

IF 需要探索变量间的相关性和分布
THEN 使用 CorrelationPairgrid

IF 需要对比 4 个以内的回归模型
  AND 展示预测值 vs 真实值 + 边缘分布
THEN 使用 PredictionMarginal

IF 需要展示超参数搜索过程和响应面
THEN 使用 HyperparamSurface

IF 需要同时展示相关矩阵和特征分布
  AND 有训练集/测试集对比
THEN 使用 CorrSplitViolin

IF 需要展示实体间的关系/流量
THEN 使用 ChordDiagram

IF 需要展示机器学习模型的特征重要性
  AND 使用 SHAP 值
THEN 使用 ShapBeeswarm
```

## 使用模板

### 基本模式

```python
from algorithms.sci_figures import TaylorDiagram, TaylorPoint, save_sci_figure

# 创建图表
models = [
    ("XGBoost", "#f2a51a"),
    ("ANN", "#d7191c"),
    ("GPR", "#2222a0"),
    ("Observed", "#000000"),
]
panels = {
    "train": [
        TaylorPoint("XGBoost", 1.02, 0.985),
        TaylorPoint("ANN", 0.93, 0.970),
        TaylorPoint("GPR", 1.08, 0.955),
    ],
    "test": [
        TaylorPoint("XGBoost", 1.00, 0.975),
        TaylorPoint("ANN", 0.96, 0.965),
        TaylorPoint("GPR", 1.06, 0.960),
    ],
}
fig = TaylorDiagram(models, panels).make()
save_sci_figure(fig, "taylor_diagram", "figures")
```

### 使用真实数据

```python
from algorithms.sci_figures import CorrelationPairgrid
import numpy as np
import pandas as pd

# 读取数据
df = pd.read_excel("data.xlsx")
data = df[["指标1", "指标2", "指标3", "指标4"]].values

# 生成图表
fig = CorrelationPairgrid(data, ["指标1", "指标2", "指标3", "指标4"]).make()
fig.savefig("figures/correlation.png", dpi=300, bbox_inches="tight")
```

### ROC 曲线

```python
from algorithms.sci_figures import CvRocCurve, RocModelSpec

specs = [
    RocModelSpec("LR", 0.889, 0.026, "#2d214c"),
    RocModelSpec("RF", 0.906, 0.029, "#8f3032"),
    RocModelSpec("XGBoost", 0.895, 0.032, "#c47b4b"),
    RocModelSpec("LightGBM", 0.902, 0.039, "#3c8849"),
    RocModelSpec("SVM", 0.861, 0.043, "#242585"),
]
fig = CvRocCurve(specs, n_folds=5).make()
fig.savefig("figures/roc_cv.png", dpi=300, bbox_inches="tight")
```

### SHAP 可解释性

```python
from algorithms.sci_figures import ShapBeeswarm
import shap

# 假设已有模型和数据
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# 提取 importance table
importance = np.array([np.abs(sv).mean(axis=0) for sv in shap_values]).T

fig = ShapBeeswarm(
    feature_names=feature_names,
    class_names=class_names,
    importance_table=importance,
    shap_values=shap_values,
    feature_values=X_test,
).make()
```

## 输出格式

所有图表默认输出三种格式:
- **PNG**: 300 dpi，适合论文嵌入和预览
- **PDF**: 矢量格式，适合论文提交
- **SVG**: 矢量格式，适合网页和编辑

```python
from algorithms.sci_figures import save_sci_figure
paths = save_sci_figure(fig, "my_figure", "figures")
# paths = {"png": "figures/my_figure.png", "pdf": "figures/my_figure.pdf", "svg": "figures/my_figure.svg"}
```

## 与论文集成

### LaTeX

```latex
\begin{figure}[H]
  \centering
  \includegraphics[width=0.85\textwidth]{figures/taylor_diagram.pdf}
  \caption{多模型评价泰勒图}
  \label{fig:taylor}
\end{figure}
```

### Typst

```typst
#figure(
  image("figures/taylor_diagram.pdf", width: 85%),
  caption: [多模型评价泰勒图],
)
```

## 自定义

每个图表类都支持自定义颜色、标签、尺寸等参数。查看源码中的 docstring 获取完整参数列表。

如需修改模板脚本的模拟数据部分，替换为真实数据即可。模板的绘图样式（字体、线宽、颜色方案）已针对论文排版优化，建议保持不变。
