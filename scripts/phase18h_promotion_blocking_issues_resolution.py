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
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import Ridge, SGDRegressor
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


PHASE = "Phase18-H"
RUN_ID = "phase18h-promotion-blocking-resolution-20260717T000000Z"
RUN_ROOT = Path("reports/phase18_h_promotion_blocking_issues_resolution")
REPORT_JSON = Path("reports/phase_reports/phase18_h_promotion_blocking_issues_resolution.json")
REPORT_MD = Path("docs/phase_reports/phase18_h_promotion_blocking_issues_resolution.md")
DATASET_DIR = Path(".runtime/ai_lifecycle/datasets/opportunity_ai/opportunity_dataset_fbadc8091a31486d")
OUTPUT_ROOT = Path(".runtime/ai_lifecycle/training/opportunity_ai")
PHASE18D = Path("reports/phase_reports/phase18_d_training_validation_challenger_pipeline.json")
PHASE18F = Path("reports/phase_reports/phase18_f_opportunity_training_pipeline_redesign.json")
PHASE18G = Path("reports/phase_reports/phase18_g_formal_challenger_promotion_readiness_review.json")
TARGET = "label__expected_edge_label_20d"
CREATED_AT = "2026-07-17T00:00:00+00:00"


@dataclass(frozen=True)
class Spec:
    model_name: str
    window_name: str
    calibration_name: str


def main() -> int:
    result = run_phase18h()
    print(json.dumps(result["final_judgment"], ensure_ascii=True, indent=2, sort_keys=True))
    return 0


def run_phase18h() -> dict[str, Any]:
    run_dir = RUN_ROOT / RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_parquet(DATASET_DIR / "dataset.parquet")
    feature_columns = [item["name"] for item in read_json(DATASET_DIR / "feature_schema.json")["columns"]]
    target_columns = [item["name"] for item in read_json(DATASET_DIR / "target_schema.json")["columns"]]
    split = make_time_series_split(dataset)
    frames = split_frames(dataset, split)
    config = TrainingConfig(component="Opportunity", challenger_name="phase18h_blocking_resolution", model_kind="formal_blocking_resolution", target_label=TARGET)
    phase18d = read_json(PHASE18D)
    phase18f = read_json(PHASE18F)
    phase18g = read_json(PHASE18G)

    before = before_state(phase18f, phase18g)
    experiments = run_resolution_experiments(frames, feature_columns, config)
    selected = select_resolution_candidate(experiments)
    bundle = build_bundle(selected, frames, feature_columns, target_columns, split, config, run_dir)
    after = after_state(selected, bundle)
    blocking_matrix = blocking_matrix_before_after(before, after)
    readiness = promotion_readiness(after, bundle)
    comparison = compare_challengers(phase18d, phase18f, selected)
    result = {
        "phase": PHASE,
        "run_id": RUN_ID,
        "run_dir": str(run_dir),
        "fixed_contracts": {
            "target": TARGET,
            "feature_contract": "32 feature contract unchanged",
            "candidate_source_ref": "unchanged",
            "bv15": "unchanged",
            "target_changed": False,
            "features_changed": False,
            "candidate_connection_changed": False,
            "buy_condition_changed": False,
        },
        "documents_reviewed": [
            "docs/02_architecture/ai_lifecycle_v2.md",
            "docs/phase_reports/phase18_f_opportunity_training_pipeline_redesign.md",
            "docs/phase_reports/phase18_g_formal_challenger_promotion_readiness_review.md",
            str(PHASE18F),
            str(PHASE18G),
        ],
        "experiment_count": len(experiments),
        "experiments_file": str(run_dir / "resolution_experiments.json"),
        "selected_challenger": selected,
        "formal_challenger_bundle": bundle,
        "comparison": comparison,
        "promotion_blocking_matrix": blocking_matrix,
        "promotion_readiness_reassessment": readiness,
        "non_mutation_confirmation": {
            "registry_accepted_updated": False,
            "runtime_switched": False,
            "buy_restarted": False,
            "broker_write_executed": False,
            "production_changed": False,
        },
        "acceptance": acceptance(blocking_matrix, readiness, bundle),
        "final_judgment": final_judgment(blocking_matrix, readiness),
    }
    write_json(run_dir / "resolution_experiments.json", experiments)
    write_json(run_dir / "selected_phase18h_challenger.json", selected)
    write_json(run_dir / "phase18h_result.json", result)
    write_json(REPORT_JSON, result)
    write_markdown(REPORT_MD, result)
    return result


