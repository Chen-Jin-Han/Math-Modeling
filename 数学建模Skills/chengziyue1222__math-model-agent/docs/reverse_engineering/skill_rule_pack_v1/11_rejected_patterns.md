# 11 Rejected Patterns

以下内容不得从样稿迁移到通用 Skill。它们要么是样稿缺陷，要么会诱发伪精确、不可读排版或错误的 Agent 行为。

| rule_id | priority | rejected pattern | source_files | evidence_pages | validation_method |
|---|---|---|---|---|---|
| REJECT-001 | P0 | 拒绝同一 quantity 在流程图、正文和结果段出现不同值；B 的最小螺距在 pp.6、21 出现 0.4498、0.449766、0.4504 等冲突。 | 24Afable5直出(1).pdf | B pp.6,21 | quantity_id 聚合差异检查；任何超舍入差异 FAIL。 |
| REJECT-002 | P0 | 拒绝表格与紧邻文字描述的坐标/速度矛盾；B p.20 表格与下方文字给出不同龙头坐标和龙尾速度。 | 24Afable5直出(1).pdf | B p.20 | 从表源与正文 claim registry 交叉重算。 |
| REJECT-003 | P0 | 拒绝先声称事件函数单调、后又展示明显振荡；B pp.6,18 对最小间隙描述矛盾。 | 24Afable5直出(1).pdf | B pp.6,18 | 语义规则检测“单调”并与采样导数/翻转数核对。 |
| REJECT-004 | P1 | 拒绝把参考文献和附录接在前一部分的半页之后；两份样稿均未真正单独起页。 | 国赛24年Aclaudeopus5直出(1).pdf, 24Afable5直出(1).pdf | A pp.48,50, B pp.36-37 | 新页标题前不得存在前一章节内容。 |
| REJECT-005 | P1 | 拒绝附录目录沿用错误章节编号；A 附录 B 使用“2.1…”，B 附录 A 使用“1.1…”，应采用 A.1/B.1 或明确文件级编号。 | 国赛24年Aclaudeopus5直出(1).pdf, 24Afable5直出(1).pdf | A pp.3-4, B pp.3-4 | 目录与附录标题编号模式一致且无主章节遗留。 |
| REJECT-006 | P1 | 拒绝用 5.5-6.5 pt 字号在 PDF 附录塞完整源码；代码应精简并把全量源码放提交包。 | 国赛24年Aclaudeopus5直出(1).pdf, 24Afable5直出(1).pdf | A pp.52-95, B pp.37-64 | 代码字号和附录页数门禁；低于 7.5 pt 或代码占总页数>45% 警告/FAIL。 |
| REJECT-007 | P1 | 拒绝流程图文字过密、字号小于最终可读阈值；样稿多个流程图缩放后难以阅读。 | 国赛24年Aclaudeopus5直出(1).pdf, 24Afable5直出(1).pdf | A pp.7,16,21,25, B pp.6,12,18,21,25 | 最终嵌入后最小字号<6.5 pt 或节点超两行则 FAIL。 |
| REJECT-008 | P0 | 拒绝把求解器残差、容差或两算法末位一致直接等同于模型真实误差和科学正确性。 | 国赛24年Aclaudeopus5直出(1).pdf, 24Afable5直出(1).pdf | A/B 摘要与验证章节 | 精度声明必须绑定 error_type 和 independent_evidence。 |
| REJECT-009 | P0 | 拒绝仅换求根器但共享同一错误判据后称为“完全独立验证”。 | 国赛24年Aclaudeopus5直出(1).pdf, 24Afable5直出(1).pdf | A pp.21-22, B pp.18-19 | 验证依赖图显示共享关键判据时，标签只能是 solver_crosscheck，不能是 independent_validation。 |
| REJECT-010 | P0 | 拒绝只检查终点构型来判断全过程可行；必须搜索全过程最坏状态。 | 国赛24年Aclaudeopus5直出(1).pdf, 24Afable5直出(1).pdf | A pp.24-27, B pp.20-22 | 可行性结果必须包含 argmin/first_failure_state。 |
| REJECT-011 | P1 | 拒绝当前样例式无目录、摘要跨两页、正文版心过窄的默认排版；除非赛事模板明确要求。 | 20260730_技能与论文资料包.zip/04_最近真实生成论文/main_v2.pdf | C pp.1-4 | 对当前样例做回归：新增目录，摘要一页，左右正文边距 24-26 mm。 |
| REJECT-012 | P0 | 拒绝把完整数学建模论文工作流直接塞进 academic-data-visualization 的单一 SKILL.md；其现有触发范围只覆盖科学图。 | 20260730_技能与论文资料包.zip/01_当前主Skill/SKILL.md | N/A - repository file | 新建论文编排/建模总控技能，图形技能保持独立触发和接口。 |
| REJECT-013 | P0 | 拒绝自动虚构文献、DOI、数据来源、求解结果或未运行的验证。 | 国赛24年Aclaudeopus5直出(1).pdf, 24Afable5直出(1).pdf, 审查报告 02_TECHNICAL_AUDIT.md | A/B references, N/A - audit | 故障注入时必须输出 unresolved/blocked，不生成替代假文献或假数值。 |

## 处理原则

- `P0`：命中即阻断最终论文或提交包。
- `P1`：命中即阻断正式排版交付，但可保留草稿供修复。
- 被拒规则只用于测试和反例库，不得作为默认模板。
