"""Models for Runtime v2 state machine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuntimeState(str, Enum):
    IDLE = "IDLE"
    MARKET_DATA_READY = "MARKET_DATA_READY"
    FEATURE_READY = "FEATURE_READY"
    CURRENT_STATE_LOADED = "CURRENT_STATE_LOADED"
    AI_INFERENCE_DONE = "AI_INFERENCE_DONE"
    DAILY_PLAN_CREATED = "DAILY_PLAN_CREATED"
    PENDING_PROMOTED = "PENDING_PROMOTED"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    APPROVED = "APPROVED"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    POST_SEND_UNKNOWN = "POST_SEND_UNKNOWN"
    MONITORING_FILL = "MONITORING_FILL"
    LEDGER_UPDATED = "LEDGER_UPDATED"
    RECONCILED = "RECONCILED"
    REPORT_READY = "REPORT_READY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"
    HALT = "HALT"


@dataclass(frozen=True)
class RuntimeTransition:
    from_state: RuntimeState
    to_state: RuntimeState
    reason: str
    allowed: bool
    requires_review: bool = False
    side_effect_boundary: bool = False

