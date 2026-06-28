from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_fund_lab_v2.safety_phase11.event_writer import _phase11_sanitize, _write_json
from ai_fund_lab_v2.safety_phase11.models import SafetyDecision, SafetyState, utc_now_iso
from ai_fund_lab_v2.safety_phase11.report_schema import build_phase11_safety_report


SYSTEM_EMERGENCY_REASONS = {
    "DUPLICATE_ORDER_SYSTEM_EMERGENCY",
    "BROKER_DUPLICATE_ORDER_RISK",
    "DUPLICATE_ACTIVE_BUY_ORDER",
    "BROKER_DIVERGENCE_DETECTED",
    "BROKER_SNAPSHOT_UNAVAILABLE",
    "BROKER_SNAPSHOT_MISSING",
    "BROKER_SNAPSHOT_STALE",
    "RUNTIME_STATE_INCONSISTENT",
    "POSITION_QUANTITY_MISMATCH",
    "ORDER_EXECUTION_SEVERE_DIVERGENCE",
    "SECRET_PERSISTENCE_VIOLATION",
    "RAW_RESPONSE_PERSISTENCE_VIOLATION",
    "UNKNOWN_SEVERE_ERROR",
    "MANUAL_EMERGENCY_STOP",
}


def build_line_notification_payload(result_or_report: Any) -> dict[str, Any]:
    report = _coerce_report(result_or_report)
    level = _notification_level(report)
    title, message = _title_and_message(level)
    sections = _sections(report, level)
    payload = {
        "schema_version": "phase11_refined_safety_line_notification_payload_v1",
        "created_at": utc_now_iso(),
        "business_date": report.get("business_date"),
        "environment": report.get("environment"),
        "runtime_id": report.get("runtime_id"),
        "notification_level": level,
        "title": title,
        "message": message,
        "sections": sections,
        "triggered_events": _triggered_events(report),
        "recommended_actions": report.get("recommended_human_actions", []),
        "requires_human_review": bool(report.get("review_required_items") or report.get("emergency_candidates")),
        "auto_sell_executed": False,
        "auto_recovery_executed": False,
        "live_order_executed": False,
        "raw_response_saved": False,
        "line_send_executed": False,
        "no_live_order_confirmation": report.get("no_live_order_confirmation", {}),
    }
    return _phase11_sanitize(payload)


def write_line_notification_payload(result_or_report: Any, *, reports_dir: Path | str = "reports") -> Path:
    payload = build_line_notification_payload(result_or_report)
    business_date = str(payload.get("business_date") or utc_now_iso()[:10])
    directory = Path(reports_dir) / "safety" / "phase11" / "notifications"
    path = directory / f"{business_date}_line_notification_payload.json"
    _write_json(path, payload)
    return path


def _coerce_report(result_or_report: Any) -> dict[str, Any]:
    if isinstance(result_or_report, dict) and "schema_version" in result_or_report:
        return dict(result_or_report)
    return build_phase11_safety_report(result_or_report)


def _notification_level(report: dict[str, Any]) -> str:
    next_state = str(report.get("next_recommended_safety_state") or "")
    decision = str(report.get("overall_decision") or "")
    reasons = set(_reason_codes(report))
    if next_state in {SafetyState.SYSTEM_EMERGENCY_STOP.value, SafetyState.EMERGENCY_STOP.value}:
        return "SYSTEM_EMERGENCY"
    if decision == SafetyDecision.EMERGENCY_STOP.value and reasons.intersection(SYSTEM_EMERGENCY_REASONS):
        return "SYSTEM_EMERGENCY"
    if report.get("buy_opportunity_review"):
        return "BUY_OPPORTUNITY_REVIEW"
    if report.get("market_stress_summary", {}).get("market_stress_detected"):
        return "MARKET_STRESS"
    if report.get("sell_review_required") or report.get("high_risk_review") or _daily_loss_review(report):
        return "POSITION_REVIEW"
    if report.get("review_required_items"):
        return "REVIEW_REQUIRED"
    return "INFO"


