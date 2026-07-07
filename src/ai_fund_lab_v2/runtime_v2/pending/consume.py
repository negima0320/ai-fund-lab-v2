"""Consume and re-submit guard helpers for Pending Order Plans."""

from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from ai_fund_lab_v2.runtime_v2.pending.lifecycle import validate_pending_transition
from ai_fund_lab_v2.runtime_v2.pending.models import (
    PendingConsumeInfo,
    PendingOrderPlan,
    PendingPlanState,
)


def consume_pending_plan(
    plan: PendingOrderPlan,
    *,
    consume_reason: str,
    submitted_order_ids: Sequence[str] = (),
    ledger_order_record_ids: Sequence[str] = (),
) -> PendingOrderPlan:
    if not consume_reason:
        raise ValueError("consume_reason is required")
    transition = validate_pending_transition(
        plan.state,
        PendingPlanState.CONSUMED,
        reason=consume_reason,
    )
    if not transition.allowed:
        raise ValueError(f"{plan.state.value} cannot be consumed")
    return replace(
        plan,
        state=PendingPlanState.CONSUMED,
        consume=PendingConsumeInfo(
            consumed=True,
            consume_reason=consume_reason,
            consumed_at=plan.updated_at,
            submitted_order_ids=tuple(submitted_order_ids),
            ledger_order_record_ids=tuple(ledger_order_record_ids),
        ),
    )


def can_submit_pending_plan(
    plan: PendingOrderPlan,
    existing_order_dedup_keys: set[str],
) -> bool:
    if plan.state != PendingPlanState.APPROVED:
        return False
    if plan.approval is None:
        return False
    if not plan.approved_item_ids:
        return False
    item_ids = {item.pending_item_id for item in plan.items}
    if any(item_id not in item_ids for item_id in plan.approved_item_ids):
        return False
    if any(not item.approved for item in plan.items if item.pending_item_id in plan.approved_item_ids):
        return False
    if plan.pending_plan_id in existing_order_dedup_keys:
        return False
    if plan.submit_constraints.expires_at and plan.approval.approval_expires_at:
        if plan.approval.approval_expires_at > plan.submit_constraints.expires_at:
            return False
    return True
