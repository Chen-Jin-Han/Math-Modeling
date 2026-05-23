from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd

import q3_strategy_optimization as q3


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "q4_outputs"
CACHE_DIR = ROOT / "internal_cache"
OUT_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)


def reset_public_output() -> None:
    """Keep final outputs limited to sensitivity ranking and data recommendations."""
    if OUT_DIR.exists():
        for p in OUT_DIR.iterdir():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    OUT_DIR.mkdir(exist_ok=True)


def elasticity_sensitivity() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    user = q3.load_features()
    user, segment_summary = q3.segment_users(user)
    strategies = q3.strategy_library()
    best_plan, _, best_summary = q3.optimize_plan(segment_summary, strategies)
    selected_ids = tuple(best_summary["selected"].split(","))
    strategies, _, _ = q3.optimize_prices_for_selected(segment_summary, strategies, selected_ids)

    base_plan, base = q3.evaluate_plan(segment_summary, strategies, selected_ids)
    variables = [
        "paid_rate",
        "arpu",
        "retention30",
        "active_days",
        "stagnation_rate",
        "resource_gap",
        "avg_diamond",
        "avg_power",
        "unique_sessions",
        "unique_campaigns",
        "ode_energy",
        "ode_drift",
    ]
    rows = []
    for var in variables:
        for direction, factor in [("down_10pct", 0.90), ("up_10pct", 1.10)]:
            seg2 = segment_summary.copy()
            if var not in seg2.columns:
                continue
            seg2[var] = seg2[var] * factor
            if var in ["paid_rate", "retention30", "stagnation_rate"]:
                seg2[var] = seg2[var].clip(0, 1)
            _, s = q3.evaluate_plan(seg2, strategies, selected_ids)
            rows.append(
                {
                    "variable": var,
                    "direction": direction,
                    "factor": factor,
                    "revenue": s["expected_revenue"],
                    "retention30": s["expected_retention30"],
                    "delta_revenue": s["expected_revenue"] - base["expected_revenue"],
                    "delta_retention": s["expected_retention30"] - base["expected_retention30"],
                    "abs_delta_revenue_pct": abs(s["expected_revenue"] - base["expected_revenue"]) / max(base["expected_revenue"], 1),
                    "abs_delta_retention_pct_point": abs(s["expected_retention30"] - base["expected_retention30"]),
                }
            )
    detail = pd.DataFrame(rows)
    rank = (
        detail.groupby("variable")
        .agg(
            mean_abs_revenue_pct=("abs_delta_revenue_pct", "mean"),
            max_abs_revenue_pct=("abs_delta_revenue_pct", "max"),
            mean_abs_retention_point=("abs_delta_retention_pct_point", "mean"),
            max_abs_retention_point=("abs_delta_retention_pct_point", "max"),
        )
        .reset_index()
    )
    rank["combined_priority_score"] = (
        0.55 * rank["mean_abs_revenue_pct"] / max(rank["mean_abs_revenue_pct"].max(), 1e-9)
        + 0.45 * rank["mean_abs_retention_point"] / max(rank["mean_abs_retention_point"].max(), 1e-9)
    )
    rank = rank.sort_values("combined_priority_score", ascending=False)
    return detail, rank, base


def build_recommendations(rank: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "priority": 1,
                "data_category": "Offer exposure-click-purchase-close funnel and price experiment data",
                "specific_fields": "strategy_id, user_id, exposure_time, trigger_reason, displayed_price, discount_tag, content_variant, impression_count, click, close, dwell_time, purchase, purchase_time, refund_flag, A/B bucket",
                "why_needed": "Q3 revenue is sensitive to paid rate, ARPU and price response. Current payment logs only show who purchased, not who saw an offer and rejected it, so true conversion and price elasticity are not identifiable.",
                "how_to_update_q3": "Estimate p_purchase(segment, price, content, trigger) from exposure denominators, replacing purchase_base and launch_salience in Q3. Use A/B buckets to estimate causal price elasticity and update S1-S8 prices/frequency.",
                "model_component": "purchase response, ARPU contribution, Monte Carlo revenue distribution",
            },
            {
                "priority": 2,
                "data_category": "Resource inventory-demand gap-building/task progress state data",
                "specific_fields": "timestamp, food/wood/stone/coin/diamond stock, required_resource_for_next_upgrade, build_queue, research_queue, troop_queue, task_id, building_id, upgrade_start/end, speedup_inventory, failed_upgrade_reason",
                "why_needed": "Q2 and Q3 show that low diamonds, resource pressure and stagnation affect next-day inactivity and retention. Current logs are mostly consumption records, so they cannot fully separate no shortage, real shortage and already-abandoned behavior.",
                "how_to_update_q3": "Construct true resource_gap=(required-stock)/required and bottleneck_type, replacing Q2 proxy scarcity. Convert S2/S5 triggers from empirical thresholds to real gap thresholds and decide whether to supply coin, wood, stone, diamonds or speedups.",
                "model_component": "retention uplift, resource relief, trigger condition, rescue package content",
            },
        ]
    )


def main() -> None:
    reset_public_output()
    detail, rank, base = elasticity_sensitivity()
    rec = build_recommendations(rank)
    detail.to_csv(CACHE_DIR / "q4_sensitivity_detail.csv", index=False, encoding="utf-8-sig")
    rank.to_csv(OUT_DIR / "q4_sensitivity_ranking.csv", index=False, encoding="utf-8-sig")
    rec.to_csv(OUT_DIR / "q4_data_collection_recommendations.csv", index=False, encoding="utf-8-sig")
    print(f"Done. Outputs written to: {OUT_DIR}")


if __name__ == "__main__":
    main()
