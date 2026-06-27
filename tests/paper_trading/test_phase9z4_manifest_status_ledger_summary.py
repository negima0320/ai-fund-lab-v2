from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import scripts.run_aifundlab_daily_paper_trading as cli
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, PositionSnapshot
from ai_fund_lab_v2.paper_trading.unified_daily_runner import (
    BusinessDates,
    UNIFIED_DAILY_RUNNER_BLOCKED,
    UNIFIED_DAILY_RUNNER_COMPLETED,
    _write_manifest,
)
from ai_fund_lab_v2.paper_trading.virtual_fill_processor import process_virtual_fills


def test_success_run_manifest_status_is_written(tmp_path: Path) -> None:
    path = _write_unified_manifest(tmp_path, status=UNIFIED_DAILY_RUNNER_COMPLETED)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == UNIFIED_DAILY_RUNNER_COMPLETED


def test_block_run_manifest_status_is_written(tmp_path: Path) -> None:
    path = _write_unified_manifest(tmp_path, status=UNIFIED_DAILY_RUNNER_BLOCKED)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == UNIFIED_DAILY_RUNNER_BLOCKED


def test_non_business_day_skip_manifest_status_is_written(tmp_path: Path) -> None:
    result = cli.write_non_business_day_skip(
        mode="paper-trading",
        operation_root=tmp_path / "operation",
        runtime_dir=tmp_path / ".runtime",
        ledger_path=str(tmp_path / "ledger.json"),
        run_date="2026-06-20",
        calendar_status={"date": "2026-06-20", "is_business_day": False, "hol_div": "0", "reason": "JQUANTS_NON_BUSINESS_DAY"},
    )
    payload = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert payload["status"] == cli.NON_BUSINESS_DAY_SKIPPED


def test_trading_calendar_not_ready_manifest_status_is_written(tmp_path: Path) -> None:
    result = cli.write_trading_calendar_not_ready_block(
        mode="paper-trading",
        operation_root=tmp_path / "operation",
        runtime_dir=tmp_path / ".runtime",
        ledger_path=str(tmp_path / "ledger.json"),
        run_date="2026-06-22",
        calendar_status={"date": "2026-06-22", "is_business_day": False, "reason": "TRADING_CALENDAR_DATE_MISSING"},
    )
    payload = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert payload["status"] == cli.TRADING_CALENDAR_NOT_READY_BLOCKED


def test_virtual_fill_ledger_summary_metadata_is_serialized() -> None:
    ledger = PaperTradingLedger(
        cash=Decimal("300000"),
        pending_orders=(
            PendingOrderState(
                code="10010",
                side="BUY",
                quantity=Decimal("100"),
                status="APPROVED",
                virtual_execution_date="2026-06-22",
            ),
        ),
    )
    result = process_virtual_fills(
        ledger=ledger,
        quote_rows=[{"code": "10010", "date": "2026-06-22", "open": "1000"}],
        execution_date="2026-06-22",
        dry_run=True,
    )
    payload = result.ledger_after.to_dict()

    assert payload["trade_count"] == 1
    assert payload["realized_pnl"] == "0"
    assert payload["unrealized_pnl"] == "0"
    assert payload["total_equity"] == "300000"
    assert payload["positions_count"] == 1
    assert payload["pending_orders_count"] == 0
    assert payload["last_execution_date"] == "2026-06-22"
    assert payload["summary"]["trade_count"] == 1


def test_summary_serialization_does_not_change_positions_cash_or_pending_orders() -> None:
    ledger = PaperTradingLedger(
        cash=Decimal("123456"),
        positions=(PositionSnapshot(code="10010", quantity=Decimal("100"), average_cost=Decimal("1000"), market_value=Decimal("110000"), unrealized_pnl=Decimal("10000")),),
        pending_orders=(PendingOrderState(code="20020", side="BUY", quantity=Decimal("100"), status="APPROVED"),),
    )
    payload = ledger.to_dict()

    assert payload["cash"] == "123456"
    assert len(payload["positions"]) == 1
    assert payload["positions"][0]["code"] == "10010"
    assert len(payload["pending_orders"]) == 1
    assert payload["pending_orders"][0]["code"] == "20020"
    assert payload["positions_count"] == 1
    assert payload["pending_orders_count"] == 1


def _write_unified_manifest(tmp_path: Path, *, status: str) -> Path:
    return _write_manifest(
        run_id="run_test",
        run_date="2026-06-22",
        status=status,
        dates=BusinessDates(
            run_date="2026-06-22",
            business_date="2026-06-22",
            market_data_target_date="2026-06-22",
            data_target_date="2026-06-22",
            decision_for="2026-06-22",
            valuation_date="2026-06-22",
            latest_available_quote_date="2026-06-22",
            virtual_order_date="2026-06-23",
            virtual_execution_date="2026-06-23",
        ),
        mode="paper-trading",
        approval_mode="auto_for_paper_trading",
        step_statuses={},
        warnings=[],
        blocked=[],
        operation_root=tmp_path / "operation",
    )
