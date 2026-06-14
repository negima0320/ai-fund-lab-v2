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

from ai_fund_lab_v2.opportunity_ai.inference import OUTPUT_COLUMNS
from ai_fund_lab_v2.opportunity_ai.training import (
    DEFAULT_DATASET_PATH,
    DEFAULT_MODEL_DIR,
    MODEL_FILENAME,
    TARGET_LABEL,
    add_scores,
    audit_opportunity_training_dataset,
    evaluate_rankers,
    regression_metric_block,
    to_jsonable,
    transform_features,
)

PHASE = "Phase5-G"
READY_FOR_PHASE5H_COMBINED_VALIDATION = "READY_FOR_PHASE5H_COMBINED_VALIDATION"
NEEDS_PHASE5E_IMPROVEMENT = "NEEDS_PHASE5E_IMPROVEMENT"
BLOCKED_BY_INPUT = "BLOCKED_BY_INPUT"

DEFAULT_MODEL_PATH = DEFAULT_MODEL_DIR / MODEL_FILENAME
DEFAULT_LATEST_INFERENCE_PATH = Path("reports/opportunity_ai/phase5f/latest_opportunity_inference.parquet")
DEFAULT_LATEST_INFERENCE_SUMMARY_PATH = Path("reports/opportunity_ai/phase5f/opportunity_inference_summary.json")
DEFAULT_LATEST_INFERENCE_AUDIT_PATH = Path("reports/opportunity_ai/phase5f/opportunity_inference_audit.json")
DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5g")

METRICS_FILENAME = "opportunity_quality_metrics.json"
AUDIT_FILENAME = "opportunity_quality_audit.json"
BY_SPLIT_FILENAME = "opportunity_quality_by_split.csv"

EVALUATED_SPLITS = ("validation", "test")
TOPN_KEYS = ("top5", "top10", "top20")


@dataclass(frozen=True)
class OpportunityQualityAuditResult:
    metrics: dict[str, Any]
    audit: dict[str, Any]
    by_split: pd.DataFrame


