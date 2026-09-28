#!/usr/bin/env python3
"""Compile and render the canonical CUMCM-style template preview."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TEMPLATE = REPOSITORY_ROOT / "skills" / "write-model-paper" / "assets" / "cume-template.tex"
PREVIEW_STEM = "cume-template-preview"


def _run(command: list[str], *, cwd: Path) -> None:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if completed.returncode:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}")


def _find_pdftoppm() -> str | None:
    """Resolve the Poppler executable when Codex's Windows PATH exposes a wrapper."""
    found = shutil.which("pdftoppm")
    if not found:
        return None
    path = Path(found)
    if path.suffix.lower() == ".cmd" and len(path.parents) >= 3:
        native = path.parents[2] / "native" / "poppler" / "Library" / "bin" / "pdftoppm.exe"
        if native.is_file():
            return str(native)
    return found


def render_preview(template: Path, output_dir: Path, *, force: bool = False) -> tuple[Path, list[Path]]:
    template = template.resolve()
    if not template.is_file():
        raise FileNotFoundError(f"template does not exist: {template}")
    xelatex = shutil.which("xelatex")
    pdftoppm = _find_pdftoppm()
    if not xelatex or not pdftoppm:
        missing = [name for name, executable in (("xelatex", xelatex), ("pdftoppm", pdftoppm)) if not executable]
        raise RuntimeError(f"required renderer unavailable: {', '.join(missing)}")

    output_dir = output_dir.resolve()
    pdf_path = output_dir / f"{PREVIEW_STEM}.pdf"
    tex_path = output_dir / f"{PREVIEW_STEM}.tex"
    page_prefix = output_dir / f"{PREVIEW_STEM}-page"
    existing = [path for path in (pdf_path, tex_path) if path.exists()]
    if existing and not force:
        rendered = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"preview already exists (use --force to replace): {rendered}")

    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template, tex_path)
    command = [xelatex, "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={output_dir}", tex_path.name]
    _run(command, cwd=output_dir)
    _run(command, cwd=output_dir)
    if not pdf_path.is_file():
        raise RuntimeError(f"XeLaTeX completed without producing {pdf_path}")
    _run([pdftoppm, "-png", "-r", "150", pdf_path.name, page_prefix.name], cwd=output_dir)
    pages = sorted(output_dir.glob(f"{PREVIEW_STEM}-page-*.png"))
    if not pages:
        raise RuntimeError("PDF rendered without page images")
    return pdf_path, pages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output-dir", type=Path, default=REPOSITORY_ROOT / "output" / "pdf")
    parser.add_argument("--force", action="store_true", help="replace an existing preview")
    args = parser.parse_args()
    try:
        pdf_path, pages = render_preview(args.template, args.output_dir, force=args.force)
    except (FileNotFoundError, FileExistsError, RuntimeError) as exc:
        print(f"template preview failed: {exc}", file=sys.stderr)
        return 1
    print(f"PDF preview: {pdf_path}")
    print(f"Rendered {len(pages)} page image(s) in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
