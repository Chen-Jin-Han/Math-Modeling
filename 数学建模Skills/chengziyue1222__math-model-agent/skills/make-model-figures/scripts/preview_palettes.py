"""Render compact previews of the semantic mathematical-modeling palettes."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

try:
    from algorithms.sci_figures import (
        MODELING_PALETTES,
        add_panel_label,
        get_modeling_palette,
        publication_rc_params,
        publication_size,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - environment diagnostic
    raise SystemExit(
        "The installed 'algorithms' package is required to preview modeling palettes."
    ) from exc


def render_palette_preview(theme_name: str, output_path: Path) -> Path:
    """Render one theme as categorical, trend, diverging, and sequential examples."""
    palette = get_modeling_palette(theme_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    x = np.linspace(0.0, 8.0, 120)

    with mpl.rc_context(publication_rc_params(language="zh")):
        fig, axes = plt.subplots(
            2,
            2,
            figsize=publication_size("double", 112),
            constrained_layout=True,
        )
        categorical = palette["categorical"]

        axes[0, 0].bar(
            ["方案 A", "方案 B", "方案 C", "方案 D"],
            [3.1, 4.2, 3.6, 5.0],
            color=categorical[:4],
        )
        axes[0, 0].set(ylabel="响应值", title="类别比较")

        for index, label in enumerate(("基准", "方案 B", "方案 C")):
            y = 0.48 + index * 0.15 + 0.22 * np.sin(x / 1.4)
            color = categorical[index]
            axes[0, 1].plot(x, y, color=color, linewidth=1.2)
            axes[0, 1].fill_between(x, y - 0.05, y + 0.05, color=color, alpha=0.2)
            axes[0, 1].text(x[-1] + 0.12, y[-1], label, color=color, va="center")
        axes[0, 1].set(xlabel="时间", ylabel="归一化值", title="趋势与区间")
        axes[0, 1].spines["right"].set_visible(False)
        axes[0, 1].spines["top"].set_visible(False)

        matrix = np.linspace(-1.0, 1.0, 20).reshape(4, 5)
        diverging = mpl.colors.LinearSegmentedColormap.from_list(
            f"{theme_name}-diverging", palette["diverging"]
        )
        image = axes[1, 0].imshow(matrix, cmap=diverging, vmin=-1, vmax=1, aspect="auto")
        axes[1, 0].set(
            xticks=np.arange(5),
            xticklabels=["S1", "S2", "S3", "S4", "S5"],
            yticks=np.arange(4),
            yticklabels=["G1", "G2", "G3", "G4"],
            title="发散量",
        )
        fig.colorbar(image, ax=axes[1, 0], label="效应")

        sequential = mpl.colors.LinearSegmentedColormap.from_list(
            f"{theme_name}-sequential", palette["sequential"]
        )
        axes[1, 1].imshow(np.linspace(0, 1, 256)[None, :], cmap=sequential, aspect="auto")
        axes[1, 1].set(
            xticks=[0, 128, 255],
            xticklabels=["低", "中", "高"],
            yticks=[],
            title="顺序量",
        )

        for label, axis in zip("abcd", axes.flat):
            add_panel_label(axis, label)
        fig.suptitle(f"{theme_name}｜数学建模配色预览", fontsize=9, fontweight="bold")
        fig.savefig(output_path, dpi=220, facecolor="white")
        plt.close(fig)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--theme",
        choices=sorted(MODELING_PALETTES),
        default="nature-accessible",
        help="Palette theme to preview.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("figures/palette-preview.png"),
        help="PNG output path.",
    )
    args = parser.parse_args()
    path = render_palette_preview(args.theme, args.output)
    print(path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
