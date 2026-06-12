from __future__ import annotations

from decimal import Decimal

from ai_fund_lab_v2.safety import (
    BrokerPositionState,
    BrokerState,
    OpenOrderState,
    PortfolioPositionState,
    PortfolioState,
    SafetyStatus,
    reconcile_states,
)

FRESH_AS_OF = "2999-01-01T00:00:00+00:00"


def portfolio_state(
    *,
    cash: str = "1000",
    buying_power: str = "900",
    positions: tuple[PortfolioPositionState, ...] = (),
    open_orders: tuple[OpenOrderState, ...] = (),
) -> PortfolioState:
    return PortfolioState(
        cash=Decimal(cash),
        buying_power=Decimal(buying_power),
        positions=positions,
        open_orders=open_orders,
        as_of=FRESH_AS_OF,
    )


def broker_state(
    *,
    cash: str = "1000",
    buying_power: str = "900",
    positions: tuple[BrokerPositionState, ...] = (),
    open_orders: tuple[OpenOrderState, ...] = (),
    source_snapshot_id: str | None = "broker-snapshot-1",
) -> BrokerState:
    return BrokerState(
        cash=Decimal(cash),
        buying_power=Decimal(buying_power),
        positions=positions,
        open_orders=open_orders,
        as_of=FRESH_AS_OF,
        source_snapshot_id=source_snapshot_id,
    )


def test_reconciliation_ok_when_states_match() -> None:
    portfolio = portfolio_state(
        positions=(PortfolioPositionState(symbol="7203", quantity=Decimal("100")),),
        open_orders=(OpenOrderState(order_id="ORD-1", symbol="7203", side="buy", quantity=Decimal("100")),),
    )
    broker = broker_state(
        positions=(BrokerPositionState(symbol="7203", quantity=Decimal("100")),),
        open_orders=(OpenOrderState(order_id="ORD-1", symbol="7203", side="buy", quantity=Decimal("100")),),
    )

    result = reconcile_states(portfolio, broker)

    assert result.status == SafetyStatus.OK
    assert result.issues == ()


def test_cash_mismatch_is_halt() -> None:
    result = reconcile_states(portfolio_state(cash="999"), broker_state(cash="1000"))

    assert result.status == SafetyStatus.HALT
    assert _codes(result) == {"cash_mismatch"}


def test_buying_power_mismatch_is_halt() -> None:
    result = reconcile_states(portfolio_state(buying_power="899"), broker_state(buying_power="900"))

    assert result.status == SafetyStatus.HALT
    assert _codes(result) == {"buying_power_mismatch"}


def test_position_quantity_mismatch_is_halt() -> None:
    portfolio = portfolio_state(positions=(PortfolioPositionState(symbol="7203", quantity=Decimal("100")),))
    broker = broker_state(positions=(BrokerPositionState(symbol="7203", quantity=Decimal("90")),))

    result = reconcile_states(portfolio, broker)

    assert result.status == SafetyStatus.HALT
    assert "position_quantity_mismatch" in _codes(result)


def test_broker_only_position_is_halt() -> None:
    result = reconcile_states(
        portfolio_state(),
        broker_state(positions=(BrokerPositionState(symbol="7203", quantity=Decimal("90")),)),
    )

    assert result.status == SafetyStatus.HALT
    assert "unknown_position" in _codes(result)


def test_portfolio_only_position_is_halt() -> None:
    result = reconcile_states(
        portfolio_state(positions=(PortfolioPositionState(symbol="7203", quantity=Decimal("90")),)),
        broker_state(),
    )

    assert result.status == SafetyStatus.HALT
    assert "position_missing_in_broker" in _codes(result)


def test_side_mismatch_is_halt() -> None:
    result = reconcile_states(
        portfolio_state(positions=(PortfolioPositionState(symbol="7203", quantity=Decimal("100"), side="long"),)),
        broker_state(positions=(BrokerPositionState(symbol="7203", quantity=Decimal("100"), side="short"),)),
    )

    assert result.status == SafetyStatus.HALT
    assert "position_side_mismatch" in _codes(result)


def test_account_type_mismatch_is_halt() -> None:
    result = reconcile_states(
        portfolio_state(positions=(PortfolioPositionState(symbol="7203", quantity=Decimal("100"), account_type="cash"),)),
        broker_state(positions=(BrokerPositionState(symbol="7203", quantity=Decimal("100"), account_type="margin"),)),
    )

    assert result.status == SafetyStatus.HALT
    assert "position_account_type_mismatch" in _codes(result)


def test_open_order_mismatch_is_halt() -> None:
    result = reconcile_states(
        portfolio_state(open_orders=(OpenOrderState(order_id="ORD-1", symbol="7203", side="buy", quantity=Decimal("100")),)),
        broker_state(open_orders=(OpenOrderState(order_id="ORD-2", symbol="7203", side="buy", quantity=Decimal("100")),)),
    )

    assert result.status == SafetyStatus.HALT
    assert "open_order_mismatch" in _codes(result)


def test_duplicate_open_order_suspected_is_halt() -> None:
    duplicate_orders = (
        OpenOrderState(order_id="ORD-1", symbol="7203", side="buy", quantity=Decimal("100")),
        OpenOrderState(order_id="ORD-2", symbol="7203", side="buy", quantity=Decimal("100")),
    )

    result = reconcile_states(portfolio_state(open_orders=duplicate_orders), broker_state(open_orders=duplicate_orders))

    assert result.status == SafetyStatus.HALT
    assert "duplicate_open_order_suspected" in _codes(result)


def test_missing_broker_snapshot_id_is_warning() -> None:
    result = reconcile_states(portfolio_state(), broker_state(source_snapshot_id=None))

    assert result.status == SafetyStatus.WARNING
    assert _codes(result) == {"broker_snapshot_id_missing"}


def test_warning_and_halt_mixed_results_in_halt() -> None:
    result = reconcile_states(portfolio_state(cash="999"), broker_state(cash="1000", source_snapshot_id=None))

    assert result.status == SafetyStatus.HALT
    assert {"cash_mismatch", "broker_snapshot_id_missing"}.issubset(_codes(result))


def _codes(result) -> set[str]:
    return {issue.code for issue in result.issues}
