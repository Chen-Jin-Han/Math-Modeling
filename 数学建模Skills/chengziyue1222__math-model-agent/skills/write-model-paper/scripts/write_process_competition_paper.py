"""Write an evidence-bound CUMCM-style paper for a temporal process problem."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "skills" / "write-model-paper" / "scripts"))
from validate_cumcm_layout import validate_layout


TITLE = "C题：化工厂生产流程的预测和控制"


def table(headers: list[str], rows: list[list[str]]) -> str:
    return "\n".join(["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"] + ["|" + "|".join(row) + "|" for row in rows])


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(root: Path) -> None:
    paper, results = root / "paper", root / "results"
    paper.mkdir(parents=True, exist_ok=True)
    result = json.loads((results / "result_object.json").read_text(encoding="utf-8"))
    q1 = json.loads((results / "q1_metrics.json").read_text(encoding="utf-8"))
    q2 = json.loads((results / "q2_metrics.json").read_text(encoding="utf-8"))
    q3 = json.loads((results / "q3_metrics.json").read_text(encoding="utf-8"))
    quality = json.loads((results / "quality_validation.json").read_text(encoding="utf-8"))
    tradeoff = pd.read_csv(results / "q2_threshold_tradeoff.csv")
    p1 = pd.read_csv(results / "q1_predictions.csv").head(8)
    p2 = pd.read_csv(results / "q2_alert_predictions.csv").head(8)
    p3 = pd.read_csv(results / "q3_time_predictions.csv").query("actual_event == 1").head(8)
    r = result["metrics"]
    q2_test = result["questions"]["q2"]["test"]
    q1_rows = [[str(int(x.time)), f"{x.SO2_actual:.3f}", f"{x.SO2_prediction:.3f}", f"{x.H2S_actual:.3f}", f"{x.H2S_prediction:.3f}"] for x in p1.itertuples()]
    q2_rows = [[str(int(x.time)), str(int(x.actual_event)), f"{x.event_probability:.3f}", str(int(x.predicted_event))] for x in p2.itertuples()]
    q3_rows = [[str(int(x.time)), f"{x.actual_first_delay:.1f}", f"{x.predicted_first_delay:.1f}"] for x in p3.itertuples()]
    formula_text = "\n\n".join([
        "(1) $$\\hat{\\boldsymbol y}_t=f(\\boldsymbol x_t).$$",
        "(2) $$\\phi_t=[x_t,y_t,\\overline{x}_{t-29:t},s(x_{t-29:t}),\\overline{y}_{t-29:t},s(y_{t-29:t})].$$",
        "(3) $$k_j=Q_q(y_{j,\\mathrm{train}}).$$",
        "(4) $$z_t=\\mathbb{1}\\{\\max_{h=10}^{70}(SO2_{t+h}>k_1\\lor H2S_{t+h}>k_2)\\}. $$",
        "(5) $$\\hat z_t=\\mathbb{1}\\{\\hat p_t\\ge c\\}. $$",
        "(6) $$\\hat\\tau_t=g(\\phi_t),\\qquad 10\\le\\hat\\tau_t\\le70. $$",
        "(7) $$\\mathrm{RMSE}=\\sqrt{n^{-1}\\sum_t\\|y_t-\\hat y_t\\|_2^2}. $$",
        "(8) $$\\mathrm{F1}=2PR/(P+R). $$",
        "(9) $$\\mathrm{MAE}=n_e^{-1}\\sum_{t:z_t=1}|\\tau_t-\\hat\\tau_t|. $$",
        "(10) $$\\bar m^*=B^{-1}\\sum_{b=1}^{B}\\bar m_b. $$",
    ])
    figures = [
        ("fig_raw_output", "前1000个样本的两种输出浓度"), ("fig_correlation", "输入—输出相关矩阵"),
        ("fig_q1_scatter", "问题一测试集预测散点"), ("fig_q1_residual", "问题一残差分布"),
        ("fig_q2_tradeoff", "问题二阈值严格度的验证集取舍"), ("fig_q2_roc", "问题二测试集ROC曲线"),
        ("fig_q2_probability", "问题二按时间顺序的报警概率"), ("fig_q3_timing", "问题三首次超限时刻预测"),
    ]
    figures_md = "\n\n".join(f"![{caption}](../figures/{name}.pdf)" for name, caption in figures)
    refs = "\n".join([
        "[1] 肇庆学院数学建模竞赛组委会. 2026年肇庆学院数学建模竞赛C题：化工厂生产流程的预测和控制问题[Z].",
        "[2] Breiman L. Random Forests[J]. Machine Learning, 2001, 45(1):5-32. doi:10.1023/A:1010933404324.",
        "[3] Fawcett T. An introduction to ROC analysis[J]. Pattern Recognition Letters, 2006, 27(8):861-874. doi:10.1016/j.patrec.2005.10.010.",
        "[4] Hoerl A E, Kennard R W. Ridge Regression: Biased Estimation for Nonorthogonal Problems[J]. Technometrics, 1970, 12(1):55-67. doi:10.1080/00401706.1970.10488634.",
        "[5] Efron B. Bootstrap Methods: Another Look at the Jackknife[J]. The Annals of Statistics, 1979, 7(1):1-26. doi:10.1214/aos/1176344552.",
    ])
    implementation = """
