from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.safety.lock_apply_models import UnlockApplyResult, UnlockApplyStatus
from ai_fund_lab_v2.safety.lock_state_writer import write_unlock_applied_state
from ai_fund_lab_v2.safety.models import SafetyReport, SafetyStatus
from ai_fund_lab_v2.safety.unlock_apply_audit_writer import write_unlock_apply_audit
from ai_fund_lab_v2.safety.unlock_apply_policy import can_apply_unlock
from ai_fund_lab_v2.safety.unlock_models import UnlockApproval


def apply_manual_unlock(
    approval: UnlockApproval | None,
    latest_report: SafetyReport | None,
    applied_by: str,
    runtime_dir: Path | str = ".runtime",
) -> UnlockApplyResult:
    allowed, message = can_apply_unlock(approval, latest_report, applied_by)
    if not allowed:
        result = UnlockApplyResult(
            applied=False,
            status=UnlockApplyStatus.REJECTED,
            approval_request_id=approval.request_id if approval else None,
            applied_by=applied_by.strip() or None,
            latest_report_status=latest_report.status if latest_report else None,
            message=message,
        )
        write_unlock_apply_audit(result, runtime_dir=runtime_dir)
        return result
    result = UnlockApplyResult(
        applied=True,
        status=UnlockApplyStatus.APPLIED,
        approval_request_id=approval.request_id if approval else None,
        applied_by=applied_by.strip(),
        latest_report_status=latest_report.status if latest_report else SafetyStatus.OK,
        message=message,
    )
    write_unlock_applied_state(result, runtime_dir=runtime_dir)
    write_unlock_apply_audit(result, runtime_dir=runtime_dir)
    return result
