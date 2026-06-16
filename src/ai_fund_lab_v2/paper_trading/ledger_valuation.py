from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.paper_trading.ledger import (
    LedgerMetadata,
    PaperTradingLedger,
    PerformanceSnapshot,
    PositionSnapshot,
    load_ledger,
    write_ledger,
)


LEDGER_VALUATION_UPDATED = "LEDGER_VALUATION_UPDATED"
LEDGER_VALUATION_DRY_RUN = "LEDGER_VALUATION_DRY_RUN"
LEDGER_VALUATION_BLOCKED = "LEDGER_VALUATION_BLOCKED"


@dataclass(frozen=True)
class LedgerValuationResult:
    status: str
    valuation_date: str
    ledger_latest_updated: bool
    ledger_before_path: str
    ledger_after_path: str
    valuation_diff_path: str
    valuation_manifest_path: str
    cash_before: str
    cash_after: str
    market_value_before: str
    market_value_after: str
    total_equity_before: str
    total_equity_after: str
    unrealized_pnl_before: str
    unrealized_pnl_after: str
    position_count: int
    missing_price_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    broker_order_api_called: bool = False
    open_d_started: bool = False
    unlock_trade_called: bool = False
    virtual_fill_executed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["missing_price_codes"] = list(self.missing_price_codes)
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        return payload


def update_ledger_valuation_from_files(
    *,
    ledger_path: Path | str,
    quotes_path: Path | str,
    valuation_date: str,
    runtime_dir: Path | str = ".runtime",
    dry_run: bool = False,
) -> LedgerValuationResult:
    ledger = load_ledger(ledger_path)
    try:
        quote_rows = _read_close_rows(Path(quotes_path), valuation_date)
    except Exception as exc:
        return _blocked_result(
            ledger=ledger,
            valuation_date=valuation_date,
            runtime_dir=runtime_dir,
            reason=f"quotes_unreadable:{type(exc).__name__}",
        )
    return update_ledger_valuation(
        ledger=ledger,
        quote_rows=quote_rows,
        valuation_date=valuation_date,
        runtime_dir=runtime_dir,
        dry_run=dry_run,
    )


def update_ledger_valuation(
    *,
    ledger: PaperTradingLedger,
    quote_rows: list[dict[str, Any]],
    valuation_date: str,
    runtime_dir: Path | str = ".runtime",
    dry_run: bool = False,
) -> LedgerValuationResult:
    if not ledger.positions:
        ledger_after = _ledger_with_positions(ledger, positions=())
        return _write_valuation_outputs(
            ledger_before=ledger,
            ledger_after=ledger_after,
            valuation_date=valuation_date,
            runtime_dir=runtime_dir,
            dry_run=dry_run,
            missing_price_codes=(),
            warnings=("no_positions_to_value",),
            blocked_reasons=(),
        )
    close_prices = _close_price_map(quote_rows, valuation_date)
    positions: list[PositionSnapshot] = []
    missing: list[str] = []
    for position in ledger.positions:
        close = close_prices.get(position.code)
        if close is None:
            missing.append(position.code)
            positions.append(position)
            continue
        market_value = close * position.quantity
        positions.append(
            PositionSnapshot(
                code=position.code,
                name=position.name,
                quantity=position.quantity,
                average_cost=position.average_cost,
                market_value=market_value,
                unrealized_pnl=(close - position.average_cost) * position.quantity,
                holding_days=position.holding_days + 1,
            )
        )
    warnings = tuple(f"missing_close_price:{code}" for code in missing)
    ledger_after = _ledger_with_positions(ledger, positions=tuple(positions))
    return _write_valuation_outputs(
        ledger_before=ledger,
        ledger_after=ledger_after,
        valuation_date=valuation_date,
        runtime_dir=runtime_dir,
        dry_run=dry_run,
        missing_price_codes=tuple(missing),
        warnings=warnings,
        blocked_reasons=(),
    )


def _ledger_with_positions(ledger: PaperTradingLedger, *, positions: tuple[PositionSnapshot, ...]) -> PaperTradingLedger:
    realized = ledger.performance.realized_pnl if ledger.performance else Decimal("0")
    trade_count = ledger.performance.trade_count if ledger.performance else 0
    market_value = sum((position.market_value for position in positions), Decimal("0"))
    unrealized = sum((position.unrealized_pnl for position in positions), Decimal("0"))
    return PaperTradingLedger(
        cash=ledger.cash,
        positions=positions,
        pending_orders=ledger.pending_orders,
        performance=PerformanceSnapshot(
            total_equity=ledger.cash + market_value,
            cash=ledger.cash,
            market_value=market_value,
            realized_pnl=realized,
            unrealized_pnl=unrealized,
            trade_count=trade_count,
        ),
        metadata=LedgerMetadata(
            ledger_id=ledger.metadata.ledger_id,
            as_of=utc_now_iso(),
            schema_version=ledger.metadata.schema_version,
            source=ledger.metadata.source,
            phase=ledger.metadata.phase,
            created_at=ledger.metadata.created_at,
            start_date=ledger.metadata.start_date,
            currency=ledger.metadata.currency,
            initial_cash=ledger.metadata.initial_cash,
            broker_order_api_called=False,
            open_d_started=False,
            unlock_trade_called=False,
            virtual_fill_executed=ledger.metadata.virtual_fill_executed,
        ),
    )


