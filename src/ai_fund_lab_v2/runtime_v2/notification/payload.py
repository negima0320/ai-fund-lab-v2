"""Notification payload builder for Runtime v2."""

from __future__ import annotations

import hashlib

from ai_fund_lab_v2.runtime_v2.notification.models import NotificationPayload
from ai_fund_lab_v2.runtime_v2.report.models import ReportArtifact


def build_notification_payload(
    *,
    report: ReportArtifact,
    channel: str,
) -> NotificationPayload:
    if not channel:
        raise ValueError("channel is required")
    title = f"Runtime report {report.business_date}"
    body = _body(report)
    payload_hash = _hash("|".join((report.report_id, channel, title, body)))
    return NotificationPayload(
        payload_id="payload-" + payload_hash[:16],
        payload_hash=payload_hash,
        mode=report.mode,
        environment=report.environment,
        business_date=report.business_date,
        channel=channel,
        title=title,
        body=body,
        source_report_id=report.report_id,
        review_required=report.review_required,
        created_at=report.created_at,
    )


def _body(report: ReportArtifact) -> str:
    return "\n".join(f"{section.title}: {section.content}" for section in report.sections)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

