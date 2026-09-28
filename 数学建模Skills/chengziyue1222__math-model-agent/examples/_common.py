"""Shared deterministic artifact helpers for end-to-end examples."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.run_manifest import build_manifest


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_manifest(project_root: Path, specification: dict[str, Any]) -> dict[str, Any]:
    manifest = build_manifest(specification, project_root)
    write_json(project_root / "run-manifest.json", manifest)
    return manifest
