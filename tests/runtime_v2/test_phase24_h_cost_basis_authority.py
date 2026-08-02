from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.asset.runtime_owned_fill_projection import (
    project_runtime_owned_fills_to_current,
)


def test_phase24_h_buy_from_empty_sets_execution_basis_cost(tmp_path: Path) -> None:
    state = _project(
        tmp_path,
        [("2026-01-01", "11110", "BUY", 100, 1000)],
        latest_positions=[_position("11110", quantity=100, average_price=999, market_value=100000)],
    )

    pos = _position_by_symbol(state, "11110")
    assert pos["quantity"] == 100
    assert pos["cost_basis"] == 100000
    assert pos["average_price"] == 1000
    assert pos["unrealized_pnl"] == 0


def test_phase24_h_add_into_open_position_uses_moving_average(tmp_path: Path) -> None:
    state = _project(
        tmp_path,
        [
            ("2026-01-01", "11110", "BUY", 100, 1000),
            ("2026-01-02", "11110", "BUY", 100, 1200),
        ],
        latest_positions=[_position("11110", quantity=200, average_price=999, market_value=240000)],
    )

    pos = _position_by_symbol(state, "11110")
    assert pos["quantity"] == 200
    assert pos["cost_basis"] == 220000
    assert pos["average_price"] == 1100
    assert pos["unrealized_pnl"] == 20000


def test_phase24_h_partial_sell_preserves_remaining_moving_average_basis(tmp_path: Path) -> None:
    state = _project(
        tmp_path,
        [
            ("2026-01-01", "11110", "BUY", 100, 1000),
            ("2026-01-02", "11110", "BUY", 100, 1200),
            ("2026-01-03", "11110", "SELL", 100, 1300),
        ],
        latest_positions=[_position("11110", quantity=100, average_price=999, market_value=140000)],
    )

    pos = _position_by_symbol(state, "11110")
    assert pos["quantity"] == 100
    assert pos["cost_basis"] == 110000
    assert pos["average_price"] == 1100
    assert pos["unrealized_pnl"] == 30000
    assert state["realized_pnl"] == 20000


def test_phase24_h_full_sell_resets_open_cost_basis(tmp_path: Path) -> None:
    state = _project(
        tmp_path,
        [
            ("2026-01-01", "11110", "BUY", 100, 1000),
            ("2026-01-02", "11110", "BUY", 100, 1200),
            ("2026-01-03", "11110", "SELL", 200, 1300),
        ],
        latest_positions=[],
    )

    assert state["positions"] == []
    assert state["market_value"] == 0
    assert state["realized_pnl"] == 40000


def test_phase24_h_same_symbol_reentry_does_not_inherit_closed_basis(tmp_path: Path) -> None:
    state = _project(
        tmp_path,
        [
            ("2026-01-01", "11110", "BUY", 100, 1000),
            ("2026-01-02", "11110", "SELL", 100, 900),
            ("2026-01-03", "11110", "BUY", 100, 1200),
        ],
        latest_positions=[_position("11110", quantity=100, average_price=1000, market_value=130000)],
    )

    pos = _position_by_symbol(state, "11110")
    assert pos["quantity"] == 100
    assert pos["cost_basis"] == 120000
    assert pos["average_price"] == 1200
    assert pos["unrealized_pnl"] == 10000
    assert state["realized_pnl"] == -10000


def test_phase24_h_multiple_close_reentry_cycles_keep_open_basis_independent(tmp_path: Path) -> None:
    state = _project(
        tmp_path,
        [
            ("2026-01-01", "11110", "BUY", 100, 1000),
            ("2026-01-02", "11110", "SELL", 100, 1100),
            ("2026-01-03", "11110", "BUY", 100, 1200),
            ("2026-01-04", "11110", "SELL", 100, 1000),
            ("2026-01-05", "11110", "BUY", 100, 900),
        ],
        latest_positions=[_position("11110", quantity=100, average_price=1050, market_value=95000)],
    )

    pos = _position_by_symbol(state, "11110")
    assert pos["cost_basis"] == 90000
    assert pos["average_price"] == 900
    assert pos["unrealized_pnl"] == 5000
    assert state["realized_pnl"] == -10000


