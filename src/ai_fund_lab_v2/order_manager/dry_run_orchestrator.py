from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from ai_fund_lab_v2.order_manager.broker_snapshot_loader import load_latest_broker_snapshot_bundle
from ai_fund_lab_v2.order_manager.dry_run_report import write_dry_run_report
from ai_fund_lab_v2.order_manager.human_review_report import write_human_review_report
from ai_fund_lab_v2.order_manager.order_plan_generator import generate_order_plan
from ai_fund_lab_v2.order_manager.order_plan_store import validate_order_plan_for_storage, write_order_plan
from ai_fund_lab_v2.order_manager.paper_ledger import PaperLedger, load_paper_ledger, paper_ledger_directory, write_paper_ledger
from ai_fund_lab_v2.order_manager.paper_ledger_update import apply_order_plan_to_paper_ledger
from ai_fund_lab_v2.order_manager.phase7_artifact_loader import load_phase7_artifact_connection
from ai_fund_lab_v2.order_manager.reconciliation import reconcile_broker_snapshot_with_paper
from ai_fund_lab_v2.order_manager.safety_report_links import write_order_manager_safety_links
from ai_fund_lab_v2.safety.lock_state_resolver import resolve_current_lock_state


class OrderManagerDryRunError(RuntimeError):
    pass


@dataclass(frozen=True)
class OrderManagerDryRunResult:
    plan_id: str
    plan_status: str
    broker_snapshot_id: str
    paper_ledger_id: str
    stored_plan_path: str
    human_review_runtime_path: str
    human_review_report_path: str
    updated_paper_ledger_path: str
    dry_run_report_json_path: str
    dry_run_report_runtime_md_path: str
    dry_run_report_reports_md_path: str
    safety_links_path: str
    phase7_decision_count: int
    reconciliation_status: str
    safety_status: str


def run_order_manager_dry_run(
    *,
    runtime_dir: Path | str = ".runtime",
    reports_dir: Path | str = "reports/phase_reports",
    repo_root: Path | str = ".",
    paper_ledger_path: Path | None = None,
) -> OrderManagerDryRunResult:
    runtime = Path(runtime_dir)
    broker = load_latest_broker_snapshot_bundle(runtime)
    phase7 = load_phase7_artifact_connection(repo_root)
    paper = _load_paper_ledger(runtime, paper_ledger_path)
    reconciliation = reconcile_broker_snapshot_with_paper(broker, paper)
    safety_state = resolve_current_lock_state(runtime)
    plan = generate_order_plan(
        allocation=phase7.allocation,
        broker=broker,
        paper=paper,
        reconciliation=reconciliation,
        runtime_dir=runtime,
    )
    validate_order_plan_for_storage(plan)
    stored_plan_path = write_order_plan(plan, runtime)
    human_runtime_path, human_report_path = write_human_review_report(
        order_plan=plan,
        reconciliation=reconciliation,
        runtime_dir=runtime,
        reports_dir=reports_dir,
    )
    updated_paper = apply_order_plan_to_paper_ledger(plan, paper)
    updated_paper_path = write_paper_ledger(updated_paper, runtime)
    dry_json, dry_runtime_md, dry_reports_md = write_dry_run_report(
        order_plan=plan,
        reconciliation=reconciliation,
        safety_state=safety_state,
        paper_ledger=updated_paper,
        runtime_dir=runtime,
        reports_dir=reports_dir,
    )
    safety_links_path = write_order_manager_safety_links(
        plan_id=plan.plan_id,
        runtime_dir=runtime,
        order_plan_path=stored_plan_path,
        reconciliation_id=reconciliation.reconciliation_id,
        paper_ledger_path=updated_paper_path,
        dry_run_report_path=dry_runtime_md,
    )
    return OrderManagerDryRunResult(
        plan_id=plan.plan_id,
        plan_status=plan.plan_status.value,
        broker_snapshot_id=broker.broker_snapshot_id,
        paper_ledger_id=paper.ledger_id,
        stored_plan_path=str(stored_plan_path),
        human_review_runtime_path=str(human_runtime_path),
        human_review_report_path=str(human_report_path),
        updated_paper_ledger_path=str(updated_paper_path),
        dry_run_report_json_path=str(dry_json),
        dry_run_report_runtime_md_path=str(dry_runtime_md),
        dry_run_report_reports_md_path=str(dry_reports_md),
        safety_links_path=str(safety_links_path),
        phase7_decision_count=len(phase7.allocation.decisions),
        reconciliation_status=reconciliation.status,
        safety_status=str(safety_state.get("status", "")),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Phase8-G Order Manager end-to-end dry-run.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--reports-dir", default="reports/phase_reports")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--paper-ledger-path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_order_manager_dry_run(
        runtime_dir=args.runtime_dir,
        reports_dir=args.reports_dir,
        repo_root=args.repo_root,
        paper_ledger_path=Path(args.paper_ledger_path) if args.paper_ledger_path else None,
    )
    print(result)
    return 0


def _load_paper_ledger(runtime_dir: Path, paper_ledger_path: Path | None) -> PaperLedger:
    if paper_ledger_path is not None:
        return load_paper_ledger(paper_ledger_path)
    directory = paper_ledger_directory(runtime_dir)
    if not directory.exists():
        raise OrderManagerDryRunError(f"Missing paper ledger directory: {directory}")
    candidates = sorted(directory.glob("*.json"), key=lambda path: (path.stat().st_mtime, path.name))
    if not candidates:
        raise OrderManagerDryRunError("No paper ledger found for dry-run.")
    return load_paper_ledger(candidates[-1])
