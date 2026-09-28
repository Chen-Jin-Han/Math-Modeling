import json
import sys
from pathlib import Path

from scripts.run_standard_skill import main as run_standard_skill
from scripts.skill_runtime import (
    STANDARD_SKILLS,
    finish_skill_run,
    register_external_artifact,
    start_skill_run,
    validate_skill_run,
)
from scripts.skill_contracts import CONTRACT_VERSION, contract_for, validate_terminal_run
from scripts.validate_skill_workflow import scan_project_scripts, validate_producers


def _write(root: Path, relative: str, text: str = "{}") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_runtime_records_start_finish_and_producer_hashes(tmp_path):
    _write(tmp_path, "input.json")
    _write(tmp_path, "results/result_object.json")
    start = start_skill_run(tmp_path, "case", "solve-model", inputs=[("selected_model_plan", "input.json")], profile="audit")
    finish_skill_run(tmp_path, start["run_id"], outputs=[("result_object", "results/result_object.json")])

    assert validate_skill_run(tmp_path, project_id="case", required_skills=["solve-model"]) == []
    registry = json.loads((tmp_path / "manifests" / "artifact-producers.json").read_text(encoding="utf-8"))
    assert registry[0]["producer_name"] == "solve-model"
    assert validate_producers(tmp_path) == []
    assert "filesystem_delta" in finish_skill_run(
        tmp_path,
        start_skill_run(tmp_path, "case", "solve-model", profile="audit")["run_id"],
        status="BLOCKED",
    )


def test_directory_backed_skill_has_stable_implementation_identity(tmp_path):
    _write(tmp_path, "skill/SKILL.md", "---\nname: test\n---\n")
    _write(tmp_path, "input.json")
    _write(tmp_path, "result.json")
    start = start_skill_run(
        tmp_path,
        "case",
        "solve-model",
        skill_path=tmp_path / "skill",
        inputs=[("selected_model_plan", "input.json")],
        profile="audit",
    )
    finish_skill_run(tmp_path, start["run_id"], outputs=[("result_object", "result.json")])
    registry = json.loads((tmp_path / "manifests" / "artifact-producers.json").read_text(encoding="utf-8"))
    assert len(start["skill_sha256"]) == 64
    assert start["contract_version"] == CONTRACT_VERSION
    assert registry[0]["producer_sha256"] == start["skill_sha256"]
    assert f"contract-{CONTRACT_VERSION}" in registry[0]["producer_version"]


def test_standard_runner_blocks_before_executing_incomplete_contract(tmp_path):
    for name in ("problem.md", "dictionary.json", "constraints.json", "goal.json"):
        _write(tmp_path, name)
    marker = tmp_path / "should-not-exist.txt"
    exit_code = run_standard_skill(
        [
            "--project-root",
            str(tmp_path),
            "--project-id",
            "case",
            "--skill",
            "select-model",
            "--skill-path",
            str(tmp_path),
            "--input",
            "official_problem=problem.md",
            "--input",
            "data_dictionary=dictionary.json",
            "--input",
            "constraint_summary=constraints.json",
            "--input",
            "project_goal=goal.json",
            "--",
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')",
        ]
    )
    assert exit_code == 1
    assert not marker.exists()


def test_runtime_records_created_and_modified_files(tmp_path):
    _write(tmp_path, "before.txt", "before")
    start = start_skill_run(tmp_path, "case", "solve-model", profile="audit")
    _write(tmp_path, "before.txt", "after")
    _write(tmp_path, "created.txt", "new")
    terminal = finish_skill_run(tmp_path, start["run_id"], status="BLOCKED")
    assert "before.txt" in terminal["filesystem_delta"]["modified"]
    assert "created.txt" in terminal["filesystem_delta"]["created"]


def test_runtime_blocks_tampered_filesystem_snapshot(tmp_path):
    start = start_skill_run(tmp_path, "case", "solve-model", profile="audit")
    snapshot = tmp_path / start["filesystem_snapshot_path"]
    snapshot.write_text('{"forged": true}', encoding="utf-8")
    errors = validate_skill_run(tmp_path, project_id="case")
    assert any("filesystem_snapshot_hash_mismatch" in error for error in errors)
    try:
        finish_skill_run(tmp_path, start["run_id"], status="BLOCKED")
    except ValueError as exc:
        assert "snapshot missing or tampered" in str(exc)
    else:
        raise AssertionError("tampered snapshot must block finish")


def test_external_render_producer_registration(tmp_path):
    _write(tmp_path, "paper/main.pdf", "%PDF-test")
    record = register_external_artifact(
        tmp_path,
        role="main_pdf",
        path="paper/main.pdf",
        producer_name="compile-latex",
        producer_version="xelatex-test",
    )
    assert record["producer_type"] == "external_tool"
    assert validate_producers(tmp_path) == []


