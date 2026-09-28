# 01 Evidence Matrix

## 1. 分析对象

- `国赛24年Aclaudeopus5直出(1).pdf`：95 页，A4；题目+摘要第 1 页，目录第 2-4 页，正文第 5-47 页，参考文献自第 48 页，附录自第 50 页。PDF 内嵌正文主字体为 SimSun/Times New Roman，正文主字号约 12.005 pt；正文长行版心约 x=70.87-524.41 pt。
- `24Afable5直出(1).pdf`：64 页，A4；题目+摘要第 1 页，目录第 2-4 页，正文第 5-35 页，参考文献自第 36 页，附录自第 37 页。正文排版与文件 A 高度同源。
- `20260730_技能与论文资料包.zip/04_最近真实生成论文/main_v2.pdf`：32 页，A4；独立封面第 1 页，摘要跨第 2-3 页，正文约第 4-21 页，参考文献第 22-23 页，附录第 24-32 页；正文版心左右边距约 89.86 pt（31.7 mm），显著窄于目标样稿。
- `20260730_技能与论文资料包.zip/01_当前主Skill/SKILL.md`：当前主 Skill 是“Academic Data Visualization”，职责为期刊科学图生成，不是完整数学建模求解、论文编排与 PDF 交付总控。

## 2. 量化对照

| 指标 | 文件 A | 文件 B | 当前样例 C | 工程结论 |
|---|---:|---:|---:|---|
| 总页数 | 95 | 64 | 32 | 附录长度差异巨大，不能用总页数衡量质量 |
| 正文页数（不含摘要/目录/参考/附录） | 43 | 31 | 18 | C 技术证据和结果分析明显更短 |
| 参考文献条目 | 20 | 12 | 13 | 数量不是质量门，必须核验语义与真实性 |
| 图题数量（文本检测） | 35 | 34 | 13 | A/B 的证据图更密集，但存在小字和冗余风险 |
| 表题数量（文本检测） | 16 | 9 | 10 | 表应由结构化结果生成 |
| 正文主字号 | 12.005 pt | 12.005 pt | 11.955 pt | 三者接近，主要差异在版心和行距 |
| 正文基线间距 | 19.87 pt | 19.87 pt | 21.67 pt | C 行距偏松，版面密度低 |
| 正文左右边距 | 约 25 mm | 约 25 mm | 约 31.7 mm | 新模板采用 A/B 的约 25 mm |
| 正文平均非空字符/页 | 817 | 764 | 639 | C 不能以大留白替代论证 |
| 代码附录主字号 | 5.5 pt | 6.5 pt | 10.46 pt | A/B 太小；建议 7.5-9 pt + 精简代码 |

## 3. 直接观察、综合推荐与反向约束

- `direct_observation`：从 PDF 元数据、字体对象、页面 bbox、目录和可视页面直接取得，例如 A4、12 pt 正文、15 pt 一级标题、三线表、统一模型与图文结构。
- `recommended_synthesis`：融合两份样稿和当前 Skill 后形成的通用规则，例如“统一模型章节条件触发”“摘要一页”“quantity_id 单一事实源”。
- `reverse_constraint`：专门阻断样稿中的缺陷，例如文件 B 的数值矛盾、两份样稿参考文献/附录未单独起页、代码字体过小、流程图文字不可读。

## 4. 规则总索引

