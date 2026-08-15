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


def test_phase29_l21t_be_adjusted_normalized_close_without_economic_reconciliation_fails_closed(tmp_path):
    pd = pytest.importorskip("pandas")
    root = tmp_path / ".runtime"
    root.mkdir()
    _write_current(root, positions=[_position("67310", current_price=2000, average_price=2000)])
    asof_view = _write_historical_asof_view(
        tmp_path,
        pd,
        rows=[
            {
                "Date": BUSINESS_DATE,
                "Code": "67310",
                "Close": 3000.0,
                "PriceSource": "adjusted",
                "SchemaVersion": 2,
            }
        ],
    )

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
    artifact = _load_json(Path(result.artifact_path))
    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False
    assert "current_valuation_quote_invalid:67310" in artifact["missing_evidence"]
    assert current["positions"][0]["current_price"] == 2000
    assert current["market_value"] == 200000


def test_phase29_l21t_be_unadjusted_close_is_valid_economic_valuation_price(tmp_path):
    pd = pytest.importorskip("pandas")
    root = tmp_path / ".runtime"
    root.mkdir()
    _write_current(root, positions=[_position("7203", current_price=1000, average_price=900)])
    asof_view = _write_historical_asof_view(
        tmp_path,
        pd,
        rows=[
            {
                "Date": BUSINESS_DATE,
                "Code": "7203",
                "Close": 1100.0,
                "PriceSource": "unadjusted",
                "SchemaVersion": 2,
            }
        ],
    )

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
    assert current["positions"][0]["current_price"] == 1100.0
    assert current["positions"][0]["valuation_price_authority"] == "PASS"
    assert current["positions"][0]["valuation_price_role"] == "economic_valuation_price"


def test_phase29_l21t_be_adjusted_price_with_explicit_reconciliation_uses_economic_price(tmp_path):
    pd = pytest.importorskip("pandas")
    root = tmp_path / ".runtime"
    root.mkdir()
    _write_current(root, positions=[_position("13010", current_price=1000, average_price=900)])
    asof_view = _write_historical_asof_view(
        tmp_path,
        pd,
        rows=[
            {
                "Date": BUSINESS_DATE,
                "Code": "13010",
                "Close": 1120.0,
                "PriceSource": "adjusted",
                "SchemaVersion": 2,
                "economic_price_reconciliation_status": "PASS",
                "economic_price_provenance": "corporate_action_adjustment_authority_reconciled",
                "economic_valuation_price": 1020.0,
            }
        ],
    )

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
    assert current["positions"][0]["current_price"] == 1020.0
    assert current["positions"][0]["valuation_adjusted"] is True
    assert current["positions"][0]["valuation_price_role"] == "reconciled_adjusted_economic_valuation_price"
    assert current["positions"][0]["market_value"] == 102000.0


