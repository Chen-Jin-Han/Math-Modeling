"""Create and validate reproducible mathematical-modeling run manifests."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import re
import subprocess
import sys
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path, PurePath, PureWindowsPath
from typing import Any


SCHEMA_VERSION = "1.0"
STAGES = {"intake", "analysis", "modeling", "validation", "writing", "review", "release"}
STATUSES = {"running", "succeeded", "failed", "partial"}
REQUIRED_FIELDS = {
    "schema_version",
    "run_id",
    "created_at",
    "problem",
    "stage",
    "status",
    "data_inputs",
    "model",
    "execution",
    "parameters",
    "metrics",
    "failed_runs",
    "artifacts",
    "environment",
    "limitations",
}
TRACKED_DEPENDENCIES = ("numpy", "scipy", "matplotlib", "pandas", "scikit-learn", "networkx")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_path(value: str) -> bool:
    path = PurePath(value)
    windows_path = PureWindowsPath(value)
    return (
        bool(value)
        and not path.is_absolute()
        and not path.anchor
        # CI runs on POSIX, where ``C:/...`` would otherwise look relative.
        and not windows_path.is_absolute()
        and not windows_path.drive
        and not value.startswith(("/", "\\"))
        and ".." not in path.parts
    )


def _file_record(root: Path, value: str | dict[str, Any], *, artifact: bool) -> dict[str, Any]:
    source = {"path": value} if isinstance(value, str) else deepcopy(value)
    relative = source.get("path")
    if not isinstance(relative, str) or not _safe_relative_path(relative):
        raise ValueError(f"unsafe project-relative path: {relative!r}")
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(f"tracked file does not exist: {relative}")
    if artifact and not isinstance(source.get("role"), str):
        raise ValueError(f"artifact {relative!r} requires a role")
    source["sha256"] = _sha256(path)
    source["bytes"] = path.stat().st_size
    return source


def _git_state(root: Path) -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return None, None


def _environment() -> dict[str, Any]:
    dependencies: dict[str, str] = {}
    for name in TRACKED_DEPENDENCIES:
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = "not-installed"
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": dependencies,
    }


def build_manifest(spec: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Enrich a concise run specification with hashes and runtime metadata."""
    root = project_root.resolve()
    manifest = deepcopy(spec)
    manifest["schema_version"] = SCHEMA_VERSION
    manifest.setdefault("run_id", uuid.uuid4().hex)
    manifest.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    manifest.setdefault("parent_run_id", None)
    manifest["data_inputs"] = [
        _file_record(root, item, artifact=False) for item in manifest.get("data_inputs", [])
    ]
    manifest["artifacts"] = [
        _file_record(root, item, artifact=True) for item in manifest.get("artifacts", [])
    ]
    execution = manifest.setdefault("execution", {})
    commit, dirty = _git_state(root)
    execution.setdefault("git_commit", commit)
    execution.setdefault("git_dirty", dirty)
    manifest["environment"] = _environment()
    manifest.setdefault("parameters", {})
    manifest.setdefault("metrics", {})
    manifest.setdefault("failed_runs", [])
    manifest.setdefault("limitations", [])
    errors = validate_manifest(manifest, root, verify_files=True)
    if errors:
        raise ValueError("invalid run specification:\n- " + "\n- ".join(errors))
    return manifest


def _check_file_records(
    records: Any, field: str, root: Path, verify_files: bool, errors: list[str]
) -> None:
    if not isinstance(records, list):
        errors.append(f"{field} must be a list")
        return
    for index, record in enumerate(records):
        label = f"{field}[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{label} must be an object")
            continue
        relative = record.get("path")
        digest = record.get("sha256")
        size = record.get("bytes")
        if not isinstance(relative, str) or not _safe_relative_path(relative):
            errors.append(f"{label}.path must be a safe project-relative path")
            continue
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            errors.append(f"{label}.sha256 must be a lowercase hexadecimal SHA-256 digest")
        if not isinstance(size, int) or size < 0:
            errors.append(f"{label}.bytes must be a non-negative integer")
        if field == "artifacts" and (
            not isinstance(record.get("role"), str) or not record["role"]
        ):
            errors.append(f"{label}.role must be a non-empty string")
        if verify_files:
            path = root / relative
            if not path.is_file():
                errors.append(f"{label}: file not found: {relative}")
            else:
                if isinstance(digest, str) and _sha256(path) != digest:
                    errors.append(f"{label}: sha256 mismatch: {relative}")
                if isinstance(size, int) and path.stat().st_size != size:
                    errors.append(f"{label}: size mismatch: {relative}")


