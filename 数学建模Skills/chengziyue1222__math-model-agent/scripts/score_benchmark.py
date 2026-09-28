"""Score a benchmark submission from a structured, evidence-linked scorecard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


def _load(path: Path):
    loader = json.loads if path.suffix.lower() == ".json" else yaml.safe_load
    return loader(path.read_text(encoding="utf-8"))


def score(scorecard_path: Path, rubric_path: Path, *, check_evidence: bool = True) -> dict:
    rubric = _load(rubric_path)
    scorecard = _load(scorecard_path)
    if not isinstance(rubric, dict) or not isinstance(scorecard, dict):
        raise ValueError("rubric and scorecard must be mappings")

    required_gates = rubric["hard_gates"]
    gates = scorecard.get("hard_gates", {})
    failed_gates = [gate for gate in required_gates if gates.get(gate) is not True]
    criteria = scorecard.get("criteria", {})
    weighted_score = 0.0
    evidence_count = 0
    errors: list[str] = []
    minimum = float(rubric["score_scale"]["minimum"])
    maximum = float(rubric["score_scale"]["maximum"])

    for name, weight in rubric["criteria"].items():
        item = criteria.get(name)
        if not isinstance(item, dict):
            errors.append(f"missing criterion: {name}")
            continue
        value = item.get("score")
        if not isinstance(value, (int, float)) or not minimum <= value <= maximum:
            errors.append(f"{name}: score must be between {minimum:g} and {maximum:g}")
            continue
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{name}: at least one evidence path is required")
            continue
        for relative in evidence:
            if not isinstance(relative, str) or not relative.strip():
                errors.append(f"{name}: evidence paths must be non-empty strings")
                continue
            evidence_count += 1
            if check_evidence and not (scorecard_path.parent / relative).exists():
                errors.append(f"{name}: evidence file does not exist: {relative}")
        weighted_score += float(weight) * (float(value) - minimum) / (maximum - minimum)

    passed = not errors and not failed_gates and weighted_score >= float(rubric["pass_score"])
    return {
        "schema_version": 1,
        "case_id": scorecard.get("case_id"),
        "score": round(weighted_score, 2),
        "pass_score": rubric["pass_score"],
        "passed": passed,
        "failed_gates": failed_gates,
        "evidence_count": evidence_count,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scorecard", type=Path)
    parser.add_argument("--rubric", type=Path, default=Path("benchmarks/rubric.yaml"))
    parser.add_argument("--skip-evidence-check", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = score(
            args.scorecard,
            args.rubric,
            check_evidence=not args.skip_evidence_check,
        )
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(f"Benchmark scoring failed: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
