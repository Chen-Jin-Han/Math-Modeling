from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from algorithms.adversarial_review import semantic_issues
from algorithms.modeling_contracts import validate_source_records
from scripts.skill_runtime import validate_skill_run
from scripts.validate_adapter_boundaries import validate_adapter_boundaries
from scripts.validate_skill_workflow import (
    scan_project_scripts,
    validate_producers,
    validate_review_binding,
)


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_layout_validator():
    path = Path(__file__).resolve().parents[2] / "skills" / "write-model-paper" / "scripts" / "validate_cumcm_layout.py"
    spec = importlib.util.spec_from_file_location("mutation_layout_validator", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "source",
    [
        "Path('main.tex').write_text('paper')",
        "name = 'main' + '.tex'\nPath(name).write_text('paper')",
        "suffix = '.tex'\nname = f'main{suffix}'\nPath(name).write_text('paper')",
        "name = ''.join(['main', '.tex'])\nPath(name).write_text('paper')",
        "from pathlib import Path\nname = Path('paper') / ('main' + '.tex')\nname.write_text('paper')",
        "import os\nname = os.path.join('paper', 'main.tex')\nopen(name, 'w').write('paper')",
        "import subprocess\nsubprocess.run(['xel' + 'atex', 'paper/main.tex'])",
        "import subprocess\ncmd = ['pan' + 'doc', 'paper.md']\nsubprocess.Popen(cmd)",
        "from base64 import b64decode\npayload = b64decode('cGFwZXI=')",
        "paper = '''" + ("x" * 8_100) + "'''",
        "target = 'main.md'\nopen(target, 'a').write('paper')",
        "import subprocess\nname = 'tect' + 'onic'\nsubprocess.check_call([name, 'main.tex'])",
    ],
)
def test_twelve_bypass_mutations_are_detected(tmp_path, source):
    _write(tmp_path, "attack.py", source)
    assert any(item["code"] == "BYPASS_DETECTED" for item in scan_project_scripts(tmp_path))


def test_unregistered_formal_artifact_is_rejected(tmp_path):
    _write(tmp_path, "paper/main.pdf", "%PDF")
    assert "formal_artifact_unregistered: paper/main.pdf" in validate_producers(tmp_path)


def test_wrong_formal_role_is_rejected(tmp_path):
    _write(tmp_path, "paper/main.pdf", "%PDF")
    _write(
        tmp_path,
        "manifests/artifact-producers.json",
        json.dumps(
            [
                {
                    "path": "paper/main.pdf",
                    "role": "result_object",
                    "producer_name": "compile-latex",
                    "output_sha256": "wrong",
                }
            ]
        ),
    )
    errors = validate_producers(tmp_path)
    assert any("formal_artifact_role_mismatch" in error for error in errors)
    assert any("producer_output_hash_mismatch" in error for error in errors)


def test_repository_topic_adapters_respect_boundary_policy():
    root = Path(__file__).resolve().parents[2]
    assert validate_adapter_boundaries(root) == []


def test_semantic_mutation_direct_project_paper_is_detected(tmp_path):
    _write(tmp_path, "project.py", "from pathlib import Path\nPath('paper/main.tex').write_text('paper')")
    assert any(item["code"] == "BYPASS_DETECTED" for item in scan_project_scripts(tmp_path))


def test_semantic_mutation_deleted_skill_trace_is_detected(tmp_path):
    errors = validate_skill_run(tmp_path, project_id="mutation", required_skills=["select-model"])
    assert "missing_passed_skill_run: select-model" in errors


def test_semantic_mutation_result_changed_after_registration_is_detected(tmp_path):
    _write(tmp_path, "results/result_object.json", '{"value": 2}')
    _write(
        tmp_path,
        "manifests/artifact-producers.json",
        json.dumps(
            [
                {
                    "path": "results/result_object.json",
                    "role": "result_object",
                    "producer_name": "solve-model",
                    "output_sha256": hashlib.sha256(b'{"value": 1}').hexdigest(),
                }
            ]
        ),
    )
    assert "producer_output_hash_mismatch: results/result_object.json" in validate_producers(tmp_path)


def test_semantic_mutation_incomplete_top50_is_detected(tmp_path):
    _write(tmp_path, "paper/main.md", "# 问题一\nS001 S002 S003")
    _write(tmp_path, "paper/paper-spec.yaml", "required_supplier_count: 50\n")
    assert any(item["code"] == "required_list_incomplete" for item in semantic_issues(tmp_path, tmp_path / "paper/main.md"))


def test_semantic_mutation_generic_ctexart_layout_is_detected(tmp_path):
    tex = tmp_path / "main.tex"
    tex.write_text(r"\documentclass{ctexart}\begin{document}paper\end{document}", encoding="utf-8")
    assert _load_layout_validator().validate_layout(tex)["status"] == "FAIL"


