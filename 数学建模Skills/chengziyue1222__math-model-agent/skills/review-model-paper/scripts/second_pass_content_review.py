"""Produce a structured, hash-bound second-pass review for a modeling paper."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT / "code") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "code"))

from algorithms.modeling_contracts import validate_contract_artifacts


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _contains(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token.lower() in text for token in tokens)


def main(
    project_root: Path,
    manuscript: Path,
    decision_contract: Path,
    quality_validation: Path,
) -> None:
    root = project_root.resolve()
    paper = manuscript.resolve()
    contract_path = decision_contract.resolve()
    quality_path = quality_validation.resolve()
    text = paper.read_text(encoding="utf-8").lower()
    contract = load_object(contract_path)
    quality = load_object(quality_path)
    questions = [row for row in contract.get("questions", []) if isinstance(row, dict)]
    artifact_issues = validate_contract_artifacts(contract, root)

    expected_markers = []
    chinese_markers = ("问题一", "问题二", "问题三", "问题四", "问题五", "问题六")
    for index, question in enumerate(questions):
        qid = str(question.get("id", "")).lower()
        markers = tuple(filter(None, (qid, chinese_markers[index] if index < len(chinese_markers) else "")))
        expected_markers.append({"id": qid or f"question-{index + 1}", "present": _contains(text, markers)})

    requires_uncertainty = any(row.get("requires_uncertainty") for row in questions)
    requires_dynamic = any(row.get("requires_dynamic_state") for row in questions)
    requires_tradeoff = any(row.get("requires_tradeoff") for row in questions)
    requires_baseline = any(row.get("requires_baseline") for row in questions)
    quality_discussion = {
        "uncertainty": not requires_uncertainty or _contains(text, ("不确定", "压力", "holdout", "stress")),
        "dynamic": not requires_dynamic or _contains(text, ("库存", "状态", "inventory", "state balance")),
        "tradeoff": not requires_tradeoff or _contains(text, ("权衡", "取舍", "词典序", "pareto", "trade-off")),
        "baseline": not requires_baseline or _contains(text, ("基线", "baseline")),
    }
    checks = [
        {
            "id": "limitations_disclosed",
            "passed": _contains(text, ("局限", "限制", "不足", "limitations", "cannot guarantee")),
            "evidence": "manuscript limitation-language scan",
        },
        {
            "id": "contract_artifacts_exist",
            "passed": not artifact_issues,
            "evidence": {"question_count": len(questions), "issues": artifact_issues},
        },
        {
            "id": "question_sections_present",
            "passed": bool(expected_markers) and all(item["present"] for item in expected_markers),
            "evidence": expected_markers,
        },
        {
            "id": "declared_quality_discussed",
            "passed": all(quality_discussion.values()),
            "evidence": quality_discussion,
        },
        {
            "id": "quality_artifact_structured",
            "passed": bool(quality) and any(key in quality for key in ("uncertainty", "dynamic_state", "baseline_comparison", "multiobjective")),
            "evidence": {"registered_sections": sorted(quality)},
        },
    ]
    report = {
        "schema_version": "1.1",
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "reviewer": "deterministic_second_pass_content_review_v1_1",
        "reviewed_path": str(paper.relative_to(root)).replace("\\", "/"),
        "decision_contract_path": str(contract_path.relative_to(root)).replace("\\", "/"),
        "quality_validation_path": str(quality_path.relative_to(root)).replace("\\", "/"),
        "manuscript_sha256": digest(paper),
        "decision_contract_sha256": digest(contract_path),
        "quality_validation_sha256": digest(quality_path),
        "checks": checks,
    }
    output = root / "reports" / "independent_review.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report["status"] != "PASS":
        raise SystemExit("second-pass content review failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--manuscript", type=Path, required=True)
    parser.add_argument("--decision-contract", type=Path, required=True)
    parser.add_argument("--quality-validation", type=Path, required=True)
    args = parser.parse_args()
    main(args.project_root, args.manuscript, args.decision_contract, args.quality_validation)
