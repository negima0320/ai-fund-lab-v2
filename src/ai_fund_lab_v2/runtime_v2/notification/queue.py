"""Notification delivery queue models and builders."""

from __future__ import annotations

import hashlib

from ai_fund_lab_v2.runtime_v2.notification.models import (
    DeliveryQueueEntry,
    DeliveryQueueStatus,
    NotificationPayload,
)


def build_delivery_queue(
    *,
    payload: NotificationPayload,
    channels: tuple[str, ...],
    delivery_mode: str = "payload-only",
) -> tuple[DeliveryQueueEntry, ...]:
    if not channels:
        return ()
    return tuple(
        DeliveryQueueEntry(
            queue_id=_queue_id(payload.payload_hash, channel, payload.business_date),
            payload_id=payload.payload_id,
            payload_hash=payload.payload_hash,
            channel=channel,
            business_date=payload.business_date,
            status=DeliveryQueueStatus.PENDING,
            delivery_mode=delivery_mode,
            review_required=payload.review_required,
            created_at=payload.created_at,
        )
        for channel in channels
    )


def _queue_id(payload_hash: str, channel: str, business_date: str) -> str:
    raw = "|".join((payload_hash, channel, business_date))
    return "notification-queue-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