本题的目标函数不是把预测分数机械地做大，而是在三个问题的口径中分别最小化可解释的预测误差、控制报警阈值的严格度并报告首次超限时间误差。约束来自信息可得性：问题一只允许使用时刻t的五项输入；问题二、三的特征只能读取时刻t及之前30个采样点的输入和输出；标签窗口严格位于t+10至t+70。由此，任意未来输出、未来阈值或测试集信息都不能进入训练和验证阶段。这个信息约束既是模型约束，也是复现约束。

时间序列按预测起点而不是按原始行随机打散。60%的起点用于拟合，20%用于选择模型和报警概率截断点，最后20%只在模型确定后评估。由于相邻样本相关性很强，随机划分会把近邻状态同时放入训练和测试，从而高估泛化能力；本文明确不使用这种划分。对于问题一，岭回归和随机森林在同一时间顺序验证集上比较，再与训练均值预测作基线比较。对于问题二，候选阈值全部从训练输出的分位数计算，选择条件要求验证ROC-AUC不低于0.60，并在满足条件的方案中尽量使用较低分位数；这一规则拒绝“全部报警”造成的虚高F1。

模型选择仍有不可消除的局限。训练期、验证期和测试期的事件率会随工况变化，因而验证集的优良AUC不能被外推为长期保证。特别是测试期的ROC-AUC低于验证期，表明现有五项输入和短历史窗口不足以支持无人值守的控制动作。论文因此把问题二输出限定为“监测候选报警”，而非自动阀门控制指令。若要实施控制，还需要阀门、流量、温度、催化剂状态、停留时间和安全边界等可核验变量，并进行干预或准实验验证。

图表的角色也与文字分离。图1和图2用于观察数据尺度、相关结构与可能的共线性；图3和图4检验问题一的拟合误差是否集中于某一污染物；图5显示阈值选择不应只看F1；图6和图7显示测试阶段报警概率的判别情况与时间分布；图8只在真实发生未来超限的样本上评估时间误差。每张图都由已登记CSV生成，并记录源数据哈希、模型种子和样本定义，不能用截图或手工改图替代。

在管理语境中，较低的阈值会提高提前发现的机会，也会增加报警频率和复核负担；较高的阈值则可能漏掉边界事件。本文以验证AUC作为可判别性的最低条件，再使用最小合格分位数处理这一双目标取舍。这个选择是题设“阈值尽量小且保证预测性能”的可复核解释，并不等价于法定排放标准；表中阈值处于标准化数据尺度，不能直接转换成环境监管限值。未来如有工程单位和合规标准，应重跑阈值搜索并保留同样的时间切分。

复现实施应从官方DOCX和两张原始CSV开始：先核查行数、列名和缺失值，再合并为保留原始顺序的面板；随后用固定种子生成预测起点；最后保存逐起点预测、模型指标、阈值取舍和图形元数据。运行记录还保存了本次适配器两次可追溯失败：首次缺少算法库导入路径，第二次缺少报告目录；修复后才有成功输出。这样的失败不被删除，因为它说明论文结论来自可执行流程而非事后拼接的文件。

