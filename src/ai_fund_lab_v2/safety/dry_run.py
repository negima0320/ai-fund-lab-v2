from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_fund_lab_v2.safety.audit_writer import write_safety_audit_log
from ai_fund_lab_v2.safety.models import BrokerState, PortfolioState, SafetyReport, TradingLock
from ai_fund_lab_v2.safety.reconciliation import reconcile_states
from ai_fund_lab_v2.safety.report import build_safety_report
from ai_fund_lab_v2.safety.report_writer import write_safety_report, write_trading_lock
from ai_fund_lab_v2.safety.trading_lock import build_trading_lock


@dataclass(frozen=True)
class SafetyDryRunResult:
    report: SafetyReport
    lock: TradingLock
    report_path: Path
    lock_path: Path
    audit_path: Path


def run_safety_dry_run(
    broker_state: BrokerState,
    portfolio_state: PortfolioState,
    runtime_dir: Path | str = ".runtime",
) -> SafetyDryRunResult:
    reconciliation_result = reconcile_states(portfolio_state, broker_state)
    lock = build_trading_lock(reconciliation_result)
    report = build_safety_report(reconciliation_result, lock, broker_snapshot_id=broker_state.source_snapshot_id)
    report_path = write_safety_report(report, runtime_dir=runtime_dir)
    lock_path = write_trading_lock(lock, runtime_dir=runtime_dir)
    audit_path = write_safety_audit_log(
        report=report,
        lock=lock,
        report_path=report_path,
        lock_path=lock_path,
        runtime_dir=runtime_dir,
    )
    return SafetyDryRunResult(report=report, lock=lock, report_path=report_path, lock_path=lock_path, audit_path=audit_path)
