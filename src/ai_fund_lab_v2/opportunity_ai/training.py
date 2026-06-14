from __future__ import annotations

import json
import math
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

PHASE = "Phase5-E"
MODEL_VERSION = "opportunity_model_phase5e_v1"
TARGET_LABEL = "label__expected_edge_label_20d"
READY_FOR_PHASE5F_INFERENCE = "READY_FOR_PHASE5F_INFERENCE"
TRAINING_COMPLETE_WITH_WARNINGS = "TRAINING_COMPLETE_WITH_WARNINGS"
BLOCKED_BY_DATASET = "BLOCKED_BY_DATASET"
BLOCKED_BY_LEAKAGE_AUDIT = "BLOCKED_BY_LEAKAGE_AUDIT"
BLOCKED_BY_MODEL_TRAINING = "BLOCKED_BY_MODEL_TRAINING"

DEFAULT_DATASET_PATH = Path("reports/opportunity_ai/phase5d/opportunity_dataset.parquet")
DEFAULT_MODEL_DIR = Path("models/opportunity_ai/phase5e")
DEFAULT_REPORT_DIR = Path("reports/opportunity_ai/phase5e")

METRICS_FILENAME = "opportunity_training_metrics.json"
AUDIT_FILENAME = "opportunity_training_audit.json"
MODEL_FILENAME = "opportunity_model.pkl"

EVALUATION_LABELS = (
    "label__future_return_20d",
    "label__future_max_return_20d",
    "label__future_max_drawdown_20d",
    "label__downside_bad_20d",
    "label__top_decile_20d",
)

REQUIRED_SPLITS = ("train", "validation", "test")

FORBIDDEN_FEATURE_PREFIXES = (
    "future_return_",
    "future_max_return_",
    "future_max_drawdown_",
    "downside_bad_",
    "top_decile_",
    "expected_edge_label_",
    "risk_adjusted_future_return_",
    "opportunity_rank_label_",
    "opportunity_quantile_label_",
    "is_top",
    "high_expected_edge_",
    "opportunity_positive_",
)

FORBIDDEN_FEATURE_TERMS = (
    "trade_result",
    "trade_profit",
    "selected",
    "bought",
    "sold",
    "cash",
    "portfolio",
    "annual_return",
    "final_assets",
    "backtest",
    "paper_trading",
    "pm_multiplier",
    "opportunity_output",
    "candidate_evaluation",
    "expected_edge_score",
    "buy_rank",
)


@dataclass(frozen=True)
class OpportunityTrainingResult:
    metrics: dict[str, Any]
    audit: dict[str, Any]


