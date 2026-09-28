"""Load, verify, and map the extracted paper-production rule pack.

The unpacked rule pack is the canonical source for rule definitions.  This
module deliberately does not copy rules into Python constants: callers obtain
the rule ID, priority, validation method, and implementation targets from the
original YAML files so diagnostics remain traceable to one source of truth.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


REQUIRED_RULE_FIELDS = {
    "rule_id", "priority", "mandatory", "implementation_target", "validation_method"
}
RULE_FILES = tuple(f"{number:02d}_{name}.yaml" for number, name in (
    (2, "layout_profile"), (3, "paper_structure_spec"), (4, "figure_grammar"),
    (5, "table_and_numeric_rules"), (6, "writing_style_rules"),
    (7, "modeling_pattern_cards"), (8, "validation_gates"),
    (9, "agent_workflow"), (12, "acceptance_tests"),
))
REJECTED_PATTERNS_FILE = "11_rejected_patterns.md"
ALLOWED_IMPLEMENTATION_STATUSES = {
    "implemented", "partially_implemented", "manual_review", "not_implemented", "blocked"
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_rule_pack(root: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return manifest and rules with their canonical source file attached."""
    base = Path(root)
    manifest = yaml.safe_load((base / "MANIFEST.yaml").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("MANIFEST.yaml must be a mapping")
    records: list[dict[str, Any]] = []
    for name in RULE_FILES:
        payload = yaml.safe_load((base / name).read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("rules"), list):
            raise ValueError(f"{name} has no rules list")
        for rule in payload["rules"]:
            if not isinstance(rule, dict):
                raise ValueError(f"{name} contains a non-mapping rule")
            records.append({**rule, "_source_file": name})
    # The manifest and evidence matrix count the rejected-pattern table as 13
    # rules.  It is Markdown rather than YAML, so parse it explicitly instead
    # of treating the manifest's 152 count as an error or inventing new rules.
    rejected = base / REJECTED_PATTERNS_FILE
    for line in rejected.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < 7 or not cells[1].startswith("REJECT-"):
            continue
        records.append({
            "rule_id": cells[1], "priority": cells[2], "mandatory": True,
            "description": cells[3], "source_files": [cells[4]],
            "evidence_pages": [cells[5]], "validation_method": cells[6],
            "implementation_target": ["SKILL.md", "Python validator", "tests", "documentation"],
            "scope": "rejected_pattern", "_source_file": REJECTED_PATTERNS_FILE,
        })
    return manifest, records


def validate_rule_pack(root: str | Path) -> dict[str, Any]:
    """Perform package-integrity checks without silently repairing source data."""
    base = Path(root)
    manifest, rules = load_rule_pack(base)
    errors: list[str] = []
    warnings: list[str] = []
    manifest_files = manifest.get("files", [])
    declared = {item.get("path"): item for item in manifest_files if isinstance(item, dict)}
    required_files = {"MANIFEST.yaml", *RULE_FILES, "00_full_analysis_report.md", "01_evidence_matrix.md",
                      "10_skill_integration_requirements.md", "11_rejected_patterns.md"}
    for name in sorted(required_files):
        if not (base / name).is_file():
            errors.append(f"missing required pack file: {name}")
    for name, item in declared.items():
        if not isinstance(name, str) or not (base / name).is_file():
            errors.append(f"manifest file missing: {name}")
            continue
        if item.get("bytes") != (base / name).stat().st_size:
            errors.append(f"manifest byte count mismatch: {name}")
        if item.get("sha256") != sha256(base / name):
            errors.append(f"manifest SHA-256 mismatch: {name}")
    ids = [str(rule.get("rule_id", "")) for rule in rules]
    duplicates = sorted(rule_id for rule_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        errors.append("duplicate rule_id: " + ", ".join(duplicates))
    for rule in rules:
        missing = sorted(field for field in REQUIRED_RULE_FIELDS if field not in rule or rule[field] in (None, "", []))
        if missing:
            errors.append(f"{rule.get('rule_id', '?')}: missing {', '.join(missing)}")
        if rule.get("priority") not in {"P0", "P1", "P2", "P3"}:
            errors.append(f"{rule.get('rule_id', '?')}: invalid priority")
        if not isinstance(rule.get("mandatory"), bool):
            errors.append(f"{rule.get('rule_id', '?')}: mandatory must be boolean")
        if not isinstance(rule.get("implementation_target"), list):
            errors.append(f"{rule.get('rule_id', '?')}: implementation_target must be a list")
    actual_counts = dict(Counter(str(rule["priority"]) for rule in rules))
    if manifest.get("rule_count_total") != len(rules):
        warnings.append(f"manifest declares {manifest.get('rule_count_total')} rules; parsed {len(rules)}")
    if manifest.get("rule_count_by_priority") != actual_counts:
        warnings.append("manifest priority counts differ from parsed rule files")
    return {
        "status": "pass" if not errors else "fail", "rule_count": len(rules),
        "priority_counts": actual_counts, "mandatory_count": sum(bool(r["mandatory"]) for r in rules),
        "errors": errors, "warnings": warnings,
    }


def implementation_type(rule: dict[str, Any]) -> str:
    """Choose a primary integration type from the rule's declared target."""
    targets = " ".join(str(x).lower() for x in rule.get("implementation_target", []))
    if "python validator" in targets:
        return "code_validator"
    if "pdf" in targets:
        return "pdf_preflight"
    if "test" in targets:
        return "unit_test"
    if "template" in targets:
        return "document_template"
    if "config" in targets:
        return "static_config"
    if "skill" in targets:
        return "prompt_rule"
    return "documentation"


def _load_implementation_evidence(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not Path(path).is_file():
        return {}
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("rules", []) if isinstance(payload, dict) else []
    evidence: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("rule_id"), str):
            raise ValueError("implementation registry entries require rule_id")
        if row.get("status") not in ALLOWED_IMPLEMENTATION_STATUSES:
            raise ValueError(f"invalid implementation status for {row['rule_id']}")
        required = ("implementation_symbol", "implementation_file", "evidence", "status_reason")
        if row["status"] == "implemented" and any(not row.get(key) for key in required):
            raise ValueError(f"implemented rule {row['rule_id']} has incomplete evidence")
        evidence[row["rule_id"]] = row
    return evidence


def write_mapping(
    root: str | Path, csv_path: str | Path, markdown_path: str | Path,
    implementation_registry: str | Path | None = None,
) -> None:
    """Write evidence-backed traceability; unknown rules remain unimplemented."""
    _, rules = load_rule_pack(root)
    evidence = _load_implementation_evidence(implementation_registry)
    rows = []
    for rule in rules:
        rule_id = str(rule["rule_id"])
        record = evidence.get(rule_id, {})
        implementation = record.get("status", "not_implemented")
        primary = record.get("implementation_type", implementation_type(rule))
        rows.append({
            "rule_id": rule_id, "priority": rule["priority"], "mandatory": rule["mandatory"],
            "rule_type": rule.get("scope", "general"), "current_status": "new integration",
            "canonical_rule_file": rule["_source_file"],
            "implementation_symbol": record.get("implementation_symbol", ""),
            "implementation_file": record.get("implementation_file", ""),
            "test_symbol": record.get("test_symbol", ""),
            "test_file": record.get("test_file", ""),
            "runtime_entrypoint": record.get("runtime_entrypoint", ""),
            "evidence": record.get("evidence", ""),
            "implementation_type": primary, "implementation_status": implementation,
            "validation_method": rule["validation_method"], "regression_risk": "low; additive adapter",
            "implemented_this_round": implementation == "implemented",
            "status_reason": record.get("status_reason", "no implementation evidence registered"),
        })
    fields = list(rows[0]) if rows else []
    with Path(csv_path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter(row["implementation_status"] for row in rows)
    lines = ["# Rule Mapping", "", "Rules are defined only in the unpacked pack. A rule is `implemented` only when the evidence registry names a real symbol and runtime/test evidence; otherwise it is explicitly not implemented.", "", f"Status counts: `{json.dumps(dict(sorted(counts.items())), sort_keys=True)}`", "", "| Rule | Priority | Mandatory | Status | Implementation evidence | Canonical source |", "|---|---|---:|---|---|---|"]
    lines += [f"| {row['rule_id']} | {row['priority']} | {row['mandatory']} | {row['implementation_status']} | `{row['implementation_file']}:{row['implementation_symbol']}` | `{row['canonical_rule_file']}` |" for row in rows]
    Path(markdown_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_validation_report(result: dict[str, Any], path: str | Path) -> None:
    lines = ["# Rule Pack Validation", "", f"Status: **{result['status'].upper()}**", "", f"- Parsed rules: {result['rule_count']}", f"- Mandatory rules: {result['mandatory_count']}", f"- Priority counts: `{json.dumps(result['priority_counts'], sort_keys=True)}`", "", "## Errors", ""]
    lines += [f"- {item}" for item in result["errors"]] or ["- None"]
    lines += ["", "## Compatibility warnings", ""]
    lines += [f"- {item}" for item in result["warnings"]] or ["- None"]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
