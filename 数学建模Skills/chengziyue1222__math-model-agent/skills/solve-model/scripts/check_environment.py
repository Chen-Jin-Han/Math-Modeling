#!/usr/bin/env python3
"""Check dependencies and the repository algorithm package without changing files."""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import sys
from pathlib import Path


REQUIRED = ("numpy", "scipy", "matplotlib", "pandas", "sklearn", "networkx")
ALGORITHM_MODULES = (
    "algorithms.modeling_contracts",
    "algorithms.modeling_quality",
    "algorithms.data_diagnostics",
    "algorithms.sci_figures",
)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    skill_root = Path(__file__).resolve().parents[1]
    missing: list[str] = []
    versions: dict[str, str] = {}

    for name in REQUIRED:
        try:
            module = importlib.import_module(name)
            versions[name] = getattr(module, "__version__", "unknown")
        except Exception as exc:  # dependency diagnostics must report all failures
            missing.append(f"{name}: {exc}")

    local_runtime = skill_root / "scripts" / "_runtime" / "run_standard_skill.py"
    repository_runtime = repo_root / "scripts" / "run_standard_skill.py"
    runtime_source = next(
        (path for path in (local_runtime, repository_runtime) if path.is_file()),
        None,
    )
    runtime_error = None if runtime_source else "bundled or repository Skill runtime not found"

    algorithm_error = None
    export_count = None
    algorithm_source = None
    distribution_version = None
    if not missing:
        repository_code = repo_root / "code"
        if repository_code.is_dir():
            sys.path.insert(0, str(repository_code))
        try:
            algorithms = importlib.import_module("algorithms")
            for module_name in ALGORITHM_MODULES:
                importlib.import_module(module_name)
            export_count = len(getattr(algorithms, "__all__", ()))
            algorithm_source = str(Path(algorithms.__file__).resolve())
            try:
                distribution_version = importlib.metadata.version("math-model-agent")
            except importlib.metadata.PackageNotFoundError:
                distribution_version = "repository-checkout"
        except Exception as exc:
            algorithm_error = f"{type(exc).__name__}: {exc}"

    report = {
        "ok": not missing and algorithm_error is None and runtime_error is None,
        "python": sys.version.split()[0],
        "repo_root": str(repo_root),
        "versions": versions,
        "missing": missing,
        "runtime_error": runtime_error,
        "runtime_source": str(runtime_source) if runtime_source else None,
        "algorithm_error": algorithm_error,
        "algorithm_source": algorithm_source,
        "math_model_agent_version": distribution_version,
        "algorithm_exports": export_count,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
