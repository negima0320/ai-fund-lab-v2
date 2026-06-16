import json
from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.order_manager.approval_cli import create_approval_record_for_plan
from ai_fund_lab_v2.order_manager.order_plan_store import write_order_plan
from ai_fund_lab_v2.order_manager.schema import OrderPlanItem, OrderPlanItemSide, create_order_plan


def test_approval_cli_creates_record_without_execution_permission(tmp_path: Path) -> None:
    runtime_dir = tmp_path / ".runtime"
    plan = create_order_plan(
        broker_snapshot_id="broker",
        paper_ledger_id="paper",
        policy_id="CAP5",
        items=(OrderPlanItem(issue_code="7203", side=OrderPlanItemSide.HOLD, action="HOLD_PLAN", quantity=Decimal("100")),),
    )
    write_order_plan(plan, runtime_dir)

    path = create_approval_record_for_plan(
        plan_id=plan.plan_id,
        reviewer="human",
        decision="approved",
        comment="reviewed",
        runtime_dir=runtime_dir,
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["decision"] == "approved"
    assert payload["approval_does_not_allow_live_order"] is True
