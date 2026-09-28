from __future__ import annotations

import pytest

from algorithms.data_diagnostics import panel_diagnostics


def test_panel_diagnostics_separates_train_and_time_holdout() -> None:
    result = panel_diagnostics(
        [
            [0, 0, 1, 1, 2, 2],
            [1, 1, 1, 0, 0, 0],
        ],
        holdout_periods=2,
    )
    assert result["entities"] == 2
    assert result["periods"] == 6
    assert result["holdout"]["periods"] == 2
    assert result["holdout"]["holdout_mean"] == pytest.approx(1.0)
    assert 0 <= result["zero_fraction"] <= 1


def test_panel_diagnostics_rejects_non_temporal_holdout_size() -> None:
    with pytest.raises(ValueError, match="leave at least one"):
        panel_diagnostics([[1, 2], [3, 4]], holdout_periods=2)
