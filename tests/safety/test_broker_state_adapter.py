from decimal import Decimal

from ai_fund_lab_v2.broker import BrokerBalanceSnapshot, BrokerOrderSnapshot, BrokerPositionSnapshot
from ai_fund_lab_v2.safety import build_broker_state_from_snapshots, build_mock_portfolio_state_from_broker_state


def test_broker_snapshots_convert_to_broker_state() -> None:
    balance = BrokerBalanceSnapshot(
        snapshot_id="balance-snapshot-1",
        as_of="2999-01-01T00:00:00+00:00",
        cash_available=Decimal("1000000"),
        buying_power=Decimal("800000"),
    )
    positions = (
        BrokerPositionSnapshot(
            snapshot_id="position-snapshot-1",
            issue_code="7203",
            quantity=Decimal("100"),
            average_price=Decimal("2500"),
            account_type="cash",
        ),
    )
    orders = (
        BrokerOrderSnapshot(
            snapshot_id="order-snapshot-1",
            order_id="ORD-1",
            issue_code="7203",
            side="buy",
            quantity=Decimal("100"),
            remaining_quantity=Decimal("60"),
            status="open",
        ),
    )

    broker_state = build_broker_state_from_snapshots(
        balance_snapshot=balance,
        position_snapshots=positions,
        order_snapshots=orders,
    )

    assert broker_state.cash == Decimal("1000000")
    assert broker_state.buying_power == Decimal("800000")
    assert broker_state.source_snapshot_id == "balance-snapshot-1"
    assert broker_state.positions[0].symbol == "7203"
    assert broker_state.positions[0].quantity == Decimal("100")
    assert broker_state.open_orders[0].order_id == "ORD-1"
    assert broker_state.open_orders[0].quantity == Decimal("60")


def test_mock_portfolio_state_matches_broker_state() -> None:
    broker_state = build_broker_state_from_snapshots(
        balance_snapshot=BrokerBalanceSnapshot(
            snapshot_id="balance-snapshot-1",
            as_of="2999-01-01T00:00:00+00:00",
            cash_available=Decimal("1000000"),
            buying_power=Decimal("800000"),
        ),
        position_snapshots=(BrokerPositionSnapshot(issue_code="7203", quantity=Decimal("100"), account_type="cash"),),
        order_snapshots=(BrokerOrderSnapshot(order_id="ORD-1", issue_code="7203", side="buy", remaining_quantity=Decimal("60"), status="open"),),
    )

    portfolio_state = build_mock_portfolio_state_from_broker_state(broker_state)

    assert portfolio_state.cash == broker_state.cash
    assert portfolio_state.buying_power == broker_state.buying_power
    assert portfolio_state.positions[0].symbol == broker_state.positions[0].symbol
    assert portfolio_state.open_orders == broker_state.open_orders
