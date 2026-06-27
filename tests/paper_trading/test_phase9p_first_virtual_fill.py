from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.first_virtual_fill import (
    DATA_NOT_READY,
    FIRST_VIRTUAL_FILL_DRY_RUN,
    FIRST_VIRTUAL_FILL_EXECUTED,
    run_first_virtual_fill,
)
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, load_ledger, write_ledger


def test_missing_execution_date_quotes_returns_data_not_ready_and_keeps_ledger(tmp_path: Path) -> None:
    ledger_path = _write_pending_ledger(tmp_path)
    quotes_path = _write_quotes(tmp_path, date="2026-06-15")
    before = Path(ledger_path).read_text(encoding="utf-8")

    result = run_first_virtual_fill(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        execution_date="2026-06-16",
        mode="execute",
        runtime_dir=tmp_path / ".runtime",
        docs_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
        public_summary_path=tmp_path / "public_summary.md",
    )

    assert result.status == DATA_NOT_READY
    assert "execution_date_quotes_missing" in result.blocked_reasons
    assert result.ledger_latest_updated is False
    assert Path(ledger_path).read_text(encoding="utf-8") == before


def test_dry_run_writes_candidate_outputs_without_latest_update(tmp_path: Path) -> None:
    ledger_path = _write_pending_ledger(tmp_path)
    quotes_path = _write_quotes(tmp_path)
    before = Path(ledger_path).read_text(encoding="utf-8")

    result = run_first_virtual_fill(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        execution_date="2026-06-16",
        mode="dry-run",
        runtime_dir=tmp_path / ".runtime",
        docs_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
        public_summary_path=tmp_path / "public_summary.md",
    )

    assert result.status == FIRST_VIRTUAL_FILL_DRY_RUN
    assert result.filled_order_count == 1
    assert result.ledger_latest_updated is False
    assert Path(result.execution_record_path).is_file()
    assert Path(ledger_path).read_text(encoding="utf-8") == before


def test_execute_fill_updates_latest_ledger_cash_position_and_records_execution(tmp_path: Path) -> None:
    ledger_path = _write_pending_ledger(tmp_path)
    quotes_path = _write_quotes(tmp_path)

    result = run_first_virtual_fill(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        execution_date="2026-06-16",
        mode="execute",
        runtime_dir=tmp_path / ".runtime",
        docs_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
        public_summary_path=tmp_path / "public_summary.md",
    )
    latest = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert result.status == FIRST_VIRTUAL_FILL_EXECUTED
    assert result.ledger_latest_updated is True
    assert result.filled_order_count == 1
    assert latest.cash == Decimal("900000")
    assert len(latest.positions) == 1
    assert latest.positions[0].code == "10010"
    assert latest.positions[0].quantity == Decimal("100")
    assert latest.positions[0].average_cost == Decimal("1000.0")
    assert len(latest.pending_orders) == 0
    assert Path(result.execution_record_path).is_file()
    assert result.prohibited_flags["broker_order_api_called"] is False
    assert result.prohibited_flags["open_d_started"] is False
    assert result.prohibited_flags["unlock_trade_called"] is False


def test_no_fill_reason_preserved_when_order_code_has_no_open_price(tmp_path: Path) -> None:
    ledger = PaperTradingLedger(
        cash=Decimal("1000000"),
        pending_orders=(PendingOrderState(code="99990", side="BUY", quantity=Decimal("100"), status="APPROVED"),),
    )
    ledger_path = write_ledger(ledger, runtime_dir=tmp_path / ".runtime")
    quotes_path = _write_quotes(tmp_path)

    result = run_first_virtual_fill(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        execution_date="2026-06-16",
        mode="execute",
        runtime_dir=tmp_path / ".runtime",
        docs_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
        public_summary_path=tmp_path / "public_summary.md",
    )
    latest = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert result.status == FIRST_VIRTUAL_FILL_EXECUTED
    assert result.filled_order_count == 0
    assert result.no_fill_order_count == 1
    assert latest.cash == Decimal("1000000")
    assert latest.pending_orders[0].no_fill_reason == "DAILY_QUOTE_MISSING"


def _write_pending_ledger(tmp_path: Path) -> Path:
    ledger = PaperTradingLedger(
        cash=Decimal("1000000"),
        pending_orders=(PendingOrderState(code="10010", side="BUY", quantity=Decimal("100"), status="APPROVED"),),
    )
    return write_ledger(ledger, runtime_dir=tmp_path / ".runtime")


def _write_quotes(tmp_path: Path, *, date: str = "2026-06-16") -> Path:
    path = tmp_path / "quotes.parquet"
    pd.DataFrame(
        [
            {"date": date, "code": "10010", "open": 1000.0, "high": 1010.0, "low": 990.0, "close": 1005.0, "volume": 1000},
        ]
    ).to_parquet(path, index=False)
    return path
