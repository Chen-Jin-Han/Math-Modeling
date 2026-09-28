"""Evidence-gated review for Markdown mathematical-modeling papers.

This module deliberately returns a failing review when a formal-paper claim cannot be
verified.  It is not a prose-quality scorer and it never manufactures a score.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .modeling_contracts import validate_contract_artifacts


GATES = ("structure", "mathematics", "figures_tables", "evidence", "validation", "citations")
COMPETITION_SECTIONS = (
    "摘要", "关键词", "问题重述", "问题分析", "模型总体框架", "模型假设", "符号说明",
    "数据预处理", "模型评价", "最终建议", "参考文献", "附录", "复现说明",
)
NUMERIC_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?\d+(?:\.\d+)?(?:%|万元|元|分钟|小时|kW)?")
FORMULA_RE = re.compile(r"(?:^|\n)\s*\(?\d+\)?\s*\$\$|\$\$.*?\$\$|\\tag\{\d+\}", re.S)
CLAIM_RE = re.compile(r"\[claim:([A-Za-z0-9_-]+)\]")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
TABLE_RE = re.compile(r"(?m)^\|.+\|\s*$\n^\|\s*:?-{3,}")
DEFAULT_MINIMUMS = {
    "minimum_body_characters": 9_000,
    "minimum_equations": 10,
    "minimum_figures": 8,
    "minimum_tables": 6,
    "minimum_references": 8,
}


@dataclass
class Issue:
    gate: str
    code: str
    message: str
    severity: str = "blocking"


@dataclass
class ReadinessReview:
    paper_mode: str
    gates: dict[str, bool] = field(default_factory=lambda: {gate: True for gate in GATES})
    issues: list[Issue] = field(default_factory=list)
    unsupported_claims: list[str] = field(default_factory=list)
    missing_figures: list[str] = field(default_factory=list)
    missing_tables: list[str] = field(default_factory=list)
    stale_evidence: list[str] = field(default_factory=list)
    return_to_stage: list[str] = field(default_factory=list)

    def fail(self, gate: str, code: str, message: str, stage: str | None = None) -> None:
        self.gates[gate] = False
        self.issues.append(Issue(gate, code, message))
        if stage and stage not in self.return_to_stage:
            self.return_to_stage.append(stage)

    @property
    def overall_status(self) -> str:
        return "PASS" if all(self.gates.values()) else "FAIL"

    def as_dict(self) -> dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "paper_mode": self.paper_mode,
            "gates": self.gates,
            "blocking_issues": [issue.__dict__ for issue in self.issues if issue.severity == "blocking"],
            "warning_issues": [issue.__dict__ for issue in self.issues if issue.severity != "blocking"],
            "unsupported_claims": self.unsupported_claims,
            "missing_figures": self.missing_figures,
            "missing_tables": self.missing_tables,
            "stale_evidence": self.stale_evidence,
            "return_to_stage": self.return_to_stage,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path, review: ReadinessReview, gate: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        review.fail(gate, "invalid_json", f"无法读取 {path.name}: {exc}")
        return None


def _pointer(data: Any, pointer: str) -> Any:
    if pointer in ("", "/"):
        return data
    value = data
    for token in pointer.lstrip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def _index_by_id(value: Any, key: str) -> dict[str, dict[str, Any]]:
    rows = value if isinstance(value, list) else value.get(key, []) if isinstance(value, dict) else []
    return {str(row.get(key)): row for row in rows if isinstance(row, dict) and row.get(key)}


def _paper_minimums(spec_path: Path) -> dict[str, int]:
    """Read optional integer readiness thresholds while preserving safe defaults."""
    minimums = dict(DEFAULT_MINIMUMS)
    if not spec_path.is_file():
        return minimums
    text = spec_path.read_text(encoding="utf-8")
    for key in minimums:
        match = re.search(rf"(?m)^\s*{re.escape(key)}\s*:\s*(\d+)\s*$", text)
        if match:
            minimums[key] = int(match.group(1))
    return minimums


def review_paper(project_root: str | Path, paper_path: str | Path, *, mode: str = "competition_paper",
                 paper_spec: str | Path | None = None) -> ReadinessReview:
    """Review a paper against registries rooted at *project_root*.

    Formal papers require machine-verifiable contracts.  Teaching examples retain the
    same traceability rules but use lower presentation thresholds.
    """
    root, paper = Path(project_root), Path(paper_path)
    review = ReadinessReview(mode)
    if not paper.is_file():
        review.fail("structure", "paper_missing", f"论文不存在: {paper}")
        return review
    text = paper.read_text(encoding="utf-8")
    headings = re.findall(r"(?m)^#{1,3}\s+(.+)$", text)
    spec_path = Path(paper_spec) if paper_spec else paper.parent / "paper-spec.yaml"
    minimums = _paper_minimums(spec_path)
    if mode == "competition_paper":
        if len(text) < minimums["minimum_body_characters"]:
            review.fail("structure", "paper_too_short", f"competition_paper 正文仅 {len(text)} 字符，需要至少 {minimums['minimum_body_characters']}", "writing")
        for section in COMPETITION_SECTIONS:
            if not any(section in heading for heading in headings):
                review.fail("structure", "missing_section", f"缺少必要章节：{section}", "writing")
        formulas = len(FORMULA_RE.findall(text))
        if formulas < minimums["minimum_equations"]:
            review.fail("mathematics", "insufficient_equations", f"编号/展示公式仅 {formulas} 个，需要至少 {minimums['minimum_equations']} 个", "modeling")
        if "目标函数" not in text or "约束" not in text:
            review.fail("mathematics", "optimization_incomplete", "未同时展示目标函数和约束", "modeling")
    elif mode == "teaching_example":
        if len(FORMULA_RE.findall(text)) < 1:
            review.fail("mathematics", "missing_equation", "教学示例缺少主要公式", "modeling")
        if not IMAGE_RE.findall(text) or not TABLE_RE.findall(text):
            review.fail("figures_tables", "teaching_visual_incomplete", "教学示例必须包含图和表", "writing")

    registry_dir = spec_path.parent
    if mode == "competition_paper" and not spec_path.is_file():
        review.fail("evidence", "paper_spec_missing", f"缺少结构化契约：{spec_path.name}", "writing")
    required = {"evidence-index.json", "claim-registry.json", "figure-registry.json", "table-registry.json", "formula-registry.json"}
    registries = {name: registry_dir / name for name in required}
    for name, path in registries.items():
        if not path.is_file() and mode == "competition_paper":
            review.fail("evidence", "registry_missing", f"缺少注册表：{name}", "writing")
    evidence = _load_json(registries["evidence-index.json"], review, "evidence") if registries["evidence-index.json"].is_file() else []
    claims = _load_json(registries["claim-registry.json"], review, "evidence") if registries["claim-registry.json"].is_file() else []
    figures = _load_json(registries["figure-registry.json"], review, "figures_tables") if registries["figure-registry.json"].is_file() else []
    tables = _load_json(registries["table-registry.json"], review, "figures_tables") if registries["table-registry.json"].is_file() else []
    formulas_registry = _load_json(registries["formula-registry.json"], review, "mathematics") if registries["formula-registry.json"].is_file() else []
    evidence_by_id = _index_by_id(evidence, "evidence_id")
    claim_by_id = _index_by_id(claims, "claim_id")
    decision_path = root / "results" / "decision_contract.json"
    if decision_path.is_file():
        decision_contract = _load_json(decision_path, review, "evidence")
        if isinstance(decision_contract, dict):
            for issue in validate_contract_artifacts(decision_contract, root):
                review.fail("evidence", issue["id"], issue["message"], "modeling")
    for evidence_id, item in evidence_by_id.items():
        path = root / str(item.get("path", ""))
        if not path.is_file() or item.get("sha256") != _sha256(path):
            review.stale_evidence.append(evidence_id)
            review.fail("evidence", "stale_evidence", f"证据 {evidence_id} 缺失或哈希不匹配", "validation")
    used_claims = set(CLAIM_RE.findall(text))
    for claim_id in used_claims:
        claim = claim_by_id.get(claim_id)
        if not claim:
            review.unsupported_claims.append(claim_id)
            review.fail("evidence", "claim_not_registered", f"论文引用未登记 claim：{claim_id}", "writing")
            continue
        source = evidence_by_id.get(str(claim.get("evidence_id")))
        if not source:
            review.unsupported_claims.append(claim_id)
            review.fail("evidence", "claim_no_evidence", f"{claim_id} 没有证据条目", "validation")
            continue
        try:
            source_data = _load_json(root / source["path"], review, "evidence")
            value = _pointer(source_data, str(claim.get("json_pointer", "")))
            if value is None:
                raise KeyError("null value")
            if isinstance(source_data, dict) and str(source_data.get("status", "")).lower() == "infeasible" and re.search(r"最优|optimal", text, re.I):
                review.fail("validation", "invalid_solver_claim", "求解结果为 infeasible，论文却声称最优", "modeling")
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            review.unsupported_claims.append(claim_id)
            review.fail("evidence", "claim_pointer_invalid", f"{claim_id} 的 JSON pointer 无法解析：{exc}", "validation")
    if mode == "competition_paper" and not used_claims:
        review.fail("evidence", "no_claim_bindings", "正式论文没有 [claim:ID] 数字证据绑定", "writing")
    for item in _index_by_id(figures, "figure_id").values():
        path = root / str(item.get("path", ""))
        if not path.is_file() or path.name not in text or not item.get("inserted_in_body"):
            label = str(item.get("figure_id"))
            review.missing_figures.append(label)
            review.fail("figures_tables", "figure_not_inserted", f"图 {label} 未实际插入正文或文件缺失", "writing")
            continue
        if item.get("sha256") is not None and item.get("sha256") != _sha256(path):
            review.fail(
                "figures_tables",
                "figure_hash_mismatch",
                f"图 {item.get('figure_id')} 与注册哈希不一致",
                "validation",
            )
        if item.get("data_file") is not None or item.get("data_sha256") is not None:
            data_path = root / str(item.get("data_file", ""))
            if not data_path.is_file() or item.get("data_sha256") != _sha256(data_path):
                review.fail(
                    "figures_tables",
                    "figure_source_hash_mismatch",
                    f"图 {item.get('figure_id')} 的源数据缺失或已经改变",
                    "validation",
                )
    for image in IMAGE_RE.findall(text):
        if not (paper.parent / image).is_file() and not (root / image).is_file():
            review.fail("figures_tables", "image_missing", f"正文引用图片不存在：{image}", "writing")
    for item in _index_by_id(tables, "table_id").values():
        if not item.get("inserted_in_body") or str(item.get("table_id")) not in text:
            label = str(item.get("table_id"))
            review.missing_tables.append(label)
            review.fail("figures_tables", "table_not_inserted", f"表 {label} 未实际插入正文", "writing")
    if mode == "competition_paper":
        if len(_index_by_id(figures, "figure_id")) < minimums["minimum_figures"]:
            review.fail("figures_tables", "insufficient_figure_registry", f"图注册表少于 {minimums['minimum_figures']} 条", "writing")
        if len(_index_by_id(tables, "table_id")) < minimums["minimum_tables"]:
            review.fail("figures_tables", "insufficient_table_registry", f"表注册表少于 {minimums['minimum_tables']} 条", "writing")
        if len(IMAGE_RE.findall(text)) < minimums["minimum_figures"]:
            review.fail("figures_tables", "insufficient_figures", f"正文图片少于 {minimums['minimum_figures']} 张", "writing")
        if len(TABLE_RE.findall(text)) < minimums["minimum_tables"]:
            review.fail("figures_tables", "insufficient_tables", f"正文 Markdown 表少于 {minimums['minimum_tables']} 张", "writing")
        if not isinstance(formulas_registry, list) or sum(bool(x.get("inserted_in_body")) for x in formulas_registry if isinstance(x, dict)) < minimums["minimum_equations"]:
            review.fail("mathematics", "formula_registry_incomplete", f"公式注册表未登记至少 {minimums['minimum_equations']} 个已插入公式", "writing")
    if "infeasible" in text.lower() and re.search(r"最优|optimal", text, re.I):
        review.fail("validation", "invalid_solver_claim", "论文同时声称 infeasible 和最优", "modeling")
    validation_text = root / "results" / "simulation_metrics.json"
    temporal_validation_text = root / "results" / "bootstrap_metrics.json"
    if mode == "competition_paper":
        data = _load_json(validation_text, review, "validation") if validation_text.is_file() else None
        temporal = _load_json(temporal_validation_text, review, "validation") if temporal_validation_text.is_file() else None
        has_simulation = isinstance(data, dict) and bool(data.get("seeds")) and bool(data.get("aggregate"))
        has_temporal_holdout = isinstance(temporal, dict) and isinstance(temporal.get("q2_alert_accuracy"), dict) and bool(temporal["q2_alert_accuracy"].get("ci95"))
        if not has_simulation and not has_temporal_holdout:
            review.fail("validation", "simulation_validation_missing", "正式论文需要可复核的仿真聚合结果，或时间预测任务的保留集自助法区间", "validation")
    references = text.split("参考文献", 1)[-1] if "参考文献" in text else ""
    ref_lines = [line for line in references.splitlines() if re.match(r"\s*\[\d+\]", line)]
    if mode == "competition_paper" and len(ref_lines) < minimums["minimum_references"]:
        review.fail("citations", "insufficient_citations", f"可核验参考文献少于 {minimums['minimum_references']} 条", "writing")
    if any("doi" in line.lower() and not re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", line, re.I) for line in ref_lines):
        review.fail("citations", "invalid_doi", "发现格式无效的 DOI", "writing")
    return review


def write_review_report(review: ReadinessReview, markdown_path: str | Path, json_path: str | Path) -> None:
    payload = review.as_dict()
    Path(json_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Paper Review Report", "", f"**{payload['overall_status']}** — mode: `{payload['paper_mode']}`", "", "## Gates", ""]
    lines += [f"- {gate}: {'PASS' if passed else 'FAIL'}" for gate, passed in payload["gates"].items()]
    lines += ["", "## Blocking issues", ""]
    lines += [f"- [{item['gate']}/{item['code']}] {item['message']}" for item in payload["blocking_issues"]] or ["- None"]
    if payload["return_to_stage"]:
        lines += ["", "## Return to stage", "", "- " + ", ".join(payload["return_to_stage"])]
    Path(markdown_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
