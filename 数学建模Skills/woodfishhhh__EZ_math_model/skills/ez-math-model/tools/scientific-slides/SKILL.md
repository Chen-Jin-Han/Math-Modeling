---
name: scientific-slides
description: Use when the user explicitly asks EZ_math_model to create defense slides, academic presentation slides, Beamer slides, or PPT after the modeling paper has been packaged.
---

# scientific-slides — 建模答辩与学术幻灯片

## 何时使用

- 用户在 packaging 完成后明确说“做答辩 PPT”“做 Beamer”“做演示文稿”。
- 题目要求汇报材料。
- 不在主 pipeline 中默认启用。

## 调用流程

1. 读取 `workdir/{task_id}/paper.md`，抽出每章核心 1-2 句。
2. 加载宿主 `scientific-slides` skill。
3. 按时长选择模板：10-15 分钟答辩、30-45 分钟研讨、30-60 分钟论文答辩。
4. 复用 `figures/` 中实际生成的图。
5. 输出到 `workdir/{task_id}/slides/`。

## 模板选型

| 场景 | 推荐 |
|---|---|
| CUMCM / 美赛答辩 | conference |
| 课题组例会 | seminar |
| 论文答辩 | defense |

## 约束

- 不替代 writer 写论文。
- 不修改 `paper.md`。
- 不独立重画 `figures/` 中已有图。
- 封面或章节分隔页可使用装饰图，但不得掩盖核心图表。

## 失败诊断

| 情况 | 处理 |
|---|---|
| 宿主 skill 未安装 | 给出基于 paper.md 的幻灯片大纲 |
| LaTeX 编译失败 | 交付 `.tex` 源并写诊断 |
| 图分辨率过低 | 提示 coder 阶段导出 300dpi |
