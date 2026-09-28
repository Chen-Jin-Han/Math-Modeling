---
name: mineru
description: |
  PDF / 图片 / 网页高质量解析为 Markdown。三种部署形态全部免费：本地 CLI（开源）、
  云 API（注册免费 token + 配额，超额才付费）、网页 flash（零注册，单文件 ≤10MB / ≤20页）。
  在中文学术 PDF / 表格 / 公式上识别质量显著高于 pdfplumber。
allowed-tools: Bash, Read
read_when:
  - 题目 PDF 含表格 / 公式 / 复杂排版
  - 阅读 zhanwen 优秀论文 PDF
  - 把附件中带数据的报告 PDF 转为 markdown
---

# mineru — PDF 高质量解析

## 何时使用

- 题目 PDF 含中文 + 表格 + 公式（pdfplumber 输出乱序时）
- 阅读 `external/zhanwen-mathmodel/` 下的优秀论文
- 转换 docx / pptx 为 markdown

## 入口

本子 skill **不**自带 Python 实现；调用宿主已安装的 `mineru-open-api` CLI
或 `mineru` Python 包。详细 CLI 文档见 [mineru 官方 skill](https://github.com/opendatalab/MinerU)。

## 模式选择决策树

```
文件 ≤ 10MB 且 ≤ 20页 且 不需表格识别
  → flash-extract（零配置、最快）

文件 > 10MB 或 > 20页 或 需要表格 / 公式 / OCR
  → extract（要 token，注册免费领）
  → 备用：本地 CLI mineru（开源，自动下载模型）
```

## 命令模板

```powershell
# Flash 模式（推荐起手）
mineru-open-api flash-extract problem.pdf -o workdir/.../out --language ch

# 限页（>20 页时）
mineru-open-api flash-extract problem.pdf -o workdir/.../out --language ch --pages 1-20

# Extract 精确模式（需 token；写入 EZMM_MINERU_TOKEN）
mineru-open-api auth                         # 一次性配置
mineru-open-api extract problem.pdf -o workdir/.../out --language ch --table --formula

# 本地 CLI（无 token，开源版）
pip install -U mineru
mineru -p problem.pdf -o workdir/.../out
```

## 入参约定

| 参数 | 默认 | 说明 |
|---|---|---|
| `--language` | `ch` | 中文文档；英文用 `en`；混合 `ch_server` |
| `--pages` | 全部 | flash 模式下题目 > 20 页时按 `1-20` 分批 |
| `-o` | stdout | 写入指定目录（推荐）；不写参数则 markdown 走 stdout |

## 配置

| Env Var | 必需 | 用途 |
|---|---|---|
| `EZMM_MINERU_TOKEN` | extract 模式必需 | 注册免费领，flash 不需要 |

## 失败诊断

| 错误 | 原因 | 处理 |
|---|---|---|
| `file page count exceeds API limit` | flash 限 20 页 | 加 `--pages 1-20`；或换 extract（要 token） |
| `TLS handshake timeout` | 网络抖动 | 重试 1 次；仍失败降级 pdfplumber |
| `no API token found` | extract 缺 token | 调 `mineru-open-api auth` 或 fallback flash |
| 输出 Markdown 含大量 `<!-- image -->` | 论文图片占位 | 正常；只对文字部分有效 |
