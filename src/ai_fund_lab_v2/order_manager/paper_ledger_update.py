from __future__ import annotations

from decimal import Decimal

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.order_manager.paper_ledger import PaperExecution, PaperLedger, PaperPosition
from ai_fund_lab_v2.order_manager.schema import OrderPlan, OrderPlanItemSide


def apply_order_plan_to_paper_ledger(order_plan: OrderPlan, ledger: PaperLedger) -> PaperLedger:
    positions = {position.issue_code: position for position in ledger.positions}
    executions = list(ledger.executions)
    cash = ledger.cash
    unresolved_sells: set[str] = set()
    for item in order_plan.items:
        if item.side == OrderPlanItemSide.SELL and item.status != "BLOCKED_BY_CASH":
            current = positions.get(item.issue_code)
            current_qty = current.quantity if current else Decimal("0")
            sell_qty = min(current_qty, item.quantity)
            if sell_qty <= 0:
                continue
            remaining = current_qty - sell_qty
            if remaining:
                positions[item.issue_code] = PaperPosition(
                    issue_code=item.issue_code,
                    issue_name=item.issue_name,
                    quantity=remaining,
                    average_price=current.average_price if current else Decimal("0"),
                    market_price=item.estimated_price,
                )
            else:
                positions.pop(item.issue_code, None)
            cash += sell_qty * item.estimated_price
            executions.append(_execution(order_plan.plan_id, item.item_id, item.issue_code, "SELL", sell_qty, item.estimated_price))
            unresolved_sells.add(item.item_id)
    for item in order_plan.items:
        if item.side != OrderPlanItemSide.BUY:
            continue
        if item.status == "BLOCKED_BY_CASH":
            continue
        if item.depends_on_fill_item_id and item.depends_on_fill_item_id not in unresolved_sells:
            continue
        cost = item.quantity * item.estimated_price
        if cost > cash:
            continue
        current = positions.get(item.issue_code)
        new_qty = (current.quantity if current else Decimal("0")) + item.quantity
        positions[item.issue_code] = PaperPosition(
            issue_code=item.issue_code,
            issue_name=item.issue_name,
            quantity=new_qty,
            average_price=item.estimated_price,
            market_price=item.estimated_price,
        )
        cash -= cost
        executions.append(_execution(order_plan.plan_id, item.item_id, item.issue_code, "BUY", item.quantity, item.estimated_price))
    return PaperLedger(
        cash=cash,
        buying_power=cash,
        positions=tuple(positions.values()),
        pending_orders=ledger.pending_orders,
        executions=tuple(executions),
        as_of=utc_now_iso(),
    )


def _execution(plan_id: str, item_id: str, issue_code: str, side: str, quantity: Decimal, price: Decimal) -> PaperExecution:
    return PaperExecution(
        paper_execution_id=f"paper_exec_{plan_id}_{item_id}",
        paper_order_id=item_id,
        issue_code=issue_code,
        side=side,
        quantity=quantity,
        price=price,
        executed_at=utc_now_iso(),
    )

