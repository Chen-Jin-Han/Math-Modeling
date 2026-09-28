from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
# ISC-licensed fixture from markokr/rarfile test/files/rar3-subdirs.rar.
RAR3_SUBDIRS = (
    "UmFyIRoHAM+QcwAADQAAAAAAAADiw3QgkDcABgAAAAYAAAADx6QEyTao9FAdMBIApIEAAHN1YlxkaXIy"
    "XGZpbGUyLnR4dACwfLUwZmlsZTIK+lF0IJA/AAgAAAAIAAAAA30kt3FIqPRQHTAaAKSBAABzdWJcd2l0"
    "aCBzcGFjZVxsb25nIGZuLnR4dADwCEdMbG9uZyBmbgojwXQgklcABQAAAAUAAAADwYnsL+Co9FAdMDIA"
    "pIEAAHN1YlzDvMi1xKnDtuG4i8OoXGZpbGUudHh0AALGAvw1KQEg9gse6FwAZmlsZQAudHh0ALByoRVm"
    "aWxlChRcdCCQNwAGAAAABgAAAAME9yniMKj0UB0wEgCkgQAAc3ViXGRpcjFcZmlsZTEudHh0APAChIVm"
    "aWxlMQrRdXTgkC0AAAAAAAAAAAADAAAAADao9FAUMAgA7UEAAHN1YlxkaXIyALB/JjP75XTgkDMAAAAA"
    "AAAAAAADAAAAAEio9FAUMA4A7UEAAHN1Ylx3aXRoIHNwYWNlAPDLG06903TgkC4AAAAAAAAAAAADAAAA"
    "ACSo9FAUMAkA7UEAAHN1YlxlbXB0eQDwcNkb8Ed04JJDAAAAAAAAAAAAAwAAAADgqPRQFDAeAO1BAABz"
    "dWJcw7zItcSpw7bhuIvDqAACxgL8NSkBIPYLHugAsDR2F89rdOCQLQAAAAAAAAAAAAMAAAAAMKj0UBQw"
    "CADtQQAAc3ViXGRpcjEA8MVYh6xSdOCQKAAAAAAAAAAAAAMAAAAA1aj0UBQwAwDtQQAAc3ViALAO1STE"
    "PXsAQAcA"
)


def _load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _pdf(path: Path, *, pages: int = 3, appendix_page: int = 3, author: str = "") -> Path:
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    for number in range(1, pages + 1):
        page = document.new_page(width=595.28, height=841.89)
        heading = "Abstract" if number == 1 else "Problem Restatement" if number == 2 else "Body"
        if number == appendix_page:
            heading = "Appendix"
        page.insert_text((72, 72), heading)
        page.insert_text((294, 810), str(number))
    document.set_metadata({"author": author})
    document.save(path)
    document.close()
    return path


def _identity_dictionary(root: Path, *, names: list[str] | None = None) -> Path:
    path = root / ".cumcm-identities.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "names": names or ["NeverMatchPerson"],
                "schools": ["NeverMatchUniversity"],
                "regions": ["NeverMatchRegion"],
                "student_ids": ["NeverMatchStudentId"],
                "windows_usernames": ["NeverMatchWindowsUser"],
                "other_terms": ["NeverMatchLaboratory"],
            }
        ),
        encoding="utf-8",
    )
    return path


def _ai_details_pdf_bytes() -> bytes:
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    page = document.new_page(width=595.28, height=841.89)
    page.insert_text(
        (72, 72),
        "Tools and Models\nPurposes and Stages\nPrompting and Interaction Process\n"
        "Adoption and Manual Modification\nManual Verification",
    )
    payload = document.tobytes()
    document.close()
    return payload


def _support_package(
    root: Path,
    *,
    main_text: str = "print('reproduced')\n",
    extra_files: dict[str, str | bytes] | None = None,
) -> tuple[Path, Path, Path]:
    _identity_dictionary(root)
    files = {"main.py": main_text, "requirements.txt": ""}
    files.update(extra_files or {})
    archive_path = root / "delivery" / "support.zip"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    manifest = {
        "files": sorted(files),
        "dependencies": {
            "file": "requirements.txt",
            "install": "python -m pip install -r requirements.txt",
        },
        "reproduce": {"command": ["{python}", "main.py"], "timeout_seconds": 30},
    }
    manifest_path = root / "delivery" / "support-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    paper = root / "paper" / "main.tex"
    paper.parent.mkdir(parents=True, exist_ok=True)
    paper.write_text(
        "\\section{AI工具使用声明}\n竞赛过程中未使用任何 AI 工具。\n"
        "\\section{参考文献}\n"
        "\\section{附录}\n\\subsection{支撑材料完整文件清单}\n"
        + "\n".join(sorted(files))
        + "\n\\lstinputlisting{main.py}\n",
        encoding="utf-8",
    )
    return archive_path, manifest_path, paper


