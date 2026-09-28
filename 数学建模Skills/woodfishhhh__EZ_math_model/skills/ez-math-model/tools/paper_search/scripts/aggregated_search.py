"""多源聚合学术搜索 — paper-search 子 skill 入口

源：OpenAlex（必）+ arXiv（必）+ Semantic Scholar（如可）+ CrossRef（兜底）。
按 (DOI 或 lower-case title) 去重；尽量在 top_k 内多元化。

用法：
    python aggregated_search.py "<query>" [--top-k 8] [--out <file>]

依赖：仅标准库。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from openalex_scholar import search as search_openalex


def _truncate(text: str, limit: int = 500) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _user_agent() -> str:
    mail = os.environ.get("EZMM_OPENALEX_EMAIL", "none@example.com")
    return f"ez-math-model/0.1 (mailto:{mail})"


def search_arxiv(query: str, top_k: int = 5, timeout: int = 25) -> list[dict[str, Any]]:
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": f"all:{query[:200]}", "start": 0, "max_results": min(max(1, top_k), 25)}
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            tree = ET.fromstring(resp.read())
    except Exception as exc:
        sys.stderr.write(f"arxiv: request failed: {exc}\n")
        return []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out: list[dict[str, Any]] = []
    for e in tree.findall("a:entry", ns):
        published = e.findtext("a:published", default="", namespaces=ns) or ""
        try:
            year = int(published[:4]) if published else None
        except ValueError:
            year = None
        out.append(
            {
                "title": (e.findtext("a:title", default="", namespaces=ns) or "").strip(),
                "authors": [
                    (a.findtext("a:name", default="", namespaces=ns) or "").strip()
                    for a in e.findall("a:author", ns)
                ][:8],
                "year": year,
                "doi": None,
                "venue": "arXiv",
                "abstract": _truncate((e.findtext("a:summary", default="", namespaces=ns) or "").strip()),
                "cited_by_count": None,
                "url": e.findtext("a:id", default="", namespaces=ns),
                "source": "arxiv",
            }
        )
    return out


def search_semantic_scholar(query: str, top_k: int = 5, timeout: int = 25) -> list[dict[str, Any]]:
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={urllib.parse.quote(query[:200])}&limit={min(max(1, top_k), 25)}"
        "&fields=title,authors,year,abstract,citationCount,externalIds,venue"
    )
    headers = {"User-Agent": _user_agent()}
    if (key := os.environ.get("EZMM_S2_API_KEY")):
        headers["x-api-key"] = key
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        sys.stderr.write(f"s2: request failed: {exc}\n")
        return []
    out: list[dict[str, Any]] = []
    for p in data.get("data") or []:
        ext = p.get("externalIds") or {}
        out.append(
            {
                "title": p.get("title"),
                "authors": [(a.get("name") or "") for a in p.get("authors") or []][:8],
                "year": p.get("year"),
                "doi": ext.get("DOI"),
                "venue": p.get("venue"),
                "abstract": _truncate(p.get("abstract") or ""),
                "cited_by_count": p.get("citationCount", 0),
                "url": (ext.get("DOI") and f"https://doi.org/{ext['DOI']}") or p.get("url"),
                "source": "s2",
            }
        )
    return out


def search_crossref(query: str, top_k: int = 5, timeout: int = 25) -> list[dict[str, Any]]:
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(
        {"query": query[:200], "rows": min(max(1, top_k), 25)}
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        sys.stderr.write(f"crossref: request failed: {exc}\n")
        return []
    out: list[dict[str, Any]] = []
    for it in (data.get("message") or {}).get("items") or []:
        title = (it.get("title") or [""])[0] if it.get("title") else ""
        authors = []
        for a in it.get("author") or []:
            name = " ".join(filter(None, [a.get("given"), a.get("family")]))
            if name:
                authors.append(name)
            if len(authors) >= 8:
                break
        year = None
        for k in ("published-print", "published-online", "issued"):
            try:
                year = it.get(k, {}).get("date-parts", [[None]])[0][0]
                if year:
                    break
            except Exception:
                continue
        out.append(
            {
                "title": title,
                "authors": authors,
                "year": year,
                "doi": it.get("DOI"),
                "venue": (it.get("container-title") or [""])[0] if it.get("container-title") else None,
                "abstract": "",
                "cited_by_count": it.get("is-referenced-by-count", 0),
                "url": it.get("URL") or (it.get("DOI") and f"https://doi.org/{it['DOI']}"),
                "source": "crossref",
            }
        )
    return out


def aggregate(query: str, top_k: int = 8) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    sources = (
        ("openalex", lambda q, k: search_openalex(q, top_k=k, mailto=os.environ.get("EZMM_OPENALEX_EMAIL"))),
        ("arxiv", search_arxiv),
        ("s2", search_semantic_scholar),
        ("crossref", search_crossref),
    )
    per_source = max(2, top_k // 2)
    for name, fn in sources:
        try:
            for paper in fn(query, per_source):
                key = (paper.get("doi") or "").lower()
                if not key:
                    key = (paper.get("title") or "").strip().lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                out.append(paper)
                if len(out) >= top_k:
                    return out
        except Exception as exc:
            sys.stderr.write(f"aggregate: {name} failed: {exc}\n")
            continue
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Multi-source scholar search.")
    ap.add_argument("query")
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--out")
    args = ap.parse_args(argv)

    results = aggregate(args.query, top_k=args.top_k)
    payload = json.dumps(results, ensure_ascii=False, indent=2)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
        sys.stderr.write(f"aggregate: wrote {len(results)} records to {args.out}\n")
    else:
        sys.stdout.write(payload + "\n")
    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
