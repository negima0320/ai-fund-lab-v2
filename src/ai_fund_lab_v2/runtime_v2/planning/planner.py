"""Order plan builder skeleton for Runtime v2."""

from __future__ import annotations

import hashlib
import math
from typing import Any

from ai_fund_lab_v2.runtime_v2.planning.models import (
    CapitalAllocationSignal,
    DailyPlan,
    OrderPlan,
    OrderPlanItem,
    PlanningDecisionStatus,
    PlanningInput,
    PlanningResult,
)

SELL_ITEM_QUANTITY_CONTRACT_MISMATCH = "SELL_ITEM_QUANTITY_CONTRACT_MISMATCH"
SELL_ITEM_QUANTITY_CONTRACT_MISSING = "SELL_ITEM_QUANTITY_CONTRACT_MISSING"
SELL_CONTRACT_SOURCE_DECISIONS = frozenset(("REDUCE", "EXIT"))


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
        safety_decision_id=input.runtime_safety.safety_decision_id,
        safety_policy_version=input.runtime_safety.safety_policy_version,
        safety_source=input.runtime_safety.safety_source,
        safety_decision=input.runtime_safety.safety_decision,
        safety_reason=input.runtime_safety.safety_reason,
        asset_state_id=input.asset_state.asset_state_id,
        created_at=input.business_date,
        review_required=review_required,
        blocked=blocked,
        policy_context=_policy_context(input.capital_allocations),
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
    safety = input.runtime_safety
    blocked = False
    review_required = False
    reasons: list[str] = []
    estimated_amount = allocation.allocated_amount if allocation else 0.0
    estimated_price = _estimated_price(allocation)
    quantity = _materialized_quantity(signal.side, allocation, estimated_amount, estimated_price)
    contract_validation = _validate_sell_quantity_contract(
        signal_side=signal.side,
        signal_id=signal.signal_id,
        allocation=allocation,
        materialized_quantity=quantity,
    )
    if contract_validation:
        blocked = True
        reasons.append(contract_validation)

    if signal.side == "BUY":
        if allocation is None or allocation.price_required and allocation.estimated_price <= 0:
            blocked = True
            reasons.append("reliable price source missing")
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
    if signal.side == "SELL":
        if allocation is None or allocation.price_required and allocation.estimated_price <= 0:
            blocked = True
            reasons.append("current position valuation missing")
        position_quantity = _current_position_quantity(input.asset_state, signal.symbol)
        if position_quantity <= 0:
            blocked = True
            reasons.append("sell source current position missing")
        if quantity <= 0:
            blocked = True
            reasons.append("sell quantity missing")
        if quantity > position_quantity:
            blocked = True
            reasons.append("sell quantity exceeds current position")
    if input.asset_state.current_positions_unknown:
        review_required = True
        reasons.append("positions unknown")
    if safety.halt_runtime or safety.emergency_stop or safety.safety_decision == "HALT":
        blocked = True
        reasons.append(safety.safety_reason or "runtime safety halted")
    if safety.safety_decision == "BLOCKED":
        blocked = True
        reasons.append(safety.safety_reason or "runtime safety blocked")
    if safety.review_required or safety.safety_decision == "REVIEW_REQUIRED":
        review_required = True
        reasons.append(safety.safety_reason or "runtime safety review required")
    if signal.side == "BUY" and safety.block_buy:
        review_required = True
        reasons.append(safety.safety_reason or "runtime safety blocks BUY")
    if signal.side == "SELL" and safety.block_sell:
        review_required = True
        reasons.append(safety.safety_reason or "runtime safety blocks SELL")

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
        safety_decision_id=safety.safety_decision_id,
        safety_policy_version=safety.safety_policy_version,
        safety_source=safety.safety_source,
        safety_decision=safety.safety_decision,
        safety_reason=safety.safety_reason,
        status=status,
        review_required=review_required,
        blocked=blocked,
        reason="; ".join(reasons),
        price_source=allocation.price_source if allocation else "",
        price_as_of=allocation.price_as_of if allocation else "",
        price_confidence=allocation.price_confidence if allocation else "",
        price_required=allocation.price_required if allocation else True,
        capital_allocation_amount=estimated_amount,
        policy_version=allocation.policy_version if allocation else "",
        policy_source=allocation.policy_source if allocation else "",
        evaluation_capital=_policy_value(allocation, "evaluation_capital"),
        target_investment_ratio=_policy_value(allocation, "target_investment_ratio"),
        cash_buffer=_policy_value(allocation, "cash_buffer"),
        max_exposure=_policy_value(allocation, "max_exposure"),
        max_positions=_policy_value(allocation, "max_positions"),
        max_buy_order_amount=_policy_value(allocation, "max_buy_order_amount"),
        max_sell_liquidation_amount=_policy_value(allocation, "max_sell_liquidation_amount"),
        min_order_amount=_policy_value(allocation, "min_order_amount"),
        buy_notional_policy=str(_policy_value(allocation, "buy_notional_policy") or ""),
        sell_liquidation_policy=str(_policy_value(allocation, "sell_liquidation_policy") or ""),
        manual_review_threshold=_policy_value(allocation, "manual_review_threshold"),
        sizing_policy_reason=allocation.sizing_policy_reason if allocation else "",
        quantity_contract=dict(allocation.quantity_contract) if allocation and allocation.quantity_contract else None,
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
        safety_decision_id=input.runtime_safety.safety_decision_id,
        safety_policy_version=input.runtime_safety.safety_policy_version,
        safety_source=input.runtime_safety.safety_source,
        safety_decision=input.runtime_safety.safety_decision,
        safety_reason=input.runtime_safety.safety_reason,
        asset_state_id="UNKNOWN",
        created_at=input.business_date,
        review_required=True,
        blocked=True,
        policy_context=_policy_context(input.capital_allocations),
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


