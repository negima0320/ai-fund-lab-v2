from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ai_fund_lab_v2.safety.models import SafetyStatus, utc_now_iso


class UnlockApplyStatus(str, Enum):
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class UnlockApplyResult:
    applied: bool
    status: UnlockApplyStatus
    approval_request_id: str | None
    applied_by: str | None
    latest_report_status: SafetyStatus | None
    message: str
    applied_at: str = field(default_factory=utc_now_iso)
