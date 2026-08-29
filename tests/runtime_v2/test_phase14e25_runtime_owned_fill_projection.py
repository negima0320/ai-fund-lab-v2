import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.asset.runtime_owned_fill_projection import (
    project_runtime_owned_fills_to_current,
)
from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetPosition, CurrentAssetState
from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import normalize_broker_readonly_payload
from ai_fund_lab_v2.runtime_v2.current_state.temporal import CURRENT_TEMPORAL_SCHEMA_VERSION
from ai_fund_lab_v2.runtime_v2.current_state.valuation import run_current_valuation_refresh
from ai_fund_lab_v2.runtime_v2.historical_support.environment import HistoricalExecutionSnapshotProvider
from ai_fund_lab_v2.runtime_v2.reconcile.reconciler import run_reconciliation


def test_phase14e25_projects_only_runtime_owned_fills_to_current(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-initial",
            "environment": "demo",
            "source": "phase14e8_demo_operation_initial_state",
            "as_of": "2026-07-07",
            "positions": [],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": 0,
            "total_equity": 1_000_000,
            "review_required": False,
            "production_equivalent": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
            "generated_from": [],
            "created_at": "2026-07-07",
        },
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "orders.jsonl",
        [
            _accepted_order("65220", "6522"),
            _accepted_order("78780", "7878"),
            _rejected_order("45910", "4591"),
        ],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [
            _position("6522", quantity=100, average_price=102, market_value=235000),
            _position("7878", quantity=100, average_price=102, market_value=155400),
            _position("6501", quantity=200, average_price=4942, market_value=959000),
        ],
    )

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
    )

    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    assert result.status == "PASS"
    assert result.runtime_owned_symbols == ("6522", "7878")
    assert result.excluded_broker_position_symbols == ("6501",)
    assert state["cash"] == 1_000_000 - (100 * 102 * 2)
    assert state["buying_power"] == state["cash"]
    assert state["market_value"] == 235000 + 155400
    assert state["total_equity"] == state["cash"] + state["market_value"]
    assert [position["symbol"] for position in state["positions"]] == ["6522", "7878"]
    assert all(position["symbol"] != "6501" for position in state["positions"])
    assert state["runtime_owned_projection"]["broker_cash_copied"] is False
    assert state["runtime_owned_projection"]["unrelated_demo_positions_copied"] is False
    assert state["source"] == "runtime_v2_runtime_owned_fill_projection"


def test_phase32_ad_current_preserves_canonical_campaign_from_runtime_owned_fills(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-initial",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2026-07-01",
            "positions": [],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": 0,
            "total_equity": 1_000_000,
            "runtime_evaluation_capital": 1_000_000,
        },
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "orders.jsonl",
        [
            {**_accepted_order("83060", "83060"), "business_date": "2026-07-02"},
            {**_accepted_order("89180", "89180"), "business_date": "2026-07-02"},
        ],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [
            _position("83060", quantity=100, average_price=641.5, market_value=64800, as_of="2026-07-02"),
            _position("89180", quantity=100, average_price=1000, market_value=101000, as_of="2026-07-02"),
        ],
    )
    buy_83060 = _execution("83060", "BUY", quantity=100, price=641.5, cash_effect=-64150, business_date="2026-07-02")
    buy_89180 = {
        **_execution("89180", "BUY", quantity=100, price=1000, cash_effect=-100000, business_date="2026-07-02"),
        "position_campaign_id": "pc-canonical-89180-0001",
    }
    _write_jsonl(runtime_root / "persistent_ledger" / "executions.jsonl", [buy_83060, buy_89180])

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2026-07-02",
        mode="historical",
    )

    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    by_symbol = {row["symbol"]: row for row in state["positions"]}
    expected_83060 = "pc-" + hashlib.sha256("83060|1|exec-83060-BUY-2026-07-02".encode("utf-8")).hexdigest()[:16] + "-83060-0001"
    assert result.status == "PASS"
    assert by_symbol["83060"]["position_campaign_id"] == expected_83060
    assert by_symbol["89180"]["position_campaign_id"] == "pc-canonical-89180-0001"
    assert "runtime-test-phase20l-fixture" not in by_symbol["83060"]["position_campaign_id"]


def test_phase24_id_negative_projected_cash_is_review_required(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-initial",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2023-02-13",
            "positions": [],
            "cash": 100_000,
            "buying_power": 100_000,
            "market_value": 0,
            "total_equity": 100_000,
            "runtime_evaluation_capital": 100_000,
        },
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "orders.jsonl",
        [_accepted_order("72030", "7203")],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            {
                "record_type": "execution",
                "source": "runtime_v2_execution_readonly",
                "execution_evidence_type": "execution_equivalent",
                "execution_id": "exec-7203",
                "order_id": "ledger-order-submit-72030",
                "dedup_key": "exec-7203",
                "symbol": "7203",
                "side": "BUY",
                "quantity": 100,
                "price": 1500,
                "business_date": "2023-02-14",
                "executed_at": "2023-02-14",
            }
        ],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [_position("7203", quantity=100, average_price=1500, market_value=150000)],
    )

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2023-02-14",
        mode="historical",
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.projected_cash == -50_000
    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    assert state["cash"] == 100_000


