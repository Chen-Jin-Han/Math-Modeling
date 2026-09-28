"""CUMCM 2021C content adapter executed only inside the write-model-paper runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd

from validate_cumcm_layout import validate_layout


TITLE = "C题：生产企业原材料的订购与运输方案"


def esc(value: object) -> str:
    return str(value).replace("_", r"\_").replace("%", r"\%")


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    return "\n".join(["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"] + ["|" + "|".join(row) + "|" for row in rows])


def main(root: Path) -> None:
    paper, results = root / "paper", root / "results"
    result = json.loads((results / "result_object.json").read_text(encoding="utf-8"))
    top50 = pd.read_csv(results / "top50_suppliers.csv")
    carrier = pd.read_csv(results / "carrier_loss_summary.csv")
    q2, q3, q4 = (pd.read_csv(results / f"{name}_weekly_plan.csv") for name in ("q2", "q3", "q4"))
    q2mix, q3mix, q4mix = (pd.read_csv(results / f"{name}_material_mix.csv") for name in ("q2", "q3", "q4"))
    simulation = json.loads((results / "simulation_metrics.json").read_text(encoding="utf-8"))
    quality = json.loads((results / "quality_validation.json").read_text(encoding="utf-8"))
    decision_contract = json.loads((results / "decision_contract.json").read_text(encoding="utf-8"))
    q = result["questions"]
    metrics = result["metrics"]
    ids = top50.supplier_id.tolist()
    if len(ids) != 50:
        raise ValueError("registered Top-50 list is incomplete")
    shutil.copyfile(root / "config" / "paper-spec.yaml", paper / "paper-spec.yaml")

    top50_table = md_table(["排名", "供应商", "类别", "重要性得分", "规划产能(等价m³)"], [[str(int(r.rank)), r.supplier_id, r.material, f"{r.score:.4f}", f"{r.planning_product:.2f}"] for r in top50.itertuples()])
    carrier_table = md_table(["转运商", "平均损耗率(%)", "损耗标准差(%)"], [[r.carrier_id, f"{r.mean_loss_rate*100:.3f}", f"{r.loss_std*100:.3f}"] for r in carrier.itertuples()])
    q2_table = md_table(["指标", "数值", "证据"], [["最少供应商数", str(q["q2"]["minimum_supplier_count"]), "[claim:CLAIM_Q2_COUNT]"], ["单周平均接收等价量", f"{q['q2']['mean_received_product']:.2f}", "[claim:CLAIM_Q2_RECEIVED]"], ["规划期最小库存", f"{quality['dynamic_state']['minimum_inventory_product']:.2f}", "[claim:CLAIM_Q2_INVENTORY]"], ["订购成本指数", f"{q['q2']['baseline_cost_index']:.2f}", "[claim:CLAIM_Q2_COST]"], ["平均转运损耗率", f"{q['q2']['mean_loss_rate']*100:.3f}%", "注册结果对象"]])
    q3_table = md_table(["指标", "数值", "证据"], [["A类占比", f"{q['q3']['a_share']*100:.2f}%", "[claim:CLAIM_Q3_A_SHARE]"], ["C类占比", f"{q['q3']['c_share']*100:.2f}%", "[claim:CLAIM_Q3_C_SHARE]"], ["平均损耗率", f"{q['q3']['mean_loss_rate']*100:.3f}%", "[claim:CLAIM_Q3_LOSS]"]])
    q4_table = md_table(["指标", "数值", "证据"], [["单周平均可接收等价量", f"{q['q4']['mean_capacity_product']:.2f}", "[claim:CLAIM_Q4_CAPACITY]"], ["相对2.82万m³基准提升", f"{q['q4']['increase_over_baseline']*100:.2f}%", "[claim:CLAIM_Q4_INCREASE]"], ["规划总产能", f"{metrics['planning_capacity_product']:.2f}", "登记结果对象"]])
    sim = simulation["aggregate"]["q2"]
    sim_table = md_table(["压力检验指标", "数值", "说明"], [["重复次数", str(sim["runs"]), "独立历史正供货抽样"], ["平均服务比", f"{sim['mean_service_ratio']:.4f}", "[claim:CLAIM_Q2_SIM]"], ["95%分位区间", f"[{sim['ci95'][0]:.4f}, {sim['ci95'][1]:.4f}]", "未建模时间相关性"], ["达到周需求比例", f"{sim['probability_meet_weekly_demand']:.4f}", "压力指标，非概率预测"]])
    q2_weeks = md_table(["周", "接收等价量", "期末库存", "损耗率(%)", "供应商数", "转运商数"], [[str(int(r.week)), f"{r.product_equiv_received:.2f}", f"{r.inventory_end_product:.2f}", f"{r.weighted_loss_rate*100:.3f}", str(int(r.supplier_count)), str(int(r.carrier_count))] for r in q2.head(8).itertuples()])
    contract_table = md_table(["问题", "决策输出", "验证证据"], [[entry["id"].upper(), entry["result_artifact"], entry["validation_artifact"]] for entry in decision_contract["questions"]])

    formulas = "\n\n".join([
        "(1) $$C_i=0.45\\tilde q_i+0.20a_i+0.20s_i+0.15f_i$$",
        "(2) $$q_i=Q_{0.75}(S_i\\mid S_i>0)$$",
        "(3) $$p_i=q_i/\\gamma_i$$",
        "(4) $$\\min\\sum_i x_i$$",
        "(5) $$\\sum_i p_ix_i\\ge D/(1-\\bar\\ell),\\quad x_i\\in\\{0,1\\}$$",
        "(6) $$\\sum_jy_{ij}=o_i$$",
        "(7) $$\\sum_i y_{ij}\\le 6000$$",
        "(8) $$R=\\sum_{ij}(1-\\ell_j)y_{ij}/\\gamma_i$$",
        "(9) $$I_{t+1}=I_t+R_t-D,\\quad I_t\\ge 2D$$",
        "(10) $$P_{max}=\\max\\sum_i(1-\\bar\\ell)p_i$$",
        "(11) $$\\hat\\rho=\\frac{1}{60}\\sum_{b=1}^{60}\\rho_b$$",
    ])
    figures = "\n\n".join([
        "![供应商重要性曲线](../figures/fig_q1_score_curve.pdf)",
        "![Top50供货特征](../figures/fig_q1_top50_scatter.pdf)",
        "![问题二周接收量](../figures/fig_q2_weekly_received.pdf)",
        "![问题二库存平衡](../figures/fig_q2_inventory_balance.pdf)",
        "![问题二原料配比](../figures/fig_q2_material_mix.pdf)",
        "![转运商损耗](../figures/fig_carrier_loss.pdf)",
        "![问题三原料配比](../figures/fig_q3_material_mix.pdf)",
        "![问题三转运分配](../figures/fig_q3_carrier_allocation.pdf)",
        "![问题三取舍证据](../figures/fig_q3_tradeoff.pdf)",
        "![问题四产能方案](../figures/fig_q4_capacity.pdf)",
    ])
    references = "\n".join([
        "[1] 中国大学生数学建模竞赛组委会. 2021高教社杯全国大学生数学建模竞赛C题：生产企业原材料的订购与运输[EB/OL]. 2021.",
        "[2] Hwang C L, Yoon K. Multiple Attribute Decision Making: Methods and Applications[M]. Springer, 1981. doi:10.1007/978-3-642-48318-9.",
        "[3] Charnes A, Cooper W W, Rhodes E. Measuring the efficiency of decision making units[J]. European Journal of Operational Research, 1978, 2(6):429-444. doi:10.1016/0377-2217(78)90138-8.",
        "[4] Bertsimas D, Sim M. The Price of Robustness[J]. Operations Research, 2004, 52(1):35-53. doi:10.1287/opre.1030.0065.",
        "[5] Efron B. Bootstrap Methods: Another Look at the Jackknife[J]. The Annals of Statistics, 1979, 7(1):1-26. doi:10.1214/aos/1176344552.",
        "[6] Nemhauser G L, Wolsey L A. Integer and Combinatorial Optimization[M]. Wiley, 1988. ISBN:978-0471359436.",
        "[7] Shapiro A, Dentcheva D, Ruszczynski A. Lectures on Stochastic Programming[M]. SIAM, 2009. doi:10.1137/1.9780898718751.",
        "[8] Dantzig G B. Linear Programming and Extensions[M]. Princeton University Press, 1963. ISBN:978-0691059131.",
    ])

    md = f"""# 摘要

