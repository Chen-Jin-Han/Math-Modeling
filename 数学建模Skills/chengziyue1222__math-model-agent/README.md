# Math Model Agent

<p align="center">
  <strong>从题意拆解、模型求解到可提交论文的一体化数学建模工作流</strong>
</p>

<p align="center">
  <a href="https://github.com/chengziyue1222/math-model-agent/actions/workflows/ci.yml"><img src="https://github.com/chengziyue1222/math-model-agent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg" alt="Python 3.10+">
</p>

**Math Model Agent** 是一个面向数学建模竞赛与建模报告的开源工具箱。它不只提供算法函数，还把题目拆解、数据诊断、模型选择、求解验证、图表、论文写作和提交前审查串成一条可复现的工作流。

它适合希望减少重复劳动、保留建模判断并交付可检查结果的参赛者、课程项目团队和研究型建模使用者。它不承诺获奖；模型洞察、数据质量与问题理解仍是决定性因素。

> 8 个标准 Codex Skills · 25 个算法与质量模块 · 149 个公开导出 · 56 个历史命令归档


## 为什么使用它？

| 你在做什么 | 对应能力 |
|---|---|
| 面对陌生赛题，不知道从哪里拆 | 逐题目标、变量、单位、约束与候选模型比较 |
| 有模型但担心结果站不住 | 基线、约束审计、时间留出、灵敏度与不确定性验证 |
| 算完了却写不成论文 | 结论驱动图表、CUMCM 风格 TeX 模板、可读的论文结构与终审 |
| 需要快一点，或需要严一点 | `rapid`、`competition`、`audit` 三档工作流按风险选择 |

## 三种工作方式

| 档位 | 适合什么情况 | 交付重点 |
|---|---|---|
| `rapid` | 题目理解、探索与初步建模 | 题意、探索模型/基线、可复现参数、初步结果与局限 |
| `competition` | 2026 国赛完整交付 | 完整建模、必要基线/验证、正式 PDF（或 DOCX）、完整代码与支撑材料、提交预检 |
| `audit` | 高风险、可复用或外部评审项目 | competition 全部能力，加完整角色契约、HMAC、全量哈希/注册表、独立复核与 PDF+DOCX |

## 30 秒开始

```bash
git clone https://github.com/chengziyue1222/math-model-agent.git
cd math-model-agent
python -m pip install ".[dev]"
python scripts/install_skills.py
```

在 Codex 中直接说：

```text
使用 $run-modeling-project 以 competition 档完成这个数学建模项目。
```

只想使用算法库时：

```python
from algorithms import topsis

ranking = topsis(decision_matrix, weights, benefit_indicators)
```

---

## 功能特性 / Features

### 🧮 算法库 / Algorithm Library (`code/algorithms/`)

149 个公开导出，25 个模块文件；核心算法按 9 大类组织，另含数据诊断、证据契约、质量、文档和生产保护模块：

**决策与评价 (23)**

| 模块 | 核心方法 | 竞赛场景 |
|------|---------|---------|
| `ahp.py` | AHP、CR 检验、层次 AHP | 多准则决策、权重分配 |
| `fuzzy_math.py` | 模糊综合评价、模糊 C-means、多层次模糊 | 不确定性建模、风险评估 |
| `evaluation.py` | TOPSIS、熵权法、DEA、PCA、RSR、FAHP | 综合评价、效率分析、排名 |

**预测与回归 (27)**

| 模块 | 核心方法 | 竞赛场景 |
|------|---------|---------|
| `grey_system.py` | GM(1,1)、灰色关联、灰色聚类 | 小样本预测、因素分析 |
| `regression.py` | 多元回归、岭回归、Lasso、Logistic | 数据拟合、因果分析、二分类 |
| `interpolation.py` | Lagrange、Newton、三次样条 | 曲面重建、缺失值填补 |
| `time_series.py` | 移动平均、指数平滑、Gompertz/Logistic、自适应滤波 | 趋势预测、增长模型、信号去噪 |

**优化与规划 (9)**

| 模块 | 核心方法 | 竞赛场景 |
|------|---------|---------|
| `metaheuristic.py` | GA、PSO、SA、蚁群、鱼群 | 组合优化、参数搜索 |
| `math_programming.py` | 线性规划、整数规划、目标规划、非线性规划 | 资源分配、背包、选址 |

