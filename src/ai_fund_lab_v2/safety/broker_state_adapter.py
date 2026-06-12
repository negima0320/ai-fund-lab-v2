from __future__ import annotations

from decimal import Decimal
from typing import Any

from ai_fund_lab_v2.broker.models import BrokerBalanceSnapshot, BrokerOrderSnapshot, BrokerPositionSnapshot
from ai_fund_lab_v2.safety.models import BrokerPositionState, BrokerState, OpenOrderState


def broker_snapshot_to_state(
    snapshot: BrokerBalanceSnapshot | tuple[BrokerBalanceSnapshot, tuple[BrokerPositionSnapshot, ...], tuple[BrokerOrderSnapshot, ...]],
) -> BrokerState:
    if isinstance(snapshot, BrokerBalanceSnapshot):
        return build_broker_state_from_snapshots(balance_snapshot=snapshot)
    balance_snapshot, position_snapshots, order_snapshots = snapshot
    return build_broker_state_from_snapshots(
        balance_snapshot=balance_snapshot,
        position_snapshots=position_snapshots,
        order_snapshots=order_snapshots,
    )


def build_broker_state_from_snapshots(
    *,
    balance_snapshot: BrokerBalanceSnapshot,
    position_snapshots: tuple[BrokerPositionSnapshot, ...] = (),
    order_snapshots: tuple[BrokerOrderSnapshot, ...] = (),
) -> BrokerState:
    return BrokerState(
        cash=balance_snapshot.cash_available,
        buying_power=balance_snapshot.buying_power,
        positions=tuple(_position_to_state(snapshot) for snapshot in position_snapshots),
        open_orders=tuple(_order_to_state(snapshot) for snapshot in order_snapshots if _is_open_order(snapshot)),
        as_of=balance_snapshot.as_of,
        source_snapshot_id=balance_snapshot.snapshot_id,
    )


def _position_to_state(snapshot: BrokerPositionSnapshot) -> BrokerPositionState:
    return BrokerPositionState(
        symbol=snapshot.issue_code,
        quantity=snapshot.quantity,
        side=_normalize_position_side(snapshot.account_type),
        account_type=snapshot.account_type,
        average_price=snapshot.average_price,
    )


def _order_to_state(snapshot: BrokerOrderSnapshot) -> OpenOrderState:
    return OpenOrderState(
        order_id=snapshot.order_id,
        symbol=snapshot.issue_code,
        side=snapshot.side,
        quantity=snapshot.remaining_quantity or snapshot.quantity,
        status=snapshot.status or "open",
    )


def _is_open_order(snapshot: BrokerOrderSnapshot) -> bool:
    status = (snapshot.status or "").lower()
    if not status:
        return True
    return status in {"open", "pending", "partial", "partially_filled", "1", "5"}


def _normalize_position_side(account_type: str) -> str:
    _ = account_type
    return "long"


def decimal_or_zero(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))
