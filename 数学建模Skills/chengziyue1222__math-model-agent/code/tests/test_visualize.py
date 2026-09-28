import json

import matplotlib
import pytest

matplotlib.use("Agg")

from solve import average_power, wave_params
from visualize import generate_figures


def test_saved_power_matches_current_model_and_figures_generate(tmp_path):
    results_path = tmp_path.parent.parent / "code" / "results.json"
    if not results_path.exists():
        # Normal repository test layout: this test lives under code/tests.
        from pathlib import Path

        results_path = Path(__file__).resolve().parents[1] / "results.json"

    results = json.loads(results_path.read_text(encoding="utf-8"))
    params = results["optimal_params"]
    wave = results["wave_params"]
    omega, wave_number = wave_params(wave["H"], wave["T"], wave["h"])
    recomputed = average_power(
        [params["r"], params["d"], params["ks"], params["cd"]],
        omega,
        wave_number,
        wave["H"],
        wave["h"],
    )

    assert recomputed == pytest.approx(results["max_power_W"], rel=1e-4)

    paths = generate_figures(results_path, tmp_path / "figures")
    assert len(paths) == 4
    assert all(path.exists() and path.stat().st_size > 10_000 for path in paths)
