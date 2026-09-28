"""Validate the historical-problem benchmark catalog and common scoring rubric."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


REQUIRED_CASE_FIELDS = {
    "schema_version",
    "id",
    "competition",
    "year",
    "problem_code",
    "title",
    "official_source",
    "archetypes",
    "capabilities",
    "baseline",
    "validation_targets",
    "known_failure_modes",
}


def _mapping(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return data


def validate_catalog(catalog_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        catalog = _mapping(catalog_path)
    except (OSError, UnicodeError, yaml.YAMLError, ValueError) as exc:
        return [str(exc)]

    root = catalog_path.parent
    case_paths = catalog.get("cases")
    if not isinstance(case_paths, list) or not 8 <= len(case_paths) <= 12:
        errors.append(f"{catalog_path}: cases must contain 8 to 12 entries")
        case_paths = []

    rubric_path = root / str(catalog.get("rubric", ""))
    try:
        rubric = _mapping(rubric_path)
        criteria = rubric.get("criteria")
        if not isinstance(criteria, dict) or sum(criteria.values()) != 100:
            errors.append(f"{rubric_path}: criterion weights must sum to 100")
        gates = rubric.get("hard_gates")
        if not isinstance(gates, list) or not gates:
            errors.append(f"{rubric_path}: hard_gates must be a non-empty list")
    except (OSError, UnicodeError, yaml.YAMLError, ValueError, TypeError) as exc:
        errors.append(str(exc))

    seen_ids: set[str] = set()
    seen_problem_keys: set[tuple[str, int, str]] = set()
    archetypes: set[str] = set()
    for relative in case_paths:
        path = root / str(relative)
        try:
            case = _mapping(path)
        except (OSError, UnicodeError, yaml.YAMLError, ValueError) as exc:
            errors.append(str(exc))
            continue
        missing = REQUIRED_CASE_FIELDS - set(case)
        if missing:
            errors.append(f"{path}: missing fields: {', '.join(sorted(missing))}")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{path}: id must be a non-empty string")
        elif case_id in seen_ids:
            errors.append(f"{path}: duplicate id {case_id}")
        else:
            seen_ids.add(case_id)
        year = case.get("year")
        problem_code = case.get("problem_code")
        competition = case.get("competition")
        if isinstance(year, int) and isinstance(problem_code, str) and isinstance(competition, str):
            key = competition, year, problem_code
            if key in seen_problem_keys:
                errors.append(f"{path}: duplicate competition/year/problem {key}")
            seen_problem_keys.add(key)
        source = case.get("official_source")
        if not isinstance(source, str) or not source.startswith("https://www.mcm.edu.cn/"):
            errors.append(f"{path}: official_source must use the official CUMCM HTTPS site")
        for field in ("archetypes", "capabilities", "validation_targets", "known_failure_modes"):
            value = case.get(field)
            if not isinstance(value, list) or not value or any(not isinstance(x, str) for x in value):
                errors.append(f"{path}: {field} must be a non-empty string list")
        if isinstance(case.get("archetypes"), list):
            archetypes.update(x for x in case["archetypes"] if isinstance(x, str))
        if not isinstance(case.get("baseline"), str) or not case["baseline"].strip():
            errors.append(f"{path}: baseline must be a non-empty string")

    if len(archetypes) < 6:
        errors.append(f"{catalog_path}: benchmark suite covers only {len(archetypes)} archetypes")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", nargs="?", type=Path, default=Path("benchmarks/catalog.yaml"))
    args = parser.parse_args()
    errors = validate_catalog(args.catalog)
    if errors:
        print("Benchmark validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    catalog = _mapping(args.catalog)
    print(f"Validated {len(catalog['cases'])} historical benchmark cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
