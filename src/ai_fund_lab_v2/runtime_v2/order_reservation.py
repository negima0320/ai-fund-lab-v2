"""Order-condition-derived cash reservation authority."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping


JPX_REGULAR_PRICE_LIMIT_BANDS: tuple[tuple[float, float], ...] = (
    (100.0, 30.0),
    (200.0, 50.0),
    (500.0, 80.0),
    (700.0, 100.0),
    (1_000.0, 150.0),
    (1_500.0, 300.0),
    (2_000.0, 400.0),
    (3_000.0, 500.0),
    (5_000.0, 700.0),
    (7_000.0, 1_000.0),
    (10_000.0, 1_500.0),
    (15_000.0, 3_000.0),
    (20_000.0, 4_000.0),
    (30_000.0, 5_000.0),
    (50_000.0, 7_000.0),
    (70_000.0, 10_000.0),
    (100_000.0, 15_000.0),
    (150_000.0, 30_000.0),
    (200_000.0, 40_000.0),
    (300_000.0, 50_000.0),
    (500_000.0, 70_000.0),
    (700_000.0, 100_000.0),
    (1_000_000.0, 150_000.0),
    (1_500_000.0, 300_000.0),
    (2_000_000.0, 400_000.0),
    (3_000_000.0, 500_000.0),
    (5_000_000.0, 700_000.0),
    (7_000_000.0, 1_000_000.0),
    (10_000_000.0, 1_500_000.0),
    (15_000_000.0, 3_000_000.0),
    (20_000_000.0, 4_000_000.0),
    (30_000_000.0, 5_000_000.0),
    (50_000_000.0, 7_000_000.0),
    (math.inf, 10_000_000.0),
)


def jpx_regular_price_limit_width(base_price: float) -> float:
    price = float(base_price)
    if price <= 0.0:
        return 0.0
    for upper_exclusive, width in JPX_REGULAR_PRICE_LIMIT_BANDS:
        if price < upper_exclusive:
            return width
    return 10_000_000.0


def jpx_regular_stop_high_price(base_price: float) -> float:
    price = float(base_price)
    return round(price + jpx_regular_price_limit_width(price), 6) if price > 0.0 else 0.0


def resolve_order_cash_reservation(
    *,
    runtime_root: Path | str,
    business_date: str,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    reference_price: float,
    reference_price_authority: Mapping[str, Any] | None = None,
    limit_price: float | None = None,
) -> dict[str, Any]:
    side_text = str(side or "").upper()
    order_type_text = str(order_type or "").upper()
    qty = float(quantity or 0.0)
    reference = float(reference_price or 0.0)
    if side_text == "BUY" and order_type_text == "LIMIT":
        price = float(limit_price if limit_price is not None else reference)
        price_type = "limit_order_limit_price_cash_reservation"
        source_field = "limit_price" if limit_price is not None else "reference_price"
        source_authority = "approved_order_limit_price" if limit_price is not None else "strategy_planning_reference_price_authority"
        authority_status = "PASS" if price > 0.0 else "REVIEW_REQUIRED"
        basis = {"status": "NOT_REQUIRED", "reason": "limit_buy_uses_limit_price"}
    elif side_text == "BUY" and order_type_text == "MARKET":
        basis = _previous_close_basis(runtime_root=Path(runtime_root), business_date=business_date, symbol=symbol)
        if basis["status"] == "PASS":
            price = jpx_regular_stop_high_price(float(basis["base_price"]))
            price_type = "market_buy_stop_high_cash_reservation"
            source_field = "previous_close"
            source_authority = "production_market_buy_price_limit_authority"
            authority_status = "PASS"
        else:
            price = reference
            price_type = "market_buy_stop_high_cash_reservation_unresolved_reference_fallback"
            source_field = "reference_price"
            source_authority = "strategy_planning_reference_price_authority"
            authority_status = "REVIEW_REQUIRED"
    else:
        price = reference
        price_type = "non_buy_reference_notional_observability"
        source_field = "reference_price"
        source_authority = "strategy_planning_reference_price_authority"
        authority_status = "PASS" if price > 0.0 else "REVIEW_REQUIRED"
        basis = {"status": "NOT_REQUIRED", "reason": "non_buy_order"}
    notional = round(qty * price, 2)
    authority = {
        "authority_type": "ORDER_CONDITION_DERIVED_RESERVATION_PRICE_AUTHORITY",
        "authority_status": authority_status,
        "reservation_price_type": price_type,
        "source_authority": source_authority,
        "source_field": source_field,
        "future_execution_price_used": False,
        "target_day_ohlc_used": False,
        "arbitrary_percentage_buffer_used": False,
        "runtime_path": "Production/Demo/Historical common runtime_v2",
        "production_broker_cash_semantics": "MARKET_BUY_USES_STOP_HIGH_PRICE_LIMIT_FOR_BUYING_POWER",
        "jpx_price_limit_table": "regular_domestic_stock_price_limit_width",
        "basis": basis,
    }
    if reference_price_authority:
        authority["reference_price_authority"] = dict(reference_price_authority)
    return {
        "reservation_price": price,
        "reservation_price_type": price_type,
        "reserved_notional": notional,
        "reservation_price_authority": authority,
        "reservation_reason": _reservation_reason(side=side_text, order_type=order_type_text, status=authority_status),
    }


def _reservation_reason(*, side: str, order_type: str, status: str) -> str:
    if side == "BUY" and order_type == "MARKET" and status == "PASS":
        return "market BUY cash reservation uses production stop-high price-limit buying-power authority"
    if side == "BUY" and order_type == "MARKET":
        return "market BUY stop-high reservation authority unresolved; reference fallback marked review-required"
    if side == "BUY" and order_type == "LIMIT":
        return "limit BUY cash reservation uses limit price authority"
    return "non-BUY notional is observability and does not pre-credit SELL proceeds"


def _previous_close_basis(*, runtime_root: Path, business_date: str, symbol: str) -> dict[str, Any]:
    source_path = runtime_root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    if not source_path.is_file():
        return {"status": "MISSING", "reason": "normalized_ohlcv_missing", "source_path": str(source_path)}
    try:
        import pandas as pd

        frame = pd.read_parquet(source_path, columns=None)
    except Exception as exc:  # pragma: no cover - parquet engines vary
        return {"status": "READ_ERROR", "reason": str(exc), "source_path": str(source_path)}
    code_col = _first_column(frame, ("Code", "code", "symbol", "LocalCode"))
    date_col = _first_column(frame, ("Date", "date", "target_date", "business_date"))
    close_col = _first_column(frame, ("Close", "close", "AdjC", "AdjustmentClose", "adjustment_close", "C"))
    if not code_col or not date_col or not close_col:
        return {"status": "SCHEMA_MISSING", "reason": "required_ohlcv_columns_missing", "source_path": str(source_path)}
    symbol_text = str(symbol).strip().removesuffix(".T")
    codes = frame[code_col].astype(str).str.replace(r"\.T$", "", regex=True)
    rows = frame[(codes == symbol_text) & (frame[date_col].astype(str) < business_date)]
    if rows.empty:
        return {"status": "MISSING", "reason": "previous_close_missing", "source_path": str(source_path)}
    rows = rows.sort_values(date_col)
    row = rows.iloc[-1]
    try:
        base_price = float(row[close_col])
    except (TypeError, ValueError):
        base_price = 0.0
    if base_price <= 0.0:
        return {"status": "REVIEW_REQUIRED", "reason": "previous_close_invalid", "source_path": str(source_path)}
    return {
        "status": "PASS",
        "reason": "previous_close_before_target_session_resolved",
        "source_path": str(source_path),
        "symbol": symbol_text,
        "business_date": business_date,
        "basis_date": str(row[date_col]),
        "base_price": base_price,
        "price_limit_width": jpx_regular_price_limit_width(base_price),
    }


def _first_column(frame: Any, candidates: tuple[str, ...]) -> str:
    columns = {str(column): str(column) for column in getattr(frame, "columns", [])}
    for candidate in candidates:
        if candidate in columns:
            return columns[candidate]
    return ""
