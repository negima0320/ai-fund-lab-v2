from __future__ import annotations

import json
import math
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.opportunity_ai.combined_validation import (
    NEEDS_PHASE5E_OR_LABEL_IMPROVEMENT,
    validate_candidate_opportunity_combined,
)
from ai_fund_lab_v2.opportunity_ai.dataset_builder import build_opportunity_dataset
from ai_fund_lab_v2.opportunity_ai.historical_candidates import build_historical_candidate_top50
from ai_fund_lab_v2.opportunity_ai.quality_audit import audit_opportunity_quality
from ai_fund_lab_v2.opportunity_ai.training import train_opportunity_model, to_jsonable

PHASE = "Phase5-I"
READY_FOR_PHASE5J_MODEL_IMPROVEMENT_OR_CALIBRATION = "READY_FOR_PHASE5J_MODEL_IMPROVEMENT_OR_CALIBRATION"
NEEDS_PHASE5_LABEL_OR_FEATURE_REVIEW = "NEEDS_PHASE5_LABEL_OR_FEATURE_REVIEW"
BLOCKED_BY_INPUT = "BLOCKED_BY_INPUT"

DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5i")
DEFAULT_PHASE4BF_SUMMARY = Path("reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json")
DEFAULT_PHASE4BC_SUMMARY = Path("reports/candidate_ai/full_range/phase4bc_long_history_feature_regeneration_summary.json")
DEFAULT_PHASE4BD_SUMMARY = Path("reports/candidate_ai/full_range/phase4bd_long_history_label_regeneration_summary.json")
DEFAULT_LATEST_INFERENCE_PATH = Path("reports/opportunity_ai/phase5f/latest_opportunity_inference.parquet")
DEFAULT_LATEST_INFERENCE_SUMMARY_PATH = Path("reports/opportunity_ai/phase5f/opportunity_inference_summary.json")
DEFAULT_LATEST_INFERENCE_AUDIT_PATH = Path("reports/opportunity_ai/phase5f/opportunity_inference_audit.json")
DEFAULT_MONTHLY_COMBINED_METRICS_PATH = Path("reports/opportunity_ai/phase5h/combined_validation_metrics.json")

FULL_HISTORY_CANDIDATE_FILENAME = "full_history_candidate_top50.parquet"
FULL_HISTORY_DATASET_FILENAME = "full_history_opportunity_dataset.parquet"
FULL_HISTORY_TRAINING_METRICS_FILENAME = "full_history_training_metrics.json"
FULL_HISTORY_QUALITY_METRICS_FILENAME = "full_history_quality_metrics.json"
FULL_HISTORY_COMBINED_METRICS_FILENAME = "full_history_combined_validation_metrics.json"
FULL_HISTORY_AUDIT_FILENAME = "full_history_audit.json"
FULL_HISTORY_SUMMARY_FILENAME = "full_history_expansion_summary.json"


@dataclass(frozen=True)
class FullHistoryExpansionResult:
    metrics: dict[str, Any]
    audit: dict[str, Any]


