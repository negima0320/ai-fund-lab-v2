import json
from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.order_manager.approval_record import HumanReviewApprovalRecord, write_approval_record
from ai_fund_lab_v2.order_manager.order_plan_store import write_order_plan
from ai_fund_lab_v2.order_manager.review_queue import build_review_queue, write_review_queue
from ai_fund_lab_v2.order_manager.schema import OrderPlanItem, OrderPlanItemSide, create_order_plan


def test_review_queue_groups_pending_and_approved(tmp_path: Path) -> None:
    runtime_dir = tmp_path / ".runtime"
    plan = create_order_plan(
        broker_snapshot_id="broker",
        paper_ledger_id="paper",
        policy_id="CAP5",
        items=(OrderPlanItem(issue_code="7203", side=OrderPlanItemSide.HOLD, action="HOLD_PLAN", quantity=Decimal("100")),),
    )
    write_order_plan(plan, runtime_dir)
    write_approval_record(HumanReviewApprovalRecord(plan_id=plan.plan_id, reviewer="human", decision="approved"), runtime_dir)

    queue = build_review_queue(runtime_dir)
    path = write_review_queue(runtime_dir)

    assert queue["counts"]["approved"] == 1
    assert queue["approval_does_not_allow_live_order"] is True
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["groups"]["approved"][0]["plan_id"] == plan.plan_id
