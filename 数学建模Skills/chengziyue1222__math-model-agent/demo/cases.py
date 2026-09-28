"""Fixed, human-readable competition cases without diagnosis logic."""

from __future__ import annotations

from dataclasses import dataclass

from nova_api.adapters import demo_case
from nova_api.models import DiagnosisRequest


@dataclass(frozen=True)
class DemoCase:
    """Presentation metadata and an existing API-compatible request."""

    case_id: str
    title: str
    summary: str
    expected_gate: str
    request: DiagnosisRequest
    presentation_order: int
    presentation_label: str
    showcase_focus: str
    judge_takeaway: str


def _request_for_demo_case(case_id: str) -> DiagnosisRequest:
    return DiagnosisRequest(
        request_id=f"DEMO-{case_id}",
        domain="campus_load_forecast",
        mode="diagnose",
        input_type="demo_case",
        case_id=case_id,
        decision_context={
            "forecast_horizon_hours": 24,
            "decision_use": "high_load_risk_assessment",
        },
    )


def _needs_review_request() -> DiagnosisRequest:
    """Supply inconclusive stability inputs; Core still selects and gates."""

    baseline = demo_case("CASE-DEMO-001")
    return DiagnosisRequest(
        request_id="DEMO-NEEDS-REVIEW-001",
        domain="campus_load_forecast",
        mode="diagnose",
        input_type="structured_data",
        data={
            "actual_load": baseline.actual_load,
            "predicted_load": baseline.predicted_load,
            "split_strategy": "chronological",
            "feature_origin_offsets": [],
            "high_load_watch": False,
            "rolling_fold_errors": [1.0, 1.0, 2.0],
            "rolling_peak_errors": [1.0, 1.0, 2.0],
        },
        decision_context={
            "forecast_horizon_hours": 24,
            "decision_use": "high_load_risk_assessment",
        },
    )


def available_cases() -> dict[str, DemoCase]:
    """Return the three fixed cases shown in the competition demonstration."""

    return {
        "CASE-DEMO-001": DemoCase(
            case_id="CASE-DEMO-001",
            title="正常模型：证据闭合",
            summary="模型完成因果基线与高负荷子集核验，可进入人工复核。",
            expected_gate="READY_FOR_REVIEW",
            request=_request_for_demo_case("CASE-DEMO-001"),
            presentation_order=2,
            presentation_label="对照案例｜READY_FOR_REVIEW",
            showcase_focus="Nova 不会一律否定模型，证据闭合后才允许人工复核。",
            judge_takeaway="READY_FOR_REVIEW 不是自动批准；它表示关键证据闭合，可将结果交给人工研判。",
        ),
        "CASE-DEMO-002": DemoCase(
            case_id="CASE-DEMO-002",
            title="特征泄漏：阻断高风险研判",
            summary="发现未来时点特征，必须阻断模型进入高风险辅助研判。",
            expected_gate="BLOCKED",
            request=_request_for_demo_case("CASE-DEMO-002"),
            presentation_order=1,
            presentation_label="首演案例｜BLOCKED",
            showcase_focus="时间泄漏一旦成立，不能用高精度掩盖风险。",
            judge_takeaway="Nova 在风险进入决策前发现未来信息泄漏，并给出可追溯的阻断依据。",
        ),
        "NEEDS-REVIEW-001": DemoCase(
            case_id="NEEDS-REVIEW-001",
            title="指标稳定性待补证",
            summary="无直接反证，但滚动稳定性证据尚未闭合，应提交人工复核。",
            expected_gate="NEEDS_REVIEW",
            request=_needs_review_request(),
            presentation_order=3,
            presentation_label="灰区案例｜NEEDS_REVIEW",
            showcase_focus="证据不足不等于失败，需要保留不确定性并请求人工复核。",
            judge_takeaway="Nova 能区分“明确阻断”和“证据未闭合”，避免把灰区结果伪装成确定结论。",
        ),
    }


def get_case(case_id: str) -> DemoCase:
    cases = available_cases()
    try:
        return cases[case_id]
    except KeyError as exc:
        choices = ", ".join(cases)
        raise ValueError(f"Unknown demo case: {case_id}. Available: {choices}") from exc
