---
name: simplify
description: Use after EZ_math_model coding has produced src/*.py and before packaging when code quality, reuse, vectorization, naming, or unnecessary complexity should be reviewed without changing behavior.
---

# simplify — 建模代码质量检查

## 何时使用

- `pipeline 03 coding` 完成后。
- `pipeline 06 packaging` 之前。
- hybrid / multi 模式下希望额外检查 `src/*.py`。

## 调用方式

优先加载宿主 `simplify` skill，输入所有 `src/*.py`。只输出建议，不直接修改代码。

检查重点：

- 重复逻辑和可抽取工具函数。
- 低效循环与可向量化处理。
- 过度防御或吞异常。
- 命名混乱。
- 与 modeling_plan 不一致的实现。

输出：

```text
workdir/{task_id}/simplify_report.md
```
