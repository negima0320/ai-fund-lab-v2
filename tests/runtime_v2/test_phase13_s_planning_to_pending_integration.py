import pytest

from ai_fund_lab_v2.runtime_v2.pending.models import PendingPlanState
from ai_fund_lab_v2.runtime_v2.planning.order_plan_builder import (
    promote_order_plan_result_to_pending,
)
from ai_fund_lab_v2.runtime_v2.planning.planner import build_order_plan
from tests.runtime_v2.planning_fixtures import make_planning_input


def test_order_plan_can_be_promoted_to_pending():
    result = build_order_plan(make_planning_input())

    pending = promote_order_plan_result_to_pending(
        result=result,
        source_order_plan_path="order_plan/2026-07-07/order_plan.json",
        source_order_plan_hash="hash-1",
    )

    assert pending.state == PendingPlanState.PENDING_APPROVAL
    assert pending.items
    assert pending.source_order_plan.artifact_hash == "hash-1"


def test_source_order_plan_path_and_hash_are_required():
    result = build_order_plan(make_planning_input())

    with pytest.raises(ValueError, match="source_order_plan_path"):
        promote_order_plan_result_to_pending(
            result=result,
            source_order_plan_path="",
            source_order_plan_hash="hash-1",
        )
    with pytest.raises(ValueError, match="source_order_plan_hash"):
        promote_order_plan_result_to_pending(
            result=result,
            source_order_plan_path="order_plan/2026-07-07/order_plan.json",
            source_order_plan_hash="",
        )


def test_promotion_does_not_submit():
    result = build_order_plan(make_planning_input())
    pending = promote_order_plan_result_to_pending(
        result=result,
        source_order_plan_path="order_plan/2026-07-07/order_plan.json",
        source_order_plan_hash="hash-1",
    )

    assert not hasattr(pending, "submitted_order_id")
    assert pending.state == PendingPlanState.PENDING_APPROVAL

