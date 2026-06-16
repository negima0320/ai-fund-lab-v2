from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.paper_trading.business_day_tracker import TRACKER_DUPLICATE_BLOCKED, TRACKER_UPDATED, update_business_day_tracker
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PerformanceSnapshot, PositionSnapshot, write_ledger


def test_phase9s_tracker_registers_day1_and_blocks_duplicate(tmp_path: Path) -> None:
    ledger_path = _write_filled_ledger(tmp_path)

    result = update_business_day_tracker(
        ledger_path=ledger_path,
        business_day_index=1,
        run_date="2026-06-16",
        decision_for="2026-06-15",
        status="FIRST_VIRTUAL_FILL_DONE",
        tracker_root=tmp_path / "tracker",
        report_root=tmp_path / "reports",
    )
    duplicate = update_business_day_tracker(
        ledger_path=ledger_path,
        business_day_index=1,
        run_date="2026-06-16",
        decision_for="2026-06-15",
        status="FIRST_VIRTUAL_FILL_DONE",
        tracker_root=tmp_path / "tracker",
        report_root=tmp_path / "reports",
    )

    assert result.status == TRACKER_UPDATED
    assert Path(result.tracker_json_path).is_file()
    assert Path(result.report_markdown_path).is_file()
    assert duplicate.status == TRACKER_DUPLICATE_BLOCKED
    assert duplicate.blocked_reasons == ("tracker_day_already_registered",)


def _write_filled_ledger(tmp_path: Path) -> Path:
    ledger = PaperTradingLedger(
        cash=Decimal("283330.0"),
        positions=(PositionSnapshot(code="15790", quantity=Decimal("200"), average_cost=Decimal("846.8"), market_value=Decimal("169360.0")),),
        performance=PerformanceSnapshot(
            total_equity=Decimal("1000000.0"),
            cash=Decimal("283330.0"),
            market_value=Decimal("716670.0"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            trade_count=5,
        ),
    )
    return write_ledger(ledger, runtime_dir=tmp_path / ".runtime")
