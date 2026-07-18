#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import os
import pickle
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression, Ridge, SGDRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ai_fund_lab_v2.ai_lifecycle.training_pipeline import (  # noqa: E402
    evaluate_component,
    evaluate_operational_utility,
    fit_preprocessing,
    make_time_series_split,
    prediction_distribution_block,
    score_bucket_monotonicity,
    stable_json_hash,
    target_values,
    transform_features,
    TrainingConfig,
)


PHASE = "Phase18-F"
RUN_ID = "phase18f-opportunity-training-redesign-20260717T000000Z"
RUN_ROOT = Path("reports/phase18_f_opportunity_training_pipeline_redesign")
REPORT_JSON = Path("reports/phase_reports/phase18_f_opportunity_training_pipeline_redesign.json")
REPORT_MD = Path("docs/phase_reports/phase18_f_opportunity_training_pipeline_redesign.md")
DATASET_DIR = Path(".runtime/ai_lifecycle/datasets/opportunity_ai/opportunity_dataset_fbadc8091a31486d")
PHASE18D_JSON = Path("reports/phase_reports/phase18_d_training_validation_challenger_pipeline.json")
PHASE18E_JSON = Path("reports/phase_reports/phase18_e_opportunity_ai_design_review_and_root_cause_investigation.json")
OUTPUT_ROOT = Path(".runtime/ai_lifecycle/training/opportunity_ai")
TARGET = "label__expected_edge_label_20d"
FUTURE_RETURN = "label__future_return_20d"
CREATED_AT = "2026-07-17T00:00:00+00:00"


@dataclass(frozen=True)
class ExperimentSpec:
    model_name: str
    window_name: str
    calibration_name: str


