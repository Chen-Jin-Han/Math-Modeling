# 技术、算法、工作流与合规审计

## 仓库本质与智能体边界

当前仓库是**算法库 + Codex Skill 指令资产 + 可复现性校验脚本 + 兼容文档归档**的混合体。`skills/run-modeling-project/SKILL.md` 定义了七阶段协作流程，`skills/run-modeling-project/scripts/project_state.py` 可持久化阶段、证据哈希、阻塞和恢复；这是真实的可执行状态管理能力。可是工具选择、追问、模型拒绝、人工确认和反馈闭环主要写在 Skill 的自然语言指令中，不是一个可独立部署、可观察、可授权的 agent runtime。

因此，固定顺序地触发 8 个 Skill 不能单独证明“智能体性”。现有可证明能力是：状态机不允许跳阶段，关键 gate 要求角色化证据，阻塞可冻结推进，Manifest 可校验输入/产物哈希。尚未证明的是：动态路由、按证据拒绝模型、跨会话状态恢复、工具调用审计、教师审批流程和普通用户的端到端体验。

## 算法库与 API

- `code/algorithms/__init__.py` 的 `__all__` 为 129 个唯一符号。17 个模块职责可辨：评价、预测、优化、图论、仿真、神经网络、元胞、图像、图表/论文等。
- 高价值语义验证并非只“执行不报错”：`test_algorithm_properties.py` 将最短路、Floyd、MST、最大流、最小费用流和匈牙利匹配与 NetworkX/SciPy 比较；还测形态学边界、元启发式边界与 Monte Carlo/M/M/s/K 性质。`test_statistical_properties.py` 验证回归闭式解、非线性拟合、Logistic、季节预测、增长曲线和模糊模型不变量。`test_math_programming.py` 覆盖线性、整数、目标和非线性规划。这些测试随完整 244 项实测通过。
- 但 API 一致性不是统一契约。AST 检查显示 Monte Carlo 7 个顶层函数接受 `seed`，`metaheuristic.py` 的随机算法、`cellular_automata.py` 等直接使用 `np.random` 却没有显式 seed/rng 参数；`metaheuristic.py` 部分函数支持 `maximize`，其他优化接口的目标方向/状态返回形式不同。大量库函数仍有 `print` 副作用（如 `ahp.py` 27 处、`grey_system.py` 23 处、`regression.py` 19 处）。
- 类型标注不统一：例如 `math_programming.py` 4/5、`ahp.py` 3/5 顶层函数参数和返回值均完整标注；许多模块较好但没有项目级 Result/Exception/Randomness 协议。这会增加教师审阅和产品编排成本。

## 测试与覆盖率

实测覆盖门通过：总体 65.50%；`graph_theory.py` 98.07%、`image_processing.py` 91.25%、`math_programming.py` 96.55%、`metaheuristic.py` 96.63%、`monte_carlo.py` 95.02%。这支持关键模块有较强测试，不支持“整个库已风险充分覆盖”的结论：其余 12 个模块没有逐模块风险门槛，65% 总门槛可由高覆盖模块抵消较低覆盖模块。`coverage-policy.json` 也只定义上述五个关键文件，未说明基于参赛风险的选择依据。

## Skills、Manifest、benchmark 与模式

| 项 | 证据 | 结论 |
|---|---|---|
| 标准 Skills | `validate_skills.py` 实测通过；8 个 `SKILL.md` 均存在 | 结构和本地引用有效；不等于已在真实 Codex/教师场景执行 |
| 总控工作流 | `project_state.py` 有 init/advance/block/resume/handoff，`stage-gates.md` 规定七阶段 | 有机器可执行状态、顺序和回退记录；总控仍依赖 Skill 指令触发专家工具 |
| quick/standard/strict | 在 `skills/` 和 `scripts/` 未发现实现 | 缺口；当前门禁固定且对竞赛时限偏重 |
| Manifest | `scripts/run_manifest.py` 实测验证三例生成 Manifest | 路径、哈希、seed、Git、依赖、失败与产物有基础；未记录 LLM/提示词/Skill 版本/工具调用/人工干预/solver 版本/数据泄漏检查 |
| JSON Schema | `schemas/run-manifest.schema.json` | 与 Python 校验器核心字段大致一致；Schema 本身未表达运行时安全路径规则和上述审计字段 |
| benchmark | 12 YAML 可校验；`statement_policy: external-reference-only` | 是评分元数据与量表，不是可端到端运行基准；没有题面、数据、解法、结果或人工干预度量 |

## 三个演示工程

