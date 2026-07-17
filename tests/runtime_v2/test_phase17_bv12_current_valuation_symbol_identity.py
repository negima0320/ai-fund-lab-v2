from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.current_state.temporal import CURRENT_TEMPORAL_SCHEMA_VERSION
from ai_fund_lab_v2.runtime_v2.current_state.valuation import run_current_valuation_refresh


BUSINESS_DATE = "2026-07-01"


def test_phase17_bv12_numeric_5_digit_symbol_valuation_uses_canonical_identity(tmp_path: Path) -> None:
    try:
        import pandas as pd
    except ImportError:
        return

    root = _runtime_root(tmp_path)
    _write_current(root, positions=[_position("36810", average_price=1000.0)])
    asof_view = _write_historical_asof_view(tmp_path, pd, {"36810": 1234.0})

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        market_evidence_path=asof_view,
        apply_current_valuation=True,
        now=_now(),
    )

    current = _read_json(root / "persistent_ledger" / "state.json")
    assert result.status == "READY"
    assert result.projection_status == "PASS"
    assert result.apply_status == "APPLIED"
    assert result.missing_symbols == ()
    assert result.valued_position_count == 1
    assert result.candidate_current["positions"][0]["symbol"] == "36810"
    assert current["positions"][0]["symbol"] == "36810"
    assert current["positions"][0]["current_price"] == 1234.0


def test_phase17_bv12_alpha_containing_5_digit_symbol_keeps_trailing_zero(tmp_path: Path) -> None:
    try:
        import pandas as pd
    except ImportError:
        return

    root = _runtime_root(tmp_path)
    _write_current(root, positions=[_position("186A0", average_price=700.0)])
    asof_view = _write_historical_asof_view(tmp_path, pd, {"186A0": 840.0})

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        market_evidence_path=asof_view,
        apply_current_valuation=True,
        now=_now(),
    )

    assert result.status == "READY"
    assert result.missing_symbols == ()
    assert result.candidate_current["positions"][0]["symbol"] == "186A0"
    assert result.candidate_current["positions"][0]["current_price"] == 840.0


def test_phase17_bv12_remaining_positions_after_full_sell_all_value_and_sold_symbol_absent(tmp_path: Path) -> None:
    try:
        import pandas as pd
    except ImportError:
        return

    root = _runtime_root(tmp_path)
    remaining = [
        _position("33500", quantity=100.0, average_price=900.0),
        _position("36810", quantity=100.0, average_price=1000.0),
        _position("186A0", quantity=100.0, average_price=700.0),
        _position("31340", quantity=100.0, average_price=500.0),
    ]
    _write_current(root, positions=remaining, cash=411300.0, realized_pnl=-10000.0)
    asof_view = _write_historical_asof_view(
        tmp_path,
        pd,
        {
            "33500": 930.0,
            "36810": 1010.0,
            "186A0": 710.0,
            "31340": 520.0,
            "70630": 3000.0,
        },
    )

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        market_evidence_path=asof_view,
        apply_current_valuation=True,
        now=_now(),
    )

    current = _read_json(root / "persistent_ledger" / "state.json")
    symbols = [position["symbol"] for position in current["positions"]]
    assert result.status == "READY"
    assert result.projection_status == "PASS"
    assert result.apply_status == "APPLIED"
    assert result.position_count == 4
    assert result.valued_position_count == 4
    assert result.missing_symbols == ()
    assert symbols == ["33500", "36810", "186A0", "31340"]
    assert "70630" not in symbols


def test_phase17_bv12_genuine_missing_quote_reports_canonical_runtime_symbol(tmp_path: Path) -> None:
    try:
        import pandas as pd
    except ImportError:
        return

    root = _runtime_root(tmp_path)
    _write_current(root, positions=[_position("36810", average_price=1000.0)])
    asof_view = _write_historical_asof_view(tmp_path, pd, {"33500": 930.0})

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        market_evidence_path=asof_view,
        apply_current_valuation=True,
        now=_now(),
    )

    current = _read_json(root / "persistent_ledger" / "state.json")
    assert result.status == "REVIEW_REQUIRED"
    assert result.projection_status == "REVIEW_REQUIRED"
    assert result.apply_status == "NOT_EXECUTED"
    assert result.missing_symbols == ("36810",)
    assert current["positions"][0]["symbol"] == "36810"
    assert current["valuation_as_of"] == "2026-06-30"


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_current(
    root: Path,
    *,
    positions: list[dict],
    cash: float = 900000.0,
    realized_pnl: float = 0.0,
) -> None:
    market_value = sum(float(position.get("market_value") or 0) for position in positions)
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
            "temporal_schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
            "business_date": "2026-06-30",
            "position_state_as_of": "2026-06-30",
            "valuation_as_of": "2026-06-30",
            "source_market_date": "2026-06-30",
            "last_execution_date": BUSINESS_DATE,
            "last_reconciled_at": "2026-07-01T06:30:00+00:00",
            "updated_at": "2026-07-01T06:30:00+00:00",
            "positions": positions,
            "cash": cash,
            "buying_power": cash,
            "market_value": market_value,
            "total_equity": cash + market_value,
            "realized_pnl": realized_pnl,
            "production_equivalent": True,
        },
    )


def _position(
    symbol: str,
    *,
    quantity: float = 100.0,
    average_price: float = 900.0,
    current_price: float = 900.0,
) -> dict:
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": average_price,
        "current_price": current_price,
        "market_value": quantity * current_price,
        "unrealized_pnl": (current_price - average_price) * quantity,
        "ownership": "runtime_owned",
        "source": "runtime_v2_runtime_owned_fill_projection",
        "position_state_source": "runtime_owned_execution_ledger",
    }


def _write_historical_asof_view(tmp_path: Path, pd: object, prices: dict[str, float]) -> Path:
    parquet = tmp_path / "normalized_ohlcv.parquet"
    pd.DataFrame(
        [{"Date": BUSINESS_DATE, "Code": symbol, "Close": price} for symbol, price in prices.items()]
    ).to_parquet(parquet, index=False)
    asof_view = tmp_path / "historical_asof_view.json"
    _write_json(
        asof_view,
        {
            "schema_version": "runtime_historical_asof_view_v1",
            "status": "PASS",
            "business_date": BUSINESS_DATE,
            "latest_available_market_date": BUSINESS_DATE,
            "authorities": [
                {
                    "authority": "normalized_ohlcv",
                    "status": "PASS",
                    "reason": "historical_asof_authority_ready",
                    "business_date": BUSINESS_DATE,
                    "logical_cutoff": BUSINESS_DATE,
                    "logical_max_date": BUSINESS_DATE,
                    "physical_source_path": str(parquet),
                    "physical_source_hash": "test",
                }
            ],
        },
    )
    return asof_view


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> datetime:
    return datetime(2026, 7, 1, 15, 35, tzinfo=timezone.utc)