def test_phase26_c_valuation_refresh_preserves_acquisition_authority(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-before",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2023-01-04",
            "positions": [_current_position("83060", quantity=100, average_price=894, market_value=89400, as_of="2023-01-04")],
            "cash": 608900.0,
            "buying_power": 608900.0,
            "market_value": 89400.0,
            "total_equity": 698300.0,
        },
    )
    _write_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl", [_accepted_order("83060", "83060")])
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [_execution("83060", "BUY", quantity=100, price=894, cash_effect=89400, business_date="2023-01-04")],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [
            _position("83060", quantity=100, average_price=894, market_value=89400, as_of="2023-01-04"),
            _position("83060", quantity=100, average_price=894, market_value=95060, as_of="2023-01-18"),
        ],
    )

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2023-01-18",
        mode="historical",
    )
    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))

    assert result.status == "PASS"
    assert state["cash"] == 608900.0
    assert state["positions"][0]["quantity"] == 100.0
    assert state["positions"][0]["average_price"] == 894.0
    assert state["positions"][0]["cost_basis"] == 89400.0
    assert state["positions"][0]["market_value"] == 95060.0
    assert state["positions"][0]["unrealized_pnl"] == 5660.0
    assert state["positions"][0]["as_of"] == "2023-01-18"


def test_phase29_l21t_bl_existing_adjusted_basis_persists_into_day2_valuation(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-day1",
            "environment": "historical",
            "source": "runtime_v2_current_valuation_refresh",
            "as_of": "2022-08-10",
            "positions": [
                {
                    **_current_position("94320", quantity=200, average_price=149.2, market_value=29960.0, as_of="2022-08-10"),
                    "current_price": 149.8,
                    "quantity_basis": "ADJUSTED",
                    "quantity_basis_provenance": "day1_current_valuation_adjusted_basis",
                    "valuation_price_basis": "ADJUSTED",
                    "valuation_price_role": "reconciled_adjusted_basis_valuation_price",
                    "valuation_price_provenance": "day1_adjusted_basis_price",
                },
                {
                    **_current_position("94340", quantity=100, average_price=151.4, market_value=15180.0, as_of="2022-08-10"),
                    "current_price": 151.8,
                    "quantity_basis": "ADJUSTED",
                    "quantity_basis_provenance": "day1_current_valuation_adjusted_basis",
                    "valuation_price_basis": "ADJUSTED",
                    "valuation_price_role": "reconciled_adjusted_basis_valuation_price",
                    "valuation_price_provenance": "day1_adjusted_basis_price",
                },
            ],
            "cash": 745820.0,
            "buying_power": 745820.0,
            "market_value": 45140.0,
            "total_equity": 790960.0,
        },
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "orders.jsonl",
        [_accepted_order("94320", "94320"), _accepted_order("94340", "94340")],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [
            _position("94320", quantity=200, average_price=149.2, market_value=29960.0, as_of="2022-08-12"),
            _position("94340", quantity=100, average_price=151.4, market_value=15180.0, as_of="2022-08-12"),
        ],
    )

    projection = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2022-08-12",
        mode="historical",
    )
    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    by_symbol = {position["symbol"]: position for position in state["positions"]}

    assert projection.status == "PASS"
    assert by_symbol["94320"]["quantity_basis"] == "ADJUSTED"
    assert by_symbol["94320"]["quantity_basis_provenance"] == "day1_current_valuation_adjusted_basis"
    assert by_symbol["94320"]["current_price"] == 149.8
    assert by_symbol["94340"]["quantity_basis"] == "ADJUSTED"
    state.update(
        {
            "schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
            "temporal_schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
            "business_date": "2022-08-12",
            "position_state_as_of": "2022-08-12",
            "valuation_as_of": "2022-08-10",
            "source_market_date": "2022-08-10",
            "last_execution_date": "2022-08-12",
            "last_reconciled_at": "2022-08-12T06:30:00+00:00",
            "updated_at": "2022-08-12T06:30:00+00:00",
        }
    )
    _write_json(runtime_root / "persistent_ledger" / "state.json", state)

    pd = pytest.importorskip("pandas")
    asof_view = _write_historical_asof_view(
        tmp_path,
        pd,
        business_date="2022-08-12",
        rows=[
            {"Date": "2022-08-12", "Code": "94320", "Open": 150.3, "High": 151.1, "Low": 147.8, "Close": 147.9, "PriceSource": "adjusted"},
            {"Date": "2022-08-12", "Code": "94340", "Open": 152.5, "High": 153.5, "Low": 151.1, "Close": 151.4, "PriceSource": "adjusted"},
        ],
        raw_rows=[
            {"Date": "2022-08-12", "Code": "94320", "O": 3758.0, "H": 3778.0, "L": 3696.0, "C": 3698.0, "AdjO": 150.3, "AdjH": 151.1, "AdjL": 147.8, "AdjC": 147.9},
            {"Date": "2022-08-12", "Code": "94340", "O": 1525.0, "H": 1535.0, "L": 1511.0, "C": 1514.0, "AdjO": 152.5, "AdjH": 153.5, "AdjL": 151.1, "AdjC": 151.4},
        ],
    )
    valuation = run_current_valuation_refresh(
        runtime_root=runtime_root,
        business_date="2022-08-12",
        apply_current_valuation=True,
        now=datetime(2022, 8, 12, 6, 35, tzinfo=timezone.utc),
        market_evidence_path=asof_view,
        safety_authority=_historical_safety_authority(),
        runtime_test_context={
            "run_id": "phase29-l21t-bl-test",
            "profile_id": "focused",
            "business_date": "2022-08-12",
            "evidence_root": str(tmp_path / "phase29-l21t-bl-test"),
        },
        environment_context={
            "mode": "historical",
            "broker_environment": "historical_simulated",
            "historical_replay": True,
            "broker_write": False,
            "external_delivery": False,
        },
        allow_legacy_temporal_current=True,
    )
    valued = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    valued_by_symbol = {position["symbol"]: position for position in valued["positions"]}

    assert valuation.status == "READY"
    assert valued_by_symbol["94320"]["current_price"] == 147.9
    assert valued_by_symbol["94320"]["quantity_basis"] == "ADJUSTED"
    assert valued_by_symbol["94320"]["valuation_price_basis"] == "ADJUSTED"


