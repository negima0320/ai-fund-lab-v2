from pathlib import Path

from ai_fund_lab_v2.safety import (
    SafetyReport,
    SafetyStatus,
    UnlockApproval,
    UnlockApplyStatus,
    apply_manual_unlock,
)


def test_manual_unlock_apply_saves_applied_state_and_audit(tmp_path: Path) -> None:
    result = apply_manual_unlock(ok_approval(), ok_report(), applied_by="operator", runtime_dir=tmp_path / ".runtime")

    assert result.applied is True
    assert result.status == UnlockApplyStatus.APPLIED
    assert result.approval_request_id == "unlock-1"
    assert len(list((tmp_path / ".runtime" / "safety" / "locks").glob("unlock_applied_*.json"))) == 1
    assert len(list((tmp_path / ".runtime" / "safety" / "unlock" / "apply_audit").glob("*.json"))) == 1


def test_manual_unlock_apply_rejects_without_approval_and_writes_audit(tmp_path: Path) -> None:
    result = apply_manual_unlock(None, ok_report(), applied_by="operator", runtime_dir=tmp_path / ".runtime")

    assert result.applied is False
    assert result.status == UnlockApplyStatus.REJECTED
    assert result.approval_request_id is None
    assert len(list((tmp_path / ".runtime" / "safety" / "locks").glob("unlock_applied_*.json"))) == 0
    assert len(list((tmp_path / ".runtime" / "safety" / "unlock" / "apply_audit").glob("*.json"))) == 1


def test_manual_unlock_apply_rejects_without_latest_report(tmp_path: Path) -> None:
    result = apply_manual_unlock(ok_approval(), None, applied_by="operator", runtime_dir=tmp_path / ".runtime")

    assert result.applied is False
    assert result.status == UnlockApplyStatus.REJECTED


def test_manual_unlock_apply_rejects_halt_or_warning_report(tmp_path: Path) -> None:
    halt = apply_manual_unlock(ok_approval(), report(SafetyStatus.HALT), applied_by="operator", runtime_dir=tmp_path / ".runtime")
    warning = apply_manual_unlock(ok_approval(), report(SafetyStatus.WARNING), applied_by="operator", runtime_dir=tmp_path / ".runtime")

    assert halt.status == UnlockApplyStatus.REJECTED
    assert warning.status == UnlockApplyStatus.REJECTED


def test_manual_unlock_apply_rejects_without_applied_by(tmp_path: Path) -> None:
    result = apply_manual_unlock(ok_approval(), ok_report(), applied_by="", runtime_dir=tmp_path / ".runtime")

    assert result.applied is False
    assert result.status == UnlockApplyStatus.REJECTED


def test_manual_unlock_apply_rejects_approval_with_non_ok_reconciliation(tmp_path: Path) -> None:
    approval = UnlockApproval(
        request_id="unlock-1",
        approved_by="reviewer",
        approval_reason="checked",
        reconciliation_status=SafetyStatus.HALT,
    )

    result = apply_manual_unlock(approval, ok_report(), applied_by="operator", runtime_dir=tmp_path / ".runtime")

    assert result.applied is False
    assert result.status == UnlockApplyStatus.REJECTED


def test_manual_unlock_apply_does_not_delete_existing_lock_file(tmp_path: Path) -> None:
    lock_dir = tmp_path / ".runtime" / "safety" / "locks"
    lock_dir.mkdir(parents=True)
    existing_lock = lock_dir / "trading_lock_existing.json"
    existing_lock.write_text('{"is_locked": true}\n', encoding="utf-8")

    result = apply_manual_unlock(ok_approval(), ok_report(), applied_by="operator", runtime_dir=tmp_path / ".runtime")

    assert result.status == UnlockApplyStatus.APPLIED
    assert existing_lock.exists()
    assert len(list(lock_dir.glob("unlock_applied_*.json"))) == 1


def ok_approval() -> UnlockApproval:
    return UnlockApproval(
        request_id="unlock-1",
        approved_by="reviewer",
        approval_reason="OK after reconciliation",
        reconciliation_status=SafetyStatus.OK,
        safety_report_path=".runtime/safety/reports/old_report.json",
    )


def ok_report() -> SafetyReport:
    return report(SafetyStatus.OK)


def report(status: SafetyStatus) -> SafetyReport:
    return SafetyReport(status=status, checked_at="2999-01-01T00:00:00+00:00", broker_snapshot_id="broker-1", issue_count=0, issues=(), trading_locked=False)