def run_full_history_expansion(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    phase4bf_summary_path: Path = DEFAULT_PHASE4BF_SUMMARY,
    phase4bc_summary_path: Path = DEFAULT_PHASE4BC_SUMMARY,
    phase4bd_summary_path: Path = DEFAULT_PHASE4BD_SUMMARY,
    latest_inference_path: Path = DEFAULT_LATEST_INFERENCE_PATH,
    latest_inference_summary_path: Path = DEFAULT_LATEST_INFERENCE_SUMMARY_PATH,
    latest_inference_audit_path: Path = DEFAULT_LATEST_INFERENCE_AUDIT_PATH,
    monthly_combined_metrics_path: Path = DEFAULT_MONTHLY_COMBINED_METRICS_PATH,
    mode: str = "full",
    max_dates: int | None = None,
    created_at: str | None = None,
) -> FullHistoryExpansionResult:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = output_dir / FULL_HISTORY_AUDIT_FILENAME
    summary_path = output_dir / FULL_HISTORY_SUMMARY_FILENAME
    phase4bf = read_json_optional(phase4bf_summary_path)
    phase4bc = read_json_optional(phase4bc_summary_path)
    phase4bd = read_json_optional(phase4bd_summary_path)
    model_path = Path(str(phase4bf.get("model_artifact_path") or ""))
    feature_path = Path(str(phase4bc.get("feature_output_path") or ""))
    label_path = Path(str(phase4bd.get("label_output_path") or ""))
    missing_inputs = [
        str(path)
        for path in (
            phase4bf_summary_path,
            phase4bc_summary_path,
            phase4bd_summary_path,
            model_path,
            feature_path,
            label_path,
            latest_inference_path,
            latest_inference_summary_path,
            latest_inference_audit_path,
        )
        if not path.is_file()
    ]
    if missing_inputs:
        audit = blocked_audit(created_at=created_at, missing_inputs=missing_inputs)
        metrics = build_metrics(
            readiness_status=BLOCKED_BY_INPUT,
            status="BLOCKED",
            created_at=created_at,
            output_dir=output_dir,
            audit=audit,
            monthly_vs_full_history={},
            candidate_summary={},
            dataset_summary={},
            training_metrics={},
            quality_metrics={},
            combined_metrics={},
        )
        write_json(summary_path, metrics)
        write_json(audit_path, audit)
        return FullHistoryExpansionResult(metrics=metrics, audit=audit)

    frequency = "all" if mode == "full" else "monthly"
    candidate_stage_dir = output_dir / "candidate_build"
    dataset_stage_dir = output_dir / "dataset_build"
    model_stage_dir = output_dir / "models"
    training_stage_dir = output_dir / "training"
    quality_stage_dir = output_dir / "quality"
    combined_stage_dir = output_dir / "combined"

    candidate_summary = build_historical_candidate_top50(
        model_path=model_path,
        feature_path=feature_path,
        label_path=label_path,
        output_dir=candidate_stage_dir,
        frequency=frequency,
        top_n=50,
        max_dates=max_dates,
    )
    candidate_path = copy_artifact(Path(candidate_summary["candidate_output_path"]), output_dir / FULL_HISTORY_CANDIDATE_FILENAME)
    dataset_summary = build_opportunity_dataset(
        candidate_path=candidate_path,
        feature_path=feature_path,
        label_path=label_path,
        output_dir=dataset_stage_dir,
    )
    dataset_path = copy_artifact(Path(dataset_summary["dataset_output_path"]), output_dir / FULL_HISTORY_DATASET_FILENAME)
    training_result = train_opportunity_model(
        dataset_path=dataset_path,
        model_dir=model_stage_dir,
        report_dir=training_stage_dir,
        created_at=created_at,
    )
    training_metrics_path = copy_json(
        Path(training_result.metrics["metrics_path"]),
        output_dir / FULL_HISTORY_TRAINING_METRICS_FILENAME,
    )
    full_model_path = Path(training_result.metrics["model_artifact_path"])
    quality_result = audit_opportunity_quality(
        dataset_path=dataset_path,
        model_path=full_model_path,
        latest_inference_path=latest_inference_path,
        latest_inference_summary_path=latest_inference_summary_path,
        latest_inference_audit_path=latest_inference_audit_path,
        output_dir=quality_stage_dir,
        created_at=created_at,
    )
    quality_metrics_path = copy_json(
        Path(quality_result.metrics["metrics_path"]),
        output_dir / FULL_HISTORY_QUALITY_METRICS_FILENAME,
    )
    combined_result = validate_candidate_opportunity_combined(
        dataset_path=dataset_path,
        model_path=full_model_path,
        latest_inference_path=latest_inference_path,
        latest_inference_summary_path=latest_inference_summary_path,
        latest_inference_audit_path=latest_inference_audit_path,
        output_dir=combined_stage_dir,
        created_at=created_at,
    )
    combined_metrics_path = copy_json(
        Path(combined_result.metrics["metrics_path"]),
        output_dir / FULL_HISTORY_COMBINED_METRICS_FILENAME,
    )
    monthly_metrics = read_json_optional(monthly_combined_metrics_path)
    monthly_vs_full_history = compare_monthly_and_full_history(monthly_metrics, combined_result.metrics)
    audit = build_audit(
        created_at=created_at,
        candidate_summary=candidate_summary,
        dataset_summary=dataset_summary,
        training_metrics=training_result.metrics,
        training_audit=training_result.audit,
        quality_metrics=quality_result.metrics,
        quality_audit=quality_result.audit,
        combined_metrics=combined_result.metrics,
        combined_audit=combined_result.audit,
        monthly_vs_full_history=monthly_vs_full_history,
    )
    readiness_status = resolve_readiness(audit)
    audit["readiness_status"] = readiness_status
    metrics = build_metrics(
        readiness_status=readiness_status,
        status="OK",
        created_at=created_at,
        output_dir=output_dir,
        audit=audit,
        monthly_vs_full_history=monthly_vs_full_history,
        candidate_summary=candidate_summary,
        dataset_summary=dataset_summary,
        training_metrics=training_result.metrics,
        quality_metrics=quality_result.metrics,
        combined_metrics=combined_result.metrics,
    )
    metrics["artifact_paths"] = {
        "candidate": str(candidate_path),
        "dataset": str(dataset_path),
        "training_metrics": str(training_metrics_path),
        "quality_metrics": str(quality_metrics_path),
        "combined_validation_metrics": str(combined_metrics_path),
        "audit": str(audit_path),
        "summary": str(summary_path),
        "model": str(full_model_path),
    }
    write_json(summary_path, metrics)
    write_json(audit_path, audit)
    return FullHistoryExpansionResult(metrics=metrics, audit=audit)


