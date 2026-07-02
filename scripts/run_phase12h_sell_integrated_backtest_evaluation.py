#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import statistics
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.safety_phase11.event_writer import _phase11_sanitize, _write_json
from ai_fund_lab_v2.safety_phase11.integrated_backtest_audit import (
    AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
    IntegratedBacktestAuditConfig,
    IntegratedBacktestAuditResult,
    run_integrated_backtest_audit,
)
from ai_fund_lab_v2.safety_phase11.models import utc_now_iso


OUTPUT_DIR = Path("reports/phase12h")
PHASE_DOC_PATH = Path("docs/phase_reports/phase12h_sell_integrated_backtest_evaluation.md")
PHASE_JSON_PATH = Path("reports/phase_reports/phase12h_sell_integrated_backtest_evaluation.json")
PHASE12_EXIT_STRATEGY = "phase12_operations_exit_adapter"
BEFORE_1Y_SUMMARY = Path("reports/safety/phase11/integrated_backtest/fix_h_1y_equity_linked_exposure/summary.json")
BEFORE_5Y_SUMMARY = Path("reports/safety/phase11/integrated_backtest/fix_g_5y_refined_mainline_full/summary.json")
QUOTE_PATH = Path(".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    one_month = _run_period(
        period_id="phase12h_sell_integrated_1m_smoke",
        start_date="2026-05-01",
        end_date="2026-05-31",
        output_subdir="phase12h_sell_integrated_1m_smoke",
    )
    blocking_issues: list[str] = []
    if one_month.status != "PASS":
        blocking_issues.append("one_month_smoke_status_not_pass")
    if int(one_month.flow_counts.get("sell_fill_count") or 0) == 0:
        blocking_issues.append("one_month_smoke_sell_count_zero")

    one_year: IntegratedBacktestAuditResult | None = None
    five_year: IntegratedBacktestAuditResult | None = None
    if not blocking_issues:
        one_year = _run_period(
            period_id="phase12h_sell_integrated_1y",
            start_date="2025-06-01",
            end_date="2026-05-31",
            output_subdir="phase12h_sell_integrated_1y",
        )
        if one_year.status != "PASS":
            blocking_issues.append("one_year_status_not_pass")
        if int(one_year.flow_counts.get("sell_fill_count") or 0) == 0:
            blocking_issues.append("one_year_sell_count_zero")

    if not blocking_issues and one_year is not None:
        five_year = _run_period(
            period_id="phase12h_sell_integrated_5y",
            start_date="2021-06-01",
            end_date="2026-05-31",
            output_subdir="phase12h_sell_integrated_5y",
        )
        if five_year.status != "PASS":
            blocking_issues.append("five_year_status_not_pass")
        if int(five_year.flow_counts.get("sell_fill_count") or 0) == 0:
            blocking_issues.append("five_year_sell_count_zero")

    before_1y = _load_summary(BEFORE_1Y_SUMMARY)
    before_5y = _load_summary(BEFORE_5Y_SUMMARY)
    one_month_summary = _period_summary(one_month)
    one_year_summary = _period_summary(one_year) if one_year else {"status": "NOT_RUN"}
    five_year_summary = _period_summary(five_year) if five_year else {"status": "NOT_RUN"}
    one_year_sell_quality = _sell_quality(one_year) if one_year else _empty_sell_quality("NOT_RUN")
    five_year_sell_quality = _sell_quality(five_year) if five_year else _empty_sell_quality("NOT_RUN")
    before_after = _before_after(before_1y, one_year, before_5y, five_year)
    sell_usage = _sell_usage(one_month, one_year, five_year)
    safety = _safety_analysis(one_year or one_month)
    judgement = _judgement(blocking_issues, one_year, five_year, before_1y)
    payload = _phase11_sanitize(
        {
            "status": "PHASE12H_SELL_INTEGRATED_BACKTEST_EVALUATION_COMPLETE",
            "generated_at": utc_now_iso(),
            "ai_retraining_executed": False,
            "demo_order_executed": False,
            "production_order_executed": False,
            "production_unlock_executed": False,
            "line_send_executed": False,
            "data_leakage_detected": False,
            "backtest_result_used_for_ai_learning": False,
            "future_return_used_for_inference_input": False,
            "broker_snapshot_used_for_ai_training": False,
            "paper_ledger_used_for_ai_training": False,
            "safety_result_used_for_ai_training": False,
            "audit_result_used_for_ai_training": False,
            "cash_portfolio_pnl_used_for_ai_training": False,
            "one_month_smoke": one_month_summary,
            "one_year_result": one_year_summary,
            "five_year_result": five_year_summary,
            "before_after_comparison": before_after,
            "sell_integration_usage": sell_usage,
            "exit_source_analysis": one_year_sell_quality["exit_source_analysis"],
            "sell_reason_analysis": one_year_sell_quality["sell_reason_analysis"],
            "early_sell_analysis": one_year_sell_quality["early_sell_analysis"],
            "loss_cut_analysis": one_year_sell_quality["loss_cut_analysis"],
            "five_year_sell_quality": five_year_sell_quality,
            "safety_analysis": safety,
            "judgement": judgement,
            "blocking_issues": blocking_issues,
            "recommended_next_tasks": _recommended_next_tasks(blocking_issues, before_after, one_year_sell_quality),
            "output_paths": {
                "one_month_summary": one_month.summary_path,
                "one_year_summary": one_year.summary_path if one_year else "",
                "five_year_summary": five_year.summary_path if five_year else "",
                "phase_report_path": str(PHASE_DOC_PATH),
                "phase_report_json_path": str(PHASE_JSON_PATH),
            },
        }
    )
    _write_json(PHASE_JSON_PATH, payload)
    PHASE_DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    PHASE_DOC_PATH.write_text(_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "judgement": judgement, "blocking_issues": blocking_issues}, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if not blocking_issues else 1


