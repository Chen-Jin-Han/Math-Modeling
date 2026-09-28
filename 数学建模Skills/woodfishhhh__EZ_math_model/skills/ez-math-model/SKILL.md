---
name: ez-math-model
description: Use when solving CUMCM, MCM, ICM, or other mathematical modeling tasks that need contest problem intake, model selection, Python solving, figures, paper writing, quality audit, and packaged deliverables.
license: MIT
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch
metadata:
  display_name: EZ Math Model
  type: workflow-skill
  version: 1.2.0
  author: woodfishhhh
  repository: https://github.com/woodfishhhh/EZ_math_model
  language_default: zh
  python_min_version: "3.10"
  marketplace_ready: true
read_when:
  - 用户请求"数学建模"、"数模"、"建模求解"、"建模分析"、"数模论文"
  - 题面提到 "CUMCM"、"全国大学生数学建模"、"国赛"、"高教社杯"
  - 题面提到 "MCM"、"ICM"、"美赛"、"COMAP"
  - 题面提到 "研究生数学建模"、"华为杯"
  - 用户上传 PDF / DOCX / Markdown 题目，且题面包含建模特征（多小问、附数据集、要求建立模型）
---

# ez-math-model

数学建模一站式 skill。把题目交给我，我会自动走完七个阶段：setup → 题目解析 →
建模方案 → 代码求解 → 论文撰写 → 质量审查 → 标准打包交付。首次使用必须完成 setup
提问；完成后写入 `external/tools/setup_state.json`。未经用户确认，只能使用本次临时默认，
不得写永久配置。

## 一句话主流程

> 收到题目 → 识别项目总文件夹 → 检查 `external/tools/setup_state.json` →
> 创建 `用户输入/runtime/output` 标准目录 → 判定 `formal/demo/blocked` →
> 识别赛事/年份/题号 → 选择模型 → 写脚本并执行 → 出图并过 chart gate →
> 写论文 → 跑对象级质量门 → staging 导出与审查 → 原子同步到 `output/` 并打包
> `output.zip`。

## 触发后的第一动作

先读以下七份文件确认本次运行的契约：

1. `pipeline/00-environment-setup.md` — 验环境（Python、字体、工作目录、上游缓存状态）
2. `references/project-root-protocol.md` — 项目总文件夹与 `用户输入/runtime/output`
3. `references/setup-policy.md` — setup 硬门与临时默认边界
4. `references/run-mode-protocol.md` — `formal/demo/blocked` 判定
5. `references/workdir-protocol.md` — runtime 产物结构与命名
6. `references/chart-quality-gate.md` — 图表有效性门
7. `references/artifact-manifest.md` — 产物 manifest 契约

formal 交付不得只检查“文件是否存在”。质量门必须覆盖图表语义、公式语法、
表格对象、优秀论文格式抽取、正文工程痕迹、DOCX/PDF 对象级导出和 zip/manifest
一致性。

然后立刻执行 setup gate：

- 读取 `external/tools/setup_state.json`。
- 若文件不存在、JSON 无法解析、`setup_completed` 不是 `true`，或用户说"重新配置工具 /
  重置 setup / 重新 setup"，**必须先运行 pipeline 00 的强制提问**，禁止进入
  pipeline 01、建模、写代码或写论文。
- setup 提问完成后，必须写入 `external/tools/setup_state.json`，再继续本次任务。
- 若 `setup_completed: true`，默认跳过交互式 setup，只做本次任务所需的轻量环境检查
  和工作目录创建。

不要用"默认不追问"绕过首次 setup；首次 setup 是硬门禁。若用户要求继续但无法
完成交互式 setup，只能写 `runtime/{task_id}/setup_assumptions.json`，并把
`setup_status` 标为 `temporary_default`，最终质量等级最高为 `provisional_pass`。

## Pipeline 索引

| # | 文件 | 入口条件 | 关键产出 |
|---|---|---|---|
| 00 | `pipeline/00-environment-setup.md` | 用户给出题目或附件；setup gate 未完成时必须先问 | setup 状态明确、`runtime/` 创建完成、env-check 通过 |
| 01 | `pipeline/01-problem-intake.md` | env-check 通过 | `runtime/.../problem.md`、`intake.json`、`attachments/`、`run_state.json` |
| 02 | `pipeline/02-modeling-plan.md` | intake 完成 | `modeling_plan.md`、（首次询问 zhanwen 拉取） |
| 03 | `pipeline/03-coding-solve.md` | modeling_plan 落盘 | `src/*.py`、`results/*`、`figures/*.png` |
| 04 | `pipeline/04-paper-writing.md` | coding 完成 | `paper.md` |
| 05 | `pipeline/05-quality-audit.md` | paper.md 落盘 | `quality_report.json`、`quality_report.md`（含证据与未通过项） |
| 06 | `pipeline/06-packaging-output.md` | 质量门评估完成 | `export_report.json`、`export_audit.json`、`output/paper/*` 四格式、`output/manifest.json`、`output.zip` |

