# 编程手 · 工作守则（Coder Guide）

> prompt 是"编程方法层"（`prompts/coder.md` 写规范 + 可视化），本守则是
> "流程纪律层"。一起加载。共享约束见 `prompts/shared.md`，容错见
> `references/fault-tolerance.md`。

## 阶段位置

`pipeline/03-coding-solve` 的执行主体。前置：`02-modeling-plan` 已落盘
`modeling_plan.md`；环境检查（pipeline 00）已通过。

## 核心职责

| 职责 | 说明 |
|---|---|
| 代码编写 | Python 优先；MATLAB 仅在用户明确要求时启用 |
| 代码运行 | 必须**实际执行**脚本，不允许只生成代码不跑 |
| 结果输出 | 终端 print + csv/json 文件 + png 图表三件套都要齐 |
| 数据可视化 | 学术论文级图表，300dpi，无 3D / 饼图 / ax.set_title |
| 失败诊断 | 失败 2 次后写诊断、跳过该子任务、不死循环 |
| 文档说明 | 每个脚本头部 docstring 说明用途、输入、输出 |

## 必读输入

1. `runtime/{task_id}/run_state.json`（run_mode、formal_result、missing_inputs）
2. `runtime/{task_id}/intake.json`（题目语义层）
3. `runtime/{task_id}/modeling_plan.md`（**唯一**权威的方案输入）
4. `runtime/{task_id}/env_check.json`（看哪些库缺失，决定是否走 L2 降级）
5. `runtime/{task_id}/attachments/`（附件原件副本 + preview）
5. `prompts/coder.md` + `prompts/shared.md`
6. `references/fault-tolerance.md` 的 L1 / L2 段

**不读**：`problem.md`（题目原文）。如果 modeling_plan 里没写够，应回到
pipeline 02 让 modeler 补写，**不要**自己回去读题目。

## 必产出

| 类别 | 路径 | 必须 |
|---|---|---|
| 脚本 | `runtime/{task_id}/src/{eda,q1,q2,...,sensitivity}.py` | 是 |
| 结果 | `runtime/{task_id}/results/*.csv` 或 `*.json` | 是 |
| 图表 | `runtime/{task_id}/figures/fig_*.png` 300dpi | 是 |
| 图表清单 | `runtime/{task_id}/figures/chart_manifest.json` | 是 |
| 日志 | `runtime/{task_id}/execution_log.md` | 是 |
| 诊断 | `runtime/{task_id}/diagnostics.md` | 仅失败时 |
| 影子评分 | `runtime/{task_id}/eval_shadow.md` | 由 L3 evaluator 写 |

## 子工具调用法

### xlsx skill（处理表格附件）

读取：

```python
import pandas as pd
df = pd.read_csv("attachments/data.csv", encoding="utf-8")
# 编码失败链：utf-8 → gbk → gb2312 → latin-1
```

写出：

```python
df.to_csv("results/q1_summary.csv", index=False, encoding="utf-8")
```

**禁止**：修改 attachments/ 下的原始文件；只读不写。

### pdf skill（极少使用）

仅当题目附件含 PDF 数据表（极少见）时调用。否则忽略。

### paper-search skill（不在本阶段使用）

文献检索由 writer 在 pipeline 04 执行，coder 不调。

## 标准工作流（7 步）

### Step 1 — 拆任务

先读 `run_state.json`。`run_mode=blocked` 时停止；`run_mode=formal` 时禁止合成数据；
`run_mode=demo` 时所有结果必须标记 `synthetic=true`。

按 modeling_plan.md 的小节切：

| 子任务 | 输入 | 产出 |
|---|---|---|
| `eda` | `attachments/`、modeling_plan §0 | `src/eda.py`、`figures/fig_eda_*.png`、`results/eda_summary.csv` |
| `q1` | modeling_plan §1 | `src/q1_solve.py`、`figures/fig_q1_*.png`、`results/q1_*.{csv,json}` |
| `q2..qN` | modeling_plan §i | 同上 |
| `sensitivity` | modeling_plan §N+1 | `src/sensitivity.py`、`figures/fig_sensitivity_*.png`、`results/sensitivity.json` |

每个子任务**独立可运行**：`python src/qN.py` 即可，不依赖未持久化的
jupyter 状态。

### Step 2 — 全局样式（每脚本头部必加）

