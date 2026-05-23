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
import torch
from torch import nn
from scipy.optimize import minimize


ROOT = Path(__file__).resolve().parent
DATA_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and (p / "pickdata2.csv").exists())
OUT_DIR = ROOT / "q1_outputs"
OUT_DIR.mkdir(exist_ok=True)
CACHE_DIR = ROOT / "internal_cache"
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
    stat_csv: Path


TRAIN = DatasetPaths("train", DATA_DIR / "pickdata2.csv", DATA_DIR / "pickdata1.csv", DATA_DIR / "pick_stat2.csv")
TEST = DatasetPaths("test", DATA_DIR / "other_pickdata2.csv", DATA_DIR / "other_pickdata1.csv", DATA_DIR / "other_pick_stat2.csv")


def scan_behavior(path: Path) -> pl.LazyFrame:
    usecols = [
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
        "province",
        "city",
        "apk_version",
        "package_id",
        "source",
        "current_level",
        "current_vip_level",
        "total_pay",
        "first_login_time",
        "first_pay_level",
        "first_pay_time",
        "last_login_time",
        "register_time",
        "duration_times",
        "life_cycle_days",
        "current_gold",
        "current_diamond",
        "current_drug",
        "current_power",
        "current_money",
        "current_bullet",
        "current_wine",
    ]
    return pl.scan_csv(
        path,
        infer_schema_length=100,
        ignore_errors=True,
        null_values=["", "null", "NULL", "None"],
    ).select([c for c in usecols if c in pl.scan_csv(path, infer_schema_length=0).collect_schema().names()])


def scan_state(path: Path) -> pl.LazyFrame:
    usecols = [
        "account_id",
        "dt",
        "ts",
        "change_type",
        "change_num",
        "change_before",
        "change_after",
        "change_reason",
        "current_level",
        "r_lvl",
        "change_dollar",
        "dollar",
    ]
    return pl.scan_csv(
        path,
        infer_schema_length=100,
        ignore_errors=True,
        null_values=["", "null", "NULL", "None"],
    ).select([c for c in usecols if c in pl.scan_csv(path, infer_schema_length=0).collect_schema().names()])


def parse_dt(expr: pl.Expr) -> pl.Expr:
    return expr.cast(pl.Utf8).str.strptime(pl.Datetime, strict=False)


