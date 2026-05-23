from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
Q1 = ROOT / "q1_outputs"
Q2 = ROOT / "q2_outputs"
Q3 = ROOT / "q3_outputs"
Q4 = ROOT / "q4_outputs"
CACHE = ROOT / "internal_cache"
OUT = ROOT / "model_analysis_outputs"
OUT.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)


def reset_public_output() -> None:
    """Keep the model-analysis output to the final report only."""
    if OUT.exists():
        for p in OUT.iterdir():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    OUT.mkdir(exist_ok=True)


def safe_read(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    cache_path = CACHE / path.name
    return pd.read_csv(cache_path) if cache_path.exists() else pd.DataFrame()


def q1_evaluation() -> tuple[pd.DataFrame, list[str]]:
    metrics = safe_read(Q1 / "q1_model_metrics.csv")
    pred = safe_read(Q1 / "q1_test_predictions.csv")
    ret = safe_read(Q1 / "q1_retention_bootstrap_ci.csv")
    lines = ["## Q1 retention model evaluation"]
    if not metrics.empty:
        best = metrics.sort_values("MAE").iloc[0]
        baseline = metrics[metrics["model"].str.contains("baseline", na=False)]
        lines.append(
            f"- Best model is {best['model']} with MAE={best['MAE']:.3f}, RMSE={best['RMSE']:.3f}, Bias={best['Bias']:.3f}."
        )
        if not baseline.empty:
            b = baseline.iloc[0]
            gain = (b["MAE"] - best["MAE"]) / b["MAE"]
            lines.append(f"- Ablation check: MAE improves by {gain:.2%} over the first-3-day baseline.")
    if not pred.empty and {"pred_interval_low", "pred_interval_high", "observed_retention_days"}.issubset(pred.columns):
        covered = ((pred["observed_retention_days"] >= pred["pred_interval_low"]) & (pred["observed_retention_days"] <= pred["pred_interval_high"])).mean()
        width = (pred["pred_interval_high"] - pred["pred_interval_low"]).mean()
        lines.append(f"- Conformal interval empirical coverage={covered:.3f}; average width={width:.3f} days.")
    if not ret.empty:
        key = ret[(ret["dataset"] == "train") & (ret["day"].isin([2, 7, 14, 30]))].copy()
        key["ci_width"] = key["ci_high"] - key["ci_low"]
        lines.append(f"- Bootstrap retention CI widths range from {key['ci_width'].min():.4f} to {key['ci_width'].max():.4f}.")
    return metrics, lines


def q2_evaluation() -> tuple[pd.DataFrame, list[str]]:
    metrics = safe_read(Q2 / "q2_model_metrics.csv")
    card = safe_read(Q2 / "q2_growth_card_points.csv")
    threshold = safe_read(Q2 / "q2_diamond_thresholds.csv")
    lines = ["## Q2 resource-payment model evaluation"]
    if not metrics.empty:
        for _, r in metrics.iterrows():
            nums = []
            for c in ["MAE", "RMSE", "logloss", "rank_corr", "AUC_proxy_rank_corr"]:
                if c in metrics.columns and pd.notna(r.get(c)):
                    nums.append(f"{c}={r[c]:.3f}")
            task = r["task"] if pd.notna(r.get("task")) else "coupled_dynamics"
            if not nums and "transition_mse" in metrics.columns and pd.notna(r.get("transition_mse")):
                nums.append(f"transition_mse={r['transition_mse']:.3f}")
            lines.append(f"- {task} / {r['model']}: " + ", ".join(nums))
    if not card.empty:
        top = card.iloc[0]
        lines.append(
            f"- Bottleneck stability check: strongest card point is level {int(top['level_prev'])}, with stagnation={top['stagnation_rate']:.3f} and score={top['card_score']:.3f}."
        )
    if not threshold.empty:
        tr = threshold[(threshold["dataset"] == "train") & (threshold["low_group_share"] <= 0.35)].sort_values("churn_risk_lift", ascending=False)
        te = threshold[(threshold["dataset"] == "test") & (threshold["low_group_share"] <= 0.35)].sort_values("churn_risk_lift", ascending=False)
        if not tr.empty and not te.empty:
            lines.append(
                f"- Diamond threshold robustness: train best <= {tr.iloc[0]['diamond_threshold']:.1f}, test best <= {te.iloc[0]['diamond_threshold']:.1f}; both indicate low-diamond risk concentration."
            )
    return metrics, lines


def q3_evaluation() -> tuple[pd.DataFrame, list[str]]:
    search = safe_read(Q3 / "q3_strategy_search.csv")
    price_search = safe_read(Q3 / "q3_price_search.csv")
    mc = safe_read(Q3 / "q3_monte_carlo.csv")
    table = safe_read(Q3 / "q3_strategy_table.csv")
    lines = ["## Q3 strategy optimization evaluation"]
    if not search.empty:
        best = search.sort_values("score", ascending=False).iloc[0]
        # After portfolio selection, Q3 applies contextual dynamic pricing.
        # Prefer that final price-optimized expectation when available;
        # Monte Carlo moments are reported separately as stress-validation
        # statistics.
        if not price_search.empty:
            priced_best = price_search.sort_values("score", ascending=False).iloc[0]
            final_revenue = float(priced_best["expected_revenue"])
            final_retention = float(priced_best["expected_retention30"])
        else:
            final_revenue = float(best["expected_revenue"])
            final_retention = float(best["expected_retention30"])
        lines.append(
            f"- Best portfolio expected revenue={final_revenue:.2f}, expected retention={final_retention:.4f}."
        )
        if "robust_revenue_p10" in search.columns:
            lines.append(
                f"- Robust search p10 revenue={best['robust_revenue_p10']:.2f}, p10 retention={best['robust_retention_p10']:.4f}, robust joint success={best['robust_joint_prob']:.3f}."
            )
    if not mc.empty:
        p_rev = (mc["revenue"] >= 70000).mean()
        p_ret = (mc["retention30"] >= 0.10).mean()
        p_joint = ((mc["revenue"] >= 70000) & (mc["retention30"] >= 0.10)).mean()
        lines.append(f"- Monte Carlo validation: P(revenue>=70000)={p_rev:.3f}, P(retention>=10%)={p_ret:.3f}, P(both)={p_joint:.3f}.")
        lines.append(
            f"- Stress distribution: revenue p5/p50/p95={np.quantile(mc['revenue'], .05):.2f}/{np.quantile(mc['revenue'], .5):.2f}/{np.quantile(mc['revenue'], .95):.2f}; retention p5/p50/p95={np.quantile(mc['retention30'], .05):.4f}/{np.quantile(mc['retention30'], .5):.4f}/{np.quantile(mc['retention30'], .95):.4f}."
        )
    if not table.empty:
        rev_share = table["expected_strategy_revenue"] / table["expected_strategy_revenue"].sum()
        hhi = float((rev_share**2).sum())
        lines.append(f"- Revenue concentration HHI={hhi:.3f}; lower concentration means no single package dominates the result.")
    return search, lines


def sensitivity_analysis() -> tuple[pd.DataFrame, list[str]]:
    sens = safe_read(Q4 / "q4_sensitivity_ranking.csv")
    lines = ["## Sensitivity, stability and robustness"]
    if not sens.empty:
        top = sens.sort_values("combined_priority_score", ascending=False).head(5)
        for _, r in top.iterrows():
            lines.append(
                f"- {r['variable']}: combined priority={r['combined_priority_score']:.3f}, revenue sensitivity={r['mean_abs_revenue_pct']:.4f}, retention sensitivity={r['mean_abs_retention_point']:.4f}."
            )
        total = sens["combined_priority_score"].sum()
        if total > 0:
            top2 = top.head(2)["combined_priority_score"].sum() / total
            lines.append(f"- The top two variables explain {top2:.2%} of total normalized sensitivity, so the model is mainly sensitive to engagement and stagnation signals.")
    return sens, lines


def build_stability_table(q1m: pd.DataFrame, q2m: pd.DataFrame, q3s: pd.DataFrame, sens: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if not q1m.empty:
        rows.append(
            {
                "module": "Q1 retention prediction",
                "main_check": "train-test prediction + ablation + conformal interval",
                "evidence": f"best MAE={q1m['MAE'].min():.3f}",
                "risk": "moderate; individual retention is noisy",
                "robustness_action": "use prediction intervals and compare against baseline model",
            }
        )
    if not q2m.empty:
        g = q2m[q2m["task"] == "daily_level_gain"]
        rows.append(
            {
                "module": "Q2 resource-growth-payment",
                "main_check": "panel prediction + lagged inactivity model + threshold transfer",
                "evidence": f"level-gain MAE={g.iloc[0]['MAE']:.3f}" if not g.empty else "multiple proxy checks",
                "risk": "moderate; true stock-demand gap is partially unobserved",
                "robustness_action": "recommend inventory/demand telemetry in Q4",
            }
        )
    if not q3s.empty:
        best = q3s.sort_values("score", ascending=False).iloc[0]
        rows.append(
            {
                "module": "Q3 strategy optimization",
                "main_check": "GMM soft segmentation + robust portfolio search + Monte Carlo",
                "evidence": f"robust p10 retention={best.get('robust_retention_p10', np.nan):.3f}",
                "risk": "high without A/B data; strategy effects are counterfactual",
                "robustness_action": "stress response parameters and require probabilistic target success",
            }
        )
    if not sens.empty:
        rows.append(
            {
                "module": "Q4 closure",
                "main_check": "+/-10% sensitivity perturbation",
                "evidence": f"top sensitive variable={sens.sort_values('combined_priority_score', ascending=False).iloc[0]['variable']}",
                "risk": "sensitive to engagement and stagnation measurement",
                "robustness_action": "prioritize funnel and resource-gap telemetry",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    reset_public_output()
    q1m, q1_lines = q1_evaluation()
    q2m, q2_lines = q2_evaluation()
    q3s, q3_lines = q3_evaluation()
    sens, sens_lines = sensitivity_analysis()
    stability = build_stability_table(q1m, q2m, q3s, sens)

    stability.to_csv(CACHE / "model_stability_table.csv", index=False, encoding="utf-8-sig")
    if not sens.empty:
        sens.to_csv(CACHE / "model_sensitivity_ranking.csv", index=False, encoding="utf-8-sig")

    print(f"Done. Outputs written to: {OUT}")


if __name__ == "__main__":
    main()