def audit_opportunity_quality(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    model_path: Path = DEFAULT_MODEL_PATH,
    latest_inference_path: Path = DEFAULT_LATEST_INFERENCE_PATH,
    latest_inference_summary_path: Path = DEFAULT_LATEST_INFERENCE_SUMMARY_PATH,
    latest_inference_audit_path: Path = DEFAULT_LATEST_INFERENCE_AUDIT_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    created_at: str | None = None,
) -> OpportunityQualityAuditResult:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / METRICS_FILENAME
    audit_path = output_dir / AUDIT_FILENAME
    by_split_path = output_dir / BY_SPLIT_FILENAME

    missing_inputs = [
        str(path)
        for path in (dataset_path, model_path, latest_inference_path, latest_inference_summary_path, latest_inference_audit_path)
        if not path.is_file()
    ]
    if missing_inputs:
        audit = blocked_audit(created_at=created_at, missing_inputs=missing_inputs)
        metrics = build_metrics_shell(
            readiness_status=BLOCKED_BY_INPUT,
            status="BLOCKED",
            dataset_path=dataset_path,
            model_path=model_path,
            latest_inference_path=latest_inference_path,
            metrics_path=metrics_path,
            audit_path=audit_path,
            by_split_path=by_split_path,
            created_at=created_at,
            audit=audit,
        )
        by_split = pd.DataFrame()
        write_json(metrics_path, metrics)
        write_json(audit_path, audit)
        by_split.to_csv(by_split_path, index=False)
        return OpportunityQualityAuditResult(metrics=metrics, audit=audit, by_split=by_split)

    dataset = pd.read_parquet(dataset_path)
    model_payload = load_model_payload(model_path)
    latest_inference = pd.read_parquet(latest_inference_path)
    latest_summary = read_json(latest_inference_summary_path)
    latest_audit = read_json(latest_inference_audit_path)

    feature_columns = list(model_payload.get("feature_columns") or [])
    label_columns = sorted(column for column in dataset.columns if str(column).startswith("label__"))
    training_audit = audit_opportunity_training_dataset(
        dataset,
        feature_columns=feature_columns,
        label_columns=label_columns,
        created_at=created_at,
    )
    scored_splits = score_validation_and_test(dataset, model_payload, feature_columns)
    quality_metrics = {
        split_name: evaluate_rankers(scored)
        for split_name, scored in scored_splits.items()
    }
    regression_metrics = {
        split_name: regression_metric_block(
            pd.to_numeric(scored[TARGET_LABEL], errors="coerce").fillna(0.0).to_numpy(dtype=float),
            pd.to_numeric(scored["score__model"], errors="coerce").fillna(0.0).to_numpy(dtype=float),
        )
        for split_name, scored in scored_splits.items()
    }
    by_split = build_by_split_table(quality_metrics)
    comparison = build_model_vs_baseline_comparison(quality_metrics)
    validation_test_gap = calculate_validation_test_gap(quality_metrics, regression_metrics)
    latest_schema = audit_latest_inference_schema(latest_inference, latest_summary=latest_summary, latest_audit=latest_audit)
    score_distribution = build_score_distribution(scored_splits)
    warnings = build_quality_warnings(
        training_audit=training_audit,
        latest_schema=latest_schema,
        score_distribution=score_distribution,
        validation_test_gap=validation_test_gap,
        quality_metrics=quality_metrics,
    )
    readiness_status = resolve_readiness(
        training_audit=training_audit,
        latest_schema=latest_schema,
        score_distribution=score_distribution,
        quality_metrics=quality_metrics,
        validation_test_gap=validation_test_gap,
    )
    promotion_ready = False
    audit = {
        "phase": PHASE,
        "created_at": created_at,
        "dataset_rows": int(len(dataset)),
        "validation_rows": int((dataset["split"] == "validation").sum()),
        "test_rows": int((dataset["split"] == "test").sum()),
        "feature_column_count": len(feature_columns),
        "label_column_count": len(label_columns),
        "forbidden_feature_column_count": int(training_audit.get("forbidden_feature_column_count", 0)),
        "future_feature_column_count": int(training_audit.get("future_feature_column_count", 0)),
        "leakage_status": training_audit.get("leakage_audit_status", "ERROR"),
        "latest_inference_schema_status": latest_schema["schema_status"],
        "latest_inference_top5_count": latest_schema["top5_count"],
        "latest_inference_top10_count": latest_schema["top10_count"],
        "latest_inference_top20_count": latest_schema["top20_count"],
        "model_all_same_score": score_distribution["model_all_same_score"],
        "model_unique_score_count": score_distribution["model_unique_score_count"],
        "candidate_baseline_available": "candidate_score_baseline" in quality_metrics["test"]["rankers"],
        "opportunity_topn_metrics_available": bool(not by_split.empty),
        "validation_test_gap_status": validation_test_gap["status"],
        "promotion_ready": promotion_ready,
        "readiness_status": readiness_status,
        "warnings": warnings,
        "latest_inference_leakage_audit_status": latest_schema["leakage_audit_status"],
        "latest_inference_label_table_read_flag": latest_schema["label_table_read_flag"],
        "latest_inference_future_feature_column_count": latest_schema["future_feature_column_count"],
        "latest_inference_forbidden_feature_column_count": latest_schema["forbidden_feature_column_count"],
    }
    metrics = {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": readiness_status,
        "created_at": created_at,
        "dataset_path": str(dataset_path),
        "model_artifact_path": str(model_path),
        "latest_inference_path": str(latest_inference_path),
        "metrics_path": str(metrics_path),
        "audit_path": str(audit_path),
        "by_split_path": str(by_split_path),
        "promotion_ready": promotion_ready,
        "dataset_rows": int(len(dataset)),
        "validation_rows": audit["validation_rows"],
        "test_rows": audit["test_rows"],
        "feature_column_count": len(feature_columns),
        "label_column_count": len(label_columns),
        "quality_metrics": quality_metrics,
        "regression_metrics": regression_metrics,
        "model_vs_baseline_lift": comparison,
        "validation_test_gap": validation_test_gap,
        "score_distribution": score_distribution,
        "latest_inference_audit": latest_schema,
        "warnings": warnings,
        "training_executed": False,
        "inference_executed": False,
        "quality_audit_executed": True,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "recommended_next_action": (
            "Proceed to Phase5-H Candidate + Opportunity Combined Validation."
            if readiness_status == READY_FOR_PHASE5H_COMBINED_VALIDATION
            else "Return to Phase5-E model/feature improvement before combined validation."
        ),
    }
    write_json(metrics_path, metrics)
    write_json(audit_path, audit)
    by_split.to_csv(by_split_path, index=False)
    return OpportunityQualityAuditResult(metrics=metrics, audit=audit, by_split=by_split)


