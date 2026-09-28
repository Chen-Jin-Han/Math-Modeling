#!/usr/bin/env python3
"""Run evidence-gated review for Markdown papers or legacy layout checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paper_path")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--mode", choices=("brief_report", "teaching_example", "competition_paper"))
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--figures-dir", default="figures")
    parser.add_argument("--results-file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root / "code"))
    try:
        from algorithms import check_paper
    except Exception as exc:
        print(f"Cannot import repository paper checker: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    if args.paper_path.lower().endswith(".md"):
        if not args.project_root or not args.mode:
            print("Markdown review requires --project-root and --mode", file=sys.stderr)
            return 2
        from algorithms.paper_readiness import review_paper, write_review_report
        review = review_paper(args.project_root, args.paper_path, mode=args.mode)
        from algorithms.adversarial_review import semantic_issues
        for issue in semantic_issues(args.project_root, args.paper_path):
            if issue["severity"] == "blocking":
                review.fail(issue["gate"], issue["code"], issue["message"], "modeling")
            else:
                from algorithms.paper_readiness import Issue
                review.issues.append(Issue(**issue))
        output = args.report_dir or Path(args.paper_path).parent
        output.mkdir(parents=True, exist_ok=True)
        write_review_report(review, output / "paper_review_report.md", output / "paper_review_report.json")
        print(json.dumps(review.as_dict(), ensure_ascii=False, indent=2))
        return 0 if review.overall_status == "PASS" else 1
    report = check_paper(
        args.paper_path,
        figures_dir=args.figures_dir,
        results_file=args.results_file,
    )
    print(report.summary())
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