def test_layout_pdf_accepts_30_body_pages_plus_abstract(tmp_path) -> None:
    module = _load(
        "validate_cumcm_layout_pages",
        "skills/write-model-paper/scripts/validate_cumcm_layout.py",
    )
    pdf = _pdf(tmp_path / "paper.pdf", pages=32, appendix_page=32)
    report = module.inspect_pdf(pdf, project_root=tmp_path)
    assert report["status"] == "PASS"
    assert report["pages_before_appendix"] == 31
    assert report["body_pages_before_appendix"] == 30


def test_layout_pdf_rejects_more_than_30_body_pages(tmp_path) -> None:
    module = _load(
        "validate_cumcm_layout_body_pages",
        "skills/write-model-paper/scripts/validate_cumcm_layout.py",
    )
    pdf = _pdf(tmp_path / "paper.pdf", pages=33, appendix_page=33)
    report = module.inspect_pdf(pdf, project_root=tmp_path)
    assert report["status"] == "FAIL"
    assert report["body_pages_before_appendix"] == 31
    assert any("maximum body length is 30" in error for error in report["errors"])


def test_layout_pdf_accepts_abstract_page_one_and_continuous_numbers(tmp_path) -> None:
    module = _load(
        "validate_cumcm_layout_numbering",
        "skills/write-model-paper/scripts/validate_cumcm_layout.py",
    )
    report = module.inspect_pdf(_pdf(tmp_path / "paper.pdf"), project_root=tmp_path)
    assert report["status"] == "PASS"
    assert report["abstract_page"] == 1
    assert report["page_numbers"] == [1, 2, 3]
    assert report["pdf"] == "paper.pdf"


def test_submission_rejects_oversized_paper(tmp_path) -> None:
    module = _load(
        "submission_preflight_size",
        "skills/review-model-paper/scripts/submission_preflight.py",
    )
    pdf = _pdf(tmp_path / "paper.pdf")
    with pdf.open("r+b") as stream:
        stream.seek(module.MAX_DELIVERY_BYTES)
        stream.write(b"x")
    archive, manifest, paper = _support_package(tmp_path)
    report = module.validate_submission(
        tmp_path,
        pdf=pdf,
        support_archive=archive,
        support_manifest=manifest,
        paper_source=paper,
    )
    assert report["status"] == "FAIL"
    assert any(issue["code"] == "PAPER_TOO_LARGE" for issue in report["issues"])


def test_submission_rejects_pdf_metadata_identity(tmp_path) -> None:
    module = _load(
        "submission_preflight_identity",
        "skills/review-model-paper/scripts/submission_preflight.py",
    )
    archive, manifest, paper = _support_package(tmp_path)
    _identity_dictionary(tmp_path, names=["Alice"])
    report = module.validate_submission(
        tmp_path,
        pdf=_pdf(tmp_path / "paper.pdf", author="Contestant Alice"),
        support_archive=archive,
        support_manifest=manifest,
        paper_source=paper,
    )
    assert report["submission_ready"] is False
    assert any(issue["code"] == "IDENTITY_IN_PDF_METADATA" for issue in report["issues"])


def test_submission_rejects_docx_properties_identity(tmp_path) -> None:
    module = _load(
        "submission_preflight_docx_identity",
        "skills/review-model-paper/scripts/submission_preflight.py",
    )
    docx = tmp_path / "paper.docx"
    with zipfile.ZipFile(docx, "w") as archive:
        archive.writestr("docProps/core.xml", "<dc:creator>Contestant Alice</dc:creator>")
        archive.writestr("word/document.xml", "<w:document/>")
    archive, manifest, paper = _support_package(tmp_path)
    _identity_dictionary(tmp_path, names=["Alice"])
    report = module.validate_submission(
        tmp_path,
        docx=docx,
        support_archive=archive,
        support_manifest=manifest,
        paper_source=paper,
    )
    assert any(issue["code"] == "IDENTITY_IN_DOCX" for issue in report["issues"])


