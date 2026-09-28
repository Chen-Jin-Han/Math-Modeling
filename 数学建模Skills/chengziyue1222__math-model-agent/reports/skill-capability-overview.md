# 数学建模标准 Skills 升级与能力概括

更新时间：2026-07-26

范围：仓库内 8 个标准 Skills、通用算法库、工作流功能库、论文生成与审查链

原则：优秀论文仅用于提炼可迁移能力；CUMCM 2021 C 的数据字段、题目分解和展示内容保留在项目适配器中，不写入通用算法。

## 一、本次场景驱动升级

| 本次发现或应用场景 | 暴露的问题 | 升级后的通用行为 | 对应 Skill / 组件 |
|---|---|---|---|
| 标准执行器缺角色时仍先运行命令 | 失败有副作用，BLOCKED 太晚 | 输入/输出角色在子进程启动前预检；违规运行留痕但命令不执行 | `run-modeling-project`、`run_standard_skill.py` |
| Skill 由目录实现时生产者哈希为空 | 无法证明具体实现版本 | 对目录内全部实现文件生成稳定聚合哈希，同时记录运行时和契约版本 | `skill_runtime.py` |
| 阶段门禁文档强于实际代码 | 可绕过 `decision_contract`、`quality_validation` 等证据 | 可执行门禁与文档完全对齐；每次推进前复核全部历史证据哈希 | `run-modeling-project` |
| C 题模型计划脚本直接生成契约 | 契约结构没有独立检查 | 新增通用决策契约校验，拒绝重复问题 ID、缺结果或缺验证的条目 | `select-model`、`modeling_contracts.py` |
| 数据分析只有行列数、缺失和负数 | 不足以支持未来 24 周不确定性论证 | 新增面板稀疏性、滞后相关、实体间相关、末段时间留出诊断 | `analyze-model-data`、`data_diagnostics.py` |
| 文献脚本内置 2021 C 书目 | 通用 Skill 会偷偷携带题目答案背景 | 必须显式输入 `source_candidates`；统一校验 DOI/ISBN/URL、重复身份并生成 BibTeX | `research-model-literature`、`modeling_contracts.py` |
| 动态库存、服务水平、基线和词典序由题目脚本手写 | 审查逻辑不可迁移，比较口径可能漂移 | 抽取状态守恒、服务水平、同口径策略比较、词典序排序为通用算法 | `solve-model`、`modeling_quality.py` |
| C 题图脚本另走 240 dpi 手工保存 | 与正式图表 Skill 的 450 dpi/元数据规则不一致 | 项目适配器统一调用正式导出：PDF、SVG、450 dpi PNG、逐图 `.figure.json` 审计 | `make-model-figures`、`sci_figures.py` |
| 论文质量依赖固定图表/公式数量 | 数量容易变成替代内容质量的目标 | 最低阈值改为 `paper-spec.yaml` 可声明；仍强制逐题结果、验证与证据覆盖 | `write-model-paper`、`paper_readiness.py` |
| 独立复核只扫描少量关键词 | 可由空泛文字通过，且只绑定正文哈希 | 复核正文覆盖、逐题产物、质量讨论与局限；同时绑定正文、决策契约、质量验证三个哈希 | `review-model-paper`、`adversarial_review.py` |

## 二、8 个标准 Skills 概括

### 1. `run-modeling-project`

负责从 intake 到 release 的可恢复编排。核心能力包括：严格单步阶段推进、全角色门禁、历史证据新鲜度复核、阻塞/恢复历史、标准 Skill 运行追踪、实现聚合哈希、产物生产者注册和反旁路检查。

### 2. `select-model`

负责逐题分解、候选模型比较、基线设计、验证路线和决策契约。对动态状态、不确定性、多目标和基线要求做显式声明；契约必须机器校验后才能交给求解、写作和审查。

### 3. `analyze-model-data`

负责不可变原始数据审计、数据字典、缺失/异常/泄漏检查、预处理记录、探索分析和时间留出。对于实体×时间数据，额外报告零膨胀、活跃实体、滞后相关、横截面依赖及训练/末段留出漂移。

### 4. `research-model-literature`

负责检索记录、来源身份核验、方法对照、可迁移规则提取和 BibTeX。来源候选必须来自显式输入或真实检索结果；通用脚本不再携带任何 C 题固定书目。优秀论文仅能支持结构、论证和审查规则，不得替代独立计算。

### 5. `solve-model`

负责模型规格、算法实现、基线、求解、仿真、敏感性/稳健性和质量验证。新增通用动态守恒、服务水平、同口径基线比较和词典序工具；随机或鲁棒结论必须说明场景来源、依赖假设和末段留出/压力证据。

### 6. `make-model-figures`

负责“结论—证据—数据源—图形”契约、科学图表生成、渲染审查和正式导出。所有正式图同时输出 PDF、SVG、450 dpi PNG 与审计 JSON，并登记数据源、样本定义、哈希和正文插入状态。

