from algorithms.sci_figures import MODELING_PAPER_THEME, paper_figure_rc_params


def test_paper_figure_theme_is_restrained_and_readable():
    params = paper_figure_rc_params()
    assert params["figure.facecolor"] == "#FFFFFF"
    assert params["axes.grid"] is True
    assert params["font.size"] >= 7
    assert params["grid.color"] == MODELING_PAPER_THEME["grid"]
    assert MODELING_PAPER_THEME["emphasis"] == "#A6534C"
