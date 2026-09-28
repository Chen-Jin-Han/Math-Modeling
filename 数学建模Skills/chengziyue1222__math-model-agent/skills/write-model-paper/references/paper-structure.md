# 数学建模论文结构

For `competition_paper`, default to: 摘要、关键词、问题重述、问题分析、模型假设、符号说明、（条件性）统一模型层、问题一至五的模型/求解/结果与分析、模型检验与灵敏度分析、模型评价与推广、参考文献、附录。Do not add a contents page.

1. 摘要：逐个子问题给出方法、关键结果、验证和结论，不写空泛背景。
2. 问题重述与分析：重述对象、条件和交付；随后说明输入输出、子问题关系、难点和建模判据。
3. 模型假设：逐条说明理由、适用范围和可能影响。
4. 符号说明：统一符号、单位、维度和代码变量名。
5. 统一模型层只在至少两个子问题共享状态、约束、数据、几何、目标或求解内核时出现；否则各题独立建立模型。
6. 模型建立：按现实关系、数学表达、公式、参数解释和适用范围展开。
7. 求解方法：说明算法、参数、初始化、停止条件；内部软件与运行细节不进入正文。
8. 结果与分析：用结果、规律、原因、证据和实际含义形成段落；按需要报告基线、约束审计、误差、敏感性、稳健性或不确定性。
8. 讨论：解释机制、优势、局限、失败条件和可迁移性。
9. 参考文献：只保留真实、可核验且正文使用的来源。
10. 附录：列出支撑材料的完整文件清单，附录 A 放补充结果/检验，附录 B 按模块包含全部自有、完整、可运行源程序。第三方库仅给出依赖、版本与安装说明，不复制库源码或二进制。

摘要必须是电子版第 1 页，问题重述紧随其后且正文不重置页码；附录开始前最多 30 页。competition 默认 PDF 且 PDF/DOCX 二选一，audit 同时交付两种格式。论文与支撑材料压缩包各自不得超过 20 MiB。支撑材料清单必须与 ZIP/RAR 逐项一致，并在干净临时目录通过复现命令；缺少本地模块、数据、配置、字体或绘图依赖时必须失败。

建立“结论—表格/图—结果文件—代码入口”映射。任何无法追溯的数字都不得进入终稿。

Counts in `paper-spec.yaml` are lower-bound delivery checks, not quality targets. Every declared question still needs a result, suitable validation and decision-grade discussion. Include a framework diagram and notation table only when they clarify the model; include sensitivity/robustness evidence whenever the conclusion depends on it. Backend claim anchors may be retained in source files for audit but are removed from reader-facing PDF/DOCX output.
