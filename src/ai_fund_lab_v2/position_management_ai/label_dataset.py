from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.training import contains_any, to_jsonable
from ai_fund_lab_v2.position_management_ai.feature_builder import (
    REQUIRED_FEATURE_COLUMNS,
    TECHNICAL_FEATURE_COLUMNS,
    build_position_features_from_quotes,
    fixture_opportunity_frame,
    fixture_position_scenarios,
    fixture_quote_frame,
    normalize_quote_frame,
)
from ai_fund_lab_v2.position_management_ai.inference import FORBIDDEN_FEATURE_PREFIXES, FORBIDDEN_FEATURE_TERMS

PHASE = "Phase6-C"
DATASET_VERSION = "position_management_label_dataset_phase6c_v1"
FEATURE_VERSION = "position_management_feature_phase6b_v1"
LABEL_VERSION = "position_management_label_phase6c_v1"
READY_FOR_PHASE6D_LABEL_VALIDATION = "READY_FOR_PHASE6D_LABEL_VALIDATION"
BLOCKED_BY_LABEL_LEAKAGE = "BLOCKED_BY_LABEL_LEAKAGE"
BLOCKED_BY_EMPTY_DATASET = "BLOCKED_BY_EMPTY_DATASET"

DEFAULT_OUTPUT_CSV_PATH = Path("reports/position_management_ai/phase6c_position_label_dataset.csv")
DEFAULT_OUTPUT_JSON_PATH = Path("reports/position_management_ai/phase6c_position_label_dataset.json")
DEFAULT_AUDIT_PATH = Path("reports/position_management_ai/phase6c_position_label_audit.json")

LABEL_COLUMNS = (
    "future_return_5bd",
    "future_return_10bd",
    "future_return_20bd",
    "future_max_return_20bd",
    "future_min_return_20bd",
    "future_drawdown_20bd",
    "future_profit_retention_20bd",
    "label_continue_winner",
    "label_exit_before_drawdown",
    "label_add_candidate",
    "label_reduce_candidate",
)

FEATURE_COLUMNS = (
    "entry_price",
    "current_price",
    "holding_days",
    "unrealized_return",
    "peak_return",
    "drawdown_from_peak",
    "return_1d",
    "return_5d",
    "return_20d",
    "volume_ratio_5d",
    "volume_ratio_20d",
    "close_over_ma_5d",
    "close_over_ma_20d",
    "ma_5_20_ratio",
    "ma_20_60_ratio",
    "volatility_20d",
    "trend_strength_score",
    "expected_edge_score",
    "buy_rank",
    "downside_risk_score",
    "risk_guard_status",
)


@dataclass(frozen=True)
class Phase6CDatasetResult:
    dataset: pd.DataFrame
    summary: dict[str, Any]
    audit: dict[str, Any]


def run_phase6c_position_label_dataset_dry_run(
    *,
    output_csv_path: Path = DEFAULT_OUTPUT_CSV_PATH,
    output_json_path: Path = DEFAULT_OUTPUT_JSON_PATH,
    audit_path: Path = DEFAULT_AUDIT_PATH,
    created_at: str | None = None,
) -> Phase6CDatasetResult:
    created_at = created_at or now_utc()
    quote_frame = fixture_quote_frame()
    position_frame = phase6c_position_scenarios()
    opportunity_frame = phase6c_opportunity_frame()
    feature_frame = build_position_features_from_quotes(
        position_frame=position_frame,
        quote_frame=quote_frame,
        opportunity_frame=opportunity_frame,
        created_at=created_at,
    )
    dataset = build_position_label_dataset_frame(
        feature_frame=feature_frame,
        quote_frame=quote_frame,
        created_at=created_at,
    )
    audit = audit_position_label_dataset(dataset, created_at=created_at)
    readiness_status = READY_FOR_PHASE6D_LABEL_VALIDATION
    if dataset.empty:
        readiness_status = BLOCKED_BY_EMPTY_DATASET
    elif audit["label_leakage_audit_status"] != "OK":
        readiness_status = BLOCKED_BY_LABEL_LEAKAGE
    audit = {**audit, "readiness_status": readiness_status}
    summary = build_phase6c_summary(
        dataset=dataset,
        audit=audit,
        output_csv_path=output_csv_path,
        output_json_path=output_json_path,
        audit_path=audit_path,
        created_at=created_at,
        readiness_status=readiness_status,
    )
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(output_csv_path, index=False)
    write_json(output_json_path, summary)
    write_json(audit_path, audit)
    return Phase6CDatasetResult(dataset=dataset, summary=summary, audit=audit)


