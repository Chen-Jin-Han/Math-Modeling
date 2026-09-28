"""Run profile-aware paper review, submission preflight, and optional audit binding."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT / "code") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "code"))

from algorithms.adversarial_review import semantic_issues
from algorithms.paper_readiness import Issue, review_paper, write_review_report
from finalize_review_package import finalize
from second_pass_content_review import main as run_second_pass
from submission_preflight import validate_submission


def main(args: argparse.Namespace) -> None:
    reports = args.project_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    review = review_paper(args.project_root, args.manuscript, mode="competition_paper")
    if review.overall_status == "PASS" and args.profile == "audit":
        run_second_pass(
            args.project_root,
            args.manuscript,
            args.decision_contract,
            args.quality_validation,
        )
    for issue in semantic_issues(args.project_root, args.manuscript):
        if issue["severity"] == "blocking":
            review.fail(issue["gate"], issue["code"], issue["message"], "modeling")
        else:
            review.issues.append(Issue(**issue))
    write_review_report(
        review,
        reports / "paper_review_report.md",
        reports / "paper_review_report.json",
    )
    if review.overall_status != "PASS":
        raise ValueError("first-pass paper review failed")

    preflight = validate_submission(
        args.project_root,
        pdf=args.pdf,
        docx=args.docx,
        support_archive=args.support_archive,
        support_manifest=args.support_manifest,
        paper_source=args.manuscript,
        identity_file=args.identity_file,
        identity_terms=args.identity_term,
        profile=args.profile,
    )
    preflight_path = reports / "submission_preflight.json"
    preflight_path.write_text(
        json.dumps(preflight, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    reproduction_path = reports / "reproduction_report.json"
    reproduction_path.write_text(
        json.dumps(preflight["clean_reproduction"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if preflight["status"] != "PASS":
        raise ValueError("submission preflight failed")

    finalize(
        args.project_root,
        manuscript=args.manuscript,
        profile=args.profile,
        pdf=args.pdf,
        docx=args.docx,
        official_problem=args.official_problem,
        decision_contract=args.decision_contract,
        quality_validation=args.quality_validation,
        result_object=args.result_object,
        project_manifest=args.project_manifest,
        layout_validation=args.layout_validation,
        latex_compile_report=args.latex_compile_report,
        docx_render_report=args.docx_render_report,
        visual_layout_audit=args.visual_layout_audit,
        paper_review_report=reports / "paper_review_report.json",
        independent_review=reports / "independent_review.json" if args.profile == "audit" else None,
        claim_registry=args.claim_registry,
        figure_registry=args.figure_registry,
        table_registry=args.table_registry,
        references_bib=args.references_bib,
        support_archive=args.support_archive,
        support_manifest=args.support_manifest,
        reproduction_report=reproduction_path,
        submission_preflight=preflight_path,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--profile", choices=("competition", "audit"), default="competition")
    parser.add_argument("--manuscript", type=Path, required=True)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--docx", type=Path)
    parser.add_argument("--official-problem", type=Path, required=True)
    parser.add_argument("--decision-contract", type=Path, required=True)
    parser.add_argument("--quality-validation", type=Path, required=True)
    parser.add_argument("--result-object", type=Path, required=True)
    parser.add_argument("--claim-registry", type=Path)
    parser.add_argument("--figure-registry", type=Path)
    parser.add_argument("--table-registry", type=Path)
    parser.add_argument("--references-bib", type=Path)
    parser.add_argument("--project-manifest", type=Path, required=True)
    parser.add_argument("--layout-validation", type=Path, required=True)
    parser.add_argument("--latex-compile-report", type=Path)
    parser.add_argument("--docx-render-report", type=Path)
    parser.add_argument("--visual-layout-audit", type=Path, required=True)
    parser.add_argument("--support-archive", type=Path, required=True)
    parser.add_argument("--support-manifest", type=Path, required=True)
    parser.add_argument("--identity-file", type=Path)
    parser.add_argument("--identity-term", action="append", default=[])
    main(parser.parse_args())
