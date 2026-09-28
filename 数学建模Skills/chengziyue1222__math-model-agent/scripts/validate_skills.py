"""Validate repository Codex Skills without depending on a user Codex installation."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
RESOURCE_PATTERN = re.compile(r"(?:references|scripts|assets)/[A-Za-z0-9_.\-/]+")
# ``scripts/_runtime/<name>`` only exists after ``scripts/install_skills.py``
# installs a Skill: it is copied from ``<repository>/scripts/<name>``. The
# reference is therefore resolved against that source rather than the checkout,
# which keeps the check meaningful instead of skipping runtime paths entirely.
RUNTIME_REFERENCE_PATTERN = re.compile(r"^scripts/_runtime/([A-Za-z0-9_.\-]+)$")


def _frontmatter(text: str, path: Path) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: SKILL.md must start with YAML frontmatter")
    try:
        raw_metadata, body = text[4:].split("\n---\n", 1)
    except ValueError as exc:
        raise ValueError(f"{path}: frontmatter closing delimiter is missing") from exc
    metadata = yaml.safe_load(raw_metadata)
    if not isinstance(metadata, dict):
        raise ValueError(f"{path}: frontmatter must be a mapping")
    return metadata, body


def _local_references(body: str) -> set[str]:
    references = set(RESOURCE_PATTERN.findall(body))
    for target in LINK_PATTERN.findall(body):
        target = target.split("#", 1)[0]
        if target and not re.match(r"^[a-z]+://", target):
            references.add(target)
    return references


def _missing_reference(skill_dir: Path, relative_path: str, repository_root: Path) -> bool:
    """Report whether a referenced SKILL.md resource is unavailable.

    Install-time runtime references are resolved against the repository
    ``scripts/`` directory they are generated from.
    """
    if (skill_dir / relative_path).exists():
        return False
    match = RUNTIME_REFERENCE_PATTERN.match(relative_path)
    if match and (repository_root / "scripts" / match.group(1)).is_file():
        return False
    return True


def validate_skill(skill_dir: Path, repository_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    if repository_root is None:
        repository_root = skill_dir.parent.parent
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return [f"{skill_dir}: missing SKILL.md"]

    try:
        metadata, body = _frontmatter(skill_file.read_text(encoding="utf-8"), skill_file)
    except (OSError, UnicodeError, ValueError) as exc:
        return [str(exc)]

    if set(metadata) != {"name", "description"}:
        errors.append(f"{skill_file}: frontmatter must contain only name and description")
    name = metadata.get("name")
    description = metadata.get("description")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name) or len(name) > 63:
        errors.append(f"{skill_file}: invalid skill name {name!r}")
    elif name != skill_dir.name:
        errors.append(f"{skill_file}: name must match directory {skill_dir.name!r}")
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{skill_file}: description must be non-empty")
    if not body.strip():
        errors.append(f"{skill_file}: instruction body must be non-empty")

    metadata_file = skill_dir / "agents" / "openai.yaml"
    if not metadata_file.exists():
        errors.append(f"{skill_dir}: missing recommended agents/openai.yaml")
    else:
        try:
            agent_metadata = yaml.safe_load(metadata_file.read_text(encoding="utf-8"))
            interface = agent_metadata["interface"]
            for field in ("display_name", "short_description", "default_prompt"):
                if not isinstance(interface.get(field), str) or not interface[field].strip():
                    errors.append(f"{metadata_file}: interface.{field} must be non-empty")
            if isinstance(name, str) and f"${name}" not in interface.get("default_prompt", ""):
                errors.append(f"{metadata_file}: default_prompt must mention ${name}")
        except (OSError, UnicodeError, yaml.YAMLError, KeyError, TypeError) as exc:
            errors.append(f"{metadata_file}: invalid metadata: {exc}")

    for relative_path in sorted(_local_references(body)):
        if _missing_reference(skill_dir, relative_path, repository_root):
            errors.append(f"{skill_file}: referenced resource does not exist: {relative_path}")

    forbidden_docs = {"README.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md", "QUICK_REFERENCE.md"}
    for filename in forbidden_docs:
        if (skill_dir / filename).exists():
            errors.append(f"{skill_dir}: remove extraneous {filename}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("skills"))
    args = parser.parse_args()

    if not args.root.is_dir():
        print(f"Skill root does not exist: {args.root}", file=sys.stderr)
        return 2
    skill_dirs = sorted(path for path in args.root.iterdir() if path.is_dir())
    if not skill_dirs:
        print(f"No Skill directories found under {args.root}", file=sys.stderr)
        return 2

    repository_root = args.root.resolve().parent
    errors = [
        error
        for skill_dir in skill_dirs
        for error in validate_skill(skill_dir, repository_root)
    ]
    if errors:
        print("Skill validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(skill_dirs)} Codex Skills under {args.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
