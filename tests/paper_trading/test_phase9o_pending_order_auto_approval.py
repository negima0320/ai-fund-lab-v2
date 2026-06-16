from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.paper_trading.first_daily_run import FIRST_RUN_PENDING_ORDERS_CREATED, run_first_daily_paper_trading_run
from ai_fund_lab_v2.paper_trading.initial_ledger import create_initial_ledger
from ai_fund_lab_v2.paper_trading.ledger import load_ledger
from tests.paper_trading.test_phase9l2_daily_inference_runner import _write_l2_inputs


def test_auto_approval_creates_pending_orders_without_changing_cash_positions_or_pnl(tmp_path: Path) -> None:
    feature_root, quotes_path = _write_l2_inputs(tmp_path)
    ledger_result = create_initial_ledger(
        initial_cash=Decimal("1000000"),
        currency="JPY",
        ledger_root=tmp_path / ".runtime" / "phase9" / "ledger",
        start_date="2026-06-16",
    )
    before = load_ledger(ledger_result.latest_path)

    result = run_first_daily_paper_trading_run(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        ledger_path=ledger_result.latest_path,
        mode="paper-trading",
        approval_mode="auto_for_paper_trading",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        feature_root=feature_root,
        canonical_quotes_path=quotes_path,
    )
    after = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert result.status == FIRST_RUN_PENDING_ORDERS_CREATED
    assert result.review_status == "auto_approved_for_paper_trading"
    assert result.pending_order_created is True
    assert result.pending_order_count > 0
    assert Path(result.auto_approval_json_path).is_file()
    assert after.cash == before.cash
    assert after.positions == before.positions
    assert after.performance.realized_pnl == before.performance.realized_pnl
    assert after.performance.unrealized_pnl == before.performance.unrealized_pnl
    assert after.performance.trade_count == before.performance.trade_count
    assert len(after.pending_orders) == result.pending_order_count
    assert result.prohibited_flags["virtual_fill_executed"] is False
    assert result.prohibited_flags["broker_order_api_called"] is False


def test_review_only_still_does_not_mutate_ledger(tmp_path: Path) -> None:
    feature_root, quotes_path = _write_l2_inputs(tmp_path)
    ledger_result = create_initial_ledger(
        initial_cash=Decimal("1000000"),
        currency="JPY",
        ledger_root=tmp_path / ".runtime" / "phase9" / "ledger",
        start_date="2026-06-16",
    )

    result = run_first_daily_paper_trading_run(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        ledger_path=ledger_result.latest_path,
        mode="review-only",
        approval_mode="auto_for_paper_trading",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        feature_root=feature_root,
        canonical_quotes_path=quotes_path,
    )
    after = load_ledger(ledger_result.latest_path)

    assert result.pending_order_created is False
    assert result.ledger_changed is False
    assert len(after.pending_orders) == 0

