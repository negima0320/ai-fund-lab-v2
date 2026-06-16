import json
from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.order_manager.order_plan_history import (
    load_latest_order_plan,
    load_order_plan_by_id,
    read_order_plan_history,
    sanitized_order_plan_summary,
)
from ai_fund_lab_v2.order_manager.order_plan_store import order_plan_directory, write_order_plan
from ai_fund_lab_v2.order_manager.schema import OrderPlanItem, OrderPlanItemSide, create_order_plan


def _plan(policy_id: str):
    return create_order_plan(
        broker_snapshot_id=f"broker_{policy_id}",
        paper_ledger_id=f"paper_{policy_id}",
        policy_id=policy_id,
        items=(OrderPlanItem(issue_code="7203", side=OrderPlanItemSide.HOLD, action="HOLD_PLAN", quantity=Decimal("100")),),
    )


def test_order_plan_history_reads_latest_by_id_and_status(tmp_path: Path) -> None:
    runtime_dir = tmp_path / ".runtime"
    plan_a = _plan("CAP5")
    plan_b = _plan("CAP4")
    write_order_plan(plan_a, runtime_dir)
    write_order_plan(plan_b, runtime_dir)

    assert load_order_plan_by_id(plan_a.plan_id, runtime_dir).policy_id == "CAP5"
    assert load_latest_order_plan(runtime_dir).plan_id in {plan_a.plan_id, plan_b.plan_id}

    history = read_order_plan_history(runtime_dir, status_filter="READY_FOR_REVIEW")
    assert {plan.plan_id for plan in history.plans} == {plan_a.plan_id, plan_b.plan_id}
    summary = sanitized_order_plan_summary(plan_a)
    assert summary["executable"] is False
    assert "item_count" in summary


def test_order_plan_history_skips_invalid_json_with_warning(tmp_path: Path) -> None:
    runtime_dir = tmp_path / ".runtime"
    write_order_plan(_plan("CAP5"), runtime_dir)
    bad_path = order_plan_directory(runtime_dir) / "broken.json"
    bad_path.write_text("{", encoding="utf-8")

    history = read_order_plan_history(runtime_dir)

    assert len(history.plans) == 1
    assert history.warnings
