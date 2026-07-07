"""Notification payload models for Runtime v2."""

from __future__ import annotations

from dataclasses import dataclass


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
    derived: bool = True
    not_current_state: bool = True

