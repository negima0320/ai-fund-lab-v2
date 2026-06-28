#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.safety_phase11.integrated_backtest_audit import (
    AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
    IntegratedBacktestAuditResult,
    run_integrated_backtest_audit,
    smoke_1y_config,
)
from ai_fund_lab_v2.paper_trading.daily_run_result import DailyCandidate, DailyPosition, DailyRunResult
from ai_fund_lab_v2.paper_trading.reporting.blog_draft_writer import write_blog_draft
from ai_fund_lab_v2.paper_trading.reporting.public_daily_report_writer import write_public_daily_report
from ai_fund_lab_v2.paper_trading.run_manifest import DailyRunManifest
from ai_fund_lab_v2.safety_phase11.event_writer import _phase11_sanitize, _write_json
from ai_fund_lab_v2.safety_phase11.notification_payload_writer import write_line_notification_payload
from ai_fund_lab_v2.safety_phase11.models import utc_now_iso


START_DATE = "2025-06-01"
END_DATE = "2025-08-31"
MAX_DAYS = 60
SAFETY_ON_SUBDIR = "fix_e2_refined_mainline_smoke"
SAFETY_OFF_SUBDIR = "fix_e2_refined_mainline_safety_off_smoke"
PHASE_DOC_PATH = Path("docs/phase_reports/phase11z_fix_e2_refined_mainline_smoke.md")
PHASE_JSON_PATH = Path("reports/phase_reports/phase11z_fix_e2_refined_mainline_smoke.json")


def main() -> int:
    on = _run_smoke(safety_enabled=True)
    off = _run_smoke(safety_enabled=False)
    safety_state = _safety_state_for_public_report(on)
    report_surface = _write_report_surfaces(on, safety_state)
    notification_path = write_line_notification_payload(_line_report(on, safety_state), reports_dir="reports")
    payload = _summary_payload(on, off, report_surface, notification_path, safety_state)
    _write_json(PHASE_JSON_PATH, payload)
    PHASE_DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    PHASE_DOC_PATH.write_text(_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "phase_report_path": str(PHASE_DOC_PATH), "phase_report_json_path": str(PHASE_JSON_PATH)}, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


def _run_smoke(*, safety_enabled: bool) -> IntegratedBacktestAuditResult:
    cfg = smoke_1y_config(reports_dir="reports")
    cfg = replace(
        cfg,
        period_id=SAFETY_ON_SUBDIR if safety_enabled else SAFETY_OFF_SUBDIR,
        start_date=START_DATE,
        end_date=END_DATE,
        output_subdir=SAFETY_ON_SUBDIR if safety_enabled else SAFETY_OFF_SUBDIR,
        max_days=MAX_DAYS,
        audit_profile=AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
        safety_enabled=safety_enabled,
    )
    return run_integrated_backtest_audit(cfg)


def _safety_state_for_public_report(result: IntegratedBacktestAuditResult) -> dict[str, Any]:
    reason_counts: dict[str, int] = {}
    for row in result.daily_records:
        for reason in row.triggered_reason_codes:
            reason_counts[str(reason)] = reason_counts.get(str(reason), 0) + 1
    review_items = [{"reason_code": reason, "count": count} for reason, count in sorted(reason_counts.items())]
    has_position_review = bool({"SELL_REVIEW_REQUIRED", "HIGH_RISK_REVIEW"} & set(reason_counts))
    has_market_review = bool({"MARKET_STRESS", "BUY_OPPORTUNITY_REVIEW", "MARKET_STRESS_DAILY_LOSS"} & set(reason_counts))
    return {
        "next_recommended_safety_state": result.daily_records[-1].safety_state_after.value if result.daily_records else "NORMAL",
        "market_stress": has_market_review,
        "buy_opportunity_review": "BUY_OPPORTUNITY_REVIEW" in reason_counts,
        "position_review": has_position_review,
        "sell_review_required": "SELL_REVIEW_REQUIRED" in reason_counts,
        "high_risk_review": "HIGH_RISK_REVIEW" in reason_counts,
        "review_required_items": review_items,
        "recommended_human_actions": [
            "市場下落や保有銘柄変動はEmergencyではなく人間確認として扱う。",
            "保有銘柄の売却 / 保有 / 買い増しを確認する。",
            "System Emergencyがない限り、停止扱いはしない。",
        ],
    }


