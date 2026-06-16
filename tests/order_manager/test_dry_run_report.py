from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.order_manager.approval_record import HumanReviewApprovalRecord
from ai_fund_lab_v2.order_manager.dry_run_report import write_dry_run_report
from ai_fund_lab_v2.order_manager.paper_ledger import PaperLedger
from ai_fund_lab_v2.order_manager.reconciliation import OrderManagerReconciliationResult
from ai_fund_lab_v2.order_manager.schema import OrderPlanItem, OrderPlanItemSide, create_order_plan


def test_dry_run_report_writes_runtime_and_reports_outputs(tmp_path: Path) -> None:
    plan = create_order_plan(
        broker_snapshot_id="broker",
        paper_ledger_id="paper",
        policy_id="CAP5",
        items=(OrderPlanItem(issue_code="7203", side=OrderPlanItemSide.HOLD, action="HOLD_PLAN", quantity=Decimal("100")),),
    )
    reconciliation = OrderManagerReconciliationResult(
        broker_snapshot_id="broker",
        paper_ledger_id="paper",
        status="OK",
        safety_status="OK",
        warning=False,
        halt_candidate=False,
        summary="match",
    )

    paths = write_dry_run_report(
        order_plan=plan,
        reconciliation=reconciliation,
        safety_state={"is_locked": False, "status": "UNLOCKED", "source": "none"},
        paper_ledger=PaperLedger(cash=Decimal("1000"), buying_power=Decimal("1000")),
        approval_record=HumanReviewApprovalRecord(plan_id=plan.plan_id, reviewer="human", decision="approved"),
        runtime_dir=tmp_path / ".runtime",
        reports_dir=tmp_path / "reports" / "phase_reports",
    )

    assert all(path.exists() for path in paths)
    assert "approval_does_not_allow_live_order: true" in paths[1].read_text(encoding="utf-8")
