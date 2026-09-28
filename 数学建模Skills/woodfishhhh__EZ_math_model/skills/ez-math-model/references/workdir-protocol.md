# Runtime Workdir Protocol

ez-math-model 面向“项目总文件夹”运行。新版本把旧 `workdir/{task_id}` 收敛为
`runtime/{task_id}`：runtime 只放中间产物，最终交付统一同步到 `output/`。

## 目录命名

```text
runtime/{YYYYMMDD-HHMMSS}-{8位 hex hash}/
```

- 时间戳精确到秒，避免同分钟内多次运行冲突。
- hash 用任务标题 + 当前时间戳的 sha1 前 8 位。
- 创建脚本：`scripts/runtime/init_workdir.ps1 -ProjectRoot <项目总文件夹>`。
- 旧版 `workdir/{task_id}` 仅作为兼容别名，不再作为新运行的默认目录。

## 标准 runtime 结构

```text
runtime/{task_id}/
├── README.md
├── project_paths.json          # 项目总文件夹、用户输入、runtime、output 映射
├── run_state.json              # setup_status、run_mode、formal_result、missing_inputs
├── setup_assumptions.json      # 仅 temporary_default 时存在
├── env_check.json
├── tools_status.json
├── problem.md
├── intake.json
├── attachments/                # 从 用户输入/ 复制来的原始附件副本
├── modeling_plan.md
├── thesis_match.json
├── src/
├── results/
├── figures/
│   └── chart_manifest.json
├── execution_log.md
├── paper.md
├── quality_report.md
├── quality_report.json
├── diagnostics.md
├── export_report.json
├── export_audit.md
├── export_audit.json
├── artifact_manifest.json
├── logs/
├── tmp/
└── deliverable.zip             # output.zip 的兼容副本，可选
```

## 标准 output 结构

```text
output/
├── source code/
│   └── src/
├── paper/
│   ├── paper.md
│   ├── paper.docx
│   ├── paper.txt
│   └── paper.pdf
├── 附件文件夹/
│   ├── figures/
│   ├── results/
│   ├── attachments/
│   ├── 质量检查报告.md
│   ├── 失败诊断.md
│   ├── export_report.json
│   ├── export_audit.json
│   ├── 导出对象审查.md
│   └── run_state.json
└── manifest.json
```

项目总文件夹根目录最终还必须有 `output.zip`，内容为项目总文件夹内全部内容
（排除 `output.zip` 自身）。

## run_state.json schema

```json
{
  "task_id": "...",
  "run_mode": "formal | demo | blocked",
  "formal_result": true,
  "setup_status": "user_confirmed | temporary_default | skipped | incomplete",
  "required_inputs": [],
  "missing_inputs": [],
  "can_generate_paper": true,
  "can_package": true,
  "created_at": "..."
}
```

## intake.json schema

```json
{
  "is_math_modeling": true,
  "title": "...",
  "background": "...",
  "ques_count": 3,
  "ques1": "...",
  "ques2": "...",
  "ques3": "...",
  "contest": "cumcm | mcm | gradmcm | unknown",
  "year": 2024,
  "problem_letter": "B",
  "attachments": [{"name": "data.csv", "kind": "csv", "note": "..."}],
  "required_inputs": [{"name": "graph data files", "reason": "题面要求附件图数据"}],
  "language": "zh"
}
```

## thesis_match.json schema

由 `scripts/runtime/match_thesis.py` 产出：

```json
{
  "match_level": "exact | year | series | fallback | internal",
  "thesis_dir": "<绝对路径或 INTERNAL>",
  "template_dir": "<绝对路径或 INTERNAL>",
  "signals": {"contest": "cumcm", "year": 2024, "problem": "B"},
  "checked_at": "2026-05-19T10:30:00+08:00"
}
```

## quality_report 必备字段

质量报告分为 `quality_report.json` 与 `quality_report.md`。JSON 是机器可审查的
单一事实源，Markdown 是人读摘要。固定分层检查如下（细节见
`pipeline/05-quality-audit.md`）：

