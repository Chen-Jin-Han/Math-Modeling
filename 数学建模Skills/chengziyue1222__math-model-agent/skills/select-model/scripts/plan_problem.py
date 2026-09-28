"""Create a structured, evidence-first model plan for the 2021C supplier-chain case."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT / "code") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "code"))

from algorithms.modeling_contracts import validate_decision_contract

def dump(root: Path, relative: str, value) -> None:
    path = root / relative; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main(root: Path) -> None:
    decomposition = {"problem_id":"cumcm-2021-c", "questions":[
        {"id":"Q1","objective":"rank 402 suppliers and publish the full Top-50","validation":"bootstrap rank stability"},
        {"id":"Q2","objective":"minimum robust supplier set and 24-week ordering/transport plan","validation":"inventory and capacity constraints"},
        {"id":"Q3","objective":"material-mix procurement policy","validation":"cost-risk Pareto comparison"},
        {"id":"Q4","objective":"maximum feasible weekly capacity","validation":"supplier and carrier bounds"}]}
    candidates = [{"name":"entropy-CRITIC TOPSIS","use":"Q1","risk":"ordinal assumptions"},{"name":"MILP","use":"Q2/Q4","risk":"scenario simplification"},{"name":"rolling LP","use":"Q2/Q3","risk":"forecast dependence"}]
    dump(root,"results/problem_decomposition.json",decomposition); dump(root,"results/candidate_models.json",candidates)
    dump(root,"results/baseline_plan.json",{"name":"equal-share feasible allocation","validation":"compare cost and supplier count"})
    dump(root,"results/selected_model_plan.json",{"primary":"rank consensus + robust MILP + rolling LP","disclosure":"Q2 is decomposed, not an integrated robust optimization model"})
    decision_contract={"version":"1.2","questions":[
        {"id":"Q1","result_artifact":"results/top50_suppliers.csv","validation_artifact":"results/supplier_ranking.csv","requires_baseline":False},
        {"id":"Q2","result_artifact":"results/q2_weekly_plan.csv","validation_artifact":"results/quality_validation.json","requires_dynamic_state":True,"requires_uncertainty":True,"requires_baseline":True},
        {"id":"Q3","result_artifact":"results/q3_weekly_plan.csv","validation_artifact":"results/q3_tradeoff.csv","requires_tradeoff":True,"requires_baseline":True},
        {"id":"Q4","result_artifact":"results/q4_weekly_plan.csv","validation_artifact":"results/quality_validation.json","requires_baseline":True}
    ]}
    issues=validate_decision_contract(decision_contract)
    if issues:
        raise ValueError(f"invalid decision contract: {issues}")
    dump(root,"results/decision_contract.json",decision_contract)
    dump(root,"results/risk_register.json",[{"risk":"supplier-count explosion","mitigation":"report implementation complexity"},{"risk":"static schedule","mitigation":"rolling weekly capacities"}])
    (root/"reports").mkdir(exist_ok=True); (root/"reports/model_selection_report.md").write_text("# Model selection\n\nFour questions are solved by a disclosed decomposition: ranking, set selection, rolling allocation, and capacity maximization. A simple feasible allocation is retained as a baseline.\n",encoding="utf-8")

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--root",type=Path,required=True); main(parser.parse_args().root)
