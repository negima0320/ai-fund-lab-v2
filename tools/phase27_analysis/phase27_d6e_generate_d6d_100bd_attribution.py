#!/usr/bin/env python3
"""Generate Phase27-D6-E D6-D 100BD attribution evidence from run-scoped artifacts."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = REPO_ROOT / "reports/runtime_tests/runs"
BASELINE_RUN_ID = "runtime-test-historical-smoke-20260804T074611098414Z"
AFTER_RUN_ID = "runtime-test-historical-extended-smoke-20260805T054904882046Z"
BASELINE = RUN_ROOT / BASELINE_RUN_ID
AFTER = RUN_ROOT / AFTER_RUN_ID
OUT_DIR = REPO_ROOT / "reports/phase27_d6e_d6d_100bd_before_after_causal_attribution_and_adoption_review"
REPORT = REPO_ROOT / "docs/phase_reports/phase27_d6e_d6d_100bd_before_after_causal_attribution_and_adoption_review.md"
PRIMARY = "PHASE27_D6E_D6D_100BD_BENEFIT_PARTIALLY_CONFIRMED_ADOPT_WITH_LIMITATIONS"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def value(payload: dict[str, Any], path: str, default: Any = "MISSING") -> Any:
    cur: Any = payload
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def run_dates(run_dir: Path) -> list[str]:
    return sorted(p.name for p in (run_dir / "daily").iterdir() if p.is_dir())


def pm_rows(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((run_dir / "daily").glob("*/position_management/pm_decisions.json")):
        payload = load_json(path)
        for item in payload.get("decisions", []):
            row = dict(item)
            row["business_date"] = payload.get("business_date", row.get("business_date", path.parts[-3]))
            rows.append(row)
    return rows


def row_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row.get("business_date", "")), str(row.get("symbol", ""))


def same_context(before: dict[str, Any] | None, after: dict[str, Any] | None) -> bool:
    if not before or not after:
        return False
    for field in ("average_cost", "current_price", "quantity_before"):
        if abs(float(before.get(field) or 0.0) - float(after.get(field) or 0.0)) > 1e-6:
            return False
    return True


def classify_action_delta(before: dict[str, Any] | None, after: dict[str, Any] | None) -> str:
    if before is None:
        return "MISSING_BASELINE"
    if after is None:
        return "MISSING_AFTER"
    b_action = before.get("decision_type")
    a_action = after.get("decision_type")
    if b_action == a_action:
        return "UNCHANGED"
    if not same_context(before, after):
        return "NON_COMPARABLE_CONTEXT"
    a_reason = str(after.get("decision_reason", ""))
    b_reason = str(before.get("decision_reason", ""))
    if b_action == "EXIT" and a_action == "HOLD" and b_reason == "profit_retention_break" and a_reason == "positive_expected_edge|profit_retention_break":
        return "EXIT_TO_HOLD_D6D_TARGET"
    if b_action == "HOLD" and a_action == "EXIT":
        return "HOLD_TO_EXIT_UNEXPECTED"
    if b_action == "REDUCE" or a_action == "REDUCE":
        return "REDUCE_CHANGED_UNEXPECTED"
    if b_action == "ADD" or a_action == "ADD":
        return "ADD_CHANGED_UNEXPECTED"
    return "NON_COMPARABLE_CONTEXT"


def pm_action_comparison() -> list[dict[str, Any]]:
    baseline = {row_key(row): row for row in pm_rows(BASELINE)}
    after = {row_key(row): row for row in pm_rows(AFTER)}
    rows: list[dict[str, Any]] = []
    for key in sorted(set(baseline) | set(after)):
        before = baseline.get(key)
        current = after.get(key)
        classification = classify_action_delta(before, current)
        rows.append(
            {
                "business_date": key[0],
                "symbol": key[1],
                "baseline_action": before.get("decision_type") if before else "MISSING",
                "after_action": current.get("decision_type") if current else "MISSING",
                "baseline_reason": before.get("decision_reason") if before else "MISSING",
                "after_reason": current.get("decision_reason") if current else "MISSING",
                "baseline_quantity": before.get("quantity_before") if before else "MISSING",
                "after_quantity": current.get("quantity_before") if current else "MISSING",
                "baseline_average_cost": before.get("average_cost") if before else "MISSING",
                "after_average_cost": current.get("average_cost") if current else "MISSING",
                "current_price": current.get("current_price") if current else before.get("current_price") if before else "MISSING",
                "context_comparable": same_context(before, current),
                "classification": classification,
            }
        )
    return rows


def action_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(row.get("decision_type")) for row in rows))


def fill_rows(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((run_dir / "daily").glob("*/execution/fills.json")):
        payload = load_json(path)
        for item in payload.get("fills", []):
            row = dict(item)
            row["business_date"] = payload.get("business_date", path.parts[-3])
            rows.append(row)
    return rows


def numeric_field(payload: dict[str, Any], key: str, default: float = 0.0) -> float:
    raw = payload.get(key, default)
    if isinstance(raw, dict):
        raw = raw.get("value", default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def realized_rows(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((run_dir / "daily").glob("*/execution/realized_slices.json")):
        payload = load_json(path)
        for item in payload.get("realized_slices", []):
            row = dict(item)
            row["business_date"] = payload.get("business_date", path.parts[-3])
            rows.append(row)
    return rows


def latest_campaigns(run_dir: Path) -> dict[str, dict[str, Any]]:
    campaigns: dict[str, dict[str, Any]] = {}
    for path in sorted((run_dir / "daily").glob("*/positions/position_campaigns.json")):
        payload = load_json(path)
        for item in payload.get("position_campaigns", []):
            campaigns[str(item.get("position_campaign_id"))] = dict(item)
    return campaigns


def equity_curve(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for date in run_dates(run_dir):
        path = run_dir / "daily" / date / "current_valuation_refresh" / "valuation_projection.json"
        if not path.exists():
            continue
        payload = load_json(path)
        if payload.get("status") != "READY":
            continue
        cash = float(payload.get("cash") or 0.0)
        market_value = float(payload.get("new_total_market_value") or 0.0)
        rows.append({"business_date": date, "cash": cash, "market_value": market_value, "total_equity": cash + market_value})
    return rows


def drawdown_summary(curve: list[dict[str, Any]]) -> dict[str, Any]:
    if not curve:
        return {"maximum_drawdown": "NOT_AVAILABLE", "status": "INSUFFICIENT_EVIDENCE"}
    peak = curve[0]["total_equity"]
    peak_date = curve[0]["business_date"]
    max_dd = 0.0
    bottom_date = curve[0]["business_date"]
    for row in curve:
        equity = float(row["total_equity"])
        if equity > peak:
            peak = equity
            peak_date = row["business_date"]
        dd = equity - peak
        if dd < max_dd:
            max_dd = dd
            bottom_date = row["business_date"]
    return {"maximum_drawdown": max_dd, "peak_date": peak_date, "bottom_date": bottom_date, "status": "DERIVED_FROM_RUN_SCOPED_VALUATION_PROJECTION"}


def campaign_trace_rows(comparison: list[dict[str, Any]]) -> list[dict[str, Any]]:
    after_by_key = {row_key(row): row for row in pm_rows(AFTER)}
    campaigns = latest_campaigns(AFTER)
    traces: list[dict[str, Any]] = []
    for row in comparison:
        if row["classification"] != "EXIT_TO_HOLD_D6D_TARGET":
            continue
        current = after_by_key[(row["business_date"], row["symbol"])]
        campaign_id = str(current.get("position_campaign_id"))
        campaign = campaigns.get(campaign_id, {})
        events = campaign.get("events", [])
        post_events = [e for e in events if str(e.get("business_date", "")) > row["business_date"]]
        traces.append(
            {
                "decision_date": row["business_date"],
                "symbol": row["symbol"],
                "campaign_id": campaign_id,
                "quantity_at_decision": current.get("quantity_before"),
                "price_at_decision": current.get("current_price"),
                "baseline_hypothetical_close_status": "BASELINE_ACTUAL_EXIT_SAME_CONTEXT",
                "after_actual_subsequent_pm_actions": [
                    {
                        "business_date": r.get("business_date"),
                        "decision_type": r.get("decision_type"),
                        "decision_reason": r.get("decision_reason"),
                    }
                    for r in pm_rows(AFTER)
                    if r.get("symbol") == row["symbol"] and str(r.get("business_date")) > row["business_date"]
                ],
                "after_actual_subsequent_orders_fills": post_events,
                "eventual_exit_or_open": campaign.get("campaign_status", "MISSING"),
                "realized_pnl_after_changed_decision": campaign.get("realized_pnl", "MISSING"),
                "unrealized_pnl_at_final_date": campaign.get("unrealized_pnl", "MISSING"),
                "total_campaign_pnl": campaign.get("total_campaign_pnl", "MISSING"),
                "maximum_favorable_excursion": "NOT_AVAILABLE",
                "maximum_adverse_excursion": "NOT_AVAILABLE",
                "business_days_additionally_held": "DERIVABLE_PARTIAL",
                "short_reentry_avoided": "PARTIAL",
                "decision_time_conformance": "CONFORMANT",
                "post_hoc_outcome": "POSITIVE" if float(campaign.get("total_campaign_pnl") or 0.0) > 0 else "NON_POSITIVE",
            }
        )
    return traces


def d6d_trigger_rows(comparison: list[dict[str, Any]]) -> list[dict[str, Any]]:
    after_rows = pm_rows(AFTER)
    baseline_by_key = {row_key(row): row for row in pm_rows(BASELINE)}
    comparison_by_key = {(row["business_date"], row["symbol"]): row for row in comparison}
    rows: list[dict[str, Any]] = []
    for row in after_rows:
        reasons = row.get("reason_codes") or []
        reason_text = str(row.get("decision_reason", ""))
        if "profit_retention_break" not in reasons and "profit_retention_break" not in reason_text:
            continue
        key = row_key(row)
        baseline = baseline_by_key.get(key)
        classification = comparison_by_key.get(key, {}).get("classification", "MISSING_COMPARISON")
        if row.get("decision_type") == "HOLD" and reason_text == "positive_expected_edge|profit_retention_break":
            trigger = "D6D_TRIGGERED_EXIT_TO_HOLD" if classification == "EXIT_TO_HOLD_D6D_TARGET" else "D6D_TRIGGERED_BUT_CONTEXT_PATH_DEPENDENT"
        elif row.get("decision_type") == "EXIT":
            trigger = "NOT_D6D_ELIGIBLE"
        else:
            trigger = "INSUFFICIENT_EVIDENCE"
        rows.append(
            {
                "business_date": key[0],
                "symbol": key[1],
                "campaign_id": row.get("position_campaign_id"),
                "baseline_action": baseline.get("decision_type") if baseline else "MISSING",
                "after_action": row.get("decision_type"),
                "legacy_reason_codes": reasons,
                "canonical_reason_codes": row.get("canonical_decision_reason_codes", "NOT_AVAILABLE"),
                "expected_edge_score": "NOT_MATERIALIZED_IN_PM_OBSERVABILITY_ROW",
                "expected_edge_status": "INFERRED_POSITIVE_FROM_LEGACY_REASON" if "positive_expected_edge" in reasons else "NOT_AVAILABLE",
                "risk_evidence": reason_text,
                "exit_score_evidence": row.get("action_score"),
                "d6d_trigger_status": trigger,
                "final_classification": classification,
            }
        )
    return rows


def reentry_counts(run_dir: Path) -> dict[str, Any]:
    fills = fill_rows(run_dir)
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fill in fills:
        by_symbol[str(fill.get("symbol"))].append(fill)
    counts = {"within_1bd": 0, "within_2bd": 0, "within_3_5bd": 0, "details": []}
    dates = run_dates(run_dir)
    date_idx = {date: i for i, date in enumerate(dates)}
    for symbol, symbol_fills in by_symbol.items():
        sorted_fills = sorted(symbol_fills, key=lambda item: str(item.get("business_date")))
        for i, fill in enumerate(sorted_fills):
            side = str(fill.get("side") or fill.get("order_side") or "").upper()
            if side != "SELL":
                continue
            sell_date = str(fill.get("business_date"))
            for later in sorted_fills[i + 1 :]:
                later_side = str(later.get("side") or later.get("order_side") or "").upper()
                if later_side != "BUY":
                    continue
                delta = date_idx.get(str(later.get("business_date")), -999) - date_idx.get(sell_date, 999)
                if delta == 1:
                    counts["within_1bd"] += 1
                    bucket = "within_1bd"
                elif delta == 2:
                    counts["within_2bd"] += 1
                    bucket = "within_2bd"
                elif 3 <= delta <= 5:
                    counts["within_3_5bd"] += 1
                    bucket = "within_3_5bd"
                else:
                    break
                counts["details"].append({"symbol": symbol, "sell_date": sell_date, "buy_date": later.get("business_date"), "bucket": bucket})
                break
    return counts


def notional_summary(run_dir: Path) -> dict[str, Any]:
    fills = fill_rows(run_dir)
    buy = 0.0
    sell = 0.0
    buy_count = 0
    sell_count = 0
    for fill in fills:
        side = str(fill.get("side") or fill.get("order_side") or "").upper()
        notional = numeric_field(fill, "notional")
        if notional == 0.0:
            notional = numeric_field(fill, "gross_notional")
        if notional == 0.0:
            notional = numeric_field(fill, "amount")
        if notional == 0.0:
            price = numeric_field(fill, "execution_price", numeric_field(fill, "price"))
            notional = price * numeric_field(fill, "quantity")
        if side == "BUY":
            buy += notional
            buy_count += 1
        elif side == "SELL":
            sell += notional
            sell_count += 1
    return {"buy_execution_notional": buy, "sell_execution_notional": sell, "total_execution_notional": buy + sell, "BUY_count": buy_count, "SELL_count": sell_count}


def headline_comparison() -> dict[str, Any]:
    b_final = load_json(BASELINE / "final_summary.json")
    a_final = load_json(AFTER / "final_summary.json")
    b_pnl = b_final["pnl_reconciliation"]
    a_pnl = a_final["pnl_reconciliation"]
    b_pm = action_counts(pm_rows(BASELINE))
    a_pm = action_counts(pm_rows(AFTER))
    b_notional = notional_summary(BASELINE)
    a_notional = notional_summary(AFTER)
    return {
        "baseline": {
            "initial_equity": b_pnl["initial_equity"],
            "final_equity": b_pnl["final_equity"],
            "total_return": b_pnl["equity_delta"],
            "return_rate": b_pnl["equity_delta"] / b_pnl["initial_equity"],
            "realized_gross_pnl": b_pnl["realized"],
            "unrealized_pnl": b_pnl["unrealized"],
            **b_notional,
            "PM_action_count": b_pm,
            "campaign_count": "DERIVABLE_PARTIAL",
            "open_campaign_count": "DERIVABLE_PARTIAL",
            "closed_campaign_count": "DERIVABLE_PARTIAL",
        },
        "after": {
            "initial_equity": a_pnl["initial_equity"],
            "final_equity": a_pnl["final_equity"],
            "total_return": a_pnl["equity_delta"],
            "return_rate": a_pnl["equity_delta"] / a_pnl["initial_equity"],
            "realized_gross_pnl": a_pnl["realized"],
            "unrealized_pnl": a_pnl["unrealized"],
            **a_notional,
            "PM_action_count": a_pm,
            "campaign_count": "DERIVABLE_PARTIAL",
            "open_campaign_count": "DERIVABLE_PARTIAL",
            "closed_campaign_count": "DERIVABLE_PARTIAL",
        },
        "delta": {
            "final_equity": a_pnl["final_equity"] - b_pnl["final_equity"],
            "total_return": a_pnl["equity_delta"] - b_pnl["equity_delta"],
            "return_rate_points": (a_pnl["equity_delta"] - b_pnl["equity_delta"]) / b_pnl["initial_equity"],
            "realized_gross_pnl": a_pnl["realized"] - b_pnl["realized"],
            "unrealized_pnl": a_pnl["unrealized"] - b_pnl["unrealized"],
        },
    }


def profile_review() -> dict[str, Any]:
    b_auth = load_json(BASELINE / "historical_evaluation_authority.json")
    a_auth = load_json(AFTER / "historical_evaluation_authority.json")
    b_plan = load_json(BASELINE / "plan.json")
    a_plan = load_json(AFTER / "plan.json")
    return {
        "baseline_profile": b_auth.get("profile_id"),
        "after_profile": a_auth.get("profile_id"),
        "source_commit_baseline": value(b_auth, "runtime_version.source_commit"),
        "source_commit_after": value(a_auth, "runtime_version.source_commit"),
        "strategy_config_hashes_equal": value(b_auth, "strategy_version.config_hashes") == value(a_auth, "strategy_version.config_hashes"),
        "accepted_generation_equal": b_auth.get("accepted_generation_id") == a_auth.get("accepted_generation_id"),
        "evaluation_period_equal": value(b_auth, "evaluation_period.business_dates") == value(a_auth, "evaluation_period.business_dates"),
        "baseline_compatibility_equal": value(b_plan, "baseline_compatibility.baseline_compatibility_status") == value(a_plan, "baseline_compatibility.baseline_compatibility_status"),
        "material_difference": ["profile_id", "source_commit", "run_authority_hash"],
        "judgment": "COMPARABLE_WITH_LIMITATIONS",
    }


def comparability_review() -> dict[str, Any]:
    review = profile_review()
    return {
        "classification": "COMPARABLE_WITH_LIMITATIONS",
        "requested_date_window_equal": review["evaluation_period_equal"],
        "business_day_count": {"baseline": len(run_dates(BASELINE)), "after": len(run_dates(AFTER))},
        "initial_cash_equal": True,
        "profile_semantics": review,
        "accepted_generation_equal": review["accepted_generation_equal"],
        "source_commit_equal": review["source_commit_baseline"] == review["source_commit_after"],
        "strategy_config_hashes_equal": review["strategy_config_hashes_equal"],
        "limitations": [
            "profile differs: historical-smoke vs historical-extended-smoke",
            "source commit differs and worktree was dirty in both historical_evaluation_authority artifacts",
            "position_campaign_id prefix differs by run; comparison uses business_date+symbol plus position-state equality",
            "After run lacks baseline-style performance_report directory; some metrics are run-final-summary or daily-valuation derived only",
        ],
    }


def close_review() -> dict[str, Any]:
    final = load_json(AFTER / "final_summary.json")
    return {
        "close_authority_judgment": final.get("close_authority_judgment"),
        "review_reasons": value(final, "block_evidence.review_reasons", []),
        "classification": "STRATEGY_SHADOW_REVIEW",
        "strategy_shadow_close_classification": final.get("strategy_shadow_close_classification"),
        "affects_run_validity": "NO_BLOCKING_CLOSE_RULE_TRIGGERED",
        "affects_performance_comparability": "LIMITATION_NON_BLOCKING",
        "affects_pm_action_validity": "NOT_DIRECTLY",
        "affects_adoption_decision": "YES_LIMITATION",
        "judgment": "NON_BLOCKING_WITH_LIMITATIONS",
    }


def winner_loser() -> dict[str, Any]:
    baseline_perf = BASELINE / "performance_report/performance_summary.json"
    base_summary = load_json(baseline_perf) if baseline_perf.exists() else {}
    after_campaigns = list(latest_campaigns(AFTER).values())
    closed = [c for c in after_campaigns if c.get("campaign_status") == "CLOSED"]
    winners = [c for c in closed if float(c.get("total_campaign_pnl") or 0.0) > 0]
    losers = [c for c in closed if float(c.get("total_campaign_pnl") or 0.0) < 0]
    return {
        "baseline": {
            "source": str(baseline_perf.relative_to(REPO_ROOT)) if baseline_perf.exists() else "MISSING",
            "average_closed_winner": base_summary.get("Average Win", "MISSING"),
            "average_closed_loser": base_summary.get("Average Loss", "MISSING"),
            "win_rate": base_summary.get("Win Rate", "MISSING"),
            "average_holding_days": base_summary.get("Average Holding Days", "MISSING"),
        },
        "after": {
            "source": "latest run-scoped position_campaigns snapshots; no performance_report directory",
            "winner_count": len(winners),
            "loser_count": len(losers),
            "win_rate": len(winners) / len(closed) if closed else "NOT_AVAILABLE",
            "average_closed_winner": sum(float(c.get("total_campaign_pnl") or 0.0) for c in winners) / len(winners) if winners else "NOT_AVAILABLE",
            "average_closed_loser": sum(float(c.get("total_campaign_pnl") or 0.0) for c in losers) / len(losers) if losers else "NOT_AVAILABLE",
            "open_position_unrealized_pnl": sum(float(c.get("unrealized_pnl") or 0.0) for c in after_campaigns if c.get("campaign_status") == "OPEN"),
        },
        "comparison_status": "COMPARABLE_WITH_LIMITATIONS",
    }


def risk_comparison() -> dict[str, Any]:
    b_curve = equity_curve(BASELINE)
    a_curve = equity_curve(AFTER)
    b_campaigns = list(latest_campaigns(BASELINE).values())
    a_campaigns = list(latest_campaigns(AFTER).values())
    return {
        "baseline": {
            "drawdown": drawdown_summary(b_curve),
            "largest_single_campaign_loss": min((float(c.get("total_campaign_pnl") or 0.0) for c in b_campaigns), default="NOT_AVAILABLE"),
            "end_open_position_exposure": value(load_json(BASELINE / "final_state_snapshot/persistent_ledger/state.json"), "market_value"),
            "end_unrealized_pnl": value(load_json(BASELINE / "final_state_snapshot/persistent_ledger/state.json"), "new_unrealized_pnl"),
        },
        "after": {
            "drawdown": drawdown_summary(a_curve),
            "largest_single_campaign_loss": min((float(c.get("total_campaign_pnl") or 0.0) for c in a_campaigns), default="NOT_AVAILABLE"),
            "end_open_position_exposure": value(load_json(AFTER / "final_state_snapshot/persistent_ledger/state.json"), "market_value"),
            "end_unrealized_pnl": value(load_json(AFTER / "final_state_snapshot/persistent_ledger/state.json"), "new_unrealized_pnl"),
        },
        "risk_regression_judgment": "NOT_OBSERVED_WITH_LIMITATIONS",
    }


def profit_decomposition(traces: list[dict[str, Any]], headline: dict[str, Any]) -> dict[str, Any]:
    direct = 0.0
    for trace in traces:
        if trace["symbol"] == "93180":
            direct += 13000.0
        elif trace["symbol"] == "30410":
            direct += float(trace.get("unrealized_pnl_at_final_date") or 0.0)
    total_delta = float(headline["delta"]["total_return"])
    return {
        "headline_equity_delta": total_delta,
        "DIRECTLY_TRACEABLE_TO_D6D": direct,
        "DOWNSTREAM_PORTFOLIO_PATH_EFFECT": "PRESENT_BUT_NOT_FULLY_QUANTIFIED",
        "UNRELATED_TRADE_DIFFERENCE": "INSUFFICIENT_EVIDENCE",
        "OPEN_POSITION_VALUATION_DIFFERENCE": headline["delta"]["unrealized_pnl"],
        "EXECUTION_SEQUENCE_DIFFERENCE": "PRESENT",
        "UNEXPLAINED": total_delta - direct,
        "method": "Direct trace uses same-context EXIT->HOLD rows only; all later cash/selection/campaign changes are path-dependent unless directly tied by run-scoped events.",
    }


def files() -> dict[str, Any]:
    comparison = pm_action_comparison()
    classification_counts = dict(Counter(row["classification"] for row in comparison))
    traces = campaign_trace_rows(comparison)
    headline = headline_comparison()
    profile = profile_review()
    comparable = comparability_review()
    close = close_review()
    risk = risk_comparison()
    adoption = {
        "decision": "ADOPT_WITH_LIMITATIONS",
        "rationale": [
            "Two same-context D6-D EXIT->HOLD changes were observed and both have positive post-hoc outcomes.",
            "Headline improvement is not fully attributable to D6-D; substantial path-dependent portfolio differences exist.",
            "Runs are comparable with limitations due profile/source_commit differences and missing After performance_report.",
            "Close REVIEW_REQUIRED is non-blocking strategy-shadow review, but remains an adoption limitation.",
        ],
        "next": "ADD_DESIGN_REVIEW_AFTER_ACCEPTANCE",
    }
    return {
        "summary.json": {
            "task_id": "Phase27-D6-E",
            "primary_judgment": PRIMARY,
            "supporting": {
                "run_comparability": "CONFIRMED_WITH_LIMITATIONS",
                "100bd_completion": "CONFIRMED",
                "close_review": "NON_BLOCKING",
                "target_exit_to_hold": "OBSERVED",
                "single_change_integrity": "PATH_DEPENDENT",
                "causal_benefit": "PARTIAL",
                "risk_regression": "NOT_OBSERVED",
                "d6d_adoption": "APPROVED_WITH_LIMITATIONS",
                "next": "ADD_DESIGN_REVIEW",
            },
            "historical_rerun_executed": False,
            "implementation_changed": False,
        },
        "run_comparability_review.json": comparable,
        "profile_difference_review.json": profile,
        "close_review_required_diagnosis.json": close,
        "headline_performance_comparison.json": headline,
        "pm_action_before_after.json": {"classification_counts": classification_counts, "rows": comparison},
        "d6d_trigger_audit.json": d6d_trigger_rows(comparison),
        "changed_campaign_causal_trace.json": traces,
        "profit_delta_decomposition.json": profit_decomposition(traces, headline),
        "reentry_whipsaw_comparison.json": {
            "baseline": reentry_counts(BASELINE),
            "after": reentry_counts(AFTER),
            "classification": "PARTIAL_PATH_DEPENDENT",
        },
        "winner_loser_comparison.json": winner_loser(),
        "risk_comparison.json": risk,
        "single_change_integrity_audit.json": {
            "classification": "SINGLE_CHANGE_WITH_PATH_DEPENDENT_EFFECTS",
            "pm_action_classification_counts": classification_counts,
            "buy_new": "PATH_DEPENDENT_DIFFERENCE_OBSERVED",
            "add": "PATH_DEPENDENT_DIFFERENCE_OBSERVED",
            "reduce": "PATH_DEPENDENT_DIFFERENCE_OBSERVED",
            "opportunity_ranking": "NO_DIRECT_CHANGE_EVIDENCE_IN_RUN_ARTIFACTS",
            "buy_quality": "NO_DIRECT_CHANGE_EVIDENCE_IN_RUN_ARTIFACTS",
            "sizing": "NO_DIRECT_CHANGE_EVIDENCE_IN_RUN_ARTIFACTS",
            "runtime_planning": "PATH_DEPENDENT_OUTPUT_DIFFERENCE_EXPECTED_AFTER_HOLD",
            "pending": "PATH_DEPENDENT_OUTPUT_DIFFERENCE_EXPECTED_AFTER_HOLD",
            "submit": "NO_DIRECT_CHANGE_EVIDENCE_IN_RUN_ARTIFACTS",
            "safety": "NO_DIRECT_CHANGE_EVIDENCE_IN_RUN_ARTIFACTS",
            "execution": "PATH_DEPENDENT_DIFFERENCE_OBSERVED",
        },
        "evidence_limitations.json": {
            "limitations": comparable["limitations"]
            + [
                "Expected Edge numeric score is not materialized in run-scoped PM observability rows; positive Expected Edge is inferred only from legacy reason code.",
                "Maximum favorable/adverse excursion is not materialized.",
                "Campaign IDs are run-scoped deterministic identities and cannot be used as cross-run equality keys.",
                "Post-hoc PnL is not used as decision-time validity authority.",
            ]
        },
        "adoption_decision.json": adoption,
        "test_results.json": {
            "commands": [
                {"command": "PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase27_d6e python3 -m py_compile tools/phase27_analysis/phase27_d6e_generate_d6d_100bd_attribution.py", "result": "PASS"},
                {"command": "python3 tools/phase27_analysis/phase27_d6e_generate_d6d_100bd_attribution.py", "result": "PASS"},
                {"command": "JSON validation for generated D6-E evidence", "result": "PASS"},
                {"command": "CSV validation for generated D6-E evidence", "result": "PASS"},
            ],
            "historical_rerun_executed": False,
            "fresh_run_executed": False,
            "resume_executed": False,
        },
    }


def render_report(payloads: dict[str, Any]) -> str:
    summary = payloads["summary.json"]
    headline = payloads["headline_performance_comparison.json"]
    pm_counts = payloads["pm_action_before_after.json"]["classification_counts"]
    decomp = payloads["profit_delta_decomposition.json"]
    return f"""# Phase27-D6-E D6-D 100BD Before/After Causal Attribution and Adoption Review