| rule_id | priority | origin | mandatory | implementation_target | description |
|---|---|---|---|---|---|
| LAYOUT-PAGE-001 | P1 | direct_observation | YES | config, template, Python validator, tests | 默认采用 A4 纵向单栏；赛事模板另有强制要求时以赛事模板覆盖。 |
| LAYOUT-MARGIN-001 | P1 | recommended_synthesis | YES | config, template, Python validator, tests | 目标版心左右边距采用约 25 mm；不得直接沿用当前样例约 31.7 mm 的窄版心。 |
| LAYOUT-MARGIN-002 | P2 | recommended_synthesis | NO | config, template, Python validator | 正文顶部有效起始位置约 25 mm；底部正文须为页码和脚注保留稳定空间。 |
| LAYOUT-FONT-001 | P1 | direct_observation | YES | config, template, Python validator, rendering pipeline, tests | 中文正文使用宋体，西文和数字使用 Times New Roman 或数学字体；全文不得无理由混用多套正文家族。 |
| LAYOUT-FONT-002 | P1 | direct_observation | YES | config, template, Python validator, tests | 正文基准字号为 12 pt；允许 11.5-12.1 pt 的编译误差，不得通过缩小正文解决超页。 |
| LAYOUT-LINE-001 | P1 | recommended_synthesis | YES | config, template, Python validator | 正文基线间距约 19.9 pt，相当于 12 pt 字号下约 1.65 倍；段落之间不额外堆积大空白。 |
| LAYOUT-PARA-001 | P1 | direct_observation | YES | template, Python validator, tests | 正文两端对齐，首行缩进 2 个汉字；公式后续行、表后说明和列表可例外。 |
| LAYOUT-TITLE-001 | P1 | recommended_synthesis | NO | SKILL.md, config, template, Python validator | 无强制封面时，第一页直接放置论文题目、摘要和关键词；不得自动生成装饰性封面。 |
| LAYOUT-TITLE-002 | P1 | direct_observation | YES | config, template, Python validator | 论文题目采用黑体约 16 pt、居中；摘要标题黑体约 14 pt、居中。 |
| LAYOUT-HEAD-001 | P1 | direct_observation | YES | config, template, Python validator, tests | 一级标题采用黑体约 15 pt、居中，中文序号“X、标题”；不强制每个一级标题另起一页。 |
| LAYOUT-HEAD-002 | P1 | recommended_synthesis | YES | config, template, Python validator | 二级、三级标题采用左对齐黑体约 12 pt；层级深度原则上不超过三级。 |
| LAYOUT-HEAD-003 | P1 | reverse_constraint | YES | template, Python validator, tests | 任何标题后必须至少容纳两行正文或一个不可拆分图表块；不得把孤立标题留在页底。 |
| LAYOUT-TOC-001 | P1 | recommended_synthesis | YES | SKILL.md, template, Python validator, tests | 目录在摘要之后单独起页，列至二级标题；仅当三级标题承担独立推导或算法模块时才列三级。 |
| LAYOUT-REF-001 | P1 | reverse_constraint | YES | template, Python validator, tests | 参考文献必须单独起页，不得像两份样稿一样在正文或上一节后半页直接开始。 |
| LAYOUT-APP-001 | P1 | reverse_constraint | YES | template, Python validator, tests | 附录必须单独起页；每个一级附录均使用独立编号并进入目录。 |
| LAYOUT-CODE-001 | P1 | reverse_constraint | YES | config, template, rendering pipeline, Python validator | 论文附录中的代码字号不得低于 7.5 pt；样稿中 5.5/6.5 pt 的完整源码排法只作为反例。 |
| LAYOUT-CODE-002 | P1 | recommended_synthesis | YES | config, template, rendering pipeline, Python validator | 代码块使用等宽字体、浅灰背景、行号可选；禁止横向溢出和函数被无意义截断。 |
| LAYOUT-PAGENO-001 | P2 | direct_observation | YES | template, Python validator | 页码置于底部居中，摘要页可计页码；封面是否计页依赛事模板。 |
| LAYOUT-DENSITY-001 | P2 | recommended_synthesis | NO | config, Python validator, documentation | 正文版面密度以每页约 700-900 个非空字符或等效图表信息为目标，不得通过大留白制造“完成感”。 |
| STRUCT-ABSTRACT-001 | P1 | recommended_synthesis | YES | SKILL.md, template, Python validator, tests | 摘要应在一页内完成，采用“问题本质与统一框架—各子问题方法/结果/验证—总体检验与关键词”的顺序。 |
| STRUCT-ABSTRACT-002 | P1 | recommended_synthesis | YES | SKILL.md, template, Python validator | 每个子问题在摘要中最多占一个紧凑段落，数字只保留能区分方案和支撑结论的关键值。 |
| STRUCT-KEYWORD-001 | P2 | recommended_synthesis | YES | template, Python validator | 关键词建议 4-7 个，按“对象/方法/关键算法/验证特征”排序，不写题目专属最终数值。 |
| STRUCT-RESTATEMENT-001 | P1 | recommended_synthesis | YES | SKILL.md, template, Python validator | 问题重述只保留背景、对象、给定条件和交付要求，不提前写模型优越性或求解结果。 |
| STRUCT-ANALYSIS-001 | P1 | direct_observation | YES | SKILL.md, template, tests | 问题分析必须先识别子问题依赖和共用状态，再说明每问的难点、判据与求解入口。 |
| STRUCT-UNIFIED-001 | P0 | recommended_synthesis | YES | SKILL.md, template, tests | 当至少两个子问题复用相同状态变量、约束判据或求解内核时，建立“统一模型/基础模型”章节；否则不得为形式而单列。 |
| STRUCT-SUBPROBLEM-001 | P1 | recommended_synthesis | YES | SKILL.md, template, Python validator | 每个核心子问题按“模型建立—求解流程—结果与分析”三段组织；纯解析证明题可将流程并入推导。 |
| STRUCT-FLOW-001 | P2 | recommended_synthesis | NO | SKILL.md, template, documentation | 总体技术路线图只画一次；子问题流程图仅在存在多阶段、分支、嵌套或回退时使用。 |
| STRUCT-ASSUMPTION-001 | P0 | recommended_synthesis | YES | SKILL.md, template, Python validator | 模型假设分为题面转写、必要理想化和可检验假设；每条写明依据、影响方向和验证方式。 |
| STRUCT-SYMBOL-001 | P1 | recommended_synthesis | YES | template, Python validator | 符号表只列跨章节复用符号，单位独立成列；临时符号在首次出现处解释。 |
| STRUCT-VALIDATION-001 | P0 | recommended_synthesis | YES | SKILL.md, template, Python validator, tests | 正文必须有独立的“模型检验与灵敏度分析”章节，至少包含硬约束、交叉验证和参数/步长敏感性。 |
| STRUCT-EVALUATION-001 | P1 | recommended_synthesis | YES | SKILL.md, template, Python validator | 模型优点、缺点和推广必须具体对应本文模型、数据与适用域，不写通用套话。 |
| STRUCT-REF-001 | P0 | direct_observation | YES | template, Python validator, tests | 参考文献置于正文后、附录前，并与正文编号一一对应。 |
| STRUCT-APPENDIX-001 | P1 | recommended_synthesis | YES | SKILL.md, template, documentation | 正文仅呈现代表结果与关键伪代码；全量结果、完整审计表和可复现代码进入附录或提交包。 |
| STRUCT-LENGTH-001 | P2 | recommended_synthesis | NO | SKILL.md, config, documentation | 在无赛事页数上限时，正文建议 28-42 页；若赛事有限制，先满足限制，再按证据价值删减而非缩字。 |
| FIG-GRAMMAR-001 | P0 | recommended_synthesis | YES | SKILL.md, config, template, Python validator, tests | 每张图必须绑定唯一核心结论和证据角色；不能只因“好看”而生成。 |
| FIG-ROUTE-001 | P1 | reverse_constraint | NO | config, template, rendering pipeline | 存在多层模块、分支或门禁时使用总体技术路线图；只画模块与数据契约，不把全部公式和数值塞入图中。 |
| FIG-GEOM-001 | P1 | direct_observation | NO | config, template, rendering pipeline | 涉及几何约束时，先画变量、方向、尺寸和边界的几何示意图，再展示数值构型。 |
| FIG-SNAPSHOT-001 | P1 | direct_observation | NO | config, rendering pipeline, Python validator | 动态过程用 3-4 个等间隔或事件驱动时刻的共享坐标多面板快照；各面板保持同尺度。 |
| FIG-GLOBALLOCAL-001 | P0 | direct_observation | NO | config, rendering pipeline, tests | 首次碰撞、极值或异常事件同时给出全局构型和局部放大，局部图标明对应对象与间隙/残差。 |
| FIG-TIMESERIES-001 | P1 | direct_observation | NO | config, rendering pipeline | 展示演化趋势时使用时间曲线，需标出阈值、临界时刻和关键区间；避免只报最终点。 |
| FIG-HEATMAP-001 | P1 | recommended_synthesis | NO | config, rendering pipeline, Python validator | 时间×对象或参数×响应的二维结构使用热力图，必须提供感知均匀色标、单位和极值注释。 |
| FIG-PARAM-001 | P1 | direct_observation | NO | config, rendering pipeline | 可行域、敏感性和响应面应画出临界边界、基准点和可行/不可行区域，而非只给散点。 |
| FIG-CONVERGENCE-001 | P0 | recommended_synthesis | NO | config, rendering pipeline, Python validator | 数值求根、优化或迭代算法声称高精度时，至少给出残差/区间宽度随迭代变化或步长减半表。 |
| FIG-COMPARE-001 | P0 | reverse_constraint | YES | SKILL.md, config, Python validator, tests | 算法比较图必须使用公平数据切分、相同指标和明确基线；弱基线不得作为唯一对照。 |
| FIG-SIZE-001 | P2 | recommended_synthesis | NO | config, rendering pipeline, Python validator | 正文单图宽度建议为版心的 0.78-1.0；双图每幅约 0.45-0.49；四宫格仅用于共享坐标的快照。 |
| FIG-TYPE-001 | P1 | reverse_constraint | YES | config, rendering pipeline, Python validator, tests | 图内字体统一为无衬线；最终嵌入论文后刻度和图例不得低于 6.5 pt，轴标题和注释建议 7-8 pt。 |
| FIG-COLOR-001 | P1 | recommended_synthesis | YES | config, rendering pipeline, Python validator | 使用 2-4 个语义主色和 1 个强调色；连续变量使用感知均匀色图，关键比较不得只靠红绿。 |
| FIG-VECTOR-001 | P1 | recommended_synthesis | YES | SKILL.md, config, rendering pipeline, tests | 线图、流程图、示意图和文字优先导出 PDF/SVG 矢量主文件，同时保留 >=450 dpi RGB 预览图。 |
| FIG-CAPTION-001 | P1 | direct_observation | YES | template, Python validator | 图题位于图下方；正文在图前说明用途，在图后解释新增证据和机制，禁止“如图所示”后无分析。 |
| FIG-NODUP-001 | P1 | recommended_synthesis | YES | SKILL.md, Python validator, tests | 同一数据不得用多张仅样式不同的图重复呈现；若局部放大或不同视角有独立证据需在图注册表中说明。 |
| TABLE-STYLE-001 | P1 | direct_observation | YES | config, template, rendering pipeline, Python validator | 正文表格默认三线表、无竖线；表题位于表上方并居中。 |
| TABLE-UNIT-001 | P1 | recommended_synthesis | YES | config, template, Python validator | 单位优先写在列名或表下注释，不在每个单元格重复。 |
| TABLE-NUM-001 | P1 | recommended_synthesis | YES | config, rendering pipeline, Python validator, tests | 同一列数字小数位统一，按小数点对齐；科学计数法指数格式一致。 |
| TABLE-WIDTH-001 | P1 | reverse_constraint | YES | template, rendering pipeline, Python validator | 表格宽度不得超过版心；超过时优先拆表、转置、缩短表头或移入附录，不得缩小至不可读。 |
| TABLE-SPLIT-001 | P2 | direct_observation | NO | SKILL.md, template | 坐标与速度、模型参数与验证指标等不同量纲的信息应拆表，避免多层表头过密。 |
| TABLE-LONG-001 | P1 | direct_observation | YES | SKILL.md, template, Python validator | 全量逐时刻/逐对象结果不进正文；正文保留代表样本，完整结果输出到附件表格并在正文引用。 |
| TABLE-CROSSPAGE-001 | P1 | recommended_synthesis | YES | template, Python validator | 跨页长表必须重复表头、标注“续表”，且一行不得跨页拆分。 |
| TABLE-SOURCE-001 | P0 | recommended_synthesis | YES | SKILL.md, rendering pipeline, Python validator, tests | 表格必须由结构化结果文件生成，禁止手工复制数字到论文。 |
| NUM-PRECISION-001 | P0 | reverse_constraint | YES | SKILL.md, config, Python validator, tests | 报告精度由输入精度、模型误差、敏感性和用途共同决定；求解器容差不等于可报告有效数字。 |
| NUM-GUARD-001 | P1 | recommended_synthesis | NO | config, template, Python validator | 内部计算保留守护位，正文通常显示 4-6 个有效数字；临界值可附高精度值但必须同时给容差或区间。 |
| NUM-RESIDUAL-001 | P0 | reverse_constraint | YES | SKILL.md, Python validator, tests | 残差小只能证明数值方程被满足，不能单独证明模型、数据口径或全局最优正确。 |
| NUM-CONSISTENCY-001 | P0 | reverse_constraint | YES | SKILL.md, config, Python validator, tests | 摘要、正文、图、表、流程图和附件中的同名量必须由同一 canonical result 生成。 |
| NUM-SIGN-001 | P0 | recommended_synthesis | YES | SKILL.md, config, Python validator, tests | 坐标系、旋向和正负号必须在模型开始处声明，并在代码、图和表中保持同一约定。 |
| NUM-THRESHOLD-001 | P0 | recommended_synthesis | YES | config, Python validator, tests | 阈值、容差和步长必须区分：物理阈值、算法停止容差、显示舍入和扫描分辨率分别记录。 |
| NUM-INTERVAL-001 | P0 | recommended_synthesis | YES | SKILL.md, template, Python validator | 事件时刻、最小可行参数和全局峰值必须报告括号/置信区间或邻域复核，而非单点数字。 |
| WRITE-CLAIM-001 | P1 | recommended_synthesis | YES | SKILL.md, template, Python validator | 每个结论按“发现—证据—机制/原因—限制”展开，不写只有形容词的结论。 |
| WRITE-FIG-001 | P1 | direct_observation | YES | SKILL.md, template, Python validator | 图前说明为什么画，图后说明读出了什么；禁止仅写“结果如图所示”。 |
| WRITE-TABLE-001 | P2 | recommended_synthesis | YES | SKILL.md, template, Python validator | 表后只解释最重要的 1-3 个比较，不逐格复述所有数字。 |
| WRITE-FORMULA-001 | P1 | direct_observation | YES | SKILL.md, template, Python validator | 公式出现前说明目的，出现后定义变量、解释物理/统计意义并说明如何计算。 |
| WRITE-ASSUME-001 | P0 | reverse_constraint | YES | SKILL.md, Python validator | 假设不得使用“为简化问题，假设……”作为唯一理由；必须写题面依据、尺度依据或后续敏感性验证。 |
| WRITE-SIGNIFICANT-001 | P0 | reverse_constraint | YES | SKILL.md, Python validator, tests | “显著”“大幅”“明显优于”等词只有在统计检验、预先定义阈值或业务量级支持时使用。 |
| WRITE-PROOF-001 | P0 | reverse_constraint | YES | SKILL.md, Python validator | 数值扫描只能支持“在所检区间和分辨率下未发现反例”，不得直接写“证明全局单调/全局最优”。 |
| WRITE-PRECISION-001 | P0 | reverse_constraint | YES | SKILL.md, Python validator | “达到机器精度”“逐位可复现”必须限定为数值实现层面，并与模型误差、输入误差分开。 |
| WRITE-AI-001 | P3 | recommended_synthesis | NO | config, Python validator, documentation | 限制高频套话：“值得注意的是”“进一步”“这说明”“从图中可以看出”不得机械重复。 |
| WRITE-SENTENCE-001 | P3 | recommended_synthesis | NO | config, Python validator | 中文技术句优先 25-55 字，单句超过 90 字时拆分；定义和条件可例外。 |
| WRITE-REPEAT-001 | P2 | recommended_synthesis | YES | Python validator, tests | 摘要、章节结尾和总评不得重复同一段结论；同一数字可因不同目的引用，但须缩写并链接 quantity_id。 |
| WRITE-LIMIT-001 | P1 | recommended_synthesis | YES | SKILL.md, template, Python validator | 模型不足必须写明受影响的结论、可能偏差方向和补救实验，不写“模型仍有提升空间”。 |
| WRITE-REF-001 | P0 | recommended_synthesis | YES | SKILL.md, Python validator, tests | 方法来源、背景事实和非原创定理必须引用；纯题面信息、本文数值结果和常识性代数不强行引用。 |
| MODEL-PATTERN-001 | P0 | direct_observation | NO | SKILL.md, config, documentation, tests | 算法模式卡：共用内核与依赖图 |
| MODEL-PATTERN-002 | P1 | direct_observation | NO | SKILL.md, config, documentation, tests | 算法模式卡：一维主参数化 |
| MODEL-PATTERN-003 | P1 | direct_observation | NO | SKILL.md, config, documentation, tests | 算法模式卡：闭式表达+数值反解 |
| MODEL-PATTERN-004 | P0 | direct_observation | NO | SKILL.md, config, documentation, tests | 算法模式卡：链式约束递推 |
| MODEL-PATTERN-005 | P0 | direct_observation | NO | SKILL.md, config, documentation, tests | 算法模式卡：解析约束速度/导数传播 |
| MODEL-PATTERN-006 | P0 | direct_observation | NO | SKILL.md, config, documentation, tests | 算法模式卡：实体几何+粗筛精判 |
| MODEL-PATTERN-007 | P0 | direct_observation | NO | SKILL.md, config, documentation, tests | 算法模式卡：带符号事件函数 |
| MODEL-PATTERN-008 | P0 | direct_observation | NO | SKILL.md, config, documentation, tests | 算法模式卡：嵌套极小-外层求根 |
| MODEL-PATTERN-009 | P0 | recommended_synthesis | NO | SKILL.md, config, documentation, tests | 算法模式卡：单调性验证后搜索 |
| MODEL-PATTERN-010 | P1 | direct_observation | NO | SKILL.md, config, documentation, tests | 算法模式卡：对称性与不变量降维 |
| MODEL-PATTERN-011 | P1 | direct_observation | NO | SKILL.md, config, documentation, tests | 算法模式卡：线性齐次缩放 |
| MODEL-PATTERN-012 | P0 | recommended_synthesis | NO | SKILL.md, config, documentation, tests | 算法模式卡：多分支上包络峰值 |
| MODEL-PATTERN-013 | P0 | direct_observation | NO | SKILL.md, config, documentation, tests | 算法模式卡：硬约束审计 |
| MODEL-PATTERN-014 | P0 | recommended_synthesis | NO | SKILL.md, config, documentation, tests | 算法模式卡：独立算法交叉验证 |
| MODEL-PATTERN-015 | P0 | recommended_synthesis | NO | SKILL.md, config, documentation, tests | 算法模式卡：敏感性与收敛性分离 |
| VAL-GATE-001 | P0 | recommended_synthesis | YES | SKILL.md, config, Python validator, tests | 题目参数、单位、对象编号和输出格式必须结构化并通过自洽检查后才能建模。 |
| VAL-GATE-002 | P0 | recommended_synthesis | YES | SKILL.md, Python validator, tests | 代码必须真实执行成功并生成机器可读结果、日志和环境记录；语言模型文本不得充当计算结果。 |
| VAL-GATE-003 | P0 | direct_observation | YES | SKILL.md, config, Python validator, tests | 所有题面硬约束、模型不变量和边界条件必须逐项审计；任一 P0 约束失败禁止写论文最终结论。 |
| VAL-GATE-004 | P0 | recommended_synthesis | YES | SKILL.md, Python validator, tests | 分支选择、首次事件和全局峰值必须有局部邻域与步长减半验证。 |
| VAL-GATE-005 | P0 | reverse_constraint | YES | SKILL.md, Python validator, tests | 至少一个关键结论使用真正独立的算法、库或解析关系交叉验证；共享关键函数须显式披露。 |
| VAL-GATE-006 | P0 | recommended_synthesis | YES | SKILL.md, Python validator, tests | 数值收敛性和模型参数敏感性分别检查；结论是否跨越决策阈值必须单独报告。 |
| VAL-GATE-007 | P0 | reverse_constraint | YES | Python validator, tests | 摘要、正文、图、表、流程图、附件中的数字执行 quantity_id 一致性校验。 |
| VAL-GATE-008 | P0 | recommended_synthesis | YES | SKILL.md, Python validator, tests | 参考文献必须存在、可核验且支撑对应论述；无法联网核验的文献标记 unresolved，不得伪造。 |
| VAL-GATE-009 | P1 | recommended_synthesis | YES | Python validator, rendering pipeline, tests | 图表必须绑定源数据哈希，文字可读、单位完整、黑白或色盲条件下仍可解释。 |
| VAL-GATE-010 | P0 | recommended_synthesis | YES | Python validator, rendering pipeline, tests | PDF 预检必须检查页面尺寸、字体嵌入、裁切、乱码、孤标题、图题分离、参考文献/附录分页和目录页码。 |
| VAL-GATE-011 | P0 | recommended_synthesis | YES | SKILL.md, Python validator, tests, documentation | 提交包必须在干净环境一键复现关键结果，并包含代码、数据/数据合同、依赖锁、运行说明和 Manifest。 |
| VAL-GATE-012 | P0 | recommended_synthesis | YES | SKILL.md, config, Python validator, tests | 失败证据必须保留：不收敛、约束违反、弱基线、缺失数据或引用未核验时输出 blocked，而非自动润色成成功。 |
| WF-STATE-001 | P0 | recommended_synthesis | YES | SKILL.md, config, Python validator, tests | 采用显式状态机：intake→parse→dependency_plan→model_design→solver_plan→execute→validate→visualize→write→reference_check→layout→consistency→pdf_preflight→package。 |
| WF-CONTRACT-001 | P0 | recommended_synthesis | YES | SKILL.md, config, documentation, tests | 每个阶段必须声明输入、输出、责任工具、阻塞条件和恢复入口；自然语言“已完成”不算产物。 |
| WF-TOOL-001 | P0 | recommended_synthesis | YES | SKILL.md, config, tests | 题目解析和写作可由模型起草；数值、文献真实性、文件哈希和 PDF 视觉检查必须调用真实工具。 |
| WF-PLAN-001 | P0 | direct_observation | YES | SKILL.md, template, tests | 建模前先生成子问题依赖图和候选模型比较表，经规则门选择后再编码。 |
| WF-CODEFIRST-001 | P0 | recommended_synthesis | YES | SKILL.md, config, tests | 所有结果性文字必须在代码执行和验证之后生成；不得先写结果再补代码。 |
| WF-FALLBACK-001 | P0 | recommended_synthesis | YES | SKILL.md, config, tests | 求解失败时按“检查合同→扩大/修正括号→替代算法→降级结论→人工复核”回退，禁止静默改参数。 |
| WF-WRITE-001 | P0 | recommended_synthesis | YES | SKILL.md, template, Python validator | 写作从验证后的 evidence registry 拉取数字、图、表和限制，摘要最后生成。 |
| WF-VISUAL-001 | P1 | recommended_synthesis | YES | SKILL.md, config, documentation, tests | 图形生成调用现有 academic-data-visualization skill，但论文编排、图题、跨图一致性由论文技能负责。 |
| WF-HUMAN-001 | P0 | recommended_synthesis | YES | SKILL.md, config, tests | 遇到题意歧义、数据口径冲突、无法核验文献或高风险假设时暂停并请求人工确认。 |
| WF-PACK-001 | P0 | recommended_synthesis | YES | SKILL.md, Python validator, tests, documentation | 最终交付前在干净目录复跑并生成提交包清单、版本和匿名扫描报告。 |
| REJECT-001 | P0 | reverse_constraint | YES | SKILL.md, Python validator, tests, documentation | 拒绝同一 quantity 在流程图、正文和结果段出现不同值；B 的最小螺距在 pp.6、21 出现 0.4498、0.449766、0.4504 等冲突。 |
| REJECT-002 | P0 | reverse_constraint | YES | Python validator, tests, documentation | 拒绝表格与紧邻文字描述的坐标/速度矛盾；B p.20 表格与下方文字给出不同龙头坐标和龙尾速度。 |
| REJECT-003 | P0 | reverse_constraint | YES | SKILL.md, Python validator, documentation | 拒绝先声称事件函数单调、后又展示明显振荡；B pp.6,18 对最小间隙描述矛盾。 |
| REJECT-004 | P1 | reverse_constraint | YES | template, Python validator, tests | 拒绝把参考文献和附录接在前一部分的半页之后；两份样稿均未真正单独起页。 |
| REJECT-005 | P1 | reverse_constraint | YES | template, Python validator, tests | 拒绝附录目录沿用错误章节编号；A 附录 B 使用“2.1…”，B 附录 A 使用“1.1…”，应采用 A.1/B.1 或明确文件级编号。 |
| REJECT-006 | P1 | reverse_constraint | YES | config, template, Python validator, documentation | 拒绝用 5.5-6.5 pt 字号在 PDF 附录塞完整源码；代码应精简并把全量源码放提交包。 |
| REJECT-007 | P1 | reverse_constraint | YES | config, rendering pipeline, Python validator | 拒绝流程图文字过密、字号小于最终可读阈值；样稿多个流程图缩放后难以阅读。 |
| REJECT-008 | P0 | reverse_constraint | YES | SKILL.md, Python validator, documentation | 拒绝把求解器残差、容差或两算法末位一致直接等同于模型真实误差和科学正确性。 |
| REJECT-009 | P0 | reverse_constraint | YES | SKILL.md, Python validator, tests | 拒绝仅换求根器但共享同一错误判据后称为“完全独立验证”。 |
| REJECT-010 | P0 | reverse_constraint | YES | SKILL.md, Python validator, tests | 拒绝只检查终点构型来判断全过程可行；必须搜索全过程最坏状态。 |
| REJECT-011 | P1 | reverse_constraint | YES | config, template, Python validator, documentation | 拒绝当前样例式无目录、摘要跨两页、正文版心过窄的默认排版；除非赛事模板明确要求。 |
| REJECT-012 | P0 | reverse_constraint | YES | SKILL.md, documentation, tests | 拒绝把完整数学建模论文工作流直接塞进 academic-data-visualization 的单一 SKILL.md；其现有触发范围只覆盖科学图。 |
| REJECT-013 | P0 | reverse_constraint | YES | SKILL.md, Python validator, tests, documentation | 拒绝自动虚构文献、DOI、数据来源、求解结果或未运行的验证。 |
| TEST-PDF-001 | P1 | recommended_synthesis | YES | tests | A4 纵向页面测试 |
| TEST-PDF-002 | P1 | recommended_synthesis | YES | tests | 正文边距测试 |
| TEST-PDF-003 | P1 | recommended_synthesis | YES | tests | 正文字体字号测试 |
| TEST-PDF-004 | P1 | recommended_synthesis | YES | tests | 摘要单页测试 |
| TEST-PDF-005 | P1 | recommended_synthesis | YES | tests | 目录存在及页码抽检 |
| TEST-PDF-006 | P1 | recommended_synthesis | YES | tests | 参考文献与附录强制分页 |
| TEST-PDF-007 | P1 | recommended_synthesis | YES | tests | 孤标题与图题分离 |
| TEST-FIG-001 | P1 | recommended_synthesis | YES | tests | 图内最小字号 |
| TEST-FIG-002 | P0 | recommended_synthesis | YES | tests | 图源哈希和 claim 合同 |
| TEST-FIG-003 | P1 | recommended_synthesis | YES | tests | 矢量主文件和高分辨率预览 |
| TEST-TABLE-001 | P0 | recommended_synthesis | YES | tests | 表格结构化来源测试 |
| TEST-NUM-001 | P0 | recommended_synthesis | YES | tests | 跨产物 quantity_id 一致性 |
| TEST-NUM-002 | P0 | recommended_synthesis | YES | tests | 报告精度合理性 |
| TEST-MODEL-001 | P0 | recommended_synthesis | YES | tests | 硬约束全量审计 |
| TEST-MODEL-002 | P0 | recommended_synthesis | YES | tests | 首次事件双侧验证 |
| TEST-MODEL-003 | P0 | recommended_synthesis | YES | tests | 上包络/全局峰值步长减半 |
| TEST-MODEL-004 | P0 | recommended_synthesis | YES | tests | 真正独立交叉验证 |
| TEST-REF-001 | P0 | recommended_synthesis | YES | tests | 文献真实性和引用闭合 |
| TEST-WRITE-001 | P0 | recommended_synthesis | YES | tests | 禁止未注册数字 |
| TEST-WRITE-002 | P0 | recommended_synthesis | YES | tests | 强断言证据门 |
| TEST-CODE-001 | P0 | recommended_synthesis | YES | tests | 干净环境复跑 |
| TEST-CODE-002 | P0 | recommended_synthesis | YES | tests | 随机性复现 |
| TEST-PACK-001 | P0 | recommended_synthesis | YES | tests | 提交包完整与匿名 |
| TEST-REG-001 | P1 | recommended_synthesis | YES | tests | 当前 main_v2 格式回归 |

## 5. 关键证据定位

1. 文件 A pp.6-15：共性结构、四层统一内核、解析速度和实体碰撞，支持统一模型与共用接口规则。
2. 文件 A pp.20-28：带符号事件函数、首个变号、嵌套极小-求根、临界构型，支持事件检测与最小可行参数模式。
3. 文件 A pp.36-46：上包络折点、硬约束、交叉验证和敏感性，支持高风险数值门。
4. 文件 B pp.6、20-21：流程图、表格和文字出现多个互相矛盾的最小螺距、坐标和速度，是建立 canonical result/quantity_id 的直接反例。
5. 文件 A pp.48-52 与文件 B pp.36-37：参考文献和附录在同页中段开始，支持强制分页的反向约束。
6. 文件 A pp.52-95、B pp.37-64：完整代码字体过小且附录占比高，支持“关键代码入文、全量源码入提交包”。
7. 当前样例 C pp.1-4：独立封面、摘要跨页、缺目录和窄版心，是模板回归的主要基线。
