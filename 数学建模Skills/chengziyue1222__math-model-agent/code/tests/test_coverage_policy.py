import json

from scripts.check_coverage import check_coverage


def _write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def test_coverage_policy_accepts_overall_and_critical_thresholds(tmp_path):
    report = {
        "totals": {"percent_covered": 70.0},
        "files": {
            "code\\algorithms\\graph_theory.py": {"summary": {"percent_covered": 82.0}},
        },
    }
    policy = {"overall_minimum": 65, "critical_modules": {"graph_theory.py": 80}}
    report_path = tmp_path / "coverage.json"
    policy_path = tmp_path / "policy.json"
    _write_json(report_path, report)
    _write_json(policy_path, policy)

    errors, observed = check_coverage(report_path, policy_path)

    assert errors == []
    assert observed == {"overall": 70.0, "graph_theory.py": 82.0}


def test_coverage_policy_reports_all_failures_and_missing_modules(tmp_path):
    report = {
        "totals": {"num_statements": 100, "covered_lines": 60},
        "files": {
            "code/algorithms/graph_theory.py": {"summary": {"percent_covered": 79.9}},
        },
    }
    policy = {
        "overall_minimum": 65,
        "critical_modules": {"graph_theory.py": 80, "monte_carlo.py": 80},
    }
    report_path = tmp_path / "coverage.json"
    policy_path = tmp_path / "policy.json"
    _write_json(report_path, report)
    _write_json(policy_path, policy)

    errors, _ = check_coverage(report_path, policy_path)

    assert errors == [
        "overall: 60.00% < 65.00%",
        "graph_theory.py: 79.90% < 80.00%",
        "monte_carlo.py: expected exactly one coverage entry, found 0",
    ]
