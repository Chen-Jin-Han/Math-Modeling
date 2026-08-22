from __future__ import annotations

import itertools
import json
import shutil
from dataclasses import dataclass, replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
Q1_DIR = ROOT / "q1_outputs"
Q2_DIR = ROOT / "q2_outputs"
OUT_DIR = ROOT / "q3_outputs"
CACHE_DIR = ROOT / "internal_cache"
OUT_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

N_NEW_USERS = 10_000
TARGET_RETENTION = 0.10
TARGET_REVENUE = 70_000.0
DAY_MAX = 30
RNG_SEED = 20260521
EPS = 1e-9


def reset_public_output() -> None:
    """Keep final outputs limited to the required strategy and proof tables."""
    if OUT_DIR.exists():
        for p in OUT_DIR.iterdir():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    OUT_DIR.mkdir(exist_ok=True)


def read_cached_csv(name: str, public_dir: Path) -> pd.DataFrame:
    cache_path = CACHE_DIR / name
    if cache_path.exists():
        return pd.read_csv(cache_path)
    return pd.read_csv(public_dir / name)


@dataclass(frozen=True)
class Strategy:
    strategy_id: str
    day: int
    trigger: str
    target_rule: str
    audience: str
    content: str
    price: float
    purchase_base: float
    retention_uplift: float
    irritation: float
    resource_relief: float
    arpu_weight: float


def load_features() -> pd.DataFrame:
    q1_train = read_cached_csv("q1_train_user_features.csv", Q1_DIR)
    q1_test = read_cached_csv("q1_test_user_features.csv", Q1_DIR)
    q2_train = read_cached_csv("q2_train_user_features.csv", Q2_DIR)
    q2_test = read_cached_csv("q2_test_user_features.csv", Q2_DIR)
    q1 = pd.concat([q1_train, q1_test], ignore_index=True)
    q2 = pd.concat([q2_train, q2_test], ignore_index=True)
    q1["account_id"] = q1["account_id"].astype(np.int64)
    q2["account_id"] = q2["account_id"].astype(np.int64)
    cols_q1 = [
        "account_id",
        "target_retention_days",
        "is_30d_retained",
        "event_count_1_3",
        "active_days_1_3",
        "level_1_3_max",
        "level_speed_1_3",
        "total_pay_1_3",
        "diamond_1_3_max",
        "power_1_3_max",
        "sessions_1_3",
        "devices_1_3",
        "campaigns_1_3",
        "drug_1_3_max",
        "bullet_1_3_max",
        "wine_1_3_max",
        "is_paid_1_3",
    ]
    q1 = q1[[c for c in cols_q1 if c in q1.columns]]
    user = q2.merge(q1, on="account_id", how="left")
    ode_train_path = CACHE_DIR / "q1_v2_train_ode_features.csv"
    ode_test_path = CACHE_DIR / "q1_v2_test_ode_features.csv"
    ode_train = pd.read_csv(ode_train_path) if ode_train_path.exists() else pd.DataFrame()
    ode_test = pd.read_csv(ode_test_path) if ode_test_path.exists() else pd.DataFrame()
    if not ode_train.empty and not ode_test.empty:
        ode = pd.concat([ode_train, ode_test], ignore_index=True)
        ode_cols = [c for c in ["ode_energy_mean", "ode_speed_mean", "ode_terminal_drift", "ode_pressure_max_1_30"] if c in ode.columns]
        for c in ode_cols:
            user[c] = ode[c].to_numpy()[: len(user)]
    user = user.replace([np.inf, -np.inf], 0).fillna(0)
    return user


def standardize(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd < EPS] = 1.0
    return (X - mu) / sd, mu, sd


