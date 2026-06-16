from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PerformanceSnapshot, PositionSnapshot, load_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.ledger_valuation import LEDGER_VALUATION_UPDATED, update_ledger_valuation_from_files


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


def _write_ledger(tmp_path: Path) -> Path:
    ledger = PaperTradingLedger(
        cash=Decimal("283330.0"),
        positions=(
            PositionSnapshot(code="15790", quantity=Decimal("200"), average_cost=Decimal("846.8"), market_value=Decimal("169360.0")),
            PositionSnapshot(code="166A0", quantity=Decimal("100"), average_cost=Decimal("1091.0"), market_value=Decimal("109100.0")),
            PositionSnapshot(code="213A0", quantity=Decimal("300"), average_cost=Decimal("544.7"), market_value=Decimal("163410.0")),
            PositionSnapshot(code="221A0", quantity=Decimal("100"), average_cost=Decimal("1538.0"), market_value=Decimal("153800.0")),
            PositionSnapshot(code="30630", quantity=Decimal("100"), average_cost=Decimal("1210.0"), market_value=Decimal("121000.0")),
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
