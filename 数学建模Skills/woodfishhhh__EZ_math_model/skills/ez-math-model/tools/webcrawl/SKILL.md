---
name: webcrawl
description: |
  网页抓取与开放检索。Jina Reader（免费零配置）+ Firecrawl + Tavily + Exa +
  SerpAPI。题目背景涉及行业 / 政策 / 经济时启用；纯数学 / 物理机理题不启用。
read_when:
  - 题目背景涉及政策 / 行业 / 地理 / 经济
  - 需要从网页拉取行业基准 / 标准
  - 评价类题目需要业界对照
---

# webcrawl — 网页抓取与开放检索

## 何时使用

- 题目纯数学 / 物理机理 → **不要启用**。
- 题目涉及行业 / 政策 / 地理 / 经济 → 启用。
- 评价类题目需要业界基准 / 标准 → 启用。

## 入口决策树

```
有具体 URL 要读 → Jina Reader（免费，零配置）
  失败 → Firecrawl scrape（要 EZMM_FIRECRAWL_KEY）
  失败 → 让 LLM 用 WebFetch（最后兜底）

要先搜后读 → Tavily（要 EZMM_TAVILY_KEY）
            / Exa（要 EZMM_EXA_KEY）
            / SerpAPI（要 EZMM_SERPAPI_KEY）
全部不可用 → 让用户给具体 URL，再走单页抓取
```

## 命令模板

### Jina Reader（免费）

```powershell
# 任意 URL → markdown，零配置
$url = 'https://example.com/article'
Invoke-RestMethod -Uri "https://r.jina.ai/$url" -OutFile workdir/.../web/$(($url | Get-FileHash -Algorithm MD5).Hash.Substring(0,8)).md
```

### Firecrawl

```python
import requests, os
r = requests.post(
    "https://api.firecrawl.dev/v1/scrape",
    headers={"Authorization": f"Bearer {os.environ['EZMM_FIRECRAWL_KEY']}"},
    json={"url": "https://...", "formats": ["markdown"]},
    timeout=60,
).json()
markdown = r["data"]["markdown"]
```

### Tavily / Exa / SerpAPI

参考 `tools/webcrawl/SKILL.md` 的代码段。

## 落盘规范

抓回的页面落到：

```
workdir/{task_id}/attachments/external/web/<sha8>.md
```

文件头三行写：

```
<!-- source: tavily | firecrawl | jina | exa | serp -->
<!-- fetched_at: 2026-05-20T10:00:00+08:00 -->
<!-- url: https://... -->
```

## 礼貌爬取

- 单源间隔 ≥ 1s
- 尊重 `robots.txt`（除非用户授权）
- 不绕过登录 / 反爬
- 大批量爬取走 Firecrawl，不裸 requests

## 失败诊断

| 情况 | 处理 |
|---|---|
| 全部 key 缺失 | 仅 Jina 可用；写诊断说明可用工具集 |
| 单页 4xx / 5xx | 退避重试 1 次；仍失败记诊断 |
| 抓回登录墙 / 验证码 | 不绕过；写诊断 |
| 超时 > 60s | 中断，写诊断 |
