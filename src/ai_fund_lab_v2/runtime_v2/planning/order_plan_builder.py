"""OrderPlan integration helpers for Runtime v2 Pending Runtime."""

from __future__ import annotations

from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import (
    BrokerCapability,
    is_symbol_allowed_by_capability,
)
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingOrderPlan
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.planning.models import OrderPlan, PlanningResult


def order_plan_to_pending_items(order_plan: OrderPlan) -> tuple[PendingOrderItem, ...]:
    return tuple(
        PendingOrderItem(
            pending_item_id=item.order_plan_item_id,
            symbol=item.symbol,
            side=item.side,
            quantity=item.quantity,
            order_type="PLACEHOLDER",
            estimated_price=item.estimated_price,
            estimated_amount=item.estimated_amount,
            approved=False,
            state=item.status.value,
            price_source=item.price_source,
            price_as_of=item.price_as_of,
            price_confidence=item.price_confidence,
            price_required=item.price_required,
            safety_decision_id=item.safety_decision_id,
            safety_policy_version=item.safety_policy_version,
            safety_source=item.safety_source,
            safety_decision=item.safety_decision,
            safety_reason=item.safety_reason,
        )
        for item in order_plan.items
        if not item.blocked
    )


def order_plan_to_pending_items_with_capability(
    order_plan: OrderPlan,
    capability: BrokerCapability,
) -> tuple[PendingOrderItem, ...]:
    """Convert order plan items after applying broker capability guards."""

    return tuple(
        PendingOrderItem(
            pending_item_id=item.order_plan_item_id,
            symbol=item.symbol,
            side=item.side,
            quantity=item.quantity,
            order_type="PLACEHOLDER",
            estimated_price=item.estimated_price,
            estimated_amount=item.estimated_amount,
            approved=False,
            state=item.status.value,
            price_source=item.price_source,
            price_as_of=item.price_as_of,
            price_confidence=item.price_confidence,
            price_required=item.price_required,
            safety_decision_id=item.safety_decision_id,
            safety_policy_version=item.safety_policy_version,
            safety_source=item.safety_source,
            safety_decision=item.safety_decision,
            safety_reason=item.safety_reason,
        )
        for item in order_plan.items
        if not item.blocked and is_symbol_allowed_by_capability(item.symbol, capability)
    )


def promote_order_plan_result_to_pending(
    *,
    result: PlanningResult,
    source_order_plan_path: str,
    source_order_plan_hash: str,
) -> PendingOrderPlan:
    if not source_order_plan_path:
        raise ValueError("source_order_plan_path is required")
    if not source_order_plan_hash:
        raise ValueError("source_order_plan_hash is required")
    return promote_order_plan_to_pending(
        order_plan_id=result.order_plan.order_plan_id,
        source_order_plan_path=source_order_plan_path,
        source_order_plan_hash=source_order_plan_hash,
        environment=result.order_plan.environment,
        plan_created_date=result.order_plan.business_date,
        intended_submit_date=result.order_plan.target_session_date,
        target_session_date=result.order_plan.target_session_date,
        items=order_plan_to_pending_items(result.order_plan),
    )
