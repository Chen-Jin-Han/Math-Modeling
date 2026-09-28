# 外部工具目录（External Tools Catalog）

> **唯一信息源**。pipeline 00 的"工具发现"节点据此向用户提问；各子 skill 按
> 此处的工具名引用。新增工具先改这里，再在对应子 skill 里加细节。

五个能力域：**PDF 解析 / 学术搜索 / 数据集 / 网页抓取 / 写作编排**。每个工具标注：
- **价格**：免费 / 免费额度 / 付费 / 需邮箱
- **何时启用**：触发条件
- **配置项**：env var 名（统一前缀 `EZMM_`）
- **降级**：未配置时怎么办

## 1. PDF 解析

| 工具 | 价格 | 何时启用 | 配置 | 文档 |
|---|---|---|---|---|
| **MinerU 本地 CLI**（开源） | **完全免费**，pip 装即用 | 中文学术 PDF / 表格 / 公式；离线场景 | 无（首次运行自动下模型） | `tools/mineru/SKILL.md` |
| **MinerU 云 API** | **免费**（注册送 token + 配额；超额才付费） | 不想本地装模型 / 跑大批量 | `EZMM_MINERU_TOKEN`（注册免费领） | `tools/mineru/SKILL.md` |
| **MinerU 网页 flash** | 免费、零注册 | 临时单文件、≤10MB / ≤20 页 | 无 | `tools/mineru/SKILL.md` |
| **宿主 pdf skill** | 免费 | 简单 PDF 文本提取 | 无 | `tools/pdf/SKILL.md` |
| **pdfplumber** | 免费 | 兜底，单栏文本 | 无 | `tools/pdf/SKILL.md` |
| **PaddleOCR / EasyOCR** | 免费 | 扫描件 PDF | 无 | `tools/pdf/SKILL.md` |
| **Nougat / pix2tex** | 免费 | 公式密集论文 | 无 | `tools/pdf/SKILL.md` |

**好处对比**：
- MinerU 三种部署形态对中文学术 PDF / 表格 / 公式识别质量都显著高于 pdfplumber，
  全部能免费用：本地 CLI 适合长期使用，云 API 适合不想装模型的场景，网页
  flash 适合一次性临时解析。
- 宿主 pdf skill 是 pdfplumber + pypdf 的封装，对纯文本 PDF 已经足够。
- 仅扫描 PDF 才需要 OCR；优秀论文 PDF 多为可选文本，OCR 通常用不上。

## 2. 学术搜索

| 工具 | 价格 | 何时启用 | 配置 | 文档 |
|---|---|---|---|---|
| **OpenAlex** | 免费 | 默认主搜索 | `EZMM_OPENALEX_EMAIL`（提配额，可选） | `tools/scholar/SKILL.md` |
| **arXiv API** | 免费 | 数学 / CS / 物理预印本 | 无 | `tools/scholar/SKILL.md` |
| **Semantic Scholar** | 免费（有 API key 配额翻倍） | 引用关系、citation count | `EZMM_S2_API_KEY`（可选） | `tools/scholar/SKILL.md` |
| **CrossRef** | 免费 | DOI 元数据兜底 | 无 | `tools/scholar/SKILL.md` |
| **谷歌学术（SerpAPI）** | 付费（5000 次免费试用） | 中英混合检索 / 引用次数 | `EZMM_SERPAPI_KEY` | `tools/scholar/SKILL.md` |
| **百度学术** | 免费 | 中文论文为主、CNKI 之外的入口 | 无（爬取或 SerpAPI 接入） | `tools/scholar/SKILL.md` |
| **CNKI 中国知网** | 付费 / 单位订阅 | 中文核心期刊 | 无官方 API，需机构访问 | `tools/scholar/SKILL.md` |

**好处对比**：
- OpenAlex 覆盖度高、有摘要、免费、有 abstract inverted index；**首选**。
- arXiv 的预印本通常比期刊版本早 1-2 年，建模赛题里有用。
- Semantic Scholar 引用图谱强，找"被引最多的关键文献"用它。
- 谷歌学术只能通过 SerpAPI 等中介；自建爬虫违反 ToS。
- 百度学术中文 SEO 友好，但无官方 API；少量手动检索可接受。

**默认策略**：OpenAlex（必）+ arXiv（必）+ Semantic Scholar（建议）；其余按需。

## 3. 数据集

| 工具 | 价格 | 何时启用 | 配置 | 文档 |
|---|---|---|---|---|
| **Kaggle Datasets** | 免费（需注册） | 题目缺数据，需找类似公开数据集 | `~/.kaggle/kaggle.json`（API token） | `tools/dataset/SKILL.md` |
| **UCI ML Repository** | 免费 | 经典机器学习数据集 | 无 | `tools/dataset/SKILL.md` |
| **HuggingFace Datasets** | 免费 | NLP / 多模态 | `EZMM_HF_TOKEN`（私有数据集需要） | `tools/dataset/SKILL.md` |
| **天池 / 阿里云数据集** | 免费 | 中文场景 / 国赛历年题相关 | 无（手动下载为主） | `tools/dataset/SKILL.md` |
| **Awesome Public Datasets** | 免费 | GitHub 索引，浏览用 | 无 | `tools/dataset/SKILL.md` |

