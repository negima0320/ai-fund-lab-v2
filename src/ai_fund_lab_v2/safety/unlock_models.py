from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from ai_fund_lab_v2.safety.models import SafetyStatus, utc_now_iso


class UnlockAuditStatus(str, Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def unlock_request_id() -> str:
    return f"unlock_{uuid4().hex}"


@dataclass(frozen=True)
class UnlockRequest:
    requested_by: str
    reason: str
    latest_report_status: SafetyStatus
    lock_id: str | None = None
    latest_report_path: str | None = None
    requires_reconciliation_ok: bool = True
    created_at: str = field(default_factory=utc_now_iso)
    request_id: str = field(default_factory=unlock_request_id)


@dataclass(frozen=True)
class UnlockApproval:
    request_id: str
    approved_by: str
    approval_reason: str
    reconciliation_status: SafetyStatus
    safety_report_path: str | None = None
    approved_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class UnlockAuditRecord:
    request_id: str
    lock_id: str | None
    status: UnlockAuditStatus
    approved_by: str | None
    requested_by: str
    reason: str
    reconciliation_status: SafetyStatus
    safety_report_path: str | None
    message: str
    created_at: str = field(default_factory=utc_now_iso)
    completed_at: str | None = None
