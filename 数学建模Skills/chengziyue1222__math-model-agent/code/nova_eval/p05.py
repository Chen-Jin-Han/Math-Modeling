"""P0.5 semantic audit, v0.1 adjudication, and independent v0.2 evaluation."""

from __future__ import annotations

import hashlib
import itertools
import json
import platform
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from nova_core.diagnosis import EvidenceBuilder, GateEngine
from nova_core.enums import ExperimentType, GateDecisionValue
from nova_core.experiments import ExperimentExecutor

from .baselines import _close, _prepare, run_strategy
from .cases import EvaluationCase, GroundTruth
from .generators import FAULT_FAMILIES, generate_case
from .metrics import annotate, failure_records, selection_matrix, summarize
from .runner import _csv, _figures, _hash, _json

V01 = "nova_eval_v0_1"
V02 = "nova_eval_v0_2"
_V01_CORE_SOURCE_HASHES = {
    "code/nova_core/__init__.py": "7C90E3B896DF4EDB3323B8AB6418695318F8E56C21D1E04022B67824923ABA17",
    "code/nova_core/__main__.py": "5F395B3BE9FE8D1C497BB4B6C3279C84B2428228D9311F627E34B02223D88F4A",
    "code/nova_core/diagnosis.py": "E19053D32A2AF4BC2008E7A603167CD35303783127B979B47A883338D8CF09E7",
    "code/nova_core/enums.py": "923CC35E7600014E438BEE8145C9213FE623445E54858D389389813C4E5737CE",
    "code/nova_core/experiments.py": "042D85B99F65289D38B925B7FA1C7A29B54C3B44FB969D7F4097AB15D861E441",
    "code/nova_core/models.py": "EE2AAD8B6E459654DBB3DED1A70D997F6FB0B84E6F78C29D71C1E6C9994BA35F",
    "code/nova_core/rule_inventory.py": "E2F43B964685E869994C90472F070B37A1C36537A8CE669F70FFF4C030B4C23E",
    "code/nova_core/service.py": "105A017E96ECDE1919D12AF7B95350B01BDE521E27B1C69C58423ACFF699EF3B",
}


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hashes(root: Path, pattern: str = "*.py") -> dict[str, str]:
    return {str(path.relative_to(root.parent)).replace("\\", "/"): _file_hash(path) for path in sorted(path for path in root.rglob(pattern) if path.is_file())}


def freeze_v01(repo: Path, output: Path) -> dict[str, Any]:
    """Create a non-destructive historical reference manifest for P0.5."""
    v01 = repo / "artifacts" / V01
    targets = {
        "nova_core_v0_1": _V01_CORE_SOURCE_HASHES,
        "nova_eval_at_p0_5_audit": _tree_hashes(repo / "code" / "nova_eval"),
        "rule_pack": _tree_hashes(repo / "docs" / "reverse_engineering" / "skill_rule_pack_v1", "*"),
        "v0_1_case_manifest": _file_hash(v01 / "case_manifest.json"),
        "v0_1_metric_summary": _file_hash(v01 / "metric_summary.json"),
        "v0_1_raw_results": _file_hash(v01 / "raw_results.json"),
    }
    status = subprocess.run(["git", "-C", str(repo), "status", "--short"], check=True, capture_output=True, text=True).stdout.splitlines()
    payload = {"status": "FROZEN_REFERENCE", "reference": V01, "git_status_at_freeze": status, "assets": targets, "note": "v0.1 Core hashes were captured before P0.5 modifications; the repository did not preserve a versioned v0.1 nova_eval source snapshot, so its audit-time source hash is separately recorded rather than misrepresented as historical."}
    _json(output / "frozen_v0_1_manifest.json", payload)
    return payload


