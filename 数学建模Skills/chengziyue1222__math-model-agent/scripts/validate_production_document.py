"""Run canonical rule-pack document checks against a source file and optional PDF."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from algorithms.document_validation import inspect_pdf_layout, validate_paper_structure


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--dependency-analysis", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    dependency = json.loads(args.dependency_analysis.read_text(encoding="utf-8")) if args.dependency_analysis else {}
    issues = [item.__dict__ for item in validate_paper_structure(args.source.read_text(encoding="utf-8"), dependency_analysis=dependency)]
    pdf = inspect_pdf_layout(args.pdf) if args.pdf else None
    result = {"status": "fail" if issues or (pdf and pdf["status"] == "fail") else "pass", "structure_issues": issues, "pdf": pdf}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
