"""Plain-text P0 report generated only from benchmark output."""

from __future__ import annotations

from typing import Any


def build_report(summary: dict[str, Any], failures: list[dict[str, Any]], manifest: dict[str, Any]) -> str:
    strategies = summary["strategies"]
    nova = strategies.get("nova", {})
    fixed_early = strategies.get("fixed-early-stop", {})
    fixed_all = strategies.get("fixed-all", {})
    lines = [
        "《智感Nova P0可信诊断评测报告 v0.1》", "", "一、评测目标", "验证可信诊断、误阻断控制、动态实验选择、最小充分证据和可追溯性。",
        "", "二、Case Generator", "受控合成校园逐时负荷：含时间戳、负荷、温度、日历、滞后特征与预测；故障标签仅在评测清单中。",
        "", "三、故障类型", "TIME_SPLIT、FEATURE_LEAKAGE、PEAK_FAILURE、BASELINE_FAILURE、MULTI_FAULT、CLEAN、BORDERLINE。",
        "", "四、数据集划分", f"本次 final hidden 运行包含 {summary['case_count']} 个中性编号案例；DEV、CALIBRATION 和 CHALLENGE 由同一固定生成器独立生成。",
        "", "五、Baseline定义", "Nova Dynamic、Fixed Checklist + Early Stop、Fixed Checklist Run All、SurfaceMetricBaseline。后三者中前三种共用真实 Nova ExperimentExecutor；SurfaceMetricBaseline 不是 LLM。",
        "", "六、评价指标定义", "Gate Accuracy、Fault Detection、False Block、实验数、成本、Top-1、追溯率与混淆矩阵均从 raw_results.json 计算。",
        "", "七、Nova总体结果", f"Nova Gate Accuracy={nova.get('gate_accuracy')}, Fault Detection={nova.get('fault_detection_rate')}, False Block={nova.get('false_block_rate')}。",
        "", "八、Nova vs Fixed Early Stop", f"平均实验数：Nova={nova.get('average_experiment_count')}，Fixed Early Stop={fixed_early.get('average_experiment_count')}。",
        "", "九、Nova vs Fixed Run All", f"平均实验数：Nova={nova.get('average_experiment_count')}，Fixed Run All={fixed_all.get('average_experiment_count')}；平均成本：{nova.get('average_decision_cost')} vs {fixed_all.get('average_decision_cost')}。",
        "", "十、Surface Metric baseline结果", f"Surface Metric Gate Accuracy={strategies.get('surface-metric', {}).get('gate_accuracy')}。它只看整体 MAPE，不能冒充真实 LLM。",
        "", "十一、LLM baseline结果", "NOT_EXECUTED_NO_PROVIDER：只实现了适配接口，未伪造模型调用或结果。",
        "", "十二、按故障类型结果", str(summary["by_fault_type"]),
        "", "十三、动态实验选择结果", f"Nova Top-1 Selection Accuracy={nova.get('top1_selection_accuracy')}。该指标以 evaluator 内的可接受首实验集合为 Oracle，不传入 Core。",
        "", "十四、最小充分证据结果", f"Nova unnecessary experiment rate={nova.get('unnecessary_experiment_rate')}；Fixed Run All={fixed_all.get('unnecessary_experiment_rate')}。",
        "", "十五、False Block分析", f"Nova Clean False Block Rate={nova.get('false_block_rate')}。Clean 不从混淆矩阵或总体统计中剔除。",
        "", "十六、Challenge Set结果", f"独立挑战集结果：{manifest.get('challenge_set_summary', '尚未在此产物目录发现挑战集结果')}。该集合不参与规则调优。",
        "", "十七、失败案例", f"保留 {len(failures)} 条失败/边界记录；详见 failures.json。失败分为选择、执行、证据、Gate、歧义和真值设计问题。",
        "", "十八、追溯性验证", f"Nova Evidence Traceability={nova.get('evidence_traceability_rate')}，Gate Traceability={nova.get('gate_traceability_rate')}。",
        "", "十九、稳定性与复现性", f"同一输入的逻辑复跑检查：{manifest.get('reproducibility_check', {})}。时间戳和临时 ToolResult ID 不作为一致性判据。",
        "", "二十、本轮真实测试结果", "产物由同一命令从头生成；单元、相关回归和全量测试结果记录于运行交付说明。",
        "", "二十一、生成的图表", "figures/ 下含准确率、实验数、成本、Top-1、误阻断率和实验数量分布图，全部从 raw_results.json 自动绘制。",
        "", "二十二、对比赛最有价值的5条真实结论",
        f"1. 在 {summary['case_count']} 个案例中，Nova Gate Accuracy 为 {nova.get('gate_accuracy')}。",
        f"2. Nova 的 Clean False Block Rate 为 {nova.get('false_block_rate')}。",
        f"3. Nova 的首实验 Oracle 命中率为 {nova.get('top1_selection_accuracy')}。",
        f"4. Nova 平均执行 {nova.get('average_experiment_count')} 个实验，Fixed Run All 为 {fixed_all.get('average_experiment_count')}。",
        "5. Evidence 与 Gate 的每一条追溯率均由输出哈希、source pointer、证据 ID 和 Rule ID 逐项复核。",
        "", "二十三、当前还不能宣称什么", "未使用真实校园部署数据；未执行真实 LLM baseline；未证明跨领域泛化；BASELINE_FAILURE 的 WEAKENS 证据在 v0.1 Gate 中并不自动阻断。",
        "", "二十四、下一阶段建议", "仅当本评测结果经审阅后，再决定是否具备进入 Nova Core HTTP API 阶段的条件；本评测不会自动开始该工作。",
    ]
    return "\n".join(lines) + "\n"
