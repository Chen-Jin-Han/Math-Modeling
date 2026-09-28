"""Fail-closed CUMCM submission, anonymity, and support-package preflight."""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable


MAX_DELIVERY_BYTES = 20 * 1024 * 1024
DEFAULT_IDENTITY_FILE = ".cumcm-identities.json"
REQUIRED_IDENTITY_GROUPS = ("names", "schools", "regions", "student_ids", "windows_usernames")
TEXT_SUFFIXES = {
    ".c", ".cfg", ".cpp", ".csv", ".h", ".ini", ".java", ".jl", ".json",
    ".log", ".m", ".md", ".py", ".r", ".tex", ".toml", ".tsv", ".txt", ".yaml", ".yml",
}
SOURCE_SUFFIXES = {".c", ".cpp", ".h", ".java", ".jl", ".m", ".py", ".r"}
ABSOLUTE_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:[\\/](?:Users|Documents and Settings)[\\/][^\s\"'<>]+|"
    r"/(?:home|Users)/[^\s\"'<>]+|\\\\[^\s\\/]+[\\/][^\s\"'<>]+)"
)
LABELED_IDENTITY_RE = re.compile(r"(?:姓名|学校|赛区|学号)\s*[:：=]\s*[^\s,，;；<]{2,}")
PATH_REFERENCE_RE = re.compile(
    r"(?i)(?:read_csv|read_excel|loadtxt)\s*\(\s*[rubf]*[\"']([^\"']+)[\"']"
)
TEX_GRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}")
TEX_FONT_RE = re.compile(r"\\(?:setmainfont|setmonofont|newfontfamily(?:\\\w+)?)\{([^}]+)\}")
RESOURCE_REFERENCE_RE = re.compile(
    r"[\"']((?:data|config|fonts|figures|assets|inputs)[\\/][^\"']+)[\"']",
    re.I,
)
VENDORED_LIBRARY_PARTS = {"site-packages", "node_modules", ".venv", "venv", "vendor"}
AI_DETAILS_FILENAME = "AI工具使用详情.pdf"
AI_DECLARATION_HEADING_RE = re.compile(
    r"\\(?:section|chapter)\*?\{[^}]*AI\s*工具使用声明[^}]*\}|"
    r"^\s*#{1,6}\s*(?:AI\s*工具使用声明|AI\s+Tool\s+Usage\s+Declaration)\s*$",
    re.I | re.M,
)
REFERENCES_HEADING_RE = re.compile(
    r"\\(?:section|chapter)\*?\{[^}]*参考文献[^}]*\}|"
    r"^\s*#{1,6}\s*(?:参考文献|References)\s*$",
    re.I | re.M,
)


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _safe_member(name: str) -> bool:
    posix = PurePosixPath(name.replace("\\", "/"))
    windows = PureWindowsPath(name)
    return bool(name) and not posix.is_absolute() and not windows.is_absolute() and not windows.drive and ".." not in posix.parts


def _issue(code: str, path: str, detail: str) -> dict[str, str]:
    return {"code": code, "path": path, "detail": detail}


def _identity_hits(text: str, terms: Iterable[str]) -> list[str]:
    hits: list[str] = []
    if ABSOLUTE_PATH_RE.search(text):
        hits.append("absolute user path")
    if LABELED_IDENTITY_RE.search(text):
        hits.append("labeled identity field")
    lowered = text.casefold()
    for term in terms:
        normalized = term.strip()
        if len(normalized) >= 2 and normalized.casefold() in lowered:
            hits.append(f"configured identity term: {normalized}")
    return sorted(set(hits))