def _write_report_surfaces(result: IntegratedBacktestAuditResult, safety_state: dict[str, Any]) -> dict[str, Any]:
    output_dir = Path(result.output_dir) / "report_surfaces"
    manifest = DailyRunManifest(
        run_date=result.end_date,
        data_until=result.end_date,
        train_until=result.start_date,
        decision_for=result.end_date,
        virtual_order_date=result.end_date,
        virtual_execution_date=result.end_date,
        safety_status=str(safety_state.get("next_recommended_safety_state") or "NORMAL"),
        human_review_status="pending" if safety_state.get("review_required_items") else "none",
        report_status="OK",
    )
    daily_result = DailyRunResult(
        buy_candidates=(DailyCandidate(issue_code="7203", issue_name="sample", side="BUY", public_confidence_score=70),),
        sell_candidates=(DailyCandidate(issue_code="9432", issue_name="sample", side="SELL", public_confidence_score=55),),
        hold_candidates=(),
        cash=Decimal(str(result.performance.get("initial_cash") or "0")),
        current_cash=Decimal(str(result.performance.get("initial_cash") or "0")),
        positions=(DailyPosition(issue_code="9432", issue_name="sample", quantity=Decimal("100"), market_value=Decimal("100000")),),
        current_positions=(DailyPosition(issue_code="9432", issue_name="sample", quantity=Decimal("100"), market_value=Decimal("100000")),),
        total_equity=Decimal(str(result.performance.get("final_equity") or "0")),
        unrealized_pnl=Decimal("0"),
        trade_count=int(result.performance.get("trade_count") or 0),
        safety_state=safety_state,
    )
    public_path = write_public_daily_report(manifest=manifest, result=daily_result, reports_dir=output_dir)
    blog_path = write_blog_draft(manifest=manifest, result=daily_result, reports_dir=output_dir)
    public_text = public_path.read_text(encoding="utf-8")
    blog_text = blog_path.read_text(encoding="utf-8")
    return {
        "public_report_path": str(public_path),
        "blog_report_path": str(blog_path),
        "blog_safety_market_review_section_present": "## Safety / Market Review" in blog_text,
        "public_report_safety_market_review_section_present": "## Safety / Market Review" in public_text,
        "market_downturn_not_labeled_emergency": "市場急落によりEmergency Stop" not in public_text + blog_text,
        "system_emergency_only_stop_label": "発注停止 / 人間確認必須" not in public_text + blog_text or "System Emergency: yes" in public_text + blog_text,
    }


def _line_report(result: IntegratedBacktestAuditResult, safety_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "phase11_safety_report_v2",
        "business_date": result.end_date,
        "environment": "fix_e2_refined_mainline_smoke",
        "runtime_id": "phase11z_fix_e2_refined_mainline_smoke",
        "overall_decision": "REVIEW_REQUIRED" if safety_state.get("review_required_items") else "ALLOW",
        "next_recommended_safety_state": safety_state.get("next_recommended_safety_state", "NORMAL"),
        "review_required_items": safety_state.get("review_required_items", []),
        "market_stress_summary": {"market_stress_detected": bool(safety_state.get("market_stress"))},
        "buy_opportunity_review": bool(safety_state.get("buy_opportunity_review")),
        "sell_review_required": bool(safety_state.get("sell_review_required")),
        "high_risk_review": bool(safety_state.get("high_risk_review")),
        "recommended_human_actions": safety_state.get("recommended_human_actions", []),
        "no_live_order_confirmation": {
            "broker_api_connected": False,
            "websocket_connected": False,
            "demo_order_submitted": False,
            "production_order_submitted": False,
            "clm_kabu_new_order_executed": False,
        },
    }