def _run_period(*, period_id: str, start_date: str, end_date: str, output_subdir: str) -> IntegratedBacktestAuditResult:
    config = IntegratedBacktestAuditConfig(
        period_id=period_id,
        start_date=start_date,
        end_date=end_date,
        output_subdir=output_subdir,
        reports_dir="reports",
        audit_profile=AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
        safety_enabled=True,
        exit_strategy=PHASE12_EXIT_STRATEGY,
    )
    return run_integrated_backtest_audit(config)


def _load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _period_summary(result: IntegratedBacktestAuditResult) -> dict[str, Any]:
    perf = dict(result.performance)
    daily = [_daily_dict(row) for row in result.daily_records]
    cash_ratios = [_safe_float(row["cash"]) / _safe_float(row["equity"]) for row in daily if _safe_float(row["equity"]) > 0]
    holding_days = _holding_days(result)
    return {
        "status": result.status,
        "period": {"start_date": result.start_date, "end_date": result.end_date, "business_day_count": result.business_day_count},
        "initial_equity": perf.get("initial_cash"),
        "final_equity": perf.get("final_equity"),
        "total_return": perf.get("total_return"),
        "annualized_return": perf.get("annualized_return"),
        "max_drawdown": perf.get("max_drawdown"),
        "profit_factor": perf.get("profit_factor"),
        "trade_count": perf.get("trade_count"),
        "buy_count": perf.get("buy_fill_count"),
        "sell_count": perf.get("sell_fill_count"),
        "average_holding_days": perf.get("average_holding_days"),
        "median_holding_days": statistics.median(holding_days) if holding_days else None,
        "win_rate": perf.get("win_rate"),
        "average_win": _average_win_loss(result)["average_win"],
        "average_loss": _average_win_loss(result)["average_loss"],
        "profit_retention_rate": _sell_quality(result)["profit_retention_rate"],
        "capital_turnover": _capital_turnover(result),
        "cash_ratio_average": round(sum(cash_ratios) / len(cash_ratios), 6) if cash_ratios else None,
        "exposure_ratio_average": perf.get("exposure_ratio"),
        "output_dir": result.output_dir,
    }


