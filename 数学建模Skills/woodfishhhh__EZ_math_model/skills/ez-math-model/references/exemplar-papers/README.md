# 优秀论文样例索引（Exemplar Papers）

> 本目录由 **MinerU flash-extract** 从 [zhanwen/MathModel](https://github.com/zhanwen/MathModel)
> 上游优秀论文 PDF 转换为 Markdown，作为 modeler / writer 的"风格 / 章节 /
> 表述"参考。**所有文件版权归原作者所有**，仅作学术参考。
>
> 限于 flash-extract 单文件 ≤ 20 页约束，每篇仅取**前 20 页**（覆盖摘要、
> 问题重述、问题分析、模型建立的核心部分，对学习写作风格已足够）。

## 文件清单

| 题型 | 赛事 / 年份 / 题号 | 主题 | 路径 |
|---|---|---|---|
| 优化 / 整数规划 | CUMCM 2023 B 题 | DFT 类矩阵的整数分解逼近 | `cumcm-2023-B_B23100070173/` |
| 数据驱动 / 评价 | CUMCM 2023 C 题 | 蔬菜类商品自动定价与补货决策 | `cumcm-2023-C_C23102890004/` |
| 物理机理 / 微分方程 | CUMCM 2023 A 题 | 定日镜场的优化设计 | `cumcm-2023-A_A23102890028/` |
| 物理机理 / 信号处理 | CUMCM 2022 A 题 | 波浪能转换装置 | `cumcm-2022-A_A22116460175/` |
| 调度优化 | CUMCM 2022 B 题 | 无人机定位编队 | `cumcm-2022-B_B22110490001/` |
| 物理建模 / 数据 | MCM 2017 A 题 | Managing the Zambezi River | `mcm-2017-A_55280/` |
| 数据洞察 | MCM 2017 C 题 | Cooperate and Navigate | `mcm-2017-C_55278/` |

每个子目录里有：
- `<name>.md` — MinerU 提取的 markdown 全文（前 20 页）
- 同目录可能还有 `images/` — 提取的论文配图（PDF 中的图）

## 怎么用

### 模仿边界与验收

优秀论文样例是格式和表达密度参考，不是内容来源。正式写作前，writer 必须输出
`runtime/{task_id}/style_reference_notes.md`，记录：

- 读取了哪 1-2 篇样例；
- 学到的摘要节奏、章节层级、公式解释方式、图表前后衔接方式；
- 本文采用的具体格式规则；
- 明确未复制原文、未同义改写原段落。

允许学习：章节节奏、摘要信息密度、公式编号和变量解释方式、图表组织方式。
禁止：连续复用原文句式、同义改写原段落、照搬公式推导上下文、套用与本题无关的
模型叙述。若借鉴具体公式、定义、模型结构或观点，必须在正文引用来源。

### modeler（pipeline 02）

读论文的 §1 问题分析、§3 模型建立 来学：
- 如何从题目导出形式化模型
- 如何写"模型选择对比"段
- 公式的排版与符号约定

**禁止**：直接抄方案。仅模仿章节结构与表述风格。

### writer（pipeline 04）

读论文的**摘要**与各章首尾段，学习：
- 摘要"背景 / 方法 / 结果 / 结论"四段式的字数比例
- 段落式陈述（无 bullet）
- 过渡词
- 公式块的引用方式（公式编号 + 在文中如何提及）

按 chapter_outline.toml 的字数指引，比对优秀论文的实际段落长度，校准
自己的写作节奏。

### 配合上游 zhanwen 仓库

如果用户在本机也通过 `scripts/install/fetch_zhanwen.ps1` 拉取了完整 zhanwen
仓库（在 `external/zhanwen-mathmodel/`），那是"原版完整 PDF"；本目录的 md
是"已提取摘要版"。两者互补：

- **快速参考**：用 `references/exemplar-papers/<name>/<name>.md`（直接读 md）
- **完整阅读**：用 `external/zhanwen-mathmodel/<...>/<filename>.pdf`（再走 pdf skill）

## 题型覆盖

按 modeler 决策树的 7 个问题类型：

| 类型 | 推荐参考 |
|---|---|
| 预测类 | 国赛 2022 B 题（无人机航迹预测） |
| 评价决策类 | 国赛 2023 C 题（蔬菜定价决策）/ MCM 2017 C 题 |
| 分类聚类类 | 国赛 2023 C 题（商品分类） |
| 优化类 | 国赛 2023 B 题（整数规划） / 国赛 2023 A 题（连续优化） |
| 统计分析类 | MCM 2017 A 题（描述性统计 + 假设检验） |
| 仿真类 | 国赛 2022 A 题（蒙特卡洛波浪能仿真） |
| 物理 / 力学机理 | 国赛 2023 A 题（光学几何） |

## 维护说明

如要新增样例，运行：

```powershell
# 1. 从 raw.githubusercontent 下载 PDF 到 $env:TEMP\ezmm-pdfs\
# 2. 调 MinerU CLI（已在 $env:USERPROFILE\.mineru\bin\mineru-open-api.exe）
$cli = "$env:USERPROFILE\.mineru\bin\mineru-open-api.exe"
& $cli flash-extract path\to\paper.pdf -o references\exemplar-papers\<name>\ --language ch --pages 1-20
```

如本机已配置 MinerU token，可去掉 `--pages 1-20` 限制，提取整篇论文：

```powershell
& $cli extract path\to\paper.pdf -o references\exemplar-papers\<name>\ --language ch
```

## 与 git 的关系

本目录**不**被 `.gitignore` 排除（这是仓库内置参考资料，与 `external/`
下的运行时缓存性质不同）。如果你 fork 本仓库不想分发 md，自行加 ignore。

## 来源声明

| 项 | 来源 |
|---|---|
| PDF 原件 | https://github.com/zhanwen/MathModel |
| 提取工具 | [MinerU](https://github.com/opendatalab/MinerU) (flash-extract 模式) |
| 版权 | 原作者所有；仅供学术参考 |
| 提取时间 | 2026-05-20 |

