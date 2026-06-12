from __future__ import annotations

from ai_fund_lab_v2.safety.models import SafetyReport, SafetyStatus
from ai_fund_lab_v2.safety.unlock_models import UnlockApproval


def can_apply_unlock(
    approval: UnlockApproval | None,
    latest_report: SafetyReport | None,
    applied_by: str,
) -> tuple[bool, str]:
    if approval is None:
        return False, "unlock approval is required"
    if latest_report is None:
        return False, "latest safety report is required"
    if not applied_by.strip():
        return False, "applied_by is required"
    if latest_report.status != SafetyStatus.OK:
        return False, "latest safety report status must be OK"
    if approval.reconciliation_status != SafetyStatus.OK:
        return False, "approval reconciliation_status must be OK"
    if not approval.approved_by.strip():
        return False, "approval approved_by is required"
    if not approval.approval_reason.strip():
        return False, "approval approval_reason is required"
    message = "unlock can be applied"
    if approval.safety_report_path:
        message = "unlock can be applied; approval report path is informational and latest OK report takes precedence"
    return True, message