def build_position_label_dataset_frame(
    *,
    feature_frame: pd.DataFrame,
    quote_frame: pd.DataFrame,
    created_at: str | None = None,
) -> pd.DataFrame:
    created_at = created_at or now_utc()
    if feature_frame.empty:
        return pd.DataFrame()
    labels = build_position_labels(feature_frame=feature_frame, quote_frame=quote_frame)
    feature_part = feature_frame.copy()
    meta_columns = ["target_date", "entry_date", "code", "dataset_version", "feature_version", "label_version", "created_at"]
    feature_part["dataset_version"] = DATASET_VERSION
    feature_part["feature_version"] = FEATURE_VERSION
    feature_part["label_version"] = LABEL_VERSION
    feature_part["created_at"] = created_at
    feature_columns = [column for column in FEATURE_COLUMNS if column in feature_part.columns]
    prefixed_features = feature_part[["target_date", "entry_date", "code", "dataset_version", "feature_version", "label_version", "created_at"] + feature_columns].rename(
        columns={column: f"feature__{column}" for column in feature_columns}
    )
    label_columns = [column for column in LABEL_COLUMNS if column in labels.columns]
    prefixed_labels = labels[["target_date", "entry_date", "code"] + label_columns].rename(
        columns={column: f"label__{column}" for column in label_columns}
    )
    dataset = prefixed_features.merge(prefixed_labels, on=["target_date", "entry_date", "code"], how="inner", validate="one_to_one")
    ordered_feature_columns = [f"feature__{column}" for column in feature_columns]
    ordered_label_columns = [f"label__{column}" for column in label_columns]
    return dataset[meta_columns + ordered_feature_columns + ordered_label_columns]


def build_position_labels(*, feature_frame: pd.DataFrame, quote_frame: pd.DataFrame) -> pd.DataFrame:
    quotes = normalize_quote_frame(quote_frame)
    rows: list[dict[str, Any]] = []
    for feature in feature_frame.to_dict("records"):
        code = str(feature["code"])
        target_date = str(feature["target_date"])
        entry_date = str(feature["entry_date"])
        current_price = float(feature["current_price"])
        current_return = float(feature["unrealized_return"])
        future = quotes[(quotes["code"] == code) & (quotes["target_date"] > target_date)].sort_values("target_date").head(20)
        if future.empty:
            continue
        future_close = pd.to_numeric(future["Close"], errors="coerce")
        future_low = pd.to_numeric(future.get("Low", future["Close"]), errors="coerce")
        return_5bd = future_return_at(future_close, current_price, 5)
        return_10bd = future_return_at(future_close, current_price, 10)
        return_20bd = future_return_at(future_close, current_price, 20)
        future_max_return_20bd = safe_return(float(future_close.max()), current_price)
        future_min_return_20bd = safe_return(float(future_low.min()), current_price)
        future_drawdown_20bd = future_min_return_20bd
        future_profit_retention_20bd = current_return + future_min_return_20bd
        expected_edge_score = float(feature.get("expected_edge_score", 0.0))
        buy_rank = int(feature.get("buy_rank", 999))
        rows.append(
            {
                "target_date": target_date,
                "entry_date": entry_date,
                "code": code,
                "future_return_5bd": round_float(return_5bd),
                "future_return_10bd": round_float(return_10bd),
                "future_return_20bd": round_float(return_20bd),
                "future_max_return_20bd": round_float(future_max_return_20bd),
                "future_min_return_20bd": round_float(future_min_return_20bd),
                "future_drawdown_20bd": round_float(future_drawdown_20bd),
                "future_profit_retention_20bd": round_float(future_profit_retention_20bd),
                "label_continue_winner": bool(
                    current_return > 0.0
                    and future_max_return_20bd > 0.04
                    and future_max_return_20bd > current_return * 0.20
                    and future_drawdown_20bd > -0.08
                ),
                "label_exit_before_drawdown": bool(future_min_return_20bd < -0.05 or future_drawdown_20bd < -0.08),
                "label_add_candidate": bool(
                    current_return > 0.0
                    and expected_edge_score >= 0.08
                    and buy_rank <= 5
                    and future_max_return_20bd > 0.06
                    and future_drawdown_20bd > -0.08
                ),
                "label_reduce_candidate": bool(
                    current_return > 0.0
                    and future_max_return_20bd < 0.04
                    and future_drawdown_20bd <= -0.04
                ),
            }
        )
    return pd.DataFrame(rows)