def build_audit(
    *,
    created_at: str,
    candidate_summary: dict[str, Any],
    dataset_summary: dict[str, Any],
    training_metrics: dict[str, Any],
    training_audit: dict[str, Any],
    quality_metrics: dict[str, Any],
    quality_audit: dict[str, Any],
    combined_metrics: dict[str, Any],
    combined_audit: dict[str, Any],
    monthly_vs_full_history: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "created_at": created_at,
        "target_date_count": int(candidate_summary.get("target_date_count", 0)),
        "candidate_rows": int(candidate_summary.get("candidate_rows", 0)),
        "dataset_rows": int(dataset_summary.get("joined_row_count", 0)),
        "train_rows": int(dataset_summary.get("train_row_count", 0)),
        "validation_rows": int(dataset_summary.get("validation_row_count", 0)),
        "test_rows": int(dataset_summary.get("test_row_count", 0)),
        "label_join_coverage": float(candidate_summary.get("label_join_coverage_rate", dataset_summary.get("join_success_rate", 0.0))),
        "leakage_status": dataset_summary.get("leakage_audit_status", "ERROR"),
        "forbidden_feature_column_count": int(dataset_summary.get("forbidden_feature_column_count", training_audit.get("forbidden_feature_column_count", 0))),
        "future_feature_column_count": int(training_audit.get("future_feature_column_count", 0)),
        "trade_result_feature_column_count": int(training_audit.get("trade_result_feature_column_count", 0)),
        "portfolio_feature_column_count": int(training_audit.get("portfolio_feature_column_count", 0)),
        "backtest_feature_column_count": int(training_audit.get("backtest_feature_column_count", 0)),
        "model_unique_score_count": int(combined_audit.get("model_unique_score_count", 0)),
        "all_same_score": bool(combined_audit.get("model_all_same_score", True)),
        "top5_lift_status": lift_status(combined_metrics, "top5"),
        "top10_lift_status": lift_status(combined_metrics, "top10"),
        "top20_lift_status": lift_status(combined_metrics, "top20"),
        "validation_test_gap_status": combined_audit.get("validation_test_gap_status", "UNKNOWN"),
        "top10_underperformance_status": top10_status(combined_metrics),
        "top10_underperformance_investigation": combined_metrics.get("top10_underperformance_investigation", {}),
        "monthly_vs_full_history": monthly_vs_full_history,
        "promotion_ready": False,
        "training_readiness_status": training_metrics.get("readiness_status"),
        "quality_readiness_status": quality_metrics.get("readiness_status"),
        "combined_readiness_status": combined_metrics.get("readiness_status"),
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
    }


def resolve_readiness(audit: dict[str, Any]) -> str:
    severe_issue = (
        audit["leakage_status"] != "OK"
        or audit["forbidden_feature_column_count"] > 0
        or audit["future_feature_column_count"] > 0
        or audit["all_same_score"]
        or audit["label_join_coverage"] < 0.95
        or audit["validation_test_gap_status"] != "OK"
        or audit["top5_lift_status"] == "FAILED"
    )
    return NEEDS_PHASE5_LABEL_OR_FEATURE_REVIEW if severe_issue else READY_FOR_PHASE5J_MODEL_IMPROVEMENT_OR_CALIBRATION


def lift_status(metrics: dict[str, Any], topn_key: str) -> str:
    try:
        validation = metrics["quality_metrics"]["validation"]
        test = metrics["quality_metrics"]["test"]
        validation_lift = (
            validation["rankers"]["model"][topn_key]["selected_mean_future_return"]
            - validation["candidate_top50_average"]["selected_mean_future_return"]
        )
        test_lift = (
            test["rankers"]["model"][topn_key]["selected_mean_future_return"]
            - test["candidate_top50_average"]["selected_mean_future_return"]
        )
    except KeyError:
        return "MISSING"
    if validation_lift > 0 and test_lift > 0:
        return "CONFIRMED"
    if validation_lift > 0 or test_lift > 0:
        return "MIXED"
    return "FAILED"


def top10_status(metrics: dict[str, Any]) -> str:
    status = lift_status(metrics, "top10")
    if status == "CONFIRMED":
        return "RESOLVED"
    investigation = metrics.get("top10_underperformance_investigation", {})
    if investigation.get("investigated"):
        return "PERSISTENT_BUT_INVESTIGATED"
    return "UNKNOWN"