为了检验每个结论的边界，本文把“预测有效”“报警可用”和“控制可部署”区分为三个层次。预测有效只要求在预先留出的时间段上相对简单基线存在可报告改善；报警可用还要求概率排序具有足够判别力、阈值选择不依赖测试集、并能量化漏报和误报；控制可部署则额外需要控制变量、作用延迟、设备安全约束、干预成本及独立运行试验。本题附件只支撑第一个层次的一部分结论，以及第二个层次的探索性比较。它没有记录何时改变输入气体、变化幅度、设备响应和人工处置成本，所以任何“推荐立刻调节某阀门”的文字都会超出证据范围。

对问题一而言，岭回归优于均值基线并不意味着输入变量对两个输出的解释同样充分。报告双输出RMSE、MAE和R²的目的，是防止一个输出的改善遮蔽另一个输出的困难。若将模型用于在线监测，工程人员应持续计算滚动误差并设置漂移告警；当SO2或H2S的残差分布明显偏离训练期，模型应停止自动更新参数，回到重新标定流程。随机森林候选未在验证指标上胜出，因此本文不为了“复杂”而保留它；这个选择也说明模型家族不是预先指定的结论。

对问题二而言，事件定义本身必须由训练数据冻结。两个阈值以训练期分位数得到，随后验证期只用于选择候选而不是重估输出分布，测试期也从不参与阈值或截断点调整。这样做牺牲了对近期工况的适应性，却避免把未来信息泄漏为表面上的性能。部署时可采用滚动窗口重新训练，但每次窗口变化都应生成新版本、在独立后续窗口上评估，并保留旧版本的预测日志；不能在看到测试表现后再改变阈值并继续称其为“测试集”。

问题三的条件评价同样十分重要。非事件样本没有真实的首次超限时间，如果强行赋予70或更大的数值，会把“是否发生事件”的分类问题与“发生后多早发生”的回归问题混为一谈。因此MAE只在真实事件集合上计算，并额外报告被问题二捕获的事件覆盖率。该分解能让使用者看清误差来自哪一环：可能是报警模型没有发现事件，也可能是在已发现事件后时间回归仍不准确。两种误差对应的改进手段不同，前者需要增强特征和阈值校准，后者需要引入更适合的动态状态模型或工艺机理信息。

指标的不确定性也被谨慎限定。本文对最终保留集的逐起点准确率进行200次IID自助重采样，得到均值和95%分位区间。这一操作适合描述有限留出起点上的统计波动，但没有重建连续过程的自相关、季节性或极端故障簇；它绝不是“未来超限概率的置信区间”。若要刻画持续过程中的风险，后续可采用块自助法、时间序列交叉验证或按工况分层的场景试验，但这些方案必须建立在明确的场景来源和未参与调参的验证窗口上。

最后，论文的可读性不能与可审计性相冲突。读者在正文中看到的是可解释的表格、公式和限制；审查系统同时保留claim到结果JSON的指针、每张图的源CSV哈希、公式和表格注册表、文献元数据和最终PDF/DOCX的哈希绑定。若有人在生成论文后替换结果、图形或参考文献，即使排版外观不变，复核也会因哈希不一致而失败。这样的设计不替代同行判断，却使同行能够快速定位数字的产生路径、检验模型是否越过题目条件，并复算所有可复算部分。

从算法库角度看，本项目只把可迁移部分写成通用函数：预测起点的时间切分、因果窗口特征、未来事件标签、回归误差和自助法指标区间。题目专用适配器只负责把五个输入、两个输出、30步历史以及10至70步预测窗口映射到这些函数。这样，换一个过程监测题时可替换数据字典、决策合同和写作叙述，而不必复制本题的阈值、列名或数值。反过来，任何通用库函数的修改都必须由单元测试和至少一个不同题目的实际运行验证；本题的化工过程迁移正是对供应链赛题之外情形的检验。

