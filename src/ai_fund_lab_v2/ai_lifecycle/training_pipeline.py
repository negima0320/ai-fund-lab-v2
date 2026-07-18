from __future__ import annotations

import hashlib
import json
import os
import pickle
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.linear_model import SGDClassifier, SGDRegressor
from sklearn.metrics import average_precision_score, mean_absolute_error, mean_squared_error, roc_auc_score


Component = Literal["Candidate", "Opportunity"]
CREATED_AT = "2026-07-17T00:00:00+00:00"
TARGET_HORIZON_BUSINESS_DAYS = 20

REQUIRED_DATASET_FILES = (
    "dataset.parquet",
    "dataset_metadata.json",
    "feature_schema.json",
    "target_schema.json",
    "lineage.json",
    "data_quality.json",
    "date_coverage.json",
    "hash_manifest.json",
    "status.json",
)

REQUIRED_TRAINING_FILES = (
    "model.pkl",
    "training_metadata.json",
    "training_config.json",
    "dataset_reference.json",
    "feature_schema.json",
    "target_schema.json",
    "split_definition.json",
    "validation_metrics.json",
    "test_metrics.json",
    "recent_holdout_metrics.json",
    "calibration_metrics.json",
    "regime_metrics.json",
    "prediction_distribution.json",
    "reproducibility.json",
    "lineage.json",
    "hash_manifest.json",
    "status.json",
)


@dataclass(frozen=True)
class DatasetAuthority:
    component: Component
    dataset_dir: Path
    dataset_hash: str
    feature_schema_hash: str
    target_schema_hash: str
    dataset_version: str


@dataclass(frozen=True)
class TrainingConfig:
    component: Component
    challenger_name: str
    model_kind: str
    target_label: str
    random_seed: int = 42
    max_iter: int = 30
    alpha: float = 0.0001
    recent_fixed_years: int | None = None
    calibration: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "challenger_name": self.challenger_name,
            "model_kind": self.model_kind,
            "target_label": self.target_label,
            "random_seed": self.random_seed,
            "max_iter": self.max_iter,
            "alpha": self.alpha,
            "recent_fixed_years": self.recent_fixed_years,
            "calibration": self.calibration,
        }


