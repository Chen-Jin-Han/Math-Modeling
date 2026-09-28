"""Render registered figures for all four questions of CUMCM 2021C."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT / "code") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "code"))

from algorithms.sci_figures import FigureContract, export_publication_figure, publication_size


FIGURE_SOURCES = {
    "fig_q1_score_curve": "results/supplier_ranking.csv",
    "fig_q1_top50_scatter": "results/top50_suppliers.csv",
    "fig_q2_weekly_received": "results/q2_weekly_plan.csv",
    "fig_q2_inventory_balance": "results/q2_weekly_plan.csv",
    "fig_q2_material_mix": "results/q2_material_mix.csv",
    "fig_carrier_loss": "results/carrier_loss_summary.csv",
    "fig_q3_material_mix": "results/q3_material_mix.csv",
    "fig_q3_carrier_allocation": "results/transport_plan_24weeks.csv",
    "fig_q3_tradeoff": "results/q3_tradeoff.csv",
    "fig_q4_capacity": "results/q4_weekly_plan.csv",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(fig, path: Path) -> None:
    source = FIGURE_SOURCES[path.name]
    role = "model-comparison" if "tradeoff" in path.name else "model-result"
    fig.set_size_inches(*publication_size("double", height_mm=82), forward=True)
    fig.tight_layout()
    export_publication_figure(
        fig,
        path,
        FigureContract(
            claim=f"{path.name} visualizes a registered result without introducing new values",
            evidence=(path.name,),
            source_paths=(source,),
            column="double",
            figure_role=role,
            n_definition="rows in the registered source table",
        ),
        dpi=450,
        strict=True,
        close=True,
    )


def main(root: Path) -> None:
    results, figures, paper = root / "results", root / "figures", root / "paper"
    figures.mkdir(exist_ok=True)
    paper.mkdir(exist_ok=True)
    ranking = pd.read_csv(results / "supplier_ranking.csv")
    q2 = pd.read_csv(results / "q2_weekly_plan.csv")
    q4 = pd.read_csv(results / "q4_weekly_plan.csv")
    tradeoff = pd.read_csv(results / "q3_tradeoff.csv")
    carrier = pd.read_csv(results / "carrier_loss_summary.csv")
    q2mix, q3mix, q4mix = (pd.read_csv(results / f"{name}_material_mix.csv") for name in ("q2", "q3", "q4"))
    routes = pd.read_csv(results / "transport_plan_24weeks.csv")
    specs: list[tuple[str, str, str, int]] = []

    fig, ax = plt.subplots(figsize=(7.2, 3.8)); ax.plot(ranking["rank"], ranking["score"], lw=1.1); ax.set(xlabel="rank", ylabel="importance score", title="Supplier importance score curve"); path=figures/"fig_q1_score_curve"; save(fig,path); specs.append(("FIG_Q1_SCORE",path.name,"results/supplier_ranking.csv",len(ranking)))
    top = ranking.head(50); fig, ax = plt.subplots(figsize=(7.2, 3.8)); ax.scatter(top["planning_product"], top["active_rate"], c=top["score"], cmap="viridis", s=25); ax.set(xlabel="planning product-equivalent capacity", ylabel="active rate", title="Top-50 supplier capacity and activity"); path=figures/"fig_q1_top50_scatter"; save(fig,path); specs.append(("FIG_Q1_TOP50",path.name,"results/top50_suppliers.csv",50))
    fig, ax = plt.subplots(figsize=(7.2, 3.8)); ax.plot(q2.week, q2.product_equiv_received, marker="o", ms=2); ax.axhline(28200, color="tab:red", ls="--", label="weekly demand"); ax.set(xlabel="week", ylabel="received product-equivalent", title="Q2 weekly received material"); ax.legend(); path=figures/"fig_q2_weekly_received"; save(fig,path); specs.append(("FIG_Q2_RECEIVED",path.name,"results/q2_weekly_plan.csv",len(q2)))
    fig, ax = plt.subplots(figsize=(7.2, 3.8)); ax.plot(q2.week, q2.inventory_end_product, marker="o", ms=2, label="ending inventory"); ax.axhline(q2.inventory_floor_product.iloc[0], color="tab:red", ls="--", label="safety floor"); ax.set(xlabel="week", ylabel="product-equivalent inventory", title="Q2 inventory balance under planning scenario"); ax.legend(); path=figures/"fig_q2_inventory_balance"; save(fig,path); specs.append(("FIG_Q2_INVENTORY",path.name,"results/q2_weekly_plan.csv",len(q2)))
    fig, ax = plt.subplots(figsize=(5.8, 3.8)); ax.bar(q2mix.material, q2mix.share, color=["#4C78A8", "#F58518", "#54A24B"]); ax.set(ylim=(0,1), xlabel="material", ylabel="share", title="Q2 economic material mix"); path=figures/"fig_q2_material_mix"; save(fig,path); specs.append(("FIG_Q2_MIX",path.name,"results/q2_material_mix.csv",len(q2mix)))
    fig, ax = plt.subplots(figsize=(7.2, 3.8)); ax.bar(carrier.carrier_id, carrier.mean_loss_rate * 100); ax.set(xlabel="carrier", ylabel="mean loss rate (%)", title="Historical carrier loss rates"); path=figures/"fig_carrier_loss"; save(fig,path); specs.append(("FIG_CARRIER_LOSS",path.name,"results/carrier_loss_summary.csv",len(carrier)))
    fig, ax = plt.subplots(figsize=(5.8, 3.8)); ax.bar(q3mix.material, q3mix.share, color=["#4C78A8", "#F58518", "#54A24B"]); ax.set(ylim=(0,1), xlabel="material", ylabel="share", title="Q3 A-priority material mix"); path=figures/"fig_q3_material_mix"; save(fig,path); specs.append(("FIG_Q3_MIX",path.name,"results/q3_material_mix.csv",len(q3mix)))
    q3route = routes[routes.scenario == "q3"].groupby("carrier_id", as_index=False).raw_shipped.sum(); fig, ax = plt.subplots(figsize=(7.2, 3.8)); ax.bar(q3route.carrier_id, q3route.raw_shipped / 24); ax.axhline(6000, color="tab:red", ls="--", label="capacity"); ax.set(xlabel="carrier", ylabel="mean weekly raw shipment", title="Q3 carrier allocation"); ax.legend(); path=figures/"fig_q3_carrier_allocation"; save(fig,path); specs.append(("FIG_Q3_ROUTE",path.name,"results/transport_plan_24weeks.csv",len(q3route)))
    fig, ax = plt.subplots(figsize=(6.2, 3.9)); scatter=ax.scatter(tradeoff.cost_index, tradeoff.a_share, c=tradeoff.c_share, cmap="viridis", s=90); [ax.annotate(str(r.policy), (r.cost_index, r.a_share), xytext=(5, 5), textcoords="offset points") for r in tradeoff.itertuples()]; ax.set(xlabel="relative procurement cost index", ylabel="A-material share", title="Q3 lexicographic trade-off evidence"); fig.colorbar(scatter, ax=ax, label="C-material share"); path=figures/"fig_q3_tradeoff"; save(fig,path); specs.append(("FIG_Q3_TRADEOFF",path.name,"results/q3_tradeoff.csv",len(tradeoff)))
    fig, ax = plt.subplots(figsize=(7.2, 3.8)); ax.plot(q4.week, q4.product_equiv_received, marker="o", ms=2); ax.axhline(28200, color="tab:red", ls="--", label="baseline capacity"); ax.set(xlabel="week", ylabel="received product-equivalent", title="Q4 technical-upgrade capacity plan"); ax.legend(); path=figures/"fig_q4_capacity"; save(fig,path); specs.append(("FIG_Q4_CAPACITY",path.name,"results/q4_weekly_plan.csv",len(q4)))
    entries=[]
    audit_records=[]
    for fid, name, data_file, sample_size in specs:
        pdf_path = figures / name
        pdf_path = pdf_path.with_suffix(".pdf")
        metadata_path = (figures / name).with_suffix(".figure.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        data_sha256 = sha(root / data_file)
        metadata["source_data"] = {"path": data_file, "sha256": data_sha256}
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        audit_records.append({"figure_id": fid, "metadata": str(metadata_path.relative_to(root)).replace("\\", "/"), **metadata["audit"]})
        entries.append({"figure_id": fid, "path": str(pdf_path.relative_to(root)).replace("\\", "/"), "metadata": str(metadata_path.relative_to(root)).replace("\\", "/"), "data_file": data_file, "data_sha256": data_sha256, "claim_ids": [], "unit": "m3 or proportion", "title": fid, "sample_size": sample_size, "inserted_in_body": True, "sha256": sha(pdf_path)})
    (paper / "figure-registry.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "reports" / "figure_audit_report.json").parent.mkdir(exist_ok=True)
    passed = all(record["passed"] for record in audit_records)
    (root / "reports" / "figure_audit_report.json").write_text(json.dumps({"status": "PASS" if passed else "FAIL", "figure_count": len(entries), "format": "pdf/svg/png at 450 dpi", "audits": audit_records}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    if not passed:
        raise RuntimeError("one or more publication figure audits failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, required=True)
    main(parser.parse_args().root)
