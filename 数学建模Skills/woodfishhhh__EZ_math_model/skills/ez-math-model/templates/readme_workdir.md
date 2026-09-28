# 任务工作目录 README

> 此 README 由 `scripts/runtime/init_workdir.ps1` 在创建工作目录时落盘。
> 占位字段会被替换为本次任务的实际值。

## 任务元信息

- 任务 ID：`{task_id}`
- 创建时间：`{created_at}`
- 题目标题：`{title}`
- 赛事 / 年份 / 题号：`{contest}` / `{year}` / `{problem_letter}`
- 输入语言：`{language}`
- 用户附件数：`{attachment_count}`

## 阶段产出索引

| 阶段 | 主要产物 | 状态 |
|---|---|---|
| 01 intake | `problem.md`, `intake.json`, `attachments/` | `{stage_01_status}` |
| 02 modeling | `modeling_plan.md`, `thesis_match.json` | `{stage_02_status}` |
| 03 coding | `src/`, `results/`, `figures/`, `execution_log.md` | `{stage_03_status}` |
| 04 paper | `paper.md` | `{stage_04_status}` |
| 05 quality | `quality_report.md` | `{stage_05_status}` |
| 06 packaging | `output/paper/*`, `output/manifest.json`, `output.zip`, `diagnostics.md` | `{stage_06_status}` |

## zhanwen 上游匹配

- match_level：`{match_level}`
- thesis_dir：`{thesis_dir}`
- template_dir：`{template_dir}`

## 重新打开此任务

阅读顺序建议：

1. `intake.json` 看拆题结果。
2. `modeling_plan.md` 看建模思路。
3. `paper.md` 看最终论文。
4. `quality_report.md` 看质量门哪些项未通过。
5. `diagnostics.md` 看失败诊断。
6. `project_paths.json` 看最终 `output/` 与 `output.zip` 的位置。