def validate_manifest(
    manifest: Any, project_root: Path, *, verify_files: bool = False
) -> list[str]:
    """Return all structural and optional on-disk integrity errors."""
    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"]
    errors: list[str] = []
    missing = REQUIRED_FIELDS - set(manifest)
    if missing:
        errors.append("missing fields: " + ", ".join(sorted(missing)))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not isinstance(manifest.get("run_id"), str) or not manifest.get("run_id"):
        errors.append("run_id must be a non-empty string")
    created_at = manifest.get("created_at")
    try:
        datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except ValueError:
        errors.append("created_at must be an ISO-8601 timestamp")
    if manifest.get("stage") not in STAGES:
        errors.append(f"stage must be one of: {', '.join(sorted(STAGES))}")
    if manifest.get("status") not in STATUSES:
        errors.append(f"status must be one of: {', '.join(sorted(STATUSES))}")

    problem = manifest.get("problem")
    if not isinstance(problem, dict):
        errors.append("problem must be an object")
    else:
        for key in ("competition", "year", "code", "title", "source"):
            value = problem.get(key)
            if key == "year":
                if not isinstance(value, int) or value < 1900:
                    errors.append("problem.year must be an integer of at least 1900")
            elif not isinstance(value, str) or not value:
                errors.append(f"problem.{key} must be a non-empty string")

    model = manifest.get("model")
    if not isinstance(model, dict):
        errors.append("model must be an object")
    else:
        for key in ("name", "version", "parameter_source"):
            if not isinstance(model.get(key), str) or not model[key]:
                errors.append(f"model.{key} must be a non-empty string")
        assumptions = model.get("assumptions_path")
        if assumptions is not None and (
            not isinstance(assumptions, str) or not _safe_relative_path(assumptions)
        ):
            errors.append("model.assumptions_path must be null or a safe project-relative path")

    execution = manifest.get("execution")
    if not isinstance(execution, dict):
        errors.append("execution must be an object")
    else:
        command = execution.get("command")
        if not isinstance(command, list) or not command or not all(
            isinstance(item, str) for item in command
        ):
            errors.append("execution.command must be a non-empty string list")
        deterministic = execution.get("deterministic")
        seeds = execution.get("random_seeds")
        if not isinstance(deterministic, bool):
            errors.append("execution.deterministic must be boolean")
        if not isinstance(seeds, dict) or not all(
            isinstance(name, str) and isinstance(seed, int) for name, seed in seeds.items()
        ):
            errors.append("execution.random_seeds must map names to integer seeds")
        elif deterministic is False and not seeds:
            errors.append("a stochastic run must record at least one random seed")
        if "git_commit" not in execution or "git_dirty" not in execution:
            errors.append("execution must record git_commit and git_dirty")

    metrics = manifest.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("metrics must be an object")
    else:
        for name, metric in metrics.items():
            if not isinstance(metric, dict):
                errors.append(f"metrics.{name} must be an object")
            elif (
                isinstance(metric.get("value"), bool)
                or not isinstance(metric.get("value"), (int, float))
                or not math.isfinite(metric["value"])
                or any(not isinstance(metric.get(key), str) for key in ("unit", "split"))
            ):
                errors.append(f"metrics.{name} requires numeric value plus string unit and split")

    failed_runs = manifest.get("failed_runs")
    if not isinstance(failed_runs, list):
        errors.append("failed_runs must be a list")
    else:
        for index, failed in enumerate(failed_runs):
            if not isinstance(failed, dict) or not all(
                isinstance(failed.get(key), str) and failed[key] for key in ("run_id", "reason")
            ):
                errors.append(f"failed_runs[{index}] requires non-empty run_id and reason")
            elif failed.get("diagnostics_path") is not None and (
                not isinstance(failed["diagnostics_path"], str)
                or not _safe_relative_path(failed["diagnostics_path"])
            ):
                errors.append(
                    f"failed_runs[{index}].diagnostics_path must be null or project-relative"
                )

    if not isinstance(manifest.get("parameters"), dict):
        errors.append("parameters must be an object")
    environment = manifest.get("environment")
    if not isinstance(environment, dict):
        errors.append("environment must be an object")
    else:
        if not isinstance(environment.get("python"), str) or not environment["python"]:
            errors.append("environment.python must be a non-empty string")
        if not isinstance(environment.get("platform"), str) or not environment["platform"]:
            errors.append("environment.platform must be a non-empty string")
        dependencies = environment.get("dependencies")
        if not isinstance(dependencies, dict):
            errors.append("environment.dependencies must map package names to versions")
        elif not all(
            isinstance(name, str) and isinstance(version, str)
            for name, version in dependencies.items()
        ):
            errors.append("environment.dependencies must map package names to versions")
    if not isinstance(manifest.get("limitations"), list) or not all(
        isinstance(item, str) for item in manifest.get("limitations", [])
    ):
        errors.append("limitations must be a string list")
    root = project_root.resolve()
    _check_file_records(manifest.get("data_inputs"), "data_inputs", root, verify_files, errors)
    _check_file_records(manifest.get("artifacts"), "artifacts", root, verify_files, errors)
    return errors


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    create = subparsers.add_parser("create", help="create a manifest from a concise JSON spec")
    create.add_argument("--spec", required=True, type=Path)
    create.add_argument("--project-root", type=Path, default=Path.cwd())
    create.add_argument("--output", required=True, type=Path)
    validate = subparsers.add_parser("validate", help="validate a completed manifest")
    validate.add_argument("manifest", type=Path)
    validate.add_argument("--project-root", type=Path, default=Path.cwd())
    validate.add_argument("--verify-files", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "create":
            manifest = build_manifest(_load_json(args.spec), args.project_root)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(f"Created {args.output}")
            return 0
        manifest = _load_json(args.manifest)
        errors = validate_manifest(manifest, args.project_root, verify_files=args.verify_files)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"Run manifest error: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("Run manifest validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Validated run manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
