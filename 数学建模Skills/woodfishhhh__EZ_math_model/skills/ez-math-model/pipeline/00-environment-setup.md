# Pipeline 00 — Setup Gate + 环境检查 + 项目目录初始化

## 入口条件

- 用户给出题目（文本 / PDF / DOCX / Markdown）或附件。
- 当前项目总文件夹可写。

## 硬门禁：首次必须 setup

在任何题目解析、建模、写代码、写论文之前，必须先检查：

```
external/tools/setup_state.json
```

处理规则：

1. 文件不存在、JSON 无法解析、`setup_completed` 不是 `true`，或
   `schema_version` 不是 `"1.0"`：进入 **首次 setup**，必须向用户提问。
2. 用户说"重新配置工具"、"重置 setup"、"重新 setup"：忽略旧状态，重新提问。
3. `setup_completed: true` 且用户没有要求重置：默认跳过交互式 setup，只执行本次
   任务的轻量环境检查和工作目录创建。
4. 旧版 `.tools_decided` 或 `<domain>.free/skip/yes` 标记只能作为迁移线索；若没有
   `setup_state.json`，必须先创建 JSON 状态，不能只看旧标记就继续。

禁止在 setup gate 未完成时进入 `pipeline/01-problem-intake.md`。

## 阶段任务

按顺序执行 1-10：

1. 识别项目总文件夹，按 `references/project-root-protocol.md` 创建
   `用户输入/`、`runtime/`、`output/`、`output/source code/`、`output/paper/`、
   `output/附件文件夹/`。
2. 创建本次任务的运行目录：调用
   `scripts/runtime/init_workdir.ps1 -ProjectRoot <project_root>`。命名规则见
   `references/workdir-protocol.md`。
3. 执行 setup gate：读取或创建 `external/tools/setup_state.json`。若未完成 setup，
   必须向用户提问；未经用户确认不得写永久 marker。若用户要求本次先继续，只能写
   `runtime/{task_id}/setup_assumptions.json`，并设置 `setup_status=temporary_default`。
4. 检查 Python 可用：`python --version` ≥ 3.10。
5. 检查关键库：`numpy pandas matplotlib seaborn scipy scikit-learn`。缺失给出
   一行 `pip install` 提示，但**不自动安装**。
6. 检查中文字体：尝试 `SimHei` / `Noto Sans CJK SC` / `Heiti SC`，写入
   `env_check.json`。
7. 检查 git 与 zhanwen 缓存状态：`external/zhanwen-mathmodel/.complete` /
   `.failed` / `.skip` 标记是否存在。
8. 首次 setup 时执行**工具发现 + 强制询问**（详见下文）；已完成 setup 时只扫描状态，
   不再追问。
9. 根据 setup 结果写入 `runtime/{task_id}/run_state.json` 的 `setup_status`。
10. 写入 `runtime/{task_id}/env_check.json` 与 `runtime/{task_id}/tools_status.json`。

## 工具发现节点（关键）

### 触发时机

必须在以下情况询问：
- `external/tools/setup_state.json` 不存在。
- `setup_state.json` 解析失败、`setup_completed` 不是 `true`，或 schema 不匹配。
- 用户显式说"重新配置工具"、"重置 setup"、"重新 setup"。

之后默认不再追问；旧版 `.tools_decided` 标记不能替代 `setup_state.json`。

### 第一步：扫描

调 `scripts/install/discover_tools.ps1 -Out runtime/{task_id}/tools_status.json`。
该脚本读 env var、检查命令行可用性，输出四个能力域的状态。

### 第二步：分组询问

向用户**一次性**展示四组工具（详见 `references/external-tools-catalog.md`）。
**先解释好处再问选择**，每组给 4 个选项：

> **🔧 PDF 解析（建议启用 MinerU）**
> 默认链路 = pdfplumber，对纯文本 PDF 够用。但如果题目 PDF 含表格 / 公式 /
> 复杂排版，pdfplumber 输出常乱序。**MinerU 三种部署全部免费**：
> - 本地 CLI（推荐）：`pip install mineru`，离线运行，无配额，**完全免费 + 开源**。
> - 云 API：注册即送免费 token + 调用配额，超额才付费。
> - 网页 flash：零注册，限 ≤10MB / ≤20 页，临时单文件用。
>
> 当前状态：`mineru_cli={...}` `mineru_token={...}`
> 选择：
>   - `yes` 现在装本地 CLI 或配置云 API token
>   - `free-only` 仅启用已检测到的免费链路（本地 CLI 已装则用之；否则走 pdfplumber）
>   - `skip` 本次不用，走 pdfplumber 兜底
>   - `later` 暂跳过，下次再问

