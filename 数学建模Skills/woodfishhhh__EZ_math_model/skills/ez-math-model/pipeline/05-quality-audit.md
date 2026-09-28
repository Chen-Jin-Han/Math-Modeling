# Pipeline 05 — 质量审查

## 入口条件

- `paper.md` 已落盘。
- `execution_log.md` 已落盘。
- `run_state.json` 已落盘。

## 阶段任务

按 `references/workdir-protocol.md` 的分层质量门逐项评估，输出
`quality_report.json` 与 `quality_report.md`。本阶段必须优先运行
`scripts/runtime/audit_quality.py --workdir runtime/{task_id}`；该脚本给出
每条通过项的证据路径、证据片段和 pass/warn/fail 状态。禁止只凭口头判断或
文件存在声明通过。

本阶段同时**汇总 L3 影子评估**：读取
`runtime/{task_id}/eval_shadow.md`（若存在），把每个角色的评分附在质量门
末尾作为参考。

**容错协议**：本阶段遵守 `references/fault-tolerance.md` 的全文。L4 反馈
重跑只有在 `intake.json.strict_quality == true` 或 `EZMM_STRICT=1` 时启用，
否则即使有评分不达标的子任务也不阻塞 packaging。

**verification 强化**：若用户启用了继承 skill 集（`external/tools/inherited_skills.{yes,recommended}` 存在）
且检测到 `verification-before-completion`，本阶段必须用其"证据 - 断言"
对齐机制审核 quality_report.md 的每条"通过项"，详见
`tools/verification-before-completion/SKILL.md`。**禁止**口头声称通过。

### 检查项与判定逻辑

| # | 检查项 | 通过条件 | 判定 |
|---|---|---|---|
| 1 | setup 完成 | `setup_status=user_confirmed` 才可正式通过；temporary/skipped 最高 provisional | 解析 run_state.json |
| 2 | 运行模式合法 | `run_mode=formal/demo/blocked` 且 formal 时 `missing_inputs=[]` | 解析 run_state.json |
| 3 | 拆题完整 | `intake.json.ques_count > 0` 且每个 quesN 文本 ≥ 30 字 | 解析 intake.json |
| 4 | 建模方案齐全 | `modeling_plan.md` 包含每个 quesN 的方案小节 | grep 章节标题 |
| 5 | 代码可执行 | `execution_log.md` 中每个脚本最终状态 `ok` 占比 ≥ 50% | 解析 log 表格 |
| 6 | 结果文件有效 | `results/` 至少 1 个 csv/json，formal 结果不得含 `synthetic=true` | 扫描结果文件 |
| 7 | 图表有效 | `chart_manifest.json` 存在；paper 只引用 `usable_in_paper=true` 图 | 解析 manifest |
| 8 | 章节齐全 | formal 论文含 9 个固定章节标题；demo 必须标注非正式 | grep 章节标题 |
| 9 | 文献唯一 | `paper.md` 中每个 `[^N]` 编号不重复定义 | 正则统计 |
| 10 | 公式有效 | `$...$` / `$$...$$` 平衡；块级公式独立成段；公式后 5 行内解释变量与来源 | `audit_quality.py` |
| 11 | 表格有效 | Markdown 表格有表头、至少 2 行数据、无重复列名、数值列有单位 | `audit_quality.py` |
| 12 | 模板残留与工程泄漏 | 正文无 `{...}` 占位符、写作指引、`runtime/`、`output/`、manifest、运行日志等 | `audit_quality.py` |
| 13 | 图文绑定 | 每张图前后有足够解释，解释含可追溯数值证据 | `audit_quality.py` |
| 14 | 产物 manifest | 关键产物登记到 `artifact_manifest.json` 或准备由 packaging 写入 | 解析 manifest |

### 图表质量硬门

质量门必须读取 `figures/chart_manifest.json`。以下情况至少记为警告，formal 模式下
记为失败：

- `paper.md` 引用了 `usable_in_paper=false` 或未登记的图；
- chart manifest 显示 `all_zero=true` 或 `all_equal=true` 的图仍作为柱状图进入论文；
- `filtered_zero_rows > 0` 但没有说明过滤逻辑；
- formal 论文引用 `synthetic=true` 图。
- `accepted` 图缺少 `chart_type`、`x_label`、`y_label`、`unit`、
  `caption_intent`、`source_hash` 等语义字段；