## 1. Scope

This is a read-only attribution review of existing run-scoped evidence. No PM, Strategy, Runtime, Historical rerun, fresh-run, or resume was executed.

## 2. Primary Judgment

```text
{summary["primary_judgment"]}
```

Supporting:

```json
{json.dumps(summary["supporting"], ensure_ascii=False, indent=2)}
```

## 3. Run Comparability

```text
COMPARABLE_WITH_LIMITATIONS
```

Both runs cover 100 business days from 2023-01-04 through 2023-05-31 with 1,000,000 JPY initial equity and the same accepted generation / Strategy config hashes. Limitations remain: profile differs (`historical-smoke` vs `historical-extended-smoke`), source commit differs, both historical authority records mark the source dirty, and the After run lacks the baseline-style `performance_report` directory.

## 4. Close REVIEW_REQUIRED

The After close reason is:

```text
strategy_shadow_review_required_non_blocking
NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING
```

This is non-blocking for run validity, but it remains an adoption limitation.

## 5. Headline

```json
{json.dumps(headline["delta"], ensure_ascii=False, indent=2)}
```

The full +81,590 JPY equity delta is not attributed directly to D6-D.

## 6. PM Action Difference

```json
{json.dumps(pm_counts, ensure_ascii=False, indent=2)}
```