def train_opportunity_model(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    model_dir: Path = DEFAULT_MODEL_DIR,
    report_dir: Path = DEFAULT_REPORT_DIR,
    created_at: str | None = None,
) -> OpportunityTrainingResult:
    created_at = created_at or now_utc()
    model_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / MODEL_FILENAME
    metrics_path = report_dir / METRICS_FILENAME
    audit_path = report_dir / AUDIT_FILENAME

    if not dataset_path.is_file():
        metrics, audit = _blocked_payload(
            BLOCKED_BY_DATASET,
            "Phase5-D opportunity dataset artifact is missing.",
            dataset_path=dataset_path,
            model_path=model_path,
            metrics_path=metrics_path,
            audit_path=audit_path,
            created_at=created_at,
        )
        write_json(metrics_path, metrics)
        write_json(audit_path, audit)
        return OpportunityTrainingResult(metrics=metrics, audit=audit)

    dataset = pd.read_parquet(dataset_path)
    feature_columns = sorted(column for column in dataset.columns if str(column).startswith("feature__"))
    label_columns = sorted(column for column in dataset.columns if str(column).startswith("label__"))
    audit = audit_opportunity_training_dataset(dataset, feature_columns=feature_columns, label_columns=label_columns, created_at=created_at)
    if audit["leakage_audit_status"] != "OK":
        metrics = _metrics_shell(
            readiness_status=BLOCKED_BY_LEAKAGE_AUDIT,
            dataset_path=dataset_path,
            model_path=model_path,
            metrics_path=metrics_path,
            audit_path=audit_path,
            created_at=created_at,
            audit=audit,
        )
        metrics["status"] = "BLOCKED"
        metrics["training_executed"] = False
        metrics["recommended_next_action"] = "Remove forbidden training features before Phase5-E training."
        write_json(metrics_path, metrics)
        write_json(audit_path, audit)
        return OpportunityTrainingResult(metrics=metrics, audit=audit)

    splits = split_dataset(dataset)
    split_missing = [name for name in REQUIRED_SPLITS if splits[name].empty]
    if TARGET_LABEL not in dataset.columns or split_missing:
        audit = {**audit, "readiness_status": BLOCKED_BY_DATASET, "split_missing": split_missing}
        metrics = _metrics_shell(
            readiness_status=BLOCKED_BY_DATASET,
            dataset_path=dataset_path,
            model_path=model_path,
            metrics_path=metrics_path,
            audit_path=audit_path,
            created_at=created_at,
            audit=audit,
        )
        metrics["status"] = "BLOCKED"
        metrics["training_executed"] = False
        metrics["recommended_next_action"] = "Rebuild Phase5-D dataset with target label and train/validation/test splits."
        write_json(metrics_path, metrics)
        write_json(audit_path, audit)
        return OpportunityTrainingResult(metrics=metrics, audit=audit)

    try:
        preprocessing = fit_preprocessing(splits["train"], feature_columns)
        x_train = transform_features(splits["train"], feature_columns, preprocessing)
        x_validation = transform_features(splits["validation"], feature_columns, preprocessing)
        x_test = transform_features(splits["test"], feature_columns, preprocessing)
        y_train = target_array(splits["train"])
        y_validation = target_array(splits["validation"])
        y_test = target_array(splits["test"])

        model, model_type, model_params = fit_model(x_train, y_train)
        train_scores = model.predict(x_train)
        validation_scores = model.predict(x_validation)
        test_scores = model.predict(x_test)
    except Exception as exc:  # pragma: no cover - defensive blocker
        audit = {**audit, "readiness_status": BLOCKED_BY_MODEL_TRAINING, "model_training_error": f"{type(exc).__name__}: {exc}"}
        metrics = _metrics_shell(
            readiness_status=BLOCKED_BY_MODEL_TRAINING,
            dataset_path=dataset_path,
            model_path=model_path,
            metrics_path=metrics_path,
            audit_path=audit_path,
            created_at=created_at,
            audit=audit,
        )
        metrics["status"] = "BLOCKED"
        metrics["training_executed"] = False
        metrics["recommended_next_action"] = "Inspect Phase5-E model training error."
        write_json(metrics_path, metrics)
        write_json(audit_path, audit)
        return OpportunityTrainingResult(metrics=metrics, audit=audit)

    baseline_state = fit_simple_rule_baseline(splits["train"])
    scored_splits = {
        "train": add_scores(splits["train"], model_score=train_scores, simple_rule_state=baseline_state),
        "validation": add_scores(splits["validation"], model_score=validation_scores, simple_rule_state=baseline_state),
        "test": add_scores(splits["test"], model_score=test_scores, simple_rule_state=baseline_state),
    }
    regression_metrics = {
        "train": regression_metric_block(y_train, train_scores),
        "validation": regression_metric_block(y_validation, validation_scores),
        "test": regression_metric_block(y_test, test_scores),
    }
    ranking_metrics = {
        split_name: evaluate_rankers(scored_frame)
        for split_name, scored_frame in scored_splits.items()
        if split_name in {"validation", "test"}
    }
    validation_test_gap = calculate_validation_test_gap(regression_metrics, ranking_metrics)
    overfit_warning = detect_overfit_warning(regression_metrics, ranking_metrics, train_rows=len(splits["train"]))
    readiness_status = TRAINING_COMPLETE_WITH_WARNINGS if overfit_warning else READY_FOR_PHASE5F_INFERENCE

    model_payload = {
        "phase": PHASE,
        "model_version": MODEL_VERSION,
        "model_type": model_type,
        "model_params": model_params,
        "target_label": TARGET_LABEL,
        "feature_columns": feature_columns,
        "label_columns": label_columns,
        "evaluation_labels": list(EVALUATION_LABELS),
        "preprocessing": preprocessing,
        "simple_rule_baseline": baseline_state,
        "model": model,
        "created_at": created_at,
        "training_executed": True,
        "inference_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
    }
    with model_path.open("wb") as handle:
        pickle.dump(model_payload, handle)

    audit = {
        **audit,
        "model_trained": True,
        "validation_metric_available": True,
        "test_metric_available": True,
        "overfit_warning": overfit_warning,
        "readiness_status": readiness_status,
    }
    metrics = {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": readiness_status,
        "created_at": created_at,
        "model_version": MODEL_VERSION,
        "model_type": model_type,
        "model_params": model_params,
        "dataset_path": str(dataset_path),
        "model_artifact_path": str(model_path),
        "metrics_path": str(metrics_path),
        "audit_path": str(audit_path),
        "target_label": TARGET_LABEL,
        "feature_columns": feature_columns,
        "label_columns": label_columns,
        "evaluation_labels": list(EVALUATION_LABELS),
        "dataset_row_count": int(len(dataset)),
        "train_rows": int(len(splits["train"])),
        "validation_rows": int(len(splits["validation"])),
        "test_rows": int(len(splits["test"])),
        "feature_column_count": len(feature_columns),
        "label_column_count": len(label_columns),
        "regression_metrics": regression_metrics,
        "ranking_metrics": ranking_metrics,
        "candidate_top50_vs_opportunity_topn": {
            split_name: block["rankers"]
            for split_name, block in ranking_metrics.items()
        },
        "validation_test_gap": validation_test_gap,
        "overfit_warning": overfit_warning,
        "small_dataset_warning": bool(len(splits["train"]) < 5000),
        "leakage_audit_status": audit["leakage_audit_status"],
        "training_executed": True,
        "inference_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "recommended_next_action": (
            "Review overfit warning and consider Phase5-E feature/model tuning before Phase5-F."
            if overfit_warning
            else "Proceed to Phase5-F Opportunity Inference."
        ),
    }
    write_json(metrics_path, metrics)
    write_json(audit_path, audit)
    return OpportunityTrainingResult(metrics=metrics, audit=audit)