def _load_identity_terms(
    root: Path,
    identity_file: Path | None,
    additional_terms: Iterable[str],
    issues: list[dict[str, str]],
) -> tuple[list[str], dict[str, Any]]:
    identity_file_was_explicit = identity_file is not None
    path = identity_file or root / DEFAULT_IDENTITY_FILE
    if not path.is_absolute():
        path = root / path
    display_path = _relative(path, root)
    terms = [value.strip() for value in additional_terms if value.strip()]
    username = Path.home().name.strip()
    if username:
        terms.append(username)
    if not path.is_file():
        if identity_file_was_explicit:
            issues.append(
                _issue(
                    "IDENTITY_DICTIONARY_MISSING",
                    display_path,
                    "the explicitly requested private identity dictionary does not exist",
                )
            )
        return sorted(set(terms), key=str.casefold), {
            "status": "FAIL" if identity_file_was_explicit else "NOT_RUN",
            "path": display_path,
            "term_count": len(set(terms)),
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        issues.append(_issue("IDENTITY_DICTIONARY_INVALID", display_path, type(exc).__name__))
        return sorted(set(terms), key=str.casefold), {
            "status": "FAIL",
            "path": display_path,
            "term_count": len(set(terms)),
        }
    if not isinstance(payload, dict):
        issues.append(_issue("IDENTITY_DICTIONARY_INVALID", display_path, "root must be an object"))
    else:
        for group in REQUIRED_IDENTITY_GROUPS:
            values = payload.get(group)
            if not isinstance(values, list) or not any(str(value).strip() for value in values):
                issues.append(
                    _issue(
                        "IDENTITY_DICTIONARY_INCOMPLETE",
                        display_path,
                        f"{group} must contain at least one value",
                    )
                )
                continue
            terms.extend(str(value).strip() for value in values if str(value).strip())
        other_terms = payload.get("other_terms", [])
        if isinstance(other_terms, list):
            terms.extend(str(value).strip() for value in other_terms if str(value).strip())
        elif other_terms is not None:
            issues.append(
                _issue("IDENTITY_DICTIONARY_INVALID", display_path, "other_terms must be an array")
            )
    unique_terms = sorted(set(terms), key=str.casefold)
    failed = any(issue["code"].startswith("IDENTITY_DICTIONARY_") for issue in issues)
    return unique_terms, {
        "status": "FAIL" if failed else "PASS",
        "path": display_path,
        "term_count": len(unique_terms),
    }


def _load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("files"), list):
        raise ValueError("support manifest must be an object with a files array")
    return value


def _manifest_files(manifest: dict[str, Any]) -> set[str]:
    files: set[str] = set()
    for item in manifest["files"]:
        value = item.get("path") if isinstance(item, dict) else item
        relative = str(value or "").replace("\\", "/")
        if not _safe_member(relative):
            raise ValueError(f"unsafe support-manifest path: {relative}")
        files.add(relative)
    return files


def _archive_members(path: Path) -> tuple[list[str], Any, dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".zip":
        archive = zipfile.ZipFile(path)
        members = [name.replace("\\", "/") for name in archive.namelist() if not name.endswith(("/", "\\"))]
        return members, archive, {"format": "zip", "backend": "stdlib", "status": "PASS"}
    if suffix == ".rar":
        try:
            import rarfile
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(f"RAR validation requires rarfile: {exc}") from exc
        try:
            setup = rarfile.tool_setup(force=True)
            if not setup.check():
                raise RuntimeError("no usable RAR extraction backend")
        except rarfile.RarCannotExec as exc:
            raise RuntimeError("no usable RAR extraction backend") from exc
        backend = str(setup.setup.get("open_cmd", ("unknown",))[0]).replace("_TOOL", "").lower()
        archive = rarfile.RarFile(path)
        members = [info.filename.replace("\\", "/") for info in archive.infolist() if not info.isdir()]
        return members, archive, {"format": "rar", "backend": backend, "status": "PASS"}
    raise ValueError("support archive must be ZIP or RAR")


def _declared_packages(root: Path, manifest: dict[str, Any]) -> set[str]:
    dependencies = manifest.get("dependencies") if isinstance(manifest.get("dependencies"), dict) else {}
    dependency_file = str(dependencies.get("file", ""))
    packages: set[str] = set()
    path = root / dependency_file if dependency_file else None
    if path and path.is_file() and path.name.lower().startswith("requirements"):
        for line in path.read_text(encoding="utf-8").splitlines():
            token = re.split(r"[<>=!~\[;\s]", line.strip(), maxsplit=1)[0]
            if token and not token.startswith(("#", "-")):
                packages.add(token.lower().replace("-", "_"))
    aliases = dependencies.get("import_names", {})
    if isinstance(aliases, dict):
        packages.update(str(name).lower() for name in aliases)
    return packages


def _validate_python_imports(root: Path, manifest: dict[str, Any], issues: list[dict[str, str]]) -> None:
    py_files = list(root.rglob("*.py"))
    local_modules = {path.stem.lower() for path in py_files}
    local_modules.update(path.name.lower() for path in root.iterdir() if path.is_dir())
    declared = _declared_packages(root, manifest)
    stdlib = {name.lower() for name in getattr(sys, "stdlib_module_names", set())}
    for path in py_files:
        relative = _relative(path, root)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (SyntaxError, UnicodeError) as exc:
            issues.append(_issue("SOURCE_PARSE_FAILED", relative, str(exc)))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".", 1)[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".", 1)[0]]
            else:
                continue
            for module in names:
                normalized = module.lower().replace("-", "_")
                if normalized not in stdlib and normalized not in local_modules and normalized not in declared:
                    issues.append(_issue("IMPORT_NOT_PROVIDED", relative, f"{module} is neither packaged nor declared"))