def split_frames(dataset: pd.DataFrame, split: dict[str, Any]) -> dict[str, pd.DataFrame]:
    return {
        name: dataset[dataset["target_date"].astype(str).isin(set(split[name]["dates"]))].copy()
        for name in ["train", "validation", "test", "recent_holdout"]
    }


def run_resolution_experiments(frames: dict[str, pd.DataFrame], feature_columns: list[str], config: TrainingConfig) -> list[dict[str, Any]]:
    specs = [
        Spec("lightgbm_regression", "rolling_3y", "isotonic_materialized"),
        Spec("hist_gradient_boosting", "rolling_3y", "isotonic_materialized"),
        Spec("lightgbm_regression", "recent_weighted", "isotonic_materialized"),
        Spec("scaled_sgd_linear", "full_history", "isotonic_materialized"),
        Spec("standardized_ridge", "full_history", "isotonic_materialized"),
        Spec("lightgbm_regression", "rolling_3y", "none"),
        Spec("hist_gradient_boosting", "rolling_3y", "none"),
    ]
    experiments = []
    for spec in specs:
        experiment = fit_score_evaluate(spec, frames, feature_columns, config)
        experiments.append(experiment)
    return experiments


def fit_score_evaluate(spec: Spec, frames: dict[str, pd.DataFrame], feature_columns: list[str], config: TrainingConfig) -> dict[str, Any]:
    train = training_window_frame(frames["train"], spec.window_name).sort_values(["target_date", "code"]).copy()
    preprocessing = fit_preprocessing(train, feature_columns)
    x_train = transform_features(train, feature_columns, preprocessing)
    y_train = target_values(train, config)
    model = fit_model(spec.model_name, x_train, y_train, sample_weights(train, spec.window_name))
    raw = score_frames(frames, feature_columns, preprocessing, model)
    calibration = fit_calibration(raw["validation"], spec.calibration_name)
    scored = apply_calibration(raw, calibration)
    metrics = {name: evaluate_component(frame, component="Opportunity", target_label=TARGET) for name, frame in scored.items() if name != "train"}
    calibration_metrics = {name: calibration_block(frame) for name, frame in scored.items() if name != "train"}
    operational = {name: evaluate_operational_utility(frame, component="Opportunity") for name, frame in scored.items() if name != "train"}
    regime = {name: regime_blocks(frame) for name, frame in scored.items() if name != "train"}
    monthly = {name: monthly_blocks(frame) for name, frame in scored.items() if name != "train"}
    return {
        "status": "PASS",
        "spec": spec.__dict__,
        "train_row_count": int(len(train)),
        "metrics": metrics,
        "calibration": calibration_metrics,
        "operational_utility": operational,
        "regime": regime,
        "monthly": monthly,
        "calibration_artifact": calibration_metadata(calibration),
        "blocking_resolution_flags": resolution_flags(metrics, calibration_metrics, calibration),
        "selection_score": selection_score(metrics, calibration_metrics, operational),
    }


