#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
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
from ai_fund_lab_v2.safety_phase11.models import SafetyReviewClass, utc_now_iso
from ai_fund_lab_v2.safety_phase11.notification_payload_writer import write_line_notification_payload


START_DATE = "2025-06-01"
END_DATE = "2025-11-30"
MAX_DAYS = 120
SAFETY_ON_SUBDIR = "refine_d1_non_blocking_review_medium_smoke"
SAFETY_OFF_SUBDIR = "refine_d1_non_blocking_review_medium_safety_off_smoke"
PHASE_DOC_PATH = Path("docs/phase_reports/phase11_safety_refine_d1_non_blocking_review_policy.md")
PHASE_JSON_PATH = Path("reports/phase_reports/phase11_safety_refine_d1_non_blocking_review_policy.json")
MARKET_PRICE_REASONS = {
    "HIGH_RISK_REVIEW",
    "SELL_REVIEW_REQUIRED",
    "BUY_REVIEW_REQUIRED",
    "BUY_OPPORTUNITY_REVIEW",
    "MARKET_STRESS",
    "INDIVIDUAL_DRAWDOWN_WARNING",
    "DAILY_LOSS_REVIEW_REQUIRED",
    "MARKET_STRESS_DAILY_LOSS",
}


def main() -> int:
    on = _run(safety_enabled=True)
    off = _run(safety_enabled=False)
    order_decisions = _load_order_decisions(on)
    review_queue = json.loads(Path(on.flow_counts["aggregated_review_queue_path"]).read_text(encoding="utf-8"))
    safety_state = _safety_state(order_decisions)
    report_surface = _write_report_surfaces(on, safety_state)
    notification_path = write_line_notification_payload(_line_report(on, safety_state), reports_dir="reports")
    payload = _payload(on, off, order_decisions, review_queue, report_surface, notification_path, safety_state)
    _write_json(PHASE_JSON_PATH, payload)
    PHASE_DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    PHASE_DOC_PATH.write_text(_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "phase_report_path": str(PHASE_DOC_PATH), "phase_report_json_path": str(PHASE_JSON_PATH)}, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


def _run(*, safety_enabled: bool) -> IntegratedBacktestAuditResult:
    cfg = smoke_1y_config(reports_dir="reports")
    return run_integrated_backtest_audit(
        replace(
            cfg,
            period_id=SAFETY_ON_SUBDIR if safety_enabled else SAFETY_OFF_SUBDIR,
            start_date=START_DATE,
            end_date=END_DATE,
            output_subdir=SAFETY_ON_SUBDIR if safety_enabled else SAFETY_OFF_SUBDIR,
            max_days=MAX_DAYS,
            audit_profile=AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
            safety_enabled=safety_enabled,
        )
    )


def _load_order_decisions(result: IntegratedBacktestAuditResult) -> list[dict[str, Any]]:
    return json.loads(Path(result.flow_counts["order_decisions_path"]).read_text(encoding="utf-8"))["order_decisions"]