def gate_semantics_audit() -> list[dict[str, Any]]:
    """Audit only what Rule Pack wording supports; unspecified means unspecified."""
    return [
        {"condition": "Explicit non-chronological time split", "applicable_rule_ids": ["VAL-GATE-002", "VAL-GATE-012"], "expected_gate": "BLOCKED", "rationale": "Execution evidence exposes future-information risk; failed evidence must be retained.", "confidence": "high", "ambiguity": None},
        {"condition": "Explicit future-origin feature", "applicable_rule_ids": ["VAL-GATE-002", "VAL-GATE-012"], "expected_gate": "BLOCKED", "rationale": "Feature provenance is executable failure evidence.", "confidence": "high", "ambiguity": None},
        {"condition": "High-load error crosses declared failure threshold", "applicable_rule_ids": ["VAL-GATE-006", "VAL-GATE-012"], "expected_gate": "BLOCKED", "rationale": "A threshold-crossing critical-region failure is preserved, not converted into success.", "confidence": "medium", "ambiguity": "Rule Pack does not define this domain threshold itself."},
        {"condition": "Model does not improve over causal persistence baseline", "applicable_rule_ids": ["VAL-GATE-012"], "expected_gate": "BLOCKED", "rationale": "VAL-GATE-012 explicitly names weak baseline as failed evidence requiring blocked/needs_review; Campus decision contract adopts blocked for a deterministic no-improvement result.", "confidence": "medium", "ambiguity": "No statistical-significance, repeated-split, or pilot-only semantics are specified."},
        {"condition": "Evidence close to a numerical threshold", "applicable_rule_ids": ["VAL-GATE-006"], "expected_gate": "UNSPECIFIED", "rationale": "The rule requires threshold-crossing and instability reporting, but gives no tolerance band or review zone.", "confidence": "high", "ambiguity": "RULE_SPEC_GAP: comparator is implemented as strict >; no manual-review band is invented."},
        {"condition": "Conflicting evidence", "applicable_rule_ids": ["VAL-GATE-012"], "expected_gate": "NEEDS_REVIEW", "rationale": "Failure evidence cannot be silently polished away; conflict resolution order is otherwise unspecified.", "confidence": "low", "ambiguity": "RULE_SPEC_GAP: no formal conflict precedence exists."},
        {"condition": "Required evidence unavailable or inconclusive", "applicable_rule_ids": ["VAL-GATE-002", "VAL-GATE-012"], "expected_gate": "NEEDS_REVIEW", "rationale": "Missing executable evidence cannot support a final readiness conclusion.", "confidence": "high", "ambiguity": None},
        {"condition": "Clean case with all required gaps closed by traceable evidence", "applicable_rule_ids": ["VAL-GATE-002", "VAL-GATE-006"], "expected_gate": "READY_FOR_REVIEW", "rationale": "The system remains human-review gated; it does not auto-approve deployment.", "confidence": "medium", "ambiguity": None},
    ]


def _ratio(case: EvaluationCase) -> float:
    actual, predicted = np.asarray(case.load), np.asarray(case.prediction)
    subset = actual >= np.quantile(actual, 0.8)
    return float(np.mean(np.abs(actual[subset] - predicted[subset])) / max(np.mean(np.abs(actual - predicted)), 1e-12))


def v02_cases(seed: int = 20260920, per_family: int = 13) -> list[EvaluationCase]:
    """Produce 104 independent final candidates, including evidence-updating cases."""
    cases: list[EvaluationCase] = []
    counter = 1
    for index, family in enumerate(FAULT_FAMILIES):
        for offset in range(per_family):
            case = generate_case(f"CASE-V2-{counter:04d}", "final_hidden_v0_2", seed + index * 20_000 + offset * 113, family)
            if family == "BORDERLINE":
                expected = GateDecisionValue.BLOCKED if _ratio(case) > 1.75 else GateDecisionValue.READY_FOR_REVIEW
                truth = replace(case.ground_truth, expected_gate=expected, fault_parameters={**case.ground_truth.fault_parameters, "formal_threshold": 1.75, "formal_comparator": ">", "actual_metric": _ratio(case)})
                case = replace(case, ground_truth=truth)
            cases.append(case); counter += 1
    for offset in range(per_family):
        base = generate_case(f"CASE-V2-{counter:04d}", "final_hidden_v0_2", seed + 190_000 + offset * 113, "CLEAN")
        truth = GroundTruth("AMBIGUOUS_MULTI_STAGE", ("ROLLING_STABILITY", "PEAK_STABILITY"), GateDecisionValue.BLOCKED, (ExperimentType.ROLLING_VALIDATION_CHALLENGE,), {"stage_1": "inconclusive rolling stability", "stage_2": "peak-fold instability", "oracle_path": ["ROLLING_VALIDATION_CHALLENGE", "PEAK_STABILITY_CHALLENGE"]})
        cases.append(replace(base, case_id=f"CASE-V2-{counter:04d}", ground_truth=truth, rolling_fold_errors=(1.0, 1.0, 2.0), rolling_peak_errors=(1.0, 1.0, 4.0)))
        counter += 1
    return cases