**图论与网络 (11)**

| 模块 | 核心方法 | 竞赛场景 |
|------|---------|---------|
| `graph_theory.py` | Dijkstra、Floyd、最小生成树、最大流、最小费用流、图染色、Euler路径、匈牙利匹配 | 最短路径、网络优化、指派问题 |

**随机模拟 (8)**

| 模块 | 核心方法 | 竞赛场景 |
|------|---------|---------|
| `monte_carlo.py` | 积分、优化、M/M/c、M/M/S/k、随机游走 | 风险分析、排队论、随机过程 |

**机器学习 (4)**

| 模块 | 核心方法 | 竞赛场景 |
|------|---------|---------|
| `neural_network.py` | BP、RBF、SOM、MIV 变量重要性 | 分类、回归、特征筛选 |

**元胞自动机 (6)**

| 模块 | 核心方法 | 竞赛场景 |
|------|---------|---------|
| `cellular_automata.py` | 生命游戏、森林火灾、DLA、SIRS、NaSch 交通流 | 交通流、传染病、自组织临界 |

**图像处理 (7)**

| 模块 | 核心方法 | 竞赛场景 |
|------|---------|---------|
| `image_processing.py` | 边缘检测、分割、形态学、特征提取 | 遥感、医学影像、去噪 |

**论文与图表 (34)**

| 模块 | 核心方法 | 竞赛场景 |
|------|---------|---------|
| `sci_figures.py` | 11 种建模结果图、模型证据契约、审查与矢量/450 DPI 交付 | 验证、比较、灵敏度、优化与论文可视化 |
| `diagram.py` | 流程图、ER 图、三线表、SQL 解析 | LaTeX 配图 |
| `paper_check.py` | 论文质量检查（结构/图表/引用/数值） | 提交前终检 |

**快速使用 / Quick Start:**

```python
from algorithms import monte_carlo_integration, edge_detection, topsis

# 蒙特卡罗积分
result = monte_carlo_integration(lambda x: x**2, 0, 1)

# 图像边缘检测
edges = edge_detection(image, method='canny')

# TOPSIS 综合评价
rank = topsis(decision_matrix, weights, benefit_indicators)
```

### 🎯 标准 Codex Skills (`skills/`)

**Codex 标准 Skills (`skills/`)：**

`run-modeling-project`、`select-model`、`solve-model`、`analyze-model-data`、`research-model-literature`、`make-model-figures`、`write-model-paper`、`review-model-paper`。每个技能均包含可触发的 `SKILL.md` 和 `agents/openai.yaml`，详细知识按需放在 `references/`，确定性检查放在 `scripts/`。其中 `run-modeling-project` 负责严格阶段门、断点恢复、运行清单和交接，其余七个 Skill 承担具体建模任务。

`legacy/skills/` 中的 56 个旧命令仅作兼容档案，不再是入口、不会被安装，也不应直接执行。迁移关系见 `legacy/command-map.yaml`；新任务唯一推荐入口是上述标准 Skills，完整项目优先从 `$run-modeling-project` 开始。

### 📐 国赛论文排版模板 / CUMCM Paper Template (`template/`)

从校赛获奖论文中提炼的国赛标准排版规范，开箱即用：

2026 国赛模式不生成目录：摘要是电子版第 1 页，问题重述随后开始且页码连续；摘要页不计入正文 30 页上限，正文恰好 30 页时附录可从电子版第 32 页开始。competition 默认交付 PDF，PDF/DOCX 二选一即可；audit 才要求双格式。论文文件和支撑材料 ZIP/RAR 分别不得超过 20 MiB。附录必须列出支撑材料的完整文件清单并包含全部自有完整源程序，支撑包须在干净临时目录复现通过，并通过元数据、身份信息和绝对路径扫描。提交前还须将 `config/cumcm-identities.example.json` 复制为项目根目录的 `.cumcm-identities.json` 并填写所有身份组；该私密文件已被 Git 忽略且不得装入支撑包，缺失或不完整会直接阻止提交就绪。2026 年起还须在参考文献前加入 `AI工具使用声明`；如使用 AI，支撑材料必须包含 `AI工具使用详情.pdf`。

