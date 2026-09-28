"""Finalize competition readiness or bind the stricter audit evidence package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


MAX_DELIVERY_BYTES = 20 * 1024 * 1024


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path.name}")
    return value


def _project_path(root: Path, path: Path) -> tuple[Path, str]:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"artifact must be inside project root: {path.name}") from exc
    return resolved, relative.as_posix()


def _status_pass(path: Path) -> bool:
    payload = load_object(path)
    return payload.get("status", payload.get("overall_status")) == "PASS"


def finalize(
    project_root: Path,
    *,
    manuscript: Path,
    official_problem: Path,
    decision_contract: Path,
    quality_validation: Path,
    result_object: Path,
    project_manifest: Path,
    layout_validation: Path,
    visual_layout_audit: Path,
    paper_review_report: Path,
    support_archive: Path,
    support_manifest: Path,
    reproduction_report: Path,
    submission_preflight: Path,
    profile: str = "competition",
    pdf: Path | None = None,
    docx: Path | None = None,
    latex_compile_report: Path | None = None,
    docx_render_report: Path | None = None,
    claim_registry: Path | None = None,
    figure_registry: Path | None = None,
    table_registry: Path | None = None,
    references_bib: Path | None = None,
    independent_review: Path | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if profile not in {"competition", "audit"}:
        raise ValueError(f"unknown review profile: {profile}")
    root = project_root.resolve()
    required: dict[str, Path | None] = {
        "manuscript": manuscript,
        "official_problem": official_problem,
        "decision_contract": decision_contract,
        "quality_validation": quality_validation,
        "result_object": result_object,
        "project_manifest": project_manifest,
        "cumcm_layout_validation": layout_validation,
        "visual_layout_audit": visual_layout_audit,
        "paper_review_report": paper_review_report,
        "support_archive": support_archive,
        "support_manifest": support_manifest,
        "reproduction_report": reproduction_report,
        "submission_preflight": submission_preflight,
    }
    formats = {"main_pdf": pdf, "main_docx": docx}
    if profile == "competition" and not any(formats.values()):
        raise ValueError("competition requires PDF or DOCX; PDF is the default")
    if profile == "audit":
        required.update(
            {
                **formats,
                "latex_compile_report": latex_compile_report,
                "docx_render_report": docx_render_report,
                "claim_registry": claim_registry,
                "figure_registry": figure_registry,
                "table_registry": table_registry,
                "references_bib": references_bib,
                "independent_content_review": independent_review,
            }
        )
    else:
        required.update({role: path for role, path in formats.items() if path is not None})
        if pdf is not None:
            required["latex_compile_report"] = latex_compile_report
        if docx is not None:
            required["docx_render_report"] = docx_render_report

    artifacts: dict[str, tuple[Path, str]] = {}
    for role, candidate in required.items():
        if candidate is None:
            raise FileNotFoundError(f"{role} is required for {profile}")
        resolved, relative = _project_path(root, candidate)
        if not resolved.is_file() or resolved.stat().st_size == 0:
            raise FileNotFoundError(f"{role} is missing or empty: {relative}")
        artifacts[role] = (resolved, relative)
    for role in ("main_pdf", "main_docx", "support_archive"):
        if role in artifacts and artifacts[role][0].stat().st_size > MAX_DELIVERY_BYTES:
            raise ValueError(f"{role} exceeds 20 MiB")

    gates = {
        "paper_review": _status_pass(artifacts["paper_review_report"][0]),
        "cumcm_layout": _status_pass(artifacts["cumcm_layout_validation"][0]),
        "visual_layout": _status_pass(artifacts["visual_layout_audit"][0]),
        "clean_reproduction": _status_pass(artifacts["reproduction_report"][0]),
        "submission_preflight": _status_pass(artifacts["submission_preflight"][0]),
    }
    if "latex_compile_report" in artifacts:
        gates["latex_compile"] = _status_pass(artifacts["latex_compile_report"][0])
    if "docx_render_report" in artifacts:
        gates["docx_render"] = _status_pass(artifacts["docx_render_report"][0])
    if profile == "audit":
        gates["independent_content_review"] = _status_pass(artifacts["independent_content_review"][0])

    binding: dict[str, Any] | None = None
    if profile == "audit":
        binding = {
            "schema_version": "1.1",
            "profile": profile,
            "status": "PASS" if all(gates.values()) else "FAIL",
            "artifacts": {
                role: {
                    "path": relative,
                    "sha256": digest(path),
                    "bytes": path.stat().st_size,
                }
                for role, (path, relative) in artifacts.items()
            },
            "gates": gates,
        }

    readiness = {
        "schema_version": "1.1",
        "profile": profile,
        "status": "READY_FOR_SUBMISSION" if all(gates.values()) else "BLOCKED",
        "paper_formats": sorted(role.removeprefix("main_") for role in formats if role in artifacts),
        "required_formats_present": (pdf is not None and docx is not None) if profile == "audit" else any(formats.values()),
        "all_review_gates_passed": all(gates.values()),
        "blocking_gates": sorted(name for name, passed in gates.items() if not passed),
    }
    if binding is not None:
        readiness["review_hash_binding_sha256"] = hashlib.sha256(
            json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    if binding is not None:
        (reports / "review_hash_binding.json").write_text(
            json.dumps(binding, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    (reports / "submission_readiness.json").write_text(
        json.dumps(readiness, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if readiness["status"] != "READY_FOR_SUBMISSION":
        raise ValueError("submission readiness is blocked")
    return binding, readiness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--profile", choices=("competition", "audit"), default="competition")
    for name in (
        "manuscript", "official-problem", "decision-contract", "quality-validation", "result-object",
        "project-manifest", "layout-validation", "visual-layout-audit", "paper-review-report",
        "support-archive", "support-manifest", "reproduction-report", "submission-preflight",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    for name in (
        "pdf", "docx", "latex-compile-report", "docx-render-report", "claim-registry",
        "figure-registry", "table-registry", "references-bib", "independent-review",
    ):
        parser.add_argument(f"--{name}", type=Path)
    args = parser.parse_args(argv)
    values = vars(args)
    project_root = values.pop("project_root")
    finalize(project_root, **values)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