def _logical_result(run: Any) -> tuple[Any, list[str], list[str]]:
    return run.gate, [item.experiment_type.value for item in run.selected_experiments], [item.direction.value for item in run.evidence]


def _oracle_cost(case: EvaluationCase) -> float | None:
    """Evaluator-only exhaustive minimum-cost path to the expected binary gate."""
    context, claim, risks, original_gaps, candidates = _prepare(case)
    best: float | None = None
    for order in itertools.permutations(candidates):
        gaps, evidence, executed = list(original_gaps), [], []
        executor, builder, engine = ExperimentExecutor(), EvidenceBuilder(), GateEngine()
        valid = True
        for spec in order:
            required = spec.parameters.get("requires_evidence_from")
            if required and required not in {item.experiment_id for item in executed}:
                valid = False; break
            result = executor.execute(spec, context, run_id="oracle")
            risk = next(item for item in risks if any(gap.gap_id in spec.target_gap_ids and gap.risk_id == item.risk_id for gap in gaps))
            item = builder.build(claim, risk, spec, result)
            evidence.append(item); executed.append(spec); gaps = _close(gaps, spec, item)
            gate = engine.decide(claim, gaps, evidence)
            expected_block = case.ground_truth.expected_gate == GateDecisionValue.BLOCKED
            if (gate.decision == GateDecisionValue.BLOCKED) == expected_block and (gate.decision == GateDecisionValue.BLOCKED or not gate.remaining_gaps):
                cost = sum(candidate.estimated_cost for candidate in executed)
                best = cost if best is None else min(best, cost)
                break
        if not valid:
            continue
    return best


def _wilson(successes: int, total: int) -> list[float] | None:
    if not total:
        return None
    z, p = 1.959963984540054, successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    radius = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5) / denom
    return [round(max(0.0, centre - radius), 6), round(min(1.0, centre + radius), 6)]


