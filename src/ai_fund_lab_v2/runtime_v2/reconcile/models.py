"""Models for Runtime v2 reconciliation results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReconciliationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"
    HALT = "HALT"


@dataclass(frozen=True)
class ReconciliationFinding:
    finding_id: str
    finding_type: str
    severity: ReconciliationSeverity
    message: str
    related_object_type: str
    related_object_id: str
    expected: str
    actual: str
    review_required: bool
    production_equivalent: bool
    created_at: str


@dataclass(frozen=True)
class ReconciliationResult:
    result_id: str
    schema_version: str
    environment: str
    mode: str
    business_date: str
    as_of: str
    findings: tuple[ReconciliationFinding, ...]
    review_required: bool
    blocked: bool
    halt: bool
    summary: str
    created_at: str
    evidence_only: bool = True
    not_submit_source: bool = True
    not_current_state: bool = True
    current_writer: bool = False