def _title_and_message(level: str) -> tuple[str, str]:
    if level == "SYSTEM_EMERGENCY":
        return (
            "SYSTEM EMERGENCY",
            "発注停止 / 人間確認必須。システム事故またはBroker不整合の可能性があります。",
        )
    if level == "BUY_OPPORTUNITY_REVIEW":
        return (
            "BUY OPPORTUNITY REVIEW",
            "大きな下落を検知。買い場候補として確認してください。自動買い停止ではありません。",
        )
    if level == "MARKET_STRESS":
        return (
            "MARKET STRESS",
            "市場下落を検知。自動停止ではありません。買い場候補として確認してください。",
        )
    if level == "POSITION_REVIEW":
        return (
            "POSITION REVIEW",
            "保有銘柄の大きな変動を検知。自動売却はしていません。売却 / 保有 / 買い増しを確認してください。",
        )
    if level == "REVIEW_REQUIRED":
        return ("SAFETY REVIEW REQUIRED", "Safety Reviewが必要です。実発注は行っていません。")
    return ("SAFETY OK", "Safety上の重大通知はありません。")


def _sections(report: dict[str, Any], level: str) -> list[dict[str, Any]]:
    sections = [
        {
            "heading": "Summary",
            "items": [
                f"Safety State: {report.get('next_recommended_safety_state')}",
                f"Overall Decision: {report.get('overall_decision')}",
                "Auto Sell Executed: false",
                "Auto Recovery Executed: false",
                "Live Order Executed: false",
            ],
        }
    ]
    if level == "SYSTEM_EMERGENCY":
        sections.append(
            {
                "heading": "System Emergency",
                "items": [
                    "発注停止 / 人間確認必須",
                    f"理由: {', '.join(_reason_codes(report)) or 'unknown'}",
                    f"対象: {', '.join(_affected_issue_codes(report)) or 'n/a'}",
                ],
            }
        )
    if report.get("market_stress_summary", {}).get("market_stress_detected"):
        sections.append(
            {
                "heading": "Market Stress",
                "items": [
                    "市場下落を検知",
                    "自動停止ではありません",
                    "買い場候補として確認してください",
                ],
            }
        )
    if report.get("buy_opportunity_review"):
        sections.append(
            {
                "heading": "Buy Opportunity Review",
                "items": [
                    "大きな下落を検知",
                    "買い場候補として確認してください",
                    "自動買い停止ではありません",
                ],
            }
        )
    if report.get("sell_review_required") or report.get("high_risk_review") or _daily_loss_review(report):
        sections.append(
            {
                "heading": "Position Review",
                "items": [
                    "保有銘柄の大きな変動を検知",
                    "自動売却はしていません",
                    "売却 / 保有 / 買い増しを確認してください",
                ],
            }
        )
    if report.get("recommended_human_actions"):
        sections.append({"heading": "Recommended Actions", "items": list(report.get("recommended_human_actions", []))})
    return sections


def _triggered_events(report: dict[str, Any]) -> list[dict[str, Any]]:
    events = []
    for item in report.get("review_required_items", []):
        events.append(
            {
                "guard": item.get("guard"),
                "reason_code": item.get("reason_code"),
                "severity": item.get("severity"),
                "affected_issue_code": item.get("affected_issue_code"),
            }
        )
    return events


def _reason_codes(report: dict[str, Any]) -> list[str]:
    return [str(item.get("reason_code") or "") for item in report.get("review_required_items", []) if item.get("reason_code")]


def _affected_issue_codes(report: dict[str, Any]) -> list[str]:
    return [
        str(item.get("affected_issue_code"))
        for item in report.get("review_required_items", [])
        if item.get("affected_issue_code")
    ]


def _daily_loss_review(report: dict[str, Any]) -> bool:
    reason = str(report.get("daily_loss_summary", {}).get("reason_code") or "")
    return reason in {"DAILY_LOSS_REVIEW_REQUIRED", "MARKET_STRESS_DAILY_LOSS"}