def audit_opportunity_training_dataset(
    dataset: pd.DataFrame,
    *,
    feature_columns: list[str],
    label_columns: list[str],
    created_at: str | None = None,
) -> dict[str, Any]:
    created_at = created_at or now_utc()
    forbidden_feature_columns = [
        column for column in feature_columns if is_forbidden_feature_column(column.replace("feature__", "", 1))
    ]
    future_feature_columns = [
        column
        for column in forbidden_feature_columns
        if column.replace("feature__", "", 1).startswith(
            (
                "future_return_",
                "future_max_return_",
                "future_max_drawdown_",
                "downside_bad_",
                "top_decile_",
            )
        )
    ]
    trade_result_columns = [column for column in feature_columns if contains_any(column, ("trade_result", "trade_profit"))]
    portfolio_columns = [column for column in feature_columns if contains_any(column, ("portfolio", "cash", "annual_return", "final_assets"))]
    backtest_columns = [column for column in feature_columns if "backtest" in column.lower()]
    paper_trading_columns = [column for column in feature_columns if "paper_trading" in column.lower()]
    ai_output_columns = [
        column
        for column in feature_columns
        if contains_any(column, ("opportunity_output", "candidate_evaluation", "expected_edge_score", "buy_rank"))
    ]
    unprefixed_label_columns = [
        column
        for column in dataset.columns
        if str(column).replace("label__", "", 1)
        in {label.replace("label__", "", 1) for label in [TARGET_LABEL, *EVALUATION_LABELS]}
        and not str(column).startswith("label__")
    ]
    split_dates = dataset[["target_date", "split"]].drop_duplicates() if {"target_date", "split"}.issubset(dataset.columns) else pd.DataFrame()
    target_date_split_separated = bool(split_dates.empty or split_dates["target_date"].value_counts().max() == 1)
    feature_label_columns_separated = bool(feature_columns) and bool(label_columns) and not unprefixed_label_columns
    leakage_ok = not (
        forbidden_feature_columns
        or trade_result_columns
        or portfolio_columns
        or backtest_columns
        or paper_trading_columns
        or ai_output_columns
        or unprefixed_label_columns
    ) and feature_label_columns_separated and target_date_split_separated
    split_counts = dataset["split"].value_counts().to_dict() if "split" in dataset.columns else {}
    return {
        "phase": PHASE,
        "created_at": created_at,
        "dataset_row_count": int(len(dataset)),
        "feature_column_count": len(feature_columns),
        "label_column_count": len(label_columns),
        "forbidden_feature_column_count": len(forbidden_feature_columns),
        "forbidden_feature_columns": forbidden_feature_columns,
        "future_feature_column_count": len(future_feature_columns),
        "trade_result_feature_column_count": len(trade_result_columns),
        "portfolio_feature_column_count": len(portfolio_columns),
        "backtest_feature_column_count": len(backtest_columns),
        "paper_trading_feature_column_count": len(paper_trading_columns),
        "ai_output_feature_column_count": len(ai_output_columns),
        "train_rows": int(split_counts.get("train", 0)),
        "validation_rows": int(split_counts.get("validation", 0)),
        "test_rows": int(split_counts.get("test", 0)),
        "model_trained": False,
        "validation_metric_available": False,
        "test_metric_available": False,
        "overfit_warning": False,
        "feature_label_columns_separated": feature_label_columns_separated,
        "target_date_split_separated": target_date_split_separated,
        "unprefixed_label_column_count": len(unprefixed_label_columns),
        "unprefixed_label_columns": unprefixed_label_columns,
        "leakage_audit_status": "OK" if leakage_ok else "ERROR",
        "readiness_status": READY_FOR_PHASE5F_INFERENCE if leakage_ok else BLOCKED_BY_LEAKAGE_AUDIT,
    }