def test_phase29_l21t_bj_bi_day1_adjusted_quantity_uses_adjusted_basis_valuation_price(tmp_path):
    pd = pytest.importorskip("pandas")
    root = tmp_path / ".runtime"
    root.mkdir()
    positions = [
        _position("23700", current_price=72, average_price=72),
        _position("23880", current_price=169, average_price=169),
        _position("45710", current_price=203, average_price=203),
        _position("66590", current_price=102, average_price=102),
        _position("76470", current_price=26, average_price=26),
        _position("89180", current_price=10, average_price=10),
        _position("93180", current_price=6, average_price=6),
        _position("94320", current_price=149.2, average_price=149.2),
        _position("94340", current_price=151.4, average_price=151.4),
    ]
    quantities = {
        "23700": 500,
        "23880": 100,
        "45710": 100,
        "66590": 400,
        "76470": 1100,
        "89180": 2700,
        "93180": 6600,
        "94320": 200,
        "94340": 100,
    }
    for position in positions:
        position["quantity"] = quantities[position["symbol"]]
        position["market_value"] = position["quantity"] * position["current_price"]
    _write_current(root, positions=positions, cash=745820)
    asof_view = _write_historical_asof_view(
        tmp_path,
        pd,
        rows=[
            {"Date": BUSINESS_DATE, "Code": "23700", "Open": 72.0, "Close": 71.0, "PriceSource": "adjusted", "SchemaVersion": 2},
            {"Date": BUSINESS_DATE, "Code": "23880", "Open": 169.0, "Close": 151.0, "PriceSource": "adjusted", "SchemaVersion": 2},
            {"Date": BUSINESS_DATE, "Code": "45710", "Open": 203.0, "Close": 199.0, "PriceSource": "adjusted", "SchemaVersion": 2},
            {"Date": BUSINESS_DATE, "Code": "66590", "Open": 102.0, "Close": 98.0, "PriceSource": "adjusted", "SchemaVersion": 2},
            {"Date": BUSINESS_DATE, "Code": "76470", "Open": 26.0, "Close": 26.0, "PriceSource": "adjusted", "SchemaVersion": 2},
            {"Date": BUSINESS_DATE, "Code": "89180", "Open": 10.0, "Close": 10.0, "PriceSource": "adjusted", "SchemaVersion": 2},
            {"Date": BUSINESS_DATE, "Code": "93180", "Open": 6.0, "Close": 6.0, "PriceSource": "adjusted", "SchemaVersion": 2},
            {"Date": BUSINESS_DATE, "Code": "94320", "Open": 149.2, "Close": 149.8, "PriceSource": "adjusted", "SchemaVersion": 2},
            {"Date": BUSINESS_DATE, "Code": "94340", "Open": 151.4, "Close": 151.8, "PriceSource": "adjusted", "SchemaVersion": 2},
        ],
        raw_rows=[
            {"Date": BUSINESS_DATE, "Code": "23700", "O": 72.0, "C": 71.0, "AdjO": 72.0, "AdjC": 71.0},
            {"Date": BUSINESS_DATE, "Code": "23880", "O": 169.0, "C": 151.0, "AdjO": 169.0, "AdjC": 151.0},
            {"Date": BUSINESS_DATE, "Code": "45710", "O": 203.0, "C": 199.0, "AdjO": 203.0, "AdjC": 199.0},
            {"Date": BUSINESS_DATE, "Code": "66590", "O": 102.0, "C": 98.0, "AdjO": 102.0, "AdjC": 98.0},
            {"Date": BUSINESS_DATE, "Code": "76470", "O": 26.0, "C": 26.0, "AdjO": 26.0, "AdjC": 26.0},
            {"Date": BUSINESS_DATE, "Code": "89180", "O": 10.0, "C": 10.0, "AdjO": 10.0, "AdjC": 10.0},
            {"Date": BUSINESS_DATE, "Code": "93180", "O": 6.0, "C": 6.0, "AdjO": 6.0, "AdjC": 6.0},
            {"Date": BUSINESS_DATE, "Code": "94320", "O": 3730.0, "C": 3744.0, "AdjO": 149.2, "AdjC": 149.8},
            {"Date": BUSINESS_DATE, "Code": "94340", "O": 1513.5, "C": 1517.5, "AdjO": 151.4, "AdjC": 151.8},
        ],
    )

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
    prices = {position["symbol"]: position["current_price"] for position in current["positions"]}
    roles = {position["symbol"]: position["valuation_price_role"] for position in current["positions"]}
    provenances = {position["symbol"]: position["valuation_price_provenance"] for position in current["positions"]}
    assert result.status == "READY"
    assert result.apply_executed is True
    assert result.position_count == 9
    assert result.valued_position_count == 9
    assert prices["23700"] == 71.0
    assert prices["94320"] == 149.8
    assert prices["94340"] == 151.8
    assert roles["94320"] == "reconciled_adjusted_basis_valuation_price"
    assert roles["94340"] == "reconciled_adjusted_basis_valuation_price"
    assert current["market_value"] == 250040.0
    assert current["total_equity"] == 995860.0
    assert "adjusted_ohlcv_close" in provenances["94320"]
    assert "adjusted_ohlcv_close" in provenances["94340"]


def test_phase29_l21t_bh_adjusted_quote_without_raw_source_still_fails_closed(tmp_path):
    pd = pytest.importorskip("pandas")
    root = tmp_path / ".runtime"
    root.mkdir()
    _write_current(root, positions=[_position("94320", current_price=149.2, average_price=149.2)])
    asof_view = _write_historical_asof_view(
        tmp_path,
        pd,
        rows=[
            {
                "Date": BUSINESS_DATE,
                "Code": "94320",
                "Close": 149.8,
                "PriceSource": "adjusted",
                "SchemaVersion": 2,
            }
        ],
    )

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
    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False
    assert current["positions"][0]["current_price"] == 149.2


def test_phase29_l21t_bj_raw_quantity_uses_raw_basis_valuation_price(tmp_path):
    pd = pytest.importorskip("pandas")
    root = tmp_path / ".runtime"
    root.mkdir()
    _write_current(
        root,
        positions=[
            {
                **_position("94320", current_price=3730.0, average_price=3730.0),
                "quantity": 8.0,
                "market_value": 29840.0,
            }
        ],
    )
    asof_view = _write_historical_asof_view(
        tmp_path,
        pd,
        rows=[
            {
                "Date": BUSINESS_DATE,
                "Code": "94320",
                "Open": 149.2,
                "Close": 149.8,
                "PriceSource": "adjusted",
                "SchemaVersion": 2,
            }
        ],
        raw_rows=[
            {
                "Date": BUSINESS_DATE,
                "Code": "94320",
                "O": 3730.0,
                "C": 3744.0,
                "AdjO": 149.2,
                "AdjC": 149.8,
            }
        ],
    )

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
    position = current["positions"][0]
    assert result.status == "READY"
    assert position["current_price"] == 3744.0
    assert position["market_value"] == 29952.0
    assert position["valuation_price_basis"] == "RAW"