| 排版要素 | 实现方式 |
|---------|---------|
| 一级标题 | 居中 16pt 黑体，中文数字编号（一、二、三...）自动生成 |
| 二级/三级标题 | 左对齐正文黑体，阿拉伯数字编号（1.1 / 1.1.1） |
| 正文引用 | `\cite{key}` 自动渲染为右上角角标 `[1]` |
| 参考文献 | `thebibliography` 按正文中首次引用顺序排列 |
| 附录代码框 | `pycode` 环境：10.5pt 等宽字体、行号、灰背景、单线框 |
| 图表 | 图题在下居中、表题在上居中、三线表、`\tabnote{}` 表注 |

编译方式：`xelatex` × 2（无需 bibtex）

### 📋 竞赛工作流 / Competition Workflow

```
Day 1: 选题分析 → 文献调研 → 问题拆解
Day 2: 模型假设 → 数学推导 → 方案设计
Day 3: 编程求解 → 数据处理 → 敏感性分析
Day 4: 论文撰写 → 图表制作 → 结果验证
Day 5: 全文审校 → 格式排版 → 最终检查
```

### 🧪 历年赛题基准 / Historical Benchmarks (`benchmarks/`)

仓库包含 2020--2023 年 CUMCM A/B/C 共 12 道基准题的元数据，不复制完整题面，只链接官方赛题归档。每个案例定义模型族、最低基线、验证目标和常见失败模式，并使用统一的 100 分量表与四项硬门评分。

```bash
python scripts/validate_benchmarks.py
python scripts/score_benchmark.py path/to/scorecard.json
```

评分必须链接实际证据文件；高分不能绕过来源可追溯、结果可复现、完整回答子问题和禁止伪造证据四项硬门。

### 🧾 统一运行清单 / Run Manifest (`schemas/run-manifest.schema.json`)

每次正式运行都应在项目根目录保存 `run-manifest.json`。它统一记录输入文件 SHA-256、模型与参数版本、命令、随机种子、Git 状态、Python/依赖环境、指标、失败尝试、局限和产物哈希。仓库只保存项目相对路径，拒绝目录穿越和未记录种子的随机运行。

```bash
python scripts/run_manifest.py create \
  --spec path/to/run-spec.json --project-root path/to/project \
  --output path/to/project/run-manifest.json
python scripts/run_manifest.py validate path/to/project/run-manifest.json \
  --project-root path/to/project --verify-files
```

可从 `schemas/run-manifest.example.json` 复制精简运行规格；正式清单遵循 `schemas/run-manifest.schema.json`。

### ✅ 覆盖率质量门 / Coverage Gate

CI 按 `coverage-policy.json` 强制执行：算法包总体语句覆盖率不低于 65%，`graph_theory.py`、`image_processing.py`、`math_programming.py`、`metaheuristic.py` 和 `monte_carlo.py` 五个关键模块分别不低于 80%。纯示范入口不计入生产覆盖率；模块本身不因覆盖率较低而被整体排除。

```bash
python -m pytest code/tests --cov=algorithms --cov-report=json:coverage.json
python scripts/check_coverage.py coverage.json
```

---

## 项目结构 / Project Structure

