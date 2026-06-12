from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.safety import (
    ReconciliationIssue,
    ReconciliationResult,
    ReconciliationSeverity,
    SafetyStatus,
    build_safety_report,
    build_trading_lock,
    list_safety_audits,
    list_safety_reports,
    list_trading_locks,
    load_latest_safety_report,
    write_safety_audit_log,
    write_safety_report,
    write_trading_lock,
)


def test_history_reader_lists_report_lock_and_audit(tmp_path: Path) -> None:
    report, lock = build_report_and_lock()
    report_path = write_safety_report(report, runtime_dir=tmp_path / ".runtime")
    lock_path = write_trading_lock(lock, runtime_dir=tmp_path / ".runtime")
    audit_path = write_safety_audit_log(report=report, lock=lock, report_path=report_path, lock_path=lock_path, runtime_dir=tmp_path / ".runtime")

    assert list_safety_reports(tmp_path / ".runtime") == [report_path]
    assert list_trading_locks(tmp_path / ".runtime") == [lock_path]
    assert list_safety_audits(tmp_path / ".runtime") == [audit_path]


def test_history_reader_loads_latest_report(tmp_path: Path) -> None:
    report, lock = build_report_and_lock()
    write_safety_report(report, runtime_dir=tmp_path / ".runtime")

    latest = load_latest_safety_report(tmp_path / ".runtime")

    assert latest is not None
    assert latest["status"] == "HALT"
    assert latest["issue_count"] == 1


def test_history_reader_returns_empty_values_for_missing_dirs(tmp_path: Path) -> None:
    assert list_safety_reports(tmp_path / ".runtime") == []
    assert list_trading_locks(tmp_path / ".runtime") == []
    assert list_safety_audits(tmp_path / ".runtime") == []
    assert load_latest_safety_report(tmp_path / ".runtime") is None


def build_report_and_lock():
    _ = Decimal("0")
    result = ReconciliationResult(
        status=SafetyStatus.HALT,
        issues=(ReconciliationIssue(code="cash_mismatch", severity=ReconciliationSeverity.HALT, message="cash mismatch"),),
    )
    lock = build_trading_lock(result)
    return build_safety_report(result, lock, broker_snapshot_id="broker-snapshot-1"), lock
