from pathlib import Path
import csv

from scripts.rule_pack import load_rule_pack, validate_rule_pack, write_mapping


PACK = Path("docs/reverse_engineering/skill_rule_pack_v1")


def test_rule_pack_parses_with_unique_ids_and_required_fields():
    manifest, rules = load_rule_pack(PACK)
    assert manifest["package_version"] == "1.0.0"
    assert len(rules) == 152
    assert len({rule["rule_id"] for rule in rules}) == len(rules)
    assert all(rule["validation_method"] and rule["implementation_target"] for rule in rules)


def test_rule_pack_validation_includes_markdown_rejection_rules_in_manifest_total():
    result = validate_rule_pack(PACK)
    assert result["status"] == "pass"
    assert result["errors"] == []
    assert result["rule_count"] == 152
    assert result["warnings"] == []


def test_mapping_requires_registered_implementation_evidence(tmp_path):
    csv_path, markdown_path = tmp_path / "mapping.csv", tmp_path / "mapping.md"
    write_mapping(PACK, csv_path, markdown_path, Path("config/rule_implementation_registry.yaml"))
    with csv_path.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 152
    assert any(row["implementation_status"] == "not_implemented" for row in rows)
    for row in rows:
        if row["implementation_status"] == "implemented":
            assert row["implementation_symbol"] and Path(row["implementation_file"]).is_file()
            assert row["test_symbol"] and Path(row["test_file"]).is_file()