> **🔧 学术搜索（建议至少启用免费三件套）**
> writer 阶段写理论性章节、引用文献时使用。
> - **OpenAlex（免费）**：覆盖度最高，**强烈推荐**。可选填邮箱提配额。
> - **arXiv（免费）**：数学 / CS 预印本，零配置即可。
> - **Semantic Scholar（免费）**：引用图谱强，可选填 API key 翻倍配额。
> - **SerpAPI（付费）**：替代谷歌学术 / 百度学术 API，5000 次免费试用。
>
> 当前状态：`openalex_email={...}` `s2_api_key={...}` `serpapi_key={...}`
> 选择：
>   - `yes` 配置我有 key 的项（OpenAlex 邮箱 / S2 / SerpAPI）
>   - `free-only` 仅启用免费默认（OpenAlex + arXiv + S2 公共配额）
>   - `skip` 本次不用文献检索，writer 改用通用文献模板
>   - `later` 暂跳过

> **🔧 数据集发现（仅当题目要求自找数据时启用）**
> 题目附件已含数据 → 不需要本组工具。
> - **Kaggle**：覆盖广、有 EDA notebook 参考。需要 `~/.kaggle/kaggle.json`。
> - **HuggingFace Datasets**：NLP / 多模态。
> - **UCI ML / 天池**：免费，无需 key。
>
> 当前状态：`kaggle_credentials={...}` `hf_token={...}`
> 选择：
>   - `yes` 配置 Kaggle / HF token
>   - `free-only` 仅启用免 key 源（UCI / 天池 / Kaggle 公开搜索）
>   - `skip` 本次不需要补外部数据
>   - `later` 暂跳过

> **🔧 网页抓取（题目涉及行业 / 政策背景时启用）**
> 题目纯数学 / 物理机理 → 不需要本组工具。
> - **Jina Reader（免费、零配置）**：单页 URL → markdown。
> - **Firecrawl（付费 + 免费额度）**：批量爬整站。
> - **Tavily / Exa（付费 + 免费额度）**：LLM-friendly 搜索。
>
> 当前状态：`firecrawl_key={...}` `tavily_key={...}` `exa_key={...}`
> 选择：
>   - `yes` 配置我有 key 的项
>   - `free-only` 仅启用 Jina（无需 key）
>   - `skip` 本次不需要外部网页参考
>   - `later` 暂跳过

> **🔧 用户自带参考资料（强烈推荐启用）**
> 仓库内有专门的投放文件夹 `external/user-corpus/`，你想让 ez-math-model
> 参考的论文、教材、笔记、历年题解，**直接拖进去即可**，不限文件名 / 不限
> 层级 / 不限格式（PDF / DOCX / Markdown / TXT / 图片都行）。
>
> 启用后：pipeline 01 末尾派一个 corpus explorer subagent 扫描该文件夹，
> 产出 `external/user-corpus/AGENTS.md`，作为 modeler / writer 的"用户钦定
> 参考"。**有缓存机制**，未变更的文件不重读，反复运行成本极低。
>
> 当前状态：`corpus_files_count={...}`（即时扫到的文件数量）
> 选择：
>   - `yes` 启用 corpus，pipeline 01 末尾派 explorer 扫描
>   - `skip` 本次不用，下次仍会问
>   - `later` 暂跳过，等想好放什么再启用

> **🔧 Agent 工作模式（影响整个 pipeline 的执行方式）**
> ez-math-model 的 7 个阶段可在三种模式间选。详细对比见
> `references/agent-mode.md`。**先讲优缺点再问选择**：
>
> - **single（单 Agent）**：所有阶段在主对话顺序推进。优点：失败定位最容易、
>   token 成本最低、零学习曲线；缺点：上下文压力大（>4 小问可能爆）、无并发、
>   总耗时长。**适合**：1-2 小问 / 物理机理题 / 用户偏好"看着每一步"。
> - **multi（多 Agent / Subagent）**：每个独立子任务派 subagent 并行。优点：
>   并发能力强（5+ 并行）、主对话上下文压力小、subagent 失败可独立重跑；
>   缺点：token 成本高（每个 subagent 重读 prompt）、失败定位难、需要派单
>   协议。**适合**：≥ 4 小问 / 数据驱动大题 / 主对话上下文已紧张。
> - **hybrid（混合，默认推荐）**：关键阶段（modeling / writing / packaging）
>   主对话直接做，琐碎阶段（coding 子任务 / corpus explorer / 文献检索）
>   subagent。优点：兼顾稳定与并发；缺点：协调略复杂。**适合**：默认通用。
>
> 当前状态：`agent_mode_decided={...}`（已决策的模式）
> 选择：
>   - `single` 单 Agent 顺序推进
>   - `multi` 全部派 subagent
>   - `hybrid` 混合模式（推荐默认）
>   - `later` 本次先按 hybrid 跑，下次再问

