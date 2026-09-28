#!/usr/bin/env python3
"""引用机制检查 — 位置式 \\scite 与键式 \\cite 混用 + 编号越界（Phase 4/5 使用）。

纯结构/形式检查（正则匹配），不做任何内容生成与内容判断。

检查项:
  [C1] 混用检测：同一文档内 \\scite{编号} 与 \\cite{键} 并存；多文件时部件与主文件机制不一致
  [C2] \\scite 编号越界：展开 n / n,m / a-b 区间，逐项校验 1 ≤ n ≤ \\bibitem 总数
  [C3] 未引用 \\bibitem 编号清单（机械报告，供人复核）
       ——第三次模拟 \\scite 重编号错位 9 处靠此发现，混用靠人眼发现

用法:  python citecheck.py <主文件.tex> [部件.tex ...]
退出码: 0 = 无问题；1 = 有问题；2 = 用法错误
"""
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 终端 GBK 会导致中文乱码

SCITE = re.compile(r"\\scite\{([^}]+)\}")
CITE = re.compile(r"\\cite[a-zA-Z]*\{([^}]+)\}")  # \cite/\citep/\citet 键式；不会误匹配 \scite
BIBITEM = re.compile(r"\\bibitem")


def expand_scite(spec):
    """展开 \\scite 参数：'3' → [3]，'2,3' → [2,3]，'4-6' → [4,5,6]；非法返回 None。"""
    nums = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                a, b = int(a), int(b)
            except ValueError:
                return None
            nums += list(range(a, b + 1))
        else:
            try:
                nums.append(int(part))
            except ValueError:
                return None
    return nums


def read_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.readlines()
    except (OSError, UnicodeDecodeError) as e:
        print(f"{path}: 无法读取（{e}）")
        return None


def main(argv):
    if not argv:
        print(__doc__)
        return 2

    files = []
    for p in argv:
        lines = read_file(p)
        if lines is None:
            return 1
        files.append((p, lines))

    issues = 0
    bibitem_count = 0
    scite_nums = set()
    mechanisms = {}  # 文件 → {'scite': n, 'cite': n}

    # 第一遍：机制统计 + 收集编号
    for p, lines in files:
        m = {"scite": 0, "cite": 0}
        for raw in lines:
            line = raw.rstrip("\n")
            if line.lstrip().startswith("%"):
                continue
            m["scite"] += len(SCITE.findall(line))
            m["cite"] += len(CITE.findall(line))
        mechanisms[p] = m
        if m["scite"] and m["cite"]:
            print(f"{p}: [C1] 同一文档内混用 \\scite（位置式）与 \\cite（键式）——统一为一种机制")
            issues += 1

    # 主文件机制（第一个参数视为主文件）
    main_mech = None
    if files:
        m = mechanisms[files[0][0]]
        if m["scite"] and not m["cite"]:
            main_mech = "scite"
        elif m["cite"] and not m["scite"]:
            main_mech = "cite"
    for p, m in mechanisms.items():
        mech = "scite" if m["scite"] and not m["cite"] else ("cite" if m["cite"] and not m["scite"] else None)
        if mech and main_mech and mech != main_mech:
            print(f"{p}: [C1] 引用机制与主文件不一致（主文件用 {main_mech}，本文件用 {mech}）——统一为一种机制")
            issues += 1

    # 第二遍：先数完全部 \bibitem 总数，再检查 \scite 编号
    # （\bibitem 在 thebibliography 末尾而 \scite 在正文中，逐行累计会误报越界）
    for p, lines in files:
        for raw in lines:
            if not raw.lstrip().startswith("%"):
                bibitem_count += len(BIBITEM.findall(raw))

    for p, lines in files:
        for n, raw in enumerate(lines, 1):
            line = raw.rstrip("\n")
            if line.lstrip().startswith("%"):
                continue
            for spec in SCITE.findall(line):
                nums = expand_scite(spec)
                if nums is None:
                    print(f"{p}:{n}: [C2] \\scite 参数无法解析：\\scite{{{spec}}}（应为 n / n,m / a-b）")
                    issues += 1
                    continue
                for num in nums:
                    scite_nums.add(num)
                    if num < 1 or num > bibitem_count:
                        print(f"{p}:{n}: [C2] \\scite 编号越界：{{{num}}}（文献共 {bibitem_count} 篇，范围 1-{bibitem_count}）——"
                              f"重编号/删文献后忘记同步的典型症状")
                        issues += 1

    # C3：未引用 bibitem（仅当 bibitem 存在时机械报告）
    if bibitem_count and scite_nums:
        unreferenced = [i for i in range(1, bibitem_count + 1) if i not in scite_nums]
        if unreferenced:
            print(f"[C3] 未被任何 \\scite 引用的文献编号：{unreferenced}（供人工复核是否误漏）")
            issues += 1

    if issues:
        print(f"\n共 {issues} 个问题。引用机制必须统一（\\scite 或 \\cite 二选一），编号必须与文献列表一致。")
        return 1
    print("引用检查通过：机制统一、\\scite 编号全部在文献范围内、无未引用编号。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