def test_submission_allows_generic_identity_scan_without_private_dictionary(tmp_path) -> None:
    module = _load(
        "submission_preflight_identity_dictionary",
        "skills/review-model-paper/scripts/submission_preflight.py",
    )
    archive, manifest, paper = _support_package(tmp_path)
    (tmp_path / ".cumcm-identities.json").unlink()

    report = module.validate_submission(
        tmp_path,
        pdf=_pdf(tmp_path / "paper.pdf"),
        support_archive=archive,
        support_manifest=manifest,
        paper_source=paper,
    )

    assert report["submission_ready"] is True
    assert report["identity_dictionary"]["status"] == "NOT_RUN"
    assert not any(issue["code"] == "IDENTITY_DICTIONARY_MISSING" for issue in report["issues"])


def test_submission_rejects_explicit_missing_identity_dictionary(tmp_path) -> None:
    module = _load(
        "submission_preflight_explicit_missing_identity_dictionary",
        "skills/review-model-paper/scripts/submission_preflight.py",
    )
    archive, manifest, paper = _support_package(tmp_path)
    private_dictionary = tmp_path / "private" / "identities.json"

    report = module.validate_submission(
        tmp_path,
        pdf=_pdf(tmp_path / "paper.pdf"),
        support_archive=archive,
        support_manifest=manifest,
        paper_source=paper,
        identity_file=private_dictionary,
    )

    assert report["submission_ready"] is False
    assert report["identity_dictionary"]["status"] == "FAIL"
    assert any(issue["code"] == "IDENTITY_DICTIONARY_MISSING" for issue in report["issues"])


def test_real_rar_archive_uses_available_extraction_backend(tmp_path) -> None:
    module = _load(
        "submission_preflight_rar_backend",
        "skills/review-model-paper/scripts/submission_preflight.py",
    )
    rar_path = tmp_path / "official-rarfile-fixture.rar"
    rar_path.write_bytes(base64.b64decode(RAR3_SUBDIRS))

    members, archive, validation = module._archive_members(rar_path)
    extracted = tmp_path / "extracted"
    try:
        archive.extractall(extracted)
    finally:
        archive.close()

    assert validation["format"] == "rar"
    assert validation["status"] == "PASS"
    assert validation["backend"] in {"unrar", "unar", "bsdtar", "sevenzip", "sevenzip2"}
    assert "sub/dir1/file1.txt" in members
    assert (extracted / "sub" / "dir1" / "file1.txt").read_text() == "file1\n"


def _is_machine_path(value: str) -> bool:
    """Detect absolute paths from either platform, including Windows drive paths.

    Kept platform-independent so the assertion below stays meaningful when the
    suite runs on a machine whose home directory differs from the developer's.
    """
    normalised = value.replace("\\", "/")
    return (
        Path(value).is_absolute()
        or normalised.startswith("/")
        or (len(normalised) > 1 and normalised[1] == ":")
    )


def test_submission_rejects_absolute_path_in_delivery_text(tmp_path) -> None:
    module = _load(
        "submission_preflight_absolute_path",
        "skills/review-model-paper/scripts/submission_preflight.py",
    )
    archive, manifest, paper = _support_package(
        tmp_path,
        extra_files={"results.json": '{"source": "C:\\\\Users\\\\Contestant\\\\data.csv"}'},
    )
    report = module.validate_submission(
        tmp_path,
        pdf=_pdf(tmp_path / "paper.pdf"),
        support_archive=archive,
        support_manifest=manifest,
        paper_source=paper,
    )
    assert any(issue["code"] == "IDENTITY_OR_PATH_IN_TEXT" for issue in report["issues"])
    assert all(not _is_machine_path(issue["path"]) for issue in report["issues"])


def test_support_package_missing_local_dependency_fails(tmp_path) -> None:
    module = _load(
        "submission_preflight_imports",
        "skills/review-model-paper/scripts/submission_preflight.py",
    )
    archive, manifest, paper = _support_package(tmp_path, main_text="import missing_local\n")
    report = module.validate_submission(
        tmp_path,
        pdf=_pdf(tmp_path / "paper.pdf"),
        support_archive=archive,
        support_manifest=manifest,
        paper_source=paper,
    )
    codes = {issue["code"] for issue in report["issues"]}
    assert "IMPORT_NOT_PROVIDED" in codes
    assert "CLEAN_REPRODUCTION_FAILED" in codes


