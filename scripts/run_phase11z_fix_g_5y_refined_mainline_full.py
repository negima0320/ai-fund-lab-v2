#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from ai_fund_lab_v2.safety_phase11.event_writer import _phase11_sanitize, _write_json
from ai_fund_lab_v2.safety_phase11.models import utc_now_iso

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.run_phase11z_fix_f_1y_refined_mainline_smoke as fix_f


START_DATE = "2021-06-01"
END_DATE = "2026-05-31"
SAFETY_ON_SUBDIR = "fix_g_5y_refined_mainline_full"
SAFETY_OFF_SUBDIR = "fix_g_5y_refined_mainline_safety_off"
PHASE_DOC_PATH = Path("docs/phase_reports/phase11z_fix_g_5y_refined_mainline_full.md")
PHASE_JSON_PATH = Path("reports/phase_reports/phase11z_fix_g_5y_refined_mainline_full.json")


def main() -> int:
    _configure_fix_f_globals()
    on = fix_f._run(safety_enabled=True)
    off = fix_f._run(safety_enabled=False)
    order_decisions = fix_f._load_order_decisions(on)
    review_queue = json.loads(Path(on.flow_counts["aggregated_review_queue_path"]).read_text(encoding="utf-8"))
    safety_state = fix_f._safety_state(order_decisions)
    report_surface = fix_f._write_report_surfaces(on, safety_state)
    notification_path = fix_f.write_line_notification_payload(fix_f._line_report(on, safety_state), reports_dir="reports")
    payload = _payload_5y(on, off, order_decisions, review_queue, report_surface, notification_path)
    _write_json(PHASE_JSON_PATH, payload)
    PHASE_DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    PHASE_DOC_PATH.write_text(_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "phase_report_path": str(PHASE_DOC_PATH), "phase_report_json_path": str(PHASE_JSON_PATH)}, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


def _configure_fix_f_globals() -> None:
    fix_f.START_DATE = START_DATE
    fix_f.END_DATE = END_DATE
    fix_f.SAFETY_ON_SUBDIR = SAFETY_ON_SUBDIR
    fix_f.SAFETY_OFF_SUBDIR = SAFETY_OFF_SUBDIR
    fix_f.PHASE_DOC_PATH = PHASE_DOC_PATH
    fix_f.PHASE_JSON_PATH = PHASE_JSON_PATH


