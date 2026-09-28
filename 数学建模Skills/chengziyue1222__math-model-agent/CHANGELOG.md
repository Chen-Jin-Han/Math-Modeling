# CHANGELOG - Math Model Skill

## Unreleased

## v7.3.0 (2026-09-23)

### Nova 本地演示与部署分层

- 新增 `demo/` 离线演示：`python demo/run_demo.py --case <CASE>` 在无服务器、无公网、无云账号、无模型 Key 的条件下跑通三个案例，分别产出 `READY_FOR_REVIEW`、`BLOCKED`、`NEEDS_REVIEW` 门禁结论。
- 新增 `ui/app.py` Streamlit 单页演示、`start_api.sh`、`requirements-prod.txt` 与 `DEPLOYMENT_TENCENT.md`，明确 Nova Core、Nova API、Nova Eval、本地演示与 UI 的分层边界。
- 新增 `README_DEMO.md`，说明 `READY_FOR_REVIEW` 仅表示可进入人工复核，不代表自动批准或自动上线。

### 图表设计系统

- `algorithms` 新增 5 个公开导出：`get_modeling_palette`、`resolve_cjk_font`、`add_panel_label`、`mm_to_inches`、`publication_size`；公开导出总数由 144 增至 149。
- `sci_figures` 补充语义调色板、CJK 字体解析与期刊栏宽换算能力；找不到中文字体时回退到 DejaVu Sans，不在无中文字体的 Linux 环境下中断出图。
- `$make-model-figures` 新增 `references/palette-system.md`、`design-and-routing.md`、`visual-qa-checklist.md` 与 `scripts/preview_palettes.py`。

### 提交预检与匿名化

- 新增 `$review-model-paper/scripts/submission_preflight.py` 与 `references/cumcm-2026-preflight.md`，覆盖 2026 CUMCM 提交前的身份信息、绝对路径、支持包依赖与归档格式检查。
- `document_validation.py` 与 `production_guards.py` 改为报告工作区相对路径，论文、图表、运行清单与提交预检不再写入用户绝对路径。
- 新增 `config/cumcm-identities.example.json` 占位模板；真实身份字典 `.cumcm-identities.json` 由 `.gitignore` 排除。

### Skill 安装与运行契约

- `scripts/install_skills.py` 为每个 Skill 复制私有 `scripts/_runtime/`，安装后的 `execute_skill.py` 入口不再要求源码仓库保留在原路径。
- `scripts/validate_skills.py` 改为按安装器实际复制的源文件校验 `scripts/_runtime/*` 引用，而不是按检出目录校验，使该检查在未安装状态下依然有效。
- 新增 `distilled-competition-playbook.md`、`cumcm-2026-authoring.md` 与 AI 工具使用说明模板。

### 发布与打包

- `pyproject.toml` 的 wheel 仅包含可导入的 `algorithms` 包，与 README 的安装约定一致；`nova_*` 应用继续从仓库运行。
- 源码分发包不再包含 `__pycache__`、`.pyc` 与本机构建元数据。
- `.gitignore` 新增 `coverage.json` 与 `.cumcm-identities.json`。

## v7.2.0 (2026-08-10)

### Workflow Profiles and Usability

- Added `rapid`, `competition`, and `audit` workflow profiles so exploratory work keeps mathematical non-negotiables without inheriting every formal-delivery gate.
- Made CUMCM layout checks venue-specific rather than a default for every modeling task.
- Added a concise executable-contract entry point to every standard Skill and aligned the project coordinator UI prompt with profile selection.

### Consistency and Developer Experience

- Corrected public documentation to report 8 standard Skills, 56 archived legacy commands, 25 module files, and 144 public algorithm exports.
- Configured pytest to use the Git-ignored repository-local `.test-tmp/pytest` directory, avoiding access-controlled Windows system temp directories.
- Removed four Ruff-reported unused imports and variables from shipped Skill scripts.

### 总控建模 Skill

