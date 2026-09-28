from __future__ import annotations

from algorithms.modeling_contracts import (
    records_to_bibtex,
    validate_contract_artifacts,
    validate_decision_contract,
    validate_quality_validation,
    validate_source_records,
)


def test_decision_contract_rejects_duplicate_and_incomplete_questions() -> None:
    issues = validate_decision_contract(
        {
            "questions": [
                {"id": "Q1", "result_artifact": "a.json", "validation_artifact": ""},
                {"id": "Q1", "result_artifact": "", "validation_artifact": "v.json"},
            ]
        }
    )
    ids = {issue["id"] for issue in issues}
    assert "decision_question_id_duplicate" in ids
    assert "result_artifact_missing" in ids
    assert "validation_artifact_missing" in ids


def test_contract_artifacts_are_verified_against_project_root(tmp_path) -> None:
    (tmp_path / "result.json").write_text("{}", encoding="utf-8")
    issues = validate_contract_artifacts(
        {
            "questions": [
                {
                    "id": "Q1",
                    "result_artifact": "result.json",
                    "validation_artifact": "missing.json",
                }
            ]
        },
        tmp_path,
    )
    assert any(issue["id"] == "decision_artifact_missing" for issue in issues)


def test_required_quality_evidence_must_pass() -> None:
    issues = validate_quality_validation(
        {"requirements": {"uncertainty_analysis_required": True, "baseline_comparison_required": True}},
        {"uncertainty": {"passed": False}},
    )
    assert {issue["id"] for issue in issues} == {"uncertainty_failed", "baseline_missing"}


def test_source_records_require_unique_verifiable_identifiers() -> None:
    records = [
        {"id": "a", "title": "One", "year": 2020, "type": "article", "doi": "10/x"},
        {"id": "b", "title": "Two", "year": 2021, "type": "article", "doi": "10/x"},
    ]
    issues = validate_source_records(records)
    assert any(issue["id"] == "source_identifier_duplicate" for issue in issues)
    rendered = records_to_bibtex(records[:1])
    assert "@article{a" in rendered
    assert "doi = {10/x}" in rendered


def test_retrieval_evidence_is_required_when_requested() -> None:
    issues = validate_source_records(
        [{"id": "a", "title": "One", "year": 2020, "type": "article", "doi": "10/x"}],
        require_retrieval_evidence=True,
    )
    ids = {issue["id"] for issue in issues}
    assert {
        "source_origin_invalid",
        "retrieval_provider_missing",
        "retrieval_timestamp_invalid",
        "source_not_fetched",
        "metadata_unverified",
        "relevance_evidence_missing",
    } <= ids
