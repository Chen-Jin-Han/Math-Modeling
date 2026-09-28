# Pipeline 02 — 建模方案

## 入口条件

- `intake.json` 已落盘且 `is_math_modeling=true` 且 `ques_count >= 1`。
- `run_state.json.run_mode != blocked`。

## 阶段任务

### 1. 资源准备节点（询问只发生一次）

按以下顺序判断 zhanwen 上游缓存：

```
if exists(.skip):
    跳过询问，走内置兜底
elif exists(.complete):
    使用上游
elif exists(.failed):
    跳过询问，走内置兜底
else:  # 首次
    询问用户是否拉取 zhanwen/MathModel（约 60-80MB sparse 子集）
    用户回答：
        yes → 调 fetch_zhanwen.ps1（或 .sh）
        no  → 本次跳过，但下次仍会询问（不写 .skip）
        skip → 写 .skip，永久跳过
```

询问的措辞固定：

> 检测到尚未下载优秀论文资源（zhanwen/MathModel，sparse 拉取约 60-80MB）。
> 是否下载用于参考？yes / no / skip。
> （选 skip 永久不再询问；选 no 仅本次跳过。）

### 2. 上游论文与模板匹配

调 `scripts/runtime/match_thesis.py`，输入 `intake.json`，输出
`runtime/{task_id}/thesis_match.json`（schema 见 `references/workdir-protocol.md`）。

### 3. 加载 modeler prompt

**等待**：若 pipeline 01 派出了 corpus explorer，等其完成（或超时 5 分钟）。

载入 `prompts/modeler.md`，并附带：
- `intake.json` 全部字段。
- `thesis_match.json` 中 `thesis_dir` 路径下的 PDF 文件清单（仅文件名，不读
  内容；后续按需 lazy load）。
- 与本题最相关的算法库章节摘要（基于关键词匹配 `references/algorithms/README.md`
  的速查表）。
- 若存在 `external/user-corpus/AGENTS.md`，整篇并入 modeler 上下文，重点是
  "Recommendations for this task" 段。

### 4. 产出建模方案

modeler 按其 prompt 中的输出格式撰写 `runtime/{task_id}/modeling_plan.md`，
覆盖：
- 0 EDA / 数据预处理方案。
- 1..N 各小问建模方案（类型判断 / 模型选择 / 求解思路 / 验证 / 可视化）。
- N+1 敏感性分析方案。
- 末尾**参考来源**段：标注 zhanwen / user-corpus / 内置算法库各贡献了哪些
  思路，便于审计。

若 `run_mode=demo`，方案必须明确哪些输入是合成/示例数据，只能作为流程验证。
若发现 formal 模式缺关键数据，停止并把 `run_state.json.run_mode` 改为 `blocked`，
不得让 coder 自行补造数据。

### 5. 角色守则强制载入

在调用 modeler prompt 前，先载入 `references/roles/modeler-guide.md` 作为
"流程纪律层"，prompt 中的内容是"建模方法层"，二者互补。

## 产出文件

| 路径 | 必须 | 说明 |
|---|---|---|
| `runtime/{task_id}/thesis_match.json` | 是 | 上游匹配结果 |
| `runtime/{task_id}/modeling_plan.md` | 是 | 建模方案 |
| `external/zhanwen-mathmodel/.complete` | 视情况 | 拉取成功标记 |
| `external/zhanwen-mathmodel/.failed` | 视情况 | 拉取失败标记 |
| `external/zhanwen-mathmodel/.skip` | 视情况 | 用户永久跳过标记 |

## 失败诊断

| 情况 | 处理 |
|---|---|
| zhanwen 拉取失败 | 写 `.failed`，`thesis_match.json.match_level=internal`，**不打断**。 |
| 网络超时 | 重试 1 次后写 `.failed`。 |
| modeling_plan.md 缺少某个 quesN 的小节 | 不打断，质量门会捕获。 |
| modeling_plan.md 完全为空（LLM 异常） | 重试 1 次仍空 → **打断**，让用户检查 prompt / 模型可用性。 |

## 下一阶段入口

`pipeline/03-coding-solve.md`。