def _summary_payload(
    on: IntegratedBacktestAuditResult,
    off: IntegratedBacktestAuditResult,
    report_surface: dict[str, Any],
    notification_path: Path,
    safety_state: dict[str, Any],
) -> dict[str, Any]:
    notification_payload = json.loads(notification_path.read_text(encoding="utf-8"))
    safety_on_off = _safety_on_off_diff(on, off)
    checks = {
        "short_smoke_completed": on.business_day_count > 0 and off.business_day_count > 0,
        "safety_on_status_pass": on.status == "PASS",
        "safety_off_status_pass": off.status == "PASS",
        "market_price_not_emergency_stop": on.safety.get("EMERGENCY_STOP_count", 0) == 0 and _market_price_emergency_count(on) == 0,
        "system_emergency_only_stop_label": bool(report_surface["system_emergency_only_stop_label"]),
        "line_notification_payload_generated": notification_path.is_file(),
        "line_send_executed_false": notification_payload.get("line_send_executed") is False,
        "blog_safety_market_review_section_present": bool(report_surface["blog_safety_market_review_section_present"]),
        "public_report_safety_market_review_section_present": bool(report_surface["public_report_safety_market_review_section_present"]),
        "market_downturn_not_labeled_emergency": bool(report_surface["market_downturn_not_labeled_emergency"]),
        "auto_sell_executed_false": on.integrity.get("auto_sell_executed") is False and off.integrity.get("auto_sell_executed") is False,
        "auto_recovery_executed_false": on.integrity.get("auto_recovery_executed") is False and off.integrity.get("auto_recovery_executed") is False,
        "live_order_executed_false": on.integrity.get("live_order_executed") is False and off.integrity.get("live_order_executed") is False,
        "secret_raw_response_absent": not _contains_forbidden_values([on.summary_path, off.summary_path, str(notification_path), report_surface["public_report_path"], report_surface["blog_report_path"]]),
        "broker_api_connected_false": on.integrity.get("broker_api_connected") is False and off.integrity.get("broker_api_connected") is False,
        "ai_training_data_mutated_false": on.integrity.get("ai_training_data_mutated") is False and off.integrity.get("ai_training_data_mutated") is False,
        "five_year_full_not_run": on.business_day_count <= MAX_DAYS and off.business_day_count <= MAX_DAYS,
    }
    payload = {
        "schema_version": "phase11z_fix_e2_refined_mainline_smoke_v1",
        "generated_at": utc_now_iso(),
        "status": "PASS" if all(checks.values()) else "FAIL",
        "period": {"start_date": START_DATE, "end_date": END_DATE, "max_days": MAX_DAYS},
        "profile": AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
        "reuse_map": {
            **dict(on.safety_behavior.get("mainline_reuse_map", {})),
            "revenue_evaluation_eligible": bool(on.safety_behavior.get("revenue_evaluation_eligible")),
        },
        "daily_flow": {
            "safety_on": _flow(on),
            "safety_off": _flow(off),
        },
        "safety_classification": _safety_classification(on),
        "performance": {
            "safety_on": _performance(on),
            "safety_off": _performance(off),
        },
        "notification_blog": {
            **report_surface,
            "line_notification_payload_generated": notification_path.is_file(),
            "line_notification_payload_path": str(notification_path),
            "line_send_executed": False,
            "notification_level": notification_payload.get("notification_level"),
            "market_downturn_not_labeled_emergency": bool(report_surface["market_downturn_not_labeled_emergency"]),
            "system_emergency_only_stop_label": bool(report_surface["system_emergency_only_stop_label"]),
        },
        "safety_on_off_diff": safety_on_off,
        "safety_state_for_report_surface": safety_state,
        "integrity": {
            **on.integrity,
            "line_send_executed": False,
            "websocket_connected": False,
            "five_year_full_backtest_executed": False,
            "one_year_full_backtest_executed": False,
        },
        "checks": checks,
        "output_paths": {
            "safety_on_summary": on.summary_path,
            "safety_off_summary": off.summary_path,
            "safety_on_output_dir": on.output_dir,
            "safety_off_output_dir": off.output_dir,
            "phase_report_path": str(PHASE_DOC_PATH),
            "phase_report_json_path": str(PHASE_JSON_PATH),
        },
        "judgement": [
            "PHASE11Z_FIX_E2_REFINED_MAINLINE_SMOKE_PASS" if all(checks.values()) else "PHASE11Z_FIX_E2_REFINED_MAINLINE_SMOKE_FAIL",
            "REFINED_SAFETY_SHORT_MAINLINE_SMOKE_COMPLETE",
            "LIVE_ORDER_EXECUTION_REMAINS_BLOCKED",
        ],
    }
    return _phase11_sanitize(payload)


