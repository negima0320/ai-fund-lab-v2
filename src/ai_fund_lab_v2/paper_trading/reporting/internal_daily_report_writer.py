from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.paper_trading.daily_run_result import DailyRunResult
from ai_fund_lab_v2.paper_trading.run_manifest import DailyRunManifest


def write_internal_daily_report(
    *,
    manifest: DailyRunManifest,
    result: DailyRunResult,
    reports_dir: Path | str = "reports/phase9/daily",
) -> tuple[Path, Path]:
    payload = render_internal_daily_report_json(manifest=manifest, result=result)
    markdown = render_internal_daily_report_markdown(payload)
    output_dir = Path(reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{manifest.run_date}_daily_operation_report.md"
    json_path = output_dir / f"{manifest.run_date}_daily_operation_report.json"
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return md_path, json_path


def render_internal_daily_report_json(*, manifest: DailyRunManifest, result: DailyRunResult) -> dict[str, Any]:
    return sanitize_mapping(
        {
            "report_type": "phase9_internal_daily_operation_report",
            "generated_at": utc_now_iso(),
            "manifest": manifest.to_dict(),
            "result": result.to_dict(),
            "phase9_boundary": {
                "broker_order_api_called": False,
                "open_d_auto_startup": False,
                "unlock_trade_called": False,
                "paper_ledger_fill_executed_by_report": False,
            },
        }
    )


def render_internal_daily_report_markdown(payload: dict[str, Any]) -> str:
    manifest = payload["manifest"]
    result = payload["result"]
    safety = result.get("safety_state", {})
    review = result.get("review_state", {})
    artifact = result.get("artifact_state", {})
    execution = result.get("execution_state", {})
    lines = [
        "# Phase9 Daily Operation Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- run_id: {manifest.get('run_id')}",
        f"- run_date: {manifest.get('run_date')}",
        f"- data_until: {manifest.get('data_until')}",
        f"- train_until: {manifest.get('train_until')}",
        f"- decision_for: {manifest.get('decision_for')}",
        f"- virtual_order_date: {manifest.get('virtual_order_date')}",
        f"- virtual_execution_date: {manifest.get('virtual_execution_date')}",
        f"- report_status: {manifest.get('report_status')}",
        "",
        "## AI Decisions",
        "",
        _candidate_section("BUY", result.get("buy_candidates", [])),
        _candidate_section("SELL", result.get("sell_candidates", [])),
        _candidate_section("HOLD", result.get("hold_candidates", [])),
        "",
        "## Artifact Loading",
        "",
        f"- integration_status: {artifact.get('integration_status', 'not_connected')}",
        f"- candidate_count: {artifact.get('candidate_count', 0)}",
        f"- allocation_decision_count: {artifact.get('allocation_decision_count', 0)}",
        f"- order_plan_item_count: {artifact.get('order_plan_item_count', 0)}",
        "",
        "### Artifact Statuses",
        "",
        _artifact_status_section(artifact.get("artifact_statuses", [])),
        "",
        "## Assets",
        "",
        "### Portfolio Summary",
        "",
        f"- cash: {result.get('cash')}",
        f"- current_cash: {result.get('current_cash')}",
        f"- total_equity: {result.get('total_equity')}",
        f"- market_value: {result.get('market_value')}",
        f"- realized_pnl: {result.get('realized_pnl')}",
        f"- unrealized_pnl: {result.get('unrealized_pnl')}",
        f"- trade_count: {result.get('trade_count')}",
        f"- position_count: {len(result.get('current_positions') or result.get('positions', []))}",
        "",
        "### Positions",
        "",
        _positions_section(result.get("current_positions") or result.get("positions", [])),
        "",
        "### Pending Orders",
        "",
        _pending_orders_section(result.get("pending_orders", [])),
        "",
        "## Virtual Fill Results",
        "",
        "### Filled Orders",
        "",
        _execution_section(execution.get("filled_orders", [])),
        "",
        "### No Fill Orders",
        "",
        _execution_section(execution.get("no_fill_orders", [])),
        "",
        "### Ledger Diff",
        "",
        f"- ledger_diff_path: {execution.get('ledger_diff_path', 'none')}",
        f"- cash_change: {_execution_cash_change(execution)}",
        "",
        "## Safety",
        "",
        f"- safety_status: {manifest.get('safety_status')}",
        f"- safety_state: {safety.get('status', 'unknown')}",
        "",
        "## Human Review",
        "",
        f"- human_review_status: {manifest.get('human_review_status')}",
        f"- review_state: {review.get('status', 'unknown')}",
        "",
        "## Phase9 Boundary",
        "",
        "- broker_order_api_called: false",
        "- open_d_auto_startup: false",
        "- unlock_trade_called: false",
        "- paper_ledger_fill_executed_by_report: false",
    ]
    return "\n".join(lines) + "\n"


def _candidate_section(title: str, candidates: list[dict[str, Any]]) -> str:
    lines = [f"### {title}", ""]
    if not candidates:
        lines.append("- none")
        return "\n".join(lines)
    for item in candidates:
        name = f" {item.get('issue_name')}" if item.get("issue_name") else ""
        reason = item.get("reason") or item.get("short_reason") or ""
        planned = ""
        if item.get("planned_quantity") not in (None, "", "0"):
            planned = f" qty={item.get('planned_quantity')}"
        if item.get("planned_amount") not in (None, "", "0"):
            planned += f" amount={item.get('planned_amount')}"
        lines.append(f"- {item.get('issue_code')}{name}{planned}: {reason}")
    return "\n".join(lines)


def _artifact_status_section(statuses: list[dict[str, Any]]) -> str:
    if not statuses:
        return "- none"
    lines: list[str] = []
    for status in statuses:
        reasons = ",".join(status.get("blocked_reasons", []))
        suffix = f" reason={reasons}" if reasons else ""
        lines.append(f"- {status.get('name')}: {status.get('status')} rows={status.get('row_count', 0)}{suffix}")
    return "\n".join(lines)


def _positions_section(positions: list[dict[str, Any]]) -> str:
    if not positions:
        return "- none"
    lines: list[str] = []
    for position in positions:
        lines.append(
            "- "
            f"{position.get('issue_code')} {position.get('issue_name', '')}"
            f" qty={position.get('quantity')}"
            f" avg={position.get('average_cost')}"
            f" market_value={position.get('market_value')}"
            f" unrealized_pnl={position.get('unrealized_pnl')}"
            f" holding_days={position.get('holding_days')}"
        )
    return "\n".join(lines)


def _pending_orders_section(orders: list[dict[str, Any]]) -> str:
    if not orders:
        return "- none"
    lines: list[str] = []
    for order in orders:
        lines.append(
            "- "
            f"{order.get('order_id')}"
            f" {order.get('side')}"
            f" {order.get('code')}"
            f" qty={order.get('quantity')}"
            f" status={order.get('status')}"
        )
    return "\n".join(lines)


def _execution_section(records: list[dict[str, Any]]) -> str:
    if not records:
        return "- none"
    lines: list[str] = []
    for record in records:
        suffix = f" no_fill_reason={record.get('no_fill_reason')}" if record.get("no_fill_reason") else ""
        lines.append(
            "- "
            f"{record.get('order_id')}"
            f" {record.get('side')}"
            f" {record.get('code')}"
            f" qty={record.get('quantity')}"
            f" price={record.get('fill_price')}"
            f" realized_pnl={record.get('realized_pnl')}"
            f" status={record.get('status')}"
            f"{suffix}"
        )
    return "\n".join(lines)


def _execution_cash_change(execution: dict[str, Any]) -> str:
    records = execution.get("filled_orders", [])
    if not records:
        return "0"
    # The exact cash change is stored in ledger_diff JSON; this summary stays human-readable.
    return "see ledger_diff"
