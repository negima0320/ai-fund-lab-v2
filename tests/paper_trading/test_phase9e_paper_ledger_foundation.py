from decimal import Decimal
from pathlib import Path

import pytest

from ai_fund_lab_v2.paper_trading.daily_run_result import DailyRunResult
from ai_fund_lab_v2.paper_trading.ledger import (
    PaperTradingLedger,
    PendingOrderState,
    PositionSnapshot,
    load_latest_ledger,
    load_ledger,
    write_ledger,
)
from ai_fund_lab_v2.paper_trading.ledger_integration import apply_ledger_to_daily_result
from ai_fund_lab_v2.paper_trading.reporting.internal_daily_report_writer import write_internal_daily_report
from ai_fund_lab_v2.paper_trading.reporting.public_daily_report_writer import write_public_daily_report
from ai_fund_lab_v2.paper_trading.run_manifest import DailyRunManifest


def test_paper_ledger_save_restore_and_latest(tmp_path: Path) -> None:
    ledger = _ledger()
    path = write_ledger(ledger, tmp_path / ".runtime")
    restored = load_ledger(path)
    latest = load_latest_ledger(tmp_path / ".runtime")

    assert path.exists()
    assert restored.metadata.ledger_id == ledger.metadata.ledger_id
    assert latest is not None
    assert latest.cash == Decimal("750000")
    assert latest.performance.total_equity == Decimal("1030000")


def test_pending_order_status_validation() -> None:
    with pytest.raises(ValueError, match="Unsupported pending order status"):
        PendingOrderState(code="7203", side="BUY", quantity=Decimal("100"), status="FILLED")


def test_ledger_reflects_daily_run_result_and_reports(tmp_path: Path) -> None:
    result = apply_ledger_to_daily_result(DailyRunResult(), _ledger())
    manifest = _manifest()
    internal_md, internal_json = write_internal_daily_report(manifest=manifest, result=result, reports_dir=tmp_path / "internal")
    public_md = write_public_daily_report(manifest=manifest, result=result, reports_dir=tmp_path / "public")

    assert result.current_cash == Decimal("750000")
    assert result.current_positions[0].issue_code == "7203"
    assert result.pending_orders[0]["status"] == "PENDING"
    internal_text = internal_md.read_text(encoding="utf-8")
    assert "Portfolio Summary" in internal_text
    assert "Pending Orders" in internal_text
    assert "7203 Toyota Motor" in internal_text
    assert internal_json.exists()
    public_text = public_md.read_text(encoding="utf-8")
    assert "仮想資産: 1030000" in public_text
    assert "保有銘柄数: 1" in public_text
    assert "現金比率: 72.82%" in public_text


def _ledger() -> PaperTradingLedger:
    return PaperTradingLedger(
        cash=Decimal("750000"),
        positions=(
            PositionSnapshot(
                code="7203",
                name="Toyota Motor",
                quantity=Decimal("100"),
                average_cost=Decimal("2500"),
                market_value=Decimal("280000"),
                unrealized_pnl=Decimal("30000"),
                holding_days=5,
            ),
        ),
        pending_orders=(PendingOrderState(code="6758", side="SELL", quantity=Decimal("100"), status="PENDING"),),
    )


def _manifest() -> DailyRunManifest:
    return DailyRunManifest(
        run_date="2026-06-16",
        data_until="2026-06-16",
        train_until="2026-06-16",
        decision_for="2026-06-16",
        virtual_order_date="2026-06-17",
        virtual_execution_date="2026-06-17",
        safety_status="OK",
        human_review_status="pending",
        report_status="OK",
    )