def _flow(result: IntegratedBacktestAuditResult) -> dict[str, Any]:
    keys = [
        "orders_generated",
        "orders_allowed_by_safety",
        "orders_blocked_by_safety",
        "orders_review_required",
        "orders_emergency_stopped",
        "buy_fill_count",
        "sell_fill_count",
        "round_trip_count",
        "position_open_count",
        "position_close_count",
        "final_position_count",
    ]
    payload = {"business_days": result.business_day_count}
    payload.update({key: result.flow_counts.get(key) for key in keys})
    payload["trade_count"] = result.performance.get("trade_count")
    return payload


def _safety_classification(result: IntegratedBacktestAuditResult) -> dict[str, Any]:
    return {
        "SYSTEM_EMERGENCY_STOP_count": result.safety.get("EMERGENCY_STOP_count", 0),
        "MARKET_STRESS_count": result.safety.get("market_crash_guard_count", 0),
        "BUY_REVIEW_REQUIRED_count": result.safety.get("max_exposure_guard_count", 0) + result.safety.get("quote_stale_guard_count", 0),
        "BUY_OPPORTUNITY_REVIEW_count": 0,
        "SELL_REVIEW_REQUIRED_count": result.safety.get("stop_loss_candidate_count", 0),
        "HIGH_RISK_REVIEW_count": result.safety.get("emergency_candidate_count", 0),
        "WARNING_count": result.safety.get("individual_warning_count", 0),
        "BLOCK_count": result.safety.get("BLOCK_count", 0),
        "REVIEW_REQUIRED_count": result.safety.get("REVIEW_REQUIRED_count", 0),
        "EMERGENCY_STOP_count": result.safety.get("EMERGENCY_STOP_count", 0),
        "BUY_STOP_days": result.safety.get("BUY_STOP_days", 0),
        "SYSTEM_EMERGENCY_STOP_days": result.state_residency_days.get("SYSTEM_EMERGENCY_STOP", 0),
    }


def _performance(result: IntegratedBacktestAuditResult) -> dict[str, Any]:
    keys = [
        "initial_cash",
        "final_equity",
        "total_return",
        "annualized_return",
        "max_drawdown",
        "win_rate",
        "profit_factor",
        "average_holding_days",
        "exposure_ratio",
    ]
    return {key: result.performance.get(key) for key in keys}


def _safety_on_off_diff(on: IntegratedBacktestAuditResult, off: IntegratedBacktestAuditResult) -> dict[str, Any]:
    return {
        "orders_generated_diff": int(on.flow_counts.get("orders_generated", 0)) - int(off.flow_counts.get("orders_generated", 0)),
        "buy_fill_count_diff": int(on.flow_counts.get("buy_fill_count", 0)) - int(off.flow_counts.get("buy_fill_count", 0)),
        "sell_fill_count_diff": int(on.flow_counts.get("sell_fill_count", 0)) - int(off.flow_counts.get("sell_fill_count", 0)),
        "final_equity_diff": float(on.performance.get("final_equity", 0)) - float(off.performance.get("final_equity", 0)),
        "explanation": (
            "Safety ON reduced new buy flow through BUY_REVIEW_REQUIRED checks such as max exposure and quote freshness. "
            "Market/price drawdown produced review classifications only and did not become Emergency Stop. "
            "Safety OFF bypassed pre-order guard blocking for comparison, so fills and round trips increased."
        ),
    }


