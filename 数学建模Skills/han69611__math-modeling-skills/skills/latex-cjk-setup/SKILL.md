---
name: "latex-cjk-setup"
description: "LaTeX中文排版配置：用XeTeXlinebreaklocale替代xeCJK解决兼容性问题，overfull hbox防护，中英文参考文献混排"
---

# LaTeX中文排版配置

## 核心方案：XeTeX原生中文换行（推荐）

在Ubuntu/texlive环境下，xeCJK常因expl3/l3kernel版本冲突导致编译失败。推荐使用fontspec + XeTeX原生指令替代xeCJK：

```latex
\documentclass[12pt,a4paper]{article}
\usepackage[left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm]{geometry}
\usepackage{fontspec}
\setmainfont{Noto Serif CJK SC}
\setsansfont{Noto Sans CJK SC}
\XeTeXlinebreaklocale "zh"
\XeTeXlinebreakskip = 0pt plus 1pt minus 0.1pt
\linespread{1.3}
\sloppy
\emergencystretch=3em
\tolerance=1000
\hbadness=1000
```

## 各指令作用说明
## 常见问题：xeCJK编译报错、中文段落Overfull hbox、中英混排间距异常
## 参考文献混排
## 知网文献检索策略