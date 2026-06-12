import json
from pathlib import Path

from ai_fund_lab_v2.safety import (
    SafetyStatus,
    UnlockApproval,
    UnlockAuditRecord,
    UnlockAuditStatus,
    UnlockRequest,
    write_unlock_approval,
    write_unlock_audit,
    write_unlock_request,
)


def test_unlock_request_approval_and_audit_are_saved(tmp_path: Path) -> None:
    request = UnlockRequest(requested_by="operator", reason="checked report", latest_report_status=SafetyStatus.OK, lock_id="lock-1")
    approval = UnlockApproval(request_id=request.request_id, approved_by="reviewer", approval_reason="OK after reconciliation", reconciliation_status=SafetyStatus.OK)
    audit = UnlockAuditRecord(
        request_id=request.request_id,
        lock_id=request.lock_id,
        status=UnlockAuditStatus.APPROVED,
        approved_by=approval.approved_by,
        requested_by=request.requested_by,
        reason=request.reason,
        reconciliation_status=SafetyStatus.OK,
        safety_report_path=".runtime/safety/reports/report.json",
        message="approved",
    )

    request_path = write_unlock_request(request, tmp_path / ".runtime")
    approval_path = write_unlock_approval(approval, tmp_path / ".runtime")
    audit_path = write_unlock_audit(audit, tmp_path / ".runtime")

    assert request_path.parent == tmp_path / ".runtime" / "safety" / "unlock" / "requests"
    assert approval_path.parent == tmp_path / ".runtime" / "safety" / "unlock" / "approvals"
    assert audit_path.parent == tmp_path / ".runtime" / "safety" / "unlock" / "audit"
    assert json.loads(request_path.read_text(encoding="utf-8"))["request_id"] == request.request_id
    assert json.loads(approval_path.read_text(encoding="utf-8"))["approved_by"] == "reviewer"
    assert json.loads(audit_path.read_text(encoding="utf-8"))["status"] == "APPROVED"


def test_unlock_writer_sanitizes_secret_like_values(tmp_path: Path) -> None:
    request = UnlockRequest(
        requested_by="operator",
        reason="token=secret-token cookie=secret-cookie password=secret-password https://example.invalid/session",
        latest_report_status=SafetyStatus.OK,
    )

    path = write_unlock_request(request, tmp_path / ".runtime")

    saved = path.read_text(encoding="utf-8")
    assert "secret-token" not in saved
    assert "secret-cookie" not in saved
    assert "secret-password" not in saved
    assert "https://example.invalid/session" not in saved
    assert "[REDACTED]" in saved