def _sell_quality(result: IntegratedBacktestAuditResult | None) -> dict[str, Any]:
    if result is None:
        return _empty_sell_quality("NOT_RUN")
    trades = [_trade_dict(trade) for trade in result.trades]
    sells = [trade for trade in trades if trade["side"] == "SELL"]
    future = _future_return_rows(sells)
    by_reason = _group_sell_pnl(sells, key_fn=lambda row: _sell_reason(row))
    by_source = _group_sell_pnl(sells, key_fn=lambda row: _exit_source(row))
    by_action = _group_sell_pnl(sells, key_fn=lambda row: _exit_action(row))
    early_rows = [row for row in future if row["future_return_20d"] is not None and row["future_return_20d"] > 0.05]
    loss_rows = [row for row in future if row["future_drawdown_20d"] is not None and row["future_drawdown_20d"] < -0.05]
    positive_future = [max(0.0, row.get("future_return_20d") or 0.0) for row in future]
    avoided = [abs(min(0.0, row.get("future_drawdown_20d") or 0.0)) * row["notional"] for row in future if _sell_reason(row).endswith("loss_cut_exit")]
    return {
        "status": "PASS",
        "sell_count": len(sells),
        "partial_sell_count": sum(1 for row in sells if _exit_action(row) == "REDUCE" or "PARTIAL_SELL" in row.get("reason", "")),
        "full_close_count": sum(1 for row in sells if _exit_action(row) == "EXIT" or "FULL_CLOSE" in row.get("reason", "")),
        "profit_retention_rate": _profit_retention_rate(future),
        "exit_source_analysis": by_source,
        "sell_reason_analysis": by_reason,
        "exit_action_analysis": by_action,
        "early_sell_analysis": {
            "evaluated_sell_count": len(future),
            "future_return_5d_average": _avg([row["future_return_5d"] for row in future]),
            "future_return_20d_average": _avg([row["future_return_20d"] for row in future]),
            "future_return_45d_average": _avg([row["future_return_45d"] for row in future]),
            "large_up_after_sell_count_20d_gt_5pct": len(early_rows),
            "early_sell_opportunity_loss": round(sum(positive_future), 6),
            "largest_up_after_sell": sorted(early_rows, key=lambda row: row.get("future_return_20d") or 0, reverse=True)[:10],
        },
        "loss_cut_analysis": {
            "evaluated_sell_count": len(future),
            "future_drawdown_5d_average": _avg([row["future_drawdown_5d"] for row in future]),
            "future_drawdown_20d_average": _avg([row["future_drawdown_20d"] for row in future]),
            "future_drawdown_45d_average": _avg([row["future_drawdown_45d"] for row in future]),
            "loss_expansion_prevented_count_20d_lt_minus_5pct": len(loss_rows),
            "loss_cut_avoided_loss": round(sum(avoided), 6),
        },
        "future_return_sample_path": str(OUTPUT_DIR / f"{result.period_id}_sell_future_returns.json"),
    }


def _empty_sell_quality(status: str) -> dict[str, Any]:
    return {
        "status": status,
        "sell_count": 0,
        "partial_sell_count": 0,
        "full_close_count": 0,
        "profit_retention_rate": None,
        "exit_source_analysis": {},
        "sell_reason_analysis": {},
        "exit_action_analysis": {},
        "early_sell_analysis": {},
        "loss_cut_analysis": {},
    }