- 新增 `$run-modeling-project`，按 intake、analysis、modeling、validation、writing、review、release 七阶段协调现有专项 Skills。
- 新增带文件哈希的阶段门状态工具，支持阻塞记录、断点恢复、严格单步推进和标准化交接，禁止以叙述替代证据。

### 旧命令归档

- 将 56 个旧版 Claude Code 命令从主入口移至 `legacy/skills/` 兼容档案；它们不再安装或推荐。
- 新增完整迁移表和档案校验器，八个标准 Codex Skills 成为唯一推荐入口。

### 运行可追溯性

- 新增统一 `run-manifest.json` 规范、示例、生成器和完整性校验器，记录数据哈希、模型版本、参数、种子、Git/运行环境、指标、失败尝试、局限与产物路径。
- 路径限制为项目相对路径；随机运行必须记录 seed；可选择逐文件复核 SHA-256 和字节数。

### 覆盖率与高价值测试

- 将算法包总体覆盖率门槛提高到 65%，图论、图像处理、数学规划、智能优化和蒙特卡罗五个关键模块分别强制达到 80%。
- 新增 NetworkX/SciPy 差分测试，以及随机图、流守恒、Euler 路径、形态学、回归、时间序列、灰色模型、模糊模型、随机优化和排队论的异常、边界与性质测试。

### 历年赛题基准

- 新增 2020--2023 年 CUMCM A/B/C 共 12 道基准题元数据，覆盖物理建模、优化、几何、运筹、预测、分类、仿真和决策。
- 新增统一评分量表、证据链接计分器和基准目录校验，官方题面仅保留来源链接。

## v6.6.0 (2026-07-18)

### 数学建模图表交付

- 将 Starry-cz/academic-data-visualization 的图表契约、出版尺寸、无障碍配色与多阶段 QA 思路融入 `make-model-figures`，保留 Apache-2.0 来源说明且不复制其素材库。
- 新增面向模型版本、情景、参数来源和随机性的 `FigureContract`、89/183 mm 尺寸、出版样式和 `audit_publication_figure`，检查字号、文字越界、栏宽与高风险色图。
- 新增 `export_publication_figure`，一次生成 PDF/SVG 矢量主稿、450 DPI PNG 校样和可追溯 `.figure.json` 审查记录。

### Correctness, reproducibility, and release engineering

- 修复遗传算法最大化符号、最小费用流供需方向与不可行解处理、边缘算子有符号卷积，并增加对应回归测试。
- 修复通用蒙特卡罗 seed、精确图染色与 LaTeX 注释/内嵌参考文献检查。
- 重构 `code/visualize.py`，统一复用求解公式，重新生成四张示例图并以端到端测试核对 7433.30 W 结果。
- 将 SciPy 下限提高到 1.9；CI 增加安装、仓库外导入、Skill 校验、Ruff、覆盖率、端到端绘图与构建。
- 明确 wheel 仅发布 `algorithms`，增加标准 Skill 安装脚本与源码分发资源清单，并清理 Ruff 问题和文档漂移。

### Codex Skill 标准化

- 新增 7 个标准 Codex Skills，包含 `SKILL.md`、UI 元数据、按需引用和确定性检查脚本。
- 将旧的提交、部署、深度审计流程改为安全默认值，外部写操作需要明确授权。
- 加强文献真实性、数据泄漏、论文披露和可复现性规则。
- 修复算法包因 `Dict` 未导入而无法加载的问题，并校正蒙特卡罗、数学规划和图像处理能力映射。
- 将实际 Python 支持范围统一为 3.10–3.13，并补充数学规划与时间序列测试。

## v6.5 (2026-07-11)

### 全链路审计与工程规范修复

**数字一致性校正（P0）**
- 算法库导出计数校正：此前分组注释误计为 106，实际 `__all__` 为 120 项；统一 README/使用说明/`__init__.py` docstring 全部为「120 个导出，17 个模块」
- 补导出漏网函数：`artificial_fish_swarm`（鱼群算法）、`build_judgment_matrix`（交互式 AHP 构造）
- skill 计数统一为 56（17 核心 + 39 扩展），更新 skill/README.md 索引