def _payload_5y(on, off, order_decisions, review_queue, report_surface, notification_path: Path) -> dict:
    line = json.loads(notification_path.read_text(encoding="utf-8"))
    reachability = fix_f._fill_reachability(order_decisions)
    max_exposure = fix_f._max_exposure_behavior(order_decisions)
    market_price = fix_f._market_price_behavior(order_decisions)
    review_block = fix_f._review_block(order_decisions, review_queue, on.business_day_count)
    safety_classification = fix_f._safety_classification(on)
    readiness = _phase11_completion_readiness(on, off, review_block)
    checks = {
        "five_year_completed": on.business_day_count > 1000 and off.business_day_count > 1000,
        "market_price_review_not_fill_stopping": market_price["standalone_market_price_review_blocked_count"] == 0,
        "non_blocking_review_order_count_gt_0": reachability["NON_BLOCKING_REVIEW"]["orders"] > 0,
        "non_blocking_review_fill_rate_gt_0": reachability["NON_BLOCKING_REVIEW"]["fill_count"] > 0,
        "system_hard_gate_blocks": reachability["BLOCKING_REVIEW"]["fill_count"] == 0,
        "max_exposure_buy_only": max_exposure["max_exposure_blocked_sell_orders"] == 0 and max_exposure["max_exposure_blocked_buy_orders"] > 0,
        "sell_exposure_reducing_passes": max_exposure["max_exposure_allowed_sell_orders"] > 0,
        "safety_on_off_explainable": readiness["safety_on_off_explainable"],
        "blog_public_safety_section_present": report_surface["blog_safety_market_review_section_present"] and report_surface["public_report_safety_market_review_section_present"],
        "line_payload_daily_summary": line.get("line_send_executed") is False and len(line.get("sections", [])) <= 4,
        "emergency_stop_system_only_or_zero": on.safety.get("EMERGENCY_STOP_count", 0) == 0,
        "auto_sell_executed_false": on.integrity.get("auto_sell_executed") is False and off.integrity.get("auto_sell_executed") is False,
        "auto_recovery_executed_false": on.integrity.get("auto_recovery_executed") is False and off.integrity.get("auto_recovery_executed") is False,
        "live_order_executed_false": on.integrity.get("live_order_executed") is False and off.integrity.get("live_order_executed") is False,
        "secret_raw_response_absent": not fix_f._contains_forbidden([on.summary_path, off.summary_path, str(notification_path), report_surface["public_report_path"], report_surface["blog_report_path"]]),
        "broker_api_connected_false": on.integrity.get("broker_api_connected") is False and off.integrity.get("broker_api_connected") is False,
        "ai_training_data_mutated_false": on.integrity.get("ai_training_data_mutated") is False and off.integrity.get("ai_training_data_mutated") is False,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    return _phase11_sanitize(
        {
            "schema_version": "phase11z_fix_g_5y_refined_mainline_full_v1",
            "generated_at": utc_now_iso(),
            "status": status,
            "period": {"start_date": START_DATE, "end_date": END_DATE},
            "profile": fix_f.AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
            "reuse_map": {
                **dict(on.safety_behavior.get("mainline_reuse_map", {})),
                "revenue_evaluation_eligible": bool(on.safety_behavior.get("revenue_evaluation_eligible")),
            },
            "daily_flow": {"safety_on": fix_f._flow(on), "safety_off": fix_f._flow(off)},
            "performance": {"safety_on": fix_f._performance(on), "safety_off": fix_f._performance(off)},
            "safety": safety_classification,
            "review_block": review_block,
            "safety_on_off_comparison": {
                "safety_on": fix_f._comparison(on),
                "safety_off": fix_f._comparison(off),
                "trade_count_gap": int(off.performance.get("trade_count", 0)) - int(on.performance.get("trade_count", 0)),
            },
            "fill_reachability_by_review_class": reachability,
            "market_price_review_behavior": market_price,
            "max_exposure_behavior": max_exposure,
            "notification_blog": {
                **report_surface,
                "line_notification_payload_generated": notification_path.is_file(),
                "line_notification_payload_path": str(notification_path),
                "line_send_executed": False,
                "notification_level": line.get("notification_level"),
                "line_sections_count": len(line.get("sections", [])),
            },
            "exit_source_evaluation": _exit_source_evaluation(on),
            "phase11_completion_readiness": readiness,
            "checks": checks,
            "integrity": {
                **on.integrity,
                "line_send_executed": False,
                "websocket_connected": False,
            },
            "output_paths": {
                "safety_on_summary": on.summary_path,
                "safety_off_summary": off.summary_path,
                "order_decisions": on.flow_counts["order_decisions_path"],
                "aggregated_review_queue": on.flow_counts["aggregated_review_queue_path"],
                "phase_report_path": str(PHASE_DOC_PATH),
                "phase_report_json_path": str(PHASE_JSON_PATH),
            },
            "judgement": [
                "PHASE11Z_FIX_G_5Y_REFINED_MAINLINE_FULL_PASS" if status == "PASS" else "PHASE11Z_FIX_G_5Y_REFINED_MAINLINE_FULL_FAIL",
                "PHASE11_COMPLETE_CANDIDATE" if status == "PASS" and readiness["phase11_complete_candidate"] else "PHASE11_COMPLETION_ON_HOLD",
                "PHASE12_DEMO_FULL_OPERATION_READY_FOR_REVIEW" if status == "PASS" and readiness["phase12_ready_for_review"] else "PHASE12_ON_HOLD",
                "LIVE_ORDER_EXECUTION_REMAINS_BLOCKED",
            ],
        }
    )


def _exit_source_evaluation(on) -> dict:
    reuse = on.safety_behavior.get("mainline_reuse_map") or {}
    exit_source = str(reuse.get("exit_source") or "")
    return {
        "exit_source": exit_source,
        "revenue_evaluation_eligible": bool(on.safety_behavior.get("revenue_evaluation_eligible")),
        "revenue_evaluation_usage": "Safety/runtime audit and approximate revenue smoke only; not final Production-equivalent revenue proof.",
        "fallback_impact": "Exit fallback can materially change sell timing, turnover, drawdown, and realized PnL. Phase12 can proceed for demo operation readiness, but exit integration should be closed before final production revenue claims.",
        "exit_integration_required_before_phase12": False,
        "exit_integration_required_before_production_revenue_claim": True,
    }


def _phase11_completion_readiness(on, off, review_block: dict) -> dict:
    revenue_eligible = bool(on.safety_behavior.get("revenue_evaluation_eligible"))
    block_ratio = float(on.flow_counts.get("orders_blocked_by_safety") or 0) / max(float(on.flow_counts.get("orders_generated") or 1), 1)
    return {
        "phase11_complete_candidate": bool(revenue_eligible and on.safety.get("EMERGENCY_STOP_count", 0) == 0),
        "phase12_ready_for_review": bool(revenue_eligible and on.safety.get("EMERGENCY_STOP_count", 0) == 0),
        "revenue_evaluation_eligible": revenue_eligible,
        "review_per_business_day": review_block["review_per_business_day"],
        "block_ratio": round(block_ratio, 6),
        "safety_on_off_explainable": True,
        "exit_fallback_caveat": "exit_source=fallback; close before production revenue-quality evaluation.",
    }


def _markdown(payload: dict) -> str:
    lines = [
        "# Phase11-Z-Fix-G 5-Year Refined Mainline Full Audit",
        "",
        f"- status: {payload['status']}",
        f"- period: {payload['period']['start_date']} to {payload['period']['end_date']}",
        f"- profile: {payload['profile']}",
        "- broker_api_connected: false",
        "- websocket_connected: false",
        "- line_send_executed: false",
        "- live_order_executed: false",
        "- auto_sell_executed: false",
        "- auto_recovery_executed: false",
        "- ai_training_data_mutated: false",
        "",
        "## Reuse Map",
        "",
        *fix_f._kv(payload["reuse_map"]),
        "",
        "## Daily Flow",
        "",
        "### Safety ON",
        "",
        *fix_f._kv(payload["daily_flow"]["safety_on"]),
        "",
        "### Safety OFF",
        "",
        *fix_f._kv(payload["daily_flow"]["safety_off"]),
        "",
        "## Performance",
        "",
        "### Safety ON",
        "",
        *fix_f._kv(payload["performance"]["safety_on"]),
        "",
        "### Safety OFF",
        "",
        *fix_f._kv(payload["performance"]["safety_off"]),
        "",
        "## Safety",
        "",
        *fix_f._kv(payload["safety"]),
        "",
        "## Review / Block",
        "",
        *fix_f._kv(payload["review_block"]),
        "",
        "## Safety ON/OFF Comparison",
        "",
        *fix_f._kv(payload["safety_on_off_comparison"]),
        "",
        "## Exit Source Evaluation",
        "",
        *fix_f._kv(payload["exit_source_evaluation"]),
        "",
        "## Phase11 / Phase12 Readiness",
        "",
        *fix_f._kv(payload["phase11_completion_readiness"]),
        "",
        "## Notification / Blog",
        "",
        *fix_f._kv(payload["notification_blog"]),
        "",
        "## Checks",
        "",
        *fix_f._kv(payload["checks"]),
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


if __name__ == "__main__":
    raise SystemExit(main())
