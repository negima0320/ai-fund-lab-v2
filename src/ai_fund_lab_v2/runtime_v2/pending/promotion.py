"""Promotion skeleton for Runtime v2 Pending Order Plans."""

from __future__ import annotations

from dataclasses import replace
from typing import Sequence

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
    )


def attach_approval_link(
    plan: PendingOrderPlan,
    *,
    approval_path: str,
    approval_hash: str,
    approval_status: str,
    approved_item_ids: Sequence[str],
    approval_expires_at: str,
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
        ),
        approved_item_ids=approved_tuple,
        items=tuple(
            replace(item, approved=item.pending_item_id in approved_tuple)
            for item in plan.items
        ),
    )

