---
name: paper-search
description: |
  论文检索子 skill。通过 OpenAlex API（默认）、arXiv、Semantic Scholar、CrossRef
  四个免费源聚合搜索学术文献，返回结构化论文元信息（含 DOI / 摘要 / 引用数）。
  默认零配置；可选 EZMM_OPENALEX_EMAIL / EZMM_S2_API_KEY 提升配额。
allowed-tools: Bash, Read
read_when:
  - 论文写作时需要参考文献
  - 模型选择论证段需要理论支撑
  - 寻找经典教材或近期综述
---

# paper-search — 多源学术论文检索

## 何时使用

- writer 在 pipeline 04 写理论性章节（"为什么用 AHP" 等）
- modeler 在 pipeline 02 选择非教科书算法时找文献
- 任何需要"标题 → DOI → 摘要"的场景

## 入口脚本

`scripts/openalex_scholar.py` — OpenAlex 单源（首选，零配置）
`scripts/aggregated_search.py` — 多源聚合（OpenAlex + arXiv + S2 + CrossRef）

## 命令行用法

```powershell
# 单源（推荐先试）
python scripts/openalex_scholar.py "AHP TOPSIS comprehensive evaluation" --top-k 5

# 多源聚合（更全但慢）
python scripts/aggregated_search.py "grey prediction GM(1,1)" --top-k 8

# 输出到文件（用于 writer 后续读取）
python scripts/aggregated_search.py "Sobol sensitivity analysis" --top-k 5 \
  --out workdir/{task_id}/refs/sensitivity.json
```

## 输出格式（JSON 数组）

```json
[
  {
    "title": "...",
    "authors": ["...", "..."],
    "year": 2022,
    "doi": "10.1109/...",
    "venue": "Journal / Conf",
    "abstract": "...（≤ 500 字符）",
    "cited_by_count": 132,
    "url": "https://doi.org/...",
    "source": "openalex | arxiv | s2 | crossref"
  }
]
```

writer 取后插入 footnote 候选；每条文献全文唯一引用一次。

## 配置

| Env Var | 必需 | 用途 |
|---|---|---|
| `EZMM_OPENALEX_EMAIL` | 否 | 提供邮箱可提升 OpenAlex 配额 |
| `EZMM_S2_API_KEY` | 否 | Semantic Scholar 配额翻倍 |

不填仍可使用所有源的免费配额。

## 限速与重试

- 单源失败重试 1 次（指数退避 1s, 4s）
- 第 2 次失败 → 标记该源不可用，跳过
- 至少 1 个源成功就返回结果，不强求全部

## 失败诊断

| 情况 | 处理 |
|---|---|
| 全部源不可达（断网） | stdout 输出 `[]`，stderr 给出诊断 |
| 单源限流 | 跳过；其他源继续 |
| 关键词太长 | 自动截至 200 字符 |
