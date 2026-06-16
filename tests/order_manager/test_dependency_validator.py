from ai_fund_lab_v2.order_manager.dependency_validator import validate_sell_first_buy_after_fill
from ai_fund_lab_v2.order_manager.schema import OrderPlan, OrderPlanItem, OrderPlanItemSide


def test_dependency_validator_accepts_sell_first_buy_after_fill() -> None:
    sell = OrderPlanItem(issue_code="7203", side=OrderPlanItemSide.SELL, action="REPLACE_SELL_PLAN")
    buy = OrderPlanItem(
        issue_code="6758",
        side=OrderPlanItemSide.BUY,
        action="REPLACE_BUY_AFTER_FILL_PLAN",
        sell_first_group_id="g1",
        depends_on_fill_item_id=sell.item_id,
        requires_broker_snapshot_refresh=True,
    )
    plan = OrderPlan(broker_snapshot_id="b", policy_id="CAP5", items=(sell, buy))

    result = validate_sell_first_buy_after_fill(plan)

    assert result.valid is True


def test_dependency_validator_rejects_missing_dependency() -> None:
    buy = OrderPlanItem(
        issue_code="6758",
        side=OrderPlanItemSide.BUY,
        action="REPLACE_BUY_AFTER_FILL_PLAN",
        sell_first_group_id="g1",
    )
    plan = OrderPlan(broker_snapshot_id="b", policy_id="CAP5", items=(buy,))

    result = validate_sell_first_buy_after_fill(plan)

    assert result.valid is False
    assert result.errors