所有示例均在隔离副本（HEAD archive + 复制未跟踪 `examples/`）运行成功；随后新 Manifest 使用 `--verify-files` 均通过。第一次尝试通过 PowerShell 二进制管道传递 tar 失败，原因是管道转码损坏 archive；未污染源仓库，改为文件式 `git archive --output` 后成功。

| 示例 | 实测结果 | 审计判断 |
|---|---|---|
| `demand_forecasting` | 24 训练 + 12 holdout；MAE 1.4167，对 seasonal-naive 的 MAE 24.0833，显示 94.12% | 合成的平滑趋势+月效应数据，模型正好匹配生成形态。额外实测线性趋势 MAE 8.2497、seasonal-drift MAE 2.25；94% 不能表述为真实预测提升或强基线胜利。源结果与本机复跑仅有浮点末位差异。 |
| `supplier_allocation` | HiGHS 线性规划目标 1060；西北角基线 1685；显示节省 37.09% | 可复现且可行性/目标重算已检查。西北角法是刻意弱的可行基线；没有 Vogel、最小元素法或独立 exact-solver 对照。数据合成、未建模固定费用、整数车辆和不确定需求。 |
| `queue_risk` | 8 次、每次 3000 顾客、固定 seed；选 3 服务器；均值等待 0.2034，拒绝率 0.008375，95% CI 已给出 | 三例中最能展示“失败候选被拒绝—选择最小可行方案”。运行前源目录没有结果/报告/Manifest；隔离复跑可生成。M/M/s/K 理论和同一模块的仿真相差 <0.05，但没有暖机、收敛诊断、跨实现理论对照或服务器成本。 |

三个案例可以作为“校园大型活动需求预测—物资调度—排队风险”的一个教学实验链，但当前只是三个独立 `python -m examples...` 脚本：没有共享数据契约、跨阶段 Manifest、UI、任务路由或教师审阅。不要把它们包装成已经集成的旗舰产品。

## 开源、隐私和匿名参评

- `LICENSE` 为 MIT（Copyright 2026 Blake）。README 与模块注释列出 `Algorithms_MathModels`、`ravenxrz/Mathematical-Modeling`、`MathModelAgent` 等来源，但未提供上游 URL、版本/commit、许可证文本、逐模块归属和改写说明。
- 未找到 `THIRD_PARTY_NOTICES.md`、`DATA_SOURCES.md`、`AI_USAGE_DISCLOSURE.md`、`ANONYMITY_CHECK.md`、`MODEL_CARD.md` 或 `LIMITATIONS.md`。这不是未授权复制的证据，但使许可证兼容性与材料来源**未验证**。
- 凭据模式扫描未命中可信 API key/token；但 `CHANGELOG.md:262` 和 `使用说明.md:1161` 含 `C:\Users\Blake\math-model` 绝对路径，Git 最近提交元数据含作者姓名/邮箱。匿名材料必须另行扫描并剔除。

## 问题分级

| 优先级 | 问题 | 可核验依据 | 建议 |
|---|---|---|---|
| P0 | 交付物不完整：`examples/` 未跟踪，`queue_risk` 源产物缺失；wheel 只含 `algorithms`，不含 Skills/scripts/examples | 初始 `git status`；wheel 内容；`MANIFEST.in` | 固化示例、加入一键入口与角色界面，或明确发布物仅是算法库 |
| P0 | 不可将合成、弱基线结果当作真实效果 | 三个 `examples/*/solve.py`、上述复跑指标 | 显著标合成；增加公平/独立基线、真实或可授权数据和失败场景 |
| P0 | 合规与匿名证据缺失 | LICENSE、README 来源表、缺失文件、绝对路径命中 | 建第三方清单、数据来源、AI披露、匿名检查、限制说明 |
| P1 | 不是完整教育产品，尚无学生/教师双角色与可视流程 | 未发现 UI/Web/CLI entry point；`pyproject.toml` 无 console script | 用最小双角色 Web/本地界面串联一个场景 |
| P1 | 随机性、目标方向、返回结构和 stdout 副作用不统一 | `metaheuristic.py`、`monte_carlo.py`、AST 指标 | 收敛核心 API，引入 `rng`/Result/异常协议 |
| P1 | Manifest/benchmark 证据范围不够 | `run_manifest.py`、Schema、`benchmarks/*.yaml` | 记录模型/提示/人工审批/solver/泄漏与可运行 benchmark 包 |
| P2 | legacy 与 129 API 会稀释参赛叙事 | `legacy/`、`algorithms/__init__.py` | 冻结 legacy；给参赛面向入口建立小型 curated API |

