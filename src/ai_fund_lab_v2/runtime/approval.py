from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from ai_fund_lab_v2.runtime.runtime_mode import RuntimeMode


class ApprovalStatus(str, Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    MISSING = "MISSING"


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    environment: RuntimeMode
    status: ApprovalStatus = ApprovalStatus.MISSING
    approver: str = ""
    reason: str = ""
    auto_paper_approval: bool = False

    @property
    def approved(self) -> bool:
        return self.status is ApprovalStatus.APPROVED

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["environment"] = self.environment.value
        payload["status"] = self.status.value
        return payload


def paper_auto_approval(*, approval_id: str = "paper_auto_approval") -> ApprovalRecord:
    return ApprovalRecord(
        approval_id=approval_id,
        environment=RuntimeMode.PAPER,
        status=ApprovalStatus.APPROVED,
        approver="paper_runtime",
        reason="paper_only_auto_approval",
        auto_paper_approval=True,
    )


def explicit_demo_approval(*, approval_id: str, approver: str) -> ApprovalRecord:
    return ApprovalRecord(
        approval_id=approval_id,
        environment=RuntimeMode.DEMO,
        status=ApprovalStatus.APPROVED,
        approver=approver,
        reason="explicit_demo_approval",
    )


def explicit_production_approval(*, approval_id: str, approver: str) -> ApprovalRecord:
    return ApprovalRecord(
        approval_id=approval_id,
        environment=RuntimeMode.PRODUCTION,
        status=ApprovalStatus.APPROVED,
        approver=approver,
        reason="explicit_production_approval",
    )


def default_deny(environment: RuntimeMode, *, reason: str = "default_deny") -> ApprovalRecord:
    return ApprovalRecord(approval_id="", environment=environment, status=ApprovalStatus.DENIED, reason=reason)