> **🔧 继承的辅助 Skills（按需启用）**
> ez-math-model 内置了 9 个外部 skills 的子 skill 协议，覆盖辅助场景。它们都是
> 可选的"加分项"，未安装也不影响主流程。
>
> | skill | 子 skill | ezmm 中的角色 |
> |---|---|---|
> | humanizer | tools/humanizer/SKILL.md | writer 后去 AI 味 |
> | simplify | tools/simplify/SKILL.md | coder 后做代码精简 |
> | scientific-slides | tools/scientific-slides/SKILL.md | 答辩 PPT |
> | systematic-debugging | tools/systematic-debugging/SKILL.md | coder 失败的根因分析 |
> | brainstorming | tools/brainstorming/SKILL.md | modeler 决策卡住时 |
> | external-context | tools/external-context/SKILL.md | 多领域并行查文献 |
> | dispatching-parallel-agents | tools/dispatching-parallel-agents/SKILL.md | multi/hybrid 派单方法论 |
> | subagent-driven-development | tools/subagent-driven-development/SKILL.md | 扩展 ezmm 本身（非建模题） |
> | verification-before-completion | tools/verification-before-completion/SKILL.md | quality_audit 强化 |
>
> 当前状态：`inherited_skills_detected={...}`（discover_tools 扫到的可用 skill）
> 选择：
>   - `yes` 开启全部检测到的辅助 skill（推荐）
>   - `recommended` 仅开启核心三件套（humanizer / verification-before-completion / systematic-debugging）
>   - `skip` 本次都不用辅助 skill
>   - `later` 暂跳过

### 第三步：落 JSON 状态

只在用户明确完成并确认保存 setup 后，才写入 `external/tools/setup_state.json`，
同时可继续写旧版标记文件以兼容现有子文档。若用户没有完成 setup，但要求本次
先继续，只能写入 `runtime/{task_id}/setup_assumptions.json`，不得写永久 marker。

| 用户选择 | 落盘 |
|---|---|
| `yes` 但需配置 | 用户确认保存后，引导用户在 `~/.ezmm.env` 写 env var，提示 "配置完成后说 'reload tools'" |
| `free-only` | 用户确认保存后，写 `external/tools/<domain>.free` |
| `skip` | 用户确认保存后，写 `external/tools/<domain>.skip` |
| `later` | 不写任何永久标记，下次入口仍会问 |

七个域决定后写 `external/tools/setup_state.json`；若没有 `setup_completed: true`，
下次入口仍必须问。

最小 JSON：

```json
{
  "schema_version": "1.0",
  "setup_completed": true,
  "completed_at": "2026-05-20T18:00:00+08:00",
  "completed_by": "ez-math-model",
  "decisions": {
    "pdf": "free-only",
    "scholar": "free-only",
    "dataset": "skip",
    "webcrawl": "skip",
    "corpus": "skip",
    "agent_mode": "hybrid",
    "inherited_skills": "recommended"
  },
  "tool_status_snapshot": "runtime/<task_id>/tools_status.json",
  "notes": "Do not store secrets here. Use EZMM_ env vars."
}
```

`decisions` 必须包含 7 个 key：`pdf`、`scholar`、`dataset`、`webcrawl`、`corpus`、
`agent_mode`、`inherited_skills`。缺 key 视为 setup 未完成，必须补问缺失项。

### 配置流程引导

如果用户选 `yes`，提示：

```
1. 复制 .env.example 到用户级 ~/.ezmm.env （或者直接 setx EZMM_XXX value）
2. 把对应 key 填进去：
   - EZMM_MINERU_TOKEN=<去 https://mineru.net 注册领取>
   - EZMM_OPENALEX_EMAIL=<你的邮箱>
   - EZMM_S2_API_KEY=<去 https://www.semanticscholar.org/product/api 申请>
   - EZMM_SERPAPI_KEY=<去 https://serpapi.com 注册>
   - EZMM_FIRECRAWL_KEY=<去 https://firecrawl.dev 注册>
   - EZMM_TAVILY_KEY=<去 https://tavily.com 注册>
   - EZMM_EXA_KEY=<去 https://exa.ai 注册>
   - Kaggle: 在 kaggle.com 账户页面下载 kaggle.json 放到 ~/.kaggle/
3. 重启当前 shell 让 env var 生效
4. 回到对话说 "reload tools" 让 ez-math-model 重新扫描
```