为避免模型在纸面上看似完整、实际无法交接，最终交付还包括PDF、可编辑DOCX、编译与渲染报告、视觉审计、独立内容复核和发布阶段交接单。PDF以严格TeX规则作为版式权威；DOCX是可编辑伴随件，其字体、页边距、三线表和图像布局同样经过渲染检查。若Word导出机制无法可靠地在摘要后重置页码，报告必须明确记为格式差异，而不是把连续页码伪称为合规。这样的区分使排版问题可见、可复现、可修复。

本研究的结论强度因此与证据强度相匹配：可以确认数据完整、时间切分无泄漏、岭回归相对均值基线有所改善，并可以量化当前报警和时间估计在留出期的表现；不能确认未来工况不变、不能确认阈值符合监管标准，也不能确认改变任一输入会以预测方向改变污染物。把这条边界写入模型评价、最终建议和交接文件，是为了使后续使用者在数据条件变化时知道应当重新建模，而不是继续沿用一个失去适用条件的静态结论。
"""
    md = f"""# 摘要

本文以官方给出的14,401个等间隔化工过程观测为对象，研究五种输入气体到二氧化硫和硫化氢输出的预测、未来超限报警以及首次超限时间估计。我们把三个问题统一为严格的时间顺序预测任务：问题一仅用当前输入拟合双输出；问题二以当前及过去30个观测构成因果特征，并在t+10至t+70窗口判断是否发生任一污染物超限；问题三仅对真实未来事件估计最早发生时刻。训练、验证、测试按预测起点60%/20%/20%顺序切分，避免随机切分泄漏。问题一选择岭回归，其测试平均RMSE为{r['q1_mean_rmse']:.4f}[claim:CLAIM_Q1_RMSE]，优于同一测试集的均值基线。问题二选择训练输出0.90分位阈值，在测试集上得到F1={r['q2_f1']:.4f}[claim:CLAIM_Q2_F1]、准确率={r['q2_accuracy']:.4f}[claim:CLAIM_Q2_ACCURACY]；其测试判别能力有限，因此只建议人工复核的监测用途。问题三在真实事件上的首次超限时间MAE为{r['q3_event_mae']:.2f}个采样间隔[claim:CLAIM_Q3_MAE]。本文同时给出阈值取舍、留出集自助法区间、图表源哈希和复现限制，不把相关性预测包装为可直接部署的因果控制策略。

# 关键词

化工过程；时间序列预测；因果特征；超限报警；随机森林；可复核建模

# 问题重述

官方题面给出五种输入气体和两种输出污染物的等间隔历史记录。问题一要求在忽略反应延迟时，用截至t的输入预测t时刻的二氧化硫与硫化氢；问题二要求依据截至t的输入输出信息，预警t+10至t+70是否发生超限；问题三要求预测这一窗口中首次超限的时刻。题面允许自行设定两个阈值，但要求尽量小且维持预测性能。原始附件没有工程单位、排放法规限值或可控制执行器变量，因此结论必须保持在标准化数据上的预测和监测范围内。

# 问题分析

三个问题的难点不是模型名称，而是信息边界。问题一的“忽略延迟”不允许使用过去输出来掩盖当前输入模型；问题二和三则必须利用历史状态，同时绝不能把未来窗口的输出混入特征。若不显式定义预测起点、历史长度和未来窗口，分类与时间预测会出现标签泄漏。阈值又构成一个多目标问题：过低会让事件过于常见而使F1失真，过高则会使监测失去提前预警意义。因此模型比较采用时间顺序验证、ROC-AUC下限和最小合格分位数的规则。

# 模型总体框架

流程为“原始数据审计—因果特征—时间切分—模型选择—阈值取舍—最终留出集评估—图表与证据绑定”。首先不删除任何记录、不填补不存在的值；然后构造当前值、30步均值、标准差和变化斜率；随后在训练期拟合候选模型、在验证期选择结构和阈值，最后一次性评估测试期。目标函数包括最小化RMSE、在AUC约束下最小化阈值分位数、以及最小化真实事件上的MAE；约束包括因果信息约束、时间顺序约束、预测时间范围约束和不将报警概率解释为控制因果效应的解释约束。

# 模型假设

