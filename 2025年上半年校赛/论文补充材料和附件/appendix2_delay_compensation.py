"""附录 2：测角误差条件下的假目标时延补偿。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


LIGHT_SPEED = 3e8
A0 = np.array([50e3, 55e3], dtype=float)
VELOCITY = np.array([50.0, 350.0])
N = 60
DT = 1.0
DELAY_SECONDS = 2e-6
SIGMA_ALPHA_DEG = 2.0


def generate_trajectory(
    *, seed: int = 42, n: int = N, sigma_alpha_deg: float = SIGMA_ALPHA_DEG
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """生成目标、理想假目标、实际假目标和最小误差时延补偿轨迹。"""
    rng = np.random.default_rng(seed)
    true = A0 + np.arange(n, dtype=float)[:, None] * DT * VELOCITY
    true_ranges = np.linalg.norm(true, axis=1)
    true_direction = true / true_ranges[:, None]
    alpha = rng.normal(0.0, np.deg2rad(sigma_alpha_deg), size=n)
    true_bearing = np.arctan2(true_direction[:, 1], true_direction[:, 0])
    measured_direction = np.column_stack((np.cos(true_bearing + alpha), np.sin(true_bearing + alpha)))

    drag_range = LIGHT_SPEED * DELAY_SECONDS / 2.0
    ideal = true + drag_range * true_direction
    actual = true + drag_range * measured_direction

    # 在只能调节时延（即沿测得方向调节距离）的约束下，将理想偏移向量
    # 投影到测得方向，得到每帧欧氏误差最小的非负拖引距离。
    optimized_range = np.maximum(0.0, drag_range * np.sum(true_direction * measured_direction, axis=1))
    optimized_delay = 2.0 * optimized_range / LIGHT_SPEED
    optimized = true + optimized_range[:, None] * measured_direction
    return true, ideal, actual, optimized, optimized_delay


def calculate_metrics(reference: np.ndarray, estimate: np.ndarray) -> tuple[float, float, np.ndarray]:
    errors = np.linalg.norm(np.asarray(estimate) - np.asarray(reference), axis=1)
    rmse = float(np.sqrt(np.mean(errors**2)))
    residual = np.sum((np.asarray(estimate) - np.asarray(reference)) ** 2)
    total = np.sum((np.asarray(reference) - np.mean(reference, axis=0)) ** 2)
    return rmse, float(1.0 - residual / total), errors


def run_experiment(*, seed: int = 42) -> dict[str, object]:
    true, ideal, actual, optimized, optimized_delay = generate_trajectory(seed=seed)
    actual_rmse, actual_r2, actual_errors = calculate_metrics(ideal, actual)
    optimized_rmse, optimized_r2, optimized_errors = calculate_metrics(ideal, optimized)
    metrics = {
        "actual_rmse_m": actual_rmse,
        "actual_r2": actual_r2,
        "optimized_rmse_m": optimized_rmse,
        "optimized_r2": optimized_r2,
        "mean_optimized_delay_us": float(np.mean(optimized_delay) * 1e6),
    }
    return {
        "true": true,
        "ideal": ideal,
        "actual": actual,
        "optimized": optimized,
        "optimized_delay": optimized_delay,
        "actual_errors": actual_errors,
        "optimized_errors": optimized_errors,
        "metrics": metrics,
    }


def save_results(result: dict[str, object], output_dir: Path, *, show: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(json.dumps(result["metrics"], ensure_ascii=False, indent=2), encoding="utf-8")
    data = np.column_stack((result["true"], result["ideal"], result["actual"], result["optimized"], result["optimized_delay"]))
    np.savetxt(output_dir / "trajectories.csv", data, delimiter=",", header="true_x,true_y,ideal_x,ideal_y,actual_x,actual_y,optimized_x,optimized_y,optimized_delay_s", comments="")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for key, style, label in (("true", "-", "True target"), ("ideal", "--", "Ideal false target"), ("actual", "-.", "Actual false target"), ("optimized", ":", "Delay optimized")):
        trajectory = result[key]
        axes[0].plot(trajectory[:, 0], trajectory[:, 1], style, label=label)
    axes[0].set(xlabel="X (m)", ylabel="Y (m)", title="False-target trajectories")
    axes[0].grid(True)
    axes[0].legend()
    axes[1].hist(result["actual_errors"], bins=20, alpha=0.65, label="Actual")
    axes[1].hist(result["optimized_errors"], bins=20, alpha=0.65, label="Optimized")
    axes[1].set(xlabel="Position error (m)", ylabel="Frequency", title="Error distributions")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(output_dir / "delay_compensation.png", dpi=180)
    if show:
        plt.show()
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/appendix2_delay"))
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()
    result = run_experiment(seed=args.seed)
    save_results(result, args.output_dir, show=args.show)
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
