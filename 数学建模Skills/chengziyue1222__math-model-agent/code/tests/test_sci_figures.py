"""Scientific figure module tests."""
import json

import numpy as np
import pytest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from algorithms.sci_figures import (
    FigureContract,
    FigureDesignBrief,
    MODELING_PALETTE,
    MODELING_PALETTES,
    TaylorDiagram,
    ChordDiagram,
    add_panel_label,
    audit_publication_figure,
    export_publication_figure,
    get_modeling_palette,
    mm_to_inches,
    publication_rc_params,
    publication_size,
    resolve_cjk_font,
    save_figure,
)


@pytest.fixture(autouse=True)
def cleanup():
    yield
    plt.close('all')


class TestTaylorDiagram:
    """Taylor 图测试"""

    def test_basic_creation(self):
        fig = plt.figure()
        ref_std = 1.0
        td = TaylorDiagram(ref_std, fig=fig)
        assert td is not None

    def test_add_point(self):
        fig = plt.figure()
        td = TaylorDiagram(1.0, fig=fig)
        td.add_sample(0.8, 0.9, label='Test')
        assert True

    def test_multiple_points(self):
        fig = plt.figure()
        td = TaylorDiagram(1.0, fig=fig)
        td.add_sample(0.8, 0.9, label='A')
        td.add_sample(1.2, 0.7, label='B')
        td.add_sample(0.95, 0.95, label='C')
        assert True


class TestChordDiagram:
    """弦图测试"""

    def test_basic_creation(self):
        matrix = np.array([
            [0, 2, 1],
            [2, 0, 3],
            [1, 3, 0],
        ])
        labels = ['A', 'B', 'C']
        cd = ChordDiagram(matrix, labels)
        assert cd is not None

    def test_render(self):
        matrix = np.array([[0, 1], [1, 0]])
        labels = ['X', 'Y']
        cd = ChordDiagram(matrix, labels)
        fig = cd.render()
        assert fig is not None


