import pytest

from ai_fund_lab_v2.runtime_v2.pending.models import PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import (
    attach_approval_link,
    promote_order_plan_to_pending,
)
from tests.runtime_v2.pending_fixtures import make_pending_item


def test_promotion_creates_pending_approval_plan():
    plan = promote_order_plan_to_pending(
        order_plan_id="order-plan-1",
        source_order_plan_path="order_plan/2026-07-07/order_plan.json",
        source_order_plan_hash="hash-1",
        environment="demo",
        plan_created_date="2026-07-07",
        intended_submit_date="2026-07-08",
        target_session_date="2026-07-08",
        items=(make_pending_item(),),
    )

    assert plan.state == PendingPlanState.PENDING_APPROVAL
    assert plan.source_order_plan.path == "order_plan/2026-07-07/order_plan.json"
    assert plan.source_order_plan.artifact_hash == "hash-1"
    assert plan.raw_request_saved is False
    assert plan.raw_response_saved is False
    assert plan.secret_saved is False


def test_valid_approval_link_moves_to_approved_and_stores_hash():
    plan = promote_order_plan_to_pending(
        order_plan_id="order-plan-1",
        source_order_plan_path="order_plan/2026-07-07/order_plan.json",
        source_order_plan_hash="hash-1",
        environment="demo",
        plan_created_date="2026-07-07",
        intended_submit_date="2026-07-08",
        target_session_date="2026-07-08",
        items=(make_pending_item(),),
    )

    approved = attach_approval_link(
        plan,
        approval_path="approval_artifact/2026-07-07/approval.json",
        approval_hash="approval-hash",
        approval_status="APPROVED",
        approved_item_ids=("item-1",),
        approval_expires_at="2026-07-08T00:00:00Z",
    )

    assert approved.state == PendingPlanState.APPROVED
    assert approved.approval.approval_hash == "approval-hash"
    assert approved.approval.approval_path == "approval_artifact/2026-07-07/approval.json"
    assert approved.approved_item_ids == ("item-1",)


def test_approval_item_ids_must_exist_in_pending_items():
    plan = promote_order_plan_to_pending(
        order_plan_id="order-plan-1",
        source_order_plan_path="order_plan/2026-07-07/order_plan.json",
        source_order_plan_hash="hash-1",
        environment="demo",
        plan_created_date="2026-07-07",
        intended_submit_date="2026-07-08",
        target_session_date="2026-07-08",
        items=(make_pending_item(),),
    )

    with pytest.raises(ValueError, match="approved_item_ids"):
        attach_approval_link(
            plan,
            approval_path="approval_artifact/2026-07-07/approval.json",
            approval_hash="approval-hash",
            approval_status="APPROVED",
            approved_item_ids=("missing-item",),
            approval_expires_at="2026-07-08T00:00:00Z",
        )


def test_promotion_source_paths_are_evidence_only():
    plan = promote_order_plan_to_pending(
        order_plan_id="order-plan-1",
        source_order_plan_path="order_plan/2026-07-07/order_plan.json",
        source_order_plan_hash="hash-1",
        environment="demo",
        plan_created_date="2026-07-07",
        intended_submit_date="2026-07-08",
        target_session_date="2026-07-08",
        items=(make_pending_item(),),
    )

    assert plan.pending_plan_id == "pending-order-plan-1"
    assert plan.source_order_plan.path.startswith("order_plan/")

