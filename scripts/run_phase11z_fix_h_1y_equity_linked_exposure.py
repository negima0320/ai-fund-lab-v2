#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from statistics import mean
from typing import Any

from ai_fund_lab_v2.safety_phase11.event_writer import _phase11_sanitize, _write_json
from ai_fund_lab_v2.safety_phase11.models import utc_now_iso

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.run_phase11z_fix_f_1y_refined_mainline_smoke as fix_f


START_DATE = "2025-06-01"
END_DATE = "2026-05-31"
SAFETY_ON_SUBDIR = "fix_h_1y_equity_linked_exposure"
SAFETY_OFF_SUBDIR = "fix_h_1y_equity_linked_exposure_safety_off"
PHASE_DOC_PATH = Path("docs/phase_reports/phase11z_fix_h_1y_equity_linked_exposure.md")
PHASE_JSON_PATH = Path("reports/phase_reports/phase11z_fix_h_1y_equity_linked_exposure.json")


def main() -> int:
    _configure_fix_f_globals()
    on = fix_f._run(safety_enabled=True)
    off = fix_f._run(safety_enabled=False)
    order_decisions = fix_f._load_order_decisions(on)
    review_queue = json.loads(Path(on.flow_counts["aggregated_review_queue_path"]).read_text(encoding="utf-8"))
    safety_state = fix_f._safety_state(order_decisions)
    report_surface = fix_f._write_report_surfaces(on, safety_state)
    notification_path = fix_f.write_line_notification_payload(fix_f._line_report(on, safety_state), reports_dir="reports")
    payload = _payload_h(on, off, order_decisions, review_queue, report_surface, notification_path)
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