def test_semantic_mutation_forged_doi_is_detected():
    record = {
        "id": "forged",
        "title": "Forged",
        "year": 2026,
        "type": "article",
        "doi": "10.1234/forged",
        "url": "https://doi.org/10.1234/different",
        "origin": "SEARCHED",
        "retrieval_provider": "Crossref",
        "retrieval_timestamp": "2026-07-26T12:00:00+08:00",
        "source_fetch_status": "FETCHED",
        "metadata_verification": {
            "status": "VERIFIED",
            "verified_identifier": "10.1234/forged",
            "evidence": "DOI resolver metadata",
        },
        "content_relevance_evidence": {"supports": "test", "location": "metadata"},
    }
    assert any(item["id"] == "source_doi_url_mismatch" for item in validate_source_records([record], require_retrieval_evidence=True))


def test_semantic_mutation_figure_source_swap_is_detected(tmp_path):
    _write(tmp_path, "paper/main.md", "# Paper\n![figure](../figures/a.pdf)")
    _write(tmp_path, "figures/a.pdf", "%PDF")
    _write(tmp_path, "results/source.csv", "new,data\n")
    figure_hash = hashlib.sha256((tmp_path / "figures/a.pdf").read_bytes()).hexdigest()
    stale_data_hash = hashlib.sha256(b"old,data\n").hexdigest()
    _write(
        tmp_path,
        "paper/figure-registry.json",
        json.dumps(
            [
                {
                    "figure_id": "F1",
                    "path": "figures/a.pdf",
                    "sha256": figure_hash,
                    "data_file": "results/source.csv",
                    "data_sha256": stale_data_hash,
                    "metadata": "figures/a.figure.json",
                    "inserted_in_body": True,
                }
            ]
        ),
    )
    assert any(item["code"] == "figure_source_hash_mismatch" for item in semantic_issues(tmp_path, tmp_path / "paper/main.md"))


def test_semantic_mutation_missing_independent_review_is_detected(tmp_path):
    _write(tmp_path, "paper/main.md", "# 完整论文\n问题一\n问题二\n问题三\n问题四\n局限性")
    questions = [
        {"id": f"Q{index}", "result_artifact": "results/result.json", "validation_artifact": "results/validation.json"}
        for index in range(1, 5)
    ]
    _write(tmp_path, "results/decision_contract.json", json.dumps({"questions": questions}))
    codes = {item["code"] for item in semantic_issues(tmp_path, tmp_path / "paper/main.md")}
    assert "REVIEW_SUSPICIOUSLY_SHALLOW" in codes


def test_semantic_mutation_q4_large_supplier_plan_without_feasibility_is_blocked(tmp_path):
    _write(tmp_path, "paper/main.md", "# 问题四\n建议使用全部供应商。")
    _write(tmp_path, "results/result_object.json", json.dumps({"solution": {"supplier_count": 402}}))
    issue = next(item for item in semantic_issues(tmp_path, tmp_path / "paper/main.md") if item["code"] == "implementation_risk_undiscussed")
    assert issue["severity"] == "blocking"


def test_semantic_mutation_claim_registry_changed_after_review_is_detected(tmp_path):
    _write(tmp_path, "paper/claim-registry.json", '[{"claim_id":"A"}]')
    original = hashlib.sha256((tmp_path / "paper/claim-registry.json").read_bytes()).hexdigest()
    _write(
        tmp_path,
        "reports/review_hash_binding.json",
        json.dumps(
            {
                "status": "PASS",
                "artifacts": {
                    "claim_registry": {
                        "path": "paper/claim-registry.json",
                        "sha256": original,
                    }
                },
            }
        ),
    )
    _write(tmp_path, "paper/claim-registry.json", '[{"claim_id":"B"}]')
    assert "review_binding_hash_mismatch: claim_registry" in validate_review_binding(tmp_path)


def test_semantic_mutation_adapter_absorbs_orchestration_is_detected(tmp_path):
    _write(tmp_path, "skills/select-model/scripts/plan_problem.py", "validate_decision_contract = True")
    _write(tmp_path, "skills/analyze-model-data/scripts/analyze_excel_inputs.py", "panel_diagnostics = True")
    _write(
        tmp_path,
        "skills/solve-model/scripts/solve_supplier_chain.py",
        "validate_state_balance = compare_policy_metrics = service_level_metrics = True\nskill_runtime = True",
    )
    _write(tmp_path, "skills/make-model-figures/scripts/render_supplier_figures.py", "export_publication_figure = True")
    _write(tmp_path, "skills/write-model-paper/scripts/write_supplier_competition_paper.py", "validate_layout = True")
    findings = validate_adapter_boundaries(tmp_path)
    assert any(item["code"] == "ADAPTER_ORCHESTRATION_BYPASS" for item in findings)
