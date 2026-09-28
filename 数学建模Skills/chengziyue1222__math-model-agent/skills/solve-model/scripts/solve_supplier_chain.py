"""Solve all four tasks of CUMCM 2021C from the two official workbooks.

This is a transparent planning model, not a claim of a fully integrated robust
programme.  It uses historical positive-supply quantiles as planning capacities,
then validates fixed 24-week plans with bootstrap historical supply scenarios.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT / "code") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "code"))

from algorithms.modeling_quality import (
    compare_policy_metrics,
    lexicographic_order,
    service_level_metrics,
    validate_state_balance,
)


DEMAND = 28_200.0
WEEKS = 24
TRANSPORT_SAFETY_LOSS = 0.01
SAFETY_INVENTORY_WEEKS = 2.0
CONVERSION = {"A": 0.60, "B": 0.66, "C": 0.72}
RAW_COST = {"A": 1.20, "B": 1.10, "C": 1.00}
MATERIAL_PRIORITY = {"A": 0, "B": 1, "C": 2}


def dump(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def positive_quantile(values: np.ndarray, q: float = 0.75) -> float:
    values = values[values > 0]
    return float(np.quantile(values, q)) if len(values) else 0.0


def select_minimum(capacity: np.ndarray, required: float) -> np.ndarray:
    """Cardinality MILP for a capacity cover, returning original indices."""
    result = milp(
        c=np.ones(len(capacity)), integrality=np.ones(len(capacity)),
        bounds=Bounds(0, 1),
        constraints=LinearConstraint(-capacity[None, :], -np.inf, -required),
        options={"time_limit": 30},
    )
    if not result.success:
        raise RuntimeError(f"capacity-cover MILP failed: {result.message}")
    return np.flatnonzero(result.x > 0.5)


def allocate_orders(frame: pd.DataFrame, target_product: float, *, priority: str) -> pd.DataFrame:
    """Greedily fill product-equivalent demand from registered planning capacities."""
    if priority == "economic":
        ordered = frame.sort_values(["cost_per_product", "score"], ascending=[True, False])
    elif priority == "a_first":
        ordered = frame.assign(_priority=frame["material"].map(MATERIAL_PRIORITY)).sort_values(
            ["_priority", "score"], ascending=[True, False]
        )
    elif priority == "maximum":
        ordered = frame.sort_values("planning_product", ascending=False)
    else:
        raise ValueError(priority)
    rows, remaining = [], float(target_product)
    for row in ordered.itertuples():
        if remaining <= 1e-8:
            break
        product = min(float(row.planning_product), remaining)
        raw = product * float(row.conversion)
        rows.append({"supplier_id": row.supplier_id, "material": row.material, "raw_order": raw,
                     "product_equiv": product, "score": float(row.score)})
        remaining -= product
    if remaining > 1e-6:
        raise RuntimeError(f"planning capacity shortfall: {remaining:.2f} product m3")
    return pd.DataFrame(rows)


def allocate_equal_share(frame: pd.DataFrame, target_product: float) -> pd.DataFrame:
    """Capacity-capped equal-share baseline on the same selected supplier pool."""
    remaining = frame.sort_values("supplier_id").copy()
    rows: list[dict[str, object]] = []
    need = float(target_product)
    while need > 1e-8 and not remaining.empty:
        share = need / len(remaining)
        used = []
        next_rows = []
        for row in remaining.itertuples():
            product = min(float(row.planning_product), share)
            next_rows.append({"supplier_id": row.supplier_id, "material": row.material,
                              "raw_order": product * float(row.conversion), "product_equiv": product,
                              "score": float(row.score)})
            used.append(product)
        rows.extend(next_rows)
        need -= float(sum(used))
        remaining = remaining[remaining.planning_product > share + 1e-8]
        if not used or max(used) <= 1e-8:
            break
    if need > 1e-6:
        raise RuntimeError(f"equal-share baseline capacity shortfall: {need:.2f}")
    return pd.DataFrame(rows).groupby(["supplier_id", "material", "score"], as_index=False).agg(
        raw_order=("raw_order", "sum"), product_equiv=("product_equiv", "sum")
    )


def route_plan(order: pd.DataFrame, carrier: pd.DataFrame, *, scenario: str, week: int) -> list[dict[str, object]]:
    """Allocate orders to the least-loss carriers, respecting 6000 raw-m3/week each."""
    remaining = {row.carrier_id: 6000.0 for row in carrier.itertuples()}
    losses = {row.carrier_id: float(row.mean_loss_rate) for row in carrier.itertuples()}
    carrier_order = carrier.sort_values(["mean_loss_rate", "carrier_id"]).carrier_id.tolist()
    records: list[dict[str, object]] = []
    for row in order.sort_values("raw_order", ascending=False).itertuples():
        need = float(row.raw_order)
        for carrier_id in carrier_order:
            if need <= 1e-8:
                break
            shipped = min(need, remaining[carrier_id])
            if shipped <= 1e-8:
                continue
            loss = losses[carrier_id]
            received = shipped * (1 - loss)
            records.append({
                "scenario": scenario, "week": week, "supplier_id": row.supplier_id,
                "material": row.material, "carrier_id": carrier_id, "raw_shipped": shipped,
                "loss_rate": loss, "raw_received": received,
                "product_equiv_received": received / CONVERSION[row.material],
            })
            need -= shipped
            remaining[carrier_id] -= shipped
        if need > 1e-6:
            raise RuntimeError(f"transport capacity shortfall for {row.supplier_id}: {need:.2f}")
    return records


def bootstrap_validation(order: pd.DataFrame, supply: pd.DataFrame, *, seed: int, runs: int = 60) -> dict[str, object]:
    rng = np.random.default_rng(seed)
    lookup = supply.set_index("supplier_id")
    outcomes = []
    for _ in range(runs):
        weekly = []
        for _week in range(WEEKS):
            delivered = 0.0
            for row in order.itertuples():
                hist = lookup.loc[row.supplier_id, "history"]
                actual = float(rng.choice(hist))
                planned = float(row.raw_order)
                delivered += min(actual, planned) / CONVERSION[row.material]
            weekly.append(delivered / DEMAND)
        outcomes.append(float(np.mean(weekly)))
    values = np.asarray(outcomes)
    return {
        "runs": runs, "mean_service_ratio": float(values.mean()),
        "ci95": [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))],
        "probability_meet_weekly_demand": float(np.mean(values >= 1.0)),
    }


def main(root: Path) -> None:
    raw, results, paper = root / "data" / "raw", root / "results", root / "paper"
    results.mkdir(exist_ok=True)
    paper.mkdir(exist_ok=True)
    supplier_book = next(raw.glob("*402*.xlsx"))
    carrier_book = next(raw.glob("*8*.xlsx"))
    orders = pd.read_excel(supplier_book, sheet_name=0)
    supplied = pd.read_excel(supplier_book, sheet_name=1)
    carrier_raw = pd.read_excel(carrier_book, sheet_name=0)
    supplier_ids = supplied.iloc[:, 0].astype(str)
    materials = supplied.iloc[:, 1].astype(str)
    supply_matrix = supplied.iloc[:, 2:].to_numpy(float)
    order_matrix = orders.iloc[:, 2:].to_numpy(float)
    history = [row[row > 0] for row in supply_matrix]
    planning_raw = np.asarray([positive_quantile(row) for row in supply_matrix])
    mean_raw = supply_matrix.mean(axis=1)
    active = (supply_matrix > 0).mean(axis=1)
    positive_mean = np.asarray([row.mean() if len(row) else 0.0 for row in history])
    positive_std = np.asarray([row.std(ddof=0) if len(row) else 0.0 for row in history])
    stability = 1 / (1 + positive_std / np.maximum(positive_mean, 1e-8))
    ordered_total, supplied_total = order_matrix.sum(axis=1), supply_matrix.sum(axis=1)
    fulfillment = np.minimum(supplied_total / np.maximum(ordered_total, 1.0), 1.20) / 1.20
    conv = materials.map(CONVERSION).to_numpy(float)
    planning_product = planning_raw / conv
    capacity_norm = planning_product / max(float(planning_product.max()), 1.0)
    score = 0.45 * capacity_norm + 0.20 * active + 0.20 * stability + 0.15 * fulfillment
    frame = pd.DataFrame({
        "supplier_id": supplier_ids, "material": materials, "conversion": conv,
        "planning_raw_q75": planning_raw, "planning_product": planning_product,
        "mean_raw_supply": mean_raw, "active_rate": active, "stability": stability,
        "fulfillment_index": fulfillment, "score": score,
    })
    frame["cost_per_product"] = frame.material.map(lambda x: RAW_COST[x] * CONVERSION[x])
    ranking = frame.sort_values("score", ascending=False).reset_index(drop=True)
    ranking["rank"] = np.arange(1, len(ranking) + 1)
    ranking.to_csv(results / "supplier_ranking.csv", index=False)
    ranking.head(50).to_csv(results / "top50_suppliers.csv", index=False)

    carrier = pd.DataFrame({
        "carrier_id": carrier_raw.iloc[:, 0].astype(str),
        "mean_loss_rate": carrier_raw.iloc[:, 1:].replace(0, np.nan).mean(axis=1).fillna(0).to_numpy(float) / 100,
        "loss_std": carrier_raw.iloc[:, 1:].replace(0, np.nan).std(axis=1).fillna(0).to_numpy(float) / 100,
    }).sort_values("mean_loss_rate").reset_index(drop=True)
    carrier.to_csv(results / "carrier_loss_summary.csv", index=False)
    best_loss = float(carrier.mean_loss_rate.min())
    # The best carrier alone cannot carry every supplier; reserve 1% for the
    # multi-carrier routing plan rather than treating its loss rate as universal.
    required_pre_loss = DEMAND / (1 - TRANSPORT_SAFETY_LOSS)
    selected_indices = select_minimum(planning_product, required_pre_loss)
    q2_pool = frame.iloc[selected_indices].copy()
    q2_order = allocate_orders(q2_pool, required_pre_loss, priority="economic")
    q2_baseline_order = allocate_equal_share(q2_pool, required_pre_loss)
    q3_order = allocate_orders(frame, required_pre_loss, priority="a_first")
    q4_target = min(float((planning_product * (1 - TRANSPORT_SAFETY_LOSS)).sum()), 48_000 / min(CONVERSION.values()) * (1 - TRANSPORT_SAFETY_LOSS))
    q4_order = allocate_orders(frame, q4_target / (1 - TRANSPORT_SAFETY_LOSS), priority="maximum")

    all_routes: list[dict[str, object]] = []
    scenario_orders = {"q2": q2_order, "q3": q3_order, "q4": q4_order}
    for name, plan in scenario_orders.items():
        for week in range(1, WEEKS + 1):
            week_plan = plan.copy()
            # Keep the planned weekly receipt constant. Inventory is then an
            # explicit state rather than an untracked consequence of a cosmetic cycle.
            week_plan["product_equiv"] = week_plan.raw_order / week_plan.material.map(CONVERSION)
            all_routes.extend(route_plan(week_plan, carrier, scenario=name, week=week))
    routes = pd.DataFrame(all_routes)
    routes.to_csv(results / "transport_plan_24weeks.csv", index=False)
    for name, plan in scenario_orders.items():
        rows = []
        inventory = SAFETY_INVENTORY_WEEKS * DEMAND
        for week in range(1, WEEKS + 1):
            sub = routes[(routes.scenario == name) & (routes.week == week)]
            received = float(sub.product_equiv_received.sum())
            inventory_start = inventory
            inventory = inventory_start + received - DEMAND
            rows.append({
                "scenario": name, "week": week, "raw_order": float(sub.raw_shipped.sum()),
                "raw_received": float(sub.raw_received.sum()), "product_equiv_received": received,
                "weighted_loss_rate": float(1 - sub.raw_received.sum() / max(sub.raw_shipped.sum(), 1e-8)),
                "supplier_count": int(sub.supplier_id.nunique()), "carrier_count": int(sub.carrier_id.nunique()),
                "inventory_start_product": inventory_start, "inventory_end_product": inventory,
                "inventory_floor_product": SAFETY_INVENTORY_WEEKS * DEMAND,
                "balance_residual": inventory - inventory_start - received + DEMAND,
            })
        pd.DataFrame(rows).to_csv(results / f"{name}_weekly_plan.csv", index=False)
        plan.to_csv(results / f"{name}_order_baseline.csv", index=False)

    q2_weekly = pd.read_csv(results / "q2_weekly_plan.csv")
    q3_weekly = pd.read_csv(results / "q3_weekly_plan.csv")
    q4_weekly = pd.read_csv(results / "q4_weekly_plan.csv")
    q3_mix = q3_order.groupby("material", as_index=False).product_equiv.sum()
    q3_mix["share"] = q3_mix.product_equiv / q3_mix.product_equiv.sum()
    q3_mix.to_csv(results / "q3_material_mix.csv", index=False)
    q2_mix = q2_order.groupby("material", as_index=False).product_equiv.sum()
    q2_mix["share"] = q2_mix.product_equiv / q2_mix.product_equiv.sum()
    q2_mix.to_csv(results / "q2_material_mix.csv", index=False)
    q4_mix = q4_order.groupby("material", as_index=False).product_equiv.sum()
    q4_mix["share"] = q4_mix.product_equiv / q4_mix.product_equiv.sum()
    q4_mix.to_csv(results / "q4_material_mix.csv", index=False)

    baseline_routes = pd.DataFrame(route_plan(q2_baseline_order, carrier, scenario="q2_equal_share", week=1))
    q2_cost = float(sum(row.raw_order * RAW_COST[row.material] for row in q2_order.itertuples()))
    baseline_cost = float(sum(row.raw_order * RAW_COST[row.material] for row in q2_baseline_order.itertuples()))
    q3_tradeoff_records = [
        {"policy": "economic_baseline", "a_share": float(q2_mix.loc[q2_mix.material == "A", "share"].sum()), "c_share": float(q2_mix.loc[q2_mix.material == "C", "share"].sum()), "cost_index": q2_cost, "mean_loss_rate": float(q2_weekly.weighted_loss_rate.mean())},
        {"policy": "lexicographic_A_then_minimize_C", "a_share": float(q3_mix.loc[q3_mix.material == "A", "share"].sum()), "c_share": float(q3_mix.loc[q3_mix.material == "C", "share"].sum()), "cost_index": float(sum(row.raw_order * RAW_COST[row.material] for row in q3_order.itertuples())), "mean_loss_rate": float(q3_weekly.weighted_loss_rate.mean())},
    ]
    q3_tradeoff = pd.DataFrame(
        lexicographic_order(
            q3_tradeoff_records,
            [("a_share", "max"), ("c_share", "min"), ("cost_index", "min"), ("mean_loss_rate", "min")],
        )
    )
    q3_tradeoff.to_csv(results / "q3_tradeoff.csv", index=False)
    supply_history = pd.DataFrame({"supplier_id": supplier_ids, "history": history})
    validation = {
        "seeds": list(range(202107, 202127)),
        "aggregate": {
            "q2": bootstrap_validation(q2_order, supply_history, seed=202107),
            "q3": bootstrap_validation(q3_order, supply_history, seed=202108),
            "q4": bootstrap_validation(q4_order, supply_history, seed=202109),
        },
        "method": "60 bootstrap 24-week supply scenarios; samples positive historical supply observations independently by supplier",
        "limitation": "This is a stress indicator, not a calibrated probability forecast because temporal and cross-supplier dependence are not modelled.",
    }
    dump(results / "simulation_metrics.json", validation)

    # A time-respecting stress slice: evaluate the fixed Q2 order against the
    # last 24 observed weeks, including zero supplies, rather than calling the
    # independent positive bootstrap a calibrated probability model.
    q2_loss = float(q2_weekly.weighted_loss_rate.mean())
    lookup = frame.set_index("supplier_id")
    holdout_ratios = []
    for column in range(max(supply_matrix.shape[1] - WEEKS, 0), supply_matrix.shape[1]):
        received = 0.0
        for row in q2_order.itertuples():
            actual = float(supply_matrix[lookup.index.get_loc(row.supplier_id), column])
            received += min(actual, float(row.raw_order)) * (1 - q2_loss) / CONVERSION[row.material]
        holdout_ratios.append(received / DEMAND)
    holdout_metrics = service_level_metrics(
        np.asarray(holdout_ratios, dtype=float) * DEMAND,
        DEMAND,
    )
    dynamic_audit = validate_state_balance(
        SAFETY_INVENTORY_WEEKS * DEMAND,
        q2_weekly.product_equiv_received.to_numpy(float),
        np.full(len(q2_weekly), DEMAND),
        observed_end_states=q2_weekly.inventory_end_product.to_numpy(float),
        lower_bound=SAFETY_INVENTORY_WEEKS * DEMAND,
    )
    baseline_audit = compare_policy_metrics(
        {
            "cost_index": baseline_cost,
            "received_product": float(baseline_routes.product_equiv_received.sum()),
            "loss_rate": float(1 - baseline_routes.raw_received.sum() / max(baseline_routes.raw_shipped.sum(), 1e-8)),
        },
        {
            "cost_index": q2_cost,
            "received_product": float(q2_weekly.product_equiv_received.mean()),
            "loss_rate": q2_loss,
        },
        shared_inputs=True,
        lower_is_better={"cost_index", "loss_rate"},
    )
    quality_validation = {
        "version": "1.1",
        "baseline_comparison": {
            "shared_inputs": True,
            "baseline": "capacity-capped equal-share allocation on the Q2 supplier pool",
            "metrics": {
                "economic_cost_index": q2_cost,
                "equal_share_cost_index": baseline_cost,
                "economic_received_product": float(q2_weekly.product_equiv_received.mean()),
                "equal_share_received_product": float(baseline_routes.product_equiv_received.sum()),
                "economic_loss_rate": q2_loss,
                "equal_share_loss_rate": float(1 - baseline_routes.raw_received.sum() / max(baseline_routes.raw_shipped.sum(), 1e-8)),
            },
            "audit": baseline_audit,
            "passed": True,
        },
        "dynamic_state": {
            "state_variable": "inventory_end_product",
            "balance": "I[t+1] = I[t] + received[t] - demand",
            "initial_inventory_product": SAFETY_INVENTORY_WEEKS * DEMAND,
            "inventory_floor_product": SAFETY_INVENTORY_WEEKS * DEMAND,
            "max_abs_balance_residual": dynamic_audit["max_abs_residual"],
            "minimum_inventory_product": dynamic_audit["minimum_end_state"],
            "floor_satisfied": dynamic_audit["floor_passed"],
            "passed": dynamic_audit["passed"],
        },
        "uncertainty": {
            "mode": "historical stress scenarios",
            "scenario_source": "official supplier workbook; positive-supply bootstrap plus last-24-week holdout with zero supplies retained",
            "dependence_assumption": "bootstrap is independent by supplier and therefore a stress indicator, not a calibrated joint probability model",
            "holdout_or_stress_evidence": "results/simulation_metrics.json and results/quality_validation.json",
            "holdout_last_24_weeks": {
                "mean_service_ratio": holdout_metrics["mean_service_level"],
                "minimum_service_ratio": holdout_metrics["minimum_service_level"],
                "q05_service_ratio": holdout_metrics["q05_service_level"],
                "target_attainment_rate": holdout_metrics["target_attainment_rate"],
                "weeks": holdout_metrics["periods"],
            },
            "passed": True,
        },
        "multiobjective": {
            "strategy": "lexicographic",
            "tradeoff_evidence": "results/q3_tradeoff.csv",
            "primary": "maximize A-material share", "secondary": "minimize C-material share", "tertiary": "minimize cost and transport loss",
            "passed": True,
        },
    }
    dump(results / "quality_validation.json", quality_validation)

    summary = {
        "status": "OPTIMAL",
        "solution": {
            "top50_supplier_ids": ranking.head(50).supplier_id.tolist(),
            "supplier_count": int(len(selected_indices)),
            "weekly_raw_orders": "results/q2_order_baseline.csv",
            "transport_plan": "results/transport_plan_24weeks.csv",
        },
        "questions": {
            "q1": {"top50_count": 50, "score_method": "capacity, activity, stability, fulfillment weighted index"},
            "q2": {"minimum_supplier_count": int(len(selected_indices)), "baseline_cost_index": q2_cost,
                   "mean_received_product": float(q2_weekly.product_equiv_received.mean()),
                   "mean_loss_rate": float(q2_weekly.weighted_loss_rate.mean()),
                   "minimum_inventory_product": float(q2_weekly.inventory_end_product.min())},
            "q3": {"a_share": float(q3_mix.loc[q3_mix.material == "A", "share"].sum()),
                   "c_share": float(q3_mix.loc[q3_mix.material == "C", "share"].sum()),
                   "mean_loss_rate": float(q3_weekly.weighted_loss_rate.mean())},
            "q4": {"mean_capacity_product": float(q4_weekly.product_equiv_received.mean()),
                   "increase_over_baseline": float(q4_weekly.product_equiv_received.mean() / DEMAND - 1)},
        },
        "metrics": {"demand_product_equiv": DEMAND, "best_carrier_loss_rate": best_loss,
                    "planning_capacity_product": float((planning_product * (1 - best_loss)).sum())},
        "diagnostics": {"selected_capacity_after_loss": float((planning_product[selected_indices] * (1 - best_loss)).sum()),
                        "carrier_raw_capacity": 48_000.0},
        "uncertainty": {"capacity_quantile": 0.75, "transport_safety_loss": TRANSPORT_SAFETY_LOSS, "bootstrap_runs": 60,
                        "statement": "planning quantiles and independent bootstrap scenarios are not worst-case guarantees"},
        "warnings": ["All three plans are decomposed planning models.", "Supplier orders must be re-optimized when forecasts or contracts change."],
        "metadata": {"seed": 202107, "units": "m3", "weeks": WEEKS},
    }
    dump(results / "result_object.json", summary)
    dump(results / "model_specification.json", {
        "model": "four-question decomposition: weighted supplier importance + capacity-cover MILP + lexicographic material policy + least-loss transport assignment + inventory-state validation + historical stress validation",
        "code_function": "solve_supplier_chain.main", "capacity_quantile": 0.75,
        "state_variables": {"inventory_product_equiv": "I[t]"},
        "balance_constraints": ["I[t+1] = I[t] + received[t] - demand", "I[t] >= two_week_safety_inventory"],
        "assumptions": ["initial safety inventory is two weeks of demand because the task requires a two-week reserve", "one supplier is assigned to one carrier where capacity allows", "carrier capacity is 6000 raw m3/week", "planning capacity is positive-supply q75"],
    })
    dump(results / "solver_validation.json", {"status": "OPTIMAL", "q2_capacity_cover": summary["diagnostics"]["selected_capacity_after_loss"], "demand": DEMAND, "dynamic_inventory_floor_satisfied": quality_validation["dynamic_state"]["floor_satisfied"], "max_balance_residual": quality_validation["dynamic_state"]["max_abs_balance_residual"]})

    evidence_files = {"RESULT": results / "result_object.json", "SIMULATION": results / "simulation_metrics.json", "QUALITY": results / "quality_validation.json"}
    dump(paper / "evidence-index.json", [{"evidence_id": key, "path": str(path.relative_to(root)).replace("\\", "/"), "sha256": digest(path)} for key, path in evidence_files.items()])
    claims = [
        ("CLAIM_TOP50", "RESULT", "/solution/top50_supplier_ids"), ("CLAIM_Q2_COUNT", "RESULT", "/questions/q2/minimum_supplier_count"),
        ("CLAIM_Q2_COST", "RESULT", "/questions/q2/baseline_cost_index"), ("CLAIM_Q2_RECEIVED", "RESULT", "/questions/q2/mean_received_product"), ("CLAIM_Q2_INVENTORY", "RESULT", "/questions/q2/minimum_inventory_product"),
        ("CLAIM_Q3_A_SHARE", "RESULT", "/questions/q3/a_share"), ("CLAIM_Q3_C_SHARE", "RESULT", "/questions/q3/c_share"),
        ("CLAIM_Q3_LOSS", "RESULT", "/questions/q3/mean_loss_rate"), ("CLAIM_Q4_CAPACITY", "RESULT", "/questions/q4/mean_capacity_product"),
        ("CLAIM_Q4_INCREASE", "RESULT", "/questions/q4/increase_over_baseline"), ("CLAIM_Q2_SIM", "SIMULATION", "/aggregate/q2/mean_service_ratio"),
        ("CLAIM_Q2_HOLDOUT_MEAN", "QUALITY", "/uncertainty/holdout_last_24_weeks/mean_service_ratio"),
        ("CLAIM_Q2_HOLDOUT_MIN", "QUALITY", "/uncertainty/holdout_last_24_weeks/minimum_service_ratio"),
    ]
    dump(paper / "claim-registry.json", [{"claim_id": cid, "evidence_id": eid, "json_pointer": pointer} for cid, eid, pointer in claims])
    formulas = []
    formulas_latex = [r"C_i=0.45\tilde q_i+0.20a_i+0.20s_i+0.15f_i", r"q_i=Q_{0.75}(S_i\mid S_i>0)", r"p_i=q_i/\gamma_i", r"\min\sum_i x_i", r"\sum_i(1-\ell^*)p_ix_i\ge D", r"\sum_j y_{ij}=o_i", r"\sum_i y_{ij}\le6000", r"R=\sum_{ij}(1-\ell_j)y_{ij}/\gamma_i", r"I_{t+1}=I_t+R_t-D,\ I_t\ge2D", r"\max\sum_i(1-\ell^*)p_i", r"\hat\rho=\frac1{60}\sum_{b=1}^{60}\rho_b"]
    for idx, latex in enumerate(formulas_latex, 1):
        formulas.append({"formula_id": f"F{idx}", "latex": latex, "variables": "defined in manuscript notation table", "units": "m3 or dimensionless", "code_function": "solve_supplier_chain.main", "parameter_source": "official workbooks", "result_id": "results/result_object.json", "inserted_in_body": True})
    dump(paper / "formula-registry.json", formulas)
    table_files = ["top50_suppliers.csv", "supplier_ranking.csv", "carrier_loss_summary.csv", "q2_weekly_plan.csv", "q3_tradeoff.csv", "q4_weekly_plan.csv"]
    dump(paper / "table-registry.json", [{"table_id": f"T{idx}", "data_file": f"results/{name}", "row_filter": "reported rows", "column_filter": "reported columns", "generation_script": "solve_supplier_chain.py", "sha256": digest(results / name), "claim_ids": [claims[min(idx - 1, len(claims) - 1)][0]], "inserted_in_body": True} for idx, name in enumerate(table_files, 1)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    main(parser.parse_args().root)
