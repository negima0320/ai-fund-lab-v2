import json
from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.broker.moomoo.snapshot_sync import write_moomoo_mock_snapshots
from ai_fund_lab_v2.order_manager.broker_snapshot_loader import load_latest_broker_snapshot_bundle
from ai_fund_lab_v2.order_manager.human_review_report import write_human_review_report
from ai_fund_lab_v2.order_manager.paper_ledger import PaperLedger, PaperPosition
from ai_fund_lab_v2.order_manager.reconciliation import reconcile_broker_snapshot_with_paper
from ai_fund_lab_v2.order_manager.safety_reconciliation import (
    build_review_only_plan_when_locked,
    load_phase8c_smoke_result,
)


def test_locked_state_generates_review_only_plan_and_human_report(tmp_path: Path) -> None:
    write_moomoo_mock_snapshots(tmp_path / ".runtime")
    bundle = load_latest_broker_snapshot_bundle(tmp_path / ".runtime")
    paper = PaperLedger(
        cash=bundle.balance.cash_available,
        buying_power=bundle.balance.buying_power,
        positions=tuple(PaperPosition(issue_code=p.issue_code, issue_name=p.issue_name, quantity=p.quantity) for p in bundle.positions),
        as_of=bundle.balance.as_of,
    )
    reconciliation = reconcile_broker_snapshot_with_paper(bundle, paper)
    lock_dir = tmp_path / ".runtime" / "safety" / "locks"
    lock_dir.mkdir(parents=True)
    (lock_dir / "lock.json").write_text(
        json.dumps({"is_locked": True, "status": "LOCKED", "reason": "manual halt"}), encoding="utf-8"
    )

    plan = build_review_only_plan_when_locked(bundle, paper, reconciliation, runtime_dir=tmp_path / ".runtime")
    runtime_report, docs_report = write_human_review_report(
        order_plan=plan,
        reconciliation=reconciliation,
        runtime_dir=tmp_path / ".runtime",
        reports_dir=tmp_path / "docs" / "phase_reports",
    )

    assert plan.plan_status.value == "REVIEW_ONLY_LOCKED"
    assert plan.executable is False
    assert plan.live_order_allowed is False
    assert plan.requires_human_review is True
    report_text = runtime_report.read_text(encoding="utf-8")
    assert "Phase8では実発注しない" in report_text
    assert "REVIEW_ONLY_LOCKED" in report_text
    assert docs_report.is_file()


def test_phase8c_smoke_result_reader_handles_skipped_result(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "phase_reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "phase8c_moomoo_readonly_smoke_result.json").write_text(
        json.dumps({"status": "SKIPPED", "executed": False, "message": "not run"}), encoding="utf-8"
    )

    result = load_phase8c_smoke_result(reports_dir)

    assert result["status"] == "SKIPPED"
    assert result["executed"] is False