### 7. `write-model-paper`

负责从证据注册表生成 brief、teaching 或 competition 三种论文模式。正式模式要求 `paper-spec`、证据/结论/公式/图/表注册表、逐题决策产物和质量验证。CUMCM 布局继续严格执行 A4、指定页边距、宋体/黑体、1.5 倍行距、2em 缩进、独立封面与摘要、正文页码重置、三线表、参考文献和代码附录规则。

### 8. `review-model-paper`

负责结构、数学、图表、证据、验证、引用六个失败即停门禁。解析 `[claim:ID]`、JSON Pointer 和 SHA-256，检查决策契约、状态平衡、不确定性、权衡、基线及逐题产物。复杂论文还需三哈希绑定的独立二次复核。

## 三、算法库概括

当前 `code/algorithms` 有 22 个模块、142 个公开导出。

| 类别 | 模块 / 主要能力 |
|---|---|
| 综合评价与决策 | AHP、模糊综合评价、熵权、TOPSIS、DEA、PCA、RSR、灰色关联、组合权重 |
| 预测与回归 | GM(1,1)/GM(2,1)、Verhulst、线性/岭/多项式/非线性/Logistic 回归、插值、移动平均、指数平滑、增长曲线 |
| 优化与规划 | 线性/整数/目标/非线性规划，遗传算法、粒子群、模拟退火、蚁群、人工鱼群 |
| 图论与网络 | 最短路、Floyd、最小生成树、最大流、最小费用流、关键路径、着色、欧拉路、匈牙利匹配 |
| 随机仿真 | 蒙特卡洛积分/优化/仿真、排队模型、随机游走 |
| 机器学习与复杂系统 | BP、RBF、SOM、MIV，元胞自动机、SIRS、交通流 |
| 图像与图表 | 图像滤波/分割/特征，科学图表、流程图、ER 图、系统图和表格 |
| 论文质量 | 论文检查、证据门禁、对抗语义审查、正式图形审计 |
| 本次新增的数据诊断 | `panel_diagnostics`：面板稀疏性、时序/横截面依赖、末段留出 |
| 本次新增的建模质量 | `validate_state_balance`、`service_level_metrics`、`compare_policy_metrics`、`lexicographic_order` |
| 本次新增的证据契约 | 决策契约、逐题文件、质量验证、文献身份/重复校验和 BibTeX 生成 |

算法库提供可迁移的计算与审查原语；C 题中的供应商字段、A/B/C 转化系数、24 周计划和具体图表列映射仍位于各 Skill 的 `scripts/*supplier*` 适配器中。

## 四、功能库概括

仓库级 `scripts` 提供 11 个主要功能模块：

- Skill 安装与结构校验：`install_skills.py`、`validate_skills.py`。
- 契约与执行：`skill_contracts.py`、`run_standard_skill.py`。
- 防篡改追踪与生产者登记：`skill_runtime.py`。
- 数据/结果运行清单：`run_manifest.py`。
- 全流程反旁路验证：`validate_skill_workflow.py`。
- 覆盖率与回归阈值：`check_coverage.py`。
- 历史基准评分与验证：`score_benchmark.py`、`validate_benchmarks.py`。
- 旧产物隔离验证：`validate_legacy_archive.py`。

功能库负责“能否执行、是否留痕、产物是谁生成、证据有没有变化、流程有没有绕开 Skill”；算法库负责“如何计算与验证”；8 个 Skills 负责“何时调用、需要哪些证据、何时阻塞”。

## 五、论文能力与边界

论文链目前覆盖：

1. 决策契约定义逐题必须回答什么。
2. 求解输出 `result_object` 和 `quality_validation`。
3. 结论、公式、图、表、证据和引用分别登记。
4. 正式图形逐图审计并输出多格式。
5. 正文按注册证据生成，关键数字绑定 claim。
6. CUMCM TeX 布局做静态门禁并编译 PDF。
7. 六门禁审查与三哈希独立复核。
8. PDF/DOCX 由各自正式工具生成、渲染和检查。

边界仍然明确：Skill 能保证流程、证据、格式和可复现性达到仓库门禁，不能保证获奖；压力测试不能自动变成校准概率；官方优秀论文不能成为本题数字、参数或答案的来源。

## 六、验证证据

- 8/8 个 Skill 通过 `skill-creator` 的结构校验。
- `scripts/validate_skills.py`：8 个标准 Skills 全部通过。
- `python -m pytest code/tests -q`：287 项通过。
- `scripts/validate_benchmarks.py`：12 个历史基准通过。
- 新增对抗覆盖包括：前置契约阻断副作用、目录 Skill 实现哈希、历史证据变更、重复文献身份、非共享输入策略比较、状态残差/下界、时间留出、三哈希复核失效、正式图表禁止 240 dpi 手工旁路。
