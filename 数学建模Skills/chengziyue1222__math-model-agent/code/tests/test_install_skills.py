import subprocess
import sys
from pathlib import Path

from scripts.install_skills import install_skills
from scripts.validate_skills import validate_skill

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _write_skill(skills_root: Path, name: str, body: str) -> Path:
    skill_dir = skills_root / name
    (skill_dir / "agents").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: A Skill used by the test suite.\n---\n\n{body}\n",
        encoding="utf-8",
    )
    (skill_dir / "agents" / "openai.yaml").write_text(
        "interface:\n"
        "  display_name: Test Skill\n"
        "  short_description: Test Skill used by the test suite\n"
        f"  default_prompt: Run ${name}\n",
        encoding="utf-8",
    )
    return skill_dir


def test_runtime_reference_resolves_to_installer_source(tmp_path):
    skill_dir = _write_skill(
        tmp_path / "skills", "demo-skill", "Run `scripts/_runtime/skill_contracts.py`."
    )
    source = tmp_path / "scripts"
    source.mkdir()
    (source / "skill_contracts.py").write_text("", encoding="utf-8")

    assert validate_skill(skill_dir, tmp_path) == []


def test_runtime_reference_without_installer_source_is_reported(tmp_path):
    skill_dir = _write_skill(
        tmp_path / "skills", "demo-skill", "Run `scripts/_runtime/not_shipped.py`."
    )

    errors = validate_skill(skill_dir, tmp_path)

    assert any("scripts/_runtime/not_shipped.py" in error for error in errors)


def test_repository_skills_validate_against_installer_sources():
    errors = [
        error
        for skill_dir in sorted((REPOSITORY_ROOT / "skills").iterdir())
        if skill_dir.is_dir()
        for error in validate_skill(skill_dir, REPOSITORY_ROOT)
    ]

    assert errors == []


def test_install_skills_copies_selected_skill(tmp_path):
    source = Path(__file__).resolve().parents[2] / "skills"
    target = tmp_path / "installed"

    destinations = install_skills(source, target, ["select-model"])

    assert destinations == [target / "select-model"]
    assert (target / "select-model" / "SKILL.md").exists()
    assert (target / "select-model" / "agents" / "openai.yaml").exists()
    assert (target / "select-model" / "scripts" / "_runtime" / "run_standard_skill.py").exists()


def test_installed_skill_entrypoint_runs_outside_repository(tmp_path):
    source = Path(__file__).resolve().parents[2] / "skills"
    target = tmp_path / "installed"
    names = sorted(path.name for path in source.iterdir() if path.is_dir())
    install_skills(source, target, names)

    for name in names:
        entrypoint = target / name / "scripts" / "execute_skill.py"
        completed = subprocess.run(
            [sys.executable, str(entrypoint), "--help"],
            cwd=tmp_path,
            text=True,
            capture_output=True,
            check=False,
        )

        assert completed.returncode == 0, f"{name}: {completed.stderr}"
        assert "--project-root" in completed.stdout


def test_install_skills_dry_run_does_not_write(tmp_path):
    source = Path(__file__).resolve().parents[2] / "skills"
    target = tmp_path / "installed"

    destinations = install_skills(source, target, ["solve-model"], dry_run=True)

    assert destinations == [target / "solve-model"]
    assert not target.exists()


def test_install_skills_dry_run_allows_existing_destination(tmp_path):
    source = Path(__file__).resolve().parents[2] / "skills"
    target = tmp_path / "installed"
    destination = target / "solve-model"
    destination.mkdir(parents=True)
    marker = destination / "local-customization.txt"
    marker.write_text("preserve", encoding="utf-8")

    destinations = install_skills(source, target, ["solve-model"], dry_run=True)

    assert destinations == [destination]
    assert marker.read_text(encoding="utf-8") == "preserve"
