"""Promotion skeleton for Runtime v2 Pending Order Plans."""

from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import capital_deployment_policy_hash_from_context
from ai_fund_lab_v2.runtime_v2.pending.lifecycle import validate_pending_transition
from ai_fund_lab_v2.runtime_v2.pending.models import (
    PendingApprovalLink,
    PendingConsumeInfo,
    PendingOrderItem,
    PendingOrderPlan,
    PendingPlanState,
    PendingSourceOrderPlan,
    PendingSubmitConstraints,
)


def promote_order_plan_to_pending(
    *,
    order_plan_id: str,
    source_order_plan_path: str,
    source_order_plan_hash: str,
    environment: str,
    plan_created_date: str,
    intended_submit_date: str,
    target_session_date: str,
    items: Sequence[PendingOrderItem],
) -> PendingOrderPlan:
    if not order_plan_id:
        raise ValueError("order_plan_id is required")
    if not source_order_plan_path:
        raise ValueError("source_order_plan_path is required")
    if not source_order_plan_hash:
        raise ValueError("source_order_plan_hash is required")
    item_tuple = tuple(items)
    policy_context = _policy_context_from_items(item_tuple)
    safety_context = _safety_context_from_items(item_tuple)
    policy_version = str(policy_context.get("policy_version") or "")
    policy_source = str(policy_context.get("policy_source") or "")
    pending_policy_hash = _policy_hash(policy_context) if policy_context else ""
    return PendingOrderPlan(
        schema_version="1",
        pending_plan_id=f"pending-{order_plan_id}",
        state=PendingPlanState.PENDING_APPROVAL,
        environment=environment,
        created_at=plan_created_date,
        updated_at=plan_created_date,
        plan_created_date=plan_created_date,
        intended_submit_date=intended_submit_date,
        target_session_date=target_session_date,
        source_order_plan=PendingSourceOrderPlan(
            order_plan_id=order_plan_id,
            path=source_order_plan_path,
            artifact_hash=source_order_plan_hash,
        ),
        approval=None,
        approved_item_ids=(),
        items=item_tuple,
        submit_constraints=PendingSubmitConstraints(),
        consume=PendingConsumeInfo(),
        raw_request_saved=False,
        raw_response_saved=False,
        secret_saved=False,
        policy_context=policy_context or None,
        policy_version=policy_version,
        policy_source=policy_source,
        pending_policy_hash=pending_policy_hash,
        safety_context=safety_context or None,
        safety_decision_id=str(safety_context.get("safety_decision_id") or ""),
        safety_policy_version=str(safety_context.get("safety_policy_version") or ""),
    )


def attach_approval_link(
    plan: PendingOrderPlan,
    *,
    approval_path: str,
    approval_hash: str,
    approval_status: str,
    approved_item_ids: Sequence[str],
    approval_expires_at: str,
    approved_order_conditions: dict | None = None,
) -> PendingOrderPlan:
    approved_tuple = tuple(approved_item_ids)
    item_ids = {item.pending_item_id for item in plan.items}
    missing = tuple(item_id for item_id in approved_tuple if item_id not in item_ids)
    if missing:
        raise ValueError(f"approved_item_ids not in pending items: {', '.join(missing)}")
    next_state = plan.state
    if approval_status == "APPROVED":
        transition = validate_pending_transition(
            plan.state,
            PendingPlanState.APPROVED,
            reason="approval link attached",
        )
        if not transition.allowed:
            raise ValueError(f"approval cannot move {plan.state.value} to APPROVED")
        next_state = PendingPlanState.APPROVED
    return replace(
        plan,
        state=next_state,
        updated_at=approval_expires_at,
        approval=PendingApprovalLink(
            approval_path=approval_path,
            approval_hash=approval_hash,
            approval_status=approval_status,
            approved_item_ids=approved_tuple,
            approval_expires_at=approval_expires_at,
            policy_version=plan.policy_version,
            policy_source=plan.policy_source,
            pending_policy_hash=plan.pending_policy_hash,
            safety_decision_id=plan.safety_decision_id,
            safety_policy_version=plan.safety_policy_version,
            approved_order_conditions=approved_order_conditions,
        ),
        approved_item_ids=approved_tuple,
        items=tuple(
            replace(item, approved=item.pending_item_id in approved_tuple)
            for item in plan.items
        ),
    )


def _policy_context_from_items(items: tuple[PendingOrderItem, ...]) -> dict:
    for item in items:
        if item.policy_version or item.policy_source:
            return {
                "policy_version": item.policy_version,
                "policy_source": item.policy_source,
                "evaluation_capital": item.evaluation_capital,
                "target_investment_ratio": item.target_investment_ratio,
                "cash_buffer": item.cash_buffer,
                "max_exposure": item.max_exposure,
                "max_position_weight": item.max_position_weight,
                "max_positions": item.max_positions,
                "max_buy_order_amount": item.max_buy_order_amount,
                "max_sell_liquidation_amount": item.max_sell_liquidation_amount,
                "min_order_amount": item.min_order_amount,
                "buy_notional_policy": item.buy_notional_policy,
                "sell_liquidation_policy": item.sell_liquidation_policy,
                "manual_review_threshold": item.manual_review_threshold,
            }
    return {}


def _safety_context_from_items(items: tuple[PendingOrderItem, ...]) -> dict:
    for item in items:
        if item.safety_decision_id or item.safety_policy_version:
            return {
                "safety_decision_id": item.safety_decision_id,
                "safety_policy_version": item.safety_policy_version,
                "safety_source": item.safety_source,
                "safety_decision": item.safety_decision,
                "safety_reason": item.safety_reason,
            }
    return {}


def _policy_hash(policy_context: dict) -> str:
    return capital_deployment_policy_hash_from_context(policy_context)