def split_dataset(dataset: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {split: dataset[dataset["split"] == split].copy() for split in REQUIRED_SPLITS}


def fit_preprocessing(dataset: pd.DataFrame, feature_columns: list[str]) -> dict[str, Any]:
    categorical_maps: dict[str, dict[str, int]] = {}
    medians: dict[str, float] = {}
    boolean_columns: list[str] = []
    for column in feature_columns:
        series = dataset[column]
        if pd.api.types.is_bool_dtype(series):
            boolean_columns.append(column)
            medians[column] = 0.0
        elif pd.api.types.is_numeric_dtype(series):
            median = pd.to_numeric(series, errors="coerce").median()
            medians[column] = float(median) if pd.notna(median) else 0.0
        else:
            values = sorted(str(value) for value in series.dropna().unique())
            categorical_maps[column] = {value: index for index, value in enumerate(values)}
            medians[column] = -1.0
    return {"categorical_maps": categorical_maps, "medians": medians, "boolean_columns": boolean_columns}


def transform_features(dataset: pd.DataFrame, feature_columns: list[str], preprocessing: dict[str, Any]) -> np.ndarray:
    matrix = pd.DataFrame(index=dataset.index)
    categorical_maps: dict[str, dict[str, int]] = preprocessing.get("categorical_maps", {})
    medians: dict[str, float] = preprocessing.get("medians", {})
    boolean_columns = set(preprocessing.get("boolean_columns", []))
    for column in feature_columns:
        if column in categorical_maps:
            matrix[column] = dataset[column].map(lambda value: categorical_maps[column].get(str(value), -1) if pd.notna(value) else -1)
        elif column in boolean_columns:
            matrix[column] = dataset[column].fillna(False).astype(float)
        else:
            matrix[column] = pd.to_numeric(dataset[column], errors="coerce").fillna(float(medians.get(column, 0.0)))
    return matrix.to_numpy(dtype=float)


def target_array(dataset: pd.DataFrame) -> np.ndarray:
    return pd.to_numeric(dataset[TARGET_LABEL], errors="coerce").fillna(0.0).to_numpy(dtype=float)


def fit_model(x_train: np.ndarray, y_train: np.ndarray) -> tuple[Any, str, dict[str, Any]]:
    params = {
        "max_iter": 80,
        "learning_rate": 0.05,
        "max_leaf_nodes": 15,
        "l2_regularization": 0.10,
        "random_state": 42,
    }
    model = HistGradientBoostingRegressor(**params)
    model.fit(x_train, y_train)
    return model, "sklearn_hist_gradient_boosting_regressor", params


def fit_simple_rule_baseline(train: pd.DataFrame) -> dict[str, Any]:
    columns = [
        "feature__price_momentum_return_20d",
        "feature__price_momentum_return_60d",
        "feature__trend_close_over_ma_20d",
        "feature__trend_ma_20_60_ratio",
        "feature__liquidity_avg_volume_20d",
        "feature__volatility_return_std_20d",
        "feature__volume_momentum_ratio_1d_20d",
    ]
    weights = {
        "feature__price_momentum_return_20d": 0.30,
        "feature__price_momentum_return_60d": 0.20,
        "feature__trend_close_over_ma_20d": 0.20,
        "feature__trend_ma_20_60_ratio": 0.15,
        "feature__liquidity_avg_volume_20d": 0.10,
        "feature__volatility_return_std_20d": -0.20,
        "feature__volume_momentum_ratio_1d_20d": -0.05,
    }
    stats: dict[str, dict[str, float]] = {}
    usable_columns = [column for column in columns if column in train.columns]
    for column in usable_columns:
        series = pd.to_numeric(train[column], errors="coerce")
        mean = float(series.mean()) if pd.notna(series.mean()) else 0.0
        std = float(series.std()) if pd.notna(series.std()) and series.std() else 1.0
        stats[column] = {"mean": mean, "std": std}
    return {"columns": usable_columns, "weights": weights, "stats": stats}


def add_scores(dataset: pd.DataFrame, *, model_score: np.ndarray, simple_rule_state: dict[str, Any]) -> pd.DataFrame:
    scored = dataset.copy()
    scored["score__model"] = model_score
    scored["score__candidate_score_baseline"] = pd.to_numeric(scored.get("feature__candidate_score", 0.0), errors="coerce").fillna(0.0)
    if "feature__candidate_rank" in scored.columns:
        scored["score__candidate_rank_baseline"] = -pd.to_numeric(scored["feature__candidate_rank"], errors="coerce").fillna(999999.0)
    else:
        scored["score__candidate_rank_baseline"] = scored["score__candidate_score_baseline"]
    scored["score__simple_rule_baseline"] = simple_rule_scores(scored, simple_rule_state)
    return scored


def simple_rule_scores(dataset: pd.DataFrame, state: dict[str, Any]) -> np.ndarray:
    scores = np.zeros(len(dataset), dtype=float)
    for column in state.get("columns", []):
        stats = state["stats"][column]
        values = pd.to_numeric(dataset[column], errors="coerce").fillna(stats["mean"])
        z_values = (values - stats["mean"]) / (stats["std"] or 1.0)
        scores += float(state["weights"].get(column, 0.0)) * z_values.to_numpy(dtype=float)
    return scores


def regression_metric_block(y_true: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    rmse = math.sqrt(mean_squared_error(y_true, scores))
    return {
        "mae": round_float(mean_absolute_error(y_true, scores)),
        "rmse": round_float(rmse),
        "r2": round_float(r2_score(y_true, scores)),
        "spearman_corr": round_float(pd.Series(y_true).corr(pd.Series(scores), method="spearman")),
        "score_mean": round_float(np.mean(scores)),
        "score_std": round_float(np.std(scores)),
    }


def evaluate_rankers(scored: pd.DataFrame) -> dict[str, Any]:
    candidate_average = selected_metric_block(scored)
    ranker_columns = {
        "model": "score__model",
        "candidate_score_baseline": "score__candidate_score_baseline",
        "candidate_rank_baseline": "score__candidate_rank_baseline",
        "simple_rule_baseline": "score__simple_rule_baseline",
    }
    rankers: dict[str, Any] = {}
    for name, score_column in ranker_columns.items():
        topn_blocks: dict[str, Any] = {"candidate_top50_average": candidate_average}
        for top_n in (5, 10, 20):
            selected = select_top_n_by_date(scored, score_column=score_column, top_n=top_n)
            topn_blocks[f"top{top_n}"] = selected_metric_block(selected)
            topn_blocks[f"top{top_n}"]["lift_vs_candidate_top50_future_return"] = round_float(
                topn_blocks[f"top{top_n}"]["selected_mean_future_return"]
                - candidate_average["selected_mean_future_return"]
            )
            topn_blocks[f"top{top_n}"]["lift_vs_candidate_top50_future_max_return"] = round_float(
                topn_blocks[f"top{top_n}"]["selected_mean_future_max_return"]
                - candidate_average["selected_mean_future_max_return"]
            )
        rankers[name] = topn_blocks
    return {
        "target_date_count": int(scored["target_date"].nunique()) if "target_date" in scored.columns else 0,
        "candidate_top50_average": candidate_average,
        "rankers": rankers,
    }


def select_top_n_by_date(scored: pd.DataFrame, *, score_column: str, top_n: int) -> pd.DataFrame:
    return (
        scored.sort_values(["target_date", score_column, "code"], ascending=[True, False, True])
        .groupby("target_date", group_keys=False)
        .head(top_n)
        .copy()
    )


def selected_metric_block(selected: pd.DataFrame) -> dict[str, Any]:
    if selected.empty:
        return {
            "selected_row_count": 0,
            "selected_target_date_count": 0,
            "selected_mean_future_return": 0.0,
            "selected_mean_future_max_return": 0.0,
            "selected_top_decile_rate": 0.0,
            "selected_downside_bad_rate": 0.0,
            "selected_mean_future_max_drawdown": 0.0,
            "win_rate_20d": 0.0,
        }
    future_return = pd.to_numeric(selected["label__future_return_20d"], errors="coerce")
    return {
        "selected_row_count": int(len(selected)),
        "selected_target_date_count": int(selected["target_date"].nunique()) if "target_date" in selected.columns else 0,
        "selected_mean_future_return": round_float(future_return.mean()),
        "selected_mean_future_max_return": round_float(pd.to_numeric(selected["label__future_max_return_20d"], errors="coerce").mean()),
        "selected_top_decile_rate": round_float(selected["label__top_decile_20d"].astype(bool).mean()),
        "selected_downside_bad_rate": round_float(selected["label__downside_bad_20d"].astype(bool).mean()),
        "selected_mean_future_max_drawdown": round_float(pd.to_numeric(selected["label__future_max_drawdown_20d"], errors="coerce").mean()),
        "win_rate_20d": round_float((future_return > 0).mean()),
    }


def calculate_validation_test_gap(regression_metrics: dict[str, Any], ranking_metrics: dict[str, Any]) -> dict[str, Any]:
    validation_top10 = ranking_metrics["validation"]["rankers"]["model"]["top10"]["selected_mean_future_return"]
    test_top10 = ranking_metrics["test"]["rankers"]["model"]["top10"]["selected_mean_future_return"]
    return {
        "rmse_validation_minus_train": round_float(regression_metrics["validation"]["rmse"] - regression_metrics["train"]["rmse"]),
        "rmse_test_minus_validation": round_float(regression_metrics["test"]["rmse"] - regression_metrics["validation"]["rmse"]),
        "model_top10_future_return_test_minus_validation": round_float(test_top10 - validation_top10),
    }


def detect_overfit_warning(regression_metrics: dict[str, Any], ranking_metrics: dict[str, Any], *, train_rows: int) -> bool:
    train_rmse = regression_metrics["train"]["rmse"]
    validation_rmse = regression_metrics["validation"]["rmse"]
    test_rmse = regression_metrics["test"]["rmse"]
    validation_top10 = ranking_metrics["validation"]["rankers"]["model"]["top10"]["selected_mean_future_return"]
    test_top10 = ranking_metrics["test"]["rankers"]["model"]["top10"]["selected_mean_future_return"]
    return bool(
        train_rows < 5000
        or (train_rmse > 0 and validation_rmse > train_rmse * 1.75)
        or (validation_rmse > 0 and test_rmse > validation_rmse * 1.75)
        or abs(validation_top10 - test_top10) > 0.10
    )


def is_forbidden_feature_column(column: str) -> bool:
    normalized = column.strip().lower().replace("-", "_")
    if normalized.startswith(FORBIDDEN_FEATURE_PREFIXES):
        return True
    return contains_any(normalized, FORBIDDEN_FEATURE_TERMS)


def contains_any(value: str, terms: tuple[str, ...]) -> bool:
    normalized = value.lower().replace("-", "_")
    return any(term in normalized for term in terms)


def _blocked_payload(
    readiness_status: str,
    reason: str,
    *,
    dataset_path: Path,
    model_path: Path,
    metrics_path: Path,
    audit_path: Path,
    created_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    audit = {
        "phase": PHASE,
        "created_at": created_at,
        "readiness_status": readiness_status,
        "leakage_audit_status": "NOT_RUN",
        "model_trained": False,
        "validation_metric_available": False,
        "test_metric_available": False,
        "overfit_warning": False,
        "block_reason": reason,
    }
    metrics = _metrics_shell(
        readiness_status=readiness_status,
        dataset_path=dataset_path,
        model_path=model_path,
        metrics_path=metrics_path,
        audit_path=audit_path,
        created_at=created_at,
        audit=audit,
    )
    metrics["status"] = "BLOCKED"
    metrics["training_executed"] = False
    metrics["recommended_next_action"] = reason
    return metrics, audit


def _metrics_shell(
    *,
    readiness_status: str,
    dataset_path: Path,
    model_path: Path,
    metrics_path: Path,
    audit_path: Path,
    created_at: str,
    audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "OK" if readiness_status in {READY_FOR_PHASE5F_INFERENCE, TRAINING_COMPLETE_WITH_WARNINGS} else "BLOCKED",
        "readiness_status": readiness_status,
        "created_at": created_at,
        "dataset_path": str(dataset_path),
        "model_artifact_path": str(model_path),
        "metrics_path": str(metrics_path),
        "audit_path": str(audit_path),
        "target_label": TARGET_LABEL,
        "feature_column_count": int(audit.get("feature_column_count", 0)),
        "label_column_count": int(audit.get("label_column_count", 0)),
        "train_rows": int(audit.get("train_rows", 0)),
        "validation_rows": int(audit.get("validation_rows", 0)),
        "test_rows": int(audit.get("test_rows", 0)),
        "leakage_audit_status": audit.get("leakage_audit_status", "NOT_RUN"),
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return round_float(float(value))
    if isinstance(value, np.ndarray):
        return [to_jsonable(item) for item in value.tolist()]
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def round_float(value: Any, digits: int = 6) -> float:
    if value is None:
        return 0.0
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(numeric) or math.isinf(numeric):
        return 0.0
    return round(numeric, digits)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