## 角色 prompt 索引

需要在阶段中扮演具体角色时载入：

| 角色 | 文件 | 用途 |
|---|---|---|
| coordinator | `prompts/coordinator.md` | 拆题，识别赛事/年份/题号/小问 |
| modeler | `prompts/modeler.md` | 建模分析，模型选择树 + 物理可行性 |
| coder | `prompts/coder.md` | 写脚本、出图、防数据泄露、参数有据 |
| writer | `prompts/writer.md` | 写论文，段落式、图必引、文献唯一编号 |

## 角色守则索引

执行阶段开始前必读对应角色守则（比 prompt 更关注流程纪律）：

- `references/roles/modeler-guide.md`
- `references/roles/coder-guide.md`
- `references/roles/writer-guide.md`

## 模板索引

- `templates/paper_zh.md` — 中文 CUMCM 论文 markdown 兜底模板
- `templates/paper_en.md` — 英文 MCM/ICM 论文 markdown 兜底模板
- `templates/chapter_outline.toml` — 章节占比与必备小节
- `templates/readme_workdir.md` — 任务工作目录的 README 模板

## 算法库索引

`references/algorithms/README.md` 提供「问题类型 → 推荐算法」速查表；按类别细看：

01 优化 / 02 预测 / 03 评价 / 04 图论 / 05 统计 / 06 综合 / 07 机器学习。

## 优秀论文样例

`references/exemplar-papers/` 下提供 7 篇 CUMCM / MCM 优秀论文的 markdown
摘录（由 MinerU 从 zhanwen/MathModel 转换，前 20 页）。modeler 与 writer
在动笔前应读取与本题最相关的 1-2 篇，抽取格式规则并写
`style_reference_notes.md`，**仅作风格 / 章节 / 表述参考**，禁止照抄或同义改写。
索引详见 `references/exemplar-papers/README.md`。

## 容错与失败处理

`references/fault-tolerance.md` 是单一信息源，定义 4 层容错：
L1 Bounded Retry / L2 Fallback Switch / L3 Evaluator Shadow / L4 Feedback
Rerun。每个 pipeline 阶段都遵守同一套容错协议，绝不死循环。

## Agent 工作模式

`references/agent-mode.md` 单一信息源，定义三种工作模式：

- **single**：所有阶段在主对话顺序推进；上下文压力大但失败定位最容易
- **multi**：每个独立子任务派 subagent 并行；并发强但 token 成本高
- **hybrid（默认）**：关键阶段主对话、琐碎阶段 subagent；兼顾稳定与并发

pipeline 00 首次会强制询问，决策落到 `external/tools/setup_state.json` 与
`external/tools/agent_mode.{single,multi,hybrid}`。

## 继承的辅助 Skills

ezmm 内置 9 个辅助子 skills（在用户机器上检测到才启用）：

| 子 skill | 何时调 |
|---|---|
| `tools/humanizer/SKILL.md` | writer 后去 AI 味 |
| `tools/simplify/SKILL.md` | coder 后做代码精简 |
| `tools/scientific-slides/SKILL.md` | 答辩 PPT |
| `tools/systematic-debugging/SKILL.md` | coder 失败的根因分析 |
| `tools/brainstorming/SKILL.md` | modeler 决策卡住时 |
| `tools/external-context/SKILL.md` | multi/hybrid 模式下并行多领域查文献 |
| `tools/dispatching-parallel-agents/SKILL.md` | multi/hybrid 派单方法论 |
| `tools/subagent-driven-development/SKILL.md` | 扩展 ezmm 本身（非建模题） |
| `tools/verification-before-completion/SKILL.md` | quality_audit 强化 |

宿主未安装对应 skill 时，子 skill 文档给出降级方案。详见
`references/external-tools-catalog.md` 与各子 skill 文件。

## 共享 Prompt 协议

`prompts/shared.md` 是所有角色 prompt 隐含加载的通用约束（输出语言 / JSON
格式 / 工具调用 / 反思 / 失败重试 / 段落式 / 引用编号 等），角色 prompt 不
重复列举。

## 子工具 Skills

ez-math-model 不内嵌 docx/pdf/xlsx/paper-search 实现，而是通过子 skill 协议
调用宿主已安装的同名 skill 或公共 API：