def test_phase29_l21t_bl_new_buy_materializes_adjusted_quantity_basis(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-initial",
            "environment": "historical",
            "source": "runtime_v2_initial_current",
            "as_of": "2022-08-10",
            "positions": [],
            "cash": 1_000_000.0,
            "buying_power": 1_000_000.0,
            "market_value": 0.0,
            "total_equity": 1_000_000.0,
        },
    )
    _write_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl", [_accepted_order("30100", "30100")])
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [_execution("30100", "BUY", quantity=200, price=101, cash_effect=20200, business_date="2022-08-12")],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [_position("30100", quantity=200, average_price=101, market_value=20200, as_of="2022-08-12")],
    )

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2022-08-12",
        mode="historical",
    )
    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    position = state["positions"][0]

    assert result.status == "PASS"
    assert position["symbol"] == "30100"
    assert position["quantity_basis"] == "ADJUSTED"
    assert position["execution_price_basis"] == "ADJUSTED"
    assert position["fill_price_basis"] == "ADJUSTED"
    assert position["quantity_basis_provenance"] == "runtime_execution_price_authority:adjusted_reference_price_basis"


def test_phase30_ak5r_execution_projection_preserves_valuation_metadata_for_open_positions(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-before",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2022-10-20",
            "valuation_as_of": "2022-10-20",
            "source_market_date": "2022-10-20",
            "positions": [
                {
                    **_current_position("44150", quantity=100, average_price=619.0, market_value=61300.0, as_of="2022-10-20"),
                    "current_price": 613.0,
                    "quantity_basis": "ADJUSTED",
                    "valuation_price_basis": "ADJUSTED",
                    "valuation_price_role": "reconciled_adjusted_basis_valuation_price",
                    "valuation_price_provenance": "prior_authoritative_adjusted_close",
                    "valuation_as_of": "2022-10-20",
                    "source_market_date": "2022-10-20",
                    "valuation_source": "prior_market_evidence",
                    "valuation_price_type": "jquants_daily_quote",
                    "valuation_quote_status": "FRESH_CURRENT_QUOTE",
                    "quote_business_date": "2022-10-20",
                    "valuation_business_date": "2022-10-20",
                },
                {
                    **_current_position("66190", quantity=100, average_price=1579.0, market_value=161100.0, as_of="2022-10-20"),
                    "current_price": 1611.0,
                    "quantity_basis": "ADJUSTED",
                    "valuation_price_basis": "ADJUSTED",
                    "valuation_price_provenance": "prior_authoritative_adjusted_close",
                    "valuation_as_of": "2022-10-20",
                    "source_market_date": "2022-10-20",
                },
            ],
            "cash": 247570.0,
            "buying_power": 247570.0,
            "market_value": 222400.0,
            "total_equity": 469970.0,
        },
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "orders.jsonl",
        [_accepted_order("44150", "44150"), _accepted_order("66190", "66190")],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [_execution("66190", "SELL", quantity=100, price=1630.0, cash_effect=163000.0, business_date="2022-10-21")],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [
            {
                **_position("44150", quantity=100, average_price=619.0, market_value=61300.0, as_of="2022-10-20"),
                "current_price": 613.0,
                "quantity_basis": "ADJUSTED",
                "valuation_price_basis": "ADJUSTED",
                "valuation_price_provenance": "ledger_prior_authoritative_adjusted_close",
            },
            _position("66190", quantity=100, average_price=1579.0, market_value=161100.0, as_of="2022-10-20"),
        ],
    )

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2022-10-21",
        mode="historical",
    )
    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    by_symbol = {position["symbol"]: position for position in state["positions"]}

    assert result.status == "PASS"
    assert list(by_symbol) == ["44150"]
    assert by_symbol["44150"]["valuation_as_of"] == "2022-10-20"
    assert by_symbol["44150"]["source_market_date"] == "2022-10-20"
    assert by_symbol["44150"]["valuation_source"] == "prior_market_evidence"
    assert by_symbol["44150"]["valuation_quote_status"] == "FRESH_CURRENT_QUOTE"
    assert by_symbol["44150"]["quote_business_date"] == "2022-10-20"
    assert by_symbol["44150"]["valuation_business_date"] == "2022-10-20"
    assert by_symbol["44150"]["quantity_basis"] == "ADJUSTED"
    assert by_symbol["44150"]["valuation_price_basis"] == "ADJUSTED"


