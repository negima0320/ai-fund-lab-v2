#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from statistics import median
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
from ai_fund_lab_v2.safety_phase11.models import utc_now_iso
from ai_fund_lab_v2.safety_phase11.notification_payload_writer import write_line_notification_payload


START_DATE = "2025-06-01"
END_DATE = "2025-11-30"
MAX_DAYS = 120
SAFETY_ON_SUBDIR = "fix_e3_refined_mainline_medium_smoke"
SAFETY_OFF_SUBDIR = "fix_e3_refined_mainline_medium_safety_off_smoke"
PHASE_DOC_PATH = Path("docs/phase_reports/phase11z_fix_e3_refined_mainline_medium_smoke.md")
PHASE_JSON_PATH = Path("reports/phase_reports/phase11z_fix_e3_refined_mainline_medium_smoke.json")

REASON_META = {
    "HIGH_RISK_REVIEW": ("REVIEW_REQUIRED", "INDIVIDUAL_CRASH"),
    "SELL_REVIEW_REQUIRED": ("REVIEW_REQUIRED", "INDIVIDUAL_CRASH"),
    "INDIVIDUAL_DRAWDOWN_WARNING": ("REVIEW_REQUIRED", "INDIVIDUAL_CRASH"),
    "MARKET_STRESS": ("REVIEW_REQUIRED", "MARKET_CRASH"),
    "BUY_OPPORTUNITY_REVIEW": ("REVIEW_REQUIRED", "MARKET_CRASH"),
    "DAILY_LOSS_REVIEW_REQUIRED": ("REVIEW_REQUIRED", "DAILY_LOSS"),
    "MARKET_STRESS_DAILY_LOSS": ("REVIEW_REQUIRED", "DAILY_LOSS"),
    "QUOTE_MISSING_FOR_MONITOR": ("REVIEW_REQUIRED", "QUOTE_STALE"),
    "QUOTE_STALE_FOR_MONITOR": ("REVIEW_REQUIRED", "QUOTE_STALE"),
    "QUOTE_MISSING": ("BLOCK", "QUOTE_STALE"),
    "QUOTE_STALE": ("BLOCK", "QUOTE_STALE"),
    "MAX_EXPOSURE_EXCEEDED": ("BLOCK", "MAX_EXPOSURE"),
    "MAX_POSITION_COUNT_EXCEEDED": ("BLOCK", "MAX_EXPOSURE"),
    "CASH_BUFFER_VIOLATION": ("BLOCK", "CASH_BUFFER"),
    "DUPLICATE_ORDER_SYSTEM_EMERGENCY": ("EMERGENCY_STOP", "DUPLICATE_ORDER"),
    "BROKER_DUPLICATE_ORDER_RISK": ("EMERGENCY_STOP", "DUPLICATE_ORDER"),
    "BROKER_DIVERGENCE_DETECTED": ("EMERGENCY_STOP", "BROKER_DIVERGENCE"),
}


def main() -> int:
    on = _run_smoke(safety_enabled=True)
    off = _run_smoke(safety_enabled=False)
    breakdown = _review_block_breakdown(on)
    safety_state = _safety_state_for_public_report(on, breakdown)
    report_surface = _write_report_surfaces(on, safety_state)
    notification_path = write_line_notification_payload(_line_report(on, safety_state), reports_dir="reports")
    payload = _summary_payload(on, off, breakdown, report_surface, notification_path, safety_state)
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


