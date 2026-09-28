# Pipeline 04 — 论文撰写

## 入口条件

- `modeling_plan.md` 已落盘。
- `execution_log.md` 已落盘且 ≥ 50% 子任务状态为 `ok`。
- `figures/` 下至少有 1 张图。
- `run_state.json.run_mode != blocked`。
- 若 `run_mode=formal`，`figures/chart_manifest.json` 中至少有 1 张
  `usable_in_paper=true` 且 `synthetic=false` 的图。

## 阶段任务

### 1. 加载 writer 角色

- prompt：`prompts/writer.md`
- 守则：`references/roles/writer-guide.md`
- 协议：`references/run-mode-protocol.md`、`references/chart-quality-gate.md`
- 模板：根据 `intake.json.language`（默认 `zh`）选择
  `templates/paper_zh.md` 或 `templates/paper_en.md`。
- 章节大纲：`templates/chapter_outline.toml`。

### 2. 上游论文参考（条件性）

若 `thesis_match.json.match_level != internal`，writer 必须先抽取 1-2 篇最相关
优秀论文的格式风格，生成内部文件 `style_reference_notes.md`。该文件只记录：

- 参考论文路径、题型、语言；
- 摘要信息密度、章节层级、公式编号/解释方式、图表前后衔接方式；
- 本文准备模仿的格式规则；
- 明确声明未复制的内容。

writer 仅可参考结构、节奏、对象组织与表述密度，**不得复制原文或同义改写原段落**。
如借鉴具体公式、定义、模型结构或观点，必须以 `{[^N] ...}` 学术格式标注。
如果 `thesis_dir/` 只有 PDF 文件名而不能解析正文，则必须退回
`references/exemplar-papers/` 的内置 markdown 样例；不能只凭文件名声称已参考。

### 3. 输入物聚合

writer 收到的输入包括：
- `run_state.json`（run_mode、formal_result、setup_status）
- `intake.json`（题目语义层）
- `modeling_plan.md`（建模方案层）
- `execution_log.md`（哪些 quesN 有结果）
- `figures/` 下所有图片的文件名、尺寸和必要时的实际图像预览
- `figures/chart_manifest.json` 中 `status=accepted` 且 `usable_in_paper=true` 的图片清单
- `src/*.py` 中每个脚本末尾的 `print` 输出（特别是数据特征块）
- `results/` 下的 csv / json（用于复述具体数值）
- `thesis_dir/` 的 PDF 文件名清单（可选）
- `external/user-corpus/AGENTS.md`（若存在）：用户钦定参考资料的索引；
  writer 在引用文献候选阶段优先查这里的论文是否能匹配到 DOI。

### 4. PaperOrchestra 子 skill 编排

writer 在正式动笔前必须加载 `tools/paper-orchestra/SKILL.md`。该子 skill
把 EZMM 的 `modeling_plan.md`、`execution_log.md`、`figures/chart_manifest.json`
和结果表映射为 PaperOrchestra 风格的 `idea.md` 与 `experimental_log.md`，用于：

- 生成或校验 `paper_orchestra/outline.json`；
- 组织文献检索与 citation pool；
- 按全局大纲一次性起草论文主体；
- 做一轮内容精修和写作质量自检。

默认使用 PaperOrchestra-first 模式：不等待用户额外确认，writer 自动尝试运行
`external/paper-orchestra/skills/paper-orchestra/SKILL.md` 的上游完整写作流程。
当 EZMM 模板和本机 TeX/导出工具足以支撑 LaTeX 路径时，把上游结果放在
`runtime/{task_id}/paper_orchestra/final/`；同时必须桥接生成 EZMM 正式
`runtime/{task_id}/paper.md`，供质量门和打包阶段继续消费。

如果 PaperOrchestra 任一步因缺少输入、无网络、无视觉能力或工具不可用而降级，
writer 不追问用户，必须在 `paper_orchestra/adapter_report.md` 记录原因，并继续用
PaperOrchestra 的大纲、文献、成文和精修纪律产出 Markdown 版 `paper.md`。

### 5. 撰写流程

按章节顺序写：

1. 标题 + 摘要 + 关键词
2. 一、问题重述
3. 二、问题分析
4. 三、模型假设
5. 四、符号说明与数据预处理
6. 五、模型的建立与求解（每个 quesN 一节）
7. 六、敏感性分析
8. 七、模型评价
9. 参考文献

若 `run_mode=demo`，标题、摘要、结果章节和结论必须显式写明“流程验证 / 非正式
结果”，不得使用“最优”“最终”“正式结论”等措辞。若 `run_mode=blocked`，不得生成
正式论文，只能输出 `diagnostics.md`。

### 6. 强制规则（来自 writer prompt）

- 段落式写作，正文严禁 bullet / numbered list。
- `figures/` 下每张 accepted 图都必须以 `![描述](figures/文件名.png)` 出现至少一次。
- 仅允许引用 `chart_manifest.json` 中 `usable_in_paper=true` 的图。
- 每张图前后至少 3 行解读分析，分析数值必须来自 `print` 输出，禁止编造。
- 文献编号 `[^N]` 全文唯一，不重复引用。
- 公式参数必须写来源（数据 / 文献 / 校准）。
- 优化类问题必须包含"无约束解 vs 物理约束解"段落。
- 正文不得泄露工程流水线痕迹，例如 `runtime/`、`output/`、`summary.json`、
  `execution_log`、`artifact_manifest`、脚本调试日志等。
- 所有公式必须能被 pandoc 转为 Word 公式对象：块级公式独立成段，前后空行；
  复杂结构只使用 pandoc 支持的 LaTeX；每个公式后 5 行内解释变量和来源。

### 7. 文献检索

理论性章节（"为什么选模型"、"敏感性分析方法论"、"评价模型理论基础"）必须
调 `tools/paper_search/SKILL.md` 获取至少 3 条参考文献。检索关键词从
`modeling_plan.md` 的模型名抽取。

## 产出文件

| 路径 | 必须 | 说明 |
|---|---|---|
| `runtime/{task_id}/paper.md` | 是 | 论文 markdown；demo 模式必须标注非正式 |
| `runtime/{task_id}/style_reference_notes.md` | formal 推荐 / 有样例时必须 | 优秀论文格式抽取记录，不进入最终论文 |
| `runtime/{task_id}/paper.humanized.md` | 否 | 若启用 humanizer，去 AI 味重写版（详见 `tools/humanizer/SKILL.md`） |
| `runtime/{task_id}/refs/external_context.md` | 否 | 若启用 external-context，多领域并行检索的文献列表 |

## 失败诊断

| 情况 | 处理 |
|---|---|
| 缺少某 quesN 的图 | 论文中省略该子小节的图引用，质量门记入未通过项 |
| chart manifest 无可用图 | 停止写正式论文，写诊断；demo 可写流程验证文档 |
| `paper-search skill` 不可用 | writer 改用通用文献模板（"经典教材 + 综述"），并在诊断中注明 |
| paper.md 字数 < 3000 | 不打断，质量门会标记字数不足 |
| 论文中出现 bullet 列表 | 写完后做一遍正则扫描，若发现 → writer 重写一次 |

## 下一阶段入口

`pipeline/05-quality-audit.md`。


