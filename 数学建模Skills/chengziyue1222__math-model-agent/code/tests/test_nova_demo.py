"""Regression checks for the local competition-demo adapters."""

from __future__ import annotations

from demo.cases import available_cases
from demo.reporting import diagnosis_markdown
from demo.run_demo import run_case


def test_fixed_demo_cases_reach_their_declared_gates(tmp_path) -> None:
    for case_id, case in available_cases().items():
        summary, full_run = run_case(case_id, tmp_path / case_id)
        assert summary["gate"]["decision"] == case.expected_gate
        assert full_run["gate_decisions"][-1]["decision"] == case.expected_gate
        assert summary["traceability"]["valid"] is True


def test_demo_report_only_renders_existing_nova_result(tmp_path) -> None:
    case = available_cases()["CASE-DEMO-002"]
    _, full_run = run_case(case.case_id, tmp_path / "blocked")
    report = diagnosis_markdown(case.title, full_run)
    assert "智感Nova诊断报告" in report
    assert "BLOCKED" in report
    assert "LEAKAGE_CHALLENGE" in report
    assert full_run["evidence"][0]["tool_result_id"] in report
