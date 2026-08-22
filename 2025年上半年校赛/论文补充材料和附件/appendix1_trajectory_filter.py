"""附录 1（第一部分）：假目标轨迹生成、拟合与卡尔曼滤波。

本文件依据论文附录恢复，并修正了原表格代码中的排版断行与逐帧欠定拟合。
卡尔曼滤波使用 NumPy 实现，因此不再依赖未随论文提供的 filterpy。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares


N = 100
DT = 1.0
SIGMA_ALPHA_DEG = 0.5
A0 = np.array([50e3, 55e3], dtype=float)
VELOCITY = np.array([50.0, 350.0])
DRAG_RANGE = 1000.0


def generate_trajectories(
    *, seed: int = 42, n: int = N, sigma_alpha_deg: float = SIGMA_ALPHA_DEG
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """生成真实目标、含测角误差的假目标和理想假目标轨迹。"""
    rng = np.random.default_rng(seed)
    times = np.arange(n, dtype=float)[:, None] * DT
    true_trajectory = A0 + times * VELOCITY
    ranges = np.linalg.norm(true_trajectory, axis=1)
    radial = true_trajectory / ranges[:, None]
    ideal_trajectory = true_trajectory + DRAG_RANGE * radial

    alpha = rng.normal(0.0, np.deg2rad(sigma_alpha_deg), size=n)
    random_angle = rng.uniform(-np.pi, np.pi, size=n)
    error_direction = np.column_stack((np.cos(random_angle), np.sin(random_angle)))
    range_error = (1.0 - np.cos(alpha)) * ranges / 2.0
    noisy_trajectory = ideal_trajectory - range_error[:, None] * error_direction
    return true_trajectory, noisy_trajectory, ideal_trajectory


def fit_constant_velocity(trajectory: np.ndarray, *, dt: float = DT) -> np.ndarray:
    """按“匀速真目标 + 固定径向拖引”模型联合拟合全部观测。"""
    trajectory = np.asarray(trajectory, dtype=float)
    if trajectory.ndim != 2 or trajectory.shape[1] != 2 or len(trajectory) < 2:
        raise ValueError("trajectory 必须是至少包含两帧的 (n, 2) 数组")
    times = np.arange(len(trajectory), dtype=float)[:, None] * dt
    first_radial = trajectory[0] / np.linalg.norm(trajectory[0])
    target_start = trajectory[0] - DRAG_RANGE * first_radial
    initial_velocity = (trajectory[-1] - trajectory[0]) / ((len(trajectory) - 1) * dt)
    initial_parameters = np.r_[target_start, initial_velocity]

    def predict(parameters: np.ndarray) -> np.ndarray:
        target = parameters[:2] + times * parameters[2:]
        radial = target / np.linalg.norm(target, axis=1)[:, None]
        return target + DRAG_RANGE * radial

    result = least_squares(
        lambda parameters: (predict(parameters) - trajectory).ravel(),
        initial_parameters,
        method="trf",
    )
    if not result.success:
        raise RuntimeError(f"轨迹拟合失败: {result.message}")
    return predict(result.x)


def kalman_filter(
    measurements: np.ndarray,
    *,
    dt: float = DT,
    process_variance: float = 1e-3,
    measurement_variance: float = 4.0,
) -> np.ndarray:
    """用二维常速度模型平滑位置观测。"""
    measurements = np.asarray(measurements, dtype=float)
    if measurements.ndim != 2 or measurements.shape[1] != 2 or len(measurements) < 2:
        raise ValueError("measurements 必须是至少包含两帧的 (n, 2) 数组")
    if process_variance < 0 or measurement_variance <= 0:
        raise ValueError("噪声方差参数必须为正")

    f = np.array(
        [[1.0, 0.0, dt, 0.0], [0.0, 1.0, 0.0, dt], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    )
    h = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])
    q_base = np.array(
        [
            [dt**4 / 4, 0.0, dt**3 / 2, 0.0],
            [0.0, dt**4 / 4, 0.0, dt**3 / 2],
            [dt**3 / 2, 0.0, dt**2, 0.0],
            [0.0, dt**3 / 2, 0.0, dt**2],
        ]
    )
    q = process_variance * q_base
    r = measurement_variance * np.eye(2)
    state = np.r_[measurements[0], measurements[1] - measurements[0]]
    covariance = np.diag([measurement_variance, measurement_variance, 25.0, 25.0])
    identity = np.eye(4)
    filtered = np.empty_like(measurements)
    filtered[0] = state[:2]

    for index, measurement in enumerate(measurements[1:], start=1):
        state = f @ state
        covariance = f @ covariance @ f.T + q
        innovation = measurement - h @ state
        innovation_covariance = h @ covariance @ h.T + r
        gain = np.linalg.solve(innovation_covariance, h @ covariance).T
        state = state + gain @ innovation
        covariance = (identity - gain @ h) @ covariance
        filtered[index] = state[:2]
    return filtered


def position_rmse(reference: np.ndarray, estimate: np.ndarray) -> float:
    """计算每帧欧氏位置误差的均方根。"""
    reference = np.asarray(reference, dtype=float)
    estimate = np.asarray(estimate, dtype=float)
    if reference.shape != estimate.shape:
        raise ValueError("reference 与 estimate 的形状必须一致")
    return float(np.sqrt(np.mean(np.sum((reference - estimate) ** 2, axis=1))))


def r2_score(reference: np.ndarray, estimate: np.ndarray) -> float:
    reference = np.asarray(reference, dtype=float)
    estimate = np.asarray(estimate, dtype=float)
    residual = np.sum((reference - estimate) ** 2)
    total = np.sum((reference - np.mean(reference, axis=0)) ** 2)
    return float(1.0 - residual / total)


def run_experiment(*, seed: int = 42) -> dict[str, object]:
    true, noisy, ideal = generate_trajectories(seed=seed)
    fitted = fit_constant_velocity(noisy)
    filtered = kalman_filter(noisy)
    metrics = {
        "noisy_rmse_m": position_rmse(ideal, noisy),
        "fitted_rmse_m": position_rmse(ideal, fitted),
        "filtered_rmse_m": position_rmse(ideal, filtered),
        "filtered_r2": r2_score(ideal, filtered),
    }
    return {"true": true, "noisy": noisy, "ideal": ideal, "fitted": fitted, "filtered": filtered, "metrics": metrics}


def save_results(result: dict[str, object], output_dir: Path, *, show: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics = result["metrics"]
    (output_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    data = np.column_stack((result["true"], result["ideal"], result["noisy"], result["fitted"], result["filtered"]))
    np.savetxt(
        output_dir / "trajectories.csv",
        data,
        delimiter=",",
        header="true_x,true_y,ideal_x,ideal_y,noisy_x,noisy_y,fitted_x,fitted_y,filtered_x,filtered_y",
        comments="",
    )
    fig, ax = plt.subplots(figsize=(10, 6))
    for key, style, label in (
        ("true", "--", "True target"),
        ("ideal", "-", "Ideal false target"),
        ("noisy", ".", "Measured false target"),
        ("fitted", "-", "Global least-squares fit"),
        ("filtered", "-", "Kalman filtered"),
    ):
        trajectory = result[key]
        ax.plot(trajectory[:, 0] / 1e3, trajectory[:, 1] / 1e3, style, label=label, alpha=0.8)
    ax.set(xlabel="X (km)", ylabel="Y (km)", title="False-target trajectory fitting and filtering")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "trajectory_comparison.png", dpi=180)
    if show:
        plt.show()
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/appendix1_filter"))
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()
    result = run_experiment(seed=args.seed)
    save_results(result, args.output_dir, show=args.show)
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
