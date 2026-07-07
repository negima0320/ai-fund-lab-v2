import pytest

from ai_fund_lab_v2.runtime_v2.asset.builder import (
    build_current_asset_state,
    build_current_asset_state_from_orders,
)
from ai_fund_lab_v2.runtime_v2.ledger.models import (
    LedgerCashRecord,
    LedgerPositionRecord,
)


def test_positions_and_cash_build_confirmed_asset_state():
    state = build_current_asset_state(
        environment="demo",
        positions=(_position_record(),),
        cash_records=(_cash_record(),),
        source="broker_positions",
        as_of="2026-07-07T00:00:00Z",
    )

    assert state.current_positions_unknown is False
    assert state.cash_unknown is False
    assert state.buying_power_unknown is False
    assert state.current_state_confirmed_empty is False
    assert state.market_value == 250000
    assert state.total_equity == 350000
    assert state.review_required is False


def test_empty_positions_and_cash_build_confirmed_empty_candidate():
    state = build_current_asset_state(
        environment="demo",
        positions=(),
        cash_records=(_cash_record(),),
        source="broker_positions",
        as_of="2026-07-07T00:00:00Z",
    )

    assert state.positions == ()
    assert state.current_state_confirmed_empty is True
    assert state.cash_unknown is False
    assert state.buying_power_unknown is False


def test_missing_positions_are_unknown_not_empty():
    state = build_current_asset_state(
        environment="demo",
        positions=None,
        cash_records=(_cash_record(),),
        source="broker_positions",
        as_of="2026-07-07T00:00:00Z",
    )

    assert state.positions is None
    assert state.current_positions_unknown is True
    assert state.current_state_confirmed_empty is False


def test_missing_cash_sets_cash_and_buying_power_unknown():
    state = build_current_asset_state(
        environment="demo",
        positions=(_position_record(),),
        cash_records=(),
        source="broker_positions",
        as_of="2026-07-07T00:00:00Z",
    )

    assert state.cash is None
    assert state.buying_power is None
    assert state.cash_unknown is True
    assert state.buying_power_unknown is True
    assert state.total_equity is None


def test_broker_orders_fallback_requires_review_and_is_not_production_equivalent():
    state = build_current_asset_state(
        environment="demo",
        positions=(_position_record(source="broker_orders_fallback"),),
        cash_records=(_cash_record(),),
        source="broker_orders_fallback",
        as_of="2026-07-07T00:00:00Z",
    )

    assert state.review_required is True
    assert state.production_equivalent is False
    assert state.current_state_confirmed_empty is False


def test_orders_alone_cannot_build_asset_state():
    with pytest.raises(ValueError, match="orders alone cannot build"):
        build_current_asset_state_from_orders([])


def _position_record(source: str = "broker_positions") -> LedgerPositionRecord:
    return LedgerPositionRecord(
        record_id="pos-1",
        record_type="position",
        schema_version="1",
        environment="demo",
        source=source,
        created_at="2026-07-07T00:00:00Z",
        dedup_key="pos-1",
        position_key="7203",
        symbol="7203",
        quantity=100,
        average_price=2500,
        market_value=250000,
        as_of="2026-07-07T00:00:00Z",
    )


def _cash_record() -> LedgerCashRecord:
    return LedgerCashRecord(
        record_id="cash-1",
        record_type="cash",
        schema_version="1",
        environment="demo",
        source="broker_cash",
        created_at="2026-07-07T00:00:00Z",
        dedup_key="cash-1",
        cash_key="cash-1",
        cash=100000,
        buying_power=50000,
        currency="JPY",
        as_of="2026-07-07T00:00:00Z",
    )

