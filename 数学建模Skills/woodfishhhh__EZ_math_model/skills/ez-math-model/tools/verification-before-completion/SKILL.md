---
name: verification-before-completion
description: Use before EZ_math_model declares quality_audit, packaging, or final delivery complete, especially when pass/fail claims must be backed by files, commands, counts, or concrete evidence.
---

# verification-before-completion — 完成前证据核验

## 何时使用

- `pipeline 05 quality_audit`。
- `pipeline 06 packaging` 前后。
- 任何准备声明“完成”“通过”“已生成”的时候。

## 核心要求

对每条 `quality_report.json/md` 与 `export_audit.json/md` 的通过项给证据，而不是
口头判断。

证据类型：

- 文件存在与大小。
- 命令 exit code 与关键输出。
- grep / diff / hash 匹配。
- 图表引用与实际文件一致。
- 结果数值与报告表述一致。
- DOCX 中 `word/media/*`、`m:oMath`、`w:tbl` 的对象计数。
- PDF 是否使用 fallback、是否高保真。
- `output/manifest.json`、`output.zip` 与 staging 发布证据一致。

## 示例

```powershell
Get-ChildItem workdir/.../figures/*.png
Select-String -Path workdir/.../paper.md -Pattern '!\\[[^\\]]*\\]\\(([^)]+)\\)'
python scripts/runtime/audit_quality.py --workdir runtime/...
python scripts/runtime/audit_export.py --workdir runtime/... --paper-output output/paper
```

如果证据收集失败，该项不能标为通过。
