"""Audit Runtime skeleton aggregator."""

from __future__ import annotations

import hashlib

from ai_fund_lab_v2.runtime_v2.audit.checks import (
    audit_notification_payload,
    audit_report,
    audit_runtime_state_boundaries,
)
from ai_fund_lab_v2.runtime_v2.audit.models import (
    AuditFinding,
    AuditResult,
    AuditSeverity,
)


def run_audit(
    *,
    mode: str,
    environment: str,
    business_date: str,
    report=None,
    notification_payload=None,
    reconciliation_result=None,
    asset_state=None,
) -> AuditResult:
    findings: tuple[AuditFinding, ...] = (
        *audit_report(report),
        *audit_notification_payload(notification_payload),
        *audit_runtime_state_boundaries(
            reconciliation_result=reconciliation_result,
            asset_state=asset_state,
        ),
    )
    halt = any(finding.severity == AuditSeverity.HALT for finding in findings)
    blocked = any(finding.severity == AuditSeverity.BLOCKED for finding in findings)
    review_required = any(finding.review_required for finding in findings)
    return AuditResult(
        audit_id=_audit_id(mode, environment, business_date, findings),
        schema_version="1",
        mode=mode,
        environment=environment,
        business_date=business_date,
        findings=findings,
        review_required=review_required,
        blocked=blocked,
        halt=halt,
        created_at=business_date,
    )


def _audit_id(
    mode: str,
    environment: str,
    business_date: str,
    findings: tuple[AuditFinding, ...],
) -> str:
    raw = "|".join((mode, environment, business_date, *(finding.finding_id for finding in findings)))
    return "audit-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
