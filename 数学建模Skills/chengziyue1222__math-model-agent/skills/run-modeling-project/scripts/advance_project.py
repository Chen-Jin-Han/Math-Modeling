"""Advance a project through an explicit, evidence-bound stage plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from project_state import STAGES, _read_state, advance, handoff, verify_evidence


def load_plan(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("transitions"), list):
        raise ValueError("project stage plan requires a transitions array")
    return value


def evidence_values(value: Any) -> list[str]:
    if not isinstance(value, dict):
        raise ValueError("transition evidence must be an object")
    rendered = []
    for role, relative in value.items():
        if not isinstance(role, str) or not isinstance(relative, str):
            raise ValueError("transition evidence must map string roles to string paths")
        rendered.append(f"{role}={relative}")
    return rendered


def main(root: Path, plan_path: Path, stage_gate_output: Path, handoff_output: Path) -> None:
    root = root.resolve()
    plan = load_plan(plan_path)
    state = _read_state(root)
    expected_id = plan.get("project_id")
    if expected_id and expected_id != state.get("project_id"):
        raise ValueError("stage plan project_id does not match project state")

    for transition in plan["transitions"]:
        if not isinstance(transition, dict):
            raise ValueError("each transition must be an object")
        target = transition.get("to")
        if target not in STAGES:
            raise ValueError(f"unknown target stage: {target!r}")
        state = _read_state(root)
        current = state["current_stage"]
        if STAGES.index(target) <= STAGES.index(current):
            continue
        if STAGES.index(target) != STAGES.index(current) + 1:
            raise ValueError(f"stage plan skips from {current} to {target}")
        advance(
            root,
            target,
            evidence_values(transition.get("evidence")),
            str(transition.get("note", "")),
        )

    state = _read_state(root)
    errors = verify_evidence(root, state)
    stage_gate = {
        "schema_version": "1.0",
        "status": "PASS" if not errors else "FAIL",
        "project_id": state["project_id"],
        "current_stage": state["current_stage"],
        "completed_stages": state["completed_stages"],
        "evidence_hash_errors": errors,
    }
    if errors:
        raise ValueError("project stage evidence is stale: " + "; ".join(errors))
    stage_gate_output.parent.mkdir(parents=True, exist_ok=True)
    stage_gate_output.write_text(json.dumps(stage_gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    handoff_output.parent.mkdir(parents=True, exist_ok=True)
    handoff_output.write_text(json.dumps(handoff(state), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--stage-gate-output", type=Path, required=True)
    parser.add_argument("--handoff-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        main(args.project_root, args.plan, args.stage_gate_output, args.handoff_output)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"Project stage plan error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