**工程规范（P1）**
- 新增 `requirements.txt`、`pyproject.toml`（含 pytest pythonpath 配置，消除 `sys.path.insert` hack）
- 新增 `LICENSE` 文件（MIT）
- 清理 `code/` 根目录临时调试文件（`_list_exports.py`/`_list_signatures.py`/`_test_import.py`）

**solve.py 物理模型修复（P1）**
- 辐射阻尼系数 `Cr` 从硬编码 `0.5` 改为 `kw*r` 的函数 `radiation_damping_coeff`（与 model.md 描述一致）
- `odeint`（deprecated）→ `solve_ivp`（RK45）
- `results.json` 改用基于 `__file__` 的绝对路径

**算法代码修复（P0/P3）**
- 移除 `dijkstra` 中的死代码（被立即覆盖的 `np.argmin` 行）
- 修复 `queuing_mmsk` 仿真利用率计算：从「离开间隔 > 1/μ」改为「总服务时间 / (服务台数 × 仿真时长)」
- 移除 `evaluation.rsr` 中未使用的 `rank_avg` 变量
- 统一 `metaheuristic.example()` 的 Rastrigin 符号（标准正号 + minimize）
- solve.py 改用项目自带 `nonlinear_programming` 求解（dogfooding），不再裸调 scipy
- 向量化 `RBFNetwork._rbf`（双重 for → 广播）、`SOM.train`（r/c 双循环 → meshgrid）、`ant_colony_tsp`（内层 for → mask）

**CI 与工程（P2）**
- 新增 GitHub Actions CI（`.github/workflows/ci.yml`）：Python 3.9–3.12 矩阵跑 pytest + 导入冒烟测试
- 清理 `__pycache__`/`.pytest_cache`，移除 conftest.py 冗余 `sys.path.insert`（由 pyproject.toml pythonpath 接管）

## v6.4 (2026-07-01)

### 新增算法（继续从 Algorithms_MathModels MATLAB 转 Python）

图论扩展（graph_theory.py）:
- **最小费用流** `min_cost_flow` — SPFA 增广路算法
- **图的染色** `graph_coloring` — 贪心/精确回溯
- **Euler 路径/回路** `euler_path` — Hierholzer 算法
- **二分图匹配** `hungarian_matching` — 匈牙利算法

时间序列扩展（time_series.py）:
- **自适应滤波** `adaptive_filter` — LMS 算法，自动调权重

算法库导出从 101 → 106 个

## v6.3 (2026-07-01)

### 新增模块（从 HuangCongQing/Algorithms_MathModels MATLAB 实现转 Python）

- **time_series.py** — 时间序列分析模块（全新文件）
  - 简单/加权/趋势移动平均
  - 一次/二次/三次指数平滑（Holt-Winters）
  - 趋势外推：Gompertz、Logistic、修正指数曲线
- **math_programming.py** — 数学规划模块（全新文件）
  - 线性规划 LP（scipy.optimize.linprog）
  - 整数规划 MILP（scipy.optimize.milp）
  - 目标规划 Goal Programming（偏差最小化）
  - 非线性规划 NLP（scipy.optimize.minimize）

算法库导出从 88 → 101 个

## v6.2 (2026-07-01)

### 新增算法（从 ravenxrz/Mathematical-Modeling 学习并转写为 Python）

- **Logistic 回归** (`regression.py`) — 梯度下降法实现二分类，自动标准化 + 截距项
- **MIV 变量重要性** (`neural_network.py`) — 基于 BP 神经网络的 Mean Impact Value 特征筛选
- **NaSch 交通流模型** (`cellular_automata.py`) — Nagel-Schreckenberg 元胞自动机，含流量-密度基本图
- **M/M/S/k 排队论** (`monte_carlo.py`) — 有限容量排队模型，解析解 + 蒙特卡罗仿真双重验证

## v6.1 (2026-07-01)

### 新增

- **template/cume-template.tex** — 国赛论文 LaTeX 排版模板（从校赛获奖论文提炼）
  - 标题等级：一级标题居中中文数字编号，二三级标题左对齐阿拉伯编号
  - 参考文献：`\cite{}` 自动右上角角标，按首次引用顺序排列
  - 附录代码框：`pycode` 环境（行号、灰背景、关键字加粗）
  - 图表格式：三线表、表注命令、中文标签