def verify_dataset_authority(authority: DatasetAuthority) -> dict[str, Any]:
    missing = [name for name in REQUIRED_DATASET_FILES if not (authority.dataset_dir / name).is_file()]
    if missing:
        return {"status": "FAIL", "missing_files": missing}
    status = _read_json(authority.dataset_dir / "status.json")
    metadata = _read_json(authority.dataset_dir / "dataset_metadata.json")
    manifest = _read_json(authority.dataset_dir / "hash_manifest.json")
    validations = {item["name"]: item["status"] for item in status.get("validations", [])}
    checks = {
        "status_pass": status.get("status") == "PASS" and status.get("validation_status") == "PASS",
        "dataset_hash_match": manifest.get("dataset_hash") == authority.dataset_hash,
        "feature_schema_hash_match": manifest.get("feature_schema_hash") == authority.feature_schema_hash,
        "target_schema_hash_match": manifest.get("target_schema_hash") == authority.target_schema_hash,
        "metadata_component_match": metadata.get("component") == authority.component,
        "dataset_version_match": metadata.get("dataset_version") == authority.dataset_version,
        "lineage_complete": validations.get("Lineage") == "PASS",
        "no_leakage_pass": validations.get("Leakage") == "PASS",
        "pit_pass": validations.get("PIT") == "PASS",
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def run_training_pipeline(
    *,
    authority: DatasetAuthority,
    output_dir: Path,
    config: TrainingConfig,
    champion_identity: dict[str, Any],
    report_dir: Path,
) -> dict[str, Any]:
    authority_result = verify_dataset_authority(authority)
    if authority_result["status"] != "PASS":
        failure = write_failure_artifact(report_dir, component=authority.component, reason="dataset authority failed", evidence=authority_result)
        return {"status": "FAIL", "failure_artifact": str(failure), "dataset_authority": authority_result}

    dataset = pd.read_parquet(authority.dataset_dir / "dataset.parquet")
    feature_columns = [item["name"] for item in _read_json(authority.dataset_dir / "feature_schema.json")["columns"]]
    target_columns = [item["name"] for item in _read_json(authority.dataset_dir / "target_schema.json")["columns"]]
    forbidden = audit_forbidden_features(feature_columns)
    if forbidden["status"] != "PASS" or config.target_label not in dataset.columns:
        failure = write_failure_artifact(report_dir, component=authority.component, reason="schema or forbidden feature failed", evidence=forbidden)
        return {"status": "FAIL", "failure_artifact": str(failure), "dataset_authority": authority_result}

    split = make_time_series_split(dataset)
    split_check = validate_split_boundaries(split)
    if split_check["status"] != "PASS":
        failure = write_failure_artifact(report_dir, component=authority.component, reason="split boundary failed", evidence=split_check)
        return {"status": "FAIL", "failure_artifact": str(failure), "dataset_authority": authority_result}

    train_frame = dataset[dataset["target_date"].astype(str).isin(split["train"]["dates"])].copy()
    if config.recent_fixed_years:
        min_train = (pd.to_datetime(split["train"]["end"]) - pd.DateOffset(years=config.recent_fixed_years)).strftime("%Y-%m-%d")
        train_frame = train_frame[train_frame["target_date"].astype(str) >= min_train].copy()
    validation_frame = dataset[dataset["target_date"].astype(str).isin(split["validation"]["dates"])].copy()
    test_frame = dataset[dataset["target_date"].astype(str).isin(split["test"]["dates"])].copy()
    recent_frame = dataset[dataset["target_date"].astype(str).isin(split["recent_holdout"]["dates"])].copy()

    preprocessing = fit_preprocessing(train_frame, feature_columns)
    x_train = transform_features(train_frame, feature_columns, preprocessing)
    y_train = target_values(train_frame, config)
    model = fit_model(x_train, y_train, config)

    scored = {
        "validation": score_frame(validation_frame, feature_columns, preprocessing, model, config),
        "test": score_frame(test_frame, feature_columns, preprocessing, model, config),
        "recent_holdout": score_frame(recent_frame, feature_columns, preprocessing, model, config),
    }
    metrics = {
        name: evaluate_component(frame, component=authority.component, target_label=config.target_label)
        for name, frame in scored.items()
    }
    calibration = evaluate_calibration(scored, component=authority.component, target_label=config.target_label)
    regime = evaluate_regime(scored, component=authority.component)
    prediction_distribution = {name: prediction_distribution_block(frame) for name, frame in scored.items()}
    operational_utility = evaluate_operational_utility(scored["recent_holdout"], component=authority.component)
    model_payload = {
        "component": authority.component,
        "config": config.to_dict(),
        "feature_columns": feature_columns,
        "target_columns": target_columns,
        "preprocessing": preprocessing,
        "model": model,
    }
    training_version = training_version_for(authority=authority, config=config, feature_columns=feature_columns, target_columns=target_columns)
    final_dir = output_dir / training_version
    tmp_dir = output_dir / f".{training_version}.tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=False)

    with (tmp_dir / "model.pkl").open("wb") as handle:
        pickle.dump(model_payload, handle)
    dataset_reference = {
        "component": authority.component,
        "dataset_dir": str(authority.dataset_dir),
        "dataset_hash": authority.dataset_hash,
        "dataset_version": authority.dataset_version,
        "feature_schema_hash": authority.feature_schema_hash,
        "target_schema_hash": authority.target_schema_hash,
    }
    reproducibility = reproducibility_payload(tmp_dir / "model.pkl", config=config, dataset_reference=dataset_reference, scored=scored)
    lineage = {
        "dataset_reference": dataset_reference,
        "champion_identity": champion_identity,
        "challenger_identity": {"name": config.challenger_name, "training_version": training_version},
        "atomic_buy_ai_bundle_promotion_performed": False,
        "registry_accepted_update_performed": False,
        "runtime_switch_performed": False,
    }
    _write_json(tmp_dir / "training_metadata.json", {
        "component": authority.component,
        "training_version": training_version,
        "created_at": CREATED_AT,
        "training_executed": True,
        "promotion_performed": False,
        "registry_accepted_update_performed": False,
        "runtime_switch_performed": False,
        "buy_restarted": False,
        "broker_write_executed": False,
        "operational_utility": operational_utility,
    })
    _write_json(tmp_dir / "training_config.json", {**config.to_dict(), "config_hash": stable_json_hash(config.to_dict())})
    _write_json(tmp_dir / "dataset_reference.json", dataset_reference)
    _copy_json(authority.dataset_dir / "feature_schema.json", tmp_dir / "feature_schema.json")
    _copy_json(authority.dataset_dir / "target_schema.json", tmp_dir / "target_schema.json")
    _write_json(tmp_dir / "split_definition.json", split)
    _write_json(tmp_dir / "validation_metrics.json", metrics["validation"])
    _write_json(tmp_dir / "test_metrics.json", metrics["test"])
    _write_json(tmp_dir / "recent_holdout_metrics.json", metrics["recent_holdout"])
    _write_json(tmp_dir / "calibration_metrics.json", calibration)
    _write_json(tmp_dir / "regime_metrics.json", regime)
    _write_json(tmp_dir / "prediction_distribution.json", prediction_distribution)
    _write_json(tmp_dir / "reproducibility.json", reproducibility)
    _write_json(tmp_dir / "lineage.json", lineage)
    manifest = hash_manifest(tmp_dir)
    _write_json(tmp_dir / "hash_manifest.json", manifest)
    status = {
        "status": "PASS",
        "dataset_authority": authority_result,
        "split_validation": split_check,
        "forbidden_feature_audit": forbidden,
        "model_artifact_integrity": "PASS" if manifest["file_hashes"].get("model.pkl") else "FAIL",
        "reproducibility_status": reproducibility["status"],
        "training_artifact_bundle_publication": "PASS",
    }
    _write_json(tmp_dir / "status.json", status)
    missing = [name for name in REQUIRED_TRAINING_FILES if not (tmp_dir / name).is_file()]
    if missing:
        failure = write_failure_artifact(report_dir, component=authority.component, reason="training bundle missing files", evidence={"missing": missing})
        shutil.rmtree(tmp_dir)
        return {"status": "FAIL", "failure_artifact": str(failure), "missing": missing}
    if final_dir.exists():
        shutil.rmtree(final_dir)
    os.replace(tmp_dir, final_dir)
    return {
        "status": "PASS",
        "component": authority.component,
        "training_version": training_version,
        "final_dir": str(final_dir),
        "dataset_authority": authority_result,
        "split_validation": split_check,
        "metrics": metrics,
        "calibration": calibration,
        "regime": regime,
        "prediction_distribution": prediction_distribution,
        "operational_utility": operational_utility,
        "reproducibility": reproducibility,
        "hash_manifest": manifest,
        "champion_identity": champion_identity,
        "challenger_identity": {"name": config.challenger_name, "training_version": training_version},
    }


def fit_preprocessing(frame: pd.DataFrame, feature_columns: list[str]) -> dict[str, Any]:
    medians: dict[str, float] = {}
    categories: dict[str, dict[str, int]] = {}
    for column in feature_columns:
        series = frame[column]
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
            numeric = pd.to_numeric(series, errors="coerce")
            medians[column] = float(numeric.median()) if pd.notna(numeric.median()) else 0.0
        else:
            values = sorted(str(value) for value in series.dropna().unique())
            categories[column] = {value: index for index, value in enumerate(values)}
            medians[column] = -1.0
    return {"medians": medians, "categories": categories}


def transform_features(frame: pd.DataFrame, feature_columns: list[str], preprocessing: dict[str, Any]) -> np.ndarray:
    matrix = pd.DataFrame(index=frame.index)
    for column in feature_columns:
        if column in preprocessing["categories"]:
            mapping = preprocessing["categories"][column]
            matrix[column] = frame[column].map(lambda value: mapping.get(str(value), -1) if pd.notna(value) else -1)
        else:
            matrix[column] = pd.to_numeric(frame[column], errors="coerce").fillna(float(preprocessing["medians"].get(column, 0.0)))
    return matrix.to_numpy(dtype=np.float64)


def target_values(frame: pd.DataFrame, config: TrainingConfig) -> np.ndarray:
    values = frame[config.target_label]
    if config.component == "Candidate":
        return values.astype(bool).astype(np.int8).to_numpy()
    return pd.to_numeric(values, errors="coerce").fillna(0.0).to_numpy(dtype=np.float64)


def fit_model(x_train: np.ndarray, y_train: np.ndarray, config: TrainingConfig) -> Any:
    if config.component == "Candidate":
        model = SGDClassifier(
            loss="log_loss",
            penalty="l2",
            alpha=config.alpha,
            max_iter=config.max_iter,
            tol=1e-4,
            random_state=config.random_seed,
            class_weight="balanced",
            shuffle=False,
        )
    else:
        model = SGDRegressor(
            loss="squared_error",
            penalty="l2",
            alpha=config.alpha,
            max_iter=config.max_iter,
            tol=1e-4,
            random_state=config.random_seed,
            shuffle=False,
        )
    model.fit(x_train, y_train)
    return model


def score_frame(frame: pd.DataFrame, feature_columns: list[str], preprocessing: dict[str, Any], model: Any, config: TrainingConfig) -> pd.DataFrame:
    scored = frame.copy()
    matrix = transform_features(scored, feature_columns, preprocessing)
    if config.component == "Candidate" and hasattr(model, "predict_proba"):
        scored["score"] = model.predict_proba(matrix)[:, 1]
    else:
        scored["score"] = model.predict(matrix)
    return scored


def evaluate_component(frame: pd.DataFrame, *, component: Component, target_label: str) -> dict[str, Any]:
    if frame.empty:
        return {"status": "FAIL", "row_count": 0}
    if component == "Candidate":
        y = frame[target_label].astype(bool).astype(int).to_numpy()
        score = frame["score"].to_numpy(dtype=float)
        auc = float(roc_auc_score(y, score)) if len(set(y.tolist())) > 1 else None
        return {
            "status": "PASS",
            "row_count": int(len(frame)),
            "target_date_count": int(frame["target_date"].nunique()),
            "auc": round_float(auc),
            "average_precision": round_float(average_precision_score(y, score)),
            "precision_at_top_50": precision_at_k(y, score, 50),
            "top50_mean_future_return_20d": top_k(frame, "score", 50)["label__future_return_20d"].mean().round(6).item(),
            "positive_score_coverage": round_float((score > 0.5).mean()),
        }
    y_true = pd.to_numeric(frame[target_label], errors="coerce").fillna(0.0)
    score = pd.to_numeric(frame["score"], errors="coerce").fillna(0.0)
    return {
        "status": "PASS",
        "row_count": int(len(frame)),
        "target_date_count": int(frame["target_date"].nunique()),
        "mae": round_float(mean_absolute_error(y_true, score)),
        "rmse": round_float(float(mean_squared_error(y_true, score)) ** 0.5),
        "spearman_rank_correlation": round_float(y_true.corr(score, method="spearman")),
        "top5": topn_return_block(frame, 5),
        "top20": topn_return_block(frame, 20),
        "score_bucket_monotonicity": score_bucket_monotonicity(frame),
        "positive_score_coverage": round_float((score > 0).mean()),
        "all_negative_day_count": int(frame.groupby("target_date")["score"].max().le(0).sum()),
        "no_buy_day_ratio": round_float(frame.groupby("target_date")["score"].max().le(0).mean()),
        "positive_candidate_count_per_day": round_float(frame.groupby("target_date")["score"].apply(lambda s: (s > 0).sum()).mean()),
        "downside_bad_rate_top20": round_float(top_n_by_date(frame, 20)["label__downside_bad_20d"].astype(bool).mean()),
    }


def topn_return_block(frame: pd.DataFrame, top_n_value: int) -> dict[str, Any]:
    selected = top_n_by_date(frame, top_n_value)
    returns = pd.to_numeric(selected["label__future_return_20d"], errors="coerce")
    return {
        "row_count": int(len(selected)),
        "mean_realized_return_20d": round_float(returns.mean()),
        "hit_rate": round_float((returns > 0).mean()),
        "median_realized_return_20d": round_float(returns.median()),
    }


def top_n_by_date(frame: pd.DataFrame, top_n_value: int) -> pd.DataFrame:
    return frame.sort_values(["target_date", "score", "code"], ascending=[True, False, True]).groupby("target_date", group_keys=False).head(top_n_value)


def top_k(frame: pd.DataFrame, score_column: str, k: int) -> pd.DataFrame:
    return frame.sort_values(score_column, ascending=False).head(min(k, len(frame)))


def precision_at_k(y: np.ndarray, score: np.ndarray, k: int) -> float | None:
    if len(y) == 0:
        return None
    order = np.argsort(score)[::-1][: min(k, len(y))]
    return round_float(y[order].mean())


def score_bucket_monotonicity(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"status": "FAIL"}
    try:
        buckets = pd.qcut(frame["score"], q=min(5, frame["score"].nunique()), duplicates="drop")
        grouped = frame.groupby(buckets, observed=True)["label__future_return_20d"].mean().tolist()
        monotonic = all(left <= right for left, right in zip(grouped, grouped[1:]))
        return {"status": "PASS", "monotonic_increasing": bool(monotonic), "bucket_means": [round_float(value) for value in grouped]}
    except Exception:
        return {"status": "REVIEW_REQUIRED", "monotonic_increasing": False, "bucket_means": []}


def evaluate_calibration(scored: dict[str, pd.DataFrame], *, component: Component, target_label: str) -> dict[str, Any]:
    if component == "Candidate":
        return {"status": "PASS", "methods": {"none": {"calibration_error": None}}, "selected": "none"}
    methods: dict[str, Any] = {}
    for name, frame in scored.items():
        target = pd.to_numeric(frame[target_label], errors="coerce").fillna(0.0)
        score = pd.to_numeric(frame["score"], errors="coerce").fillna(0.0)
        methods[name] = {
            "method": "none",
            "calibration_error": round_float((score - target).abs().mean()),
            "positive_score_sign_consistency": round_float(((score > 0) == (target > 0)).mean()),
            "positive_rate": round_float((score > 0).mean()),
            "all_negative_day_count": int(frame.groupby("target_date")["score"].max().le(0).sum()),
        }
    return {"status": "PASS", "methods": {"none": methods}, "selected": "none"}


def evaluate_regime(scored: dict[str, pd.DataFrame], *, component: Component) -> dict[str, Any]:
    merged = pd.concat(scored.values(), ignore_index=True)
    if merged.empty:
        return {"status": "FAIL"}
    regime_column = "feature__market_downtrend_flag" if "feature__market_downtrend_flag" in merged.columns else None
    if regime_column:
        merged["regime"] = np.where(merged[regime_column].astype(bool), "bearish", "bullish_or_neutral")
    elif "feature__volatility_return_std_20d" in merged.columns:
        vol = pd.to_numeric(merged["feature__volatility_return_std_20d"], errors="coerce")
        merged["regime"] = np.where(vol >= vol.median(), "high_volatility", "low_volatility")
    else:
        merged["regime"] = "neutral"
    blocks = {}
    for regime, frame in merged.groupby("regime"):
        blocks[str(regime)] = evaluate_component(frame, component=component, target_label=("label__momentum_candidate_label" if component == "Candidate" else "label__expected_edge_label_20d"))
    return {"status": "PASS", "regimes": blocks}


def evaluate_operational_utility(frame: pd.DataFrame, *, component: Component) -> dict[str, Any]:
    if component == "Candidate":
        return {"status": "PASS", "positive_candidate_coverage": round_float((frame["score"] > 0.5).mean())}
    by_day = frame.groupby("target_date")["score"]
    top5 = top_n_by_date(frame, 5)
    top20 = top_n_by_date(frame, 20)
    return {
        "status": "PASS",
        "positive_candidate_coverage": round_float((frame["score"] > 0).mean()),
        "no_buy_day_ratio": round_float(by_day.max().le(0).mean()),
        "expected_opportunity_frequency": round_float((by_day.apply(lambda s: (s > 0).sum()) > 0).mean()),
        "rank_1_5_performance": topn_return_block(frame, 5),
        "rank_1_20_performance": topn_return_block(frame, 20),
        "turnover_proxy": round_float(top5.groupby("target_date")["code"].nunique().mean()),
        "transaction_cost_sensitivity": {"cost_bps": 30, "top5_cost_adjusted_edge": round_float(top5["label__future_return_20d"].mean() - 0.003)},
        "cost_adjusted_edge": round_float(top20["label__future_return_20d"].mean() - 0.003),
        "concentration": round_float(top20["code"].value_counts(normalize=True).head(10).sum()),
        "cash_stagnation_risk": "HIGH" if by_day.max().le(0).mean() > 0.5 else "LOW",
        "top_n_forced_buy_used": False,
        "negative_expected_edge_buy_allowed": False,
        "no_buy_reason_ignored": False,
    }


def prediction_distribution_block(frame: pd.DataFrame) -> dict[str, Any]:
    score = pd.to_numeric(frame["score"], errors="coerce")
    return {
        "row_count": int(len(frame)),
        "score_min": round_float(score.min()),
        "score_max": round_float(score.max()),
        "score_mean": round_float(score.mean()),
        "score_std": round_float(score.std()),
        "positive_rate": round_float((score > 0).mean()),
    }


def make_time_series_split(dataset: pd.DataFrame) -> dict[str, Any]:
    dates = sorted(dataset["target_date"].astype(str).unique().tolist())
    train = [date for date in dates if date <= "2024-12-02"]
    validation = [date for date in dates if "2025-01-06" <= date <= "2025-12-01"]
    test = [date for date in dates if "2026-01-05" <= date <= "2026-03-03"]
    recent = [date for date in dates if "2026-04-01" <= date <= "2026-05-15"]
    return {
        "policy": "time_series_with_20bd_embargo",
        "target_horizon_business_days": TARGET_HORIZON_BUSINESS_DAYS,
        "embargo_business_days": TARGET_HORIZON_BUSINESS_DAYS,
        "random_split_used": False,
        "train": _split_block(train),
        "validation": _split_block(validation),
        "test": _split_block(test),
        "recent_holdout": _split_block(recent),
    }


def _split_block(dates: list[str]) -> dict[str, Any]:
    return {"start": dates[0] if dates else None, "end": dates[-1] if dates else None, "date_count": len(dates), "dates": dates}


def validate_split_boundaries(split: dict[str, Any]) -> dict[str, Any]:
    names = ["train", "validation", "test", "recent_holdout"]
    non_empty = all(split[name]["date_count"] > 0 for name in names)
    gaps = {
        "train_to_validation": business_gap(split["train"]["end"], split["validation"]["start"]),
        "validation_to_test": business_gap(split["validation"]["end"], split["test"]["start"]),
        "test_to_recent_holdout": business_gap(split["test"]["end"], split["recent_holdout"]["start"]),
    }
    gap_ok = all(value >= TARGET_HORIZON_BUSINESS_DAYS for value in gaps.values())
    return {"status": "PASS" if non_empty and gap_ok else "FAIL", "non_empty": non_empty, "gaps": gaps, "label_leakage_prevention": "PASS" if gap_ok else "FAIL"}


def business_gap(left: str | None, right: str | None) -> int:
    if left is None or right is None:
        return 0
    return len(pd.bdate_range(pd.to_datetime(left) + pd.offsets.BDay(1), pd.to_datetime(right) - pd.offsets.BDay(1)))


def audit_forbidden_features(feature_columns: list[str]) -> dict[str, Any]:
    forbidden_terms = ("future_return_", "future_max_return_", "future_max_drawdown_", "downside_bad_", "top_decile_", "expected_edge", "selected", "bought", "cash", "portfolio", "pnl", "backtest")
    bad = [column for column in feature_columns if any(term in column.replace("feature__", "", 1).lower() for term in forbidden_terms)]
    return {"status": "PASS" if not bad else "FAIL", "forbidden_feature_columns": bad}


def reproducibility_payload(model_path: Path, *, config: TrainingConfig, dataset_reference: dict[str, Any], scored: dict[str, pd.DataFrame]) -> dict[str, Any]:
    prediction_hash = stable_json_hash({
        name: frame[["target_date", "code", "score"]].sort_values(["target_date", "code"]).to_dict("records")
        for name, frame in scored.items()
    })
    return {
        "status": "PASS",
        "model_content_hash": file_hash(model_path),
        "training_config_hash": stable_json_hash(config.to_dict()),
        "dataset_identity": dataset_reference,
        "prediction_hash": prediction_hash,
        "feature_schema_hash": dataset_reference["feature_schema_hash"],
        "target_schema_hash": dataset_reference["target_schema_hash"],
    }


def training_version_for(*, authority: DatasetAuthority, config: TrainingConfig, feature_columns: list[str], target_columns: list[str]) -> str:
    payload = {
        "component": authority.component,
        "dataset_hash": authority.dataset_hash,
        "config": config.to_dict(),
        "feature_columns": feature_columns,
        "target_columns": target_columns,
    }
    return f"{authority.component.lower()}_training_{stable_json_hash(payload)[:16]}"


def hash_manifest(directory: Path) -> dict[str, Any]:
    file_hashes = {path.name: file_hash(path) for path in sorted(directory.iterdir()) if path.is_file() and path.name != "hash_manifest.json"}
    return {"file_hashes": file_hashes, "bundle_hash": stable_json_hash(file_hashes), "model_hash": file_hashes.get("model.pkl")}


def compare_training_bundles(primary: dict[str, Any], rerun: dict[str, Any]) -> dict[str, Any]:
    if primary.get("status") != "PASS" or rerun.get("status") != "PASS":
        return {"status": "FAIL"}
    checks = {
        "model_content_hash": primary["hash_manifest"]["model_hash"] == rerun["hash_manifest"]["model_hash"],
        "training_config_hash": primary["reproducibility"]["training_config_hash"] == rerun["reproducibility"]["training_config_hash"],
        "metrics_hash": stable_json_hash(primary["metrics"]) == stable_json_hash(rerun["metrics"]),
        "feature_schema_hash": primary["reproducibility"]["feature_schema_hash"] == rerun["reproducibility"]["feature_schema_hash"],
        "target_schema_hash": primary["reproducibility"]["target_schema_hash"] == rerun["reproducibility"]["target_schema_hash"],
        "dataset_identity": primary["reproducibility"]["dataset_identity"] == rerun["reproducibility"]["dataset_identity"],
        "prediction_hash": primary["reproducibility"]["prediction_hash"] == rerun["reproducibility"]["prediction_hash"],
    }
    return {"status": "PASS" if all(checks.values()) else "REVIEW_REQUIRED", "checks": checks}


def write_failure_artifact(report_dir: Path, *, component: str, reason: str, evidence: dict[str, Any]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{component.lower()}_training_failure.json"
    _write_json(path, {"status": "FAILED", "component": component, "reason": reason, "evidence": evidence, "registry_changed": False, "runtime_changed": False})
    return path


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def round_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), 6)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _copy_json(src: Path, dst: Path) -> None:
    _write_json(dst, _read_json(src))
