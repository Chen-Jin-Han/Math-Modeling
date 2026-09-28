from pathlib import Path

import yaml

from scripts.validate_legacy_archive import validate_archive


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_archive_has_exactly_56_mapped_commands():
    assert validate_archive(ROOT) == []
    mapping = yaml.safe_load((ROOT / "legacy" / "command-map.yaml").read_text(encoding="utf-8"))
    assert len(mapping["commands"]) == 56
    assert mapping["recommended_entry"] == "run-modeling-project"


def test_only_standard_skill_tree_contains_active_skill_manifests():
    active = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}
    assert active == {
        "analyze-model-data",
        "make-model-figures",
        "research-model-literature",
        "review-model-paper",
        "run-modeling-project",
        "select-model",
        "solve-model",
        "write-model-paper",
    }
    assert not list((ROOT / "legacy").rglob("SKILL.md"))
