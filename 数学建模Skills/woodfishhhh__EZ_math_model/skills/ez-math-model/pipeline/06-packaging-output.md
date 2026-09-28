# Pipeline 06 — 打包交付

## 入口条件

- `quality_report.md` 已落盘。
- `run_state.json.run_mode != blocked`。
- 检查项 3（拆题完整）与检查项 8（章节齐全）均未失败（失败时 05 阶段已经
  打断，不会进入此阶段）。

## 阶段任务

本阶段必须是原子发布流程：`staging output → export → export audit → manifest →
temporary zip → zip verify → publish output/ + output.zip`。在临时压缩包验证通过前，
不得破坏旧 `output/`；发布后不得再修改 `output/manifest.json` 或压缩包内容。

### 1. Markdown → 四格式导出

调 `scripts/runtime/export_paper.ps1` 将 `runtime/{task_id}/paper.md` 导出到
`output/paper/`：

```text
output/paper/
├── paper.md
├── paper.docx
├── paper.txt
└── paper.pdf
```

转换要点：
- 图片统一走相对路径 `figures/xxx.png`，所以转换前要 `cd runtime/{task_id}` 或
  在转换器命令里指定 resource path。
- 数学公式：`$...$` 与 `$$...$$` 必须正确转换为 docx 公式对象（OMML），
  详见 `tools/docx/SKILL.md` 的 pandoc 调用约定。
- 模板：若 `thesis_match.json.template_dir` 指向 zhanwen 的论文模板包，必须先
  判断其中 `.docx` 是可用 reference-doc、格式说明还是样例论文。只有可解包、
  含 Word 样式且不是“格式要求/说明/通知”的文档才能作为 `--reference-doc`；
  找不到时必须在 `export_report.json.reference_doc_missing_reason` 中说明。
- 若 pandoc 的 PDF 引擎不可用，`export_paper.ps1` 必须生成一个 text-only
  `paper.pdf` 占位兜底，并在 `diagnostics.md` 中记录高保真 PDF 生成失败原因。
  中文论文使用该兜底时，PDF 可读性不满足 formal 高保真要求，最终等级最高为
  `provisional_pass`。
- 若 `paper.docx` 或 `paper.pdf` 仍缺失，质量等级不能高于 `provisional_pass`。
- `export_paper.ps1` 必须输出并落盘 `export_report.json`，至少包含
  `reference_doc_used`、`reference_doc_missing_reason`、`docx_formula_objects_count`、
  `docx_latex_fallback_count`、`embedded_image_count`、`docx_table_count`、
  `pdf_fallback`、`pdf_readability`、`paper_pdf_high_fidelity`。

### 1.5 导出对象审查

导出后必须运行：

```powershell
python scripts/runtime/audit_export.py `
  --workdir runtime/{task_id} `
  --paper-output output.__staging.../paper `
  --export-report runtime/{task_id}/export_report.json
