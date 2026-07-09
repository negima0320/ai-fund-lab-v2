"""Simulation Broker adapter for Runtime v2 tests.

The adapter returns Runtime v2 Broker ReadOnly snapshots and performs no
external I/O. It is intentionally small: Runtime behavior stays in Runtime v2
components, while this class only replaces the broker boundary.
"""

from __future__ import annotations

from dataclasses import replace

from ai_fund_lab_v2.runtime_v2.broker_readonly.models import BrokerReadOnlyBundle
from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import normalize_broker_readonly_payload
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.simulation.models import (
    SimulationBrokerPosition,
    SimulationBrokerState,
    SimulationSubmitResult,
)


class SimulationBroker:
    """In-memory broker adapter that supports BUY/SELL immediate fills."""

    def __init__(self, state: SimulationBrokerState) -> None:
        self._cash = float(state.cash)
        self._buying_power = float(state.buying_power)
        self._positions = {position.symbol: position for position in state.positions}
        self._orders: list[dict[str, object]] = []
        self._executions: list[dict[str, object]] = []
        self._submitted_pending_items: set[str] = set()
        self.realized_pnl_by_execution: dict[str, float] = {}

    def snapshot(self, *, business_date: str) -> BrokerReadOnlyBundle:
        return normalize_broker_readonly_payload(
            environment="simulation",
            source="simulation_broker",
            as_of=business_date,
            orders=tuple(self._orders),
            executions=tuple(self._executions),
            positions=tuple(
                {
                    "position_ref": f"sim-position-{position.symbol}",
                    "position_key": position.symbol,
                    "symbol": position.symbol,
                    "quantity": position.quantity,
                    "average_price": position.average_price,
                    "market_value": position.market_value,
                }
                for position in self._positions.values()
                if position.quantity > 0
            ),
            cash={
                "cash_ref": f"sim-cash-{business_date}",
                "cash": self._cash,
                "buying_power": self._buying_power,
                "currency": "JPY",
            },
        )

    def submit(
        self,
        *,
        pending_plan_id: str,
        item: PendingOrderItem,
        business_date: str,
    ) -> SimulationSubmitResult:
        if item.pending_item_id in self._submitted_pending_items:
            return SimulationSubmitResult(
                status="BLOCKED",
                submitted=False,
                blocked=True,
                review_required=False,
                reason="duplicate pending item submit",
            )
        if item.state == "POST_SEND_UNKNOWN":
            return SimulationSubmitResult(
                status="REVIEW_REQUIRED",
                submitted=False,
                blocked=False,
                review_required=True,
                reason="post_send_unknown cannot auto resubmit",
                post_send_unknown=True,
            )
        if not item.approved:
            return SimulationSubmitResult(
                status="BLOCKED",
                submitted=False,
                blocked=True,
                review_required=False,
                reason="approval required",
            )

        side = item.side.upper()
        amount = float(item.quantity) * float(item.estimated_price)
        if side == "BUY" and amount > self._buying_power:
            return SimulationSubmitResult(
                status="BLOCKED",
                submitted=False,
                blocked=True,
                review_required=False,
                reason="insufficient buying power",
            )
        if side == "SELL":
            position = self._positions.get(item.symbol)
            if position is None or item.quantity > position.quantity:
                return SimulationSubmitResult(
                    status="BLOCKED",
                    submitted=False,
                    blocked=True,
                    review_required=False,
                    reason="insufficient position quantity",
                )

        order_ref = f"sim-order-{pending_plan_id}-{item.pending_item_id}"
        execution_ref = f"sim-exec-{pending_plan_id}-{item.pending_item_id}"
        self._submitted_pending_items.add(item.pending_item_id)
        self._orders.append(
            {
                "order_ref": order_ref,
                "pending_plan_id": pending_plan_id,
                "pending_item_id": item.pending_item_id,
                "symbol": item.symbol,
                "side": side,
                "quantity": item.quantity,
                "order_status": "filled",
                "filled_quantity": item.quantity,
                "remaining_quantity": 0,
                "accepted_at": business_date,
                "updated_at": business_date,
            }
        )
        self._executions.append(
            {
                "execution_ref": execution_ref,
                "order_ref": order_ref,
                "execution_key": execution_ref,
                "symbol": item.symbol,
                "side": side,
                "quantity": item.quantity,
                "price": item.estimated_price,
                "executed_at": business_date,
            }
        )
        realized_pnl = self._apply_fill(item)
        if realized_pnl is not None:
            self.realized_pnl_by_execution[execution_ref] = realized_pnl
        return SimulationSubmitResult(
            status="ACCEPTED",
            submitted=True,
            blocked=False,
            review_required=False,
            reason="simulated fill accepted",
            order_ref=order_ref,
            execution_ref=execution_ref,
            realized_pnl=realized_pnl,
        )

    def _apply_fill(self, item: PendingOrderItem) -> float | None:
        side = item.side.upper()
        amount = float(item.quantity) * float(item.estimated_price)
        if side == "BUY":
            existing = self._positions.get(item.symbol)
            old_quantity = existing.quantity if existing else 0.0
            old_cost = old_quantity * (existing.average_price if existing else 0.0)
            new_quantity = old_quantity + item.quantity
            average_price = (old_cost + amount) / new_quantity
            self._positions[item.symbol] = SimulationBrokerPosition(
                symbol=item.symbol,
                quantity=new_quantity,
                average_price=average_price,
                market_value=new_quantity * item.estimated_price,
            )
            self._cash -= amount
            self._buying_power -= amount
            return None

        position = self._positions[item.symbol]
        realized_pnl = (item.estimated_price - position.average_price) * item.quantity
        remaining_quantity = position.quantity - item.quantity
        self._cash += amount
        self._buying_power += amount
        if remaining_quantity <= 0:
            del self._positions[item.symbol]
        else:
            self._positions[item.symbol] = replace(
                position,
                quantity=remaining_quantity,
                market_value=remaining_quantity * item.estimated_price,
            )
        return realized_pnl