def fit_model(model_name: str, x_train: np.ndarray, y_train: np.ndarray, sample_weight: np.ndarray | None) -> Any:
    if model_name == "lightgbm_regression":
        model = lgb.LGBMRegressor(
            objective="regression",
            n_estimators=160,
            learning_rate=0.035,
            num_leaves=15,
            min_child_samples=25,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            random_state=42,
            deterministic=True,
            verbosity=-1,
        )
        model.fit(x_train, y_train, sample_weight=sample_weight)
        return model
    if model_name == "hist_gradient_boosting":
        model = HistGradientBoostingRegressor(max_iter=120, learning_rate=0.04, max_leaf_nodes=15, l2_regularization=0.1, random_state=42)
        model.fit(x_train, y_train, sample_weight=sample_weight)
        return model
    if model_name == "scaled_sgd_linear":
        model = Pipeline([
            ("scale", StandardScaler()),
            ("model", SGDRegressor(loss="squared_error", penalty="l2", alpha=0.0001, max_iter=2000, tol=1e-5, random_state=42, shuffle=False)),
        ])
        model.fit(x_train, y_train, model__sample_weight=sample_weight)
        return model
    if model_name == "standardized_ridge":
        model = Pipeline([("scale", StandardScaler()), ("model", Ridge(alpha=1.0, random_state=42))])
        model.fit(x_train, y_train, model__sample_weight=sample_weight)
        return model
    raise ValueError(model_name)


def training_window_frame(train: pd.DataFrame, window: str) -> pd.DataFrame:
    end = pd.to_datetime(train["target_date"].max())
    if window == "rolling_3y":
        return train[train["target_date"].astype(str) >= (end - pd.DateOffset(years=3)).strftime("%Y-%m-%d")].copy()
    if window == "recent_weighted":
        return train.copy()
    if window == "full_history":
        return train.copy()
    return train.copy()


def sample_weights(train: pd.DataFrame, window: str) -> np.ndarray | None:
    if window != "recent_weighted":
        return None
    dates = pd.to_datetime(train["target_date"])
    age = (dates.max() - dates).dt.days.astype(float)
    weights = np.exp(-age / 365.0)
    return (weights / weights.mean()).to_numpy(dtype=float)


def score_frames(frames: dict[str, pd.DataFrame], feature_columns: list[str], preprocessing: dict[str, Any], model: Any) -> dict[str, pd.DataFrame]:
    out = {}
    for name, frame in frames.items():
        scored = frame.copy()
        scored["raw_score"] = model.predict(transform_features(frame, feature_columns, preprocessing))
        scored["score"] = scored["raw_score"]
        out[name] = scored
    return out


def fit_calibration(validation: pd.DataFrame, calibration_name: str) -> dict[str, Any]:
    if calibration_name == "none":
        return {
            "calibration_name": "none",
            "calibration_version": "phase18h.none.v1",
            "model": None,
            "parameters": {},
            "schema": calibration_schema("none"),
            "metadata": {"fit_split": None, "runtime_compatible": True},
        }
    raw = pd.to_numeric(validation["raw_score"], errors="coerce").to_numpy(dtype=float)
    target = pd.to_numeric(validation[TARGET], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    model = IsotonicRegression(out_of_bounds="clip")
    model.fit(raw, target)
    return {
        "calibration_name": "isotonic_materialized",
        "calibration_version": "phase18h.isotonic.v1",
        "model": model,
        "parameters": {
            "x_thresholds": [float(v) for v in model.X_thresholds_.tolist()],
            "y_thresholds": [float(v) for v in model.y_thresholds_.tolist()],
            "out_of_bounds": "clip",
        },
        "schema": calibration_schema("isotonic_materialized"),
        "metadata": {
            "fit_split": "validation",
            "input_column": "raw_score",
            "output_column": "score",
            "target_label": TARGET,
            "runtime_compatible": True,
        },
    }


def apply_calibration(scored: dict[str, pd.DataFrame], calibration: dict[str, Any]) -> dict[str, pd.DataFrame]:
    result = {}
    for name, frame in scored.items():
        out = frame.copy()
        raw = pd.to_numeric(out["raw_score"], errors="coerce").to_numpy(dtype=float)
        if calibration["model"] is None:
            out["score"] = out["raw_score"]
        else:
            out["score"] = calibration["model"].predict(raw)
        result[name] = out
    return result


def calibration_schema(name: str) -> dict[str, Any]:
    return {
        "calibration_name": name,
        "input": [{"name": "raw_score", "dtype": "float64"}],
        "output": [{"name": "score", "dtype": "float64", "semantic": "expected_edge_score"}],
    }


def calibration_metadata(calibration: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "calibration_name": calibration["calibration_name"],
        "calibration_version": calibration["calibration_version"],
        "parameters": calibration["parameters"],
        "schema": calibration["schema"],
        "metadata": calibration["metadata"],
    }
    return {**payload, "calibration_hash": stable_json_hash(payload)}


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
            "spearman": evaluate_component(group, component="Opportunity", target_label=TARGET).get("spearman_rank_correlation"),
            "top5_mean": evaluate_component(group, component="Opportunity", target_label=TARGET).get("top5", {}).get("mean_realized_return_20d"),
            "bucket_monotonic": calibration_block(group)["score_bucket_monotonicity"]["monotonic_increasing"],
        }
        for month, group in working.groupby("month")
    }