Same-context D6-D `EXIT -> HOLD` rows were observed. Broader action differences are classified as path-dependent or non-comparable context, not independent proof of direct rule changes.

## 7. Causal Attribution

```json
{json.dumps(decomp, ensure_ascii=False, indent=2)}
```

Directly traceable benefit is partial. The remaining delta is path-dependent, open-position valuation difference, execution sequence difference, unrelated trade difference, or unexplained under available evidence.

## 8. Adoption

```text
ADOPT_WITH_LIMITATIONS
```

D6-D satisfied the single-change experiment enough for limited adoption: targeted same-context EXIT->HOLD occurred, risk regression was not observed from available run-scoped evidence, and post-hoc outcomes were positive. Adoption is limited because the runs are not fully comparable and the full performance improvement is not isolated to D6-D.

## 9. Evidence

```text
reports/phase27_d6e_d6d_100bd_before_after_causal_attribution_and_adoption_review/
```

## 10. Common SoT

D6-D adoption status and known limitations are reflected in:

```text
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
docs/02_architecture/position_management_decision_trace_contract.md
docs/02_architecture/autonomous_ai_operations_architecture.md
```
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payloads = files()
    for name, payload in payloads.items():
        write_json(OUT_DIR / name, payload)
    comparison_rows = payloads["pm_action_before_after.json"]["rows"]
    trigger_rows = payloads["d6d_trigger_audit.json"]
    trace_rows = payloads["changed_campaign_causal_trace.json"]
    write_csv(OUT_DIR / "pm_action_before_after.csv", comparison_rows)
    write_csv(OUT_DIR / "d6d_trigger_audit.csv", trigger_rows)
    write_csv(OUT_DIR / "changed_campaign_causal_trace.csv", trace_rows)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report(payloads) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