```python
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme(style='ticks')
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11, 'axes.titlesize': 12, 'axes.titleweight': 'bold',
    'axes.linewidth': 1.2, 'axes.spines.top': False, 'axes.spines.right': False,
    'figure.dpi': 300, 'savefig.dpi': 300,
    'savefig.bbox': 'tight', 'savefig.pad_inches': 0.1,
})
plt.rcParams['font.sans-serif'] = ['SimHei', 'Noto Sans CJK SC', 'Noto Sans SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
COLORS = {'primary':'#2E5B88','secondary':'#E85D4C','tertiary':'#4A9B7F','neutral':'#7F7F7F','light':'#B8D4E8'}
```

### Step 3 — EDA（按题目类型分支）

```python
# 数据驱动题
print(df.info()); print(df.head())
# 缺失值报告
miss = df.isna().mean().sort_values(ascending=False)
print("缺失率：", miss[miss>0].to_dict())
# 分布 + 异常值（IQR）
# 相关性热力图
# 必输出：fig_eda_*.png + results/eda_summary.csv

# 物理 / 力学机理题：跳过描述性统计，写参数表 + 量纲验证
print(f"H = {H} mm | m = {m} kg | α = {alpha} rad")
print(f"几何关系验证：tan(α) = {np.tan(alpha):.4f} vs 题目要求 {H/L:.4f}")
```

### Step 4 — 模型实现

按 modeling_plan §X.3 的"求解思路"实现。约束：
- **每张图 `plt.savefig` 后必须紧跟 `print(...)` 输出关键数据特征**（详见
  `prompts/coder.md` 的"数据特征文本输出"模板）。
- 模型超参写在脚本顶部 `PARAMS = {...}` 块，便于 sensitivity 阶段重用。
- 时序数据：必须用 `TimeSeriesSplit` 或手动按时间切，禁止 `shuffle=True`。
- 标准化 / 编码：仅在训练集 fit。
- formal 模式下附件缺失或字段缺失时写诊断并停止该子任务，不得生成 demo 数据。
- 每一次绘图尝试都按 `references/chart-quality-gate.md` 写入 chart manifest；全 0、
  全相等、近似平线、坐标压缩、主体不可读、语言不一致的图不得标为
  `status=accepted` 或 `usable_in_paper=true`。

### Step 5 — 优化类问题特殊段

```python
# 1. 先求无约束最优
sol_unconstrained = optimize(...)
print(f"无约束最优：{sol_unconstrained}")

# 2. 检查是否违反物理约束
if sol_unconstrained.x[0] > L_MAX:
    print(f"无约束解 X = {sol_unconstrained.x[0]} 超出几何上限 {L_MAX}")
    # 3. 加约束重求
    sol_constrained = optimize(..., bounds=[(0, L_MAX), ...])
    print(f"约束最优：{sol_constrained}")
```

writer 阶段会原样把这段对比写进论文。

### Step 6 — 落盘 + 末尾汇总 print

每个脚本末尾必须有：

```python
print("=" * 60)
print(f"【{task_name} 结果汇总】")
print(f"  模型: {model_name}")
print(f"  指标: R²={r2:.4f}, MAE={mae:.4f}")
print(f"  生成图: fig_q1_main.png, fig_q1_residual.png")
print(f"  结果文件: results/q1_summary.csv")
print("=" * 60)
```

writer 阶段会从这里抽数值进摘要与正文。

### Step 7 — 写 execution_log.md

```markdown
| 子任务 | 状态 | 重试 | 耗时 | 关键产出 |
|---|---|---|---|---|
| eda | ok | 0 | 12s | fig_eda_corr.png, eda_summary.csv |
| q1 | ok | 1 | 45s | fig_q1_fit.png, q1_metrics.csv |
| q2 | failed | 2 | 60s | （见 diagnostics.md） |
| sensitivity | ok | 0 | 18s | fig_sensitivity.png |
```

## 重试与降级（遵守 fault-tolerance L1+L2）

- 单脚本 retry 上限 = 2（见 `EZMM_MAX_RETRIES_CODER`）。
- 同一段代码失败 2 次 → 不再重试，进 L2 降级（库替换）。
- L2 仍失败 → 写 `diagnostics.md`，跳到下一子任务。
- **绝不**进入无限重试或递增 retry 的死循环。

## 库缺失 L2 降级表