**好处对比**：
- 题目附件已含数据时，跳过此域。
- 题目要求"自行查找数据"或"补充外部数据"时优先 Kaggle / UCI；想找中文场景
  数据用天池。
- Kaggle 的 API token 一次配置长期可用；非常推荐。

## 4. 网页抓取与开放检索

| 工具 | 价格 | 何时启用 | 配置 | 文档 |
|---|---|---|---|---|
| **Firecrawl** | 免费额度 + 付费 | 题目背景需爬政府 / 行业网页 | `EZMM_FIRECRAWL_KEY` | `tools/webcrawl/SKILL.md` |
| **Jina Reader** | 免费 | 单页 URL → markdown，0 配置 | 无（公共端点） | `tools/webcrawl/SKILL.md` |
| **Tavily Search** | 免费额度 + 付费 | LLM-friendly 搜索 + 摘要 | `EZMM_TAVILY_KEY` | `tools/webcrawl/SKILL.md` |
| **Exa（former Metaphor）** | 免费额度 + 付费 | 神经搜索，找"类似的页" | `EZMM_EXA_KEY` | `tools/webcrawl/SKILL.md` |
| **SerpAPI** | 付费 | 谷歌 / 谷歌学术 / 百度结果 | `EZMM_SERPAPI_KEY` | `tools/webcrawl/SKILL.md` |

**好处对比**：
- 题目纯数学 / 物理机理（无外部背景需要）→ 全部不需要。
- 题目涉及政策 / 行业 / 经济背景 → 至少配 Jina（免费）或 Tavily。
- Firecrawl 是"爬一整个网站"的 batch 利器；单页用 Jina 即可。
- SerpAPI 主要作用是替代谷歌学术 API，二选一即可。

## 5. 写作编排

| 工具 | 价格 | 何时启用 | 配置 | 文档 |
|---|---|---|---|---|
| **PaperOrchestra vendored pack** | 免费，MIT | writer 阶段组织大纲、文献、成文、精修 | 无 | `tools/paper-orchestra/SKILL.md` |

**好处对比**：
- PaperOrchestra 提供 outline → plotting/literature → section writing →
  refinement 的论文写作纪律。EZMM 默认只借用该纪律，最终仍输出数学建模竞赛所需的
  `paper.md`。
- vendored upstream 位于 `external/paper-orchestra/`，无嵌入 LLM 调用、无内置
  API key；实际检索仍优先走 EZMM 的 `tools/scholar/SKILL.md` /
  `tools/paper_search/SKILL.md`。
- 只有用户明确要求原生 LaTeX research-paper package 时，才进入上游
  PaperOrchestra 完整 LaTeX 流程。

## env 配置约定

所有外部工具 env var 统一前缀 `EZMM_`。`.env.example` 列出全部可填项。
建议放在用户级 `~/.ezmm.env` 或 PowerShell `$PROFILE`，不要提交到 git。

不要直接把 token 贴到 prompt / SKILL / pipeline 文档里。任何脚本必须通过
`os.environ.get("EZMM_XXX")` 或 `$env:EZMM_XXX` 读取。

## 询问策略（pipeline 00 用）

pipeline 00 先检查 `external/tools/setup_state.json`。没有该文件、JSON 损坏、
`setup_completed` 不是 `true`，或缺少 7 个 `decisions` key 时，必须进入首次
setup 提问；完成后写入该 JSON。旧版 `.tools_decided` / `.enabled` / `.skip-*`
只作为兼容线索，不能替代 `setup_state.json`。

setup 一共记录 7 个域；其中外部工具的 4 个域按下面模式提问，每组只问 1 个问题：

```
[PDF 解析] 是否启用 MinerU 提升 PDF 题目识别质量？
  yes        — 现在配置 MinerU token
  free-only  — 仅启用 flash-extract（无需 token，免费但有 ≤10MB / ≤20 页限制）
  skip       — 本次不用，继续走 pdfplumber 兜底
  later      — 暂跳过，下次再问（不写 .skip 标记）
```

用户选择最终写入 `setup_state.json.decisions`。为兼容旧文档，也可以同步写
`external/tools/<domain>.free`、`external/tools/<domain>.skip` 或
`external/tools/agent_mode.hybrid` 等标记；`later` 不应标记为已完成。

## 不在 catalog 中的工具

下面这些**不要**在没有用户明确指令时启用：

- 任何需要付款且没有免费额度的 API（避免误扣费）。
- 自建谷歌学术爬虫（违反 ToS）。
- 任何需要绕过反爬虫的工具。
- 私有数据集 / 公司内网爬取。

## 维护规则

新增工具时按域插入；价格 / 配额 / 配置项变化时改这里。pipeline 与子 skill
不要重复列工具元信息，统一引用本目录。



