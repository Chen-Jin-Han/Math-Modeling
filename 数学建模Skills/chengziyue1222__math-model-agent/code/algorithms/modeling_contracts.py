"""Machine-checkable contracts shared by modeling, writing, and review Skills."""

from __future__ import annotations

import re
from datetime import datetime
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


REQUIRED_QUALITY_KEYS = {
    "uncertainty": ("uncertainty_analysis_required", ("uncertainty",)),
    "dynamic": ("dynamic_validation_required", ("dynamic", "dynamic_state")),
    "tradeoff": ("tradeoff_analysis_required", ("tradeoff", "multiobjective")),
    "baseline": ("baseline_comparison_required", ("baseline", "baseline_comparison")),
}


def validate_decision_contract(contract: Mapping[str, Any]) -> list[dict[str, str]]:
    """Validate question-level result and verification obligations."""
    issues: list[dict[str, str]] = []
    questions = contract.get("questions")
    if not isinstance(questions, list) or not questions:
        return [{"id": "decision_questions_missing", "message": "decision contract has no questions"}]
    seen: set[str] = set()
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, Mapping):
            issues.append({"id": "decision_question_invalid", "message": f"question {index} is not an object"})
            continue
        qid = str(question.get("id", "")).strip()
        if not qid:
            issues.append({"id": "decision_question_id_missing", "message": f"question {index} has no id"})
        elif qid in seen:
            issues.append({"id": "decision_question_id_duplicate", "message": f"duplicate question id: {qid}"})
        seen.add(qid)
        for key in ("result_artifact", "validation_artifact"):
            if not str(question.get(key, "")).strip():
                issues.append({"id": f"{key}_missing", "message": f"{qid or index} has no {key}"})
    requirements = contract.get("requirements", {})
    if requirements is not None and not isinstance(requirements, Mapping):
        issues.append({"id": "decision_requirements_invalid", "message": "requirements must be an object"})
    return issues


def validate_contract_artifacts(contract: Mapping[str, Any], project_root: Path) -> list[dict[str, str]]:
    """Verify that every declared question result and validation artifact exists."""
    issues = validate_decision_contract(contract)
    for question in contract.get("questions", []) if isinstance(contract.get("questions"), list) else []:
        if not isinstance(question, Mapping):
            continue
        qid = str(question.get("id", "?"))
        for key in ("result_artifact", "validation_artifact"):
            value = str(question.get(key, "")).strip()
            if value and not (project_root / value).is_file():
                issues.append(
                    {"id": "decision_artifact_missing", "message": f"{qid} {key} does not exist: {value}"}
                )
    return issues


def validate_quality_validation(
    contract: Mapping[str, Any], quality: Mapping[str, Any]
) -> list[dict[str, str]]:
    """Check that required robustness claims are backed by explicit passing evidence."""
    issues: list[dict[str, str]] = []
    requirements = contract.get("requirements", {})
    if not isinstance(requirements, Mapping):
        requirements = {}
    for quality_key, (requirement_key, aliases) in REQUIRED_QUALITY_KEYS.items():
        if not requirements.get(requirement_key):
            continue
        record = next((quality.get(alias) for alias in aliases if quality.get(alias) is not None), None)
        if not isinstance(record, Mapping):
            issues.append({"id": f"{quality_key}_missing", "message": f"required {quality_key} validation is absent"})
        elif record.get("passed") is not True:
            issues.append(
                {"id": f"{quality_key}_failed", "message": f"required {quality_key} validation did not pass"}
            )
    return issues


