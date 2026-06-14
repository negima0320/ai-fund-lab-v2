from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.dataset_builder import (
    FORBIDDEN_FEATURE_PREFIXES,
    FORBIDDEN_FEATURE_TERMS,
    contains_any,
    is_forbidden_feature_column,
)

PHASE = "Phase5-D2"
DEFAULT_TOP_N = 50
MODEL_VERSION = "phase4bf_formal_candidate_model"
READY_FOR_PHASE5D_DATASET = "READY_FOR_PHASE5D_DATASET"
BLOCKED_BY_NO_TARGET_DATES = "BLOCKED_BY_NO_TARGET_DATES"
BLOCKED_BY_NO_CANDIDATES = "BLOCKED_BY_NO_CANDIDATES"
BLOCKED_BY_LEAKAGE_AUDIT = "BLOCKED_BY_LEAKAGE_AUDIT"

OPERATIONAL_FORBIDDEN_TERMS = (
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
)


@dataclass(frozen=True)
class HistoricalCandidateBuildResult:
    candidates: pd.DataFrame
    summary: dict[str, Any]
    audit: dict[str, Any]


def build_historical_candidate_top50(
    *,
    model_path: Path,
    feature_path: Path,
    label_path: Path,
    output_dir: Path = Path("reports/opportunity_ai/phase5d2"),
    frequency: str = "monthly",
    top_n: int = DEFAULT_TOP_N,
    max_dates: int | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = output_dir / "historical_candidate_top50.parquet"
    summary_path = output_dir / "historical_candidate_top50_summary.json"
    audit_path = output_dir / "historical_candidate_top50_audit.json"

    model_payload = read_pickle(model_path)
    model = model_payload.get("model")
    feature_columns = [str(column) for column in model_payload.get("feature_columns", [])]
    if model is None or not feature_columns:
        raise ValueError("model artifact must contain model and feature_columns")

    feature = read_table(feature_path)
    label = read_table(label_path, columns=["target_date", "code"])
    result = build_historical_candidate_top50_frame(
        model=model,
        model_feature_columns=feature_columns,
        feature_frame=feature,
        label_frame=label,
        frequency=frequency,
        top_n=top_n,
        max_dates=max_dates,
    )
    result.candidates.to_parquet(candidate_path, index=False, engine="pyarrow")
    summary = {
        **result.summary,
        "candidate_output_path": str(candidate_path),
        "summary_path": str(summary_path),
        "audit_path": str(audit_path),
        "model_path": str(model_path),
        "feature_path": str(feature_path),
        "label_path": str(label_path),
    }
    write_json(summary_path, summary)
    write_json(audit_path, result.audit)
    return summary


def build_historical_candidate_top50_frame(
    *,
    model: Any,
    model_feature_columns: list[str],
    feature_frame: pd.DataFrame,
    label_frame: pd.DataFrame,
    frequency: str = "monthly",
    top_n: int = DEFAULT_TOP_N,
    max_dates: int | None = None,
    created_at: str | None = None,
) -> HistoricalCandidateBuildResult:
    created_at = created_at or now_utc()
    feature = normalize_key_columns(feature_frame)
    labels = normalize_key_columns(label_frame)
    selected_dates = select_target_dates(
        feature_dates=feature["target_date"].drop_duplicates().astype(str).tolist(),
        label_dates=labels["target_date"].drop_duplicates().astype(str).tolist(),
        frequency=frequency,
        max_dates=max_dates,
    )
    stripped_feature_columns = [column.replace("feature__", "", 1) for column in model_feature_columns]
    audit = audit_historical_candidate_inputs(
        model_feature_columns=model_feature_columns,
        source_feature_columns=[str(column) for column in feature.columns],
        selected_target_dates=selected_dates,
    )
    if not selected_dates:
        candidates = empty_candidate_frame()
        summary = summary_payload(candidates, labels, selected_dates, audit, BLOCKED_BY_NO_TARGET_DATES)
        return HistoricalCandidateBuildResult(candidates=candidates, summary=summary, audit=audit)
    if audit["leakage_audit_status"] != "OK":
        candidates = empty_candidate_frame()
        summary = summary_payload(candidates, labels, selected_dates, audit, BLOCKED_BY_LEAKAGE_AUDIT)
        return HistoricalCandidateBuildResult(candidates=candidates, summary=summary, audit=audit)

    label_keys = set(zip(labels["target_date"].astype(str), labels["code"].astype(str)))
    rows: list[dict[str, Any]] = []
    selected_date_set = set(selected_dates)
    feature_for_selected_dates = feature[feature["target_date"].astype(str).isin(selected_date_set)]
    for target_date, snapshot in feature_for_selected_dates.groupby("target_date", sort=True):
        target_date = str(target_date)
        snapshot = eligible_snapshot(snapshot)
        if snapshot.empty:
            continue
        scores = predict_scores(model, feature_matrix(snapshot, stripped_feature_columns))
        scored = build_scored_rows(snapshot, scores, top_n=top_n, created_at=created_at)
        rows.extend(scored)

    candidates = pd.DataFrame(rows, columns=list(candidate_columns()))
    joined_keys = sum(1 for row in rows if (str(row["target_date"]), str(row["code"])) in label_keys)
    audit = {
        **audit,
        "candidate_snapshot_count": len(selected_dates),
        "target_date_count": len(selected_dates),
        "candidate_rows": int(len(candidates)),
        "candidate_count_per_date_min": int(candidates.groupby("target_date").size().min()) if not candidates.empty else 0,
        "candidate_count_per_date_max": int(candidates.groupby("target_date").size().max()) if not candidates.empty else 0,
        "label_joinable_target_date_count": int(len(set(candidates["target_date"].astype(str)).intersection(set(labels["target_date"].astype(str))))) if not candidates.empty else 0,
        "label_joinable_row_count": int(joined_keys),
        "label_join_coverage_rate": rate(joined_keys, len(candidates)),
    }
    readiness = READY_FOR_PHASE5D_DATASET
    if candidates.empty:
        readiness = BLOCKED_BY_NO_CANDIDATES
    elif audit["leakage_audit_status"] != "OK":
        readiness = BLOCKED_BY_LEAKAGE_AUDIT
    elif audit["label_joinable_row_count"] <= 0:
        readiness = BLOCKED_BY_NO_CANDIDATES
    summary = summary_payload(candidates, labels, selected_dates, audit, readiness)
    return HistoricalCandidateBuildResult(candidates=candidates, summary=summary, audit=audit)


def select_target_dates(
    *,
    feature_dates: list[str],
    label_dates: list[str],
    frequency: str,
    max_dates: int | None,
) -> list[str]:
    common = sorted(set(feature_dates).intersection(label_dates))
    if frequency == "all":
        selected = common
    elif frequency == "weekly":
        selected = [date for index, date in enumerate(common) if index % 5 == 0]
    elif frequency == "monthly":
        by_month: dict[str, str] = {}
        for date in common:
            by_month[date[:7]] = date
        selected = sorted(by_month.values())
    else:
        raise ValueError("frequency must be one of: monthly, weekly, all")
    if max_dates is not None:
        selected = selected[-max_dates:]
    return selected


def build_scored_rows(snapshot: pd.DataFrame, scores: np.ndarray, *, top_n: int, created_at: str) -> list[dict[str, Any]]:
    scored = snapshot.copy()
    scored["candidate_score"] = np.round(scores.astype(float), 8)
    scored = scored.sort_values(["candidate_score", "code"], ascending=[False, True]).head(top_n).copy()
    scored["candidate_rank"] = range(1, len(scored) + 1)
    inference_run_id = f"phase5d2_historical_candidate_top50_{str(scored['target_date'].iloc[0])}"
    rows: list[dict[str, Any]] = []
    for row in scored.to_dict("records"):
        rows.append(
            {
                "target_date": str(row.get("target_date")),
                "code": str(row.get("code")),
                "candidate_score": float(row.get("candidate_score")),
                "candidate_rank": int(row.get("candidate_rank")),
                "candidate_reason": candidate_reason(row, float(row.get("candidate_score"))),
                "excluded_reason": "",
                "model_version": MODEL_VERSION,
                "feature_version": str(row.get("feature_version") or "candidate_features_real_runtime_v1"),
                "feature_snapshot_id": row.get("source_snapshot_id") or row.get("feature_version"),
                "inference_run_id": inference_run_id,
                "created_at": created_at,
            }
        )
    return rows


def eligible_snapshot(frame: pd.DataFrame) -> pd.DataFrame:
    eligible = frame.copy()
    if "universe_eligible" in eligible.columns:
        eligible = eligible[eligible["universe_eligible"].astype(bool)]
    if "excluded_reason" in eligible.columns:
        eligible = eligible[eligible["excluded_reason"].fillna("").astype(str).eq("")]
    return eligible


def feature_matrix(frame: pd.DataFrame, feature_columns: list[str]) -> np.ndarray:
    missing = [column for column in feature_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"feature table missing model columns: {', '.join(missing)}")
    values = frame[feature_columns].copy()
    for column in values.columns:
        if values[column].dtype == bool:
            values[column] = values[column].astype(float)
    return values.astype(float).to_numpy()


def predict_scores(model: Any, x_input: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(x_input)
        if proba.ndim == 2 and proba.shape[1] > 1:
            return np.asarray(proba[:, 1], dtype=float)
    if hasattr(model, "decision_function"):
        raw = np.asarray(model.decision_function(x_input), dtype=float)
        return 1.0 / (1.0 + np.exp(-raw))
    return np.asarray(model.predict(x_input), dtype=float)


def candidate_reason(row: dict[str, Any], score: float) -> str:
    reasons: list[str] = []
    if score >= 0.5:
        reasons.append("high_candidate_score")
    if numeric(row.get("price_momentum_return_20d")) > 0:
        reasons.append("price_momentum_positive")
    if numeric(row.get("price_momentum_return_60d")) > 0:
        reasons.append("long_momentum_positive")
    if numeric(row.get("volume_momentum_ratio_5d")) > 1:
        reasons.append("volume_momentum_positive")
    if numeric(row.get("liquidity_avg_volume_20d")) > 0:
        reasons.append("liquidity_available")
    return "|".join(reasons) if reasons else "formal_score_ranked"


def audit_historical_candidate_inputs(
    *,
    model_feature_columns: list[str],
    source_feature_columns: list[str],
    selected_target_dates: list[str],
) -> dict[str, Any]:
    stripped = [column.replace("feature__", "", 1) for column in model_feature_columns]
    future_columns = [column for column in stripped if column.startswith(FORBIDDEN_FEATURE_PREFIXES)]
    forbidden_model_columns = [column for column in stripped if is_forbidden_feature_column(column)]
    source_operational_columns = [
        column for column in source_feature_columns if contains_any(column, OPERATIONAL_FORBIDDEN_TERMS)
    ]
    trade_columns = [column for column in source_operational_columns if contains_any(column, ("trade_result", "trade_profit"))]
    portfolio_columns = [
        column
        for column in source_operational_columns
        if contains_any(column, ("portfolio", "cash", "annual_return", "final_assets"))
    ]
    backtest_columns = [column for column in source_operational_columns if "backtest" in column.lower()]
    ai_output_columns = [
        column
        for column in source_operational_columns
        if contains_any(column, ("opportunity_output", "candidate_evaluation"))
    ]
    leakage_ok = not (
        future_columns
        or forbidden_model_columns
        or source_operational_columns
    )
    return {
        "phase": PHASE,
        "created_at": now_utc(),
        "selected_target_dates": selected_target_dates,
        "model_feature_column_count": len(model_feature_columns),
        "future_feature_column_count": len(future_columns),
        "future_feature_columns": future_columns,
        "forbidden_feature_column_count": len(set(forbidden_model_columns + source_operational_columns)),
        "forbidden_feature_columns": sorted(set(forbidden_model_columns + source_operational_columns)),
        "trade_result_column_count": len(trade_columns),
        "portfolio_column_count": len(portfolio_columns),
        "backtest_column_count": len(backtest_columns),
        "ai_output_leakage_column_count": len(ai_output_columns),
        "broker_api_called": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "leakage_audit_status": "OK" if leakage_ok else "ERROR",
    }


def summary_payload(
    candidates: pd.DataFrame,
    labels: pd.DataFrame,
    selected_dates: list[str],
    audit: dict[str, Any],
    readiness_status: str,
) -> dict[str, Any]:
    per_date = candidates.groupby("target_date").size() if not candidates.empty else pd.Series(dtype=int)
    return {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY_FOR_PHASE5D_DATASET else "BLOCKED",
        "readiness_status": readiness_status,
        "historical_candidate_generation_executed": True,
        "frequency": None,
        "top_n": DEFAULT_TOP_N,
        "candidate_snapshot_count": len(selected_dates),
        "target_date_count": len(selected_dates),
        "target_date_min": selected_dates[0] if selected_dates else None,
        "target_date_max": selected_dates[-1] if selected_dates else None,
        "label_target_date_min": str(labels["target_date"].min()) if not labels.empty else None,
        "label_target_date_max": str(labels["target_date"].max()) if not labels.empty else None,
        "candidate_rows": int(len(candidates)),
        "candidate_count_per_date_min": int(per_date.min()) if not per_date.empty else 0,
        "candidate_count_per_date_max": int(per_date.max()) if not per_date.empty else 0,
        "label_joinable_target_date_count": audit.get("label_joinable_target_date_count", 0),
        "label_join_coverage_rate": audit.get("label_join_coverage_rate", 0.0),
        "future_feature_column_count": audit["future_feature_column_count"],
        "forbidden_feature_column_count": audit["forbidden_feature_column_count"],
        "trade_result_column_count": audit["trade_result_column_count"],
        "portfolio_column_count": audit["portfolio_column_count"],
        "backtest_column_count": audit["backtest_column_count"],
        "ai_output_leakage_column_count": audit["ai_output_leakage_column_count"],
        "leakage_audit_status": audit["leakage_audit_status"],
        "training_executed": False,
        "inference_executed": True,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "recommended_next_action": "Run Phase5-D dataset builder with historical candidate artifact." if readiness_status == READY_FOR_PHASE5D_DATASET else "Fix Phase5-D2 blocker before dataset build.",
    }


def read_table(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path, columns=columns)
    if path.suffix == ".csv":
        return pd.read_csv(path, dtype={"code": str}, usecols=columns)
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows") if isinstance(payload, dict) else payload
    frame = pd.DataFrame(rows)
    if columns:
        frame = frame[[column for column in columns if column in frame.columns]]
    return frame


def read_pickle(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    return payload if isinstance(payload, dict) else {}


def normalize_key_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    if "target_date" not in frame.columns or "code" not in frame.columns:
        raise ValueError("table must contain target_date and code")
    frame["target_date"] = frame["target_date"].astype(str)
    frame["code"] = frame["code"].astype(str)
    return frame


def empty_candidate_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=list(candidate_columns()))


def candidate_columns() -> tuple[str, ...]:
    return (
        "target_date",
        "code",
        "candidate_score",
        "candidate_rank",
        "candidate_reason",
        "excluded_reason",
        "model_version",
        "feature_version",
        "feature_snapshot_id",
        "inference_run_id",
        "created_at",
    )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def numeric(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0