def _safety_state(order_decisions: list[dict[str, Any]]) -> dict[str, Any]:
    reason_counts = Counter()
    for item in order_decisions:
        reason_counts.update(item.get("non_blocking_review_reason_codes") or [])
        reason_counts.update(item.get("blocking_reason_codes") or [])
    return {
        "next_recommended_safety_state": "WARNING" if reason_counts else "NORMAL",
        "market_stress": any(reason in reason_counts for reason in {"MARKET_STRESS", "BUY_OPPORTUNITY_REVIEW", "MARKET_STRESS_DAILY_LOSS"}),
        "buy_opportunity_review": "BUY_OPPORTUNITY_REVIEW" in reason_counts,
        "position_review": any(reason in reason_counts for reason in {"SELL_REVIEW_REQUIRED", "HIGH_RISK_REVIEW", "INDIVIDUAL_DRAWDOWN_WARNING"}),
        "sell_review_required": "SELL_REVIEW_REQUIRED" in reason_counts,
        "high_risk_review": "HIGH_RISK_REVIEW" in reason_counts,
        "review_required_items": [{"reason_code": reason, "count": count} for reason, count in sorted(reason_counts.items())],
        "recommended_human_actions": [
            "Market/price review is notification-only unless a system or hard risk gate is present.",
            "Review aggregated daily position changes before manual action.",
            "System Emergency only remains order-stop semantics.",
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
        cash=Decimal(str(result.performance.get("initial_cash") or "0")),
        current_cash=Decimal(str(result.performance.get("initial_cash") or "0")),
        positions=(DailyPosition(issue_code="9432", issue_name="sample", quantity=Decimal("100"), market_value=Decimal("100000")),),
        current_positions=(DailyPosition(issue_code="9432", issue_name="sample", quantity=Decimal("100"), market_value=Decimal("100000")),),
        total_equity=Decimal(str(result.performance.get("final_equity") or "0")),
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
        "environment": "phase11_safety_refine_d1",
        "runtime_id": "phase11_safety_refine_d1_non_blocking_review_policy",
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


def _payload(
    on: IntegratedBacktestAuditResult,
    off: IntegratedBacktestAuditResult,
    order_decisions: list[dict[str, Any]],
    review_queue: dict[str, Any],
    report_surface: dict[str, Any],
    notification_path: Path,
    safety_state: dict[str, Any],
) -> dict[str, Any]:
    line = json.loads(notification_path.read_text(encoding="utf-8"))
    reachability = _fill_reachability(order_decisions)
    max_exposure = _max_exposure_behavior(order_decisions)
    market_price = _market_price_behavior(order_decisions)
    checks = {
        "medium_smoke_completed": on.business_day_count == MAX_DAYS and off.business_day_count == MAX_DAYS,
        "market_price_review_not_fill_stopping": market_price["standalone_market_price_review_blocked_count"] == 0,
        "non_blocking_review_reaches_fill": reachability["NON_BLOCKING_REVIEW"]["fill_count"] > 0,
        "system_hard_gate_blocks": reachability["BLOCKING_REVIEW"]["fill_count"] == 0,
        "max_exposure_buy_only": max_exposure["max_exposure_blocked_sell_orders"] == 0 and max_exposure["max_exposure_blocked_buy_orders"] > 0,
        "sell_exposure_reducing_passes": max_exposure["max_exposure_allowed_sell_orders"] > 0,
        "aggregated_review_queue_present": review_queue["aggregated_review_item_count"] > 0,
        "review_compression_ratio_present": review_queue["review_compression_ratio"] >= 1,
        "line_payload_daily_summary": line.get("line_send_executed") is False and len(line.get("sections", [])) <= 4,
        "blog_public_safety_section_present": report_surface["blog_safety_market_review_section_present"] and report_surface["public_report_safety_market_review_section_present"],
        "emergency_stop_system_only_or_zero": on.safety.get("EMERGENCY_STOP_count", 0) == 0,
        "auto_sell_executed_false": on.integrity.get("auto_sell_executed") is False and off.integrity.get("auto_sell_executed") is False,
        "auto_recovery_executed_false": on.integrity.get("auto_recovery_executed") is False and off.integrity.get("auto_recovery_executed") is False,
        "live_order_executed_false": on.integrity.get("live_order_executed") is False and off.integrity.get("live_order_executed") is False,
        "secret_raw_response_absent": not _contains_forbidden([on.summary_path, off.summary_path, str(notification_path), report_surface["public_report_path"], report_surface["blog_report_path"]]),
        "broker_api_connected_false": on.integrity.get("broker_api_connected") is False and off.integrity.get("broker_api_connected") is False,
        "ai_training_data_mutated_false": on.integrity.get("ai_training_data_mutated") is False and off.integrity.get("ai_training_data_mutated") is False,
        "one_year_full_not_run": on.business_day_count <= MAX_DAYS and off.business_day_count <= MAX_DAYS,
        "five_year_full_not_run": on.business_day_count <= MAX_DAYS and off.business_day_count <= MAX_DAYS,
    }
    payload = {
        "schema_version": "phase11_safety_refine_d1_non_blocking_review_policy_v1",
        "generated_at": utc_now_iso(),
        "status": "PASS" if all(checks.values()) else "FAIL",
        "period": {"start_date": START_DATE, "end_date": END_DATE, "max_days": MAX_DAYS},
        "review_class_spec": {
            "BLOCKING_REVIEW": "System fault or hard risk gate; fill_allowed=false.",
            "NON_BLOCKING_REVIEW": "Market/price/position review; fill_allowed=true and human review/reporting remains.",
            "INFO_ONLY": "No human review required; fill_allowed=true.",
        },
        "daily_flow": {"safety_on": _flow(on), "safety_off": _flow(off)},
        "fill_reachability_by_review_class": reachability,
        "max_exposure_behavior": max_exposure,
        "market_price_review_behavior": market_price,
        "review_aggregation": {k: review_queue[k] for k in ["raw_review_occurrence_count", "aggregated_review_item_count", "review_compression_ratio", "blocking_review_count", "non_blocking_review_count", "info_only_count"]},
        "notification_blog": {
            **report_surface,
            "line_notification_payload_generated": notification_path.is_file(),
            "line_notification_payload_path": str(notification_path),
            "line_send_executed": False,
            "notification_level": line.get("notification_level"),
            "line_sections_count": len(line.get("sections", [])),
        },
        "safety_on_off_diff": {
            "trade_count_on": on.performance.get("trade_count"),
            "trade_count_off": off.performance.get("trade_count"),
            "trade_count_gap": int(off.performance.get("trade_count", 0)) - int(on.performance.get("trade_count", 0)),
            "final_equity_on": on.performance.get("final_equity"),
            "final_equity_off": off.performance.get("final_equity"),
        },
        "output_paths": {
            "safety_on_summary": on.summary_path,
            "safety_off_summary": off.summary_path,
            "order_decisions": on.flow_counts["order_decisions_path"],
            "aggregated_review_queue": on.flow_counts["aggregated_review_queue_path"],
            "phase_report_path": str(PHASE_DOC_PATH),
            "phase_report_json_path": str(PHASE_JSON_PATH),
        },
        "checks": checks,
        "integrity": {
            **on.integrity,
            "line_send_executed": False,
            "websocket_connected": False,
            "one_year_full_backtest_executed": False,
            "five_year_full_backtest_executed": False,
        },
        "judgement": [
            "PHASE11_SAFETY_REFINE_D1_NON_BLOCKING_REVIEW_POLICY_PASS" if all(checks.values()) else "PHASE11_SAFETY_REFINE_D1_NON_BLOCKING_REVIEW_POLICY_FAIL",
            "PHASE11_REFINED_1Y_MAINLINE_SMOKE_READY" if all(checks.values()) else "PHASE11_REFINED_1Y_MAINLINE_SMOKE_ON_HOLD",
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
        "non_blocking_review_order_count",
        "blocking_review_order_count",
        "human_review_required_order_count",
        "buy_fill_count",
        "sell_fill_count",
        "virtual_orders_submitted",
        "virtual_fills",
        "final_position_count",
    ]
    payload = {"business_days": result.business_day_count, "trade_count": result.performance.get("trade_count")}
    payload.update({key: result.flow_counts.get(key) for key in keys})
    return payload


def _fill_reachability(order_decisions: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for klass in SafetyReviewClass:
        rows = [item for item in order_decisions if item["review_class"] == klass.value]
        output[klass.value] = {
            "orders": len(rows),
            "fill_allowed_count": sum(1 for item in rows if item["fill_allowed"]),
            "submitted_count": sum(1 for item in rows if item["submitted_to_virtual_fill"]),
            "fill_count": sum(1 for item in rows if item["filled"]),
        }
    return output


def _market_price_behavior(order_decisions: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [item for item in order_decisions if set(item.get("non_blocking_review_reason_codes") or []).intersection(MARKET_PRICE_REASONS)]
    standalone = [item for item in rows if not item.get("blocking_reason_codes")]
    return {
        "market_price_review_order_count": len(rows),
        "market_price_review_fill_allowed_count": sum(1 for item in rows if item["fill_allowed"]),
        "market_price_review_filled_count": sum(1 for item in rows if item["filled"]),
        "market_price_review_blocked_count": sum(1 for item in rows if not item["fill_allowed"]),
        "standalone_market_price_review_order_count": len(standalone),
        "standalone_market_price_review_blocked_count": sum(1 for item in standalone if not item["fill_allowed"]),
        "market_price_with_hard_gate_block_count": sum(1 for item in rows if not item["fill_allowed"] and item.get("blocking_reason_codes")),
    }


def _max_exposure_behavior(order_decisions: list[dict[str, Any]]) -> dict[str, Any]:
    max_exposure = [item for item in order_decisions if "MAX_EXPOSURE_EXCEEDED" in item.get("blocking_reason_codes", [])]
    sell_orders = [item for item in order_decisions if item["side"] == "SELL"]
    return {
        "max_exposure_blocked_buy_orders": sum(1 for item in max_exposure if item["side"] == "BUY"),
        "max_exposure_blocked_sell_orders": sum(1 for item in max_exposure if item["side"] == "SELL"),
        "max_exposure_allowed_sell_orders": sum(1 for item in sell_orders if item["fill_allowed"]),
        "max_exposure_allowed_exposure_reducing_orders": sum(1 for item in sell_orders if item["fill_allowed"]),
    }


def _contains_forbidden(paths: list[str]) -> bool:
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
        "# Phase11-Safety-Refine-D1 Non-Blocking Review Policy",
        "",
        f"- status: {payload['status']}",
        f"- period: {payload['period']['start_date']} to {payload['period']['end_date']}",
        f"- max_days: {payload['period']['max_days']}",
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
        "## Review Class Spec",
        "",
        *_kv(payload["review_class_spec"]),
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
        "## Fill Reachability",
        "",
        *_kv(payload["fill_reachability_by_review_class"]),
        "",
        "## Market / Price Review",
        "",
        *_kv(payload["market_price_review_behavior"]),
        "",
        "## MAX Exposure",
        "",
        *_kv(payload["max_exposure_behavior"]),
        "",
        "## Review Aggregation",
        "",
        *_kv(payload["review_aggregation"]),
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
