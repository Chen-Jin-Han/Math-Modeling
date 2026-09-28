"""Enforce overall and per-module coverage thresholds from a JSON policy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _percentage(summary: dict[str, Any]) -> float:
    if isinstance(summary.get("percent_covered"), (int, float)):
        return float(summary["percent_covered"])
    statements = summary.get("num_statements")
    covered = summary.get("covered_lines")
    if not isinstance(statements, int) or not isinstance(covered, int) or statements <= 0:
        raise ValueError("coverage summary lacks a usable percentage")
    return covered / statements * 100.0


def check_coverage(report_path: Path, policy_path: Path) -> tuple[list[str], dict[str, float]]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    observed: dict[str, float] = {}

    overall = _percentage(report.get("totals", {}))
    observed["overall"] = overall
    overall_minimum = float(policy["overall_minimum"])
    if overall + 1e-9 < overall_minimum:
        errors.append(f"overall: {overall:.2f}% < {overall_minimum:.2f}%")

    files = report.get("files")
    if not isinstance(files, dict):
        raise ValueError("coverage report files must be an object")
    normalized = {str(path).replace("\\", "/"): data for path, data in files.items()}
    critical = policy.get("critical_modules")
    if not isinstance(critical, dict) or not critical:
        raise ValueError("policy critical_modules must be a non-empty object")
    for module, threshold_value in critical.items():
        matches = [data for path, data in normalized.items() if path.endswith(f"/{module}")]
        if len(matches) != 1:
            errors.append(f"{module}: expected exactly one coverage entry, found {len(matches)}")
            continue
        percentage = _percentage(matches[0].get("summary", {}))
        observed[module] = percentage
        threshold = float(threshold_value)
        if percentage + 1e-9 < threshold:
            errors.append(f"{module}: {percentage:.2f}% < {threshold:.2f}%")
    return errors, observed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, nargs="?", default=Path("coverage.json"))
    parser.add_argument("--policy", type=Path, default=Path("coverage-policy.json"))
    args = parser.parse_args()
    try:
        errors, observed = check_coverage(args.report, args.policy)
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"Coverage policy error: {exc}", file=sys.stderr)
        return 2
    print("Coverage results:")
    for name, percentage in observed.items():
        print(f"- {name}: {percentage:.2f}%")
    if errors:
        print("Coverage policy failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Coverage policy passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