- `paper.md` 中图片路径未使用 `figures/文件名.png`；
- `figures/*.png` 未登记 manifest，或 manifest 的 accepted 图实际不存在；
- 图片前后解释不足，或解释没有来自 print/results 的数值证据。

质量审查不得只看“PNG 是否存在”。无信息图表比没有图更糟，必须剔除。

### 公式、表格与正文对象硬门

formal 模式下，以下情况直接失败：

- 未闭合 `$` / `$$`，或块级公式没有独立成段；
- 公式后 5 行内没有“其中 / 参数 / 来源 / where / source”等变量说明；
- 表格为空、表头重复、数据行少于 2 行、数值列无单位；
- `paper.md` 残留模板占位符、写作指引、`Same structure`、`Interpretation 1`；
- 正文出现 `runtime/`、`output/`、`summary.json`、`execution_log`、
  `artifact_manifest` 等工程流水线痕迹。

### 分层报告

`quality_report.json` 必须包含：

```json
{
  "run_mode": "formal",
  "blocking": false,
  "status_counts": {"pass": 12, "warn": 1, "fail": 0},
  "quality_ceiling": "pass",
  "gates": [
    {
      "gate": "formula_gate",
      "item": "formula_syntax_and_explanation",
      "status": "pass",
      "detail": "...",
      "evidence": "paper.md"
    }
  ]
}
```

`blocking=true` 时不得进入正式 packaging。若用户明确要求保留不完整交付，只能降级为
`provisional_pass`，并在最终消息中明示失败项。

### quality_report.md 格式

```markdown
# 质量审查报告

| # | 检查项 | 状态 | 详情 |
|---|---|---|---|
| 1 | setup 完成 | ⚠ | setup_status=temporary_default，最高 provisional_pass |
| 2 | 运行模式合法 | ✓ | run_mode=formal，missing_inputs=[] |
| 3 | 拆题完整 | ✓ | ques_count=3，每问 ≥ 30 字 |
| 4 | 建模方案齐全 | ✓ | 已覆盖 q1/q2/q3 |
| 5 | 代码可执行 | ⚠ | 4/5 子任务 ok，q2 失败 |
| 6 | 结果文件有效 | ✓ | 共 6 个结果文件，无 synthetic formal 结果 |
| 7 | 图表有效 | ⚠ | 1 张图因全 0 被剔除，paper 未引用 |
| 8 | 章节齐全 | ✓ | 9 章俱在 |
| 9 | 文献唯一 | ✓ | 共 8 条文献，无重复 |
| 10 | 公式有效 | ✓ | 公式分隔符平衡，块级公式均有参数说明 |
| 11 | 表格有效 | ✓ | 共 4 张表，无空表或重复列 |
| 12 | 模板残留与工程泄漏 | ✓ | 无占位符和运行路径泄漏 |
| 13 | 图文绑定 | ✓ | 5 张图均有上下文解释和数值证据 |
| 14 | 产物 manifest | ✓ | packaging 前置登记完整 |

## 总体评估

通过：11 / 14
警告：3 / 14（temporary setup 时只允许 provisional）
失败：0 / 14

## 未通过项的影响

- 检查 3：q2 子任务失败 → 论文中 q2 章节可能数据不足。
- 检查 5：fig_q3_main.png 缺失 → 论文中该引用需在打包前清理或保留为占位。
```

### 状态符号

- `✓` 通过
- `⚠` 警告（非阻塞，记录但不打断）
- `✗` 失败（阻塞，必须由用户确认是否继续打包）

## 产出文件

| 路径 | 必须 | 说明 |
|---|---|---|
| `runtime/{task_id}/quality_report.md` | 是 | 质量审查结果 |

## 失败诊断

| 情况 | 处理 |
|---|---|
| `run_mode=blocked` | **打断**，不得 packaging，只输出诊断 |
| formal 模式缺必需输入 | **打断**，让用户补齐附件或授权 demo |
| setup 未确认 | 不打断，但最终等级最高 `provisional_pass` |
| 章节齐全失败 | **打断**，让用户决定是否打包不完整论文 |
| 文献唯一失败 | 不打断，记入诊断；packaging 阶段会去重提示 |
| 其他检查警告 | 不打断 |

## 下一阶段入口

`pipeline/06-packaging-output.md`。

