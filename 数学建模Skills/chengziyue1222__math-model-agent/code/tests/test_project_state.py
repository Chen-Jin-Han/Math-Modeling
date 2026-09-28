import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills" / "run-modeling-project" / "scripts" / "project_state.py"
SPEC = importlib.util.spec_from_file_location("project_state", SCRIPT)
project_state = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(project_state)


def _evidence(root, role, relative, content="verified"):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"{role}={relative}"


def test_project_state_advances_one_verified_gate_at_a_time(tmp_path):
    state = project_state.initialize(tmp_path, "case-2026-a", "run-manifest.json", "audit")
    assert state["current_stage"] == "intake"
    evidence = [
        _evidence(tmp_path, "problem_source", "docs/source.md"),
        _evidence(tmp_path, "task_decomposition", "docs/tasks.md"),
    ]

    state = project_state.advance(tmp_path, "analysis", evidence, "problem parsed")

    assert state["current_stage"] == "analysis"
    assert state["completed_stages"] == ["intake"]
    assert set(state["evidence"]) == {"problem_source", "task_decomposition"}
    assert len(state["evidence"]["problem_source"]["sha256"]) == 64


def test_gate_rejects_skips_missing_files_and_missing_roles(tmp_path):
    project_state.initialize(tmp_path, "case", "run-manifest.json", "audit")
    with pytest.raises(ValueError, match="exactly one stage"):
        project_state.advance(tmp_path, "modeling", [], "")
    with pytest.raises(FileNotFoundError, match="evidence file"):
        project_state.advance(
            tmp_path,
            "analysis",
            ["problem_source=missing.md", "task_decomposition=missing2.md"],
            "",
        )
    one = _evidence(tmp_path, "problem_source", "source.md")
    with pytest.raises(ValueError, match="task_decomposition"):
        project_state.advance(tmp_path, "analysis", [one], "")


def test_block_resume_and_handoff_preserve_history(tmp_path):
    project_state.initialize(tmp_path, "case", "run-manifest.json")
    blocked = project_state.block(tmp_path, "missing source", "obtain official data")
    assert project_state.handoff(blocked)["status"] == "blocked"
    with pytest.raises(ValueError, match="active blocker"):
        project_state.advance(tmp_path, "analysis", [], "")

    resumed = project_state.resume(tmp_path)

    assert resumed["active_blocker"] is None
    assert resumed["blocker_history"][0]["resolved_at"] is not None
    assert project_state.handoff(resumed)["status"] == "active"


def test_manifest_gate_requires_configured_manifest_path(tmp_path):
    state = project_state.initialize(tmp_path, "case", "records/run-manifest.json")
    state["current_stage"] = "modeling"
    project_state._write_state(tmp_path, state)
    evidence = [
        _evidence(tmp_path, "implementation", "src/solve.py"),
        _evidence(tmp_path, "machine_results", "results/results.json"),
        _evidence(tmp_path, "quality_validation", "results/quality.json"),
        _evidence(tmp_path, "run_manifest", "run-manifest.json"),
    ]
    with pytest.raises(ValueError, match="configured path"):
        project_state.advance(tmp_path, "validation", evidence, "")


def test_advance_rejects_mutated_evidence_from_previous_gate(tmp_path):
    project_state.initialize(tmp_path, "case", "run-manifest.json", "audit")
    source = _evidence(tmp_path, "problem_source", "docs/source.md", "original")
    tasks = _evidence(tmp_path, "task_decomposition", "docs/tasks.md")
    project_state.advance(tmp_path, "analysis", [source, tasks], "")
    (tmp_path / "docs" / "source.md").write_text("mutated", encoding="utf-8")
    next_evidence = [
        _evidence(tmp_path, "data_audit", "results/data.json"),
        _evidence(tmp_path, "model_selection", "results/model.json"),
        _evidence(tmp_path, "decision_contract", "results/contract.json"),
    ]
    with pytest.raises(ValueError, match="previous gate evidence is stale"):
        project_state.advance(tmp_path, "modeling", next_evidence, "")


def test_verify_evidence_reports_missing_or_changed_files(tmp_path):
    state = project_state.initialize(tmp_path, "case", "run-manifest.json", "audit")
    evidence = [
        _evidence(tmp_path, "problem_source", "source.md"),
        _evidence(tmp_path, "task_decomposition", "tasks.md"),
    ]
    state = project_state.advance(tmp_path, "analysis", evidence, "")
    assert project_state.verify_evidence(tmp_path, state) == []
    (tmp_path / "tasks.md").unlink()
    assert any("missing" in error for error in project_state.verify_evidence(tmp_path, state))


@pytest.mark.parametrize("unsafe", ["../state.json", "/tmp/state.json", "C:/state.json"])
def test_initialization_rejects_unsafe_manifest_path(tmp_path, unsafe):
    with pytest.raises(ValueError, match="safe project-relative"):
        project_state.initialize(tmp_path, "case", unsafe)


def test_competition_review_accepts_pdf_without_docx(tmp_path):
    state = project_state.initialize(tmp_path, "case", "run-manifest.json", "competition")
    state["current_stage"] = "writing"
    project_state._write_state(tmp_path, state)
    roles = list(project_state.COMPETITION_GATES["review"]) + ["main_pdf", "latex_compile_report"]
    evidence = [
        _evidence(tmp_path, role, "run-manifest.json" if role == "run_manifest" else f"evidence/{role}.json")
        for role in roles
    ]
    advanced = project_state.advance(tmp_path, "review", evidence, "PDF delivery")
    assert advanced["current_stage"] == "review"
    assert "main_docx" not in advanced["evidence"]


def test_audit_review_still_requires_full_audit_evidence(tmp_path):
    state = project_state.initialize(tmp_path, "case", "run-manifest.json", "audit")
    state["current_stage"] = "writing"
    project_state._write_state(tmp_path, state)
    roles = [role for role in project_state.AUDIT_GATES["review"] if role != "review_hash_binding"]
    evidence = [
        _evidence(tmp_path, role, "run-manifest.json" if role == "run_manifest" else f"evidence/{role}.json")
        for role in roles
    ]
    with pytest.raises(ValueError, match="review_hash_binding"):
        project_state.advance(tmp_path, "review", evidence, "missing audit binding")