```
math-model-agent/
│
├── code/                            # 🔧 代码模块
│   ├── algorithms/                  # 25 个 Python 算法与质量模块（可直接 import）
│   │   ├── __init__.py              # 统一导出入口，from algorithms import * 即用
│   │   ├── ahp.py                   # 层次分析法：AHP 构造、一致性检验 CR
│   │   ├── grey_system.py           # 灰色系统：GM(1,1) 预测、灰色关联分析
│   │   ├── regression.py            # 回归分析：多元回归、岭回归、Lasso
│   │   ├── interpolation.py         # 插值拟合：Lagrange、样条、径向基
│   │   ├── graph_theory.py          # 图论算法：Dijkstra、Floyd、Kruskal 最小生成树
│   │   ├── fuzzy_math.py            # 模糊数学：隶属函数、模糊综合评价
│   │   ├── neural_network.py        # 神经网络：BP、RBF、SVM
│   │   ├── metaheuristic.py         # 元启发式优化：遗传算法 GA、模拟退火 SA、粒子群 PSO、蚁群
│   │   ├── cellular_automata.py     # 元胞自动机：1D/2D CA、生命游戏
│   │   ├── monte_carlo.py           # 蒙特卡罗：积分、优化、排队系统、随机游走
│   │   ├── image_processing.py      # 图像处理：边缘检测、分割、形态学
│   │   ├── evaluation.py            # 综合评价：TOPSIS、DEA、PCA、RSR
│   │   ├── sci_figures.py           # 科研图表：11 种标准科研可视化
│   │   ├── diagram.py               # TikZ 图表生成：LaTeX 配图自动化
│   │   ├── paper_check.py           # 论文检查：格式、引用、一致性审查
│   │   ├── time_series.py           # 时间序列：移动平均、指数平滑、趋势外推
│   │   └── math_programming.py      # 数学规划：线性/整数/目标/非线性规划
│   ├── solve.py                     # 求解脚本示例（2022 国赛 A 题波浪能）
│   ├── visualize.py                 # 可视化示例脚本
│   └── results.json                 # 求解结果存档
│
├── legacy/                          # 📦 兼容档案（不安装、不推荐）
│   ├── command-map.yaml             # 56 个旧命令到标准 Skills 的迁移表
│   └── skills/                      # 旧 Claude Code 命令文档
│   ├── README.md                    # Skills 索引与使用说明
│   │
│   ├── core/                        # 📦 17 个核心建模 Skills
│   │   ├── math_model_skill.md      # 五层能力架构总控
│   │   ├── model_selector.md        # 18 种问题类型 → 模型决策树
│   │   ├── model_library.md         # 15 个模块模型库速查
│   │   ├── model_library_extended.md# 扩展模型库（更多方法）
│   │   ├── modeling_pipeline.md     # 11 步统一建模流程
│   │   ├── modeling_norms.md        # 建模规范与最佳实践
│   │   ├── judge_engine.md          # 六维度评审引擎
│   │   ├── paper_generator.md       # 结构化论文生成
│   │   ├── paper_check.md           # 论文质量检查清单
│   │   ├── python_mapping.md        # MATLAB → Python 映射表
│   │   ├── evaluation.md            # 综合评价方法指南
│   │   ├── monte_carlo.md           # 蒙特卡罗决策与模板
│   │   ├── image_processing.md      # 图像处理流水线
│   │   ├── sci_figures.md           # 11 种科研图表规范
│   │   ├── diagram_tools.md         # TikZ / 图表工具指南
│   │   └── math_competition_guide.md# 竞赛实战全流程指南
│   │
│   ├── latex/                       # 📄 5 个 LaTeX 编译 Skills
│   │   ├── compile-latex.md         # XeLaTeX 自动编译（含错误修复重试）
│   │   ├── extract-tikz.md          # 提取 TikZ 图表转 SVG
│   │   ├── new-diagram.md           # 从模板生成 TikZ 图表
│   │   ├── proofread.md             # 语法拼写检查
│   │   └── visual-audit.md          # 视觉布局审计
│   │
│   ├── paper/                       # ✍️ 6 个论文写作 Skills
│   │   ├── review-paper.md          # 论文审阅（七维度）
│   │   ├── seven-pass-review.md     # 七遍审稿法
│   │   ├── validate-bib.md          # 参考文献一致性检查
│   │   ├── humanize.md              # AI 痕迹消除、人味润色
│   │   ├── preregister.md           # 预注册研究方案
│   │   └── respond-to-referees.md   # 审稿回复信撰写
│   │
│   ├── research/                    # 🔬 5 个研究构思 Skills
│   │   ├── lit-review.md            # 文献综述系统梳理
│   │   ├── ideation.md              # 研究选题与创意生成
│   │   ├── interview-me.md          # 苏格拉底式提问引导
│   │   ├── devils-advocate.md       # 魔鬼代言人（挑刺反驳）
│   │   └── research.md              # 研究设计全流程
│   │
│   ├── data/                        # 📊 4 个数据分析 Skills
│   │   ├── data-analysis.md         # 数据清洗 / EDA / 统计检验 / 特征工程
│   │   ├── audit-reproducibility.md # 可复现性审计
│   │   ├── review-r.md              # R 代码审查
│   │   └── stata-replication.md     # Stata 复现映射
│   │
│   ├── quarto/                      # 🌐 3 个 Quarto 部署 Skills
│   │   ├── deploy.md                # 部署到 GitHub Pages
│   │   ├── translate-to-quarto.md   # LaTeX → Quarto 转换
│   │   └── qa-quarto.md             # Quarto 质量对比检查
│   │
│   ├── lecture/                     # 🎓 3 个讲座课程 Skills
│   │   ├── create-lecture.md        # 课程/讲座创建
│   │   ├── pedagogy-review.md       # 教学法审查
│   │   └── slide-excellence.md      # 幻灯片优化
│   │
│   ├── workflow/                    # ⚙️ 10 个工作流 Skills
│   │   ├── commit.md                # Git 智能提交
│   │   ├── checkpoint.md            # 检查点保存
│   │   ├── learn.md                 # 学习模式
│   │   ├── prompt.md                # 提示词优化
│   │   ├── deep-prompt.md           # 深度提示词
│   │   ├── prompt-only.md           # 仅提示词模式
│   │   ├── compress-session.md      # 会话压缩
│   │   ├── context-status.md        # 上下文状态查看
│   │   ├── promote-memory.md        # 记忆提升
│   │   └── standard-save.md         # 标准保存
│   │
│   └── audit/                       # 🔍 3 个审计验证 Skills
│       ├── deep-audit.md            # 深度审计
│       ├── verify-claims.md         # 声明验证
│       └── permission-check.md      # 权限检查
│
├── skills/                          # 🤖 8 个标准 Codex Skills
│   ├── run-modeling-project/        # 阶段门、恢复与交接总控
│   ├── select-model/                # 赛题分类与模型选型
│   ├── solve-model/                 # 建模、求解与验证
│   ├── analyze-model-data/          # 数据分析与可复现输出
│   ├── research-model-literature/   # 文献检索与引用核验
│   ├── make-model-figures/          # 科研绘图与视觉检查
│   ├── write-model-paper/           # 建模论文写作
│   └── review-model-paper/          # 提交前论文审查
│
├── template/                        # 📐 国赛 LaTeX 论文排版模板
│   └── cume-template.tex            # 完整模板（标题等级/角标引用/代码框/三线表）
│
├── patterns/                        # 📝 6 个获奖论文模式库
│   ├── abstract_patterns.md         # 摘要写作模式（问题→方法→结果→关键词）
│   ├── model_selection_rules.md     # 模型选择决策规则
│   ├── discussion_rules.md          # 讨论/分析写作规范
│   ├── evaluation_rules.md          # 模型评价写作规范
│   ├── appendix_rules.md            # 附录代码排版规范
│   └── visual_rules.md             # 图表可视化规范
│
├── data/                            # 📁 示例数据集（空，竞赛时放入题目数据）
├── figures/                         # 🖼️ 示例图表（2022 国赛 A 题波浪能配图）
│   ├── fig01_time_history.png       # 时序图
│   ├── fig02_power_vs_damping.png   # 功率-阻尼关系图
│   ├── fig03_power_heatmap.png      # 功率热力图
│   └── fig04_sensitivity.png        # 敏感性分析图
├── paper/                           # 📄 论文输出目录（空，编译产物存放处）
│
├── 使用说明.md                      # 📖 完整使用指南（含工作流演示）
├── CHANGELOG.md                     # 📋 版本历史
└── README.md                        # 📖 本文件
```

