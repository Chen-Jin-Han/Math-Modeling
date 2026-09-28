from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_canonical_paper_style_is_explicit():
    style = yaml.safe_load((ROOT / "config" / "paper_style.yaml").read_text(encoding="utf-8"))
    assert style["page"]["running_header"] == "none"
    assert style["page"]["margins_mm"]["left"] == 25
    assert style["typography"]["line_spacing"] == 1.65
    assert style["typography"]["appendix_code_pt"] == 8.5
    assert style["tables"]["style"] == "three-line"


def test_both_cumcm_templates_follow_the_canonical_layout_without_contents():
    templates = (
        ROOT / "template" / "cume-template.tex",
        ROOT / "skills" / "write-model-paper" / "assets" / "cume-template.tex",
    )
    for template in templates:
        text = template.read_text(encoding="utf-8")
        assert "left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.8cm" in text
        assert r"\linespread{1.65}" in text
        assert r"\pagestyle{plain}" in text
        assert r"\tableofcontents" not in text
        assert r"\renewcommand{\contentsname}{目录}" not in text
        assert text.count(r"\setcounter{page}{1}") == 1
        assert text.index(r"\setcounter{page}{1}") < text.index("摘\\quad 要")
        assert text.index("摘\\quad 要") < text.index(r"\section{问题重述}")
        assert r"\newcommand{\PaperTitle}" in text

    style = yaml.safe_load((ROOT / "config" / "paper_style.yaml").read_text(encoding="utf-8"))
    assert style["front_matter"]["contents"] is False
    assert style["page"]["numbering_continuous"] is True
    assert style["page"]["max_body_pages"] == 30
    assert style["page"]["abstract_page_excluded_from_body_limit"] is True
    assert style["delivery"]["paper_max_bytes"] == 20 * 1024 * 1024