def _future_return_rows(sells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    price_by_code_date = _load_quote_lookup()
    if not price_by_code_date:
        return []
    all_dates = sorted({key[1] for key in price_by_code_date})
    rows = []
    for sell in sells:
        sell_date = str(sell["business_date"])
        code = str(sell["issue_code"])
        idx = _date_index(all_dates, sell_date)
        if idx is None:
            continue
        base = _safe_float(sell["price"])
        if base <= 0:
            continue
        row = {
            "business_date": sell_date,
            "issue_code": code,
            "sell_reason": _sell_reason(sell),
            "exit_source": _exit_source(sell),
            "exit_action": _exit_action(sell),
            "notional": _safe_float(sell["notional"]),
        }
        for horizon in (5, 20, 45):
            future_date = all_dates[min(idx + horizon, len(all_dates) - 1)]
            prices = [
                _safe_float(price_by_code_date.get((code, all_dates[pos]), {}).get("close"))
                for pos in range(idx + 1, min(idx + horizon, len(all_dates) - 1) + 1)
                if (code, all_dates[pos]) in price_by_code_date
            ]
            future_price = _safe_float(price_by_code_date.get((code, future_date), {}).get("close"))
            row[f"future_return_{horizon}d"] = round(future_price / base - 1, 6) if future_price > 0 else None
            row[f"future_drawdown_{horizon}d"] = round(min((price / base - 1 for price in prices), default=0.0), 6) if prices else None
        rows.append(row)
    path = OUTPUT_DIR / "latest_sell_future_returns.json"
    _write_json(path, {"rows": rows})
    return rows


def _load_quote_lookup() -> dict[tuple[str, str], dict[str, Any]]:
    if not QUOTE_PATH.exists():
        return {}
    import pandas as pd

    frame = pd.read_parquet(QUOTE_PATH, columns=["date", "code", "close"])
    frame["date"] = frame["date"].astype(str)
    frame["code"] = frame["code"].astype(str)
    return {(str(row["code"]), str(row["date"])): row for row in frame.to_dict(orient="records")}


def _date_index(all_dates: list[str], target: str) -> int | None:
    candidates = [index for index, item in enumerate(all_dates) if item >= target]
    return candidates[0] if candidates else None


def _before_after(before_1y: dict[str, Any], one_year: IntegratedBacktestAuditResult | None, before_5y: dict[str, Any], five_year: IntegratedBacktestAuditResult | None) -> dict[str, Any]:
    return {
        "one_year": _comparison(before_1y, one_year),
        "five_year": _comparison(before_5y, five_year),
        "before_source": {
            "one_year": str(BEFORE_1Y_SUMMARY),
            "five_year": str(BEFORE_5Y_SUMMARY),
            "one_year_exit_source": ((before_1y.get("safety_behavior") or {}).get("mainline_reuse_map") or {}).get("exit_source", "fallback"),
            "five_year_exit_source": ((before_5y.get("safety_behavior") or {}).get("mainline_reuse_map") or {}).get("exit_source", "fallback"),
        },
        "after_exit_source": PHASE12_EXIT_STRATEGY,
    }


def _comparison(before: dict[str, Any], after: IntegratedBacktestAuditResult | None) -> dict[str, Any]:
    if not before or after is None:
        return {"status": "NOT_AVAILABLE"}
    before_perf = before.get("performance") or {}
    after_perf = after.performance
    keys = ["final_equity", "total_return", "annualized_return", "max_drawdown", "profit_factor", "trade_count", "buy_fill_count", "sell_fill_count"]
    return {
        "status": "PASS",
        "before": {key: before_perf.get(key) for key in keys},
        "after": {key: after_perf.get(key) for key in keys},
        "delta": {key: _delta(after_perf.get(key), before_perf.get(key)) for key in keys},
    }


def _sell_usage(*results: IntegratedBacktestAuditResult | None) -> dict[str, Any]:
    rows = {}
    for result in results:
        if result is None:
            continue
        order_decisions_path = Path(result.flow_counts.get("order_decisions_path") or "")
        decisions = json.loads(order_decisions_path.read_text(encoding="utf-8")).get("order_decisions", []) if order_decisions_path.exists() else []
        sells = [item for item in decisions if item.get("side") == "SELL"]
        rows[result.period_id] = {
            "exit_adapter_called": any(item.get("exit_source") == PHASE12_EXIT_STRATEGY for item in sells),
            "order_plan_sell_items": len(sells),
            "sell_items_with_exit_source": sum(1 for item in sells if item.get("exit_source")),
            "sell_items_with_sell_reason": sum(1 for item in sells if item.get("sell_reason")),
            "sell_items_with_position_id": sum(1 for item in sells if item.get("position_id")),
            "sell_filled": sum(1 for item in sells if item.get("filled")),
            "fill_ledger_report_reflected": int(result.flow_counts.get("sell_fill_count") or 0) > 0,
        }
    return rows


def _safety_analysis(result: IntegratedBacktestAuditResult) -> dict[str, Any]:
    flow = result.flow_counts
    safety = result.safety
    order_decisions_path = Path(flow.get("order_decisions_path") or "")
    decisions = json.loads(order_decisions_path.read_text(encoding="utf-8")).get("order_decisions", []) if order_decisions_path.exists() else []
    max_blocks = [item for item in decisions if "MAX_EXPOSURE_EXCEEDED" in item.get("blocking_reason_codes", [])]
    return {
        "orders_generated": flow.get("orders_generated"),
        "orders_allowed_by_safety": flow.get("orders_allowed_by_safety"),
        "orders_blocked_by_safety": flow.get("orders_blocked_by_safety"),
        "MAX_EXPOSURE_blocks": len(max_blocks),
        "NON_BLOCKING_REVIEW_count": flow.get("non_blocking_review_count"),
        "BLOCK_count": safety.get("BLOCK_count"),
        "SYSTEM_EMERGENCY_STOP_count": safety.get("EMERGENCY_STOP_count"),
    }


def _group_sell_pnl(sells: list[dict[str, Any]], *, key_fn) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "pnl": 0.0})
    for row in sells:
        key = key_fn(row)
        grouped[key]["count"] += 1
        grouped[key]["pnl"] += _safe_float(row.get("realized_pnl"))
    return {key: {"count": value["count"], "pnl": round(value["pnl"], 6)} for key, value in sorted(grouped.items())}