def test_phase29_l21t_bl_explicit_basis_conflict_fails_closed(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-before",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2022-08-10",
            "positions": [
                {
                    **_current_position("94320", quantity=200, average_price=149.2, market_value=29960.0, as_of="2022-08-10"),
                    "quantity_basis": "ADJUSTED",
                    "quantity_basis_provenance": "prior_current_basis",
                }
            ],
            "cash": 745820.0,
            "buying_power": 745820.0,
            "market_value": 29960.0,
            "total_equity": 775780.0,
        },
    )
    _write_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl", [_accepted_order("94320", "94320")])
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [
            {
                **_position("94320", quantity=200, average_price=149.2, market_value=739600.0, as_of="2022-08-12"),
                "quantity_basis": "RAW",
                "quantity_basis_provenance": "conflicting_raw_basis_fixture",
            }
        ],
    )

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2022-08-12",
        mode="historical",
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "runtime_owned_position_basis_conflict:94320" in result.reason


def test_phase26_d_initial_day_same_date_prefill_current_applies_buy_cash_once(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-initial",
            "environment": "historical",
            "source": "runtime_v2_initial_current",
            "as_of": "2023-01-04",
            "positions": [],
            "cash": 1_000_000.0,
            "buying_power": 1_000_000.0,
            "market_value": 0.0,
            "total_equity": 1_000_000.0,
        },
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "orders.jsonl",
        [_accepted_order("83060", "83060"), _accepted_order("76470", "76470"), _accepted_order("94320", "94320")],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution("83060", "BUY", quantity=100, price=894, cash_effect=89400, business_date="2023-01-04"),
            _execution("76470", "BUY", quantity=5400, price=28, cash_effect=151200, business_date="2023-01-04"),
            _execution("94320", "BUY", quantity=1000, price=150.5, cash_effect=150500, business_date="2023-01-04"),
        ],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [
            _position("83060", quantity=100, average_price=894, market_value=89400, as_of="2023-01-04"),
            _position("76470", quantity=5400, average_price=28, market_value=151200, as_of="2023-01-04"),
            _position("94320", quantity=1000, average_price=150.5, market_value=150500, as_of="2023-01-04"),
        ],
    )

    first = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2023-01-04",
        mode="historical",
    )
    first_state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    second = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2023-01-04",
        mode="historical",
    )
    second_state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))

    assert first.status == "PASS"
    assert first_state["cash"] == 608900.0
    assert first_state["buying_power"] == 608900.0
    assert first_state["market_value"] == 391100.0
    assert first_state["total_equity"] == 1_000_000.0
    assert len(first_state["positions"]) == 3
    assert len(first_state["runtime_owned_projection"]["applied_execution_dedup_keys"]) == 3
    assert second.status == "PASS"
    assert second_state["cash"] == first_state["cash"]
    assert second_state["positions"] == first_state["positions"]
    assert second_state["total_equity"] == first_state["total_equity"]


def test_phase26_d_same_date_current_with_all_execution_identities_does_not_replay(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-post-fill",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2023-01-04",
            "positions": [_current_position("83060", quantity=100, average_price=894, market_value=89400, as_of="2023-01-04")],
            "cash": 910600.0,
            "buying_power": 910600.0,
            "market_value": 89400.0,
            "total_equity": 1_000_000.0,
            "runtime_owned_projection": {
                "projection_status": "PASS",
                "applied_execution_dedup_keys": ["exec-83060-BUY-2023-01-04"],
                "applied_execution_ids": ["exec-83060-BUY-2023-01-04"],
            },
        },
    )
    _write_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl", [_accepted_order("83060", "83060")])
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [_execution("83060", "BUY", quantity=100, price=894, cash_effect=89400, business_date="2023-01-04")],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [_position("83060", quantity=100, average_price=894, market_value=89400, as_of="2023-01-04")],
    )

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2023-01-04",
        mode="historical",
    )
    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))

    assert result.status == "PASS"
    assert state["cash"] == 910600.0
    assert state["positions"][0]["quantity"] == 100.0
    assert state["positions"][0]["cost_basis"] == 89400.0
    assert state["total_equity"] == 1_000_000.0


def test_phase26_d_same_date_current_applies_only_missing_execution_identities(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-partial",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2023-01-04",
            "positions": [_current_position("83060", quantity=100, average_price=894, market_value=89400, as_of="2023-01-04")],
            "cash": 910600.0,
            "buying_power": 910600.0,
            "market_value": 89400.0,
            "total_equity": 1_000_000.0,
            "runtime_owned_projection": {
                "projection_status": "PASS",
                "applied_execution_dedup_keys": ["exec-83060-BUY-2023-01-04"],
            },
        },
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "orders.jsonl",
        [_accepted_order("83060", "83060"), _accepted_order("76470", "76470"), _accepted_order("94320", "94320")],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution("83060", "BUY", quantity=100, price=894, cash_effect=89400, business_date="2023-01-04"),
            _execution("76470", "BUY", quantity=5400, price=28, cash_effect=151200, business_date="2023-01-04"),
            _execution("94320", "BUY", quantity=1000, price=150.5, cash_effect=150500, business_date="2023-01-04"),
        ],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [
            _position("83060", quantity=100, average_price=894, market_value=89400, as_of="2023-01-04"),
            _position("76470", quantity=5400, average_price=28, market_value=151200, as_of="2023-01-04"),
            _position("94320", quantity=1000, average_price=150.5, market_value=150500, as_of="2023-01-04"),
        ],
    )

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2023-01-04",
        mode="historical",
    )
    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))

    assert result.status == "PASS"
    assert state["cash"] == 608900.0
    assert {position["symbol"]: position["quantity"] for position in state["positions"]} == {
        "83060": 100.0,
        "76470": 5400.0,
        "94320": 1000.0,
    }
    assert len(state["runtime_owned_projection"]["applied_execution_dedup_keys"]) == 3