---

## 快速开始 / Getting Started

### 1. 克隆仓库 / Clone

```bash
git clone https://github.com/chengziyue1222/math-model-agent.git
cd math-model-agent
```

### 2. 安装依赖 / Install Dependencies

需要 Python 3.10 或更高版本。

```bash
python -m pip install .

# 开发与测试环境
python -m pip install ".[dev]"
```

### 3. 使用算法库 / Use Algorithm Library

```python
import sys
import numpy as np
sys.path.insert(0, 'code')
from algorithms import *

# AHP 层次分析法
weights, lambda_max, CR, passed = ahp_weight(comparison_matrix)

# GM(1,1) 灰色预测
predicted = gm11_predict(data, predict_count=5)

# 遗传算法优化
lower = np.array([-5.0, -5.0])
upper = np.array([5.0, 5.0])
def sphere(X):
    return np.sum(X**2, axis=1)
result = genetic_algorithm(sphere, 2, (lower, upper), vectorized=True)
```

### 4. 使用 Codex Skills / Use Codex Skills

标准技能包位于 `skills/`。安装全部技能：

```bash
python scripts/install_skills.py
```

也可只安装指定技能，或先预览目标路径：

```bash
python scripts/install_skills.py select-model solve-model
python scripts/install_skills.py --dry-run
```