def test_phase24_h_phase24g_generalized_sequence_reconciles_execution_basis_pnl(tmp_path: Path) -> None:
    state = _project(
        tmp_path,
        [
            ("2022-07-04", "94320", "BUY", 1100, 155.2),
            ("2022-07-05", "94320", "BUY", 100, 156.6),
            ("2022-07-11", "94340", "BUY", 1100, 153.9),
            ("2022-07-11", "23880", "BUY", 1400, 132),
            ("2022-07-13", "66590", "BUY", 1000, 145),
            ("2022-07-14", "23880", "SELL", 1400, 113),
            ("2022-07-15", "66590", "SELL", 1000, 122),
            ("2022-07-15", "23880", "BUY", 1400, 113),
            ("2022-07-19", "24370", "BUY", 100, 1235),
            ("2022-07-19", "23880", "SELL", 1400, 115),
            ("2022-07-19", "66590", "BUY", 1400, 122),
            ("2022-07-20", "66590", "SELL", 1400, 118),
            ("2022-07-20", "23880", "BUY", 1400, 120),
            ("2022-07-21", "23880", "SELL", 1400, 122),
            ("2022-07-22", "23880", "BUY", 1500, 119),
            ("2022-07-25", "66590", "BUY", 1600, 102),
            ("2022-07-25", "23880", "SELL", 1500, 110),
            ("2022-07-26", "66590", "SELL", 1600, 103),
            ("2022-07-26", "23880", "BUY", 1300, 120),
            ("2022-07-26", "24370", "SELL", 100, 1249),
            ("2022-07-27", "66590", "BUY", 1600, 103),
            ("2022-07-28", "66590", "SELL", 1600, 103),
            ("2022-07-28", "24370", "BUY", 100, 1370),
            ("2022-07-29", "66590", "BUY", 1600, 104),
            ("2022-07-29", "23880", "SELL", 1300, 121),
        ],
        latest_positions=[
            _position("94320", quantity=1200, average_price=155.2, market_value=182760),
            _position("94340", quantity=1100, average_price=153.9, market_value=169290),
            _position("66590", quantity=1600, average_price=145, market_value=166400),
            _position("24370", quantity=100, average_price=1235, market_value=135200),
        ],
    )

    assert sum(pos["cost_basis"] for pos in state["positions"]) == pytest.approx(659070)
    assert state["market_value"] == pytest.approx(653650)
    assert state["new_unrealized_pnl"] == pytest.approx(-5420)
    assert sum(pos["unrealized_pnl"] for pos in state["positions"]) == pytest.approx(-5420)
    assert state["realized_pnl"] == pytest.approx(-58800)
    assert state["realized_pnl"] + state["new_unrealized_pnl"] == pytest.approx(-64220)
    assert state["total_equity"] - state["runtime_evaluation_capital"] == pytest.approx(-64220)
    assert state["cash"] == pytest.approx(282130)
    assert len(state["positions"]) == 4


def _project(
    tmp_path: Path,
    events: list[tuple[str, str, str, float, float]],
    *,
    latest_positions: list[dict],
) -> dict:
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-initial",
            "environment": "historical",
            "source": "fixture",
            "as_of": "2026-01-01",
            "positions": [],
            "cash": 1_000_000,
            "runtime_evaluation_capital": 1_000_000,
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
            "created_at": "2026-01-01",
        },
    )
    _write_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl", [_order(*event) for event in events])
    _write_jsonl(runtime_root / "persistent_ledger" / "executions.jsonl", [_execution(*event) for event in events])
    _write_jsonl(runtime_root / "persistent_ledger" / "positions.jsonl", latest_positions)

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date=events[-1][0],
        mode="historical",
    )

    assert result.status == "PASS"
    return json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))


def _order(business_date: str, symbol: str, side: str, quantity: float, price: float) -> dict:
    return {
        "record_type": "order",
        "source": "runtime_v2_submit_pipeline",
        "status": "ACCEPTED",
        "order_id": f"submit-{business_date}-{symbol}-{side}-{quantity}",
        "business_date": business_date,
        "pending_plan_id": "pending-phase24h",
        "pending_item_id": f"pending-{business_date}-{symbol}-{side}-{quantity}",
        "side": side,
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "issue_code_normalization": {"broker_issue_code": symbol},
        "record_id": f"ledger-order-submit-{business_date}-{symbol}-{side}-{quantity}",
    }


def _execution(business_date: str, symbol: str, side: str, quantity: float, price: float) -> dict:
    return {
        "record_type": "execution",
        "source": "runtime_v2_execution_readonly",
        "execution_evidence_type": "execution_equivalent",
        "execution_id": f"execution-equivalent:{business_date}:{symbol}:{side}:{quantity}:{price}",
        "order_id": f"submit-{business_date}-{symbol}-{side}-{quantity}",
        "business_date": business_date,
        "mode": "historical",
        "side": side,
        "symbol": symbol,
        "quantity": quantity,
        "filled_quantity": quantity,
        "remaining_quantity": 0,
        "price": price,
        "average_price": price,
        "cash_effect": quantity * price,
        "dedup_key": f"runtime_v2_execution_equivalent:{business_date}:{symbol}:{side}:{quantity}:{price}",
        "executed_at": f"{business_date}T09:00:00+09:00",
    }


def _position(symbol: str, *, quantity: float, average_price: float, market_value: float) -> dict:
    return {
        "record_type": "position",
        "source": "runtime_v2_execution_readonly",
        "symbol": symbol,
        "position_key": symbol,
        "quantity": quantity,
        "average_price": average_price,
        "market_value": market_value,
        "as_of": "2026-01-01T09:00:00+09:00",
        "recorded_at": "2026-01-01T09:00:00+09:00",
        "record_id": f"ledger-position-{symbol}",
    }


def _position_by_symbol(state: dict, symbol: str) -> dict:
    return next(position for position in state["positions"] if position["symbol"] == symbol)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")

