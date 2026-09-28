"""Generate figures for the wave-energy optimization example."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import solve_ivp

from solve import (
    G,
    PI,
    RHO,
    added_mass_and_damping,
    average_power,
    excitation_force,
    wave_params,
)


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RESULTS_PATH = Path(__file__).resolve().with_name("results.json")
DEFAULT_OUTPUT_DIR = ROOT / "figures"
PARAMETER_BOUNDS = (
    (0.5, 5.0),
    (0.5, 10.0),
    (1_000.0, 1_000_000.0),
    (100.0, 100_000.0),
)

def _configure_matplotlib() -> None:
    """Restore plotting defaults in case another module changed global rcParams."""
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    matplotlib.rcParams["figure.dpi"] = 150
    matplotlib.rcParams["savefig.dpi"] = 300
    matplotlib.rcParams["savefig.bbox"] = "tight"


_configure_matplotlib()


def load_results(path: str | Path = DEFAULT_RESULTS_PATH) -> dict:
    """Load a saved optimization result."""
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def _problem_values(
    results: dict,
) -> tuple[np.ndarray, float, float, float, float, float, float]:
    optimal = results["optimal_params"]
    wave = results["wave_params"]
    params = np.array(
        [optimal["r"], optimal["d"], optimal["ks"], optimal["cd"]], dtype=float
    )
    height = float(wave["H"])
    period = float(wave["T"])
    depth = float(wave["h"])
    omega, wave_number = wave_params(height, period, depth)
    power = average_power(params, omega, wave_number, height, depth)
    return params, height, period, depth, omega, wave_number, power


def _save(fig: plt.Figure, output_dir: Path, filename: str) -> Path:
    path = output_dir / filename
    fig.savefig(path)
    plt.close(fig)
    return path


def _time_history_figure(
    params: np.ndarray,
    height: float,
    period: float,
    depth: float,
    omega: float,
    wave_number: float,
    best_power: float,
) -> plt.Figure:
    radius, draft, stiffness, damping = params
    mass = RHO * PI * radius**2 * draft
    added_mass, radiation_damping = added_mass_and_damping(
        radius, draft, omega, wave_number
    )
    total_mass = mass + added_mass
    total_damping = radiation_damping + damping
    total_stiffness = stiffness + RHO * G * PI * radius**2
    force = excitation_force(radius, draft, height, wave_number, depth)

    def motion_equation(time: float, state: np.ndarray) -> list[float]:
        displacement, velocity = state
        acceleration = (
            force * np.cos(omega * time)
            - total_damping * velocity
            - total_stiffness * displacement
        ) / total_mass
        return [velocity, acceleration]

    time = np.linspace(0.0, 6.0 * period, 2_000)
    solution = solve_ivp(
        motion_equation,
        (float(time[0]), float(time[-1])),
        [0.0, 0.0],
        t_eval=time,
        method="RK45",
    )
    displacement = solution.y[0]
    velocity = solution.y[1]
    instantaneous_power = damping * velocity**2
    wave_displacement = (height / 2.0) * np.cos(omega * time)

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    axes[0].plot(time, wave_displacement, "b-", linewidth=1.5, label="波面位移")
    axes[0].set_ylabel("位移 (m)")
    axes[0].set_title("波面位移", fontsize=14)
    axes[1].plot(time, displacement, "r-", linewidth=1.5, label="浮子位移")
    axes[1].set_ylabel("位移 (m)")
    axes[1].set_title("浮子垂荡位移", fontsize=14)
    axes[2].plot(time, instantaneous_power, "g-", linewidth=1.5, label="瞬时功率")
    axes[2].axhline(
        best_power, color="r", linestyle="--", label=f"解析平均功率 = {best_power:.1f} W"
    )
    axes[2].set_xlabel("时间 (s)")
    axes[2].set_ylabel("功率 (W)")
    axes[2].set_title("瞬时输出功率", fontsize=14)
    for axis in axes:
        axis.legend()
        axis.grid(True, alpha=0.3)
    fig.suptitle("波浪能转换装置运动与功率特性", fontsize=16, fontweight="bold")
    fig.tight_layout()
    return fig


def _damping_figure(
    params: np.ndarray,
    height: float,
    depth: float,
    omega: float,
    wave_number: float,
    best_power: float,
) -> plt.Figure:
    damping_values = np.linspace(100.0, 140_000.0, 500)
    powers = [
        average_power(
            [params[0], params[1], params[2], damping],
            omega,
            wave_number,
            height,
            depth,
        )
        for damping in damping_values
    ]

    fig, axis = plt.subplots(figsize=(10, 6))
    axis.plot(damping_values, powers, "b-", linewidth=2)
    axis.axvline(
        params[3], color="r", linestyle="--", label=f"保存参数 $c_d$ = {params[3]:.0f} N·s/m"
    )
    axis.axhline(best_power, color="g", linestyle=":", label=f"功率 = {best_power:.1f} W")
    axis.set_xlabel("阻尼系数 $c_d$ (N·s/m)", fontsize=14)
    axis.set_ylabel("平均输出功率 $\\bar{P}$ (W)", fontsize=14)
    axis.set_title("平均输出功率 vs 阻尼系数", fontsize=16)
    axis.legend(fontsize=11)
    axis.grid(True, alpha=0.3)
    return fig


def _heatmap_figure(
    params: np.ndarray,
    height: float,
    depth: float,
    omega: float,
    wave_number: float,
) -> plt.Figure:
    radius_values = np.linspace(*PARAMETER_BOUNDS[0], 50)
    draft_values = np.linspace(*PARAMETER_BOUNDS[1], 50)
    radii, drafts = np.meshgrid(radius_values, draft_values)
    power_grid = np.empty_like(radii)
    for row in range(power_grid.shape[0]):
        for column in range(power_grid.shape[1]):
            power_grid[row, column] = average_power(
                [radii[row, column], drafts[row, column], params[2], params[3]],
                omega,
                wave_number,
                height,
                depth,
            )

    fig, axis = plt.subplots(figsize=(10, 8))
    image = axis.pcolormesh(radii, drafts, power_grid, cmap="hot", shading="auto")
    axis.plot(
        params[0], params[1], "w*", markersize=20, label=f"保存参数 ({params[0]:.2f}, {params[1]:.2f})"
    )
    axis.set_xlabel("浮子半径 $r$ (m)", fontsize=14)
    axis.set_ylabel("吃水深度 $d$ (m)", fontsize=14)
    axis.set_title("平均输出功率热力图 ($r$ vs $d$)", fontsize=16)
    axis.legend(fontsize=11, loc="upper left")
    fig.colorbar(image, ax=axis, label="功率 (W)")
    return fig


def _sensitivity_figure(
    params: np.ndarray,
    height: float,
    depth: float,
    omega: float,
    wave_number: float,
    best_power: float,
) -> plt.Figure:
    names = ["半径 $r$", "吃水 $d$", "刚度 $k_s$", "阻尼 $c_d$"]
    negative_changes = []
    positive_changes = []
    for index, bounds in enumerate(PARAMETER_BOUNDS):
        for factor, changes in ((0.9, negative_changes), (1.1, positive_changes)):
            trial = params.copy()
            trial[index] = np.clip(trial[index] * factor, *bounds)
            trial_power = average_power(trial, omega, wave_number, height, depth)
            changes.append((trial_power - best_power) / best_power * 100.0)

    fig, axis = plt.subplots(figsize=(10, 6))
    positions = np.arange(len(names))
    axis.barh(positions, positive_changes, height=0.4, color="steelblue", label="+10%（边界裁剪）")
    axis.barh(positions, negative_changes, height=0.4, color="coral", label="-10%（边界裁剪）")
    axis.set_yticks(positions, labels=names, fontsize=13)
    axis.set_xlabel("功率变化 (%)", fontsize=14)
    axis.set_title("参数局部敏感度分析", fontsize=16)
    axis.legend(fontsize=11)
    axis.grid(True, alpha=0.3, axis="x")
    axis.axvline(0, color="black", linewidth=0.8)
    return fig


def generate_figures(
    results_path: str | Path = DEFAULT_RESULTS_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> list[Path]:
    """Generate all four example figures and return their paths."""
    _configure_matplotlib()
    results = load_results(results_path)
    params, height, period, depth, omega, wave_number, best_power = _problem_values(results)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    figures = (
        ("fig01_time_history.png", _time_history_figure(
            params, height, period, depth, omega, wave_number, best_power
        )),
        ("fig02_power_vs_damping.png", _damping_figure(
            params, height, depth, omega, wave_number, best_power
        )),
        ("fig03_power_heatmap.png", _heatmap_figure(
            params, height, depth, omega, wave_number
        )),
        ("fig04_sensitivity.png", _sensitivity_figure(
            params, height, depth, omega, wave_number, best_power
        )),
    )
    return [_save(figure, output, filename) for filename, figure in figures]


def main() -> None:
    for path in generate_figures():
        print(f"已生成: {path}")


if __name__ == "__main__":
    main()
