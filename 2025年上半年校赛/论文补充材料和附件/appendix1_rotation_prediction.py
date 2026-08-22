"""附录 1（第二部分）：测角误差下的旋转几何预测实验。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from appendix1_trajectory_filter import (
    A0,
    DRAG_RANGE,
    DT,
    N,
    VELOCITY,
    position_rmse,
    r2_score,
)


def generate_trajectories(
    *, seed: int = 42, n: int = N, sigma_alpha_deg: float = 1.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """返回真实、含误差、理想轨迹以及每帧实际测角误差。"""
    rng = np.random.default_rng(seed)
    true = A0 + np.arange(n, dtype=float)[:, None] * DT * VELOCITY
    ranges = np.linalg.norm(true, axis=1)
    radial = true / ranges[:, None]
    ideal = true + DRAG_RANGE * radial
    alpha = rng.normal(0.0, np.deg2rad(sigma_alpha_deg), size=n)
    measured_direction = np.column_stack(
        (
            np.cos(np.arctan2(radial[:, 1], radial[:, 0]) + alpha),
            np.sin(np.arctan2(radial[:, 1], radial[:, 0]) + alpha),
        )
    )
    range_error = (1.0 - np.cos(alpha)) * ranges / 2.0
    noisy = ideal - range_error[:, None] * measured_direction
    return true, noisy, ideal, alpha


def rotate_vectors(vectors: np.ndarray, angles: np.ndarray) -> np.ndarray:
    """逐行旋转二维向量，避免原附录只使用固定标准差角。"""
    vectors = np.asarray(vectors, dtype=float)
    angles = np.asarray(angles, dtype=float)
    if vectors.ndim != 2 or vectors.shape[1] != 2 or angles.shape != (len(vectors),):
        raise ValueError("vectors 应为 (n, 2)，angles 应为 (n,)")
    cosine, sine = np.cos(angles), np.sin(angles)
    return np.column_stack((cosine * vectors[:, 0] - sine * vectors[:, 1], sine * vectors[:, 0] + cosine * vectors[:, 1]))


def predict_rotated_trajectory(true: np.ndarray, ideal: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """按论文旋转构型预测：将真目标至理想假目标的拖引向量旋转。"""
    displacement = ideal - true
    return true + rotate_vectors(displacement, alpha)


def run_experiment(*, seed: int = 42) -> dict[str, object]:
    true, noisy, ideal, alpha = generate_trajectories(seed=seed)
    predicted = predict_rotated_trajectory(true, ideal, alpha)
    metrics = {
        "measured_rmse_m": position_rmse(ideal, noisy),
        "rotated_prediction_rmse_m": position_rmse(ideal, predicted),
        "measured_r2": r2_score(ideal, noisy),
    }
    return {"true": true, "noisy": noisy, "ideal": ideal, "predicted": predicted, "alpha": alpha, "metrics": metrics}


def save_results(result: dict[str, object], output_dir: Path, *, show: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(json.dumps(result["metrics"], ensure_ascii=False, indent=2), encoding="utf-8")
    data = np.column_stack((result["true"], result["ideal"], result["noisy"], result["predicted"], result["alpha"]))
    np.savetxt(output_dir / "trajectories.csv", data, delimiter=",", header="true_x,true_y,ideal_x,ideal_y,noisy_x,noisy_y,predicted_x,predicted_y,alpha_rad", comments="")
    fig, ax = plt.subplots(figsize=(10, 6))
    for key, style, label in (("true", "--", "True target"), ("ideal", "-", "Ideal false target"), ("noisy", ".", "Measured false target"), ("predicted", "-", "Rotated prediction")):
        trajectory = result[key]
        ax.plot(trajectory[:, 0] / 1e3, trajectory[:, 1] / 1e3, style, label=label, alpha=0.8)
    ax.set(xlabel="X (km)", ylabel="Y (km)", title="Angular-error rotation model")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "rotation_prediction.png", dpi=180)
    if show:
        plt.show()
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/appendix1_rotation"))
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()
    result = run_experiment(seed=args.seed)
    save_results(result, args.output_dir, show=args.show)
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