def validate_source_records(
    records: Sequence[Mapping[str, Any]],
    *,
    require_retrieval_evidence: bool = False,
) -> list[dict[str, str]]:
    """Reject unverifiable or duplicate bibliography candidates."""
    issues: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_identifiers: set[str] = set()
    for index, record in enumerate(records, start=1):
        source_id = str(record.get("id", "")).strip()
        if not source_id:
            issues.append({"id": "source_id_missing", "message": f"source {index} has no id"})
        elif source_id in seen_ids:
            issues.append({"id": "source_id_duplicate", "message": f"duplicate source id: {source_id}"})
        seen_ids.add(source_id)
        for field in ("title", "year", "type"):
            if not str(record.get(field, "")).strip():
                issues.append({"id": f"source_{field}_missing", "message": f"{source_id or index} has no {field}"})
        identifiers = [
            f"{key}:{str(record.get(key, '')).strip().lower()}"
            for key in ("doi", "isbn", "url")
            if str(record.get(key, "")).strip()
        ]
        if not identifiers:
            issues.append({"id": "source_identifier_missing", "message": f"{source_id or index} has no DOI/ISBN/URL"})
        doi = str(record.get("doi", "")).strip()
        url = str(record.get("url", "")).strip()
        if doi and not re.fullmatch(r"10\.\d{4,9}/\S+", doi, flags=re.IGNORECASE):
            issues.append({"id": "source_doi_invalid", "message": f"{source_id or index} has a malformed DOI"})
        if doi and re.match(r"https?://(?:dx\.)?doi\.org/", url, flags=re.IGNORECASE):
            resolved = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", url, flags=re.IGNORECASE)
            if resolved.rstrip("/").lower() != doi.rstrip("/").lower():
                issues.append(
                    {
                        "id": "source_doi_url_mismatch",
                        "message": f"{source_id or index} DOI does not match its resolver URL",
                    }
                )
        for identifier in identifiers:
            if identifier in seen_identifiers:
                issues.append({"id": "source_identifier_duplicate", "message": f"duplicate identifier: {identifier}"})
            seen_identifiers.add(identifier)
        if require_retrieval_evidence:
            origin = str(record.get("origin", "")).strip().upper()
            if origin not in {"SEARCHED", "USER_SUPPLIED", "MANUALLY_ENTERED"}:
                issues.append({"id": "source_origin_invalid", "message": f"{source_id or index} has invalid origin"})
            provider = str(record.get("retrieval_provider", "")).strip()
            if not provider:
                issues.append({"id": "retrieval_provider_missing", "message": f"{source_id or index} has no retrieval provider"})
            timestamp = str(record.get("retrieval_timestamp", "")).strip()
            try:
                parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError
            except ValueError:
                issues.append({"id": "retrieval_timestamp_invalid", "message": f"{source_id or index} lacks a UTC/offset retrieval timestamp"})
            if str(record.get("source_fetch_status", "")).strip().upper() != "FETCHED":
                issues.append({"id": "source_not_fetched", "message": f"{source_id or index} was not fetched"})
            verification = record.get("metadata_verification")
            if not isinstance(verification, Mapping) or str(verification.get("status", "")).upper() != "VERIFIED":
                issues.append({"id": "metadata_unverified", "message": f"{source_id or index} metadata is not verified"})
            elif not str(verification.get("evidence", "")).strip():
                issues.append({"id": "metadata_evidence_missing", "message": f"{source_id or index} has no metadata evidence"})
            elif doi and str(verification.get("verified_identifier", "")).strip().lower() != doi.lower():
                issues.append(
                    {
                        "id": "doi_verification_evidence_missing",
                        "message": f"{source_id or index} DOI is not the identifier recorded by metadata verification",
                    }
                )
            relevance = record.get("content_relevance_evidence")
            if not isinstance(relevance, Mapping):
                issues.append({"id": "relevance_evidence_missing", "message": f"{source_id or index} has no relevance evidence"})
            else:
                if not str(relevance.get("supports", "")).strip():
                    issues.append({"id": "relevance_support_missing", "message": f"{source_id or index} has no supported claim/method"})
                if not str(relevance.get("location", "")).strip():
                    issues.append({"id": "relevance_location_missing", "message": f"{source_id or index} has no page/section/metadata location"})
    return issues


def records_to_bibtex(records: Sequence[Mapping[str, Any]]) -> str:
    """Render verified source records into a conservative BibTeX file."""
    type_map = {"article": "article", "book": "book", "inproceedings": "inproceedings", "web": "misc"}
    blocks: list[str] = []
    for record in records:
        entry_type = type_map.get(str(record.get("type", "")).lower(), "misc")
        key = re.sub(r"[^A-Za-z0-9_:-]+", "_", str(record["id"]))
        fields: list[tuple[str, str]] = []
        for field in ("author", "title", "journal", "booktitle", "publisher", "year", "volume", "number", "pages", "doi", "isbn", "url"):
            value = str(record.get(field, "")).strip()
            if value:
                fields.append((field, value.replace("\n", " ")))
        rendered = ",\n".join(f"  {field} = {{{value}}}" for field, value in fields)
        blocks.append(f"@{entry_type}{{{key},\n{rendered}\n}}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")
