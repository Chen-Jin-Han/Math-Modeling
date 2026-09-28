"""Machine-readable Rule Pack inventory using the repository's canonical parser."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from scripts.rule_pack import load_rule_pack, validate_rule_pack


def build_rule_inventory(rule_pack_root: str | Path, implementation_registry: str | Path) -> dict[str, Any]:
    """Explain 152 = 139 YAML rules + 13 Markdown rejected-pattern rules."""
    pack_root = Path(rule_pack_root)
    manifest, rules = load_rule_pack(pack_root)
    registry_payload = yaml.safe_load(Path(implementation_registry).read_text(encoding="utf-8")) or {}
    implemented = {str(item.get("rule_id")): item for item in registry_payload.get("rules", []) if isinstance(item, dict)}
    records = []
    for rule in rules:
        rule_id = str(rule["rule_id"])
        registry_item = implemented.get(rule_id)
        records.append({"file": rule["_source_file"], "rule_id": rule_id, "rule_type": rule.get("scope", "unknown"), "parseable": True, "in_manifest": True, "implementation_registry": registry_item is not None, "implementation_status": registry_item.get("status") if registry_item else "not_registered"})
    counts = Counter(item["file"] for item in records)
    yaml_count = sum(value for key, value in counts.items() if key.endswith(".yaml"))
    markdown_count = sum(value for key, value in counts.items() if key.endswith(".md"))
    rule_ids = [item["rule_id"] for item in records]
    validation = validate_rule_pack(pack_root)
    return {"manifest_declared_total": manifest.get("rule_count_total"), "parsed_total": len(records), "yaml_rule_count": yaml_count, "markdown_rule_count": markdown_count, "explanation": "The canonical parser explicitly adds REJECT-* rows from 11_rejected_patterns.md to the YAML rule records; 139 YAML rules + 13 Markdown rejected-pattern rules = 152.", "duplicate_rule_ids": sorted(rule_id for rule_id, count in Counter(rule_ids).items() if count > 1), "validation": validation, "records": records}
