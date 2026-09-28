#!/usr/bin/env python3
"""题目信息抽取：把 PDF / Word / Excel / txt / csv 转成一份 markdown 提取物。

用法：
    python extract_input.py <输入文件> -o <输出.md>

分派：
    .pdf   -> pdftotext -layout（缺 poppler 时退 pypdf）
    .docx  -> officecli view <f> text
    .xlsx  -> officecli view <f> text（输出 A1=值 行，保留稀疏单元格）
    .xls   -> pandas+xlrd（可选依赖，缺时提示转存 .xlsx）
    .txt/.csv -> 直接读（utf-8，errors=replace）

乱码处理（第三次模拟踩坑：pdftotext 中文乱码、PDF 内嵌字体把 α/β 存为私有区码点）：
    - 私有区码点（U+E000-F8FF，如 α/β）自动映射为 Unicode 字符
    - pdftotext 输出乱码率 >5% 自动降级 pypdf 重抽
    - 最终仍乱码时 stdout 打 GARBLED: 行并退出码 3，上层据此直接跳 OCR 兜底链

退出码: 0 = OK；1 = 空内容（可能是扫描版）；2 = 不支持的扩展名；3 = 乱码（建议 OCR）
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# PDF 内嵌字体私有区码点映射（可扩展；本次模拟：α→U+F061、β→U+F062）
PUA_MAP = {"": "α", "": "β"}


def apply_pua(text):
    for k, v in PUA_MAP.items():
        text = text.replace(k, v)
    return text


def garbled_score(text):
    """乱码启发式：替换符(U+FFFD) + 私有区 + 不可打印控制字符占比。"""
    if not text:
        return 0.0

    def is_bad(ch):
        o = ord(ch)
        return ch == "�" or 0xE000 <= o <= 0xF8FF or 0xF0000 <= o <= 0x10FFFD \
            or o < 0x09 or 0x0B <= o <= 0x1F

    return sum(is_bad(ch) for ch in text) / len(text)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def extract_pdf(path):
    """pdftotext 优先；输出为空或乱码（>5%）时降级 pypdf 重抽，取乱码率更低者。"""
    out = ""
    if shutil.which("pdftotext"):
        r = run(["pdftotext", "-layout", str(path), "-"])
        out = r.stdout if r.returncode == 0 else r.stderr
    if not out or garbled_score(apply_pua(out)) > 0.05:
        try:
            import pypdf
            alt = "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(str(path)).pages)
            if garbled_score(apply_pua(alt)) < garbled_score(apply_pua(out)):
                out = alt
        except ImportError:
            pass
        except Exception:
            pass
    if not out:
        out = "ERROR: 无法抽取 PDF 文本（缺 pdftotext(poppler)/pypdf），可能是扫描版"
    return out


def extract_docx(path):
    if not shutil.which("officecli"):
        return "ERROR: 缺 officecli，无法抽取 .docx/.xlsx（安装见 officecli skill）"
    return run(["officecli", "view", str(path), "text"]).stdout


def extract_xlsx(path):
    if not shutil.which("officecli"):
        return "ERROR: 缺 officecli，无法抽取 .xlsx（安装见 officecli skill）"
    return run(["officecli", "view", str(path), "text"]).stdout


def extract_xls(path):
    """.xls 老格式（二进制 Excel 97-2003）：pandas+xlrd 逐 sheet 输出。"""
    try:
        import pandas as pd
    except ImportError:
        return "ERROR: 缺 pandas/xlrd 读取 .xls（pip install pandas xlrd）；或转存为 .xlsx 用 officecli"
    try:
        xls = pd.read_excel(str(path), sheet_name=None, header=None)
    except Exception as e:
        return f"ERROR: .xls 读取失败（{e}）；或转存为 .xlsx 用 officecli"
    parts = []
    for name, df in xls.items():
        parts.append(f"## Sheet: {name}（{df.shape[0]} 行 × {df.shape[1]} 列）")
        parts.append(df.to_string(index=False))
    return "\n\n".join(parts)


def extract_txt(path):
    return path.read_text(encoding="utf-8", errors="replace")


HANDLERS = {".pdf": extract_pdf, ".docx": extract_docx, ".xlsx": extract_xlsx,
            ".xls": extract_xls, ".txt": extract_txt, ".csv": extract_txt, ".md": extract_txt}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="输入文件路径")
    ap.add_argument("-o", "--out", required=True, help="输出 markdown 路径")
    args = ap.parse_args()

    src = Path(args.input)
    handler = HANDLERS.get(src.suffix.lower())
    if handler is None:
        print(f"SKIP: 不支持 {src.suffix}（支持 pdf/docx/xlsx/xls/txt/csv/md）")
        sys.exit(2)

    text = apply_pua(handler(src))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(text, encoding="utf-8")

    n = len(text.splitlines())
    empty = not text.strip()  # 单行合法文档（如标题）不算空；无文本才算
    if src.suffix.lower() == ".pdf" and garbled_score(text) > 0.05:
        print(f"GARBLED: {src.name} 文本层乱码率 {garbled_score(text):.0%}，pdftotext/pypdf 均不可用——"
              f"直接走 OCR 兜底链（pdftoppm 渲染成图 + tesseract/paddleocr）或人工转录")
        sys.exit(3)
    print(f"OK: {src.name} -> {args.out}（{n} 行）" + ("；内容为空，可能是扫描版，需 OCR 或人工转录" if empty else ""))


if __name__ == "__main__":
    main()