- 更新 `/mm-paper` 命令：引用模板 + 排版规范指引
- 更新 `/compile-latex` 命令：`thebibliography` 编译策略 + 格式检查点

## v4.0 (2026-06-16)

### 新增

整合36个Claude Code Skills，形成完整的学术工作流工具集：

1. **skill/latex/** — LaTeX编译相关（5个）
   - compile-latex: XeLaTeX 3遍编译Beamer
   - extract-tikz: 提取TikZ图表转SVG
   - new-diagram: 从模板生成TikZ图表
   - proofread: 语法拼写检查
   - visual-audit: 视觉布局审计

2. **skill/quarto/** — Quarto/部署（3个）
   - deploy: 部署到GitHub Pages
   - translate-to-quarto: LaTeX转Quarto
   - qa-quarto: Quarto质量对比

3. **skill/paper/** — 论文写作与审阅（6个）
   - review-paper: 7维度并行审查
   - seven-pass-review: 七遍审稿法
   - respond-to-referees: 回复审稿人
   - humanize: 检测AI写作痕迹
   - validate-bib: 验证引用完整性
   - preregister: 起草预注册文档

4. **skill/research/** — 研究与构思（5个）
   - lit-review: 结构化文献综述
   - research: 生成研究问题
   - ideation: 多轮访谈形式化
   - interview-me: 互动式访谈
   - devils-advocate: 对抗性挑战

5. **skill/data/** — 数据分析（4个）
   - data-analysis: R数据分析管道
   - review-r: R代码审查
   - audit-reproducibility: 数值声明验证
   - stata-replication: Stata复现管道

6. **skill/lecture/** — 讲座/课程（3个）
   - create-lecture: 创建Beamer讲座
   - slide-excellence: 综合幻灯片审查
   - pedagogy-review: 教学法审查

7. **skill/workflow/** — 工作流（10个）
   - commit: 完整提交流程
   - learn: 提取知识为skill
   - checkpoint: 保存状态快照
   - compress-session: 压缩会话笔记
   - context-status: 会话健康状态
   - prompt: 结构化prompt执行
   - deep-prompt: 生成prompt不执行
   - prompt-only: 只生成prompt
   - standard-save: 升级learn条目
   - promote-memory: 升级到MEMORY

8. **skill/audit/** — 审计/验证（3个）
   - deep-audit: 全仓库深度审计
   - permission-check: 权限配置诊断
   - verify-claims: 链式验证声明

### 优化

- 重构skill目录结构，按功能分类
- 创建skill/README.md主索引文件
- 更新使用说明.md，添加36个skills完整清单

---

## v3.0 (2026-06-15)

### 融合来源

- `E:\论文\数学建模算法与应用(OCR) 司守奎 第3版教材.pdf` — 534页教材，16章，覆盖LP/IP/NLP/图论/插值拟合/微分方程/数理统计/差分方程/SVM/多元统计/PLSR/智能优化/综合评价/预测方法/多目标规划

### 新增

1. **skill/model_selector.md** — 模型决策引擎 v2.0
   - 8大问题类型决策规则（规划/预测/评价/图网络/统计/微分方程/智能优化/SVM）
   - 每个模型含：IF-THEN决策规则、主模型+辅助模型+验证模型组合、Python实现代码
   - 新增：灰色预测GM(1,1)、马尔可夫预测、层次聚类(Ward法)、TOPSIS、模糊综合评价、ε约束法、目标规划、模拟退火、遗传算法

2. **skill/modeling_pipeline.md** — 统一建模流程 v2.0
   - 11步标准化流程：问题理解→假设→变量→目标→约束→模型选择→求解→验证→敏感性分析→结果解释→论文输出
   - 每步含：目标、执行步骤、输出要求、检查清单

3. **skill/python_mapping.md** — Matlab→Python工程化映射
   - 核心库对照表（linprog/fmincon/intlinprog/ode45/SVM/KMeans/PCA等）
   - 8个常用算法Python实现（线性规划/非线性规划/整数规划/ODE/GM(1,1)/TOPSIS/层次聚类/遗传算法）
   - 工程目录结构规范（data/src/model/report/）

### 优化

1. **skill/judge_engine.md** — 评审引擎升级至 v3.0
   - 评分权重调整：模型质量30(+5)、验证完整性25(+5)、创新性20、表达质量15(+5)、工程质量10
   - 新增检查项：模型合理性、参数解释、实验可信度、结果可迁移性
   - 三级验证要求明确化（解析+数值+仿真）

2. **patterns/model_selection_rules.md** — 模型选择规则库扩充
   - 新增教材来源的模型：LP/IP/NLP/多目标规划/GM(1,1)/马尔可夫/层次聚类/TOPSIS/模糊评价/PCA/DEA/SVM/模拟退火/遗传算法

### 保留

1. 所有v2.0文件完整保留
2. 波浪能项目实战经验完整保留

### 废弃

- 无：本次为教材知识蒸馏融合，不删除任何已有能力

### 原因

- 输入：司守奎《数学建模算法与应用》第3版（534页，16章）
- 目标：将教材方法论与获奖论文经验融合，形成完整的模型决策+工程实现能力
- 效果：模型覆盖从10类扩展至18类，新增统一建模流程和Python工程化映射

---

## v2.0 (2026-06-15)

### 融合来源

- `E:\论文\patterns\` — 6个模式库文件（摘要/模型选择/评估验证/图表/讨论/附录）
- `E:\论文\skill\` — 4个核心能力文件（math_model_skill/paper_generator/judge_engine/model_library）
- `E:\论文\report\` — 3个评审报告（paper_review/score_report/upgrade_report）
- `C:\Users\Blake\math-model\` — 已有波浪能项目实战经验

### 新增

1. **patterns/ 目录** — 6个模式库文件
   - `abstract_patterns.md` — 3种摘要模板（递进式/框架式/方法导向式）
   - `model_selection_rules.md` — 问题类型→模型映射决策树
   - `evaluation_rules.md` — 三级验证体系（解析/数值/仿真）
   - `visual_rules.md` — 学术图表风格规范
   - `discussion_rules.md` — 四层讨论结构（结果→对比→策略→局限）
   - `appendix_rules.md` — 附录内容与代码规范

2. **skill/ 目录** — 4个核心能力文件
   - `math_model_skill.md` — 五层能力架构（问题理解→模型选择→模型构建→求解验证→表达输出）
   - `paper_generator.md` — 结构化论文生成引擎
   - `judge_engine.md` — 六维度评审体系（100分制）+ 自动修正流程
   - `model_library.md` — 10类模型库（几何/优化/决策/数据/微分方程/搜索/成分数据/时间序列/统计/路径）

3. **使用说明.md 更新**
   - 新增附录B：核心能力文件详解
   - 新增附录D：模式库详解
   - 更新目录结构，增加 skill/ 和 patterns/ 目录

### 优化

1. **模型选择流程** — 建立问题特征→模型映射决策树，明确模型组合策略
2. **结果表达规范** — 图表必须有结论/洞察，学术风格统一，禁止默认样式
3. **讨论分析结构** — 四层讨论结构，一般性策略提炼，局限性讨论
4. **评审能力** — 六维度评审体系，自动评分与缺陷定位，最多3轮自动修正

### 保留

1. 波浪能项目的 analysis.md、model.md、code/、figures/ 完整保留
2. 使用说明.md 的阶段1-10工作流完整保留
3. 使用说明.md 的阶段11-14速查内容完整保留（已与新文件交叉引用）

### 废弃

- 无：本次为融合升级，不删除任何已有能力

### 原因

- 输入：E:\论文 下12篇获奖论文蒸馏的模式库、能力文件、评审报告
- 目标：将论文蒸馏成果与波浪能项目实战经验融合，形成完整的数学建模能力体系
- 效果：能力从单一项目经验扩展为可迁移的通用建模能力