def _holding_days(result: IntegratedBacktestAuditResult) -> list[int]:
    buys: dict[str, list[dict[str, Any]]] = defaultdict(list)
    holding_days: list[int] = []
    for trade in [_trade_dict(item) for item in result.trades]:
        if trade["side"] == "BUY":
            buys[trade["issue_code"]].append(trade)
        elif trade["side"] == "SELL" and buys[trade["issue_code"]]:
            buy = buys[trade["issue_code"]].pop(0)
            holding_days.append((date.fromisoformat(trade["business_date"]) - date.fromisoformat(buy["business_date"])).days)
    return holding_days


def _average_win_loss(result: IntegratedBacktestAuditResult) -> dict[str, Any]:
    pnls = [_safe_float(trade.realized_pnl) for trade in result.trades if trade.side == "SELL"]
    wins = [item for item in pnls if item > 0]
    losses = [item for item in pnls if item < 0]
    return {"average_win": _avg(wins), "average_loss": _avg(losses)}


def _profit_retention_rate(future_rows: list[dict[str, Any]]) -> float | None:
    values = []
    for row in future_rows:
        realized_proxy = -(row.get("future_return_20d") or 0.0)
        future_peak = max(row.get("future_return_5d") or 0.0, row.get("future_return_20d") or 0.0, row.get("future_return_45d") or 0.0, 0.0)
        if future_peak > 0:
            values.append(max(0.0, min(1.0, 1.0 - future_peak + realized_proxy)))
    return _avg(values)


def _capital_turnover(result: IntegratedBacktestAuditResult) -> float:
    total_notional = sum((trade.notional for trade in result.trades), Decimal("0"))
    avg_equity = sum((row.equity for row in result.daily_records), Decimal("0")) / Decimal(max(len(result.daily_records), 1))
    return round(float(total_notional / avg_equity), 6) if avg_equity > 0 else 0.0


def _daily_dict(row) -> dict[str, Any]:
    return {"cash": float(row.cash), "equity": float(row.equity)}


def _trade_dict(trade) -> dict[str, Any]:
    return {
        "business_date": trade.business_date,
        "issue_code": trade.issue_code,
        "side": trade.side,
        "quantity": trade.quantity,
        "price": float(trade.price),
        "notional": float(trade.notional),
        "reason": trade.reason,
        "order_id": trade.order_id,
        "realized_pnl": float(trade.realized_pnl),
    }


def _sell_reason(row: dict[str, Any]) -> str:
    if row.get("sell_reason"):
        return str(row.get("sell_reason"))
    reason = str(row.get("reason") or "")
    parts = reason.split(":")
    if len(parts) >= 2 and parts[0] == PHASE12_EXIT_STRATEGY:
        return parts[1]
    return reason or "unknown"


def _exit_source(row: dict[str, Any]) -> str:
    if row.get("exit_source"):
        return str(row.get("exit_source"))
    reason = str(row.get("reason") or "")
    return PHASE12_EXIT_STRATEGY if reason.startswith(PHASE12_EXIT_STRATEGY) else "fallback"