def test_phase26_c_historical_snapshot_refs_no_fill_positions_by_valuation_date(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-before",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2023-01-04",
            "positions": [_current_position("83060", quantity=100, average_price=894, market_value=95060, as_of="2023-01-04")],
            "cash": 608900.0,
            "buying_power": 608900.0,
            "market_value": 95060.0,
            "total_equity": 703960.0,
        },
    )
    snapshot_path = tmp_path / "tachibana_snapshot.json"
    report_path = tmp_path / "snapshot_report.json"

    result = HistoricalExecutionSnapshotProvider(
        runtime_root=runtime_root,
        business_date="2023-01-18",
    )(mode="historical", snapshot_path=snapshot_path, report_path=report_path)
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))

    assert result.status == "PASS"
    assert payload["positions"][0]["position_ref"] == "historical-position-83060-2023-01-18"
    assert payload["positions"][0]["average_price"] == 894.0
    assert payload["positions"][0]["market_value"] == 95060.0


def test_phase26_c_buy_add_recalculates_weighted_average_cost_and_uses_valuation(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-before",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2023-01-04",
            "positions": [
                {
                    **_current_position("72030", quantity=100, average_price=10, market_value=1000, as_of="2023-01-04"),
                    "quantity_basis": "ADJUSTED",
                    "quantity_basis_provenance": "prior_current_basis",
                }
            ],
            "cash": 10000.0,
            "buying_power": 10000.0,
            "market_value": 1000.0,
            "total_equity": 11000.0,
        },
    )
    _write_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl", [_accepted_order("72030", "72030")])
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution("72030", "BUY", quantity=100, price=10, cash_effect=1000, business_date="2023-01-04"),
            _execution("72030", "BUY", quantity=50, price=20, cash_effect=1000, business_date="2023-01-05"),
        ],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [
            _position("72030", quantity=100, average_price=10, market_value=1000, as_of="2023-01-04"),
            _position("72030", quantity=150, average_price=10, market_value=3000, as_of="2023-01-05"),
        ],
    )

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2023-01-05",
        mode="historical",
    )
    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    position = state["positions"][0]

    assert result.status == "PASS"
    assert state["cash"] == 9000.0
    assert position["quantity"] == 150.0
    assert round(position["average_price"], 6) == round(2000.0 / 150.0, 6)
    assert position["cost_basis"] == 2000.0
    assert position["market_value"] == 3000.0
    assert position["unrealized_pnl"] == 1000.0
    assert position["quantity_basis"] == "ADJUSTED"
    assert position["quantity_basis_provenance"] == "prior_current_basis"


def test_phase26_c_full_exit_removes_active_position_and_preserves_cash(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-before",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2023-01-04",
            "positions": [_current_position("72030", quantity=100, average_price=10, market_value=1000, as_of="2023-01-04")],
            "cash": 10000.0,
            "buying_power": 10000.0,
            "market_value": 1000.0,
            "total_equity": 11000.0,
        },
    )
    _write_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl", [_accepted_order("72030", "72030")])
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution("72030", "BUY", quantity=100, price=10, cash_effect=1000, business_date="2023-01-04"),
            _execution("72030", "SELL", quantity=100, price=12, cash_effect=1200, business_date="2023-01-05"),
        ],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [_position("72030", quantity=100, average_price=10, market_value=1000, as_of="2023-01-04")],
    )

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2023-01-05",
        mode="historical",
    )
    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))

    assert result.status == "PASS"
    assert state["positions"] == []
    assert state["cash"] == 11200.0
    assert state["market_value"] == 0
    assert state["total_equity"] == 11200.0


