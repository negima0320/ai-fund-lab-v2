from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.paper_trading.initial_ledger import INITIAL_LEDGER_BLOCKED, INITIAL_LEDGER_CREATED, create_initial_ledger
from ai_fund_lab_v2.paper_trading.ledger import load_ledger


def test_create_initial_ledger_writes_latest_json(tmp_path: Path) -> None:
    result = create_initial_ledger(
        initial_cash=Decimal("1000000"),
        currency="JPY",
        ledger_root=tmp_path / "ledger",
        start_date="2026-06-16",
    )

    latest = tmp_path / "ledger" / "latest.json"
    ledger = load_ledger(latest)
    assert result.status == INITIAL_LEDGER_CREATED
    assert latest.is_file()
    assert ledger.cash == Decimal("1000000")
    assert ledger.metadata.initial_cash == Decimal("1000000")
    assert ledger.metadata.currency == "JPY"
    assert ledger.metadata.start_date == "2026-06-16"
    assert ledger.positions == ()
    assert ledger.pending_orders == ()
    assert ledger.performance.total_equity == Decimal("1000000")
    assert ledger.performance.realized_pnl == Decimal("0")
    assert ledger.performance.unrealized_pnl == Decimal("0")
    assert ledger.performance.trade_count == 0
    assert not any(result.prohibited_flags.values())


def test_duplicate_create_is_blocked_without_overwrite(tmp_path: Path) -> None:
    root = tmp_path / "ledger"
    first = create_initial_ledger(initial_cash=Decimal("1000000"), currency="JPY", ledger_root=root, start_date="2026-06-16")
    second = create_initial_ledger(initial_cash=Decimal("1000000"), currency="JPY", ledger_root=root, start_date="2026-06-16")

    assert first.status == INITIAL_LEDGER_CREATED
    assert second.status == INITIAL_LEDGER_BLOCKED
    assert "latest_ledger_already_exists" in second.blocked_reasons


def test_overwrite_allowed_only_with_flag(tmp_path: Path) -> None:
    root = tmp_path / "ledger"
    create_initial_ledger(initial_cash=Decimal("1000000"), currency="JPY", ledger_root=root, start_date="2026-06-16")
    result = create_initial_ledger(
        initial_cash=Decimal("1000000"),
        currency="JPY",
        ledger_root=root,
        start_date="2026-06-16",
        overwrite=True,
    )

    assert result.status == INITIAL_LEDGER_CREATED
    assert (root / "latest.json").is_file()
    assert not any(result.prohibited_flags.values())