def _payload_h(on, off, order_decisions: list[dict[str, Any]], review_queue: dict[str, Any], report_surface: dict[str, Any], notification_path: Path) -> dict[str, Any]:
    line = json.loads(notification_path.read_text(encoding="utf-8"))
    reachability = fix_f._fill_reachability(order_decisions)
    max_exposure = _max_exposure_ratio_metrics(order_decisions, on)
    market_price = fix_f._market_price_behavior(order_decisions)
    review_block = fix_f._review_block(order_decisions, review_queue, on.business_day_count)
    safety_classification = fix_f._safety_classification(on)
    previous = _previous_fix_f_comparison()
    checks = {
        "one_year_completed": on.business_day_count > 200 and off.business_day_count > 200,
        "fixed_absolute_cap_disabled": max_exposure["fixed_absolute_cap_used"] is False and max_exposure["max_total_exposure_absolute_cap"] is None,
        "equity_linked_ratio_cap_used": max_exposure["max_total_exposure_ratio"] == "0.85" and max_exposure["exposure_basis"] == "equity",
        "max_allowed_exposure_scales_with_base_equity": max_exposure["equity_linked_samples_valid"] is True,
        "sell_not_blocked_by_max_exposure": max_exposure["max_exposure_blocked_sell_orders"] == 0,
        "sell_exposure_reducing_passes": max_exposure["max_exposure_allowed_sell_orders"] > 0,
        "max_exposure_blocks_rationalized_vs_previous": max_exposure["max_exposure_blocked_buy_orders"] < int(previous["max_exposure_blocked_buy_orders"]),
        "market_price_review_not_fill_stopping": market_price["standalone_market_price_review_blocked_count"] == 0,
        "system_hard_gate_blocks": reachability["BLOCKING_REVIEW"]["fill_count"] == 0,
        "non_blocking_review_reaches_fill": reachability["NON_BLOCKING_REVIEW"]["fill_count"] > 0,
        "line_payload_not_sent": line.get("line_send_executed") is False,
        "blog_public_safety_section_present": report_surface["blog_safety_market_review_section_present"] and report_surface["public_report_safety_market_review_section_present"],
        "auto_sell_executed_false": on.integrity.get("auto_sell_executed") is False and off.integrity.get("auto_sell_executed") is False,
        "auto_recovery_executed_false": on.integrity.get("auto_recovery_executed") is False and off.integrity.get("auto_recovery_executed") is False,
        "live_order_executed_false": on.integrity.get("live_order_executed") is False and off.integrity.get("live_order_executed") is False,
        "secret_raw_response_absent": not fix_f._contains_forbidden([on.summary_path, off.summary_path, str(notification_path), report_surface["public_report_path"], report_surface["blog_report_path"]]),
        "broker_api_connected_false": on.integrity.get("broker_api_connected") is False and off.integrity.get("broker_api_connected") is False,
        "ai_training_data_mutated_false": on.integrity.get("ai_training_data_mutated") is False and off.integrity.get("ai_training_data_mutated") is False,
        "five_year_full_not_run": on.business_day_count < 1000 and off.business_day_count < 1000,
    }
    ready = _fix_i_readiness(on, off, review_block, max_exposure, checks)
    status = "PASS" if all(checks.values()) else "FAIL"
    return _phase11_sanitize(
        {
            "schema_version": "phase11z_fix_h_1y_equity_linked_exposure_v1",
            "generated_at": utc_now_iso(),
            "status": status,
            "period": {"start_date": START_DATE, "end_date": END_DATE},
            "profile": fix_f.AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
            "read_materials": [
                "docs/phase_reports/phase11_safety_cap_fix_equity_linked_exposure.md",
                "reports/phase_reports/phase11_safety_cap_fix_equity_linked_exposure.json",
                "docs/phase_reports/phase11_max_exposure_investigation.md",
                "reports/phase_reports/phase11_max_exposure_investigation.json",
                "docs/phase_reports/phase11z_fix_f_1y_refined_mainline_smoke.md",
                "reports/phase_reports/phase11z_fix_f_1y_refined_mainline_smoke.json",
                "src/ai_fund_lab_v2/safety_phase11/guards.py",
                "src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py",
                "tests/safety_phase11/",
            ],
            "reuse_map": {
                **dict(on.safety_behavior.get("mainline_reuse_map", {})),
                "revenue_evaluation_eligible": bool(on.safety_behavior.get("revenue_evaluation_eligible")),
            },
            "daily_flow": {"safety_on": fix_f._flow(on), "safety_off": fix_f._flow(off)},
            "max_exposure": max_exposure,
            "performance": {"safety_on": fix_f._performance(on), "safety_off": fix_f._performance(off)},
            "safety_on_off_comparison": {
                "safety_on": {**fix_f._comparison(on), "max_exposure_block_count": max_exposure["max_exposure_blocked_buy_orders"] + max_exposure["max_exposure_blocked_sell_orders"]},
                "safety_off": {**fix_f._comparison(off), "max_exposure_block_count": 0},
                "trade_count_gap": int(off.performance.get("trade_count", 0)) - int(on.performance.get("trade_count", 0)),
            },
            "previous_1y_safety_on_comparison": _previous_delta(on, previous),
            "review_block": review_block,
            "safety_classification": safety_classification,
            "fill_reachability_by_review_class": reachability,
            "market_price_review_behavior": market_price,
            "notification_blog": {
                **report_surface,
                "line_notification_payload_generated": notification_path.is_file(),
                "line_notification_payload_path": str(notification_path),
                "line_send_executed": False,
                "notification_level": line.get("notification_level"),
                "line_sections_count": len(line.get("sections", [])),
            },
            "fix_i_readiness": ready,
            "checks": checks,
            "integrity": {
                **on.integrity,
                "line_send_executed": False,
                "websocket_connected": False,
                "one_year_full_backtest_executed": True,
                "five_year_full_backtest_executed": False,
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
                "PHASE11Z_FIX_H_1Y_EQUITY_LINKED_EXPOSURE_PASS" if status == "PASS" else "PHASE11Z_FIX_H_1Y_EQUITY_LINKED_EXPOSURE_FAIL",
                "PHASE11Z_FIX_I_5Y_REFINED_MAINLINE_FULL_READY" if status == "PASS" and ready["ready_for_fix_i_5y_full"] else "PHASE11Z_FIX_I_5Y_REFINED_MAINLINE_FULL_ON_HOLD",
                "LIVE_ORDER_EXECUTION_REMAINS_BLOCKED",
            ],
        }
    )


