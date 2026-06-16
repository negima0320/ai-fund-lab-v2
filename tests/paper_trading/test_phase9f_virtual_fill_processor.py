from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, PositionSnapshot, load_latest_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.virtual_fill_processor import process_virtual_fills


def test_buy_100_shares_fills() -> None:
    ledger = PaperTradingLedger(cash=Decimal("300000"), pending_orders=(PendingOrderState(code="7203", side="BUY", quantity=Decimal("100"), status="APPROVED"),))
    result = process_virtual_fills(ledger=ledger, quote_rows=[_quote("7203", 2000)], execution_date="2026-06-17", dry_run=True)
    assert len(result.executions) == 1
    assert result.ledger_after.cash == Decimal("100000")
    assert result.ledger_after.positions[0].code == "7203"
    assert result.ledger_after.positions[0].average_cost == Decimal("2000")


def test_buy_cash_insufficient_no_fill() -> None:
    ledger = PaperTradingLedger(cash=Decimal("100000"), pending_orders=(PendingOrderState(code="7203", side="BUY", quantity=Decimal("100"), status="APPROVED"),))
    result = process_virtual_fills(ledger=ledger, quote_rows=[_quote("7203", 2000)], execution_date="2026-06-17", dry_run=True)
    assert result.no_fill_orders[0].no_fill_reason == "CASH_INSUFFICIENT"
    assert result.ledger_after.cash == Decimal("100000")


def test_buy_invalid_lot_no_fill() -> None:
    ledger = PaperTradingLedger(cash=Decimal("300000"), pending_orders=(PendingOrderState(code="7203", side="BUY", quantity=Decimal("50"), status="APPROVED"),))
    result = process_virtual_fills(ledger=ledger, quote_rows=[_quote("7203", 2000)], execution_date="2026-06-17", dry_run=True)
    assert result.no_fill_orders[0].no_fill_reason == "LOT_SIZE_INVALID"


def test_sell_fill_updates_cash_position_and_realized_pnl() -> None:
    ledger = PaperTradingLedger(
        cash=Decimal("100000"),
        positions=(PositionSnapshot(code="6758", quantity=Decimal("200"), average_cost=Decimal("1000"), market_value=Decimal("200000")),),
        pending_orders=(PendingOrderState(code="6758", side="SELL", quantity=Decimal("100"), status="APPROVED"),),
    )
    result = process_virtual_fills(ledger=ledger, quote_rows=[_quote("6758", 1200)], execution_date="2026-06-17", dry_run=True)
    assert result.ledger_after.cash == Decimal("220000")
    assert result.ledger_after.positions[0].quantity == Decimal("100")
    assert result.ledger_after.performance.realized_pnl == Decimal("20000")


def test_sell_quantity_insufficient_no_fill() -> None:
    ledger = PaperTradingLedger(
        cash=Decimal("100000"),
        positions=(PositionSnapshot(code="6758", quantity=Decimal("50"), average_cost=Decimal("1000"), market_value=Decimal("50000")),),
        pending_orders=(PendingOrderState(code="6758", side="SELL", quantity=Decimal("100"), status="APPROVED"),),
    )
    result = process_virtual_fills(ledger=ledger, quote_rows=[_quote("6758", 1200)], execution_date="2026-06-17", dry_run=True)
    assert result.no_fill_orders[0].no_fill_reason == "SELL_QUANTITY_INSUFFICIENT"


def test_average_cost_updates_for_additional_buy() -> None:
    ledger = PaperTradingLedger(
        cash=Decimal("500000"),
        positions=(PositionSnapshot(code="7203", quantity=Decimal("100"), average_cost=Decimal("1000"), market_value=Decimal("100000")),),
        pending_orders=(PendingOrderState(code="7203", side="BUY", quantity=Decimal("100"), status="APPROVED"),),
    )
    result = process_virtual_fills(ledger=ledger, quote_rows=[_quote("7203", 2000)], execution_date="2026-06-17", dry_run=True)
    assert result.ledger_after.positions[0].average_cost == Decimal("1500")


def test_open_price_missing_no_fill() -> None:
    ledger = PaperTradingLedger(cash=Decimal("300000"), pending_orders=(PendingOrderState(code="7203", side="BUY", quantity=Decimal("100"), status="APPROVED"),))
    result = process_virtual_fills(ledger=ledger, quote_rows=[{"Date": "2026-06-17", "Code": "7203"}], execution_date="2026-06-17", dry_run=True)
    assert result.no_fill_orders[0].no_fill_reason == "OPEN_PRICE_MISSING"


def test_dry_run_does_not_overwrite_latest(tmp_path: Path) -> None:
    runtime = tmp_path / ".runtime"
    ledger = PaperTradingLedger(cash=Decimal("300000"), pending_orders=(PendingOrderState(code="7203", side="BUY", quantity=Decimal("100"), status="APPROVED"),))
    path = write_ledger(ledger, runtime)
    result = process_virtual_fills(ledger=ledger, quote_rows=[_quote("7203", 2000)], execution_date="2026-06-17", runtime_dir=runtime, output_root=tmp_path / "out", dry_run=True)
    latest = load_latest_ledger(runtime)
    assert latest is not None
    assert latest.cash == Decimal("300000")
    assert Path(result.ledger_after_path).exists()
    assert path.exists()
    assert result.broker_order_api_called is False
    assert result.open_d_started is False
    assert result.unlock_trade_called is False


def _quote(code: str, open_price: int) -> dict[str, object]:
    return {"Date": "2026-06-17", "Code": code, "Open": open_price}

