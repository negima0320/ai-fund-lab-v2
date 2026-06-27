from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from ai_fund_lab_v2.runtime.order_command import OrderCommand, OrderSide
from ai_fund_lab_v2.runtime.runtime_mode import RuntimeMode


class OrderAuthorizationStatus(str, Enum):
    APPROVED = "APPROVED"
    BLOCKED_NO_APPROVAL = "BLOCKED_NO_APPROVAL"
    BLOCKED_LIVE_ORDER_DISABLED = "BLOCKED_LIVE_ORDER_DISABLED"
    BLOCKED_APPROVAL_SCOPE_MISMATCH = "BLOCKED_APPROVAL_SCOPE_MISMATCH"
    BLOCKED_APPROVAL_EXPIRED = "BLOCKED_APPROVAL_EXPIRED"
    BLOCKED_SECOND_PASSWORD_MISSING = "BLOCKED_SECOND_PASSWORD_MISSING"
    BLOCKED_PRODUCTION_PROHIBITED = "BLOCKED_PRODUCTION_PROHIBITED"


@dataclass(frozen=True)
class OrderApprovalScope:
    approval_id: str
    environment: RuntimeMode
    issue_code: str
    side: OrderSide
    quantity: Decimal
    max_notional: Decimal
    expires_at: datetime

    def __post_init__(self) -> None:
        if not self.approval_id:
            raise ValueError("approval_id is required.")
        if self.quantity <= Decimal("0"):
            raise ValueError("approval quantity must be positive.")
        if self.max_notional < Decimal("0"):
            raise ValueError("approval max_notional must be non-negative.")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["environment"] = self.environment.value
        payload["side"] = self.side.value
        payload["quantity"] = str(self.quantity)
        payload["max_notional"] = str(self.max_notional)
        payload["expires_at"] = self.expires_at.isoformat()
        return payload


@dataclass(frozen=True)
class OrderAuthorizationResult:
    status: OrderAuthorizationStatus
    approved: bool = False
    reason: str = ""
    second_password_value_saved: bool = False
    broker_api_called: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


@dataclass(frozen=True)
class OrderApprovalGate:
    production_orders_prohibited: bool = True

    def authorize(
        self,
        command: OrderCommand,
        approval_scope: OrderApprovalScope | None,
        *,
        second_password_present: bool,
        now: datetime | None = None,
    ) -> OrderAuthorizationResult:
        if command.environment is RuntimeMode.PRODUCTION and self.production_orders_prohibited:
            return _blocked(OrderAuthorizationStatus.BLOCKED_PRODUCTION_PROHIBITED, "production_order_prohibited")
        if not command.live_order_allowed:
            return _blocked(OrderAuthorizationStatus.BLOCKED_LIVE_ORDER_DISABLED, "live_order_allowed_false")
        if approval_scope is None:
            return _blocked(OrderAuthorizationStatus.BLOCKED_NO_APPROVAL, "approval_missing")
        current_time = _aware_utc(now)
        if _aware_utc(approval_scope.expires_at) <= current_time:
            return _blocked(OrderAuthorizationStatus.BLOCKED_APPROVAL_EXPIRED, "approval_expired")
        if not _scope_matches(command, approval_scope):
            return _blocked(OrderAuthorizationStatus.BLOCKED_APPROVAL_SCOPE_MISMATCH, "approval_scope_mismatch")
        if not second_password_present:
            return _blocked(OrderAuthorizationStatus.BLOCKED_SECOND_PASSWORD_MISSING, "second_password_missing")
        return OrderAuthorizationResult(status=OrderAuthorizationStatus.APPROVED, approved=True, reason="approved_for_demo_dry_run")


def _scope_matches(command: OrderCommand, scope: OrderApprovalScope) -> bool:
    notional = command.quantity * (command.limit_price if command.limit_price > Decimal("0") else Decimal("0"))
    return (
        command.approval_id == scope.approval_id
        and command.environment is scope.environment
        and command.issue_code == scope.issue_code
        and command.side is scope.side
        and command.quantity == scope.quantity
        and notional <= scope.max_notional
    )


def _blocked(status: OrderAuthorizationStatus, reason: str) -> OrderAuthorizationResult:
    return OrderAuthorizationResult(status=status, approved=False, reason=reason)


def _aware_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
