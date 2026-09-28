"""Install the repository's standard Codex Skills into a user-selected Skill root."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPOSITORY_ROOT / "skills"
RUNTIME_SOURCE = REPOSITORY_ROOT / "scripts"
RUNTIME_FILES = ("run_standard_skill.py", "skill_contracts.py", "skill_runtime.py")


def default_target() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    return (Path(codex_home) if codex_home else Path.home() / ".codex") / "skills"


def install_skills(
    source: Path,
    target: Path,
    names: list[str] | None = None,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> list[Path]:
    """Install self-contained Skills after preflighting every destination."""
    available = {path.name: path for path in source.iterdir() if path.is_dir()}
    selected_names = names or sorted(available)
    unknown = sorted(set(selected_names) - set(available))
    if unknown:
        raise ValueError(f"Unknown Skills: {', '.join(unknown)}")
    missing_runtime = [
        str(RUNTIME_SOURCE / name)
        for name in RUNTIME_FILES
        if not (RUNTIME_SOURCE / name).is_file()
    ]
    if missing_runtime:
        raise FileNotFoundError("Missing shared Skill runtime: " + ", ".join(missing_runtime))

    destinations = [target / name for name in selected_names]
    conflicts = [path for path in destinations if path.exists()]
    if conflicts and not force and not dry_run:
        rendered = ", ".join(str(path) for path in conflicts)
        raise FileExistsError(f"Destination already exists (use --force to update): {rendered}")
    if dry_run:
        return destinations

    target.mkdir(parents=True, exist_ok=True)
    for name, destination in zip(selected_names, destinations):
        shutil.copytree(
            available[name],
            destination,
            dirs_exist_ok=force,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
        runtime_destination = destination / "scripts" / "_runtime"
        runtime_destination.mkdir(parents=True, exist_ok=True)
        (runtime_destination / "__init__.py").write_text(
            '"""Private runtime bundled with the installed modeling Skill."""\n',
            encoding="utf-8",
        )
        for filename in RUNTIME_FILES:
            source_file = RUNTIME_SOURCE / filename
            shutil.copy2(source_file, runtime_destination / filename)
    return destinations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="Skill names; omit to install all standard Skills")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=default_target())
    parser.add_argument("--force", action="store_true", help="Update existing Skill directories")
    parser.add_argument("--dry-run", action="store_true", help="Print destinations without copying")
    args = parser.parse_args()

    try:
        destinations = install_skills(
            args.source, args.target, args.names, force=args.force, dry_run=args.dry_run
        )
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        parser.error(str(exc))

    verb = "Would install" if args.dry_run else "Installed"
    for destination in destinations:
        print(f"{verb}: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