**绝不**要求用户把 token 直接贴进对话。

### 临时默认状态

如果用户明确说“先按默认跑一次”或宿主无法交互，只能写本次 runtime 内状态：

```json
{
  "schema_version": "1.0",
  "setup_status": "temporary_default",
  "created_at": "2026-05-20T18:00:00+08:00",
  "decisions": {
    "pdf": "free-only",
    "scholar": "free-only",
    "dataset": "skip unless required by problem",
    "webcrawl": "skip unless required by problem",
    "corpus": "skip",
    "agent_mode": "hybrid",
    "inherited_skills": "recommended"
  },
  "persisted": false
}
```

此时必须同步更新 `runtime/{task_id}/run_state.json`：

```json
{
  "setup_status": "temporary_default",
  "can_package": false
}
```

质量门最高只能给 `provisional_pass`，最终诊断必须说明 setup 未持久化。

### 状态持久化

`external/tools/` 目录结构只在用户确认保存后出现：

```
external/tools/
├── setup_state.json            # setup 硬门禁状态，判断是否还需要强制提问
├── .tools_decided              # 兼容标记；不能替代 setup_state.json
├── pdf.free                    # 用户选了 free-only
├── scholar.skip                # 用户选了 skip
├── dataset.skip                # later 不写文件
├── webcrawl.free
├── corpus.yes                  # 用户选了启用 user-corpus
├── agent_mode.hybrid           # 用户选了 hybrid 模式
├── inherited_skills.yes        # 用户选了开启全部辅助 skill
└── tools_decision_log.md       # 决策记录（时间 / 用户选择 / 当时检测到的 env var）
```

域名约定：`pdf` `scholar` `dataset` `webcrawl` `corpus` `agent_mode`
`inherited_skills`，七个独立。

## 产出文件

| 路径 | 必须 | 说明 |
|---|---|---|
| `runtime/{task_id}/` | 是 | 本次运行目录已创建 |
| `runtime/{task_id}/project_paths.json` | 是 | 项目总文件夹与标准输出目录映射 |
| `runtime/{task_id}/run_state.json` | 是 | setup_status、run_mode、formal_result 等运行状态 |
| `runtime/{task_id}/README.md` | 是 | 由 `templates/readme_workdir.md` 渲染 |
| `runtime/{task_id}/env_check.json` | 是 | 环境检查结果 |
| `runtime/{task_id}/tools_status.json` | 是 | 外部工具扫描结果（discover_tools 输出） |
| `runtime/{task_id}/setup_assumptions.json` | 临时默认时 | 本次临时 setup 决策；不得持久化 |
| `external/tools/setup_state.json` | 用户确认保存后 | setup gate 状态；后续是否跳过交互式 setup 的唯一主标记 |
| `runtime/{task_id}/attachments/` | 是 | 用户附件副本（可空） |
| `external/tools/.tools_decided` | 可选兼容 | 旧版询问完成标记；不能替代 setup_state.json |
| `external/tools/<domain>.{free,skip,yes}` | 视用户选择 | 域级配置标记，仅用户确认保存后写 |

## env_check.json schema

```json
{
  "python_version": "3.11.5",
  "platform": "Windows-10-...",
  "missing_libraries": ["xgboost"],
  "fonts_available": ["SimHei", "Microsoft YaHei"],
  "git_available": true,
  "zhanwen_status": "absent | complete | failed | skip",
  "setup_completed": true,
  "setup_state_path": "external/tools/setup_state.json"
}
```

## 失败诊断

| 情况 | 处理 |
|---|---|
| Python 不可用 | **打断**。告知用户安装 Python ≥ 3.10。 |
| 关键库缺失 | 不打断。在 `env_check.json.missing_libraries` 列出，并在最终诊断报告里提示用户 `pip install` 命令。 |
| 中文字体全部缺失 | 不打断。写入诊断报告，coder 阶段会回退到 DejaVu Sans，论文可能出现方块。 |
| 工作目录创建失败（权限） | **打断**。告知具体原因。 |
| 用户选 `yes` 但 env var 仍未配置 | 不打断。降级为 `free-only` 等价，写诊断说明哪些域降级了。 |
| 用户已经决策过且 `setup_state.json.setup_completed == true` | 跳过交互式 setup，做轻量检查后进入 pipeline 01。 |
| 只有 `.tools_decided` 但没有 `setup_state.json` | 旧标记只能作为预填线索；仍必须让用户确认后才可生成 JSON。 |

## 下一阶段入口

`pipeline/01-problem-intake.md`。


