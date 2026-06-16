from __future__ import annotations

from dataclasses import dataclass

from ai_fund_lab_v2.order_manager.schema import OrderPlan, OrderPlanItemSide


@dataclass(frozen=True)
class DependencyValidationResult:
    valid: bool
    errors: tuple[str, ...] = ()


def validate_sell_first_buy_after_fill(order_plan: OrderPlan) -> DependencyValidationResult:
    errors: list[str] = []
    item_ids = {item.item_id for item in order_plan.items}
    sell_ids = {item.item_id for item in order_plan.items if item.side == OrderPlanItemSide.SELL}
    for item in order_plan.items:
        if item.side == OrderPlanItemSide.BUY and item.sell_first_group_id:
            if not item.depends_on_fill_item_id:
                errors.append(f"BUY item {item.item_id} missing sell dependency.")
            elif item.depends_on_fill_item_id not in item_ids:
                errors.append(f"BUY item {item.item_id} depends on unknown item.")
            elif item.depends_on_fill_item_id not in sell_ids:
                errors.append(f"BUY item {item.item_id} dependency is not SELL.")
            if not item.requires_broker_snapshot_refresh:
                errors.append(f"BUY item {item.item_id} must require broker snapshot refresh.")
    return DependencyValidationResult(valid=not errors, errors=tuple(errors))