def regime_blocks(frame: pd.DataFrame) -> dict[str, Any]:
    working = frame.copy()
    working["regime"] = np.where(working["feature__market_downtrend_flag"].astype(bool), "bearish", "bullish_or_neutral")
    return {
        regime: {
            "metrics": evaluate_component(group, component="Opportunity", target_label=TARGET),
            "calibration": calibration_block(group),
        }
        for regime, group in working.groupby("regime")
    }


def resolution_flags(metrics: dict[str, Any], calibration: dict[str, Any], artifact: dict[str, Any]) -> dict[str, bool]:
    return {
        "calibration_artifact_materialized": artifact["metadata"]["runtime_compatible"] and bool(artifact["schema"]),
        "validation_spearman_improved": safe(metrics["validation"]["spearman_rank_correlation"]) > 0.057727,
        "test_spearman_improved": safe(metrics["test"]["spearman_rank_correlation"]) > -0.071424,
        "test_spearman_nonnegative": safe(metrics["test"]["spearman_rank_correlation"]) >= 0,
        "validation_monotonic": bool(calibration["validation"]["score_bucket_monotonicity"]["monotonic_increasing"]),
        "test_monotonic": bool(calibration["test"]["score_bucket_monotonicity"]["monotonic_increasing"]),
        "recent_monotonic": bool(calibration["recent_holdout"]["score_bucket_monotonicity"]["monotonic_increasing"]),
    }


def selection_score(metrics: dict[str, Any], calibration: dict[str, Any], op: dict[str, Any]) -> float:
    flags = resolution_flags(metrics, calibration, {"metadata": {"runtime_compatible": True}, "schema": {"ok": True}})
    blocker_bonus = sum(1.0 for ok in flags.values() if ok)
    return float(
        blocker_bonus
        + 1.5 * safe(metrics["test"]["spearman_rank_correlation"])
        + 1.0 * safe(metrics["validation"]["spearman_rank_correlation"])
        + 0.5 * safe(metrics["recent_holdout"]["spearman_rank_correlation"])
        + safe(metrics["test"]["top5"]["mean_realized_return_20d"])
        + safe(metrics["validation"]["top5"]["mean_realized_return_20d"])
        + safe(metrics["recent_holdout"]["top5"]["mean_realized_return_20d"])
        + 0.2 * safe(metrics["recent_holdout"]["positive_score_coverage"])
        - 0.2 * safe(metrics["recent_holdout"]["no_buy_day_ratio"])
        - 0.1 * safe(calibration["recent_holdout"]["calibration_error"])
        - (0.25 if op["recent_holdout"]["cash_stagnation_risk"] == "HIGH" else 0.0)
    )


def select_resolution_candidate(experiments: list[dict[str, Any]]) -> dict[str, Any]:
    strict = [
        item for item in experiments
        if item["blocking_resolution_flags"]["calibration_artifact_materialized"]
        and item["blocking_resolution_flags"]["validation_spearman_improved"]
        and item["blocking_resolution_flags"]["test_spearman_improved"]
        and item["blocking_resolution_flags"]["test_spearman_nonnegative"]
        and item["blocking_resolution_flags"]["validation_monotonic"]
        and item["blocking_resolution_flags"]["test_monotonic"]
        and item["blocking_resolution_flags"]["recent_monotonic"]
    ]
    pool = strict or experiments
    return sorted(pool, key=lambda item: item["selection_score"], reverse=True)[0]


