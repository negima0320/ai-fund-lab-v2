from decimal import Decimal

import pytest

from ai_fund_lab_v2.order_manager import OrderPlan, OrderPlanItem, OrderPlanItemSide, create_order_plan


def test_order_plan_defaults_are_non_executable_and_review_required() -> None:
    item = OrderPlanItem(
        issue_code="7203",
        issue_name="TOYOTA",
        side=OrderPlanItemSide.BUY,
        action="NEW_BUY_PLAN",
        quantity=Decimal("100"),
        estimated_price=Decimal("2500"),
        estimated_value=Decimal("250000"),
    )
    plan = OrderPlan(broker_snapshot_id="snapshot_mock", policy_id="CAP5", items=(item,))

    assert plan.broker == "moomoo"
    assert plan.executable is False
    assert plan.live_order_allowed is False
    assert plan.requires_human_review is True
    assert plan.items[0].executable is False
    assert plan.to_dict()["items"][0]["estimated_value"] == "250000"


def test_order_plan_rejects_executable_flags() -> None:
    item = OrderPlanItem(issue_code="7203", side=OrderPlanItemSide.HOLD, action="HOLD_PLAN")

    with pytest.raises(ValueError, match="must not be executable"):
        OrderPlan(broker_snapshot_id="snapshot_mock", policy_id="CAP5", items=(item,), executable=True)

    with pytest.raises(ValueError, match="must not allow live orders"):
        OrderPlan(broker_snapshot_id="snapshot_mock", policy_id="CAP5", items=(item,), live_order_allowed=True)


def test_order_plan_marks_locked_state_as_review_only() -> None:
    plan = create_order_plan(
        broker_snapshot_id="snapshot_mock",
        policy_id="CAP5",
        items=[OrderPlanItem(issue_code="7203", side=OrderPlanItemSide.NOOP, action="BLOCKED_BY_SAFETY")],
        safety_status="HALT",
        lock_state="locked",
    )

    assert plan.plan_status.value == "REVIEW_ONLY_LOCKED"
    assert plan.executable is False

