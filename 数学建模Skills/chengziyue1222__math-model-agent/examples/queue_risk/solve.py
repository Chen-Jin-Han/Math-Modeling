"""Select queue capacity using analytical and seeded Monte Carlo evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np

from algorithms.monte_carlo import queuing_mmsk
from examples._common import write_json, write_manifest


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _confidence_interval(values: np.ndarray) -> tuple[float, float]:
    mean = float(values.mean())
    if len(values) < 2:
        return mean, mean
    half_width = 1.96 * float(values.std(ddof=1)) / np.sqrt(len(values))
    return mean - half_width, mean + half_width


def run(project_root: Path) -> dict:
    root = project_root.resolve()
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    candidates = []
    for servers in config["candidate_servers"]:
        runs = []
        for replication in range(int(config["replications"])):
            seed = int(config["base_seed"]) + servers * 1000 + replication
            runs.append(
                queuing_mmsk(
                    float(config["arrival_rate"]),
                    float(config["service_rate"]),
                    n_servers=int(servers),
                    capacity=int(config["system_capacity"]),
                    n_customers=int(config["customers_per_replication"]),
                    seed=seed,
                )
            )
        waits = np.array([run_result["sim_avg_wait_time"] for run_result in runs])
        rejection = np.array([run_result["sim_pk"] for run_result in runs])
        wait_ci = _confidence_interval(waits)
        rejection_ci = _confidence_interval(rejection)
        analytical_wait = float(runs[0]["avg_wait_time"])
        analytical_rejection = float(runs[0]["pk"])
        candidate = {
            "servers": int(servers),
            "rho": float(runs[0]["rho"]),
            "analytical_wait": analytical_wait,
            "analytical_rejection_probability": analytical_rejection,
            "simulated_mean_wait": float(waits.mean()),
            "simulated_wait_ci95": list(wait_ci),
            "simulated_rejection_probability": float(rejection.mean()),
            "simulated_rejection_ci95": list(rejection_ci),
            "meets_targets": bool(
                waits.mean() <= float(config["max_mean_wait"])
                and rejection.mean() <= float(config["max_rejection_probability"])
            ),
        }
        candidates.append(candidate)

    feasible = [candidate for candidate in candidates if candidate["meets_targets"]]
    if not feasible:
        raise RuntimeError("no candidate server count meets both risk targets")
    selected = min(feasible, key=lambda candidate: candidate["servers"])
    rejected = [
        {
            "run_id": f"queue-{candidate['servers']}-servers",
            "reason": "candidate violates at least one wait or rejection target",
            "diagnostics_path": "reports/rejected-candidates.json",
        }
        for candidate in candidates
        if not candidate["meets_targets"]
    ]
    reproducibility_probe = queuing_mmsk(
        float(config["arrival_rate"]),
        float(config["service_rate"]),
        n_servers=int(selected["servers"]),
        capacity=int(config["system_capacity"]),
        n_customers=int(config["customers_per_replication"]),
        seed=int(config["base_seed"]) + int(selected["servers"]) * 1000,
    )
    first_selected_run = queuing_mmsk(
        float(config["arrival_rate"]),
        float(config["service_rate"]),
        n_servers=int(selected["servers"]),
        capacity=int(config["system_capacity"]),
        n_customers=int(config["customers_per_replication"]),
        seed=int(config["base_seed"]) + int(selected["servers"]) * 1000,
    )
    checks = {
        "selected_candidate_meets_targets": bool(selected["meets_targets"]),
        "smallest_feasible_candidate_selected": selected["servers"]
        == min(candidate["servers"] for candidate in feasible),
        "fixed_seed_reproduces_wait": reproducibility_probe["sim_avg_wait_time"]
        == first_selected_run["sim_avg_wait_time"],
        "fixed_seed_reproduces_rejection": reproducibility_probe["sim_pk"]
        == first_selected_run["sim_pk"],
        "analytical_rejection_inside_broad_simulation_tolerance": abs(
            selected["analytical_rejection_probability"]
            - selected["simulated_rejection_probability"]
        )
        < 0.05,
        "candidate_server_counts_are_ordered": [candidate["servers"] for candidate in candidates]
        == sorted(config["candidate_servers"]),
    }
    if not all(checks.values()):
        raise RuntimeError(f"queue validation failed: {checks}")

    results = {
        "model": "seeded-m-m-s-k-design",
        "model_version": config["model_version"],
        "selected_servers": selected["servers"],
        "selected": selected,
        "candidates": candidates,
        "targets": {
            "max_mean_wait": config["max_mean_wait"],
            "max_rejection_probability": config["max_rejection_probability"],
        },
    }
    validation = {"passed": True, "checks": checks}
    write_json(root / "results" / "results.json", results)
    write_json(root / "reports" / "validation.json", validation)
    write_json(root / "reports" / "rejected-candidates.json", rejected)

    figure_path = root / "figures" / "queue_design.svg"
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    servers = np.array([candidate["servers"] for candidate in candidates])
    waits = np.array([candidate["simulated_mean_wait"] for candidate in candidates])
    rejection = np.array(
        [candidate["simulated_rejection_probability"] for candidate in candidates]
    )
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4))
    axes[0].plot(servers, waits, marker="o", color="#0072B2")
    axes[0].axhline(config["max_mean_wait"], color="#D55E00", linestyle="--", label="Target")
    axes[0].set(xlabel="Servers", ylabel="Mean wait", title="Waiting-time risk")
    axes[1].plot(servers, rejection, marker="o", color="#009E73")
    axes[1].axhline(
        config["max_rejection_probability"], color="#D55E00", linestyle="--", label="Target"
    )
    axes[1].set(xlabel="Servers", ylabel="Rejection probability", title="Capacity risk")
    for axis in axes:
        axis.set_xticks(servers)
        axis.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(figure_path, format="svg")
    plt.close(fig)

    specification = {
        "run_id": "queue-risk-v1",
        "problem": {
            "competition": "workflow-demo",
            "year": 2026,
            "code": "random-simulation",
            "title": "Finite-capacity service-system design",
            "source": "config.json",
        },
        "stage": "validation",
        "status": "succeeded",
        "data_inputs": ["config.json"],
        "model": {
            "name": "seeded-m-m-s-k-design",
            "version": config["model_version"],
            "assumptions_path": "assumptions.md",
            "parameter_source": "config.json",
        },
        "execution": {
            "command": ["python", "-m", "examples.queue_risk.solve"],
            "deterministic": False,
            "random_seeds": {"numpy_base": int(config["base_seed"])},
        },
        "parameters": config,
        "metrics": {
            "selected_servers": {
                "value": selected["servers"],
                "unit": "servers",
                "split": "simulation",
            },
            "mean_wait": {
                "value": selected["simulated_mean_wait"],
                "unit": "time units",
                "split": "simulation",
            },
            "rejection_probability": {
                "value": selected["simulated_rejection_probability"],
                "unit": "probability",
                "split": "simulation",
            },
        },
        "failed_runs": rejected,
        "artifacts": [
            {"path": "results/results.json", "role": "machine-readable-results"},
            {"path": "reports/validation.json", "role": "validation-report"},
            {"path": "reports/rejected-candidates.json", "role": "failed-candidate-log"},
            {"path": "figures/queue_design.svg", "role": "decision-figure"},
        ],
        "limitations": [
            "Poisson arrivals and exponential service may not fit real service systems.",
            "The decision rule omits server cost and time-varying demand.",
        ],
    }
    write_manifest(root, specification)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    results = run(args.project_root)
    print(
        json.dumps(
            {"selected_servers": results["selected_servers"], **results["selected"]},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
