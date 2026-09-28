---
name: model-library-extended
description: 扩展模型库 — 基于 Algorithms_MathModels 仓库补充的 9 大算法模块
---

# 扩展模型库

> 基于 [Algorithms_MathModels](https://github.com/HuangCongQing/Algorithms_MathModels) 仓库转化的 Python 实现。
> 代码位于 `math-model/code/algorithms/`

---

## 1. AHP 层次分析法

**适用场景**: 多准则决策、权重确定、方案排序、评价体系构建

**核心方法**:
- `ahp_weight(A)` — 计算权重向量 + 一致性检验
- `consistency_check(A)` — 完整一致性报告 (CR < 0.1 通过)
- `hierarchical_ahp(goal_w, criteria_w)` — 多层次综合排序

**决策条件**:
```
IF 问题涉及多准则决策 / 需要确定各因素权重 / 方案排序
THEN
  主模型: AHP 层次分析法
  辅助模型: 一致性检验 (CR < 0.1)
  验证模型: 灵敏度分析 (改变判断矩阵看结果稳定性)
```

**使用模板**:
```python
from algorithms.ahp import ahp_weight, consistency_check
A = np.array([[1, 3, 5], [1/3, 1, 3], [1/5, 1/3, 1]])
result = consistency_check(A)
```

---

## 2. 灰色系统完整版

**适用场景**: 小样本预测、关联分析、聚类评估、S 型增长

**核心方法**:
| 方法 | 用途 | 使用条件 |
|------|------|---------|
| `gm11_predict` | GM(1,1) 灰色预测 | 数据量少 (≥4), 近似指数增长 |
| `gm21_predict` | GM(2,1) 二阶预测 | 波动较大, GM(1,1) 效果不好 |
| `verhulst_predict` | Verhulst S 型预测 | S 型增长 (人口/产品生命周期) |
| `grey_auto_predict` | 自动选择最优模型 | 不确定用哪个模型 |
| `grey_correlation` | 灰色关联分析 | 多因素关联度排序 |
| `grey_clustering` | 灰色聚类 | 灰色分类评估 |

**决策条件**:
```
IF 数据量少 (< 30) / 近似指数增长 / 需要多因素关联分析
THEN
  主模型: GM(1,1) 或灰色关联
  辅助模型: 级比检验 + 残差检验
  验证模型: 后验差比检验 (C < 0.35 好, P > 0.95 好)
```

---

## 3. 插值方法

**适用场景**: 数据补全、函数逼近、曲线拟合、缺失值处理

**核心方法**:
| 方法 | 特点 | 适用场景 |
|------|------|---------|
| `lagrange_interp` | 全局多项式 | 节点少 (< 10) |
| `newton_interp` | 全局, 可递增节点 | 节点逐步增加 |
| `piecewise_linear_interp` | 分段线性, 稳定 | 一般用途 |
| `cubic_spline_interp` | 三次样条, 光滑 | 需要光滑曲线 |

**决策条件**:
```
IF 需要补全缺失数据 / 函数逼近 / 离散数据变连续
THEN
  节点少 (< 10): 拉格朗日或牛顿插值
  节点多: 三次样条插值 (避免龙格现象)
  只需简单补全: 分段线性插值
```

---

## 4. 回归分析

**适用场景**: 变量关系建模、预测、因素筛选

**核心方法**:
| 方法 | 用途 | 使用条件 |
|------|------|---------|
| `linear_regression` | 多元线性回归 | 线性关系 |
| `polynomial_regression` | 多项式回归 | 非线性, 单变量 |
| `ridge_regression` | 岭回归 (L2) | 多重共线性 |
| `stepwise_regression` | 逐步回归 | 变量筛选 |
| `nonlinear_regression` | 非线性回归 | 已知函数形式 |

**决策条件**:
```
IF 需要建立变量间关系 / 预测 / 筛选重要变量
THEN
  线性关系: linear_regression
  非线性已知形式: nonlinear_regression
  变量太多需要筛选: stepwise_regression
  多重共线性: ridge_regression
```

---

## 5. 图论完整版

**适用场景**: 路径规划、网络优化、项目管理、物流配送

**核心方法**:
| 方法 | 用途 | 时间复杂度 |
|------|------|-----------|
| `dijkstra` | 单源最短路径 | O(V²) |
| `floyd` | 全源最短路径 | O(V³) |
| `prim_mst` | 最小生成树 | O(V²) |
| `max_flow` | 最大流 | O(VE²) |
| `critical_path` | 关键路径 (PERT) | O(V+E) |

**决策条件**:
```
IF 问题涉及路径/网络/流/调度
THEN
  单源最短路: dijkstra
  所有节点对最短路: floyd
  最小连接成本: prim_mst
  网络最大流量: max_flow
  项目工期优化: critical_path
```

---

## 6. 模糊数学完整版

**适用场景**: 不确定性评价、模糊分类、模式识别

**核心方法**:
| 方法 | 用途 |
|------|------|
| `fuzzy_comprehensive_evaluation` | 一级模糊综合评价 |
| `multi_level_fuzzy_evaluation` | 多层次模糊评价 |
| `fuzzy_cmeans` | 模糊 C 均值聚类 |
| `fuzzy_pattern_recognition` | 模糊模式识别 |

**决策条件**:
```
IF 评价指标带有模糊性 / 需要处理不确定性 / 软分类
THEN
  评价问题: fuzzy_comprehensive_evaluation
  多层次评价: multi_level_fuzzy_evaluation
  软聚类: fuzzy_cmeans
```

---

## 7. 神经网络

**适用场景**: 非线性映射、分类、预测、模式识别

**核心方法**:
| 方法 | 用途 | 特点 |
|------|------|------|
| `BPNeuralNetwork` | 通用逼近器 | 可调层数/节点 |
| `RBFNetwork` | 函数逼近 | 训练快, 泛化好 |
| `SOM` | 无监督聚类 | 自组织, 可视化 |

**决策条件**:
```
IF 问题复杂度高 / 非线性关系 / 数据量大
THEN
  分类/回归: BPNeuralNetwork
  函数逼近: RBFNetwork
  无监督聚类/可视化: SOM
```

---

## 8. 智能优化算法

**适用场景**: 复杂优化、组合优化、多峰函数

**核心方法**:
| 方法 | 特点 | 适用场景 |
|------|------|---------|
| `genetic_algorithm` | 全局搜索, 并行 | 通用优化 |
| `particle_swarm` | 收敛快, 易实现 | 连续优化 |
| `simulated_annealing` | 跳出局部最优 | 组合优化 |
| `ant_colony_tsp` | 离散优化 | TSP/路径优化 |
| `artificial_fish_swarm` | 群体智能 | 多峰优化 |

**决策条件**:
```
IF 问题非凸/多峰/离散/传统方法失效
THEN
  连续优化: PSO 或 GA
  组合优化 (TSP等): ACO 或 SA
  多峰函数: GA (多样性好)
```

---

## 9. 元胞自动机

**适用场景**: 复杂系统模拟、扩散过程、传染病、自组织

**核心方法**:
| 方法 | 用途 |
|------|------|
| `GameOfLife` | 复杂性/涌现行为演示 |
| `ForestFire` | 扩散/传播过程 |
| `ElementaryCA` | 一维模式生成 |
| `DLA` | 分形生长 |
| `SIRSModel` | 传染病传播 |

**决策条件**:
```
IF 问题涉及空间扩散/传播/复杂系统/自组织
THEN
  传染病: SIRSModel
  火灾/信息扩散: ForestFire
  分形/生长: DLA
  通用演示: GameOfLife
```

---

## 速查: 问题类型 → 算法

| 问题类型 | 推荐算法 | 代码入口 |
|---------|---------|---------|
| 多准则决策 | AHP | `algorithms.ahp` |
| 小样本预测 | 灰色系统 | `algorithms.grey_system` |
| 关联分析 | 灰色关联 | `algorithms.grey_system` |
| 数据补全 | 插值 | `algorithms.interpolation` |
| 变量关系 | 回归分析 | `algorithms.regression` |
| 最短路径 | Dijkstra/Floyd | `algorithms.graph_theory` |
| 网络流 | 最大流 | `algorithms.graph_theory` |
| 项目调度 | 关键路径 | `algorithms.graph_theory` |
| 模糊评价 | 模糊综合评价 | `algorithms.fuzzy_math` |
| 软聚类 | FCM | `algorithms.fuzzy_math` |
| 非线性映射 | 神经网络 | `algorithms.neural_network` |
| 复杂优化 | GA/PSO/SA | `algorithms.metaheuristic` |
| TSP | ACO | `algorithms.metaheuristic` |
| 传染病模拟 | SIRS | `algorithms.cellular_automata` |
| 扩散模拟 | 森林火灾 | `algorithms.cellular_automata` |
