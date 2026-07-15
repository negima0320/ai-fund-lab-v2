from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.current_state.temporal import CURRENT_TEMPORAL_SCHEMA_VERSION
from ai_fund_lab_v2.runtime_v2.current_state.valuation import run_current_valuation_refresh


BUSINESS_DATE = "2026-07-06"


def test_phase17aa_historical_current_valuation_uses_run_scoped_market_and_safety_authority(tmp_path):
    pd = pytest.importorskip("pandas")
    root = tmp_path / ".runtime"
    root.mkdir()
    _write_current(root)
    asof_view = _write_historical_asof_view(tmp_path, pd, symbols={"7203": 1100.0, "6758": 2000.0})

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        now=_now(),
        market_evidence_path=asof_view,
        safety_authority=_safety_authority(),
        runtime_test_context=_runtime_test_context(tmp_path),
        environment_context=_historical_environment(),
        allow_legacy_temporal_current=True,
    )

    current = _load_json(root / "persistent_ledger" / "state.json")
    assert result.status == "READY"
    assert result.apply_executed is True
    assert result.market_evidence_path == str(asof_view)
    assert result.market_date == BUSINESS_DATE
    assert result.position_count == 2
    assert result.valued_position_count == 2
    assert result.new_total_market_value == 310000.0
    assert current["cash"] == 690000
    assert [position["quantity"] for position in current["positions"]] == [100, 100]
    assert [position["current_price"] for position in current["positions"]] == [1100.0, 2000.0]


def test_phase17aa_missing_historical_safety_blocks_apply_but_preserves_valuation_count(tmp_path):
    pd = pytest.importorskip("pandas")
    root = tmp_path / ".runtime"
    root.mkdir()
    _write_current(root)
    asof_view = _write_historical_asof_view(tmp_path, pd, symbols={"7203": 1100.0, "6758": 2000.0})

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        now=_now(),
        market_evidence_path=asof_view,
        safety_authority={},
        runtime_test_context=_runtime_test_context(tmp_path),
        environment_context=_historical_environment(),
        allow_legacy_temporal_current=True,
    )

    current = _load_json(root / "persistent_ledger" / "state.json")
    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False
    assert result.valued_position_count == 2
    assert current["positions"][0]["current_price"] == 1000


def test_phase17aa_missing_historical_quote_requires_review_and_no_apply(tmp_path):
    pd = pytest.importorskip("pandas")
    root = tmp_path / ".runtime"
    root.mkdir()
    _write_current(root)
    asof_view = _write_historical_asof_view(tmp_path, pd, symbols={"7203": 1100.0})

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        now=_now(),
        market_evidence_path=asof_view,
        safety_authority=_safety_authority(),
        runtime_test_context=_runtime_test_context(tmp_path),
        environment_context=_historical_environment(),
        allow_legacy_temporal_current=True,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False
    assert "6758" in result.missing_symbols


def _write_current(root: Path) -> None:
    positions = [
        _position("7203", current_price=1000, average_price=900),
        _position("6758", current_price=1800, average_price=1700),
    ]
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
            "temporal_schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
            "position_state_as_of": BUSINESS_DATE,
            "valuation_as_of": "2026-07-03",
            "source_market_date": "2026-07-03",
            "last_execution_date": BUSINESS_DATE,
            "last_reconciled_at": "2026-07-06T08:30:00+00:00",
            "updated_at": "2026-07-06T08:30:00+00:00",
            "positions": positions,
            "cash": 690000,
            "buying_power": 690000,
            "market_value": 280000,
            "total_equity": 970000,
            "production_equivalent": False,
        },
    )


def _position(symbol: str, *, current_price: float, average_price: float) -> dict:
    return {
        "symbol": symbol,
        "quantity": 100,
        "average_price": average_price,
        "current_price": current_price,
        "market_value": 100 * current_price,
        "unrealized_pnl": (current_price - average_price) * 100,
        "ownership": "runtime_owned",
    }


def _write_historical_asof_view(tmp_path: Path, pd, *, symbols: dict[str, float]) -> Path:
    parquet = tmp_path / "normalized_ohlcv.parquet"
    pd.DataFrame(
        [
            {"Date": BUSINESS_DATE, "Code": symbol, "Close": price}
            for symbol, price in symbols.items()
        ]
    ).to_parquet(parquet)
    asof_view = tmp_path / "runs" / "runtime-test-phase17aa" / "daily" / BUSINESS_DATE / "market_refresh" / "historical_asof_view.json"
    _write_json(
        asof_view,
        {
            "schema_version": "phase17_l_historical_asof_view_v1",
            "status": "PASS",
            "reason": "historical_asof_view_ready",
            "business_date": BUSINESS_DATE,
            "latest_available_market_date": BUSINESS_DATE,
            "logical_identity": f"historical-asof:{BUSINESS_DATE}",
            "future_rows_excluded_from_consumer": True,
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


def _safety_authority() -> dict:
    return {
        "safety_status": "PASS",
        "safety_decision": "ALLOW",
        "safety_policy_version": "historical_replay_neutral_safety_v1",
        "safety_source": "data_readiness_historical_temporal_authority",
        "safety_action_permissions": {"broker_write": "BLOCKED"},
    }


def _runtime_test_context(tmp_path: Path) -> dict:
    evidence_root = tmp_path / "runs" / "runtime-test-phase17aa"
    return {
        "run_id": "runtime-test-phase17aa",
        "profile_id": "historical-smoke",
        "evidence_root": str(evidence_root),
        "business_date": BUSINESS_DATE,
        "job": "current_valuation_refresh",
    }


def _historical_environment() -> dict:
    return {
        "historical_replay": True,
        "simulation": True,
        "broker_write": False,
        "external_delivery": False,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> datetime:
    return datetime(2026, 7, 6, 8, 45, tzinfo=timezone.utc)
