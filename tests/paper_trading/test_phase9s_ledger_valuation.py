from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PerformanceSnapshot, PositionSnapshot, load_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.ledger_valuation import LEDGER_VALUATION_STALE_SOURCE, LEDGER_VALUATION_UPDATED, update_ledger_valuation_from_files


def test_phase9s_ledger_valuation_updates_close_price_values(tmp_path: Path) -> None:
    ledger_path = _write_ledger(tmp_path)
    quotes_path = _write_quotes(tmp_path)

    result = update_ledger_valuation_from_files(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        valuation_date="2026-06-16",
        runtime_dir=tmp_path / ".runtime",
    )
    latest = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert result.status == LEDGER_VALUATION_UPDATED
    assert result.ledger_latest_updated is True
    assert latest.cash == Decimal("283330.0")
    assert latest.performance.market_value == Decimal("709810.0")
    assert latest.performance.total_equity == Decimal("993140.0")
    assert latest.performance.unrealized_pnl == Decimal("-6860.0")
    assert latest.performance.trade_count == 5
    assert latest.positions[0].holding_days == 1
    assert latest.positions[0].last_valuation_date == "2026-06-16"
    assert Path(result.valuation_manifest_path).is_file()


def test_phase9s_missing_price_keeps_previous_position_value(tmp_path: Path) -> None:
    ledger_path = _write_ledger(tmp_path)
    path = tmp_path / "quotes.parquet"
    pd.DataFrame([{"date": "2026-06-16", "code": "15790", "close": 845.8}]).to_parquet(path, index=False)

    result = update_ledger_valuation_from_files(
        ledger_path=ledger_path,
        quotes_path=path,
        valuation_date="2026-06-16",
        runtime_dir=tmp_path / ".runtime",
    )

    assert "166A0" in result.missing_price_codes
    assert any("missing_close_price:166A0" == warning for warning in result.warnings)


def test_phase9s_stale_quote_source_does_not_update_latest_ledger(tmp_path: Path) -> None:
    ledger_path = _write_ledger(tmp_path)
    before = Path(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json").read_text(encoding="utf-8")
    quotes_path = _write_quotes(tmp_path)

    result = update_ledger_valuation_from_files(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        valuation_date="2026-06-16",
        run_date="2026-06-17",
        expected_valuation_date="2026-06-17",
        runtime_dir=tmp_path / ".runtime",
    )
    after = Path(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json").read_text(encoding="utf-8")

    assert result.status == LEDGER_VALUATION_STALE_SOURCE
    assert result.ledger_latest_updated is False
    assert result.stale_price_source is True
    assert result.quote_source_max_date == "2026-06-16"
    assert "valuation_date_stale:2026-06-16<expected:2026-06-17" in result.blocked_reasons
    assert before == after


def test_phase9s_same_valuation_date_does_not_increment_holding_days(tmp_path: Path) -> None:
    ledger_path = _write_ledger(tmp_path, holding_days=3, last_valuation_date="2026-06-16")
    quotes_path = _write_quotes(tmp_path)

    result = update_ledger_valuation_from_files(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        valuation_date="2026-06-16",
        runtime_dir=tmp_path / ".runtime",
    )
    latest = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert result.status == LEDGER_VALUATION_UPDATED
    assert latest.positions[0].holding_days == 3
    assert latest.positions[0].last_valuation_date == "2026-06-16"


def test_phase9s_valuation_output_path_is_unique_per_run(tmp_path: Path) -> None:
    ledger_path = _write_ledger(tmp_path)
    quotes_path = _write_quotes(tmp_path)

    first = update_ledger_valuation_from_files(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        valuation_date="2026-06-16",
        runtime_dir=tmp_path / ".runtime",
    )
    second = update_ledger_valuation_from_files(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        valuation_date="2026-06-16",
        runtime_dir=tmp_path / ".runtime",
    )

    assert first.valuation_manifest_path != second.valuation_manifest_path
    assert "run_date=2026-06-16" in first.valuation_manifest_path
    assert Path(first.valuation_manifest_path).is_file()
    assert Path(second.valuation_manifest_path).is_file()


def _write_ledger(tmp_path: Path, *, holding_days: int = 0, last_valuation_date: str = "") -> Path:
    ledger = PaperTradingLedger(
        cash=Decimal("283330.0"),
        positions=(
            PositionSnapshot(code="15790", quantity=Decimal("200"), average_cost=Decimal("846.8"), market_value=Decimal("169360.0"), holding_days=holding_days, last_valuation_date=last_valuation_date),
            PositionSnapshot(code="166A0", quantity=Decimal("100"), average_cost=Decimal("1091.0"), market_value=Decimal("109100.0"), holding_days=holding_days, last_valuation_date=last_valuation_date),
            PositionSnapshot(code="213A0", quantity=Decimal("300"), average_cost=Decimal("544.7"), market_value=Decimal("163410.0"), holding_days=holding_days, last_valuation_date=last_valuation_date),
            PositionSnapshot(code="221A0", quantity=Decimal("100"), average_cost=Decimal("1538.0"), market_value=Decimal("153800.0"), holding_days=holding_days, last_valuation_date=last_valuation_date),
            PositionSnapshot(code="30630", quantity=Decimal("100"), average_cost=Decimal("1210.0"), market_value=Decimal("121000.0"), holding_days=holding_days, last_valuation_date=last_valuation_date),
        ),
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


def _write_quotes(tmp_path: Path) -> Path:
    path = tmp_path / "quotes.parquet"
    pd.DataFrame(
        [
            {"date": "2026-06-16", "code": "15790", "close": 845.8},
            {"date": "2026-06-16", "code": "166A0", "close": 1112.0},
            {"date": "2026-06-16", "code": "213A0", "close": 542.5},
            {"date": "2026-06-16", "code": "221A0", "close": 1530.0},
            {"date": "2026-06-16", "code": "30630", "close": 1137.0},
        ]
    ).to_parquet(path, index=False)
    return path
