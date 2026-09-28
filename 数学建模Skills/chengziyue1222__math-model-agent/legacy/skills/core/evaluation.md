---
name: evaluation
description: 综合评价方法库 — TOPSIS、熵权法、DEA、PCA、RSR、FAHP 等 8 种常用评价方法
---

# 综合评价方法库

来源: [Giyn/MathematicalModelingAlgorithm](https://github.com/Giyn/MathematicalModelingAlgorithm)、[MathModelAgent](https://github.com/jihe520/MathModelAgent) 及自主实现。

## 方法列表

| 方法 | 函数名 | 用途 | 数据要求 |
|------|--------|------|----------|
| 熵权法 | `entropy_weight()` | 客观赋权 | 正向/负向指标标记 |
| TOPSIS | `topsis()` | 多方案排序 | 至少 2 个方案 |
| AHP+TOPSIS | `ahp_topsis()` | 主客观组合评价 | AHP 权重 + 数据 |
| DEA | `dea()` | 效率评价 | 投入/产出矩阵 |
| PCA | `pca()` | 降维/赋权 | 连续数据 |
| RSR | `rsr()` | 综合评价分档 | 至少 3 个方案 |
| FAHP | `fahp()` | 模糊层次赋权 | 模糊互补矩阵 |
| 灰色关联 | `grey_relational()` | 关联度排序 | 参考序列 |
| 组合赋权 | `combined_weight()` | 主客观权重融合 | 两组权重 |

## 决策规则

```
IF 需要客观确定权重
  AND 数据量充足（>10 个样本）
THEN 使用 entropy_weight()

IF 需要对多个方案排序
  AND 有明确的正向/负向指标
THEN 使用 topsis()

IF 有专家经验（AHP 权重）
  AND 想结合数据客观性
THEN 使用 ahp_topsis() 或 combined_weight()

IF 需要评价决策单元的效率
  AND 有明确的投入/产出指标
THEN 使用 dea()

IF 指标过多需要降维
  AND 指标间存在相关性
THEN 使用 pca()

IF 需要对方案分档（不只是排序）
THEN 使用 rsr()

IF 需要从模糊互补矩阵求权重
THEN 使用 fahp()
```

## 使用模板

### TOPSIS 评价

```python
from algorithms.evaluation import topsis, entropy_weight
import numpy as np

# 数据：行=方案，列=指标
data = np.array([
    [80, 90, 100],   # 方案1
    [70, 85, 95],    # 方案2
    [90, 80, 85],    # 方案3
    [85, 95, 90],    # 方案4
])

# 客观赋权
weights = entropy_weight(data)

# 评价
result = topsis(data, weights)
for i, (score, rank) in enumerate(zip(result.scores, result.ranks)):
    print(f"方案{i+1}: 得分={score:.4f}, 排名={rank}")
```

### DEA 效率评价

```python
from algorithms.evaluation import dea
import numpy as np

# 投入矩阵（行=DMU，列=投入指标）
inputs = np.array([
    [20, 300],  # DMU1
    [30, 200],  # DMU2
    [40, 100],  # DMU3
])

# 产出矩阵
outputs = np.array([
    [1000],
    [1000],
    [1000],
])

result = dea(inputs, outputs)
for i, (eff, is_eff) in enumerate(zip(result.efficiency, result.is_efficient)):
    print(f"DMU{i+1}: 效率={eff:.4f}, {'有效' if is_eff else '无效'}")
```

### PCA 降维

```python
from algorithms.evaluation import pca
import numpy as np

data = np.random.randn(100, 10)  # 100个样本，10个指标

# 自动选择主成分（累积方差>85%）
result = pca(data)
print(f"选择 {result.transformed.shape[1]} 个主成分")
print(f"方差贡献率: {result.variance_ratio[:3]}")

# 指定主成分数
result = pca(data, k=3)
```

### RSR 分档

```python
from algorithms.evaluation import rsr
import numpy as np

data = np.array([
    [99.54, 60.27, 16.15],
    [96.52, 59.67, 20.10],
    [99.36, 43.91, 15.60],
    [92.83, 58.99, 17.04],
    [91.71, 35.40, 15.01],
])

result = rsr(data, n_levels=3)
for i in range(len(data)):
    print(f"方案{i+1}: RSR={result.rsr_values[i]:.4f}, 等级={result.levels[i]}")
```

### AHP+TOPSIS 组合评价

```python
from algorithms.evaluation import ahp_topsis
from algorithms.ahp import ahp_weight
import numpy as np

# AHP 主观权重
judgment = np.array([
    [1, 3, 5],
    [1/3, 1, 3],
    [1/5, 1/3, 1],
])
ahp_w = ahp_weight(judgment)[0]

# 数据
data = np.array([[80, 90, 100], [70, 85, 95], [90, 80, 85]])

# 组合评价
result = ahp_topsis(data, ahp_w, entropy_ratio=0.4)
```

## 与其他模块配合

| 场景 | 组合方式 |
|------|----------|
| 评价 + 赋权 | `ahp_weight()` → `topsis()` |
| 客观赋权 + 评价 | `entropy_weight()` → `topsis()` |
| 主客观组合 | `combined_weight(ahp_w, ew)` → `topsis()` |
| 降维 + 评价 | `pca()` → `topsis(transformed)` |
| 灰色评价 | `grey_correlation()` + `grey_relational()` |
| 模糊评价 | `fahp()` → `fuzzy_comprehensive_evaluation()` |