def score_validation_and_test(dataset: pd.DataFrame, model_payload: dict[str, Any], feature_columns: list[str]) -> dict[str, pd.DataFrame]:
    scored: dict[str, pd.DataFrame] = {}
    for split_name in EVALUATED_SPLITS:
        split_frame = dataset[dataset["split"] == split_name].copy()
        for column in feature_columns:
            if column not in split_frame.columns:
                split_frame[column] = np.nan
        matrix = transform_features(split_frame, feature_columns, model_payload.get("preprocessing", {}))
        scores = np.asarray(model_payload["model"].predict(matrix), dtype=float)
        scored[split_name] = add_scores(split_frame, model_score=scores, simple_rule_state=model_payload.get("simple_rule_baseline", {}))
    return scored


def build_by_split_table(quality_metrics: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split_name, split_metrics in quality_metrics.items():
        rows.append(metric_row(split_name, "candidate_top50", "average", split_metrics["candidate_top50_average"]))
        for ranker_name, ranker_metrics in split_metrics["rankers"].items():
            for topn_key in TOPN_KEYS:
                rows.append(metric_row(split_name, ranker_name, topn_key, ranker_metrics[topn_key]))
    return pd.DataFrame(rows)


def metric_row(split_name: str, ranker_name: str, selection: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "split": split_name,
        "ranker": ranker_name,
        "selection": selection,
        "selected_row_count": metrics["selected_row_count"],
        "selected_target_date_count": metrics["selected_target_date_count"],
        "mean_future_return_20d": metrics["selected_mean_future_return"],
        "mean_future_max_return_20d": metrics["selected_mean_future_max_return"],
        "top_decile_rate_20d": metrics["selected_top_decile_rate"],
        "downside_bad_rate_20d": metrics["selected_downside_bad_rate"],
        "mean_future_max_drawdown_20d": metrics["selected_mean_future_max_drawdown"],
        "win_rate_20d": metrics["win_rate_20d"],
        "lift_vs_candidate_top50_future_return": metrics.get("lift_vs_candidate_top50_future_return", 0.0),
        "lift_vs_candidate_top50_future_max_return": metrics.get("lift_vs_candidate_top50_future_max_return", 0.0),
    }


def build_model_vs_baseline_comparison(quality_metrics: dict[str, Any]) -> dict[str, Any]:
    comparison: dict[str, Any] = {}
    for split_name, split_metrics in quality_metrics.items():
        split_block: dict[str, Any] = {}
        for topn_key in TOPN_KEYS:
            model_metrics = split_metrics["rankers"]["model"][topn_key]
            candidate_metrics = split_metrics["rankers"]["candidate_score_baseline"][topn_key]
            split_block[topn_key] = {
                "model_minus_candidate_score_mean_future_return": round_float(
                    model_metrics["selected_mean_future_return"] - candidate_metrics["selected_mean_future_return"]
                ),
                "model_minus_candidate_score_mean_future_max_return": round_float(
                    model_metrics["selected_mean_future_max_return"] - candidate_metrics["selected_mean_future_max_return"]
                ),
                "model_minus_candidate_score_top_decile_rate": round_float(
                    model_metrics["selected_top_decile_rate"] - candidate_metrics["selected_top_decile_rate"]
                ),
                "model_minus_candidate_score_downside_bad_rate": round_float(
                    model_metrics["selected_downside_bad_rate"] - candidate_metrics["selected_downside_bad_rate"]
                ),
                "model_minus_candidate_score_win_rate": round_float(
                    model_metrics["win_rate_20d"] - candidate_metrics["win_rate_20d"]
                ),
            }
        comparison[split_name] = split_block
    return comparison


def calculate_validation_test_gap(quality_metrics: dict[str, Any], regression_metrics: dict[str, Any]) -> dict[str, Any]:
    gap: dict[str, Any] = {
        "rmse_test_minus_validation": round_float(regression_metrics["test"]["rmse"] - regression_metrics["validation"]["rmse"]),
    }
    severe = False
    for topn_key in TOPN_KEYS:
        validation_return = quality_metrics["validation"]["rankers"]["model"][topn_key]["selected_mean_future_return"]
        test_return = quality_metrics["test"]["rankers"]["model"][topn_key]["selected_mean_future_return"]
        delta = round_float(test_return - validation_return)
        gap[f"model_{topn_key}_future_return_test_minus_validation"] = delta
        if abs(delta) > 0.10:
            severe = True
    gap["status"] = "WARNING" if severe else "OK"
    return gap


def audit_latest_inference_schema(
    latest_inference: pd.DataFrame,
    *,
    latest_summary: dict[str, Any],
    latest_audit: dict[str, Any],
) -> dict[str, Any]:
    required_columns = list(OUTPUT_COLUMNS)
    missing_columns = [column for column in required_columns if column not in latest_inference.columns]
    top5_count = int(latest_inference["is_top5"].sum()) if "is_top5" in latest_inference.columns else 0
    top10_count = int(latest_inference["is_top10"].sum()) if "is_top10" in latest_inference.columns else 0
    top20_count = int(latest_inference["is_top20"].sum()) if "is_top20" in latest_inference.columns else 0
    schema_ok = not missing_columns and top5_count == 5 and top10_count == 10 and top20_count == 20
    leakage_ok = latest_audit.get("leakage_audit_status") == "OK" and latest_summary.get("label_table_read_flag") is False
    return {
        "schema_status": "OK" if schema_ok else "ERROR",
        "missing_columns": missing_columns,
        "row_count": int(len(latest_inference)),
        "top5_count": top5_count,
        "top10_count": top10_count,
        "top20_count": top20_count,
        "all_same_score": bool(latest_inference["expected_edge_score"].nunique(dropna=False) <= 1) if "expected_edge_score" in latest_inference.columns else True,
        "unique_score_count": int(latest_inference["expected_edge_score"].nunique(dropna=False)) if "expected_edge_score" in latest_inference.columns else 0,
        "leakage_audit_status": "OK" if leakage_ok else "ERROR",
        "label_table_read_flag": bool(latest_summary.get("label_table_read_flag", True)),
        "future_feature_column_count": int(latest_audit.get("future_feature_column_count", -1)),
        "forbidden_feature_column_count": int(latest_audit.get("forbidden_feature_column_count", -1)),
        "trade_result_feature_column_count": int(latest_audit.get("trade_result_feature_column_count", -1)),
        "portfolio_feature_column_count": int(latest_audit.get("portfolio_feature_column_count", -1)),
        "backtest_feature_column_count": int(latest_audit.get("backtest_feature_column_count", -1)),
        "ai_output_leakage_column_count": int(latest_audit.get("ai_output_leakage_column_count", -1)),
    }


def build_score_distribution(scored_splits: dict[str, pd.DataFrame]) -> dict[str, Any]:
    all_scores = pd.concat([frame["score__model"] for frame in scored_splits.values()], ignore_index=True)
    split_stats = {}
    for split_name, frame in scored_splits.items():
        scores = pd.to_numeric(frame["score__model"], errors="coerce")
        split_stats[split_name] = {
            "row_count": int(len(scores)),
            "unique_score_count": int(scores.nunique(dropna=False)),
            "all_same_score": bool(scores.nunique(dropna=False) <= 1),
            "score_min": round_float(scores.min()),
            "score_max": round_float(scores.max()),
            "score_mean": round_float(scores.mean()),
            "score_std": round_float(scores.std()),
        }
    return {
        "model_unique_score_count": int(all_scores.nunique(dropna=False)),
        "model_all_same_score": bool(all_scores.nunique(dropna=False) <= 1),
        "by_split": split_stats,
    }


def build_quality_warnings(
    *,
    training_audit: dict[str, Any],
    latest_schema: dict[str, Any],
    score_distribution: dict[str, Any],
    validation_test_gap: dict[str, Any],
    quality_metrics: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if training_audit.get("leakage_audit_status") != "OK":
        warnings.append("training_dataset_leakage_audit_failed")
    if latest_schema["schema_status"] != "OK":
        warnings.append("latest_inference_schema_failed")
    if latest_schema["leakage_audit_status"] != "OK":
        warnings.append("latest_inference_leakage_audit_failed")
    if score_distribution["model_all_same_score"]:
        warnings.append("model_score_collapse")
    if validation_test_gap["status"] != "OK":
        warnings.append("validation_test_instability")
    for split_name, split_metrics in quality_metrics.items():
        model_top10 = split_metrics["rankers"]["model"]["top10"]["selected_mean_future_return"]
        candidate_top50 = split_metrics["candidate_top50_average"]["selected_mean_future_return"]
        if model_top10 < candidate_top50:
            warnings.append(f"{split_name}_model_top10_under_candidate_top50")
    return warnings


def resolve_readiness(
    *,
    training_audit: dict[str, Any],
    latest_schema: dict[str, Any],
    score_distribution: dict[str, Any],
    quality_metrics: dict[str, Any],
    validation_test_gap: dict[str, Any],
) -> str:
    metrics_available = all(
        split in quality_metrics and "model" in quality_metrics[split]["rankers"]
        for split in EVALUATED_SPLITS
    )
    severe_issue = (
        training_audit.get("leakage_audit_status") != "OK"
        or latest_schema["schema_status"] != "OK"
        or latest_schema["leakage_audit_status"] != "OK"
        or score_distribution["model_all_same_score"]
        or not metrics_available
        or validation_test_gap["status"] != "OK"
    )
    return NEEDS_PHASE5E_IMPROVEMENT if severe_issue else READY_FOR_PHASE5H_COMBINED_VALIDATION


def load_model_payload(model_path: Path) -> dict[str, Any]:
    with model_path.open("rb") as handle:
        payload = pickle.load(handle)
    if not isinstance(payload, dict) or "model" not in payload:
        raise ValueError("Phase5-E model artifact payload is invalid")
    return payload


def blocked_audit(*, created_at: str, missing_inputs: list[str]) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "created_at": created_at,
        "dataset_rows": 0,
        "validation_rows": 0,
        "test_rows": 0,
        "feature_column_count": 0,
        "label_column_count": 0,
        "forbidden_feature_column_count": 0,
        "future_feature_column_count": 0,
        "leakage_status": "NOT_RUN",
        "latest_inference_schema_status": "NOT_RUN",
        "latest_inference_top5_count": 0,
        "latest_inference_top10_count": 0,
        "latest_inference_top20_count": 0,
        "model_all_same_score": False,
        "model_unique_score_count": 0,
        "candidate_baseline_available": False,
        "opportunity_topn_metrics_available": False,
        "validation_test_gap_status": "NOT_RUN",
        "promotion_ready": False,
        "readiness_status": BLOCKED_BY_INPUT,
        "missing_inputs": missing_inputs,
    }


def build_metrics_shell(
    *,
    readiness_status: str,
    status: str,
    dataset_path: Path,
    model_path: Path,
    latest_inference_path: Path,
    metrics_path: Path,
    audit_path: Path,
    by_split_path: Path,
    created_at: str,
    audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": status,
        "readiness_status": readiness_status,
        "created_at": created_at,
        "dataset_path": str(dataset_path),
        "model_artifact_path": str(model_path),
        "latest_inference_path": str(latest_inference_path),
        "metrics_path": str(metrics_path),
        "audit_path": str(audit_path),
        "by_split_path": str(by_split_path),
        "promotion_ready": False,
        "dataset_rows": int(audit.get("dataset_rows", 0)),
        "validation_rows": int(audit.get("validation_rows", 0)),
        "test_rows": int(audit.get("test_rows", 0)),
        "quality_audit_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def round_float(value: Any, digits: int = 6) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(numeric) or math.isinf(numeric):
        return 0.0
    return round(numeric, digits)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