def audit_position_label_dataset(dataset: pd.DataFrame, *, created_at: str | None = None) -> dict[str, Any]:
    created_at = created_at or now_utc()
    columns = [str(column) for column in dataset.columns]
    feature_columns = [column for column in columns if column.startswith("feature__")]
    label_columns = [column for column in columns if column.startswith("label__")]
    forbidden_feature_columns = [
        column for column in feature_columns if is_forbidden_label_dataset_feature(column.replace("feature__", "", 1))
    ]
    future_feature_columns = [
        column
        for column in feature_columns
        if column.replace("feature__", "", 1).startswith(("future_return_", "future_max_return_", "future_min_return_", "future_drawdown_", "future_profit_retention_", "top_decile_", "downside_bad_"))
    ]
    unprefixed_label_columns = [column for column in columns if column in LABEL_COLUMNS]
    feature_label_separated = bool(feature_columns) and bool(label_columns) and not unprefixed_label_columns
    label_distribution = build_label_distribution(dataset)
    label_leakage_ok = not (forbidden_feature_columns or future_feature_columns or unprefixed_label_columns) and feature_label_separated
    return {
        "phase": PHASE,
        "created_at": created_at,
        "dataset_row_count": int(len(dataset)),
        "feature_column_count": len(feature_columns),
        "label_column_count": len(label_columns),
        "feature_columns": feature_columns,
        "label_columns": label_columns,
        "forbidden_feature_column_count": len(forbidden_feature_columns),
        "forbidden_feature_columns": forbidden_feature_columns,
        "future_feature_column_count": len(future_feature_columns),
        "future_feature_columns": future_feature_columns,
        "unprefixed_label_column_count": len(unprefixed_label_columns),
        "unprefixed_label_columns": unprefixed_label_columns,
        "feature_label_columns_separated": feature_label_separated,
        "label_distribution": label_distribution,
        "label_leakage_audit_status": "OK" if label_leakage_ok else "ERROR",
        "forbidden_feature_audit_status": "OK" if not forbidden_feature_columns and not future_feature_columns else "ERROR",
        "training_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
    }


def build_label_distribution(dataset: pd.DataFrame) -> dict[str, dict[str, int]]:
    distribution: dict[str, dict[str, int]] = {}
    for label in ("label__label_continue_winner", "label__label_exit_before_drawdown", "label__label_add_candidate", "label__label_reduce_candidate"):
        if label not in dataset.columns:
            continue
        counts = dataset[label].astype(bool).value_counts().to_dict()
        distribution[label] = {
            "true": int(counts.get(True, 0)),
            "false": int(counts.get(False, 0)),
        }
    return distribution


def phase6c_position_scenarios() -> pd.DataFrame:
    base = fixture_position_scenarios()
    scenarios: list[pd.DataFrame] = []
    for target_date in ("2026-05-22", "2026-05-29", "2026-06-05"):
        scenario = base.copy()
        scenario["target_date"] = target_date
        scenarios.append(scenario)
    return pd.concat(scenarios, ignore_index=True)


def phase6c_opportunity_frame() -> pd.DataFrame:
    base = fixture_opportunity_frame()
    frames: list[pd.DataFrame] = []
    for index, target_date in enumerate(("2026-05-22", "2026-05-29", "2026-06-05")):
        frame = base.copy()
        frame["target_date"] = target_date
        if index == 1:
            frame.loc[frame["code"].isin(["2003", "2006"]), "buy_rank"] = [4, 6]
        if index == 2:
            frame.loc[frame["code"].isin(["2002", "2005"]), "risk_guard_status"] = "bad"
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def build_phase6c_summary(
    *,
    dataset: pd.DataFrame,
    audit: dict[str, Any],
    output_csv_path: Path,
    output_json_path: Path,
    audit_path: Path,
    created_at: str,
    readiness_status: str,
) -> dict[str, Any]:
    target_dates = sorted(dataset["target_date"].astype(str).unique().tolist()) if "target_date" in dataset.columns else []
    codes = sorted(dataset["code"].astype(str).unique().tolist()) if "code" in dataset.columns else []
    return {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY_FOR_PHASE6D_LABEL_VALIDATION else "BLOCKED",
        "readiness_status": readiness_status,
        "created_at": created_at,
        "dataset_version": DATASET_VERSION,
        "feature_version": FEATURE_VERSION,
        "label_version": LABEL_VERSION,
        "output_csv_path": str(output_csv_path),
        "output_json_path": str(output_json_path),
        "audit_path": str(audit_path),
        "row_count": int(len(dataset)),
        "target_date_count": len(target_dates),
        "target_dates": target_dates,
        "code_count": len(codes),
        "codes": codes,
        "label_distribution": audit.get("label_distribution", {}),
        "label_leakage_audit_status": audit.get("label_leakage_audit_status", "NOT_RUN"),
        "forbidden_feature_audit_status": audit.get("forbidden_feature_audit_status", "NOT_RUN"),
        "feature_label_columns_separated": bool(audit.get("feature_label_columns_separated", False)),
        "training_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
    }


def future_return_at(future_close: pd.Series, current_price: float, horizon: int) -> float:
    if future_close.empty:
        return 0.0
    index = min(horizon, len(future_close)) - 1
    return safe_return(float(future_close.iloc[index]), current_price)


def is_forbidden_label_dataset_feature(column: str) -> bool:
    normalized = column.strip().lower().replace("-", "_")
    if normalized.startswith(FORBIDDEN_FEATURE_PREFIXES):
        return True
    if normalized.startswith(("future_min_return_", "future_drawdown_", "future_profit_retention_", "label_")):
        return True
    return contains_any(normalized, FORBIDDEN_FEATURE_TERMS)


def safe_return(current: float, previous: float) -> float:
    if previous == 0 or np.isnan(previous):
        return 0.0
    return float(current) / float(previous) - 1.0


def round_float(value: Any, digits: int = 8) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if np.isnan(numeric) or np.isinf(numeric):
        return 0.0
    return round(numeric, digits)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
