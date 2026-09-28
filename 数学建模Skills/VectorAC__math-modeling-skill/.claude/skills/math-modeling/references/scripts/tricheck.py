#!/usr/bin/env python3
"""三方核对半自动 — 论文关键数字 vs checkpoint 记录 vs 来源文件（Phase 5 使用）。

纯结构/形式检查（正则数值提取 + 数值比对），内容判断永远由人完成：
提取不到数值 / 单位缺失 → 标 MANUAL，交人工复核（模型数字是否换了说法、是否单位不同）。

checkpoint.json 的 tri_check 段（Phase 3 过渡时写入，示例）:
  { "tri_check": [ {"key": "平均等待时间", "value": 12.3, "unit": "min",
                     "source": "03_q1_results.md", "tol": 0.01}, ... ] }

检查项:
  [T1] 出现性：key 在 main.tex 中出现（不出现 → MANUAL，可能换了说法）
  [T2] 一致性：key 位置 ±40 字符窗口内提取数值 vs value，|差| ≤ max(tol*|value|, 1e-9)
  [T3] 来源核对：value 以 str(value)/6g 字符串形式在 source 文件内出现（精确匹配；
       仅为展示，不参与退出码——显示舍入须人工复核）

输出: 每条 key 一行（key | 论文提取值 | checkpoint 值 | 来源出现 | PASS/FAIL/MANUAL）

用法:  python tricheck.py <checkpoint.json> <main.tex>
退出码: 0 = 全部机械通过；1 = 存在 FAIL 或 MANUAL；2 = 用法错误
"""
import json
import os
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 终端 GBK 会导致中文乱码

NUMBER = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
WINDOW = 40  # key 位置前后字符窗口


def extract_numbers(text, pos, key_len):
    """key 位置 ±WINDOW 字符窗口内提取所有数值（浮点数优先）。"""
    lo, hi = max(0, pos - WINDOW), min(len(text), pos + key_len + WINDOW)
    return [float(x) for x in NUMBER.findall(text[lo:hi]) if float(x) != 0.0]


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    ck_path, tex_path = argv
    if not os.path.exists(ck_path) or not os.path.exists(tex_path):
        print("用法错误：checkpoint 或 main.tex 不存在")
        return 2

    with open(ck_path, encoding="utf-8") as f:
        ck = json.load(f)
    entries = ck.get("tri_check", [])
    if not entries:
        print("checkpoint 无 tri_check 段（Phase 3 未写入关键数字）——跳过三方核对，请在 Phase 3 过渡时写入")
        return 0

    try:
        with open(tex_path, encoding="utf-8") as f:
            tex = f.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"{tex_path}: 无法读取（{e}）")
        return 1

    issues = 0
    print(f"{'关键数字':<16} | {'论文提取':>12} | {'checkpoint':>12} | 来源 | 结论")
    print("-" * 70)
    for e in entries:
        key = str(e.get("key", ""))
        value = float(e.get("value"))
        tol = float(e.get("tol", 0.01))
        source = str(e.get("source", ""))

        # T3：来源核对（source 相对 checkpoint 所在目录解析）
        src_ok = "-"
        if source:
            src_path = source
            if not os.path.isabs(src_path):
                src_path = os.path.join(os.path.dirname(os.path.abspath(ck_path)), source)
            if os.path.exists(src_path):
                with open(src_path, encoding="utf-8", errors="replace") as f:
                    src_text = f.read()
                fmt = [str(value), f"{value:.6g}"]
                src_ok = "✓" if any(f in src_text for f in fmt) else "✗"
            else:
                src_ok = "缺文件"

        # T1+T2：论文中出现性与数值一致性
        positions = [m.start() for m in re.finditer(re.escape(key), tex)]
        if not positions:
            print(f"{key:<16} | {'—':>12} | {value:>12.6g} | {src_ok} | MANUAL（key 未在论文出现——可能换了说法）")
            issues += 1
            continue
        found, best_diff = None, None
        for pos in positions:
            for num in extract_numbers(tex, pos, len(key)):
                diff = abs(num - value)
                if best_diff is None or diff < best_diff:
                    best_diff, found = diff, num
        tol_abs = max(tol * abs(value), 1e-9)
        if found is None:
            print(f"{key:<16} | {'—':>12} | {value:>12.6g} | {src_ok} | MANUAL（key 附近提取不到数值）")
            issues += 1
        elif best_diff <= tol_abs:
            print(f"{key:<16} | {found:>12.6g} | {value:>12.6g} | {src_ok} | PASS")
        else:
            print(f"{key:<16} | {found:>12.6g} | {value:>12.6g} | {src_ok} | FAIL（差 {best_diff:.6g}，超容差 {tol_abs:.6g}）")
            issues += 1

    if issues:
        print(f"\n共 {issues} 项未通过机械核对。FAIL 需定位修改；MANUAL 交人工复核（可能换说法/单位/舍入）。")
        return 1
    print("\n三方核对机械检查全部通过；MANUAL 项为 0，可声称关键数字一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