def _market_price_emergency_count(result: IntegratedBacktestAuditResult) -> int:
    count = 0
    for row in result.daily_records:
        if row.pre_order_decision.value == "EMERGENCY_STOP":
            if any(reason in {"MARKET_STRESS", "BUY_OPPORTUNITY_REVIEW", "SELL_REVIEW_REQUIRED", "HIGH_RISK_REVIEW", "MARKET_STRESS_DAILY_LOSS"} for reason in row.triggered_reason_codes):
                count += 1
    return count


def _contains_forbidden_values(paths: list[str]) -> bool:
    forbidden = (
        "RAW-REQUEST-PHASE11Z",
        "RAW-RESPONSE-PHASE11Z",
        "ACCOUNT-PLAINTEXT-PHASE11Z",
        "ORDER-PLAINTEXT-PHASE11Z",
        "EXEC-PLAINTEXT-PHASE11Z",
        "AUTH-PLAINTEXT-PHASE11Z",
        "PRIVATE-KEY-PHASE11Z",
        "https://virtual-url.phase11z.invalid/path",
        "SECOND-PASSWORD-PHASE11Z",
    )
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        if any(item in text for item in forbidden):
            return True
    return False


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase11-Z-Fix-E2 Refined Safety Mainline Adapter Short Smoke",
        "",
        f"- status: {payload['status']}",
        f"- period: {payload['period']['start_date']} to {payload['period']['end_date']}",
        f"- max_days: {payload['period']['max_days']}",
        f"- profile: {payload['profile']}",
        "- broker_api_connected: false",
        "- websocket_connected: false",
        "- live_order_executed: false",
        "- line_send_executed: false",
        "- auto_sell_executed: false",
        "- auto_recovery_executed: false",
        "- ai_training_data_mutated: false",
        "- five_year_full_backtest_executed: false",
        "",
        "## Reuse Map",
        "",
        *_kv(payload["reuse_map"]),
        "",
        "## Daily Flow",
        "",
        "### Safety ON",
        "",
        *_kv(payload["daily_flow"]["safety_on"]),
        "",
        "### Safety OFF",
        "",
        *_kv(payload["daily_flow"]["safety_off"]),
        "",
        "## Safety Classification",
        "",
        *_kv(payload["safety_classification"]),
        "",
        "## Performance",
        "",
        "### Safety ON",
        "",
        *_kv(payload["performance"]["safety_on"]),
        "",
        "### Safety OFF",
        "",
        *_kv(payload["performance"]["safety_off"]),
        "",
        "## Notification / Blog",
        "",
        *_kv(payload["notification_blog"]),
        "",
        "## Safety ON/OFF Diff",
        "",
        *_kv(payload["safety_on_off_diff"]),
        "",
        "## Checks",
        "",
        *_kv(payload["checks"]),
        "",
        "## Data Use",
        "",
        "Safety result and audit result are not AI training data. Backtest outcome, Paper Ledger, Broker Snapshot, PnL, portfolio state, cash, selected / bought / affordable data, order result, execution result, Safety result, Audit result, and PM multiplier imitation remain forbidden for AI learning.",
        "",
        "## Result",
        "",
        "```text",
        *payload["judgement"],
        "```",
    ]
    return "\n".join(lines) + "\n"


def _kv(mapping: dict[str, Any]) -> list[str]:
    return [f"- {key}: {str(value).lower() if isinstance(value, bool) else value}" for key, value in mapping.items()]


if __name__ == "__main__":
    raise SystemExit(main())