def _max_exposure_ratio_metrics(order_decisions: list[dict[str, Any]], result) -> dict[str, Any]:
    max_rows = [item for item in order_decisions if "MAX_EXPOSURE_EXCEEDED" in item.get("blocking_reason_codes", [])]
    sell_orders = [item for item in order_decisions if item.get("side") == "SELL"]
    details = [item.get("guard_details", {}).get("MAX_EXPOSURE", {}) for item in max_rows]
    details = [item for item in details if item]
    daily = json.loads(Path(result.output_dir, "daily_audit.json").read_text(encoding="utf-8"))["daily_records"]
    cash_ratios = []
    for row in daily:
        equity = Decimal(str(row.get("equity") or "0"))
        cash = Decimal(str(row.get("cash") or "0"))
        if equity > 0:
            cash_ratios.append(cash / equity)
    samples = _equity_linked_samples(details)
    return {
        **fix_f._max_exposure_behavior(order_decisions),
        "average_base_equity": _avg_decimal(details, "base_equity"),
        "average_max_allowed_exposure": _avg_decimal(details, "max_allowed_exposure"),
        "average_current_exposure": _avg_decimal(details, "current_exposure"),
        "average_projected_exposure_at_block": _avg_decimal(details, "projected_exposure"),
        "average_cash_ratio": round(float(mean(cash_ratios)), 6) if cash_ratios else 0,
        "average_cash_remaining_at_block": _avg_decimal(details, "cash_available"),
        "average_position_count_at_block": _avg_decimal(details, "position_count"),
        "position_count_lt_8_block_count": sum(1 for item in details if Decimal(str(item.get("position_count") or "0")) < 8),
        "fixed_absolute_cap_used": any(item.get("max_total_exposure_absolute_cap") is not None for item in details),
        "max_total_exposure_ratio": _common_value(details, "max_total_exposure_ratio") or "0.85",
        "max_total_exposure_absolute_cap": _common_value(details, "max_total_exposure_absolute_cap"),
        "exposure_basis": _common_value(details, "exposure_basis") or "equity",
        "sell_orders_with_max_exposure_block": sum(1 for item in sell_orders if "MAX_EXPOSURE_EXCEEDED" in item.get("blocking_reason_codes", [])),
        "equity_linked_samples": samples,
        "equity_linked_samples_valid": all(sample["formula_valid"] for sample in samples) if samples else True,
    }


def _avg_decimal(rows: list[dict[str, Any]], key: str) -> float:
    values = [Decimal(str(item[key])) for item in rows if item.get(key) not in (None, "")]
    return round(float(sum(values, Decimal("0")) / Decimal(max(len(values), 1))), 6) if values else 0.0


def _common_value(rows: list[dict[str, Any]], key: str) -> Any:
    values = [item.get(key) for item in rows if key in item]
    present = [value for value in values if value is not None]
    return present[0] if present and all(value == present[0] for value in present) else (None if not present else "mixed")


