"""Notification payload models for Runtime v2."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DeliveryQueueStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


@dataclass(frozen=True)
class NotificationPayload:
    payload_id: str
    payload_hash: str
    mode: str
    environment: str
    business_date: str
    channel: str
    title: str
    body: str
    source_report_id: str
    review_required: bool
    created_at: str
    run_id: str = ""
    current_portfolio: dict[str, Any] = field(default_factory=dict)
    today_operation: dict[str, Any] = field(default_factory=dict)
    execution_equivalent_count: int = 0
    warnings: tuple[str, ...] = ()
    severity: str = "INFO"
    runtime_state: str = ""
    reason_summary: str = ""
    policy_summary: str = ""
    safety_summary: str = ""
    guard_summary: str = ""
    buy_ai_summary: str = ""
    selected_candidates: int = 0
    selected_top_rank: int | None = None
    position_management_summary: str = ""
    next_operator_action: str = ""
    non_trading_day_demo_override: bool = False
    production_equivalent: bool = True
    acceptance_scope: str = "regular_runtime"
    notification_delivery_status: str = "PAYLOAD_ONLY"
    notification_sent: bool = False
    derived: bool = True
    not_current_state: bool = True


@dataclass(frozen=True)
class DeliveryQueueEntry:
    queue_id: str
    payload_id: str
    payload_hash: str
    channel: str
    business_date: str
    status: DeliveryQueueStatus
    delivery_mode: str
    review_required: bool
    created_at: str
    derived: bool = True
    not_current_state: bool = True
    not_submit_source: bool = True


@dataclass(frozen=True)
class DeliveryResult:
    result_id: str
    queue_id: str
    payload_id: str
    channel: str
    business_date: str
    status: DeliveryQueueStatus
    sender: str
    delivery_mode: str
    attempted: bool
    sent: bool
    review_required: bool
    reason: str
    created_at: str
    derived: bool = True
    not_current_state: bool = True
    not_submit_source: bool = True
