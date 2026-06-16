from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.paper_trading.ledger import load_ledger


VIRTUAL_FILL_READY = "VIRTUAL_FILL_READY"
DATA_NOT_YET_AVAILABLE = "DATA_NOT_YET_AVAILABLE"
PARTIAL_READY = "PARTIAL_READY"
NOT_READY = "NOT_READY"


@dataclass(frozen=True)
class CanonicalUpdateResult:
    status: str
    target_date: str
    canonical_path: str
    source_normalized_path: str
    backup_path: str = ""
    execute: bool = False
    target_date_row_count: int = 0
    min_date: str = ""
    max_date: str = ""
    duplicate_date_code_count: int = 0
    abnormal_price_count: int = 0
    future_row_count: int = 0
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        return payload


@dataclass(frozen=True)
class VirtualFillReadinessResult:
    status: str
    target_date: str
    ledger_path: str
    quotes_path: str
    pending_order_count: int
    pending_order_codes: tuple[str, ...]
    target_date_row_count: int
    open_price_availability: dict[str, bool]
    open_prices: dict[str, str]
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    virtual_fill_executed: bool = False
    ledger_updated: bool = False
    broker_order_api_called: bool = False
    open_d_started: bool = False
    unlock_trade_called: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["pending_order_codes"] = list(self.pending_order_codes)
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        return payload


