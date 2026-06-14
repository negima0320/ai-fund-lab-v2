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

from ai_fund_lab_v2.opportunity_ai.dataset_builder import FEATURE_META_COLUMNS, read_table, select_jquants_feature_columns
from ai_fund_lab_v2.opportunity_ai.training import (
    DEFAULT_MODEL_DIR,
    MODEL_FILENAME,
    TRAINING_COMPLETE_WITH_WARNINGS,
    contains_any,
    is_forbidden_feature_column,
    to_jsonable,
    transform_features,
)

PHASE = "Phase5-F"
READY_FOR_PHASE5G_QUALITY_AUDIT = "READY_FOR_PHASE5G_QUALITY_AUDIT"
BLOCKED_BY_INPUT = "BLOCKED_BY_INPUT"
BLOCKED_BY_MODEL_ARTIFACT = "BLOCKED_BY_MODEL_ARTIFACT"
BLOCKED_BY_JOIN_COVERAGE = "BLOCKED_BY_JOIN_COVERAGE"
BLOCKED_BY_LEAKAGE_AUDIT = "BLOCKED_BY_LEAKAGE_AUDIT"
BLOCKED_BY_INFERENCE = "BLOCKED_BY_INFERENCE"

DEFAULT_CANDIDATE_PATH = Path("reports/candidate_ai/full_range/phase4bg_formal_candidate_inference_top50.json")
DEFAULT_FEATURE_PATH = Path(".runtime/candidate_ai/features/phase4bc_long_history_features_2021-06-14_2026-06-12.parquet")
DEFAULT_MODEL_PATH = DEFAULT_MODEL_DIR / MODEL_FILENAME
DEFAULT_TRAINING_METRICS_PATH = Path("reports/opportunity_ai/phase5e/opportunity_training_metrics.json")
DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5f")

INFERENCE_FILENAME = "latest_opportunity_inference.parquet"
TOP20_FILENAME = "latest_opportunity_top20.csv"
SUMMARY_FILENAME = "opportunity_inference_summary.json"
AUDIT_FILENAME = "opportunity_inference_audit.json"

OUTPUT_COLUMNS = (
    "target_date",
    "code",
    "expected_edge_score",
    "buy_rank",
    "expected_return_horizon",
    "downside_risk_score",
    "buy_reason",
    "no_buy_reason",
    "candidate_score",
    "candidate_rank",
    "model_version",
    "feature_version",
    "inference_run_id",
    "created_at",
    "is_top5",
    "is_top10",
    "is_top20",
)


@dataclass(frozen=True)
class OpportunityInferenceResult:
    output: pd.DataFrame
    summary: dict[str, Any]
    audit: dict[str, Any]


