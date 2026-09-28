from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_literature_adapter_uses_explicit_verified_candidates(tmp_path) -> None:
    module = _load(
        "build_source_record",
        "skills/research-model-literature/scripts/build_source_record.py",
    )
    candidates = tmp_path / "candidates.json"
    candidates.write_text(
        json.dumps(
            [
                {
                    "id": "method2024",
                    "title": "Verified method",
                    "author": "A. Author",
                    "year": 2024,
                    "type": "article",
                    "doi": "10.1000/example",
                    "purpose": "method definition",
                    "origin": "SEARCHED",
                    "retrieval_provider": "Crossref",
                    "retrieval_timestamp": "2026-07-26T12:00:00+00:00",
                    "source_fetch_status": "FETCHED",
                    "metadata_verification": {
                        "status": "VERIFIED",
                        "verified_identifier": "10.1000/example",
                        "evidence": "Crossref title, author, year, and DOI match",
                    },
                    "content_relevance_evidence": {
                        "supports": "method definition",
                        "location": "abstract",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    module.main(tmp_path, candidates)
    validation = json.loads((tmp_path / "results" / "bib_validation.json").read_text(encoding="utf-8"))
    assert validation["status"] == "PASS"
    assert "@article{method2024" in (tmp_path / "paper" / "references.bib").read_text(encoding="utf-8")


def test_literature_adapter_rejects_duplicate_identifiers(tmp_path) -> None:
    module = _load(
        "build_source_record_duplicate",
        "skills/research-model-literature/scripts/build_source_record.py",
    )
    candidates = tmp_path / "candidates.json"
    candidates.write_text(
        json.dumps(
            [
                {
                    "id": "a", "title": "A", "year": 2020, "type": "article", "doi": "10/x",
                    "origin": "SEARCHED", "retrieval_provider": "Crossref",
                    "retrieval_timestamp": "2026-07-26T12:00:00+00:00", "source_fetch_status": "FETCHED",
                    "metadata_verification": {"status": "VERIFIED", "evidence": "match"},
                    "content_relevance_evidence": {"supports": "A", "location": "abstract"},
                },
                {
                    "id": "b", "title": "B", "year": 2021, "type": "article", "doi": "10/x",
                    "origin": "SEARCHED", "retrieval_provider": "Crossref",
                    "retrieval_timestamp": "2026-07-26T12:00:00+00:00", "source_fetch_status": "FETCHED",
                    "metadata_verification": {"status": "VERIFIED", "evidence": "match"},
                    "content_relevance_evidence": {"supports": "B", "location": "abstract"},
                },
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="validation failed"):
        module.main(tmp_path, candidates)
    validation = json.loads((tmp_path / "results" / "bib_validation.json").read_text(encoding="utf-8"))
    assert validation["status"] == "FAIL"


def test_c_topic_adapters_delegate_quality_work_to_generic_library() -> None:
    solve = (ROOT / "skills" / "solve-model" / "scripts" / "solve_supplier_chain.py").read_text(encoding="utf-8")
    figures = (ROOT / "skills" / "make-model-figures" / "scripts" / "render_supplier_figures.py").read_text(encoding="utf-8")
    assert "validate_state_balance(" in solve
    assert "compare_policy_metrics(" in solve
    assert "service_level_metrics(" in solve
    assert "export_publication_figure(" in figures
    assert ".savefig(" not in figures
    assert "dpi=240" not in figures
    assert not (ROOT / "skills" / "write-model-paper" / "scripts" / "write_traceable_summary.py").exists()
    assert (ROOT / "skills" / "write-model-paper" / "scripts" / "write_supplier_competition_paper.py").is_file()


def test_second_pass_review_binds_contract_and_quality_hashes(tmp_path) -> None:
    module = _load(
        "second_pass_content_review",
        "skills/review-model-paper/scripts/second_pass_content_review.py",
    )
    (tmp_path / "paper").mkdir()
    (tmp_path / "results").mkdir()
    manuscript = tmp_path / "paper" / "main.md"
    result = tmp_path / "results" / "q1.json"
    validation = tmp_path / "results" / "q1-validation.json"
    contract = tmp_path / "results" / "decision_contract.json"
    quality = tmp_path / "results" / "quality_validation.json"
    manuscript.write_text("# 问题一\n结果及局限。\n", encoding="utf-8")
    result.write_text("{}", encoding="utf-8")
    validation.write_text("{}", encoding="utf-8")
    contract.write_text(
        json.dumps(
            {
                "questions": [
                    {
                        "id": "Q1",
                        "result_artifact": "results/q1.json",
                        "validation_artifact": "results/q1-validation.json",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    quality.write_text(json.dumps({"uncertainty": {"passed": True}}), encoding="utf-8")
    module.main(tmp_path, manuscript, contract, quality)
    report = json.loads((tmp_path / "reports" / "independent_review.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert len(report["decision_contract_sha256"]) == 64
    assert len(report["quality_validation_sha256"]) == 64


def _review_paths(tmp_path: Path, *, audit: bool = False) -> dict[str, Path]:
    relatives = {
        "manuscript": "paper/main.md",
        "pdf": "paper/main.pdf",
        "official_problem": "problem/official.pdf",
        "decision_contract": "results/decision_contract.json",
        "quality_validation": "results/quality_validation.json",
        "result_object": "results/result_object.json",
        "project_manifest": "run-manifest.json",
        "layout_validation": "reports/cumcm_layout_validation.json",
        "latex_compile_report": "reports/latex_compile_report.json",
        "visual_layout_audit": "reports/visual_layout_audit.json",
        "paper_review_report": "reports/paper_review_report.json",
        "support_archive": "delivery/support.zip",
        "support_manifest": "delivery/support-manifest.json",
        "reproduction_report": "reports/reproduction_report.json",
        "submission_preflight": "reports/submission_preflight.json",
    }
    if audit:
        relatives.update(
            {
                "docx": "paper/main.docx",
                "docx_render_report": "reports/docx_render_report.json",
                "claim_registry": "paper/claim-registry.json",
                "figure_registry": "paper/figure-registry.json",
                "table_registry": "paper/table-registry.json",
                "references_bib": "paper/references.bib",
                "independent_review": "reports/independent_review.json",
            }
        )
    paths = {}
    for name, relative in relatives.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        paths[name] = path
        if name == "paper_review_report":
            payload = {"overall_status": "PASS"}
        elif path.suffix == ".json":
            payload = {"status": "PASS"}
        else:
            path.write_bytes(b"rendered")
            continue
        path.write_text(json.dumps(payload), encoding="utf-8")
    return paths


def test_competition_review_package_accepts_pdf_only(tmp_path) -> None:
    module = _load(
        "finalize_review_package_competition",
        "skills/review-model-paper/scripts/finalize_review_package.py",
    )
    binding, readiness = module.finalize(tmp_path, **_review_paths(tmp_path))
    assert binding is None
    assert readiness["status"] == "READY_FOR_SUBMISSION"
    assert readiness["paper_formats"] == ["pdf"]
    assert not (tmp_path / "reports" / "review_hash_binding.json").exists()


def test_audit_review_package_keeps_full_evidence_boundary(tmp_path) -> None:
    module = _load(
        "finalize_review_package_audit",
        "skills/review-model-paper/scripts/finalize_review_package.py",
    )
    paths = _review_paths(tmp_path, audit=True)
    binding, readiness = module.finalize(tmp_path, profile="audit", **paths)
    assert binding is not None and binding["status"] == "PASS"
    assert {"main_pdf", "main_docx", "independent_content_review"} <= set(binding["artifacts"])
    assert readiness["status"] == "READY_FOR_SUBMISSION"


def test_review_package_fails_when_visual_audit_fails(tmp_path) -> None:
    module = _load(
        "finalize_review_package_failure",
        "skills/review-model-paper/scripts/finalize_review_package.py",
    )
    paths = _review_paths(tmp_path)
    paths["visual_layout_audit"].write_text(json.dumps({"status": "FAIL"}), encoding="utf-8")
    with pytest.raises(ValueError, match="submission readiness"):
        module.finalize(tmp_path, **paths)