def test_phase29_l21t_bj_adjusted_quantity_raw_price_without_basis_reconciliation_fails_closed(tmp_path):
    root = tmp_path / ".runtime"
    root.mkdir()
    _write_current(root, positions=[_position("94320", current_price=149.2, average_price=149.2)])
    market_path = _write_market_evidence(
        tmp_path,
        {
            "94320": {
                "symbol": "94320",
                "price": 149.8,
                "price_type": "jquants_daily_quote",
                "market_date": BUSINESS_DATE,
                "observed_at": BUSINESS_DATE,
                "source": "fixture",
                "freshness_status": "READY",
                "adjusted": True,
                "price_role": "reconciled_raw_economic_valuation_price",
                "economic_price_reconciliation_status": "PASS",
                "economic_price_provenance": "raw_ohlcv_close:fixture:C",
                "economic_valuation_price": 3744.0,
                "price_basis": "RAW",
            }
        },
    )

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        now=_now(),
        market_evidence_path=market_path,
        safety_authority=_safety_authority(),
        runtime_test_context=_runtime_test_context(tmp_path),
        environment_context=_historical_environment(),
        allow_legacy_temporal_current=True,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False


def test_phase29_l21t_bj_raw_quantity_adjusted_price_without_basis_reconciliation_fails_closed(tmp_path):
    root = tmp_path / ".runtime"
    root.mkdir()
    _write_current(
        root,
        positions=[
            {
                **_position("94320", current_price=3730.0, average_price=3730.0),
                "quantity": 8.0,
                "market_value": 29840.0,
            }
        ],
    )
    market_path = _write_market_evidence(
        tmp_path,
        {
            "94320": {
                "symbol": "94320",
                "price": 149.8,
                "price_type": "jquants_daily_quote",
                "market_date": BUSINESS_DATE,
                "observed_at": BUSINESS_DATE,
                "source": "fixture",
                "freshness_status": "READY",
                "adjusted": True,
                "price_role": "adjusted_analytical_price",
                "economic_price_reconciliation_status": "REVIEW_REQUIRED",
                "economic_price_provenance": "",
                "adjusted_basis_valuation_price": 149.8,
                "adjusted_basis_reconciliation_status": "PASS",
                "adjusted_basis_price_provenance": "fixture_adjusted_close",
                "adjusted_analytical_open": 149.2,
                "adjusted_analytical_price": 149.8,
            }
        },
    )

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        now=_now(),
        market_evidence_path=market_path,
        safety_authority=_safety_authority(),
        runtime_test_context=_runtime_test_context(tmp_path),
        environment_context=_historical_environment(),
        allow_legacy_temporal_current=True,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False


def _write_current(root: Path, *, positions: list[dict] | None = None, cash: float = 690000) -> None:
    positions = positions or [
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
            "cash": cash,
            "buying_power": cash,
            "market_value": sum(float(position.get("market_value") or 0) for position in positions),
            "total_equity": cash + sum(float(position.get("market_value") or 0) for position in positions),
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


def _write_historical_asof_view(
    tmp_path: Path,
    pd,
    *,
    symbols: dict[str, float] | None = None,
    rows: list[dict] | None = None,
    raw_rows: list[dict] | None = None,
) -> Path:
    parquet = tmp_path / "normalized_ohlcv.parquet"
    rows = rows or [{"Date": BUSINESS_DATE, "Code": symbol, "Close": price} for symbol, price in (symbols or {}).items()]
    pd.DataFrame(rows).to_parquet(parquet)
    raw_parquet = tmp_path / "raw_ohlcv.parquet"
    if raw_rows is not None:
        pd.DataFrame(raw_rows).to_parquet(raw_parquet)
    authorities = [
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
    ]
    if raw_rows is not None:
        authorities.append(
            {
                "authority": "raw_ohlcv",
                "status": "PASS",
                "reason": "historical_asof_authority_ready",
                "business_date": BUSINESS_DATE,
                "logical_cutoff": BUSINESS_DATE,
                "logical_max_date": BUSINESS_DATE,
                "physical_source_path": str(raw_parquet),
                "physical_source_hash": "test-raw",
            }
        )
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
            "authorities": authorities,
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


def _write_market_evidence(tmp_path: Path, quotes: dict[str, dict]) -> Path:
    path = tmp_path / "market_evidence.json"
    _write_json(
        path,
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "runtime_business_date": BUSINESS_DATE,
            "business_date": BUSINESS_DATE,
            "market_date": BUSINESS_DATE,
            "latest_available_market_date": BUSINESS_DATE,
            "market_status": "READY",
            "market_freshness_status": "READY",
            "quote_status": "READY",
            "quotes": quotes,
        },
    )
    return path


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
