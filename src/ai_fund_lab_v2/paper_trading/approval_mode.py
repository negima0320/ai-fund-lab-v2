from __future__ import annotations

from dataclasses import dataclass


MANUAL_REQUIRED = "manual_required"
AUTO_FOR_PAPER_TRADING = "auto_for_paper_trading"
REVIEW_ONLY = "review_only"
APPROVAL_MODES = {MANUAL_REQUIRED, AUTO_FOR_PAPER_TRADING, REVIEW_ONLY}
AUTO_APPROVAL_REVIEW_STATUS = "auto_approved_for_paper_trading"


@dataclass(frozen=True)
class ApprovalModeValidationResult:
    status: str
    approval_mode: str
    execution_mode: str
    allowed: bool
    blocked_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "approval_mode": self.approval_mode,
            "execution_mode": self.execution_mode,
            "allowed": self.allowed,
            "blocked_reasons": list(self.blocked_reasons),
        }


def validate_approval_mode(*, approval_mode: str, execution_mode: str) -> ApprovalModeValidationResult:
    mode = str(approval_mode or "").strip()
    execution = str(execution_mode or "").strip()
    blocked: list[str] = []
    if mode not in APPROVAL_MODES:
        blocked.append("approval_mode_unsupported")
    if mode == AUTO_FOR_PAPER_TRADING and execution != "paper-trading":
        blocked.append("auto_approval_only_allowed_in_paper_trading_mode")
    if execution == "broker" and mode == AUTO_FOR_PAPER_TRADING:
        blocked.append("auto_approval_blocked_in_broker_mode")
    allowed = not blocked
    return ApprovalModeValidationResult(
        status="APPROVAL_MODE_ALLOWED" if allowed else "APPROVAL_MODE_BLOCKED",
        approval_mode=mode,
        execution_mode=execution,
        allowed=allowed,
        blocked_reasons=tuple(blocked),
    )