def update_canonical_normalized_for_date(
    *,
    target_date: str,
    canonical_path: Path | str = ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet",
    source_normalized_path: Path | str = ".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet",
    execute: bool = False,
    backup_existing: bool = True,
) -> CanonicalUpdateResult:
    canonical = Path(canonical_path)
    source = Path(source_normalized_path)
    blocked: list[str] = []
    warnings: list[str] = []
    if not canonical.is_file():
        blocked.append("canonical_normalized_path_missing")
    if not source.is_file():
        blocked.append("source_normalized_path_missing")
    if blocked:
        return CanonicalUpdateResult(
            status=NOT_READY,
            target_date=target_date,
            canonical_path=str(canonical),
            source_normalized_path=str(source),
            execute=execute,
            blocked_reasons=tuple(blocked),
        )
    canonical_df = pd.read_parquet(canonical)
    source_df = pd.read_parquet(source)
    source_date_col = _date_column(source_df)
    canonical_date_col = _date_column(canonical_df)
    source_future_rows = int((pd.to_datetime(source_df[source_date_col]) > pd.Timestamp(target_date)).sum())
    target_rows = source_df[source_df[source_date_col].astype(str) == target_date].copy()
    if target_rows.empty:
        return CanonicalUpdateResult(
            status=DATA_NOT_YET_AVAILABLE,
            target_date=target_date,
            canonical_path=str(canonical),
            source_normalized_path=str(source),
            execute=execute,
            target_date_row_count=0,
            min_date=_min_date(canonical_df),
            max_date=_max_date(canonical_df),
            future_row_count=source_future_rows,
            blocked_reasons=("target_date_source_rows_missing",),
        )
    target_rows = _align_columns(target_rows, canonical_df)
    merged = canonical_df[canonical_df[canonical_date_col].astype(str) != target_date].copy()
    merged = pd.concat([merged, target_rows], ignore_index=True)
    merged = _normalize_canonical_columns(merged)
    duplicate_count = int(merged.duplicated(subset=["date", "code"]).sum())
    if duplicate_count:
        merged = merged.drop_duplicates(subset=["date", "code"], keep="last")
    abnormal = _abnormal_price_count(target_rows)
    future_rows = int((pd.to_datetime(merged["date"]) > pd.Timestamp(target_date)).sum()) + source_future_rows
    if abnormal:
        blocked.append("target_date_abnormal_price")
    if future_rows:
        blocked.append("future_rows_detected")
    backup_path = ""
    if not blocked and execute:
        if backup_existing:
            backup_path = _backup_path(canonical)
            Path(backup_path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(canonical, backup_path)
        canonical.parent.mkdir(parents=True, exist_ok=True)
        merged.to_parquet(canonical, index=False)
    status = VIRTUAL_FILL_READY if not blocked else NOT_READY
    if not execute and not blocked:
        status = "CANONICAL_UPDATE_READY"
    return CanonicalUpdateResult(
        status=status,
        target_date=target_date,
        canonical_path=str(canonical),
        source_normalized_path=str(source),
        backup_path=backup_path,
        execute=execute,
        target_date_row_count=len(target_rows),
        min_date=_min_date(merged),
        max_date=_max_date(merged),
        duplicate_date_code_count=duplicate_count,
        abnormal_price_count=abnormal,
        future_row_count=future_rows,
        warnings=tuple(warnings),
        blocked_reasons=tuple(blocked),
    )


def check_pending_virtual_fill_readiness(
    *,
    target_date: str,
    ledger_path: Path | str = ".runtime/phase9/ledger/latest.json",
    quotes_path: Path | str = ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet",
) -> VirtualFillReadinessResult:
    ledger = load_ledger(ledger_path)
    pending_orders = [order for order in ledger.pending_orders if order.status in {"APPROVED", "PENDING_VIRTUAL_FILL"}]
    codes = tuple(dict.fromkeys(order.code for order in pending_orders))
    quote_file = Path(quotes_path)
    if not quote_file.is_file():
        return VirtualFillReadinessResult(
            status=NOT_READY,
            target_date=target_date,
            ledger_path=str(ledger_path),
            quotes_path=str(quotes_path),
            pending_order_count=len(pending_orders),
            pending_order_codes=codes,
            target_date_row_count=0,
            open_price_availability={code: False for code in codes},
            open_prices={},
            blocked_reasons=("quotes_path_missing",),
        )
    quotes = pd.read_parquet(quote_file)
    date_col = _date_column(quotes)
    rows = quotes[quotes[date_col].astype(str) == target_date].copy()
    if rows.empty:
        return VirtualFillReadinessResult(
            status=DATA_NOT_YET_AVAILABLE,
            target_date=target_date,
            ledger_path=str(ledger_path),
            quotes_path=str(quotes_path),
            pending_order_count=len(pending_orders),
            pending_order_codes=codes,
            target_date_row_count=0,
            open_price_availability={code: False for code in codes},
            open_prices={},
            blocked_reasons=("execution_date_quotes_missing",),
        )
    rows = _normalize_canonical_columns(rows)
    by_code = {str(item["code"]): item for item in rows.to_dict(orient="records")}
    availability: dict[str, bool] = {}
    prices: dict[str, str] = {}
    missing: list[str] = []
    abnormal: list[str] = []
    for code in codes:
        row = by_code.get(code)
        if not row:
            availability[code] = False
            missing.append(code)
            continue
        price = _decimal(row.get("open"))
        if price <= 0:
            availability[code] = False
            abnormal.append(code)
            continue
        availability[code] = True
        prices[code] = str(price)
    blocked: list[str] = []
    if missing:
        blocked.append("pending_order_open_price_missing")
    if abnormal:
        blocked.append("pending_order_open_price_abnormal")
    if len(pending_orders) != 5:
        blocked.append("pending_order_count_not_5")
    status = VIRTUAL_FILL_READY if not blocked else PARTIAL_READY
    return VirtualFillReadinessResult(
        status=status,
        target_date=target_date,
        ledger_path=str(ledger_path),
        quotes_path=str(quotes_path),
        pending_order_count=len(pending_orders),
        pending_order_codes=codes,
        target_date_row_count=len(rows),
        open_price_availability=availability,
        open_prices=prices,
        blocked_reasons=tuple(blocked),
    )


def write_phase9q_report(
    *,
    target_date: str,
    fetch_status: str,
    canonical_update: CanonicalUpdateResult,
    readiness: VirtualFillReadinessResult,
    markdown_path: Path | str = "docs/phase_reports/phase9q_market_data_refresh_for_pending_virtual_fill.md",
    json_path: Path | str = "reports/phase_reports/phase9q_market_data_refresh_for_pending_virtual_fill.json",
) -> dict[str, Any]:
    judgment = _judgment(canonical_update=canonical_update, readiness=readiness)
    payload = {
        "judgment": judgment,
        "target_date": target_date,
        "fetch_status": fetch_status,
        "raw_update_status": fetch_status,
        "canonical_normalized_update_status": canonical_update.status,
        "canonical_normalized": canonical_update.to_dict(),
        "canonical_min_date": canonical_update.min_date,
        "canonical_max_date": canonical_update.max_date,
        "target_date_row_count": canonical_update.target_date_row_count or readiness.target_date_row_count,
        "pending_order_codes": list(readiness.pending_order_codes),
        "open_price_availability": readiness.open_price_availability,
        "open_prices": readiness.open_prices,
        "virtual_fill_readiness": readiness.to_dict(),
        "blocked_reasons": list(dict.fromkeys(list(canonical_update.blocked_reasons) + list(readiness.blocked_reasons))),
        "next_action": _next_action(judgment),
        "ledger_updated": False,
        "virtual_fill_executed": False,
        "broker_order_api_called": False,
        "open_d_started": False,
        "unlock_trade_called": False,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    Path(markdown_path).parent.mkdir(parents=True, exist_ok=True)
    Path(markdown_path).write_text(_render_markdown(payload), encoding="utf-8")
    return payload


def _judgment(*, canonical_update: CanonicalUpdateResult, readiness: VirtualFillReadinessResult) -> str:
    if readiness.status == VIRTUAL_FILL_READY:
        return VIRTUAL_FILL_READY
    if canonical_update.status == DATA_NOT_YET_AVAILABLE or readiness.status == DATA_NOT_YET_AVAILABLE:
        return DATA_NOT_YET_AVAILABLE
    if readiness.status == PARTIAL_READY:
        return PARTIAL_READY
    return NOT_READY


def _next_action(judgment: str) -> str:
    if judgment == VIRTUAL_FILL_READY:
        return "Run Phase9-R virtual fill execution for 2026-06-16."
    if judgment == DATA_NOT_YET_AVAILABLE:
        return "Retry J-Quants per-date fetch after 2026-06-16 daily_quotes is distributed."
    if judgment == PARTIAL_READY:
        return "Inspect missing pending order open prices before virtual fill."
    return "Resolve market data refresh or canonical normalized update failure."


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9-Q Market Data Refresh for Pending Virtual Fill",
        "",
        f"- judgment: {payload['judgment']}",
        f"- target_date: {payload['target_date']}",
        f"- fetch_status: {payload['fetch_status']}",
        f"- canonical_normalized_update_status: {payload['canonical_normalized_update_status']}",
        f"- canonical_min_date: {payload['canonical_min_date']}",
        f"- canonical_max_date: {payload['canonical_max_date']}",
        f"- target_date_row_count: {payload['target_date_row_count']}",
        "",
        "## Pending Order Codes",
        "",
    ]
    lines.extend(f"- {code}: open_price_available={payload['open_price_availability'].get(code)}" for code in payload["pending_order_codes"])
    lines.extend(["", "## Blocked Reasons", ""])
    blocked = payload["blocked_reasons"]
    lines.extend([f"- {reason}" for reason in blocked] if blocked else ["- none"])
    lines.extend(
        [
            "",
            "## Next Action",
            "",
            payload["next_action"],
            "",
            "## Safety",
            "",
            "- ledger_updated: false",
            "- virtual_fill_executed: false",
            "- broker_order_api_called: false",
            "- open_d_started: false",
            "- unlock_trade_called: false",
            "",
        ]
    )
    return "\n".join(lines)


def _normalize_canonical_columns(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    if "date" not in df.columns:
        df["date"] = df.get("Date", df.get("target_date"))
    if "code" not in df.columns:
        df["code"] = df.get("Code", df.get("LocalCode"))
    if "open" not in df.columns:
        df["open"] = df.get("Open", df.get("AdjustmentOpen"))
    if "high" not in df.columns:
        df["high"] = df.get("High", df.get("AdjustmentHigh"))
    if "low" not in df.columns:
        df["low"] = df.get("Low", df.get("AdjustmentLow"))
    if "close" not in df.columns:
        df["close"] = df.get("Close", df.get("AdjustmentClose"))
    if "volume" not in df.columns:
        df["volume"] = df.get("Volume", df.get("AdjustmentVolume"))
    df["date"] = df["date"].astype(str)
    df["code"] = df["code"].astype(str)
    return df


def _align_columns(target_rows: pd.DataFrame, canonical_df: pd.DataFrame) -> pd.DataFrame:
    rows = _normalize_canonical_columns(target_rows)
    for column in canonical_df.columns:
        if column not in rows.columns:
            rows[column] = None
    for column in rows.columns:
        if column not in canonical_df.columns:
            canonical_df[column] = None
    return rows[canonical_df.columns]


def _date_column(frame: pd.DataFrame) -> str:
    for column in ("date", "Date", "target_date"):
        if column in frame.columns:
            return column
    raise ValueError("date column not found")


def _min_date(frame: pd.DataFrame) -> str:
    col = _date_column(frame)
    return str(frame[col].min()) if not frame.empty else ""


def _max_date(frame: pd.DataFrame) -> str:
    col = _date_column(frame)
    return str(frame[col].max()) if not frame.empty else ""


def _abnormal_price_count(frame: pd.DataFrame) -> int:
    df = _normalize_canonical_columns(frame)
    count = 0
    for column in ("open", "high", "low", "close"):
        count += int((pd.to_numeric(df[column], errors="coerce").fillna(0) <= 0).sum())
    return count


def _decimal(value: Any) -> Decimal:
    if value in (None, "") or pd.isna(value):
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))


def _backup_path(path: Path) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return str(path.with_name(f"{path.name}.backup_{stamp}"))
