#!/usr/bin/env python3
"""Execute one standard Skill under the repository's trace and contract runtime."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from .skill_contracts import validate_records
    from .skill_runtime import (
        STANDARD_SKILLS,
        fail_skill_run,
        finish_skill_run,
        start_skill_run,
    )
except ImportError:  # direct execution from the repository checkout
    from scripts.skill_contracts import validate_records
    from scripts.skill_runtime import (
        STANDARD_SKILLS,
        fail_skill_run,
        finish_skill_run,
        start_skill_run,
    )


def main(argv: list[str] | None = None, *, default_skill: str | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--skill", choices=STANDARD_SKILLS, default=default_skill)
    parser.add_argument("--skill-path", required=True)
    parser.add_argument("--profile", choices=("rapid", "competition", "audit"), default="competition")
    parser.add_argument("--input", action="append", default=[], metavar="ROLE=PATH")
    parser.add_argument("--output", action="append", default=[], metavar="ROLE=PATH")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="command to execute; prefix with --")
    args = parser.parse_args(argv)
    if not args.skill:
        parser.error("--skill is required")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    outputs = []
    try:
        for value in args.output:
            role, path = value.split("=", 1)
            if not role.strip() or not path.strip():
                raise ValueError(f"invalid output role/path: {value!r}")
            outputs.append((role, path))
    except ValueError as exc:
        parser.error(str(exc))
    start = start_skill_run(
        args.project_root,
        args.project_id,
        args.skill,
        skill_path=args.skill_path,
        inputs=args.input,
        command_or_invocation=" ".join(command),
        profile=args.profile,
    )
    if not command:
        terminal = fail_skill_run(args.project_root, start["run_id"], "no execution command supplied", exit_code=2)
        print(json.dumps(terminal, ensure_ascii=False, indent=2))
        return 2
    contract_errors = validate_records(
        args.skill,
        start["inputs"],
        [{"role": role} for role, _ in outputs],
        profile=args.profile,
    )
    if contract_errors:
        terminal = finish_skill_run(
            args.project_root,
            start["run_id"],
            status="BLOCKED",
            warnings=["preflight contract violation", *contract_errors],
            exit_code=1,
        )
        print(json.dumps(terminal, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    completed = subprocess.run(command, cwd=args.project_root, text=True, capture_output=True, check=False)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode:
        terminal = fail_skill_run(args.project_root, start["run_id"], f"command exited {completed.returncode}", exit_code=completed.returncode)
        print(json.dumps(terminal, ensure_ascii=False, indent=2), file=sys.stderr)
        return completed.returncode
    try:
        terminal = finish_skill_run(args.project_root, start["run_id"], outputs=outputs)
    except (OSError, ValueError) as exc:
        terminal = fail_skill_run(args.project_root, start["run_id"], str(exc), exit_code=1)
        print(json.dumps(terminal, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(terminal, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