def _policy_context(allocations: tuple[CapitalAllocationSignal, ...]) -> dict | None:
    for allocation in allocations:
        if allocation.policy_context:
            return dict(allocation.policy_context)
    return None


def _policy_value(allocation: CapitalAllocationSignal | None, key: str):
    if allocation is None or not allocation.policy_context:
        return None
    return allocation.policy_context.get(key)


def _estimated_price(allocation: CapitalAllocationSignal | None) -> float:
    if allocation is None:
        return 0.0
    return allocation.estimated_price if allocation.estimated_price > 0 else 0.0


def _materialized_quantity(
    side: str,
    allocation: CapitalAllocationSignal | None,
    estimated_amount: float,
    estimated_price: float,
) -> float:
    contract = allocation.quantity_contract if allocation else None
    final_sell_quantity = _authoritative_final_sell_quantity(side, contract)
    if final_sell_quantity is not None:
        return final_sell_quantity
    return _round_lot_quantity(estimated_amount, estimated_price)


def _validate_sell_quantity_contract(
    *,
    signal_side: str,
    signal_id: str,
    allocation: CapitalAllocationSignal | None,
    materialized_quantity: float,
) -> str:
    if str(signal_side).upper() != "SELL":
        return ""
    contract = allocation.quantity_contract if allocation else None
    if not _requires_sell_quantity_contract(signal_id=signal_id, contract=contract):
        return ""
    final_sell_quantity = _authoritative_final_sell_quantity(signal_side, contract)
    if final_sell_quantity is None:
        return SELL_ITEM_QUANTITY_CONTRACT_MISSING
    if not _same_quantity(materialized_quantity, final_sell_quantity):
        return SELL_ITEM_QUANTITY_CONTRACT_MISMATCH
    return ""


def _requires_sell_quantity_contract(
    *,
    signal_id: str,
    contract: dict[str, Any] | None,
) -> bool:
    source_decision = _contract_source_decision(contract)
    if source_decision in SELL_CONTRACT_SOURCE_DECISIONS:
        return True
    normalized_signal_id = str(signal_id or "").lower()
    return normalized_signal_id.startswith("sell-reduce-") or normalized_signal_id.startswith("sell-exit-")


def _authoritative_final_sell_quantity(
    side: str,
    contract: dict[str, Any] | None,
) -> float | None:
    if str(side).upper() != "SELL":
        return None
    if _contract_source_decision(contract) not in SELL_CONTRACT_SOURCE_DECISIONS:
        return None
    if not contract or "final_sell_quantity" not in contract:
        return None
    try:
        final_quantity = float(contract.get("final_sell_quantity"))
    except (TypeError, ValueError):
        return None
    if final_quantity <= 0:
        return None
    return final_quantity


def _contract_source_decision(contract: dict[str, Any] | None) -> str:
    if not contract:
        return ""
    return str(contract.get("source_decision") or contract.get("source_decision_type") or "").upper()


def _same_quantity(left: float, right: float) -> bool:
    return abs(float(left or 0.0) - float(right or 0.0)) < 1e-9


def _current_position_quantity(asset_state, symbol: str) -> float:
    positions = asset_state.positions or ()
    normalized_symbol = str(symbol).strip()
    return float(
        sum(
            float(position.quantity)
            for position in positions
            if str(position.symbol).strip() == normalized_symbol and float(position.quantity) > 0
        )
    )


def _round_lot_quantity(amount: float, price: float) -> float:
    if amount <= 0 or price <= 0:
        return 0.0
    return float(math.floor((amount / price) / 100.0) * 100)


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
