"""Validate explicit source candidates and build traceable literature artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT / "code") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "code"))

from algorithms.modeling_contracts import records_to_bibtex, validate_source_records


def dump(root: Path, name: str, value: object) -> None:
    path = root / "results" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(root: Path, source_candidates: Path) -> None:
    loaded = json.loads(source_candidates.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError("source_candidates must be a JSON array")
    records = [record for record in loaded if isinstance(record, dict)]
    malformed = len(loaded) - len(records)
    issues = validate_source_records(records, require_retrieval_evidence=True)
    if malformed:
        issues.append({"id": "source_record_invalid", "message": f"{malformed} candidates are not objects"})

    queries = [
        {
            "query": str(record.get("query") or record.get("title", "")).strip(),
            "purpose": str(record.get("purpose", "method or problem evidence")).strip(),
            "candidate_id": record.get("id"),
        }
        for record in records
    ]
    dump(root, "search_queries.json", queries)
    dump(root, "search_results.json", records)
    retrieval_log = [
        {
            "candidate_id": record.get("id"),
            "origin": record.get("origin"),
            "retrieval_provider": record.get("retrieval_provider"),
            "retrieval_timestamp": record.get("retrieval_timestamp"),
            "source_fetch_status": record.get("source_fetch_status"),
            "url": record.get("url") or (f"https://doi.org/{record['doi']}" if record.get("doi") else None),
        }
        for record in records
    ]
    metadata_verification = [
        {"candidate_id": record.get("id"), **(record.get("metadata_verification") or {})}
        for record in records
    ]
    relevance_evidence = [
        {"candidate_id": record.get("id"), **(record.get("content_relevance_evidence") or {})}
        for record in records
    ]
    dump(root, "retrieval_log.json", retrieval_log)
    dump(root, "metadata_verification.json", metadata_verification)
    dump(root, "relevance_evidence.json", relevance_evidence)
    if issues:
        dump(root, "selected_sources.json", [])
        dump(root, "rejected_sources.json", issues)
        dump(root, "bib_validation.json", {"status": "FAIL", "records": len(records), "issues": issues})
        raise ValueError("source candidate validation failed")

    dump(root, "selected_sources.json", records)
    dump(root, "rejected_sources.json", [])
    report = root / "reports" / "literature_evidence.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# Literature evidence\n\n"
        f"{len(records)} source candidates passed identity, fetch-provenance, metadata, duplication, and relevance checks. "
        "They may support framing and method choices; project-specific numerical claims must still "
        "come from registered data and result artifacts.\n",
        encoding="utf-8",
    )
    bib = root / "paper" / "references.bib"
    bib.parent.mkdir(parents=True, exist_ok=True)
    bib.write_text(records_to_bibtex(records), encoding="utf-8")
    dump(root, "bib_validation.json", {"status": "PASS", "records": len(records), "issues": []})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-candidates", type=Path, required=True)
    args = parser.parse_args()
    main(args.root, args.source_candidates)