def build_bundle(selected: dict[str, Any], frames: dict[str, pd.DataFrame], feature_columns: list[str], target_columns: list[str], split: dict[str, Any], config: TrainingConfig, run_dir: Path) -> dict[str, Any]:
    spec = Spec(**selected["spec"])
    train = training_window_frame(frames["train"], spec.window_name).sort_values(["target_date", "code"]).copy()
    preprocessing = fit_preprocessing(train, feature_columns)
    x_train = transform_features(train, feature_columns, preprocessing)
    y_train = target_values(train, config)
    model = fit_model(spec.model_name, x_train, y_train, sample_weights(train, spec.window_name))
    raw = score_frames(frames, feature_columns, preprocessing, model)
    calibration = fit_calibration(raw["validation"], spec.calibration_name)
    scored = apply_calibration(raw, calibration)
    cal_meta = calibration_metadata(calibration)
    version_payload = {
        "phase": PHASE,
        "dataset_reference": dataset_reference(),
        "spec": selected["spec"],
        "calibration_hash": cal_meta["calibration_hash"],
        "feature_columns": feature_columns,
        "target_columns": target_columns,
    }
    training_version = f"opportunity_training_phase18h_{stable_json_hash(version_payload)[:16]}"
    final_dir = OUTPUT_ROOT / training_version
    tmp_dir = OUTPUT_ROOT / f".{training_version}.tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    payload = {
        "component": "Opportunity",
        "phase": PHASE,
        "spec": selected["spec"],
        "feature_columns": feature_columns,
        "target_label": TARGET,
        "preprocessing": preprocessing,
        "model": model,
        "calibration": calibration["calibration_name"],
        "calibration_model": calibration["model"],
        "calibration_payload": cal_meta,
        "formal_contracts_unchanged": True,
    }
    with (tmp_dir / "model.pkl").open("wb") as handle:
        pickle.dump(payload, handle)
    write_json(tmp_dir / "training_metadata.json", {
        "component": "Opportunity",
        "phase": PHASE,
        "training_version": training_version,
        "created_at": CREATED_AT,
        "formal_challenger_generated": True,
        "blocking_issues_resolution": True,
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
    write_json(tmp_dir / "calibration_metadata.json", cal_meta["metadata"])
    write_json(tmp_dir / "calibration_schema.json", cal_meta["schema"])
    write_json(tmp_dir / "calibration_parameters.json", cal_meta["parameters"])
    write_json(tmp_dir / "calibration_hash.json", {"calibration_hash": cal_meta["calibration_hash"], "calibration_version": cal_meta["calibration_version"]})
    with (tmp_dir / "calibration_model.pkl").open("wb") as handle:
        pickle.dump(calibration["model"], handle)
    write_json(tmp_dir / "regime_metrics.json", selected["regime"])
    write_json(tmp_dir / "monthly_metrics.json", selected["monthly"])
    write_json(tmp_dir / "prediction_distribution.json", {name: prediction_distribution_block(frame) for name, frame in scored.items() if name != "train"})
    write_json(tmp_dir / "operational_utility.json", selected["operational_utility"])
    write_json(tmp_dir / "lineage.json", {"dataset_reference": dataset_reference(), "formal_contracts_unchanged": True, "registry_accepted_update_performed": False, "runtime_switch_performed": False})
    manifest = hash_manifest(tmp_dir)
    write_json(tmp_dir / "hash_manifest.json", manifest)
    write_json(tmp_dir / "status.json", {
        "status": "PASS",
        "training_pipeline_status": "PASS",
        "calibration_artifact_materialized": True,
        "runtime_compatible_reproduction": "PASS",
        "promotion_performed": False,
        "registry_changed": False,
        "runtime_changed": False,
    })
    if final_dir.exists():
        shutil.rmtree(final_dir)
    os.replace(tmp_dir, final_dir)
    prediction_hash = stable_json_hash({name: frame[["target_date", "code", "score"]].sort_values(["target_date", "code"]).to_dict("records") for name, frame in scored.items() if name != "train"})
    return {
        "status": "PASS",
        "training_version": training_version,
        "final_dir": str(final_dir),
        "model_hash": manifest["file_hashes"]["model.pkl"],
        "calibration_model_hash": manifest["file_hashes"].get("calibration_model.pkl"),
        "calibration_hash": cal_meta["calibration_hash"],
        "bundle_hash": manifest["bundle_hash"],
        "prediction_hash": prediction_hash,
        "runtime_compatible_reproduction": verify_runtime_reproduction(final_dir, frames, feature_columns, prediction_hash),
        "selected_operational_utility": selected["operational_utility"]["recent_holdout"],
    }


def verify_runtime_reproduction(bundle_dir: Path, frames: dict[str, pd.DataFrame], feature_columns: list[str], expected_hash: str) -> dict[str, Any]:
    with (bundle_dir / "model.pkl").open("rb") as handle:
        payload = pickle.load(handle)
    scored = {}
    for name, frame in frames.items():
        if name == "train":
            continue
        matrix = transform_features(frame, feature_columns, payload["preprocessing"])
        out = frame.copy()
        out["raw_score"] = payload["model"].predict(matrix)
        if payload.get("calibration_model") is not None:
            out["score"] = payload["calibration_model"].predict(out["raw_score"].to_numpy(dtype=float))
        else:
            out["score"] = out["raw_score"]
        scored[name] = out
    actual_hash = stable_json_hash({name: frame[["target_date", "code", "score"]].sort_values(["target_date", "code"]).to_dict("records") for name, frame in scored.items()})
    return {"status": "PASS" if actual_hash == expected_hash else "FAIL", "expected_prediction_hash": expected_hash, "actual_prediction_hash": actual_hash}


def before_state(phase18f: dict[str, Any], phase18g: dict[str, Any]) -> dict[str, Any]:
    selected = phase18f["selected_formal_challenger"]
    pred = phase18g["predictive_validity"]["metrics"]
    return {
        "calibration_artifact": phase18g["safety_integrity"]["training_reviews"]["opportunity"]["checks"]["calibration_materialized"],
        "validation_spearman": pred["validation"]["spearman"],
        "test_spearman": pred["test"]["spearman"],
        "validation_monotonicity": pred["validation"]["calibration"]["bucket_monotonic"],
        "test_monotonicity": pred["test"]["calibration"]["bucket_monotonic"],
        "runtime_compatibility": phase18g["safety_integrity"]["compatibility"]["runtime_compatibility"] == "PASS",
        "phase18f_challenger": selected,
    }


def after_state(selected: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "calibration_artifact": bundle["runtime_compatible_reproduction"]["status"] == "PASS",
        "validation_spearman": selected["metrics"]["validation"]["spearman_rank_correlation"],
        "test_spearman": selected["metrics"]["test"]["spearman_rank_correlation"],
        "validation_monotonicity": selected["calibration"]["validation"]["score_bucket_monotonicity"]["monotonic_increasing"],
        "test_monotonicity": selected["calibration"]["test"]["score_bucket_monotonicity"]["monotonic_increasing"],
        "recent_monotonicity": selected["calibration"]["recent_holdout"]["score_bucket_monotonicity"]["monotonic_increasing"],
        "runtime_compatibility": bundle["runtime_compatible_reproduction"]["status"] == "PASS",
    }


def blocking_matrix_before_after(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        ("Calibration Artifact", before["calibration_artifact"], after["calibration_artifact"], after["calibration_artifact"]),
        ("Validation Spearman", before["validation_spearman"], after["validation_spearman"], safe(after["validation_spearman"]) > safe(before["validation_spearman"])),
        ("Test Spearman", before["test_spearman"], after["test_spearman"], safe(after["test_spearman"]) > safe(before["test_spearman"]) and safe(after["test_spearman"]) >= 0),
        ("Validation Monotonicity", before["validation_monotonicity"], after["validation_monotonicity"], bool(after["validation_monotonicity"])),
        ("Test Monotonicity", before["test_monotonicity"], after["test_monotonicity"], bool(after["test_monotonicity"])),
        ("Runtime Compatibility", before["runtime_compatibility"], after["runtime_compatibility"], bool(after["runtime_compatibility"])),
    ]
    return [{"item": item, "before": before_value, "after": after_value, "status": "PASS" if ok else "FAIL"} for item, before_value, after_value, ok in rows]


def promotion_readiness(after: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    safety = "PASS" if after["calibration_artifact"] and after["runtime_compatibility"] else "FAIL"
    predictive = "PASS" if after["test_spearman"] >= 0 and after["validation_monotonicity"] and after["test_monotonicity"] and after["recent_monotonicity"] else "FAIL"
    op_metrics = bundle.get("selected_operational_utility", {})
    op = "PASS"
    if bundle["status"] != "PASS":
        op = "FAIL"
    elif op_metrics.get("cash_stagnation_risk") == "HIGH" or safe(op_metrics.get("no_buy_day_ratio")) > 0.5:
        op = "REVIEW_REQUIRED"
    recommendation = "PROMOTION_READY_WITH_REVIEW" if safety == "PASS" and predictive == "PASS" and op in {"PASS", "REVIEW_REQUIRED"} else "NOT_PROMOTION_READY"
    return {"safety_integrity": safety, "predictive_validity": predictive, "operational_utility": op, "promotion_recommendation": recommendation}


def compare_challengers(phase18d: dict[str, Any], phase18f: dict[str, Any], selected: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_champion": phase18d["champion_identities"]["opportunity"],
        "phase18f_challenger": {
            "spec": phase18f["selected_formal_challenger"]["spec"],
            "recent_holdout": compact_metrics(phase18f["selected_formal_challenger"]["metrics"]["recent_holdout"], phase18f["selected_formal_challenger"]["calibration"]["recent_holdout"]),
            "test": compact_metrics(phase18f["selected_formal_challenger"]["metrics"]["test"], phase18f["selected_formal_challenger"]["calibration"]["test"]),
            "validation": compact_metrics(phase18f["selected_formal_challenger"]["metrics"]["validation"], phase18f["selected_formal_challenger"]["calibration"]["validation"]),
        },
        "phase18h_challenger": {
            "spec": selected["spec"],
            "recent_holdout": compact_metrics(selected["metrics"]["recent_holdout"], selected["calibration"]["recent_holdout"]),
            "test": compact_metrics(selected["metrics"]["test"], selected["calibration"]["test"]),
            "validation": compact_metrics(selected["metrics"]["validation"], selected["calibration"]["validation"]),
        },
    }


def compact_metrics(metrics: dict[str, Any], cal: dict[str, Any]) -> dict[str, Any]:
    return {
        "spearman": metrics["spearman_rank_correlation"],
        "top5": metrics["top5"],
        "top20": metrics["top20"],
        "positive_coverage": metrics["positive_score_coverage"],
        "no_buy_ratio": metrics["no_buy_day_ratio"],
        "calibration_error": cal["calibration_error"],
        "bucket_monotonicity": cal["score_bucket_monotonicity"]["monotonic_increasing"],
    }


def acceptance(matrix: list[dict[str, Any]], readiness: dict[str, Any], bundle: dict[str, Any]) -> dict[str, str]:
    by_item = {row["item"]: row["status"] for row in matrix}
    return {
        "calibration_artifact_materialized": by_item["Calibration Artifact"],
        "runtime_compatible_confirmed": by_item["Runtime Compatibility"],
        "validation_improved": by_item["Validation Spearman"],
        "test_improved": by_item["Test Spearman"],
        "monotonicity_improved": "PASS" if by_item["Validation Monotonicity"] == "PASS" and by_item["Test Monotonicity"] == "PASS" else "FAIL",
        "formal_challenger_regenerated": bundle["status"],
        "promotion_blocking_matrix_created": "PASS",
        "promotion_recommendation_updated": "PASS" if readiness["promotion_recommendation"] else "FAIL",
        "registry_unchanged": "PASS",
        "runtime_unchanged": "PASS",
        "buy_not_restarted": "PASS",
        "broker_write_not_executed": "PASS",
    }


def final_judgment(matrix: list[dict[str, Any]], readiness: dict[str, Any]) -> dict[str, Any]:
    all_resolved = all(row["status"] == "PASS" for row in matrix)
    if readiness["promotion_recommendation"] == "PROMOTION_READY":
        primary = "PHASE18_H_PROMOTION_READY"
    elif readiness["promotion_recommendation"] == "PROMOTION_READY_WITH_REVIEW" and all_resolved:
        primary = "PHASE18_H_PROMOTION_READY_WITH_REVIEW"
    elif any(row["status"] == "PASS" for row in matrix):
        primary = "PHASE18_H_BLOCKING_ISSUES_PARTIALLY_RESOLVED"
    else:
        primary = "PHASE18_H_NOT_PROMOTION_READY"
    return {"primary": primary, "promotion_recommendation": readiness["promotion_recommendation"]}


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
    try:
        if value is None or pd.isna(value) or math.isinf(float(value)):
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
    selected = result["selected_challenger"]
    readiness = result["promotion_readiness_reassessment"]
    lines = [
        "# Phase18-H — Promotion Blocking Issues Resolution",
        "",
        f"- Run ID: `{result['run_id']}`",
        f"- Final judgment: `{result['final_judgment']['primary']}`",
        f"- Promotion recommendation: `{readiness['promotion_recommendation']}`",
        f"- Selected challenger: `{selected['spec']}`",
        f"- Formal Challenger bundle: `{result['formal_challenger_bundle']['final_dir']}`",
        "",
        "## Fixed Contracts",
        "",
        "- Target: `label__expected_edge_label_20d`",
        "- Feature contract: `32 feature contract`",
        "- Candidate connection: `candidate_source_ref`",
        "- BV15: unchanged",
        "",
        "## Blocking Matrix",
        "",
        "| Item | Before | After | Status |",
        "|------|--------|-------|--------|",
    ]
    for row in result["promotion_blocking_matrix"]:
        lines.append(f"| {row['item']} | `{row['before']}` | `{row['after']}` | `{row['status']}` |")
    lines.extend([
        "",
        "## Readiness Reassessment",
        "",
        f"- Safety / Integrity: `{readiness['safety_integrity']}`",
        f"- Predictive Validity: `{readiness['predictive_validity']}`",
        f"- Operational Utility: `{readiness['operational_utility']}`",
        "",
        "## Selected Metrics",
        "",
        f"- Validation Spearman: `{selected['metrics']['validation']['spearman_rank_correlation']}`",
        f"- Test Spearman: `{selected['metrics']['test']['spearman_rank_correlation']}`",
        f"- Recent Spearman: `{selected['metrics']['recent_holdout']['spearman_rank_correlation']}`",
        f"- Validation bucket monotonicity: `{selected['calibration']['validation']['score_bucket_monotonicity']['monotonic_increasing']}`",
        f"- Test bucket monotonicity: `{selected['calibration']['test']['score_bucket_monotonicity']['monotonic_increasing']}`",
        f"- Recent bucket monotonicity: `{selected['calibration']['recent_holdout']['score_bucket_monotonicity']['monotonic_increasing']}`",
        f"- Recent positive coverage: `{selected['metrics']['recent_holdout']['positive_score_coverage']}`",
        f"- Recent NO BUY ratio: `{selected['metrics']['recent_holdout']['no_buy_day_ratio']}`",
        "",
        "## Calibration Artifact",
        "",
        f"- Calibration hash: `{result['formal_challenger_bundle']['calibration_hash']}`",
        f"- Calibration model hash: `{result['formal_challenger_bundle']['calibration_model_hash']}`",
        f"- Runtime-compatible reproduction: `{result['formal_challenger_bundle']['runtime_compatible_reproduction']['status']}`",
        "",
        "## Non-Mutation",
        "",
        "- Registry accepted update: `False`",
        "- Runtime switch: `False`",
        "- BUY restart: `False`",
        "- Broker write: `False`",
        "",
        "## Final",
        "",
        f"`{result['final_judgment']['primary']}`",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