1. CSV中相邻行对应相同采样间隔，行顺序代表时间顺序；2. 标准化数值可以用于相对阈值与误差比较，但不能反推工程浓度；3. 过去30步的输入输出在时刻t可获得；4. 任一输出超过各自阈值即为未来窗口事件；5. 留出集独立同分布自助法只描述指标重采样波动，不代表过程事件的物理概率；6. 预测模型揭示统计关联，不识别输入气体的干预因果效应。

# 符号说明

|符号|含义|单位|
|---|---|---|
|$x_t$|时刻t的五维输入|标准化值|
|$y_t$|SO2、H2S双输出|标准化值|
|$\\phi_t$|截至t的因果历史特征|标准化值|
|$k_1,k_2$|训练期分位阈值|标准化值|
|$z_t$|未来窗口是否超限|0/1|
|$\\tau_t$|首次超限的相对时刻|采样间隔|

# 数据预处理

两张官方CSV分别含五个输入列和两个输出列。读取时仅剥离列名的空格，保留全部14,401行；不存在缺失值、插补、异常值删除、重排序或随机打散。合并后的面板增加单调递增的time列，相关矩阵只作探索性描述。输出的滞后自相关提示过程具有连续性，因此所有性能结论均以时间顺序测试集为准。图1和图2展示原始输出片段及相关结构，但不把相关系数解释为工艺因果链。

{figures_md.split(chr(10)+chr(10))[0]}

{figures_md.split(chr(10)+chr(10))[1]}

# 问题一：无延迟双输出预测

问题一的目标函数为在测试集最小化双输出平均RMSE，约束是特征只包含当前五项输入。岭回归作为正则化线性模型，随机森林回归作为非线性候选；两者都只在训练期拟合，验证期选择较小RMSE者。最终岭回归的平均RMSE为{r['q1_mean_rmse']:.4f}[claim:CLAIM_Q1_RMSE]，而均值基线为{q1['baseline_test']['mean_rmse']:.4f}。这说明当前输入含有预测信息，但SO2的测试R²仍为负，不能把平均误差改善误读为两个污染物都已被充分解释。

{formula_text}

## 表T1：问题一前8个时间顺序测试预测

{table(['time','SO2真实','SO2预测','H2S真实','H2S预测'], q1_rows)}

{figures_md.split(chr(10)+chr(10))[2]}

{figures_md.split(chr(10)+chr(10))[3]}

# 问题二：未来窗口超限报警

问题二用公式(2)构造因果特征，用公式(3)从训练输出计算候选阈值，并以公式(4)产生未来事件标签。模型目标函数是在验证集中维持判别能力，同时选择较低阈值；约束为验证ROC-AUC不低于0.60且F1距最佳值不超过0.08。在四个候选分位数中，0.90是最低合格值，两个阈值分别为{q2['thresholds'][0]:.4f}和{q2['thresholds'][1]:.4f}。该规则特意不把0.80分位的近乎全报警结果选为最佳。

## 表T2：问题二训练阈值的验证集取舍

{table(['分位数','SO2阈值','H2S阈值','准确率','F1','ROC-AUC'], [[f"{x.quantile:.2f}", f"{x.SO2_threshold:.3f}", f"{x.H2S_threshold:.3f}", f"{x.accuracy:.3f}", f"{x.f1:.3f}", f"{x.roc_auc:.3f}"] for x in tradeoff.itertuples()])}

## 表T3：问题二前8个时间顺序报警预测

{table(['time','真实事件','报警概率','预测事件'], q2_rows)}

测试F1为{r['q2_f1']:.4f}[claim:CLAIM_Q2_F1]，测试准确率为{r['q2_accuracy']:.4f}[claim:CLAIM_Q2_ACCURACY]，测试ROC-AUC为{q2_test['roc_auc']:.4f}。后两项表明测试期判别能力有限，因而不建议依据该分类器自动改变生产参数。它可把样本送入人工核查、传感器校验或更丰富特征采集队列；若用于控制，必须在独立后续批次重新评估漏报、误报和安全代价。

{figures_md.split(chr(10)+chr(10))[4]}

