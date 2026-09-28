# 容错机制（Fault Tolerance）

> ez-math-model 的"四层容错"设计。每个 pipeline 阶段、每个角色 prompt
> 都遵守同一套容错协议。本文是单一信息源，pipeline 文档只引用不重复。

## 设计原则

- **Wrap, don't rewrite**：容错都在编排层加，不修改角色 prompt 的核心
  指令。失败时是"换 wrapper / 换实例"，而不是"改 prompt 改到能通过"。
- **失败后状态污染防护**：重试 / 切换 fallback 时**新建 Agent 实例**，
  不复用脏 chat_history。
- **可观测优先**：所有重试 / 降级 / 跳过都要写 `execution_log.md` 或
  `diagnostics.md`，便于事后审计。
- **永不死锁**：每层都有"放弃并降级"的明确出口，绝不无限重试。

## 四层容错总览

```
L1 Bounded Retry（角色内）          ← Agent 自己的 try/except + retry
L2 Fallback Switch（编排层）        ← 主模型失败 → 备用模型 / 备用工具
L3 Evaluator Shadow（编排层）       ← 独立评估器对产出打分
L4 Feedback Rerun（编排层）         ← 评分不通过 → 注入反馈 → 新建实例重跑
```

L1 必启用；L2 在外部工具配置允许时启用；L3 / L4 是可选增强，默认 L3 开
（shadow，不阻塞），L4 关（避免过度自我修正）。

## L1 — Bounded Retry（有限重试）

**触发**：JSON 解析失败 / API 一过性错误 / 单段代码执行非零退出。

**最大次数**：

| 子操作 | 默认上限 | 说明 |
|---|---|---|
| 角色 prompt 输出 JSON 解析失败 | 3 | 第 3 次仍失败 → 抛 `MalformedOutputError`，进 L2 |
| 单个 coder 子任务（脚本执行） | 2 | 第 2 次失败 → 写诊断、跳过该子任务 |
| OpenAlex / Semantic Scholar API 临时失败 | 2 + 指数退避 (1s, 4s) | 第 2 次失败 → 标该源不可用，本会话跳过 |
| zhanwen `fetch_zhanwen` clone | 1 | 失败立刻写 `.failed`，pipeline 走内置兜底 |
| docx skill / pdf skill / xlsx skill | 0（一次成败） | 不重试，立即降级到下一档工具链 |

**每次失败必做**：
1. 把异常摘要追加到 `execution_log.md` 的 retry 列。
2. 切换"修复策略"：第 1 次只读异常信息修；第 2 次直接简化输入或换思路。
3. 不把 retry 次数提示写到主对话里污染上下文，只写日志。

## L2 — Fallback Switch（备用切换）

**触发**：L1 用尽仍失败 / 主资源（模型 / 工具 / 缓存）整体不可用。

**默认 Fallback 链**：

| 域 | 主 → 备用顺序 |
|---|---|
| LLM 模型 | 当前模型 → `EZMM_FALLBACK_MODEL`（如有）→ 跳过该子任务 |
| PDF 解析 | MinerU 本地 CLI → MinerU 云 API → 宿主 pdf skill → pdfplumber → 视觉直读 |
| 论文搜索 | OpenAlex → arXiv → Semantic Scholar → CrossRef → SerpAPI（如配） → 内置文献模板 |
| 网页抓取 | Jina Reader → Firecrawl → Tavily → Exa → SerpAPI → 让用户给具体 URL |
| 数据集 | Kaggle → HuggingFace → UCI → 天池（手工） → 让用户上传 |
| 上游论文 | zhanwen `thesis_dir` → user-corpus AGENTS.md → 内置算法库 |
| docx 转换 | 宿主 docx skill → pandoc → python-docx → demo 可仅输出 markdown；formal 需对象审查通过或降级为 provisional |

**关键约束**：
- 每次切换 fallback **新建 Agent 实例**，避免复用上次失败时的 chat_history。
- 切换后第 1 次仍失败 → 进 L2 的下一档；不再回头试主资源。
- 所有 fallback 使用情况记入 `diagnostics.md`，让用户知晓"哪几个工具未生效"。

## L3 — Evaluator Shadow（影子评估）

**默认开启**。每个角色产出落盘后，由一个轻量评估器对产出**打分但不阻塞**。

### 评估器载入方式

不必额外起 LLM 调用：在主 LLM 完成产出后，紧接着发一段 **structured eval**
prompt，让同一 LLM（或 fallback 上的便宜模型）以独立"评委"视角评分。

```
你现在是 ez-math-model 的内部质量评委。请仅基于以下产出，给出 0-1 的浮点
评分（保留两位小数）和一句改进建议。**不要重写产出**。

产出内容：
<...>

输出：
{"score": 0.85, "advice": "符号说明表缺少单位列，建议补全"}
```