def run_opportunity_inference(
    *,
    candidate_path: Path = DEFAULT_CANDIDATE_PATH,
    feature_path: Path = DEFAULT_FEATURE_PATH,
    model_path: Path = DEFAULT_MODEL_PATH,
    training_metrics_path: Path = DEFAULT_TRAINING_METRICS_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    created_at: str | None = None,
    inference_run_id: str | None = None,
) -> OpportunityInferenceResult:
    created_at = created_at or now_utc()
    inference_run_id = inference_run_id or f"phase5f_{created_at.replace(':', '').replace('+', 'Z')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / INFERENCE_FILENAME
    top20_path = output_dir / TOP20_FILENAME
    summary_path = output_dir / SUMMARY_FILENAME
    audit_path = output_dir / AUDIT_FILENAME

    if not candidate_path.is_file():
        return _blocked_result(
            BLOCKED_BY_INPUT,
            "latest Candidate Top50 artifact is missing.",
            candidate_path=candidate_path,
            feature_path=feature_path,
            model_path=model_path,
            output_path=output_path,
            top20_path=top20_path,
            summary_path=summary_path,
            audit_path=audit_path,
            created_at=created_at,
        )
    if not feature_path.is_file():
        return _blocked_result(
            BLOCKED_BY_INPUT,
            "inference feature artifact is missing.",
            candidate_path=candidate_path,
            feature_path=feature_path,
            model_path=model_path,
            output_path=output_path,
            top20_path=top20_path,
            summary_path=summary_path,
            audit_path=audit_path,
            created_at=created_at,
        )
    if not model_path.is_file():
        return _blocked_result(
            BLOCKED_BY_MODEL_ARTIFACT,
            "Phase5-E model artifact is missing.",
            candidate_path=candidate_path,
            feature_path=feature_path,
            model_path=model_path,
            output_path=output_path,
            top20_path=top20_path,
            summary_path=summary_path,
            audit_path=audit_path,
            created_at=created_at,
        )

    model_payload = load_model_payload(model_path)
    candidate = normalize_candidate_frame(read_table(candidate_path))
    target_dates = sorted(candidate["target_date"].dropna().astype(str).unique().tolist())
    feature = read_feature_frame_for_dates(feature_path, target_dates)
    inference_frame = build_inference_feature_frame(candidate_frame=candidate, feature_frame=feature)
    feature_columns = list(model_payload.get("feature_columns") or [])
    inference_frame = ensure_model_feature_columns(inference_frame, feature_columns)

    audit = audit_opportunity_inference_frame(
        inference_frame,
        feature_columns=feature_columns,
        input_candidate_count=len(candidate),
        label_table_read_flag=False,
        created_at=created_at,
    )
    if audit["leakage_audit_status"] != "OK":
        summary = build_summary(
            readiness_status=BLOCKED_BY_LEAKAGE_AUDIT,
            status="BLOCKED",
            candidate_path=candidate_path,
            feature_path=feature_path,
            model_path=model_path,
            output_path=output_path,
            top20_path=top20_path,
            summary_path=summary_path,
            audit_path=audit_path,
            created_at=created_at,
            model_payload=model_payload,
            training_metrics_path=training_metrics_path,
            audit=audit,
            output_count=0,
        )
        write_json(summary_path, summary)
        write_json(audit_path, audit)
        return OpportunityInferenceResult(output=pd.DataFrame(columns=OUTPUT_COLUMNS), summary=summary, audit=audit)
    if inference_frame.empty:
        audit = {**audit, "readiness_status": BLOCKED_BY_JOIN_COVERAGE}
        summary = build_summary(
            readiness_status=BLOCKED_BY_JOIN_COVERAGE,
            status="BLOCKED",
            candidate_path=candidate_path,
            feature_path=feature_path,
            model_path=model_path,
            output_path=output_path,
            top20_path=top20_path,
            summary_path=summary_path,
            audit_path=audit_path,
            created_at=created_at,
            model_payload=model_payload,
            training_metrics_path=training_metrics_path,
            audit=audit,
            output_count=0,
        )
        write_json(summary_path, summary)
        write_json(audit_path, audit)
        return OpportunityInferenceResult(output=pd.DataFrame(columns=OUTPUT_COLUMNS), summary=summary, audit=audit)

    try:
        matrix = transform_features(inference_frame, feature_columns, model_payload.get("preprocessing", {}))
        scores = model_payload["model"].predict(matrix)
    except Exception as exc:  # pragma: no cover - defensive blocker
        audit = {**audit, "readiness_status": BLOCKED_BY_INFERENCE, "inference_error": f"{type(exc).__name__}: {exc}"}
        summary = build_summary(
            readiness_status=BLOCKED_BY_INFERENCE,
            status="BLOCKED",
            candidate_path=candidate_path,
            feature_path=feature_path,
            model_path=model_path,
            output_path=output_path,
            top20_path=top20_path,
            summary_path=summary_path,
            audit_path=audit_path,
            created_at=created_at,
            model_payload=model_payload,
            training_metrics_path=training_metrics_path,
            audit=audit,
            output_count=0,
        )
        write_json(summary_path, summary)
        write_json(audit_path, audit)
        return OpportunityInferenceResult(output=pd.DataFrame(columns=OUTPUT_COLUMNS), summary=summary, audit=audit)

    output = build_inference_output(
        inference_frame,
        scores=np.asarray(scores, dtype=float),
        model_version=str(model_payload.get("model_version") or "opportunity_model_unknown"),
        created_at=created_at,
        inference_run_id=inference_run_id,
    )
    audit = {
        **audit,
        "output_count": int(len(output)),
        "all_same_score": bool(output["expected_edge_score"].nunique(dropna=False) <= 1),
        "unique_score_count": int(output["expected_edge_score"].nunique(dropna=False)),
        "top5_count": int(output["is_top5"].sum()),
        "top10_count": int(output["is_top10"].sum()),
        "top20_count": int(output["is_top20"].sum()),
        "readiness_status": READY_FOR_PHASE5G_QUALITY_AUDIT,
    }
    output.to_parquet(output_path, index=False, engine="pyarrow")
    output[output["is_top20"]].to_csv(top20_path, index=False)
    summary = build_summary(
        readiness_status=READY_FOR_PHASE5G_QUALITY_AUDIT,
        status="OK",
        candidate_path=candidate_path,
        feature_path=feature_path,
        model_path=model_path,
        output_path=output_path,
        top20_path=top20_path,
        summary_path=summary_path,
        audit_path=audit_path,
        created_at=created_at,
        model_payload=model_payload,
        training_metrics_path=training_metrics_path,
        audit=audit,
        output_count=len(output),
    )
    write_json(summary_path, summary)
    write_json(audit_path, audit)
    return OpportunityInferenceResult(output=output, summary=summary, audit=audit)


