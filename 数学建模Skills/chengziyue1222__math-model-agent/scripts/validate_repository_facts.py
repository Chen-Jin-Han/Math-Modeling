#!/usr/bin/env python3
"""Prevent public module and export counts from drifting out of documentation."""

from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


def _module_count() -> int:
    return sum(
        path.name != "__init__.py"
        for path in (REPOSITORY_ROOT / "code" / "algorithms").glob("*.py")
    )


def _export_count() -> int:
    sys.path.insert(0, str(REPOSITORY_ROOT / "code"))
    import algorithms

    return len(algorithms.__all__)


def _standard_skill_count() -> int:
    return sum(path.is_dir() for path in (REPOSITORY_ROOT / "skills").iterdir())


def main() -> int:
    module_count = _module_count()
    export_count = _export_count()
    skill_count = _standard_skill_count()
    expected = {
        REPOSITORY_ROOT / "README.md": (
            f"{skill_count} 个标准 Codex Skills · {module_count} 个算法与质量模块",
            f"{export_count} 个公开导出，{module_count} 个模块文件",
        ),
        REPOSITORY_ROOT / "使用说明.md": (
            f"{module_count} 个模块文件",
            f"{export_count} 个公开导出",
        ),
        REPOSITORY_ROOT / "code" / "algorithms" / "__init__.py": (
            f"{export_count} 个公开导出，{module_count} 个算法与质量模块",
        ),
    }
    errors = []
    for path, required_phrases in expected.items():
        text = path.read_text(encoding="utf-8")
        for phrase in required_phrases:
            if phrase not in text:
                errors.append(f"{path.relative_to(REPOSITORY_ROOT)} missing: {phrase}")
    if errors:
        print("Repository-fact validation failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"Validated {module_count} module files and {export_count} public exports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
