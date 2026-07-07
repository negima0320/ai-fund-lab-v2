"""Audit checks for Runtime v2 derived artifacts and boundaries."""

from __future__ import annotations

import hashlib

from ai_fund_lab_v2.runtime_v2.audit.models import AuditFinding, AuditSeverity


def audit_report(report) -> tuple[AuditFinding, ...]:
    if report is None:
        return ()
    findings: list[AuditFinding] = []
    if getattr(report, "derived", False) is not True:
        findings.append(_finding("REPORT_NOT_DERIVED", AuditSeverity.HALT, "report", getattr(report, "report_id", "")))
    if getattr(report, "not_current_state", False) is not True:
        findings.append(_finding("REPORT_MARKED_CURRENT_STATE", AuditSeverity.HALT, "report", getattr(report, "report_id", "")))
    if bool(getattr(report, "review_required", False)):
        findings.append(_finding("REPORT_REVIEW_REQUIRED", AuditSeverity.REVIEW_REQUIRED, "report", getattr(report, "report_id", "")))
    return tuple(findings)


def audit_notification_payload(payload) -> tuple[AuditFinding, ...]:
    if payload is None:
        return ()
    findings: list[AuditFinding] = []
    if getattr(payload, "derived", False) is not True:
        findings.append(_finding("NOTIFICATION_PAYLOAD_NOT_DERIVED", AuditSeverity.HALT, "notification_payload", getattr(payload, "payload_id", "")))
    if getattr(payload, "not_current_state", False) is not True:
        findings.append(_finding("NOTIFICATION_PAYLOAD_MARKED_CURRENT_STATE", AuditSeverity.HALT, "notification_payload", getattr(payload, "payload_id", "")))
    return tuple(findings)


def audit_runtime_state_boundaries(
    *,
    reconciliation_result=None,
    asset_state=None,
) -> tuple[AuditFinding, ...]:
    findings: list[AuditFinding] = []
    if asset_state is None:
        findings.append(_finding("CURRENT_ASSET_STATE_UNKNOWN", AuditSeverity.REVIEW_REQUIRED, "asset_state", "missing"))
    if reconciliation_result is not None and bool(getattr(reconciliation_result, "review_required", False)):
        findings.append(_finding("RECONCILIATION_REVIEW_REQUIRED", AuditSeverity.REVIEW_REQUIRED, "reconciliation_result", getattr(reconciliation_result, "result_id", "")))
    return tuple(findings)


def _finding(
    finding_type: str,
    severity: AuditSeverity,
    related_object_type: str,
    related_object_id: str,
) -> AuditFinding:
    raw = "|".join((finding_type, related_object_type, related_object_id))
    return AuditFinding(
        finding_id="audit-finding-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16],
        finding_type=finding_type,
        severity=severity,
        message=f"{finding_type} detected.",
        related_object_type=related_object_type,
        related_object_id=related_object_id,
        review_required=severity in {AuditSeverity.REVIEW_REQUIRED, AuditSeverity.BLOCKED, AuditSeverity.HALT},
        created_at="",
    )