def _validate_references(root: Path, manifest: dict[str, Any], issues: list[dict[str, str]]) -> None:
    fonts: set[str] = set()
    dependencies = manifest.get("dependencies") if isinstance(manifest.get("dependencies"), dict) else {}
    if isinstance(dependencies.get("fonts"), list):
        fonts = {str(value).casefold() for value in dependencies["fonts"]}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        relative = _relative(path, root)
        references = (
            PATH_REFERENCE_RE.findall(text)
            + TEX_GRAPHICS_RE.findall(text)
            + RESOURCE_REFERENCE_RE.findall(text)
        )
        for value in references:
            normalized = value.replace("\\", "/")
            if normalized.startswith(("http://", "https://")) or not Path(normalized).suffix:
                continue
            if not _safe_member(normalized):
                issues.append(_issue("LOCAL_REFERENCE_ESCAPES_PACKAGE", relative, normalized))
                continue
            candidates = ((path.parent / normalized).resolve(), (root / normalized).resolve())
            if not any(candidate.is_file() for candidate in candidates):
                issues.append(_issue("LOCAL_REFERENCE_MISSING", relative, normalized))
        for font in TEX_FONT_RE.findall(text):
            if font.casefold() not in fonts:
                issues.append(_issue("FONT_DEPENDENCY_UNDECLARED", relative, font))


def _validate_dependency_instructions(root: Path, manifest: dict[str, Any], issues: list[dict[str, str]]) -> None:
    dependencies = manifest.get("dependencies") if isinstance(manifest.get("dependencies"), dict) else {}
    dependency_file = str(dependencies.get("file", ""))
    install = str(dependencies.get("install", "")).strip()
    if not dependency_file or not (root / dependency_file).is_file():
        issues.append(_issue("DEPENDENCY_FILE_MISSING", "support-manifest.json", dependency_file or "not declared"))
    if not install:
        issues.append(_issue("INSTALL_INSTRUCTIONS_MISSING", "support-manifest.json", "dependencies.install is empty"))
    if dependencies.get("fonts") and not str(dependencies.get("font_installation", "")).strip():
        issues.append(_issue("FONT_INSTALL_INSTRUCTIONS_MISSING", "support-manifest.json", "dependencies.font_installation is empty"))


def _scan_tree(root: Path, identity_terms: list[str], issues: list[dict[str, str]]) -> None:
    for path in root.rglob("*"):
        relative = _relative(path, root)
        for hit in _identity_hits(relative, identity_terms):
            issues.append(_issue("IDENTITY_IN_NAME", relative, hit))
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        for hit in _identity_hits(text, identity_terms):
            issues.append(_issue("IDENTITY_OR_PATH_IN_TEXT", relative, hit))