def load_model_payload(model_path: Path) -> dict[str, Any]:
    with model_path.open("rb") as handle:
        payload = pickle.load(handle)
    if not isinstance(payload, dict) or "model" not in payload:
        raise ValueError("Phase5-E model artifact payload is invalid")
    return payload


def normalize_candidate_frame(candidate: pd.DataFrame) -> pd.DataFrame:
    candidate = candidate.copy()
    if "target_date" not in candidate.columns or "code" not in candidate.columns:
        raise ValueError("candidate artifact must contain target_date and code")
    candidate["target_date"] = candidate["target_date"].astype(str)
    candidate["code"] = candidate["code"].astype(str)
    return candidate.drop_duplicates(["target_date", "code"], keep="first")


def read_feature_frame_for_dates(feature_path: Path, target_dates: list[str]) -> pd.DataFrame:
    if feature_path.suffix == ".parquet" and target_dates:
        try:
            return pd.read_parquet(feature_path, filters=[("target_date", "in", target_dates)])
        except Exception:
            pass
    feature = read_table(feature_path)
    if "target_date" not in feature.columns:
        raise ValueError("feature artifact must contain target_date")
    return feature[feature["target_date"].astype(str).isin(target_dates)].copy()


def build_inference_feature_frame(*, candidate_frame: pd.DataFrame, feature_frame: pd.DataFrame) -> pd.DataFrame:
    candidate = normalize_candidate_frame(candidate_frame)
    feature = feature_frame.copy()
    feature["target_date"] = feature["target_date"].astype(str)
    feature["code"] = feature["code"].astype(str)
    feature = feature.drop_duplicates(["target_date", "code"], keep="first")

    candidate_feature_columns = [column for column in ("candidate_score", "candidate_rank", "candidate_reason") if column in candidate.columns]
    candidate_meta_columns = [
        column
        for column in ("target_date", "code", "model_version", "feature_snapshot_id", "candidate_inference_run_id", "inference_run_id")
        if column in candidate.columns
    ]
    candidate_part = candidate[candidate_meta_columns + candidate_feature_columns].rename(
        columns={column: f"feature__{column}" for column in candidate_feature_columns}
    )
    jq_feature_columns = select_jquants_feature_columns(feature)
    feature_part = feature[["target_date", "code"] + optional_columns(feature, ("as_of_date", "feature_version")) + jq_feature_columns].rename(
        columns={column: f"feature__{column}" for column in jq_feature_columns}
    )
    merged = candidate_part.merge(feature_part, on=["target_date", "code"], how="inner", validate="one_to_one")
    if "as_of_date" not in merged.columns:
        merged["as_of_date"] = merged["target_date"]
    if "feature_version" not in merged.columns:
        merged["feature_version"] = "opportunity_feature_v1"
    return merged


