"""Order plan builder skeleton for Runtime v2."""

from __future__ import annotations

import hashlib

from ai_fund_lab_v2.runtime_v2.planning.models import (
    CapitalAllocationSignal,
    DailyPlan,
    OrderPlan,
    OrderPlanItem,
    PlanningDecisionStatus,
    PlanningInput,
    PlanningResult,
    SafetySignal,
)


def build_order_plan(input: PlanningInput) -> PlanningResult:
    """Build an OrderPlan from provided planning inputs without AI inference."""

    if input.asset_state is None:
        return _blocked_result(input, "asset_state missing")

    items = tuple(_build_item(input, signal) for signal in input.ai_signals)
    blocked = any(item.blocked for item in items)
    review_required = any(item.review_required for item in items)
    status = _status_for_items(items, blocked, review_required)
    order_plan = OrderPlan(
        schema_version="1",
        order_plan_id=_plan_id(input.environment, input.business_date, input.ai_signals),
        environment=input.environment,
        business_date=input.business_date,
        target_session_date=input.target_session_date,
        status=status,
        items=items,
        source_ai_signal_ids=tuple(signal.signal_id for signal in input.ai_signals),
        source_allocation_ids=tuple(
            allocation.allocation_id for allocation in input.capital_allocations
        ),
        source_safety_ids=tuple(signal.safety_id for signal in input.safety_signals),
        asset_state_id=input.asset_state.asset_state_id,
        created_at=input.business_date,
        review_required=review_required,
        blocked=blocked,
    )
    daily_plan = DailyPlan(
        daily_plan_id=f"daily-{order_plan.order_plan_id}",
        environment=input.environment,
        business_date=input.business_date,
        target_session_date=input.target_session_date,
        order_plan_id=order_plan.order_plan_id,
        status=status,
        summary=f"{len(items)} item(s)",
        created_at=input.business_date,
    )
    return PlanningResult(
        daily_plan=daily_plan,
        order_plan=order_plan,
        status=status,
        review_required=review_required,
        blocked=blocked,
    )


def _build_item(input: PlanningInput, signal) -> OrderPlanItem:
    allocation = _find_allocation(input.capital_allocations, signal.symbol, signal.side)
    safety = _find_safety(input.safety_signals, signal.symbol, signal.side)
    blocked = False
    review_required = False
    reasons: list[str] = []

    if signal.side == "BUY":
        if input.asset_state.cash_unknown:
            blocked = True
            reasons.append("cash unknown")
        if input.asset_state.buying_power_unknown:
            blocked = True
            reasons.append("buying power unknown")
        if allocation and input.asset_state.buying_power is not None:
            if allocation.cash_required > input.asset_state.buying_power:
                blocked = True
                reasons.append("cash_required exceeds buying_power")
    if input.asset_state.current_positions_unknown:
        review_required = True
        reasons.append("positions unknown")
    if safety:
        if safety.blocked or not safety.allowed:
            blocked = True
            reasons.append(safety.reason or "safety blocked")
        if safety.review_required:
            review_required = True
            reasons.append(safety.reason or "safety review required")

    estimated_amount = allocation.allocated_amount if allocation else 0.0
    estimated_price = 0.0
    quantity = 0.0
    status = (
        PlanningDecisionStatus.BLOCKED
        if blocked
        else PlanningDecisionStatus.REVIEW_REQUIRED
        if review_required
        else PlanningDecisionStatus.CREATED
    )
    return OrderPlanItem(
        order_plan_item_id=f"opi-{signal.signal_id}",
        symbol=signal.symbol,
        side=signal.side,
        quantity=quantity,
        estimated_price=estimated_price,
        estimated_amount=estimated_amount,
        source_signal_id=signal.signal_id,
        allocation_id=allocation.allocation_id if allocation else "",
        safety_id=safety.safety_id if safety else "",
        status=status,
        review_required=review_required,
        blocked=blocked,
        reason="; ".join(reasons),
    )


def _blocked_result(input: PlanningInput, reason: str) -> PlanningResult:
    order_plan_id = _plan_id(input.environment, input.business_date, input.ai_signals)
    order_plan = OrderPlan(
        schema_version="1",
        order_plan_id=order_plan_id,
        environment=input.environment,
        business_date=input.business_date,
        target_session_date=input.target_session_date,
        status=PlanningDecisionStatus.BLOCKED,
        items=(),
        source_ai_signal_ids=tuple(signal.signal_id for signal in input.ai_signals),
        source_allocation_ids=tuple(
            allocation.allocation_id for allocation in input.capital_allocations
        ),
        source_safety_ids=tuple(signal.safety_id for signal in input.safety_signals),
        asset_state_id="UNKNOWN",
        created_at=input.business_date,
        review_required=True,
        blocked=True,
    )
    daily_plan = DailyPlan(
        daily_plan_id=f"daily-{order_plan_id}",
        environment=input.environment,
        business_date=input.business_date,
        target_session_date=input.target_session_date,
        order_plan_id=order_plan_id,
        status=PlanningDecisionStatus.BLOCKED,
        summary=reason,
        created_at=input.business_date,
    )
    return PlanningResult(
        daily_plan=daily_plan,
        order_plan=order_plan,
        status=PlanningDecisionStatus.BLOCKED,
        review_required=True,
        blocked=True,
        errors=(reason,),
    )


def _find_allocation(
    allocations: tuple[CapitalAllocationSignal, ...],
    symbol: str,
    side: str,
) -> CapitalAllocationSignal | None:
    return next(
        (item for item in allocations if item.symbol == symbol and item.side == side),
        None,
    )


def _find_safety(
    safety_signals: tuple[SafetySignal, ...],
    symbol: str,
    side: str,
) -> SafetySignal | None:
    return next(
        (item for item in safety_signals if item.symbol == symbol and item.side == side),
        None,
    )


def _status_for_items(
    items: tuple[OrderPlanItem, ...],
    blocked: bool,
    review_required: bool,
) -> PlanningDecisionStatus:
    if not items:
        return PlanningDecisionStatus.NO_ACTION
    if blocked:
        return PlanningDecisionStatus.BLOCKED
    if review_required:
        return PlanningDecisionStatus.REVIEW_REQUIRED
    return PlanningDecisionStatus.CREATED


def _plan_id(environment: str, business_date: str, signals) -> str:
    raw = "|".join((environment, business_date, *(signal.signal_id for signal in signals)))
    return "order-plan-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

