"""Manage resumable, evidence-gated state for a modeling project."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePath, PureWindowsPath
from typing import Any


SCHEMA_VERSION = "1.1"
STAGES = ("intake", "analysis", "modeling", "validation", "writing", "review", "release")
COMPETITION_GATES = {
    "intake": (),
    "analysis": ("problem_source", "task_decomposition"),
    "modeling": ("data_audit", "model_selection", "decision_contract"),
    "validation": ("implementation", "machine_results", "quality_validation", "run_manifest"),
    "writing": (
        "validation_report",
        "quality_validation",
        "paper_spec",
        "evidence_index",
        "figure_registry",
    ),
    "review": (
        "manuscript",
        "decision_contract",
        "quality_validation",
        "figure_inventory",
        "cumcm_layout_validation",
        "visual_layout_audit",
        "paper_review_report",
        "submission_readiness",
        "submission_preflight",
        "support_archive",
        "support_manifest",
        "reproduction_report",
        "run_manifest",
    ),
    "release": ("review_report", "submission_checklist", "run_manifest"),
}
AUDIT_GATES = {
    **COMPETITION_GATES,
    "writing": COMPETITION_GATES["writing"] + ("claim_registry", "table_registry", "formula_registry"),
    "review": COMPETITION_GATES["review"]
    + (
        "main_pdf",
        "main_docx",
        "latex_compile_report",
        "docx_render_report",
        "independent_content_review",
        "review_hash_binding",
        "producer_registry",
        "signed_skill_trace",
    ),
}
RAPID_GATES = {
    "intake": (),
    "analysis": ("problem_source", "task_decomposition"),
    "modeling": ("model_selection",),
    "validation": ("implementation", "machine_results"),
    "writing": ("exploratory_summary",),
    "review": ("limitations",),
    "release": ("handoff",),
}
PROFILE_GATES = {"rapid": RAPID_GATES, "competition": COMPETITION_GATES, "audit": AUDIT_GATES}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_path(root: Path) -> Path:
    return root / ".modeling" / "project-state.json"


def _safe_relative(value: str) -> bool:
    path = PurePath(value)
    windows_path = PureWindowsPath(value)
    return (
        bool(value)
        and not path.is_absolute()
        and not path.anchor
        # Reject Windows drive paths even while this code runs on POSIX CI.
        and not windows_path.is_absolute()
        and not windows_path.drive
        and not value.startswith(("/", "\\"))
        and ".." not in path.parts
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_state(root: Path) -> dict[str, Any]:
    path = _state_path(root)
    if not path.is_file():
        raise FileNotFoundError(f"project state not found: {path}")
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or state.get("schema_version") not in {"1.0", SCHEMA_VERSION}:
        raise ValueError("unsupported or malformed project state")
    if state.get("schema_version") == "1.0":
        state["profile"] = "audit"
    return state


def _write_state(root: Path, state: dict[str, Any]) -> None:
    path = _state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def initialize(root: Path, project_id: str, manifest: str, profile: str = "competition") -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"project root is not a directory: {root}")
    if not project_id.strip():
        raise ValueError("project_id must be non-empty")
    if profile not in PROFILE_GATES:
        raise ValueError(f"unknown workflow profile: {profile}")
    if not _safe_relative(manifest):
        raise ValueError("manifest must be a safe project-relative path")
    path = _state_path(root)
    if path.exists():
        raise FileExistsError(f"project state already exists: {path}")
    now = _now()
    state = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "profile": profile,
        "current_stage": "intake",
        "completed_stages": [],
        "run_manifest": manifest,
        "evidence": {},
        "active_blocker": None,
        "blocker_history": [],
        "transitions": [],
        "created_at": now,
        "updated_at": now,
    }
    _write_state(root, state)
    return state


def _parse_evidence(
    root: Path,
    values: list[str],
    *,
    hash_evidence: bool,
) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"evidence must use role=path: {value!r}")
        role, relative = value.split("=", 1)
        if not role or not _safe_relative(relative):
            raise ValueError(f"invalid evidence role or path: {value!r}")
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"evidence file not found: {relative}")
        record: dict[str, Any] = {
            "path": relative.replace("\\", "/"),
            "bytes": path.stat().st_size,
            "verified_at": _now(),
        }
        if hash_evidence:
            record["sha256"] = _sha256(path)
        evidence[role] = record
    return evidence


def verify_evidence(root: Path, state: dict[str, Any]) -> list[str]:
    """Return missing or mutated evidence errors for all previously accepted gates."""
    errors: list[str] = []
    for role, record in sorted(state.get("evidence", {}).items()):
        relative = str(record.get("path", ""))
        if not _safe_relative(relative):
            errors.append(f"{role}: unsafe evidence path")
            continue
        path = root / relative
        if not path.is_file():
            errors.append(f"{role}: evidence file is missing: {relative}")
            continue
        if "sha256" in record and _sha256(path) != record.get("sha256"):
            errors.append(f"{role}: evidence hash changed: {relative}")
    return errors


def advance(root: Path, target: str, evidence_values: list[str], note: str) -> dict[str, Any]:
    root = root.resolve()
    state = _read_state(root)
    if state.get("active_blocker") is not None:
        raise ValueError("cannot advance while an active blocker exists")
    stale_errors = verify_evidence(root, state)
    if stale_errors:
        raise ValueError("previous gate evidence is stale: " + "; ".join(stale_errors))
    current = state.get("current_stage")
    if current not in STAGES or target not in STAGES:
        raise ValueError("unknown project stage")
    if STAGES.index(target) != STAGES.index(current) + 1:
        raise ValueError(f"must advance exactly one stage from {current}")
    profile = str(state.get("profile", "audit"))
    requirements = PROFILE_GATES[profile][target]
    evidence = _parse_evidence(root, evidence_values, hash_evidence=profile == "audit")
    expected_manifest = state["run_manifest"].replace("\\", "/")
    if "run_manifest" in requirements:
        supplied = evidence.get("run_manifest")
        if supplied is None or supplied["path"] != expected_manifest:
            raise ValueError(f"run_manifest evidence must use configured path {expected_manifest}")
    missing = [role for role in requirements if role not in evidence]
    if missing:
        raise ValueError("missing gate evidence: " + ", ".join(missing))
    if target == "review" and profile == "competition":
        delivered = {"main_pdf", "main_docx"}.intersection(evidence)
        if not delivered:
            raise ValueError("competition review requires main_pdf or main_docx")
        if "main_pdf" in delivered and "latex_compile_report" not in evidence:
            raise ValueError("PDF delivery requires latex_compile_report")
        if "main_docx" in delivered and "docx_render_report" not in evidence:
            raise ValueError("DOCX delivery requires docx_render_report")
    state["evidence"].update(evidence)
    state["completed_stages"].append(current)
    state["current_stage"] = target
    state["transitions"].append(
        {"from": current, "to": target, "at": _now(), "evidence_roles": sorted(evidence), "note": note}
    )
    _write_state(root, state)
    return state


def block(root: Path, reason: str, next_action: str) -> dict[str, Any]:
    root = root.resolve()
    state = _read_state(root)
    if state.get("active_blocker") is not None:
        raise ValueError("an active blocker already exists")
    if not reason.strip() or not next_action.strip():
        raise ValueError("reason and next_action must be non-empty")
    blocker = {"reason": reason, "next_action": next_action, "blocked_at": _now(), "resolved_at": None}
    state["active_blocker"] = blocker
    state["blocker_history"].append(blocker.copy())
    _write_state(root, state)
    return state


def resume(root: Path) -> dict[str, Any]:
    root = root.resolve()
    state = _read_state(root)
    if state.get("active_blocker") is None:
        raise ValueError("project has no active blocker")
    resolved_at = _now()
    state["active_blocker"]["resolved_at"] = resolved_at
    state["blocker_history"][-1]["resolved_at"] = resolved_at
    state["active_blocker"] = None
    _write_state(root, state)
    return state


def handoff(state: dict[str, Any]) -> dict[str, Any]:
    stage = state["current_stage"]
    if stage == "release" and state.get("active_blocker") is None:
        status = "complete"
    elif state.get("active_blocker") is not None:
        status = "blocked"
    else:
        status = "active"
    next_index = min(STAGES.index(stage) + 1, len(STAGES) - 1)
    next_stage = STAGES[next_index]
    return {
        "project_id": state["project_id"],
        "profile": state.get("profile", "audit"),
        "current_stage": stage,
        "status": status,
        "completed_stages": state["completed_stages"],
        "run_manifest": state["run_manifest"],
        "verified_evidence": [
            {"role": role, **record} for role, record in sorted(state["evidence"].items())
        ],
        "blocker": state.get("active_blocker"),
        "next_gate_requires": list(PROFILE_GATES[str(state.get("profile", "audit"))][next_stage]) if stage != "release" else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("status", "resume", "handoff", "verify"):
        command = subparsers.add_parser(action)
        command.add_argument("--project-root", type=Path, default=Path.cwd())
        if action == "handoff":
            command.add_argument("--output", type=Path)
    init = subparsers.add_parser("init")
    init.add_argument("--project-root", type=Path, default=Path.cwd())
    init.add_argument("--project-id", required=True)
    init.add_argument("--manifest", default="run-manifest.json")
    init.add_argument("--profile", choices=tuple(PROFILE_GATES), default="competition")
    advance_parser = subparsers.add_parser("advance")
    advance_parser.add_argument("--project-root", type=Path, default=Path.cwd())
    advance_parser.add_argument("--to", required=True, choices=STAGES)
    advance_parser.add_argument("--evidence", action="append", default=[])
    advance_parser.add_argument("--note", default="")
    block_parser = subparsers.add_parser("block")
    block_parser.add_argument("--project-root", type=Path, default=Path.cwd())
    block_parser.add_argument("--reason", required=True)
    block_parser.add_argument("--next-action", required=True)
    args = parser.parse_args()
    try:
        if args.action == "init":
            result = initialize(args.project_root, args.project_id, args.manifest, args.profile)
        elif args.action == "advance":
            result = advance(args.project_root, args.to, args.evidence, args.note)
        elif args.action == "block":
            result = block(args.project_root, args.reason, args.next_action)
        elif args.action == "resume":
            result = resume(args.project_root)
        else:
            state = _read_state(args.project_root.resolve())
            if args.action == "handoff":
                result = handoff(state)
            elif args.action == "verify":
                errors = verify_evidence(args.project_root.resolve(), state)
                result = {"status": "PASS" if not errors else "FAIL", "errors": errors}
            else:
                result = state
            if args.action == "handoff" and args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"Project state error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
