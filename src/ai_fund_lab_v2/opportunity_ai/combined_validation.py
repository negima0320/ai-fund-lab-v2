from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.quality_audit import (
    DEFAULT_DATASET_PATH,
    DEFAULT_LATEST_INFERENCE_AUDIT_PATH,
    DEFAULT_LATEST_INFERENCE_PATH,
    DEFAULT_LATEST_INFERENCE_SUMMARY_PATH,
    DEFAULT_MODEL_PATH,
    audit_latest_inference_schema,
    audit_opportunity_training_dataset,
    build_by_split_table,
    build_model_vs_baseline_comparison,
    build_score_distribution,
    calculate_validation_test_gap,
    load_model_payload,
    read_json,
    score_validation_and_test,
)
from ai_fund_lab_v2.opportunity_ai.training import (
    TARGET_LABEL,
    regression_metric_block,
    select_top_n_by_date,
    selected_metric_block,
    to_jsonable,
)

PHASE = "Phase5-H"
READY_FOR_PHASE5I_FULL_HISTORY_EXPANSION = "READY_FOR_PHASE5I_FULL_HISTORY_EXPANSION"
NEEDS_PHASE5E_OR_LABEL_IMPROVEMENT = "NEEDS_PHASE5E_OR_LABEL_IMPROVEMENT"
BLOCKED_BY_INPUT = "BLOCKED_BY_INPUT"

DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5h")
METRICS_FILENAME = "combined_validation_metrics.json"
AUDIT_FILENAME = "combined_validation_audit.json"
BY_DATE_FILENAME = "combined_validation_by_date.csv"
BY_SPLIT_FILENAME = "combined_validation_by_split.csv"

EVALUATED_SPLITS = ("validation", "test")
TOPN_CONFIG = {"top5": 5, "top10": 10, "top20": 20}


@dataclass(frozen=True)
class CombinedValidationResult:
    metrics: dict[str, Any]
    audit: dict[str, Any]
    by_date: pd.DataFrame
    by_split: pd.DataFrame


