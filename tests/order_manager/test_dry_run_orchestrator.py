from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.broker.moomoo.snapshot_sync import write_moomoo_mock_snapshots
from ai_fund_lab_v2.order_manager.broker_snapshot_loader import load_latest_broker_snapshot_bundle
from ai_fund_lab_v2.order_manager.dry_run_orchestrator import run_order_manager_dry_run
from ai_fund_lab_v2.order_manager.paper_ledger import PaperLedger, PaperPosition, write_paper_ledger


def test_dry_run_orchestrator_runs_end_to_end_without_external_connection(tmp_path: Path) -> None:
    runtime_dir = tmp_path / ".runtime"
    reports_dir = tmp_path / "reports" / "phase_reports"
    write_moomoo_mock_snapshots(runtime_dir)
    broker = load_latest_broker_snapshot_bundle(runtime_dir)
    ledger = PaperLedger(
        cash=broker.balance.cash_available,
        buying_power=broker.balance.buying_power,
        positions=tuple(
            PaperPosition(issue_code=position.issue_code, issue_name=position.issue_name, quantity=position.quantity)
            for position in broker.positions
        ),
        as_of=broker.balance.as_of,
    )
    ledger_path = write_paper_ledger(ledger, runtime_dir)

    result = run_order_manager_dry_run(
        runtime_dir=runtime_dir,
        reports_dir=reports_dir,
        repo_root=Path("."),
        paper_ledger_path=ledger_path,
    )

    assert result.plan_id
    assert Path(result.stored_plan_path).exists()
    assert Path(result.human_review_runtime_path).exists()
    assert Path(result.updated_paper_ledger_path).exists()
    assert Path(result.dry_run_report_json_path).exists()
    assert Path(result.safety_links_path).exists()
    assert result.phase7_decision_count == 9
