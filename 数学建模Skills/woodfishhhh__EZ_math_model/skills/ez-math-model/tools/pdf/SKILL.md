---
name: pdf
description: Use when EZ_math_model needs to read or convert PDF problem statements, extract text or tables from PDF attachments, summarize reference papers, or fall back when MinerU is unavailable.
---

# pdf — PDF 读取与转换兜底

## 何时使用

- 用户上传 `.pdf` 题目。
- 需要读取优秀论文 PDF 的摘要、目录或局部章节。
- MinerU 不可用或输出失败。
- PDF 扫描件需要 OCR。

## 优先链路

1. `mineru` skill。
2. 宿主 `pdf` skill。
3. `pdfplumber` 文本和表格提取。
4. 图像 OCR 兜底。

## 论文 PDF 导出兜底

`scripts/runtime/export_paper.ps1` 的 simple text-only PDF 只用于占位交付。该兜底
使用基础字体，非 ASCII 字符会被替换为 `?`，因此中文 formal 论文不能把它视为
高保真 PDF。出现该兜底时必须：

- 在 `export_report.json` 中写 `pdf_fallback` 与 `paper_pdf_high_fidelity=false`；
- 在 `export_audit.json` 中标记 `pdf_readability=placeholder` 或 warning；
- 最终质量等级最高为 `provisional_pass`。

## 题目 PDF 转 Markdown

```python
import pdfplumber

with pdfplumber.open("problem.pdf") as pdf:
    text = "\n\n".join(page.extract_text() or "" for page in pdf.pages)

with open("problem.md", "w", encoding="utf-8") as f:
    f.write(text)
```

复杂表格、公式和多栏排版优先交给 `mineru`。

## 参考论文读取策略

- 优先读标题、摘要、目录、参考文献。
- 只在需要借鉴模型表述时读对应章节。
- 每篇累计读取页数不超过 5 页。
- 不全文复制优秀论文内容。

## 失败诊断

| 情况 | 处理 |
|---|---|
| 全部 PDF 工具不可用 | 保留原 PDF，让多模态能力直接读 |
| 提取乱码 | 写诊断，建议用户提供文本版 |
| 公式提取失败 | 保留原始字符串，由 writer 补 LaTeX |
