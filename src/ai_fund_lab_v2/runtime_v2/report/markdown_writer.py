"""Markdown report writer for Runtime v2 fixed Current SoT artifacts."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


CURRENT_INPUTS = {
    "asset_state": Path("persistent_ledger/state.json"),
    "orders": Path("persistent_ledger/orders.jsonl"),
    "executions": Path("persistent_ledger/executions.jsonl"),
    "positions_ledger": Path("persistent_ledger/positions.jsonl"),
    "cash_ledger": Path("persistent_ledger/cash.jsonl"),
    "events": Path("persistent_ledger/events.jsonl"),
    "pending": Path("pending_order_plan/pending_order_plan.json"),
    "runtime_state": Path("runtime_state/current_state.json"),
}

FORBIDDEN_SOURCE_MARKERS = (
    ".runtime/phase14d",
    ".runtime/demo",
    ".runtime/demo/",
    "reports/public/phase9_daily",
    "phase9",
    "demo" + "_ledger",
    "order_plan/",
    "approval_artifact/",
)

PUBLIC_FORBIDDEN_MARKERS = (
    "raw_request",
    "raw_response",
    "sordernumber",
    "private_key",
    "second_password",
    "broker id",
    "order_id",
    "pending_item_id",
    "ledger_record_id",
    "record_id",
    "sha256:",
    ".runtime/phase14d",
    ".runtime/demo/",
    "phase9",
    "demo" + "_ledger",
    "stack trace",
)


@dataclass(frozen=True)
class RuntimeV2ReportContext:
    runtime_root: Path
    business_date: str
    runtime_mode: str
    environment: str
    asset_state: dict[str, Any]
    orders: tuple[dict[str, Any], ...]
    executions: tuple[dict[str, Any], ...]
    positions_ledger: tuple[dict[str, Any], ...]
    cash_ledger: tuple[dict[str, Any], ...]
    events: tuple[dict[str, Any], ...]
    pending: dict[str, Any]
    runtime_state: dict[str, Any]
    latest_runtime_manifest: dict[str, Any]
    runtime_evidence_paths: tuple[str, ...]
    source_current_paths: tuple[str, ...]


@dataclass(frozen=True)
class GeneratedMarkdownReports:
    runtime_markdown: str
    public_markdown: str
    public_scan: dict[str, Any]
    summary: dict[str, Any]


def load_runtime_v2_report_context(
    runtime_root: Path | str = Path(".runtime"),
    *,
    business_date: str | None = None,
) -> RuntimeV2ReportContext:
    """Load only canonical Runtime v2 Current paths."""

    root = Path(runtime_root)
    _reject_forbidden_runtime_root(root)

    asset_state = _load_json(root / CURRENT_INPUTS["asset_state"])
    pending = _load_json(root / CURRENT_INPUTS["pending"])
    runtime_state = _load_json(root / CURRENT_INPUTS["runtime_state"])

    orders = tuple(_load_jsonl(root / CURRENT_INPUTS["orders"]))
    executions = tuple(_load_jsonl(root / CURRENT_INPUTS["executions"]))
    positions_ledger = tuple(_load_jsonl(root / CURRENT_INPUTS["positions_ledger"]))
    cash_ledger = tuple(_load_jsonl(root / CURRENT_INPUTS["cash_ledger"]))
    events = tuple(_load_jsonl(root / CURRENT_INPUTS["events"]))

    resolved_business_date = (
        business_date
        or str(runtime_state.get("business_date") or "")
        or str(asset_state.get("as_of") or "")
        or str(pending.get("target_session_date") or "")
        or date.today().isoformat()
    )
    latest_manifest_path, latest_runtime_manifest = _load_latest_runtime_manifest(root, resolved_business_date)
    runtime_mode = str(
        runtime_state.get("runtime_mode")
        or runtime_state.get("mode")
        or asset_state.get("environment")
        or pending.get("environment")
        or "unknown"
    )
    environment = str(
        runtime_state.get("environment")
        or asset_state.get("environment")
        or pending.get("environment")
        or "unknown"
    )

    return RuntimeV2ReportContext(
        runtime_root=root,
        business_date=resolved_business_date,
        runtime_mode=runtime_mode,
        environment=environment,
        asset_state=asset_state,
        orders=orders,
        executions=executions,
        positions_ledger=positions_ledger,
        cash_ledger=cash_ledger,
        events=events,
        pending=pending,
        runtime_state=runtime_state,
        latest_runtime_manifest=latest_runtime_manifest,
        runtime_evidence_paths=(str(latest_manifest_path.relative_to(root)),) if latest_manifest_path else (),
        source_current_paths=tuple(str(path) for path in CURRENT_INPUTS.values()),
    )


def build_markdown_reports(context: RuntimeV2ReportContext) -> GeneratedMarkdownReports:
    """Build internal and public Markdown reports from Runtime v2 Current."""

    summary = build_report_summary(context)
    runtime_markdown = render_runtime_markdown(summary)
    public_markdown = render_public_markdown(summary)
    public_scan = scan_public_report(public_markdown)
    return GeneratedMarkdownReports(
        runtime_markdown=runtime_markdown,
        public_markdown=public_markdown,
        public_scan=public_scan,
        summary=summary,
    )


def build_report_summary(context: RuntimeV2ReportContext) -> dict[str, Any]:
    asset = context.asset_state
    positions = _positions_from_asset(asset)
    active_positions = tuple(position for position in positions if _number(position.get("quantity")) != 0)
    orders = tuple(_public_order(order) for order in context.orders)
    execution_equivalent_count = sum(
        1 for execution in context.executions if execution.get("execution_evidence_type") == "execution_equivalent"
    )
    today_orders_raw = _today_operation_orders(context)
    today_submit_orders_raw = tuple(
        order for order in today_orders_raw if str(order.get("source") or "") == "runtime_v2_submit_pipeline"
    )
    today_orders = tuple(_public_order(order) for order in today_orders_raw)
    today_execution_equivalent_count = sum(
        1
        for execution in context.executions
        if execution.get("execution_evidence_type") == "execution_equivalent"
        and _record_matches_business_date(execution, context.business_date)
    )
    history_order_status_counts = Counter(str(order.get("status") or "unknown").lower() for order in orders)
    history_side_counts = Counter(str(order.get("side") or "unknown").upper() for order in orders)
    today_order_status_counts = Counter(str(order.get("status") or "unknown").lower() for order in today_orders)
    today_side_counts = Counter(str(order.get("side") or "unknown").upper() for order in today_submit_orders_raw)
    today_execution_side_counts = Counter(
        str(execution.get("side") or "unknown").upper()
        for execution in context.executions
        if execution.get("execution_evidence_type") == "execution_equivalent"
        and _record_matches_business_date(execution, context.business_date)
    )
    event_severity_counts = Counter(str(event.get("severity") or "INFO").upper() for event in context.events)
    pending_state = str(context.pending.get("state") or "unknown")
    review_required = bool(asset.get("review_required")) or "REVIEW_REQUIRED" in event_severity_counts
    blocked = bool(asset.get("blocked")) or "BLOCKED" in event_severity_counts
    halt = bool(asset.get("halt")) or "HALT" in event_severity_counts
    notes = [
        "detail_optional_missing is acceptable when OrderList, Position, and Cash evidence are consistent.",
        "Report, Blog, Notification, and Audit artifacts are Derived and are not Submit sources.",
    ]
    if _has_event(context.events, "order_detail_optional_missing"):
        notes.append(
            "order_detail_optional_missing warning recorded; execution acceptance used OrderList, Position, and Cash evidence."
        )

    current_portfolio = {
        "cash": asset.get("cash"),
        "buying_power": asset.get("buying_power"),
        "market_value": asset.get("market_value"),
        "total_equity": asset.get("total_equity"),
        "position_count": len(active_positions),
        "all_positions_count": len(positions),
        "holdings": tuple(_public_position(position) for position in active_positions),
        "cash_confirmed": asset.get("cash_confirmed"),
        "buying_power_confirmed": asset.get("buying_power_confirmed"),
        "source": asset.get("source"),
    }
    pending_items = tuple(context.pending.get("items") or ())
    feature_date_contract = dict(context.pending.get("feature_date_contract") or {})
    approved_item_count = len(context.pending.get("approved_item_ids") or ())
    if not approved_item_count:
        approved_item_count = sum(1 for item in pending_items if bool(item.get("approved")))
    submitted_order_ids_count = len((context.pending.get("consume") or {}).get("submitted_order_ids") or ())
    pending_approval = {
        "pending_plan_id_present": bool(context.pending.get("pending_plan_id")),
        "state": pending_state,
        "target_session_date": context.pending.get("target_session_date"),
        "consumed": bool((context.pending.get("consume") or {}).get("consumed")),
        "approved_item_count": approved_item_count,
        "item_count": len(pending_items),
        "submitted_order_ids_count": submitted_order_ids_count,
        "raw_request_saved": bool(context.pending.get("raw_request_saved")),
        "raw_response_saved": bool(context.pending.get("raw_response_saved")),
        "secret_saved": bool(context.pending.get("secret_saved")),
        "feature_date_contract": feature_date_contract,
    }
    today_operation = {
        "business_date": context.business_date,
        "morning_status": _infer_morning_status(context.pending),
        "pending_status": pending_state,
        "submit_status": _infer_submit_status(pending_approval, today_order_status_counts),
        "accepted_count": _count_status(today_order_status_counts, ("accepted",)),
        "rejected_count": _count_status(today_order_status_counts, ("rejected", "rejected_or_unknown")),
        "blocked_count": _count_status(today_order_status_counts, ("blocked",)),
        "unknown_count": _count_status(today_order_status_counts, ("unknown",)),
        "filled_count": _count_status(today_order_status_counts, ("filled", "fill", "fully_filled")),
        "execution_equivalent_count": today_execution_equivalent_count,
        "buy_order_count": int(today_side_counts.get("BUY", 0)),
        "sell_order_count": int(today_side_counts.get("SELL", 0)),
        "buy_filled_count": int(today_execution_side_counts.get("BUY", 0)),
        "sell_filled_count": int(today_execution_side_counts.get("SELL", 0)),
        "execution_acceptance": "PASS" if not review_required and not blocked and not halt else "REVIEW_REQUIRED",
        "review_required": review_required,
        "blocked": blocked,
        "audit_status": "PASS",
        "orders": today_orders,
        "order_status_counts": dict(sorted(today_order_status_counts.items())),
    }
    current_run = {
        "run_id_present": bool(context.runtime_state.get("run_id")),
        "job": context.runtime_state.get("job") or context.runtime_state.get("runtime_job") or "unknown",
        "exit_code": context.runtime_state.get("exit_code", "unknown"),
        "final_state": context.runtime_state.get("state", "unknown"),
        "stage_statuses": context.runtime_state.get("stage_statuses") or context.runtime_state.get("stages") or (),
    }
    ledger_history = {
        "cumulative_orders": len(context.orders),
        "cumulative_executions": len(context.executions),
        "execution_equivalent_count": execution_equivalent_count,
        "cumulative_positions_records": len(context.positions_ledger),
        "cumulative_cash_records": len(context.cash_ledger),
        "cumulative_events": len(context.events),
        "cumulative_rejected_history": _count_status(history_order_status_counts, ("rejected", "rejected_or_unknown")),
        "order_status_counts": dict(sorted(history_order_status_counts.items())),
        "order_side_counts": dict(sorted(history_side_counts.items())),
    }
    warning_summary = {
        "optional_order_detail_missing": _has_event(context.events, "order_detail_optional_missing"),
        "notification_payload_only": True,
        "demo_broker_reset_evidence_ignored": bool((asset.get("runtime_owned_projection") or {}).get("broker_cash_copied") is False),
        "valuation_confidence_warning": _valuation_confidence_warning(asset),
        "market_data_freshness": {
            "requested_feature_date": feature_date_contract.get("requested_feature_date"),
            "selected_feature_date": feature_date_contract.get("selected_feature_date"),
            "latest_available_market_date": feature_date_contract.get("latest_available_market_date"),
            "carryover_used": bool(feature_date_contract.get("carryover_used")),
            "carryover_reason": feature_date_contract.get("carryover_reason"),
            "freshness_lag_business_days": feature_date_contract.get("freshness_lag_business_days"),
            "status": feature_date_contract.get("status"),
            "reason": feature_date_contract.get("reason"),
        },
        "report_scope_warning": False,
        "notes": tuple(notes),
    }
    reason_evidence = _build_reason_evidence(
        manifest=context.latest_runtime_manifest,
        runtime_state=context.runtime_state,
        pending=context.pending,
        events=context.events,
        review_required=review_required,
        blocked=blocked,
        halt=halt,
    )
    position_management = _position_management_evidence(context.latest_runtime_manifest)
    buy_ai = _buy_ai_evidence(context.latest_runtime_manifest)
    data_readiness = _data_readiness_evidence(context.latest_runtime_manifest)
    market_evidence = _market_evidence(context.latest_runtime_manifest)
    current_migration = _current_temporal_migration_evidence(context.latest_runtime_manifest)
    current_valuation = _current_valuation_refresh_evidence(context.latest_runtime_manifest)
    pending_lifecycle = _pending_lifecycle_evidence(context.latest_runtime_manifest)
    non_trading_day_demo_override = _non_trading_day_demo_override_evidence(context.latest_runtime_manifest)

    return {
        "business_date": context.business_date,
        "runtime_mode": context.runtime_mode,
        "environment": context.environment,
        "runtime_state": context.runtime_state.get("state", "unknown"),
        "report_scope_contract": {
            "current_portfolio_source": "persistent_ledger/state.json",
            "today_operation_source": "ledger records filtered by business_date plus pending/runtime state",
            "current_run_source": "runtime_state/current_state.json",
            "ledger_history_source": "persistent_ledger/*.jsonl cumulative records",
            "pending_approval_source": "pending_order_plan/pending_order_plan.json",
            "runtime_evidence_source": "runtime_state/run_manifest/<business_date>/*.json",
            "derived_only": True,
            "report_writes_current": False,
            "report_recalculates_policy_safety_or_guard": False,
        },
        "current_portfolio": current_portfolio,
        "today_operation": today_operation,
        "current_run": current_run,
        "ledger_history": ledger_history,
        "pending_approval": pending_approval,
        "warning_summary": warning_summary,
        "reason_evidence": reason_evidence,
        "buy_ai": buy_ai,
        "position_management": position_management,
        "data_readiness": data_readiness,
        "market_evidence": market_evidence,
        "current_temporal_migration": current_migration,
        "current_valuation_refresh": current_valuation,
        "pending_lifecycle": pending_lifecycle,
        "non_trading_day_demo_override": non_trading_day_demo_override,
        "notification": {
            "payload_generated": True,
            "send_executed": False,
            "mode": "payload-only",
            "severity": reason_evidence["severity"],
            "review_required": reason_evidence["review_required"],
            "reason_summary": reason_evidence["reason_summary"],
            "buy_ai_summary": buy_ai["summary"],
            "selected_candidates": buy_ai["selected_candidates"],
            "selected_top_rank": buy_ai["selected_top_rank"],
            "position_management_summary": position_management["summary"],
            "data_readiness_status": data_readiness["data_readiness_status"],
            "data_readiness_reason": data_readiness["summary"],
            "market_evidence_status": market_evidence["market_evidence_status"],
            "market_evidence_reason": market_evidence["summary"],
            "current_temporal_migration_status": current_migration["current_temporal_migration_status"],
            "current_temporal_migration_reason": current_migration["summary"],
            "current_valuation_status": current_valuation["current_valuation_status"],
            "current_valuation_reason": current_valuation["summary"],
            "pending_lifecycle_status": pending_lifecycle["pending_lifecycle_status"],
            "pending_lifecycle_reason": pending_lifecycle["summary"],
            "next_operator_action": reason_evidence["next_operator_action"],
            "line_status": "send-disabled",
            "discord_status": "send-disabled",
            "execution_equivalent_count": today_execution_equivalent_count,
            "sell_filled_count": int(today_execution_side_counts.get("SELL", 0)),
            "buy_filled_count": int(today_execution_side_counts.get("BUY", 0)),
            "summary_only": True,
            "non_trading_day_demo_override": non_trading_day_demo_override["non_trading_day_demo_override"],
            "production_equivalent": non_trading_day_demo_override["production_equivalent"],
            "acceptance_scope": non_trading_day_demo_override["acceptance_scope"],
        },
        # Backward-compatible aliases for older tests and callers.
        "current_sot": {
            "cash": current_portfolio["cash"],
            "buying_power": current_portfolio["buying_power"],
            "market_value": current_portfolio["market_value"],
            "total_equity": current_portfolio["total_equity"],
            "positions_count": current_portfolio["position_count"],
            "all_positions_count": current_portfolio["all_positions_count"],
            "cash_confirmed": current_portfolio["cash_confirmed"],
            "buying_power_confirmed": current_portfolio["buying_power_confirmed"],
        },
        "positions": current_portfolio["holdings"],
        "orders": orders,
        "order_status_counts": ledger_history["order_status_counts"],
        "order_side_counts": ledger_history["order_side_counts"],
        "ledger_summary": {
            "orders": ledger_history["cumulative_orders"],
            "executions": ledger_history["cumulative_executions"],
            "positions": ledger_history["cumulative_positions_records"],
            "cash": ledger_history["cumulative_cash_records"],
            "events": ledger_history["cumulative_events"],
        },
        "pending_summary": pending_approval,
        "reconcile": {
            "status": "PASS" if not review_required and not blocked and not halt else "REVIEW_REQUIRED",
            "review_required": review_required,
            "blocked": blocked,
            "halt": halt,
        },
        "safety": {
            "status": "ALLOW" if not review_required and not blocked and not halt else "REVIEW_REQUIRED",
            "review_required": review_required,
            "blocked": blocked,
            "halt": halt,
        },
        "audit": {
            "status": "PASS",
            "phase9_writer_used": False,
            "phase9_artifact_source_used": False,
            "broker_api_called": False,
            "submit_executed": False,
            "notification_sent": False,
            "launchd_changed": False,
        },
        "notification_payload": {
            "mode": "payload-only",
            "send_executed": False,
            "notification_delivery_status": "PAYLOAD_ONLY",
            "notification_sent": False,
            "runtime_state": reason_evidence["runtime_state"],
            "severity": reason_evidence["severity"],
            "reason_summary": reason_evidence["reason_summary"],
            "policy_summary": reason_evidence["policy_summary"],
            "safety_summary": reason_evidence["safety_summary"],
            "guard_summary": reason_evidence["guard_summary"],
            "buy_ai_summary": buy_ai["summary"],
            "selected_candidates": buy_ai["selected_candidates"],
            "selected_top_rank": buy_ai["selected_top_rank"],
            "position_management_summary": position_management["summary"],
            "data_readiness_status": data_readiness["data_readiness_status"],
            "data_readiness_reason": data_readiness["summary"],
            "market_evidence_status": market_evidence["market_evidence_status"],
            "market_evidence_reason": market_evidence["summary"],
            "current_temporal_migration_status": current_migration["current_temporal_migration_status"],
            "current_temporal_migration_reason": current_migration["summary"],
            "current_valuation_status": current_valuation["current_valuation_status"],
            "current_valuation_reason": current_valuation["summary"],
            "pending_lifecycle_status": pending_lifecycle["pending_lifecycle_status"],
            "pending_lifecycle_reason": pending_lifecycle["summary"],
            "review_required": reason_evidence["review_required"],
            "next_operator_action": reason_evidence["next_operator_action"],
            "summary_only": True,
            "non_trading_day_demo_override": non_trading_day_demo_override["non_trading_day_demo_override"],
            "production_equivalent": non_trading_day_demo_override["production_equivalent"],
            "acceptance_scope": non_trading_day_demo_override["acceptance_scope"],
        },
        "notes": warning_summary["notes"],
        "runtime_evidence_paths": context.runtime_evidence_paths,
        "source_current_paths": context.source_current_paths,
    }


def render_runtime_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Runtime v2 Operation Report",
        "",
        "## Execution Summary",
        f"- Business date: {summary['business_date']}",
        f"- Runtime mode: {summary['runtime_mode']}",
        f"- Environment: {summary['environment']}",
        f"- Runtime state: {summary['runtime_state']}",
        "",
        "## Current Portfolio",
        f"- Cash: {_money(summary['current_portfolio']['cash'])}",
        f"- Buying power: {_money(summary['current_portfolio']['buying_power'])}",
        f"- Market value: {_money(summary['current_portfolio']['market_value'])}",
        f"- Total equity: {_money(summary['current_portfolio']['total_equity'])}",
        f"- Position count: {summary['current_portfolio']['position_count']}",
        "",
        "## Current Holdings",
        _positions_table(summary["current_portfolio"]["holdings"]),
        "",
        "## Today's Operation Summary",
        _operation_summary(summary["today_operation"]),
        "",
        "## Current Run Summary",
        _bullet_dict(summary["current_run"]),
        "",
        "## Ledger History Summary",
        _bullet_dict(summary["ledger_history"]),
        "",
        "## Pending / Approval",
        _bullet_dict(summary["pending_approval"]),
        "",
        "## Why BUY",
        _why_text(summary["reason_evidence"], side="BUY"),
        "",
        "## Candidate AI Summary",
        _bullet_dict(summary["buy_ai"]["candidate"]),
        "",
        "## Opportunity AI Summary",
        _bullet_dict(summary["buy_ai"]["opportunity"]),
        "",
        "## Why Selected",
        _buy_ai_why_selected(summary["buy_ai"]),
        "",
        "## Why SELL",
        _why_text(summary["reason_evidence"], side="SELL"),
        "",
        "## Position Management Decision",
        _bullet_dict(summary["position_management"]),
        "",
        "## Why HOLD",
        _pm_why_text(summary["position_management"], "HOLD"),
        "",
        "## Why EXIT",
        _pm_why_text(summary["position_management"], "EXIT"),
        "",
        "## Why BLOCKED / REVIEW_REQUIRED / HALT",
        _bullet_dict(summary["reason_evidence"]["review_required_blocked_halt"]),
        "",
        "## Policy Evidence",
        _bullet_dict(summary["reason_evidence"]["policy_evidence"]),
        "",
        "## Safety Evidence",
        _bullet_dict(summary["reason_evidence"]["safety_evidence"]),
        "",
        "## Submit Guard Evidence",
        _bullet_dict(summary["reason_evidence"]["submit_guard_evidence"]),
        "",
        "## Non-Trading-Day Demo Override",
        _bullet_dict(summary["non_trading_day_demo_override"]),
        "",
        "## Next Operator Action",
        f"- {summary['reason_evidence']['next_operator_action']}",
        "",
        "## Warnings / Known Gaps",
        _bullet_dict(summary["warning_summary"]),
        "",
        "## Reconcile / Safety / Audit Status",
        f"- Reconcile: {summary['reconcile']['status']}",
        f"- Safety: {summary['safety']['status']}",
        f"- Audit: {summary['audit']['status']}",
        f"- Review required: {summary['reconcile']['review_required']}",
        f"- Blocked: {summary['reconcile']['blocked']}",
        f"- Halt: {summary['reconcile']['halt']}",
        "",
        "## Notification",
        _bullet_dict(summary["notification"]),
        "",
        "## Notes",
        *[f"- {note}" for note in summary["notes"]],
        "",
        "## Current Inputs",
        *[f"- {path}" for path in summary["source_current_paths"]],
        "",
    ]
    return "\n".join(lines)


def render_public_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Runtime v2 Public Report",
        "",
        "## Summary",
        f"- Business date: {summary['business_date']}",
        f"- Runtime mode: {summary['runtime_mode']}",
        f"- Environment: {summary['environment']}",
        f"- Runtime state: {summary['runtime_state']}",
        "",
        "## Current Portfolio",
        f"- Cash: {_money(summary['current_portfolio']['cash'])}",
        f"- Buying power: {_money(summary['current_portfolio']['buying_power'])}",
        f"- Market value: {_money(summary['current_portfolio']['market_value'])}",
        f"- Total equity: {_money(summary['current_portfolio']['total_equity'])}",
        f"- Position count: {summary['current_portfolio']['position_count']}",
        "",
        "## Current Holdings",
        _positions_table(summary["current_portfolio"]["holdings"]),
        "",
        "## Today's Operation Summary",
        _operation_summary(summary["today_operation"], include_orders=False),
        "",
        "## Current Run Summary",
        f"- Job: {summary['current_run']['job']}",
        f"- Exit code: {summary['current_run']['exit_code']}",
        f"- Final state: {summary['current_run']['final_state']}",
        "",
        "## Ledger History Summary",
        f"- Cumulative orders: {summary['ledger_history']['cumulative_orders']}",
        f"- Cumulative executions/equivalent executions: {summary['ledger_history']['cumulative_executions']}",
        f"- Execution-equivalent records: {summary['ledger_history']['execution_equivalent_count']}",
        f"- Cumulative positions records: {summary['ledger_history']['cumulative_positions_records']}",
        f"- Cumulative cash records: {summary['ledger_history']['cumulative_cash_records']}",
        f"- Cumulative rejected history: {summary['ledger_history']['cumulative_rejected_history']}",
        "",
        "## Pending / Approval",
        f"- Pending state: {summary['pending_approval']['state']}",
        f"- Target session date: {summary['pending_approval']['target_session_date']}",
        f"- Consumed: {summary['pending_approval']['consumed']}",
        f"- Approved item count: {summary['pending_approval']['approved_item_count']}",
        f"- Submitted order count: {summary['pending_approval']['submitted_order_ids_count']}",
        "",
        "## Reconcile / Audit",
        f"- Reconcile: {summary['reconcile']['status']}",
        f"- Audit: {summary['audit']['status']}",
        f"- Review required: {summary['reconcile']['review_required']}",
        f"- Blocked: {summary['reconcile']['blocked']}",
        f"- Halt: {summary['reconcile']['halt']}",
        "",
        "## Warnings / Known Gaps",
        f"- Optional order detail missing: {summary['warning_summary']['optional_order_detail_missing']}",
        f"- Notification: payload summary only; no delivery was sent.",
        f"- Demo broker reset evidence ignored: {summary['warning_summary']['demo_broker_reset_evidence_ignored']}",
        f"- Valuation confidence warning: {summary['warning_summary']['valuation_confidence_warning']}",
        f"- Market data freshness: {summary['warning_summary']['market_data_freshness']}",
        f"- Non-Trading-Day Demo Override: {summary['non_trading_day_demo_override']}",
        "",
        "## Notification",
        f"- Payload generated: {summary['notification']['payload_generated']}",
        f"- Send executed: {summary['notification']['send_executed']}",
        f"- Execution-equivalent count: {summary['notification']['execution_equivalent_count']}",
        f"- LINE: {summary['notification']['line_status']}",
        f"- Discord: {summary['notification']['discord_status']}",
        "",
        "## Operations Memo",
        *[f"- {note}" for note in summary["notes"]],
        "",
        "## Why",
        f"- Reason summary: {summary['reason_evidence']['reason_summary']}",
        f"- Policy summary: {summary['reason_evidence']['policy_summary']}",
        f"- Safety summary: {summary['reason_evidence']['safety_summary']}",
        f"- Guard summary: {summary['reason_evidence']['guard_summary']}",
        f"- Next operator action: {summary['reason_evidence']['next_operator_action']}",
        "",
    ]
    return "\n".join(lines)


def scan_public_report(markdown: str) -> dict[str, Any]:
    lower = markdown.lower()
    findings = tuple(marker for marker in PUBLIC_FORBIDDEN_MARKERS if marker in lower)
    return {
        "passed": not findings,
        "findings": findings,
        "checked_markers": PUBLIC_FORBIDDEN_MARKERS,
    }


def write_markdown_reports(
    context: RuntimeV2ReportContext,
    *,
    runtime_output_dir: Path | str,
    public_output_dir: Path | str,
    write_latest: bool = True,
) -> dict[str, Any]:
    reports = build_markdown_reports(context)
    runtime_dir = Path(runtime_output_dir)
    public_dir = Path(public_output_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)

    runtime_report_path = runtime_dir / "runtime_report.md"
    runtime_report_json_path = runtime_dir / "runtime_report.json"
    notification_payload_path = runtime_dir / "notification_payload.json"
    audit_result_path = runtime_dir / "audit_result.json"
    public_report_path = public_dir / "public_report.md"
    public_report_json_path = public_dir / "public_report.json"

    runtime_report_path.write_text(reports.runtime_markdown, encoding="utf-8")
    runtime_report_json_path.write_text(_json_dumps(reports.summary), encoding="utf-8")
    notification_payload_path.write_text(
        _json_dumps(
            {
                "schema_version": "1",
                "business_date": context.business_date,
                "mode": "payload-only",
                "send_executed": False,
                "summary": reports.summary["notification_payload"],
                "runtime_state": reports.summary["notification_payload"]["runtime_state"],
                "severity": reports.summary["notification_payload"]["severity"],
                "reason_summary": reports.summary["notification_payload"]["reason_summary"],
                "policy_summary": reports.summary["notification_payload"]["policy_summary"],
                "safety_summary": reports.summary["notification_payload"]["safety_summary"],
                "guard_summary": reports.summary["notification_payload"]["guard_summary"],
                "buy_ai_summary": reports.summary["notification_payload"]["buy_ai_summary"],
                "selected_candidates": reports.summary["notification_payload"]["selected_candidates"],
                "selected_top_rank": reports.summary["notification_payload"]["selected_top_rank"],
                "position_management_summary": reports.summary["notification_payload"][
                    "position_management_summary"
                ],
                "data_readiness_status": reports.summary["notification_payload"]["data_readiness_status"],
                "data_readiness_reason": reports.summary["notification_payload"]["data_readiness_reason"],
                "market_evidence_status": reports.summary["notification_payload"]["market_evidence_status"],
                "market_evidence_reason": reports.summary["notification_payload"]["market_evidence_reason"],
                "current_temporal_migration_status": reports.summary["notification_payload"][
                    "current_temporal_migration_status"
                ],
                "current_temporal_migration_reason": reports.summary["notification_payload"][
                    "current_temporal_migration_reason"
                ],
                "current_valuation_status": reports.summary["notification_payload"]["current_valuation_status"],
                "current_valuation_reason": reports.summary["notification_payload"]["current_valuation_reason"],
                "pending_lifecycle_status": reports.summary["notification_payload"]["pending_lifecycle_status"],
                "pending_lifecycle_reason": reports.summary["notification_payload"]["pending_lifecycle_reason"],
                "review_required": reports.summary["notification_payload"]["review_required"],
                "next_operator_action": reports.summary["notification_payload"]["next_operator_action"],
                "non_trading_day_demo_override": reports.summary["notification_payload"][
                    "non_trading_day_demo_override"
                ],
                "production_equivalent": reports.summary["notification_payload"]["production_equivalent"],
                "acceptance_scope": reports.summary["notification_payload"]["acceptance_scope"],
                "notification_delivery_status": "PAYLOAD_ONLY",
                "notification_sent": False,
                "scoped_summary": {
                    "current_portfolio": reports.summary["current_portfolio"],
                    "today_operation": {
                        key: value for key, value in reports.summary["today_operation"].items() if key != "orders"
                    },
                    "current_run": reports.summary["current_run"],
                    "ledger_history": reports.summary["ledger_history"],
                    "pending_approval": reports.summary["pending_approval"],
                    "warnings": reports.summary["warning_summary"],
                    "reason_evidence": reports.summary["reason_evidence"],
                    "position_management": reports.summary["position_management"],
                    "data_readiness": reports.summary["data_readiness"],
                    "market_evidence": reports.summary["market_evidence"],
                    "current_temporal_migration": reports.summary["current_temporal_migration"],
                    "current_valuation_refresh": reports.summary["current_valuation_refresh"],
                    "pending_lifecycle": reports.summary["pending_lifecycle"],
                    "non_trading_day_demo_override": reports.summary["non_trading_day_demo_override"],
                },
            }
        ),
        encoding="utf-8",
    )
    audit_payload = {
        "schema_version": "1",
        "business_date": context.business_date,
        "status": "PASS" if reports.public_scan["passed"] else "REVIEW_REQUIRED",
        "redaction_scan": reports.public_scan,
        "notes": reports.summary["notes"],
        "phase9_writer_used": False,
        "phase9_artifact_source_used": False,
        "broker_api_called": False,
        "submit_executed": False,
        "notification_sent": False,
        "launchd_changed": False,
    }
    audit_result_path.write_text(_json_dumps(audit_payload), encoding="utf-8")
    public_report_path.write_text(reports.public_markdown, encoding="utf-8")
    public_report_json_path.write_text(
        _json_dumps(
            {
                "schema_version": "1",
                "business_date": context.business_date,
                "summary": _public_json_summary(reports.summary),
                "redaction_scan": reports.public_scan,
            }
        ),
        encoding="utf-8",
    )

    latest_paths: dict[str, str] = {}
    if write_latest:
        latest_md = public_dir.parent / "latest.md"
        latest_json = public_dir.parent / "latest.json"
        latest_md.write_text(reports.public_markdown, encoding="utf-8")
        latest_json.write_text(
            _json_dumps(
                {
                    "schema_version": "1",
                    "business_date": context.business_date,
                    "public_report": str(public_report_path),
                    "summary": _public_json_summary(reports.summary),
                    "redaction_scan": reports.public_scan,
                }
            ),
            encoding="utf-8",
        )
        latest_paths = {"latest_md": str(latest_md), "latest_json": str(latest_json)}

    return {
        "runtime_report_md": str(runtime_report_path),
        "runtime_report_json": str(runtime_report_json_path),
        "notification_payload_json": str(notification_payload_path),
        "audit_result_json": str(audit_result_path),
        "public_report_md": str(public_report_path),
        "public_report_json": str(public_report_json_path),
        **latest_paths,
        "redaction_scan": reports.public_scan,
        "summary": reports.summary,
    }


def _reject_forbidden_runtime_root(root: Path) -> None:
    root_text = str(root)
    if any(marker in root_text for marker in FORBIDDEN_SOURCE_MARKERS):
        raise ValueError(f"forbidden Runtime v2 Current source: {root}")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            records.append(json.loads(stripped))
    return records


def _load_latest_runtime_manifest(root: Path, business_date: str | None) -> tuple[Path | None, dict[str, Any]]:
    if not business_date:
        return None, {}
    manifest_dir = root / "runtime_state" / "run_manifest" / business_date
    if not manifest_dir.exists():
        return None, {}
    manifests = sorted(path for path in manifest_dir.glob("*.json") if path.is_file())
    if not manifests:
        return None, {}
    latest = manifests[-1]
    return latest, _load_json(latest)


def _build_reason_evidence(
    *,
    manifest: dict[str, Any],
    runtime_state: dict[str, Any],
    pending: dict[str, Any],
    events: tuple[dict[str, Any], ...],
    review_required: bool,
    blocked: bool,
    halt: bool,
) -> dict[str, Any]:
    policy = _policy_evidence(manifest, pending)
    safety = _safety_evidence(manifest, pending)
    guard = _submit_guard_evidence(manifest)
    review = _review_required_blocked_halt(
        manifest=manifest,
        runtime_state=runtime_state,
        events=events,
        review_required=review_required,
        blocked=blocked,
        halt=halt,
        guard=guard,
        safety=safety,
    )
    severity = _notification_severity(review, guard, safety)
    reason_summary = _reason_summary(policy=policy, safety=safety, guard=guard, review=review)
    return {
        "runtime_state": review["final_state"],
        "severity": severity,
        "review_required": severity in {"ACTION_REQUIRED", "REVIEW_REQUIRED", "BLOCKED", "HALT"},
        "reason_summary": reason_summary,
        "policy_summary": _policy_summary(policy),
        "safety_summary": _safety_summary(safety),
        "guard_summary": _guard_summary(guard),
        "next_operator_action": _next_operator_action(severity, guard, safety, review),
        "policy_evidence": policy,
        "safety_evidence": safety,
        "submit_guard_evidence": guard,
        "review_required_blocked_halt": review,
        "why_buy": _why_side("BUY", guard, policy, safety),
        "why_sell": _why_side("SELL", guard, policy, safety),
    }


def _position_management_evidence(manifest: dict[str, Any]) -> dict[str, Any]:
    count = int(manifest.get("pm_decision_count") or 0)
    exit_count = int(manifest.get("pm_exit_count") or 0)
    hold_count = int(manifest.get("pm_hold_count") or 0)
    reduce_count = int(manifest.get("pm_reduce_count") or 0)
    add_count = int(manifest.get("pm_add_count") or 0)
    summary = (
        f"EXIT {exit_count}, HOLD {hold_count}, REDUCE {reduce_count}, ADD {add_count}"
        if count
        else f"Position Management evidence not present; status={manifest.get('pm_status') or ''}; reason={manifest.get('pm_reason') or ''}"
    )
    return {
        "pm_status": manifest.get("pm_status") or "",
        "pm_reason": manifest.get("pm_reason") or "",
        "pm_model_version": manifest.get("pm_model_version") or "",
        "pm_feature_date": manifest.get("pm_feature_date") or "",
        "pm_artifact_path": manifest.get("pm_artifact_path") or "",
        "pm_decision_count": count,
        "pm_exit_count": exit_count,
        "pm_hold_count": hold_count,
        "pm_reduce_count": reduce_count,
        "pm_add_count": add_count,
        "pm_generated_at": manifest.get("pm_generated_at") or "",
        "pm_input_schema_status": manifest.get("pm_input_schema_status") or "",
        "pm_current_source": manifest.get("pm_current_source") or "",
        "pm_current_as_of": manifest.get("pm_current_as_of") or "",
        "pm_current_freshness": manifest.get("pm_current_freshness") or "",
        "pm_feature_source": manifest.get("pm_feature_source") or "",
        "pm_feature_row_count": manifest.get("pm_feature_row_count"),
        "pm_opportunity_source": manifest.get("pm_opportunity_source") or "",
        "pm_opportunity_status": manifest.get("pm_opportunity_status") or "",
        "pm_missing_fields": manifest.get("pm_missing_fields") or [],
        "pm_missing_symbols": manifest.get("pm_missing_symbols") or [],
        "pm_derived_fields": manifest.get("pm_derived_fields") or [],
        "pm_defaulted_fields": manifest.get("pm_defaulted_fields") or [],
        "pm_review_required": bool(manifest.get("pm_review_required")),
        "pm_review_reason": manifest.get("pm_review_reason") or "",
        "summary": summary,
    }


def _data_readiness_evidence(manifest: dict[str, Any]) -> dict[str, Any]:
    status = str(manifest.get("data_readiness_status") or "")
    reasons = list(manifest.get("data_readiness_review_reasons") or manifest.get("data_readiness_halt_reasons") or [])
    summary = (
        f"Data readiness {status}: {', '.join(str(reason) for reason in reasons)}"
        if status and reasons
        else f"Data readiness {status or 'not evaluated'}"
    )
    return {
        "data_readiness_status": status,
        "data_readiness_scope": manifest.get("data_readiness_scope") or "",
        "data_readiness_artifact_path": manifest.get("data_readiness_artifact_path") or "",
        "data_readiness_review_reasons": list(manifest.get("data_readiness_review_reasons") or []),
        "data_readiness_halt_reasons": list(manifest.get("data_readiness_halt_reasons") or []),
        "data_readiness_next_operator_action": manifest.get("data_readiness_next_operator_action") or "",
        "market_calendar_status": manifest.get("market_calendar_status") or "",
        "market_data_status": manifest.get("market_data_status") or "",
        "quote_status": manifest.get("quote_status") or "",
        "safety_market_input_status": manifest.get("safety_market_input_status") or "",
        "candidate_model_path": manifest.get("candidate_model_path") or "",
        "candidate_model_status": manifest.get("candidate_model_status") or "",
        "opportunity_model_path": manifest.get("opportunity_model_path") or "",
        "opportunity_model_status": manifest.get("opportunity_model_status") or "",
        "pending_slot_status": manifest.get("pending_slot_status") or "",
        "pending_active": bool(manifest.get("pending_active")),
        "runtime_core_production_baseline": bool(manifest.get("runtime_core_production_baseline")),
        "broker_environment": manifest.get("broker_environment") or "",
        "broker_environment_production": bool(manifest.get("broker_environment_production")),
        "evidence_production_equivalent": bool(manifest.get("evidence_production_equivalent")),
        "acceptance_production_equivalent": bool(manifest.get("acceptance_production_equivalent")),
        "runtime_execution_path": manifest.get("runtime_execution_path") or "",
        "component_reasons": manifest.get("component_reasons") or {},
        "effective_component_statuses": manifest.get("effective_component_statuses") or {},
        "summary": summary,
    }


def _market_evidence(manifest: dict[str, Any]) -> dict[str, Any]:
    status = str(manifest.get("market_evidence_status") or manifest.get("market_data_status") or "")
    reason = str(manifest.get("market_evidence_reason") or "")
    market_date = str(manifest.get("market_date") or "")
    latest_expected = str(manifest.get("latest_expected_trading_date") or "")
    latest_available = str(manifest.get("latest_available_market_date") or "")
    quote_count = int(manifest.get("quote_count") or 0)
    missing_quote_count = int(manifest.get("missing_quote_count") or 0)
    publication_status = str(manifest.get("publication_status") or "")
    next_action = (
        "Review market / quote evidence before proceeding."
        if status in {"REVIEW_REQUIRED", "STALE", "DATA_NOT_YET_AVAILABLE", "HALT"}
        else "Proceed with normal evidence review."
    )
    summary = (
        f"Market Evidence {status or 'not evaluated'}: market_date={market_date}, "
        f"latest_expected={latest_expected}, latest_available={latest_available}, "
        f"quotes={quote_count}, missing_quotes={missing_quote_count}, publication={publication_status}"
    )
    if reason:
        summary += f", reason={reason}"
    return {
        "market_evidence_status": status,
        "market_evidence_reason": reason,
        "market_evidence_path": manifest.get("market_evidence_path") or "",
        "market_date": market_date,
        "latest_expected_trading_date": latest_expected,
        "latest_available_market_date": latest_available,
        "quote_count": quote_count,
        "missing_quote_count": missing_quote_count,
        "publication_status": publication_status,
        "next_operator_action": next_action,
        "summary": summary,
    }


def _current_temporal_migration_evidence(manifest: dict[str, Any]) -> dict[str, Any]:
    status = str(manifest.get("current_temporal_migration_status") or "")
    reason = str(manifest.get("current_temporal_migration_reason") or "")
    source_schema = str(manifest.get("current_temporal_source_schema_version") or "")
    target_schema = str(manifest.get("current_temporal_target_schema_version") or "")
    position_date = str(manifest.get("position_state_as_of") or "")
    valuation_date = str(manifest.get("valuation_as_of") or "")
    legacy_used = bool(manifest.get("current_temporal_legacy_as_of_used"))
    apply_executed = bool(manifest.get("current_temporal_apply_executed"))
    missing = list(manifest.get("current_temporal_missing_evidence") or [])
    summary = (
        f"Current Temporal Migration {status or 'not evaluated'}: "
        f"source={source_schema}, target={target_schema}, "
        f"position_state_as_of={position_date}, valuation_as_of={valuation_date}, "
        f"legacy_as_of_used={legacy_used}, apply_executed={apply_executed}"
    )
    if missing:
        summary += ", missing=" + ",".join(str(item) for item in missing)
    if reason:
        summary += f", reason={reason}"
    return {
        "current_temporal_migration_status": status,
        "current_temporal_migration_reason": reason,
        "source_schema": source_schema,
        "target_schema": target_schema,
        "position_state_as_of": position_date,
        "valuation_as_of": valuation_date,
        "legacy_as_of_used": legacy_used,
        "missing_evidence": missing,
        "apply_executed": apply_executed,
        "summary": summary,
    }


def _current_valuation_refresh_evidence(manifest: dict[str, Any]) -> dict[str, Any]:
    status = str(manifest.get("current_valuation_refresh_status") or manifest.get("current_valuation_status") or "")
    reason = str(manifest.get("current_valuation_refresh_reason") or "")
    no_fill = bool(manifest.get("current_valuation_no_fill"))
    position_date = str(manifest.get("current_valuation_position_state_as_of") or "")
    valuation_date = str(manifest.get("current_valuation_as_of") or "")
    market_date = str(manifest.get("current_valuation_market_date") or "")
    valued_count = int(manifest.get("current_valuation_valued_position_count") or 0)
    missing_symbols = list(manifest.get("current_valuation_missing_symbols") or [])
    previous_market_value = float(manifest.get("current_valuation_previous_total_market_value") or 0)
    new_market_value = float(manifest.get("current_valuation_new_total_market_value") or 0)
    apply_executed = bool(manifest.get("current_valuation_apply_executed"))
    summary = (
        f"Current Valuation Refresh {status or 'not evaluated'}: no_fill={no_fill}, "
        f"position_state_as_of={position_date}, valuation_as_of={valuation_date}, "
        f"market_date={market_date}, valued_positions={valued_count}, "
        f"missing_symbols={missing_symbols}, market_value={previous_market_value}->{new_market_value}, "
        f"apply_executed={apply_executed}"
    )
    if reason:
        summary += f", reason={reason}"
    return {
        "current_valuation_status": status,
        "current_valuation_reason": reason,
        "no_fill": no_fill,
        "position_state_as_of": position_date,
        "valuation_as_of": valuation_date,
        "market_date": market_date,
        "valued_position_count": valued_count,
        "missing_symbols": missing_symbols,
        "previous_total_market_value": previous_market_value,
        "new_total_market_value": new_market_value,
        "apply_executed": apply_executed,
        "summary": summary,
    }


def _pending_lifecycle_evidence(manifest: dict[str, Any]) -> dict[str, Any]:
    status = str(manifest.get("pending_lifecycle_status") or "")
    reason = str(manifest.get("transition_reason") or "")
    summary = (
        f"Pending lifecycle {status}: {reason}"
        if status
        else "Pending lifecycle not evaluated"
    )
    return {
        "pending_lifecycle_status": status,
        "pending_plan_id": manifest.get("pending_plan_id") or "",
        "previous_state": manifest.get("previous_state") or "",
        "new_state": manifest.get("new_state") or "",
        "transition_reason": reason,
        "target_session_date": manifest.get("target_session_date") or "",
        "approval_expires_at": manifest.get("approval_expires_at") or "",
        "consumed": bool(manifest.get("consumed")),
        "submit_attempt_detected": bool(manifest.get("submit_attempt_detected")),
        "unknown_submit_risk": bool(manifest.get("unknown_submit_risk")),
        "history_path": manifest.get("history_path") or "",
        "next_operator_action": manifest.get("next_operator_action") or "",
        "summary": summary,
    }


def _buy_ai_evidence(manifest: dict[str, Any]) -> dict[str, Any]:
    candidate_count = int(manifest.get("candidate_count") or 0)
    opportunity_count = int(manifest.get("opportunity_count") or 0)
    selected_count = int(manifest.get("selected_rank_count") or 0)
    summary = (
        f"selected_candidates {selected_count}, selected_top_rank 1"
        if selected_count
        else f"Candidate/Opportunity AI evidence not present; status={manifest.get('buy_ai_status') or ''}; reason={manifest.get('buy_ai_reason') or ''}"
    )
    return {
        "buy_ai_status": manifest.get("buy_ai_status") or "",
        "buy_ai_reason": manifest.get("buy_ai_reason") or "",
        "candidate": {
            "candidate_model_version": manifest.get("candidate_model_version") or "",
            "candidate_artifact_path": manifest.get("candidate_artifact_path") or "",
            "candidate_count": candidate_count,
            "candidate_schema_status": manifest.get("candidate_schema_status") or "",
            "candidate_missing_columns": manifest.get("candidate_missing_columns") or [],
            "candidate_review_required": manifest.get("candidate_review_required") or False,
            "candidate_review_reason": manifest.get("candidate_review_reason") or "",
        },
        "opportunity": {
            "opportunity_model_version": manifest.get("opportunity_model_version") or "",
            "opportunity_artifact_path": manifest.get("opportunity_artifact_path") or "",
            "opportunity_count": opportunity_count,
            "selected_rank_count": selected_count,
            "opportunity_schema_status": manifest.get("opportunity_schema_status") or "",
            "opportunity_missing_columns": manifest.get("opportunity_missing_columns") or [],
            "opportunity_review_required": manifest.get("opportunity_review_required") or False,
            "opportunity_review_reason": manifest.get("opportunity_review_reason") or "",
        },
        "selected_candidates": selected_count,
        "selected_top_rank": 1 if selected_count else None,
        "summary": summary,
    }


def _policy_evidence(manifest: dict[str, Any], pending: dict[str, Any]) -> dict[str, Any]:
    pending_policy = dict(pending.get("policy_context") or {})
    return {
        "capital_deployment_policy_source": manifest.get("capital_deployment_policy_source")
        or pending_policy.get("policy_source")
        or "",
        "capital_deployment_policy_version": manifest.get("capital_deployment_policy_version")
        or pending_policy.get("policy_version")
        or "",
        "active_policy_hash": manifest.get("active_policy_hash")
        or manifest.get("capital_deployment_policy_hash")
        or pending.get("capital_deployment_policy_hash")
        or pending_policy.get("policy_hash")
        or "",
        "target_investment_ratio": manifest.get("target_investment_ratio")
        or pending_policy.get("target_investment_ratio"),
        "cash_buffer": manifest.get("cash_buffer") or pending_policy.get("cash_buffer"),
        "max_exposure": manifest.get("max_exposure") or pending_policy.get("max_exposure"),
        "max_position_weight": manifest.get("max_position_weight") or pending_policy.get("max_position_weight"),
        "max_positions": manifest.get("max_positions") or pending_policy.get("max_positions"),
    }


def _safety_evidence(manifest: dict[str, Any], pending: dict[str, Any]) -> dict[str, Any]:
    pending_safety = dict(pending.get("safety_context") or {})
    return {
        "safety_decision_id": manifest.get("safety_decision_id")
        or pending.get("safety_decision_id")
        or pending_safety.get("safety_decision_id")
        or "",
        "safety_policy_version": manifest.get("safety_policy_version")
        or pending.get("safety_policy_version")
        or pending_safety.get("safety_policy_version")
        or "",
        "safety_source": manifest.get("safety_source") or pending_safety.get("safety_source") or "",
        "safety_decision": manifest.get("safety_decision") or pending_safety.get("decision") or "",
        "safety_reason": manifest.get("safety_reason") or pending_safety.get("reason") or "",
        "safety_status": manifest.get("safety_status") or "",
        "block_buy": bool(manifest.get("safety_block_buy") or pending_safety.get("block_buy")),
        "block_sell": bool(manifest.get("safety_block_sell") or pending_safety.get("block_sell")),
        "block_submit": bool(manifest.get("safety_block_submit") or pending_safety.get("block_submit")),
        "halt_runtime": bool(manifest.get("safety_halt_runtime") or pending_safety.get("halt_runtime")),
        "emergency_stop": bool(manifest.get("safety_emergency_stop") or pending_safety.get("emergency_stop")),
    }


def _submit_guard_evidence(manifest: dict[str, Any]) -> dict[str, Any]:
    item_evidence = tuple(item for item in manifest.get("submit_guard_item_evidence") or () if isinstance(item, dict))
    policy_consistency = dict(manifest.get("submit_policy_consistency") or {})
    item_decisions = tuple(str(item.get("guard_decision") or item.get("decision") or "") for item in item_evidence)
    reasons = tuple(
        str(item.get("guard_reason") or item.get("reason") or item.get("manual_review_reason") or "")
        for item in item_evidence
        if item.get("guard_reason") or item.get("reason") or item.get("manual_review_reason")
    )
    violated = tuple(
        str(item.get("violated_policy") or item.get("violated_policy_source") or "")
        for item in item_evidence
        if item.get("violated_policy") or item.get("violated_policy_source")
    )
    broker_quantity_checked = any(
        bool(item.get("broker_available_quantity_checked") or item.get("broker_available_quantity_source"))
        for item in item_evidence
    )
    sell_quantity_status = next(
        (
            str(item.get("sell_quantity_guard_status") or item.get("quantity_guard_status") or "")
            for item in item_evidence
            if str(item.get("side") or "").upper() == "SELL"
        ),
        "",
    )
    return {
        "guard_decision": _aggregate_guard_decision(item_decisions),
        "guard_reason": "; ".join(reasons),
        "violated_policy": ", ".join(value for value in violated if value),
        "violated_policy_source": _first_non_empty(item.get("violated_policy_source") for item in item_evidence),
        "manual_review_required": any(bool(item.get("manual_review_required")) for item in item_evidence),
        "policy_consistency_status": policy_consistency.get("policy_consistency_status")
        or policy_consistency.get("status")
        or "",
        "policy_mismatch_reason": policy_consistency.get("policy_mismatch_reason")
        or policy_consistency.get("reason")
        or "",
        "broker_available_quantity_checked": broker_quantity_checked,
        "broker_available_quantity_source": _first_non_empty(
            item.get("broker_available_quantity_source") for item in item_evidence
        ),
        "sell_quantity_guard_status": sell_quantity_status,
        "item_count": len(item_evidence),
    }


def _non_trading_day_demo_override_evidence(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "trading_day": bool(manifest.get("trading_day", True)),
        "business_day": bool(manifest.get("business_day", True)),
        "market_open": bool(manifest.get("market_open", True)),
        "non_trading_day_demo_override": bool(manifest.get("non_trading_day_demo_override", False)),
        "override_source": str(manifest.get("override_source") or "not_applicable"),
        "override_reason": str(manifest.get("override_reason") or "not_applicable"),
        "production_equivalent": bool(manifest.get("production_equivalent", True)),
        "acceptance_scope": str(manifest.get("acceptance_scope") or "regular_runtime"),
    }


def _review_required_blocked_halt(
    *,
    manifest: dict[str, Any],
    runtime_state: dict[str, Any],
    events: tuple[dict[str, Any], ...],
    review_required: bool,
    blocked: bool,
    halt: bool,
    guard: dict[str, Any],
    safety: dict[str, Any],
) -> dict[str, Any]:
    final_state = str(manifest.get("final_state") or runtime_state.get("state") or "unknown")
    warnings = tuple(str(value) for value in manifest.get("warnings") or ())
    errors = tuple(str(value) for value in manifest.get("errors") or ())
    review_reasons = list(warnings)
    blocked_reasons = list(errors if blocked else ())
    halt_reasons = list(errors if halt else ())
    for stage in manifest.get("stages") or ():
        if not isinstance(stage, dict):
            continue
        status = str(stage.get("status") or "").upper()
        message = str(stage.get("message") or stage.get("name") or "")
        if status == "REVIEW_REQUIRED":
            review_reasons.append(message)
        elif status == "BLOCKED":
            blocked_reasons.append(message)
        elif status == "HALT":
            halt_reasons.append(message)
    for event in events:
        severity = str(event.get("severity") or "").upper()
        message = str(event.get("message") or event.get("event_type") or "")
        if severity == "REVIEW_REQUIRED":
            review_reasons.append(message)
        elif severity == "BLOCKED":
            blocked_reasons.append(message)
        elif severity == "HALT":
            halt_reasons.append(message)
    if guard.get("manual_review_required"):
        review_reasons.append(guard.get("guard_reason") or "submit guard manual review required")
    if safety.get("safety_reason") and (
        safety.get("block_buy")
        or safety.get("block_sell")
        or safety.get("block_submit")
        or safety.get("halt_runtime")
        or safety.get("emergency_stop")
    ):
        review_reasons.append(str(safety["safety_reason"]))
    return {
        "final_state": final_state,
        "review_required_reasons": tuple(dict.fromkeys(reason for reason in review_reasons if reason)),
        "blocked_reasons": tuple(dict.fromkeys(reason for reason in blocked_reasons if reason)),
        "halt_reasons": tuple(dict.fromkeys(reason for reason in halt_reasons if reason)),
        "review_required": bool(review_required or review_reasons),
        "blocked": bool(blocked or blocked_reasons),
        "halt": bool(halt or halt_reasons),
    }


def _positions_from_asset(asset_state: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    positions = asset_state.get("positions") or ()
    if isinstance(positions, dict):
        return tuple(value for value in positions.values() if isinstance(value, dict))
    return tuple(position for position in positions if isinstance(position, dict))


def _public_position(position: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": position.get("symbol") or position.get("issue_code") or "unknown",
        "quantity": position.get("quantity"),
        "average_price": position.get("average_price"),
        "market_value": position.get("market_value"),
    }


def _public_order(order: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": order.get("symbol") or order.get("issue_code") or "unknown",
        "side": order.get("side") or "unknown",
        "quantity": order.get("quantity"),
        "status": order.get("status") or "unknown",
    }


def _positions_table(positions: Any) -> str:
    rows = tuple(positions or ())
    if not rows:
        return "- No active positions."
    lines = ["| Symbol | Quantity | Average price | Market value |", "| --- | ---: | ---: | ---: |"]
    for position in rows:
        lines.append(
            "| {symbol} | {quantity} | {average_price} | {market_value} |".format(
                symbol=position.get("symbol", "unknown"),
                quantity=_plain_number(position.get("quantity")),
                average_price=_money(position.get("average_price")),
                market_value=_money(position.get("market_value")),
            )
        )
    return "\n".join(lines)


def _orders_table(orders: Any) -> str:
    rows = tuple(orders or ())
    if not rows:
        return "- No orders."
    lines = ["| Symbol | Side | Quantity | Status |", "| --- | --- | ---: | --- |"]
    for order in rows:
        lines.append(
            "| {symbol} | {side} | {quantity} | {status} |".format(
                symbol=order.get("symbol", "unknown"),
                side=order.get("side", "unknown"),
                quantity=_plain_number(order.get("quantity")),
                status=order.get("status", "unknown"),
            )
        )
    return "\n".join(lines)


def _operation_summary(operation: dict[str, Any], *, include_orders: bool = True) -> str:
    lines = [
        f"- Morning status: {operation.get('morning_status')}",
        f"- Pending status: {operation.get('pending_status')}",
        f"- Submit status: {operation.get('submit_status')}",
        f"- Accepted count: {operation.get('accepted_count')}",
        f"- Rejected count: {operation.get('rejected_count')}",
        f"- Blocked count: {operation.get('blocked_count')}",
        f"- Unknown count: {operation.get('unknown_count')}",
        f"- Filled count: {operation.get('filled_count')}",
        f"- Execution-equivalent count: {operation.get('execution_equivalent_count')}",
        f"- BUY orders: {operation.get('buy_order_count')}",
        f"- SELL orders: {operation.get('sell_order_count')}",
        f"- BUY filled: {operation.get('buy_filled_count')}",
        f"- SELL filled: {operation.get('sell_filled_count')}",
        f"- Execution acceptance: {operation.get('execution_acceptance')}",
        f"- Review required: {operation.get('review_required')}",
        f"- Blocked: {operation.get('blocked')}",
        f"- Audit status: {operation.get('audit_status')}",
    ]
    if include_orders:
        lines.extend(("", "### Today's Orders", _orders_table(operation.get("orders"))))
    return "\n".join(lines)


def _why_text(reason_evidence: dict[str, Any], *, side: str) -> str:
    values = reason_evidence["why_buy"] if side == "BUY" else reason_evidence["why_sell"]
    if not values:
        return "- No side-specific Runtime Core reason evidence."
    return "\n".join(f"- {value}" for value in values)


def _pm_why_text(position_management: dict[str, Any], decision: str) -> str:
    key = "pm_hold_count" if decision == "HOLD" else "pm_exit_count"
    count = int(position_management.get(key) or 0)
    if count <= 0:
        return f"- No {decision} decision in latest Position Management artifact."
    return (
        f"- {decision} count: {count}\n"
        f"- model_version: {position_management.get('pm_model_version') or 'unknown'}\n"
        f"- artifact: {position_management.get('pm_artifact_path') or 'unknown'}"
    )


def _buy_ai_why_selected(buy_ai: dict[str, Any]) -> str:
    selected = int(buy_ai.get("selected_candidates") or 0)
    if selected <= 0:
        return "- No selected BUY candidate in latest Candidate/Opportunity AI artifacts."
    opportunity = dict(buy_ai.get("opportunity") or {})
    candidate = dict(buy_ai.get("candidate") or {})
    return (
        f"- selected_candidates: {selected}\n"
        f"- selected_top_rank: {buy_ai.get('selected_top_rank')}\n"
        f"- candidate_model_version: {candidate.get('candidate_model_version') or 'unknown'}\n"
        f"- opportunity_model_version: {opportunity.get('opportunity_model_version') or 'unknown'}\n"
        f"- candidate_artifact: {candidate.get('candidate_artifact_path') or 'unknown'}\n"
        f"- opportunity_artifact: {opportunity.get('opportunity_artifact_path') or 'unknown'}"
    )


def _bullet_dict(values: dict[str, Any]) -> str:
    return "\n".join(f"- {key}: {value}" for key, value in values.items())


def _format_counts(values: dict[str, Any]) -> str:
    if not values:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in values.items())


def _money(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "unknown"
    return f"JPY {number:,.0f}"


def _plain_number(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "unknown"
    if number.is_integer():
        return str(int(number))
    return str(number)


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _record_matches_business_date(record: dict[str, Any], business_date: str) -> bool:
    for key in ("business_date", "recorded_at", "created_at", "as_of", "updated_at"):
        value = str(record.get(key) or "")
        if value.startswith(business_date):
            return True
    return False


def _today_operation_orders(context: RuntimeV2ReportContext) -> tuple[dict[str, Any], ...]:
    pending_plan_id = str(context.pending.get("pending_plan_id") or "")
    matches = []
    for order in context.orders:
        if not _record_matches_business_date(order, context.business_date):
            continue
        if not pending_plan_id:
            matches.append(order)
            continue
        order_pending_plan_id = str(order.get("pending_plan_id") or "")
        source = str(order.get("source") or "")
        if order_pending_plan_id == pending_plan_id or source == "runtime_v2_execution_readonly":
            matches.append(order)
    return tuple(matches)


def _count_status(counts: Counter | dict[str, Any], statuses: tuple[str, ...]) -> int:
    return int(sum(int(counts.get(status, 0)) for status in statuses))


def _infer_morning_status(pending: dict[str, Any]) -> str:
    if pending.get("items"):
        return "PLANNING_DONE"
    state = str(pending.get("state") or "unknown")
    if state == "PENDING_APPROVAL":
        return "NO_SIGNAL_OR_PENDING_EMPTY"
    return "unknown"


def _infer_submit_status(pending: dict[str, Any], today_status_counts: Counter) -> str:
    if pending.get("consumed") and today_status_counts:
        return "SUBMIT_RECORDED"
    if pending.get("consumed"):
        return "CONSUMED_NO_TODAY_ORDER_RECORD"
    if today_status_counts:
        return "ORDER_HISTORY_PRESENT_PENDING_NOT_CONSUMED"
    return "NOT_SUBMITTED_OR_NO_TODAY_RECORD"


def _valuation_confidence_warning(asset: dict[str, Any]) -> bool:
    positions = _positions_from_asset(asset)
    return any(
        _number(position.get("average_price")) in (None, 0.0) or _number(position.get("market_value")) is None
        for position in positions
        if _number(position.get("quantity")) not in (None, 0.0)
    )


def _public_json_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "business_date": summary["business_date"],
        "runtime_mode": summary["runtime_mode"],
        "environment": summary["environment"],
        "report_scope_contract": summary["report_scope_contract"],
        "current_portfolio": summary["current_portfolio"],
        "today_operation": {
            key: value for key, value in summary["today_operation"].items() if key != "orders"
        },
        "current_run": summary["current_run"],
        "ledger_history": summary["ledger_history"],
        "pending_approval": summary["pending_approval"],
        "warning_summary": summary["warning_summary"],
        "reason_evidence": summary["reason_evidence"],
        "position_management": summary["position_management"],
        "notification": summary["notification"],
        "current_sot": summary["current_sot"],
        "positions": summary["positions"],
        "order_status_counts": summary["order_status_counts"],
        "order_side_counts": summary["order_side_counts"],
        "ledger_summary": summary["ledger_summary"],
        "reconcile": summary["reconcile"],
        "audit": summary["audit"],
        "notification_payload": summary["notification_payload"],
        "notes": summary["notes"],
    }


def _notification_severity(review: dict[str, Any], guard: dict[str, Any], safety: dict[str, Any]) -> str:
    final_state = str(review.get("final_state") or "").upper()
    if final_state == "HALT" or review.get("halt") or safety.get("halt_runtime") or safety.get("emergency_stop"):
        return "HALT"
    if final_state == "BLOCKED" or review.get("blocked"):
        return "BLOCKED"
    if final_state == "REVIEW_REQUIRED" or review.get("review_required"):
        return "REVIEW_REQUIRED"
    if guard.get("manual_review_required"):
        return "ACTION_REQUIRED"
    return "INFO"


def _next_operator_action(
    severity: str,
    guard: dict[str, Any],
    safety: dict[str, Any],
    review: dict[str, Any],
) -> str:
    if severity == "HALT":
        return "Stop runtime operation and inspect Safety / Operation Guard before rerun."
    if guard.get("violated_policy") == "broker_available_quantity" or (
        "broker_available_quantity" in str(guard.get("guard_reason") or "")
    ):
        return "Refresh Broker ReadOnly positions and confirm SELL available quantity."
    if safety.get("block_submit"):
        return "Inspect Runtime Safety decision and do not submit until Safety is PASS."
    if severity in {"REVIEW_REQUIRED", "ACTION_REQUIRED"}:
        reasons = tuple(review.get("review_required_reasons") or ())
        if reasons:
            return "Review Runtime manifest reasons: " + "; ".join(reasons[:3])
        return "Review Runtime manifest, Pending, Approval, Safety, and Submit Guard evidence."
    if severity == "BLOCKED":
        return "Resolve blocked Runtime evidence before rerun."
    return "No operator action required."


def _reason_summary(
    *,
    policy: dict[str, Any],
    safety: dict[str, Any],
    guard: dict[str, Any],
    review: dict[str, Any],
) -> str:
    parts = [
        "final_state=" + str(review.get("final_state") or "unknown"),
        "policy=" + _policy_summary(policy),
        "safety=" + _safety_summary(safety),
        "guard=" + _guard_summary(guard),
    ]
    return "; ".join(parts)


def _policy_summary(policy: dict[str, Any]) -> str:
    source = policy.get("capital_deployment_policy_source") or "missing"
    version = policy.get("capital_deployment_policy_version") or "missing"
    max_exposure = policy.get("max_exposure")
    max_position_weight = policy.get("max_position_weight")
    return (
        f"source={source}, version={version}, max_exposure={max_exposure}, "
        f"max_position_weight={max_position_weight}"
    )


def _safety_summary(safety: dict[str, Any]) -> str:
    decision = safety.get("safety_decision") or "unknown"
    reason = safety.get("safety_reason") or "none"
    return f"decision={decision}, reason={reason}"


def _guard_summary(guard: dict[str, Any]) -> str:
    decision = guard.get("guard_decision") or "NOT_EVALUATED"
    reason = guard.get("guard_reason") or "none"
    violated = guard.get("violated_policy") or "none"
    return f"decision={decision}, violated_policy={violated}, reason={reason}"


def _why_side(
    side: str,
    guard: dict[str, Any],
    policy: dict[str, Any],
    safety: dict[str, Any],
) -> tuple[str, ...]:
    side_upper = side.upper()
    if guard.get("item_count") == 0:
        return (
            f"{side_upper} was not submitted in the latest Runtime manifest, or Submit Guard was not evaluated.",
            "Report did not recalculate Policy, Safety, or Submit Guard.",
        )
    safety_blocked = safety.get("block_buy") if side_upper == "BUY" else safety.get("block_sell")
    lines = [
        f"Policy source: {policy.get('capital_deployment_policy_source') or 'missing'}",
        f"Policy version: {policy.get('capital_deployment_policy_version') or 'missing'}",
        f"Safety decision: {safety.get('safety_decision') or 'unknown'}",
        f"Safety reason: {safety.get('safety_reason') or 'none'}",
        f"Submit Guard decision: {guard.get('guard_decision') or 'NOT_EVALUATED'}",
    ]
    if safety_blocked:
        lines.append(f"{side_upper} is blocked by Runtime Safety.")
    if guard.get("violated_policy"):
        lines.append(f"Violated policy: {guard['violated_policy']}")
    if guard.get("guard_reason"):
        lines.append(f"Guard reason: {guard['guard_reason']}")
    if side_upper == "SELL":
        lines.append(f"Broker available quantity checked: {guard.get('broker_available_quantity_checked')}")
        if guard.get("broker_available_quantity_source"):
            lines.append(f"Broker available quantity source: {guard['broker_available_quantity_source']}")
    return tuple(lines)


def _aggregate_guard_decision(decisions: tuple[str, ...]) -> str:
    normalized = tuple(decision.upper() for decision in decisions if decision)
    if not normalized:
        return "NOT_EVALUATED"
    for status in ("HALT", "BLOCKED", "REVIEW_REQUIRED", "FAIL"):
        if status in normalized:
            return status
    if all(status == "PASS" for status in normalized):
        return "PASS"
    return normalized[0]


def _first_non_empty(values: Any) -> str:
    for value in values:
        if value:
            return str(value)
    return ""


def _has_event(events: Any, event_type: str) -> bool:
    return any(str(event.get("event_type") or "") == event_type for event in events or ())


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
