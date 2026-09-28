"""Single-page local Streamlit demonstration for Zhigan Nova."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "code"
for path in (PROJECT_ROOT, CODE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from demo.cases import DemoCase, available_cases, get_case
from demo.reporting import diagnosis_markdown
from nova_api.services import DiagnosisApiService


OUTPUT_ROOT = PROJECT_ROOT / "demo" / "outputs"
GATE_STYLE = {
    "BLOCKED": ("●", "阻断高风险辅助研判", "发现了不能带入高风险决策的反证。", "#C2413B", "#FFF1F0"),
    "NEEDS_REVIEW": ("●", "证据尚未闭合，进入人工复核", "没有直接反证，但关键证据缺口仍然存在。", "#A16207", "#FFF8E6"),
    "READY_FOR_REVIEW": ("●", "证据闭合，可进入人工复核", "可供人工判断，但不代表自动批准或自动上线。", "#15803D", "#ECFDF3"),
}
SEVERITY_LABELS = {"critical": "严重", "high": "高", "medium": "中", "low": "低"}
DIRECTION_LABELS = {"SUPPORTS": "支持主张", "REFUTES": "构成反证", "INCONCLUSIVE": "尚无定论"}


def _run_case(case_id: str) -> tuple[dict[str, object], dict[str, object]]:
    """Use the existing API service and retrieve the Core's complete result."""

    case = get_case(case_id)
    service = DiagnosisApiService(artifact_root=OUTPUT_ROOT)
    summary = service.run(case.request)
    full_run = service.get(str(summary["run_id"]), full=True)
    if full_run is None:
        raise RuntimeError("Nova run completed but its saved record could not be read.")
    return summary, full_run


def _show_gate(gate: dict[str, Any]) -> None:
    decision = str(gate["decision"])
    icon, label, explanation, color, background = GATE_STYLE.get(
        decision, ("●", decision, "请查看详细诊断结果。", "#475569", "#F1F5F9")
    )
    st.markdown(
        f"""<div class="nova-gate" style="border-left-color:{color};background:{background}">
        <h2 style="color:{color}">{icon} {decision}</h2>
        <p><strong>{label}</strong></p><p>{explanation}</p></div>""",
        unsafe_allow_html=True,
    )
    st.write(f"**Nova 的判断依据：** {gate['reason']}")
    st.caption("触发规则：" + "、".join(gate["triggered_rules"]))
    gaps = gate["remaining_gaps"]
    st.caption("剩余证据缺口：" + ("、".join(gaps) if gaps else "无"))


