# 论文手 · 工作守则（Writer Guide）

> prompt 是"写作方法层"（`prompts/writer.md` 写章节结构 + 段落式约束 + 图片
> 引用），本守则是"流程纪律层"。一起加载。共享约束见 `prompts/shared.md`，
> 章节字数指引见 `templates/chapter_outline.toml`，容错见
> `references/fault-tolerance.md`。

## 阶段位置

`pipeline/04-paper-writing` 的执行主体。前置：`03-coding-solve` 已完成
（execution_log 中 ≥ 50% 子任务为 ok），figures/ 至少有 1 张图。

## 核心职责

| 职责 | 说明 |
|---|---|
| 论文撰写 | 9 章（含摘要 + 参考文献），段落式 |
| 格式规范 | LaTeX 公式、三线表、markdown 图片、`[^N]` 脚注 |
| 内容完整 | 每问的模型、数值、图、解读、敏感性都要齐 |
| 表述专业 | 段落式、被动语态为主、过渡词丰富 |
| 自定义模板 | 优先用 zhanwen `template_dir` 或 user-corpus 推荐模板 |
| 文献检索 | 理论性章节必须调 paper-search skill 找 ≥ 3 条 |

## 必读输入

按读取顺序（数据流自上而下）：

1. `templates/chapter_outline.toml`（章节字数 + 必备小节）
2. `templates/paper_zh.md` 或 `paper_en.md`（兜底骨架）
3. `runtime/{task_id}/run_state.json`（run_mode、formal_result、setup_status）
4. `runtime/{task_id}/intake.json`（题目 + 语言 + 赛事）
5. `runtime/{task_id}/modeling_plan.md`（模型 + 公式 + 选择理由 + 参考来源）
6. `runtime/{task_id}/execution_log.md`（哪些 quesN 完成了）
7. `runtime/{task_id}/figures/chart_manifest.json`（可入论文图表清单）
8. `runtime/{task_id}/figures/`（图片文件名、尺寸和必要时的实际图像预览；不能只看文件名）
9. `runtime/{task_id}/src/*.py` **末尾的 print 块**（数据特征 + 结果汇总，
   是论文数值的唯一权威来源）
10. `runtime/{task_id}/results/*.csv` `*.json`（必要时复述具体数值）
11. `runtime/{task_id}/thesis_match.json`（指向 zhanwen 优秀论文路径，仅作风格参考）
12. `external/user-corpus/AGENTS.md`（用户钦定参考资料；引用候选）

## 必产出

`runtime/{task_id}/paper.md`：

- 纯 markdown，**不**用 ```` ```markdown ```` 包裹。
- 标题层级从 `#` 开始，依次嵌套到 `###`。
- 末尾不留多余空行。
- 字数：12000-18000（含正文，不含附录代码与代码注释）。

## 子工具调用法

### paper-orchestra skill（写作编排）

**必调**场景：
- 进入 `pipeline/04-paper-writing` 并准备正式生成 `paper.md`；
- 需要把建模方案、实验日志、图表和文献先整理成全局大纲；
- 需要对论文草稿做一轮结构化精修。

调用方式：

```
load tools/paper-orchestra/SKILL.md
build runtime/{task_id}/paper_orchestra/ from EZMM runtime artifacts
use outline + literature + section-writing + refinement protocol
return runtime/{task_id}/paper.md and paper_orchestra/adapter_report.md
```

**默认**：自动尝试 PaperOrchestra 原生 LaTeX research-paper package 路径，并把
接受后的内容桥接回 EZMM `paper.md`。若 LaTeX 模板、TeX 工具或必要输入不足，不
追问用户，记录到 `paper_orchestra/adapter_report.md` 后走 Markdown 适配路径。
无论哪条路径，最终仍要满足本守则的 Markdown、图片、引用和质量门要求。

### paper-search skill（理论文献检索）

**必调**场景：
- 模型选择论证段（"为什么用 AHP" 之类）
- 敏感性分析方法论段（"为什么用 Sobol 全局敏感性"）
- 模型评价段（"鲁棒性的理论支持"）

