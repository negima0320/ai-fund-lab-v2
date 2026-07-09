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
        run_id="",
        current_portfolio={},
        today_operation={},
        execution_equivalent_count=0,
        warnings=(),
        severity="REVIEW_REQUIRED" if report.review_required else "INFO",
    )


def build_notification_payload_from_summary(
    *,
    summary: dict,
    channel: str,
    source_report_id: str,
) -> NotificationPayload:
    if not channel:
        raise ValueError("channel is required")
    business_date = str(summary.get("business_date") or "")
    current_portfolio = dict(summary.get("current_portfolio") or {})
    today_operation = dict(summary.get("today_operation") or {})
    warning_summary = summary.get("warning_summary") or {}
    warnings = tuple(str(note) for note in warning_summary.get("notes") or ())
    review_required = bool(today_operation.get("review_required") or summary.get("reconcile", {}).get("review_required"))
    severity = "REVIEW_REQUIRED" if review_required else "INFO"
    execution_equivalent_count = int(
        today_operation.get("execution_equivalent_count")
        or summary.get("notification", {}).get("execution_equivalent_count")
        or 0
    )
    title = f"Runtime report {business_date}"
    body = _summary_body(
        business_date=business_date,
        current_portfolio=current_portfolio,
        today_operation=today_operation,
        severity=severity,
    )
    payload_hash = _hash("|".join((source_report_id, channel, title, body)))
    return NotificationPayload(
        payload_id="payload-" + payload_hash[:16],
        payload_hash=payload_hash,
        mode=str(summary.get("runtime_mode") or summary.get("mode") or ""),
        environment=str(summary.get("environment") or ""),
        business_date=business_date,
        channel=channel,
        title=title,
        body=body,
        source_report_id=source_report_id,
        review_required=review_required,
        created_at=business_date,
        run_id=str((summary.get("current_run") or {}).get("run_id") or ""),
        current_portfolio=current_portfolio,
        today_operation=today_operation,
        execution_equivalent_count=execution_equivalent_count,
        warnings=warnings,
        severity=severity,
    )


def _body(report: ReportArtifact) -> str:
    return "\n".join(f"{section.title}: {section.content}" for section in report.sections)


def _summary_body(
    *,
    business_date: str,
    current_portfolio: dict,
    today_operation: dict,
    severity: str,
) -> str:
    return "\n".join(
        (
            f"business_date={business_date}",
            f"severity={severity}",
            f"total_equity={current_portfolio.get('total_equity')}",
            f"accepted_count={today_operation.get('accepted_count')}",
            f"execution_equivalent_count={today_operation.get('execution_equivalent_count')}",
        )
    )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
