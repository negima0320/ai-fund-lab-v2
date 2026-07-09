"""Notification sender interfaces for Runtime v2 Level 1 component review."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ai_fund_lab_v2.runtime_v2.notification.models import (
    DeliveryQueueEntry,
    DeliveryQueueStatus,
    DeliveryResult,
    NotificationPayload,
)


@dataclass(frozen=True)
class LineNotificationSender:
    delivery_mode: str = "payload-only"

    def deliver(self, *, payload: NotificationPayload, queue_entry: DeliveryQueueEntry) -> DeliveryResult:
        return _not_implemented_result(
            payload=payload,
            queue_entry=queue_entry,
            sender="line",
            delivery_mode=self.delivery_mode,
        )


@dataclass(frozen=True)
class DiscordNotificationSender:
    delivery_mode: str = "payload-only"

    def deliver(self, *, payload: NotificationPayload, queue_entry: DeliveryQueueEntry) -> DeliveryResult:
        return _not_implemented_result(
            payload=payload,
            queue_entry=queue_entry,
            sender="discord",
            delivery_mode=self.delivery_mode,
        )


def _not_implemented_result(
    *,
    payload: NotificationPayload,
    queue_entry: DeliveryQueueEntry,
    sender: str,
    delivery_mode: str,
) -> DeliveryResult:
    return DeliveryResult(
        result_id=_result_id(queue_entry.queue_id, sender),
        queue_id=queue_entry.queue_id,
        payload_id=payload.payload_id,
        channel=queue_entry.channel,
        business_date=payload.business_date,
        status=DeliveryQueueStatus.NOT_IMPLEMENTED,
        sender=sender,
        delivery_mode=delivery_mode,
        attempted=False,
        sent=False,
        review_required=False,
        reason="sender interface present; external delivery is not implemented in Level 1",
        created_at=payload.created_at,
    )


def _result_id(queue_id: str, sender: str) -> str:
    raw = "|".join((queue_id, sender))
    return "notification-result-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