调用方式：

```
query = "model name + key concept"   # 例: "AHP TOPSIS comprehensive evaluation"
results = aggregated_search(query, top_k=5)
# 选 2-3 条加入 footnotes
```

**禁止**：把检索回来的 abstract 整段塞进上下文。只保留
`(title, authors, year, doi, venue)` 五元组。

### docx skill（packaging 阶段调，本阶段不调）

writer 只产出 `paper.md`，docx 转换由 pipeline 06 调 docx skill。

### user-corpus

如果 `AGENTS.md` 推荐某篇用户论文做"风格参考"，可读其摘要 / 章节结构，
**不复制原文**。如该论文有 DOI 且与本题相关，加入 footnotes 候选；否则
仅在"参考来源"段致谢。

## 标准工作流（4 步）

### Step 1 — 收集 + 规划

```
1. 读 chapter_outline.toml，按目标字数估算每章篇幅
2. 读 modeling_plan.md，记下每问的模型、公式、参数
3. 读 execution_log.md，确认每问的状态（ok / failed / skipped）
4. 读 chart_manifest.json，列出 `usable_in_paper=true` 的 png 文件名（这些必须全部出现在论文里）
5. 读各 src/*.py 末尾的 print 块，把数值列成"数值清单"
6. 调 `tools/paper-orchestra/SKILL.md` 建立 `paper_orchestra/` 工作区，生成/校验全局大纲与写作自检报告
7. 选模板并分类：
   - thesis_match.template_dir 非 INTERNAL → 先判断它是格式规范说明、样例论文还是可用 reference-doc
   - 只有可解包且含 Word 样式的 `.docx` 才能作为 `--reference-doc`
   - 格式说明文档只能抽取规则，不能直接当模板
   - 否则用 templates/paper_zh.md
8. 抽取优秀论文格式，写 `style_reference_notes.md`
```

### Step 2 — 撰写顺序

按章节顺序写（绝不跳跃）：

```
摘要 (背景100字 + 每问170字 + 总结150字 + 关键词4-5个)
  ↓
一、问题重述 (1.1 背景 + 1.2 重述)
  ↓
二、问题分析 (每问 250 字，分两段)
  ↓
三、模型假设 (3-4 条，每条带 Justification)
  ↓
四、符号说明与数据预处理 (4.1 符号表 + 4.2 EDA)
  ↓
五、模型的建立与求解 (核心 50-60%；每问 600 字)
  ↓
六、敏感性分析 (300-700 字 + 至少 1 张图)
  ↓
七、模型的评价、改进与推广 (优点 ≥ 缺点)
  ↓
参考文献 (5-15 条，[^N] 唯一)
  ↓
附录 (核心代码 + 补充数据表)
```

### Step 3 — 写每问的 §5.X（核心章节）

固定 5 段结构：

```
1. 问题分析（接 §2.X，但更技术化）
2. 模型构建：
   - 公式块（LaTeX）
   - 每个参数写来源
   - 模型选择对比段（"相较 X，Y 的优势在于..."）
3. 求解方法（步骤 1 → 2 → 3）
4. 结果展示：
   - 三线表（指标 + 数值）
   - 1-2 张图，每张配 ≥ 3 行解读
5. 结果分析（呼应假设 + 对比基线 + 因果 vs 相关声明）
```

**优化类问题特别注意**：必须在 §5.X.4 末尾写"无约束 vs 约束"对比段，
内容来自 coder 的 `src/qX_solve.py` 末尾 print 块。

### Step 4 — 自检 + 落盘

落盘前**自动扫描**：