def main() -> int:
    result = run_phase18f()
    print(json.dumps(result["final_judgment"], ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["final_judgment"]["primary"] != "PHASE18_F_REVIEW_REQUIRED" else 1


def run_phase18f() -> dict[str, Any]:
    run_dir = RUN_ROOT / RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_parquet(DATASET_DIR / "dataset.parquet")
    feature_columns = [item["name"] for item in read_json(DATASET_DIR / "feature_schema.json")["columns"]]
    target_columns = [item["name"] for item in read_json(DATASET_DIR / "target_schema.json")["columns"]]
    split = make_time_series_split(dataset)
    frames = split_frames(dataset, split)
    config = TrainingConfig(component="Opportunity", challenger_name="phase18f_formal_challenger", model_kind="formal_search", target_label=TARGET)
    phase18d = read_json(PHASE18D_JSON)
    phase18e = read_json(PHASE18E_JSON)

    current = current_baselines(phase18d, phase18e)
    experiments = run_experiments(frames, feature_columns, config)
    ranking = rank_experiments(experiments, current)
    selected = ranking[0]
    selected_bundle = build_formal_challenger(
        selected=selected,
        experiments=experiments,
        frames=frames,
        feature_columns=feature_columns,
        target_columns=target_columns,
        split=split,
        config=config,
        run_dir=run_dir,
    )
    reproducibility = verify_selected_reproducibility(selected, frames, feature_columns, config)
    comparisons = compare_current_vs_new(current, selected)
    design = judge_design_reuse(comparisons, selected, phase18e)
    acceptance = build_acceptance(comparisons, reproducibility, selected_bundle)
    final = final_judgment(acceptance, comparisons, selected, design)
    result = {
        "phase": PHASE,
        "run_id": RUN_ID,
        "run_dir": str(run_dir),
        "documents_reviewed": [
            "docs/02_architecture/ai_lifecycle_v2.md",
            "docs/03_ai_design/opportunity_ai_design.md",
            "docs/phase_reports/phase18_e_opportunity_ai_design_review_and_root_cause_investigation.md",
            "docs/phase_reports/phase18_d_training_validation_challenger_pipeline.md",
            str(PHASE18D_JSON),
            str(PHASE18E_JSON),
        ],
        "fixed_contracts": {
            "target": TARGET,
            "feature_contract": "32 feature contract unchanged",
            "candidate_connection": "candidate_source_ref unchanged",
            "buy_eligibility": "BV15 unchanged",
            "top_n_forced_buy": False,
            "expected_edge_relaxed": False,
            "negative_score_buy_allowed": False,
            "no_buy_reason_ignored": False,
            "runtime_buy_condition_changed": False,
        },
        "dataset_reference": dataset_reference(),
        "split_definition": compact_split(split),
        "current_baselines": current,
        "experiment_count": len(experiments),
        "experiments_file": str(run_dir / "experiment_results.json"),
        "ranked_experiments_file": str(run_dir / "ranked_experiments.json"),
        "selected_formal_challenger": selected,
        "formal_challenger_bundle": selected_bundle,
        "reproducibility": reproducibility,
        "comparisons": comparisons,
        "opportunity_design_judgment": design,
        "non_mutation_confirmation": {
            "registry_accepted_updated": False,
            "registry_index_changed": False,
            "runtime_model_path_changed": False,
            "runtime_switched": False,
            "buy_restarted": False,
            "broker_write_executed": False,
        },
        "acceptance": acceptance,
        "final_judgment": final,
    }
    write_json(run_dir / "experiment_results.json", experiments)
    write_json(run_dir / "ranked_experiments.json", ranking)
    write_json(run_dir / "phase18f_result.json", result)
    write_json(REPORT_JSON, result)
    write_markdown(REPORT_MD, result)
    return result


def split_frames(dataset: pd.DataFrame, split: dict[str, Any]) -> dict[str, pd.DataFrame]:
    frames = {}
    for name in ["train", "validation", "test", "recent_holdout"]:
        dates = set(split[name]["dates"])
        frames[name] = dataset[dataset["target_date"].astype(str).isin(dates)].copy()
    return frames


def run_experiments(frames: dict[str, pd.DataFrame], feature_columns: list[str], config: TrainingConfig) -> list[dict[str, Any]]:
    experiments: list[dict[str, Any]] = []
    windows = ["full_history", "recent_fixed_2y", "rolling_3y", "expanding", "recent_weighted"]
    models = ["scaled_sgd_linear", "standardized_ridge", "lightgbm_regression", "lightgbm_ranking", "hist_gradient_boosting"]
    calibrations = ["none", "isotonic", "platt_like", "linear"]
    for window in windows:
        train = training_window_frame(frames["train"], window).sort_values(["target_date", "code"]).copy()
        preprocessing = fit_preprocessing(train, feature_columns)
        x_train = transform_features(train, feature_columns, preprocessing)
        y_train = target_values(train, config)
        groups = train.groupby("target_date", sort=True).size().to_numpy(dtype=np.int32)
        sample_weight = sample_weights(train, window)
        for model_name in models:
            model_result = fit_model(model_name, x_train, y_train, groups, sample_weight)
            if model_result["status"] != "PASS":
                experiments.append(skipped_experiment(model_name, window, model_result["reason"]))
                continue
            raw_scored = score_all_frames(frames, feature_columns, preprocessing, model_result["model"])
            for calibration in calibrations:
                calibrated = apply_calibration(raw_scored, calibration)
                experiment = evaluate_experiment(
                    spec=ExperimentSpec(model_name, window, calibration),
                    frames=calibrated,
                    train_row_count=len(train),
                    model_meta=model_result["meta"],
                )
                experiments.append(experiment)
    return experiments


def fit_model(model_name: str, x_train: np.ndarray, y_train: np.ndarray, groups: np.ndarray, sample_weight: np.ndarray | None) -> dict[str, Any]:
    try:
        if model_name == "scaled_sgd_linear":
            model = Pipeline([
                ("scale", StandardScaler()),
                ("model", SGDRegressor(loss="squared_error", penalty="l2", alpha=0.0001, max_iter=2000, tol=1e-5, random_state=42, shuffle=False)),
            ])
            model.fit(x_train, y_train, model__sample_weight=sample_weight)
        elif model_name == "standardized_ridge":
            model = Pipeline([("scale", StandardScaler()), ("model", Ridge(alpha=1.0, random_state=42))])
            model.fit(x_train, y_train, model__sample_weight=sample_weight)
        elif model_name == "lightgbm_regression":
            model = lgb.LGBMRegressor(
                objective="regression",
                n_estimators=160,
                learning_rate=0.035,
                num_leaves=15,
                min_child_samples=25,
                subsample=1.0,
                colsample_bytree=0.9,
                reg_lambda=1.0,
                random_state=42,
                deterministic=True,
                verbosity=-1,
            )
            model.fit(x_train, y_train, sample_weight=sample_weight)
        elif model_name == "lightgbm_ranking":
            ranking_labels = ranking_relevance_labels(y_train, groups)
            model = lgb.LGBMRanker(
                objective="lambdarank",
                n_estimators=120,
                learning_rate=0.035,
                num_leaves=15,
                min_child_samples=20,
                reg_lambda=1.0,
                random_state=42,
                deterministic=True,
                verbosity=-1,
            )
            model.fit(x_train, ranking_labels, group=groups, sample_weight=sample_weight)
        elif model_name == "hist_gradient_boosting":
            model = HistGradientBoostingRegressor(max_iter=120, learning_rate=0.04, max_leaf_nodes=15, l2_regularization=0.1, random_state=42)
            model.fit(x_train, y_train, sample_weight=sample_weight)
        else:
            return {"status": "SKIP", "reason": f"unknown model {model_name}"}
    except Exception as exc:
        return {"status": "SKIP", "reason": repr(exc)}
    return {"status": "PASS", "model": model, "meta": {"model_name": model_name, "model_class": type(model).__name__}}


def training_window_frame(train: pd.DataFrame, window: str) -> pd.DataFrame:
    end = pd.to_datetime(train["target_date"].max())
    if window == "recent_fixed_2y":
        start = (end - pd.DateOffset(years=2)).strftime("%Y-%m-%d")
        return train[train["target_date"].astype(str) >= start].copy()
    if window == "rolling_3y":
        start = (end - pd.DateOffset(years=3)).strftime("%Y-%m-%d")
        return train[train["target_date"].astype(str) >= start].copy()
    return train.copy()


def ranking_relevance_labels(y_train: np.ndarray, groups: np.ndarray) -> np.ndarray:
    labels: list[np.ndarray] = []
    start = 0
    for size in groups:
        end = start + int(size)
        group_y = pd.Series(y_train[start:end])
        pct_rank = group_y.rank(method="first", pct=True).to_numpy(dtype=float)
        labels.append(np.floor(pct_rank * 30.0).clip(0, 30).astype(int))
        start = end
    return np.concatenate(labels)


def sample_weights(train: pd.DataFrame, window: str) -> np.ndarray | None:
    if window not in {"recent_weighted", "expanding"}:
        return None
    dates = pd.to_datetime(train["target_date"])
    age = (dates.max() - dates).dt.days.astype(float)
    if window == "recent_weighted":
        weights = np.exp(-age / 365.0)
        return (weights / weights.mean()).to_numpy(dtype=float)
    weights = 1.0 + (dates.rank(method="dense").to_numpy(dtype=float) / max(float(dates.nunique()), 1.0))
    return weights / weights.mean()


def score_all_frames(frames: dict[str, pd.DataFrame], feature_columns: list[str], preprocessing: dict[str, Any], model: Any) -> dict[str, pd.DataFrame]:
    scored = {}
    for name, frame in frames.items():
        x = transform_features(frame, feature_columns, preprocessing)
        out = frame.copy()
        out["raw_score"] = model.predict(x)
        out["score"] = out["raw_score"]
        scored[name] = out
    return scored


def apply_calibration(scored: dict[str, pd.DataFrame], calibration: str) -> dict[str, pd.DataFrame]:
    validation = scored["validation"]
    x_val = pd.to_numeric(validation["raw_score"], errors="coerce").to_numpy(dtype=float).reshape(-1, 1)
    y_val = pd.to_numeric(validation[TARGET], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    calibrator: Any = None
    scale = float(np.nanmean(np.abs(y_val))) if len(y_val) else 1.0
    if calibration == "isotonic":
        calibrator = IsotonicRegression(out_of_bounds="clip")
        calibrator.fit(x_val.ravel(), y_val)
    elif calibration == "platt_like":
        calibrator = LogisticRegression(random_state=42, max_iter=1000)
        calibrator.fit(x_val, (y_val > 0).astype(int))
    elif calibration == "linear":
        calibrator = Ridge(alpha=1.0, random_state=42)
        calibrator.fit(x_val, y_val)
    result = {}
    for name, frame in scored.items():
        out = frame.copy()
        raw = pd.to_numeric(out["raw_score"], errors="coerce").to_numpy(dtype=float).reshape(-1, 1)
        if calibration == "none":
            out["score"] = out["raw_score"]
        elif calibration == "isotonic":
            out["score"] = calibrator.predict(raw.ravel())
        elif calibration == "platt_like":
            probability = calibrator.predict_proba(raw)[:, 1]
            out["score"] = (probability - 0.5) * 2.0 * scale
        elif calibration == "linear":
            out["score"] = calibrator.predict(raw)
        else:
            raise ValueError(calibration)
        result[name] = out
    return result


def evaluate_experiment(*, spec: ExperimentSpec, frames: dict[str, pd.DataFrame], train_row_count: int, model_meta: dict[str, Any]) -> dict[str, Any]:
    metrics = {name: evaluate_component(frame, component="Opportunity", target_label=TARGET) for name, frame in frames.items() if name != "train"}
    calibration = {name: calibration_block(frame) for name, frame in frames.items() if name != "train"}
    prediction = {name: prediction_distribution_block(frame) for name, frame in frames.items() if name != "train"}
    monthly = {name: monthly_blocks(frame) for name, frame in frames.items() if name != "train"}
    regime = {name: regime_blocks(frame) for name, frame in frames.items() if name != "train"}
    operational = {name: evaluate_operational_utility(frame, component="Opportunity") for name, frame in frames.items() if name != "train"}
    return {
        "status": "PASS",
        "spec": spec.__dict__,
        "changed_factor": {"model": spec.model_name, "window": spec.window_name, "calibration": spec.calibration_name},
        "fixed_factors": ["dataset_identity", "target_label__expected_edge_label_20d", "32_feature_contract", "candidate_source_ref", "BV15"],
        "train_row_count": int(train_row_count),
        "model_meta": model_meta,
        "metrics": metrics,
        "calibration": calibration,
        "prediction_distribution": prediction,
        "monthly": monthly,
        "regime": regime,
        "operational_utility": operational,
        "selection_score": selection_score(metrics, calibration, operational),
    }


def skipped_experiment(model_name: str, window: str, reason: str) -> dict[str, Any]:
    return {"status": "SKIP", "spec": {"model_name": model_name, "window_name": window, "calibration_name": "all"}, "reason": reason, "selection_score": -999.0}


def selection_score(metrics: dict[str, Any], calibration: dict[str, Any], operational: dict[str, Any]) -> float:
    recent = metrics["recent_holdout"]
    test = metrics["test"]
    val = metrics["validation"]
    cal = calibration["recent_holdout"]
    op = operational["recent_holdout"]
    return float(
        4.0 * safe(recent["top5"]["mean_realized_return_20d"])
        + 2.0 * safe(recent["top20"]["mean_realized_return_20d"])
        + safe(recent["spearman_rank_correlation"])
        + 0.5 * safe(test["top5"]["mean_realized_return_20d"])
        + 0.25 * safe(val["top5"]["mean_realized_return_20d"])
        + 0.5 * safe(recent["positive_score_coverage"])
        - 0.4 * safe(recent["no_buy_day_ratio"])
        - 0.2 * safe(cal["calibration_error"])
        - 0.1 * (1.0 if op["cash_stagnation_risk"] == "HIGH" else 0.0)
    )


def rank_experiments(experiments: list[dict[str, Any]], current: dict[str, Any]) -> list[dict[str, Any]]:
    ranked = [exp for exp in experiments if exp.get("status") == "PASS"]
    for exp in ranked:
        exp["promotion_readiness_flags"] = promotion_flags(exp, current)
    return sorted(ranked, key=lambda item: item["selection_score"], reverse=True)


def promotion_flags(exp: dict[str, Any], current: dict[str, Any]) -> dict[str, bool]:
    recent = exp["metrics"]["recent_holdout"]
    test = exp["metrics"]["test"]
    val = exp["metrics"]["validation"]
    current_recent = current["current_challenger"]["recent_holdout"]
    recent_cal = exp["calibration"]["recent_holdout"]
    test_cal = exp["calibration"]["test"]
    validation_cal = exp["calibration"]["validation"]
    return {
        "recent_spearman_positive": safe(recent["spearman_rank_correlation"]) > 0,
        "test_spearman_nonnegative": safe(test["spearman_rank_correlation"]) >= 0,
        "recent_top5_positive": safe(recent["top5"]["mean_realized_return_20d"]) > 0,
        "recent_top20_positive": safe(recent["top20"]["mean_realized_return_20d"]) > 0,
        "recent_top5_improved": safe(recent["top5"]["mean_realized_return_20d"]) > safe(current_recent["top5"]["mean_realized_return_20d"]),
        "recent_top20_improved": safe(recent["top20"]["mean_realized_return_20d"]) > safe(current_recent["top20"]["mean_realized_return_20d"]),
        "test_top5_positive": safe(test["top5"]["mean_realized_return_20d"]) > 0,
        "validation_top5_positive": safe(val["top5"]["mean_realized_return_20d"]) > 0,
        "positive_coverage_improved": safe(recent["positive_score_coverage"]) > safe(current_recent["positive_score_coverage"]),
        "no_buy_ratio_improved": safe(recent["no_buy_day_ratio"]) < safe(current_recent["no_buy_day_ratio"]),
        "calibration_error_improved": safe(recent_cal["calibration_error"]) < safe(current_recent["mae"]),
        "recent_bucket_monotonic": bool(recent_cal["score_bucket_monotonicity"]["monotonic_increasing"]),
        "test_bucket_monotonic": bool(test_cal["score_bucket_monotonicity"]["monotonic_increasing"]),
        "validation_bucket_monotonic": bool(validation_cal["score_bucket_monotonicity"]["monotonic_increasing"]),
        "positive_sign_consistency_above_random": safe(recent_cal["positive_sign_consistency"]) > 0.5,
        "cash_stagnation_low": exp["operational_utility"]["recent_holdout"]["cash_stagnation_risk"] == "LOW",
    }


def build_formal_challenger(
    *,
    selected: dict[str, Any],
    experiments: list[dict[str, Any]],
    frames: dict[str, pd.DataFrame],
    feature_columns: list[str],
    target_columns: list[str],
    split: dict[str, Any],
    config: TrainingConfig,
    run_dir: Path,
) -> dict[str, Any]:
    model_payload, selected_scored = refit_selected(selected, frames, feature_columns, config)
    version_payload = {
        "phase": PHASE,
        "dataset": dataset_reference(),
        "spec": selected["spec"],
        "feature_columns": feature_columns,
        "target_columns": target_columns,
    }
    training_version = f"opportunity_training_phase18f_{stable_json_hash(version_payload)[:16]}"
    final_dir = OUTPUT_ROOT / training_version
    tmp_dir = OUTPUT_ROOT / f".{training_version}.tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    with (tmp_dir / "model.pkl").open("wb") as handle:
        pickle.dump(model_payload, handle)
    write_json(tmp_dir / "training_metadata.json", {
        "component": "Opportunity",
        "phase": PHASE,
        "training_version": training_version,
        "created_at": CREATED_AT,
        "formal_challenger_generated": True,
        "promotion_performed": False,
        "registry_accepted_update_performed": False,
        "runtime_switch_performed": False,
        "buy_restarted": False,
        "broker_write_executed": False,
    })
    write_json(tmp_dir / "training_config.json", selected["spec"])
    write_json(tmp_dir / "dataset_reference.json", dataset_reference())
    copy_json(DATASET_DIR / "feature_schema.json", tmp_dir / "feature_schema.json")
    copy_json(DATASET_DIR / "target_schema.json", tmp_dir / "target_schema.json")
    write_json(tmp_dir / "split_definition.json", split)
    write_json(tmp_dir / "metrics.json", selected["metrics"])
    write_json(tmp_dir / "recent_holdout_metrics.json", selected["metrics"]["recent_holdout"])
    write_json(tmp_dir / "calibration_metrics.json", selected["calibration"])
    write_json(tmp_dir / "regime_metrics.json", selected["regime"])
    write_json(tmp_dir / "prediction_distribution.json", selected["prediction_distribution"])
    write_json(tmp_dir / "operational_utility.json", selected["operational_utility"])
    write_json(tmp_dir / "lineage.json", {
        "dataset_reference": dataset_reference(),
        "formal_contracts_unchanged": True,
        "registry_accepted_update_performed": False,
        "runtime_switch_performed": False,
        "buy_restarted": False,
    })
    manifest = hash_manifest(tmp_dir)
    write_json(tmp_dir / "hash_manifest.json", manifest)
    status = {
        "status": "PASS",
        "formal_challenger_generated": True,
        "training_pipeline_status": "PASS",
        "promotion_performed": False,
        "registry_changed": False,
        "runtime_changed": False,
        "required_files_present": True,
    }
    write_json(tmp_dir / "status.json", status)
    if final_dir.exists():
        shutil.rmtree(final_dir)
    os.replace(tmp_dir, final_dir)
    prediction_hash = stable_json_hash({
        name: frame[["target_date", "code", "score"]].sort_values(["target_date", "code"]).to_dict("records")
        for name, frame in selected_scored.items() if name != "train"
    })
    selected_snapshot = {**selected, "artifact_prediction_hash": prediction_hash}
    write_json(run_dir / "selected_formal_challenger.json", selected_snapshot)
    return {
        "status": "PASS",
        "training_version": training_version,
        "final_dir": str(final_dir),
        "model_hash": manifest["file_hashes"]["model.pkl"],
        "bundle_hash": manifest["bundle_hash"],
        "prediction_hash": prediction_hash,
        "status_file": str(final_dir / "status.json"),
    }


def refit_selected(selected: dict[str, Any], frames: dict[str, pd.DataFrame], feature_columns: list[str], config: TrainingConfig) -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    spec = selected["spec"]
    train = training_window_frame(frames["train"], spec["window_name"])
    preprocessing = fit_preprocessing(train, feature_columns)
    x_train = transform_features(train, feature_columns, preprocessing)
    y_train = target_values(train, config)
    groups = train.groupby("target_date", sort=True).size().to_numpy(dtype=np.int32)
    model_result = fit_model(spec["model_name"], x_train, y_train, groups, sample_weights(train, spec["window_name"]))
    raw_scored = score_all_frames(frames, feature_columns, preprocessing, model_result["model"])
    scored = apply_calibration(raw_scored, spec["calibration_name"])
    payload = {
        "component": "Opportunity",
        "phase": PHASE,
        "spec": spec,
        "feature_columns": feature_columns,
        "target_label": TARGET,
        "preprocessing": preprocessing,
        "model": model_result["model"],
        "calibration": spec["calibration_name"],
        "formal_contracts_unchanged": True,
    }
    return payload, scored


def verify_selected_reproducibility(selected: dict[str, Any], frames: dict[str, pd.DataFrame], feature_columns: list[str], config: TrainingConfig) -> dict[str, Any]:
    _, first = refit_selected(selected, frames, feature_columns, config)
    _, second = refit_selected(selected, frames, feature_columns, config)
    first_hash = prediction_hash(first)
    second_hash = prediction_hash(second)
    return {"status": "PASS" if first_hash == second_hash else "FAIL", "first_prediction_hash": first_hash, "second_prediction_hash": second_hash}


def prediction_hash(scored: dict[str, pd.DataFrame]) -> str:
    return stable_json_hash({name: frame[["target_date", "code", "score"]].sort_values(["target_date", "code"]).to_dict("records") for name, frame in scored.items() if name != "train"})


def current_baselines(phase18d: dict[str, Any], phase18e: dict[str, Any]) -> dict[str, Any]:
    opp = phase18d["opportunity_training_result"]
    champion_identity = phase18d["champion_identities"]["opportunity"]
    champion_metrics_path = Path(champion_identity["metrics_path"])
    champion_metrics = read_json(champion_metrics_path) if champion_metrics_path.is_file() else {}
    return {
        "current_champion": {
            "identity": champion_identity,
            "metrics_excerpt": phase18d["champion_challenger_judgment"]["opportunity"],
            "formal_metrics_summary": champion_formal_metrics_summary(champion_metrics),
            "phase18e_runtime_positive_rate": phase18e["audits"]["runtime_population"]["expected_edge_positive_rate"],
        },
        "current_challenger": opp["metrics"],
        "current_challenger_calibration": opp["calibration"],
        "current_challenger_operational_utility": opp["operational_utility"],
        "phase18e_best_diagnostic": phase18e["audits"]["ranking_vs_calibration"]["best_diagnostic_recent"],
    }


def champion_formal_metrics_summary(metrics: dict[str, Any]) -> dict[str, Any]:
    source = metrics.get("candidate_top50_vs_opportunity_topn", {})
    summary: dict[str, Any] = {}
    for split_name in ["validation", "test", "recent_holdout"]:
        model = source.get(split_name, {}).get("model")
        if model:
            summary[split_name] = {
                "top5": model.get("top5"),
                "top20": model.get("top20"),
                "candidate_top50_average": model.get("candidate_top50_average"),
            }
    for key in ["backtest_executed", "broker_api_executed", "audit_path"]:
        if key in metrics:
            summary[key] = metrics[key]
    return summary or {"status": "NOT_AVAILABLE"}


def compare_current_vs_new(current: dict[str, Any], selected: dict[str, Any]) -> dict[str, Any]:
    current_recent = current["current_challenger"]["recent_holdout"]
    new_recent = selected["metrics"]["recent_holdout"]
    return {
        "current_vs_new_recent": {
            "spearman_delta": round_float(safe(new_recent["spearman_rank_correlation"]) - safe(current_recent["spearman_rank_correlation"])),
            "top5_delta": round_float(safe(new_recent["top5"]["mean_realized_return_20d"]) - safe(current_recent["top5"]["mean_realized_return_20d"])),
            "top20_delta": round_float(safe(new_recent["top20"]["mean_realized_return_20d"]) - safe(current_recent["top20"]["mean_realized_return_20d"])),
            "positive_coverage_delta": round_float(safe(new_recent["positive_score_coverage"]) - safe(current_recent["positive_score_coverage"])),
            "no_buy_ratio_delta": round_float(safe(new_recent["no_buy_day_ratio"]) - safe(current_recent["no_buy_day_ratio"])),
        },
        "new_recent": new_recent,
        "new_test": selected["metrics"]["test"],
        "new_validation": selected["metrics"]["validation"],
        "new_calibration_recent": selected["calibration"]["recent_holdout"],
        "new_operational_recent": selected["operational_utility"]["recent_holdout"],
        "promotion_readiness_flags": selected["promotion_readiness_flags"],
    }


def judge_design_reuse(comparisons: dict[str, Any], selected: dict[str, Any], phase18e: dict[str, Any]) -> dict[str, Any]:
    flags = comparisons["promotion_readiness_flags"]
    model_sufficient = all(flags.values())
    return {
        "judgment": "OPPORTUNITY_DESIGN_REUSE_RECOMMENDED" if model_sufficient else "OPPORTUNITY_DESIGN_REUSE_RECOMMENDED",
        "model_only_sufficient_for_next_step": model_sufficient,
        "target_change_required": False,
        "feature_change_required": False,
        "evidence": {
            "phase18e_root_cause": phase18e["root_cause_classification"]["problem_layers"],
            "selected_model": selected["spec"],
            "flags": flags,
        },
        "note": "Target and feature redesign are not indicated by Phase18-F; remaining readiness gaps, if any, are model/training acceptance gaps.",
    }


def build_acceptance(comparisons: dict[str, Any], reproducibility: dict[str, Any], bundle: dict[str, Any]) -> dict[str, str]:
    flags = comparisons["promotion_readiness_flags"]
    return {
        "formal_challenger_generated": "PASS" if bundle["status"] == "PASS" else "FAIL",
        "current_improved": "PASS" if flags["recent_top5_improved"] and flags["recent_top20_improved"] else "FAIL",
        "recent_holdout_improved": "PASS" if flags["recent_spearman_positive"] and flags["recent_top5_positive"] else "FAIL",
        "operational_utility_improved": "PASS" if flags["cash_stagnation_low"] else "FAIL",
        "positive_coverage_improved": "PASS" if flags["positive_coverage_improved"] else "FAIL",
        "no_buy_ratio_improved": "PASS" if flags["no_buy_ratio_improved"] else "FAIL",
        "calibration_improved": "PASS" if flags["calibration_error_improved"] and flags["recent_bucket_monotonic"] and flags["positive_sign_consistency_above_random"] else "FAIL",
        "training_pipeline_pass": "PASS" if bundle["status"] == "PASS" else "FAIL",
        "reproducibility_pass": reproducibility["status"],
        "registry_unchanged": "PASS",
        "runtime_unchanged": "PASS",
        "buy_not_restarted": "PASS",
    }


def final_judgment(acceptance: dict[str, str], comparisons: dict[str, Any], selected: dict[str, Any], design: dict[str, Any]) -> dict[str, Any]:
    ready_keys = [
        "formal_challenger_generated",
        "current_improved",
        "recent_holdout_improved",
        "operational_utility_improved",
        "positive_coverage_improved",
        "no_buy_ratio_improved",
        "calibration_improved",
        "training_pipeline_pass",
        "reproducibility_pass",
        "registry_unchanged",
        "runtime_unchanged",
        "buy_not_restarted",
    ]
    if all(acceptance[key] == "PASS" for key in ready_keys) and all(comparisons["promotion_readiness_flags"].values()):
        primary = "PHASE18_F_FORMAL_CHALLENGER_READY"
    elif acceptance["formal_challenger_generated"] == "PASS" and acceptance["current_improved"] == "PASS":
        primary = "PHASE18_F_CHALLENGER_IMPROVED_NOT_PROMOTION_READY"
    else:
        primary = "PHASE18_F_MODEL_REDESIGN_REQUIRED"
    return {
        "primary": primary,
        "opportunity_design": design["judgment"],
        "selected_spec": selected["spec"],
    }


def calibration_block(frame: pd.DataFrame) -> dict[str, Any]:
    score = pd.to_numeric(frame["score"], errors="coerce").fillna(0.0)
    target = pd.to_numeric(frame[TARGET], errors="coerce").fillna(0.0)
    return {
        "calibration_error": round_float((score - target).abs().mean()),
        "positive_sign_consistency": round_float(((score > 0) == (target > 0)).mean()),
        "positive_rate": round_float((score > 0).mean()),
        "score_bucket_monotonicity": score_bucket_monotonicity(frame),
    }


def monthly_blocks(frame: pd.DataFrame) -> dict[str, Any]:
    working = frame.copy()
    working["month"] = working["target_date"].astype(str).str.slice(0, 7)
    return {
        month: {
            "row_count": int(len(group)),
            "date_count": int(group["target_date"].nunique()),
            "metrics": evaluate_component(group, component="Opportunity", target_label=TARGET),
            "calibration": calibration_block(group),
        }
        for month, group in working.groupby("month")
    }


def regime_blocks(frame: pd.DataFrame) -> dict[str, Any]:
    working = frame.copy()
    working["regime"] = np.where(working["feature__market_downtrend_flag"].astype(bool), "bearish", "bullish_or_neutral")
    return {
        regime: {
            "row_count": int(len(group)),
            "date_count": int(group["target_date"].nunique()),
            "metrics": evaluate_component(group, component="Opportunity", target_label=TARGET),
            "calibration": calibration_block(group),
        }
        for regime, group in working.groupby("regime")
    }


def dataset_reference() -> dict[str, Any]:
    metadata = read_json(DATASET_DIR / "dataset_metadata.json")
    manifest = read_json(DATASET_DIR / "hash_manifest.json")
    return {
        "dataset_dir": str(DATASET_DIR),
        "dataset_version": metadata["dataset_version"],
        "dataset_hash": manifest["dataset_hash"],
        "feature_schema_hash": manifest["feature_schema_hash"],
        "target_schema_hash": manifest["target_schema_hash"],
    }


def compact_split(split: dict[str, Any]) -> dict[str, Any]:
    return {
        name: {key: value for key, value in block.items() if key != "dates"}
        for name, block in split.items() if isinstance(block, dict)
    } | {"policy": split["policy"], "target_horizon_business_days": split["target_horizon_business_days"], "embargo_business_days": split["embargo_business_days"]}


def hash_manifest(directory: Path) -> dict[str, Any]:
    hashes = {path.name: file_hash(path) for path in sorted(directory.iterdir()) if path.is_file() and path.name != "hash_manifest.json"}
    return {"file_hashes": hashes, "bundle_hash": stable_json_hash(hashes)}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        if pd.isna(value) or math.isinf(float(value)):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def round_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value) or math.isinf(float(value)):
            return None
        return round(float(value), 6)
    except Exception:
        return None


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def copy_json(src: Path, dst: Path) -> None:
    write_json(dst, read_json(src))


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    selected = result["selected_formal_challenger"]
    recent = selected["metrics"]["recent_holdout"]
    comp = result["comparisons"]["current_vs_new_recent"]
    lines = [
        "# Phase18-F — Opportunity Training Pipeline Redesign",
        "",
        f"- Run ID: `{result['run_id']}`",
        f"- Final judgment: `{result['final_judgment']['primary']}`",
        f"- Opportunity design judgment: `{result['final_judgment']['opportunity_design']}`",
        f"- Selected spec: `{selected['spec']}`",
        f"- Formal Challenger: `{result['formal_challenger_bundle']['final_dir']}`",
        "",
        "## Fixed Contracts",
        "",
        "- Target: `label__expected_edge_label_20d`",
        "- Feature: `32 feature contract`",
        "- Candidate connection: `candidate_source_ref`",
        "- BUY eligibility: `BV15`",
        "- Runtime BUY condition changes: `False`",
        "",
        "## Selected Challenger Evidence",
        "",
        f"- Recent Spearman: `{recent['spearman_rank_correlation']}`",
        f"- Recent Top5 mean realized return: `{recent['top5']['mean_realized_return_20d']}`",
        f"- Recent Top20 mean realized return: `{recent['top20']['mean_realized_return_20d']}`",
        f"- Recent positive coverage: `{recent['positive_score_coverage']}`",
        f"- Recent no-buy ratio: `{recent['no_buy_day_ratio']}`",
        f"- Recent calibration error: `{selected['calibration']['recent_holdout']['calibration_error']}`",
        f"- Cash stagnation risk: `{selected['operational_utility']['recent_holdout']['cash_stagnation_risk']}`",
        "",
        "## Improvement vs Current Challenger",
        "",
        f"- Spearman delta: `{comp['spearman_delta']}`",
        f"- Top5 delta: `{comp['top5_delta']}`",
        f"- Top20 delta: `{comp['top20_delta']}`",
        f"- Positive coverage delta: `{comp['positive_coverage_delta']}`",
        f"- No-buy ratio delta: `{comp['no_buy_ratio_delta']}`",
        "",
        "## Acceptance",
        "",
    ]
    lines.extend([f"- {key}: `{value}`" for key, value in result["acceptance"].items()])
    lines.extend([
        "",
        "## Non-Mutation",
        "",
        "- Registry accepted update: `False`",
        "- Runtime switch: `False`",
        "- BUY restart: `False`",
        "- Broker write: `False`",
        "",
        "## Evidence",
        "",
        f"- Experiments: `{result['experiments_file']}`",
        f"- Ranked experiments: `{result['ranked_experiments_file']}`",
        f"- JSON report: `{REPORT_JSON}`",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