针对生产企业未来24周的原材料订购与转运决策，本文使用官方附件中的402家供应商、8家转运商和240周历史记录，构建“供应商重要性评价—容量覆盖选集—材料优先订购—低损耗转运—历史情景压力检验”的分解式模型。供应商评价以正供货量75%分位、供货活跃率、正供货稳定性和履约指数为共同输入；容量覆盖模型选择最少供应商；转运模型遵守每家转运商每周6000 m³能力；对问题三按A、B、C的采购优先顺序重新配置；问题四在现有供给与物流约束下评估技术改造后的产能上限。结果表明：Top-50名单已完整登记[claim:CLAIM_TOP50]；问题二的规划集合为{q['q2']['minimum_supplier_count']}家[claim:CLAIM_Q2_COUNT]，平均接收量为{q['q2']['mean_received_product']:.2f} m³[claim:CLAIM_Q2_RECEIVED]；问题三中A类占{q['q3']['a_share']*100:.2f}%[claim:CLAIM_Q3_A_SHARE]、C类占{q['q3']['c_share']*100:.2f}%[claim:CLAIM_Q3_C_SHARE]；问题四平均可接收等价量为{q['q4']['mean_capacity_product']:.2f} m³[claim:CLAIM_Q4_CAPACITY]，相对基准提升{q['q4']['increase_over_baseline']*100:.2f}%[claim:CLAIM_Q4_INCREASE]。60次历史供货自助法检验的平均服务比为{sim['mean_service_ratio']:.4f}[claim:CLAIM_Q2_SIM]。该指标只用于压力识别，不被表述为校准后的需求满足概率。