def test_phase26_b_mixed_fill_projection_uses_target_date_valuation_and_post_fill_cash(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-before",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2023-01-17",
            "positions": [
                {
                    **_current_position("76470", quantity=5400, average_price=28, market_value=151200, as_of="2023-01-04"),
                    "quantity_basis": "ADJUSTED",
                    "quantity_basis_provenance": "prior_current_basis_76470",
                },
                {
                    **_current_position("83060", quantity=100, average_price=894, market_value=89400, as_of="2023-01-04"),
                    "quantity_basis": "ADJUSTED",
                    "quantity_basis_provenance": "prior_current_basis_83060",
                },
                {
                    **_current_position("94320", quantity=1000, average_price=150.5, market_value=150500, as_of="2023-01-04"),
                    "quantity_basis": "ADJUSTED",
                    "quantity_basis_provenance": "prior_current_basis_94320",
                },
            ],
            "cash": 217800.0,
            "buying_power": 217800.0,
            "market_value": 391100.0,
            "total_equity": 608900.0,
        },
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "orders.jsonl",
        [
            _accepted_order("76470", "76470"),
            _accepted_order("83060", "83060"),
            _accepted_order("94320", "94320"),
            _accepted_order("93180", "93180"),
        ],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution("76470", "BUY", quantity=5400, price=28, cash_effect=151200, business_date="2023-01-04"),
            _execution("83060", "BUY", quantity=100, price=894, cash_effect=89400, business_date="2023-01-04"),
            _execution("94320", "BUY", quantity=1000, price=150.5, cash_effect=150500, business_date="2023-01-04"),
            _execution("76470", "SELL", quantity=1700, price=27, cash_effect=45900, business_date="2023-01-18"),
            _execution("93180", "BUY", quantity=59600, price=3, cash_effect=178800, business_date="2023-01-18"),
        ],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [
            _position("76470", quantity=5400, average_price=28, market_value=151200, as_of="2023-01-04"),
            _position("83060", quantity=100, average_price=894, market_value=89400, as_of="2023-01-04"),
            _position("94320", quantity=1000, average_price=150.5, market_value=150500, as_of="2023-01-04"),
            _position("76470", quantity=3700, average_price=28, market_value=96200, as_of="2023-01-18"),
            _position("83060", quantity=100, average_price=894, market_value=95060, as_of="2023-01-18"),
            _position("94320", quantity=1000, average_price=150.5, market_value=149700, as_of="2023-01-18"),
            _position("93180", quantity=59600, average_price=3, market_value=178800, as_of="2023-01-18"),
        ],
    )

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2023-01-18",
        mode="historical",
    )
    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    bundle = normalize_broker_readonly_payload(
        environment="historical",
        source="runtime_v2_execution_readonly_simulation",
        as_of="2023-01-18",
        positions=[
            {"position_ref": "p-76470-2023-01-18", "position_key": "76470", "symbol": "76470", "quantity": 3700, "average_price": 28, "market_value": 96200},
            {"position_ref": "p-83060-2023-01-18", "position_key": "83060", "symbol": "83060", "quantity": 100, "average_price": 894, "market_value": 95060},
            {"position_ref": "p-94320-2023-01-18", "position_key": "94320", "symbol": "94320", "quantity": 1000, "average_price": 150.5, "market_value": 149700},
            {"position_ref": "p-93180-2023-01-18", "position_key": "93180", "symbol": "93180", "quantity": 59600, "average_price": 3, "market_value": 178800},
        ],
        cash={"cash_ref": "cash-2023-01-18", "cash": 84900, "buying_power": 84900},
    )
    reconciliation = run_reconciliation(
        mode="historical",
        environment="historical",
        business_date="2023-01-18",
        broker_positions=bundle.positions,
        broker_cash=bundle.cash,
        asset_state=_asset_state_from_payload(state),
    )

    assert result.status == "PASS"
    assert state["cash"] == 84900.0
    assert state["buying_power"] == 84900.0
    assert state["market_value"] == 519760.0
    assert state["total_equity"] == 604660.0
    assert {position["symbol"]: position["market_value"] for position in state["positions"]} == {
        "76470": 96200.0,
        "83060": 95060.0,
        "94320": 149700.0,
        "93180": 178800.0,
    }
    by_symbol = {position["symbol"]: position for position in state["positions"]}
    assert by_symbol["76470"]["quantity_basis"] == "ADJUSTED"
    assert by_symbol["76470"]["quantity_basis_provenance"] == "prior_current_basis_76470"
    assert by_symbol["94320"]["quantity_basis"] == "ADJUSTED"
    assert by_symbol["93180"]["quantity_basis"] == "ADJUSTED"
    assert {position["as_of"] for position in state["positions"]} == {"2023-01-18"}
    assert reconciliation.findings == ()


def test_phase26_c_negative_cost_basis_average_price_mismatch_fails_closed(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-before",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2023-01-04",
            "positions": [
                {
                    **_current_position("83060", quantity=100, average_price=894, market_value=95060, as_of="2023-01-04"),
                    "cost_basis": 95060.0,
                }
            ],
            "cash": 608900.0,
            "buying_power": 608900.0,
            "market_value": 95060.0,
            "total_equity": 703960.0,
        },
    )
    _write_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl", [_accepted_order("83060", "83060")])
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [_execution("83060", "BUY", quantity=100, price=894, cash_effect=89400, business_date="2023-01-04")],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [_position("83060", quantity=100, average_price=894, market_value=95060, as_of="2023-01-18")],
    )

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2023-01-18",
        mode="historical",
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "runtime_owned_cost_basis_average_price_mismatch:83060" in result.reason


