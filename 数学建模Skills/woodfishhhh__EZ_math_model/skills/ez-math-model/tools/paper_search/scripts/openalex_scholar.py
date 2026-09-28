"""OpenAlex Scholar 单源检索 — paper-search 子 skill 入口

用法：
    python openalex_scholar.py "<query>" [--top-k 5] [--out <file>] [--mailto <email>]

返回：
    JSON 数组（schema 见同目录 SKILL.md）。
    成功输出到 stdout（或 --out 指定文件）；状态信息走 stderr。

依赖：仅标准库（urllib + json）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any


OPENALEX_ENDPOINT = "https://api.openalex.org/works"


def _rebuild_abstract(inv_index: dict[str, list[int]] | None) -> str:
    if not inv_index:
        return ""
    n = max((max(p) for p in inv_index.values() if p), default=-1) + 1
    if n <= 0:
        return ""
    words = [""] * n
    for word, positions in inv_index.items():
        for p in positions:
            if 0 <= p < n:
                words[p] = word
    return " ".join(w for w in words if w)


def _truncate(text: str, limit: int = 500) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _normalize(work: dict[str, Any]) -> dict[str, Any]:
    authors = []
    for a in work.get("authorships", []) or []:
        name = (a.get("author") or {}).get("display_name")
        if name:
            authors.append(name)
        if len(authors) >= 8:
            break
    venue = (work.get("host_venue") or work.get("primary_location", {}).get("source") or {}).get(
        "display_name"
    )
    doi_full = work.get("doi") or ""
    doi = doi_full.replace("https://doi.org/", "") if doi_full else None
    return {
        "title": work.get("title"),
        "authors": authors,
        "year": work.get("publication_year"),
        "doi": doi,
        "venue": venue,
        "abstract": _truncate(_rebuild_abstract(work.get("abstract_inverted_index"))),
        "cited_by_count": work.get("cited_by_count", 0),
        "url": doi_full or work.get("id"),
        "source": "openalex",
    }


def search(query: str, top_k: int = 5, mailto: str | None = None, timeout: int = 25) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    params = {
        "search": query.strip()[:200],
        "per-page": str(min(max(1, top_k), 25)),
    }
    if mailto:
        params["mailto"] = mailto
    url = f"{OPENALEX_ENDPOINT}?{urllib.parse.urlencode(params)}"
    headers = {
        "User-Agent": f"ez-math-model/0.1 (mailto:{mailto or 'none@example.com'})",
        "Accept": "application/json",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        sys.stderr.write(f"openalex: request failed: {exc}\n")
        return []
    return [_normalize(w) for w in data.get("results", [])]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="OpenAlex single-source scholar search.")
    ap.add_argument("query", help="search keywords")
    ap.add_argument("--top-k", type=int, default=5, help="max results (default 5, max 25)")
    ap.add_argument("--out", help="write JSON to file instead of stdout")
    ap.add_argument(
        "--mailto",
        default=os.environ.get("EZMM_OPENALEX_EMAIL"),
        help="contact email for higher rate limit (default $EZMM_OPENALEX_EMAIL)",
    )
    args = ap.parse_args(argv)

    results = search(args.query, top_k=args.top_k, mailto=args.mailto)
    payload = json.dumps(results, ensure_ascii=False, indent=2)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
        sys.stderr.write(f"openalex: wrote {len(results)} records to {args.out}\n")
    else:
        sys.stdout.write(payload + "\n")
    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