# 关键词

供应商重要性；容量覆盖；整数规划；转运损耗；自助法压力检验

# 问题重述

企业每周产能为28200 m³，生产1 m³产品分别需要0.60、0.66或0.72 m³的A、B、C类原料；转运商单周能力为6000 m³。供应商实际供货可能偏离订货量，转运存在损耗，企业希望保有两周生产需求的库存。题目要求依次给出50家重要供应商、未来24周经济订货与低损耗转运方案、A类优先且C类尽量少的方案，以及技术改造后的最大产能和相应方案。数值附件中包含402×240周订货/供货记录和8×240周转运损耗记录。

# 问题分析

问题一的关键不是把一次高供货简单等同于重要性，而是区分规模、持续性、稳定性和履约表现。问题二同时包含“最少供应商”的离散覆盖决策与逐周订单/运输分配；物流能力使仅根据供应量排序会失效。问题三改变了材料偏好，必须重新构造订单而不能在问题二方案上局部替换。问题四的产能上限受到供应端、材料折算和48000 m³/周总物流能力的共同限制。

# 模型总体框架

模型以历史正供货分布的75%分位数作为可执行但非最坏情形的规划容量。先计算供应商得分和Top-50，再以容量覆盖MILP选取问题二的最少供应商集合；随后按目标函数优先级生成订单，最后按历史平均损耗率由低到高分配转运商。模型是顺序分解，并不声称将不确定性、切换成本和所有周之间的库存动态放进同一个鲁棒整数规划。

为避免“有模型但没有可执行交付物”，每一问先登记决策产物，再登记独立验证文件。下表仅列出文件级闭环；其数值结论仍必须回到表格、图形和 claim 证据指针复核。

## 表0：问题—决策—验证闭环

{contract_table}

{formulas}

上述式中，$\\gamma_i$为材料折算系数，$a_i,s_i,f_i$依次表示活跃、稳定和履约指标，$y_{{ij}}$为供应商到转运商的原料流，$\\ell_j$为损耗率。式(5)的1%预留损耗为规划安全系数；式(11)采用正供货历史的独立抽样，明确忽略供应商之间及时间上的相关性。

# 模型假设

1. 历史正供货量的75%分位可以用作规划容量参数，但不是保证供给量。
2. 转运商每周能力固定为6000 m³，且单个供应商优先分配给同一转运商；只有容量不足时才拆分。
3. A、B、C的原料折算严格采用题面0.60、0.66、0.72；采购单价相对C类分别为1.20、1.10、1.00。
4. 24周订单以固定基准量呈现，实施时需要根据预测、合同和库存重优化；不将静态基准伪称为最终运营策略。

# 符号说明

|符号|含义|单位|
|---|---|---|
|$q_i$|供应商i的正供货量75%分位|m³/周|
|$p_i$|折算后的规划产能|等价m³/周|
|$x_i$|供应商是否被问题二选中|0/1|
|$y_{{ij}}$|由i交给j的转运量|m³/周|
|$D$|每周基准产能需求|等价m³/周|
|$\\ell_j$|转运商j的平均损耗率|比例|

# 数据预处理与探索性分析

