---
name: "09-verify"
description: "最终验证v2.0，融合paper-score评分系统（100分制），含结构检查+自动评分+档位预测"
---

# 09-verify — 最终验证与评分

本 skill 承接 `08-reviewer-mode`。目标是在提交前对全部产出做系统检查，确保论文、代码、图表、结果一致且无遗漏。

## 必须产出

- `reports/VERIFY_REPORT.md`：验收报告（含评分）
- `paper/main.pdf`：最终论文PDF

## 检查清单

1. 论文结构检查
2. 图表引用检查
3. 数值一致性检查
4. 占位符检查
5. 编译检查
6. 代码可复现检查
7. 摘要质量检查
8. 格式规范检查
9. 08-reviewer-mode修复项检查

## 论文自动评分（融合 paper-score，总分100分）

## 审批节点（必须执行）
