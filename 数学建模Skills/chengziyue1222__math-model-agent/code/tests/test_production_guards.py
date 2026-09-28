from algorithms.production_guards import (
    preflight_pdf, validate_artifact_registry, validate_figure_registry,
    validate_table_registry, validate_transition, validate_writing,
)


def test_registry_rejects_unverified_and_conflicting_results(tmp_path):
    artifact = tmp_path / "result.json"
    artifact.write_text("{}", encoding="utf-8")
    import hashlib
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    registry = {"artifacts": [
        {"path": "result.json", "role": "result", "sha256": digest, "verification_status": "unverified", "published_values": {"x": 1}},
        {"path": "result.json", "role": "result", "sha256": digest, "verification_status": "verified", "published_values": {"x": 2}},
    ]}
    issues = validate_artifact_registry(tmp_path, registry)
    assert {issue.rule_id for issue in issues} >= {"VAL-GATE-006", "VAL-GATE-012"}


def test_figure_and_table_contracts_are_checked(tmp_path):
    issues = validate_figure_registry(tmp_path, [{"figure_id": "F1"}])
    assert issues[0].rule_id == "FIG-GRAMMAR-001"
    table_issues = validate_table_registry([{"table_id": "T1", "title_position": "below", "vertical_rules": True}])
    assert {issue.rule_id for issue in table_issues} == {"TABLE-STYLE-001", "TABLE-SOURCE-001"}


def test_unsupported_strong_claim_is_warning_and_workflow_cannot_skip():
    assert validate_writing("The model is optimal.")[0].rule_id == "WRITE-SIGNIFICANT-001"
    assert not validate_writing("The model is optimal [claim:C1].")
    assert validate_transition("parse", "model_design", ["intake", "parse", "model_design"]) == []
    assert validate_transition("intake", "model_design", ["intake", "parse", "model_design"])[0].rule_id == "WF-STATE-001"


def test_pdf_preflight_missing_file_is_honest(tmp_path):
    result = preflight_pdf(tmp_path / "missing.pdf")
    assert result["status"] == "fail"
    assert result["issues"][0]["rule_id"] == "TEST-PDF-001"
