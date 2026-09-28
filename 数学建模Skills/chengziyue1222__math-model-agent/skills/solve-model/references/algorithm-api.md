# Repository Algorithm API

从仓库根目录运行，或先将 `code/` 加入 `sys.path`：

```python
import sys
sys.path.insert(0, "code")
from algorithms import ahp_weight, topsis, gm11_predict
```

## 决策与评价

- `ahp_weight(A)` → `(weights, lambda_max, CR, passed)`
- `entropy_weight(data)` → 权重
- `topsis(data, weights=None, positive_indicators=None)` → `TOPSISResult`
- `dea(...)`、`pca(...)`、`rsr(...)`、`fahp(...)`

## 预测与拟合

- `gm11_predict(x0, predict_n=5, predict_count=None)` → 字典结果
- `linear_regression(X, y)`、`ridge_regression(X, y, ...)`
- `lagrange_interp(...)`、`newton_interp(...)`、`cubic_spline_interp(...)`
- 移动平均、指数平滑、Gompertz/Logistic 曲线位于 `time_series.py`

## 优化与网络

- `linear_programming(c, A_ub=None, b_ub=None, A_eq=None, b_eq=None, bounds=None, maximize=False)`
- `nonlinear_programming(objective, x0, bounds=None, ..., maximize=False)`
- `genetic_algorithm(fitness_func, n_vars, bounds, ..., vectorized=True)`
- `particle_swarm(...)`、`simulated_annealing(...)`
- `dijkstra(graph, source)`、`floyd(graph)`、`prim_mst(graph)`、`max_flow(...)`

## 仿真与其他

- `monte_carlo_integration(f, a, b, n_samples=100000, seed=None, vectorized=True)`
- `queuing_simulation(...)`、`queuing_mmsk(...)`、`random_walk(...)`
- `GameOfLife`、`ForestFire`、`SIRSModel`、`NaSchTraffic`
- `edge_detection(...)`、`image_segmentation(...)`、`feature_extraction(...)`
- `check_paper(path, figures_dir="figures", results_file=None)`

## 建模质量与证据契约

- `validate_state_balance(initial_state, inflows, outflows, observed_end_states=None, lower_bound=None)` → 逐期状态、残差、最低状态与是否通过。
- `service_level_metrics(achieved, target)` → 均值、最小值、5% 分位、达标率和逐期服务水平。
- `compare_policy_metrics(baseline, candidate, shared_inputs=True, lower_is_better=...)` → 同口径增量；未声明共享输入时拒绝比较。
- `lexicographic_order(records, objectives)` → 按显式 `min`/`max` 优先级给出稳定排序。
- `validate_decision_contract(...)`、`validate_contract_artifacts(...)`、`validate_quality_validation(...)` → 供建模、写作和审查共同使用的机器契约。
- `panel_diagnostics(values, holdout_periods=...)` → 面板稀疏性、时序相关、实体间相关和末段留出诊断。

在使用前以 Python `inspect.signature` 或源代码核对参数；不要从旧 README 猜测函数名或返回值。