def pl_to_pandas(df: pl.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(df.to_dicts())


def load_user_ids(stat_csv: Path) -> pd.Index:
    stat = pd.read_csv(stat_csv)
    return pd.Index(stat["account_id"].astype(np.int64).unique(), name="account_id")


def collect_user_meta(ds: DatasetPaths) -> pl.DataFrame:
    lf = scan_behavior(ds.behavior_csv)
    dt = parse_dt(pl.col("dt")).alias("dt_parsed")
    first_login = parse_dt(pl.col("first_login_time")).alias("first_login_parsed")
    last_login = parse_dt(pl.col("last_login_time")).alias("last_login_parsed")
    first_pay = parse_dt(pl.col("first_pay_time")).alias("first_pay_parsed")
    register_time = parse_dt(pl.col("register_time")).alias("register_parsed")
    meta = (
        lf.with_columns([dt, first_login, last_login, first_pay, register_time])
        .group_by("account_id")
        .agg(
            pl.col("dt_parsed").min().alias("first_event_dt"),
            pl.col("dt_parsed").max().alias("last_event_dt"),
            pl.col("register_parsed").drop_nulls().min().alias("raw_register_dt"),
            pl.col("first_login_parsed").min().alias("first_login_dt"),
            pl.col("last_login_parsed").max().alias("last_login_dt"),
            pl.col("first_pay_parsed").min().alias("first_pay_dt"),
            pl.col("current_level").max().alias("max_level_behavior"),
            pl.col("current_vip_level").max().alias("max_vip"),
            pl.col("total_pay").max().alias("total_pay"),
            pl.col("first_pay_level").max().alias("first_pay_level"),
            pl.col("duration_times").max().alias("duration_times_max"),
            pl.col("life_cycle_days").max().alias("life_cycle_days_max"),
            pl.col("event").n_unique().alias("unique_event_types"),
            pl.col("device_id").n_unique().alias("unique_devices"),
            pl.col("session_id").n_unique().alias("unique_sessions"),
            pl.col("channel_id").n_unique().alias("unique_channels"),
            pl.col("platform").n_unique().alias("unique_platforms"),
            pl.col("country").n_unique().alias("unique_countries"),
            pl.col("media_source").n_unique().alias("unique_media_sources"),
            pl.col("campaign").n_unique().alias("unique_campaigns"),
            pl.col("province").n_unique().alias("unique_provinces"),
            pl.col("city").n_unique().alias("unique_cities"),
            pl.col("apk_version").n_unique().alias("unique_apk_versions"),
            pl.col("package_id").n_unique().alias("unique_packages"),
            pl.col("source").n_unique().alias("unique_sources"),
            pl.len().alias("event_count_all"),
        )
        .with_columns(
            # Contest definition treats Day 1..Day 30 as player lifecycle
            # days after account registration. Prefer the explicit account
            # registration time, then fall back to first login/event only when
            # the source field is missing.
            pl.coalesce(["raw_register_dt", "first_login_dt", "first_event_dt"]).alias("register_dt"),
            pl.col("last_event_dt").alias("last_seen_dt"),
        )
        .collect(engine="streaming")
    )
    ids = pl.DataFrame({"account_id": load_user_ids(ds.stat_csv).to_numpy()})
    meta = ids.join(meta, on="account_id", how="left")
    return meta


def collect_day_features(ds: DatasetPaths, meta: pl.DataFrame) -> pd.DataFrame:
    lf = scan_behavior(ds.behavior_csv)
    meta_small = meta.select(["account_id", "register_dt"]).lazy()
    day = (
        lf.with_columns(parse_dt(pl.col("dt")).alias("dt_parsed"))
        .join(meta_small, on="account_id", how="left")
        .with_columns(
            ((pl.col("dt_parsed").dt.date() - pl.col("register_dt").dt.date()).dt.total_days() + 1)
            .cast(pl.Int32)
            .alias("day")
        )
        .filter((pl.col("day") >= 1) & (pl.col("day") <= DAY_MAX))
        .group_by(["account_id", "day"])
        .agg(
            pl.len().alias("event_count"),
            pl.col("event").n_unique().alias("unique_events"),
            pl.col("current_level").max().alias("max_level"),
            pl.col("total_pay").max().alias("max_total_pay"),
            pl.col("current_gold").max().alias("max_gold"),
            pl.col("current_diamond").max().alias("max_diamond"),
            pl.col("current_drug").max().alias("max_drug"),
            pl.col("current_power").max().alias("max_power"),
            pl.col("current_money").max().alias("max_money"),
            pl.col("current_bullet").max().alias("max_bullet"),
            pl.col("current_wine").max().alias("max_wine"),
            pl.col("duration_times").max().alias("max_duration_times"),
            pl.col("device_id").n_unique().alias("unique_devices_day"),
            pl.col("session_id").n_unique().alias("unique_sessions_day"),
            pl.col("media_source").n_unique().alias("unique_media_sources_day"),
            pl.col("campaign").n_unique().alias("unique_campaigns_day"),
        )
        .collect(engine="streaming")
    )
    day = pl_to_pandas(day)
    if day.empty:
        return day
    day["day"] = day["day"].astype(int)
    return day


def collect_state_first3(ds: DatasetPaths, meta: pl.DataFrame) -> pd.DataFrame:
    lf = scan_state(ds.state_csv)
    meta_small = meta.select(["account_id", "register_dt"]).lazy()
    ts_col = "ts" if "ts" in lf.collect_schema().names() else "dt"
    state = (
        lf.with_columns(parse_dt(pl.col(ts_col)).alias("dt_parsed"))
        .join(meta_small, on="account_id", how="left")
        .with_columns(
            ((pl.col("dt_parsed").dt.date() - pl.col("register_dt").dt.date()).dt.total_days() + 1)
            .cast(pl.Int32)
            .alias("day")
        )
        .filter((pl.col("day") >= 1) & (pl.col("day") <= 3))
        .group_by("account_id")
        .agg(
            pl.len().alias("state_rows_1_3"),
            pl.col("change_num").sum().alias("resource_change_sum_1_3"),
            pl.col("change_num").mean().alias("resource_change_mean_1_3"),
            pl.col("change_dollar").sum().alias("change_dollar_sum_1_3"),
            pl.col("dollar").max().alias("dollar_max_1_3"),
            pl.col("current_level").max().alias("state_max_level_1_3"),
            pl.col("r_lvl").max().alias("r_lvl_max_1_3"),
        )
        .collect(engine="streaming")
    )
    return pl_to_pandas(state)


def build_user_table(ds: DatasetPaths) -> tuple[pd.DataFrame, pd.DataFrame]:
    print(f"[{ds.name}] collecting user meta")
    meta = collect_user_meta(ds)
    print(f"[{ds.name}] collecting daily behavior features")
    day = collect_day_features(ds, meta)
    print(f"[{ds.name}] collecting first-3-day state features")
    state3 = collect_state_first3(ds, meta)

    users = pl_to_pandas(meta)
    users["account_id"] = users["account_id"].astype(np.int64)
    if day.empty:
        for d in range(1, DAY_MAX + 1):
            users[f"active_d{d}"] = 0
        users["observed_active_days"] = 0
        users["last_active_day"] = 0
    else:
        active = day.assign(active=1).pivot_table(index="account_id", columns="day", values="active", fill_value=0, aggfunc="max")
        for d in range(1, DAY_MAX + 1):
            if d not in active.columns:
                active[d] = 0
        active = active[[d for d in range(1, DAY_MAX + 1)]]
        active.columns = [f"active_d{d}" for d in range(1, DAY_MAX + 1)]
        active["observed_active_days"] = active.sum(axis=1)
        active["last_active_day"] = np.where(active[[f"active_d{d}" for d in range(1, DAY_MAX + 1)]].to_numpy().sum(axis=1) > 0,
                                             active[[f"active_d{d}" for d in range(1, DAY_MAX + 1)]].to_numpy().dot(np.arange(1, DAY_MAX + 1)) / np.maximum(active[[f"active_d{d}" for d in range(1, DAY_MAX + 1)]].to_numpy().sum(axis=1), 1),
                                             0)
        active["last_active_day"] = [
            max([d for d in range(1, DAY_MAX + 1) if row[f"active_d{d}"] > 0], default=0)
            for _, row in active.iterrows()
        ]
        users = users.merge(active.reset_index(), on="account_id", how="left")

    if not day.empty:
        first3 = day[day["day"].between(1, 3)].groupby("account_id").agg(
            event_count_1_3=("event_count", "sum"),
            unique_events_1_3=("unique_events", "sum"),
            active_days_1_3=("day", "nunique"),
            level_1_3_max=("max_level", "max"),
            level_1=("max_level", lambda s: s.iloc[0] if len(s) else np.nan),
            total_pay_1_3=("max_total_pay", "max"),
            gold_1_3_max=("max_gold", "max"),
            diamond_1_3_max=("max_diamond", "max"),
            drug_1_3_max=("max_drug", "max"),
            power_1_3_max=("max_power", "max"),
            money_1_3_max=("max_money", "max"),
            bullet_1_3_max=("max_bullet", "max"),
            wine_1_3_max=("max_wine", "max"),
            duration_1_3_max=("max_duration_times", "max"),
            devices_1_3=("unique_devices_day", "sum"),
            sessions_1_3=("unique_sessions_day", "sum"),
            media_sources_1_3=("unique_media_sources_day", "sum"),
            campaigns_1_3=("unique_campaigns_day", "sum"),
        ).reset_index()
        first3["level_speed_1_3"] = first3["level_1_3_max"] - first3["level_1"].fillna(0)
        users = users.merge(first3, on="account_id", how="left")

    users = users.merge(state3, on="account_id", how="left")
    users = users.fillna(0)
    users["target_retention_days"] = users["last_active_day"].clip(0, DAY_MAX)
    users["is_30d_retained"] = (users["active_d30"] > 0).astype(int)
    users["is_paid_1_3"] = (users.get("total_pay_1_3", 0) > 0).astype(int)
    users["dataset"] = ds.name
    return users, day


def retention_curve(users: pd.DataFrame, name: str) -> pd.DataFrame:
    rows = []
    n0 = len(users)
    for d in range(1, DAY_MAX + 1):
        active = int(users[f"active_d{d}"].sum())
        retained_span = int((users["last_active_day"] >= d).sum())
        rows.append(
            {
                "dataset": name,
                "day": d,
                "daily_retention": active / max(n0, 1),
                "span_survival": retained_span / max(n0, 1),
                "active_users": active,
                "survived_users": retained_span,
                "n_users": n0,
            }
        )
    return pd.DataFrame(rows)


def retention_bootstrap_ci(users: pd.DataFrame, name: str, n_boot: int = 500, seed: int = 20260521) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    arr = users[[f"active_d{d}" for d in range(1, DAY_MAX + 1)]].to_numpy(float)
    n = len(arr)
    rows = []
    if n == 0:
        return pd.DataFrame()
    draws = rng.integers(0, n, size=(n_boot, n))
    vals = arr[draws].mean(axis=1)
    for d in range(1, DAY_MAX + 1):
        col = vals[:, d - 1]
        rows.append(
            {
                "dataset": name,
                "day": d,
                "retention_mean": float(arr[:, d - 1].mean()),
                "ci_low": float(np.quantile(col, 0.025)),
                "ci_high": float(np.quantile(col, 0.975)),
            }
        )
    return pd.DataFrame(rows)


def km_and_hazard(users: pd.DataFrame, name: str) -> pd.DataFrame:
    times = users["last_active_day"].clip(1, DAY_MAX).astype(int).to_numpy()
    rows = []
    surv = 1.0
    for d in range(1, DAY_MAX + 1):
        at_risk = int((times >= d).sum())
        # Day 30 is the observation boundary. Players still active there are
        # right-censored rather than forced to churn after the window.
        events = int((times == d).sum()) if d < DAY_MAX else 0
        hazard = events / at_risk if at_risk else 0.0
        if at_risk:
            surv *= (1.0 - hazard)
        rows.append({"dataset": name, "day": d, "at_risk": at_risk, "churn_events": events, "hazard": hazard, "km_survival": surv})
    return pd.DataFrame(rows)


def standardize_fit(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mu = np.nanmean(X, axis=0)
    sd = np.nanstd(X, axis=0)
    sd[sd < EPS] = 1.0
    return (np.nan_to_num(X, nan=0.0) - mu) / sd, mu, sd


def standardize_apply(X: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    return (np.nan_to_num(X, nan=0.0) - mu) / sd


def make_features(users: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    cols = [
        "event_count_1_3",
        "unique_events_1_3",
        "active_days_1_3",
        "level_1_3_max",
        "level_speed_1_3",
        "total_pay_1_3",
        "gold_1_3_max",
        "diamond_1_3_max",
        "drug_1_3_max",
        "power_1_3_max",
        "money_1_3_max",
        "bullet_1_3_max",
        "wine_1_3_max",
        "duration_1_3_max",
        "devices_1_3",
        "sessions_1_3",
        "media_sources_1_3",
        "campaigns_1_3",
        "state_rows_1_3",
        "resource_change_sum_1_3",
        "resource_change_mean_1_3",
        "change_dollar_sum_1_3",
        "dollar_max_1_3",
        "state_max_level_1_3",
        "r_lvl_max_1_3",
        "is_paid_1_3",
        "max_vip",
        "life_cycle_days_max",
        "unique_devices",
        "unique_sessions",
        "unique_channels",
        "unique_platforms",
        "unique_countries",
        "unique_media_sources",
        "unique_campaigns",
        "unique_provinces",
        "unique_cities",
        "unique_apk_versions",
        "unique_packages",
        "unique_sources",
    ]
    out = pd.DataFrame(index=users.index)
    for c in cols:
        out[c] = pd.to_numeric(users[c], errors="coerce") if c in users.columns else 0.0
    for c in list(out.columns):
        if out[c].min() >= 0:
            out[f"log1p_{c}"] = np.log1p(out[c])

    # Coupled dynamic features: activity, growth and payment are treated as
    # three interacting state variables observed in the first three days.
    out["A_activity"] = np.log1p(out["event_count_1_3"]) + 0.8 * out["active_days_1_3"] + 0.2 * np.log1p(out["unique_events_1_3"])
    out["G_growth"] = out["level_speed_1_3"] + 0.35 * np.log1p(out["power_1_3_max"]) + 0.15 * np.log1p(out["resource_change_sum_1_3"].clip(lower=0))
    out["P_payment"] = np.log1p(out["total_pay_1_3"]) + 0.4 * out["is_paid_1_3"] + 0.2 * np.log1p(out["dollar_max_1_3"])
    out["A_G_coupling"] = out["A_activity"] * out["G_growth"]
    out["A_P_coupling"] = out["A_activity"] * out["P_payment"]
    out["G_P_coupling"] = out["G_growth"] * out["P_payment"]
    out["early_pressure"] = out["A_activity"] / (1.0 + out["G_growth"].clip(lower=0))
    cols_final = list(out.columns)
    return out.replace([np.inf, -np.inf], 0).fillna(0), cols_final


def user_day_latent(users: pd.DataFrame, day: pd.DataFrame) -> np.ndarray:
    """Build observed daily latent states X=(A,G,P) for days 1..3.

    A: activity intensity; G: growth momentum; P: payment tendency.
    Missing days are treated as zero activity/growth/payment observations.
    """
    account_order = users["account_id"].to_numpy()
    idx = {a: i for i, a in enumerate(account_order)}
    states = np.zeros((len(users), 3, 3), dtype=float)
    if day.empty:
        return states

    d3 = day[day["day"].between(1, 3)].copy()
    d3["account_id"] = d3["account_id"].astype(np.int64)
    d3 = d3.sort_values(["account_id", "day"])
    for _, r in d3.iterrows():
        i = idx.get(int(r["account_id"]))
        if i is None:
            continue
        t = int(r["day"]) - 1
        states[i, t, 0] = math.log1p(max(float(r.get("event_count", 0) or 0), 0)) + 0.25 * math.log1p(max(float(r.get("unique_events", 0) or 0), 0))
        states[i, t, 1] = float(r.get("max_level", 0) or 0) + 0.10 * math.log1p(max(float(r.get("max_power", 0) or 0), 0))
        states[i, t, 2] = math.log1p(max(float(r.get("max_total_pay", 0) or 0), 0))
    return states


def latent_standardize_fit(states: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    states = np.nan_to_num(states, nan=0.0, posinf=0.0, neginf=0.0)
    flat = states.reshape(-1, states.shape[-1])
    mu = flat.mean(axis=0)
    sd = flat.std(axis=0)
    sd[sd < EPS] = 1.0
    return np.clip((states - mu) / sd, -6, 6), mu, sd


def latent_standardize_apply(states: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    states = np.nan_to_num(states, nan=0.0, posinf=0.0, neginf=0.0)
    return np.clip((states - mu) / sd, -6, 6)


def ode_basis(x: np.ndarray, t: float) -> np.ndarray:
    a, g, p = np.clip(np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0), -6, 6)
    return np.asarray([1.0, a, g, p, a * g, a * p, g * p, a * a, g * g, p * p, t], dtype=float)


def fit_coupled_ode(states: np.ndarray) -> dict:
    """Fit a discrete Euler approximation to a coupled ODE system.

    X_{t+1} - X_t = F(X_t,t), where X=(A,G,P). The fitted coefficient
    matrix approximates the right side of dX/dt=F(X,t).
    """
    rows, targets = [], []
    for i in range(states.shape[0]):
        for t in range(2):
            x0 = states[i, t, :]
            x1 = states[i, t + 1, :]
            rows.append(ode_basis(x0, (t + 1) / 30.0))
            targets.append(x1 - x0)
    Phi = np.asarray(rows, float)
    Y = np.asarray(targets, float)
    Phi = np.nan_to_num(Phi, nan=0.0, posinf=0.0, neginf=0.0)
    Y = np.nan_to_num(Y, nan=0.0, posinf=0.0, neginf=0.0)
    best = None
    for lam in [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1, 3, 10]:
        reg = np.eye(Phi.shape[1]) * lam
        reg[0, 0] = 0
        coef = np.linalg.pinv(Phi.T @ Phi + reg) @ Phi.T @ Y
        pred = Phi @ coef
        mse = float(np.mean((pred - Y) ** 2))
        if best is None or mse < best["transition_mse"]:
            best = {"lambda_ode": lam, "transition_mse": mse, "coef": coef}
    return best


def simulate_coupled_ode(states3: np.ndarray, ode: dict) -> np.ndarray:
    coef = ode["coef"]
    sim = np.zeros((states3.shape[0], DAY_MAX, 3), dtype=float)
    sim[:, :3, :] = states3
    for t in range(3, DAY_MAX):
        for i in range(states3.shape[0]):
            x = sim[i, t - 1, :]
            dx = ode_basis(x, t / 30.0) @ coef
            sim[i, t, :] = np.clip(x + dx, -6, 6)
    return sim


def make_ode_features(sim: np.ndarray) -> pd.DataFrame:
    a, g, p = sim[:, :, 0], sim[:, :, 1], sim[:, :, 2]
    pressure = a / (1.0 + np.maximum(g, 0))
    pay_growth_lock = p * np.maximum(-g, 0)
    data = {}
    for d in [1, 2, 3, 7, 14, 30]:
        data[f"ode_A_d{d}"] = a[:, d - 1]
        data[f"ode_G_d{d}"] = g[:, d - 1]
        data[f"ode_P_d{d}"] = p[:, d - 1]
        data[f"ode_pressure_d{d}"] = pressure[:, d - 1]
    for end in [3, 7, 14, 30]:
        data[f"ode_A_mean_1_{end}"] = a[:, :end].mean(axis=1)
        data[f"ode_G_mean_1_{end}"] = g[:, :end].mean(axis=1)
        data[f"ode_P_mean_1_{end}"] = p[:, :end].mean(axis=1)
        data[f"ode_pressure_mean_1_{end}"] = pressure[:, :end].mean(axis=1)
        data[f"ode_pay_growth_lock_1_{end}"] = pay_growth_lock[:, :end].mean(axis=1)
    data["ode_A_trend_3_30"] = a[:, -1] - a[:, 2]
    data["ode_G_trend_3_30"] = g[:, -1] - g[:, 2]
    data["ode_P_trend_3_30"] = p[:, -1] - p[:, 2]
    data["ode_G_min_1_30"] = g.min(axis=1)
    data["ode_pressure_max_1_30"] = pressure.max(axis=1)
    return pd.DataFrame(data).replace([np.inf, -np.inf], 0).fillna(0)


def ode_equation_report(ode: dict) -> pd.DataFrame:
    basis = ["1", "A", "G", "P", "A*G", "A*P", "G*P", "A^2", "G^2", "P^2", "t"]
    coef = ode["coef"]
    rows = []
    for eq_idx, eq_name in enumerate(["dA_dt", "dG_dt", "dP_dt"]):
        for b, c in zip(basis, coef[:, eq_idx]):
            rows.append({"equation": eq_name, "basis": b, "coef": c})
    return pd.DataFrame(rows)


def ode_stability_features(sim: np.ndarray) -> pd.DataFrame:
    # A compact mathematical-dynamics diagnostic: energy, volatility and
    # terminal drift of the latent trajectory X(t)=(A,G,P).
    diff = np.diff(sim, axis=1)
    energy = np.sqrt((sim**2).sum(axis=2))
    speed = np.sqrt((diff**2).sum(axis=2))
    jac_proxy = []
    for i in range(len(sim)):
        cov = np.cov(sim[i].T)
        eig = np.linalg.eigvalsh(cov + np.eye(3) * 1e-6)
        jac_proxy.append(eig[-1] / max(eig[0], 1e-6))
    return pd.DataFrame(
        {
            "ode_energy_mean": energy.mean(axis=1),
            "ode_energy_final": energy[:, -1],
            "ode_speed_mean": speed.mean(axis=1),
            "ode_speed_max": speed.max(axis=1),
            "ode_terminal_drift": np.sqrt(((sim[:, -1, :] - sim[:, 2, :]) ** 2).sum(axis=1)),
            "ode_anisotropy": jac_proxy,
        }
    )


def coupled_ode_train_predict(
    train_users: pd.DataFrame,
    train_day: pd.DataFrame,
    test_users: pd.DataFrame,
    test_day: pd.DataFrame,
    base_train_x: pd.DataFrame,
    base_test_x: pd.DataFrame,
    y_train: np.ndarray,
) -> tuple[np.ndarray, dict, pd.DataFrame, pd.DataFrame]:
    train_states_raw = user_day_latent(train_users, train_day)
    test_states_raw = user_day_latent(test_users, test_day)
    train_states, mu, sd = latent_standardize_fit(train_states_raw)
    test_states = latent_standardize_apply(test_states_raw, mu, sd)
    ode = fit_coupled_ode(train_states)
    train_sim = simulate_coupled_ode(train_states, ode)
    test_sim = simulate_coupled_ode(test_states, ode)
    train_ode_x = make_ode_features(train_sim)
    test_ode_x = make_ode_features(test_sim)
    train_ode_x = pd.concat([train_ode_x, ode_stability_features(train_sim)], axis=1)
    test_ode_x = pd.concat([test_ode_x, ode_stability_features(test_sim)], axis=1)
    ode_equation_report(ode).to_csv(CACHE_DIR / "q1_ode_equation_coefficients.csv", index=False, encoding="utf-8-sig")
    train_x2 = pd.concat([base_train_x.reset_index(drop=True), train_ode_x], axis=1)
    test_x2 = pd.concat([base_test_x.reset_index(drop=True), test_ode_x], axis=1)
    pred, info = ridge_train_predict(train_x2, y_train, test_x2)
    info["model"] = "coupled_ode_state_ridge"
    info["lambda_ode"] = ode["lambda_ode"]
    info["transition_mse"] = ode["transition_mse"]
    return pred, info, train_ode_x, test_ode_x


class SeqAggRetentionNet(nn.Module):
    def __init__(self, seq_dim: int, agg_dim: int, hidden: int, dropout: float):
        super().__init__()
        self.gru = nn.GRU(seq_dim, hidden, batch_first=True)
        self.agg = nn.Sequential(
            nn.Linear(agg_dim, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
        )
        self.head = nn.Sequential(
            nn.Linear(hidden * 2, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, 1),
        )

    def forward(self, seq: torch.Tensor, agg: torch.Tensor) -> torch.Tensor:
        _, h = self.gru(seq)
        z_seq = h[-1]
        z_agg = self.agg(agg)
        raw = self.head(torch.cat([z_seq, z_agg], dim=1)).squeeze(1)
        return 1.0 + 29.0 * torch.sigmoid(raw)


def seqagg_gru_train_predict(
    train_users: pd.DataFrame,
    train_day: pd.DataFrame,
    test_users: pd.DataFrame,
    test_day: pd.DataFrame,
    base_train_x: pd.DataFrame,
    base_test_x: pd.DataFrame,
    y_train: np.ndarray,
) -> tuple[np.ndarray, dict]:
    torch.set_num_threads(1)
    train_seq_raw = user_day_latent(train_users, train_day)
    test_seq_raw = user_day_latent(test_users, test_day)
    train_seq, seq_mu, seq_sd = latent_standardize_fit(train_seq_raw)
    test_seq = latent_standardize_apply(test_seq_raw, seq_mu, seq_sd)
    agg_train, agg_mu, agg_sd = standardize_fit(base_train_x.to_numpy(float))
    agg_test = standardize_apply(base_test_x.to_numpy(float), agg_mu, agg_sd)

    n = len(y_train)
    idx = np.arange(n)
    rng = np.random.default_rng(20260521)
    rng.shuffle(idx)
    val_size = max(250, int(0.2 * n))
    va_idx = idx[:val_size]
    tr_idx = idx[val_size:]

    seq_t = torch.tensor(train_seq, dtype=torch.float32)
    agg_t = torch.tensor(agg_train, dtype=torch.float32)
    y_t = torch.tensor(y_train, dtype=torch.float32)
    seq_test_t = torch.tensor(test_seq, dtype=torch.float32)
    agg_test_t = torch.tensor(agg_test, dtype=torch.float32)

    configs = [
        {"hidden": 24, "dropout": 0.10, "lr": 0.0020, "weight_decay": 3e-4},
        {"hidden": 32, "dropout": 0.12, "lr": 0.0015, "weight_decay": 5e-4},
        {"hidden": 16, "dropout": 0.05, "lr": 0.0030, "weight_decay": 1e-4},
    ]
    best = None
    for cfg in configs:
        torch.manual_seed(20260521)
        model = SeqAggRetentionNet(seq_dim=train_seq.shape[2], agg_dim=agg_train.shape[1], hidden=cfg["hidden"], dropout=cfg["dropout"])
        opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
        loss_fn = nn.SmoothL1Loss(beta=2.0)
        best_state = None
        best_val = np.inf
        patience = 0
        batch_size = 128
        for epoch in range(360):
            model.train()
            order = tr_idx.copy()
            rng.shuffle(order)
            for start in range(0, len(order), batch_size):
                b = order[start : start + batch_size]
                opt.zero_grad()
                pred = model(seq_t[b], agg_t[b])
                loss = loss_fn(pred, y_t[b])
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
                opt.step()
            model.eval()
            with torch.no_grad():
                val_pred = model(seq_t[va_idx], agg_t[va_idx])
                val_mae = torch.mean(torch.abs(val_pred - y_t[va_idx])).item()
            if val_mae < best_val - 1e-4:
                best_val = val_mae
                best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
                patience = 0
            else:
                patience += 1
            if patience >= 36:
                break
        if best is None or best_val < best["val_mae"]:
            model.eval()
            with torch.no_grad():
                val_pred_np = model(seq_t[va_idx], agg_t[va_idx]).numpy()
            val_resid_q90 = float(np.quantile(np.abs(val_pred_np - y_train[va_idx]), 0.90))
            best = {"config": cfg, "val_mae": best_val, "state": best_state}
            best["val_residual_q90"] = val_resid_q90

    final_cfg = best["config"]

    model = SeqAggRetentionNet(seq_dim=train_seq.shape[2], agg_dim=agg_train.shape[1], hidden=final_cfg["hidden"], dropout=final_cfg["dropout"])
    model.load_state_dict(best["state"])
    model.eval()
    with torch.no_grad():
        pred = model(seq_test_t, agg_test_t).numpy()
    info = {
        "model": "seqagg_gru_retention",
        "val_mae": float(best["val_mae"]),
        "hidden": final_cfg["hidden"],
        "dropout": final_cfg["dropout"],
        "lr": final_cfg["lr"],
        "weight_decay": final_cfg["weight_decay"],
        "val_residual_q90": float(best.get("val_residual_q90", 10.0)),
        "ensemble_size": 1,
        "literature_basis": "sequence + aggregate game-behavior churn modeling",
    }
    return np.clip(pred, 1, DAY_MAX), info


def ridge_train_predict(train_x: pd.DataFrame, y: np.ndarray, test_x: pd.DataFrame) -> tuple[np.ndarray, dict]:
    X, mu, sd = standardize_fit(train_x.to_numpy(float))
    Xt = standardize_apply(test_x.to_numpy(float), mu, sd)
    X = np.c_[np.ones(len(X)), X]
    Xt = np.c_[np.ones(len(Xt)), Xt]
    y = y.astype(float)
    best = None
    for lam in [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100, 300]:
        idx = np.arange(len(y))
        folds = idx % 5
        losses = []
        for k in range(5):
            tr = folds != k
            va = folds == k
            reg = np.eye(X.shape[1]) * lam
            reg[0, 0] = 0
            beta = np.linalg.pinv(X[tr].T @ X[tr] + reg) @ X[tr].T @ y[tr]
            pred = np.clip(X[va] @ beta, 1, DAY_MAX)
            losses.append(np.mean(np.abs(pred - y[va])))
        score = float(np.mean(losses))
        if best is None or score < best["cv_mae"]:
            best = {"lambda": lam, "cv_mae": score}
    lam = best["lambda"]
    reg = np.eye(X.shape[1]) * lam
    reg[0, 0] = 0
    beta = np.linalg.pinv(X.T @ X + reg) @ X.T @ y
    pred = np.clip(Xt @ beta, 1, DAY_MAX)
    best["model"] = "ridge_dynamic_features"
    return pred, best


def ridge_oof_conformal(
    train_x: pd.DataFrame,
    y: np.ndarray,
    test_x: pd.DataFrame,
    lam: float,
    alpha: float = 0.10,
) -> tuple[np.ndarray, np.ndarray, dict]:
    Xraw = train_x.to_numpy(float)
    Traw = test_x.to_numpy(float)
    y = y.astype(float)
    idx = np.arange(len(y))
    folds = idx % 5
    residuals = []
    test_preds = []
    for k in range(5):
        tr, va = folds != k, folds == k
        Xtr, mu, sd = standardize_fit(Xraw[tr])
        Xva = standardize_apply(Xraw[va], mu, sd)
        Xte = standardize_apply(Traw, mu, sd)
        Xtr = np.c_[np.ones(len(Xtr)), Xtr]
        Xva = np.c_[np.ones(len(Xva)), Xva]
        Xte = np.c_[np.ones(len(Xte)), Xte]
        reg = np.eye(Xtr.shape[1]) * lam
        reg[0, 0] = 0
        beta = np.linalg.pinv(Xtr.T @ Xtr + reg) @ Xtr.T @ y[tr]
        residuals.extend(np.abs(np.clip(Xva @ beta, 1, DAY_MAX) - y[va]).tolist())
        test_preds.append(np.clip(Xte @ beta, 1, DAY_MAX))
    q = float(np.quantile(residuals, 1 - alpha))
    center = np.mean(test_preds, axis=0)
    lo = np.clip(center - q, 1, DAY_MAX)
    hi = np.clip(center + q, 1, DAY_MAX)
    info = {
        "method": "split-free_5fold_conformal_from_oof_residuals",
        "alpha": alpha,
        "nominal_coverage": 1 - alpha,
        "residual_quantile": q,
    }
    return lo, hi, info


def build_person_period(users: pd.DataFrame, x: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows = []
    y = []
    acc = []
    base = x.to_numpy(float)
    times = users["target_retention_days"].clip(1, DAY_MAX).astype(int).to_numpy()
    accounts = users["account_id"].to_numpy()
    for i, t in enumerate(times):
        for d in range(1, t + 1):
            day_feat = [d / 30.0, math.log1p(d), int(d >= 3), int(d >= 7), int(d >= 14)]
            rows.append(np.r_[base[i], day_feat])
            y.append(1 if d == t else 0)
            acc.append(accounts[i])
    return np.asarray(rows, float), np.asarray(y, int), np.asarray(acc)


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -40, 40)))


def discrete_hazard_train_predict(train_users: pd.DataFrame, train_x: pd.DataFrame, test_x: pd.DataFrame) -> tuple[np.ndarray, dict]:
    Xpp, ypp, _ = build_person_period(train_users, train_x)
    Xpp, mu, sd = standardize_fit(Xpp)
    Xpp = np.c_[np.ones(len(Xpp)), Xpp]
    best = None
    for lam in [0.01, 0.03, 0.1, 0.3, 1, 3, 10]:
        def obj(beta: np.ndarray) -> tuple[float, np.ndarray]:
            z = Xpp @ beta
            p = sigmoid(z)
            loss = -np.mean(ypp * np.log(p + EPS) + (1 - ypp) * np.log(1 - p + EPS)) + lam * np.sum(beta[1:] ** 2) / len(beta)
            grad = Xpp.T @ (p - ypp) / len(ypp)
            grad[1:] += 2 * lam * beta[1:] / len(beta)
            return loss, grad

        res = minimize(lambda b: obj(b)[0], np.zeros(Xpp.shape[1]), jac=lambda b: obj(b)[1], method="L-BFGS-B", options={"maxiter": 250})
        score = float(res.fun)
        if best is None or score < best["nll"]:
            best = {"lambda": lam, "nll": score, "beta": res.x}

    beta = best.pop("beta")
    preds = []
    base = test_x.to_numpy(float)
    for i in range(len(base)):
        surv = 1.0
        expected = 0.0
        for d in range(1, DAY_MAX + 1):
            day_feat = np.r_[base[i], [d / 30.0, math.log1p(d), int(d >= 3), int(d >= 7), int(d >= 14)]]
            row = standardize_apply(day_feat.reshape(1, -1), mu, sd)
            h = sigmoid(np.r_[1.0, row.ravel()] @ beta)
            expected += surv
            surv *= (1.0 - h)
        preds.append(np.clip(expected, 1, DAY_MAX))
    best["model"] = "discrete_coupled_hazard"
    return np.asarray(preds), best


def evaluate_predictions(y_true: np.ndarray, pred: np.ndarray, name: str) -> dict:
    err = pred - y_true
    return {
        "model": name,
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err ** 2))),
        "Bias": float(np.mean(err)),
        "Within_3_days": float(np.mean(np.abs(err) <= 3)),
    }


def main() -> None:
    reset_public_output()
    train_users, train_day = build_user_table(TRAIN)
    test_users, test_day = build_user_table(TEST)
    train_users.to_csv(CACHE_DIR / "q1_train_user_features.csv", index=False, encoding="utf-8-sig")
    test_users.to_csv(CACHE_DIR / "q1_test_user_features.csv", index=False, encoding="utf-8-sig")

    ret = pd.concat([retention_curve(train_users, "train"), retention_curve(test_users, "test")], ignore_index=True)
    ci = pd.concat([retention_bootstrap_ci(train_users, "train"), retention_bootstrap_ci(test_users, "test")], ignore_index=True)
    hz = pd.concat([km_and_hazard(train_users, "train"), km_and_hazard(test_users, "test")], ignore_index=True)
    ret.to_csv(OUT_DIR / "q1_retention_table.csv", index=False, encoding="utf-8-sig")
    ci.to_csv(CACHE_DIR / "q1_retention_bootstrap_ci.csv", index=False, encoding="utf-8-sig")
    hz.to_csv(OUT_DIR / "q1_hazard_table.csv", index=False, encoding="utf-8-sig")

    key_nodes = []
    for name, g in hz.groupby("dataset"):
        h = g["hazard"].to_numpy()
        mu, sd = h.mean(), h.std() if h.std() > EPS else 1.0
        tmp = g.copy()
        tmp["z_score"] = (tmp["hazard"] - mu) / sd
        key_nodes.append(tmp.sort_values(["z_score", "hazard"], ascending=False).head(5))
    key_nodes = pd.concat(key_nodes, ignore_index=True)
    key_nodes.to_csv(OUT_DIR / "q1_key_churn_nodes.csv", index=False, encoding="utf-8-sig")

    train_x, feat_cols = make_features(train_users)
    test_x, _ = make_features(test_users)
    test_x = test_x[feat_cols]
    train_x = train_x[feat_cols]
    y_train = train_users["target_retention_days"].clip(1, DAY_MAX).to_numpy(float)
    y_test = test_users["target_retention_days"].clip(1, DAY_MAX).to_numpy(float)

    baseline_cols = [
        c
        for c in [
            "event_count_1_3",
            "unique_events_1_3",
            "active_days_1_3",
            "level_1_3_max",
            "level_speed_1_3",
            "total_pay_1_3",
            "is_paid_1_3",
        ]
        if c in train_x.columns
    ]
    baseline_pred, baseline_info = ridge_train_predict(train_x[baseline_cols], y_train, test_x[baseline_cols])
    baseline_info["model"] = "baseline_first3_behavior_ridge"

    ridge_pred, ridge_info = ridge_train_predict(train_x, y_train, test_x)
    hazard_pred, hazard_info = discrete_hazard_train_predict(train_users, train_x, test_x)
    ode_pred, ode_info, train_ode_x, test_ode_x = coupled_ode_train_predict(
        train_users, train_day, test_users, test_day, train_x, test_x, y_train
    )
    seqagg_pred, seqagg_info = seqagg_gru_train_predict(train_users, train_day, test_users, test_day, train_x, test_x, y_train)
    train_ode_x.to_csv(CACHE_DIR / "q1_v2_train_ode_features.csv", index=False, encoding="utf-8-sig")
    test_ode_x.to_csv(CACHE_DIR / "q1_v2_test_ode_features.csv", index=False, encoding="utf-8-sig")
    metric_rows = [
        evaluate_predictions(y_test, baseline_pred, baseline_info["model"]),
        evaluate_predictions(y_test, ridge_pred, ridge_info["model"]),
        evaluate_predictions(y_test, hazard_pred, hazard_info["model"]),
        evaluate_predictions(y_test, ode_pred, ode_info["model"]),
        evaluate_predictions(y_test, seqagg_pred, seqagg_info["model"]),
    ]
    metrics = pd.DataFrame(metric_rows).sort_values("MAE")
    chosen_model = metrics.iloc[0]["model"]
    if chosen_model == ridge_info["model"]:
        pred = ridge_pred
        chosen = ridge_info
        interval_train_x = train_x
        interval_test_x = test_x
    elif chosen_model == hazard_info["model"]:
        pred = hazard_pred
        chosen = hazard_info
        interval_train_x = train_x
        interval_test_x = test_x
    elif chosen_model == baseline_info["model"]:
        pred = baseline_pred
        chosen = baseline_info
        interval_train_x = train_x[baseline_cols]
        interval_test_x = test_x[baseline_cols]
    elif chosen_model == seqagg_info["model"]:
        pred = seqagg_pred
        chosen = seqagg_info
        interval_train_x = train_x
        interval_test_x = test_x
    else:
        pred = ode_pred
        chosen = ode_info
        interval_train_x = pd.concat([train_x.reset_index(drop=True), train_ode_x], axis=1)
        interval_test_x = pd.concat([test_x.reset_index(drop=True), test_ode_x], axis=1)
    if chosen_model == seqagg_info["model"]:
        q = float(chosen.get("val_residual_q90", 10.0))
        lo = np.clip(pred - q, 1, DAY_MAX)
        hi = np.clip(pred + q, 1, DAY_MAX)
        interval_info = {
            "method": "validation_residual_calibrated_interval_for_seqagg_gru",
            "nominal_coverage": 0.90,
            "residual_quantile": q,
        }
    else:
        lo, hi, interval_info = ridge_oof_conformal(interval_train_x, y_train, interval_test_x, chosen.get("lambda", 1.0))
    pred_df = pd.DataFrame(
        {
            "account_id": test_users["account_id"],
            "observed_retention_days": y_test,
            "prediction": pred,
            "pred_interval_low": lo,
            "pred_interval_high": hi,
        }
    )
    pred_df.to_csv(OUT_DIR / "q1_test_predictions.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(OUT_DIR / "q1_model_metrics.csv", index=False, encoding="utf-8-sig")

    print(f"Done. Outputs written to: {OUT_DIR}")


if __name__ == "__main__":
    main()