def _inject_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {max-width:1260px; padding-top:2.1rem; padding-bottom:2.5rem;}
        .nova-eyebrow {color:#2563EB; font-weight:700; font-size:.9rem; letter-spacing:.08em;}
        .nova-hero {font-size:2.35rem; font-weight:800; margin:.1rem 0 .35rem; color:#102A43;}
        .nova-subtitle {color:#486581; font-size:1.08rem; margin-bottom:1.15rem;}
        .nova-badge {display:inline-block; padding:.35rem .7rem; border-radius:999px; margin:.1rem .35rem .5rem 0; font-size:.86rem; font-weight:600; background:#EFF6FF; color:#1D4ED8;}
        .nova-card {border:1px solid #D9E2EC; border-radius:14px; padding:1rem 1.1rem; min-height:165px; background:#FFF;}
        .nova-card h4 {margin:0 0 .45rem;} .nova-card p {color:#486581; margin:.3rem 0; line-height:1.48;}
        .nova-flow {border:1px solid #D9E2EC; border-radius:12px; padding:.8rem .65rem; text-align:center; background:#F8FAFC; min-height:92px;}
        .nova-flow strong {display:block; color:#102A43; margin-bottom:.25rem;} .nova-flow small {color:#627D98;}
        .nova-gate {border-left:7px solid; border-radius:14px; padding:1.2rem 1.35rem; margin:.5rem 0 1rem;}
        .nova-gate h2 {margin:0 0 .35rem;} .nova-gate p {margin:.25rem 0; color:#243B53;}
        .nova-section-note {color:#627D98; margin-top:-.35rem; margin-bottom:.8rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _show_case_cards(cases: dict[str, DemoCase]) -> None:
    st.markdown("#### 固定比赛案例")
    for column, demo_case in zip(st.columns(3), sorted(cases.values(), key=lambda item: item.presentation_order)):
        _, _, _, color, _ = GATE_STYLE[demo_case.expected_gate]
        with column:
            st.markdown(
                f"""<div class="nova-card"><h4 style="color:{color}">{demo_case.presentation_label}</h4>
                <p><strong>{demo_case.title}</strong></p><p>{demo_case.summary}</p>
                <p><strong>展示重点：</strong>{demo_case.showcase_focus}</p></div>""",
                unsafe_allow_html=True,
            )


def _show_contract(contract: dict[str, Any]) -> None:
    target = str(contract.get("target", contract.get("decision_use", "未来 24 小时高负荷风险辅助研判")))
    horizon = str(contract.get("horizon_hours", contract.get("forecast_horizon_hours", 24)))
    first, second, third = st.columns(3)
    first.metric("研判对象", target)
    second.metric("预测时域", f"{horizon} 小时")
    third.metric("诊断模式", str(contract.get("mode", "diagnose")))
    with st.expander("查看原始 DecisionContract"):
        st.json(contract, expanded=False)


def _show_risks(risks: list[dict[str, Any]]) -> None:
    if not risks:
        st.success("未发现已记录风险。")
        return
    for risk in risks:
        severity = str(risk.get("severity", "unknown")).lower()
        st.markdown(
            f"**{SEVERITY_LABELS.get(severity, severity.upper())}｜{risk.get('risk_type', '风险')}**  \\\n+{risk.get('description', '无描述')}  \\\n+*决策影响：{risk.get('decision_impact', '未说明')}*"
        )


def _show_experiments(full_run: dict[str, Any]) -> None:
    trace = full_run["selection_trace"]
    for index, experiment in enumerate(full_run["experiments_executed"], start=1):
        selection = trace[index - 1] if index <= len(trace) else {}
        with st.container(border=True):
            st.markdown(f"**{index}. {experiment['experiment_type']}**")
            st.write(experiment["description"])
            first, second, third = st.columns(3)
            first.caption("目标缺口：" + "、".join(experiment.get("target_gap_ids", [])))
            second.caption(f"信息增益：{experiment.get('expected_information_gain', '未记录')}")
            third.caption("选择理由：" + str(selection.get("selection_reason", "由 Nova Core 选择")))
    with st.expander("查看完整实验选择轨迹"):
        st.dataframe(trace, use_container_width=True, hide_index=True)


def _show_evidence(evidence: list[dict[str, Any]]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in evidence:
        grouped[str(item.get("direction", "INCONCLUSIVE"))].append(item)
    for direction in ("REFUTES", "SUPPORTS", "INCONCLUSIVE"):
        items = grouped.get(direction, [])
        if not items:
            continue
        st.markdown(f"**{DIRECTION_LABELS[direction]}（{len(items)} 条）**")
        for item in items:
            st.markdown(
                f"- `{item['experiment_id']}` → `{item['tool_result_id']}` → **{item['observation']}**  \\\n+  指标：`{item['metric']}` = `{item['value']}`；置信度：`{item['confidence']}`"
            )
    with st.expander("查看完整 Evidence 字段与溯源哈希"):
        st.dataframe(evidence, use_container_width=True, hide_index=True)


def _show_traceability(summary: dict[str, Any], full_run: dict[str, Any]) -> None:
    trace = summary["traceability"]
    first, second, third = st.columns(3)
    first.metric("追溯校验", "有效" if trace["valid"] else "失败")
    second.metric("Evidence", trace["evidence_count"])
    third.metric("ToolResult", trace["tool_result_count"])
    st.caption(f"运行编号：{full_run['run_id']}｜停止原因：{full_run['stop_reason']}")


st.set_page_config(page_title="智感Nova｜可信诊断", page_icon="◈", layout="wide")
_inject_style()
st.markdown('<div class="nova-eyebrow">ZHIGAN NOVA · LOCAL COMPETITION DEMO</div>', unsafe_allow_html=True)
st.markdown('<div class="nova-hero">智感Nova</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="nova-subtitle">校园负荷预测模型可信诊断智能体：在模型进入未来 24 小时高风险辅助研判前，核验其是否具备可信证据。</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<span class="nova-badge">本地离线运行</span><span class="nova-badge">不依赖公网或云端</span><span class="nova-badge">真实结果由 Nova Core 生成</span>',
    unsafe_allow_html=True,
)

cases = available_cases()
_show_case_cards(cases)
st.divider()
st.markdown("### 开始演示")
st.caption("推荐答辩顺序：先展示 BLOCKED 的泄漏风险，再展示 READY_FOR_REVIEW 与 NEEDS_REVIEW 的不同证据边界。")
ordered_ids = [item.case_id for item in sorted(cases.values(), key=lambda item: item.presentation_order)]
selected_id = st.selectbox(
    "选择固定演示案例",
    options=ordered_ids,
    format_func=lambda item: f"{item}｜{cases[item].presentation_label}｜{cases[item].title}",
)
case = cases[selected_id]
st.info(f"**本案例要让评委看到：** {case.judge_takeaway}")

actions, reset = st.columns([4, 1])
with actions:
    start = st.button("开始可信诊断", type="primary", use_container_width=True)
with reset:
    if st.button("重置", use_container_width=True):
        st.session_state.pop("nova_result", None)
        st.rerun()

if start:
    with st.spinner("Nova Core 正在选择实验、执行核验并构建证据链……"):
        try:
            summary, full_run = _run_case(selected_id)
        except Exception as exc:
            st.error(f"诊断执行失败：{type(exc).__name__}: {exc}")
        else:
            st.session_state["nova_result"] = (case, summary, full_run)

if "nova_result" not in st.session_state:
    st.caption("选择案例后点击“开始可信诊断”。所有计算均在本机完成。")
    st.stop()

case, summary, full_run = st.session_state["nova_result"]
gate = full_run["gate_decisions"][-1]

st.divider()
st.markdown("### 可信诊断结果")
_show_gate(gate)

st.markdown("#### 从研判契约到 Gate 的真实证据链")
for column, title, subtitle in zip(
    st.columns(5),
    ("DecisionContract", "Risk", "Experiment", "Evidence", "Gate"),
    ("明确高风险研判边界", "识别可信性风险", "选择并执行核验", "保留可追溯结果", "给出受限决策"),
):
    with column:
        st.markdown(f'<div class="nova-flow"><strong>{title}</strong><small>{subtitle}</small></div>', unsafe_allow_html=True)

st.markdown("### 1. DecisionContract")
st.markdown('<p class="nova-section-note">Nova 先明确：要对什么预测用途做可信性判断。</p>', unsafe_allow_html=True)
_show_contract(full_run["decision_contract"])

st.markdown("### 2. Risk 风险识别")
st.markdown('<p class="nova-section-note">风险是后续实验与 Gate 判断的起点，而不是模型性能的替代指标。</p>', unsafe_allow_html=True)
_show_risks(full_run["risks"])

st.markdown("### 3. Experiment 实验选择与执行")
st.markdown('<p class="nova-section-note">以下实验由现有 Nova Core 选择和执行；界面只负责展示。</p>', unsafe_allow_html=True)
_show_experiments(full_run)

st.markdown("### 4. Evidence 证据链")
st.markdown('<p class="nova-section-note">每条证据均可回溯到对应实验与 ToolResult，不由页面虚构。</p>', unsafe_allow_html=True)
_show_evidence(full_run["evidence"])

st.markdown("### 5. Traceability 追溯校验")
_show_traceability(summary, full_run)

report = diagnosis_markdown(case.title, full_run)
st.markdown("### 导出诊断报告")
st.caption("报告整理已有 Nova 结果，不重新生成实验、Evidence 或 Gate。")
st.download_button(
    "下载 Markdown 诊断报告",
    data=report,
    file_name=f"zhigan-nova-{full_run['run_id']}.md",
    mime="text/markdown",
    use_container_width=True,
)

st.divider()
st.caption("智感Nova本地比赛演示版｜真实诊断由本地 Nova Core 完成｜READY_FOR_REVIEW 仅表示可进入人工复核，不代表自动批准。")