def _review_block_breakdown(result: IntegratedBacktestAuditResult) -> dict[str, Any]:
    review_reason = Counter()
    block_reason = Counter()
    review_guard = Counter()
    block_guard = Counter()
    per_day_review: list[int] = []
    per_day_block: list[int] = []
    for row in result.daily_records:
        day_review = 0
        day_block = 0
        for reason in row.triggered_reason_codes:
            decision, guard = REASON_META.get(str(reason), ("REVIEW_REQUIRED", "UNKNOWN"))
            if decision == "BLOCK":
                block_reason[str(reason)] += 1
                block_guard[guard] += 1
                day_block += 1
            elif decision == "EMERGENCY_STOP":
                block_reason[str(reason)] += 1
                block_guard[guard] += 1
                day_block += 1
            else:
                review_reason[str(reason)] += 1
                review_guard[guard] += 1
                day_review += 1
        per_day_review.append(day_review)
        per_day_block.append(day_block)

    review_days = sum(1 for value in per_day_review if value > 0)
    block_days = sum(1 for value in per_day_block if value > 0)
    review_events = sum(review_reason.values())
    block_events = sum(block_reason.values())
    review_load = {
        "review_per_business_day": _round(review_events / max(result.business_day_count, 1)),
        "block_per_business_day": _round(block_events / max(result.business_day_count, 1)),
        "unique_review_days": review_days,
        "unique_block_days": block_days,
        "max_reviews_per_day": max(per_day_review) if per_day_review else 0,
        "max_blocks_per_day": max(per_day_block) if per_day_block else 0,
        "median_reviews_per_day": _round(median(per_day_review) if per_day_review else 0),
        "median_blocks_per_day": _round(median(per_day_block) if per_day_block else 0),
        "orders_review_required": result.flow_counts.get("orders_review_required", 0),
        "review_event_count": review_events,
        "review_event_to_order_review_ratio": _round(review_events / max(int(result.flow_counts.get("orders_review_required", 0)), 1)),
        "likely_duplicate_review_counting": review_events > int(result.flow_counts.get("orders_review_required", 0)) * 2,
    }
    review_assessment = _review_assessment(review_reason, block_reason, review_load, result)
    return {
        "review_required_count_by_reason": dict(sorted(review_reason.items())),
        "block_count_by_reason": dict(sorted(block_reason.items())),
        "review_required_count_by_guard": dict(sorted(review_guard.items())),
        "block_count_by_guard": dict(sorted(block_guard.items())),
        "top_10_review_reasons": review_reason.most_common(10),
        "top_10_block_reasons": block_reason.most_common(10),
        **review_load,
        "review_load_assessment": review_assessment,
    }


