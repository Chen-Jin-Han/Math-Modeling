---
name: paper-check
description: 论文质量检查与验收 — 自动检测章节结构、图表引用、占位符、数值一致性等
---

# 论文质量检查

来源: [MathModelAgent](https://github.com/jihe520/MathModelAgent) 的 `6verity` skill。

## 功能

| 检查项 | 级别 | 说明 |
|--------|------|------|
| 章节结构 | FAIL | include/input 顺序、文件是否存在 |
| 标题完整性 | FAIL | 每个章节是否有 = Title / \section{} |
| 占位符 | FAIL | TODO、待补充、示例数据等 |
| 内部泄露 | FAIL | 论文正文出现内部文件名 |
| 图片引用 | FAIL | 引用的图片文件是否存在 |
| caption | FAIL/WARN | figure 是否有 caption，长度是否合理 |
| 参考文献 | WARN | 文件是否存在、是否有引用标记 |
| 数值一致性 | WARN | 结果文件中的指标是否出现在论文中 |
| 章节长度 | WARN | 章节是否过短 |
| 列表密度 | WARN | 是否过多列表而缺少段落叙述 |
| 未引用图表 | WARN | figures/ 中的 PDF 是否都被引用 |

## 使用

```python
from algorithms.paper_check import check_paper

# 基本用法
report = check_paper(
    paper_dir="paper",
    figures_dir="figures",
    results_file="reports/RESULTS_REPORT.md",
)

print(report.summary())  # 打印报告
print(report.passed)     # True/False
print(report.fail_count) # FAIL 数量
print(report.warn_count) # WARN 数量
```

### 命令行

```bash
python -m algorithms.paper_check paper [main.typ]
```

### 完整参数

```python
from algorithms.paper_check import PaperChecker

checker = PaperChecker(
    paper_dir="paper",                    # 论文目录
    main_file="paper/main.typ",           # 入口文件（自动检测）
    sections_dir="paper/sections",        # 章节目录（自动检测）
    references_file="paper/references.typ",  # 参考文献（自动检测）
    figures_dir="figures",                # 图表目录
    results_file="reports/RESULTS_REPORT.md",  # 结果报告
    problem_analysis_file="reports/ANALYSIS_MODELING_REPORT.md",  # 问题分析
    all_results_json="figures/all_results.json",  # 汇总 JSON
    extra_internal_terms=["my_workflow"],  # 额外内部术语
)

report = checker.run()
```

## 引擎支持

- **Typst**: 检查 `#include("...")`、`= Title`、`#figure(image(...), caption: [...])`
- **LaTeX**: 检查 `\input{}`、`\section{}`、`\begin{figure}...\end{figure}`

引擎由入口文件扩展名自动检测（`.typ` → Typst，`.tex` → LaTeX）。

## 验收标准

### 硬错误（FAIL）

- 缺少入口文件或核心正文
- include 的章节文件不存在
- 章节顺序错误
- 存在占位符
- 正文泄露内部文件名
- 引用的图片不存在
- figure 缺少 caption

### 警告（WARN）

- 章节过短（< 800 字符）
- caption 过长（> 80 字符）或过短（< 4 字符）
- 参考文献偏少
- 列表过多
- 图表后缺少解释
- 结果指标在论文中难以找到

## 与工作流集成

在论文撰写完成后、提交前运行：

```python
# 5writing 完成后
report = check_paper("paper", figures_dir="figures")
if not report.passed:
    print("需要修复以下问题：")
    for r in report.results:
        if r.severity.value == "FAIL":
            print(f"  - {r}")
```