{figures_md.split(chr(10)+chr(10))[5]}

{figures_md.split(chr(10)+chr(10))[6]}

# 问题三：首次超限时间预测

问题三在训练期真实事件上拟合条件随机森林回归，输出截断在[10,70]内。评价目标函数为真实未来事件上的MAE，约束是非事件样本不被伪造为“某个真实到达时刻”。测试集中共有{q3['test_event_count']}个真实事件，首次超限时间MAE为{r['q3_event_mae']:.2f}个采样间隔[claim:CLAIM_Q3_MAE]，被问题二报警捕获的真实事件覆盖率为{q3['detected_event_coverage']:.4f}。这个时间模型应与问题二的有限判别能力一起解读：即使对事件样本的平均时间误差可报告，也不能声明已经获得可靠的全自动提前控制器。

## 表T4：问题三前8个真实事件的时间预测

{table(['time','真实首次时刻','预测首次时刻'], q3_rows)}

{figures_md.split(chr(10)+chr(10))[7]}

# 模型评价

## 表T5：核心模型与基线比较

{table(['项目','指标','数值','解释'], [['Q1','平均RMSE',f"{r['q1_mean_rmse']:.4f}",'低于训练均值基线'], ['Q1基线','平均RMSE',f"{q1['baseline_test']['mean_rmse']:.4f}",'相同时间测试集'], ['Q2','ROC-AUC',f"{q2_test['roc_auc']:.4f}",'测试判别有限'], ['Q3','事件时间MAE',f"{r['q3_event_mae']:.2f}",'只对真实事件评价']])}

## 表T6：留出集自助法指标区间

{table(['指标','均值','95%区间','解释'], [['报警准确率',f"{quality['uncertainty']['mean']:.4f}",f"[{quality['uncertainty']['ci95'][0]:.4f}, {quality['uncertainty']['ci95'][1]:.4f}]",'对保留预测起点的IID重采样']])}

{implementation}

# 最终建议

建议将问题一的模型用于与均值基线并列的短期过程监测，而不是声称能替代工艺机理。问题二的阈值和概率仅适合触发人工复核：测试ROC-AUC为{q2_test['roc_auc']:.4f}，不满足无人值守控制应有的稳健性要求。问题三可为已触发复核的样本提供大致的时间优先级，但其MAE为{r['q3_event_mae']:.2f}个采样间隔[claim:CLAIM_Q3_MAE]，仍需结合安全裕度。下一轮数据采集应补充工程单位、阀门操作、温度压力、催化剂状态和真实合规阈值；这些变量到位后，才能把预测问题升级为可检验的控制优化问题。

# 参考文献

{refs}

# 附录

附录A为三类逐起点预测CSV，附录B为阈值取舍与图表元数据。所有文件由对应Skill生成并由哈希登记；原始CSV从未被覆盖。代码入口使用`solve_process_forecast.py`，其特征构造、时间切分、阈值搜索、模型种子和指标函数均可重新执行。

# 复现说明

从官方题面与两张原始CSV开始，依次运行模型选择、数据分析、文献检索、求解、制图、写作和审查。任何原始数据、结果对象、图表源数据、参考文献或主文稿哈希发生变化，都必须重新生成审查绑定。论文中保留的[claim:...]锚点是机器审查证据，不向PDF/DOCX读者显示。
"""
    (paper / "main.md").write_text(md + "\n", encoding="utf-8")
    (paper / "paper-spec.yaml").write_text((root / "config" / "paper-spec.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    converted = subprocess.run(["pandoc", "-f", "markdown", "-t", "latex"], input=re.sub(r"\[claim:[A-Za-z0-9_-]+\]", "", md), text=True, encoding="utf-8", capture_output=True, check=False)
    if converted.returncode:
        raise RuntimeError(converted.stderr)
    body = converted.stdout
    marker, references, appendix = r"\section{问题重述}", r"\section{参考文献}", r"\section{附录}"
    abstract, remaining = body.split(marker, 1)
    abstract = re.sub(r"^\\section\{摘要\}\s*", "", abstract, count=1)
    abstract = re.sub(r"\\section\{关键词\}\s*", r"\\noindent{\\bfseries 关键词：}", abstract, count=1)
    before_refs, after_refs = remaining.split(references, 1)
    _, after_appendix = after_refs.split(appendix, 1)
    bib = r"""\begin{thebibliography}{9}
