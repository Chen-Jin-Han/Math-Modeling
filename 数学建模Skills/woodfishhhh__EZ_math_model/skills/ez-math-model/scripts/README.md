# scripts/

ez-math-model 的辅助脚本。pipeline 的 7 个阶段通过这里调用确定性子操作，
LLM 不直接执行 git / 文件系统重活。

## 安装类（install/）

| 脚本 | 平台 | 用途 | 输入 | 输出 |
|---|---|---|---|---|
| `fetch_zhanwen.ps1` | Windows | 拉取上游 zhanwen/MathModel 的 sparse 子集 | 无（参数 `-Force` 强制刷新） | 写入 `external/zhanwen-mathmodel/` 子目录 + `.complete` 或 `.failed` 标记 |
| `fetch_zhanwen.sh` | POSIX | 同上 | 同上（`--force`） | 同上 |
| `verify_environment.ps1` | Windows | 检查 Python / Git / 关键库 / 字体 / zhanwen 状态 | `-Out <path>` 可选 | stdout 或文件中的 JSON |

### fetch_zhanwen 行为契约

1. 若存在 `.skip` 标记 → 直接退出，返回码 0。
2. 若存在 `.complete` 标记且未传 `-Force` → 直接退出，返回码 0。
3. git 不可用 → 写 `.failed`，返回码 1。
4. clone 或 sparse-checkout 失败 → 恢复 .gitkeep / README.md / .skip 后写
   `.failed`，返回码 1。
5. 拉取成功但所有预期目录都不存在（上游目录改名） → 写 `.failed`，返回码 1。
6. 拉取成功 → 删除 `.failed`，写 `.complete`，返回码 0。

`.failed` 文件的 body 包含错误时间戳与简要原因；`.complete` 文件的 body 包
含拉取时间戳与 `repo` URL。

## 运行时（runtime/）

| 脚本 | 平台 | 用途 | 输入 | 输出 |
|---|---|---|---|---|
| `init_workdir.ps1` | Windows | 创建 `runtime/{YYYYMMDD-HHMMSS}-{8位hash}/` 骨架、标准 `用户输入/runtime/output` 目录并渲染 README | `-ProjectRoot -Title -Language -Contest -Year -ProblemLetter` | stdout JSON `{task_id, task_dir, output_root}` |
| `match_thesis.py` | 任意 Python | 题目纯文本 → 上游优秀论文路径匹配 | stdin 或 `--problem-text`，`--root` 指定仓库根 | stdout JSON（schema 见 `references/workdir-protocol.md`） |
| `audit_quality.py` | 任意 Python | pre-export 质量门：正文、图文、公式、表格、模板残留 | `--workdir <runtime task dir>` | `quality_report.json/md`，blocking 时返回非零 |
| `export_paper.ps1` | Windows | 把 `paper.md` 导出到 `output/paper/paper.md|docx|txt|pdf` 并统计对象指标 | `-WorkDir <runtime task dir>` | stdout JSON + `export_report.json` |
| `audit_export.py` | 任意 Python | post-export 对象审查：DOCX 图片/公式/表格，PDF 可读性 | `--workdir <runtime> --paper-output <dir>` | `export_audit.json/md`，blocking 时返回非零 |
| `pack_deliverable.ps1` | Windows | staging 原子发布 runtime 产物到 `output/` 并生成项目根目录 `output.zip` | `-WorkDir <runtime task dir>` | stdout 输出 zip 路径 |

### match_thesis.py 测试样例

| 输入 | 期望 match_level | 期望 thesis_dir 关键片段 |
|---|---|---|
| `2023 国赛 B 题` | exact | `2023年优秀论文/B题` |
| `2010 高教社杯` | year | `2010年优秀论文` |
| `MCM 美赛 题目内容...` | series | `美赛论文/{最新年}美赛特等奖原版论文集` |
| `Problem A continuous...` | exact / year | `美赛论文/{年}美赛...` |
| `求函数 f(x) 的最值` | fallback | `2024年数模悉知&论文模版/`（最新一年的模板包） |
| zhanwen 未下载（`.complete` 不存在） | internal | `INTERNAL` |

5 级回落优先级：`exact > year > series > fallback > internal`。命中即返回。

## POSIX 等价脚本

`init_workdir.ps1` / `export_paper.ps1` / `pack_deliverable.ps1` / `verify_environment.ps1` 当前
仅给 Windows 版。POSIX 用户可手动用 `bash` + `python` 实现等价效果，未来按
需补 `.sh` 版本（不影响现版功能）。

## 错误约定

所有脚本遵循"不抛黑天鹅"原则：可预期失败（git 不可用、网络不可达、附件
不可读）必须写诊断标记或返回非零码 + stderr 一行说明，绝不允许 PowerShell
ErrorActionPreference 默认抛出红色异常打断 LLM。