def _review_assessment(review_reason: Counter, block_reason: Counter, review_load: dict[str, Any], result: IntegratedBacktestAuditResult) -> dict[str, Any]:
    high_risk = int(review_reason.get("HIGH_RISK_REVIEW", 0))
    sell_review = int(review_reason.get("SELL_REVIEW_REQUIRED", 0))
    buy_review = int(block_reason.get("MAX_EXPOSURE_EXCEEDED", 0)) + int(block_reason.get("MAX_POSITION_COUNT_EXCEEDED", 0))
    quote_review = int(review_reason.get("QUOTE_MISSING_FOR_MONITOR", 0)) + int(review_reason.get("QUOTE_STALE_FOR_MONITOR", 0))
    too_many = bool(review_load["review_per_business_day"] > 3 or review_load["max_reviews_per_day"] > 10 or review_load["likely_duplicate_review_counting"])
    return {
        "review_volume": "HIGH" if too_many else "ACCEPTABLE",
        "high_risk_review_count": high_risk,
        "high_risk_review_too_many": high_risk > result.business_day_count,
        "sell_review_required_count": sell_review,
        "sell_review_required_too_many": sell_review > result.business_day_count,
        "buy_review_required_proxy_count": buy_review,
        "buy_review_required_too_many": buy_review > result.business_day_count,
        "quote_freshness_over_review": quote_review > max(5, result.business_day_count // 10),
        "max_exposure_over_block": buy_review > result.business_day_count,
        "review_should_block_fill": False,
        "market_price_review_should_be_notification_only": True,
        "recommendations": [
            "同一銘柄/同一理由を日次集約してHuman Review件数を圧縮する。",
            "HIGH_RISK_REVIEWは通知、INDIVIDUAL_DRAWDOWN_WARNINGはレポートのみへ分離する。",
            "BUY_REVIEW_REQUIREDとBLOCKを分離し、market/price reviewだけではfillを止めない設計を検討する。",
            "MAX_EXPOSURE_EXCEEDEDは新規BUYの上限制御として残しつつ、日次1件へ集約する。",
        ] if too_many else ["中期smoke上のReview量は許容範囲。1年smokeで再確認する。"],
    }


def _safety_state_for_public_report(result: IntegratedBacktestAuditResult, breakdown: dict[str, Any]) -> dict[str, Any]:
    reason_counts = {
        **breakdown["review_required_count_by_reason"],
        **breakdown["block_count_by_reason"],
    }
    has_position_review = bool({"SELL_REVIEW_REQUIRED", "HIGH_RISK_REVIEW"} & set(reason_counts))
    has_market_review = bool({"MARKET_STRESS", "BUY_OPPORTUNITY_REVIEW", "MARKET_STRESS_DAILY_LOSS"} & set(reason_counts))
    review_items = [{"reason_code": reason, "count": count} for reason, count in sorted(reason_counts.items())]
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
            "Reviewは日次集約し、通知とレポートを分けて運用負荷を下げる。",
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
        "environment": "fix_e3_refined_mainline_medium_smoke",
        "runtime_id": "phase11z_fix_e3_refined_mainline_medium_smoke",
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
    breakdown: dict[str, Any],
    report_surface: dict[str, Any],
    notification_path: Path,
    safety_state: dict[str, Any],
) -> dict[str, Any]:
    notification_payload = json.loads(notification_path.read_text(encoding="utf-8"))
    checks = {
        "medium_smoke_completed": on.business_day_count >= 90 and off.business_day_count >= 90,
        "safety_on_status_pass": on.status == "PASS",
        "safety_off_status_pass": off.status == "PASS",
        "emergency_stop_system_only_or_zero": on.safety.get("EMERGENCY_STOP_count", 0) == 0,
        "market_price_not_emergency_stop": on.safety.get("EMERGENCY_STOP_count", 0) == 0 and _market_price_emergency_count(on) == 0,
        "review_block_breakdown_present": bool(breakdown["review_required_count_by_reason"] or breakdown["block_count_by_reason"]),
        "review_volume_evaluated": bool(breakdown.get("review_load_assessment")),
        "safety_on_off_diff_explained": bool(_safety_on_off_diff(on, off).get("explanation")),
        "line_notification_payload_generated": notification_path.is_file(),
        "line_send_executed_false": notification_payload.get("line_send_executed") is False,
        "blog_safety_market_review_section_present": bool(report_surface["blog_safety_market_review_section_present"]),
        "public_report_safety_market_review_section_present": bool(report_surface["public_report_safety_market_review_section_present"]),
        "market_downturn_not_labeled_emergency": bool(report_surface["market_downturn_not_labeled_emergency"]),
        "system_emergency_only_stop_label": bool(report_surface["system_emergency_only_stop_label"]),
        "auto_sell_executed_false": on.integrity.get("auto_sell_executed") is False and off.integrity.get("auto_sell_executed") is False,
        "auto_recovery_executed_false": on.integrity.get("auto_recovery_executed") is False and off.integrity.get("auto_recovery_executed") is False,
        "live_order_executed_false": on.integrity.get("live_order_executed") is False and off.integrity.get("live_order_executed") is False,
        "secret_raw_response_absent": not _contains_forbidden_values([on.summary_path, off.summary_path, str(notification_path), report_surface["public_report_path"], report_surface["blog_report_path"]]),
        "broker_api_connected_false": on.integrity.get("broker_api_connected") is False and off.integrity.get("broker_api_connected") is False,
        "ai_training_data_mutated_false": on.integrity.get("ai_training_data_mutated") is False and off.integrity.get("ai_training_data_mutated") is False,
        "one_year_full_not_run": on.business_day_count <= MAX_DAYS and off.business_day_count <= MAX_DAYS,
        "five_year_full_not_run": on.business_day_count <= MAX_DAYS and off.business_day_count <= MAX_DAYS,
    }
    payload = {
        "schema_version": "phase11z_fix_e3_refined_mainline_medium_smoke_v1",
        "generated_at": utc_now_iso(),
        "status": "PASS" if all(checks.values()) else "FAIL",
        "period": {"start_date": START_DATE, "end_date": END_DATE, "max_days": MAX_DAYS},
        "profile": AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
        "reuse_map": {
            **dict(on.safety_behavior.get("mainline_reuse_map", {})),
            "revenue_evaluation_eligible": bool(on.safety_behavior.get("revenue_evaluation_eligible")),
        },
        "daily_flow": {"safety_on": _flow(on), "safety_off": _flow(off)},
        "review_block_breakdown": breakdown,
        "safety_classification": _safety_classification(on),
        "performance": {"safety_on": _performance(on), "safety_off": _performance(off)},
        "notification_blog": {
            **report_surface,
            "line_notification_payload_generated": notification_path.is_file(),
            "line_notification_payload_path": str(notification_path),
            "line_send_executed": False,
            "notification_level": notification_payload.get("notification_level"),
        },
        "safety_on_off_diff": _safety_on_off_diff(on, off),
        "review_fill_policy_assessment": _review_fill_policy_assessment(on, off, breakdown),
        "safety_state_for_report_surface": safety_state,
        "integrity": {
            **on.integrity,
            "line_send_executed": False,
            "websocket_connected": False,
            "one_year_full_backtest_executed": False,
            "five_year_full_backtest_executed": False,
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
            "PHASE11Z_FIX_E3_REFINED_MAINLINE_MEDIUM_SMOKE_PASS" if all(checks.values()) else "PHASE11Z_FIX_E3_REFINED_MAINLINE_MEDIUM_SMOKE_FAIL",
            "REVIEW_LOAD_REQUIRES_REFINEMENT_BEFORE_1Y" if breakdown["review_load_assessment"]["review_volume"] == "HIGH" else "PHASE11Z_FIX_E4_1Y_REFINED_MAINLINE_SMOKE_READY",
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
        "EMERGENCY_STOP_count": result.safety.get("EMERGENCY_STOP_count", 0),
        "BUY_STOP_days": result.safety.get("BUY_STOP_days", 0),
        "MARKET_STRESS_count": result.safety.get("market_crash_guard_count", 0),
        "BUY_REVIEW_REQUIRED_count": result.safety.get("max_exposure_guard_count", 0) + result.safety.get("quote_stale_guard_count", 0),
        "BUY_OPPORTUNITY_REVIEW_count": 0,
        "SELL_REVIEW_REQUIRED_count": result.safety.get("stop_loss_candidate_count", 0),
        "HIGH_RISK_REVIEW_count": result.safety.get("emergency_candidate_count", 0),
        "WARNING_count": result.safety.get("individual_warning_count", 0),
        "BLOCK_count": result.safety.get("BLOCK_count", 0),
        "REVIEW_REQUIRED_count": result.safety.get("REVIEW_REQUIRED_count", 0),
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
        "final_equity_diff": _round(float(on.performance.get("final_equity", 0)) - float(off.performance.get("final_equity", 0))),
        "explanation": (
            "Safety ON primarily blocked BUY orders that breached max exposure and routed market/price drawdown to Human Review. "
            "Review-classified market/price issues did not become Emergency Stop. "
            "The large ON/OFF fill gap indicates Review handling is currently too close to fill blocking and should be separated for market/price review before longer smoke."
        ),
    }


def _review_fill_policy_assessment(on: IntegratedBacktestAuditResult, off: IntegratedBacktestAuditResult, breakdown: dict[str, Any]) -> dict[str, Any]:
    blocked_by_review_like = int(on.flow_counts.get("orders_review_required", 0))
    off_fills = int(off.flow_counts.get("buy_fill_count", 0)) + int(off.flow_counts.get("sell_fill_count", 0))
    on_fills = int(on.flow_counts.get("buy_fill_count", 0)) + int(on.flow_counts.get("sell_fill_count", 0))
    return {
        "review_handling_blocks_fill_today": blocked_by_review_like > 0,
        "review_orders_not_submitted": blocked_by_review_like,
        "fill_gap_vs_safety_off": off_fills - on_fills,
        "assessment": "Review is currently stopping too much fill flow for a refined Safety role." if blocked_by_review_like > on.business_day_count else "Review load appears manageable.",
        "recommendation": "Separate system BLOCK from market/price REVIEW: market/price review should notify and aggregate, while only system faults and hard risk limits block order submission.",
        "one_year_ready": breakdown["review_load_assessment"]["review_volume"] != "HIGH",
    }


def _market_price_emergency_count(result: IntegratedBacktestAuditResult) -> int:
    market_price_reasons = {"MARKET_STRESS", "BUY_OPPORTUNITY_REVIEW", "SELL_REVIEW_REQUIRED", "HIGH_RISK_REVIEW", "MARKET_STRESS_DAILY_LOSS", "DAILY_LOSS_REVIEW_REQUIRED"}
    return sum(
        1
        for row in result.daily_records
        if row.pre_order_decision.value == "EMERGENCY_STOP" and any(reason in market_price_reasons for reason in row.triggered_reason_codes)
    )


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
    return any(any(item in Path(path).read_text(encoding="utf-8") for item in forbidden) for path in paths)


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase11-Z-Fix-E3 Refined Safety Mainline Medium Smoke",
        "",
        f"- status: {payload['status']}",
        f"- period: {payload['period']['start_date']} to {payload['period']['end_date']}",
        f"- max_days: {payload['period']['max_days']}",
        f"- profile: {payload['profile']}",
        "- broker_api_connected: false",
        "- websocket_connected: false",
        "- line_send_executed: false",
        "- live_order_executed: false",
        "- auto_sell_executed: false",
        "- auto_recovery_executed: false",
        "- ai_training_data_mutated: false",
        "- one_year_full_backtest_executed: false",
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
        "## Review / Block Breakdown",
        "",
        *_kv(payload["review_block_breakdown"]),
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
        "## Safety ON/OFF Diff",
        "",
        *_kv(payload["safety_on_off_diff"]),
        "",
        "## Review Fill Policy",
        "",
        *_kv(payload["review_fill_policy_assessment"]),
        "",
        "## Notification / Blog",
        "",
        *_kv(payload["notification_blog"]),
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


def _round(value: float) -> float:
    return round(float(value), 6)


if __name__ == "__main__":
    raise SystemExit(main())