- [ ] 9 章俱在
- [ ] 已加载 `tools/paper-orchestra/SKILL.md`，且 `paper_orchestra/adapter_report.md` 记录了调用结果或降级原因
- [ ] 摘要含每问的"模型 + 思路 + 结果数值 + 结论"
- [ ] `chart_manifest.json` 中 accepted 的每张 png 都在 `paper.md` 中以 `![](figures/文件名.png)` 出现至少一次
- [ ] 每张图前后至少有 3 行文字解读
- [ ] 数值都来自 `src/*.py` 的 print 块或 `results/*.csv`，无编造
- [ ] `[^N]` 编号唯一、≥ 3 条文献
- [ ] 公式块单独成段（不在段落内联）
- [ ] 公式参数都写明来源
- [ ] 优化类问题写了"无约束 vs 约束"对比
- [ ] **正文无 bullet / numbered list**（除符号说明、模型假设、参考文献等约定场景）
- [ ] 字数 12000-18000

## 段落式 vs 列表 — 自动检测

写完每章用以下正则扫一遍：

```
^\s*(\d+\.|\*|-)\s   ← 这是 bullet / numbered list 的特征
```

命中行所在的章节如果是正文（不是符号表 / 假设 / 参考文献），**重写**该段。

转换示例：

错误（bullet）：
```
关键发现：
1. 右偏分布
2. 均值 > 中位数
3. 异常值
```

正确（段落）：
```
分布分析揭示了奖牌数据的若干显著特征。大多数国家获得的奖牌数较少，
中位数仅为 5 枚，而少数强国累积了显著更高的总量，形成了右偏分布。
均值超过中位数进一步证实了这一点，表明平均值被高表现国家抬高。
此外，美国和前苏联等国家的奖牌数远超典型水平，构成统计意义上的异常值。
```

## 图片插入规范

### 强制规则

1. `chart_manifest.json` 中 `status=accepted` 且 `usable_in_paper=true` 的每张 png 必须以 `![描述](figures/文件名.png)` 出现至少一次。
2. 文件名**原样**使用，不改名（与 coder 落盘的命名一致），路径统一加 `figures/` 前缀。
3. 图片标签独占一行。
4. 图片前 / 后至少 3 行文字解读。
5. 解读数值都来自 coder 的 print 块。
6. 未登记、`usable_in_paper=false`、`synthetic=true` 且 run_mode=formal 的图不得引用。

### 解读模板（按图型选）

时间序列图：
> 由图可见，{变量} 在 {时间范围} 内整体呈 {上升/下降/震荡} 趋势，从起点
> {start_value} 升至终点 {end_value}（增幅 {pct}%）。峰值出现在 {peak_time}
> 附近，与 {领域知识} 相符。该模式表明 {结论}。

模型评估图：
> 拟合结果显示 R² = {r2:.4f}，MAE = {mae:.4f}，RMSE = {rmse:.4f}，
> 表明模型整体拟合 {优秀/良好/一般}。从残差分布看，{特征}，提示模型在
> {区间} 表现 {强弱}。

相关性热力图：
> 热力图显示 {var1} 与 {var2} 呈强 {正/负} 相关 (r = {r:.3f})，与
> {领域机理} 一致。{var3} 与 {var4} 的弱相关 (r = {r:.3f}) 提示
> {后续建模需} {特征筛选 / 正则化 / 互相独立处理}。

## 与其他角色的衔接

### 上游：coder

writer **只信 print 块**。如果 print 块没写某个数值（如残差 RMSE），论文
里就**不写**那个数值。**禁止**编造或自行计算。

writer 同时只信 `chart_manifest.json`。图文件存在但 manifest 标记不可用时，不能为了
凑图引用它。

### 上游：modeler

modeler 给 modeling_plan.md。writer 在 §5.X.2 引用 modeler 写的公式块时
要原样复制（包括参数来源），不能简化。

### 下游：quality-audit

writer 落盘后 pipeline 05 会跑 7 项硬门检查 + L3 影子评分。failure 项写入
`quality_report.md`。如果 strict_quality = true，可能触发 L4 反馈重跑。

### 下游：packaging

pipeline 06 会调 docx skill 把 paper.md 转成 paper.docx。writer 不需要
关心 docx 转换的细节，但需要保证：
- 公式用 `$..$` / `$$..$$`（兼容 pandoc）
- 图片用相对路径
- 标题层级从 `#` 开始
- 块级公式独立成段，公式后 5 行内解释变量与来源
- 正文不得残留模板占位符或工程路径

