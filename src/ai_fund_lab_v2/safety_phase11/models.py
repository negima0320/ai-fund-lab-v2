from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4


class SafetyState(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    MARKET_STRESS = "MARKET_STRESS"
    BUY_REVIEW_REQUIRED = "BUY_REVIEW_REQUIRED"
    BUY_OPPORTUNITY_REVIEW = "BUY_OPPORTUNITY_REVIEW"
    BUY_STOP = "BUY_STOP"
    SYSTEM_EMERGENCY_STOP = "SYSTEM_EMERGENCY_STOP"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    RECOVERY_CANDIDATE = "RECOVERY_CANDIDATE"
    MANUAL_APPROVED = "MANUAL_APPROVED"


class SafetyDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class SafetySeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"
    EMERGENCY = "EMERGENCY"


class SafetyReviewClass(str, Enum):
    BLOCKING_REVIEW = "BLOCKING_REVIEW"
    NON_BLOCKING_REVIEW = "NON_BLOCKING_REVIEW"
    INFO_ONLY = "INFO_ONLY"


class SafetyGuardName(str, Enum):
    DUPLICATE_ORDER = "DUPLICATE_ORDER"
    CASH_BUFFER = "CASH_BUFFER"
    MAX_EXPOSURE = "MAX_EXPOSURE"
    QUOTE_STALE = "QUOTE_STALE"
    BROKER_SNAPSHOT_FRESHNESS = "BROKER_SNAPSHOT_FRESHNESS"
    ORDER_EXECUTION_CONSISTENCY = "ORDER_EXECUTION_CONSISTENCY"
    MARKET_CRASH = "MARKET_CRASH"
    BROKER_DIVERGENCE = "BROKER_DIVERGENCE"
    DAILY_LOSS = "DAILY_LOSS"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    INDIVIDUAL_CRASH = "INDIVIDUAL_CRASH"
    MARKET_RECOVERY = "MARKET_RECOVERY"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safety_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value).replace(",", ""))


def decimal_or_zero(value: Any) -> Decimal:
    parsed = decimal_or_none(value)
    return parsed if parsed is not None else Decimal("0")


@dataclass(frozen=True)
class SafetyEvent:
    guard_name: SafetyGuardName
    decision: SafetyDecision
    severity: SafetySeverity
    reason_code: str
    message: str
    state_before: SafetyState
    state_after: SafetyState | None = None
    runtime_id: str | None = None
    business_date: str | None = None
    environment: str | None = None
    issue_code: str | None = None
    requires_human_review: bool = False
    auto_trade_executed: bool = False
    raw_response_saved: bool = False
    event_id: str = field(default_factory=lambda: safety_id("safety_event"))
    created_at: str = field(default_factory=utc_now_iso)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HumanReviewItem:
    guard_name: SafetyGuardName
    reason_code: str
    message: str
    severity: SafetySeverity
    recommended_action: str
    issue_code: str | None = None
    event_id: str | None = None
    review_id: str = field(default_factory=lambda: safety_id("human_review"))
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class SafetyCheckInput:
    current_state: SafetyState | str = SafetyState.NORMAL
    runtime_id: str | None = None
    business_date: str | None = None
    environment: str | None = None
    order_plan: dict[str, Any] = field(default_factory=dict)
    open_orders: tuple[dict[str, Any], ...] = ()
    positions: tuple[dict[str, Any], ...] = ()
    quotes: dict[str, dict[str, Any]] = field(default_factory=dict)
    market: dict[str, Any] = field(default_factory=dict)
    broker_snapshot: dict[str, Any] = field(default_factory=dict)
    runtime_state: dict[str, Any] = field(default_factory=dict)
    ledger_state: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    manual_emergency_stop: bool = False


@dataclass(frozen=True)
class SafetyCheckResult:
    guard_name: SafetyGuardName
    decision: SafetyDecision
    severity: SafetySeverity
    reason_code: str
    message: str
    state_before: SafetyState
    state_after: SafetyState | None = None
    events: tuple[SafetyEvent, ...] = ()
    review_items: tuple[HumanReviewItem, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def allow(
        cls,
        guard_name: SafetyGuardName,
        state_before: SafetyState,
        *,
        reason_code: str = "ALLOW",
        message: str = "Safety guard passed.",
        details: dict[str, Any] | None = None,
    ) -> "SafetyCheckResult":
        return cls(
            guard_name=guard_name,
            decision=SafetyDecision.ALLOW,
            severity=SafetySeverity.INFO,
            reason_code=reason_code,
            message=message,
            state_before=state_before,
            details=details or {},
        )
