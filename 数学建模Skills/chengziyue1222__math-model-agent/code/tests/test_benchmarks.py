import json
from pathlib import Path

import yaml

from scripts.score_benchmark import score
from scripts.validate_benchmarks import validate_catalog


ROOT = Path(__file__).resolve().parents[2]


def test_historical_benchmark_catalog_is_valid():
    assert validate_catalog(ROOT / "benchmarks" / "catalog.yaml") == []


def test_catalog_contains_twelve_diverse_cases():
    catalog = yaml.safe_load((ROOT / "benchmarks" / "catalog.yaml").read_text(encoding="utf-8"))
    cases = [
        yaml.safe_load((ROOT / "benchmarks" / relative).read_text(encoding="utf-8"))
        for relative in catalog["cases"]
    ]
    assert len(cases) == 12
    assert len({case["id"] for case in cases}) == 12
    assert len({kind for case in cases for kind in case["archetypes"]}) >= 10


def test_scorecard_computes_weighted_score_with_evidence(tmp_path):
    rubric = ROOT / "benchmarks" / "rubric.yaml"
    criteria = yaml.safe_load(rubric.read_text(encoding="utf-8"))["criteria"]
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("verified", encoding="utf-8")
    scorecard = {
        "case_id": "cumcm-2022-a",
        "hard_gates": {
            "source_traceability": True,
            "reproducible_result": True,
            "answers_all_subproblems": True,
            "no_fabricated_evidence": True,
        },
        "criteria": {
            name: {"score": 4, "evidence": ["evidence.txt"]} for name in criteria
        },
    }
    path = tmp_path / "scorecard.json"
    path.write_text(json.dumps(scorecard), encoding="utf-8")

    result = score(path, rubric)

    assert result["score"] == 80.0
    assert result["passed"] is True
    assert result["evidence_count"] == len(criteria)


def test_failed_hard_gate_blocks_high_scoring_submission(tmp_path):
    rubric = ROOT / "benchmarks" / "rubric.yaml"
    criteria = yaml.safe_load(rubric.read_text(encoding="utf-8"))["criteria"]
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("verified", encoding="utf-8")
    scorecard = {
        "case_id": "cumcm-2022-a",
        "hard_gates": {
            "source_traceability": False,
            "reproducible_result": True,
            "answers_all_subproblems": True,
            "no_fabricated_evidence": True,
        },
        "criteria": {
            name: {"score": 5, "evidence": ["evidence.txt"]} for name in criteria
        },
    }
    path = tmp_path / "scorecard.json"
    path.write_text(json.dumps(scorecard), encoding="utf-8")

    result = score(path, rubric)

    assert result["score"] == 100.0
    assert result["passed"] is False
    assert result["failed_gates"] == ["source_traceability"]
