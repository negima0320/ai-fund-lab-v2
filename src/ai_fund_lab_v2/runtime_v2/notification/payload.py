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
        runtime_state="REVIEW_REQUIRED" if report.review_required else "INFO",
        reason_summary="report_review_required=" + str(report.review_required),
        next_operator_action="Review Runtime report." if report.review_required else "No operator action required.",
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
    reason_evidence = summary.get("reason_evidence") or {}
    buy_ai = summary.get("buy_ai") or {}
    position_management = summary.get("position_management") or {}
    notification_summary = summary.get("notification_payload") or {}
    override_summary = summary.get("non_trading_day_demo_override") or {}
    warnings = tuple(str(note) for note in warning_summary.get("notes") or ())
    review_required = bool(
        today_operation.get("review_required")
        or summary.get("reconcile", {}).get("review_required")
        or reason_evidence.get("review_required")
        or notification_summary.get("review_required")
    )
    severity = _classify_severity(summary=summary, reason_evidence=reason_evidence, review_required=review_required)
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
        reason_summary=str(reason_evidence.get("reason_summary") or notification_summary.get("reason_summary") or ""),
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
        runtime_state=str(reason_evidence.get("runtime_state") or notification_summary.get("runtime_state") or ""),
        reason_summary=str(reason_evidence.get("reason_summary") or notification_summary.get("reason_summary") or ""),
        policy_summary=str(reason_evidence.get("policy_summary") or notification_summary.get("policy_summary") or ""),
        safety_summary=str(reason_evidence.get("safety_summary") or notification_summary.get("safety_summary") or ""),
        guard_summary=str(reason_evidence.get("guard_summary") or notification_summary.get("guard_summary") or ""),
        buy_ai_summary=str(buy_ai.get("summary") or notification_summary.get("buy_ai_summary") or ""),
        selected_candidates=int(buy_ai.get("selected_candidates") or notification_summary.get("selected_candidates") or 0),
        selected_top_rank=buy_ai.get("selected_top_rank") or notification_summary.get("selected_top_rank"),
        position_management_summary=str(
            position_management.get("summary") or notification_summary.get("position_management_summary") or ""
        ),
        next_operator_action=str(
            reason_evidence.get("next_operator_action") or notification_summary.get("next_operator_action") or ""
        ),
        non_trading_day_demo_override=bool(
            notification_summary.get("non_trading_day_demo_override")
            or override_summary.get("non_trading_day_demo_override")
        ),
        production_equivalent=bool(
            notification_summary.get("production_equivalent", override_summary.get("production_equivalent", True))
        ),
        acceptance_scope=str(
            notification_summary.get("acceptance_scope") or override_summary.get("acceptance_scope") or "regular_runtime"
        ),
        notification_delivery_status="PAYLOAD_ONLY",
        notification_sent=False,
    )


def _body(report: ReportArtifact) -> str:
    return "\n".join(f"{section.title}: {section.content}" for section in report.sections)


def _summary_body(
    *,
    business_date: str,
    current_portfolio: dict,
    today_operation: dict,
    severity: str,
    reason_summary: str = "",
) -> str:
    return "\n".join(
        (
            f"business_date={business_date}",
            f"severity={severity}",
            f"reason_summary={reason_summary}",
            f"total_equity={current_portfolio.get('total_equity')}",
            f"accepted_count={today_operation.get('accepted_count')}",
            f"execution_equivalent_count={today_operation.get('execution_equivalent_count')}",
        )
    )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _classify_severity(*, summary: dict, reason_evidence: dict, review_required: bool) -> str:
    runtime_state = str(
        reason_evidence.get("runtime_state")
        or (summary.get("current_run") or {}).get("final_state")
        or summary.get("runtime_state")
        or ""
    ).upper()
    safety = reason_evidence.get("safety_evidence") or {}
    guard = reason_evidence.get("submit_guard_evidence") or {}
    if runtime_state == "HALT" or safety.get("halt_runtime") or safety.get("emergency_stop"):
        return "HALT"
    if runtime_state == "BLOCKED" or (summary.get("reconcile") or {}).get("blocked"):
        return "BLOCKED"
    if runtime_state == "REVIEW_REQUIRED" or review_required:
        return "REVIEW_REQUIRED"
    if guard.get("manual_review_required"):
        return "ACTION_REQUIRED"
    return "INFO"
