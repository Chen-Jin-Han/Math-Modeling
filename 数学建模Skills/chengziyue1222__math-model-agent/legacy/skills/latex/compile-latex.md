# /compile-latex

## 用途

检测 LaTeX 项目的实际编译链，完成可复现编译并报告错误、警告和输出文件。

## 用法

```bash
/compile-latex path/to/main.tex
```

## 编译流程

1. 确认主文件、引擎需求、字体、图片和引用后端。
2. 识别 `thebibliography`、BibTeX、Biber 或无参考文献场景。
3. 优先在独立输出目录编译，避免覆盖用户已有产物。
4. 根据交叉引用状态运行必要次数，不固定为三遍。
5. 检查未定义引用、缺失字体、溢出、错误退出码和 PDF 是否生成。
6. 视觉检查关键页面后再交付。

## 典型策略

- 项目国赛模板：XeLaTeX 两遍，使用 `thebibliography`，无需 BibTeX。
- BibTeX：LaTeX → BibTeX → LaTeX → LaTeX。
- Biber：LaTeX → Biber → LaTeX → LaTeX。

不在未确认时安装 TeX 包、删除辅助文件或覆盖现有 PDF。
