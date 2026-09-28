---
name: subagent-driven-development
description: Use when developing or extending EZ_math_model itself from a written implementation plan, especially adding algorithms, tool skills, templates, or multi-step repo changes.
---

# subagent-driven-development — EZMM 开发派单

## 何时使用

- 用户要求扩展 EZ_math_model 本身。
- 已有书面实施计划。
- 计划任务互相独立且完成标志清晰。
- 需要把多步开发任务交给 subagent。

## 不适用场景

求解一道数学建模题时不要默认使用本 skill。`pipeline 03` 的 coder 并发用 `dispatching-parallel-agents`。

## 调用条件

优先加载宿主 `subagent-driven-development` skill。派单前确认：

1. 有明确计划文件或任务列表。
2. 每个任务有独立写入范围。
3. 每个任务有验收标准。
4. 任务之间没有未解决依赖。

## EZMM 场景映射

| 场景 | 推荐工具 |
|---|---|
| 求解一道建模题 | dispatching-parallel-agents |
| 添加算法库章节 | subagent-driven-development |
| 添加新 tool skill | subagent-driven-development |
| 执行现成 plan.md | subagent-driven-development |

## 失败诊断

| 情况 | 处理 |
|---|---|
| 宿主 skill 未安装 | 主对话顺序实施 |
| 计划任务有依赖 | 退化为顺序实施 |
| 写入范围冲突 | 重新拆分任务 |
