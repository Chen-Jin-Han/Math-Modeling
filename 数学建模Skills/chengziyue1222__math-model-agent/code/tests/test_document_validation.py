import fitz
import yaml

from algorithms.document_validation import (
    inspect_pdf_layout, render_three_line_table, select_figure_grammar,
    validate_cross_artifact_values, validate_paper_structure,
)


def test_pdf_layout_extracts_page_and_font_evidence(tmp_path):
    pdf = fitz.open()
    page = pdf.new_page(width=595.28, height=841.89)
    page.insert_text((72, 72), "Body text for inspection", fontsize=12)
    path = tmp_path / "a4.pdf"
    pdf.save(path)
    pdf.close()
    report = inspect_pdf_layout(path)
    assert report["status"] == "pass"
    assert report["pages"][0]["margins"]["left_pt"] > 8
    assert report["fonts"]


def test_structure_requires_sections_and_respects_dependency_trigger():
    source = "\n".join(["摘要 Keywords", "问题重述", "问题分析", "模型假设", "符号说明", "模型检验", "模型评价", "参考文献", "附录"])
    assert not validate_paper_structure(source, dependency_analysis={"shared_kernel_required": False})
    failures = validate_paper_structure(source, dependency_analysis={"shared_kernel_required": True})
    assert any(item.rule_id == "STRUCT-UNIFIED-001" for item in failures)


def test_figure_grammar_selects_only_matching_signal():
    with open(
        "docs/reverse_engineering/skill_rule_pack_v1/04_figure_grammar.yaml",
        encoding="utf-8",
    ) as stream:
        grammar = yaml.safe_load(stream)["grammar"]
    selected = select_figure_grammar(["运动/演化/仿真过程"], grammar)
    assert selected and selected[0]["recommended_figure"].startswith("共享坐标")
    assert select_figure_grammar(["unrelated"], grammar) == []


def test_three_line_table_is_generated_from_structured_rows():
    tex = render_three_line_table(["x"], [["1.20"]], "Caption", "tab:x")
    assert "\\toprule" in tex and "\\caption{Caption}" in tex
    assert "|" not in tex


def test_cross_artifact_values_allow_declared_rounding():
    good = validate_cross_artifact_values({"q": 1.23456}, [{"quantity_id": "q", "value": 1.235, "decimals": 3, "artifact": "paper"}])
    assert good == []
    bad = validate_cross_artifact_values({"q": 1.23456}, [{"quantity_id": "q", "value": 1.23, "decimals": 3, "artifact": "paper"}])
    assert bad[0].rule_id == "REJECT-001"
