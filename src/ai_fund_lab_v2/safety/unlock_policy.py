from __future__ import annotations

from ai_fund_lab_v2.safety.models import SafetyReport, SafetyStatus
from ai_fund_lab_v2.safety.unlock_models import UnlockRequest


def can_request_unlock(
    latest_report: SafetyReport,
    requested_by: str,
    reason: str,
) -> tuple[bool, str]:
    if latest_report is None:
        return False, "latest_report is required"
    if not requested_by.strip():
        return False, "requested_by is required"
    if not reason.strip():
        return False, "reason is required"
    return True, "unlock request can be created"


def can_approve_unlock(
    request: UnlockRequest,
    latest_report: SafetyReport,
    approved_by: str,
    approval_reason: str,
) -> tuple[bool, str]:
    if request is None:
        return False, "unlock request is required"
    if latest_report is None:
        return False, "latest_report is required"
    if not approved_by.strip():
        return False, "approved_by is required"
    if not approval_reason.strip():
        return False, "approval_reason is required"
    if latest_report.status != SafetyStatus.OK:
        return False, "latest_report status must be OK before unlock approval"
    return True, "unlock request can be approved"