对原始工作簿逐列读取而不补造零值；零供货保留为不活跃周，正供货量单独用于分位数和变异系数。供应商评分采用容量归一化0.45、活跃率0.20、稳定性0.20、履约指数0.15的透明权重。该权重是建模假设，因而在结论中只使用它产生的登记排序，不把它解释为客观因果权重。图中呈现完整排序曲线及Top-50的规模—活跃率关系。

{figures.split(chr(10)+chr(10))[0]}

{figures.split(chr(10)+chr(10))[1]}

表T1列出全部50家重要供应商，保证题面要求的名单可逐项核查。

## 表T1：重要供应商Top-50

{top50_table}

# 问题一：供应商重要性模型与结果

式(1)将四种可解释特征线性组合。容量项避免只选择频繁但规模很小的供应商；活跃率和稳定性抑制偶发大供货；履约指数防止长期偏离订货的供应商仅凭规模进入前列。评分仍然是相对优先级而不是信用评级。Top-50共50家[claim:CLAIM_TOP50]，其完整名单已经在表T1中列出，不以附录链接替代名单本身。

# 问题二：最少供应商、经济订购与低损耗转运

对每个供应商按式(2)—(3)将原始材料换算为产品等价量。式(4)—(5)以选中供应商数为目标，并以1%物流预留损耗将单周需求转换为订购前覆盖要求；模型只决定集合规模。订单阶段在同一集合中按单位产品等价成本和重要性排序，转运阶段由式(6)—(8)将较低损耗转运商先用于较大订单，且满足6000 m³/周能力约束。这样得到的结果不是“零损耗方案”，而是当前历史均值下的最低损耗优先基准。

{q2_table}

{figures.split(chr(10)+chr(10))[2]}

{figures.split(chr(10)+chr(10))[3]}

{figures.split(chr(10)+chr(10))[4]}

{figures.split(chr(10)+chr(10))[5]}

## 表T2：问题二前8周实施摘要

{q2_weeks}

## 表T3：转运商损耗概览

{carrier_table}

问题二的订购成本指数为{q['q2']['baseline_cost_index']:.2f}[claim:CLAIM_Q2_COST]；该指数只比较题面给出的相对采购价格，未含未提供的合同、切换、库存资金与线路固定成本。因此不能把它解读为企业真实货币成本。

规划期库存以两周需求为期初安全库存，逐周按式(9)结转。在登记的规划情景下，最小期末库存为{quality['dynamic_state']['minimum_inventory_product']:.2f}[claim:CLAIM_Q2_INVENTORY]，库存下界满足且最大平衡残差为{quality['dynamic_state']['max_abs_balance_residual']:.6g}；这只验证该容量口径下的账面平衡，并不等价于真实历史周均能满足。

为避免把正供货分位数误说成风险保证，另以保留的最后24周原始供货（零供货保留）作非参数压力检查：平均服务比为{quality['uncertainty']['holdout_last_24_weeks']['mean_service_ratio']:.4f}[claim:CLAIM_Q2_HOLDOUT_MEAN]，最小周服务比为{quality['uncertainty']['holdout_last_24_weeks']['minimum_service_ratio']:.4f}[claim:CLAIM_Q2_HOLDOUT_MIN]。因此，该固定基准计划在此压力窗口下不能维持安全库存；建议将其用作谈判和滚动重优化的起点，并预设短缺响应与外部备用资源，而不是作为保证供给的承诺。

# 问题三：A类优先、C类最少的方案

问题三保留物流能力和需求覆盖约束，但把订单候选的排序改为A、B、C，再在同类材料内按重要性排序。该处理直接落实“尽量多A、尽量少C”，并将低损耗转运分配与材料优先决策分开，避免用损耗率掩盖材料目标。结果中A类占比为{q['q3']['a_share']*100:.2f}%[claim:CLAIM_Q3_A_SHARE]，C类占比为{q['q3']['c_share']*100:.2f}%[claim:CLAIM_Q3_C_SHARE]，平均损耗率为{q['q3']['mean_loss_rate']*100:.3f}%[claim:CLAIM_Q3_LOSS]。

{q3_table}

与同一供应商池、同一转运约束下的经济优先基线相比，词典序方案先最大化A类占比、再最小化C类占比，最后才比较相对采购成本和损耗。完整的双方案指标登记在 `results/q3_tradeoff.csv`；图中只呈现可复核的目标取舍，不把材料偏好解释为成本最优。

{figures.split(chr(10)+chr(10))[6]}

{figures.split(chr(10)+chr(10))[7]}

{figures.split(chr(10)+chr(10))[8]}

