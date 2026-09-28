#!/usr/bin/env python3
"""交回核对 — 分发版 vs 交回版部件结构 diff（组装空间步骤 0，替代人工结构核对）。

纯结构/形式检查（行级比对 + 正则），不做内容生成与内容判断。
正文改动不检查、不拦（预期行为——队友本就该改正文）；只拦结构级变更。

检查项:
  [H1] 锚点注释完整性：分发中的锚点注释行（% ─── 名称 ───）逐行比对，交回缺失 → FAIL
  [H2] 文档级命令混入：交回出现 \\documentclass / \\begin{document} / \\usepackage / \\newenvironment
       （注释行除外）→ FAIL
  [H3] label 变更：交回 vs 分发 \\label 差集（删除/新增逐项列出）；前缀越界（不符 qN:/cmn:）→ FAIL
  [H4] \\input 新增：交回出现分发没有的 \\input → 报告（白名单式，交人判断）

用法:  python handback-check.py --dist <分发文件|目录> --ret <交回文件|目录>
      传目录时按同名 .tex 逐文件比对（无同名交回 → FAIL）
退出码: 0 = 无结构问题；1 = 有结构问题；2 = 用法错误
"""
import argparse
import os
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 终端 GBK 会导致中文乱码

ANCHOR = re.compile(r"^%\s*─+.*$")  # 锚点注释行（% ─── 名称 ───）
DOC_CMDS = re.compile(r"\\documentclass|\\begin\{document\}|\\usepackage|\\newenvironment")
LABEL = re.compile(r"\\label\{([^}]+)\}")
INPUT = re.compile(r"\\input\{([^}]+)\}")
PART_QN = re.compile(r"part_q(\d+)\.tex$", re.I)
PART_COMMON = re.compile(r"part_common\.tex$", re.I)


def read_lines(path):
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


def collect(lines):
    """返回 (锚点行集合, label 集合, input 集合)。"""
    anchors, labels, inputs = set(), set(), set()
    for raw in lines:
        if ANCHOR.match(raw):
            anchors.add(raw.rstrip("\n").strip())
        if raw.lstrip().startswith("%"):
            continue
        labels.update(LABEL.findall(raw))
        inputs.update(INPUT.findall(raw))
    return anchors, labels, inputs


def check_pair(dist_path, ret_path):
    issues = 0
    dist_lines = read_lines(dist_path)
    ret_lines = read_lines(ret_path)
    if dist_lines is None or ret_lines is None:
        return 1

    base = os.path.basename(dist_path)
    d_anchors, d_labels, d_inputs = collect(dist_lines)
    r_anchors, r_labels, r_inputs = collect(ret_lines)

    # H1：锚点缺失
    for anchor in sorted(d_anchors - r_anchors):
        print(f"{ret_path}: [H1] 交回缺失锚点注释行：{anchor}——部件结构被改动，需确认")
        issues += 1

    # H2：文档级命令混入
    for n, raw in enumerate(ret_lines, 1):
        line = raw.rstrip("\n")
        if line.lstrip().startswith("%"):
            continue
        if DOC_CMDS.search(line):
            print(f"{ret_path}:{n}: [H2] 文档级命令混入（只允许出现在 main.tex）：{line.strip()}")
            issues += 1

    # H3：label 变更 + 前缀越界
    prefix = expected_prefix(base)
    for lab in sorted(d_labels - r_labels):
        print(f"{ret_path}: [H3] label 被删除：\\label{{{lab}}}——需确认是否为有意结构改动")
        issues += 1
    for lab in sorted(r_labels - d_labels):
        print(f"{ret_path}: [H3] 新增 label：\\label{{{lab}}}——需确认是否为有意结构改动")
        issues += 1
    for lab in sorted(r_labels):
        if prefix and not lab.startswith(prefix):
            print(f"{ret_path}: [H3] label 前缀越界：\\label{{{lab}}}（{base} 应以 {prefix} 开头）")
            issues += 1

    # H4：\input 新增（白名单式，交人判断）
    for t in sorted(r_inputs - d_inputs):
        print(f"{ret_path}: [H4] 新增 \\input：\\input{{{t}}}（交回带了额外文件/片段，需确认）")
        issues += 1

    return issues


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dist", required=True, help="分发版文件或目录")
    ap.add_argument("--ret", required=True, help="交回版文件或目录")
    args = ap.parse_args(argv)

    if not os.path.exists(args.dist) or not os.path.exists(args.ret):
        print("用法错误：--dist / --ret 路径不存在")
        return 2

    dist_is_dir = os.path.isdir(args.dist)
    ret_is_dir = os.path.isdir(args.ret)
    if dist_is_dir != ret_is_dir:
        print("用法错误：--dist / --ret 必须同为文件或同为目录")
        return 2

    if not dist_is_dir:
        return 1 if check_pair(args.dist, args.ret) else 0

    # 目录模式：按同名 .tex 逐文件比对
    issues, checked = 0, 0
    for name in sorted(os.listdir(args.dist)):
        if not name.lower().endswith(".tex"):
            continue
        dist_file = os.path.join(args.dist, name)
        ret_file = os.path.join(args.ret, name)
        checked += 1
        if not os.path.exists(ret_file):
            print(f"{ret_file}: [H1] 交回目录中缺失该部件文件（未交回？）")
            issues += 1
            continue
        issues += check_pair(dist_file, ret_file)

    if checked == 0:
        print("用法错误：--dist 目录下没有 .tex 文件")
        return 2
    if issues:
        print(f"\n共 {issues} 个结构问题。确认后进入组装：改动属正文内容则接受，属结构则走白名单修复。")
        return 1
    print(f"交回核对通过：{checked} 个部件锚点完整、无文档级命令混入、label 无变更、无新增 \\input。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
