# Artifact Manifest

每次运行必须登记所有关键产物。manifest 是质量门、打包和用户排查的共同依据。

## 文件位置

```text
runtime/{task_id}/artifact_manifest.json
output/manifest.json
```

`runtime` 版本记录全过程，`output` 版本只记录最终交付物。

## schema

```json
{
  "task_id": "...",
  "run_mode": "formal | demo | blocked",
  "setup_status": "user_confirmed | temporary_default | skipped | incomplete",
  "manifest_schema": "2.0",
  "verification_policy": "verified=true requires object or required-artifact audit",
  "artifacts": [
    {
      "path": "output/paper/paper.pdf",
      "type": "paper_pdf",
      "source": "runtime/.../paper.md",
      "stage": "packaging",
      "formal": true,
      "exists": true,
      "verified": true,
      "verification_status": "verified",
      "size": 123456,
      "file_count": 0,
      "sha256": "...",
      "created_at": "...",
      "notes": ""
    }
  ]
}
```

## 必登产物

| 类型 | 路径 |
|---|---|
| `problem_markdown` | `runtime/{task_id}/problem.md` |
| `intake_json` | `runtime/{task_id}/intake.json` |
| `run_state` | `runtime/{task_id}/run_state.json` |
| `modeling_plan` | `runtime/{task_id}/modeling_plan.md` |
| `source_code` | `output/source code/` |
| `paper_md` | `output/paper/paper.md` |
| `paper_docx` | `output/paper/paper.docx` |
| `paper_txt` | `output/paper/paper.txt` |
| `paper_pdf` | `output/paper/paper.pdf` |
| `figures` | `output/附件文件夹/figures/` |
| `results` | `output/附件文件夹/results/` |
| `quality_report` | `output/附件文件夹/质量检查报告.md` |
| `diagnostics` | `output/附件文件夹/失败诊断.md` |
| `export_report` | `output/附件文件夹/export_report.json` |
| `export_audit` | `output/附件文件夹/export_audit.json` |
| `project_zip` | `项目总文件夹/output.zip`，内容为总文件夹内全部内容（排除 output.zip 自身） |

## 质量门要求

质量审查不得只依赖文件系统扫描。manifest 也不得只由文件扫描结果生成。它必须基于
必登产物清单逐项登记，确认每个必登产物：

- 存在；
- 类型正确；
- `verification_status` 明确；
- `verified=true` 有对应审查证据；
- `formal` 与 `run_mode` 一致；
- demo 产物没有被标成 formal。

`verified=true` 不能表示“文件存在”。未经过 `audit_quality.py`、
`audit_export.py` 或打包阶段必登清单验证的产物，必须写
`verification_status=exists_only` 或 `not_checked`。缺失项不能从 manifest 中消失；
必须登记为 `exists=false`、`verified=false`，并写入 `diagnostics.md`。

## 对象级字段

`paper_docx` 的 `notes` 或配套 `export_report.json` 必须记录：

- `reference_doc_used` / `reference_doc_missing_reason`
- `docx_formula_objects_count`
- `docx_latex_fallback_count`
- `embedded_image_count`
- `docx_table_count`

`paper_pdf` 的 `notes` 或配套 `export_report.json` 必须记录：

- PDF 生成引擎；
- 是否使用 text-only fallback；
- `pdf_readability`；
- `paper_pdf_high_fidelity`。

`project_zip` 必须由临时 zip 验证通过后发布。为避免自引用 hash，manifest 不要求记录
`output.zip` 自身 hash，但必须说明 zip 排除规则，并确保压缩包中包含
`output/manifest.json`。
