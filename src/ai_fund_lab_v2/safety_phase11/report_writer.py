from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.safety_phase11.event_writer import _phase11_sanitize, _write_json
from ai_fund_lab_v2.safety_phase11.models import SafetyDecision, SafetyState, utc_now_iso
from ai_fund_lab_v2.safety_phase11.report_schema import build_phase11_safety_report
from ai_fund_lab_v2.safety_phase11.safety_manager import SafetyManagerResult


def build_safety_report_payload(result: Any) -> dict[str, Any]:
    return _phase11_sanitize(build_phase11_safety_report(result))


def write_safety_report(result: Any, reports_dir: Path | str = "reports") -> Path:
    business_date = getattr(result, "business_date", None) or utc_now_iso()[:10]
    directory = Path(reports_dir) / "safety" / "phase11"
    path = directory / f"{business_date}_safety_report.json"
    _write_json(path, build_safety_report_payload(result))
    return path


def build_safety_markdown_report(result: Any, *, safety_report_path: Path | str = "") -> str:
    payload = build_safety_report_payload(result)
    lines = [
        f"# Phase11 Safety Report {payload['business_date']}",
        "",
        f"- report_id: {payload['report_id']}",
        f"- generated_at: {payload['generated_at']}",
        f"- environment: {payload['environment']}",
        f"- runtime_id: {payload['runtime_id']}",
        f"- current_safety_state: {payload['current_safety_state']}",
        f"- overall_decision: {payload['overall_decision']}",
        f"- next_recommended_safety_state: {payload['next_recommended_safety_state']}",
        "",
        "## New Buy Permission",
        "",
        "新規買い可否:",
        "ALLOW" if "new_buy" not in payload["blocked_actions"] and "new_buy_during_buy_stop" not in payload["blocked_actions"] else "BLOCKED",
        "",
        "## Emergency Candidates",
        "",
        *_list_lines(payload["emergency_candidates"]),
        "",
        "## Review Required Items",
        "",
        *_list_lines([item["reason_code"] for item in payload["review_required_items"]]),
        "",
        "## Market Crash / Recovery",
        "",
        f"- market_crash_status: {payload['market_crash_status']}",
        f"- market_stress_detected: {payload['market_stress_summary']['market_stress_detected']}",
        f"- buy_opportunity_review: {payload['buy_opportunity_review']}",
        f"- sell_review_required: {payload['sell_review_required']}",
        f"- high_risk_review: {payload['high_risk_review']}",
        "- emergency_stop_from_market_price_decline: false",
        "- auto_sell_executed: false",
        "- auto_buy_stop_executed: false",
        f"- recovery_candidate_status: {payload['recovery_candidate_status']}",
        "",
        "## Recommended Human Actions",
        "",
        *_list_lines(payload["recommended_human_actions"]),
        "",
        "## Blocked Actions",
        "",
        *_list_lines(payload["blocked_actions"]),
        "",
        "## No Live Order Confirmation",
        "",
        f"- broker_api_connected: {payload['no_live_order_confirmation']['broker_api_connected']}",
        f"- websocket_connected: {payload['no_live_order_confirmation']['websocket_connected']}",
        f"- demo_order_submitted: {payload['no_live_order_confirmation']['demo_order_submitted']}",
        f"- production_order_submitted: {payload['no_live_order_confirmation']['production_order_submitted']}",
        f"- clm_kabu_new_order_executed: {payload['no_live_order_confirmation']['clm_kabu_new_order_executed']}",
        f"- auto_sell_executed: {payload['auto_sell_executed']}",
        f"- auto_recovery_executed: {payload['auto_recovery_executed']}",
    ]
    if safety_report_path:
        lines.extend(["", f"JSON: {safety_report_path}"])
    return "\n".join(lines) + "\n"


def write_safety_markdown_report(result: Any, reports_dir: Path | str = "reports", *, safety_report_path: Path | str = "") -> Path:
    business_date = getattr(result, "business_date", None) or utc_now_iso()[:10]
    directory = Path(reports_dir) / "safety" / "phase11"
    path = directory / f"{business_date}_safety_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_phase11_sanitize(build_safety_markdown_report(result, safety_report_path=safety_report_path)), encoding="utf-8")
    return path


def write_safety_report_bundle(result: Any, reports_dir: Path | str = "reports") -> tuple[Path, Path]:
    json_path = write_safety_report(result, reports_dir=reports_dir)
    markdown_path = write_safety_markdown_report(result, reports_dir=reports_dir, safety_report_path=json_path)
    return json_path, markdown_path


def _list_lines(values: list[str]) -> list[str]:
    if not values:
        return ["- none"]
    return [f"- {value}" for value in values]


def _review_item_payload(item: Any) -> dict[str, Any]:
    return {
        "review_id": item.review_id,
        "event_id": item.event_id,
        "guard_name": item.guard_name.value,
        "reason_code": item.reason_code,
        "message": item.message,
        "severity": item.severity.value,
        "issue_code": item.issue_code,
        "recommended_action": item.recommended_action,
    }


def _detail_value(guard_results: tuple[Any, ...], key: str, default: str) -> Any:
    for result in guard_results:
        if key in result.details:
            return result.details[key]
    return default


def _has_reason(guard_results: tuple[Any, ...], reason_code: str) -> bool:
    return any(result.reason_code == reason_code for result in guard_results)


def _allowed_actions(result: SafetyManagerResult) -> list[str]:
    base = ["read_only_broker_sync", "quote_polling", "audit", "report"]
    if result.overall_decision is SafetyDecision.ALLOW and result.current_state in {SafetyState.NORMAL, SafetyState.WARNING}:
        return base + ["pre_order_safety_passed_candidate"]
    return base


def _blocked_actions(result: SafetyManagerResult) -> list[str]:
    blocked = ["broker_order_api", "demo_order_submit", "production_order_submit", "auto_sell", "auto_cancel", "auto_retry"]
    if result.overall_decision is not SafetyDecision.ALLOW:
        blocked.append("new_buy")
    if result.state_candidate is SafetyState.EMERGENCY_STOP:
        blocked.append("all_order_submission")
    return blocked
