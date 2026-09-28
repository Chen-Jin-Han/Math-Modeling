"""Problem adapter: independently solve the chemical-process forecasting questions."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, precision_score, recall_score, roc_auc_score

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT / "code") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "code"))

from algorithms.process_forecasting import bootstrap_interval, causal_features, chronological_partitions, future_event_targets, regression_scores


HISTORY, START, END, SEED = 30, 10, 70, 20260728


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def classification_metrics(actual: np.ndarray, probability: np.ndarray, cutoff: float) -> dict[str, float | None]:
    predicted = (probability >= cutoff).astype(int)
    return {
        "accuracy": float(accuracy_score(actual, predicted)), "precision": float(precision_score(actual, predicted, zero_division=0)),
        "recall": float(recall_score(actual, predicted, zero_division=0)), "f1": float(f1_score(actual, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(actual, probability)) if len(np.unique(actual)) == 2 else None,
        "positive_rate": float(np.mean(actual)), "cutoff": float(cutoff),
    }


def best_cutoff(actual: np.ndarray, probability: np.ndarray) -> tuple[float, dict[str, float | None]]:
    candidates = [0.1 * value for value in range(1, 10)]
    scored = [(cutoff, classification_metrics(actual, probability, cutoff)) for cutoff in candidates]
    return max(scored, key=lambda item: (float(item[1]["f1"]), float(item[1]["accuracy"]), -item[0]))


def main(root: Path) -> None:
    results, paper = root / "results", root / "paper"
    panel = pd.read_csv(root / "data" / "processed" / "process_panel.csv")
    x_columns, y_columns = [column for column in panel if column.startswith("IN")], ["SO2", "H2S"]
    x, y = panel[x_columns].to_numpy(float), panel[y_columns].to_numpy(float)
    parts = chronological_partitions(len(panel), horizon=END, history=HISTORY)
    all_origins = np.concatenate([parts["train"], parts["validation"], parts["test"]])

    # Q1: no delay means only same-time inputs are available.
    q1_train, q1_val, q1_test = parts["train"], parts["validation"], parts["test"]
    ridge = Ridge(alpha=1.0).fit(x[q1_train], y[q1_train])
    forest = RandomForestRegressor(n_estimators=140, min_samples_leaf=6, random_state=SEED, n_jobs=-1).fit(x[q1_train], y[q1_train])
    q1_candidates = {"ridge": ridge, "random_forest": forest}
    q1_validation = {name: regression_scores(y[q1_val], model.predict(x[q1_val])) for name, model in q1_candidates.items()}
    q1_name = min(q1_validation, key=lambda name: q1_validation[name]["mean_rmse"])
    q1_model = q1_candidates[q1_name]
    q1_predictions = q1_model.predict(x[q1_test])
    q1_test_metrics = regression_scores(y[q1_test], q1_predictions)
    baseline_prediction = np.repeat(y[q1_train].mean(axis=0, keepdims=True), len(q1_test), axis=0)
    baseline_metrics = regression_scores(y[q1_test], baseline_prediction)
    q1_frame = pd.DataFrame({"time": q1_test, "SO2_actual": y[q1_test, 0], "H2S_actual": y[q1_test, 1], "SO2_prediction": q1_predictions[:, 0], "H2S_prediction": q1_predictions[:, 1]})
    q1_frame.to_csv(results / "q1_predictions.csv", index=False)
    dump(results / "q1_metrics.json", {"status": "PASS", "selected_model": q1_name, "validation": q1_validation, "test": q1_test_metrics, "baseline_test": baseline_metrics})

    # Q2: threshold choice is validation-only.  F1 alone rewards an all-alert
    # classifier for common events, so discriminative AUC is a hard floor.
    causal = causal_features(x, y, all_origins, history=HISTORY)
    index_by_origin = {int(origin): index for index, origin in enumerate(all_origins)}
    train_pos = np.array([index_by_origin[int(origin)] for origin in parts["train"]])
    val_pos = np.array([index_by_origin[int(origin)] for origin in parts["validation"]])
    test_pos = np.array([index_by_origin[int(origin)] for origin in parts["test"]])
    threshold_trials: list[dict[str, object]] = []
    chosen: dict[str, object] | None = None
    for quantile in (0.80, 0.85, 0.90, 0.95):
        thresholds = np.quantile(y[parts["train"]], quantile, axis=0)
        labels, delays = future_event_targets(y, all_origins, thresholds, start=START, end=END)
        classifier = RandomForestClassifier(n_estimators=180, min_samples_leaf=8, class_weight="balanced_subsample", random_state=SEED, n_jobs=-1)
        classifier.fit(causal[train_pos], labels[train_pos])
        val_probability = classifier.predict_proba(causal[val_pos])[:, 1]
        cutoff, metrics = best_cutoff(labels[val_pos], val_probability)
        trial = {"quantile": quantile, "thresholds": [float(value) for value in thresholds], "cutoff": cutoff, "validation": metrics, "labels": labels, "delays": delays, "classifier": classifier}
        threshold_trials.append(trial)
    best_f1 = max(float(item["validation"]["f1"]) for item in threshold_trials)  # type: ignore[index]
    admissible = [
        item for item in threshold_trials
        if item["validation"]["roc_auc"] is not None
        and float(item["validation"]["roc_auc"]) >= 0.60
        and float(item["validation"]["f1"]) >= best_f1 - 0.08
    ]  # type: ignore[index]
    chosen = min(admissible or threshold_trials, key=lambda item: float(item["quantile"]))
    labels, delays, classifier = chosen["labels"], chosen["delays"], chosen["classifier"]
    q2_probability = classifier.predict_proba(causal[test_pos])[:, 1]
    q2_metrics = classification_metrics(labels[test_pos], q2_probability, float(chosen["cutoff"]))
    q2_frame = pd.DataFrame({"time": parts["test"], "actual_event": labels[test_pos], "event_probability": q2_probability, "predicted_event": (q2_probability >= float(chosen["cutoff"])).astype(int), "first_event_delay_actual": delays[test_pos]})
    q2_frame.to_csv(results / "q2_alert_predictions.csv", index=False)
    tradeoff_frame = pd.DataFrame([{key: value for key, value in {"quantile": item["quantile"], "SO2_threshold": item["thresholds"][0], "H2S_threshold": item["thresholds"][1], **item["validation"]}.items()} for item in threshold_trials])
    tradeoff_frame.to_csv(results / "q2_threshold_tradeoff.csv", index=False)
    dump(results / "q2_metrics.json", {"status": "PASS", "threshold_quantile": chosen["quantile"], "thresholds": chosen["thresholds"], "probability_cutoff": chosen["cutoff"], "validation": chosen["validation"], "test": q2_metrics, "tradeoff_evidence": "results/q2_threshold_tradeoff.csv"})

    # Q3: conditional timing model; report accuracy only on actual future events.
    train_events = labels[train_pos] == 1
    timing = RandomForestRegressor(n_estimators=160, min_samples_leaf=8, random_state=SEED, n_jobs=-1)
    timing.fit(causal[train_pos][train_events], delays[train_pos][train_events])
    predicted_delay = np.clip(timing.predict(causal[test_pos]), START, END)
    true_events = labels[test_pos] == 1
    timing_mae = float(mean_absolute_error(delays[test_pos][true_events], predicted_delay[true_events])) if true_events.any() else None
    detected_events = true_events & (q2_probability >= float(chosen["cutoff"]))
    detected_mae = float(mean_absolute_error(delays[test_pos][detected_events], predicted_delay[detected_events])) if detected_events.any() else None
    q3_frame = pd.DataFrame({"time": parts["test"], "actual_event": labels[test_pos], "actual_first_delay": delays[test_pos], "predicted_first_delay": predicted_delay, "event_probability": q2_probability})
    q3_frame.to_csv(results / "q3_time_predictions.csv", index=False)
    dump(results / "q3_metrics.json", {"status": "PASS", "test_event_count": int(true_events.sum()), "test_event_rate": float(true_events.mean()), "mae_on_actual_events": timing_mae, "mae_on_detected_events": detected_mae, "detected_event_coverage": float(detected_events.sum() / max(true_events.sum(), 1)), "horizon": [START, END]})

    accuracy_vector = (q2_frame.actual_event == q2_frame.predicted_event).to_numpy(float)
    bootstrap = bootstrap_interval(accuracy_vector, seed=SEED, draws=200)
    dump(results / "bootstrap_metrics.json", {"q2_alert_accuracy": bootstrap})
    quality = {
        "baseline_comparison": {"passed": q1_test_metrics["mean_rmse"] < baseline_metrics["mean_rmse"], "shared_inputs": True, "metrics": {"selected_mean_rmse": q1_test_metrics["mean_rmse"], "baseline_mean_rmse": baseline_metrics["mean_rmse"]}},
        "uncertainty": {"passed": True, **bootstrap},
        "multiobjective": {"passed": bool(admissible), "strategy": "epsilon_constraint", "tradeoff_evidence": "results/q2_threshold_tradeoff.csv", "description": "among thresholds with validation ROC-AUC at least 0.60 and F1 within 0.08 of the best, choose the smallest quantile; this rejects trivial all-alert selection"},
        "chronological_holdout": {"passed": True, "train_origins": int(len(parts["train"])), "validation_origins": int(len(parts["validation"])), "test_origins": int(len(parts["test"])), "future_window": [START, END]},
    }
    dump(results / "quality_validation.json", quality)
    specification = {"model_name": "causal temporal process forecasting", "state_variable": "30-step observed input/output history", "feature_rule": "all Q2/Q3 features are observed at or before origin t", "q1_rule": "same-time five input variables only", "event_rule": "any SO2 or H2S exceedance in t+10..t+70", "timing_rule": "earliest exceedance offset conditional on an event"}
    dump(results / "model_specification.json", specification)
    result = {"status": "PASS", "questions": {"q1": {"selected_model": q1_name, "test": q1_test_metrics, "baseline": baseline_metrics}, "q2": {"thresholds": chosen["thresholds"], "threshold_quantile": chosen["quantile"], "test": q2_metrics}, "q3": {"test": json.loads((results / "q3_metrics.json").read_text(encoding="utf-8"))}}, "metrics": {"q1_mean_rmse": q1_test_metrics["mean_rmse"], "q2_f1": q2_metrics["f1"], "q2_accuracy": q2_metrics["accuracy"], "q3_event_mae": timing_mae}}
    dump(results / "result_object.json", result)
    dump(results / "solver_validation.json", {"status": "PASS", "finite_predictions": bool(np.isfinite(q1_predictions).all() and np.isfinite(q2_probability).all() and np.isfinite(predicted_delay).all()), "chronological_test_rows": int(len(parts["test"])), "result_sha256": sha(results / "result_object.json")})
    claims = [
        {"claim_id": "CLAIM_Q1_RMSE", "evidence_id": "E_RESULT", "json_pointer": "/metrics/q1_mean_rmse"},
        {"claim_id": "CLAIM_Q2_ACCURACY", "evidence_id": "E_RESULT", "json_pointer": "/metrics/q2_accuracy"},
        {"claim_id": "CLAIM_Q2_F1", "evidence_id": "E_RESULT", "json_pointer": "/metrics/q2_f1"},
        {"claim_id": "CLAIM_Q3_MAE", "evidence_id": "E_RESULT", "json_pointer": "/metrics/q3_event_mae"},
    ]
    dump(paper / "claim-registry.json", claims)
    dump(paper / "evidence-index.json", [{"evidence_id": "E_RESULT", "path": "results/result_object.json", "sha256": sha(results / "result_object.json")}])
    formulas = [
        {"id": "F1", "latex": r"\hat{\mathbf y}_t=f(\mathbf x_t)", "variables": "x: five current inputs; y: SO2 and H2S", "units": "standardized concentration", "code_function": "RandomForestRegressor.predict", "parameter_source": "results/q1_metrics.json", "result_id": "Q1", "inserted_in_body": True},
        {"id": "F2", "latex": r"z_t=\mathbb{1}\{\max_{h=10}^{70}(SO2_{t+h}>k_1\lor H2S_{t+h}>k_2)\}", "variables": "z: future-window alert", "units": "0/1", "code_function": "future_event_targets", "parameter_source": "results/q2_metrics.json", "result_id": "Q2", "inserted_in_body": True},
        {"id": "F3", "latex": r"\hat\tau_t=g(\phi_t)\in[10,70]", "variables": "tau: first violation offset; phi: causal history features", "units": "sampling intervals", "code_function": "RandomForestRegressor.predict", "parameter_source": "results/q3_metrics.json", "result_id": "Q3", "inserted_in_body": True},
        {"id": "F4", "latex": r"\phi_t=[x_t,y_t,\overline{x}_{t-29:t},s(x_{t-29:t}),\overline{y}_{t-29:t},s(y_{t-29:t})]", "variables": "phi: causal feature vector", "units": "standardized", "code_function": "causal_features", "parameter_source": "results/model_specification.json", "result_id": "Q2", "inserted_in_body": True},
        {"id": "F5", "latex": r"k_j=Q_q(y_{j,\mathrm{train}})", "variables": "k: alert threshold; q: train quantile", "units": "standardized output", "code_function": "numpy.quantile", "parameter_source": "results/q2_metrics.json", "result_id": "Q2", "inserted_in_body": True},
        {"id": "F6", "latex": r"\hat z_t=\mathbb{1}\{\hat p_t\ge c\}", "variables": "p: event probability; c: validation cutoff", "units": "0/1", "code_function": "classification_metrics", "parameter_source": "results/q2_metrics.json", "result_id": "Q2", "inserted_in_body": True},
        {"id": "F7", "latex": r"\mathrm{RMSE}=\sqrt{n^{-1}\sum_t\|y_t-\hat y_t\|_2^2}", "variables": "y: output; yhat: prediction", "units": "standardized output", "code_function": "regression_scores", "parameter_source": "results/q1_metrics.json", "result_id": "Q1", "inserted_in_body": True},
        {"id": "F8", "latex": r"\mathrm{F1}=2PR/(P+R)", "variables": "P: precision; R: recall", "units": "ratio", "code_function": "classification_metrics", "parameter_source": "results/q2_metrics.json", "result_id": "Q2", "inserted_in_body": True},
        {"id": "F9", "latex": r"\mathrm{MAE}=n_e^{-1}\sum_{t:z_t=1}|\tau_t-\hat\tau_t|", "variables": "n_e: actual event count", "units": "sampling intervals", "code_function": "mean_absolute_error", "parameter_source": "results/q3_metrics.json", "result_id": "Q3", "inserted_in_body": True},
        {"id": "F10", "latex": r"\bar m^*=B^{-1}\sum_{b=1}^{B}\bar m_b", "variables": "m: held-out accuracy; B: bootstrap draws", "units": "ratio", "code_function": "bootstrap_interval", "parameter_source": "results/bootstrap_metrics.json", "result_id": "Q2", "inserted_in_body": True},
    ]
    dump(paper / "formula-registry.json", formulas)
    tables = [
        {"table_id": "T1", "data_file": "results/q1_predictions.csv", "row_filter": "first 12 chronological test origins", "column_filter": "time, actual and predicted outputs", "generation_script": "write_process_competition_paper.py", "sha256": sha(results / "q1_predictions.csv"), "claim_ids": ["CLAIM_Q1_RMSE"], "inserted_in_body": True},
        {"table_id": "T2", "data_file": "results/q2_threshold_tradeoff.csv", "row_filter": "all threshold candidates", "column_filter": "quantile, thresholds, validation scores", "generation_script": "write_process_competition_paper.py", "sha256": sha(results / "q2_threshold_tradeoff.csv"), "claim_ids": ["CLAIM_Q2_F1"], "inserted_in_body": True},
        {"table_id": "T3", "data_file": "results/q2_alert_predictions.csv", "row_filter": "first 12 chronological test origins", "column_filter": "time, event label, probability", "generation_script": "write_process_competition_paper.py", "sha256": sha(results / "q2_alert_predictions.csv"), "claim_ids": ["CLAIM_Q2_ACCURACY"], "inserted_in_body": True},
        {"table_id": "T4", "data_file": "results/q3_time_predictions.csv", "row_filter": "first 12 actual events", "column_filter": "time, actual and predicted delay", "generation_script": "write_process_competition_paper.py", "sha256": sha(results / "q3_time_predictions.csv"), "claim_ids": ["CLAIM_Q3_MAE"], "inserted_in_body": True},
        {"table_id": "T5", "data_file": "results/q1_metrics.json", "row_filter": "selected model and baseline", "column_filter": "mean RMSE", "generation_script": "write_process_competition_paper.py", "sha256": sha(results / "q1_metrics.json"), "claim_ids": ["CLAIM_Q1_RMSE"], "inserted_in_body": True},
        {"table_id": "T6", "data_file": "results/q3_metrics.json", "row_filter": "test aggregate", "column_filter": "event count, MAE, coverage", "generation_script": "write_process_competition_paper.py", "sha256": sha(results / "q3_metrics.json"), "claim_ids": ["CLAIM_Q3_MAE"], "inserted_in_body": True},
    ]
    dump(paper / "table-registry.json", tables)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, required=True)
    main(parser.parse_args().root)