def _scan_pdf(path: Path, root: Path, terms: list[str], issues: list[dict[str, str]]) -> None:
    if path.stat().st_size > MAX_DELIVERY_BYTES:
        issues.append(_issue("PAPER_TOO_LARGE", _relative(path, root), f"{path.stat().st_size} bytes"))
    try:
        import fitz
        document = fitz.open(path)
        metadata = json.dumps(document.metadata or {}, ensure_ascii=False)
        document.close()
    except Exception as exc:  # noqa: BLE001
        issues.append(_issue("PDF_METADATA_UNREADABLE", _relative(path, root), str(exc)))
        return
    for hit in _identity_hits(metadata, terms):
        issues.append(_issue("IDENTITY_IN_PDF_METADATA", _relative(path, root), hit))


def _scan_docx(path: Path, root: Path, terms: list[str], issues: list[dict[str, str]]) -> None:
    if path.stat().st_size > MAX_DELIVERY_BYTES:
        issues.append(_issue("PAPER_TOO_LARGE", _relative(path, root), f"{path.stat().st_size} bytes"))
    try:
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.startswith("docProps/") or name.startswith("word/") and name.endswith(".xml")]
            text = "\n".join(archive.read(name).decode("utf-8", errors="replace") for name in members)
    except (OSError, zipfile.BadZipFile) as exc:
        issues.append(_issue("DOCX_PROPERTIES_UNREADABLE", _relative(path, root), str(exc)))
        return
    for hit in _identity_hits(text, terms):
        issues.append(_issue("IDENTITY_IN_DOCX", _relative(path, root), hit))


def _validate_appendix(paper_source: Path | None, manifest_files: set[str], root: Path, issues: list[dict[str, str]]) -> None:
    if paper_source is None:
        return
    text = paper_source.read_text(encoding="utf-8")
    match = re.search(r"附录|Appendix", text, re.I)
    if not match:
        issues.append(_issue("APPENDIX_MISSING", _relative(paper_source, root), "appendix heading not found"))
        return
    appendix = text[match.start():]
    if not re.search(r"完整文件清单|complete file (?:list|inventory)", appendix, re.I):
        issues.append(_issue("APPENDIX_FILE_LIST_MISSING", _relative(paper_source, root), "complete support-file list heading not found"))
    for relative in sorted(manifest_files):
        if relative not in appendix:
            issues.append(_issue("APPENDIX_FILE_NOT_LISTED", _relative(paper_source, root), relative))
        if Path(relative).suffix.lower() in SOURCE_SUFFIXES:
            escaped = re.escape(relative).replace("/", r"[\\/]")
            full_code = re.search(rf"\\lstinputlisting(?:\[[^]]*\])?\{{{escaped}\}}", appendix, re.I)
            markdown_code = re.search(rf"(?s){escaped}.{{0,160}}```", appendix, re.I)
            if not full_code and not markdown_code:
                issues.append(_issue("APPENDIX_SOURCE_NOT_COMPLETE", _relative(paper_source, root), relative))


