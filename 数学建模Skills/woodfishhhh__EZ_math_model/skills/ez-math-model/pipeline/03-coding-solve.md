# Pipeline 03 — 代码求解

## 入口条件

- `modeling_plan.md` 已落盘且包含每个 quesN 的小节。
- `thesis_match.json` 已落盘。
- `run_state.json.run_mode != blocked`。
- 若 `run_mode=formal`，`run_state.json.formal_result == true` 且 `missing_inputs=[]`。

## 阶段任务

### 1. 加载 coder 角色

- prompt：`prompts/coder.md`
- 守则：`references/roles/coder-guide.md`
- 协议：`references/run-mode-protocol.md`、`references/chart-quality-gate.md`

在生成任何代码前读取 `run_state.json`。若 `run_mode=blocked`，立即停止并写
`diagnostics.md`；若缺数据但用户未授权 demo，禁止自行造数。

### 2. 任务清单生成

按 `modeling_plan.md` 的小节切分子任务：

| 子任务 | 输入 | 产出 |
|---|---|---|
| `eda` | `attachments/`、modeling_plan §0 | `src/eda.py`、`figures/fig_eda_*.png`、`results/eda_summary.csv`（数据驱动题） |
| `q1` | modeling_plan §1 | `src/q1_solve.py`、`figures/fig_q1_*.png`、`results/q1_*.{csv,json}` |
| `q2..qN` | modeling_plan §i | 同上 |
| `sensitivity` | modeling_plan §N+1 | `src/sensitivity.py`、`figures/fig_sensitivity_*.png`、`results/sensitivity.json` |

### 3. 逐子任务执行

容错策略：依据 `references/fault-tolerance.md` 的 L1+L2+L3 协议。**绝不**在
本阶段实现自定义重试，必须复用 fault-tolerance 的统一约束。

每个子任务循环（伪代码）：

```
attempt = 0
while attempt < EZMM_MAX_RETRIES_CODER:   # 默认 2
    生成代码 → 落盘 src/{name}.py
    执行：python src/{name}.py
    if 退出码 == 0:
        记 execution_log.md：name=ok, retries=attempt
        触发 L3 影子评估（quality_audit 阶段读取）
        break
    else:
        attempt += 1
        # 修复策略：
        #   第 1 次：读异常 + 改局部
        #   第 2 次：换思路（更简单算法 / 更小数据集 / 更宽松约束）
        记 execution_log.md：name=retry-{attempt}, error_summary=<一行>
        if attempt == EZMM_MAX_RETRIES_CODER:
            进 L2 fallback：库缺失尝试同类替代（详见 references/fault-tolerance.md L2）
            if L2 仍失败:
                记 execution_log.md：name=failed
                写诊断到 diagnostics.md（含错误摘要、影响、建议）
                break  # 不打断，继续下一子任务
```

### 3.1 禁止静默 synthetic fallback

`formal` 模式下，脚本不得因为附件缺失、读取失败或字段不存在而自动调用
`synthetic_cases()`、`make_demo_data()`、随机数造样本或内置示例数据。正确处理是：

- 写入 `diagnostics.md`，说明缺失的文件、字段或样例；
- 将对应子任务记录为 `blocked` 或 `failed`；
- 不生成会被 writer 当作正式结论的结果表和图。

只有 `run_mode=demo` 且 `formal_result=false` 时可以生成合成数据，且所有结果表必须
包含 `synthetic=true` 字段，图表 manifest 也必须标记 `synthetic=true`。

**库缺失 L2 降级表**（节选自 fault-tolerance.md，便于本阶段查阅）：

| 缺失库 | 替代方案 |
|---|---|
| xgboost | sklearn `GradientBoostingRegressor / Classifier` |
| lightgbm | sklearn `HistGradientBoosting*` |
| seaborn | matplotlib + 全局 rcParams |
| statsmodels | sklearn 简单回归；ARIMA 改 `pmdarima` |
| networkx | scipy.sparse.csgraph |
| pulp | scipy.optimize.linprog（整数规划用 milp） |

降级动作必须在脚本开头注释里写：`# 替换 xgboost -> sklearn.GradientBoosting (库缺失)`。

### 4. 图表质量登记（强制）

每一次绘图尝试都必须先校验待绘图数据，并写入
`figures/chart_manifest.json`。通过、拒绝、跳过都要登记；被拒图可以不保存
PNG，但必须说明拒绝原因。至少登记：

- `schema_version`、`figure`、`status`、`chart_type`、`source`、`source_hash`
- `metric_columns`、`x_label`、`y_label`、`unit`、`caption_intent`
- `width_px`、`height_px`、`dpi`、`figure_exists`
- `rows_before`、`rows_after_filter`、`filtered_zero_rows`
- `all_zero`、`all_equal`、`near_flat`、`axis_compressed`
- `dominant_single_color`、`label_language`、`synthetic`
- `usable_in_paper`、`reason_code`、`reason_detail`

