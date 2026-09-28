# 2021 C 题官方展示稿：可迁移能力学习记录

## 目的与边界

学习样本为中国大学生在线、全国大学生数学建模竞赛组委会发布的 C066、C085、C169、C283 展示页。仅提取章节组织、建模闭环、验证与表达的抽象模式；不转录正文、公式、图表、供应商名单、参数或任何数值结果，也不把展示稿的解法或答案用于重新计算本题。

来源：

- [C066 官方展示页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2021qgdxssxjmjslwzs/241212/1734085.shtml)
- [C085 官方展示页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2021qgdxssxjmjslwzs/241212/1734093.shtml)
- [C169 官方展示页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2021qgdxssxjmjslwzs/241212/1734095.shtml)
- [C283 官方展示页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2021qgdxssxjmjslwzs/241212/1734097.shtml)

## 四篇展示稿的方法对照

| 展示稿 | 可学习的方法路线 | 可学习的论证与表达 | 不可迁移的内容 |
|---|---|---|---|
| C066 | 供应商评价作为规划输入；四问通过同一数据口径逐步衔接 | 先定义评价口径，再给每问决策表、结果表与解释，令读者能从结论回到模型 | 评价权重、名单、数值、原文表格和公式 |
| C085 | 不确定供货下的分层决策；订购与运输联动，而非彼此孤立 | 明确随机量、阶段顺序与方案比较，将不确定性写成模型的一部分 | 随机分布、样本处理、算法参数和结果 |
| C169 | 用优化算法组合完成四问，并把计划输出与灵敏度分析相连 | 模型选择、算法、可执行计划、敏感性/结果解释形成闭环 | 算法实现细节、调参路径、输出方案 |
| C283 | 简单贪心基线与复杂多目标方案公平比较 | 说明目标冲突、复杂度与相对于基线的增益，避免“模型复杂即更优” | 贪心规则、目标权重、比较数值 |

共同能力不是某个算法名称，而是：每问均有明确决策变量和可执行产物；复杂模型有公平基线；不确定性和多目标取舍有证据；图表和表格服务于验证而非装饰。

## 当前 2021 C 草稿与展示稿能力的差距

| 差距 | 当前状态 | 应达到的通用能力 | 责任 Skill |
|---|---|---|---|
| 问题—模型—输出闭环 | 已有四问文字与 CSV，但没有统一机器可审计的逐问决策契约 | 每问登记目标、决策、约束、结果文件、验证文件和耦合关系 | select-model, run-modeling-project, write-model-paper, review-model-paper |
| 多期计划可行性 | 24 周计划尚未以显式库存/状态方程逐周验收 | 声明需要状态时，必须登记状态变量和周期平衡约束 | select-model, solve-model, review-model-paper |
| 不确定性 | 使用独立历史抽样压力试验，且已披露局限 | 登记情景来源、相关性假设和留出/压力验证；不把抽样频率说成已校准概率 | analyze-model-data, solve-model, make-model-figures, review-model-paper |
| 多目标取舍 | 当前以加权排序/情景为主，缺少显式取舍前沿或权重敏感性登记 | 使用 Pareto、epsilon-constraint、lexicographic，或有证据的权重敏感性 | select-model, solve-model, make-model-figures, review-model-paper |
| 复杂模型的公平比较 | 有简单排序和情景对比，但未以统一输入/指标形成正式基线契约 | 基线与复杂法共享输入、约束和指标，并报告不可行性与代价 | select-model, solve-model, make-model-figures, review-model-paper |
| 论文中的验证表达 | 图表与表格已登记，但每问的“为何可信”没有统一质量证据源 | 每问至少给出平衡/可行性、基线/取舍或不确定性验证之一 | make-model-figures, write-model-paper, review-model-paper |

这张表是能力差距，不是向任何展示稿对齐结果。当前草稿在新标准下应回到建模/验证阶段补齐证据，不能仅润色正文后声称通过。

## 已修改的通用 Skill 与运行时文件

| 文件 | 修改内容 | 预期行为变化 |
|---|---|---|
| `scripts/skill_contracts.py` | 新增 `decision_contract` 与 `quality_validation` 角色并串接选择、求解、制图、写作、审查 | 缺少逐问决策或质量验证证据的正式运行不能通过契约校验 |
| `skills/run-modeling-project/SKILL.md`、`references/stage-gates.md`、`references/handoff-schema.md` | 把两项证据加入阶段门和交接 | 项目不能把叙述当作跨阶段信息，必须携带可审计文件 |
| `skills/analyze-model-data/SKILL.md` | 增加时间依赖、相关性、零值/支持集与未来留出检查 | 独立抽样不再是默认前提 |
| `skills/research-model-literature/SKILL.md` | 明确只学习展示稿的方法结构，不继承其答案 | 文献/范例检索不再成为答案泄漏通道 |
| `skills/select-model/SKILL.md` | 要求逐问决策契约、动态状态/不确定性/多目标路线 | 选模型阶段必须提前声明可验证的模型语义 |
| `skills/solve-model/SKILL.md` | 强制周期平衡、同输入基线、情景来源、样本外压力和取舍证据 | 求解成功不再足以宣布方案可信 |
| `skills/make-model-figures/SKILL.md` | 每问要求决策级验证图或表 | 不能只生成漂亮的结果图 |
| `skills/write-model-paper/SKILL.md` | 正文从决策/质量契约写作，每问展示可执行输出与验证 | 论文不能只罗列结果表 |
| `skills/review-model-paper/SKILL.md` | 对契约中的动态、不确定性、取舍和基线要求设置硬门 | 审查能将缺失返回到建模/验证，而非仅标注措辞问题 |
| `code/algorithms/adversarial_review.py` | 增加契约驱动的 fail-closed 语义审查 | 已声明而未实现的高阶能力会被明确拦截 |

## 新增对抗测试

| 测试 | 注入缺陷 | 修改前 | 修改后 |
|---|---|---|---|
| `test_declared_decision_quality_requirements_fail_closed` | 多期、随机、多目标、基线均被声明，但没有状态方程、情景证据、取舍证据或公平基线 | 审查可能只检查登记表是否齐全 | 返回四个独立 blocking codes：状态、不确定性、取舍、基线 |
| `test_declared_decision_quality_requirements_accept_complete_evidence` | 同样声明要求，但提供状态平衡、情景来源/压力验证、epsilon 取舍证据和同输入基线指标 | 无法区分真实闭环与空泛声明 | 不触发以上四类 blocker |
| `test_quality_evidence_roles_are_required_across_the_competition_pipeline` | 删除选择、求解、制图、写作、审查间的决策/质量证据交接 | 单个 Skill 可各自通过而证据在交接处丢失 | 契约测试验证两类证据贯穿整条正式流水线 |

## 可迁移规则与本题专用内容的分界

可迁移规则：逐问决策契约、状态平衡、情景/鲁棒语义、基线公平性、多目标取舍证据、图表服务验证、结论可追溯、展示稿学习的非复制边界。

本题专用内容：原材料类别、供应商与转运商编码、周数、需求/产能/损耗数值、评价权重、选中名单、公式参数、具体订单与运输方案。它们不写入通用 Skill，也不写入上述新增测试的断言。

## 兼容性结论

Skill 合同版本已从 `1.0` 升至 `1.1`。此前生成的项目运行记录仍可作为历史证据，但不满足新增的 `decision_contract` 和 `quality_validation` 角色，不能在新规则下被重标为正式通过；必须由新版选择与求解链重新产生证据。此处不改写既有 2021 C 题计算结果。