def kmeans(X: np.ndarray, k: int = 5, seed: int = RNG_SEED, max_iter: int = 200) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    Xs, _, _ = standardize(X)
    n = len(Xs)
    centers = Xs[rng.choice(n, size=k, replace=False)]
    labels = np.zeros(n, dtype=int)
    for _ in range(max_iter):
        dist = ((Xs[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = dist.argmin(axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for j in range(k):
            if (labels == j).any():
                centers[j] = Xs[labels == j].mean(axis=0)
    return labels, centers


def gmm_em_diag(X: np.ndarray, k: int = 5, seed: int = RNG_SEED, max_iter: int = 150) -> tuple[np.ndarray, np.ndarray, dict]:
    rng = np.random.default_rng(seed)
    Xs, mu, sd = standardize(X)
    n, p = Xs.shape
    labels, centers = kmeans(Xs, k=k, seed=seed)
    weights = np.array([(labels == j).mean() for j in range(k)])
    means = np.vstack([Xs[labels == j].mean(axis=0) if (labels == j).any() else centers[j] for j in range(k)])
    vars_ = np.vstack([Xs[labels == j].var(axis=0) + 0.15 if (labels == j).any() else np.ones(p) for j in range(k)])
    ll_old = -np.inf
    resp = np.zeros((n, k))
    for _ in range(max_iter):
        logp = []
        for j in range(k):
            v = np.maximum(vars_[j], 1e-4)
            lp = np.log(weights[j] + EPS) - 0.5 * (np.log(2 * np.pi * v).sum() + (((Xs - means[j]) ** 2) / v).sum(axis=1))
            logp.append(lp)
        logp = np.vstack(logp).T
        m = logp.max(axis=1, keepdims=True)
        prob = np.exp(logp - m)
        resp = prob / np.maximum(prob.sum(axis=1, keepdims=True), EPS)
        nk = resp.sum(axis=0) + EPS
        weights = nk / n
        means = (resp.T @ Xs) / nk[:, None]
        for j in range(k):
            diff = Xs - means[j]
            vars_[j] = (resp[:, j][:, None] * diff * diff).sum(axis=0) / nk[j] + 0.05
        ll = float(np.sum(m.ravel() + np.log(prob.sum(axis=1) + EPS)))
        if abs(ll - ll_old) < 1e-5 * max(abs(ll_old), 1):
            break
        ll_old = ll
    labels = resp.argmax(axis=1)
    info = {"log_likelihood": ll_old, "weights": weights.tolist(), "feature_mu": mu.tolist(), "feature_sd": sd.tolist()}
    return labels, resp, info


def segment_users(user: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = pd.DataFrame(
        {
            "log_event": np.log1p(user["event_count"].clip(lower=0)),
            "active_days": user["active_days"],
            "log_pay": np.log1p(user["total_pay"].clip(lower=0)),
            "paid": user["paid"],
            "max_level": user["max_level"],
            "stagnation_rate": user["stagnation_rate"],
            "resource_gap": user["resource_gap_degree"],
            "avg_scarcity": user["avg_scarcity"],
            "avg_diamond": np.log1p(user["avg_diamond"].clip(lower=0)),
            "avg_power": np.log1p(user["avg_power"].clip(lower=0)),
            "session_density": np.log1p(user.get("unique_sessions", user.get("sessions_1_3", 0)).clip(lower=0)),
            "campaign_touch": np.log1p(user.get("unique_campaigns", user.get("campaigns_1_3", 0)).clip(lower=0)),
            "extra_resource_stock": np.log1p(
                user.get("avg_drug", user.get("drug_1_3_max", 0)).clip(lower=0)
                + user.get("avg_bullet", user.get("bullet_1_3_max", 0)).clip(lower=0)
                + user.get("avg_wine", user.get("wine_1_3_max", 0)).clip(lower=0)
            ),
            "ode_energy": user.get("ode_energy_mean", 0),
            "ode_drift": user.get("ode_terminal_drift", 0),
            "ode_pressure": user.get("ode_pressure_max_1_30", 0),
        }
    )
    labels, resp, gmm_info = gmm_em_diag(features.to_numpy(float), k=5)
    user = user.copy()
    user["segment_raw"] = labels
    for j in range(resp.shape[1]):
        user[f"segment_prob_{j}"] = resp[:, j]
    summary = (
        user.groupby("segment_raw")
        .agg(
            n=("account_id", "count"),
            paid_rate=("paid", "mean"),
            arpu=("total_pay", "mean"),
            arppu=("total_pay", lambda s: s[s > 0].mean() if (s > 0).any() else 0.0),
            retention30=("is_30d_retained", "mean"),
            avg_retention=("target_retention_days", "mean"),
            active_days=("active_days", "mean"),
            max_level=("max_level", "mean"),
            stagnation_rate=("stagnation_rate", "mean"),
            resource_gap=("resource_gap_degree", "mean"),
            avg_diamond=("avg_diamond", "mean"),
            avg_power=("avg_power", "mean"),
            unique_sessions=("unique_sessions", "mean") if "unique_sessions" in user.columns else ("active_days", "mean"),
            unique_campaigns=("unique_campaigns", "mean") if "unique_campaigns" in user.columns else ("active_days", "mean"),
            ode_energy=("ode_energy_mean", "mean") if "ode_energy_mean" in user.columns else ("active_days", "mean"),
            ode_drift=("ode_terminal_drift", "mean") if "ode_terminal_drift" in user.columns else ("active_days", "mean"),
            share=("account_id", lambda s: len(s) / len(user)),
        )
        .reset_index()
    )

    def persona(row: pd.Series) -> str:
        if row["paid_rate"] < 0.02 and row["active_days"] < summary["active_days"].median():
            return "zero_casual"
        if row["paid_rate"] < 0.05 and row["stagnation_rate"] > summary["stagnation_rate"].median():
            return "at_risk_free"
        if row["paid_rate"] >= 0.05 and row["arppu"] < summary["arppu"].quantile(0.65):
            return "micro_monthly"
        if row["paid_rate"] >= 0.05 and row["arppu"] >= summary["arppu"].quantile(0.65):
            return "mid_high_spender"
        return "growth_active"

    summary["segment"] = summary.apply(persona, axis=1)
    summary["gmm_weight"] = [gmm_info["weights"][int(i)] for i in summary["segment_raw"]]
    summary["gmm_log_likelihood"] = gmm_info["log_likelihood"]
    # Ensure names are unique and stable for tables.
    seen = {}
    names = []
    for s in summary["segment"]:
        seen[s] = seen.get(s, 0) + 1
        names.append(s if seen[s] == 1 else f"{s}_{seen[s]}")
    summary["segment"] = names
    mapping = dict(zip(summary["segment_raw"], summary["segment"]))
    user["segment"] = user["segment_raw"].map(mapping)
    return user, summary.drop(columns=["segment_raw"]).sort_values("share", ascending=False)


def strategy_library() -> list[Strategy]:
    return [
        Strategy("S1", 1, "login_day==1", "all_new", "All new players", "6 RMB first-charge pack: small diamonds, food/wood/stone starter bundle, 1h speedup", 6, 0.260, 0.014, 0.004, 0.35, 1.00),
        Strategy("S2", 3, "diamond<=300 or stagnation>=2 days", "at_risk_free", "At-risk free and low-diamond users", "12 RMB bottleneck relief: coin + wood + stone + small diamonds", 12, 0.180, 0.036, 0.003, 0.70, 0.95),
        Strategy("S3", 5, "active_days_1_3>=2 and unpaid", "growth_active", "High-activity unpaid users", "18 RMB growth accelerator: building speedups + coin + selectable base resource", 18, 0.140, 0.026, 0.005, 0.55, 1.05),
        Strategy("S4", 7, "paid or high_activity", "micro_monthly", "Micro-pay and stable active players", "30 RMB monthly card: daily diamonds + speedups", 30, 0.145, 0.024, 0.004, 0.45, 1.15),
        Strategy("S5", 10, "level>=10 and resource_gap high", "growth_active", "Players near level bottlenecks", "30 RMB level breakthrough pack: coin + wood + stone + research/building speedups", 30, 0.120, 0.028, 0.006, 0.60, 1.00),
        Strategy("S6", 14, "paid and power high", "mid_high_spender", "Mid/high spenders", "68 RMB war-prep pack: diamonds + advanced speedups + hero experience", 68, 0.100, 0.012, 0.007, 0.35, 1.35),
        Strategy("S7", 21, "league_score high or active>=14 days", "micro_monthly", "Socially engaged and retained players", "30 RMB alliance support pack: alliance resources + speedups + coin", 30, 0.090, 0.017, 0.003, 0.40, 1.05),
        Strategy("S8", 26, "late_retention_high and paid", "mid_high_spender", "Late-stage retained spenders", "128 RMB season sprint pack: diamonds + premium acceleration + hero materials", 128, 0.060, 0.005, 0.007, 0.20, 1.50),
    ]


def segment_strategy_response(seg: pd.Series, st: Strategy) -> tuple[float, float, float, float]:
    paid_rate = float(seg["paid_rate"])
    arpu = float(seg["arpu"])
    active = float(seg["active_days"])
    stagnation = float(seg["stagnation_rate"])
    gap = float(seg["resource_gap"])
    retention = float(seg["retention30"])
    ode_drift = float(seg.get("ode_drift", 0))
    ode_energy = float(seg.get("ode_energy", 0))

    audience_boost = 1.0
    if st.target_rule in str(seg["segment"]):
        audience_boost += 0.55
    if st.target_rule == "all_new":
        audience_boost += 0.10
    if st.target_rule == "at_risk_free" and stagnation > 0.55:
        audience_boost += 0.45
    if st.target_rule == "growth_active" and active >= 7:
        audience_boost += 0.35
    if st.target_rule == "micro_monthly" and paid_rate >= 0.03:
        audience_boost += 0.40
    if st.target_rule == "mid_high_spender" and arpu >= 3:
        audience_boost += 0.55

    price_elasticity = np.exp(-0.014 * max(st.price - 18, 0))
    willingness = 0.72 + 2.15 * paid_rate + 0.022 * arpu + 0.15 * np.log1p(active)
    pressure_need = 1.0 + 0.25 * max(gap, 0) + 0.30 * stagnation + 0.03 * max(ode_drift, 0)
    # New-server launch packs have stronger salience than passive historical
    # purchases. The multiplier is a calibrated intervention assumption,
    # stress-tested later by Monte Carlo rather than treated as observed fact.
    launch_salience = 1.45
    purchase_prob = st.purchase_base * audience_boost * price_elasticity * willingness * pressure_need * launch_salience
    purchase_prob = float(np.clip(purchase_prob, 0.003, 0.58))

    uplift_need = 1.0 + 1.8 * max(TARGET_RETENTION - retention, 0) + 0.35 * stagnation
    dynamic_response = 1.0 + 0.02 * max(ode_energy, 0)
    retention_uplift = st.retention_uplift * audience_boost * uplift_need * (0.75 + st.resource_relief) * dynamic_response
    retention_uplift -= st.irritation * (1.0 + 0.25 * max(st.price - 30, 0) / 30)
    retention_uplift = float(np.clip(retention_uplift, -0.015, 0.075))

    exposed_share = 1.0
    if st.target_rule == "at_risk_free":
        exposed_share = float(np.clip(0.35 + stagnation, 0.35, 0.95))
    elif st.target_rule == "growth_active":
        exposed_share = float(np.clip(active / 18, 0.25, 0.90))
    elif st.target_rule == "micro_monthly":
        exposed_share = float(np.clip(0.25 + 4 * paid_rate + active / 30, 0.25, 0.92))
    elif st.target_rule == "mid_high_spender":
        exposed_share = float(np.clip(0.15 + 5 * paid_rate + arpu / 30, 0.10, 0.85))

    arpu = exposed_share * purchase_prob * st.price * st.arpu_weight
    return exposed_share, purchase_prob, retention_uplift, arpu


def evaluate_plan(segment_summary: pd.DataFrame, strategies: list[Strategy], selected_ids: tuple[str, ...]) -> tuple[pd.DataFrame, dict]:
    selected = [s for s in strategies if s.strategy_id in selected_ids]
    rows = []
    total_revenue = 0.0
    retained = 0.0
    for _, seg in segment_summary.iterrows():
        n = N_NEW_USERS * float(seg["share"])
        base_ret = float(seg["retention30"])
        seg_revenue = n * float(seg["arpu"])
        p_survive = base_ret
        cumulative_irritation = 0.0
        for st in selected:
            exposed, buy_prob, uplift, arpu = segment_strategy_response(seg, st)
            seg_revenue += n * arpu
            p_survive += exposed * uplift * (1 - p_survive)
            cumulative_irritation += exposed * st.irritation
            rows.append(
                {
                    "strategy_id": st.strategy_id,
                    "segment": seg["segment"],
                    "expected_exposed_users": n * exposed,
                    "purchase_probability": buy_prob,
                    "expected_buyers": n * exposed * buy_prob,
                    "price": st.price,
                    "expected_revenue": n * arpu,
                    "retention_uplift": exposed * uplift,
                    "content": st.content,
                    "trigger": st.trigger,
                    "audience": st.audience,
                }
            )
        p_survive -= 0.08 * max(cumulative_irritation - 0.025, 0)
        p_survive = float(np.clip(p_survive, 0.0, 0.55))
        retained += n * p_survive
        total_revenue += seg_revenue

    plan = pd.DataFrame(rows)
    summary = {
        "selected": ",".join(selected_ids),
        "expected_revenue": total_revenue,
        "expected_retention30": retained / N_NEW_USERS,
        "expected_retained_users": retained,
        "num_strategies": len(selected_ids),
    }
    return plan, summary


def robust_plan_score(segment_summary: pd.DataFrame, strategies: list[Strategy], selected_ids: tuple[str, ...], seed: int) -> dict:
    rng = np.random.default_rng(seed)
    selected = [s for s in strategies if s.strategy_id in selected_ids]
    revenue_draws = []
    retention_draws = []
    for _ in range(180):
        seg2 = segment_summary.copy()
        # Bayesian posterior-style uncertainty over segment composition and
        # response parameters. This is a light Thompson-sampling surrogate:
        # evaluate plans across plausible worlds rather than one point estimate.
        share_noise = rng.dirichlet(np.maximum(seg2["share"].to_numpy(float) * 450, 1.0))
        seg2["share"] = share_noise
        seg2["paid_rate"] = np.clip(seg2["paid_rate"] * rng.lognormal(0, 0.08, len(seg2)), 0, 1)
        seg2["arpu"] = np.clip(seg2["arpu"] * rng.lognormal(0, 0.18, len(seg2)), 0, None)
        seg2["retention30"] = np.clip(seg2["retention30"] + rng.normal(0, 0.012, len(seg2)), 0, 1)
        seg2["active_days"] = np.clip(seg2["active_days"] * rng.lognormal(0, 0.07, len(seg2)), 0, DAY_MAX)
        seg2["stagnation_rate"] = np.clip(seg2["stagnation_rate"] + rng.normal(0, 0.035, len(seg2)), 0, 1)
        _, s = evaluate_plan(seg2, selected, tuple(st.strategy_id for st in selected))
        response_shock = rng.lognormal(mean=-0.5 * 0.18**2, sigma=0.18)
        retention_shock = rng.normal(1.0, 0.10)
        revenue_draws.append(s["expected_revenue"] * response_shock)
        retention_draws.append(np.clip(s["expected_retention30"] * retention_shock, 0, 1))
    revenue_draws = np.asarray(revenue_draws)
    retention_draws = np.asarray(retention_draws)
    return {
        "robust_revenue_p10": float(np.quantile(revenue_draws, 0.10)),
        "robust_retention_p10": float(np.quantile(retention_draws, 0.10)),
        "robust_joint_prob": float(np.mean((revenue_draws >= TARGET_REVENUE) & (retention_draws >= TARGET_RETENTION))),
    }


def optimize_plan(segment_summary: pd.DataFrame, strategies: list[Strategy]) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    results = []
    best = None
    ids = [s.strategy_id for s in strategies]
    for r in range(3, len(ids) + 1):
        for combo in itertools.combinations(ids, r):
            plan, summary = evaluate_plan(segment_summary, strategies, combo)
            robust = robust_plan_score(segment_summary, strategies, combo, seed=RNG_SEED + len(results))
            summary.update(robust)
            feasible = summary["expected_retention30"] >= TARGET_RETENTION and summary["expected_revenue"] >= TARGET_REVENUE
            # Multi-objective scalarization: revenue with retention barrier and
            # parsimony penalty, so the plan is strong but not spammy.
            score = 0.72 * summary["expected_revenue"] + 0.28 * summary["robust_revenue_p10"]
            score -= 600_000 * max(TARGET_RETENTION - summary["expected_retention30"], 0) ** 2
            score -= 900_000 * max(TARGET_RETENTION - summary["robust_retention_p10"], 0) ** 2
            score -= 2_000 * max(summary["num_strategies"] - 7, 0)
            score += 12_000 * summary["robust_joint_prob"]
            summary["feasible"] = feasible
            summary["score"] = score
            results.append(summary)
            if feasible and (best is None or score > best[2]["score"]):
                best = (plan, combo, summary)
    search = pd.DataFrame(results).sort_values(["feasible", "score"], ascending=[False, False])
    if best is None:
        top = search.iloc[0]
        combo = tuple(top["selected"].split(","))
        plan, summary = evaluate_plan(segment_summary, strategies, combo)
        best = (plan, combo, summary)
    return best[0], search, best[2]


def price_grid_for_strategy(st: Strategy) -> list[float]:
    grids = {
        "S1": [6, 8, 12],
        "S2": [12, 18, 24],
        "S3": [18, 24, 30],
        "S4": [25, 30, 45],
        "S5": [30, 45, 60],
        "S6": [68, 98, 128],
        "S7": [30, 45, 60],
        "S8": [98, 128, 198],
    }
    return grids.get(st.strategy_id, [st.price])


def optimize_prices_for_selected(
    segment_summary: pd.DataFrame, strategies: list[Strategy], selected_ids: tuple[str, ...]
) -> tuple[list[Strategy], pd.DataFrame, dict]:
    selected_base = [s for s in strategies if s.strategy_id in selected_ids]
    selected_set = set(selected_ids)
    other = [s for s in strategies if s.strategy_id not in selected_set]
    rows = []
    best = None
    grids = [price_grid_for_strategy(s) for s in selected_base]
    for prices in itertools.product(*grids):
        priced_selected = [replace(st, price=float(p)) for st, p in zip(selected_base, prices)]
        priced_library = other + priced_selected
        _, summary = evaluate_plan(segment_summary, priced_library, selected_ids)
        avg_price = float(np.mean(prices))
        price_dispersion = float(np.std(prices))
        score = summary["expected_revenue"]
        score -= 800_000 * max(TARGET_RETENTION - summary["expected_retention30"], 0) ** 2
        # Avoid a purely high-price solution that looks good in simulation but
        # would be hard to defend in live operations.
        score -= 250 * max(avg_price - 60, 0)
        score -= 80 * price_dispersion
        row = {
            "prices": json.dumps(dict(zip([s.strategy_id for s in selected_base], prices))),
            "expected_revenue": summary["expected_revenue"],
            "expected_retention30": summary["expected_retention30"],
            "score": score,
            "feasible": summary["expected_revenue"] >= TARGET_REVENUE and summary["expected_retention30"] >= TARGET_RETENTION,
        }
        rows.append(row)
        if row["feasible"] and (best is None or row["score"] > best[0]["score"]):
            best = (row, priced_library, summary)
    search = pd.DataFrame(rows).sort_values(["feasible", "score"], ascending=[False, False])
    if best is None:
        top = search.iloc[0]
        price_map = json.loads(top["prices"])
        priced_selected = [replace(st, price=float(price_map[st.strategy_id])) for st in selected_base]
        priced_library = other + priced_selected
        _, summary = evaluate_plan(segment_summary, priced_library, selected_ids)
        best = (top.to_dict(), priced_library, summary)
    best[2]["price_optimization_score"] = float(best[0]["score"])
    best[2]["optimized_prices"] = best[0]["prices"]
    return best[1], search, best[2]


def monte_carlo(segment_summary: pd.DataFrame, strategies: list[Strategy], selected_ids: tuple[str, ...], n_iter: int = 5000) -> pd.DataFrame:
    rng = np.random.default_rng(RNG_SEED)
    selected = [s for s in strategies if s.strategy_id in selected_ids]
    shares = segment_summary["share"].to_numpy(float)
    shares = shares / shares.sum()
    rows = []
    for _ in range(n_iter):
        purchase_market_shock = float(np.clip(rng.lognormal(mean=-0.5 * 0.28**2, sigma=0.28), 0.45, 1.75))
        retention_market_shock = float(np.clip(rng.normal(1.0, 0.16), 0.55, 1.35))
        counts = rng.multinomial(N_NEW_USERS, shares)
        revenue = 0.0
        retained = 0
        for count, (_, seg) in zip(counts, segment_summary.iterrows()):
            base_pay = max(float(seg["arpu"]), 0)
            base_ret = float(seg["retention30"])
            p_ret = base_ret
            # Historical base revenue is skewed; gamma noise approximates LTV
            # heterogeneity without assuming normality.
            revenue += rng.gamma(shape=max(count, 1), scale=base_pay) if base_pay > 0 else 0.0
            irritation = 0.0
            for st in selected:
                exposed, buy_prob, uplift, _ = segment_strategy_response(seg, st)
                strategy_purchase_shock = float(np.clip(rng.lognormal(mean=-0.5 * 0.18**2, sigma=0.18), 0.55, 1.55))
                strategy_retention_shock = float(np.clip(rng.normal(1.0, 0.12), 0.65, 1.35))
                buy_prob = float(np.clip(buy_prob * purchase_market_shock * strategy_purchase_shock, 0.0, 0.85))
                uplift = float(uplift * retention_market_shock * strategy_retention_shock)
                exposed_n = rng.binomial(count, exposed)
                buyers = rng.binomial(exposed_n, buy_prob)
                revenue += buyers * st.price * st.arpu_weight
                p_ret += exposed * uplift * (1 - p_ret)
                irritation += exposed * st.irritation
            p_ret -= 0.08 * max(irritation - 0.025, 0)
            p_ret = float(np.clip(p_ret, 0.0, 0.55))
            retained += rng.binomial(count, p_ret)
        rows.append({"revenue": revenue, "retention30": retained / N_NEW_USERS, "retained_users": retained})
    return pd.DataFrame(rows)


def strategy_table(best_plan: pd.DataFrame, strategies: list[Strategy]) -> pd.DataFrame:
    rows = []
    for st in strategies:
        p = best_plan[best_plan["strategy_id"] == st.strategy_id]
        if p.empty:
            continue
        rows.append(
            {
                "strategy_id": st.strategy_id,
                "push_time_or_trigger": f"Day {st.day}; {st.trigger}",
                "target_audience": st.audience,
                "package_content": st.content,
                "price_rmb": st.price,
                "expected_exposed_users": p["expected_exposed_users"].sum(),
                "expected_buyers": p["expected_buyers"].sum(),
                "expected_strategy_revenue": p["expected_revenue"].sum(),
                "expected_arpu_contribution": p["expected_revenue"].sum() / N_NEW_USERS,
                "avg_retention_uplift": np.average(p["retention_uplift"], weights=np.maximum(p["expected_exposed_users"], 1)),
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values("strategy_id")


def main() -> None:
    reset_public_output()
    user = load_features()
    user, segment_summary = segment_users(user)
    strategies = strategy_library()
    best_plan, search, best_summary = optimize_plan(segment_summary, strategies)
    portfolio_summary = best_summary.copy()
    selected_ids = tuple(best_summary["selected"].split(","))
    strategies, price_search, price_summary = optimize_prices_for_selected(segment_summary, strategies, selected_ids)
    best_plan, best_summary = evaluate_plan(segment_summary, strategies, selected_ids)
    for k in ["robust_revenue_p10", "robust_retention_p10", "robust_joint_prob"]:
        if k in portfolio_summary:
            best_summary[k] = portfolio_summary[k]
    best_summary.update(price_summary)
    mc = monte_carlo(segment_summary, strategies, selected_ids)
    table = strategy_table(best_plan, strategies)

    user.to_csv(CACHE_DIR / "q3_user_segments.csv", index=False, encoding="utf-8-sig")
    segment_summary.to_csv(CACHE_DIR / "q3_segment_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([s.__dict__ for s in strategies]).to_csv(CACHE_DIR / "q3_strategy_library.csv", index=False, encoding="utf-8-sig")
    search.to_csv(CACHE_DIR / "q3_strategy_search.csv", index=False, encoding="utf-8-sig")
    price_search.to_csv(CACHE_DIR / "q3_price_search.csv", index=False, encoding="utf-8-sig")
    best_plan.to_csv(CACHE_DIR / "q3_best_plan_by_segment.csv", index=False, encoding="utf-8-sig")
    table.to_csv(OUT_DIR / "q3_strategy_table.csv", index=False, encoding="utf-8-sig")
    mc.to_csv(OUT_DIR / "q3_monte_carlo.csv", index=False, encoding="utf-8-sig")

    print(f"Done. Outputs written to: {OUT_DIR}")


if __name__ == "__main__":
    main()
