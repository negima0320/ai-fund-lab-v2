"""Delivery ledger skeleton for Runtime v2 notification dedup."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    PAYLOAD_CREATED = "PAYLOAD_CREATED"
    READY_TO_SEND = "READY_TO_SEND"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    POST_SEND_UNKNOWN = "POST_SEND_UNKNOWN"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class DeliveryLedgerRecord:
    delivery_id: str
    payload_hash: str
    channel: str
    target_date: str
    status: DeliveryStatus
    sent_at: str
    retry_allowed: bool
    review_required: bool
    created_at: str


def is_duplicate_delivery(
    *,
    existing_records: tuple[DeliveryLedgerRecord, ...],
    payload_hash: str,
    channel: str,
    target_date: str,
) -> bool:
    return any(
        record.payload_hash == payload_hash
        and record.channel == channel
        and record.target_date == target_date
        for record in existing_records
    )