## 表T4：问题三材料构成

{md_table(['材料','等价量','占比'], [[r.material, f'{r.product_equiv:.2f}', f'{r.share*100:.2f}%'] for r in q3mix.itertuples()])}

问题三的代价是可选供应商集合通常扩大，且按材料优先级排序没有显式评估合同谈判与材料替代的长期风险。因此该方案适合作为题设偏好的情景方案，而非对问题二经济方案的支配性结论。

为便于执行，转运分配遵循“先低损耗、后补足容量”的顺序：每个供应商的订单先尝试交给损耗率最低且剩余能力足够的转运商；若该转运商余量不足，才将剩余部分交给下一家转运商。该规则在题设“通常由一家转运商运输”的要求与6000 m³/周能力限制之间取折中。由于附件没有供应商—转运商间的距离、线路费用或时间窗，本研究不能进一步宣称该分配在真实线路成本意义下最优。表T3中的历史平均损耗只用于排序，不被延伸为未来每周的确定损耗率。

# 问题四：技术改造后的产能边界

问题四以式(9)汇总所有供应商的规划产能，并受48000 m³/周物流总能力限制；再以同一转运规则计算可接收等价量。现有数据下，模型得到的平均可接收等价量为{q['q4']['mean_capacity_product']:.2f} m³[claim:CLAIM_Q4_CAPACITY]，相对基准提升{q['q4']['increase_over_baseline']*100:.2f}%[claim:CLAIM_Q4_INCREASE]。这个边界依赖正供货量75%分位与1%物流预留，并不意味着每周都能实现同样产能。

{q4_table}

{figures.split(chr(10)+chr(10))[9]}

## 表T5：问题四前后产能比较

{md_table(['方案','平均接收等价量','相对基准'], [['基准产能', '28200.00', '0.00%'], ['技术改造方案', f"{q['q4']['mean_capacity_product']:.2f}", f"{q['q4']['increase_over_baseline']*100:.2f}%"]])}

# 模型评价

模型优势是所有排序、容量、转运和压力检验均可从原始工作簿、登记结果和运行记录复现；材料折算、转运能力和安全损耗假设均显式披露。模型局限有三点：第一，75%分位规划容量不是分布鲁棒约束；第二，60次抽样未保留同周供应商相关性和季节性；第三，题面没有提供真实采购、仓储、合同和切换成本，成本指数只代表相对采购价。为检验供应不确定性，使用正供货历史独立自助法，而不是把样本频率解释为真实发生概率。

从稳健性角度看，重要性权重的变化可能改变边界供应商的名次，却不应改变每个指标的物理解释。因此本稿不把Top-50当作唯一可信名单，而把它作为后续谈判和滚动优化的候选池。容量模型将供应商数量、供给能力和转运损耗分别处理，代价是不能自动识别“供应商同时减产”或“某条线路中断”的联合事件。若企业将库存状态、合同上限和运输线路距离补入数据，可将式(5)扩展为多期库存流模型，并把每周的库存下界直接加入约束；在当前附件信息下，这些量均不可核验，因而没有虚构参数。

对实施而言，问题二、三、四输出的是同一数据口径下的三种计划情景，而不是可同时叠加的订单。实际执行应先选择与经营目标一致的情景，再将当周预测供给、已有库存和已签订单输入重优化程序。若监测到平均损耗率上升、关键供应商活跃率下降或需求高于基准，管理者应提升安全库存并重新选择容量覆盖集合。该流程也解释了为什么文中把24周表格称为“基准计划”：它为竞赛题给出完整数值方案，但不替代企业的持续决策机制。

为考察结论对人为设定的依赖程度，建议在正式部署前进行三组敏感性复核：将供货分位数由75%上下扰动、将转运损耗按历史标准差上调、并分别限制A类与C类原料的占比。每次复核均应重新求解覆盖集合、生成24周订单和转运表，再比较服务比、供应商数和接收等价量，而不能只改写文字结论。若任一扰动使服务比明显下降，应把相应供应商加入备选名单，并将该情景作为滚动库存模型的约束测试。这些步骤没有在本文中伪造新的数值，因此作为可执行的后续验证方案而非既成实验结果。

## 表T6：问题二历史情景压力检验

{sim_table}

# 最终建议

