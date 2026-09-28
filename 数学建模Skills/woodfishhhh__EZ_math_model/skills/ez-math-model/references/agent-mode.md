# Agent 工作模式（Agent Mode）

> ez-math-model 的 pipeline 7 个阶段，可在以下三种 Agent 工作模式间选择。
> 这份文档是单一信息源；pipeline 文件只引用、不重复优缺点。

## 三种模式

```
single  ─ 主对话单线推进，所有阶段在同一个 Agent 上下文里
multi   ─ 每个阶段（或子任务）派 subagent 独立执行
hybrid  ─ 关键阶段 subagent，琐碎阶段主对话直接做（默认）
```

## 优缺点对比

| 维度 | single | multi | hybrid |
|---|---|---|---|
| **上下文压力** | 高，长跑后接近爆 | 低，主对话只看汇总 | 中等 |
| **并发能力** | 无（顺序） | 强（可并行 5+ 子任务） | 中等（按需） |
| **总耗时** | 中（无 spawn 开销） | 大题更短 / 小题更长 | 大题更短 / 小题适中 |
| **失败定位** | 容易（一条线性日志） | 难（多 subagent 混合） | 中等 |
| **token 成本** | 低 | 高（每个 subagent 重读 prompt） | 中等 |
| **可重入性** | 失败需从头复述 | 失败 subagent 可独立重跑 | 部分可独立重跑 |
| **稳定性** | 高 | 中（subagent 协议出错风险） | 高 |
| **学习曲线** | 0 | 需理解派单与状态文件协议 | 同 multi |
| **适用题量** | 1-2 小问 / 物理机理题 | ≥ 4 小问 / 数据驱动大题 | 通用 |

## 何时选哪种

### single — 简单顺序

**典型场景**：
- 题目仅 1-2 小问。
- 题目是物理机理题（无大量数据 EDA）。
- 用户机器只有一个 LLM 实例（不支持 subagent 派单）。
- 用户偏好"看着每一步"。

**特征代码**：`agent_mode = "single"` → `external/tools/agent_mode.single`

### multi — 全部派单

**典型场景**：
- 题目 ≥ 4 个独立小问（典型 CUMCM B 题）。
- 大量 EDA + 多个独立模型。
- 主对话上下文已接近 60% 上限。
- 用户希望"快"。

**特征代码**：`agent_mode = "multi"` → `external/tools/agent_mode.multi`

### hybrid — 默认推荐

**典型场景**：默认。除非用户明确选其他。

策略：
- 阶段 00（环境）/ 01（intake）/ 02（modeling）/ 06（packaging）：主对话直接做。
- 阶段 03（coding）：拆 ques1..N，每个**子任务**一个 subagent。
- 阶段 04（writing）：主对话直接做。
- corpus explorer：subagent。
- 文献检索：主对话调 paper-search 脚本。

formal 论文交付是高风险产物。无论 single/multi/hybrid，若宿主支持 subagent，
pipeline 05/06 必须至少安排独立审查面：

- visual reviewer：实际读取图片和图表上下文，剔除废图、平线图、压缩图、不可读图；
- paper format reviewer：核对优秀论文格式模仿、章节层级、模板残留、工程痕迹；
- object/export reviewer：核对公式、表格、DOCX/PDF 对象和 manifest/zip 一致性。

宿主不支持 subagent 时，主对话必须按同样三张清单顺序自审，并把证据写入
`quality_report.json`、`export_audit.json` 或 `diagnostics.md`。

**特征代码**：`agent_mode = "hybrid"` → `external/tools/agent_mode.hybrid`

## 派单协议（multi / hybrid 共用）

### 派单边界

只在**有明确产出文件**且**无外部副作用**的子任务派 subagent：

| 可派单 | 不派单 |
|---|---|
| coder 单个 ques 求解 | 工具发现 / 询问用户 |
| corpus explorer | docx 转换（必须主对话做完决策） |
| 论文章节检索文献 | git clone / fetch_zhanwen |
| 多源学术搜索 | 任何需要 `AskUserQuestion` 的步骤 |

### 入参约定

每次 `Agent({ subagent_type, prompt })` 派单时，prompt 必须包含：

