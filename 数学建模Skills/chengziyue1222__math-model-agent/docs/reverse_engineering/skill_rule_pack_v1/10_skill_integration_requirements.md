# 10 Skill Integration Requirements

## 执行结论

当前资料包中的主 Skill 是 `academic-data-visualization`，它明确面向 Nature/Cell/Science 科学图生成，并排除统计测试、数据清洗、文献综述和代码调试。它可以承担论文中的 `figure_generator`，但不能作为数学建模论文全流程的唯一宿主。将本规则包全部追加到该 `SKILL.md` 会造成触发范围冲突、文件过长、职责混杂和回归风险。

推荐结构是：**保留现有图形 Skill，新建数学建模论文总控 Skill，并通过文件接口调用图形 Skill。** 若真实 `math-model` 仓库已有 `run-modeling-project`、`write-paper` 等 Skill，应扩展这些 Skill，而不是重复建立同名能力。

## 集成规则

| rule_id | description | source_files | evidence_pages | confidence | mandatory | scope | implementation_target | validation_method | rule_origin | priority |
|---|---|---|---|---|---|---|---|---|---|---|
| INTEG-001 | 新建或扩展 `math-model-paper-production`/`run-modeling-project` 总控 Skill；现有图形 Skill 只通过接口被调用。 | 20260730_技能与论文资料包.zip/01_当前主Skill/SKILL.md | N/A - repository file | high | YES | skill architecture | SKILL.md, documentation, tests | 触发测试：论文任务命中总控，单图任务仍只命中 figure skill。 | recommended_synthesis | P0 |
| INTEG-002 | 不应只修改 SKILL.md；规则分别落入配置、模板、validator、rendering pipeline 和 tests。 | 规则包 | N/A | high | YES | repository | config, template, Python validator, rendering pipeline, tests | 变更清单中至少包含每类实现目标；仅提示词变更则 FAIL。 | recommended_synthesis | P0 |
| INTEG-003 | 建立单一事实源 `claim_registry.yaml/results/*.json`，摘要、正文、图、表和流程图仅引用 quantity_id。 | 24Afable5直出(1).pdf | pp.6,20-21 | high | YES | results | SKILL.md, config, Python validator, tests | 注入冲突值，consistency checker 必须阻断。 | reverse_constraint | P0 |
| INTEG-004 | 复用现有 `references/typography.md`、`color-palettes.md`、`export-specs.md`，新增论文嵌入尺寸层，不直接照搬 5-7 pt 到缩小后的正文图。 | 20260730_技能与论文资料包.zip/01_当前主Skill/SKILL.md | references files | high | YES | figures | config, rendering pipeline, tests | 验证最终嵌入后最小图中文字 >=6.5 pt。 | recommended_synthesis | P1 |
| INTEG-005 | 新增论文样式配置、结构配置、图形语法、数值显示和验证门配置，所有配置必须有 schema。 | 规则包 | N/A | high | YES | config | config, Python validator, tests | YAML schema/唯一 rule_id/必填字段检查通过。 | recommended_synthesis | P1 |
| INTEG-006 | 新增 PDF 预检器：字体、版心、目录、分页、孤标题、图表可读性和代码溢出。 | 国赛24年Aclaudeopus5直出(1).pdf, 24Afable5直出(1).pdf, 20260730_技能与论文资料包.zip/04_最近真实生成论文/main_v2.pdf | 全文 | high | YES | preflight | Python validator, rendering pipeline, tests | 对 A/B/C 运行，能识别已知缺陷；对新样例 0 blocking。 | recommended_synthesis | P0 |
| INTEG-007 | 新增数值一致性、引用核验、硬约束、交叉验证独立性和干净环境复跑测试。 | 规则包 | N/A | high | YES | validation | Python validator, tests | P0 故障注入全部被阻断。 | recommended_synthesis | P0 |
| INTEG-008 | 保留现有生产图脚本、调色板和 QA；不得大规模重写现有 `assets/figures`。 | 20260730_技能与论文资料包.zip/01_当前主Skill/SKILL.md | N/A - repository file | high | YES | compatibility | SKILL.md, documentation, tests | 现有 figure skill 回归测试继续通过。 | recommended_synthesis | P1 |
| INTEG-009 | 当前资料包没有真实数学建模仓库全量源码和 LaTeX 模板源，Codex 必须先审计真实目录后再确定精确落点。 | 资料包 | N/A | high | YES | unresolved | documentation | 生成 repository_map.md 和 change_plan.md，经确认后实施。 | direct_observation | P0 |
| INTEG-010 | 以当前 `main_v2.pdf` 作为格式回归夹具，但不得改变其已验证数值；先只重排，再跑真题验证新工作流。 | 20260730_技能与论文资料包.zip/04_最近真实生成论文/main_v2.pdf | 全文 | high | YES | regression | template, rendering pipeline, tests | 新旧 canonical result 哈希一致，PDF 格式门提升。 | recommended_synthesis | P1 |

## 推荐目录

```text
skills/
├── run-modeling-project/              # 总控状态机与阶段门
├── parse-modeling-problem/            # 题目、参数、单位、输出合同
├── design-modeling-solution/          # 依赖图、候选模型、算法模式卡
├── execute-modeling-experiments/      # 代码生成、真实运行、Manifest
├── validate-modeling-evidence/        # 约束、交叉验证、收敛、敏感性
├── write-modeling-paper/              # 结构、摘要、正文和 claim registry
├── render-modeling-paper/             # LaTeX/Word 模板与 PDF 编译
└── academic-data-visualization/       # 现有图形 Skill，保持独立
config/
├── paper_style.yaml
├── paper_structure.yaml
├── figure_grammar.yaml
├── numeric_display.yaml
├── validation_gates.yaml
└── schemas/
templates/
├── paper/main.tex
├── paper/sections/
├── tables/
└── appendix/
scripts/
├── validate_rule_pack.py
├── validate_claim_consistency.py
├── validate_constraints.py
├── validate_references.py
├── validate_figures.py
├── pdf_preflight.py
└── build_submission.py
tests/
├── fixtures/main_v2/
├── fixtures/known_bad_sample_A_B/
├── test_claim_consistency.py
├── test_pdf_layout.py
├── test_failure_blocking.py
└── test_clean_room_reproduction.py
```

## 实施阶段

1. **基线审计**：记录真实仓库分支、dirty 状态、测试、当前模板和现有 Skill 引用。
2. **P0 证据链**：claim registry、真实执行、硬约束、数字一致性、失败阻断。
3. **P1 结构与排版**：25 mm 版心、摘要一页、目录、图表、分页、代码附录。
4. **P2 自动化**：规则 schema、报告、增量缓存、干净环境复跑。
5. **P3 润色**：语言重复、视觉密度、图形主题微调。
6. **双回归**：现有 figure Skill 不退化；同一真题的新论文通过全部 P0/P1。

## Codex 不得自行猜测的未决事项

- 真实 `C:\Users\Blake\math-model` 仓库当前目录、未提交改动和模板源文件位置。
- 目标赛事是否强制封面、页数、字体、匿名格式或指定参考文献规范。
- `main_v2.pdf` 对应的源数据、源代码、LaTeX 源和 canonical result。
- 用户希望完整源码进入论文还是仅进入提交压缩包。
- 是否允许联网核验全部参考文献。