def ensure_model_feature_columns(frame: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    frame = frame.copy()
    for column in feature_columns:
        if column not in frame.columns:
            frame[column] = np.nan
    return frame


def build_inference_output(
    frame: pd.DataFrame,
    *,
    scores: np.ndarray,
    model_version: str,
    created_at: str,
    inference_run_id: str,
) -> pd.DataFrame:
    output = pd.DataFrame(
        {
            "target_date": frame["target_date"].astype(str),
            "code": frame["code"].astype(str),
            "expected_edge_score": [round_float(score) for score in scores],
            "expected_return_horizon": "20d",
            "downside_risk_score": calculate_downside_risk_score(frame),
            "candidate_score": pd.to_numeric(frame.get("feature__candidate_score", 0.0), errors="coerce").fillna(0.0),
            "candidate_rank": pd.to_numeric(frame.get("feature__candidate_rank", 0), errors="coerce").fillna(0).astype(int),
            "model_version": model_version,
            "feature_version": frame.get("feature_version", "opportunity_feature_v1"),
            "inference_run_id": inference_run_id,
            "created_at": created_at,
        }
    )
    output = output.sort_values(["target_date", "expected_edge_score", "code"], ascending=[True, False, True]).copy()
    output["buy_rank"] = output.groupby("target_date")["expected_edge_score"].rank(method="first", ascending=False).astype(int)
    output["is_top5"] = output["buy_rank"] <= 5
    output["is_top10"] = output["buy_rank"] <= 10
    output["is_top20"] = output["buy_rank"] <= 20
    output["buy_reason"] = output.apply(build_buy_reason, axis=1)
    output["no_buy_reason"] = output.apply(build_no_buy_reason, axis=1)
    return output[list(OUTPUT_COLUMNS)]


def calculate_downside_risk_score(frame: pd.DataFrame) -> pd.Series:
    volatility = pd.to_numeric(frame.get("feature__volatility_return_std_20d", 0.0), errors="coerce").fillna(0.0)
    return_20d = pd.to_numeric(frame.get("feature__price_momentum_return_20d", 0.0), errors="coerce").fillna(0.0)
    trend = pd.to_numeric(frame.get("feature__trend_close_over_ma_20d", 0.0), errors="coerce").fillna(0.0)
    volume_ratio = pd.to_numeric(frame.get("feature__volume_momentum_ratio_1d_20d", 1.0), errors="coerce").fillna(1.0)
    score = (
        0.45 * (volatility / 0.08).clip(lower=0.0, upper=1.0)
        + 0.25 * ((-return_20d) / 0.20).clip(lower=0.0, upper=1.0)
        + 0.20 * ((-trend) / 0.20).clip(lower=0.0, upper=1.0)
        + 0.10 * ((volume_ratio - 3.0) / 3.0).clip(lower=0.0, upper=1.0)
    )
    return score.map(round_float)


def build_buy_reason(row: pd.Series) -> str:
    reasons: list[str] = []
    if bool(row["is_top5"]):
        reasons.append("opportunity_top5")
    elif bool(row["is_top10"]):
        reasons.append("opportunity_top10")
    elif bool(row["is_top20"]):
        reasons.append("opportunity_top20")
    if float(row["expected_edge_score"]) > 0:
        reasons.append("positive_expected_edge")
    if float(row["candidate_score"]) > 0:
        reasons.append("candidate_prior_available")
    if float(row["downside_risk_score"]) < 0.50:
        reasons.append("downside_risk_not_extreme")
    return "|".join(reasons) or "ranked_by_expected_edge"


def build_no_buy_reason(row: pd.Series) -> str:
    reasons: list[str] = []
    if not bool(row["is_top20"]):
        reasons.append("below_opportunity_top20")
    if float(row["downside_risk_score"]) >= 0.70:
        reasons.append("high_downside_risk_score")
    if float(row["expected_edge_score"]) <= 0:
        reasons.append("non_positive_expected_edge_score")
    return "|".join(reasons)


def audit_opportunity_inference_frame(
    frame: pd.DataFrame,
    *,
    feature_columns: list[str],
    input_candidate_count: int,
    label_table_read_flag: bool,
    created_at: str | None = None,
) -> dict[str, Any]:
    created_at = created_at or now_utc()
    actual_feature_columns = [column for column in frame.columns if str(column).startswith("feature__")]
    forbidden_feature_columns = [
        column for column in feature_columns if is_forbidden_feature_column(column.replace("feature__", "", 1))
    ] + [
        column for column in actual_feature_columns if is_forbidden_feature_column(column.replace("feature__", "", 1))
    ]
    forbidden_feature_columns = sorted(set(forbidden_feature_columns))
    future_feature_columns = [
        column
        for column in forbidden_feature_columns
        if column.replace("feature__", "", 1).startswith(
            ("future_return_", "future_max_return_", "future_max_drawdown_", "downside_bad_", "top_decile_")
        )
    ]
    trade_result_columns = [column for column in actual_feature_columns if contains_any(column, ("trade_result", "trade_profit"))]
    portfolio_columns = [column for column in actual_feature_columns if contains_any(column, ("portfolio", "cash", "annual_return", "final_assets"))]
    backtest_columns = [column for column in actual_feature_columns if "backtest" in column.lower()]
    ai_output_columns = [
        column
        for column in actual_feature_columns
        if contains_any(column, ("opportunity_output", "candidate_evaluation", "expected_edge_score", "buy_rank"))
    ]
    label_columns = [column for column in frame.columns if str(column).startswith("label__")]
    as_of_violations = count_as_of_date_violations(frame)
    leakage_ok = not (
        forbidden_feature_columns
        or future_feature_columns
        or trade_result_columns
        or portfolio_columns
        or backtest_columns
        or ai_output_columns
        or label_columns
        or label_table_read_flag
        or as_of_violations
    )
    return {
        "phase": PHASE,
        "created_at": created_at,
        "input_candidate_count": int(input_candidate_count),
        "output_count": int(len(frame)),
        "feature_column_count": len(feature_columns),
        "actual_feature_column_count": len(actual_feature_columns),
        "missing_model_feature_count": len([column for column in feature_columns if column not in frame.columns]),
        "forbidden_feature_column_count": len(forbidden_feature_columns),
        "forbidden_feature_columns": forbidden_feature_columns,
        "future_feature_column_count": len(future_feature_columns),
        "label_table_read_flag": bool(label_table_read_flag),
        "label_column_count": len(label_columns),
        "trade_result_feature_column_count": len(trade_result_columns),
        "portfolio_feature_column_count": len(portfolio_columns),
        "backtest_feature_column_count": len(backtest_columns),
        "ai_output_leakage_column_count": len(ai_output_columns),
        "as_of_date_violation_count": as_of_violations,
        "all_same_score": False,
        "unique_score_count": 0,
        "top5_count": 0,
        "top10_count": 0,
        "top20_count": 0,
        "leakage_audit_status": "OK" if leakage_ok else "ERROR",
        "readiness_status": READY_FOR_PHASE5G_QUALITY_AUDIT if leakage_ok else BLOCKED_BY_LEAKAGE_AUDIT,
    }


def build_summary(
    *,
    readiness_status: str,
    status: str,
    candidate_path: Path,
    feature_path: Path,
    model_path: Path,
    output_path: Path,
    top20_path: Path,
    summary_path: Path,
    audit_path: Path,
    created_at: str,
    model_payload: dict[str, Any],
    training_metrics_path: Path,
    audit: dict[str, Any],
    output_count: int,
) -> dict[str, Any]:
    training_metrics = read_json_optional(training_metrics_path)
    training_readiness_status = str(training_metrics.get("readiness_status") or "")
    return {
        "phase": PHASE,
        "status": status,
        "readiness_status": readiness_status,
        "created_at": created_at,
        "candidate_path": str(candidate_path),
        "feature_path": str(feature_path),
        "model_artifact_path": str(model_path),
        "training_metrics_path": str(training_metrics_path),
        "output_path": str(output_path),
        "top20_path": str(top20_path),
        "summary_path": str(summary_path),
        "audit_path": str(audit_path),
        "model_version": str(model_payload.get("model_version") or ""),
        "training_readiness_status": training_readiness_status,
        "training_warning_acknowledged": training_readiness_status == TRAINING_COMPLETE_WITH_WARNINGS,
        "promotion_ready": False,
        "input_candidate_count": int(audit.get("input_candidate_count", 0)),
        "output_count": int(output_count),
        "feature_column_count": int(audit.get("feature_column_count", 0)),
        "forbidden_feature_column_count": int(audit.get("forbidden_feature_column_count", 0)),
        "future_feature_column_count": int(audit.get("future_feature_column_count", 0)),
        "label_table_read_flag": bool(audit.get("label_table_read_flag", False)),
        "trade_result_feature_column_count": int(audit.get("trade_result_feature_column_count", 0)),
        "portfolio_feature_column_count": int(audit.get("portfolio_feature_column_count", 0)),
        "backtest_feature_column_count": int(audit.get("backtest_feature_column_count", 0)),
        "ai_output_leakage_column_count": int(audit.get("ai_output_leakage_column_count", 0)),
        "all_same_score": bool(audit.get("all_same_score", False)),
        "unique_score_count": int(audit.get("unique_score_count", 0)),
        "top5_count": int(audit.get("top5_count", 0)),
        "top10_count": int(audit.get("top10_count", 0)),
        "top20_count": int(audit.get("top20_count", 0)),
        "leakage_audit_status": audit.get("leakage_audit_status", "NOT_RUN"),
        "training_executed": False,
        "inference_executed": status == "OK",
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "recommended_next_action": (
            "Proceed to Phase5-G Opportunity Quality Audit."
            if readiness_status == READY_FOR_PHASE5G_QUALITY_AUDIT
            else "Fix Phase5-F inference blocker before quality audit."
        ),
    }


def _blocked_result(
    readiness_status: str,
    reason: str,
    *,
    candidate_path: Path,
    feature_path: Path,
    model_path: Path,
    output_path: Path,
    top20_path: Path,
    summary_path: Path,
    audit_path: Path,
    created_at: str,
) -> OpportunityInferenceResult:
    audit = {
        "phase": PHASE,
        "created_at": created_at,
        "input_candidate_count": 0,
        "output_count": 0,
        "feature_column_count": 0,
        "forbidden_feature_column_count": 0,
        "future_feature_column_count": 0,
        "label_table_read_flag": False,
        "trade_result_feature_column_count": 0,
        "portfolio_feature_column_count": 0,
        "backtest_feature_column_count": 0,
        "ai_output_leakage_column_count": 0,
        "all_same_score": False,
        "unique_score_count": 0,
        "top5_count": 0,
        "top10_count": 0,
        "top20_count": 0,
        "leakage_audit_status": "NOT_RUN",
        "readiness_status": readiness_status,
        "block_reason": reason,
    }
    summary = build_summary(
        readiness_status=readiness_status,
        status="BLOCKED",
        candidate_path=candidate_path,
        feature_path=feature_path,
        model_path=model_path,
        output_path=output_path,
        top20_path=top20_path,
        summary_path=summary_path,
        audit_path=audit_path,
        created_at=created_at,
        model_payload={},
        training_metrics_path=DEFAULT_TRAINING_METRICS_PATH,
        audit=audit,
        output_count=0,
    )
    summary["block_reason"] = reason
    write_json(summary_path, summary)
    write_json(audit_path, audit)
    return OpportunityInferenceResult(output=pd.DataFrame(columns=OUTPUT_COLUMNS), summary=summary, audit=audit)


def count_as_of_date_violations(frame: pd.DataFrame) -> int:
    if "as_of_date" not in frame.columns or "target_date" not in frame.columns:
        return 0
    as_of = pd.to_datetime(frame["as_of_date"], errors="coerce")
    target = pd.to_datetime(frame["target_date"], errors="coerce")
    return int(((as_of > target) | as_of.isna() | target.isna()).sum())


def optional_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> list[str]:
    return [column for column in columns if column in frame.columns]


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def round_float(value: Any, digits: int = 8) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(numeric) or math.isinf(numeric):
        return 0.0
    return round(numeric, digits)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