def test_support_manifest_must_match_archive_exactly(tmp_path) -> None:
    module = _load(
        "submission_preflight_manifest",
        "skills/review-model-paper/scripts/submission_preflight.py",
    )
    archive, manifest, paper = _support_package(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["files"].append("missing.csv")
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    report = module.validate_submission(
        tmp_path,
        pdf=_pdf(tmp_path / "paper.pdf"),
        support_archive=archive,
        support_manifest=manifest,
        paper_source=paper,
    )
    assert any(issue["code"] == "SUPPORT_MANIFEST_MISMATCH" for issue in report["issues"])


def test_oversized_support_archive_fails(tmp_path) -> None:
    module = _load(
        "submission_preflight_archive_size",
        "skills/review-model-paper/scripts/submission_preflight.py",
    )
    archive, manifest, paper = _support_package(
        tmp_path,
        extra_files={"large.bin": "x" * (module.MAX_DELIVERY_BYTES + 1)},
    )
    report = module.validate_submission(
        tmp_path,
        pdf=_pdf(tmp_path / "paper.pdf"),
        support_archive=archive,
        support_manifest=manifest,
        paper_source=paper,
    )
    assert any(issue["code"] == "SUPPORT_ARCHIVE_TOO_LARGE" for issue in report["issues"])


def test_minimal_clean_directory_reproduction_passes(tmp_path) -> None:
    module = _load(
        "submission_preflight_clean",
        "skills/review-model-paper/scripts/submission_preflight.py",
    )
    archive, manifest, paper = _support_package(tmp_path)
    report = module.validate_submission(
        tmp_path,
        pdf=_pdf(tmp_path / "paper.pdf"),
        support_archive=archive,
        support_manifest=manifest,
        paper_source=paper,
    )
    assert report["status"] == "PASS"
    assert report["clean_reproduction"]["status"] == "PASS"
    assert report["ai_disclosure"]["declaration"] == "not_used"


def test_ai_use_requires_exact_details_pdf_in_support_package(tmp_path) -> None:
    module = _load(
        "submission_preflight_ai_missing",
        "skills/review-model-paper/scripts/submission_preflight.py",
    )
    archive, manifest, paper = _support_package(tmp_path)
    text = paper.read_text(encoding="utf-8").replace(
        "竞赛过程中未使用任何 AI 工具。",
        "竞赛过程中使用了 AI 工具，用于代码调试，所有采用内容均已人工核验。",
    )
    paper.write_text(text, encoding="utf-8")
    report = module.validate_submission(
        tmp_path,
        pdf=_pdf(tmp_path / "paper.pdf"),
        support_archive=archive,
        support_manifest=manifest,
        paper_source=paper,
    )
    assert any(issue["code"] == "AI_USAGE_DETAILS_MISSING" for issue in report["issues"])


def test_ai_use_with_exact_details_pdf_passes(tmp_path) -> None:
    module = _load(
        "submission_preflight_ai_present",
        "skills/review-model-paper/scripts/submission_preflight.py",
    )
    archive, manifest, paper = _support_package(
        tmp_path,
        extra_files={"AI工具使用详情.pdf": _ai_details_pdf_bytes()},
    )
    text = paper.read_text(encoding="utf-8").replace(
        "竞赛过程中未使用任何 AI 工具。",
        "竞赛过程中使用了 AI 工具，用于代码调试，所有采用内容均已人工核验。",
    )
    paper.write_text(text, encoding="utf-8")
    report = module.validate_submission(
        tmp_path,
        pdf=_pdf(tmp_path / "paper.pdf"),
        support_archive=archive,
        support_manifest=manifest,
        paper_source=paper,
    )
    assert report["status"] == "PASS"
    assert report["ai_disclosure"]["status"] == "PASS"
    assert report["ai_disclosure"]["declaration"] == "used"
    assert report["ai_disclosure"]["details_file"] is True
    assert report["ai_disclosure"]["details_content"]["status"] == "PASS"


def test_csv_profile_report_uses_relative_not_user_path(tmp_path) -> None:
    source = tmp_path / "sample.csv"
    output = tmp_path / "profile.json"
    source.write_text("x\n1\n", encoding="utf-8")
    script = ROOT / "skills" / "analyze-model-data" / "scripts" / "profile_csv.py"
    result = subprocess.run(
        [sys.executable, str(script), str(source), "--output", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert Path(report["file"]).name == "sample.csv"
    assert not Path(report["file"]).is_absolute()
    assert ":\\" not in report["file"]
