"""Report models for Runtime v2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReportSection:
    section_id: str
    title: str
    content: str
    source_refs: tuple[str, ...]
    review_required: bool
    severity: str


@dataclass(frozen=True)
class ReportArtifact:
    report_id: str
    schema_version: str
    mode: str
    environment: str
    business_date: str
    target_session_date: str
    report_type: str
    sections: tuple[ReportSection, ...]
    source_current_paths: tuple[str, ...]
    source_history_refs: tuple[str, ...]
    review_required: bool
    blocked: bool
    halt: bool
    created_at: str
    derived: bool = True
    not_current_state: bool = True


@dataclass(frozen=True)
class ReportBuildInput:
    mode: str
    environment: str
    business_date: str
    target_session_date: str
    asset_state: Any | None = None
    pending_plan: Any | None = None
    ledger_orders: tuple[Any, ...] = ()
    ledger_executions: tuple[Any, ...] = ()
    ledger_positions: tuple[Any, ...] = ()
    ledger_cash_records: tuple[Any, ...] = ()
    broker_orders: tuple[Any, ...] = ()
    broker_executions: tuple[Any, ...] = ()
    broker_positions: tuple[Any, ...] = ()
    broker_cash: Any | None = None
    planning_result: Any | None = None
    approval_artifact: Any | None = None
    reconciliation_result: Any | None = None
    review_events: tuple[Any, ...] = ()