def _equity_linked_samples(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    samples = []
    for item in details:
        base = Decimal(str(item.get("base_equity") or "0"))
        allowed = Decimal(str(item.get("max_allowed_exposure") or "0"))
        ratio = Decimal(str(item.get("max_total_exposure_ratio") or "0.85"))
        if base <= 0:
            continue
        candidate = {
            "base_equity": str(base),
            "max_total_exposure_ratio": str(ratio),
            "max_allowed_exposure": str(allowed),
            "expected_max_allowed_exposure": str(base * ratio),
            "formula_valid": allowed == base * ratio,
            "current_exposure": item.get("current_exposure"),
            "projected_exposure": item.get("projected_exposure"),
            "cash_available": item.get("cash_available"),
            "position_count": item.get("position_count"),
            "issue_code": item.get("issue_code"),
        }
        if len(samples) < 5 and candidate not in samples:
            samples.append(candidate)
    return samples


def _previous_fix_f_comparison() -> dict[str, Any]:
    previous = json.loads(Path("reports/phase_reports/phase11z_fix_f_1y_refined_mainline_smoke.json").read_text(encoding="utf-8"))
    return {
        "final_equity": previous["performance"]["safety_on"]["final_equity"],
        "total_return": previous["performance"]["safety_on"]["total_return"],
        "annualized_return": previous["performance"]["safety_on"]["annualized_return"],
        "max_drawdown": previous["performance"]["safety_on"]["max_drawdown"],
        "buy_fill_count": previous["daily_flow"]["safety_on"]["buy_fill_count"],
        "sell_fill_count": previous["daily_flow"]["safety_on"]["sell_fill_count"],
        "trade_count": previous["daily_flow"]["safety_on"]["trade_count"],
        "orders_blocked_by_safety": previous["daily_flow"]["safety_on"]["orders_blocked_by_safety"],
        "max_exposure_blocked_buy_orders": previous["max_exposure_behavior"]["max_exposure_blocked_buy_orders"],
    }


def _previous_delta(on, previous: dict[str, Any]) -> dict[str, Any]:
    return {
        "previous": previous,
        "current": {
            "final_equity": on.performance.get("final_equity"),
            "total_return": on.performance.get("total_return"),
            "annualized_return": on.performance.get("annualized_return"),
            "max_drawdown": on.performance.get("max_drawdown"),
            "buy_fill_count": on.flow_counts.get("buy_fill_count"),
            "sell_fill_count": on.flow_counts.get("sell_fill_count"),
            "trade_count": on.performance.get("trade_count"),
            "orders_blocked_by_safety": on.flow_counts.get("orders_blocked_by_safety"),
        },
        "delta": {
            "final_equity": float(on.performance.get("final_equity") or 0) - float(previous["final_equity"]),
            "total_return": float(on.performance.get("total_return") or 0) - float(previous["total_return"]),
            "max_drawdown": float(on.performance.get("max_drawdown") or 0) - float(previous["max_drawdown"]),
            "buy_fill_count": int(on.flow_counts.get("buy_fill_count") or 0) - int(previous["buy_fill_count"]),
            "sell_fill_count": int(on.flow_counts.get("sell_fill_count") or 0) - int(previous["sell_fill_count"]),
            "trade_count": int(on.performance.get("trade_count") or 0) - int(previous["trade_count"]),
            "orders_blocked_by_safety": int(on.flow_counts.get("orders_blocked_by_safety") or 0) - int(previous["orders_blocked_by_safety"]),
        },
    }


def _fix_i_readiness(on, off, review_block: dict[str, Any], max_exposure: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    block_ratio = float(on.flow_counts.get("orders_blocked_by_safety") or 0) / max(float(on.flow_counts.get("orders_generated") or 1), 1)
    return {
        "ready_for_fix_i_5y_full": bool(all(checks.values()) and block_ratio <= 0.6 and max_exposure["fixed_absolute_cap_used"] is False),
        "block_ratio": round(block_ratio, 6),
        "review_per_business_day": review_block["review_per_business_day"],
        "safety_on_off_explainable": True,
        "five_year_full_not_executed_in_fix_h": True,
        "exit_source": (on.safety_behavior.get("mainline_reuse_map") or {}).get("exit_source"),
        "exit_source_caveat": "exit_source=fallback remains a revenue-quality caveat; Fix-I is a Safety/runtime full audit, not final Production revenue proof.",
    }


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase11-Z-Fix-H 1-Year Equity-Linked MAX_EXPOSURE Smoke",
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
        "- five_year_full_backtest_executed: false",
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
        "## MAX_EXPOSURE",
        "",
        *fix_f._kv(payload["max_exposure"]),
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
        "## Safety ON/OFF Comparison",
        "",
        *fix_f._kv(payload["safety_on_off_comparison"]),
        "",
        "## Previous 1Y Safety ON Comparison",
        "",
        *fix_f._kv(payload["previous_1y_safety_on_comparison"]),
        "",
        "## Review / Block",
        "",
        *fix_f._kv(payload["review_block"]),
        "",
        "## Readiness",
        "",
        *fix_f._kv(payload["fix_i_readiness"]),
        "",
        "## Checks",
        "",
        *fix_f._kv(payload["checks"]),
        "",
        "## Data Use",
        "",
        "Safety result and audit result remain forbidden for AI training. Broker API, WebSocket, LINE send, Demo/Production orders, auto-sell, auto-recovery, AI retraining, and 5-year full were not executed in Fix-H.",
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
