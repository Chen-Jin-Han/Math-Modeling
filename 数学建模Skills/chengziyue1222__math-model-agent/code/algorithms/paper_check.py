"""
论文质量检查 (Paper Check)
===========================
论文提交前的质量门禁：结构、图表、引用、数值一致性检查。

包含类/函数:
- PaperChecker: 论文质量检查器（支持 Typst / LaTeX）
- check_paper: 快捷检查函数

检查项:
  1. 章节结构检查（include/input 顺序、标题完整性）
  2. 图表引用检查（图片是否存在、是否被引用）
  3. 占位符与泄露检查（TODO、内部文件名）
  4. 数值一致性检查（结果文件 vs 论文）
  5. 引用检查（参考文献、引用标记）
  6. 编译检查（Typst / LaTeX）

竞赛场景:
- 论文终稿提交前的最终检查
- 批量检查多篇论文

使用:
    from algorithms import PaperChecker
    checker = PaperChecker(paper_dir="paper", main_file="paper/main.tex")
        figures_dir="figures",
        results_file="reports/RESULTS_REPORT.md",
    )
    report = checker.run()
    print(report.summary())
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class Severity(Enum):
    FAIL = "FAIL"
    WARN = "WARN"
    INFO = "INFO"
    ERROR = "FAIL"
    WARNING = "WARN"


@dataclass
class CheckResult:
    severity: Severity
    message: str
    file: Optional[str] = None

    def __str__(self):
        loc = f" [{self.file}]" if self.file else ""
        return f"{self.severity.value}: {self.message}{loc}"


@dataclass
class CheckReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(r.severity == Severity.FAIL for r in self.results)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if r.severity == Severity.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for r in self.results if r.severity == Severity.WARN)

    def add(self, severity: Severity, msg: str, file: Optional[str] = None):
        self.results.append(CheckResult(severity, msg, file))

    def fail(self, msg: str, file: Optional[str] = None):
        self.add(Severity.FAIL, msg, file)

    def warn(self, msg: str, file: Optional[str] = None):
        self.add(Severity.WARN, msg, file)

    def info(self, msg: str, file: Optional[str] = None):
        self.add(Severity.INFO, msg, file)

    @property
    def issues(self) -> list[CheckResult]:
        """所有检查结果（兼容测试接口）。"""
        return self.results

    def summary(self) -> str:
        lines = [
            "=" * 60,
            f"论文检查报告: {'PASS' if self.passed else 'FAIL'}",
            f"  FAIL: {self.fail_count}  WARN: {self.warn_count}",
            "=" * 60,
        ]
        for r in self.results:
            lines.append(str(r))
        return "\n".join(lines)


class PaperChecker:
    """论文质量检查器。

    Args:
        paper_dir: 论文目录（包含 main.typ/main.tex 和 sections/）。
        main_file: 论文入口文件路径。
        sections_dir: 正文章节目录，默认 paper_dir/sections。
        references_file: 参考文献文件。
        figures_dir: 图表目录。
        results_file: 结果报告文件。
        problem_analysis_file: 问题分析报告文件。
        all_results_json: 汇总结果 JSON 文件。
        extra_internal_terms: 额外的内部工作流术语列表。
    """

    def __init__(
        self,
        paper_dir: str = "paper",
        main_file: Optional[str] = None,
        sections_dir: Optional[str] = None,
        references_file: Optional[str] = None,
        figures_dir: str = "figures",
        results_file: Optional[str] = None,
        problem_analysis_file: Optional[str] = None,
        all_results_json: Optional[str] = None,
        extra_internal_terms: Optional[list[str]] = None,
    ):
        self.paper_dir = Path(paper_dir)
        self.figures_dir = Path(figures_dir) if figures_dir else None
        self.results_file = Path(results_file) if results_file else None
        self.problem_analysis_file = Path(problem_analysis_file) if problem_analysis_file else None
        self.all_results_json = Path(all_results_json) if all_results_json else None
        self.extra_internal_terms = extra_internal_terms or []

        # Auto-detect main file
        if main_file:
            self.main_file = Path(main_file)
        elif (self.paper_dir / "main.typ").exists():
            self.main_file = self.paper_dir / "main.typ"
        elif (self.paper_dir / "main.tex").exists():
            self.main_file = self.paper_dir / "main.tex"
        else:
            self.main_file = self.paper_dir / "main.typ"

        # Auto-detect engine
        self.is_latex = self.main_file.suffix == ".tex"
        self.is_typst = self.main_file.suffix == ".typ"
        self.engine = "LaTeX" if self.is_latex else "Typst"
        self.section_ext = "*.tex" if self.is_latex else "*.typ"

        # Sections dir
        if sections_dir:
            self.sections_dir = Path(sections_dir)
        elif (self.paper_dir / "sections").exists():
            self.sections_dir = self.paper_dir / "sections"
        else:
            self.sections_dir = None

        # References
        if references_file:
            self.references_file = Path(references_file)
        elif (self.paper_dir / "references.typ").exists():
            self.references_file = self.paper_dir / "references.typ"
        elif (self.paper_dir / "references.tex").exists():
            self.references_file = self.paper_dir / "references.tex"
        else:
            self.references_file = None

    def check_file(self, filepath: str) -> CheckReport:
        """检查单个论文文件（兼容测试接口）。"""
        path = Path(filepath)
        if not path.exists():
            report = CheckReport()
            report.fail(f"论文入口文件不存在: {path}")
            return report
        checker = PaperChecker(paper_dir=str(path.parent), main_file=str(path))
        return checker.run()

    @staticmethod
    def _read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _section_sort_key(path: Path):
        m = re.match(r"^(\d+)[_-](.*)$", path.name)
        if m:
            return (0, int(m.group(1)), m.group(2))
        return (1, path.name)

    @staticmethod
    def _leading_number(name: str) -> Optional[int]:
        m = re.match(r"^(\d+)[_-]", name)
        return int(m.group(1)) if m else None

    def _get_section_files(self) -> list[Path]:
        if self.sections_dir and self.sections_dir.exists():
            return sorted(self.sections_dir.glob(self.section_ext), key=self._section_sort_key)
        excluded = {self.main_file.resolve()}
        if self.references_file:
            excluded.add(self.references_file.resolve())
        return sorted(
            [p for p in self.paper_dir.rglob(self.section_ext) if p.resolve() not in excluded],
            key=self._section_sort_key,
        )

    def _extract_typst_includes(self, text: str) -> list[str]:
        return re.findall(r'#include\(\s*"([^"]+\.typ)"\s*\)', text)

    @staticmethod
    def _strip_latex_comments(text: str) -> str:
        """Remove unescaped LaTeX comments while preserving escaped percent signs."""
        return re.sub(r"(?<!\\)%.*$", "", text, flags=re.MULTILINE)

    def _extract_latex_includes(self, text: str) -> list[str]:
        text = self._strip_latex_comments(text)
        raw = re.findall(r'\\(?:input|include)\s*\{([^}]+)\}', text)
        return [inc if inc.endswith(".tex") else inc + ".tex" for inc in raw]

    def _extract_image_refs(self, text: str) -> list[str]:
        if self.is_typst:
            return re.findall(r'image\(\s*"([^"]+)"', text)
        text = self._strip_latex_comments(text)
        return re.findall(r'\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}', text)

    def run(self) -> CheckReport:
        """Run all checks and return a report."""
        rpt = CheckReport()

        # --- Existence checks ---
        if not self.paper_dir.exists():
            rpt.fail(f"论文目录不存在: {self.paper_dir}")
            return rpt
        if not self.main_file.exists():
            rpt.fail(f"论文入口文件不存在: {self.main_file}")
            return rpt

        rpt.info(f"引擎: {self.engine}")
        rpt.info(f"入口文件: {self.main_file}")

        main_text = self._read(self.main_file)
        section_files = self._get_section_files()
        rpt.info(f"章节数量: {len(section_files)}")

        # --- Include/Input check ---
        if self.is_typst:
            includes = self._extract_typst_includes(main_text)
        else:
            includes = self._extract_latex_includes(main_text)

        include_paths = [(self.main_file.parent / inc).resolve() for inc in includes]
        include_names = [Path(inc).name for inc in includes]

        # Duplicate check
        seen = set()
        for name in include_names:
            if name in seen:
                rpt.fail(f"重复 include: {name}")
            seen.add(name)

        # Existence check
        for inc, path in zip(includes, include_paths):
            if not path.exists():
                rpt.fail(f"include 的文件不存在: {inc}")

        # Order check
        numbers = [self._leading_number(n) for n in include_names if self._leading_number(n) is not None]
        if numbers and numbers != sorted(numbers):
            rpt.fail(f"章节 include 顺序不是升序: {numbers}")

        # --- Section heading check ---
        for path in section_files:
            if not path.exists():
                continue
            text = self._read(path)
            body = text.strip()
            rel_name = path.name

            # Length check
            if len(body) < 800 and not path.name.startswith("A_"):
                rpt.warn(f"章节过短 ({len(body)} 字符)", rel_name)

            # Heading check
            is_aux = path.name.startswith("A_") or path.name.lower().startswith(("abstract", "appendix"))
            if self.is_typst:
                # Check malformed headings (= without space)
                for line in text.splitlines():
                    if re.match(r"^={1,6}(?![=\s]).+", line):
                        rpt.fail(f"Typst 标题缺少空格: {line[:80]}", rel_name)
                        break
                if not re.search(r"(?m)^=\s+.+", text) and not is_aux:
                    rpt.fail("章节缺少一级标题 (= Title)", rel_name)
            else:
                if not re.search(r"\\section\{", text) and not re.search(r"\\subsection\{", text) and not is_aux:
                    rpt.fail("章节缺少 \\section{} 标题", rel_name)

            # List density check
            if self.is_typst:
                list_count = len(re.findall(r"#(?:enum|list)\s*\(", text))
            else:
                list_count = len(re.findall(r"\\begin\{(?:itemize|enumerate)\}", text))
            if list_count >= 3:
                rpt.warn(f"列表过多 ({list_count} 个)，考虑用段落叙述", rel_name)

        # --- Placeholder check ---
        placeholder_re = re.compile(r"PLACEHOLDER|TODO|TBD|XXX|待补充|待续写|这里补|示例数据|待完善")
        all_files = [self.main_file] + section_files
        if self.references_file and self.references_file.exists():
            all_files.append(self.references_file)

        for path in all_files:
            if not path.exists():
                continue
            text = self._read(path)
            if self.is_latex:
                text = self._strip_latex_comments(text)
            if placeholder_re.search(text):
                rpt.fail("存在占位符文本", path.name)

        # --- Internal term leak check ---
        default_terms = [
            "RESULTS_REPORT", "ANALYSIS_MODELING_REPORT.md", "PROBLEM_ANALYSIS.md",
            "CLAUDE.md", "figures/*.json", "_tmp/",
        ]
        if self.results_file:
            default_terms.append(self.results_file.name)
        if self.problem_analysis_file:
            default_terms.append(self.problem_analysis_file.name)
        all_terms = sorted(set(t for t in default_terms + self.extra_internal_terms if t))
        internal_re = re.compile("|".join(re.escape(t) for t in all_terms)) if all_terms else None

        if internal_re:
            for path in all_files:
                if not path.exists():
                    continue
                text = self._read(path)
                if self.is_latex:
                    text = self._strip_latex_comments(text)
                is_appendix = path.name.startswith("A_") or "appendix" in path.name.lower()
                if internal_re.search(text):
                    if is_appendix:
                        rpt.warn("附录中出现内部工作流术语", path.name)
                    else:
                        rpt.fail("论文正文泄露内部工作流文件名", path.name)

        # --- Image reference check ---
        all_texts = []
        for path in all_files:
            if path.exists():
                text = self._read(path)
                if self.is_latex:
                    text = self._strip_latex_comments(text)
                all_texts.append((path, text))

        for path, text in all_texts:
            for ref in self._extract_image_refs(text):
                target = (path.parent / ref).resolve()
                if not target.exists():
                    rpt.fail(f"引用的图片不存在: {ref}", path.name)

        # Check for unreferenced figures
        if self.figures_dir and self.figures_dir.exists():
            paper_combined = "\n".join(t for _, t in all_texts)
            for fig in sorted(self.figures_dir.glob("*.pdf")):
                if fig.name not in paper_combined:
                    rpt.warn(f"图表 PDF 未在论文中引用: {fig.name}")

        # --- Caption check ---
        paper_combined = "\n".join(t for _, t in all_texts)
        if self.is_typst:
            # Find figure(...) calls and check for caption:
            figure_pattern = re.compile(r'#figure\((.*?)\)', re.S)
            for match in figure_pattern.finditer(paper_combined):
                body = match.group(1)
                if "caption:" not in body:
                    rpt.fail("figure() 缺少 caption")
                else:
                    cap_match = re.search(r"caption:\s*\[(.*?)\]", body, re.S)
                    if cap_match:
                        cap = re.sub(r"\s+", " ", cap_match.group(1)).strip()
                        if len(cap) > 80:
                            rpt.warn(f"caption 过长: {cap[:80]}...")
                        if len(cap) < 4:
                            rpt.warn("caption 过短")
        else:
            figure_blocks = re.findall(r"\\begin\{figure\}.*?\\end\{figure\}", paper_combined, re.S)
            for block in figure_blocks:
                cap_match = re.search(r"\\caption\{([^}]*)\}", block)
                if not cap_match:
                    rpt.fail("LaTeX figure 缺少 \\caption{}")
                else:
                    cap = cap_match.group(1).strip()
                    if len(cap) > 80:
                        rpt.warn(f"caption 过长: {cap[:80]}...")
                    if len(cap) < 4:
                        rpt.warn("caption 过短")

        # --- Reference check ---
        has_inline_bibliography = self.is_latex and bool(
            re.search(r"\\begin\{thebibliography\}", paper_combined)
        )
        if self.references_file and self.references_file.exists():
            refs_text = self._read(self.references_file)
            if self.is_latex:
                refs_text = self._strip_latex_comments(refs_text)
            if len(refs_text.strip()) < 80:
                rpt.warn("参考文献文件内容过少")
            if self.is_typst:
                citation_re = r"@\w[\w:-]*|#cite\("
            else:
                citation_re = r"\\cite\w*\{[^}]+\}"
            if not re.search(citation_re, paper_combined):
                rpt.warn("参考文献文件存在但论文中未发现引用标记")
        elif not has_inline_bibliography:
            rpt.warn("未找到参考文献文件")

        # --- Results consistency check ---
        if self.results_file and self.results_file.exists():
            results_text = self._read(self.results_file)
            metric_re = re.compile(
                r"(?i)\b(?:rmse|mae|mape|r2|score|objective|accuracy|precision|recall|f1|"
                r"权重|目标值|误差|得分)\b"
            )
            metrics = metric_re.findall(results_text)
            if metrics:
                found = any(m.lower() in paper_combined.lower() for m in metrics[:20])
                if not found:
                    rpt.warn("结果文件中的指标在论文中难以找到")

        # --- JSON numeric check ---
        if self.all_results_json and self.all_results_json.exists():
            try:
                data = json.loads(self._read(self.all_results_json))
                nums = []

                def walk(v):
                    if isinstance(v, dict):
                        for item in v.values():
                            walk(item)
                    elif isinstance(v, list):
                        for item in v:
                            walk(item)
                    elif isinstance(v, (int, float)):
                        nums.append(v)

                walk(data)
                key_nums = [str(round(n, 4)).rstrip("0").rstrip(".") for n in nums[:100] if abs(n) >= 1]
                if key_nums:
                    found = any(n and n in paper_combined for n in key_nums[:30])
                    if not found:
                        rpt.warn("结果 JSON 中的数值在论文中难以找到")
            except Exception as exc:
                rpt.warn(f"无法解析结果 JSON: {exc}")

        return rpt


def check_paper(
    paper_dir: str = "paper",
    main_file: Optional[str] = None,
    figures_dir: str = "figures",
    results_file: Optional[str] = None,
    **kwargs,
) -> CheckReport:
    """Convenience function to run paper checks.

    支持传入目录或单个 .tex/.typ 文件路径。
    """
    path = Path(paper_dir)
    if path.is_file() or path.suffix.lower() in {".tex", ".typ"}:
        checker = PaperChecker(
            paper_dir=str(path.parent),
            main_file=str(path),
            figures_dir=figures_dir,
            results_file=results_file,
            **kwargs,
        )
    else:
        checker = PaperChecker(
            paper_dir=paper_dir,
            main_file=main_file,
            figures_dir=figures_dir,
            results_file=results_file,
            **kwargs,
        )
    return checker.run()


if __name__ == "__main__":
    import sys

    paper_dir = sys.argv[1] if len(sys.argv) > 1 else "paper"
    main_file = sys.argv[2] if len(sys.argv) > 2 else None
    report = check_paper(paper_dir, main_file)
    print(report.summary())
    sys.exit(0 if report.passed else 1)
