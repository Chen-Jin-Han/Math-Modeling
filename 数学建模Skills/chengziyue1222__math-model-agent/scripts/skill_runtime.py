#!/usr/bin/env python3
"""Record and verify tamper-evident executions of standard modeling Skills.

The JSONL trace is an event log: a ``start`` event is appended before work starts and
one terminal event is appended afterwards.  Terminal records retain the original input
hashes and include output hashes plus producer registrations.  A project-local HMAC key
protects the event chain against accidental or hand-written trace files.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePath
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from .skill_contracts import CONTRACT_VERSION
except ImportError:  # direct execution from the repository checkout
    from scripts.skill_contracts import CONTRACT_VERSION


RUNTIME_VERSION = "1.3"
STANDARD_SKILLS = (
    "run-modeling-project",
    "select-model",
    "analyze-model-data",
    "research-model-literature",
    "solve-model",
    "make-model-figures",
    "write-model-paper",
    "review-model-paper",
)
TERMINAL_STATUSES = {"PASS", "FAIL", "BLOCKED"}
ALLOWED_EXTERNAL_PRODUCERS = {"compile-latex", "paper-docx", "paper-render-audit"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative(value: str) -> bool:
    path = PurePath(value)
    return bool(value) and not path.is_absolute() and not path.anchor and ".." not in path.parts


def _relative_record(root: Path, value: str, *, hash_file: bool = True) -> dict[str, Any]:
    if not _safe_relative(value):
        raise ValueError(f"path must be project-relative: {value!r}")
    path = root / value
    if not path.is_file():
        raise FileNotFoundError(f"tracked file does not exist: {value}")
    record: dict[str, Any] = {"path": value.replace("\\", "/"), "bytes": path.stat().st_size}
    if hash_file:
        record["sha256"] = _sha256(path)
    return record


def _input_records(
    root: Path,
    values: list[str | tuple[str, str]],
    *,
    hash_files: bool,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for value in values:
        if isinstance(value, tuple):
            role, relative = value
        elif "=" in value:
            role, relative = value.split("=", 1)
        else:
            role, relative = "input", value
        record = _relative_record(root, relative, hash_file=hash_files)
        record["role"] = role
        records.append(record)
    return records


def _trace_path(root: Path) -> Path:
    return root / "manifests" / "skill-runs.jsonl"


def _producer_path(root: Path) -> Path:
    return root / "manifests" / "artifact-producers.json"


def _key_path(root: Path) -> Path:
    return root / ".modeling" / "skill-runtime.key"


def _snapshot_path(root: Path, run_id: str) -> Path:
    return root / ".modeling" / "runtime-snapshots" / f"{run_id}.json"


def _project_snapshot(root: Path) -> dict[str, dict[str, Any]]:
    ignored = {
        ".git",
        ".modeling",
        ".test-tmp",
        "__pycache__",
        "node_modules",
        "venv",
        ".venv",
    }
    snapshot: dict[str, dict[str, Any]] = {}
    for path in root.rglob("*"):
        if not path.is_file() or any(part in ignored for part in path.relative_to(root).parts):
            continue
        relative = str(path.relative_to(root)).replace("\\", "/")
        if relative in {"manifests/skill-runs.jsonl", "manifests/artifact-producers.json"}:
            continue
        stat = path.stat()
        snapshot[relative] = {
            "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": _sha256(path),
        }
    return snapshot


def _write_snapshot(root: Path, run_id: str, snapshot: dict[str, dict[str, Any]]) -> Path:
    path = _snapshot_path(root, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return path


def _filesystem_delta(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    return {
        "created": sorted(set(after) - set(before)),
        "modified": sorted(
            path
            for path in set(before) & set(after)
            if before[path].get("sha256") != after[path].get("sha256")
        ),
        "deleted": sorted(set(before) - set(after)),
    }


def _key(root: Path) -> bytes:
    path = _key_path(root)
    if path.is_file():
        return path.read_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    key = os.urandom(32)
    path.write_bytes(key)
    return key


def _signature(key: bytes, record: dict[str, Any]) -> str:
    payload = {name: value for name, value in record.items() if name != "trace_signature"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(key, encoded, hashlib.sha256).hexdigest()


def _append(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    record = dict(record)
    if record.get("profile", "audit") == "audit":
        record["trace_signature"] = _signature(_key(root), record)
    path = _trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def _read_events(root: Path) -> list[dict[str, Any]]:
    path = _trace_path(root)
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid trace JSON at line {number}: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"trace line {number} is not an object")
        events.append(record)
    return events


def _implementation_hashes(skill_path: str | Path | None) -> dict[str, str]:
    if skill_path is None:
        return {}
    path = Path(skill_path)
    if path.is_file():
        return {path.name: _sha256(path)}
    if path.is_dir():
        return {
            str(item.relative_to(path)).replace("\\", "/"): _sha256(item)
            for item in sorted(path.rglob("*"))
            if item.is_file()
        }
    return {}


def _implementation_digest(hashes: dict[str, str]) -> str | None:
    """Hash the complete implementation map so directory-backed Skills have an identity."""
    if not hashes:
        return None
    payload = json.dumps(hashes, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def start_skill_run(
    project_root: str | Path,
    project_id: str,
    skill: str,
    *,
    skill_path: str | Path | None = None,
    inputs: list[str | tuple[str, str]] | None = None,
    command_or_invocation: str = "",
    profile: str = "competition",
) -> dict[str, Any]:
    """Append the required start event and return its stable run identifier."""
    root = Path(project_root).resolve()
    if skill not in STANDARD_SKILLS:
        raise ValueError(f"unknown standard skill: {skill}")
    if not project_id.strip():
        raise ValueError("project_id must be non-empty")
    if profile not in {"rapid", "competition", "audit"}:
        raise ValueError(f"unknown workflow profile: {profile}")
    audit = profile == "audit"
    input_records = _input_records(root, inputs or [], hash_files=audit)
    implementation_hashes = _implementation_hashes(skill_path) if audit else {}
    run_id = uuid.uuid4().hex
    snapshot_file = _write_snapshot(root, run_id, _project_snapshot(root)) if audit else None
    record = {
        "event": "start",
        "runtime_version": RUNTIME_VERSION,
        "contract_version": CONTRACT_VERSION,
        "profile": profile,
        "run_id": run_id,
        "project_id": project_id,
        "skill": skill,
        "skill_path": str(skill_path or ""),
        "skill_sha256": _implementation_digest(implementation_hashes),
        "implementation_hashes": implementation_hashes,
        "filesystem_snapshot_path": str(snapshot_file.relative_to(root)).replace("\\", "/") if snapshot_file else None,
        "filesystem_snapshot_sha256": _sha256(snapshot_file) if snapshot_file else None,
        "started_at": _now(),
        "inputs": input_records,
        "command_or_invocation": command_or_invocation,
        "status": "RUNNING",
    }
    return _append(root, record)


def _latest_start(root: Path, run_id: str) -> dict[str, Any]:
    for event in reversed(_read_events(root)):
        if event.get("run_id") == run_id and event.get("event") == "start":
            return event
    raise ValueError(f"start event not found for run_id={run_id}")


def _write_producers(root: Path, registrations: list[dict[str, Any]]) -> None:
    path = _producer_path(root)
    existing: list[dict[str, Any]] = []
    if path.is_file():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, list):
            raise ValueError("artifact producer registry must be a JSON array")
        existing = [item for item in loaded if isinstance(item, dict)]
    by_path = {str(item.get("path")): item for item in existing}
    by_path.update({str(item["path"]): item for item in registrations})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(by_path.values(), key=lambda item: item["path"]), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def finish_skill_run(
    project_root: str | Path,
    run_id: str,
    *,
    outputs: list[tuple[str, str]] | None = None,
    status: str = "PASS",
    warnings: list[str] | None = None,
    manual_interventions: list[str] | None = None,
    fallback_scripts: list[str] | None = None,
    fallback_reason: str | None = None,
    exit_code: int = 0,
) -> dict[str, Any]:
    """Append a terminal event and register output producer records."""
    root = Path(project_root).resolve()
    if status not in TERMINAL_STATUSES:
        raise ValueError(f"terminal status must be one of {sorted(TERMINAL_STATUSES)}")
    start = _latest_start(root, run_id)
    output_records: list[dict[str, Any]] = []
    for role, relative in outputs or []:
        if not role.strip():
            raise ValueError("output role must be non-empty")
        record = _relative_record(
            root,
            relative,
            hash_file=start.get("profile", "audit") == "audit",
        )
        record["role"] = role
        output_records.append(record)
    finished_at = _now()
    duration = max(0.0, time.time() - datetime.fromisoformat(start["started_at"]).timestamp())
    audit = start.get("profile", "audit") == "audit"
    filesystem_delta: dict[str, list[str]] = {"created": [], "modified": [], "deleted": []}
    if audit:
        snapshot_file = root / str(start.get("filesystem_snapshot_path", ""))
        expected_snapshot_hash = str(start.get("filesystem_snapshot_sha256", ""))
        if not snapshot_file.is_file() or _sha256(snapshot_file) != expected_snapshot_hash:
            raise ValueError(f"filesystem snapshot missing or tampered: {snapshot_file}")
        before = json.loads(snapshot_file.read_text(encoding="utf-8"))
        filesystem_delta = _filesystem_delta(before, _project_snapshot(root))
    record = {
        "event": "finish",
        "runtime_version": RUNTIME_VERSION,
        "contract_version": start.get("contract_version", CONTRACT_VERSION),
        "profile": start.get("profile", "audit"),
        "run_id": run_id,
        "project_id": start["project_id"],
        "skill": start["skill"],
        "started_at": start["started_at"],
        "finished_at": finished_at,
        "duration_seconds": round(duration, 6),
        "inputs": start["inputs"],
        "outputs": output_records,
        "command_or_invocation": start["command_or_invocation"],
        "exit_code": exit_code,
        "status": status,
        "warnings": warnings or [],
        "manual_interventions": manual_interventions or [],
        "fallback_scripts": fallback_scripts or [],
        "fallback_reason": fallback_reason,
        "filesystem_delta": filesystem_delta,
    }
    terminal = _append(root, record)
    if status == "PASS" and audit:
        registrations = [
            {
                **item,
                "producer_type": "skill",
                "producer_name": start["skill"],
                "producer_version": f"{RUNTIME_VERSION}/contract-{start.get('contract_version', CONTRACT_VERSION)}",
                "producer_sha256": start.get("skill_sha256"),
                "run_id": run_id,
                "input_hashes": {item["path"]: item["sha256"] for item in start["inputs"]},
                "output_sha256": item["sha256"],
            }
            for item in output_records
        ]
        _write_producers(root, registrations)
    return terminal


def register_external_artifact(
    project_root: str | Path,
    *,
    role: str,
    path: str,
    producer_name: str,
    producer_version: str,
    input_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Register a rendered artifact produced outside the eight standard Skills."""
    root = Path(project_root).resolve()
    if producer_name not in ALLOWED_EXTERNAL_PRODUCERS:
        raise ValueError(f"external producer is not allowed: {producer_name}")
    output = _relative_record(root, path)
    inputs = [_relative_record(root, item) for item in input_paths or []]
    registration = {
        **output,
        "role": role,
        "producer_type": "external_tool",
        "producer_name": producer_name,
        "producer_version": producer_version,
        "producer_sha256": None,
        "run_id": f"external-{uuid.uuid4().hex}",
        "input_hashes": {item["path"]: item["sha256"] for item in inputs},
        "output_sha256": output["sha256"],
        "registered_at": _now(),
    }
    _write_producers(root, [registration])
    return registration


