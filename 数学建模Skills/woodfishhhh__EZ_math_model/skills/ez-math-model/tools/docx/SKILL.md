---
name: docx
description: Use when EZ_math_model needs to convert paper.md to paper.docx, read a DOCX problem statement, preserve equations and tables, or package a modeling report as a Word document.
---

# docx — Word 文档读写与打包

## 何时使用

- 把 `paper.md` 转换为 `paper.docx`。
- 读取用户上传的 `.docx` 题目。
- 需要参考模板、图片嵌入、公式对象或表格保真。

## 优先链路

1. 宿主 `docx` skill。
2. `pandoc` 直调。
3. `python-docx` 兜底。

## Markdown 转 DOCX

```powershell
pandoc paper.md `
  --from gfm+tex_math_dollars+pipe_tables `
  --to docx `
  --output paper.docx `
  --resource-path .
```

有参考模板时追加：

```powershell
--reference-doc <template.docx>
```

## DOCX 转文本

优先使用宿主 `docx` skill。没有宿主能力时，用 `python-docx` 提取段落和表格，再写成 Markdown 友好文本。

## 产出要求

- 输出文件默认与 `paper.md` 同目录：`paper.docx`。
- 图片必须嵌入，不保留失效本地链接。
- `$...$` 与 `$$...$$` 尽量转换为 Word 可编辑公式；失败时保留原始 LaTeX 文本并写诊断。

## 对象级验收

DOCX 不是“文件存在就合格”。转换后必须把 `.docx` 当 zip 解包检查：

- `word/document.xml` 必须存在且可读取。
- 公式验收：统计 `m:oMath` / `m:oMathPara`。若 `paper.md` 有公式但 DOCX 中
  公式对象数为 0，formal 模式失败。
- 图片验收：统计 `word/media/*`。Markdown 图片引用数不得超过嵌入图片数；
  缺图必须列出文件名。
- 表格验收：统计 `w:tbl`。Markdown 表格应转换为 Word 表格对象；未转换时至少
  降级为 warning，formal 视严重程度阻塞。
- LaTeX fallback：统计 `word/document.xml` 中残留 `$...$`。formal 模式下残留
  公式文本不得直接标为通过。

EZMM 内置 `scripts/runtime/audit_export.py` 会执行上述检查，生成
`export_audit.json` 与 `export_audit.md`。

## 失败诊断

| 情况 | 处理 |
|---|---|
| 宿主 skill、pandoc、python-docx 都不可用 | 保留 `paper.md`，在 `diagnostics.md` 写缺失工具 |
| 公式渲染异常 | formal 模式阻塞正式发布；demo 模式保留 LaTeX 文本并降级 |
| 图片路径错误 | 检查 Markdown 相对路径和 `--resource-path` |