class TestSaveFigure:
    """保存图表测试"""

    def test_save_png(self, tmp_path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        path = str(tmp_path / "test.png")
        save_figure(fig, path)
        import os
        assert os.path.exists(path)

    def test_save_pdf(self, tmp_path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        path = str(tmp_path / "test.pdf")
        save_figure(fig, path)
        import os
        assert os.path.exists(path)

    def test_save_svg(self, tmp_path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        path = str(tmp_path / "test.svg")
        save_figure(fig, path)
        import os
        assert os.path.exists(path)


class TestPublicationWorkflow:
    def test_publication_defaults(self):
        assert mm_to_inches(25.4) == pytest.approx(1.0)
        assert publication_size("single", 50) == pytest.approx((89 / 25.4, 50 / 25.4))
        assert publication_rc_params()["savefig.dpi"] == 450
        assert len(MODELING_PALETTE["categorical"]) == 6
        assert "nature-accessible" in MODELING_PALETTES
        assert publication_rc_params()["axes.unicode_minus"] is False
        assert publication_rc_params(language="zh")["font.sans-serif"][0]

    def test_cjk_font_resolution_is_safe(self):
        font_name = resolve_cjk_font()
        assert font_name is None or isinstance(font_name, str)
        with pytest.raises(ValueError, match="language"):
            publication_rc_params(language="fr")

    def test_named_palette_returns_semantic_roles(self):
        palette = get_modeling_palette("nature-accessible")

        assert len(palette["categorical"]) == 6
        assert palette["accent"] == "#D55E00"
        palette["accent"] = "#000000"
        assert MODELING_PALETTES["nature-accessible"]["accent"] == "#D55E00"
        with pytest.raises(ValueError, match="unknown palette"):
            get_modeling_palette("missing-theme")

    def test_design_brief_validates_asymmetric_layout(self):
        with pytest.raises(ValueError, match="hero_panel"):
            FigureDesignBrief(
                "Primary result is stable",
                layout_recipe="hero-plus-proof",
            )

        brief = FigureDesignBrief(
            "Primary result is stable",
            layout_recipe="hero-plus-proof",
            hero_panel="(a) primary result",
            support_sequence=("(b) residuals",),
        )
        assert brief.hero_panel == "(a) primary result"

    def test_contract_rejects_missing_claim_and_unknown_column(self):
        with pytest.raises(ValueError, match="claim"):
            FigureContract("", ("series",))
        with pytest.raises(ValueError, match="column"):
            FigureContract("Trend increases", ("series",), column="triple")
        with pytest.raises(ValueError, match="theme_name"):
            FigureContract("Trend increases", ("series",), theme_name="typo")
        with pytest.raises(ValueError, match="design_brief"):
            FigureContract("Trend increases", ("series",), design_brief="invalid")

    def test_audit_detects_wrong_width_and_small_text(self):
        fig, axis = plt.subplots(figsize=(2, 2))
        axis.plot([0, 1], [0, 1])
        axis.set_xlabel("x")
        axis.set_ylabel("y")
        axis.set_title("tiny", fontsize=4)
        contract = FigureContract("Increasing trend", ("line slope",), column="double")

        report = audit_publication_figure(fig, contract)

        assert not report.passed
        assert any("figure width" in error for error in report.errors)
        assert any("below 5 pt" in error for error in report.errors)

    def test_panel_label_helper_uses_consistent_typography(self):
        fig, axis = plt.subplots()
        label = add_panel_label(axis, "a")

        assert label.get_fontsize() == 8
        assert label.get_fontweight() == "bold"
        assert label.get_fontstyle() == "normal"

    def test_export_writes_vector_raster_and_audit_metadata(self, tmp_path):
        with matplotlib.rc_context(publication_rc_params()):
            fig, axis = plt.subplots(
                figsize=publication_size("single", 60), constrained_layout=True
            )
            axis.plot(
                [0, 1, 2],
                [1, 2, 4],
                color=MODELING_PALETTE["categorical"][0],
            )
            axis.set_xlabel("Time (day)")
            axis.set_ylabel("Response (unit)")
            brief = FigureDesignBrief(
                "Response increases over time",
                layout_recipe="evidence-grid",
            )
            contract = FigureContract(
                "Response increases over time",
                ("three observations", "positive slope"),
                source_paths=("results.csv",),
                column="single",
                figure_role="model-result",
                model_name="deterministic trend example v1",
                scenario="baseline",
                parameter_source="three fixed observations",
                randomness="deterministic; no random seed",
                n_definition="n = 3 time points",
                statistic="raw observations",
                uncertainty="not applicable to deterministic example",
                panel_evidence=("(a) three observations",),
                data_transformations=("none",),
                theme_name="nature-accessible",
                design_brief=brief,
            )
            paths = export_publication_figure(fig, tmp_path / "trend", contract)

        assert set(paths) == {"pdf", "svg", "png", "metadata"}
        assert all(
            (tmp_path / f"trend.{extension}").is_file()
            for extension in ("pdf", "svg", "png")
        )
        metadata = json.loads(
            (tmp_path / "trend.figure.json").read_text(encoding="utf-8")
        )
        assert metadata["audit"]["passed"] is True
        assert metadata["contract"]["claim"] == "Response increases over time"
        assert metadata["contract"]["model_name"] == "deterministic trend example v1"
        assert metadata["contract"]["theme_name"] == "nature-accessible"
        assert metadata["contract"]["design_brief"]["layout_recipe"] == "evidence-grid"
        assert metadata["audit"]["metrics"]["figure_role"] == "model-result"
        assert metadata["export"]["dpi"] == 450
        assert metadata["schema_version"] == 2

    def test_strict_export_refuses_failed_audit(self, tmp_path):
        fig, axis = plt.subplots(figsize=(2, 2))
        axis.plot([0, 1], [0, 1])
        contract = FigureContract("Increasing trend", ("line slope",), column="double")

        with pytest.raises(ValueError, match="audit failed"):
            export_publication_figure(fig, tmp_path / "invalid", contract)
        assert not (tmp_path / "invalid.png").exists()

    def test_export_rejects_low_resolution(self, tmp_path):
        fig, axis = plt.subplots(figsize=publication_size("double", 60))
        axis.plot([0, 1], [0, 1])
        contract = FigureContract("Increasing trend", ("line slope",))

        with pytest.raises(ValueError, match="at least 450"):
            export_publication_figure(fig, tmp_path / "low-resolution", contract, dpi=300)
