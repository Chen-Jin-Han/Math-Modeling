# Pipeline 01 — 题目解析

## 入口条件

- `runtime/{task_id}/` 已存在。
- `env_check.json` 已落盘。
- `run_state.json` 已落盘，`setup_status != incomplete`。
- 用户原始输入位于 `用户输入/`，并已复制到 `runtime/{task_id}/attachments/`。

## 阶段任务

1. **抽取题目原文**到 `runtime/{task_id}/problem.md`：
   - PDF：通过 `tools/pdf/SKILL.md` 调宿主 pdf skill；如未安装 pdf skill，
     退化为 `pdfplumber` 直读，并保留原 PDF 在 `attachments/`。
   - DOCX：通过 `tools/docx/SKILL.md` 提取纯文本。
   - Markdown / TXT：直接复制内容。
   - 多文件题目：按用户上传顺序合并并加分隔标题。
2. **加载 coordinator prompt** (`prompts/coordinator.md`)，输入题目原文，得到
   `intake.json`（schema 见 `references/workdir-protocol.md`）。
3. **附件清单分类**：扫描 `attachments/` 目录，把每个文件按扩展名分类
   （csv/xlsx/json/png/jpg/txt/pdf 等），写入 `intake.json.attachments`。
4. **生成附件描述**（数据驱动题）：对 csv / xlsx，调 xlsx skill 读取
   shape、列名、前 3 行预览，写入 `intake.json.attachments[i].preview`。
5. **判定必要输入是否齐全**：从题面和 `intake.json` 中识别必需附件、数据列、
   样例输入或外部数据源，写入 `run_state.json.required_inputs`。
   - 若题面明确要求附件数据而 `attachments/` 为空或缺关键文件，设置
     `run_mode=blocked`、`formal_result=false`、`can_generate_paper=false`、
     `can_package=false`，把缺项写入 `run_state.json.missing_inputs` 与
     `diagnostics.md`，并停止进入 pipeline 02。
   - 只有用户明确授权“demo / 合成数据演示 / 流程验证”时，才可设置
     `run_mode=demo`。demo 结果不得写成正式结论。
   - 输入齐全时设置 `run_mode=formal`、`formal_result=true`。
6. 更新 `runtime/{task_id}/README.md` 的相关字段。
7. **派 corpus explorer**（仅当 pipeline 00 的 corpus 域决策为 `yes`）：
   按 `tools/user-corpus-explorer/SKILL.md` 的"调度方式"派一个 subagent 扫描
   `external/user-corpus/`，产出 `external/user-corpus/AGENTS.md`。
   - 派单后**不阻塞**当前阶段，立即返回。
   - pipeline 02 启动前等待 explorer 完成（典型 30s-3min）。
   - 若 corpus 域决策为 `skip` / `later` / 未决策 → 跳过此步。

## 产出文件

| 路径 | 必须 | 说明 |
|---|---|---|
| `runtime/{task_id}/problem.md` | 是 | 题目原文（清洗后的 markdown） |
| `runtime/{task_id}/intake.json` | 是 | 拆题结构化结果 |
| `runtime/{task_id}/run_state.json` | 是 | run_mode、required_inputs、missing_inputs |
| `runtime/{task_id}/attachments/` | 是 | 用户附件副本（含预览元信息可有可无） |
| `external/user-corpus/AGENTS.md` | 视情况 | corpus 域 = yes 时由 explorer 产出 |
| `external/user-corpus/.corpus_index.json` | 视情况 | 同上，缓存 |

## 失败诊断

| 情况 | 处理 |
|---|---|
| `intake.json.is_math_modeling = false` | **打断**，输出拒绝原因，建议改用其他 skill。 |
| `intake.json.ques_count = 0` 但是是建模题 | **打断**，让用户确认 problem.md 中是否还有未识别的小问。 |
| PDF 抽取乱码 | 不打断，写诊断报告，建议用户提供文本版或重新上传。 |
| 附件读不出 | 不打断，写入 `attachments[i].error`，coder 阶段视情况绕过。 |
| 必需附件缺失 | 设置 `run_mode=blocked` 并停止；除非用户授权 demo，否则禁止合成数据兜底。 |
| corpus explorer 派单失败 | 不打断，写诊断；pipeline 02 直接走 zhanwen / 内置兜底。 |
| corpus 为空但用户选了 yes | explorer 写"corpus is empty"AGENTS.md，pipeline 继续。 |

## 下一阶段入口

`pipeline/02-modeling-plan.md`。