def _validate_ai_disclosure(
    paper_source: Path,
    manifest_files: set[str],
    root: Path,
    issues: list[dict[str, str]],
) -> dict[str, Any]:
    display_path = _relative(paper_source, root)
    if not paper_source.is_file():
        issues.append(_issue("PAPER_SOURCE_MISSING", display_path, "source is required to verify AI disclosure"))
        return {"status": "FAIL", "declaration": None, "details_file": False}
    text = paper_source.read_text(encoding="utf-8")
    text = re.sub(r"(?m)(?<!\\)%.*$", "", text)
    declaration = AI_DECLARATION_HEADING_RE.search(text)
    details_present = any(PurePosixPath(name).name == AI_DETAILS_FILENAME for name in manifest_files)
    if declaration is None:
        issues.append(_issue("AI_DECLARATION_MISSING", display_path, "place AI工具使用声明 before references"))
        return {"status": "FAIL", "declaration": None, "details_file": details_present}

    references = REFERENCES_HEADING_RE.search(text)
    if references is None:
        issues.append(_issue("AI_DECLARATION_POSITION_UNCHECKED", display_path, "references heading not found"))
        end = len(text)
    else:
        end = references.start()
        if declaration.start() > references.start():
            issues.append(_issue("AI_DECLARATION_AFTER_REFERENCES", display_path, "move declaration before references"))
    declaration_text = text[declaration.end():end] if declaration.start() < end else ""
    no_ai = bool(re.search(r"未\s*使用(?:任何)?\s*(?:生成式)?\s*AI\s*工具|did\s+not\s+use\s+any\s+AI", declaration_text, re.I))
    used_ai = bool(re.search(r"(?<!未)使用(?:了|过)?\s*(?:生成式)?\s*AI\s*工具|used\s+(?:an?\s+)?AI", declaration_text, re.I))
    if no_ai and used_ai:
        issues.append(_issue("AI_DECLARATION_CONFLICT", display_path, "both used-AI and no-AI statements were detected"))
        declaration_kind = "conflict"
    elif no_ai:
        declaration_kind = "not_used"
        if details_present:
            issues.append(_issue("AI_DECLARATION_CONFLICT", AI_DETAILS_FILENAME, "details file exists but declaration says AI was not used"))
    elif used_ai:
        declaration_kind = "used"
        if not details_present:
            issues.append(_issue("AI_USAGE_DETAILS_MISSING", "support-manifest.json", f"add exact file {AI_DETAILS_FILENAME}"))
    else:
        declaration_kind = "unclear"
        issues.append(_issue("AI_DECLARATION_UNCLEAR", display_path, "state explicitly whether AI tools were used"))

    failed_codes = {
        "AI_DECLARATION_POSITION_UNCHECKED",
        "AI_DECLARATION_AFTER_REFERENCES",
        "AI_DECLARATION_CONFLICT",
        "AI_USAGE_DETAILS_MISSING",
        "AI_DECLARATION_UNCLEAR",
    }
    failed = any(issue["code"] in failed_codes for issue in issues)
    return {
        "status": "FAIL" if failed else "PASS",
        "declaration": declaration_kind,
        "details_file": details_present,
    }


def _validate_ai_details_pdf(
    clean_root: Path,
    issues: list[dict[str, str]],
) -> dict[str, Any]:
    matches = [path for path in clean_root.rglob("*") if path.is_file() and path.name == AI_DETAILS_FILENAME]
    if len(matches) != 1:
        if len(matches) > 1:
            issues.append(_issue("AI_USAGE_DETAILS_DUPLICATED", AI_DETAILS_FILENAME, f"found {len(matches)} copies"))
        return {"status": "FAIL", "sections": {}}
    path = matches[0]
    try:
        import fitz

        document = fitz.open(path)
        text = "\n".join(page.get_text("text") for page in document)
        document.close()
    except Exception as exc:  # noqa: BLE001
        issues.append(_issue("AI_USAGE_DETAILS_INVALID", AI_DETAILS_FILENAME, f"unreadable PDF: {exc}"))
        return {"status": "FAIL", "sections": {}}
    if not text.strip():
        issues.append(_issue("AI_USAGE_DETAILS_INVALID", AI_DETAILS_FILENAME, "PDF has no extractable text"))
        return {"status": "FAIL", "sections": {}}
    required = {
        "tools_and_models": r"工具.{0,20}模型|模型.{0,20}工具|tools?.{0,30}models?",
        "purposes_and_stages": r"目的|环节|purposes?|stages?",
        "prompting_process": r"提示|交互|prompt(?:ing)?|interactions?|process",
        "adoption": r"采用|adoption|adopted",
        "manual_modification": r"人工.{0,20}修改|manual.{0,30}modification",
        "verification": r"核验|复核|verification|verified",
    }
    sections = {name: bool(re.search(pattern, text, re.I | re.S)) for name, pattern in required.items()}
    missing = [name for name, present in sections.items() if not present]
    if missing:
        issues.append(_issue("AI_USAGE_DETAILS_INCOMPLETE", AI_DETAILS_FILENAME, f"missing sections: {', '.join(missing)}"))
    return {"status": "FAIL" if missing else "PASS", "sections": sections}


