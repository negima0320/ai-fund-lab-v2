import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.asset.runtime_owned_fill_projection import (
    project_runtime_owned_fills_to_current,
)
from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetPosition, CurrentAssetState
from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import normalize_broker_readonly_payload
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
                _current_position("76470", quantity=5400, average_price=28, market_value=151200, as_of="2023-01-04"),
                _current_position("83060", quantity=100, average_price=894, market_value=89400, as_of="2023-01-04"),
                _current_position("94320", quantity=1000, average_price=150.5, market_value=150500, as_of="2023-01-04"),
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


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
