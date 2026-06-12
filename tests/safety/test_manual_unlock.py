from pathlib import Path

import pytest

from ai_fund_lab_v2.safety import (
    ManualUnlockError,
    SafetyReport,
    SafetyStatus,
    TradingLock,
    approve_unlock_request,
    create_unlock_request,
)


def test_ok_report_creates_unlock_request_and_audit(tmp_path: Path) -> None:
    request = create_unlock_request(ok_report(), requested_by="operator", reason="checked report", runtime_dir=tmp_path / ".runtime", lock_id="lock-1")

    assert request.request_id.startswith("unlock_")
    assert request.requested_by == "operator"
    assert request.reason == "checked report"
    assert request.lock_id == "lock-1"
    assert len(list((tmp_path / ".runtime" / "safety" / "unlock" / "requests").glob("*.json"))) == 1
    assert len(list((tmp_path / ".runtime" / "safety" / "unlock" / "audit").glob("*.json"))) == 1


def test_request_requires_requested_by_and_reason(tmp_path: Path) -> None:
    with pytest.raises(ManualUnlockError, match="requested_by"):
        create_unlock_request(ok_report(), requested_by="", reason="checked", runtime_dir=tmp_path / ".runtime")
    with pytest.raises(ManualUnlockError, match="reason"):
        create_unlock_request(ok_report(), requested_by="operator", reason="", runtime_dir=tmp_path / ".runtime")


def test_halt_report_cannot_be_approved_and_writes_rejected_audit(tmp_path: Path) -> None:
    request = create_unlock_request(ok_report(), requested_by="operator", reason="checked", runtime_dir=tmp_path / ".runtime")

    with pytest.raises(ManualUnlockError, match="must be OK"):
        approve_unlock_request(request, halt_report(), approved_by="reviewer", approval_reason="still halt", runtime_dir=tmp_path / ".runtime")

    audit_files = list((tmp_path / ".runtime" / "safety" / "unlock" / "audit").glob("*.json"))
    assert len(audit_files) == 2
    assert any("REJECTED" in path.read_text(encoding="utf-8") for path in audit_files)


def test_warning_report_cannot_be_approved(tmp_path: Path) -> None:
    request = create_unlock_request(ok_report(), requested_by="operator", reason="checked", runtime_dir=tmp_path / ".runtime")

    with pytest.raises(ManualUnlockError, match="must be OK"):
        approve_unlock_request(request, warning_report(), approved_by="reviewer", approval_reason="still warning", runtime_dir=tmp_path / ".runtime")


def test_ok_report_can_be_approved_and_writes_approval_and_audit(tmp_path: Path) -> None:
    request = create_unlock_request(ok_report(), requested_by="operator", reason="checked", runtime_dir=tmp_path / ".runtime")

    approval = approve_unlock_request(request, ok_report(), approved_by="reviewer", approval_reason="OK after reconciliation", runtime_dir=tmp_path / ".runtime")

    assert approval.request_id == request.request_id
    assert approval.approved_by == "reviewer"
    assert len(list((tmp_path / ".runtime" / "safety" / "unlock" / "approvals").glob("*.json"))) == 1
    assert len(list((tmp_path / ".runtime" / "safety" / "unlock" / "audit").glob("*.json"))) == 2


def test_approval_requires_approved_by_and_reason(tmp_path: Path) -> None:
    request = create_unlock_request(ok_report(), requested_by="operator", reason="checked", runtime_dir=tmp_path / ".runtime")

    with pytest.raises(ManualUnlockError, match="approved_by"):
        approve_unlock_request(request, ok_report(), approved_by="", approval_reason="OK", runtime_dir=tmp_path / ".runtime")
    with pytest.raises(ManualUnlockError, match="approval_reason"):
        approve_unlock_request(request, ok_report(), approved_by="reviewer", approval_reason="", runtime_dir=tmp_path / ".runtime")


def test_manual_unlock_does_not_disable_or_delete_lock(tmp_path: Path) -> None:
    lock = TradingLock(is_locked=True, reason="cash_mismatch", status=SafetyStatus.HALT)
    request = create_unlock_request(ok_report(), requested_by="operator", reason="checked", runtime_dir=tmp_path / ".runtime", lock_id="lock-1")

    approve_unlock_request(request, ok_report(), approved_by="reviewer", approval_reason="OK after reconciliation", runtime_dir=tmp_path / ".runtime")

    assert lock.is_locked is True
    assert lock.status == SafetyStatus.HALT
    assert not (tmp_path / ".runtime" / "safety" / "locks").exists()


def ok_report() -> SafetyReport:
    return SafetyReport(status=SafetyStatus.OK, checked_at="2999-01-01T00:00:00+00:00", broker_snapshot_id="broker-1", issue_count=0, issues=(), trading_locked=False)


def halt_report() -> SafetyReport:
    return SafetyReport(status=SafetyStatus.HALT, checked_at="2999-01-01T00:00:00+00:00", broker_snapshot_id="broker-1", issue_count=1, issues=(), trading_locked=True)


def warning_report() -> SafetyReport:
    return SafetyReport(status=SafetyStatus.WARNING, checked_at="2999-01-01T00:00:00+00:00", broker_snapshot_id="broker-1", issue_count=1, issues=(), trading_locked=False)
