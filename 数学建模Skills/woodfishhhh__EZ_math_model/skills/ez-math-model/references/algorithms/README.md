# 算法库速查

> 本目录是 ez-math-model 的算法知识层。每篇文档遵循统一结构：
> **何时选用 → 核心思路 → 关键参数 → 常见坑 → 验证手段 → Python 入口**。
> 不写完整代码，只写「选了之后该怎么用」。

## 按问题类型选算法

| 问题类型 | 首选算法 | 升级方向 | 文档 |
|---|---|---|---|
| 预测·有多个影响因素 | 线性回归 | Ridge / Lasso / XGBoost | [02 预测](02-prediction.md) |
| 预测·仅时间序列 | ARIMA | Prophet / 指数平滑 / LSTM | [02 预测](02-prediction.md) |
| 预测·数据极少（<15） | 灰色预测 GM(1,1) | — | [02 预测](02-prediction.md) |
| 评价·定权重 | AHP / 熵权法 | 主客观加权融合 | [03 评价](03-evaluation.md) |
| 评价·方案排序 | TOPSIS | PCA-TOPSIS / 模糊综合 | [03 评价](03-evaluation.md) |
| 分类·有标签 | 逻辑回归 | 随机森林 / SVM / XGBoost | [07 机器学习](07-machine-learning.md) |
| 聚类·无标签 | K-Means | DBSCAN / 层次聚类 | [05 统计](05-statistics.md) |
| 优化·线性约束 | 线性规划 | 整数规划 / 0-1 规划 | [01 优化](01-optimization.md) |
| 优化·非线性 | 遗传算法 | 模拟退火 / PSO | [01 优化](01-optimization.md) |
| 优化·多目标 | NSGA-II | MOEA/D | [01 优化](01-optimization.md) |
| 序贯决策 | 动态规划 | 强化学习 | [01 优化](01-optimization.md) |
| 网络·最短路径 | Dijkstra | A* / Bellman-Ford | [04 图论](04-graph.md) |
| 网络·最小生成树 | Kruskal / Prim | — | [04 图论](04-graph.md) |
| 网络·最大流 | Edmonds-Karp | Push-Relabel | [04 图论](04-graph.md) |
| 统计·相关性 | Pearson / Spearman | 偏相关 / 因子分析 | [05 统计](05-statistics.md) |
| 统计·组间比较 | t 检验 / ANOVA | 非参数检验 | [05 统计](05-statistics.md) |
| 统计·降维 | PCA | t-SNE / UMAP | [05 统计](05-statistics.md) |
| 仿真·风险 | 蒙特卡洛 | CVaR / VaR | [06 综合](06-comprehensive.md) |
| 仿真·空间 | 元胞自动机 | Agent-based modeling | [06 综合](06-comprehensive.md) |
| 仿真·状态转移 | 马尔可夫链 | HMM | [06 综合](06-comprehensive.md) |
| 排队 | M/M/1 / M/M/c | 网络排队 | [06 综合](06-comprehensive.md) |

## 高分组合速查

| 题型 | 组合 |
|---|---|
| 综合评价 | AHP + TOPSIS |
| 预测 + 不确定性 | XGBoost + Bootstrap |
| 方案优选 | AHP + 熵权法 + TOPSIS |
| 风险评估 | Logistic + 蒙特卡洛 |
| 文本分析 | TF-IDF + LDA + 情感分析 |
| 时空预测 | ARIMA / LSTM + 空间聚类 |
| 投资优化 | 预测模型 + 动态规划 |
| 因果效应 | DID / 回归 + SHAP |

## 选模型时反复问自己的 5 个问题

1. 数据是「确定常量」还是「样本分布」？前者别套数据驱动模板。
2. 优化变量有没有物理上下界？没有写边界 = 必扣分。
3. 简单基线（线性回归 / K-Means / 线性规划）够不够用？不够再升级。
4. 验证策略是什么？没有交叉验证 / Bootstrap / 基线对比 = 论文薄。
5. 我能不能 5 分钟内向评委讲清楚为什么选这个模型？讲不清就不选。