| 检查项 | 通过条件 |
|---|---|
| setup 完成 | `setup_status=user_confirmed` 才可正式通过 |
| 运行模式合法 | `run_mode` 为 formal/demo/blocked，formal 不缺关键输入 |
| 拆题完整 | `intake.json.ques_count > 0` 且每个 quesN 文本 ≥ 30 字 |
| 建模方案齐全 | `modeling_plan.md` 包含每个 quesN 的方案小节 |
| 代码可执行 | `execution_log.md` 中脚本最终状态 `ok` 占比 ≥ 50% |
| 结果文件有效 | `results/` 至少有 1 个 CSV 或 JSON，formal 结果无 `synthetic=true` |
| 图表有效 | `chart_manifest.json` 存在，paper 只引用 `usable_in_paper=true` 图 |
| 章节齐全 | formal 论文含摘要、问题重述、问题分析、模型假设、符号说明、模型建立与求解、敏感性、模型评价、参考文献 |
| 文献唯一 | `paper.md` 中 `[^N]` 编号无重复定义 |
| 公式有效 | 公式分隔符平衡、块级公式独立成段、参数来源可追溯 |
| 表格有效 | 表头完整、至少 2 行数据、无重复表头、数值列有单位 |
| 模板残留与工程泄漏 | 正文无占位符、写作指引、runtime/output/manifest 等工程痕迹 |
| 图文绑定 | 每张图前后有解释，解释含来自 print/results 的数值证据 |
| 产物 manifest | 必登产物存在、类型正确、formal 标记与 run_mode 一致 |

`quality_report.json` 必须包含 `run_mode`、`blocking`、`status_counts`、
`quality_ceiling` 和 `gates[]`。每个 gate 必须包含 `gate`、`item`、`status`、
`detail`、`evidence`。

## export_audit.json

packaging 阶段导出后必须生成对象审查报告：

```json
{
  "run_mode": "formal",
  "blocking": false,
  "quality_ceiling": "pass",
  "metrics": {
    "markdown_image_refs": 5,
    "markdown_block_formulas": 8,
    "markdown_tables": 4,
    "docx_formula_objects_count": 8,
    "embedded_image_count": 5,
    "docx_table_count": 4,
    "pdf_fallback": false,
    "pdf_readability": "pandoc_pdf"
  }
}
```

formal 模式下，`blocking=true` 不得发布正式包。

## diagnostics.md

无失败时仍然存一份空的诊断说明，便于打包阶段一致地包含此文件：

```markdown
# 失败诊断

无失败项。本次运行所有阶段均通过。
```

有失败时按以下结构记录：

```markdown
# 失败诊断

## 阶段：03-coding-solve
- 脚本：q2_solve.py
- 时间：2026-05-19T11:02:13+08:00
- 错误摘要：[一行]
- 已尝试：[简述重试逻辑]
- 影响：q2 的结果不可作为正式结论
- 用户建议动作：补充附件 data.csv / 安装 xgboost / 授权 demo ...
```

## 路径安全

- runtime 路径不得包含上级跳转（`..`）。
- `用户输入/` 只读，所有处理都在 `runtime/{task_id}/attachments/` 副本上进行。
- 所有相对路径以 `runtime/{task_id}` 为根。
- 禁止把 runtime 创建在 skill 安装目录；默认应位于项目总文件夹下。

## 重试与续跑

- 每个 pipeline 阶段开始时检查自身入口条件文件是否齐全，缺失直接打断。
- 若用户希望从中间阶段重跑，可复制对应 `runtime/{task_id}` 后从该阶段启动。
- packaging 阶段必须重新同步 `output/`，不能只复用旧 `deliverable.zip`。
- packaging 必须先写入 staging 输出目录，临时 zip 验证通过后再发布；失败时保留旧
  `output/`。
- 新 `output.zip` 不得包含历史 `runtime/*/deliverable.zip`，避免 stale artifact 嵌套。