def test_runtime_detects_tampered_trace_and_output(tmp_path):
    _write(tmp_path, "input.json")
    _write(tmp_path, "results/result_object.json")
    start = start_skill_run(tmp_path, "case", "solve-model", inputs=["input.json"], profile="audit")
    finish_skill_run(tmp_path, start["run_id"], outputs=[("result_object", "results/result_object.json")])
    _write(tmp_path, "results/result_object.json", '{"changed": true}')
    errors = validate_skill_run(tmp_path, project_id="case", required_skills=["solve-model"])
    assert any("output_hash_mismatch" in error for error in errors)
    trace = tmp_path / "manifests" / "skill-runs.jsonl"
    trace.write_text(trace.read_text(encoding="utf-8").replace("solve-model", "fake-skill", 1), encoding="utf-8")
    assert any("trace_signature_invalid" in error for error in validate_skill_run(tmp_path, project_id="case"))


def test_runtime_accepts_superseded_signed_run_but_checks_current_run(tmp_path):
    _write(tmp_path, "input.json", '{"version": 1}')
    _write(tmp_path, "results/result_object.json", '{"value": 1}')
    first = start_skill_run(tmp_path, "case", "solve-model", inputs=[("selected_model_plan", "input.json")], profile="audit")
    finish_skill_run(tmp_path, first["run_id"], outputs=[("result_object", "results/result_object.json")])
    _write(tmp_path, "input.json", '{"version": 2}')
    _write(tmp_path, "results/result_object.json", '{"value": 2}')
    second = start_skill_run(tmp_path, "case", "solve-model", inputs=[("selected_model_plan", "input.json")], profile="audit")
    finish_skill_run(tmp_path, second["run_id"], outputs=[("result_object", "results/result_object.json")])
    assert validate_skill_run(tmp_path, project_id="case", required_skills=["solve-model"]) == []


def test_runtime_requires_each_standard_skill(tmp_path):
    assert set(STANDARD_SKILLS) == {
        "run-modeling-project", "select-model", "analyze-model-data", "research-model-literature",
        "solve-model", "make-model-figures", "write-model-paper", "review-model-paper",
    }
    errors = validate_skill_run(tmp_path, project_id="case", required_skills=list(STANDARD_SKILLS))
    assert len([item for item in errors if item.startswith("missing_passed_skill_run")]) == 8


def test_bypass_scanner_flags_direct_paper_writes(tmp_path):
    _write(tmp_path, "run_project.py", "Path('main.tex').write_text('paper')\n")
    findings = scan_project_scripts(tmp_path)
    assert findings and findings[0]["code"] == "BYPASS_DETECTED"


def test_quality_evidence_roles_are_required_across_the_competition_pipeline():
    assert "decision_contract" in contract_for("select-model")["outputs"]
    assert "decision_contract" in contract_for("solve-model")["inputs"]
    assert "quality_validation" in contract_for("solve-model")["outputs"]
    assert "quality_validation" in contract_for("make-model-figures")["inputs"]
    assert {"decision_contract", "quality_validation"} <= set(contract_for("write-model-paper")["inputs"])
    assert {"decision_contract", "quality_validation"} <= set(contract_for("review-model-paper")["inputs"])
    assert "source_candidates" in contract_for("research-model-literature")["inputs"]
    assert {"retrieval_log", "metadata_verification", "relevance_evidence"} <= set(
        contract_for("research-model-literature")["outputs"]
    )
    assert {"cumcm_layout_validation", "render_request"} <= set(
        contract_for("write-model-paper")["outputs"]
    )
    competition_review = contract_for("review-model-paper", profile="competition")
    assert ("main_pdf", "main_docx") in competition_review["one_of_inputs"]
    assert "main_docx" not in competition_review["inputs"]
    assert "independent_content_review" not in competition_review["outputs"]
    assert "review_hash_binding" not in competition_review["outputs"]
    assert "submission_readiness" in competition_review["outputs"]
    audit_review = contract_for("review-model-paper", profile="audit")
    assert {"main_pdf", "main_docx", "docx_render_report"} <= set(audit_review["inputs"])
    assert {"independent_content_review", "review_hash_binding"} <= set(audit_review["outputs"])


def test_competition_trace_omits_audit_signature_and_registry(tmp_path):
    _write(tmp_path, "input.json")
    _write(tmp_path, "results/result_object.json")
    start = start_skill_run(
        tmp_path,
        "case",
        "solve-model",
        inputs=[("selected_model_plan", "input.json")],
        profile="competition",
    )
    terminal = finish_skill_run(
        tmp_path,
        start["run_id"],
        outputs=[("result_object", "results/result_object.json")],
    )
    assert "trace_signature" not in start
    assert "trace_signature" not in terminal
    assert not (tmp_path / "manifests" / "artifact-producers.json").exists()


def test_legacy_contract_run_is_not_reinterpreted_as_current_version():
    legacy = contract_for("research-model-literature", version="1.1")
    run = {
        "run_id": "legacy",
        "skill": "research-model-literature",
        "status": "PASS",
        "inputs": [{"role": role} for role in legacy["inputs"]],
        "outputs": [{"role": role} for role in legacy["outputs"]],
    }
    assert validate_terminal_run(run) == []


def test_v12_contract_run_remains_valid_after_v13_render_gates():
    legacy = contract_for("write-model-paper", version="1.2")
    run = {
        "run_id": "legacy-v12",
        "skill": "write-model-paper",
        "contract_version": "1.2",
        "status": "PASS",
        "inputs": [{"role": role} for role in legacy["inputs"]],
        "outputs": [{"role": role} for role in legacy["outputs"]],
    }
    assert validate_terminal_run(run) == []
