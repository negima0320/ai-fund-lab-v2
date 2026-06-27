from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.first_virtual_fill import FIRST_VIRTUAL_FILL_DRY_RUN, FIRST_VIRTUAL_FILL_EXECUTED, run_first_virtual_fill
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, load_ledger, write_ledger


def test_phase9r_dry_run_no_latest_update(tmp_path: Path) -> None:
    ledger_path = _write_phase9r_ledger(tmp_path)
    quotes_path = _write_phase9r_quotes(tmp_path)
    before = Path(ledger_path).read_text(encoding="utf-8")

    result = run_first_virtual_fill(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        execution_date="2026-06-16",
        mode="dry-run",
        runtime_dir=tmp_path / ".runtime",
        docs_report_path=tmp_path / "dry.md",
        json_report_path=tmp_path / "dry.json",
        public_summary_path=tmp_path / "dry_public.md",
    )

    assert result.status == FIRST_VIRTUAL_FILL_DRY_RUN
    assert result.filled_order_count == 5
    assert result.ledger_latest_updated is False
    assert Path(ledger_path).read_text(encoding="utf-8") == before


def test_phase9r_execute_fills_pending_orders_and_updates_ledger(tmp_path: Path) -> None:
    ledger_path = _write_phase9r_ledger(tmp_path)
    quotes_path = _write_phase9r_quotes(tmp_path)

    result = run_first_virtual_fill(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        execution_date="2026-06-16",
        mode="execute",
        runtime_dir=tmp_path / ".runtime",
        docs_report_path=tmp_path / "execute.md",
        json_report_path=tmp_path / "execute.json",
        public_summary_path=tmp_path / "execute_public.md",
    )
    latest = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert result.status == FIRST_VIRTUAL_FILL_EXECUTED
    assert result.filled_order_count == 5
    assert result.no_fill_order_count == 0
    assert latest.cash == Decimal("283330.0")
    assert len(latest.positions) == 5
    assert len(latest.pending_orders) == 0
    assert latest.performance.trade_count == 5
    assert latest.performance.realized_pnl == Decimal("0")
    assert latest.performance.unrealized_pnl == Decimal("0.0")
    assert {position.code: position.average_cost for position in latest.positions} == {
        "15790": Decimal("846.8"),
        "166A0": Decimal("1091.0"),
        "213A0": Decimal("544.7"),
        "221A0": Decimal("1538.0"),
        "30630": Decimal("1210.0"),
    }
    assert Path(result.execution_record_path).is_file()
    assert Path(result.ledger_snapshot_dir, "ledger_before.json").is_file()
    assert Path(result.ledger_snapshot_dir, "ledger_after.json").is_file()
    assert Path(result.ledger_snapshot_dir, "ledger_diff.json").is_file()
    assert result.prohibited_flags["broker_order_api_called"] is False
    assert result.prohibited_flags["open_d_started"] is False
    assert result.prohibited_flags["unlock_trade_called"] is False


def test_phase9r_insufficient_cash_preserves_no_fill(tmp_path: Path) -> None:
    ledger = PaperTradingLedger(
        cash=Decimal("1000"),
        pending_orders=(PendingOrderState(code="15790", side="BUY", quantity=Decimal("200"), status="APPROVED"),),
    )
    ledger_path = write_ledger(ledger, runtime_dir=tmp_path / ".runtime")
    quotes_path = _write_phase9r_quotes(tmp_path)

    result = run_first_virtual_fill(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        execution_date="2026-06-16",
        mode="execute",
        runtime_dir=tmp_path / ".runtime",
        docs_report_path=tmp_path / "nofill.md",
        json_report_path=tmp_path / "nofill.json",
        public_summary_path=tmp_path / "nofill_public.md",
    )
    latest = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert result.filled_order_count == 0
    assert result.no_fill_order_count == 1
    assert latest.cash == Decimal("1000")
    assert len(latest.positions) == 0
    assert latest.pending_orders[0].no_fill_reason == "CASH_INSUFFICIENT"


def _write_phase9r_ledger(tmp_path: Path) -> Path:
    ledger = PaperTradingLedger(
        cash=Decimal("1000000"),
        pending_orders=(
            PendingOrderState(code="15790", side="BUY", quantity=Decimal("200"), status="APPROVED"),
            PendingOrderState(code="166A0", side="BUY", quantity=Decimal("100"), status="APPROVED"),
            PendingOrderState(code="213A0", side="BUY", quantity=Decimal("300"), status="APPROVED"),
            PendingOrderState(code="221A0", side="BUY", quantity=Decimal("100"), status="APPROVED"),
            PendingOrderState(code="30630", side="BUY", quantity=Decimal("100"), status="APPROVED"),
        ),
    )
    return write_ledger(ledger, runtime_dir=tmp_path / ".runtime")


def _write_phase9r_quotes(tmp_path: Path) -> Path:
    path = tmp_path / "quotes.parquet"
    pd.DataFrame(
        [
            {"date": "2026-06-16", "code": "15790", "open": 846.8},
            {"date": "2026-06-16", "code": "166A0", "open": 1091.0},
            {"date": "2026-06-16", "code": "213A0", "open": 544.7},
            {"date": "2026-06-16", "code": "221A0", "open": 1538.0},
            {"date": "2026-06-16", "code": "30630", "open": 1210.0},
        ]
    ).to_parquet(path, index=False)
    return path