def fail_skill_run(project_root: str | Path, run_id: str, reason: str, *, exit_code: int = 1) -> dict[str, Any]:
    return finish_skill_run(project_root, run_id, status="FAIL", warnings=[reason], exit_code=exit_code)


def list_project_skill_runs(project_root: str | Path, project_id: str | None = None) -> list[dict[str, Any]]:
    root = Path(project_root).resolve()
    starts: dict[str, dict[str, Any]] = {}
    terminal: dict[str, dict[str, Any]] = {}
    for event in _read_events(root):
        if project_id and event.get("project_id") != project_id:
            continue
        if event.get("event") == "start":
            starts[str(event.get("run_id"))] = event
        elif event.get("event") == "finish":
            terminal[str(event.get("run_id"))] = event
    records = []
    for run_id, start in starts.items():
        records.append(terminal.get(run_id, start))
    return sorted(records, key=lambda item: str(item.get("started_at", "")))


def validate_skill_run(
    project_root: str | Path,
    *,
    project_id: str | None = None,
    required_skills: list[str] | None = None,
    verify_files: bool = True,
    profile: str | None = None,
) -> list[str]:
    """Return trace, integrity, and required-producer violations."""
    root = Path(project_root).resolve()
    errors: list[str] = []
    try:
        events = _read_events(root)
        audit_events = [event for event in events if event.get("profile", "audit") == "audit"]
        key_path = _key_path(root)
        if not audit_events:
            key = b""
        elif not key_path.is_file():
            return ["skill trace has no runtime key; possible hand-written trace"]
        else:
            key = key_path.read_bytes()
    except (OSError, UnicodeError, ValueError) as exc:
        return [f"skill trace unreadable: {exc}"]
    starts: dict[str, dict[str, Any]] = {}
    finished: dict[str, dict[str, Any]] = {}
    for index, event in enumerate(events, 1):
        event_profile = str(event.get("profile", "audit"))
        if event_profile == "audit" and event.get("trace_signature") != _signature(key, event):
            errors.append(f"trace_signature_invalid at event {index}")
        if profile and event_profile != profile:
            continue
        if project_id and event.get("project_id") != project_id:
            continue
        run_id = str(event.get("run_id", ""))
        if event.get("event") == "start":
            if run_id in starts:
                errors.append(f"duplicate start event for {run_id}")
            starts[run_id] = event
        elif event.get("event") == "finish":
            if run_id not in starts:
                errors.append(f"finish without start for {run_id}")
            finished[run_id] = event
        else:
            errors.append(f"unknown trace event at {index}")
    # A project legitimately reruns downstream Skills after correcting an input.
    # Historical events remain signed audit evidence, but only the newest
    # successful run of each Skill is the current artifact assertion.  Requiring
    # every historical hash to equal today's files would make any honest rerun
    # permanently fail validation and encourage trace deletion.
    latest_successful: dict[str, str] = {}
    for run_id, start in starts.items():
        final = finished.get(run_id)
        if final and final.get("skill") == start.get("skill") and final.get("status") == "PASS":
            latest_successful[str(start.get("skill"))] = run_id

    passed = set(latest_successful)
    for run_id, start in starts.items():
        audit = start.get("profile", "audit") == "audit"
        if verify_files and audit:
            snapshot_path = root / str(start.get("filesystem_snapshot_path", ""))
            if (
                not snapshot_path.is_file()
                or start.get("filesystem_snapshot_sha256") != _sha256(snapshot_path)
            ):
                errors.append(f"filesystem_snapshot_hash_mismatch: {run_id}")
        final = finished.get(run_id)
        if final is None:
            errors.append(f"unfinished skill run: {run_id}")
            continue
        if final.get("skill") != start.get("skill") or final.get("status") not in TERMINAL_STATUSES:
            errors.append(f"invalid terminal record: {run_id}")
            continue
        if verify_files and audit and latest_successful.get(str(start.get("skill"))) == run_id:
            for label, records in (("input", start.get("inputs", [])), ("output", final.get("outputs", []))):
                for item in records:
                    if not isinstance(item, dict):
                        errors.append(f"invalid {label} record in {run_id}")
                        continue
                    # The orchestration trace is append-only: its terminal event
                    # necessarily changes the trace file after its own start.
                    # Signature verification above still authenticates it.
                    if label == "input" and item.get("role") == "skill_trace":
                        continue
                    path = root / str(item.get("path", ""))
                    if not path.is_file() or item.get("sha256") != _sha256(path):
                        errors.append(f"{label}_hash_mismatch: {item.get('path')} ({run_id})")
    for skill in required_skills or []:
        if skill not in STANDARD_SKILLS:
            errors.append(f"unknown required skill: {skill}")
        elif skill not in passed:
            errors.append(f"missing_passed_skill_run: {skill}")
    return errors


