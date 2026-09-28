---
name: brainstorming
description: Use when EZ_math_model model selection is unclear after the modeling decision tree, the problem spans multiple domains, or modeler needs several candidate approaches before writing modeling_plan.md.
---

# brainstorming — 建模方案发散入口

## 何时使用

- `pipeline 02 modeling` 跑完决策树后仍无法确定主模型。
- 题目跨多个领域，单一速查表不能匹配。
- writer 找不到理论表述或引用角度时，可偶尔用于发散。

## 调用方式

优先加载宿主 `brainstorming` skill。输入：

- `intake.json`
- `problem.md`
- 算法库 README 或模型速查表

要求输出 3-5 个候选方案、优劣对比、推荐主选与备选。

## 与 modeler 的衔接

brainstorming 输出不直接写入 `modeling_plan.md`。modeler 必须把候选方案回填到模型选择段，说明为什么选主方案、为什么放弃备选。

## 失败诊断

| 情况 | 处理 |
|---|---|
| 宿主 skill 未安装 | modeler 自行列出 2 个候选并标记 fallback |
| 候选方案过多 | 强制收敛到 top 3，再回到决策树 |
| 输出偏离题面 | 只保留与目标函数、数据约束直接相关的方案 |

## 边界

- 不替代 modeler 的最终决策。
- 不调用外部检索；文献检索交给 `paper-search` 或 `scholar`。
- 不延伸到 coder 阶段。