```
工作目录：{absolute workdir path}
本次任务的 task_id：{YYYYMMDD-HHMMSS-hash}
你必须读：{需要读的相对路径列表}
你必须落盘：{产出文件清单 + schema}
受 fault-tolerance 约束：L1 重试 ≤ 2，失败写诊断后退出
完成后输出一行 'DONE <task_name>' 到 stdout
不允许：调用 AskUserQuestion / 修改 attachments / 调用 Web 长连接
```

### 状态协调

subagent 之间**不直接通信**，只通过 `workdir/` 下的文件：

- `execution_log.md` — coder 子任务汇总（每个 subagent 完成后追加一行，**追加**不覆盖）
- `eval_shadow.md` — L3 影子评分（每个 subagent 各写一段）
- `diagnostics.md` — 失败诊断（任意 subagent 都可追加）

主对话在所有 subagent 完成（或超时）后**聚合 + 排重**。

### 并发上限

```
最大并发 = 2     # 默认
```

理由：
- Jupyter 内核 / 文件 I/O 争用
- LLM API 限速
- 用户机器 CPU / 内存

如要提高，在 intake.json 加 `"max_concurrency": N`，或环境变量
`EZMM_MAX_CONCURRENCY`。

### 超时与回收

- 单个 subagent 软超时：5 分钟。
- 硬超时：10 分钟，主对话主动取消并写诊断。
- subagent 卡死 → 跳过该子任务，记 `diagnostics.md`，继续其他。

## 失败诊断

| 情况 | 处理 |
|---|---|
| subagent 派单失败（API 错误） | 主对话直接顺序做该子任务 |
| subagent 输出乱码 / 不合 schema | 主对话重写该段产出 |
| 多个 subagent 同时写 execution_log | **必须**追加（`Edit` 不允许整体重写）+ 末尾去重 |
| subagent 间产出冲突 | 主对话保留先到达的，丢弃后到达的，写诊断 |
| 全部 subagent 都失败 | 降级到 single 模式重跑当前阶段 |

## 与共享 prompt 的关系

`prompts/shared.md` 的所有约束（语言、JSON、工具调用、反思、段落式、失败重试）
对 single / multi / hybrid 三种模式都生效。subagent 的 prompt **必须**显式引用
`prompts/shared.md`，避免 subagent 行为漂移。

## 配置项

| 配置 | 默认 | 含义 |
|---|---|---|
| `external/tools/setup_state.json.decisions.agent_mode` | hybrid | setup gate 的主状态 |
| `external/tools/agent_mode.{single,multi,hybrid}` | hybrid | 用户决策标记 |
| `EZMM_MAX_CONCURRENCY` | 2 | 并发 subagent 上限 |
| `EZMM_SUBAGENT_SOFT_TIMEOUT` | 300（秒） | 软超时 |
| `EZMM_SUBAGENT_HARD_TIMEOUT` | 600 | 硬超时 |

## 何时不派 subagent（即使 multi 模式）

- 用户**显式**说"不要用 subagent"
- 题目极简（1 小问 + 无附件）
- 主对话上下文 < 30% 时不必为优化而派
- subagent 模型与主对话不同 → 行为可能漂移，先在 single 验证

## 与各 pipeline 文件的对应

| pipeline | single | multi | hybrid 默认 |
|---|---|---|---|
| 00 环境 | 主 | 主 | 主 |
| 01 intake | 主 | 主 | 主 |
| 01 corpus explorer | 主 | sub | sub |
| 02 modeling | 主 | sub | 主 |
| 02 zhanwen 拉取 | 主 | 主 | 主 |
| 03 coding 子任务 | 主（顺序） | sub（并发） | sub（并发） |
| 04 writing | 主 | sub（章节并发） | 主 |
| 04 文献检索 | 主 | sub | 主 |
| 05 quality | 主 + 独立审查 | 主 + 独立审查 | 主 + 独立审查 |
| 06 packaging | 主 + 对象审查 | 主 + 对象审查 | 主 + 对象审查 |

## 不在本文档管理的内容

- 各角色 prompt（`prompts/*.md`）
- 各子 skill 调用（`tools/*/SKILL.md`）
- 容错的 4 层细节（`references/fault-tolerance.md`）
- 工作目录文件 schema（`references/workdir-protocol.md`）