| 域 | 文件 | 何时用 |
|---|---|---|
| Word 转换 | `tools/docx/SKILL.md` | paper.md → paper.docx |
| PDF 提取（基础） | `tools/pdf/SKILL.md` | 题目 / 论文 PDF 转文本 |
| **PDF 高质量解析** | `tools/mineru/SKILL.md` | 含表格 / 公式的中文学术 PDF |
| 表格附件 | `tools/xlsx/SKILL.md` | csv / xlsx 读写 |
| 文献检索（基础） | `tools/paper_search/SKILL.md` | OpenAlex 单源 |
| **多源学术搜索** | `tools/scholar/SKILL.md` | OpenAlex + arXiv + S2 + SerpAPI 聚合 |
| **论文写作编排** | `tools/paper-orchestra/SKILL.md` | writer 阶段调用 PaperOrchestra 子 skill 做大纲、文献、成文与精修 |
| **数据集发现** | `tools/dataset/SKILL.md` | Kaggle / UCI / HuggingFace / 天池 |
| **网页抓取** | `tools/webcrawl/SKILL.md` | Jina / Firecrawl / Tavily / Exa |
| **用户自带 corpus** | `tools/user-corpus-explorer/SKILL.md` | 扫 `external/user-corpus/`，产出 AGENTS.md |

外部工具的元信息（价格 / 配额 / 何时启用）单一信息源在
`references/external-tools-catalog.md`。

## 外部工具配置

启用付费 / 注册类工具前，pipeline 00 会在首次使用时**强制问一次**，按 7 个域
分组询问，每组给固定选项。决策落到 `external/tools/setup_state.json`，永久缓存；
后续默认不再进入交互式 setup。详见 `pipeline/00-environment-setup.md`。

env var 一律以 `EZMM_` 开头，写入用户级 `~/.ezmm.env`（参考仓库根
`.env.example`），**绝不**提交到 git。

7 个域：`pdf` / `scholar` / `dataset` / `webcrawl` / `corpus` / `agent_mode` / `inherited_skills`。

## 用户自带参考资料

仓库内 `external/user-corpus/` 是给你专门的投放区。把想让 ez-math-model
参考的论文、教材、笔记、历年题解直接拖进去（不限格式 / 层级 / 文件名），
启用后 pipeline 01 末尾派 subagent 扫描，产出 `AGENTS.md` 给 modeler /
writer 用。详见 `tools/user-corpus-explorer/SKILL.md` 与 `external/user-corpus/README.md`。

## zhanwen/MathModel 集成

`scripts/install/fetch_zhanwen.ps1` / `.sh` 负责按需拉取上游优秀论文与模板。
匹配协议见 `scripts/runtime/match_thesis.py`：(赛事, 年份, 题号) → 同年份 →
同赛事最新年份 → 全局最新 → 内置 markdown 兜底，五级回落，命中即返回。

询问只发生一次，发生在 pipeline 02 入口。`.skip` 标记存在时永久跳过询问。
`.failed` 标记存在时直接走内置兜底，不再重试拉取。

## 失败兜底矩阵

| 失败点 | 处理 |
|---|---|
| Python 不可用 | 打断，提示用户安装 Python ≥ 3.10 |
| 题目无法解析（intake 阶段） | 打断，把已读到的内容存入 `problem.md` 并请求人确认 |
| zhanwen 拉取失败 | 写 `.failed`，pipeline 切到内置模板兜底，**不打断** |
| 单段代码执行失败 | coder 自动重试至多 2 轮（参考 `pipeline/03-coding-solve.md`），仍失败则记入 `diagnostics.md` 并继续 |
| 单张图生成失败 | 该绘图尝试写入 chart manifest 的 rejected 记录，论文中跳过，写 `quality_report.md` 标记缺图，**不打断** |
| 论文章节缺失 | 质量门记入 `quality_report.md`；formal 模式阻塞正式打包，demo 可降级打包 |
| docx 公式/图片/表格对象审查失败 | formal 模式阻塞正式发布；demo 模式降级并写 `diagnostics.md` |

## 运行模式与交付结构

每次运行都必须显式记录 `run_mode`：

- `formal`：真实输入齐全，可写正式结论。
- `demo`：用户允许用合成/示例数据验证流程，不得写正式结果。
- `blocked`：缺关键输入且未授权 demo，停止并输出诊断。

最终交付必须同步到：

```text
output/
├── source code/
├── paper/
│   ├── paper.md
│   ├── paper.docx
│   ├── paper.txt
│   └── paper.pdf
└── 附件文件夹/
```

每次运行仍新建 `runtime/{YYYYMMDD-HHMMSS}-{8位hash}/`，所有中间产物落在其中，
便于失败定位和重试。详见 `references/project-root-protocol.md` 与
`references/workdir-protocol.md`。


