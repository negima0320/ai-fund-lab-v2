"""Report builder skeleton for Runtime v2."""

from __future__ import annotations

import hashlib

from ai_fund_lab_v2.runtime_v2.report.models import (
    ReportArtifact,
    ReportBuildInput,
    ReportSection,
)


def build_runtime_report(input: ReportBuildInput) -> ReportArtifact:
    """Build a derived runtime report without using it as Current State."""

    sections = (
        _section(
            "runtime_summary",
            "Runtime Summary",
            f"mode={input.mode} environment={input.environment}",
            ("runtime_state/current_state.json",),
        ),
        _section(
            "planning_summary",
            "Planning",
            _object_summary(input.planning_result, "planning result"),
            ("order_plan/history",),
            _review(input.planning_result),
        ),
        _section(
            "approval_summary",
            "Approval",
            _object_summary(input.approval_artifact, "approval artifact"),
            ("approval_artifact/history",),
            _review(input.approval_artifact),
        ),
        _section(
            "pending_summary",
            "Pending",
            _object_summary(input.pending_plan, "pending plan"),
            ("pending_order_plan/pending_order_plan.json",),
            _review(input.pending_plan),
        ),
        _section(
            "orders_summary",
            "Orders",
            f"ledger_orders={len(input.ledger_orders)} broker_orders={len(input.broker_orders)}",
            ("persistent_ledger/orders.jsonl", "broker_orders/history"),
        ),
        _section(
            "executions_summary",
            "Executions",
            f"ledger_executions={len(input.ledger_executions)} broker_executions={len(input.broker_executions)}",
            ("persistent_ledger/executions.jsonl", "broker_executions/history"),
        ),
        _section(
            "positions_summary",
            "Positions",
            f"ledger_positions={len(input.ledger_positions)} broker_positions={len(input.broker_positions)}",
            ("persistent_ledger/positions.jsonl", "broker_positions/history"),
        ),
        _section(
            "asset_summary",
            "Asset",
            _asset_summary(input.asset_state),
            ("persistent_ledger/state.json",),
            _review(input.asset_state),
        ),
        _section(
            "reconciliation_summary",
            "Reconciliation",
            _object_summary(input.reconciliation_result, "reconciliation result"),
            ("reconciliation_result/history",),
            _review(input.reconciliation_result),
            _severity(input.reconciliation_result),
        ),
        _section(
            "review_required_summary",
            "Review Required",
            _review_events_summary(input.review_events),
            ("persistent_ledger/events.jsonl",),
            _review_events_require_review(input.review_events),
            "REVIEW_REQUIRED" if _review_events_require_review(input.review_events) else "INFO",
        ),
    )
    review_required = any(section.review_required for section in sections)
    blocked = bool(getattr(input.reconciliation_result, "blocked", False))
    halt = bool(getattr(input.reconciliation_result, "halt", False))
    return ReportArtifact(
        report_id=_report_id(input),
        schema_version="1",
        mode=input.mode,
        environment=input.environment,
        business_date=input.business_date,
        target_session_date=input.target_session_date,
        report_type="runtime",
        sections=sections,
        source_current_paths=(
            "persistent_ledger/state.json",
            "pending_order_plan/pending_order_plan.json",
            "runtime_state/current_state.json",
        ),
        source_history_refs=(
            "order_plan/history",
            "approval_artifact/history",
            "reconciliation_result/history",
        ),
        review_required=review_required,
        blocked=blocked,
        halt=halt,
        created_at=input.business_date,
    )


def _section(
    section_id: str,
    title: str,
    content: str,
    source_refs: tuple[str, ...],
    review_required: bool = False,
    severity: str = "INFO",
) -> ReportSection:
    return ReportSection(
        section_id=section_id,
        title=title,
        content=content,
        source_refs=source_refs,
        review_required=review_required,
        severity=severity,
    )


def _object_summary(value, label: str) -> str:
    if value is None:
        return f"{label}=missing"
    identifier = (
        getattr(value, "order_plan_id", None)
        or getattr(value, "pending_plan_id", None)
        or getattr(value, "approval_id", None)
        or getattr(value, "result_id", None)
        or "present"
    )
    return f"{label}={identifier}"


def _asset_summary(asset_state) -> str:
    if asset_state is None:
        return "asset_state=missing state_unknown=true"
    positions = getattr(asset_state, "positions", None)
    position_count = "unknown" if positions is None else str(len(positions))
    return (
        f"asset_state={asset_state.asset_state_id} "
        f"positions={position_count} cash={asset_state.cash} "
        f"buying_power={asset_state.buying_power} source={asset_state.source}"
    )


def _review_events_summary(events) -> str:
    if not events:
        return "review_events=0"
    labels = tuple(
        str(
            getattr(event, "event_type", None)
            or getattr(event, "event_id", None)
            or getattr(event, "message", None)
            or event
        )
        for event in events
    )
    return f"review_events={len(events)} labels={','.join(labels)}"


def _review_events_require_review(events) -> bool:
    return any(str(getattr(event, "severity", "REVIEW_REQUIRED")).upper() != "INFO" for event in events)


def _review(value) -> bool:
    return bool(getattr(value, "review_required", False))


def _severity(value) -> str:
    if bool(getattr(value, "halt", False)):
        return "HALT"
    if bool(getattr(value, "blocked", False)):
        return "BLOCKED"
    if bool(getattr(value, "review_required", False)):
        return "REVIEW_REQUIRED"
    return "INFO"


def _report_id(input: ReportBuildInput) -> str:
    raw = "|".join((input.mode, input.environment, input.business_date, input.target_session_date))
    return "report-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