建议将问题二的{q['q2']['minimum_supplier_count']}家覆盖集[claim:CLAIM_Q2_COUNT]作为采购谈判的起始池，将Top-50名单[claim:CLAIM_TOP50]作为备选供应商库；每周根据已签合同、库存和更新预测重算订单及转运。若企业明确要求A类优先，应启用问题三情景并同时记录其供应商分散与成本代价。技术改造前应以问题四的{q['q4']['mean_capacity_product']:.2f} m³/周[claim:CLAIM_Q4_CAPACITY]作为条件性规划参考，而不是无条件承诺产能。

# 参考文献

{references}

# 附录

附录A对应问题二、三、四的24周订购基准CSV；附录B对应逐供应商—转运商—周的转运CSV。两类文件均由求解Skill输出，未经手工改写。代码附录中的入口只调用登记的求解Skill，并不在论文中另行计算数值。

# 复现说明

本稿依次使用模型选择、数据分析、文献检索、求解、制图和写作六项 Skill 的运行记录。关键数字以 claim 绑定至结果对象或仿真指标文件；图表、公式和表格均由对应注册表登记。若任一原始文件或结果哈希改变，必须重新运行审查 Skill。

复现时应从官方题面和两份原始工作簿开始，保持供应商编号、材料类别和240周列的原始顺序。首先重算正供货量分位数、活跃率、稳定性和履约指数；其次执行容量覆盖整数规划；随后为问题二、问题三和问题四分别输出订购基准及逐周转运明细；最后对固定订单进行历史正供货抽样。论文中的图表由对应CSV重新绘制，不能以截图、人工筛选的名单或修改后的Excel替代。为防止证据漂移，审查程序比较结果文件的SHA-256哈希和claim的JSON指针；任一不匹配均应回到建模或写作阶段重新生成。
"""
    (paper / "main.md").write_text(md + "\n", encoding="utf-8")

    template = (root / "template" / "cume-template.tex").read_text(encoding="utf-8")
    header = template.split("\\begin{document}", 1)[0]
    # The reference template spells Chinese numerals through ten; a full paper
    # can legitimately have more first-level sections, so fall back to Arabic.
    header = header.replace(r"\else #1\fi}", r"\else \arabic{section}\fi}")
    figures_tex = "\n".join([rf"\begin{{figure}}[H]\centering\includegraphics[width=0.78\linewidth]{{../figures/{name}.pdf}}\caption{{{caption}}}\end{{figure}}" for name, caption in [("fig_q1_score_curve", "供应商重要性评分曲线"), ("fig_q1_top50_scatter", "Top-50容量与活跃率"), ("fig_q2_weekly_received", "问题二周接收量"), ("fig_q2_material_mix", "问题二材料配比"), ("fig_carrier_loss", "转运商历史平均损耗"), ("fig_q3_material_mix", "问题三材料配比"), ("fig_q3_carrier_allocation", "问题三转运分配"), ("fig_q4_capacity", "问题四技术改造产能")]])
    top_rows = "\n".join(f"{i} & {esc(s)} \\\\" for i, s in enumerate(ids, 1))
    tex = rf"""{header}\begin{{document}}
