"""Apply the strict CUMCM companion-document layout to a Pandoc DOCX."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


BODY_FONT = "SimSun"
HEADING_FONT = "SimHei"


def set_run_font(run, name: str, size: float, *, bold: bool | None = None) -> None:
    run.font.name = name
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(0, 0, 0)
    if bold is not None:
        run.bold = bold
    fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    for key in ("ascii", "hAnsi", "eastAsia", "cs"):
        fonts.set(qn(f"w:{key}"), name)


def set_page_field(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend((begin, instruction, separate, text, end))
    set_run_font(run, BODY_FONT, 10.5)


def remove_footer_references(sect_pr) -> None:
    for item in list(sect_pr.findall(qn("w:footerReference"))):
        sect_pr.remove(item)
    for item in list(sect_pr.findall(qn("w:headerReference"))):
        sect_pr.remove(item)
    page_number = sect_pr.find(qn("w:pgNumType"))
    if page_number is not None:
        sect_pr.remove(page_number)


def append_section_break(paragraph, source_sect_pr) -> None:
    sect_pr = deepcopy(source_sect_pr)
    remove_footer_references(sect_pr)
    section_type = sect_pr.find(qn("w:type"))
    if section_type is None:
        section_type = OxmlElement("w:type")
        sect_pr.insert(0, section_type)
    section_type.set(qn("w:val"), "nextPage")
    paragraph._p.get_or_add_pPr().append(sect_pr)


def set_table_borders(table) -> None:
    properties = table._tbl.tblPr
    existing = properties.find(qn("w:tblBorders"))
    if existing is not None:
        properties.remove(existing)
    borders = OxmlElement("w:tblBorders")
    for edge, value, size in (
        ("top", "single", "10"),
        ("bottom", "single", "10"),
        ("left", "nil", "0"),
        ("right", "nil", "0"),
        ("insideH", "nil", "0"),
        ("insideV", "nil", "0"),
    ):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), value)
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "000000")
        borders.append(element)
    properties.append(borders)
    for cell in table.rows[0].cells:
        tc_pr = cell._tc.get_or_add_tcPr()
        cell_borders = OxmlElement("w:tcBorders")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "8")
        bottom.set(qn("w:color"), "000000")
        cell_borders.append(bottom)
        tc_pr.append(cell_borders)


def set_cell_margins(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    margins = tc_pr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    for edge, value in (("top", 70), ("bottom", 70), ("start", 90), ("end", 90)):
        item = margins.find(qn(f"w:{edge}"))
        if item is None:
            item = OxmlElement(f"w:{edge}")
            margins.append(item)
        item.set(qn("w:w"), str(value))
        item.set(qn("w:type"), "dxa")


def insert_cover(document: Document, *, title_text: str, subtitle_text: str, date_text: str) -> None:
    title = document.add_paragraph()
    title.paragraph_format.space_before = Pt(210)
    title.paragraph_format.space_after = Pt(54)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run_font(title.add_run(title_text), HEADING_FONT, 22, bold=True)

    subtitle = document.add_paragraph()
    subtitle.paragraph_format.space_after = Pt(36)
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run_font(subtitle.add_run(subtitle_text), BODY_FONT, 14)

    date = document.add_paragraph()
    date.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run_font(date.add_run(date_text), BODY_FONT, 12)

    section_end = document.add_paragraph()
    section_end.add_run().add_break(WD_BREAK.PAGE)

    elements = [title._p, subtitle._p, date._p, section_end._p]
    body = document._body._body
    for index, element in enumerate(elements):
        body.remove(element)
        body.insert(index, element)


def main(input_path: Path, output_path: Path, *, title_text: str, subtitle_text: str, date_text: str) -> None:
    document = Document(input_path)
    body_section = document.sections[-1]
    body_section.page_width = Cm(21.0)
    body_section.page_height = Cm(29.7)
    body_section.left_margin = Cm(3.17)
    body_section.right_margin = Cm(3.17)
    body_section.top_margin = Cm(2.54)
    body_section.bottom_margin = Cm(2.54)
    body_section.header_distance = Cm(1.5)
    body_section.footer_distance = Cm(1.5)
    body_section.different_first_page_header_footer = True

    footer = body_section.footer
    footer.is_linked_to_previous = False
    footer_paragraph = footer.paragraphs[0]
    footer_paragraph.clear()
    set_page_field(footer_paragraph)
    body_sect_pr = document._element.body.sectPr
    page_number = body_sect_pr.find(qn("w:pgNumType"))
    if page_number is None:
        page_number = OxmlElement("w:pgNumType")
        body_sect_pr.append(page_number)
    page_number.set(qn("w:start"), "1")

    normal = document.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(12)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.first_line_indent = Pt(24)

    for style_name, size, centered in (
        ("Heading 1", 16, True),
        ("Heading 2", 14, False),
        ("Heading 3", 12, False),
    ):
        style = document.styles[style_name]
        style.font.name = HEADING_FONT
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), HEADING_FONT)
        style.paragraph_format.first_line_indent = Pt(0)
        style.paragraph_format.line_spacing = 1.5
        style.paragraph_format.space_before = Pt(12)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER if centered else WD_ALIGN_PARAGRAPH.LEFT
        )

    body_start = None
    for paragraph in document.paragraphs:
        if paragraph.text.strip() == "问题重述":
            body_start = paragraph
            break
    if body_start is None:
        raise ValueError("cannot locate 问题重述 for body page-number restart")
    body_start.paragraph_format.page_break_before = True

    for paragraph in document.paragraphs:
        name = paragraph.style.name if paragraph.style is not None else ""
        if name.startswith("Heading"):
            paragraph.paragraph_format.first_line_indent = Pt(0)
        elif paragraph.text.strip():
            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            paragraph.paragraph_format.line_spacing = 1.5
            paragraph.paragraph_format.first_line_indent = Pt(24)
        for run in paragraph.runs:
            if name.startswith("Heading"):
                set_run_font(run, HEADING_FONT, 16 if name == "Heading 1" else 14 if name == "Heading 2" else 12, bold=True)
            else:
                set_run_font(run, BODY_FONT, 12)

    for table in document.tables:
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True
        set_table_borders(table)
        for row_index, row in enumerate(table.rows):
            for cell in row.cells:
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                set_cell_margins(cell)
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.first_line_indent = Pt(0)
                    paragraph.paragraph_format.line_spacing = 1.0
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in paragraph.runs:
                        set_run_font(run, HEADING_FONT if row_index == 0 else BODY_FONT, 10.5, bold=row_index == 0)

    for shape in document.inline_shapes:
        if shape.width > Cm(14.7):
            ratio = Cm(14.7) / shape.width
            shape.width = Cm(14.7)
            shape.height = int(shape.height * ratio)

    insert_cover(document, title_text=title_text, subtitle_text=subtitle_text, date_text=date_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--title", default="C题：生产企业原材料的订购与运输方案")
    parser.add_argument("--subtitle", default="数学建模竞赛")
    parser.add_argument("--date", default="2026年7月")
    args = parser.parse_args()
    main(args.input, args.output, title_text=args.title, subtitle_text=args.subtitle, date_text=args.date)
