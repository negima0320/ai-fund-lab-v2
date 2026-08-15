import pytest

from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import (
    normalize_broker_readonly_payload,
)


def test_normalizer_returns_broker_readonly_bundle():
    bundle = normalize_broker_readonly_payload(
        environment="demo",
        source="broker_readonly",
        as_of="2026-07-07T00:00:00Z",
        orders=(_order_payload(),),
        executions=(_execution_payload(),),
        positions=(_position_payload(),),
        cash=_cash_payload(),
    )

    assert bundle.environment == "demo"
    assert bundle.source == "broker_readonly"
    assert len(bundle.orders) == 1
    assert len(bundle.executions) == 1
    assert len(bundle.positions) == 1
    assert bundle.cash.cash == 100000


def test_phase29_l21t_x_normalizer_uses_cash_available_when_cash_field_missing():
    bundle = normalize_broker_readonly_payload(
        environment="historical",
        source="runtime_v2_execution_readonly_simulation",
        as_of="2023-06-23",
        cash={"cash_ref": "historical-cash-2023-06-23", "cash_available": "129890.0", "buying_power": "129890.0"},
    )

    assert bundle.cash.cash == 129890.0
    assert bundle.cash.buying_power == 129890.0


def test_normalizer_requires_environment_source_and_as_of():
    with pytest.raises(ValueError, match="environment is required"):
        normalize_broker_readonly_payload(environment="", source="src", as_of="ts")
    with pytest.raises(ValueError, match="source is required"):
        normalize_broker_readonly_payload(environment="demo", source="", as_of="ts")
    with pytest.raises(ValueError, match="as_of is required"):
        normalize_broker_readonly_payload(environment="demo", source="src", as_of="")


def test_normalizer_hashes_raw_broker_refs_and_does_not_store_raw_id():
    bundle = normalize_broker_readonly_payload(
        environment="demo",
        source="broker_readonly",
        as_of="2026-07-07T00:00:00Z",
        orders=({"order_id": "RAW-ORDER-1", **_order_payload()},),
    )

    order = bundle.orders[0]
    assert order.order_ref_hash.startswith("sha256:")
    assert order.order_ref_hash != "RAW-ORDER-1"
    assert not hasattr(order, "order_id")


def test_fallback_source_marks_review_and_not_production_equivalent():
    bundle = normalize_broker_readonly_payload(
        environment="demo",
        source="broker_orders_fallback",
        as_of="2026-07-07T00:00:00Z",
        orders=(_order_payload(),),
    )

    assert bundle.review_required is True
    assert bundle.production_equivalent is False
    assert bundle.orders[0].review_required is True
    assert bundle.orders[0].production_equivalent is False


def _order_payload():
    return {
        "order_ref": "ORDER-1",
        "pending_plan_id": "pending-1",
        "pending_item_id": "item-1",
        "symbol": "7203",
        "side": "BUY",
        "quantity": 100,
        "order_status": "accepted",
        "filled_quantity": 0,
        "remaining_quantity": 100,
        "accepted_at": "2026-07-07T00:00:00Z",
        "updated_at": "2026-07-07T00:00:00Z",
    }


def _execution_payload():
    return {
        "execution_ref": "EXEC-1",
        "order_ref": "ORDER-1",
        "execution_key": "exec-key-1",
        "symbol": "7203",
        "side": "BUY",
        "quantity": 100,
        "price": 2500,
        "executed_at": "2026-07-07T00:01:00Z",
    }


def _position_payload():
    return {
        "position_ref": "POS-1",
        "position_key": "7203",
        "symbol": "7203",
        "quantity": 100,
        "average_price": 2500,
        "market_value": 250000,
    }


def _cash_payload():
    return {
        "cash_ref": "CASH-1",
        "cash": 100000,
        "buying_power": 50000,
        "currency": "JPY",
    }