def _clean_run(root: Path, manifest: dict[str, Any], issues: list[dict[str, str]]) -> dict[str, Any]:
    reproduce = manifest.get("reproduce") if isinstance(manifest.get("reproduce"), dict) else {}
    command = reproduce.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(value, str) and value for value in command):
        issues.append(_issue("REPRODUCE_COMMAND_MISSING", "support-manifest.json", "reproduce.command must be a non-empty string array"))
        return {"status": "FAIL", "exit_code": None}
    resolved_command = [sys.executable if value == "{python}" else value for value in command]
    timeout = min(max(int(reproduce.get("timeout_seconds", 120)), 1), 600)
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP"}
    }
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONPATH"] = str(root)
    try:
        result = subprocess.run(
            resolved_command,
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        issues.append(_issue("CLEAN_REPRODUCTION_FAILED", "support-package", type(exc).__name__))
        return {"status": "FAIL", "exit_code": None}
    if result.returncode:
        detail = (result.stderr or result.stdout or f"exit {result.returncode}").replace(str(root), "<clean-root>")[:1000]
        issues.append(_issue("CLEAN_REPRODUCTION_FAILED", "support-package", detail))
    return {"status": "PASS" if result.returncode == 0 else "FAIL", "exit_code": result.returncode}


def validate_submission(
    project_root: Path,
    *,
    pdf: Path | None = None,
    docx: Path | None = None,
    support_archive: Path | None = None,
    support_manifest: Path | None = None,
    paper_source: Path | None = None,
    identity_file: Path | None = None,
    identity_terms: Iterable[str] = (),
    profile: str = "competition",
) -> dict[str, Any]:
    root = project_root.resolve()
    issues: list[dict[str, str]] = []
    terms, identity_dictionary = _load_identity_terms(root, identity_file, identity_terms, issues)
    deliveries = [path for path in (pdf, docx) if path is not None]
    if profile == "competition" and not deliveries:
        issues.append(_issue("PAPER_DELIVERY_MISSING", "paper", "competition requires PDF or DOCX; PDF is the default"))
    if profile == "audit" and (pdf is None or docx is None):
        issues.append(_issue("AUDIT_FORMATS_INCOMPLETE", "paper", "audit requires both PDF and DOCX"))
    for path in deliveries:
        if not path.is_file():
            issues.append(_issue("PAPER_DELIVERY_MISSING", _relative(path, root), "file does not exist"))
            continue
        for hit in _identity_hits(path.name, terms):
            issues.append(_issue("IDENTITY_IN_NAME", _relative(path, root), hit))
        if path.suffix.lower() == ".pdf":
            _scan_pdf(path, root, terms, issues)
        elif path.suffix.lower() == ".docx":
            _scan_docx(path, root, terms, issues)

    reproduction = {"status": "FAIL", "exit_code": None}
    archive_validation = {"format": None, "backend": None, "status": "FAIL"}
    ai_disclosure = {"status": "FAIL", "declaration": None, "details_file": False}
    if paper_source is None:
        issues.append(_issue("PAPER_SOURCE_REQUIRED", "paper", "paper source is required to verify appendix and AI disclosure"))
    if support_archive is None or support_manifest is None:
        issues.append(_issue("SUPPORT_PACKAGE_MISSING", "support-package", "archive and manifest are required"))
    elif not support_archive.is_file() or not support_manifest.is_file():
        issues.append(_issue("SUPPORT_PACKAGE_MISSING", "support-package", "archive or manifest does not exist"))
    else:
        for delivery_path in (support_archive, support_manifest, paper_source):
            if delivery_path is None:
                continue
            for hit in _identity_hits(delivery_path.name, terms):
                issues.append(_issue("IDENTITY_IN_NAME", _relative(delivery_path, root), hit))
        if support_archive.stat().st_size > MAX_DELIVERY_BYTES:
            issues.append(_issue("SUPPORT_ARCHIVE_TOO_LARGE", _relative(support_archive, root), f"{support_archive.stat().st_size} bytes"))
        try:
            manifest = _load_manifest(support_manifest)
            expected = _manifest_files(manifest)
            if paper_source is not None:
                ai_disclosure = _validate_ai_disclosure(paper_source, expected, root, issues)
            members, archive, archive_validation = _archive_members(support_archive)
            actual = set(members)
            if DEFAULT_IDENTITY_FILE in {PurePosixPath(name).name for name in actual}:
                issues.append(
                    _issue(
                        "PRIVATE_IDENTITY_DICTIONARY_BUNDLED",
                        _relative(support_archive, root),
                        f"remove {DEFAULT_IDENTITY_FILE} from the support archive",
                    )
                )
            unsafe = sorted(name for name in actual if not _safe_member(name))
            if unsafe:
                issues.append(_issue("ARCHIVE_PATH_UNSAFE", _relative(support_archive, root), ", ".join(unsafe)))
            if actual != expected:
                detail = f"missing={sorted(expected - actual)} unexpected={sorted(actual - expected)}"
                issues.append(_issue("SUPPORT_MANIFEST_MISMATCH", _relative(support_archive, root), detail))
            bundled_libraries = sorted(
                name
                for name in actual
                if VENDORED_LIBRARY_PARTS.intersection(PurePosixPath(name).parts)
                or Path(name).suffix.lower() in {".dll", ".pyd", ".so", ".whl"}
            )
            if bundled_libraries:
                issues.append(
                    _issue(
                        "THIRD_PARTY_LIBRARY_BUNDLED",
                        _relative(support_archive, root),
                        ", ".join(bundled_libraries),
                    )
                )
            with tempfile.TemporaryDirectory(prefix="cumcm-support-") as temporary:
                clean_root = Path(temporary)
                if not unsafe:
                    archive.extractall(clean_root)
                    _scan_tree(clean_root, terms, issues)
                    _validate_python_imports(clean_root, manifest, issues)
                    _validate_references(clean_root, manifest, issues)
                    _validate_dependency_instructions(clean_root, manifest, issues)
                    reproduction = _clean_run(clean_root, manifest, issues)
                    if ai_disclosure.get("declaration") == "used":
                        ai_disclosure["details_content"] = _validate_ai_details_pdf(clean_root, issues)
                        if ai_disclosure["details_content"]["status"] != "PASS":
                            ai_disclosure["status"] = "FAIL"
            archive.close()
            _validate_appendix(paper_source, expected, root, issues)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
            issues.append(_issue("SUPPORT_PACKAGE_INVALID", _relative(support_archive, root), str(exc)))

    return {
        "schema_version": "1.0",
        "profile": profile,
        "status": "PASS" if not issues else "FAIL",
        "submission_ready": not issues,
        "paper_formats": sorted(path.suffix.lower().lstrip(".") for path in deliveries if path.is_file()),
        "identity_dictionary": identity_dictionary,
        "archive_validation": archive_validation,
        "clean_reproduction": reproduction,
        "ai_disclosure": ai_disclosure,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--profile", choices=("competition", "audit"), default="competition")
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--docx", type=Path)
    parser.add_argument("--support-archive", type=Path, required=True)
    parser.add_argument("--support-manifest", type=Path, required=True)
    parser.add_argument("--paper-source", type=Path)
    parser.add_argument("--identity-file", type=Path)
    parser.add_argument("--identity-term", action="append", default=[])
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    report = validate_submission(
        args.project_root,
        pdf=args.pdf,
        docx=args.docx,
        support_archive=args.support_archive,
        support_manifest=args.support_manifest,
        paper_source=args.paper_source,
        identity_file=args.identity_file,
        identity_terms=args.identity_term,
        profile=args.profile,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
