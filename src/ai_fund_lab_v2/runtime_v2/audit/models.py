"""Audit models for Runtime v2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AuditSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"
    HALT = "HALT"


@dataclass(frozen=True)
class AuditFinding:
    finding_id: str
    finding_type: str
    severity: AuditSeverity
    message: str
    related_object_type: str
    related_object_id: str
    review_required: bool
    created_at: str


@dataclass(frozen=True)
class AuditResult:
    audit_id: str
    schema_version: str
    mode: str
    environment: str
    business_date: str
    findings: tuple[AuditFinding, ...]
    review_required: bool
    blocked: bool
    halt: bool
    created_at: str
    evidence_only: bool = True
    not_submit_source: bool = True