def _exit_action(row: dict[str, Any]) -> str:
    if row.get("exit_action"):
        return str(row.get("exit_action"))
    reason = str(row.get("reason") or "")
    if "PARTIAL_SELL" in reason:
        return "REDUCE"
    if row.get("side") == "SELL":
        return "EXIT"
    return ""


def _avg(values: list[float | None]) -> float | None:
    clean = [float(item) for item in values if item is not None]
    return round(sum(clean) / len(clean), 6) if clean else None


def _safe_float(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _delta(after: Any, before: Any) -> Any:
    if isinstance(after, str) or isinstance(before, str):
        return None
    return round(_safe_float(after) - _safe_float(before), 6)


def _judgement(blocking_issues: list[str], one_year: IntegratedBacktestAuditResult | None, five_year: IntegratedBacktestAuditResult | None, before_1y: dict[str, Any]) -> str:
    if blocking_issues:
        return "PHASE12H_BLOCKED_BEFORE_FULL_EVALUATION"
    before_return = _safe_float((before_1y.get("performance") or {}).get("annualized_return"))
    after_return = _safe_float(one_year.performance.get("annualized_return") if one_year else 0)
    if one_year and five_year and after_return >= before_return and after_return >= 0.5:
        return "SELL_INTEGRATION_CONTRIBUTES_TO_TARGET_RETURN"
    if one_year and after_return >= 0.5:
        return "SELL_INTEGRATION_TARGET_RETURN_OK_BUT_BEFORE_RESULT_NOT_IMPROVED"
    return "SELL_INTEGRATION_NEEDS_CALIBRATION_BEFORE_PRODUCTION_REVENUE_CLAIM"


def _recommended_next_tasks(blocking_issues: list[str], before_after: dict[str, Any], sell_quality: dict[str, Any]) -> list[str]:
    tasks = []
    if blocking_issues:
        tasks.append("Fix blocking issues before rerunning 5-year full backtest.")
    one_year_delta = ((before_after.get("one_year") or {}).get("delta") or {})
    if _safe_float(one_year_delta.get("annualized_return")) < 0:
        tasks.append("Tune Phase12 Exit Adapter thresholds; current integrated exit underperforms fallback on annualized return.")
    early = sell_quality.get("early_sell_analysis") or {}
    if int(early.get("large_up_after_sell_count_20d_gt_5pct") or 0) > 0:
        tasks.append("Review early-sell cases with >5% 20-day post-sell return and add confirmation logic if needed.")
    tasks.append("Keep Demo/Production order wire locked until backtest and Demo operation review pass.")
    return tasks


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase12-H SELL Integrated Backtest Evaluation",
        "",
        f"- status: {payload['status']}",
        f"- judgement: {payload['judgement']}",
        "- ai_retraining_executed: false",
        "- demo_order_executed: false",
        "- production_order_executed: false",
        "- line_send_executed: false",
        "- data_leakage_detected: false",
        "",
        "## One Month Smoke",
        "",
        *_kv(payload["one_month_smoke"]),
        "",
        "## One Year Result",
        "",
        *_kv(payload["one_year_result"]),
        "",
        "## Five Year Result",
        "",
        *_kv(payload["five_year_result"]),
        "",
        "## Before / After",
        "",
        *_kv(payload["before_after_comparison"]),
        "",
        "## SELL Integration Usage",
        "",
        *_kv(payload["sell_integration_usage"]),
        "",
        "## SELL Reason Analysis",
        "",
        *_kv(payload["sell_reason_analysis"]),
        "",
        "## Early Sell Analysis",
        "",
        *_kv(payload["early_sell_analysis"]),
        "",
        "## Loss Cut Analysis",
        "",
        *_kv(payload["loss_cut_analysis"]),
        "",
        "## Safety Analysis",
        "",
        *_kv(payload["safety_analysis"]),
        "",
        "## Blocking Issues",
        "",
        *_kv({"blocking_issues": payload["blocking_issues"]}),
        "",
        "## Recommended Next Tasks",
        "",
        *_kv({"recommended_next_tasks": payload["recommended_next_tasks"]}),
    ]
    return "\n".join(lines) + "\n"


def _kv(mapping: dict[str, Any]) -> list[str]:
    return [f"- {key}: {json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else value}" for key, value in mapping.items()]


if __name__ == "__main__":
    raise SystemExit(main())
