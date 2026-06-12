import json
from pathlib import Path

from ai_fund_lab_v2.safety import (
    ReconciliationIssue,
    ReconciliationResult,
    ReconciliationSeverity,
    SafetyStatus,
    build_safety_report,
    build_trading_lock,
    write_safety_audit_log,
    write_safety_report,
    write_trading_lock,
)


def test_audit_writer_saves_summary_under_runtime_safety_audit(tmp_path: Path) -> None:
    result = ReconciliationResult(
        status=SafetyStatus.HALT,
        issues=(ReconciliationIssue(code="cash_mismatch", severity=ReconciliationSeverity.HALT, message="cash mismatch"),),
    )
    lock = build_trading_lock(result)
    report = build_safety_report(result, lock, broker_snapshot_id="broker-snapshot-1")
    report_path = write_safety_report(report, runtime_dir=tmp_path / ".runtime")
    lock_path = write_trading_lock(lock, runtime_dir=tmp_path / ".runtime")

    audit_path = write_safety_audit_log(
        report=report,
        lock=lock,
        report_path=report_path,
        lock_path=lock_path,
        runtime_dir=tmp_path / ".runtime",
    )

    assert audit_path.parent == tmp_path / ".runtime" / "safety" / "audit"
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert payload["status"] == "HALT"
    assert payload["issue_count"] == 1
    assert payload["trading_locked"] is True
    assert payload["broker_snapshot_id"] == "broker-snapshot-1"
    assert payload["report_path"] == str(report_path)
    assert payload["lock_path"] == str(lock_path)