全 0、全相等、过滤后有效行少于 2、缺单位或缺指标名的图不得进入论文。柱状图尤其
必须剔除无意义零值行，不能把“0 值柱子”当作有效信息。

图像语义同样是硬门：曲线近似水平且无法解释、轨迹被全局坐标压扁、主体占满整张图、
单色块、标签语言与论文语言不一致、嵌入 PDF 后不可读，均不能标为
`status=accepted`。所有 `figures/*.png` 必须能在 manifest 中按文件名找到记录；
所有 `accepted` 图必须实际存在且 `figure_exists=true`。

### 5. Sub-agent 派单细节（可选）

派单决策由 `external/tools/agent_mode.{single,multi,hybrid}` 标记决定。
**single 模式跳过本节**，按顺序执行所有子任务；**multi / hybrid 模式**按下文派单。

详细派单协议见 `references/agent-mode.md`。如宿主已安装
`dispatching-parallel-agents` skill，按其指引判定"是否真正独立"再派单
（详见 `tools/dispatching-parallel-agents/SKILL.md`）。

若主对话上下文已超过 60% 上限，或 modeling_plan.md 拆出 ≥ 5 个子任务，
**应派 coder sub-agent**：每个子任务一个 subagent，并发上限默认 2（避免内核
争用与文件竞写）。派单模板：

```
subagent_type = general-purpose
description   = "ez-math-model coder for {task_name}"
prompt        = (
    "工作目录：{workdir}\n"
    "请按 prompts/coder.md + references/roles/coder-guide.md 完成子任务 {task_name}。\n"
    "modeling_plan 第 {section} 节、附件清单：{attachments}\n"
    "落盘要求：src/{task_name}.py + results/{task_name}_*.csv + figures/fig_{task_name}_*.png\n"
    "完成后输出一行 'DONE {task_name}' 到 stdout。\n"
    "受 fault-tolerance L1 约束，最多重试 2 次。"
)
```

主流程等 subagent 全部 DONE 后聚合 `execution_log.md`，再进 pipeline 04。

### 6. 数据特征文本输出（强制）

每段绑图代码后必须 `print` 关键数据特征（模板见 `prompts/coder.md`）。
没有 print 的图后续 writer 无法解读，质量门会扣分。

### 7. 工程优化约束（优化类问题强制）

若 `intake.json` 中识别出"优化类"（关键词：最优 / 优化 / 极值 / 最大化 /
最小化 / 调度 / 选择），coder 必须在 `print` 中包含"无约束 vs 物理约束"对比
段落（详见 `prompts/coder.md`）。

### 8. 执行日志

`execution_log.md` 是 markdown 表格 + 详细记录块：

```markdown
| 子任务 | 状态 | 重试 | 耗时 | 关键产出 |
|---|---|---|---|---|
| eda | ok | 0 | 12s | fig_eda_corr.png, eda_summary.csv |
| q1 | ok | 1 | 45s | fig_q1_fit.png, q1_metrics.csv |
| q2 | failed | 2 | 60s | （见诊断） |
| sensitivity | ok | 0 | 18s | fig_sensitivity.png |
```

## 产出文件

| 路径 | 必须 | 说明 |
|---|---|---|
| `runtime/{task_id}/src/*.py` | 是 | 每个子任务一个脚本 |
| `runtime/{task_id}/results/` | 是 | 至少 1 个结果文件；demo 结果需含 `synthetic=true` |
| `runtime/{task_id}/figures/` | 是 | 只保存通过图表有效性与视觉语义检查的图 |
| `runtime/{task_id}/figures/chart_manifest.json` | 是 | 图表质量登记 |
| `runtime/{task_id}/execution_log.md` | 是 | 执行状态汇总 |

## 失败诊断

| 情况 | 处理 |
|---|---|
| 单个脚本 2 次重试仍失败 | L1 用尽 → 若 `external/tools/inherited_skills.{yes,recommended}` 存在且检测到 systematic-debugging，调 `tools/systematic-debugging/SKILL.md` 做根因分析；否则记 `diagnostics.md`，**不打断**，跳到下一子任务 |
| 全部脚本失败（≥ 80% 子任务 failed） | **打断**，输出最常见错误类型，让用户检查环境 |
| 关键库（如 xgboost）缺失 | 不打断，coder 自动 fallback 到 sklearn 同类模型（参考本文件 §3 L2 降级表） |
| 附件读取失败 | 不打断，相关子任务标记 skip 并写诊断 |
| formal 模式下需要合成数据 | **打断该子任务**，写诊断；不得自动 fallback |
| 图表数据全 0 / 全相等 | 登记 `status=rejected` 且 `usable_in_paper=false`，writer 不得引用 |
| 图表视觉语义失败 | 重画；仍失败则登记 rejected，不得保存为论文图 |
| simplify skill 已启用 | 所有子任务完成后调 `tools/simplify/SKILL.md` 写 `simplify_report.md`（不修代码） |

## 下一阶段入口

`pipeline/04-paper-writing.md`。