def _parse_outputs(values: list[str]) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for value in values:
        if "=" not in value:
            raise ValueError(f"output must use role=path: {value!r}")
        role, path = value.split("=", 1)
        parsed.append((role, path))
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    start = commands.add_parser("start")
    start.add_argument("--project-root", type=Path, required=True)
    start.add_argument("--project-id", required=True)
    start.add_argument("--skill", choices=STANDARD_SKILLS, required=True)
    start.add_argument("--skill-path")
    start.add_argument("--profile", choices=("rapid", "competition", "audit"), default="competition")
    start.add_argument("--input", action="append", default=[])
    start.add_argument("--command", default="")
    finish = commands.add_parser("finish")
    finish.add_argument("--project-root", type=Path, required=True)
    finish.add_argument("--run-id", required=True)
    finish.add_argument("--output", action="append", default=[])
    finish.add_argument("--status", choices=sorted(TERMINAL_STATUSES), default="PASS")
    finish.add_argument("--warning", action="append", default=[])
    finish.add_argument("--exit-code", type=int, default=0)
    fail = commands.add_parser("fail")
    fail.add_argument("--project-root", type=Path, required=True)
    fail.add_argument("--run-id", required=True)
    fail.add_argument("--reason", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--project-root", type=Path, required=True)
    validate.add_argument("--project-id")
    validate.add_argument("--require-skill", action="append", default=[])
    validate.add_argument("--no-verify-files", action="store_true")
    validate.add_argument("--profile", choices=("rapid", "competition", "audit"))
    listing = commands.add_parser("list")
    listing.add_argument("--project-root", type=Path, required=True)
    listing.add_argument("--project-id")
    external = commands.add_parser("register-external")
    external.add_argument("--project-root", type=Path, required=True)
    external.add_argument("--role", required=True)
    external.add_argument("--path", required=True)
    external.add_argument("--producer", choices=sorted(ALLOWED_EXTERNAL_PRODUCERS), required=True)
    external.add_argument("--producer-version", required=True)
    external.add_argument("--input", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        if args.action == "start":
            result = start_skill_run(
                args.project_root,
                args.project_id,
                args.skill,
                skill_path=args.skill_path,
                inputs=args.input,
                command_or_invocation=args.command,
                profile=args.profile,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.action == "finish":
            result = finish_skill_run(args.project_root, args.run_id, outputs=_parse_outputs(args.output), status=args.status, warnings=args.warning, exit_code=args.exit_code)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.action == "fail":
            print(json.dumps(fail_skill_run(args.project_root, args.run_id, args.reason), ensure_ascii=False, indent=2))
            return 0
        if args.action == "list":
            print(json.dumps(list_project_skill_runs(args.project_root, args.project_id), ensure_ascii=False, indent=2))
            return 0
        if args.action == "register-external":
            result = register_external_artifact(
                args.project_root,
                role=args.role,
                path=args.path,
                producer_name=args.producer,
                producer_version=args.producer_version,
                input_paths=args.input,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        errors = validate_skill_run(
            args.project_root,
            project_id=args.project_id,
            required_skills=args.require_skill,
            verify_files=not args.no_verify_files,
            profile=args.profile,
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"skill runtime error: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("skill trace validation failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print("skill trace validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
