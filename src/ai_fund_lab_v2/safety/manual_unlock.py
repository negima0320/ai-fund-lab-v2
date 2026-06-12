from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.safety.models import SafetyReport, utc_now_iso
from ai_fund_lab_v2.safety.unlock_models import UnlockApproval, UnlockAuditRecord, UnlockAuditStatus, UnlockRequest
from ai_fund_lab_v2.safety.unlock_policy import can_approve_unlock, can_request_unlock
from ai_fund_lab_v2.safety.unlock_writer import write_unlock_approval, write_unlock_audit, write_unlock_request


class ManualUnlockError(RuntimeError):
    """Raised when manual unlock policy requirements are not satisfied."""


def create_unlock_request(
    latest_report: SafetyReport,
    requested_by: str,
    reason: str,
    runtime_dir: Path | str = ".runtime",
    lock_id: str | None = None,
    latest_report_path: str | None = None,
) -> UnlockRequest:
    allowed, message = can_request_unlock(latest_report, requested_by, reason)
    if not allowed:
        raise ManualUnlockError(message)
    request = UnlockRequest(
        requested_by=requested_by.strip(),
        reason=reason.strip(),
        latest_report_status=latest_report.status,
        lock_id=lock_id,
        latest_report_path=latest_report_path,
    )
    write_unlock_request(request, runtime_dir=runtime_dir)
    write_unlock_audit(
        UnlockAuditRecord(
            request_id=request.request_id,
            lock_id=request.lock_id,
            status=UnlockAuditStatus.REQUESTED,
            approved_by=None,
            requested_by=request.requested_by,
            reason=request.reason,
            reconciliation_status=latest_report.status,
            safety_report_path=latest_report_path,
            message=message,
        ),
        runtime_dir=runtime_dir,
    )
    return request


def approve_unlock_request(
    request: UnlockRequest,
    latest_report: SafetyReport,
    approved_by: str,
    approval_reason: str,
    runtime_dir: Path | str = ".runtime",
    safety_report_path: str | None = None,
) -> UnlockApproval:
    allowed, message = can_approve_unlock(request, latest_report, approved_by, approval_reason)
    if not allowed:
        _write_rejected_audit(request, latest_report, approved_by, approval_reason, message, runtime_dir, safety_report_path)
        raise ManualUnlockError(message)
    approval = UnlockApproval(
        request_id=request.request_id,
        approved_by=approved_by.strip(),
        approval_reason=approval_reason.strip(),
        reconciliation_status=latest_report.status,
        safety_report_path=safety_report_path,
    )
    write_unlock_approval(approval, runtime_dir=runtime_dir)
    write_unlock_audit(
        UnlockAuditRecord(
            request_id=request.request_id,
            lock_id=request.lock_id,
            status=UnlockAuditStatus.APPROVED,
            approved_by=approval.approved_by,
            requested_by=request.requested_by,
            reason=request.reason,
            reconciliation_status=latest_report.status,
            safety_report_path=safety_report_path,
            message=message,
            completed_at=utc_now_iso(),
        ),
        runtime_dir=runtime_dir,
    )
    return approval


def _write_rejected_audit(
    request: UnlockRequest,
    latest_report: SafetyReport,
    approved_by: str,
    approval_reason: str,
    message: str,
    runtime_dir: Path | str,
    safety_report_path: str | None,
) -> None:
    _ = approval_reason
    write_unlock_audit(
        UnlockAuditRecord(
            request_id=request.request_id,
            lock_id=request.lock_id,
            status=UnlockAuditStatus.REJECTED,
            approved_by=approved_by.strip() or None,
            requested_by=request.requested_by,
            reason=request.reason,
            reconciliation_status=latest_report.status,
            safety_report_path=safety_report_path,
            message=message,
            completed_at=utc_now_iso(),
        ),
        runtime_dir=runtime_dir,
    )
