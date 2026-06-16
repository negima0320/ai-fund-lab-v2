import json
from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.order_manager.order_plan_store import load_order_plan, write_order_plan
from ai_fund_lab_v2.order_manager.schema import OrderPlanItem, OrderPlanItemSide, create_order_plan


def test_order_plan_store_persists_required_safe_fields(tmp_path: Path) -> None:
    plan = create_order_plan(
        broker_snapshot_id="broker_snapshot_1",
        paper_ledger_id="paper_ledger_1",
        policy_id="CAP5",
        items=[OrderPlanItem(issue_code="7203", side=OrderPlanItemSide.HOLD, action="HOLD_PLAN", quantity=Decimal("100"))],
    )

    path = write_order_plan(plan, tmp_path / ".runtime")

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["plan_id"] == plan.plan_id
    assert payload["generated_at"]
    assert payload["schema_version"] == "phase8.order_plan.v1"
    assert payload["source"] == "phase8_order_plan"
    assert payload["status"] == "READY_FOR_REVIEW"
    assert payload["executable"] is False
    assert payload["live_order_allowed"] is False
    assert payload["requires_human_review"] is True
    loaded = load_order_plan(path)
    assert loaded.plan_id == plan.plan_id
    assert loaded.plan_status.value == "READY_FOR_REVIEW"