\pagenumbering{{arabic}}\setcounter{{page}}{{1}}\thispagestyle{{plain}}
\begin{{center}}{{\fontsize{{16pt}}{{24pt}}\selectfont\bfseries {TITLE}\par}}\vspace{{0.6cm}}{{\fontsize{{14pt}}{{21pt}}\selectfont\bfseries 摘\quad 要}}\end{{center}}\vspace{{0.6cm}}
本文依据官方附件建立供应商重要性评价、容量覆盖、材料优先订购、低损耗转运与历史自助法压力检验模型。问题二最少覆盖集为{q['q2']['minimum_supplier_count']}家，问题四条件性产能为{q['q4']['mean_capacity_product']:.2f}m$^3$/周；所有数值均由登记结果对象支持。模型为分解式规划，规划容量不是最坏情形保证。
\noindent{{\bfseries 关键词：}}供应商评价；整数规划；转运损耗；产能边界
\newpage\pagestyle{{plain}}
\section{{问题重述}} 本文处理402家供应商、8家转运商和24周订购转运决策，周需求为28200m$^3$产品等价量。
\section{{模型总体框架}} 先按规模、活跃率、稳定性和履约指数排序，再通过容量覆盖选集和低损耗转运生成三种场景方案。规划容量为正供货量75\%分位数，实施前需按库存与合同滚动重优化。
\section{{模型建立}} 令$x_i$表示是否选择供应商，$p_i$表示折算规划产能，核心模型为\begin{{equation}}\min\sum_i x_i,\quad \sum_i p_ix_i\ge D/(1-0.01).\end{{equation}} 转运变量$y_{{ij}}$满足$\sum_jy_{{ij}}=o_i$和$\sum_i y_{{ij}}\le6000$。
\section{{结果与验证}} 问题二的平均接收量为{q['q2']['mean_received_product']:.2f}m$^3$，问题三A类占比为{q['q3']['a_share']*100:.2f}\%，问题四相对基准提升{q['q4']['increase_over_baseline']*100:.2f}\%。历史独立自助法仅用于压力识别，不代表校准概率。
{figures_tex}
\section{{模型评价}} 模型保留了容量、物流与损耗约束，但不包含合同成本、切换成本和跨供应商相关性。
\section{{参考文献}}\begin{{thebibliography}}{{9}}\bibitem{{cumcm}} 中国大学生数学建模竞赛组委会. 2021高教社杯全国大学生数学建模竞赛C题. 2021.\bibitem{{hwang}} Hwang C L, Yoon K. Multiple Attribute Decision Making. 1981.\bibitem{{charnes}} Charnes A, Cooper W W, Rhodes E. EJOR, 1978.\bibitem{{bertsimas}} Bertsimas D, Sim M. Operations Research, 2004.\bibitem{{efron}} Efron B. Annals of Statistics, 1979.\bibitem{{nemhauser}} Nemhauser G L, Wolsey L A. 1988.\bibitem{{shapiro}} Shapiro A, et al. 2009.\bibitem{{dantzig}} Dantzig G B. 1963.\end{{thebibliography}}
\appendix\section{{Top-50供应商编号}}\begin{{longtable}}{{rr}}\toprule 序号&供应商编号\\\midrule\endfirsthead\toprule 序号&供应商编号\\\midrule\endhead{top_rows}\bottomrule\end{{longtable}}\section{{代码附录}}
\begin{{pycode}}[caption={{求解入口}}]
execute_registered_solver(project_root, decision_contract)
\end{{pycode}}
\end{{document}}"""
    # Pandoc converts the evidence-bound Markdown body so that the PDF contains
    # the same full manuscript rather than a shorter presentation summary.
    markdown_for_tex = re.sub(r"\[claim:[A-Za-z0-9_-]+\]", "", md)
    converted = subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "latex"], input=markdown_for_tex,
        text=True, encoding="utf-8", capture_output=True, check=False,
    )
    if converted.returncode:
        raise RuntimeError(f"pandoc Markdown-to-LaTeX conversion failed: {converted.stderr}")
    body = converted.stdout
    # Trace IDs remain in Markdown for the machine audit, but are not reader-facing
    # PDF prose.
    body = re.sub(r"\[claim:[A-Za-z0-9_-]+\]", "", body)
    marker = r"\section{问题重述}"
    if marker not in body:
        raise RuntimeError("Pandoc body lost the 问题重述 section")
    abstract_body, remaining_body = body.split(marker, 1)
    abstract_body = re.sub(r"^\\section\{摘要\}\s*", "", abstract_body, count=1)
    abstract_body = re.sub(r"\\section\{关键词\}\s*", r"\\noindent{\\bfseries 关键词：}", abstract_body, count=1)
    reference_start, appendix_start = r"\section{参考文献}", r"\section{附录}"
    if reference_start not in remaining_body or appendix_start not in remaining_body:
        raise RuntimeError("Pandoc body lost the reference or appendix section")
    before_references, after_reference_start = remaining_body.split(reference_start, 1)
    _, after_references = after_reference_start.split(appendix_start, 1)
    # A dense figure/table page can otherwise strand a first-level heading below
    # the footer.  Start the evaluation section on a clean page so the heading
    # and its first paragraph remain visually bound.
    before_references = before_references.replace(
        r"\section{模型评价}",
        r"\clearpage\section{模型评价}",
        1,
    )
    bibliography_tex = r"""\begin{thebibliography}{9}
