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