def validate_candidate_opportunity_combined(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    model_path: Path = DEFAULT_MODEL_PATH,
    latest_inference_path: Path = DEFAULT_LATEST_INFERENCE_PATH,
    latest_inference_summary_path: Path = DEFAULT_LATEST_INFERENCE_SUMMARY_PATH,
    latest_inference_audit_path: Path = DEFAULT_LATEST_INFERENCE_AUDIT_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    created_at: str | None = None,
) -> CombinedValidationResult:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / METRICS_FILENAME
    audit_path = output_dir / AUDIT_FILENAME
    by_date_path = output_dir / BY_DATE_FILENAME
    by_split_path = output_dir / BY_SPLIT_FILENAME

    missing_inputs = [
        str(path)
        for path in (dataset_path, model_path, latest_inference_path, latest_inference_summary_path, latest_inference_audit_path)
        if not path.is_file()
    ]
    if missing_inputs:
        audit = blocked_audit(created_at=created_at, missing_inputs=missing_inputs)
        metrics = metrics_shell(
            readiness_status=BLOCKED_BY_INPUT,
            status="BLOCKED",
            dataset_path=dataset_path,
            model_path=model_path,
            latest_inference_path=latest_inference_path,
            metrics_path=metrics_path,
            audit_path=audit_path,
            by_date_path=by_date_path,
            by_split_path=by_split_path,
            created_at=created_at,
            audit=audit,
        )
        by_date = pd.DataFrame()
        by_split = pd.DataFrame()
        write_json(metrics_path, metrics)
        write_json(audit_path, audit)
        by_date.to_csv(by_date_path, index=False)
        by_split.to_csv(by_split_path, index=False)
        return CombinedValidationResult(metrics=metrics, audit=audit, by_date=by_date, by_split=by_split)

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
    quality_metrics = {split: evaluate_split_combined(scored) for split, scored in scored_splits.items()}
    regression_metrics = {
        split: regression_metric_block(
            pd.to_numeric(scored[TARGET_LABEL], errors="coerce").fillna(0.0).to_numpy(dtype=float),
            pd.to_numeric(scored["score__model"], errors="coerce").fillna(0.0).to_numpy(dtype=float),
        )
        for split, scored in scored_splits.items()
    }
    by_split = build_by_split_table(quality_metrics)
    by_date = build_by_date_table(scored_splits)
    model_vs_baseline_lift = build_model_vs_baseline_comparison(quality_metrics)
    validation_test_gap = calculate_validation_test_gap(quality_metrics, regression_metrics)
    latest_schema = audit_latest_inference_schema(latest_inference, latest_summary=latest_summary, latest_audit=latest_audit)
    score_distribution = build_score_distribution(scored_splits)
    top10_investigation = investigate_top10_underperformance(by_date, quality_metrics)
    readiness_status = resolve_readiness(
        training_audit=training_audit,
        latest_schema=latest_schema,
        score_distribution=score_distribution,
        quality_metrics=quality_metrics,
        validation_test_gap=validation_test_gap,
        top10_investigation=top10_investigation,
    )
    promotion_ready = False
    audit = {
        "phase": PHASE,
        "created_at": created_at,
        "dataset_rows": int(len(dataset)),
        "target_date_count": int(dataset["target_date"].nunique()),
        "validation_target_date_count": int(dataset.loc[dataset["split"] == "validation", "target_date"].nunique()),
        "test_target_date_count": int(dataset.loc[dataset["split"] == "test", "target_date"].nunique()),
        "validation_rows": int((dataset["split"] == "validation").sum()),
        "test_rows": int((dataset["split"] == "test").sum()),
        "leakage_status": training_audit.get("leakage_audit_status", "ERROR"),
        "forbidden_feature_column_count": int(training_audit.get("forbidden_feature_column_count", 0)),
        "future_feature_column_count": int(training_audit.get("future_feature_column_count", 0)),
        "trade_result_feature_column_count": int(training_audit.get("trade_result_feature_column_count", 0)),
        "portfolio_feature_column_count": int(training_audit.get("portfolio_feature_column_count", 0)),
        "model_score_available": not score_distribution["model_all_same_score"],
        "candidate_top50_baseline_available": bool(quality_metrics["test"]["candidate_top50_average"]),
        "candidate_score_baseline_available": "candidate_score_baseline" in quality_metrics["test"]["rankers"],
        "opportunity_top5_metrics_available": "top5" in quality_metrics["test"]["rankers"]["model"],
        "opportunity_top10_metrics_available": "top10" in quality_metrics["test"]["rankers"]["model"],
        "opportunity_top20_metrics_available": "top20" in quality_metrics["test"]["rankers"]["model"],
        "top10_underperformance_investigated": top10_investigation["investigated"],
        "latest_inference_schema_status": latest_schema["schema_status"],
        "latest_inference_leakage_audit_status": latest_schema["leakage_audit_status"],
        "latest_inference_top5_count": latest_schema["top5_count"],
        "latest_inference_top10_count": latest_schema["top10_count"],
        "latest_inference_top20_count": latest_schema["top20_count"],
        "model_all_same_score": score_distribution["model_all_same_score"],
        "model_unique_score_count": score_distribution["model_unique_score_count"],
        "validation_test_gap_status": validation_test_gap["status"],
        "promotion_ready": promotion_ready,
        "readiness_status": readiness_status,
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
        "by_date_path": str(by_date_path),
        "by_split_path": str(by_split_path),
        "promotion_ready": promotion_ready,
        "dataset_rows": int(len(dataset)),
        "target_date_count": audit["target_date_count"],
        "validation_target_date_count": audit["validation_target_date_count"],
        "test_target_date_count": audit["test_target_date_count"],
        "quality_metrics": quality_metrics,
        "model_vs_baseline_lift": model_vs_baseline_lift,
        "validation_test_gap": validation_test_gap,
        "score_distribution": score_distribution,
        "latest_inference_audit": latest_schema,
        "top10_underperformance_investigation": top10_investigation,
        "training_executed": False,
        "inference_executed": False,
        "combined_validation_executed": True,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "recommended_next_action": (
            "Proceed to Phase5-I Full History Expansion."
            if readiness_status == READY_FOR_PHASE5I_FULL_HISTORY_EXPANSION
            else "Return to Phase5-E model or Phase5-B label improvement before full history expansion."
        ),
    }
    write_json(metrics_path, metrics)
    write_json(audit_path, audit)
    by_date.to_csv(by_date_path, index=False)
    by_split.to_csv(by_split_path, index=False)
    return CombinedValidationResult(metrics=metrics, audit=audit, by_date=by_date, by_split=by_split)


def evaluate_split_combined(scored: pd.DataFrame) -> dict[str, Any]:
    from ai_fund_lab_v2.opportunity_ai.training import evaluate_rankers

    return evaluate_rankers(scored)


