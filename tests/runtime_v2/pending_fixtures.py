from dataclasses import replace

from ai_fund_lab_v2.runtime_v2.pending.models import (
    PendingApprovalLink,
    PendingConsumeInfo,
    PendingOrderItem,
    PendingOrderPlan,
    PendingPlanState,
    PendingSourceOrderPlan,
    PendingSubmitConstraints,
)


def make_pending_item(pending_item_id: str = "item-1") -> PendingOrderItem:
    return PendingOrderItem(
        pending_item_id=pending_item_id,
        symbol="7203",
        side="BUY",
        quantity=100,
        order_type="MARKET",
        estimated_price=2500,
        estimated_amount=250000,
        approved=False,
        state="PENDING_APPROVAL",
    )


def make_pending_plan(
    pending_plan_id: str = "pending-order-plan-1",
    state: PendingPlanState = PendingPlanState.PENDING_APPROVAL,
) -> PendingOrderPlan:
    return PendingOrderPlan(
        schema_version="1",
        pending_plan_id=pending_plan_id,
        state=state,
        environment="demo",
        created_at="2026-07-07T00:00:00Z",
        updated_at="2026-07-07T00:00:00Z",
        plan_created_date="2026-07-07",
        intended_submit_date="2026-07-08",
        target_session_date="2026-07-08",
        source_order_plan=PendingSourceOrderPlan(
            order_plan_id="order-plan-1",
            path="order_plan/2026-07-07/order_plan.json",
            artifact_hash="hash-1",
        ),
        approval=None,
        approved_item_ids=(),
        items=(make_pending_item(),),
        submit_constraints=PendingSubmitConstraints(
            expires_at="2026-07-09T00:00:00Z",
        ),
        consume=PendingConsumeInfo(),
        raw_request_saved=False,
        raw_response_saved=False,
        secret_saved=False,
    )


def make_approved_pending_plan() -> PendingOrderPlan:
    plan = make_pending_plan(state=PendingPlanState.APPROVED)
    return replace(
        plan,
        approval=PendingApprovalLink(
            approval_path="approval_artifact/2026-07-07/approval.json",
            approval_hash="approval-hash",
            approval_status="APPROVED",
            approved_item_ids=("item-1",),
            approval_expires_at="2026-07-08T00:00:00Z",
        ),
        approved_item_ids=("item-1",),
        items=(replace(plan.items[0], approved=True),),
    )
