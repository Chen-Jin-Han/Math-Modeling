from __future__ import annotations

import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import polars as pl
from scipy.optimize import minimize


ROOT = Path(__file__).resolve().parent
DATA_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and (p / "pickdata1.csv").exists())
OUT_DIR = ROOT / "q2_outputs"
Q1_DIR = ROOT / "q1_outputs"
CACHE_DIR = ROOT / "internal_cache"
OUT_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

DAY_MAX = 30
EPS = 1e-9


def reset_public_output() -> None:
    """Keep final outputs limited to tables/summaries required by the problem."""
    if OUT_DIR.exists():
        for p in OUT_DIR.iterdir():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    OUT_DIR.mkdir(exist_ok=True)


@dataclass
class DatasetPaths:
    name: str
    behavior_csv: Path
    state_csv: Path


TRAIN = DatasetPaths("train", DATA_DIR / "pickdata2.csv", DATA_DIR / "pickdata1.csv")
TEST = DatasetPaths("test", DATA_DIR / "other_pickdata2.csv", DATA_DIR / "other_pickdata1.csv")


def pl_to_pandas(df: pl.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(df.to_dicts())


def parse_dt(expr: pl.Expr) -> pl.Expr:
    return expr.cast(pl.Utf8).str.strptime(pl.Datetime, strict=False)


def scan_behavior(path: Path) -> pl.LazyFrame:
    cols = [
        "account_id",
        "dt",
        "event",
        "device_id",
        "session_id",
        "channel_id",
        "platform",
        "country",
        "media_source",
        "campaign",
        "current_level",
        "current_vip_level",
        "current_gold",
        "current_diamond",
        "current_drug",
        "current_power",
        "current_money",
        "current_bullet",
        "current_wine",
        "total_pay",
        "first_login_time",
        "first_pay_level",
        "first_pay_time",
        "register_time",
        "duration_times",
        "life_cycle_days",
        "lid",
    ]
    schema = pl.scan_csv(path, infer_schema_length=0).collect_schema().names()
    return pl.scan_csv(path, infer_schema_length=100, ignore_errors=True, null_values=["", "null", "NULL"]).select(
        [c for c in cols if c in schema]
    )


def scan_state(path: Path) -> pl.LazyFrame:
    cols = [
        "account_id",
        "dt",
        "ts",
        "resource_id",
        "resource_name",
        "change_type",
        "change_num",
        "change_before",
        "change_after",
        "change_reason",
        "current_level",
        "first_login_time",
        "current_build",
        "league_funds",
        "user_league_score",
        "lid",
        "change_dollar",
        "dollar",
    ]
    schema = pl.scan_csv(path, infer_schema_length=0).collect_schema().names()
    return pl.scan_csv(path, infer_schema_length=100, ignore_errors=True, null_values=["", "null", "NULL"]).select(
        [c for c in cols if c in schema]
    )


def collect_anchor(ds: DatasetPaths) -> pl.DataFrame:
    b = scan_behavior(ds.behavior_csv).with_columns(
        [
            parse_dt(pl.col("dt")).alias("dt_parsed"),
            parse_dt(pl.col("register_time")).alias("register_parsed"),
            parse_dt(pl.col("first_login_time")).alias("b_first_login_parsed"),
        ]
    )
    s = scan_state(ds.state_csv).with_columns(
        [
            parse_dt(pl.col("ts")).alias("dt_parsed"),
            parse_dt(pl.col("first_login_time")).alias("s_first_login_parsed"),
        ]
    )
    bm = b.group_by("account_id").agg(
        [
            pl.col("dt_parsed").min().alias("b_min"),
            pl.col("register_parsed").drop_nulls().min().alias("register_dt"),
            pl.col("b_first_login_parsed").drop_nulls().min().alias("b_first_login_dt"),
        ]
    )
    sm = s.group_by("account_id").agg(
        [
            pl.col("dt_parsed").min().alias("s_min"),
            pl.col("s_first_login_parsed").drop_nulls().min().alias("s_first_login_dt"),
        ]
    )
    return (
        bm.join(sm, on="account_id", how="outer_coalesce")
        # Align with Q1: player day is anchored at explicit account
        # registration time whenever available, then first-login/event
        # fallbacks are used for incomplete records.
        .with_columns(pl.coalesce(["register_dt", "b_first_login_dt", "s_first_login_dt", "b_min", "s_min"]).alias("anchor_dt"))
        .select(["account_id", "anchor_dt"])
        .collect(engine="streaming")
    )


def collect_behavior_daily(ds: DatasetPaths, anchor: pl.DataFrame) -> pd.DataFrame:
    lf = scan_behavior(ds.behavior_csv)
    day = (
        lf.with_columns(parse_dt(pl.col("dt")).alias("dt_parsed"))
        .join(anchor.lazy(), on="account_id", how="left")
        .with_columns(((pl.col("dt_parsed").dt.date() - pl.col("anchor_dt").dt.date()).dt.total_days() + 1).cast(pl.Int32).alias("day"))
        .filter((pl.col("day") >= 1) & (pl.col("day") <= DAY_MAX))
        .group_by(["account_id", "day"])
        .agg(
            pl.len().alias("event_count"),
            pl.col("event").n_unique().alias("event_diversity"),
            pl.col("current_level").max().alias("level"),
            pl.col("current_vip_level").max().alias("vip_level"),
            pl.col("current_gold").max().alias("gold_stock"),
            pl.col("current_diamond").max().alias("diamond_stock"),
            pl.col("current_drug").max().alias("drug_stock"),
            pl.col("current_power").max().alias("power"),
            pl.col("current_money").max().alias("money_stock"),
            pl.col("current_bullet").max().alias("bullet_stock"),
            pl.col("current_wine").max().alias("wine_stock"),
            pl.col("total_pay").max().alias("total_pay_cum"),
            pl.col("first_pay_level").max().alias("first_pay_level"),
            parse_dt(pl.col("first_pay_time")).min().alias("first_pay_dt"),
            pl.col("duration_times").max().alias("duration_times"),
            pl.col("life_cycle_days").max().alias("life_cycle_days"),
            pl.col("device_id").n_unique().alias("unique_devices_day"),
            pl.col("session_id").n_unique().alias("unique_sessions_day"),
            pl.col("channel_id").n_unique().alias("unique_channels_day"),
            pl.col("media_source").n_unique().alias("unique_media_sources_day"),
            pl.col("campaign").n_unique().alias("unique_campaigns_day"),
        )
        .collect(engine="streaming")
    )
    return pl_to_pandas(day)


def collect_state_daily(ds: DatasetPaths, anchor: pl.DataFrame) -> pd.DataFrame:
    lf = scan_state(ds.state_csv)
    rid = pl.col("resource_id").cast(pl.Utf8).str.to_lowercase()
    rname = pl.col("resource_name").cast(pl.Utf8)
    is_get = pl.col("change_type") == "get"
    is_reduce = pl.col("change_type") == "reduce"
    num = pl.col("change_num").cast(pl.Float64).fill_null(0.0)

    food = rid == "food"
    wood = rid == "wood"
    stone = rid == "stone"
    coin = rid == "coin"
    gem = rid == "gem"
    basic = food | wood | stone
    speedup = rname.str.contains("加速", literal=True)

    daily = (
        lf.with_columns(parse_dt(pl.col("ts")).alias("dt_parsed"))
        .join(anchor.lazy(), on="account_id", how="left")
        .with_columns(((pl.col("dt_parsed").dt.date() - pl.col("anchor_dt").dt.date()).dt.total_days() + 1).cast(pl.Int32).alias("day"))
        .filter((pl.col("day") >= 1) & (pl.col("day") <= DAY_MAX))
        .group_by(["account_id", "day"])
        .agg(
            pl.len().alias("resource_events"),
            pl.when(food & is_get).then(num).otherwise(0.0).sum().alias("food_get"),
            pl.when(food & is_reduce).then(num).otherwise(0.0).sum().alias("food_reduce"),
            pl.when(wood & is_get).then(num).otherwise(0.0).sum().alias("wood_get"),
            pl.when(wood & is_reduce).then(num).otherwise(0.0).sum().alias("wood_reduce"),
            pl.when(stone & is_get).then(num).otherwise(0.0).sum().alias("stone_get"),
            pl.when(stone & is_reduce).then(num).otherwise(0.0).sum().alias("stone_reduce"),
            pl.when(coin & is_get).then(num).otherwise(0.0).sum().alias("coin_get"),
            pl.when(coin & is_reduce).then(num).otherwise(0.0).sum().alias("coin_reduce"),
            pl.when(gem & is_get).then(num).otherwise(0.0).sum().alias("gem_get"),
            pl.when(gem & is_reduce).then(num).otherwise(0.0).sum().alias("gem_reduce"),
            pl.when(speedup & is_get).then(num).otherwise(0.0).sum().alias("speedup_get"),
            pl.when(speedup & is_reduce).then(num).otherwise(0.0).sum().alias("speedup_reduce"),
            pl.when(basic & is_get).then(num).otherwise(0.0).sum().alias("basic_get"),
            pl.when(basic & is_reduce).then(num).otherwise(0.0).sum().alias("basic_reduce"),
            pl.col("current_build").max().alias("current_build"),
            pl.col("league_funds").max().alias("league_funds"),
            pl.col("user_league_score").max().alias("user_league_score"),
            pl.col("lid").max().alias("lid"),
            pl.col("change_dollar").sum().alias("change_dollar_sum"),
            pl.col("dollar").max().alias("dollar_max"),
        )
        .collect(engine="streaming")
    )
    return pl_to_pandas(daily)


def complete_panel(users: pd.Index, daily: pd.DataFrame) -> pd.DataFrame:
    base = pd.MultiIndex.from_product([users.to_numpy(), np.arange(1, DAY_MAX + 1)], names=["account_id", "day"]).to_frame(index=False)
    out = base.merge(daily, on=["account_id", "day"], how="left")
    fill_zero = [c for c in out.columns if c not in ["account_id", "day", "first_pay_dt"]]
    out[fill_zero] = out[fill_zero].fillna(0)
    return out


def build_panel(ds: DatasetPaths) -> tuple[pd.DataFrame, pd.DataFrame]:
    print(f"[{ds.name}] anchor")
    anchor = collect_anchor(ds)
    print(f"[{ds.name}] behavior daily")
    bd = collect_behavior_daily(ds, anchor)
    print(f"[{ds.name}] state/resource daily")
    sd = collect_state_daily(ds, anchor)
    users = pd.Index(pl_to_pandas(anchor)["account_id"].astype(np.int64).unique(), name="account_id")
    daily = bd.merge(sd, on=["account_id", "day"], how="outer")
    daily = complete_panel(users, daily)
    daily = daily.sort_values(["account_id", "day"]).reset_index(drop=True)

    for c in [
        "level",
        "gold_stock",
        "diamond_stock",
        "drug_stock",
        "power",
        "money_stock",
        "bullet_stock",
        "wine_stock",
        "total_pay_cum",
        "vip_level",
        "duration_times",
        "life_cycle_days",
    ]:
        if c not in daily:
            daily[c] = 0.0
        daily[c] = daily.groupby("account_id")[c].ffill().fillna(0)

    daily["level_prev"] = daily.groupby("account_id")["level"].shift(1).fillna(0)
    daily["level_gain"] = (daily["level"] - daily["level_prev"]).clip(lower=0)
    daily["active"] = ((daily["event_count"] > 0) | (daily["resource_events"] > 0)).astype(int)
    daily["stagnant"] = ((daily["active"] == 1) & (daily["level_gain"] <= 0)).astype(int)
    daily["basic_net"] = daily["basic_get"] - daily["basic_reduce"]
    daily["coin_net"] = daily["coin_get"] - daily["coin_reduce"]
    daily["gem_net"] = daily["gem_get"] - daily["gem_reduce"]
    daily["basic_pressure"] = np.log1p(daily["basic_reduce"]) - np.log1p(daily["basic_get"])
    daily["coin_pressure"] = np.log1p(daily["coin_reduce"]) - np.log1p(daily["coin_get"])
    daily["gem_pressure"] = np.log1p(daily["gem_reduce"]) - np.log1p(daily["gem_get"])
    daily["resource_pressure"] = daily[["basic_pressure", "coin_pressure", "gem_pressure"]].sum(axis=1)
    daily["scarcity_index"] = daily["resource_pressure"] + 0.25 * np.log1p(daily["speedup_reduce"]) - 0.10 * np.log1p(daily["diamond_stock"].clip(lower=0))
    daily["pay_increment"] = daily.groupby("account_id")["total_pay_cum"].diff().fillna(daily["total_pay_cum"]).clip(lower=0)

    user = daily.groupby("account_id").agg(
        total_pay=("total_pay_cum", "max"),
        first_pay_day=("day", lambda s: 0),
        max_level=("level", "max"),
        avg_level_gain=("level_gain", "mean"),
        total_level_gain=("level_gain", "sum"),
        active_days=("active", "sum"),
        event_count=("event_count", "sum"),
        avg_event_diversity=("event_diversity", "mean"),
        avg_gold=("gold_stock", "mean"),
        avg_diamond=("diamond_stock", "mean"),
        avg_drug=("drug_stock", "mean"),
        min_diamond=("diamond_stock", "min"),
        avg_power=("power", "mean"),
        avg_money=("money_stock", "mean"),
        avg_bullet=("bullet_stock", "mean"),
        avg_wine=("wine_stock", "mean"),
        unique_devices=("unique_devices_day", "sum"),
        unique_sessions=("unique_sessions_day", "sum"),
        unique_channels=("unique_channels_day", "sum"),
        unique_media_sources=("unique_media_sources_day", "sum"),
        unique_campaigns=("unique_campaigns_day", "sum"),
        total_basic_reduce=("basic_reduce", "sum"),
        total_basic_get=("basic_get", "sum"),
        total_coin_reduce=("coin_reduce", "sum"),
        total_coin_get=("coin_get", "sum"),
        total_gem_reduce=("gem_reduce", "sum"),
        total_gem_get=("gem_get", "sum"),
        total_speedup_reduce=("speedup_reduce", "sum"),
        avg_scarcity=("scarcity_index", "mean"),
        stagnation_days=("stagnant", "sum"),
        league_score=("user_league_score", "max"),
        league_funds=("league_funds", "max"),
        current_build=("current_build", "max"),
        max_vip=("vip_level", "max"),
        last_active_day=("day", lambda s: int(daily.loc[s.index, "day"][daily.loc[s.index, "active"] > 0].max()) if (daily.loc[s.index, "active"] > 0).any() else 0),
    ).reset_index()

    first_pay = daily[daily["pay_increment"] > 0].sort_values(["account_id", "day"]).groupby("account_id").first()[
        ["day", "level", "pay_increment", "diamond_stock", "gold_stock"]
    ]
    first_pay = first_pay.rename(columns={"day": "first_pay_day", "level": "first_pay_level_obs", "pay_increment": "first_pay_amount"})
    user = user.drop(columns=["first_pay_day"]).merge(first_pay.reset_index(), on="account_id", how="left")
    user[["first_pay_day", "first_pay_level_obs", "first_pay_amount", "diamond_stock", "gold_stock"]] = user[
        ["first_pay_day", "first_pay_level_obs", "first_pay_amount", "diamond_stock", "gold_stock"]
    ].fillna(0)
    user["paid"] = (user["total_pay"] > 0).astype(int)
    user["stagnation_rate"] = user["stagnation_days"] / np.maximum(user["active_days"], 1)
    user["resource_gap_degree"] = np.log1p(user["total_basic_reduce"] + user["total_coin_reduce"] + user["total_gem_reduce"]) - np.log1p(
        user["total_basic_get"] + user["total_coin_get"] + user["total_gem_get"]
    )
    return daily, user


def standardize_fit(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd < EPS] = 1.0
    return (X - mu) / sd, mu, sd


def standardize_apply(X: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return (X - mu) / sd


def ridge_fit_predict(train_x: pd.DataFrame, y: np.ndarray, test_x: pd.DataFrame, lambdas=None) -> tuple[np.ndarray, dict, np.ndarray]:
    if lambdas is None:
        lambdas = [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100]
    X, mu, sd = standardize_fit(train_x.to_numpy(float))
    Xt = standardize_apply(test_x.to_numpy(float), mu, sd)
    X = np.c_[np.ones(len(X)), X]
    Xt = np.c_[np.ones(len(Xt)), Xt]
    y = np.asarray(y, float)
    best = None
    idx = np.arange(len(y))
    folds = idx % 5
    for lam in lambdas:
        losses = []
        for k in range(5):
            tr, va = folds != k, folds == k
            reg = np.eye(X.shape[1]) * lam
            reg[0, 0] = 0
            beta = np.linalg.pinv(X[tr].T @ X[tr] + reg) @ X[tr].T @ y[tr]
            pred = X[va] @ beta
            losses.append(float(np.mean(np.abs(pred - y[va]))))
        if best is None or np.mean(losses) < best["cv_mae"]:
            best = {"lambda": lam, "cv_mae": float(np.mean(losses))}
    reg = np.eye(X.shape[1]) * best["lambda"]
    reg[0, 0] = 0
    beta = np.linalg.pinv(X.T @ X + reg) @ X.T @ y
    return Xt @ beta, best, beta


def logistic_fit_predict(train_x: pd.DataFrame, y: np.ndarray, test_x: pd.DataFrame, balanced: bool = False) -> tuple[np.ndarray, dict, np.ndarray]:
    X, mu, sd = standardize_fit(train_x.to_numpy(float))
    Xt = standardize_apply(test_x.to_numpy(float), mu, sd)
    X = np.c_[np.ones(len(X)), X]
    Xt = np.c_[np.ones(len(Xt)), Xt]
    y = np.asarray(y, float)
    if balanced:
        pos = max(float(y.sum()), 1.0)
        neg = max(float(len(y) - y.sum()), 1.0)
        w = np.where(y > 0, len(y) / (2 * pos), len(y) / (2 * neg))
        w = w / np.mean(w)
    else:
        w = np.ones_like(y)
    best = None
    for lam in [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1, 3]:
        def obj(beta):
            z = np.clip(X @ beta, -40, 40)
            p = 1 / (1 + np.exp(-z))
            loss = -np.mean(w * (y * np.log(p + EPS) + (1 - y) * np.log(1 - p + EPS))) + lam * np.sum(beta[1:] ** 2) / len(beta)
            grad = X.T @ (w * (p - y)) / len(y)
            grad[1:] += 2 * lam * beta[1:] / len(beta)
            return loss, grad

        res = minimize(lambda b: obj(b)[0], np.zeros(X.shape[1]), jac=lambda b: obj(b)[1], method="L-BFGS-B", options={"maxiter": 250})
        if best is None or res.fun < best["nll"]:
            best = {"lambda": lam, "nll": float(res.fun), "beta": res.x}
    beta = best.pop("beta")
    pred = 1 / (1 + np.exp(-np.clip(Xt @ beta, -40, 40)))
    return pred, best, beta


def panel_growth_model(train_daily: pd.DataFrame, test_daily: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = [
        "day",
        "level_prev",
        "basic_get",
        "basic_reduce",
        "coin_get",
        "coin_reduce",
        "gem_get",
        "gem_reduce",
        "speedup_get",
        "speedup_reduce",
        "gold_stock",
        "diamond_stock",
        "power",
        "event_count",
        "resource_pressure",
        "scarcity_index",
    ]
    tr = train_daily[train_daily["active"] == 1].copy()
    te = test_daily[test_daily["active"] == 1].copy()
    Xtr = pd.DataFrame({f: np.log1p(tr[f].clip(lower=0)) if f not in ["day", "level_prev", "resource_pressure", "scarcity_index"] else tr[f] for f in features})
    Xte = pd.DataFrame({f: np.log1p(te[f].clip(lower=0)) if f not in ["day", "level_prev", "resource_pressure", "scarcity_index"] else te[f] for f in features})
    pred, info, beta = ridge_fit_predict(Xtr, tr["level_gain"].to_numpy(float), Xte)
    pred = np.clip(pred, 0, None)
    metrics = {
        "task": "daily_level_gain",
        "model": "scarcity_panel_ridge",
        "MAE": float(np.mean(np.abs(pred - te["level_gain"].to_numpy(float)))),
        "RMSE": float(np.sqrt(np.mean((pred - te["level_gain"].to_numpy(float)) ** 2))),
        "lambda": info["lambda"],
        "cv_mae": info["cv_mae"],
    }
    coef = pd.DataFrame({"feature": ["intercept"] + features, "coef": beta})
    return pd.DataFrame([metrics]), coef


def card_point_analysis(daily: pd.DataFrame) -> pd.DataFrame:
    g = daily[daily["active"] == 1].groupby("level_prev").agg(
        n=("account_id", "count"),
        avg_gain=("level_gain", "mean"),
        stagnation_rate=("stagnant", "mean"),
        avg_scarcity=("scarcity_index", "mean"),
        basic_pressure=("basic_pressure", "mean"),
        coin_pressure=("coin_pressure", "mean"),
        gem_pressure=("gem_pressure", "mean"),
        avg_diamond=("diamond_stock", "mean"),
    ).reset_index()
    g = g[g["n"] >= 20].copy()
    for c in ["stagnation_rate", "avg_scarcity", "basic_pressure", "coin_pressure", "gem_pressure", "avg_gain"]:
        sd = g[c].std() or 1.0
        g[f"z_{c}"] = (g[c] - g[c].mean()) / sd
    g["card_score"] = g["z_stagnation_rate"] + g["z_avg_scarcity"] - g["z_avg_gain"]
    return g.sort_values("card_score", ascending=False)


def threshold_analysis(train_daily: pd.DataFrame, test_daily: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    def add_next_inactive(df: pd.DataFrame) -> pd.DataFrame:
        cur = df[df["day"] < DAY_MAX].copy()
        nxt = df[["account_id", "day", "active"]].copy()
        nxt["day"] -= 1
        nxt = nxt.rename(columns={"active": "next_active"})
        out = cur.merge(nxt, on=["account_id", "day"], how="left")
        out["next_inactive"] = (out["next_active"].fillna(0) <= 0).astype(int)
        return out

    rows = []
    for source, df in [("train", train_daily), ("test", test_daily)]:
        active = add_next_inactive(df)
        active = active[active["active"] == 1].copy()
        qs = np.unique(np.nanquantile(active["diamond_stock"].clip(lower=0), np.linspace(0.05, 0.95, 19)))
        for th in qs:
            low = active["diamond_stock"] <= th
            if low.mean() < 0.03 or low.mean() > 0.97:
                continue
            rows.append(
                {
                    "dataset": source,
                    "diamond_threshold": float(th),
                    "low_group_share": float(low.mean()),
                    "stagnation_low": float(active.loc[low, "stagnant"].mean()),
                    "stagnation_high": float(active.loc[~low, "stagnant"].mean()),
                    "risk_lift": float(active.loc[low, "stagnant"].mean() - active.loc[~low, "stagnant"].mean()),
                    "next_inactive_low": float(active.loc[low, "next_inactive"].mean()),
                    "next_inactive_high": float(active.loc[~low, "next_inactive"].mean()),
                    "churn_risk_lift": float(active.loc[low, "next_inactive"].mean() - active.loc[~low, "next_inactive"].mean()),
                    "avg_scarcity_low": float(active.loc[low, "scarcity_index"].mean()),
                    "avg_scarcity_high": float(active.loc[~low, "scarcity_index"].mean()),
                }
            )
    table = pd.DataFrame(rows).sort_values(["dataset", "churn_risk_lift"], ascending=[True, False])
    train_candidates = table[(table["dataset"] == "train") & (table["low_group_share"] <= 0.35)]
    if train_candidates.empty:
        train_candidates = table[table["dataset"] == "train"]
    best_train = train_candidates.sort_values("churn_risk_lift", ascending=False).iloc[0].to_dict() if not train_candidates.empty else {}
    return table, best_train


def scarcity_lag_causal_model(train_daily: pd.DataFrame, test_daily: pd.DataFrame, diamond_threshold: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    def lag_frame(df: pd.DataFrame) -> pd.DataFrame:
        cur = df[df["day"] < DAY_MAX].copy()
        nxt = df[["account_id", "day", "active"]].copy()
        nxt["day"] -= 1
        nxt = nxt.rename(columns={"active": "next_active"})
        out = cur.merge(nxt, on=["account_id", "day"], how="left")
        out = out[(out["active"] == 1) & out["next_active"].notna()].copy()
        out["next_inactive"] = (out["next_active"] <= 0).astype(int)
        out["low_diamond"] = (out["diamond_stock"] <= diamond_threshold).astype(int)
        out["low_gold"] = (out["gold_stock"] <= np.nanquantile(train_daily["gold_stock"].clip(lower=0), 0.15)).astype(int)
        return out

    tr = lag_frame(train_daily)
    te = lag_frame(test_daily)
    features = [
        "low_diamond",
        "low_gold",
        "day",
        "level",
        "event_count",
        "resource_pressure",
        "scarcity_index",
        "gold_stock",
        "diamond_stock",
        "basic_reduce",
        "coin_reduce",
        "gem_reduce",
        "speedup_reduce",
    ]
    Xtr = pd.DataFrame({f: np.log1p(tr[f].clip(lower=0)) if f.endswith("_stock") or f.endswith("_reduce") or f == "event_count" else tr[f] for f in features})
    Xte = pd.DataFrame({f: np.log1p(te[f].clip(lower=0)) if f.endswith("_stock") or f.endswith("_reduce") or f == "event_count" else te[f] for f in features})
    pred, info, beta = logistic_fit_predict(Xtr, tr["next_inactive"].to_numpy(int), Xte)
    y = te["next_inactive"].to_numpy(int)
    metrics = pd.DataFrame(
        [
            {
                "task": "next_day_inactive",
                "model": "lagged_scarcity_churn_logistic",
                "logloss": float(-np.mean(y * np.log(pred + EPS) + (1 - y) * np.log(1 - pred + EPS))),
                "rank_corr": float(pd.Series(pred).corr(pd.Series(y), method="spearman")),
                "lambda": info["lambda"],
                "diamond_threshold": diamond_threshold,
            }
        ]
    )
    coef = pd.DataFrame({"feature": ["intercept"] + features, "coef": beta})

    # Standardization makes coefficients less intuitive, so also report a
    # controlled marginal risk difference by replacing only low_diamond.
    Xhi = Xte.copy()
    Xlo = Xte.copy()
    Xhi["low_diamond"] = 0
    Xlo["low_diamond"] = 1
    Xstd, mu, sd = standardize_fit(Xtr.to_numpy(float))
    beta2 = beta
    ph = 1 / (1 + np.exp(-np.clip(np.c_[np.ones(len(Xhi)), standardize_apply(Xhi.to_numpy(float), mu, sd)] @ beta2, -40, 40)))
    plow = 1 / (1 + np.exp(-np.clip(np.c_[np.ones(len(Xlo)), standardize_apply(Xlo.to_numpy(float), mu, sd)] @ beta2, -40, 40)))
    metrics["controlled_low_diamond_churn_lift"] = float(np.mean(plow - ph))
    return metrics, coef.sort_values("coef", key=lambda s: s.abs(), ascending=False)


def first_payment_analysis(train_user: pd.DataFrame, test_user: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for name, user in [("train", train_user), ("test", test_user)]:
        paid = user[user["paid"] == 1].copy()
        if paid.empty:
            continue
        bins = [0, 1, 3, 7, 14, 30, 999]
        labels = ["D1", "D2-D3", "D4-D7", "D8-D14", "D15-D30", "after/unknown"]
        paid["first_pay_day_bin"] = pd.cut(paid["first_pay_day"].replace(0, 999), bins=bins, labels=labels, include_lowest=True)
        for b, g in paid.groupby("first_pay_day_bin", observed=False):
            rows.append({"dataset": name, "group_type": "first_pay_day", "group": str(b), "n": len(g), "avg_retention": g["last_active_day"].mean(), "avg_total_pay": g["total_pay"].mean()})
        paid["first_pay_amount_bin"] = pd.qcut(paid["first_pay_amount"].rank(method="first"), q=min(4, len(paid)), labels=False) + 1
        for b, g in paid.groupby("first_pay_amount_bin"):
            rows.append({"dataset": name, "group_type": "first_pay_amount_q", "group": f"Q{int(b)}", "n": len(g), "avg_retention": g["last_active_day"].mean(), "avg_total_pay": g["total_pay"].mean()})
        paid["first_pay_level_bin"] = pd.cut(paid["first_pay_level_obs"], bins=[-1, 5, 10, 15, 20, 999], labels=["0-5", "6-10", "11-15", "16-20", "21+"])
        for b, g in paid.groupby("first_pay_level_bin", observed=False):
            rows.append({"dataset": name, "group_type": "first_pay_level", "group": str(b), "n": len(g), "avg_retention": g["last_active_day"].mean(), "avg_total_pay": g["total_pay"].mean()})
    table = pd.DataFrame(rows)

    features = ["first_pay_day", "first_pay_level_obs", "first_pay_amount", "active_days", "event_count", "total_level_gain", "avg_scarcity", "max_vip"]
    tr = train_user[train_user["paid"] == 1].copy()
    te = test_user[test_user["paid"] == 1].copy()
    Xtr = pd.DataFrame({f: np.log1p(tr[f].clip(lower=0)) if f not in ["avg_scarcity"] else tr[f] for f in features})
    Xte = pd.DataFrame({f: np.log1p(te[f].clip(lower=0)) if f not in ["avg_scarcity"] else te[f] for f in features})
    pred, info, _ = ridge_fit_predict(Xtr, tr["last_active_day"].to_numpy(float), Xte)
    metrics = pd.DataFrame(
        [
            {
                "task": "paid_user_retention_from_first_pay",
                "model": "first_pay_ridge",
                "MAE": float(np.mean(np.abs(pred - te["last_active_day"].to_numpy(float)))) if len(te) else np.nan,
                "RMSE": float(np.sqrt(np.mean((pred - te["last_active_day"].to_numpy(float)) ** 2))) if len(te) else np.nan,
                "lambda": info["lambda"],
                "cv_mae": info["cv_mae"],
            }
        ]
    )
    return table, metrics


def total_pay_model(train_user: pd.DataFrame, test_user: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = [
        "active_days",
        "event_count",
        "avg_event_diversity",
        "max_level",
        "total_level_gain",
        "avg_level_gain",
        "stagnation_rate",
        "resource_gap_degree",
        "avg_scarcity",
        "avg_gold",
        "avg_diamond",
        "min_diamond",
        "avg_power",
        "total_basic_reduce",
        "total_coin_reduce",
        "total_gem_reduce",
        "total_speedup_reduce",
        "league_score",
        "league_funds",
        "current_build",
        "max_vip",
    ]
    Xtr = pd.DataFrame({f: np.log1p(train_user[f].clip(lower=0)) if f not in ["avg_scarcity", "resource_gap_degree", "stagnation_rate"] else train_user[f] for f in features})
    Xte = pd.DataFrame({f: np.log1p(test_user[f].clip(lower=0)) if f not in ["avg_scarcity", "resource_gap_degree", "stagnation_rate"] else test_user[f] for f in features})

    pay_prob, clf_info, clf_beta = logistic_fit_predict(Xtr, train_user["paid"].to_numpy(int), Xte)
    paid_tr = train_user[train_user["paid"] == 1].copy()
    paid_te = test_user[test_user["paid"] == 1].copy()
    Xtr_paid = Xtr.loc[paid_tr.index]
    Xte_paid = Xte.loc[paid_te.index]
    amount_pred_paid, reg_info, reg_beta = ridge_fit_predict(Xtr_paid, np.log1p(paid_tr["total_pay"].to_numpy(float)), Xte_paid)
    amount_pred = np.zeros(len(test_user))
    amount_pred[paid_te.index.to_numpy()] = np.expm1(amount_pred_paid).clip(min=0)

    metrics = pd.DataFrame(
        [
            {
                "task": "paid_probability",
                "model": "logistic_key_factor",
                "AUC_proxy_rank_corr": float(pd.Series(pay_prob).corr(pd.Series(test_user["paid"].to_numpy()), method="spearman")),
                "lambda": clf_info["lambda"],
            },
            {
                "task": "positive_total_pay",
                "model": "log_amount_ridge",
                "MAE": float(np.mean(np.abs(amount_pred[paid_te.index.to_numpy()] - paid_te["total_pay"].to_numpy(float)))) if len(paid_te) else np.nan,
                "RMSE": float(np.sqrt(np.mean((amount_pred[paid_te.index.to_numpy()] - paid_te["total_pay"].to_numpy(float)) ** 2))) if len(paid_te) else np.nan,
                "lambda": reg_info["lambda"],
                "cv_mae": reg_info["cv_mae"],
            },
        ]
    )
    coef = pd.DataFrame(
        {
            "feature": ["intercept"] + features,
            "paid_probability_coef": clf_beta,
            "positive_amount_coef": reg_beta if len(reg_beta) == len(features) + 1 else np.nan,
        }
    )
    return metrics, coef.sort_values("positive_amount_coef", key=lambda s: s.abs(), ascending=False)


def state_transition_model(train_daily: pd.DataFrame, test_daily: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    def build(df: pd.DataFrame) -> pd.DataFrame:
        cur = df[df["day"] < DAY_MAX].copy()
        nxt = df[["account_id", "day", "active", "total_pay_cum"]].copy()
        nxt["day"] -= 1
        nxt = nxt.rename(columns={"active": "next_active", "total_pay_cum": "next_total_pay"})
        out = cur.merge(nxt, on=["account_id", "day"], how="left")
        out = out[(out["active"] == 1) & out["next_active"].notna()].copy()
        out["state"] = np.where(out["total_pay_cum"] > 0, "paid_active", "free_active")
        out["next_state"] = np.select(
            [
                out["next_active"] <= 0,
                (out["next_active"] > 0) & (out["next_total_pay"] > out["total_pay_cum"]),
                (out["next_active"] > 0) & (out["next_total_pay"] > 0),
            ],
            ["inactive", "converted_or_paid_more", "paid_active"],
            default="free_active",
        )
        return out

    tr = build(train_daily)
    te = build(test_daily)
    diamond_th = np.nanquantile(tr["diamond_stock"].clip(lower=0), 0.30)
    gold_th = np.nanquantile(tr["gold_stock"].clip(lower=0), 0.30)
    for df in [tr, te]:
        df["low_diamond"] = (df["diamond_stock"] <= diamond_th).astype(int)
        df["low_gold"] = (df["gold_stock"] <= gold_th).astype(int)
        df["stagnant_pressure"] = df["stagnant"] * df["resource_pressure"]
        df["low_diamond_pressure"] = df["low_diamond"] * df["resource_pressure"]
        df["activity_growth"] = np.log1p(df["event_count"].clip(lower=0)) * np.log1p(df["level"].clip(lower=0))
        df["paid_state"] = (df["total_pay_cum"] > 0).astype(int)
        df["paid_pressure"] = df["paid_state"] * df["resource_pressure"]
    features = [
        "day",
        "level",
        "event_count",
        "stagnant",
        "low_diamond",
        "low_gold",
        "resource_pressure",
        "scarcity_index",
        "stagnant_pressure",
        "low_diamond_pressure",
        "activity_growth",
        "paid_state",
        "paid_pressure",
        "diamond_stock",
        "gold_stock",
        "basic_reduce",
        "coin_reduce",
        "gem_reduce",
        "speedup_reduce",
    ]
    targets = ["inactive", "converted_or_paid_more", "paid_active", "free_active"]
    rows, coef_rows = [], []
    for target in targets:
        ytr = (tr["next_state"] == target).astype(int).to_numpy()
        yte = (te["next_state"] == target).astype(int).to_numpy()
        if ytr.sum() < 10:
            continue
        Xtr = pd.DataFrame({f: np.log1p(tr[f].clip(lower=0)) if f.endswith("_stock") or f.endswith("_reduce") or f == "event_count" else tr[f] for f in features})
        Xte = pd.DataFrame({f: np.log1p(te[f].clip(lower=0)) if f.endswith("_stock") or f.endswith("_reduce") or f == "event_count" else te[f] for f in features})
        use_balanced = (ytr.mean() < 0.08 or ytr.mean() > 0.92) and target != "converted_or_paid_more"
        pred, info, beta = logistic_fit_predict(Xtr, ytr, Xte, balanced=use_balanced)
        rows.append(
            {
                "task": f"transition_to_{target}",
                "model": "scarcity_state_transition_logistic",
                "logloss": float(-np.mean(yte * np.log(pred + EPS) + (1 - yte) * np.log(1 - pred + EPS))),
                "rank_corr": float(pd.Series(pred).corr(pd.Series(yte), method="spearman")),
                "base_rate_test": float(yte.mean()),
                "lambda": info["lambda"],
            }
        )
        for f, b in zip(["intercept"] + features, beta):
            coef_rows.append({"target_state": target, "feature": f, "coef": b})
    coef = pd.DataFrame(coef_rows).sort_values("coef", key=lambda s: s.abs(), ascending=False)
    return pd.DataFrame(rows), coef


def fit_resource_dynamics(daily: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = daily.sort_values(["account_id", "day"]).copy()
    # Five-dimensional state:
    # R resource pressure, G growth velocity, C coin stock, D diamond stock,
    # P cumulative payment tendency. This is the Q2 counterpart of Q1's
    # activity-growth-payment dynamics.
    df["R"] = df["resource_pressure"].clip(-20, 20)
    df["G"] = df["level_gain"].clip(0, 10)
    df["C"] = np.log1p(df["gold_stock"].clip(lower=0))
    df["D"] = np.log1p(df["diamond_stock"].clip(lower=0))
    df["P"] = np.log1p(df["total_pay_cum"].clip(lower=0))
    states = ["R", "G", "C", "D", "P"]
    nxt = df[["account_id", "day"] + states].copy()
    nxt["day"] -= 1
    nxt = nxt.rename(columns={s: f"{s}_next" for s in states})
    cur = df[df["day"] < DAY_MAX].merge(nxt, on=["account_id", "day"], how="inner")
    cur = cur[cur["active"] == 1].copy()

    def basis(row):
        R, G, C, D, P = [row[s] for s in states]
        return np.array(
            [
                1,
                R,
                G,
                C,
                D,
                P,
                R * G,
                R * D,
                G * P,
                C * D,
                D * P,
                R * R,
                G * G,
                P * P,
                row["day"] / 30,
                row["stagnant"],
                np.log1p(row["event_count"]),
            ],
            dtype=float,
        )

    Phi = np.vstack([basis(r) for _, r in cur.iterrows()])
    Y = np.vstack([(cur[f"{s}_next"].to_numpy(float) - cur[s].to_numpy(float)) for s in states]).T
    Phi = np.nan_to_num(Phi, nan=0.0, posinf=0.0, neginf=0.0)
    Y = np.nan_to_num(Y, nan=0.0, posinf=0.0, neginf=0.0)
    best = None
    for lam in [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1, 3, 10]:
        reg = np.eye(Phi.shape[1]) * lam
        reg[0, 0] = 0
        B = np.linalg.pinv(Phi.T @ Phi + reg) @ Phi.T @ Y
        pred = Phi @ B
        mse = float(np.mean((pred - Y) ** 2))
        if best is None or mse < best["transition_mse"]:
            best = {"lambda": lam, "transition_mse": mse, "B": B}
    basis_names = [
        "1",
        "R",
        "G",
        "C",
        "D",
        "P",
        "R*G",
        "R*D",
        "G*P",
        "C*D",
        "D*P",
        "R^2",
        "G^2",
        "P^2",
        "t",
        "stagnant",
        "log_event",
    ]
    coef_rows = []
    for eq_idx, state in enumerate(states):
        for b, c in zip(basis_names, best["B"][:, eq_idx]):
            coef_rows.append({"equation": f"d{state}_dt", "basis": b, "coef": c})
    diagnostics = pd.DataFrame(
        [
            {
                "model": "resource_growth_payment_coupled_ode",
                "lambda": best["lambda"],
                "transition_mse": best["transition_mse"],
                "n_transitions": len(cur),
            }
        ]
    )
    return diagnostics, pd.DataFrame(coef_rows)


def gift_recommendation(train_daily: pd.DataFrame, threshold: dict) -> pd.DataFrame:
    th = threshold.get("diamond_threshold", np.nan)
    active = train_daily[(train_daily["active"] == 1) & (train_daily["diamond_stock"] <= th) & (train_daily["stagnant"] == 1)].copy()
    if active.empty:
        active = train_daily[(train_daily["active"] == 1) & (train_daily["stagnant"] == 1)].copy()
    rows = []
    for res in ["food", "wood", "stone", "coin", "gem", "speedup"]:
        get = active[f"{res}_get"].sum() if f"{res}_get" in active else 0.0
        red = active[f"{res}_reduce"].sum() if f"{res}_reduce" in active else 0.0
        rows.append({"resource": res, "reduce": red, "get": get, "deficit_ratio": float((red + 1) / (get + 1)), "net_deficit": float(red - get)})
    out = pd.DataFrame(rows).sort_values(["deficit_ratio", "net_deficit"], ascending=False)
    out["recommendation"] = ""
    if not out.empty:
        top = out.iloc[0]["resource"]
        out.loc[out.index[0], "recommendation"] = f"priority supply: {top}; pair with small diamonds/speedup to avoid repeated stagnation"
    return out


def main() -> None:
    reset_public_output()
    train_daily, train_user = build_panel(TRAIN)
    test_daily, test_user = build_panel(TEST)
    train_daily.to_csv(CACHE_DIR / "q2_train_daily_panel.csv", index=False, encoding="utf-8-sig")
    test_daily.to_csv(CACHE_DIR / "q2_test_daily_panel.csv", index=False, encoding="utf-8-sig")
    train_user.to_csv(CACHE_DIR / "q2_train_user_features.csv", index=False, encoding="utf-8-sig")
    test_user.to_csv(CACHE_DIR / "q2_test_user_features.csv", index=False, encoding="utf-8-sig")

    growth_metrics, growth_coef = panel_growth_model(train_daily, test_daily)
    card = card_point_analysis(train_daily)
    threshold, best_th = threshold_analysis(train_daily, test_daily)
    causal_metrics, causal_coef = scarcity_lag_causal_model(train_daily, test_daily, best_th.get("diamond_threshold", 100.0))
    first_pay_table, first_pay_metrics = first_payment_analysis(train_user, test_user)
    pay_metrics, pay_coef = total_pay_model(train_user, test_user)
    transition_metrics, transition_coef = state_transition_model(train_daily, test_daily)
    dyn_metrics, dyn_coef = fit_resource_dynamics(train_daily)
    gift = gift_recommendation(train_daily, best_th)

    metrics = pd.concat([growth_metrics, causal_metrics, first_pay_metrics, pay_metrics, transition_metrics, dyn_metrics], ignore_index=True)
    metrics.to_csv(OUT_DIR / "q2_model_metrics.csv", index=False, encoding="utf-8-sig")
    growth_coef.to_csv(CACHE_DIR / "q2_growth_model_coefficients.csv", index=False, encoding="utf-8-sig")
    card.to_csv(OUT_DIR / "q2_growth_card_points.csv", index=False, encoding="utf-8-sig")
    threshold.to_csv(OUT_DIR / "q2_diamond_thresholds.csv", index=False, encoding="utf-8-sig")
    first_pay_table.to_csv(OUT_DIR / "q2_first_payment_analysis.csv", index=False, encoding="utf-8-sig")
    pay_coef.to_csv(OUT_DIR / "q2_total_pay_key_factors.csv", index=False, encoding="utf-8-sig")
    causal_coef.to_csv(CACHE_DIR / "q2_lagged_scarcity_coefficients.csv", index=False, encoding="utf-8-sig")
    transition_coef.to_csv(CACHE_DIR / "q2_state_transition_coefficients.csv", index=False, encoding="utf-8-sig")
    dyn_coef.to_csv(CACHE_DIR / "q2_coupled_dynamics_coefficients.csv", index=False, encoding="utf-8-sig")
    gift.to_csv(OUT_DIR / "q2_rescue_package_proxy.csv", index=False, encoding="utf-8-sig")

    print(f"Done. Outputs written to: {OUT_DIR}")


if __name__ == "__main__":
    main()