安装后可使用 `$select-model`、`$solve-model`、`$review-model-paper` 等名称调用。安装器会为每个 Skill 复制私有 `_runtime`，因此执行入口不依赖本源码仓库继续保留在原路径。`pip install .` 仅安装可导入的 `algorithms` Python 包；Skill、论文模板和旧版命令文档是仓库配套资源，不混入 wheel。源码分发包仍保留这些资源，便于完整归档。

### 5. 兼容档案 / Compatibility Archive

`legacy/skills/` 保留旧版命令原文，仅供追溯，不是可安装或推荐的 Skill。请查阅 `legacy/command-map.yaml`，改用对应的标准 `$skill-name`；完整建模项目使用 `$run-modeling-project`。

---

## 蒸馏来源 / Distillation Sources

| 来源 | 内容 | 贡献 |
|------|------|------|
| 司守奎《数学建模算法与应用》第3版 | 534页，16章 | 模型决策引擎、统一建模流程、Python 映射 |
| zhanwen/MathModel (10,588⭐) | 32 张思维导图、竞赛论文 | 10 大算法类别、竞赛工作流 |
| MathModelAgent | 6 阶段工作流 | 科研图表模板、论文校验 |
| Starry-cz/academic-data-visualization | Apache-2.0 出版级绘图 Skill | 图表契约、版面规格、无障碍配色与多阶段 QA 思路 |
| Giyn/MathematicalModelingAlgorithm | TOPSIS/DEA/PCA/RSR | 综合评价方法实现 |
| 国赛/美赛获奖论文 (12篇) | 实战模式提炼 | 摘要模板、验证体系、讨论结构 |

---

## 竞赛覆盖 / Competition Coverage

- ✅ 全国大学生数学建模竞赛 (CUMCM)
- ✅ 美国大学生数学建模竞赛 (MCM/ICM)
- ✅ 研究生数学建模竞赛
- ✅ MathorCup、华为杯等企业赛事

---

## 版本历史 / Changelog

- **v7.3.0** (2026-09-23) — Streamlit 界面与 2026 CUMCM 提交预检；公开导出增至 149，图表设计系统补齐调色板与中文字体回退
- **v7.2.0** (2026-08-10) — 新增 rapid / competition / audit 三档工作流，统一标准 Skill 的可执行契约入口，并校正文档与 Windows 测试体验
- **v6.0** (2026-07-08) — 蒸馏 zhanwen/MathModel + MathModelAgent，新增蒙特卡罗、图像处理、综合评价、竞赛工作流
- **v5.0** (2026-06-16) — 部署 CodeBuddy 论文 Skills + 数学建模 Skills，总计 55 个 slash commands
- **v4.0** (2026-06-16) — 整合 36 个 Claude Code Skills
- **v3.0** (2026-06-15) — 蒸馏《数学建模算法与应用》教材
- **v2.0** (2026-06-15) — 融合获奖论文模式库

详见 [CHANGELOG.md](CHANGELOG.md)。

---

## 反馈、贡献与支持 / Feedback, Contributions, and Support

欢迎通过 GitHub Issues 提交可复现的 bug、功能建议或文档问题；请附上 Python 版本、运行命令、完整报错和最小复现数据（请勿上传敏感或受限数据）。

如需私下联系，请发送邮件至 [chengziyue1222@163.com](mailto:chengziyue1222@163.com)。

如果这个项目对你有帮助，欢迎赏脸笔者一杯咖啡；感谢你的支持，赞赏不附带技术支持或功能交付承诺。后续将继续维护升级。

<p align="center">
  <img src="assets/support/wechat-support.jpg" alt="微信赞赏码" width="280">
</p>

---

## 许可证 / License

MIT
