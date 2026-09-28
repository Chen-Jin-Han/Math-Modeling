"""Presentation-only renderers for existing Nova diagnosis results."""

from __future__ import annotations

import json
from typing import Any


_GATE_LABELS = {
    "BLOCKED": "阻断：不可进入高风险辅助研判",
    "NEEDS_REVIEW": "待复核：证据尚未闭合",
    "READY_FOR_REVIEW": "可复核：证据已闭合，仍需人工确认",
}
_DIRECTION_LABELS = {
    "SUPPORTS": "支持主张",
    "REFUTES": "构成反证",
    "INCONCLUSIVE": "尚无定论",
}


def _bullet_lines(items: list[str], empty: str = "- 无") -> list[str]:
    return [f"- {item}" for item in items] if items else [empty]


def diagnosis_markdown(case_title: str, full_run: dict[str, Any]) -> str:
    """Render existing Nova results; this function makes no diagnosis decision."""

    gate = full_run["gate_decisions"][-1]
    contract = full_run["decision_contract"]
    risks = full_run["risks"]
    experiments = full_run["experiments_executed"]
    evidence = full_run["evidence"]
    traceability = "有效" if all(item.get("source_hash") for item in evidence) else "待核验"
    evidence_summary = {
        direction: sum(item.get("direction") == direction for item in evidence)
        for direction in ("SUPPORTS", "REFUTES", "INCONCLUSIVE")
    }

    lines = [
        "# 智感Nova诊断报告",
        "",
        "> 本报告只整理本地 Nova Core 已生成的诊断结果；不重新执行实验，不虚构 Evidence，也不修改 Gate。",
        "",
        f"**案例：** {case_title}",
        f"**运行编号：** {full_run['run_id']}",
        "",
        "## 诊断摘要",
        f"- **最终 Gate：** {gate['decision']} — {_GATE_LABELS.get(gate['decision'], gate['decision'])}",
        f"- **判断原因：** {gate['reason']}",
        f"- **停止原因：** {full_run['stop_reason']}",
        f"- **证据概览：** 支持 {evidence_summary['SUPPORTS']} 条；反证 {evidence_summary['REFUTES']} 条；未定 {evidence_summary['INCONCLUSIVE']} 条。",
        "",
        "## DecisionContract",
        "```json",
        json.dumps(contract, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 风险识别",
    ]
    lines.extend(_bullet_lines([f"{item['risk_type']}（{item['severity']}）：{item['description']}" for item in risks]))
    lines.extend(["", "## 执行实验"])
    lines.extend(_bullet_lines([f"{item['experiment_type']}：{item['description']}" for item in experiments]))
    lines.extend(["", "## 关键证据"])
    lines.extend(_bullet_lines([
        f"{_DIRECTION_LABELS.get(item['direction'], item['direction'])}｜{item['observation']}（{item['metric']}={item['value']}；来源 {item['tool_result_id']}）"
        for item in evidence
    ]))
    lines.extend([
        "",
        "## 最终 Gate",
        f"**{gate['decision']}** — {_GATE_LABELS.get(gate['decision'], gate['decision'])}",
        "",
        f"- 原因：{gate['reason']}",
        f"- 触发规则：{', '.join(gate['triggered_rules'])}",
        f"- 剩余证据缺口：{', '.join(gate['remaining_gaps']) or '无'}",
        f"- Traceability：{traceability}；Evidence 数={len(evidence)}；ToolResult 数={len(full_run['tool_results'])}",
        "",
        f"- 停止原因：{full_run['stop_reason']}",
        "",
        "## 展示边界",
        "- READY_FOR_REVIEW 仅表示可进入人工复核，不代表自动批准或自动上线。",
        "- 本地演示不依赖服务器、公网、腾讯云账号或 DeepSeek Key。",
    ])
    return "\n".join(lines) + "\n"


def diagnosis_console_report(case_title: str, full_run: dict[str, Any]) -> str:
    """Render the compact terminal report from the Markdown report."""

    gate = full_run["gate_decisions"][-1]
    report = diagnosis_markdown(case_title, full_run)
    return "\n".join([
        "--------------------------------",
        report.rstrip(),
        "",
        f"最终Gate：{gate['decision']}",
        "--------------------------------",
    ])