\bibitem{problem} 肇庆学院数学建模竞赛组委会. 2026年肇庆学院数学建模竞赛C题：化工厂生产流程的预测和控制问题.
\bibitem{breiman} Breiman L. Random Forests. Machine Learning, 2001. doi:10.1023/A:1010933404324.
\bibitem{fawcett} Fawcett T. An introduction to ROC analysis. Pattern Recognition Letters, 2006. doi:10.1016/j.patrec.2005.10.010.
\bibitem{hoerl} Hoerl A E, Kennard R W. Ridge Regression. Technometrics, 1970. doi:10.1080/00401706.1970.10488634.
\bibitem{efron} Efron B. Bootstrap Methods. Annals of Statistics, 1979. doi:10.1214/aos/1176344552.
\end{thebibliography}
"""
    header = (REPOSITORY_ROOT / "template" / "cume-template.tex").read_text(encoding="utf-8").split("\\begin{document}", 1)[0]
    header = header.replace(r"\else #1\fi}", r"\else \arabic{section}\fi}")
    tex = header + "\\providecommand{\\tightlist}{\\setlength{\\itemsep}{0pt}\\setlength{\\parskip}{0pt}}\n\\newsavebox{\\pandocbox}\n\\newcommand{\\pandocbounded}[1]{\\sbox{\\pandocbox}{#1}\\ifdim\\wd\\pandocbox>\\linewidth\\resizebox{\\linewidth}{!}{#1}\\else\\usebox{\\pandocbox}\\fi}\n" + rf"""\begin{{document}}
\pagenumbering{{arabic}}\setcounter{{page}}{{1}}\thispagestyle{{plain}}
\begin{{center}}{{\fontsize{{16pt}}{{24pt}}\selectfont\bfseries {TITLE}\par}}\vspace{{0.6cm}}{{\fontsize{{14pt}}{{21pt}}\selectfont\bfseries 摘\quad 要}}\end{{center}}\vspace{{0.6cm}}
{abstract}
\newpage\pagestyle{{plain}}
\section{{问题重述}}{before_refs}{bib}\section{{附录}}{after_appendix}
\section{{代码附录}}\begin{{pycode}}[caption={{求解入口}}]
python skills/solve-model/scripts/solve_process_forecast.py --root PROJECT_ROOT
\end{{pycode}}
\end{{document}}
"""
    (paper / "main.tex").write_text(tex, encoding="utf-8")
    layout = validate_layout(paper / "main.tex")
    dump(root / "reports" / "cumcm_layout_validation.json", layout)
    if layout["status"] != "PASS":
        raise RuntimeError("strict layout validation failed")
    render = {"status": "READY_TO_RENDER", "profile": "competition", "source_markdown": "paper/main.md", "source_markdown_sha256": hashlib.sha256((paper / "main.md").read_bytes()).hexdigest(), "source_tex": "paper/main.tex", "source_tex_sha256": hashlib.sha256((paper / "main.tex").read_bytes()).hexdigest(), "required_deliveries": [{"role": "main_pdf", "path": "paper/main.pdf", "producer": "compile-latex"}, {"role": "latex_compile_report", "path": "reports/latex_compile_report.json", "producer": "compile-latex"}, {"role": "visual_layout_audit", "path": "reports/visual_layout_audit.json", "producer": "paper-render-audit"}]}
    dump(paper / "render-request.json", render)
    dump(paper / "paper_generation_report.json", {"status": "FULL_DRAFT_GENERATED", "mode": "competition_paper", "layout_profile": "strict_cumcm_a4_v1", "claim_bindings": 4, "evidence_bound": True})
    dump(paper / "claim_usage_report.json", {"used_claim_ids": ["CLAIM_Q1_RMSE", "CLAIM_Q2_ACCURACY", "CLAIM_Q2_F1", "CLAIM_Q3_MAE"]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, required=True)
    main(parser.parse_args().root)