def test_phase26_b_reconciliation_detects_market_value_and_total_equity_mismatch(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-current",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2023-01-18",
            "positions": [_current_position("76470", quantity=3700, average_price=28, market_value=103600, as_of="2023-01-04")],
            "cash": 84900.0,
            "buying_power": 84900.0,
            "market_value": 103600.0,
            "total_equity": 188500.0,
        },
    )
    bundle = normalize_broker_readonly_payload(
        environment="historical",
        source="runtime_v2_execution_readonly_simulation",
        as_of="2023-01-18",
        positions=[
            {"position_ref": "p-76470-2023-01-18", "position_key": "76470", "symbol": "76470", "quantity": 3700, "average_price": 28, "market_value": 96200},
        ],
        cash={"cash_ref": "cash-2023-01-18", "cash": 84900, "buying_power": 84900},
    )

    reconciliation = run_reconciliation(
        mode="historical",
        environment="historical",
        business_date="2023-01-18",
        broker_positions=bundle.positions,
        broker_cash=bundle.cash,
        asset_state=_asset_state_from_payload(json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))),
    )

    assert [finding.finding_type for finding in reconciliation.findings] == [
        "POSITION_MARKET_VALUE_MISMATCH",
        "TOTAL_EQUITY_MISMATCH",
    ]


def test_phase29_l21t_x_reconciliation_ignores_micro_yen_cash_float_noise(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-2023-06-23",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2023-06-23",
            "positions": [
                _current_position("94320", quantity=1400, average_price=150.62142857142857, market_value=231700.0, as_of="2023-06-23"),
                _current_position("37820", quantity=500, average_price=53, market_value=24500.0, as_of="2023-06-23"),
                _current_position("76470", quantity=3700, average_price=25.883092394720297, market_value=107300.0, as_of="2023-06-23"),
                _current_position("99840", quantity=100, average_price=1630, market_value=169680.0, as_of="2023-06-23"),
                _current_position("83060", quantity=100, average_price=930, market_value=103350.0, as_of="2023-06-23"),
                _current_position("21340", quantity=1500, average_price=13.24137931034483, market_value=46500.0, as_of="2023-06-23"),
                _current_position("40520", quantity=100, average_price=1021, market_value=141900.0, as_of="2023-06-23"),
                _current_position("94340", quantity=800, average_price=152.8, market_value=122240.00000000001, as_of="2023-06-23"),
            ],
            "cash": 129889.99999999999,
            "buying_power": 129889.99999999999,
            "market_value": 947170.0,
            "total_equity": 1077060.0,
        },
    )
    bundle = normalize_broker_readonly_payload(
        environment="historical",
        source="runtime_v2_execution_readonly_simulation",
        as_of="2023-06-23",
        positions=[
            {"position_ref": "p-94320", "position_key": "94320", "symbol": "94320", "quantity": 1400, "average_price": 150.62142857142857, "market_value": 231700.0},
            {"position_ref": "p-37820", "position_key": "37820", "symbol": "37820", "quantity": 500, "average_price": 53, "market_value": 24500.0},
            {"position_ref": "p-76470", "position_key": "76470", "symbol": "76470", "quantity": 3700, "average_price": 25.883092394720297, "market_value": 107300.0},
            {"position_ref": "p-99840", "position_key": "99840", "symbol": "99840", "quantity": 100, "average_price": 1630, "market_value": 169680.0},
            {"position_ref": "p-83060", "position_key": "83060", "symbol": "83060", "quantity": 100, "average_price": 930, "market_value": 103350.0},
            {"position_ref": "p-21340", "position_key": "21340", "symbol": "21340", "quantity": 1500, "average_price": 13.24137931034483, "market_value": 46500.0},
            {"position_ref": "p-40520", "position_key": "40520", "symbol": "40520", "quantity": 100, "average_price": 1021, "market_value": 141900.0},
            {"position_ref": "p-94340", "position_key": "94340", "symbol": "94340", "quantity": 800, "average_price": 152.8, "market_value": 122240.00000000001},
        ],
        cash={"cash_ref": "cash-2023-06-23", "cash": 129890.0, "buying_power": 129890.0},
    )

    reconciliation = run_reconciliation(
        mode="historical",
        environment="historical",
        business_date="2023-06-23",
        broker_positions=bundle.positions,
        broker_cash=bundle.cash,
        asset_state=_asset_state_from_payload(json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))),
    )

    assert reconciliation.findings == ()


def test_phase29_l21t_x_reconciliation_preserves_cash_mismatch_protection(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-cash-mismatch",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2023-06-23",
            "positions": [],
            "cash": 129889.99,
            "buying_power": 129889.99,
            "market_value": 0.0,
            "total_equity": 129889.99,
        },
    )
    bundle = normalize_broker_readonly_payload(
        environment="historical",
        source="runtime_v2_execution_readonly_simulation",
        as_of="2023-06-23",
        positions=[],
        cash={"cash_ref": "cash-2023-06-23", "cash": 129890.0, "buying_power": 129890.0},
    )

    reconciliation = run_reconciliation(
        mode="historical",
        environment="historical",
        business_date="2023-06-23",
        broker_positions=bundle.positions,
        broker_cash=bundle.cash,
        asset_state=_asset_state_from_payload(json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))),
    )

    assert [finding.finding_type for finding in reconciliation.findings] == [
        "CASH_MISMATCH",
        "BUYING_POWER_MISMATCH",
        "TOTAL_EQUITY_MISMATCH",
    ]


def _accepted_order(symbol: str, broker_symbol: str) -> dict:
    return {
        "record_type": "order",
        "source": "runtime_v2_submit_pipeline",
        "status": "ACCEPTED",
        "symbol": symbol,
        "issue_code_normalization": {"broker_issue_code": broker_symbol},
        "record_id": f"ledger-order-submit-{symbol}",
    }