def _write_valuation_outputs(
    *,
    ledger_before: PaperTradingLedger,
    ledger_after: PaperTradingLedger,
    valuation_date: str,
    runtime_dir: Path | str,
    dry_run: bool,
    missing_price_codes: tuple[str, ...],
    warnings: tuple[str, ...],
    blocked_reasons: tuple[str, ...],
) -> LedgerValuationResult:
    output_dir = Path(runtime_dir) / "phase9" / "ledger_valuations" / valuation_date
    output_dir.mkdir(parents=True, exist_ok=True)
    before_path = output_dir / "ledger_before.json"
    after_path = output_dir / "ledger_after_valuation.json"
    diff_path = output_dir / "valuation_diff.json"
    manifest_path = output_dir / "valuation_manifest.json"
    before_path.write_text(json.dumps(ledger_before.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    after_path.write_text(json.dumps(ledger_after.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    diff = _valuation_diff(ledger_before, ledger_after)
    diff_path.write_text(json.dumps(diff, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "valuation_date": valuation_date,
        "status": LEDGER_VALUATION_DRY_RUN if dry_run else LEDGER_VALUATION_UPDATED,
        "ledger_latest_updated": not dry_run and not blocked_reasons,
        "ledger_before_path": str(before_path),
        "ledger_after_path": str(after_path),
        "valuation_diff_path": str(diff_path),
        "missing_price_codes": list(missing_price_codes),
        "warnings": list(warnings),
        "blocked_reasons": list(blocked_reasons),
        "broker_order_api_called": False,
        "open_d_started": False,
        "unlock_trade_called": False,
        "virtual_fill_executed": False,
        "created_at": utc_now_iso(),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    updated = False
    status = LEDGER_VALUATION_DRY_RUN if dry_run else LEDGER_VALUATION_UPDATED
    if blocked_reasons:
        status = LEDGER_VALUATION_BLOCKED
    elif not dry_run:
        write_ledger(ledger_after, runtime_dir=runtime_dir)
        updated = True
    return LedgerValuationResult(
        status=status,
        valuation_date=valuation_date,
        ledger_latest_updated=updated,
        ledger_before_path=str(before_path),
        ledger_after_path=str(after_path),
        valuation_diff_path=str(diff_path),
        valuation_manifest_path=str(manifest_path),
        cash_before=str(ledger_before.cash),
        cash_after=str(ledger_after.cash),
        market_value_before=str(ledger_before.performance.market_value),
        market_value_after=str(ledger_after.performance.market_value),
        total_equity_before=str(ledger_before.performance.total_equity),
        total_equity_after=str(ledger_after.performance.total_equity),
        unrealized_pnl_before=str(ledger_before.performance.unrealized_pnl),
        unrealized_pnl_after=str(ledger_after.performance.unrealized_pnl),
        position_count=len(ledger_after.positions),
        missing_price_codes=missing_price_codes,
        warnings=warnings,
        blocked_reasons=blocked_reasons,
    )


def _blocked_result(*, ledger: PaperTradingLedger, valuation_date: str, runtime_dir: Path | str, reason: str) -> LedgerValuationResult:
    return _write_valuation_outputs(
        ledger_before=ledger,
        ledger_after=ledger,
        valuation_date=valuation_date,
        runtime_dir=runtime_dir,
        dry_run=True,
        missing_price_codes=(),
        warnings=(),
        blocked_reasons=(reason,),
    )


def _valuation_diff(before: PaperTradingLedger, after: PaperTradingLedger) -> dict[str, str]:
    return {
        "cash_change": str(after.cash - before.cash),
        "market_value_change": str(after.performance.market_value - before.performance.market_value),
        "total_equity_change": str(after.performance.total_equity - before.performance.total_equity),
        "unrealized_pnl_change": str(after.performance.unrealized_pnl - before.performance.unrealized_pnl),
        "realized_pnl_change": str(after.performance.realized_pnl - before.performance.realized_pnl),
        "position_count_before": str(len(before.positions)),
        "position_count_after": str(len(after.positions)),
        "pending_order_count_before": str(len(before.pending_orders)),
        "pending_order_count_after": str(len(after.pending_orders)),
    }


def _read_close_rows(path: Path, valuation_date: str) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".parquet":
        frame = pd.read_parquet(path)
    elif path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        frame = pd.DataFrame(payload.get("rows") if isinstance(payload, dict) else payload)
    date_col = "date" if "date" in frame.columns else "Date"
    return frame[frame[date_col].astype(str) == valuation_date].to_dict(orient="records")


def _close_price_map(rows: list[dict[str, Any]], valuation_date: str) -> dict[str, Decimal]:
    prices: dict[str, Decimal] = {}
    for row in rows:
        row_date = str(row.get("date") or row.get("Date") or row.get("target_date") or "")
        if row_date != valuation_date:
            continue
        code = str(row.get("code") or row.get("Code") or row.get("LocalCode") or "")
        close_value = row.get("close", row.get("Close"))
        if code and close_value not in (None, ""):
            close = Decimal(str(close_value))
            if close.is_finite() and close > 0:
                prices[code] = close
    return prices
