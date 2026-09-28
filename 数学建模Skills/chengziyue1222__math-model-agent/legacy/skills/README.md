# Math Model Skills

数学建模工作流工具集 — 56 个 skill 文件（17 核心 + 39 扩展）+ 17 个算法模块。

> `skill/` 保留原有 Claude Code 风格命令文档。可被 Codex 自动发现的标准技能位于 `../skills/`，当前包含选型、求解、数据分析、文献研究、科研绘图、论文写作和论文审查 7 个技能。

## 目录结构

```
skill/
├── core/          (17 个核心 skill 文件)
├── latex/         (5 个 LaTeX 编译相关)
├── quarto/        (3 个 Quarto/部署)
├── paper/         (6 个论文写作与审阅)
├── research/      (5 个研究与构思)
├── data/          (4 个数据分析)
├── lecture/       (3 个讲座/课程)
├── workflow/      (10 个工作流)
└── audit/         (3 个审计/验证)
```

## 核心 Skills (`core/`)

| Skill 文件 | 用途 |
|------------|------|
| `math_model_skill.md` | 五层能力架构总控 |
| `model_selector.md` | 18 种问题类型→模型决策 |
| `model_library.md` | 模型库速查 |
| `model_library_extended.md` | 扩展模型库 |
| `modeling_pipeline.md` | 11 步统一建模流程 |
| `modeling_norms.md` | 建模规范与最佳实践 |
| `judge_engine.md` | 六维度评审引擎 |
| `paper_generator.md` | 结构化论文生成 |
| `python_mapping.md` | MATLAB→Python 映射 |
| `evaluation.md` | 综合评价方法指南 |
| `monte_carlo.md` | 蒙特卡罗决策与模板 |
| `image_processing.md` | 图像处理流水线 |
| `sci_figures.md` | 科研图表规范 |
| `math_competition_guide.md` | 竞赛实战全流程 |
| `paper_check.md` | 论文质量检查清单 |
| `diagram_tools.md` | TikZ/图表工具指南 |
| `algorithm_api.md` | 算法库 API 速查 |

## 扩展 Skills

### LaTeX/编译相关 (5 个)
| Skill | 用途 | 用法 |
|-------|------|------|
| `/compile-latex` | XeLaTeX 3遍编译 | `/compile-latex Lecture01` |
| `/extract-tikz` | 提取TikZ图表 | `/extract-tikz Lecture2` |
| `/new-diagram` | 生成TikZ图表 | `/new-diagram DAG output` |
| `/proofread` | 语法拼写检查 | `/proofread file.tex` |
| `/visual-audit` | 视觉布局审计 | `/visual-audit Lecture01.qmd` |

### Quarto/部署 (3 个)
| Skill | 用途 | 用法 |
|-------|------|------|
| `/deploy` | 渲染部署到GitHub Pages | `/deploy Lecture1` |
| `/translate-to-quarto` | LaTeX转Quarto | `/translate-to-quarto file.tex` |
| `/qa-quarto` | Quarto质量对比 | `/qa-quarto Lecture` |

### 论文写作与审阅 (6 个)
| Skill | 用途 | 用法 |
|-------|------|------|
| `/review-paper` | 7维度并行审查 | `/review-paper paper.pdf` |
| `/seven-pass-review` | 七遍审稿法 | `/seven-pass-review manuscript.pdf` |
| `/respond-to-referees` | 回复审稿人 | `/respond-to-referees refs.pdf revised.pdf` |
| `/humanize` | 检测AI写作痕迹 | `/humanize file.tex` |
| `/validate-bib` | 验证引用完整性 | `/validate-bib -semantic` |
| `/preregister` | 起草预注册文档 | `/preregister --style osf` |

### 研究与构思 (5 个)
| Skill | 用途 | 用法 |
|-------|------|------|
| `/lit-review` | 结构化文献综述 | `/lit-review "主题"` |
| `/research` | 生成研究问题 | `/research "话题"` |
| `/ideation` | 多轮访谈形式化 | `/ideation "话题"` |
| `/interview-me` | 互动式访谈 | `/interview-me "话题"` |
| `/devils-advocate` | 对抗性挑战 | `/devils-advocate file.tex` |

### 数据分析 (4 个)
| Skill | 用途 | 用法 |
|-------|------|------|
| `/data-analysis` | 数据分析管道 | `/data-analysis dataset.csv` |
| `/review-r` | R代码审查 | `/review-r scripts.R` |
| `/audit-reproducibility` | 数值声明验证 | `/audit-reproducibility paper.pdf` |
| `/stata-replication` | Stata复现管道 | `/stata-replication paper.pdf` |

### 讲座/课程 (3 个)
| Skill | 用途 | 用法 |
|-------|------|------|
| `/create-lecture` | 创建Beamer讲座 | `/create-lecture 主题` |
| `/slide-excellence` | 综合幻灯片审查 | `/slide-excellence file.tex` |
| `/pedagogy-review` | 教学法审查 | `/pedagogy-review file.tex` |

### 工作流 (10 个)
| Skill | 用途 | 用法 |
|-------|------|------|
| `/commit` | 完整提交流程 | `/commit "提交信息"` |
| `/learn` | 提取知识为skill | `/learn skill-name` |
| `/checkpoint` | 保存状态快照 | `/checkpoint topic` |
| `/compress-session` | 压缩会话笔记 | `/compress-session topic` |
| `/context-status` | 会话健康状态 | `/context-status` |
| `/prompt` | 结构化prompt执行 | `/prompt "想法"` |
| `/deep-prompt` | 生成prompt不执行 | `/deep-prompt "想法"` |
| `/prompt-only` | 只生成prompt | `/prompt-only "想法"` |
| `/standard-save` | 升级learn条目 | `/standard-save path.md` |
| `/promote-memory` | 升级到MEMORY.md | `/promote-memory` |

### 审计/验证 (3 个)
| Skill | 用途 | 用法 |
|-------|------|------|
| `/deep-audit` | 全仓库深度审计 | `/deep-audit` |
| `/permission-check` | 权限配置诊断 | `/permission-check` |
| `/verify-claims` | 链式验证声明 | `/verify-claims draft.pdf` |

## 使用方法

### Codex

将 `../skills/` 中需要的技能目录安装到 `$CODEX_HOME/skills`，然后通过 `$select-model`、`$solve-model`、`$review-model-paper` 等名称调用。

### 旧版 Claude Code 命令

1. 切换到项目目录。
2. 输入本目录对应的 slash command。
3. 按照提示提供参数。
