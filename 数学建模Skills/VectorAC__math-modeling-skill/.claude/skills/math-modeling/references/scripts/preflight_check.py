#!/usr/bin/env python3
"""LaTeX 论文预检脚本 — 编译前拦截机械问题（Phase 5 使用）。

纯结构/形式检查（正则匹配），不做任何内容生成与内容判断。

检查项:
  [L1] 残留占位符（【】/TODO/FIXME/占位/待补/这里插入 等）
  [L2] \\includegraphics 引用的图片文件不存在
  [L2] \\ref/\\cref/\\eqref 引用无对应 \\label
  [L2] 摘要区公式数量超上限（国赛 ≤2 / 美赛 ≤3，允许核心公式简写版）
  [L2] 中文行内半角标点（汉字,;:?!汉字）
  [L3] 孤立 label（定义但全文无引用；单文件口径，跨文件口径用 combinecheck.py）
  [LOG] 页数报告 + Missing character 缺字形统计（--log 参数，或自动找 main.tex 同目录同名 .log）
  [L2] 页数超限（--max-pages <N>，国赛正文 ≤30 用；超限退出码 1——机械拦截，不靠人凌晨看日志）

用法:  python preflight_check.py main.tex [part_q1.tex ...] [--log <path>] [--max-pages <N>]
退出码: 0 = 无问题；1 = 有问题（L1 阻止声称完成，L2 必须修复）；2 = 用法错误
"""
import os
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 终端 GBK 会导致中文乱码