def compare_monthly_and_full_history(monthly: dict[str, Any], full: dict[str, Any]) -> dict[str, Any]:
    if not monthly:
        return {"available": False}
    comparison: dict[str, Any] = {"available": True}
    for split in ("validation", "test"):
        comparison[split] = {}
        for topn in ("top5", "top10", "top20"):
            monthly_return = nested_get(monthly, ["quality_metrics", split, "rankers", "model", topn, "selected_mean_future_return"])
            full_return = nested_get(full, ["quality_metrics", split, "rankers", "model", topn, "selected_mean_future_return"])
            comparison[split][topn] = {
                "monthly_mean_future_return": round_float(monthly_return),
                "full_history_mean_future_return": round_float(full_return),
                "delta_full_minus_monthly": round_float(full_return - monthly_return),
            }
    comparison["monthly_readiness_status"] = monthly.get("readiness_status")
    comparison["full_history_readiness_status"] = full.get("readiness_status")
    return comparison


def build_metrics(
    *,
    readiness_status: str,
    status: str,
    created_at: str,
    output_dir: Path,
    audit: dict[str, Any],
    monthly_vs_full_history: dict[str, Any],
    candidate_summary: dict[str, Any],
    dataset_summary: dict[str, Any],
    training_metrics: dict[str, Any],
    quality_metrics: dict[str, Any],
    combined_metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": status,
        "readiness_status": readiness_status,
        "created_at": created_at,
        "output_dir": str(output_dir),
        "promotion_ready": False,
        "target_date_count": audit.get("target_date_count", 0),
        "candidate_rows": audit.get("candidate_rows", 0),
        "dataset_rows": audit.get("dataset_rows", 0),
        "train_rows": audit.get("train_rows", 0),
        "validation_rows": audit.get("validation_rows", 0),
        "test_rows": audit.get("test_rows", 0),
        "label_join_coverage": audit.get("label_join_coverage", 0.0),
        "top5_lift_status": audit.get("top5_lift_status"),
        "top10_lift_status": audit.get("top10_lift_status"),
        "top20_lift_status": audit.get("top20_lift_status"),
        "top10_underperformance_status": audit.get("top10_underperformance_status"),
        "monthly_vs_full_history": monthly_vs_full_history,
        "candidate_summary": compact_summary(candidate_summary),
        "dataset_summary": compact_summary(dataset_summary),
        "training_readiness_status": training_metrics.get("readiness_status"),
        "quality_readiness_status": quality_metrics.get("readiness_status"),
        "combined_readiness_status": combined_metrics.get("readiness_status"),
        "quality_metrics": combined_metrics.get("quality_metrics", {}),
        "top10_underperformance_investigation": combined_metrics.get("top10_underperformance_investigation", {}),
        "training_executed": bool(training_metrics),
        "quality_audit_executed": bool(quality_metrics),
        "combined_validation_executed": bool(combined_metrics),
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "recommended_next_action": (
            "Proceed to Phase5-J model improvement or calibration."
            if readiness_status == READY_FOR_PHASE5J_MODEL_IMPROVEMENT_OR_CALIBRATION
            else "Review Phase5 labels/features before model calibration."
        ),
    }


def blocked_audit(*, created_at: str, missing_inputs: list[str]) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "created_at": created_at,
        "target_date_count": 0,
        "candidate_rows": 0,
        "dataset_rows": 0,
        "train_rows": 0,
        "validation_rows": 0,
        "test_rows": 0,
        "label_join_coverage": 0.0,
        "leakage_status": "NOT_RUN",
        "forbidden_feature_column_count": 0,
        "future_feature_column_count": 0,
        "trade_result_feature_column_count": 0,
        "portfolio_feature_column_count": 0,
        "backtest_feature_column_count": 0,
        "model_unique_score_count": 0,
        "all_same_score": False,
        "top5_lift_status": "MISSING",
        "top10_lift_status": "MISSING",
        "top20_lift_status": "MISSING",
        "validation_test_gap_status": "NOT_RUN",
        "top10_underperformance_status": "UNKNOWN",
        "promotion_ready": False,
        "readiness_status": BLOCKED_BY_INPUT,
        "missing_inputs": missing_inputs,
    }


def copy_artifact(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def copy_json(source: Path, destination: Path) -> Path:
    return copy_artifact(source, destination)


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def nested_get(payload: dict[str, Any], keys: list[str]) -> float:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return 0.0
        current = current[key]
    return float(current)


def compact_summary(payload: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "candidate_rows",
        "joined_row_count",
        "train_row_count",
        "validation_row_count",
        "test_row_count",
        "feature_column_count",
        "label_column_count",
        "leakage_audit_status",
        "label_join_coverage_rate",
    )
    return {key: payload[key] for key in keys if key in payload}


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