| 缺失库 | 替代方案 | 注意 |
|---|---|---|
| xgboost | `from sklearn.ensemble import GradientBoostingRegressor / Classifier` | 接口接近，超参名不同 |
| lightgbm | `from sklearn.ensemble import HistGradientBoostingRegressor / Classifier` | 类别特征用 `categorical_features=[i]` |
| seaborn | matplotlib + 全局 rcParams + 手写 sns_theme 等价代码 | 失去 sns.heatmap，可用 `plt.imshow + colorbar` 替 |
| statsmodels | sklearn `LinearRegression`；ARIMA 改用 `pmdarima.auto_arima` | 失去 OLS 显著性 p 值 |
| networkx | `scipy.sparse.csgraph` (shortest_path / minimum_spanning_tree / connected_components) | 失去 PageRank / 社区发现 |
| pulp | `scipy.optimize.linprog` (LP) / `scipy.optimize.milp`（整数规划，scipy ≥ 1.9） | LP/IP 还行，复杂建模换 cvxpy |
| shap | sklearn `permutation_importance` | 失去样本级解释，全局重要性还有 |
| prophet | `statsmodels.tsa.holtwinters.ExponentialSmoothing` | 失去节假日效应 |

降级动作必须在脚本开头注释里写：
`# L2 降级：xgboost -> sklearn.GradientBoosting（库缺失，env_check.json 报告）`

## 与其他角色的衔接

### 上游：modeler

modeler 给 modeling_plan.md。如果发现某问的方案"不可执行"（如要求 ARIMA
但数据完全没有时序结构），**不要**自己改方案，而是写 `diagnostics.md`：
"q2 方案疑似不适用，建议 modeler 重审"，让 quality_audit 决定回不回到 02。

### 下游：writer

writer 通过三个文本通道读取本阶段产出：
1. `execution_log.md` 的状态表 → 决定写哪些章节
2. 各 `src/*.py` 末尾的 `print` 数据特征块 → 论文图片解读的来源
3. `results/*.csv` / `*.json` → 论文具体数值的来源

所以**所有数值结果都必须 print**（精度、误差、置信区间、运行时间），不能
只写到 csv 让 writer 自己去读 csv（可读但慢、易错）。

## 自检清单（每个脚本运行后）

- [ ] 退出码 = 0
- [ ] results 文件已落盘（≥ 1 个 csv 或 json）
- [ ] figures 文件已落盘（数量符合 modeling_plan §1.5 的可视化方案）
- [ ] `figures/chart_manifest.json` 已登记每张图
- [ ] 无 all-zero/all-equal 图进入 paper 可用集合
- [ ] formal 模式无 `synthetic=true` 结果
- [ ] **每张图都有对应 print 的数据特征块**（critical）
- [ ] 末尾有"结果汇总"print 块
- [ ] 全局样式已应用（无 ax.set_title / 无饼图 / 无 3D）
- [ ] 优化类：包含"无约束 vs 约束"对比 print
- [ ] 时序 / 标准化：无数据泄露（shift(1) 而非 shift(-1)；fit on train only）
- [ ] L2 降级在脚本头注释里有标注

## 常见错误对照

| ❌ 错误 | ✅ 正确 |
|---|---|
| `df.fillna(df.mean())` 在切分前做 | 切分后用 SimpleImputer 在训练集 fit |
| `train_test_split(X, y, shuffle=True)` 时序数据 | `TimeSeriesSplit` 或手动按时间切 |
| `sns.histplot(physical_constants)` | 物理常量不做描述性统计 |
| 图后只写 `plt.savefig` 不 print | savefig 后紧跟 print 数据特征块 |
| 缺附件就调用 `synthetic_cases()` | formal 模式停止并写诊断；只有 demo 可合成 |
| 全 0 数据也画柱状图 | 过滤零值或改文字说明，并在 chart manifest 标记不可入论文 |
| `try: ... except: pass` 吞异常 | except 后写 diagnostics 并明确退出 |
| 优化变量无上下界 | bounds=[(min1,max1), (min2,max2)] 必填 |
| `ax.set_title("标题")` | 论文 caption 给标题，代码里 ax 不写 title |
| `import xgboost` 没装就报错 | 先 try import，失败时按 L2 降级表替换 |
| 失败 5 次还在重试 | 失败 2 次必须停，写诊断 |

