from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


TRAINING_DATASET_READY = "TRAINING_DATASET_READY"
TRAINING_DATASET_REPAIR_REQUIRED = "TRAINING_DATASET_REPAIR_REQUIRED"
TRAINING_DATASET_BLOCKED = "TRAINING_DATASET_BLOCKED"

FORBIDDEN_SOURCE_TERMS = (
    "backtest",
    "paper_ledger",
    "ledger",
    "pnl",
    "order_plan",
    "orderplan",
    "human_review",
    "broker",
    "blog",
    "public_confidence",
    "report",
)

FORBIDDEN_COLUMN_TERMS = (
    "paper_ledger",
    "realized_pnl",
    "unrealized_pnl",
    "profit_factor",
    "win_rate",
    "drawdown",
    "order_plan",
    "human_review",
    "selected",
    "bought",
    "cash",
    "portfolio_value",
    "broker",
    "public_confidence",
)


@dataclass(frozen=True)
class TrainingDatasetAuditResult:
    ai_name: str
    status: str
    dataset_path: str
    data_until: str
    safe_train_until: str
    train_until: str
    label_horizon: int | None
    row_count: int = 0
    min_date: str = ""
    max_date: str = ""
    code_count: int = 0
    feature_columns: tuple[str, ...] = ()
    label_columns: tuple[str, ...] = ()
    feature_schema_hash: str = ""
    label_null_rate: float = 0.0
    feature_null_rate: float = 0.0
    forbidden_columns_check: str = "UNKNOWN"
    forbidden_source_check: str = "UNKNOWN"
    future_leakage_check: str = "UNKNOWN"
    source_data_refs: dict[str, Any] | None = None
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    model_retraining_executed: bool = False
    inference_executed: bool = False
    order_plan_generation_executed: bool = False
    broker_order_api_called: bool = False
    virtual_fill_executed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["feature_columns"] = list(self.feature_columns)
        payload["label_columns"] = list(self.label_columns)
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        payload["source_data_refs"] = self.source_data_refs or {}
        return payload


def audit_training_dataset(
    *,
    ai_name: str,
    dataset_path: Path | str,
    data_until: str,
    safe_train_until: str,
    train_until: str,
    label_horizon: int | None,
    source_data_refs: dict[str, Any],
    label_source_until: str,
) -> TrainingDatasetAuditResult:
    path = Path(dataset_path)
    blocked: list[str] = []
    warnings: list[str] = []
    if label_horizon is None:
        blocked.append("missing_label_horizon")
    if train_until > safe_train_until:
        blocked.append("train_until_after_safe_train_until")
    if label_source_until > data_until:
        blocked.append("label_source_after_data_until")
    source_text = json.dumps(source_data_refs, ensure_ascii=True, sort_keys=True).lower()
    forbidden_source = any(term in source_text for term in FORBIDDEN_SOURCE_TERMS)
    source_ok = ("jquants" in source_text) or ("phase9/canonical_data/normalized_daily_quotes" in source_text)
    if forbidden_source:
        blocked.append("forbidden_source_detected")
    if not source_ok:
        blocked.append("source_data_refs_not_jquants_only")
    if not path.is_file():
        blocked.append("dataset_missing")
        return TrainingDatasetAuditResult(
            ai_name=ai_name,
            status=TRAINING_DATASET_BLOCKED,
            dataset_path=str(path),
            data_until=data_until,
            safe_train_until=safe_train_until,
            train_until=train_until,
            label_horizon=label_horizon,
            forbidden_source_check="FAILED" if forbidden_source or not source_ok else "OK",
            source_data_refs=source_data_refs,
            blocked_reasons=tuple(blocked),
        )
    frame = pd.read_parquet(path)
    date_col = "target_date" if "target_date" in frame.columns else "date"
    feature_columns = tuple(sorted(column for column in frame.columns if str(column).startswith("feature__")))
    label_columns = tuple(sorted(column for column in frame.columns if str(column).startswith("label__")))
    forbidden_columns = [
        column
        for column in frame.columns
        if any(term in str(column).lower() for term in FORBIDDEN_COLUMN_TERMS)
    ]
    if forbidden_columns:
        blocked.append("forbidden_columns_detected")
    if not feature_columns:
        blocked.append("feature_columns_missing")
    if not label_columns:
        blocked.append("label_columns_missing")
    dates = frame[date_col].astype(str) if date_col in frame.columns else pd.Series(dtype=str)
    future_rows = int((dates > train_until).sum()) if not dates.empty else 0
    if future_rows:
        blocked.append("feature_row_after_train_until")
    max_date = str(dates.max()) if not dates.empty else ""
    min_date = str(dates.min()) if not dates.empty else ""
    label_null_rate = _null_rate(frame, list(label_columns))
    feature_null_rate = _null_rate(frame, list(feature_columns))
    if label_null_rate > 0.05:
        warnings.append(f"label_null_rate_high:{label_null_rate:.6f}")
    if feature_null_rate > 0.50:
        warnings.append(f"feature_null_rate_high:{feature_null_rate:.6f}")
    status = TRAINING_DATASET_BLOCKED if blocked else (TRAINING_DATASET_REPAIR_REQUIRED if warnings else TRAINING_DATASET_READY)
    return TrainingDatasetAuditResult(
        ai_name=ai_name,
        status=status,
        dataset_path=str(path),
        data_until=data_until,
        safe_train_until=safe_train_until,
        train_until=train_until,
        label_horizon=label_horizon,
        row_count=int(len(frame)),
        min_date=min_date,
        max_date=max_date,
        code_count=int(frame["code"].astype(str).nunique()) if "code" in frame.columns else 0,
        feature_columns=feature_columns,
        label_columns=label_columns,
        feature_schema_hash=_schema_hash(feature_columns),
        label_null_rate=round(label_null_rate, 6),
        feature_null_rate=round(feature_null_rate, 6),
        forbidden_columns_check="FAILED" if forbidden_columns else "OK",
        forbidden_source_check="FAILED" if forbidden_source or not source_ok else "OK",
        future_leakage_check="FAILED" if future_rows else "OK",
        source_data_refs=source_data_refs,
        warnings=tuple(warnings),
        blocked_reasons=tuple(dict.fromkeys(blocked)),
    )


def _schema_hash(columns: tuple[str, ...]) -> str:
    payload = json.dumps(list(columns), ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _null_rate(frame: pd.DataFrame, columns: list[str]) -> float:
    if frame.empty or not columns:
        return 0.0
    return float(frame[columns].isna().sum().sum() / (len(frame) * len(columns)))
