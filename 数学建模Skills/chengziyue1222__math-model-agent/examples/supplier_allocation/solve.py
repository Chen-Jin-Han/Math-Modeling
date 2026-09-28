"""Solve and independently validate a transportation allocation model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np

from algorithms.math_programming import linear_programming
from examples._common import write_json, write_manifest


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _northwest_corner(capacity: np.ndarray, demand: np.ndarray) -> np.ndarray:
    remaining_supply = capacity.copy()
    remaining_demand = demand.copy()
    allocation = np.zeros((len(capacity), len(demand)))
    i = j = 0
    while i < len(capacity) and j < len(demand):
        quantity = min(remaining_supply[i], remaining_demand[j])
        allocation[i, j] = quantity
        remaining_supply[i] -= quantity
        remaining_demand[j] -= quantity
        if remaining_supply[i] <= 1e-12:
            i += 1
        if remaining_demand[j] <= 1e-12:
            j += 1
    return allocation


def run(project_root: Path) -> dict:
    root = project_root.resolve()
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    data = json.loads((root / "data" / "transportation.json").read_text(encoding="utf-8"))
    capacity = np.asarray(data["capacity"], dtype=float)
    demand = np.asarray(data["demand"], dtype=float)
    unit_cost = np.asarray(data["unit_cost"], dtype=float)
    n_suppliers, n_regions = unit_cost.shape
    if unit_cost.shape != (len(capacity), len(demand)):
        raise ValueError("unit-cost matrix shape does not match supply and demand")
    if not np.isclose(capacity.sum(), demand.sum()):
        raise ValueError("this demonstration requires balanced total supply and demand")

    variables = n_suppliers * n_regions
    a_supply = np.zeros((n_suppliers, variables))
    for supplier in range(n_suppliers):
        a_supply[supplier, supplier * n_regions : (supplier + 1) * n_regions] = 1
    a_demand = np.zeros((n_regions, variables))
    for region in range(n_regions):
        a_demand[region, region::n_regions] = 1
    solution = linear_programming(
        unit_cost.ravel(),
        A_ub=a_supply,
        b_ub=capacity,
        A_eq=a_demand,
        b_eq=demand,
        bounds=[(0, None)] * variables,
    )
    if not solution["success"]:
        raise RuntimeError(f"transportation solver failed: {solution['message']}")
    allocation = np.asarray(solution["x"]).reshape(n_suppliers, n_regions)
    objective = float(np.sum(allocation * unit_cost))
    baseline = _northwest_corner(capacity, demand)
    baseline_cost = float(np.sum(baseline * unit_cost))
    savings = float((baseline_cost - objective) / baseline_cost * 100)
    tolerance = float(config["feasibility_tolerance"])
    supply_used = allocation.sum(axis=1)
    demand_met = allocation.sum(axis=0)
    checks = {
        "solver_success": bool(solution["success"]),
        "nonnegative_allocation": bool(np.all(allocation >= -tolerance)),
        "capacity_respected": bool(np.all(supply_used <= capacity + tolerance)),
        "demand_met": bool(np.allclose(demand_met, demand, atol=tolerance)),
        "objective_recomputed": bool(np.isclose(objective, solution["fun"], atol=tolerance)),
        "beats_feasible_baseline": objective < baseline_cost,
    }
    if not all(checks.values()):
        raise RuntimeError(f"allocation validation failed: {checks}")

    results = {
        "model": "balanced-transportation-linear-program",
        "model_version": config["model_version"],
        "suppliers": data["suppliers"],
        "regions": data["regions"],
        "allocation": allocation.tolist(),
        "supply_used": supply_used.tolist(),
        "demand_met": demand_met.tolist(),
        "metrics": {
            "optimal_cost": objective,
            "northwest_corner_cost": baseline_cost,
            "cost_savings_percent": savings,
        },
    }
    validation = {"passed": True, "checks": checks}
    write_json(root / "results" / "results.json", results)
    write_json(root / "reports" / "validation.json", validation)

    figure_path = root / "figures" / "allocation_matrix.svg"
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    image = ax.imshow(allocation, cmap="Blues", aspect="auto")
    for i in range(n_suppliers):
        for j in range(n_regions):
            ax.text(j, i, f"{allocation[i, j]:.0f}", ha="center", va="center", color="#111827")
    ax.set_xticks(range(n_regions), data["regions"])
    ax.set_yticks(range(n_suppliers), data["suppliers"])
    ax.set(xlabel="Demand region", ylabel="Supplier", title="Optimal shipped quantity")
    fig.colorbar(image, ax=ax, label="Quantity")
    fig.tight_layout()
    fig.savefig(figure_path, format="svg")
    plt.close(fig)

    specification = {
        "run_id": "supplier-allocation-v1",
        "problem": {
            "competition": "workflow-demo",
            "year": 2026,
            "code": "operations-research",
            "title": "Minimum-cost supplier allocation",
            "source": "data/transportation.json",
        },
        "stage": "validation",
        "status": "succeeded",
        "data_inputs": ["data/transportation.json", "config.json"],
        "model": {
            "name": "balanced-transportation-linear-program",
            "version": config["model_version"],
            "assumptions_path": "assumptions.md",
            "parameter_source": "config.json",
        },
        "execution": {
            "command": ["python", "-m", "examples.supplier_allocation.solve"],
            "deterministic": True,
            "random_seeds": {},
        },
        "parameters": config,
        "metrics": {
            "optimal_cost": {"value": objective, "unit": "cost units", "split": "full"},
            "baseline_cost": {"value": baseline_cost, "unit": "cost units", "split": "full"},
            "cost_savings": {"value": savings, "unit": "%", "split": "full"},
        },
        "failed_runs": [],
        "artifacts": [
            {"path": "results/results.json", "role": "machine-readable-results"},
            {"path": "reports/validation.json", "role": "validation-report"},
            {"path": "figures/allocation_matrix.svg", "role": "decision-figure"},
        ],
        "limitations": [
            "The synthetic example excludes fixed charges, integer trucks, and uncertain demand.",
            "Linear unit costs are assumed constant over the planning period.",
        ],
    }
    write_manifest(root, specification)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    results = run(args.project_root)
    print(json.dumps(results["metrics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
