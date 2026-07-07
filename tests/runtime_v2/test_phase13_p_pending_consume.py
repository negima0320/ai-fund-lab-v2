import pytest
from dataclasses import replace

from ai_fund_lab_v2.runtime_v2.pending.consume import (
    can_submit_pending_plan,
    consume_pending_plan,
)
from ai_fund_lab_v2.runtime_v2.pending.models import PendingPlanState
from tests.runtime_v2.pending_fixtures import make_approved_pending_plan


def test_submitted_can_consume_and_stores_links():
    plan = replace(make_approved_pending_plan(), state=PendingPlanState.SUBMITTED)

    consumed = consume_pending_plan(
        plan,
        consume_reason="submitted orders recorded",
        submitted_order_ids=("submitted-1",),
        ledger_order_record_ids=("ledger-order-1",),
    )

    assert consumed.state == PendingPlanState.CONSUMED
    assert consumed.consume.consumed is True
    assert consumed.consume.consume_reason == "submitted orders recorded"
    assert consumed.consume.submitted_order_ids == ("submitted-1",)
    assert consumed.consume.ledger_order_record_ids == ("ledger-order-1",)


def test_post_send_unknown_can_consume():
    plan = replace(make_approved_pending_plan(), state=PendingPlanState.POST_SEND_UNKNOWN)

    consumed = consume_pending_plan(plan, consume_reason="manual reconciliation")

    assert consumed.state == PendingPlanState.CONSUMED


def test_consumed_plan_cannot_submit():
    plan = replace(make_approved_pending_plan(), state=PendingPlanState.CONSUMED)

    assert can_submit_pending_plan(plan, set()) is False


def test_approved_can_submit_when_clean():
    plan = make_approved_pending_plan()

    assert can_submit_pending_plan(plan, set()) is True


def test_resubmit_guard_blocks_submitted_post_send_unknown_review_and_dedup():
    approved = make_approved_pending_plan()

    assert can_submit_pending_plan(
        replace(approved, state=PendingPlanState.SUBMITTED),
        set(),
    ) is False
    assert can_submit_pending_plan(
        replace(approved, state=PendingPlanState.POST_SEND_UNKNOWN),
        set(),
    ) is False
    assert can_submit_pending_plan(
        replace(approved, state=PendingPlanState.REVIEW_REQUIRED),
        set(),
    ) is False
    assert can_submit_pending_plan(approved, {approved.pending_plan_id}) is False


def test_pending_approval_cannot_be_consumed():
    with pytest.raises(ValueError, match="cannot be consumed"):
        consume_pending_plan(
            replace(make_approved_pending_plan(), state=PendingPlanState.PENDING_APPROVAL),
            consume_reason="not allowed",
        )

