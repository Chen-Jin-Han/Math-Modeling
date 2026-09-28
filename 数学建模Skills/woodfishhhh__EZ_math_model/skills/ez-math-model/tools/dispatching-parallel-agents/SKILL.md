---
name: dispatching-parallel-agents
description: Use when EZ_math_model runs in multi or hybrid mode and has two or more independent subtasks that can be assigned to subagents without shared files, shared state, or dataflow dependencies.
---

# dispatching-parallel-agents — 并行派单协议

## 何时使用

- `agent_mode = multi` 或 `hybrid`。
- `pipeline 03` 拆出多个 `ques` 子任务。
- 多个文献 query 可独立检索。
- 开发 EZ_math_model 时有互不冲突的实现任务。

## 独立性检查

派单前逐项确认：

1. 任务间没有数据流依赖。
2. 任务间不会写同一个文件。
3. 任务间不需要共享中间状态。

任一项不满足，就改为顺序执行或分批执行。