PLACEHOLDER = re.compile(r"【[^】]*】|TODO|FIXME|占位|待补|待插入|这里插入|placeholder", re.I)
GRAPHICS = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
LABEL = re.compile(r"\\label\{([^}]+)\}")
REF = re.compile(r"\\\w*ref\{([^}]+)\}")
MATH_DISPLAY = re.compile(r"\\\[|\\begin\{(equation|align|gather)\*?\}")
INLINE_DOLLAR = re.compile(r"(?<!\\)\$")  # 行内公式 $..$（排除转义 \$），成对计数
HALF_WIDTH_PUNCT = re.compile(r"[\u4e00-\u9fa5][,;:?!][\u4e00-\u9fa5]")
IMG_EXTS = (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg")

# 摘要区识别：国赛模板的摘要节也用 \begin{abstract}（cumcmthesis.cls 重定义），
# 故按 \documentclass{cumcmthesis} 判国赛，否则按环境类型判。
ABSTRACT_BEGIN_MCM = re.compile(r"\\begin\{abstract\}")
ABSTRACT_END_MCM = re.compile(r"\\end\{abstract\}")
ABSTRACT_BEGIN_CUMCM = re.compile(r"\\section\*?\{摘要\}")
ABSTRACT_END_CUMCM = re.compile(r"\\section\*?\{")
DOCUMENTCLASS_CUMCM = re.compile(r"\\documentclass(?:\[[^\]]*\])?\{cumcmthesis\}")
ABSTRACT_FORMULA_LIMIT = {"cumcm": 2, "mcm": 3}
GRAPHICSPATH = re.compile(r"\\graphicspath\{((?:\s*\{[^}]*\})+)\}")  # 块间容忍空白（续行拼接后 {a}  {b}）
PAGE_COUNT = re.compile(r"Output written on [^\s]+ \(([0-9]+) pages")
MISSING_CHAR = re.compile(r"Missing character: There is no (.+?) in font ([^!]+)!")


def join_continued_lines(lines):
    """LaTeX 行尾 % 吞掉换行符：把 'xxx%\\nnext' 拼成 'xxxnext'。

    根因（第三次模拟 preflight 误报）：cumcmthesis.cls 的 \\graphicspath 用
    行尾 % 续行跨两行，单行正则匹配不到 → 返回空目录 → 裸文件名图片被误报不存在。
    """
    out, i, n = [], 0, len(lines)
    while i < n:
        cur = lines[i].rstrip("\n")
        while cur.rstrip().endswith("%") and i + 1 < n:
            cur = cur.rstrip()[:-1] + lines[i + 1].rstrip("\n")
            i += 1
        out.append(cur)
        i += 1
    return out


def find_abstract_ranges(lines):
    """返回 (start, end, kind) 列表（0 基行号，end 不含）。kind: 'cumcm' | 'mcm'。"""
    is_cumcm_doc = any(DOCUMENTCLASS_CUMCM.search(line) for line in lines)
    ranges, start, kind = [], None, None
    for i, line in enumerate(lines):
        if start is None:
            if ABSTRACT_BEGIN_CUMCM.search(line):
                start, kind = i, "cumcm"
            elif ABSTRACT_BEGIN_MCM.search(line):
                start, kind = i, "cumcm" if is_cumcm_doc else "mcm"
        else:
            end_pat = ABSTRACT_END_CUMCM if kind == "cumcm" else ABSTRACT_END_MCM
            if end_pat.search(line):
                ranges.append((start, i, kind))
                start, kind = None, None
    if start is not None:
        ranges.append((start, len(lines), kind))
    return ranges


def get_graphicspaths(lines):
    """解析 \\graphicspath{{a}{b}} → [a, b]（先做行尾 % 续行拼接）。"""
    dirs = []
    for line in join_continued_lines(lines):
        m = GRAPHICSPATH.search(line)
        if m:
            dirs += re.findall(r"\{([^}]*)\}", m.group(1))
    return dirs


def get_cls_graphicspaths(base, lines):
    """文档声明 cumcmthesis 且同目录有 cumcmthesis.cls 时，并入 .cls 的 \\graphicspath。

    .cls 的 graphicspath 是模板级搜索路径（figures/pictures/... 等默认目录），
    不并入会让依赖这些默认目录的裸文件名图片被误报不存在。
    """
    if not any(DOCUMENTCLASS_CUMCM.search(line) for line in lines):
        return []
    cls_path = os.path.join(base, "cumcmthesis.cls")
    if not os.path.exists(cls_path):
        return []
    with open(cls_path, encoding="utf-8", errors="replace") as f:
        return get_graphicspaths(f.readlines())


def check_log(log_path, max_pages=None):
    """解析编译日志：页数报告（可选超限拦截）+ Missing character（按 字符×字体 去重统计）。

    max_pages: 非 None 时，页数超过该值判 [L2]（机械拦截「正文 ≤30 页」类硬门禁）。
    """
    issues = 0
    if not os.path.exists(log_path):
        print(f"[LOG] 未找到编译日志：{log_path}（跳过日志检查）")
        return 0
    with open(log_path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    m = PAGE_COUNT.search(text)
    if m:
        pages = int(m.group(1))
        print(f"[LOG] 编译产物页数：{pages} 页（以实际编译产物为准回写 checkpoint）")
        if max_pages is not None and pages > max_pages:
            print(f"[L2] 页数超限：{pages} 页 > 上限 {max_pages} 页（正文 ≤30 页为硬门禁，"
                  f"超页删除纪律见 phase4 模板「超页删除纪律」）")
            issues += 1
    else:
        print("[LOG] 日志中未解析到页数（缺少 'Output written ... (N pages)' 行），可能未完成编译")
    missing = set(MISSING_CHAR.findall(text))
    if missing:
        kinds = [f"{c}@{f}" for c, f in sorted(missing)][:8]
        print(f"[L2] Missing character 缺字形 {len(missing)} 类（{', '.join(kinds)}{'…' if len(missing) > 8 else ''}）——编译后会有空白/错误字形，需换字体或查字体编码")
        issues += len(missing)
    return issues


def check_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError) as e:
        print(f"{path}: 无法读取（{e}）")
        return 1

    base = os.path.dirname(os.path.abspath(path))
    issues = 0
    labels = set()
    refs = set()
    abs_ranges = find_abstract_ranges(lines)

    # 国赛 2026 AI 合规：支撑材料必须含《AI工具使用详情.pdf》（2026-09-01 试行规定）
    if any(DOCUMENTCLASS_CUMCM.search(line) for line in lines):
        pdf_candidates = [os.path.join(base, "AI工具使用详情.pdf"),
                          os.path.join(base, "支撑材料", "AI工具使用详情.pdf")]
        if not any(os.path.exists(p) for p in pdf_candidates):
            print(f"{path}: [L2] 国赛支撑材料缺少《AI工具使用详情.pdf》（2026 新规必带项，"
                  "文件名固定；模板见 references/cumcm-template/ai-usage-detail-template.tex）")
            issues += 1
    search_dirs = [base] + [os.path.join(base, d) for d in get_graphicspaths(lines)]
    search_dirs += [os.path.join(base, d) for d in get_cls_graphicspaths(base, lines)]

    for n, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        if line.lstrip().startswith("%"):
            continue  # 纯注释行（模板说明里的"占位符"字样不算）

        m = PLACEHOLDER.search(line)
        if m:
            print(f"{path}:{n}: [L1] 残留占位符：{m.group(0)}")
            issues += 1

        for g in GRAPHICS.findall(line):
            img = g.strip()
            if img.startswith("/") or "://" in img:
                continue  # 绝对路径/URL，跳过
            found = False
            for d in search_dirs:
                for ext in ("", *IMG_EXTS):
                    if os.path.exists(os.path.join(d, img + ext)):
                        found = True
                        break
                if found:
                    break
            if not found:
                print(f"{path}:{n}: [L2] 图片文件不存在：{img}")
                issues += 1

        for r in REF.findall(line):
            refs.add(r)
        for lab in LABEL.findall(line):
            labels.add(lab)

        for m in HALF_WIDTH_PUNCT.finditer(line):
            print(f"{path}:{n}: [L2] 中文行内半角标点：…{m.group(0)}…（改用全角）")
            issues += 1

    # 摘要区公式数量：按赛别阈值（国赛 ≤2 / 美赛 ≤3），允许核心公式简写版
    for s, e, kind in abs_ranges:
        limit = ABSTRACT_FORMULA_LIMIT[kind]
        count = 0
        for raw in lines[s:e]:
            line = raw.rstrip("\n")
            if line.lstrip().startswith("%"):
                continue
            count += len(INLINE_DOLLAR.findall(line)) // 2  # $..$ 成对
            count += len(MATH_DISPLAY.findall(line))  # \[ / equation / align / gather
        if count > limit:
            print(f"{path}: 摘要区（{kind}）含 {count} 个公式，超过上限 {limit}（国赛 ≤2 / 美赛 ≤3），请精简为核心公式简写版")
            issues += 1

    for r in sorted(refs - labels):
        print(f"{path}: [L2] 引用无对应 label：\\ref{{{r}}}")
        issues += 1

    # L3 孤立 label：单文件口径；跨文件（部件间互相 \ref）口径由 combinecheck.py 处理
    for lab in sorted(labels - refs):
        print(f"{path}: [L3] 孤立 label（定义但无引用）：\\label{{{lab}}}（故意的锚点可忽略；附录表无引用需处理）")
        issues += 1

    return issues


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    log_path, rest, i = None, [], 0
    max_pages = None
    while i < len(argv):
        a = argv[i]
        if a == "--log":
            i += 1
            if i >= len(argv):
                print("用法错误：--log 需要路径参数")
                return 2
            log_path = argv[i]
        elif a.startswith("--log="):
            log_path = a[len("--log="):]
        elif a == "--max-pages":
            i += 1
            if i >= len(argv):
                print("用法错误：--max-pages 需要整数参数")
                return 2
            try:
                max_pages = int(argv[i])
            except ValueError:
                print("用法错误：--max-pages 需要整数参数")
                return 2
        elif a.startswith("--max-pages="):
            try:
                max_pages = int(a[len("--max-pages="):])
            except ValueError:
                print("用法错误：--max-pages 需要整数参数")
                return 2
        else:
            rest.append(a)
        i += 1
    if not rest:
        print("用法错误：缺少 tex 文件参数")
        return 2
    if log_path is None:  # 自动找第一个 tex 文件同目录同名 .log
        base = os.path.dirname(os.path.abspath(rest[0]))
        log_path = os.path.join(base, os.path.basename(os.path.splitext(rest[0])[0]) + ".log")

    total = sum(check_file(p) for p in rest)
    total += check_log(log_path, max_pages)
    if total:
        print(f"\n共 {total} 个问题。L1（占位符）未清除前不得声称论文完成；L2 全部修复后再编译。")
        return 1
    print("预检通过：无占位符、无缺失图片、无悬空引用、无孤立 label、摘要公式数量符合标准、标点规范、日志无缺字形。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
