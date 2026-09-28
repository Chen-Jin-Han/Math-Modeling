import json
import hashlib

from algorithms.adversarial_review import semantic_issues


def test_required_supplier_list_and_registry_completeness_are_enforced(tmp_path):
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "main.md").write_text("# result\nS001\n", encoding="utf-8")
    (paper_dir / "paper-spec.yaml").write_text("required_supplier_count: 50\n", encoding="utf-8")
    (paper_dir / "formula-registry.json").write_text(json.dumps([{"latex": "x"}]), encoding="utf-8")
    (paper_dir / "table-registry.json").write_text(json.dumps([{"data_file": "x"}]), encoding="utf-8")

    codes = {issue["code"] for issue in semantic_issues(tmp_path, paper_dir / "main.md")}

    assert "required_list_incomplete" in codes
    assert "formula_registry_incomplete" in codes
    assert "table_registry_incomplete" in codes


def test_decomposition_cannot_be_described_as_integrated_robust(tmp_path):
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "main.md").write_text("一体化鲁棒优化模型", encoding="utf-8")
    (tmp_path / "model_specification.json").write_text(json.dumps({"method": "decomposition"}), encoding="utf-8")

    codes = {issue["code"] for issue in semantic_issues(tmp_path, paper_dir / "main.md")}

    assert "model_claim_code_mismatch" in codes


def test_declared_decision_quality_requirements_fail_closed(tmp_path):
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "main.md").write_text("# paper", encoding="utf-8")
    (tmp_path / "decision_contract.json").write_text(
        json.dumps({
            "questions": [{
                "id": "planning",
                "result_artifact": "results/plan.csv",
                "validation_artifact": "reports/validation.json",
                "requires_dynamic_state": True,
                "requires_uncertainty": True,
                "requires_tradeoff": True,
                "requires_baseline": True,
            }]
        }),
        encoding="utf-8",
    )
    (tmp_path / "model_specification.json").write_text(json.dumps({"variables": ["x"]}), encoding="utf-8")
    (tmp_path / "quality_validation.json").write_text(json.dumps({"uncertainty": {"mode": "deterministic"}}), encoding="utf-8")

    codes = {issue["code"] for issue in semantic_issues(tmp_path, paper_dir / "main.md")}

    assert {"multi_period_state_missing", "uncertainty_evidence_missing", "tradeoff_evidence_missing", "baseline_comparison_missing"} <= codes


def test_declared_decision_quality_requirements_accept_complete_evidence(tmp_path):
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "main.md").write_text("# paper", encoding="utf-8")
    (tmp_path / "decision_contract.json").write_text(
        json.dumps({
            "questions": [{
                "id": "planning",
                "result_artifact": "results/plan.csv",
                "validation_artifact": "reports/validation.json",
                "requires_dynamic_state": True,
                "requires_uncertainty": True,
                "requires_tradeoff": True,
                "requires_baseline": True,
            }]
        }),
        encoding="utf-8",
    )
    (tmp_path / "model_specification.json").write_text(json.dumps({"state_variables": ["inventory"], "balance_constraints": ["I[t+1]=I[t]+in-out"]}), encoding="utf-8")
    (tmp_path / "quality_validation.json").write_text(
        json.dumps({
            "uncertainty": {"mode": "scenario", "scenario_source": "held-out history", "holdout_or_stress_evidence": "reports/stress.json"},
            "multiobjective": {"strategy": "epsilon_constraint", "tradeoff_evidence": "results/frontier.csv"},
            "baseline_comparison": {"shared_inputs": True, "metrics": {"cost": 1.0}},
        }),
        encoding="utf-8",
    )

    codes = {issue["code"] for issue in semantic_issues(tmp_path, paper_dir / "main.md")}

    assert not {"multi_period_state_missing", "uncertainty_evidence_missing", "tradeoff_evidence_missing", "baseline_comparison_missing"} & codes


def test_hash_bound_second_pass_review_clears_only_the_anti_shallow_gate(tmp_path):
    paper_dir = tmp_path / "paper"
    reports = tmp_path / "reports"
    paper_dir.mkdir()
    reports.mkdir()
    manuscript = paper_dir / "main.md"
    manuscript.write_text("问题一\n问题二\n问题三\n问题四\n", encoding="utf-8")
    contract = tmp_path / "decision_contract.json"
    quality = tmp_path / "quality_validation.json"
    contract.write_text(json.dumps({"questions": []}), encoding="utf-8")
    quality.write_text(json.dumps({"uncertainty": {"passed": True}}), encoding="utf-8")
    checks = [
        {"id": item, "passed": True}
        for item in (
            "limitations_disclosed",
            "contract_artifacts_exist",
            "question_sections_present",
            "declared_quality_discussed",
            "quality_artifact_structured",
        )
    ]
    reports.joinpath("independent_review.json").write_text(json.dumps({
        "status": "PASS",
        "reviewer": "deterministic_second_pass_content_review_v1_1",
        "reviewed_path": "paper/main.md",
        "decision_contract_path": "decision_contract.json",
        "quality_validation_path": "quality_validation.json",
        "manuscript_sha256": hashlib.sha256(manuscript.read_bytes()).hexdigest(),
        "decision_contract_sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
        "quality_validation_sha256": hashlib.sha256(quality.read_bytes()).hexdigest(),
        "checks": checks,
    }), encoding="utf-8")

    codes = {issue["code"] for issue in semantic_issues(tmp_path, manuscript)}

    assert "REVIEW_SUSPICIOUSLY_SHALLOW" not in codes


def test_second_pass_review_is_invalidated_when_quality_artifact_changes(tmp_path):
    paper_dir = tmp_path / "paper"
    reports = tmp_path / "reports"
    paper_dir.mkdir()
    reports.mkdir()
    manuscript = paper_dir / "main.md"
    manuscript.write_text("问题一\n问题二\n问题三\n问题四\n", encoding="utf-8")
    contract = tmp_path / "decision_contract.json"
    quality = tmp_path / "quality_validation.json"
    contract.write_text(json.dumps({"questions": []}), encoding="utf-8")
    quality.write_text(json.dumps({"uncertainty": {"passed": True}}), encoding="utf-8")
    checks = [
        {"id": item, "passed": True}
        for item in (
            "limitations_disclosed",
            "contract_artifacts_exist",
            "question_sections_present",
            "declared_quality_discussed",
            "quality_artifact_structured",
        )
    ]
    reports.joinpath("independent_review.json").write_text(json.dumps({
        "status": "PASS",
        "reviewer": "deterministic_second_pass_content_review_v1_1",
        "reviewed_path": "paper/main.md",
        "decision_contract_path": "decision_contract.json",
        "quality_validation_path": "quality_validation.json",
        "manuscript_sha256": hashlib.sha256(manuscript.read_bytes()).hexdigest(),
        "decision_contract_sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
        "quality_validation_sha256": hashlib.sha256(quality.read_bytes()).hexdigest(),
        "checks": checks,
    }), encoding="utf-8")
    quality.write_text(json.dumps({"uncertainty": {"passed": False}}), encoding="utf-8")

    codes = {issue["code"] for issue in semantic_issues(tmp_path, manuscript)}

    assert "REVIEW_SUSPICIOUSLY_SHALLOW" in codes
