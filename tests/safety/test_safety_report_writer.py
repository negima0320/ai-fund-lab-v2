import json
from pathlib import Path

from ai_fund_lab_v2.safety import (
    ReconciliationIssue,
    ReconciliationResult,
    ReconciliationSeverity,
    SafetyStatus,
    build_safety_report,
    build_trading_lock,
    write_safety_report,
    write_trading_lock,
)


def test_safety_report_and_lock_are_written_under_runtime_safety(tmp_path: Path) -> None:
    result = ReconciliationResult(
        status=SafetyStatus.HALT,
        issues=(
            ReconciliationIssue(
                code="cash_mismatch",
                severity=ReconciliationSeverity.HALT,
                message="cash mismatch",
                expected="1000",
                actual="999",
            ),
        ),
    )
    lock = build_trading_lock(result)
    report = build_safety_report(result, lock, broker_snapshot_id="broker-snapshot-1")

    report_path = write_safety_report(report, runtime_dir=tmp_path / ".runtime")
    lock_path = write_trading_lock(lock, runtime_dir=tmp_path / ".runtime")

    assert report_path.parent == tmp_path / ".runtime" / "safety" / "reports"
    assert lock_path.parent == tmp_path / ".runtime" / "safety" / "locks"
    assert report_path.is_file()
    assert lock_path.is_file()
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    lock_payload = json.loads(lock_path.read_text(encoding="utf-8"))
    assert report_payload["status"] == "HALT"
    assert report_payload["issue_count"] == 1
    assert report_payload["trading_locked"] is True
    assert lock_payload["is_locked"] is True
    assert lock_payload["issues"][0]["code"] == "cash_mismatch"


def test_safety_writer_sanitizes_secret_like_values(tmp_path: Path) -> None:
    result = ReconciliationResult(
        status=SafetyStatus.HALT,
        issues=(
            ReconciliationIssue(
                code="api_auth_failed",
                severity=ReconciliationSeverity.HALT,
                message="sAuthId=secret-auth token=secret-token https://example.invalid/session",
            ),
        ),
    )
    lock = build_trading_lock(result)
    report = build_safety_report(result, lock, broker_snapshot_id="broker-snapshot-1")

    report_path = write_safety_report(report, runtime_dir=tmp_path / ".runtime")
    lock_path = write_trading_lock(lock, runtime_dir=tmp_path / ".runtime")

    saved_text = report_path.read_text(encoding="utf-8") + lock_path.read_text(encoding="utf-8")
    assert "secret-auth" not in saved_text
    assert "secret-token" not in saved_text
    assert "https://example.invalid/session" not in saved_text
    assert "[REDACTED]" in saved_text
