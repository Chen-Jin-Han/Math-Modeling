#!/usr/bin/env python3
"""跨部件合并检查 — 把所有部件 + main.tex 在内存中合并后统一检查（Phase 5 组装后使用）。

纯结构/形式检查（正则匹配、内存合并、不写任何临时文件），不做内容生成与内容判断。

检查项:
  [K1] 跨文件 \\ref/\\cref/\\eqref 解析率 100%（label 定义在其他文件也算解析成功）
       ——修复 preflight_check.py 对单部件跑时跨部件 \\ref 误报的问题
  [K2] label 重复：同名 label 在全集内定义 ≥2 次（跨文件/同文件）
  [K3] label 前缀约定：part_qN.tex → qN: 开头；part_common.tex → cmn: 开头；main.tex 无要求
  [K4] main.tex 的 \\input{...} 目标是否都在参数文件列表内
  [K5] 孤立 label：全集定义但无引用（单文件口径由 preflight_check.py L3 负责）

用法:  python combinecheck.py <main.tex> [part_q1.tex ...]
退出码: 0 = 无问题；1 = 有问题；2 = 用法错误
"""
import os
import re
import sys
from collections import Counter

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 终端 GBK 会导致中文乱码

LABEL = re.compile(r"\\label\{([^}]+)\}")
REF = re.compile(r"\\\w*ref\{([^}]+)\}")  # \ref/\cref/\eqref/\pageref 等
INPUT = re.compile(r"\\input\{([^}]+)\}")
PART_QN = re.compile(r"part_q(\d+)\.tex$", re.I)
PART_COMMON = re.compile(r"part_common\.tex$", re.I)


def read_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.readlines()
    except (OSError, UnicodeDecodeError) as e:
        print(f"{path}: 无法读取（{e}）")
        return None


def expected_prefix(filename):
    m = PART_QN.search(filename)
    if m:
        return f"q{m.group(1)}:"
    if PART_COMMON.search(filename):
        return "cmn:"
    return None


def main(argv):
    if not argv:
        print(__doc__)
        return 2

    issues = 0
    all_labels = []
    all_refs = set()
    input_targets = []
    file_prefixes = {}  # 文件名 → 期望前缀（None = 无要求）

    for p in argv:
        lines = read_file(p)
        if lines is None:
            return 1
        base = os.path.basename(p)
        file_prefixes[p] = expected_prefix(base)
        for n, raw in enumerate(lines, 1):
            line = raw.rstrip("\n")
            if line.lstrip().startswith("%"):
                continue
            all_labels += [(p, n, lab) for lab in LABEL.findall(line)]
            all_refs.update(REF.findall(line))
            if base == os.path.basename(argv[0]):  # 主文件的 \input
                input_targets += [(p, n, t) for t in INPUT.findall(line)]

    # K1：悬空引用（全集口径）
    label_set = {lab for _, _, lab in all_labels}
    for r in sorted(all_refs - label_set):
        print(f"[K1] 跨部件悬空引用（全集无此 label）：\\ref{{{r}}}")
        issues += 1

    # K2：label 重复
    dup = [lab for lab, cnt in Counter(lab for _, _, lab in all_labels).items() if cnt > 1]
    for lab in sorted(dup):
        where = ", ".join(f"{p}:{n}" for p, n, l in all_labels if l == lab)
        print(f"[K2] label 重复定义：\\label{{{lab}}}（出现在 {where}）")
        issues += 1

    # K3：前缀约定
    for p, n, lab in all_labels:
        prefix = file_prefixes[p]
        if prefix and not lab.startswith(prefix):
            print(f"{p}:{n}: [K3] label 前缀违反约定：\\label{{{lab}}}（{os.path.basename(p)} 应以 {prefix} 开头）")
            issues += 1

    # K4：main.tex 的 \input 目标在参数列表内
    known = {os.path.basename(p) for p in argv}
    for p, n, t in input_targets:
        target = os.path.basename(t.replace("\\", "/"))
        if target not in known:
            print(f"{p}:{n}: [K4] \\input 目标不在检查文件列表内：\\input{{{t}}}（请把该文件加入命令行参数）")
            issues += 1

    # K5：孤立 label（全集口径）
    for lab in sorted(label_set - all_refs):
        where = ", ".join(f"{p}:{n}" for p, n, l in all_labels if l == lab)
        print(f"[K5] 孤立 label（全集无引用）：\\label{{{lab}}}（定义于 {where}）")
        issues += 1

    if issues:
        print(f"\n共 {issues} 个问题。引用率必须 100%、label 不得重复、前缀必须合规。")
        return 1
    print("合并检查通过：跨文件引用解析率 100%、无重复 label、前缀合规、\\input 目标齐全、无孤立 label。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
