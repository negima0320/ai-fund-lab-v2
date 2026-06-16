from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.order_manager.order_plan_store import write_order_plan
from ai_fund_lab_v2.order_manager.paper_ledger import PaperLedger, PaperPosition, load_paper_ledger, write_paper_ledger
from ai_fund_lab_v2.order_manager.paper_ledger_cli import apply_saved_plan_to_paper_ledger
from ai_fund_lab_v2.order_manager.schema import OrderPlanItem, OrderPlanItemSide, create_order_plan


def test_paper_ledger_cli_applies_saved_plan_as_dry_run(tmp_path: Path) -> None:
    runtime_dir = tmp_path / ".runtime"
    sell = OrderPlanItem(
        issue_code="7203",
        side=OrderPlanItemSide.SELL,
        action="REPLACE_SELL_PLAN",
        quantity=Decimal("100"),
        estimated_price=Decimal("1000"),
        estimated_value=Decimal("100000"),
        sell_first_group_id="g1",
    )
    buy = OrderPlanItem(
        issue_code="6501",
        side=OrderPlanItemSide.BUY,
        action="REPLACE_BUY_AFTER_FILL_PLAN",
        quantity=Decimal("100"),
        estimated_price=Decimal("900"),
        estimated_value=Decimal("90000"),
        sell_first_group_id="g1",
        depends_on_fill_item_id=sell.item_id,
        requires_broker_snapshot_refresh=True,
    )
    plan = create_order_plan(
        broker_snapshot_id="broker",
        paper_ledger_id="paper",
        policy_id="CAP5",
        items=(sell, buy),
    )
    write_order_plan(plan, runtime_dir)
    ledger = PaperLedger(
        cash=Decimal("0"),
        buying_power=Decimal("0"),
        positions=(PaperPosition(issue_code="7203", quantity=Decimal("100"), average_price=Decimal("1000")),),
    )
    ledger_path = write_paper_ledger(ledger, runtime_dir)

    updated_path = apply_saved_plan_to_paper_ledger(
        plan_id=plan.plan_id,
        paper_ledger_path=ledger_path,
        runtime_dir=runtime_dir,
    )

    updated = load_paper_ledger(updated_path)
    quantities = {position.issue_code: position.quantity for position in updated.positions}
    assert "7203" not in quantities
    assert quantities["6501"] == Decimal("100")
    assert len(updated.executions) == 2
