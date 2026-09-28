import json

import pytest

from scripts.run_manifest import build_manifest, main, validate_manifest


def _spec() -> dict:
    return {
        "run_id": "test-run",
        "created_at": "2026-07-18T08:00:00+00:00",
        "problem": {
            "competition": "unit-test",
            "year": 2026,
            "code": "A",
            "title": "manifest",
            "source": "tests",
        },
        "stage": "validation",
        "status": "succeeded",
        "data_inputs": ["data.csv"],
        "model": {
            "name": "baseline",
            "version": "1.0",
            "assumptions_path": None,
            "parameter_source": "inline",
        },
        "execution": {
            "command": ["python", "solve.py"],
            "deterministic": False,
            "random_seeds": {"numpy": 42},
        },
        "parameters": {"alpha": 0.1},
        "metrics": {"rmse": {"value": 1.2, "unit": "items", "split": "test"}},
        "failed_runs": [{"run_id": "pilot", "reason": "diverged"}],
        "artifacts": [{"path": "result.json", "role": "result"}],
        "limitations": ["synthetic data"],
    }


def test_build_manifest_hashes_inputs_and_records_environment(tmp_path):
    (tmp_path / "data.csv").write_bytes(b"x\n1\n")
    (tmp_path / "result.json").write_text('{"ok": true}\n', encoding="utf-8")

    manifest = build_manifest(_spec(), tmp_path)

    assert manifest["data_inputs"][0]["sha256"] == (
        "daff832f802000e645771a60983c76c963f6ee602a6230e45237bd360e91cc1a"
    )
    assert manifest["artifacts"][0]["role"] == "result"
    assert manifest["environment"]["python"]
    assert "git_commit" in manifest["execution"]
    assert "git_dirty" in manifest["execution"]
    assert validate_manifest(manifest, tmp_path, verify_files=True) == []


def test_integrity_validation_detects_changed_input(tmp_path):
    (tmp_path / "data.csv").write_text("x\n1\n", encoding="utf-8")
    (tmp_path / "result.json").write_text("{}\n", encoding="utf-8")
    manifest = build_manifest(_spec(), tmp_path)
    (tmp_path / "data.csv").write_text("x\n2\n", encoding="utf-8")

    errors = validate_manifest(manifest, tmp_path, verify_files=True)

    assert any("sha256 mismatch" in error for error in errors)


@pytest.mark.parametrize("unsafe", ["../secret.csv", "/tmp/secret.csv", "C:/secret.csv"])
def test_manifest_rejects_paths_outside_project(tmp_path, unsafe):
    spec = _spec()
    spec["data_inputs"] = [unsafe]

    with pytest.raises(ValueError, match="unsafe project-relative path"):
        build_manifest(spec, tmp_path)


def test_stochastic_run_requires_seed(tmp_path):
    (tmp_path / "data.csv").write_text("x\n1\n", encoding="utf-8")
    (tmp_path / "result.json").write_text("{}\n", encoding="utf-8")
    spec = _spec()
    spec["execution"]["random_seeds"] = {}

    with pytest.raises(ValueError, match="random seed"):
        build_manifest(spec, tmp_path)


def test_cli_creates_and_verifies_manifest(tmp_path, monkeypatch):
    (tmp_path / "data.csv").write_text("x\n1\n", encoding="utf-8")
    (tmp_path / "result.json").write_text("{}\n", encoding="utf-8")
    spec_path = tmp_path / "spec.json"
    manifest_path = tmp_path / "run-manifest.json"
    spec_path.write_text(json.dumps(_spec()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_manifest.py",
            "create",
            "--spec",
            str(spec_path),
            "--project-root",
            str(tmp_path),
            "--output",
            str(manifest_path),
        ],
    )
    assert main() == 0
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_manifest.py",
            "validate",
            str(manifest_path),
            "--project-root",
            str(tmp_path),
            "--verify-files",
        ],
    )
    assert main() == 0