```

审查内容包括：

- 解压 `paper.docx`，统计 `word/media/*`、`m:oMath` / `m:oMathPara`、
  `w:tbl`、残留 `$...$`；
- Markdown 图片引用数不得超过 DOCX 嵌入图片数；
- Markdown 表格数应转换为 Word 表格对象；
- 若 Markdown 有公式但 DOCX 中无 OMML 公式对象，formal 模式失败；
- PDF 使用 text-only fallback 时标记 `paper_pdf_high_fidelity=false`。

产出 `export_audit.json` 与 `export_audit.md`，并复制到
`output/附件文件夹/`。`export_audit.json.blocking=true` 时不得发布正式包。

### 2. 写诊断报告

无失败时 `diagnostics.md` 仍要落盘空报告：

```markdown
# 失败诊断

无失败项。本次运行所有阶段均通过。
```

有失败时按 `references/workdir-protocol.md` 中的"diagnostics.md"格式记录。

### 3. 同步标准 output 目录

调 `scripts/runtime/pack_deliverable.ps1 -WorkDir runtime/{task_id}`。脚本必须先构建
`output.__staging.{task_id}`，在 staging 内完成导出、对象审查、manifest 与临时 zip
验证；全部通过后再替换标准输出目录：

```
output/
├── source code/
│   └── src/
├── paper/
│   ├── paper.md
│   ├── paper.docx
│   ├── paper.txt
│   └── paper.pdf
├── 附件文件夹/
│   ├── figures/
│   ├── results/
│   ├── attachments/
│   ├── 质量检查报告.md
│   └── 失败诊断.md
└── manifest.json
```

中文文件名只用于附件说明类文件；论文四格式统一使用 `paper.*`，便于自动化读取。
`artifact_manifest.final.json` 只能在最终 manifest 写完后复制，不能复制旧 manifest。

### 4. 压缩项目交付

打包脚本必须在项目总文件夹根目录生成：

```text
output.zip
```

压缩包内容为项目总文件夹内的全部内容（`用户输入/`、`runtime/`、`output/` 等），
但排除正在生成的 `output.zip` 自身、临时 zip 和 `runtime/*/deliverable.zip`
历史兼容包，避免旧交付包嵌套进新包。脚本也可复制一份到
`runtime/{task_id}/deliverable.zip` 作为兼容别名；面向用户的主交付物是
`项目总文件夹/output.zip`。

`output/manifest.json` 不得通过扫描现有文件后全部写 `verified=true`。它必须由必登
产物清单驱动，缺失项也要登记，并写明 `exists`、`verified`、
`verification_status`、`size`、`file_count`、`sha256` 和 `notes`。`verified=true`
只能来自质量审查或对象审查证据，不能等同于文件存在。

### 5. 输出最终消息

向用户报告：

```
任务完成。交付包：output.zip
- 论文：output/paper/paper.md / paper.docx / paper.txt / paper.pdf
- 源代码：output/source code/
- 附件：output/附件文件夹/（图表 N 张，结果 M 个文件）
- 运行模式：formal/demo
- 质量门通过：X / 10
- 警告：Y 项（详见 output/附件文件夹/质量检查报告.md）
- 失败：Z 项（详见失败诊断.md）
```

## 产出文件

| 路径 | 必须 | 说明 |
|---|---|---|
| `output/paper/paper.md` | 是 | Markdown 论文 |
| `output/paper/paper.docx` | 是 | Word 论文；缺失则质量降级并记诊断 |
| `output/paper/paper.txt` | 是 | 纯文本论文 |
| `output/paper/paper.pdf` | 是 | PDF 论文；缺失则质量降级并记诊断 |
| `output/source code/` | 是 | 项目源代码 |
| `output/附件文件夹/` | 是 | 图表、结果、附件、质量报告、诊断 |
| `output/manifest.json` | 是 | 最终产物 manifest |
| `output.zip` | 是 | 最终交付包 |
| `runtime/{task_id}/export_report.json` | 是 | 导出过程与对象计数 |
| `runtime/{task_id}/export_audit.json` | 是 | DOCX/PDF 对象级审查 |

## 失败诊断

| 情况 | 处理 |
|---|---|
| pandoc / docx skill 不可用 | demo 可降级交付 markdown；formal 阻塞正式发布或最高 provisional |
| 公式转换异常 | formal 模式阻塞正式发布；demo 模式降级并写诊断 |
| PDF 导出失败 | 不打断，但最终等级不能高于 `provisional_pass` |
| text-only PDF 兜底 | 中文 formal 不算高保真 PDF，最高 `provisional_pass` |
| export audit blocking | 不发布正式包，保留 staging 与诊断 |
| 打包脚本失败 | 不打断，保留旧 `output/`，列出 staging 与 runtime 路径让用户排查 |

## 下一阶段入口

无。本阶段是 pipeline 终点。

完成后 ez-math-model 一次运行结束，下次运行新建工作目录。


