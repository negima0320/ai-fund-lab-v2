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
        },
        "current_portfolio": current_portfolio,
        "today_operation": today_operation,
        "current_run": current_run,
        "ledger_history": ledger_history,
        "pending_approval": pending_approval,
        "warning_summary": warning_summary,
        "notification": {
            "payload_generated": True,
            "send_executed": False,
            "mode": "payload-only",
            "line_status": "send-disabled",
            "discord_status": "send-disabled",
            "execution_equivalent_count": today_execution_equivalent_count,
            "sell_filled_count": int(today_execution_side_counts.get("SELL", 0)),
            "buy_filled_count": int(today_execution_side_counts.get("BUY", 0)),
            "summary_only": True,
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
            "summary_only": True,
        },
        "notes": warning_summary["notes"],
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
                "scoped_summary": {
                    "current_portfolio": reports.summary["current_portfolio"],
                    "today_operation": {
                        key: value for key, value in reports.summary["today_operation"].items() if key != "orders"
                    },
                    "current_run": reports.summary["current_run"],
                    "ledger_history": reports.summary["ledger_history"],
                    "pending_approval": reports.summary["pending_approval"],
                    "warnings": reports.summary["warning_summary"],
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


def _has_event(events: Any, event_type: str) -> bool:
    return any(str(event.get("event_type") or "") == event_type for event in events or ())


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