def build_by_date_table(scored_splits: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split_name, scored in scored_splits.items():
        for target_date, date_frame in scored.groupby("target_date"):
            candidate_metrics = selected_metric_block(date_frame)
            rows.append(by_date_row(split_name, str(target_date), "candidate_top50", "average", candidate_metrics, candidate_metrics))
            for ranker_name, score_column in (
                ("model", "score__model"),
                ("candidate_score_baseline", "score__candidate_score_baseline"),
            ):
                for selection, top_n in TOPN_CONFIG.items():
                    selected = select_top_n_by_date(date_frame, score_column=score_column, top_n=top_n)
                    metrics = selected_metric_block(selected)
                    rows.append(by_date_row(split_name, str(target_date), ranker_name, selection, metrics, candidate_metrics))
                if ranker_name == "model":
                    tail = select_model_top10_tail(date_frame)
                    rows.append(by_date_row(split_name, str(target_date), "model", "top6_10", selected_metric_block(tail), candidate_metrics))
    return pd.DataFrame(rows)


def by_date_row(
    split_name: str,
    target_date: str,
    ranker: str,
    selection: str,
    metrics: dict[str, Any],
    candidate_metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "split": split_name,
        "target_date": target_date,
        "ranker": ranker,
        "selection": selection,
        "selected_row_count": metrics["selected_row_count"],
        "mean_future_return_20d": metrics["selected_mean_future_return"],
        "mean_future_max_return_20d": metrics["selected_mean_future_max_return"],
        "top_decile_rate_20d": metrics["selected_top_decile_rate"],
        "downside_bad_rate_20d": metrics["selected_downside_bad_rate"],
        "mean_future_max_drawdown_20d": metrics["selected_mean_future_max_drawdown"],
        "win_rate_20d": metrics["win_rate_20d"],
        "candidate_top50_mean_future_return_20d": candidate_metrics["selected_mean_future_return"],
        "lift_vs_candidate_top50_future_return": round_float(
            metrics["selected_mean_future_return"] - candidate_metrics["selected_mean_future_return"]
        ),
        "lift_vs_candidate_top50_future_max_return": round_float(
            metrics["selected_mean_future_max_return"] - candidate_metrics["selected_mean_future_max_return"]
        ),
        "downside_bad_delta_vs_candidate_top50": round_float(
            metrics["selected_downside_bad_rate"] - candidate_metrics["selected_downside_bad_rate"]
        ),
    }


def select_model_top10_tail(date_frame: pd.DataFrame) -> pd.DataFrame:
    top10 = select_top_n_by_date(date_frame, score_column="score__model", top_n=10)
    return top10.sort_values(["target_date", "score__model", "code"], ascending=[True, False, True]).tail(5)


def investigate_top10_underperformance(by_date: pd.DataFrame, quality_metrics: dict[str, Any]) -> dict[str, Any]:
    model_top10 = by_date[(by_date["ranker"] == "model") & (by_date["selection"] == "top10")].copy()
    model_tail = by_date[(by_date["ranker"] == "model") & (by_date["selection"] == "top6_10")].copy()
    candidate_score_top10 = by_date[(by_date["ranker"] == "candidate_score_baseline") & (by_date["selection"] == "top10")].copy()
    under = model_top10[model_top10["lift_vs_candidate_top50_future_return"] < 0].copy()
    test_under = under[under["split"] == "test"].copy()
    tail_under = model_tail[model_tail["lift_vs_candidate_top50_future_return"] < 0].copy()
    down_regime = under[under["candidate_top50_mean_future_return_20d"] <= 0].copy()
    test_model_top10 = quality_metrics["test"]["rankers"]["model"]["top10"]
    test_candidate_score_top10 = quality_metrics["test"]["rankers"]["candidate_score_baseline"]["top10"]
    return {
        "investigated": True,
        "underperforming_target_date_count": int(len(under)),
        "test_underperforming_target_date_count": int(len(test_under)),
        "underperforming_target_dates": under["target_date"].tolist(),
        "test_underperforming_target_dates": test_under["target_date"].tolist(),
        "down_regime_underperforming_date_count": int(len(down_regime)),
        "down_regime_underperforming_target_dates": down_regime["target_date"].tolist(),
        "top6_10_underperforming_date_count": int(len(tail_under)),
        "top6_10_underperforming_target_dates": tail_under["target_date"].tolist(),
        "test_model_top10_mean_future_return": test_model_top10["selected_mean_future_return"],
        "test_candidate_top50_mean_future_return": quality_metrics["test"]["candidate_top50_average"]["selected_mean_future_return"],
        "test_candidate_score_top10_mean_future_return": test_candidate_score_top10["selected_mean_future_return"],
        "model_top10_beats_candidate_score_top10_on_test": bool(
            test_model_top10["selected_mean_future_return"] > test_candidate_score_top10["selected_mean_future_return"]
        ),
        "test_model_top10_downside_bad_rate": test_model_top10["selected_downside_bad_rate"],
        "test_candidate_top50_downside_bad_rate": quality_metrics["test"]["candidate_top50_average"]["selected_downside_bad_rate"],
        "test_candidate_score_top10_downside_bad_rate": test_candidate_score_top10["selected_downside_bad_rate"],
        "downside_bad_increased_vs_candidate_top50": bool(
            test_model_top10["selected_downside_bad_rate"] > quality_metrics["test"]["candidate_top50_average"]["selected_downside_bad_rate"]
        ),
        "likely_causes": infer_top10_causes(under, test_under, tail_under, down_regime, test_model_top10, test_candidate_score_top10),
    }


def infer_top10_causes(
    under: pd.DataFrame,
    test_under: pd.DataFrame,
    tail_under: pd.DataFrame,
    down_regime: pd.DataFrame,
    test_model_top10: dict[str, Any],
    test_candidate_score_top10: dict[str, Any],
) -> list[str]:
    causes: list[str] = []
    if not test_under.empty:
        causes.append("underperformance_is_target_date_specific")
    if len(down_regime) >= max(1, len(under) // 2):
        causes.append("underperformance_concentrated_in_down_regime_proxy_dates")
    if len(tail_under) >= max(1, len(under) // 2):
        causes.append("top6_10_tail_dilutes_top10_quality")
    if test_model_top10["selected_mean_future_return"] > test_candidate_score_top10["selected_mean_future_return"]:
        causes.append("candidate_score_baseline_is_not_the_test_top10_cause")
    if test_model_top10["selected_downside_bad_rate"] > test_candidate_score_top10["selected_downside_bad_rate"]:
        causes.append("model_top10_has_more_downside_bad_than_candidate_score_top10")
    if not causes:
        causes.append("cause_not_isolated_with_current_audit_features")
    return causes


def resolve_readiness(
    *,
    training_audit: dict[str, Any],
    latest_schema: dict[str, Any],
    score_distribution: dict[str, Any],
    quality_metrics: dict[str, Any],
    validation_test_gap: dict[str, Any],
    top10_investigation: dict[str, Any],
) -> str:
    leakage_ok = training_audit.get("leakage_audit_status") == "OK"
    latest_ok = latest_schema["schema_status"] == "OK" and latest_schema["leakage_audit_status"] == "OK"
    top5_lift_confirmed = (
        quality_metrics["validation"]["rankers"]["model"]["top5"]["selected_mean_future_return"]
        > quality_metrics["validation"]["candidate_top50_average"]["selected_mean_future_return"]
        and quality_metrics["test"]["rankers"]["model"]["top5"]["selected_mean_future_return"]
        > quality_metrics["test"]["candidate_top50_average"]["selected_mean_future_return"]
    )
    severe_issue = (
        not leakage_ok
        or not latest_ok
        or score_distribution["model_all_same_score"]
        or validation_test_gap["status"] != "OK"
        or not top5_lift_confirmed
        or not top10_investigation["investigated"]
        or "cause_not_isolated_with_current_audit_features" in top10_investigation["likely_causes"]
    )
    return NEEDS_PHASE5E_OR_LABEL_IMPROVEMENT if severe_issue else READY_FOR_PHASE5I_FULL_HISTORY_EXPANSION


def blocked_audit(*, created_at: str, missing_inputs: list[str]) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "created_at": created_at,
        "dataset_rows": 0,
        "target_date_count": 0,
        "validation_target_date_count": 0,
        "test_target_date_count": 0,
        "leakage_status": "NOT_RUN",
        "forbidden_feature_column_count": 0,
        "future_feature_column_count": 0,
        "trade_result_feature_column_count": 0,
        "portfolio_feature_column_count": 0,
        "model_score_available": False,
        "candidate_top50_baseline_available": False,
        "candidate_score_baseline_available": False,
        "opportunity_top5_metrics_available": False,
        "opportunity_top10_metrics_available": False,
        "opportunity_top20_metrics_available": False,
        "top10_underperformance_investigated": False,
        "promotion_ready": False,
        "readiness_status": BLOCKED_BY_INPUT,
        "missing_inputs": missing_inputs,
    }


def metrics_shell(
    *,
    readiness_status: str,
    status: str,
    dataset_path: Path,
    model_path: Path,
    latest_inference_path: Path,
    metrics_path: Path,
    audit_path: Path,
    by_date_path: Path,
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
        "by_date_path": str(by_date_path),
        "by_split_path": str(by_split_path),
        "promotion_ready": False,
        "dataset_rows": int(audit.get("dataset_rows", 0)),
        "combined_validation_executed": False,
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
