from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.asset.runtime_owned_fill_projection import (
    project_runtime_owned_fills_to_current,
)
from ai_fund_lab_v2.runtime_v2.ledger.performance_events import (
    load_canonical_execution_events,
    resolve_performance_fills,
)
from ai_fund_lab_v2.runtime_v2.planning.morning_pipeline import _budget_no_signal_reason


def test_phase17_bs_five_buy_smoke_resolves_five_canonical_performance_fills(tmp_path):
    runtime_root = tmp_path / ".runtime"
    symbols = ("8105", "6740", "6659", "3667", "4564")
    quantities = (1100, 3000, 2800, 5600, 8500)
    prices = (100.0, 101.0, 102.0, 103.0, 104.0)
    orders = [
        _submit_order(symbol, quantity=quantity, price=price, pending_item_id=f"item-{symbol}")
        for symbol, quantity, price in zip(symbols, quantities, prices)
    ]
    executions = []
    for symbol, quantity, price in zip(symbols, quantities, prices):
        executions.append(_broker_detail_execution(symbol, quantity=quantity, price=price))
        executions.append(_execution_equivalent(symbol, quantity=quantity, price=price))
    _write_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl", orders)
    _write_jsonl(runtime_root / "persistent_ledger" / "executions.jsonl", executions)

    resolution = load_canonical_execution_events(
        executions_path=runtime_root / "persistent_ledger" / "executions.jsonl",
        orders_path=runtime_root / "persistent_ledger" / "orders.jsonl",
    )

    assert resolution.status == "PASS"
    assert resolution.raw_execution_count == 10
    assert resolution.raw_broker_detail_count == 5
    assert resolution.canonical_execution_count == 5
    assert {event.symbol for event in resolution.events} == set(symbols)
    assert sum(event.quantity for event in resolution.events) == sum(quantities)
    assert sum(event.gross_notional for event in resolution.events) == sum(q * p for q, p in zip(quantities, prices))
    assert all(event.evidence_type == "execution_equivalent" for event in resolution.events)
    assert all(event.pending_item_id == f"item-{event.symbol}" for event in resolution.events)


def test_phase17_bs_canonical_resolution_is_idempotent_with_duplicate_equivalent_rows():
    executions = [
        _broker_detail_execution("8105", quantity=100, price=100),
        _execution_equivalent("8105", quantity=100, price=100),
        _execution_equivalent("8105", quantity=100, price=100),
    ]

    first = resolve_performance_fills(executions=executions, orders=[_submit_order("8105", quantity=100, price=100)])
    second = resolve_performance_fills(executions=executions, orders=[_submit_order("8105", quantity=100, price=100)])

    assert first.status == "PASS"
    assert first.canonical_execution_count == 1
    assert first.duplicate_canonical_count == 1
    assert second.canonical_execution_count == first.canonical_execution_count


def test_phase17_bs_missing_execution_equivalent_fails_closed_for_performance():
    resolution = resolve_performance_fills(
        executions=[_broker_detail_execution("8105", quantity=100, price=100)],
        orders=[_submit_order("8105", quantity=100, price=100)],
    )

    assert resolution.status == "REVIEW_REQUIRED"
    assert resolution.reason == "canonical_execution_equivalent_missing"
    assert resolution.canonical_execution_count == 0
    assert resolution.missing_canonical_equivalent_count == 1


def test_phase17_bs_sell_fill_uses_same_canonical_contract():
    resolution = resolve_performance_fills(
        executions=[
            _broker_detail_execution("8105", side="SELL", quantity=100, price=120),
            _execution_equivalent("8105", side="SELL", quantity=100, price=120),
        ],
        orders=[_submit_order("8105", side="SELL", quantity=100, price=120)],
    )

    assert resolution.status == "PASS"
    assert resolution.canonical_execution_count == 1
    assert resolution.events[0].side == "SELL"
    assert resolution.events[0].gross_notional == 12_000


def test_phase17_bs_runtime_owned_projection_counts_canonical_fills_once(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-initial",
            "environment": "historical",
            "source": "fixture",
            "as_of": "2026-07-06",
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
            "created_at": "2026-07-06",
        },
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "orders.jsonl",
        [
            _submit_order("8105", quantity=100, price=100),
            _submit_order("6740", quantity=200, price=200),
        ],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _broker_detail_execution("8105", quantity=100, price=100),
            _execution_equivalent("8105", quantity=100, price=100),
            _broker_detail_execution("6740", quantity=200, price=200),
            _execution_equivalent("6740", quantity=200, price=200),
        ],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [
            _position("8105", quantity=100, average_price=100, market_value=11_000),
            _position("6740", quantity=200, average_price=200, market_value=42_000),
        ],
    )

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2026-07-06",
        mode="historical",
    )

    assert result.status == "PASS"
    assert result.projected_cash == 1_000_000 - 10_000 - 40_000
    assert result.projected_cash != 1_000_000 - (10_000 + 40_000) * 2
    assert result.projected_market_value == 53_000
def _submit_order(
    symbol: str,
    *,
    side: str = "BUY",
    quantity: float,
    price: float,
    pending_item_id: str | None = None,
) -> dict:
    return {
        "record_type": "order",
        "source": "runtime_v2_submit_pipeline",
        "status": "ACCEPTED",
        "order_id": f"submit-{symbol}-{side}",
        "business_date": "2026-07-06",
        "pending_plan_id": "pending-bs",
        "pending_item_id": pending_item_id or f"pending-{symbol}",
        "side": side,
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "issue_code_normalization": {"broker_issue_code": symbol},
        "record_id": f"ledger-order-submit-{symbol}-{side}",
    }


def _broker_detail_execution(
    symbol: str,
    *,
    side: str = "BUY",
    quantity: float,
    price: float,
) -> dict:
    return {
        "record_type": "execution",
        "source": "runtime_v2_execution_readonly_simulation",
        "execution_evidence_type": "broker_detail_execution",
        "execution_id": f"broker-detail-{symbol}-{side}",
        "order_id": f"broker-order-{symbol}-{side}",
        "business_date": "2026-07-06",
        "mode": "historical",
        "side": side,
        "symbol": symbol,
        "quantity": quantity,
        "filled_quantity": quantity,
        "remaining_quantity": 0,
        "price": price,
        "average_price": price,
        "cash_effect": quantity * price,
        "dedup_key": f"broker-detail:{symbol}:{side}",
        "executed_at": "2026-07-06T09:00:00+09:00",
    }


def _execution_equivalent(
    symbol: str,
    *,
    side: str = "BUY",
    quantity: float,
    price: float,
) -> dict:
    return {
        "record_type": "execution",
        "source": "runtime_v2_execution_readonly",
        "execution_evidence_type": "execution_equivalent",
        "execution_id": f"execution-equivalent:{symbol}:{side}",
        "order_id": f"broker-order-{symbol}-{side}",
        "business_date": "2026-07-06",
        "mode": "historical",
        "side": side,
        "symbol": symbol,
        "quantity": quantity,
        "filled_quantity": quantity,
        "remaining_quantity": 0,
        "price": price,
        "average_price": price,
        "cash_effect": quantity * price,
        "source_order_hash": f"broker-order-{symbol}-{side}",
        "source_broker_order_hash": f"broker-order-{symbol}-{side}",
        "dedup_key": f"runtime_v2_execution_equivalent:{symbol}:{side}",
        "executed_at": "2026-07-06T09:00:00+09:00",
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
        "as_of": "2026-07-06T09:00:00+09:00",
        "recorded_at": "2026-07-06T09:00:00+09:00",
        "record_id": f"ledger-position-{symbol}",
    }


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