def _rejected_order(symbol: str, broker_symbol: str) -> dict:
    payload = _accepted_order(symbol, broker_symbol)
    payload["status"] = "REJECTED_OR_UNKNOWN"
    return payload


def _position(
    symbol: str,
    *,
    quantity: float,
    average_price: float,
    market_value: float,
    as_of: str = "2026-07-08T06:24:02+00:00",
) -> dict:
    return {
        "record_type": "position",
        "source": "runtime_v2_execution_readonly",
        "symbol": symbol,
        "position_key": symbol,
        "quantity": quantity,
        "average_price": average_price,
        "market_value": market_value,
        "as_of": as_of,
        "recorded_at": as_of,
        "record_id": f"ledger-position-{symbol}-{as_of}",
    }


def _current_position(symbol: str, *, quantity: float, average_price: float, market_value: float, as_of: str) -> dict:
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": average_price,
        "market_value": market_value,
        "cost_basis": quantity * average_price,
        "unrealized_pnl": market_value - quantity * average_price,
        "source": "runtime_v2_runtime_owned_fill_projection",
        "as_of": as_of,
    }


def _execution(
    symbol: str,
    side: str,
    *,
    quantity: float,
    price: float,
    cash_effect: float,
    business_date: str = "2023-01-18",
) -> dict:
    return {
        "record_type": "execution",
        "source": "runtime_v2_execution_readonly",
        "execution_evidence_type": "execution_equivalent",
        "execution_id": f"exec-{symbol}-{side}-{business_date}",
        "order_id": f"order-{symbol}-{side}",
        "dedup_key": f"exec-{symbol}-{side}-{business_date}",
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "filled_quantity": quantity,
        "price": price,
        "cash_effect": cash_effect,
        "business_date": business_date,
        "executed_at": business_date,
    }


def _asset_state_from_payload(payload: dict) -> CurrentAssetState:
    return CurrentAssetState(
        schema_version=str(payload.get("schema_version") or "1"),
        asset_state_id=str(payload.get("asset_state_id") or "asset-current"),
        environment=str(payload.get("environment") or "historical"),
        source=str(payload.get("source") or "runtime_v2_runtime_owned_fill_projection"),
        as_of=str(payload.get("as_of") or ""),
        positions=tuple(
            CurrentAssetPosition(
                symbol=str(position.get("symbol") or ""),
                quantity=float(position.get("quantity") or 0),
                average_price=float(position.get("average_price") or 0),
                market_value=float(position.get("market_value") or 0),
                source=str(position.get("source") or payload.get("source") or ""),
                as_of=str(position.get("as_of") or payload.get("as_of") or ""),
            )
            for position in payload.get("positions") or ()
        ),
        cash=float(payload["cash"]) if payload.get("cash") is not None else None,
        buying_power=float(payload["buying_power"]) if payload.get("buying_power") is not None else None,
        market_value=float(payload["market_value"]) if payload.get("market_value") is not None else None,
        total_equity=float(payload["total_equity"]) if payload.get("total_equity") is not None else None,
        review_required=bool(payload.get("review_required", False)),
        production_equivalent=bool(payload.get("production_equivalent", False)),
        current_state_confirmed_empty=bool(payload.get("current_state_confirmed_empty", False)),
        current_positions_unknown=bool(payload.get("current_positions_unknown", False)),
        cash_unknown=bool(payload.get("cash_unknown", False)),
        buying_power_unknown=bool(payload.get("buying_power_unknown", False)),
        generated_from=tuple(payload.get("generated_from") or ()),
        created_at=str(payload.get("created_at") or payload.get("as_of") or ""),
    )


def _historical_safety_authority() -> dict:
    return {
        "safety_status": "PASS",
        "safety_decision": "ALLOW",
        "safety_policy_version": "historical_replay_neutral_safety_v1",
        "safety_source": "data_readiness_historical_temporal_authority",
        "safety_action_permissions": {"broker_write": "BLOCKED"},
    }


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _write_historical_asof_view(
    tmp_path: Path,
    pd,
    *,
    business_date: str,
    rows: list[dict],
    raw_rows: list[dict],
) -> Path:
    parquet = tmp_path / f"normalized_ohlcv_{business_date}.parquet"
    pd.DataFrame(rows).to_parquet(parquet)
    raw_parquet = tmp_path / f"raw_ohlcv_{business_date}.parquet"
    pd.DataFrame(raw_rows).to_parquet(raw_parquet)
    asof_view = tmp_path / f"historical_asof_view_{business_date}.json"
    _write_json(
        asof_view,
        {
            "schema_version": "runtime_historical_asof_view_v1",
            "business_date": business_date,
            "status": "PASS",
            "authorities": [
                {
                    "authority": "normalized_ohlcv",
                    "status": "PASS",
                    "reason": "historical_asof_authority_ready",
                    "business_date": business_date,
                    "logical_cutoff": business_date,
                    "logical_max_date": business_date,
                    "physical_source_path": str(parquet),
                },
                {
                    "authority": "raw_ohlcv",
                    "status": "PASS",
                    "reason": "historical_asof_authority_ready",
                    "business_date": business_date,
                    "logical_cutoff": business_date,
                    "logical_max_date": business_date,
                    "physical_source_path": str(raw_parquet),
                },
            ],
        },
    )
    return asof_view
