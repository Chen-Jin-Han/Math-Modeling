#!/usr/bin/env python3
"""ez-math-model — 题目 → 上游优秀论文路径匹配器

用法:
    python match_thesis.py [--root <path>] [--problem-text <text> | < problem.md]

输入:
    stdin 或 --problem-text 给出题目纯文本（也可以是 intake.json 的拼接）。
    --root 指定 ez-math-model 仓库根目录（含 external/zhanwen-mathmodel 的层级）。
    若 --root 省略，默认取本文件所在的 .../scripts/runtime/ 上溯两级。

输出:
    一份 JSON 写到 stdout，schema 见 references/workdir-protocol.md：
      {
        "match_level": "exact|year|series|fallback|internal",
        "thesis_dir": "<绝对路径或 INTERNAL>",
        "template_dir": "<绝对路径或 INTERNAL>",
        "signals": {"contest": "...", "year": ..., "problem": "..."},
        "checked_at": "<ISO8601>"
      }

设计:
    纯标准库（re, os, sys, json, datetime, argparse），无第三方依赖。
    五级回落：exact -> year -> series -> fallback -> internal。
    内部不抛异常，所有失败都翻译为 internal 兜底。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

CONTEST_PATTERNS = [
    ("cumcm",   [r"CUMCM", r"全国大学生数学建模", r"国赛", r"高教社杯", r"高教社"]),
    ("mcm",     [r"MCM\b", r"\bICM\b", r"美赛", r"COMAP", r"Mathematical\s+Contest\s+in\s+Modeling"]),
    ("gradmcm", [r"研究生数学建模", r"华为杯", r"中国研究生数学建模"]),
]

YEAR_RE = re.compile(r"(20\d{2})")
PROBLEM_LETTER_ZH_RE = re.compile(r"([A-F])\s*题")
PROBLEM_LETTER_EN_RE = re.compile(r"\bProblem\s*([A-F])\b", flags=re.IGNORECASE)

ZHANWEN_REL = os.path.join("external", "zhanwen-mathmodel")
COMPLETE_MARKER = ".complete"

# 上游目录命名常量（核对自 zhanwen/MathModel 实际结构）
DIR_CUMCM_THESIS = "国赛论文"
DIR_CUMCM_PROBLEM = "国赛试题"
DIR_MCM_THESIS = "美赛论文"
DIR_LATEX_TEMPLATES = "数学建模Latex模版"


def detect_contest(text: str) -> str:
    for contest, pats in CONTEST_PATTERNS:
        for pat in pats:
            if re.search(pat, text, flags=re.IGNORECASE):
                return contest
    return "unknown"


def detect_year(text: str) -> int | None:
    years = [int(m.group(1)) for m in YEAR_RE.finditer(text)]
    if not years:
        return None
    plausible = [y for y in years if 1990 <= y <= 2099]
    if not plausible:
        return None
    return max(plausible)


def detect_problem_letter(text: str) -> str | None:
    m = PROBLEM_LETTER_ZH_RE.search(text)
    if m:
        return m.group(1).upper()
    m = PROBLEM_LETTER_EN_RE.search(text)
    return m.group(1).upper() if m else None


def list_year_dirs(parent: str, pattern: re.Pattern) -> list[tuple[int, str]]:
    """列出 parent 下匹配 pattern 的子目录，返回 [(year, dirname)] 按年份降序。"""
    if not os.path.isdir(parent):
        return []
    out: list[tuple[int, str]] = []
    for name in os.listdir(parent):
        full = os.path.join(parent, name)
        if not os.path.isdir(full):
            continue
        m = pattern.match(name)
        if not m:
            continue
        try:
            y = int(m.group(1))
        except (ValueError, IndexError):
            continue
        out.append((y, name))
    out.sort(key=lambda kv: kv[0], reverse=True)
    return out


CUMCM_YEAR_RE = re.compile(r"^(20\d{2})年优秀论文$")
MCM_YEAR_RE = re.compile(r"^(20\d{2})美赛特等奖原版论文集$")
TEMPLATE_YEAR_RE = re.compile(r"^(20\d{2})年数模悉知")


def cumcm_year_dir(zhanwen_root: str, year: int) -> str | None:
    p = os.path.join(zhanwen_root, DIR_CUMCM_THESIS, f"{year}年优秀论文")
    return p if os.path.isdir(p) else None


def cumcm_problem_dir(zhanwen_root: str, year: int, letter: str) -> str | None:
    parent = cumcm_year_dir(zhanwen_root, year)
    if not parent:
        return None
    if letter:
        upper = letter.upper()
        for name in os.listdir(parent):
            full = os.path.join(parent, name)
            if not os.path.isdir(full):
                continue
            if name.upper().startswith(upper):
                return full
    return parent


def mcm_year_dir(zhanwen_root: str, year: int) -> str | None:
    p = os.path.join(zhanwen_root, DIR_MCM_THESIS, f"{year}美赛特等奖原版论文集")
    return p if os.path.isdir(p) else None


def latest_year_dir(zhanwen_root: str, contest: str) -> str | None:
    if contest == "cumcm":
        ys = list_year_dirs(os.path.join(zhanwen_root, DIR_CUMCM_THESIS), CUMCM_YEAR_RE)
        if ys:
            return os.path.join(zhanwen_root, DIR_CUMCM_THESIS, ys[0][1])
    elif contest == "mcm":
        ys = list_year_dirs(os.path.join(zhanwen_root, DIR_MCM_THESIS), MCM_YEAR_RE)
        if ys:
            return os.path.join(zhanwen_root, DIR_MCM_THESIS, ys[0][1])
    return None


def latest_template_dir(zhanwen_root: str) -> str | None:
    """返回最新一年的 '{年}年数模悉知&论文模版' 目录，找不到返回 Latex 模板目录。"""
    ys = list_year_dirs(zhanwen_root, TEMPLATE_YEAR_RE)
    if ys:
        for y, name in ys:
            full = os.path.join(zhanwen_root, name)
            if os.path.isdir(full):
                return full
    latex = os.path.join(zhanwen_root, DIR_LATEX_TEMPLATES)
    return latex if os.path.isdir(latex) else None


def resolve_root(cli_root: str | None) -> str:
    if cli_root:
        return os.path.abspath(cli_root)
    here = os.path.abspath(os.path.dirname(__file__))
    # scripts/runtime -> scripts -> repo root
    return os.path.abspath(os.path.join(here, "..", ".."))


def now_iso() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")


def make_internal(signals: dict) -> dict:
    return {
        "match_level": "internal",
        "thesis_dir": "INTERNAL",
        "template_dir": "INTERNAL",
        "signals": signals,
        "checked_at": now_iso(),
    }


def match(text: str, repo_root: str) -> dict:
    contest = detect_contest(text)
    year = detect_year(text)
    letter = detect_problem_letter(text)
    signals = {"contest": contest, "year": year, "problem": letter}

    zhanwen_root = os.path.join(repo_root, ZHANWEN_REL)
    if not os.path.isfile(os.path.join(zhanwen_root, COMPLETE_MARKER)):
        return make_internal(signals)

    template_dir = latest_template_dir(zhanwen_root) or "INTERNAL"

    if contest == "cumcm" and year:
        if letter:
            tdir = cumcm_problem_dir(zhanwen_root, year, letter)
            if tdir:
                return {
                    "match_level": "exact",
                    "thesis_dir": tdir,
                    "template_dir": template_dir,
                    "signals": signals,
                    "checked_at": now_iso(),
                }
        ydir = cumcm_year_dir(zhanwen_root, year)
        if ydir:
            return {
                "match_level": "year",
                "thesis_dir": ydir,
                "template_dir": template_dir,
                "signals": signals,
                "checked_at": now_iso(),
            }

    if contest == "mcm" and year:
        ydir = mcm_year_dir(zhanwen_root, year)
        if ydir:
            return {
                "match_level": "exact" if letter else "year",
                "thesis_dir": ydir,
                "template_dir": template_dir,
                "signals": signals,
                "checked_at": now_iso(),
            }

    if contest in ("cumcm", "mcm"):
        latest = latest_year_dir(zhanwen_root, contest)
        if latest:
            return {
                "match_level": "series",
                "thesis_dir": latest,
                "template_dir": template_dir,
                "signals": signals,
                "checked_at": now_iso(),
            }

    if contest == "gradmcm":
        gdir = os.path.join(zhanwen_root, "2018年研究生数学建模")
        if os.path.isdir(gdir):
            return {
                "match_level": "series",
                "thesis_dir": gdir,
                "template_dir": template_dir,
                "signals": signals,
                "checked_at": now_iso(),
            }

    if template_dir != "INTERNAL":
        return {
            "match_level": "fallback",
            "thesis_dir": template_dir,
            "template_dir": template_dir,
            "signals": signals,
            "checked_at": now_iso(),
        }

    return make_internal(signals)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Match math modeling problem to zhanwen/MathModel thesis paths.")
    ap.add_argument("--root", help="ez-math-model repo root", default=None)
    ap.add_argument("--problem-text", help="Problem text inline (else read stdin)", default=None)
    args = ap.parse_args(argv)

    if args.problem_text is not None:
        text = args.problem_text
    else:
        text = sys.stdin.read()

    if not text or not text.strip():
        sys.stderr.write("match_thesis: empty problem text\n")
        out = make_internal({"contest": "unknown", "year": None, "problem": None})
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 1

    repo_root = resolve_root(args.root)
    result = match(text, repo_root)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
