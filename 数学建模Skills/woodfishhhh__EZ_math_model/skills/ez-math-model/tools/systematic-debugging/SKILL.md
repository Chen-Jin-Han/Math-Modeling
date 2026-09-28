---
name: systematic-debugging
description: Use when EZ_math_model coder or packaging fails repeatedly with the same error and needs root-cause analysis instead of another blind retry.
---

# systematic-debugging — 根因诊断

## 何时使用

- `coder` 单脚本 L1 重试 2 次仍失败。
- 同一异常类型连续出现。
- packaging 转换失败且普通修复无效。
- 需要验证假设而不是继续“再试一次”。

## 调用方式

优先加载宿主 `systematic-debugging` skill。输入：

- 失败代码。
- 完整 traceback。
- `modeling_plan.md` 对应章节。
- 附件数据预览。
- 已尝试修复记录。

要求输出：

- 5-10 条可能根因。
- 每条根因对应的验证步骤。
- 按概率排序的修复建议。
