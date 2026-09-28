"""Validate the compatibility-only archive and its standard-Skill replacements."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def validate_archive(root: Path) -> list[str]:
    errors: list[str] = []
    mapping_path = root / "legacy" / "command-map.yaml"
    try:
        mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        return [str(exc)]
    if not isinstance(mapping, dict):
        return [f"{mapping_path}: expected a mapping"]
    if mapping.get("status") != "compatibility-only":
        errors.append(f"{mapping_path}: status must be compatibility-only")
    commands = mapping.get("commands")
    if not isinstance(commands, dict) or len(commands) != 56:
        errors.append(f"{mapping_path}: commands must map exactly 56 archived documents")
        commands = {}
    standard = {
        path.parent.name
        for path in (root / "skills").glob("*/SKILL.md")
        if path.parent.is_dir()
    }
    if mapping.get("recommended_entry") != "run-modeling-project":
        errors.append(f"{mapping_path}: recommended_entry must be run-modeling-project")
    for relative, replacement in commands.items():
        path = root / str(relative)
        if not path.is_file():
            errors.append(f"missing archived command: {relative}")
        if replacement not in standard:
            errors.append(f"{relative}: unknown standard replacement {replacement!r}")
    archived = {
        path.relative_to(root).as_posix()
        for path in (root / "legacy" / "skills").rglob("*.md")
        if path.name != "README.md"
    }
    if set(commands) != archived:
        for missing in sorted(archived - set(commands)):
            errors.append(f"archived command lacks mapping: {missing}")
        for extra in sorted(set(commands) - archived):
            errors.append(f"mapping is not an archived command: {extra}")
    if (root / "skill").exists():
        errors.append(f"{root / 'skill'}: primary legacy command directory must not exist")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate_archive(args.root.resolve())
    if errors:
        print("Legacy archive validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Validated 56 compatibility-only command documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
