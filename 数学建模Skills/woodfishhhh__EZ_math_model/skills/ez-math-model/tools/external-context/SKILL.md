---
name: external-context
description: Use when EZ_math_model multi or hybrid mode needs several domain-specialist subagents to gather outside knowledge, industry context, model theory, or sensitivity-analysis references in parallel.
---

# external-context — 并行外部知识检索

## 何时使用

- 题目跨经济、工程、政策等多个领域。
- 单个 `paper-search` query 覆盖不足。
- modeler 或 writer 需要多组外部知识摘要。
- `agent_mode = multi` 或 `hybrid`。

## 调用方式

优先加载宿主 `external-context` skill，并行派 2-3 个 specialist：

```text
specialist 1: 找 {模型 A} 经典文献
specialist 2: 找 {题目领域} 行业基准
specialist 3: 找 {敏感性分析} 方法论文献
```

每个 specialist 输出不超过 500 字摘要和 DOI / URL 列表，最后聚合到：

```text
workdir/{task_id}/refs/external_context.md
```

## 与 paper-search 的区别

| 工具 | 适用 |
|---|---|
| `paper-search` | 单 query 多源聚合，主对话直接跑 |
| `external-context` | 多 query 并行，专家式摘要与交叉验证 |

## 失败诊断

| 情况 | 处理 |
|---|---|
| 宿主 skill 未安装 | 降级为 `paper-search` 串行检索 |
| specialist 结论冲突 | 保留所有结论，标注争议点 |
| 全部 specialist 失败 | 回到 `paper-search` 或 `webcrawl` |

## 边界

- 不直接生成 `paper.md` 引用文本。
- 不替代 writer 的引用编号管理。
- 不绕过 multi/hybrid 并发约束。