def _add_v02_metrics(records: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    for strategy, values in summary["strategies"].items():
        rows = [row for row in records if row["strategy"] == strategy and row["strategy_result"]["execution_status"] == "EXECUTED"]
        values["exact_gate_accuracy"] = values["gate_accuracy"]
        values["safety_binary_accuracy"] = values["gate_accuracy"]
        values["confidence_intervals_95"] = {"gate_accuracy": _wilson(sum(row["evaluation"]["correct_gate"] for row in rows), len(rows)), "fault_detection_rate": _wilson(sum(row["ground_truth"]["expected_gate"] == "BLOCKED" and row["strategy_result"]["gate"] == "BLOCKED" for row in rows), sum(row["ground_truth"]["expected_gate"] == "BLOCKED" for row in rows)), "clean_false_block_rate": _wilson(sum(row["evaluation"]["false_block"] for row in rows), sum(row["ground_truth"]["fault_type"] == "CLEAN" for row in rows)), "top1_selection_accuracy": _wilson(sum(row["evaluation"]["first_experiment_hit"] for row in rows), len(rows))}
        regrets = [row["evaluation"].get("selection_regret") for row in rows if row["evaluation"].get("selection_regret") is not None]
        values["average_selection_regret"] = round(sum(regrets) / len(regrets), 6) if regrets else None


def _adjudication(v01_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    failures, borderline = [], []
    for row in v01_rows:
        if row["strategy"] != "nova" or row["evaluation"]["correct_gate"]:
            continue
        fault = row["ground_truth"]["fault_type"]
        if fault == "BASELINE_FAILURE":
            failures.append({"case_id": row["case_id"], "category": "GATE_IMPLEMENTATION_DEFECT", "evidence": "Baseline experiment produced non-positive mae_improvement; VAL-GATE-012 names weak baseline as failed evidence, but v0.1 converted WEAKENS into READY_FOR_REVIEW.", "recommended_action": "Map deterministic no-improvement baseline evidence to REFUTES; do not infer statistical superiority."})
        elif fault == "BORDERLINE":
            evidence = next(item for item in row["strategy_result"]["evidence"] if item["evidence_type"] == "HIGH_LOAD_SUBSET_EVALUATION")
            metric = evidence["value"]
            borderline.append({"case_id": row["case_id"], "ground_truth": row["ground_truth"]["expected_gate"], "actual_metric": metric, "formal_threshold": 1.75, "distance_to_threshold": metric - 1.75, "expected_gate": row["ground_truth"]["expected_gate"], "nova_gate": row["strategy_result"]["gate"], "rule_triggered": row["strategy_result"]["gate_decision"]["triggered_rules"], "failure_reason": "GENERATOR/ground-truth used injected magnitude rather than the actual formal metric; formal comparator is strict >."})
            failures.append({"case_id": row["case_id"], "category": "GROUND_TRUTH_DEFECT", "evidence": f"Actual high-load ratio={metric} is above 1.75 while historical expected gate was non-block.", "recommended_action": "For v0.2 derive borderline truth from actual metric and publish comparator; do not add an unspecified tolerance."})
    return failures, borderline


def _claims() -> list[dict[str, Any]]:
    return [
        {"claim_id": "CLAIM-COMP-001", "statement": "Nova forms traceable Gates for the evaluated fault families.", "status": "SUPPORTED_BY_V0_1", "evidence": ["evidence_traceability_rate=1.0", "gate_traceability_rate=1.0"]},
        {"claim_id": "CLAIM-COMP-002", "statement": "Nova reduces experiment count versus Fixed Run All.", "status": "SUPPORTED_BY_V0_1", "evidence": ["1.286 vs 2.429 experiments"]},
        {"claim_id": "CLAIM-COMP-003", "statement": "Dynamic selection lowers cost versus Fixed Early Stop.", "status": "NOT_SUPPORTED_BY_V0_1", "evidence": ["equal average cost and experiment count"]},
        {"claim_id": "CLAIM-COMP-004", "statement": "Dynamic selection chooses the Oracle-acceptable first experiment more often than Fixed Early Stop.", "status": "SUPPORTED_BY_V0_1", "evidence": ["Top-1 1.0 vs 0.714286"]},
    ]


def _report(summary: dict[str, Any], adjudication: list[dict[str, Any]], v02_manifest: dict[str, Any]) -> str:
    nova, early, all_fixed = (summary["strategies"].get(name, {}) for name in ("nova", "fixed-early-stop", "fixed-all"))
    sections = [
        ("为什么没有直接改Gate刷分", "v0.1 Hidden 已冻结为历史审计集；v0.2 使用完全独立 seed 与 104 个案例。"),
        ("BASELINE_FAILURE正式归因", "GATE_IMPLEMENTATION_DEFECT：VAL-GATE-012 将弱基线列为失败证据。v0.2 仅将确定的非正改进映射为 REFUTES，不把所有弱证据一律阻断。"),
        ("BORDERLINE正式归因", "GROUND_TRUTH_DEFECT/RULE_SPEC_GAP：历史标签来自注入幅度，非实际 ratio；正式规则无容差带，v0.2 使用严格 > 1.75。"),
        ("v0.1 Ground Truth审计", f"保留全部 {len(adjudication)} 条错误归因。"),
        ("Gate语义审计", "见 gate_semantics_audit.json；未明确规则均标为 UNSPECIFIED。"),
        ("实际Rule变更", "无 Rule Pack 文本变更；rule_change_proposal.json 仅记录实现对 VAL-GATE-012 的一致性修正。"),
        ("实际Core变更", "弱基线 REFUTES；新增滚动验证与峰值稳定性两个真实实验，以及 inconclusive gap 保持开放。"),
        ("Experiment变化", "新增 ROLLING_VALIDATION_CHALLENGE 与 prerequisite-aware PEAK_STABILITY_CHALLENGE。"),
        ("Multi-stage诊断案例", "AMBIGUOUS_MULTI_STAGE 先产生 INCONCLUSIVE rolling evidence，再由第二个峰值稳定性实验形成 BLOCKED。"),
        ("Evidence状态更新后的二次选择示例", "见 multistage_selection_example.json。"),
        ("v0.2数据划分", "DEV/CALIBRATION/FINAL_HIDDEN/CHALLENGE 的生成种子独立；本次 Final Hidden 104 例。"),
        ("Final Hidden结果", f"Nova Exact/Safety Accuracy={nova.get('exact_gate_accuracy')}；95% CI={nova.get('confidence_intervals_95', {}).get('gate_accuracy')}。"),
        ("Nova vs Fixed Early Stop", f"Nova cost={nova.get('average_decision_cost')}，Fixed Early Stop={early.get('average_decision_cost')}；绝对差={round((early.get('average_decision_cost') or 0)-(nova.get('average_decision_cost') or 0), 6)}。"),
        ("Nova vs Fixed Run All", f"Nova experiments={nova.get('average_experiment_count')}，Fixed Run All={all_fixed.get('average_experiment_count')}。"),
        ("Selection Regret", f"Nova average regret={nova.get('average_selection_regret')}；基于 evaluator-only exhaustive path oracle。"),
        ("Exact Gate vs Safety Gate结果", "当前合同仅含 BLOCKED/READY_FOR_REVIEW，二者相同；mapping_v0_2.json 保留未来多状态扩展规则。"),
        ("False Block", f"Nova Clean False Block={nova.get('false_block_rate')}。"),
        ("Failure Analysis", "详见 failure_adjudication.json 和 failures.json；不删除任何失败。"),
        ("Challenge Set", "v0.2 challenge 生成器已独立定义；本阶段不将其用于最终调参。"),
        ("95% CI", str(nova.get("confidence_intervals_95"))),
        ("本轮真实测试", "单元、相关回归和全量 suite 均应由交付命令复核。"),
        ("SUPPORTED Claims", "Traceability；相较 Fixed Run All 的实验节省；v0.1 Top-1 优势。"),
        ("PARTIALLY_SUPPORTED Claims", "多阶段动态选择已在 controlled case 中展示；需更多现实任务验证。"),
        ("NOT_SUPPORTED Claims", "v0.1 未证明动态策略相对 Fixed Early Stop 的总体成本/准确率优势。"),
        ("当前仍不能宣称什么", "真实校园部署、真实 LLM 对照、跨领域泛化和统计显著策略优势均未证明。"),
        ("HTTP API阶段条件", "P0.5 结果和 Rule Pack 变更需人工审阅后决定；本工具不会自动开始 HTTP API。"),
    ]
    return "《智感Nova P0.5 Gate语义与可信评测加固报告 v0.2》\n\n" + "\n\n".join(f"{index + 1}. {title}\n{body}" for index, (title, body) in enumerate(sections)) + "\n"


def run_p05(repo: str | Path, output: str | Path, *, seed: int = 20260920, execute_final: bool = True) -> dict[str, Any]:
    repo_path, output_path = Path(repo).resolve(), Path(output).resolve(); output_path.mkdir(parents=True, exist_ok=True)
    frozen = freeze_v01(repo_path, output_path)
    audit = gate_semantics_audit(); _json(output_path / "gate_semantics_audit.json", audit)
    v01 = json.loads((repo_path / "artifacts" / V01 / "raw_results.json").read_text(encoding="utf-8")); adjudication, borderline = _adjudication(v01)
    _json(output_path / "failure_adjudication.json", adjudication); _csv(output_path / "borderline_audit.csv", borderline)
    proposal = [{"rule_id": "VAL-GATE-012", "old_behavior": "Non-positive causal baseline improvement became WEAKENS and could finish READY_FOR_REVIEW.", "new_behavior": "Deterministic non-positive causal baseline improvement is REFUTES/BLOCKED.", "reason": "Rule wording explicitly includes weak baseline in retained failed evidence.", "evidence": "gate_semantics_audit.json", "compatibility": "Does not assert statistical inferiority or alter Rule Pack text.", "risk": "Single-split baseline remains a limitation disclosed in Evidence."}]
    _json(output_path / "rule_change_proposal.json", proposal); _json(output_path / "competition_claims.json", _claims())
    mapping = {"exact_gate": "exact enum equality", "safety_binary": {"BLOCKED": "BLOCK", "READY_FOR_REVIEW": "NON_BLOCK", "NEEDS_REVIEW": "NON_BLOCK_PENDING"}, "note": "REVALIDATE/PILOT_ONLY are UNSPECIFIED by current formal Rule Pack and are not collapsed into a success state."}
    _json(output_path / "gate_evaluation_mapping_v0_2.json", mapping)
    if not execute_final:
        return {"frozen": frozen, "adjudication": adjudication}
    cases = v02_cases(seed); raw: list[dict[str, Any]] = []
    for case in cases:
        for strategy in ("nova", "fixed-early-stop", "fixed-all", "surface-metric"):
            run = run_strategy(case, strategy)
            raw.append({"case_id": case.case_id, "partition": case.partition, "seed": case.seed, "strategy": strategy, "ground_truth": case.ground_truth.to_dict(), "strategy_result": run.to_dict()})
    annotate(raw)
    for row in raw:
        if row["strategy"] != "surface-metric":
            oracle = _oracle_cost(next(case for case in cases if case.case_id == row["case_id"]))
            row["evaluation"]["oracle_min_cost"] = oracle
            row["evaluation"]["selection_regret"] = round(row["strategy_result"]["estimated_cost"] - oracle, 6) if oracle is not None else None
    summary = summarize(raw); _add_v02_metrics(raw, summary)
    failures, matrix = failure_records(raw), selection_matrix(raw)
    manifests = [case.manifest_record() for case in cases]
    v02_manifest = {"benchmark": V02, "status": "FINAL_HIDDEN_EXECUTED_ONCE", "seed": seed, "case_count": len(cases), "case_manifest_hash": _hash(manifests), "core_hash_at_run": _hash(_tree_hashes(repo_path / "code" / "nova_core")), "rule_pack_hash": _hash(_tree_hashes(repo_path / "docs" / "reverse_engineering" / "skill_rule_pack_v1", "*")), "platform": platform.platform(), "python": sys.version}
    multi = next(case for case in cases if case.ground_truth.fault_type == "AMBIGUOUS_MULTI_STAGE")
    multi_run = run_strategy(multi, "nova").to_dict(); _json(output_path / "multistage_selection_example.json", {"case_manifest": multi.manifest_record(), "selection_trace": multi_run["selection_trace"], "experiments": multi_run["selected_experiments"], "evidence": multi_run["evidence"], "gate": multi_run["gate"]})
    _json(output_path / "v0_2_final_manifest.json", v02_manifest); _json(output_path / "case_manifest.json", manifests); _json(output_path / "raw_results.json", raw); _json(output_path / "metric_summary.json", summary); _json(output_path / "failures.json", failures); _csv(output_path / "selection_matrix.csv", matrix)
    _csv(output_path / "case_results.csv", [{"case_id": row["case_id"], "strategy": row["strategy"], "fault_type": row["ground_truth"]["fault_type"], "expected_gate": row["ground_truth"]["expected_gate"], "gate": row["strategy_result"]["gate"], "correct": row["evaluation"]["correct_gate"], "cost": row["strategy_result"]["estimated_cost"], "oracle_cost": row["evaluation"].get("oracle_min_cost"), "regret": row["evaluation"].get("selection_regret")} for row in raw])
    _figures(raw, output_path / "figures")
    (output_path / "report.txt").write_text(_report(summary, adjudication, v02_manifest), encoding="utf-8")
    return {"manifest": v02_manifest, "summary": summary, "adjudication": adjudication}


def run_v02_challenge(output: str | Path, *, seed: int = 20260921) -> dict[str, Any]:
    """Run a post-final, non-tuning challenge set without touching final artifacts."""
    output_path = Path(output).resolve(); output_path.mkdir(parents=True, exist_ok=True)
    cases = [replace(case, partition="challenge_v0_2") for case in v02_cases(seed, per_family=3)]
    raw: list[dict[str, Any]] = []
    for case in cases:
        for strategy in ("nova", "fixed-early-stop", "fixed-all", "surface-metric"):
            run = run_strategy(case, strategy)
            raw.append({"case_id": case.case_id, "partition": case.partition, "seed": case.seed, "strategy": strategy, "ground_truth": case.ground_truth.to_dict(), "strategy_result": run.to_dict()})
    annotate(raw)
    summary = summarize(raw); _add_v02_metrics(raw, summary)
    _json(output_path / "challenge_manifest.json", {"benchmark": V02, "partition": "CHALLENGE_V0_2", "seed": seed, "case_count": len(cases), "case_manifest_hash": _hash([case.manifest_record() for case in cases]), "non_tuning_statement": "Executed after FINAL_HIDDEN_V0_2; no rule, Core, generator, or ground-truth changes were made from this result."})
    _json(output_path / "case_manifest.json", [case.manifest_record() for case in cases]); _json(output_path / "raw_results.json", raw); _json(output_path / "metric_summary.json", summary); _json(output_path / "failures.json", failure_records(raw)); _csv(output_path / "selection_matrix.csv", selection_matrix(raw)); _figures(raw, output_path / "figures")
    (output_path / "report.txt").write_text("《智感Nova P0.5 Challenge Set报告 v0.2》\n\n这是 FINAL_HIDDEN_V0_2 之后执行的独立挑战集；其结果不用于调参或重报 final 成绩。\n\n" + json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"summary": summary, "case_count": len(cases)}


def adjudicate_final_output(output: str | Path) -> list[dict[str, Any]]:
    """Classify observed final errors without rerunning or changing final data."""
    output_path = Path(output).resolve()
    raw = json.loads((output_path / "raw_results.json").read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for row in raw:
        if row["strategy"] != "nova" or row["evaluation"]["correct_gate"]:
            continue
        fault, evidence = row["ground_truth"]["fault_type"], row["strategy_result"]["evidence"]
        if fault == "BASELINE_FAILURE" and evidence and evidence[0]["direction"] == "SUPPORTS":
            category, action = "GENERATOR_DEFECT", "Future benchmark generator must construct an observed non-positive baseline margin (not merely label an intended fault); do not alter this Final Hidden score."
            rationale = "The realized baseline comparison supports the model, so the injected case did not instantiate its claimed weak-baseline condition."
        else:
            category, action = "GENUINE_MODEL_LIMITATION", "Investigate on DEV_v0_3 only; keep v0.2 Final frozen."
            rationale = "Observed gate differs from formal evaluator mapping after the case instantiated its declared condition."
        records.append({"case_id": row["case_id"], "fault_type": fault, "category": category, "expected_gate": row["ground_truth"]["expected_gate"], "nova_gate": row["strategy_result"]["gate"], "evidence": evidence, "rationale": rationale, "recommended_action": action})
    _json(output_path / "post_final_failure_adjudication.json", records)
    (output_path / "report_addendum.txt").write_text("P0.5 Final 后失败归因附录\n\nFinal Hidden 已冻结，以下归因不触发重跑。\n\n" + json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return records