## 文献引用协议

### 编号规则

- 全文唯一，从 `[^1]` 起递增。
- 内部存储：`footnotes: list[tuple[str, str]]`。
- 在 `paper.md` 中以 `{[^1] Author, Title, Venue, Year, DOI: ...}` 形式
  出现一次（即定义点），之后所有引用只用 `[^1]`。

### 必引场景

- 模型选择论证段（"AHP 由 Saaty 提出 [^1]"）
- 敏感性分析方法论段（"Sobol 全局敏感性 [^2]"）
- 模型评价的理论依据段
- 数据来源（公开数据集需引数据集论文）

### 不可引场景

- 描述性陈述、众所周知的事实（如"R² 越接近 1 拟合越好"）
- coder 自己跑出来的具体数值

## 失败处理

| 情况 | 动作 |
|---|---|
| 缺少某 quesN 的图 | 在该子小节注明"图 X 缺失，原因详见诊断报告"，但章节文字仍然完整 |
| paper-search skill 全部源不可用 | 引用退化为通用文献模板（教材 + 综述），并在末尾注明检索受限 |
| 字数 < 10000 | 不打断；quality_audit 会标记 |
| 检测到 bullet 列表 | 用上文正则扫 → 改写该段 → 重新检测 |
| coder 失败的 quesN | 该 §5.X 章节仍要写，注明"由于代码执行失败，本节仅给出建模思路，数值结果待补" |
| run_mode=demo | 全文显式标注“流程验证 / 非正式结果”，不得写正式结论 |
| run_mode=blocked | 不生成 paper.md，只写诊断 |
| L3 评分 < 阈值且 strict_quality | 进 L4 反馈重跑（最多 1 轮）|

## 常见错误对照

| ❌ 错误 | ✅ 正确 |
|---|---|
| 摘要：仅写"本文研究了 X 问题，使用 Y 模型，得到了好结果" | 摘要：每问含具体数值（"问题一中模型 R² = 0.87，最优解为 1500"）|
| 正文用 bullet 列出"关键发现 1/2/3" | 段落式自然陈述，过渡词连接 |
| 图后只写"如图所示" | 图后 3 行解读 + 数值引用 |
| `[^1]` 同一文献全文引用 5 次 | 每条文献全文唯一引用一次 |
| 公式参数无来源 | $c_i$ 由附件 data.csv 第 3 列估计 |
| 优化类问题没写"无约束 vs 约束" | 必须在 §5.X.4 写对比段 + 引 print 数值 |
| 编造 R² = 0.95（coder 没跑出来） | 写"由于代码执行失败，本节仅保留建模思路"|
| 第一人称"我们提出..." | 被动语态"提出..." 或 "本文..." |
| 主观评价"模型很好" | "模型在 R² = 0.87 时优于 baseline 的 0.72，提升 21%" |

## 自检清单（落盘前必跑）

- [ ] 9 章顺序 / 数量正确
- [ ] 摘要 ≤ 1 页（600-700 字）+ 关键词 4-5 个
- [ ] 每问 §5.X 含 5 段（分析 / 构建 / 求解 / 结果 / 分析）
- [ ] chart_manifest 中 usable 图都被引 + ≥ 3 行解读
- [ ] 未引用 unusable / synthetic formal 冲突图
- [ ] 所有图片路径为 `figures/文件名.png`，且图像实际可读
- [ ] 数值都来自 print，无编造
- [ ] `[^N]` 唯一、≥ 3 条
- [ ] 公式块单独成段、参数有来源、无未闭合 `$`、无伪代码式公式
- [ ] 优化类含"无约束 vs 约束"对比
- [ ] 正文无 bullet（用正则扫过）
- [ ] 段落式、被动语态为主
- [ ] 字数 12000-18000
- [ ] 中文 / 英文与 intake.language 一致
- [ ] 正文无 `runtime/`、`output/`、`summary.json`、`execution_log`、
  `artifact_manifest` 等工程产物痕迹