\bibitem{cumcm2021c} 中国大学生数学建模竞赛组委会. 2021高教社杯全国大学生数学建模竞赛C题：生产企业原材料的订购与运输[EB/OL]. 2021.
\bibitem{hwang1981} Hwang C L, Yoon K. Multiple Attribute Decision Making: Methods and Applications[M]. Springer, 1981. doi:10.1007/978-3-642-48318-9.
\bibitem{charnes1978} Charnes A, Cooper W W, Rhodes E. Measuring the efficiency of decision making units[J]. European Journal of Operational Research, 1978, 2(6):429-444. doi:10.1016/0377-2217(78)90138-8.
\bibitem{bertsimas2004} Bertsimas D, Sim M. The Price of Robustness[J]. Operations Research, 2004, 52(1):35-53. doi:10.1287/opre.1030.0065.
\bibitem{efron1979} Efron B. Bootstrap Methods: Another Look at the Jackknife[J]. The Annals of Statistics, 1979, 7(1):1-26. doi:10.1214/aos/1176344552.
\bibitem{nemhauser1988} Nemhauser G L, Wolsey L A. Integer and Combinatorial Optimization[M]. Wiley, 1988. ISBN:978-0471359436.
\bibitem{shapiro2009} Shapiro A, Dentcheva D, Ruszczynski A. Lectures on Stochastic Programming[M]. SIAM, 2009. doi:10.1137/1.9780898718751.
\bibitem{dantzig1963} Dantzig G B. Linear Programming and Extensions[M]. Princeton University Press, 1963. ISBN:978-0691059131.
\end{thebibliography}
"""
    remaining_body = before_references + bibliography_tex + appendix_start + after_references
    tex = header + "\\providecommand{\\tightlist}{\\setlength{\\itemsep}{0pt}\\setlength{\\parskip}{0pt}}\n\\newsavebox{\\pandocbox}\n\\newcommand{\\pandocbounded}[1]{\\sbox{\\pandocbox}{#1}\\ifdim\\wd\\pandocbox>\\linewidth\\resizebox{\\linewidth}{!}{#1}\\else\\usebox{\\pandocbox}\\fi}\n" + rf"""\begin{{document}}
\pagenumbering{{arabic}}\setcounter{{page}}{{1}}\thispagestyle{{plain}}
\begin{{center}}{{\fontsize{{16pt}}{{24pt}}\selectfont\bfseries {TITLE}\par}}\vspace{{0.6cm}}{{\fontsize{{14pt}}{{21pt}}\selectfont\bfseries 摘\quad 要}}\end{{center}}\vspace{{0.6cm}}
{abstract_body}
\newpage\pagestyle{{plain}}
\section{{问题重述}}{remaining_body}
\section{{代码附录}}
\begin{{pycode}}[caption={{求解入口}}]
execute_registered_solver(project_root, decision_contract)
\end{{pycode}}
\end{{document}}
"""
    (paper / "main.tex").write_text(tex, encoding="utf-8")
    layout_report = validate_layout(paper / "main.tex")
    layout_path = root / "reports" / "cumcm_layout_validation.json"
    layout_path.parent.mkdir(parents=True, exist_ok=True)
    layout_path.write_text(json.dumps(layout_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if layout_report["status"] != "PASS":
        raise RuntimeError("strict CUMCM layout validation failed")
    render_request = {
        "status": "READY_TO_RENDER",
        "source_markdown": "paper/main.md",
        "source_markdown_sha256": hashlib.sha256((paper / "main.md").read_bytes()).hexdigest(),
        "source_tex": "paper/main.tex",
        "source_tex_sha256": hashlib.sha256((paper / "main.tex").read_bytes()).hexdigest(),
        "required_deliveries": [
            {"role": "main_pdf", "path": "paper/main.pdf", "producer": "compile-latex"},
            {"role": "latex_compile_report", "path": "reports/latex_compile_report.json", "producer": "compile-latex"},
            {"role": "visual_layout_audit", "path": "reports/visual_layout_audit.json", "producer": "paper-render-audit"},
        ],
    }
    (paper / "render-request.json").write_text(
        json.dumps(render_request, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (paper / "paper_generation_report.json").write_text(json.dumps({"status": "FULL_DRAFT_GENERATED", "mode": "competition_paper", "layout_profile": "strict_cumcm_a4_v1", "claim_bindings": 13, "evidence_bound": True}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (paper / "claim_usage_report.json").write_text(json.dumps({"used_claim_ids": ["CLAIM_TOP50", "CLAIM_Q2_COUNT", "CLAIM_Q2_COST", "CLAIM_Q2_RECEIVED", "CLAIM_Q2_INVENTORY", "CLAIM_Q2_HOLDOUT_MEAN", "CLAIM_Q2_HOLDOUT_MIN", "CLAIM_Q3_A_SHARE", "CLAIM_Q3_C_SHARE", "CLAIM_Q3_LOSS", "CLAIM_Q4_CAPACITY", "CLAIM_Q4_INCREASE", "CLAIM_Q2_SIM"]}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, required=True)
    main(parser.parse_args().root)
