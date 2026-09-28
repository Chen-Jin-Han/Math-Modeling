"""论文检查模块测试"""
from algorithms.paper_check import PaperChecker, check_paper, CheckReport, Severity


class TestPaperChecker:
    """PaperChecker 类测试"""

    def test_init(self):
        checker = PaperChecker()
        assert checker is not None

    def test_check_nonexistent_file(self):
        checker = PaperChecker()
        result = checker.check_file("nonexistent.tex")
        assert isinstance(result, CheckReport)

    def test_check_empty_tex(self, tmp_path):
        f = tmp_path / "empty.tex"
        f.write_text("")
        checker = PaperChecker()
        result = checker.check_file(str(f))
        assert isinstance(result, CheckReport)

    def test_check_basic_tex(self, tmp_path):
        f = tmp_path / "basic.tex"
        f.write_text(r"""
\documentclass{article}
\begin{document}
\section{Introduction}
Hello world.
\end{document}
""")
        checker = PaperChecker()
        result = checker.check_file(str(f))
        assert isinstance(result, CheckReport)

    def test_severity_levels(self):
        """严重程度枚举"""
        assert hasattr(Severity, 'ERROR')
        assert hasattr(Severity, 'WARNING')
        assert hasattr(Severity, 'INFO')

    def test_latex_comments_do_not_create_missing_image_failures(self, tmp_path):
        paper = tmp_path / "main.tex"
        paper.write_text(
            r"""\documentclass{article}
\begin{document}
% \includegraphics{missing.png}
\section{Introduction}
Text.
\end{document}
""",
            encoding="utf-8",
        )

        report = check_paper(str(paper), figures_dir="")

        assert not any("missing.png" in result.message for result in report.results)

    def test_inline_bibliography_counts_as_references(self, tmp_path):
        paper = tmp_path / "main.tex"
        paper.write_text(
            r"""\documentclass{article}
\begin{document}
\section{Introduction}
As shown by \cite{sample}, this is supported.
\begin{thebibliography}{9}
\bibitem{sample} A sufficiently descriptive inline reference entry.
\end{thebibliography}
\end{document}
""",
            encoding="utf-8",
        )

        report = check_paper(str(paper), figures_dir="")

        assert not any("未找到参考文献文件" in result.message for result in report.results)


class TestCheckPaper:
    """check_paper 便捷函数测试"""

    def test_returns_report(self, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text(r"\documentclass{article}\begin{document}Test\end{document}")
        result = check_paper(str(f))
        assert isinstance(result, CheckReport)

    def test_report_has_issues(self, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text(r"\documentclass{article}\begin{document}Test\end{document}")
        result = check_paper(str(f))
        assert hasattr(result, 'issues')
        assert isinstance(result.issues, list)
