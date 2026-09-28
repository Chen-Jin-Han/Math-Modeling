---
name: user-corpus-explorer
description: Use near the end of EZ_math_model intake when external/user-corpus contains user-provided papers, notes, PDFs, datasets, or examples that should become a local AGENTS.md reference index.
---

# user-corpus-explorer — 用户资料库索引

## 何时使用

- `external/user-corpus/` 存在用户自带参考材料。
- `pipeline 00` 对该域决策不是 `skip`。
- `pipeline 01` intake 结束前需要生成用户资料索引。

## 设计原则

- 由 subagent 执行，不污染主对话上下文。
- 每次覆盖生成 `external/user-corpus/AGENTS.md`。
- 失败不打断主 pipeline。
- 不上传全文到外部服务。

## 扫描范围

递归扫描 `external/user-corpus/`，跳过：

- `.gitkeep`
- `README.md`
- `AGENTS.md`
- `.corpus_index.json`
- `.git/`、`.cache/`、以 `.` 开头的目录
- 大于 200MB 的文件只记录路径和大小

## 读取策略

| 扩展名 | 策略 |
|---|---|
| `.md` `.txt` | 读全文，超长读首尾 |
| `.pdf` | MinerU → pdf → pdfplumber，长文仅读首 15 页和末 5 页 |
| `.docx` | docx 提取文本 |
| `.html` | Jina Reader 或 BeautifulSoup |
| 图片 | 视觉描述 |
| 其他二进制 | 只记录元信息 |

## 输出

生成：

```text
external/user-corpus/AGENTS.md
external/user-corpus/.corpus_index.json
```

`AGENTS.md` 包含 inventory、per-file index、cross-cutting topics、recommendations、limitations。

## 下游衔接

- modeler 必读 recommendations，并在 `modeling_plan.md` 标注参考来源。
- writer 可优先把 corpus 中可验证 DOI 的论文列入参考候选。
- coder 不直接读 corpus，除非 modeler 在计划中转述其方法。

## 失败诊断

| 情况 | 处理 |
|---|---|
| corpus 目录为空 | 写空索引，pipeline 继续 |
| 单文件读取失败 | 在 limitations 记录 |
| MinerU 不可用 | 降级 pdf → pdfplumber |
| 总耗时超过 5 分钟 | 写已完成索引，剩余标 unread |