### 评分项与阈值

| 阶段 | 关键评分项 | 默认阈值 |
|---|---|---|
| coordinator | is_math_modeling 判定 / ques_count / contest 信号识别 | 0.70 |
| modeler | 每问方案完整 / 物理边界写明 / EDA 类型判断正确 | 0.65 |
| coder | print 数据特征齐全 / 图片成功 / 异常处理 | 0.60 |
| writer | 9 章齐全 / 图必引 + 解读 ≥3 行 / 文献编号唯一 / 无 bullet | 0.70 |

### 影子模式落盘

`workdir/{task_id}/eval_shadow.md`：

```markdown
# Evaluator Shadow Log

| 阶段 | 时间 | 评分 | 阈值 | 是否通过 | 建议 |
|---|---|---|---|---|---|
| modeler | 2026-05-20T10:30 | 0.72 | 0.65 | ✓ | EDA 章节物理量纲检查可加一段 |
| coder/q2 | 2026-05-20T10:42 | 0.55 | 0.60 | ✗ | 缺少混淆矩阵的 print |
| writer | 2026-05-20T11:08 | 0.78 | 0.70 | ✓ | 摘要数值结果建议加单位 |
```

**默认不阻塞 pipeline**：评分低不触发重跑，只在 `quality_report.md` 末尾
合并展示。

## L4 — Feedback Rerun（反馈重跑）

**默认关闭**。当用户显式要求"严格质量"或题目高赛事级别（如赛事 = MCM/ICM
正式提交）时启用。

### 启用方式

在 `intake.json` 中加 `"strict_quality": true`，或环境变量 `EZMM_STRICT=1`。

### 触发与动作

```
当 L3 evaluator score < threshold:
    if rerun_count < MAX_FEEDBACK_ROUNDS（默认 1）:
        新建该角色的 Agent 实例
        prompt = 原 prompt + "\n\n## 上一次产出的不足\n<advice>\n请改进后重新输出。"
        rerun_count += 1
    else:
        放弃，写诊断，进入下一阶段
```

### 安全约束

- `MAX_FEEDBACK_ROUNDS = 1`（保守默认）。多了会陷入"被评估器牵着鼻子走"。
- 每轮 rerun **新建 Agent 实例**，不复用脏历史。
- 第二次仍未通过 → **不再重跑**，写诊断"L4 已耗尽预算"，进下一阶段。
- L4 重跑不替换 L3 评估器，仍由它评分；评估器自己不能成为重跑的目标。

## 配置项汇总

| 环境变量 / 配置 | 默认值 | 含义 |
|---|---|---|
| `EZMM_MAX_RETRIES_JSON` | 3 | L1 JSON 解析重试上限 |
| `EZMM_MAX_RETRIES_CODER` | 2 | L1 单脚本重试上限 |
| `EZMM_FALLBACK_MODEL` | （空） | L2 备用模型；空则跳过该子任务 |
| `EZMM_EVAL_THRESHOLD_DEFAULT` | 0.65 | L3 通用阈值 |
| `EZMM_EVAL_DISABLE` | 0 | 设 1 关闭 L3（极少需要） |
| `EZMM_STRICT` / intake.strict_quality | 0 / false | 设 1 开启 L4 |
| `EZMM_MAX_FEEDBACK_ROUNDS` | 1 | L4 最大反馈重跑轮数 |

## 与各 pipeline 文件的对应

| pipeline 文件 | 容错重点 |
|---|---|
| `00-environment-setup.md` | L2：python / 字体 / git 缺失时如何降级提示 |
| `01-problem-intake.md` | L1：PDF 抽取乱码重试 / coordinator JSON 重解析 |
| `02-modeling-plan.md` | L1+L2：modeler 输出格式重试；zhanwen → user-corpus → 内置兜底 |
| `03-coding-solve.md` | L1：每脚本 2 次重试；L2：库缺失降级；L3：每子任务后评分 |
| `04-paper-writing.md` | L3：章节完整性评分；L4（可选）：缺章重写 |
| `05-quality-audit.md` | 汇总 L3 evaluator 影子日志 + audit_quality 分层硬门 |
| `06-packaging-output.md` | L2：导出失败降级；formal 需 audit_export 对象审查通过才可正式发布 |

## 不属于本文档的内容

- 单个工具的具体调用方式 → 见 `tools/<name>/SKILL.md`
- 角色级的写作 / 编程纪律 → 见 `references/roles/*.md`
- 共享 prompt 约束 → 见 `prompts/shared.md`

## 维护原则

新增工具或 pipeline 阶段时，先回到本文件加一行 fallback 链路或评分项，
再回到对应子 skill / pipeline 加细节，避免容错逻辑零散。


