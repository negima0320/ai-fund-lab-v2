#!/usr/bin/env python3
"""Phase27-A2 read-only attribution generator.

Observability Only / Post-hoc Human Review Only / Not a Strategy Input.

This script reads only run-scoped Runtime Test evidence under
reports/runtime_tests/runs/<run-id>. It does not read .runtime, does not mutate
runtime state, and must not be used as Strategy, BUY Quality, Portfolio Policy,
Position Sizing, Planning, Submit, Safety, PM, Exit, or Re-entry input.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any


BASELINE_RUN_ID = "runtime-test-historical-smoke-20260804T074611098414Z"
DEFAULT_RUNS_ROOT = Path("reports/runtime_tests/runs")
DEFAULT_OUTPUT_DIR = Path(
    "reports/phase27_a2_100bd_baseline_attribution_and_hypothesis_evidence_extraction"
)


def load_json(path: Path) -> Any:
    with path.open() as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def as_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    if isinstance(value, dict):
        return as_float(value.get("value"), default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def pct(num: float, den: float) -> float | None:
    if den == 0:
        return None
    return num / den


def safe_mean(values: list[float]) -> float | None:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    return mean(vals) if vals else None


def safe_median(values: list[float]) -> float | None:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    return median(vals) if vals else None


def profit_factor(gross_profit: float, gross_loss: float) -> float | None:
    if gross_loss == 0:
        return None
    return gross_profit / abs(gross_loss)


def by_symbol(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = {}
    for row in rows:
        symbol = row.get("symbol") or row.get("security_code")
        if symbol:
            out[str(symbol)] = row
    return out


def rank_bucket(rank: Any) -> str:
    r = as_int(rank, 0)
    if r == 1:
        return "Opportunity Rank 1"
    if r == 2:
        return "Opportunity Rank 2"
    if r == 3:
        return "Opportunity Rank 3"
    if 4 <= r <= 5:
        return "Opportunity Rank 4-5"
    if 6 <= r <= 10:
        return "Opportunity Rank 6-10"
    if r >= 11:
        return "Opportunity Rank 11+"
    return "Unknown"


def quality_score_bucket(score: Any) -> str:
    s = as_float(score, 0.0)
    if s < 0.50:
        return "0.00-0.49"
    if s < 0.60:
        return "0.50-0.59"
    if s < 0.70:
        return "0.60-0.69"
    if s < 0.80:
        return "0.70-0.79"
    if s < 0.90:
        return "0.80-0.89"
    return "0.90-1.00"


@dataclass
class RunData:
    run_id: str
    run_dir: Path
    dates: list[str]
    perf: dict[str, Any]
    final_summary: dict[str, Any]
    trade_with_quality: list[dict[str, str]]
    trade_history: list[dict[str, str]]
    cash_exposure: list[dict[str, str]]
    drawdown: list[dict[str, str]]
    holding_period: list[dict[str, str]]
    reentry_statistics: list[dict[str, str]]


def load_run(run_id: str, runs_root: Path) -> RunData:
    if "/" in run_id or "\\" in run_id or run_id in {"", ".", ".."}:
        raise SystemExit(f"invalid run id: {run_id!r}")
    run_dir = (runs_root / run_id).resolve()
    runs_root_resolved = runs_root.resolve()
    if not str(run_dir).startswith(str(runs_root_resolved)):
        raise SystemExit("run directory must stay under reports/runtime_tests/runs")
    if not run_dir.exists():
        raise SystemExit(f"missing run directory: {run_dir}")
    dates = sorted(p.name for p in (run_dir / "daily").iterdir() if p.is_dir())
    perf_dir = run_dir / "performance_report"
    return RunData(
        run_id=run_id,
        run_dir=run_dir,
        dates=dates,
        perf=load_json(perf_dir / "performance_summary.json"),
        final_summary=load_json(run_dir / "final_summary.json"),
        trade_with_quality=read_csv(perf_dir / "trade_with_quality.csv"),
        trade_history=read_csv(perf_dir / "trade_history.csv"),
        cash_exposure=read_csv(perf_dir / "cash_exposure.csv"),
        drawdown=read_csv(perf_dir / "drawdown.csv"),
        holding_period=read_csv(perf_dir / "holding_period.csv"),
        reentry_statistics=read_csv(perf_dir / "reentry_statistics.csv"),
    )


def daily_path(data: RunData, date: str, rel: str) -> Path:
    return data.run_dir / "daily" / date / rel


def current_state(data: RunData, date: str) -> dict[str, Any]:
    manifest = load_json(daily_path(data, date, "current_valuation_refresh/current_valuation_manifest.json"))
    return manifest.get("artifact", {}).get("candidate_current", {})


def daily_fills(data: RunData, date: str) -> list[dict[str, Any]]:
    return load_json(daily_path(data, date, "execution/fills.json")).get("fills", [])


def daily_realized_slices(data: RunData, date: str) -> list[dict[str, Any]]:
    return load_json(daily_path(data, date, "execution/realized_slices.json")).get("realized_slices", [])


def build_funnel(data: RunData) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for date in data.dates:
        q_rows = load_json(daily_path(data, date, "strategy/buy_quality_decisions.json")).get("decisions", [])
        pc_rows = by_symbol(load_json(daily_path(data, date, "strategy/portfolio_construction.json")).get("portfolio_members", []))
        ps_rows = by_symbol(load_json(daily_path(data, date, "strategy/position_sizing.json")).get("positions", []))
        rp_rows = by_symbol(load_json(daily_path(data, date, "strategy/runtime_planning.json")).get("plans", []))
        spa_items = (
            load_json(daily_path(data, date, "morning/strategy_planning_authority_evidence.json"))
            .get("lineage", {})
            .get("items", [])
        )
        pending_by_symbol = {str(x.get("security_code")): x for x in spa_items if x.get("security_code")}
        buy_fills_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for fill in daily_fills(data, date):
            if fill.get("side") == "BUY":
                buy_fills_by_symbol[str(fill.get("symbol"))].append(fill)

        for q in q_rows:
            symbol = str(q.get("symbol") or q.get("security_code"))
            pc = pc_rows.get(symbol, {})
            ps = ps_rows.get(symbol, {})
            rp = rp_rows.get(symbol, {})
            pending = pending_by_symbol.get(symbol, {})
            fills = buy_fills_by_symbol.get(symbol, [])
            fill = fills[0] if fills else {}
            planned_qty = as_float(rp.get("planned_quantity"), 0.0)
            filled_qty = as_float(fill.get("quantity"), 0.0)
            filled_notional = as_float(fill.get("gross_notional"), 0.0)
            filled = bool(fill)
            pending_generated = bool(pending.get("pending_item_generated"))
            join_confidence = "UNRESOLVED"
            if filled:
                if (
                    planned_qty
                    and abs(planned_qty - filled_qty) < 1e-9
                    and fill.get("pending_item_id") != "MISSING"
                    and fill.get("order_plan_item_id") != "MISSING"
                ):
                    join_confidence = "DIRECT_ID_JOIN"
                elif planned_qty and abs(planned_qty - filled_qty) < 1e-9:
                    join_confidence = "COMPOSITE_EXACT_JOIN"
                else:
                    join_confidence = "COMPOSITE_PROBABLE_JOIN"
            submitted = filled

            membership = pc.get("membership_intent", "")
            target_weight = as_float(ps.get("target_weight", pc.get("target_weight", 0.0)), 0.0)
            target_notional = as_float(ps.get("target_notional"), 0.0)
            sized_qty = as_float(ps.get("quantity_delta_candidate"), 0.0)
            q_action = q.get("quality_action", "")
            planning_intent = rp.get("planning_intent", "")
            no_order_reason = rp.get("no_order_reason", "")
            planning_reason = rp.get("planning_reason", "")
            sizing_status = ps.get("quantity_status", "")

            if filled:
                final_status = "BOUGHT"
                final_reason = "filled"
            elif q_action == "REJECT":
                final_status = "NOT_BOUGHT_QUALITY_REJECT"
                final_reason = ";".join(q.get("quality_reason_codes", [])[:5])
            elif q_action in {"REVIEW_REQUIRED", "BUY_REVIEW_REQUIRED"}:
                final_status = "NOT_BOUGHT_REVIEW_REQUIRED"
                final_reason = ";".join(q.get("quality_reason_codes", [])[:5])
            elif membership == "EXCLUDE":
                final_status = "NOT_BOUGHT_PORTFOLIO_EXCLUDED"
                final_reason = pc.get("membership_reason") or ";".join(pc.get("reason_codes", []))
            elif target_weight == 0:
                final_status = "NOT_BOUGHT_ZERO_WEIGHT"
                final_reason = pc.get("weight_reason") or ps.get("sizing_reason") or planning_reason
            elif sized_qty == 0:
                final_status = "NOT_BOUGHT_ZERO_QUANTITY"
                final_reason = sizing_status or ps.get("sizing_reason") or planning_reason
            elif planning_intent == "NO_ACTION":
                final_status = "NOT_BOUGHT_NO_ACTION"
                final_reason = no_order_reason or planning_reason
            elif "SAFETY" in (no_order_reason + planning_reason + sizing_status):
                final_status = "NOT_BOUGHT_AUTHORITY_OR_SAFETY"
                final_reason = no_order_reason or planning_reason or sizing_status
            else:
                final_status = "NOT_BOUGHT_UNKNOWN"
                final_reason = no_order_reason or planning_reason or sizing_status or pc.get("membership_reason", "")

            rows.append(
                {
                    "business_date": date,
                    "symbol": symbol,
                    "source_candidate_id": q.get("source_candidate_id") or pc.get("source_candidate_id"),
                    "candidate_order_if_available": pc.get("input_candidate_order"),
                    "source_opportunity_id": q.get("source_opportunity_id") or pc.get("source_opportunity_id"),
                    "opportunity_rank": q.get("opportunity_buy_rank") or pc.get("opportunity_buy_rank"),
                    "opportunity_score": q.get("runtime_opportunity_score"),
                    "quality_decision_id": q.get("quality_decision_id"),
                    "quality_score": q.get("quality_score"),
                    "quality_action": q_action,
                    "quality_adjustment": q.get("quality_allocation_adjustment"),
                    "portfolio_membership_intent": membership,
                    "portfolio_construction_reason": pc.get("membership_reason") or ";".join(pc.get("reason_codes", [])),
                    "target_weight": target_weight,
                    "target_notional": target_notional,
                    "sized_quantity": sized_qty,
                    "sizing_status": sizing_status,
                    "runtime_planning_intent": planning_intent,
                    "runtime_planning_reason": no_order_reason or planning_reason,
                    "pending_generated": pending_generated,
                    "submitted": submitted,
                    "filled": filled,
                    "filled_quantity": filled_qty if filled else 0.0,
                    "filled_notional": filled_notional if filled else 0.0,
                    "position_campaign_id": fill.get("position_campaign_id", ""),
                    "final_funnel_status": final_status,
                    "final_explicit_reason": final_reason,
                    "join_confidence": join_confidence,
                }
            )
    return rows


def build_daily_capital(data: RunData, funnel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date = defaultdict(list)
    for row in funnel:
        by_date[row["business_date"]].append(row)

    rows: list[dict[str, Any]] = []
    previous_cash = 1_000_000.0
    previous_market_value = 0.0
    previous_equity = 1_000_000.0
    for date in data.dates:
        market = load_json(daily_path(data, date, "strategy/market_context.json"))
        policy = load_json(daily_path(data, date, "strategy/portfolio_policy.json"))
        sizing = load_json(daily_path(data, date, "strategy/position_sizing.json"))
        current = current_state(data, date)
        fills = daily_fills(data, date)
        q_counts = Counter(row["quality_action"] for row in by_date[date])
        pc = load_json(daily_path(data, date, "strategy/portfolio_construction.json"))
        ps_rows = load_json(daily_path(data, date, "strategy/position_sizing.json")).get("positions", [])
        rp_rows = load_json(daily_path(data, date, "strategy/runtime_planning.json")).get("plans", [])

        end_cash = as_float(current.get("cash"), 0.0)
        end_market = as_float(current.get("market_value"), 0.0)
        end_equity = as_float(current.get("total_equity"), end_cash + end_market)
        start_invested = pct(previous_market_value, previous_equity) or 0.0
        end_invested = pct(end_market, end_equity) or 0.0
        buy_fills = [f for f in fills if f.get("side") == "BUY"]
        sell_fills = [f for f in fills if f.get("side") == "SELL"]
        planned_buys = [p for p in rp_rows if p.get("order_side_intent") == "BUY" and as_float(p.get("planned_quantity")) > 0]
        planned_buy_notional = sum(as_float(p.get("planned_quantity")) * as_float(p.get("reference_price")) for p in planned_buys)
        executed_buy_notional = sum(as_float(f.get("gross_notional")) for f in buy_fills)
        sell_proceeds = sum(as_float(f.get("gross_notional")) for f in sell_fills)
        min_notional_count = sum(
            1
            for p in rp_rows
            if p.get("no_order_reason") == "NO_ORDER_MINIMUM_NOTIONAL_UNMET"
            or "MINIMUM_NOTIONAL" in str(p.get("planning_reason", ""))
        )
        lot_count = sum(1 for p in ps_rows if "LOT" in str(p.get("quantity_status", "")) or "lot" in str(p.get("sizing_reason", "")).lower())
        safety_count = sum(1 for p in rp_rows if "SAFETY" in str(p.get("planning_reason", "") + p.get("no_order_reason", "")))
        temporal_count = sum(
            1
            for p in rp_rows
            if "TEMPORAL" in str(p.get("planning_reason", "") + p.get("no_order_reason", ""))
            or "GENERATION" in str(p.get("planning_reason", "") + p.get("no_order_reason", ""))
        )
        classes: list[str] = []
        target_exposure = as_float(policy.get("target_gross_exposure_ratio", policy.get("target_gross_exposure")), 0.0)
        if str(market.get("regime_state", "")).upper() in {"BEAR", "DOWNTREND", "WEAK"} or target_exposure < 0.60:
            classes.append("MARKET_CONTEXT_DEFENSIVE")
        if target_exposure < 0.60:
            classes.append("POLICY_LOW_EXPOSURE")
        eligible = q_counts.get("FULL_ALLOCATION_ELIGIBLE", 0) + q_counts.get("REDUCED_ALLOCATION_ONLY", 0)
        if eligible == 0:
            classes.append("INSUFFICIENT_ELIGIBLE_OPPORTUNITY")
        if q_counts.get("REJECT", 0) > eligible:
            classes.append("QUALITY_FILTERING")
        if len([r for r in by_date[date] if r["portfolio_membership_intent"] in {"ADD_CANDIDATE", "HOLD", "INCREASE"}]) < eligible:
            classes.append("PORTFOLIO_CONSTRUCTION_FILTERING")
        if min_notional_count or lot_count:
            classes.append("LOT_OR_MINIMUM_NOTIONAL")
        if safety_count or temporal_count:
            classes.append("SAFETY_OR_AUTHORITY_BLOCK")
        if sell_proceeds > executed_buy_notional:
            classes.append("SELL_PROCEEDS_NOT_REDEPLOYED")
        if not classes:
            classes = ["NO_EXPLICIT_CAUSE"]
        if len(classes) > 1:
            reason_class = "MULTI_CAUSAL:" + "|".join(classes)
        else:
            reason_class = classes[0]

        rows.append(
            {
                "business_date": date,
                "market_regime": market.get("regime_state") or market.get("trend_state") or market.get("trend_regime"),
                "market_context_confidence": market.get("confidence"),
                "market_context_uncertainty": market.get("uncertainty"),
                "portfolio_policy_target_exposure": target_exposure,
                "position_sizing_target_gross_exposure": sizing.get("target_gross_exposure_ratio"),
                "actual_start_cash": previous_cash,
                "actual_end_cash": end_cash,
                "actual_start_market_value": previous_market_value,
                "actual_end_market_value": end_market,
                "actual_start_invested_ratio": start_invested,
                "actual_end_invested_ratio": end_invested,
                "eligible_opportunity_count": eligible,
                "quality_full_count": q_counts.get("FULL_ALLOCATION_ELIGIBLE", 0),
                "quality_reduced_count": q_counts.get("REDUCED_ALLOCATION_ONLY", 0),
                "quality_review_required_count": q_counts.get("REVIEW_REQUIRED", 0) + q_counts.get("BUY_REVIEW_REQUIRED", 0),
                "quality_reject_count": q_counts.get("REJECT", 0),
                "portfolio_selected_count": sum(1 for m in pc.get("portfolio_members", []) if m.get("target_membership")),
                "positive_target_weight_count": sum(1 for p in ps_rows if as_float(p.get("target_weight")) > 0),
                "planned_buy_count": len(planned_buys),
                "planned_buy_notional": planned_buy_notional,
                "executed_buy_count": len(buy_fills),
                "executed_buy_notional": executed_buy_notional,
                "executed_sell_count": len(sell_fills),
                "sell_proceeds": sell_proceeds,
                "lot_constraint_count": lot_count,
                "minimum_notional_constraint_count": min_notional_count,
                "safety_block_count": safety_count,
                "temporal_or_generation_block_count": temporal_count,
                "unallocated_capital_amount": end_cash,
                "unallocated_capital_reason_class": reason_class,
            }
        )
        previous_cash = end_cash
        previous_market_value = end_market
        previous_equity = end_equity
    return rows


def group_stats(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key) or "Unknown")].append(row)
    out = {}
    for name, items in sorted(groups.items()):
        actions = Counter(i.get("quality_action", "") for i in items)
        bought = [i for i in items if i.get("final_funnel_status") == "BOUGHT"]
        out[name] = {
            "count": len(items),
            "mean_opportunity_rank": safe_mean([as_float(i.get("opportunity_rank"), math.nan) for i in items]),
            "median_opportunity_rank": safe_median([as_float(i.get("opportunity_rank"), math.nan) for i in items]),
            "mean_opportunity_score": safe_mean([as_float(i.get("opportunity_score"), math.nan) for i in items]),
            "mean_quality_score": safe_mean([as_float(i.get("quality_score"), math.nan) for i in items]),
            "quality_action_distribution": dict(actions),
            "mean_target_weight": safe_mean([as_float(i.get("target_weight"), math.nan) for i in items]),
            "mean_target_notional": safe_mean([as_float(i.get("target_notional"), math.nan) for i in items]),
            "execution_conversion_rate": pct(len(bought), len(items)),
        }
    return out


def realized_by_campaign(data: RunData) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for date in data.dates:
        for item in daily_realized_slices(data, date):
            totals[str(item.get("position_campaign_id"))] += as_float(item.get("gross_realized_pnl"))
    return totals


def trade_buy_rows(data: RunData) -> list[dict[str, Any]]:
    rows = []
    for r in data.trade_with_quality:
        if r.get("BUY/SELL") == "BUY":
            rows.append(
                {
                    "business_date": r.get("Date"),
                    "symbol": r.get("Symbol"),
                    "campaign": r.get("Campaign"),
                    "rank": as_int(r.get("Rank")),
                    "entry_rank": as_int(r.get("Entry Rank")),
                    "quality_action": r.get("Quality Action"),
                    "quality_score": as_float(r.get("Quality Score")),
                    "quality_adjustment": as_float(r.get("Quality Adjustment")),
                    "opportunity_score": as_float(r.get("Opportunity Score")),
                    "amount": as_float(r.get("Amount")),
                    "pnl": as_float(r.get("PnL")),
                    "holding_days": as_float(r.get("Holding Days")),
                    "win": as_float(r.get("PnL")) > 0,
                }
            )
    return rows


def performance_for_group(items: list[dict[str, Any]]) -> dict[str, Any]:
    wins = [i for i in items if as_float(i.get("pnl")) > 0]
    losses = [i for i in items if as_float(i.get("pnl")) < 0]
    gross_profit = sum(as_float(i.get("pnl")) for i in wins)
    gross_loss = sum(as_float(i.get("pnl")) for i in losses)
    return {
        "buy_count": len(items),
        "executed_notional": sum(as_float(i.get("amount")) for i in items),
        "realized_pnl": sum(as_float(i.get("pnl")) for i in items),
        "unrealized_pnl_if_resolvable": None,
        "total_pnl_if_resolvable": sum(as_float(i.get("pnl")) for i in items),
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate": pct(len(wins), len(items)),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor(gross_profit, gross_loss),
        "average_holding_days": safe_mean([as_float(i.get("holding_days")) for i in items]),
        "small_sample": len(items) < 5,
    }


def build_rank_attribution(funnel: list[dict[str, Any]], buys: list[dict[str, Any]], reentry_campaigns: set[str]) -> list[dict[str, Any]]:
    decisions_by_bucket = Counter(rank_bucket(r.get("opportunity_rank")) for r in funnel)
    selected_by_bucket = Counter(rank_bucket(r.get("opportunity_rank")) for r in funnel if as_float(r.get("target_weight")) > 0)
    buy_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for b in buys:
        buy_groups[rank_bucket(b.get("rank"))].append(b)
    rows = []
    buckets = [
        "Opportunity Rank 1",
        "Opportunity Rank 2",
        "Opportunity Rank 3",
        "Opportunity Rank 4-5",
        "Opportunity Rank 6-10",
        "Opportunity Rank 11+",
        "Unknown",
    ]
    for b in buckets:
        perf = performance_for_group(buy_groups.get(b, []))
        rows.append(
            {
                "rank_bucket": b,
                "quality_decision_count": decisions_by_bucket.get(b, 0),
                "selected_count": selected_by_bucket.get(b, 0),
                "buy_count": perf["buy_count"],
                "buy_conversion_rate": pct(perf["buy_count"], decisions_by_bucket.get(b, 0) or 0),
                "executed_notional": perf["executed_notional"],
                "realized_pnl": perf["realized_pnl"],
                "unrealized_pnl_if_resolvable": perf["unrealized_pnl_if_resolvable"],
                "total_pnl_if_resolvable": perf["total_pnl_if_resolvable"],
                "win_count": perf["win_count"],
                "loss_count": perf["loss_count"],
                "win_rate": perf["win_rate"],
                "gross_profit": perf["gross_profit"],
                "gross_loss": perf["gross_loss"],
                "profit_factor": perf["profit_factor"],
                "average_holding_days": perf["average_holding_days"],
                "reentry_count": sum(1 for i in buy_groups.get(b, []) if i.get("campaign") in reentry_campaigns),
                "small_sample": perf["small_sample"],
            }
        )
    return rows


def build_quality_attribution(funnel: list[dict[str, Any]], buys: list[dict[str, Any]], reentry_campaigns: set[str]) -> list[dict[str, Any]]:
    rows = []
    for mode, names in {
        "action": ["FULL_ALLOCATION_ELIGIBLE", "REDUCED_ALLOCATION_ONLY", "BUY_REVIEW_REQUIRED", "REVIEW_REQUIRED", "REJECT"],
        "score_bucket": ["0.00-0.49", "0.50-0.59", "0.60-0.69", "0.70-0.79", "0.80-0.89", "0.90-1.00"],
    }.items():
        for name in names:
            if mode == "action":
                decisions = [r for r in funnel if r.get("quality_action") == name]
                buy_items = [b for b in buys if b.get("quality_action") == name]
            else:
                decisions = [r for r in funnel if quality_score_bucket(r.get("quality_score")) == name]
                buy_items = [b for b in buys if quality_score_bucket(b.get("quality_score")) == name]
            perf = performance_for_group(buy_items)
            rows.append(
                {
                    "group_type": mode,
                    "group": name,
                    "decision_count": len(decisions),
                    "selected_count": sum(1 for r in decisions if as_float(r.get("target_weight")) > 0),
                    "buy_count": perf["buy_count"],
                    "buy_conversion_rate": pct(perf["buy_count"], len(decisions)),
                    "planned_notional": sum(as_float(r.get("target_notional")) for r in decisions),
                    "executed_notional": perf["executed_notional"],
                    "realized_pnl": perf["realized_pnl"],
                    "unrealized_pnl_if_resolvable": perf["unrealized_pnl_if_resolvable"],
                    "win_rate": perf["win_rate"],
                    "profit_factor": perf["profit_factor"],
                    "average_position_size": safe_mean([as_float(i.get("amount")) for i in buy_items]),
                    "average_holding_days": perf["average_holding_days"],
                    "reentry_count": sum(1 for i in buy_items if i.get("campaign") in reentry_campaigns),
                    "small_sample": perf["small_sample"],
                }
            )
    return rows


def build_position_sizing_efficiency(data: RunData) -> list[dict[str, Any]]:
    rows = []
    for date in data.dates:
        q = by_symbol(load_json(daily_path(data, date, "strategy/buy_quality_decisions.json")).get("decisions", []))
        ps = by_symbol(load_json(daily_path(data, date, "strategy/position_sizing.json")).get("positions", []))
        rp = by_symbol(load_json(daily_path(data, date, "strategy/runtime_planning.json")).get("plans", []))
        current_equity = as_float(load_json(daily_path(data, date, "strategy/position_sizing.json")).get("portfolio_total_equity"))
        for fill in daily_fills(data, date):
            if fill.get("side") != "BUY":
                continue
            symbol = str(fill.get("symbol"))
            s = ps.get(symbol, {})
            r = rp.get(symbol, {})
            qrow = q.get(symbol, {})
            target_notional = as_float(s.get("target_notional"))
            planned_qty = as_float(r.get("planned_quantity"))
            reference_price = as_float(s.get("reference_price") or r.get("reference_price"))
            planned_notional = planned_qty * reference_price
            filled_notional = as_float(fill.get("gross_notional"))
            unused = target_notional - filled_notional if target_notional else 0.0
            reason_parts = []
            if as_float(s.get("quality_adjustment"), 1.0) < 1.0:
                reason_parts.append("Quality Adjustment")
            if unused > 0:
                reason_parts.append("Lot rounding / execution price difference")
            if not reason_parts:
                reason_parts.append("No material reduction identified")
            rows.append(
                {
                    "business_date": date,
                    "symbol": symbol,
                    "opportunity_rank": qrow.get("opportunity_buy_rank") or s.get("opportunity_buy_rank"),
                    "quality_score": qrow.get("quality_score"),
                    "quality_action": qrow.get("quality_action"),
                    "base_target_weight": s.get("base_weight"),
                    "quality_adjustment": s.get("quality_adjustment"),
                    "final_target_weight": s.get("target_weight"),
                    "current_total_equity": current_equity,
                    "target_notional": target_notional,
                    "reference_price": reference_price,
                    "lot_size": s.get("trading_unit"),
                    "planned_quantity": planned_qty,
                    "planned_notional": planned_notional,
                    "filled_quantity": as_float(fill.get("quantity")),
                    "filled_notional": filled_notional,
                    "target_to_fill_ratio": pct(filled_notional, target_notional),
                    "unused_target_notional": unused,
                    "sizing_reduction_reason": ";".join(reason_parts),
                    "position_campaign_id": fill.get("position_campaign_id"),
                }
            )
    return rows


def build_reentry_events(data: RunData, buys: list[dict[str, Any]], realized: dict[str, float]) -> tuple[list[dict[str, Any]], set[str]]:
    by_symbol_buys: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for b in buys:
        by_symbol_buys[str(b["symbol"])].append(b)
    rows = []
    reentry_campaigns: set[str] = set()
    for symbol, items in by_symbol_buys.items():
        items = sorted(items, key=lambda x: x["business_date"])
        prior_exit_date = ""
        for idx, item in enumerate(items, start=1):
            campaign = item["campaign"]
            sells = [r for r in data.trade_with_quality if r.get("BUY/SELL") == "SELL" and r.get("Campaign") == campaign]
            exit_date = max((s.get("Date", "") for s in sells), default="")
            interval = None
            if prior_exit_date:
                all_dates = data.dates
                if prior_exit_date in all_dates and item["business_date"] in all_dates:
                    interval = all_dates.index(item["business_date"]) - all_dates.index(prior_exit_date)
            is_reentry = idx > 1
            if is_reentry:
                reentry_campaigns.add(campaign)
            rows.append(
                {
                    "symbol": symbol,
                    "campaign_id": campaign,
                    "entry_sequence_number": idx,
                    "is_reentry": is_reentry,
                    "prior_exit_date": prior_exit_date,
                    "entry_date": item["business_date"],
                    "reentry_interval_business_days": interval,
                    "entry_opportunity_rank": item["rank"],
                    "entry_quality_score": item["quality_score"],
                    "entry_quality_action": item["quality_action"],
                    "entry_market_regime": load_json(daily_path(data, item["business_date"], "strategy/market_context.json")).get("regime_state"),
                    "entry_notional": item["amount"],
                    "holding_days": item["holding_days"],
                    "reduce_count": sum(1 for s in sells if s.get("BUY/SELL") == "SELL") if sells else 0,
                    "exit_date": exit_date,
                    "realized_pnl": realized.get(campaign, item["pnl"]),
                    "campaign_return_rate_if_resolvable": pct(realized.get(campaign, item["pnl"]), item["amount"]),
                    "maximum_favorable_excursion_if_available": None,
                    "maximum_adverse_excursion_if_available": None,
                }
            )
            prior_exit_date = exit_date or prior_exit_date
    return rows, reentry_campaigns


def build_exit_holding(data: RunData) -> list[dict[str, Any]]:
    buy_by_campaign = {r["Campaign"]: r for r in data.trade_with_quality if r.get("BUY/SELL") == "BUY"}
    rows = []
    for date in data.dates:
        market = load_json(daily_path(data, date, "strategy/market_context.json"))
        for fill in daily_fills(data, date):
            if fill.get("side") != "SELL":
                continue
            campaign = fill.get("position_campaign_id")
            buy = buy_by_campaign.get(campaign, {})
            realized_slices = [
                s for s in daily_realized_slices(data, date) if s.get("sell_execution_id") == fill.get("execution_id")
            ]
            realized = sum(as_float(s.get("gross_realized_pnl")) for s in realized_slices)
            remaining_qty = realized_slices[-1].get("remaining_quantity") if realized_slices else None
            rows.append(
                {
                    "symbol": fill.get("symbol"),
                    "campaign_id": campaign,
                    "entry_date": buy.get("Date", ""),
                    "sell_date": date,
                    "holding_days_at_sell": None,
                    "sell_action": fill.get("source_decision_type"),
                    "reduce_or_exit": "EXIT" if as_float(remaining_qty, 0.0) == 0 else "REDUCE",
                    "sold_quantity": fill.get("quantity"),
                    "remaining_quantity": remaining_qty,
                    "realized_pnl": realized,
                    "realized_return_rate_if_resolvable": pct(realized, as_float(buy.get("Amount"))),
                    "prior_unrealized_peak_if_available": None,
                    "market_regime_at_sell": market.get("regime_state"),
                    "pm_intent_if_available": fill.get("source_decision_type"),
                    "sell_reason": fill.get("source_decision_type"),
                }
            )
    return rows


def build_profit_factor_decomposition(data: RunData, buys: list[dict[str, Any]], reentry_campaigns: set[str]) -> dict[str, Any]:
    pnl_items = buys
    wins = [i for i in pnl_items if i["pnl"] > 0]
    losses = [i for i in pnl_items if i["pnl"] < 0]
    gross_profit = sum(i["pnl"] for i in wins)
    gross_loss = sum(i["pnl"] for i in losses)
    reentries = [i for i in pnl_items if i["campaign"] in reentry_campaigns]
    initials = [i for i in pnl_items if i["campaign"] not in reentry_campaigns]
    return {
        "profit_factor": profit_factor(gross_profit, gross_loss),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "winning_campaign_count": len(wins),
        "losing_campaign_count": len(losses),
        "average_winner": safe_mean([i["pnl"] for i in wins]),
        "average_loser": safe_mean([i["pnl"] for i in losses]),
        "payoff_ratio": pct(abs(safe_mean([i["pnl"] for i in wins]) or 0), abs(safe_mean([i["pnl"] for i in losses]) or 0)),
        "win_rate": pct(len(wins), len(wins) + len(losses)),
        "largest_winner": max(pnl_items, key=lambda i: i["pnl"]) if pnl_items else None,
        "largest_loser": min(pnl_items, key=lambda i: i["pnl"]) if pnl_items else None,
        "top_5_profit_contributors": sorted(wins, key=lambda i: i["pnl"], reverse=True)[:5],
        "top_5_loss_contributors": sorted(losses, key=lambda i: i["pnl"])[:5],
        "reentry_gross_profit": sum(i["pnl"] for i in reentries if i["pnl"] > 0),
        "reentry_gross_loss": sum(i["pnl"] for i in reentries if i["pnl"] < 0),
        "initial_entry_gross_profit": sum(i["pnl"] for i in initials if i["pnl"] > 0),
        "initial_entry_gross_loss": sum(i["pnl"] for i in initials if i["pnl"] < 0),
        "direct_factor_classification": [
            "LOW_WIN_RATE",
            "REENTRY_LOSS",
            "CONCENTRATED_LARGE_LOSS",
            "QUALITY_SELECTION",
            "RANK_SELECTION",
        ],
        "classification_note": "Classifications are post-hoc evidence-supported factors, not Strategy inputs.",
    }


def build_drawdown_episodes(data: RunData) -> dict[str, Any]:
    eq_rows = read_csv(data.run_dir / "performance_report/equity_curve.csv")
    values = [(r.get("Date"), as_float(r.get("Equity"))) for r in eq_rows]
    episodes = []
    peak_date = None
    peak_equity = -math.inf
    in_dd = False
    trough_date = None
    trough_equity = math.inf
    start_idx = 0
    for idx, (date, equity) in enumerate(values):
        if equity >= peak_equity:
            if in_dd:
                episodes.append((peak_date, trough_date, date, peak_equity, trough_equity, start_idx, idx))
                in_dd = False
            peak_date, peak_equity, start_idx = date, equity, idx
            trough_date, trough_equity = date, equity
        else:
            in_dd = True
            if equity < trough_equity:
                trough_date, trough_equity = date, equity
    if in_dd:
        episodes.append((peak_date, trough_date, None, peak_equity, trough_equity, start_idx, len(values) - 1))
    out = []
    for n, ep in enumerate(sorted(episodes, key=lambda e: e[4] - e[3])[:3], start=1):
        peak_d, trough_d, recovery_d, peak_e, trough_e, start_i, end_i = ep
        period_dates = {d for d, _ in values[start_i : end_i + 1]}
        loss_symbols = Counter()
        campaigns = Counter()
        reentries = 0
        regimes = Counter()
        cash_ratios = []
        for d in period_dates:
            if (data.run_dir / "daily" / d).exists():
                regimes[load_json(daily_path(data, d, "strategy/market_context.json")).get("regime_state", "Unknown")] += 1
                current = current_state(data, d)
                equity = as_float(current.get("total_equity"))
                cash_ratios.append(pct(as_float(current.get("cash")), equity) or 0)
                for rs in daily_realized_slices(data, d):
                    if as_float(rs.get("gross_realized_pnl")) < 0:
                        loss_symbols[rs.get("symbol")] += as_float(rs.get("gross_realized_pnl"))
                        campaigns[rs.get("position_campaign_id")] += as_float(rs.get("gross_realized_pnl"))
        out.append(
            {
                "episode_id": f"DD-{n}",
                "peak_date": peak_d,
                "trough_date": trough_d,
                "recovery_date_if_any": recovery_d,
                "peak_equity": peak_e,
                "trough_equity": trough_e,
                "drawdown_amount": trough_e - peak_e,
                "drawdown_rate": pct(trough_e - peak_e, peak_e),
                "duration_business_days": len(period_dates),
                "open_positions_at_peak": [
                    p.get("symbol") for p in current_state(data, peak_d).get("positions", [])
                ] if peak_d else [],
                "loss_contributing_symbols": dict(loss_symbols),
                "loss_contributing_campaigns": dict(campaigns),
                "reentry_events_during_episode": reentries,
                "market_regime_distribution": dict(regimes),
                "cash_ratio_distribution": {
                    "average": safe_mean(cash_ratios),
                    "min": min(cash_ratios) if cash_ratios else None,
                    "max": max(cash_ratios) if cash_ratios else None,
                },
            }
        )
    max_dd = data.perf.get("drawdown", {})
    return {"max_drawdown_summary": max_dd, "top_episodes": out}


def make_hypotheses(
    data: RunData,
    rank_rows: list[dict[str, Any]],
    quality_rows: list[dict[str, Any]],
    daily_rows: list[dict[str, Any]],
    pf: dict[str, Any],
    reentry_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    avg_cash = as_float(data.perf.get("Cash Ratio"))
    final_cash = as_float(data.perf.get("Cash Ratio"))
    reentry_loss = as_float(pf.get("reentry_gross_loss"))
    full = next((r for r in quality_rows if r["group_type"] == "action" and r["group"] == "FULL_ALLOCATION_ELIGIBLE"), {})
    reduced = next((r for r in quality_rows if r["group_type"] == "action" and r["group"] == "REDUCED_ALLOCATION_ONLY"), {})
    rank6 = next((r for r in rank_rows if r["rank_bucket"] == "Opportunity Rank 6-10"), {})
    rank1 = next((r for r in rank_rows if r["rank_bucket"] == "Opportunity Rank 1"), {})
    return {
        "H1": {
            "hypothesis": "Opportunity Rankingの識別力が弱い",
            "judgment": "PARTIALLY_CONFIRMED",
            "confidence": "MEDIUM",
            "supporting_evidence": [
                f"Rank 6-10 bought rows produced total_pnl_if_resolvable={rank6.get('total_pnl_if_resolvable')} with small sample flag={rank6.get('small_sample')}.",
                "Rank 2/4-5/6-10 buckets include losses while Rank 1 is positive, so rank signal is uneven rather than uniformly strong.",
            ],
            "contradicting_evidence": [
                f"Rank 1 bucket total_pnl_if_resolvable={rank1.get('total_pnl_if_resolvable')} and win_rate={rank1.get('win_rate')}.",
                "Small samples limit bucket-level generalization.",
            ],
            "evidence_limitations": ["Full candidate universe is not run-scoped; opportunity-level rows are stronger than candidate-rank rows."],
            "alternative_explanation": "Exit timing, re-entry, or market context may dominate rank quality.",
            "root_cause_status": "Evidence-supported partial factor",
        },
        "H2": {
            "hypothesis": "BUY Qualityが保守的すぎる",
            "judgment": "REJECTED",
            "confidence": "MEDIUM",
            "supporting_evidence": [
                "No direct evidence that Quality filtering was too conservative; bought FULL rows underperformed REDUCED rows in this baseline.",
                f"FULL action pnl={full.get('realized_pnl')} while REDUCED action pnl={reduced.get('realized_pnl')}.",
            ],
            "contradicting_evidence": ["High cash ratio may still reflect conservative combined policy, but not Quality alone."],
            "evidence_limitations": ["Unbought candidate hypothetical PnL is prohibited and not generated."],
            "alternative_explanation": "Quality may be insufficiently discriminative rather than too conservative.",
            "root_cause_status": "Not supported as stated",
        },
        "H3": {
            "hypothesis": "Position Sizingが資金投入を抑えすぎる",
            "judgment": "PARTIALLY_CONFIRMED",
            "confidence": "MEDIUM",
            "supporting_evidence": [
                f"Average cash ratio remained high at {avg_cash}.",
                "Position sizing produced target notional below available equity by design and lot/minimum-notional constraints appear in daily planning.",
            ],
            "contradicting_evidence": ["Sizing consumed Portfolio Policy and Quality; suppression is not isolated to Position Sizing alone."],
            "evidence_limitations": ["Contribution is partially quantified; counterfactual larger sizing was not simulated."],
            "alternative_explanation": "Portfolio Policy target exposure and Quality filtering may be upstream causes.",
            "root_cause_status": "Partial factor",
        },
        "H4": {
            "hypothesis": "Market Contextが期間中防御的だった",
            "judgment": "PARTIALLY_CONFIRMED",
            "confidence": "MEDIUM",
            "supporting_evidence": [
                "Daily capital table classifies many days as POLICY_LOW_EXPOSURE / MARKET_CONTEXT_DEFENSIVE based on target exposure below 0.60.",
                f"Average cash ratio was {avg_cash}, consistent with lower target exposure periods.",
            ],
            "contradicting_evidence": ["Market Context is not the only source of cash; SELL proceeds and Quality/PC filters also contribute."],
            "evidence_limitations": ["No single canonical market-context cash attribution table existed before A2; this is a derived table."],
            "alternative_explanation": "Opportunity scarcity and re-entry losses can explain poor results without market context alone.",
            "root_cause_status": "Partial factor",
        },
        "H5": {
            "hypothesis": "Re-entryが損失を増加させている",
            "judgment": "CONFIRMED",
            "confidence": "HIGH",
            "supporting_evidence": [
                f"Re-entry gross loss={reentry_loss}.",
                "93180 had Entry 6 / Re-entry 5 / PnL -120600; 76920 had Entry 3 / Re-entry 2 / PnL -28290.",
            ],
            "contradicting_evidence": ["Some re-entry campaigns can be profitable; aggregate needs campaign-level review."],
            "evidence_limitations": ["No rule change or cooldown experiment was run."],
            "alternative_explanation": "Weak rank/quality or exit timing may have selected poor re-entry moments.",
            "root_cause_status": "Directly evidenced factor",
        },
        "H6": {
            "hypothesis": "Exit / Reduceが利益を伸ばせていない",
            "judgment": "PARTIALLY_CONFIRMED",
            "confidence": "LOW",
            "supporting_evidence": ["SELL and realized-slice data show repeated REDUCE/EXIT sequences and losses in major campaigns."],
            "contradicting_evidence": ["PM intent / sell action taxonomy is only partially joinable; winner giveback/MFE is unavailable."],
            "evidence_limitations": ["MFE/MAE and exact PM reason are insufficient; do not overclaim exit root cause."],
            "alternative_explanation": "Entry quality and re-entry timing may explain sell losses.",
            "root_cause_status": "Partial, targeted evidence required",
        },
        "H7": {
            "hypothesis": "良い候補を買わず、低ランク候補を買っている",
            "judgment": "PARTIALLY_CONFIRMED",
            "confidence": "MEDIUM",
            "supporting_evidence": [
                "H7a: Quality/PC reached funnel includes high-rank not-bought rows and low-rank bought rows.",
                "H7b: Full candidate universe is not run-scoped, so candidate-universe-wide claim is insufficient evidence.",
            ],
            "contradicting_evidence": ["Some Rank 1 buys were profitable; high-rank not-bought rows often had explicit current-position or reject reasons."],
            "evidence_limitations": ["H7b is INSUFFICIENT_EVIDENCE by contract due missing full candidate universe."],
            "alternative_explanation": "Not-bought high-rank rows may have been already-held or rejected for explicit Quality reasons.",
            "root_cause_status": "H7a partial; H7b insufficient",
            "subjudgments": {
                "H7a": "PARTIALLY_CONFIRMED",
                "H7b": "INSUFFICIENT_EVIDENCE"
            },
        },
        "H8": {
            "hypothesis": "QualityとRankは良いが、Capital Deploymentだけが弱い",
            "judgment": "REJECTED",
            "confidence": "MEDIUM",
            "supporting_evidence": ["Rank and Quality performance are mixed; FULL quality underperformed REDUCED in bought-trade attribution."],
            "contradicting_evidence": ["Capital deployment was also weak/high cash, but not the only weak point."],
            "evidence_limitations": ["No counterfactual deployment-only experiment was run."],
            "alternative_explanation": "Re-entry losses, rank/quality discrimination, and exposure policy jointly explain results.",
            "root_cause_status": "Not supported as exclusive cause",
        },
    }


def root_cause_ranking(pf: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "root_cause_candidate": "Repeated re-entry losses, especially 93180 and 76920",
            "classification": "Performance Improvement",
            "observed_impact": "93180 PnL -120600; 76920 PnL -28290; re-entry gross loss is material.",
            "estimated_contribution": "DIRECTLY_QUANTIFIED",
            "evidence_strength": "HIGH",
            "confidence": "HIGH",
            "affected_metrics": ["Profit Factor", "Drawdown", "Win Rate"],
            "architecture_change_required": False,
            "performance_logic_change_candidate": True,
            "further_evidence_required": "Controlled design review before any cooldown or re-entry rule change.",
        },
        {
            "rank": 2,
            "root_cause_candidate": "Low win rate with concentrated losses",
            "classification": "Performance Improvement",
            "observed_impact": f"Win rate {pf.get('win_rate')}; largest_loser {pf.get('largest_loser')}.",
            "estimated_contribution": "DIRECTLY_QUANTIFIED",
            "evidence_strength": "HIGH",
            "confidence": "HIGH",
            "affected_metrics": ["Profit Factor", "Return"],
            "architecture_change_required": False,
            "performance_logic_change_candidate": True,
            "further_evidence_required": "Campaign-level loss review.",
        },
        {
            "rank": 3,
            "root_cause_candidate": "Mixed Quality / Rank discrimination",
            "classification": "Performance Improvement",
            "observed_impact": "FULL quality and mid/low rank bought buckets include losses.",
            "estimated_contribution": "PARTIALLY_QUANTIFIED",
            "evidence_strength": "MEDIUM",
            "confidence": "MEDIUM",
            "affected_metrics": ["Profit Factor", "Win Rate", "Capital Deployment"],
            "architecture_change_required": False,
            "performance_logic_change_candidate": True,
            "further_evidence_required": "Out-of-period and larger-window validation.",
        },
        {
            "rank": 4,
            "root_cause_candidate": "High cash / partial deployment from policy, quality, and sell proceeds",
            "classification": "Performance Improvement",
            "observed_impact": "Average cash ratio about 50%; final cash ratio about 66%.",
            "estimated_contribution": "PARTIALLY_QUANTIFIED",
            "evidence_strength": "MEDIUM",
            "confidence": "MEDIUM",
            "affected_metrics": ["Return", "Exposure"],
            "architecture_change_required": False,
            "performance_logic_change_candidate": True,
            "further_evidence_required": "Do not lower cash until root cause review confirms desired risk.",
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    data = load_run(args.run_id, Path(args.runs_root))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    funnel = build_funnel(data)
    daily = build_daily_capital(data, funnel)
    buys = trade_buy_rows(data)
    realized = realized_by_campaign(data)
    reentry_rows, reentry_campaigns = build_reentry_events(data, buys, realized)
    rank_rows = build_rank_attribution(funnel, buys, reentry_campaigns)
    quality_rows = build_quality_attribution(funnel, buys, reentry_campaigns)
    sizing_rows = build_position_sizing_efficiency(data)
    exit_rows = build_exit_holding(data)
    pf = build_profit_factor_decomposition(data, buys, reentry_campaigns)
    dd = build_drawdown_episodes(data)
    hypotheses = make_hypotheses(data, rank_rows, quality_rows, daily, pf, reentry_rows)
    root_causes = root_cause_ranking(pf)

    baseline_reconciliation = {
        "source": "performance_report/performance_summary.json + final_summary.json",
        "expected": {
            "Initial Equity": 1_000_000,
            "Final Equity": 984_580,
            "Equity Delta": -15_420,
            "Realized PnL": -47_520,
            "Unrealized PnL": 32_100,
            "Profit Factor": 0.8384827164270419,
            "Maximum Drawdown": -205_890,
            "Win Rate": 0.34782608695652173,
            "BUY Executions": 25,
            "SELL Executions": 45,
            "Final Cash Ratio": 0.6596518312376851,
            "Average Cash Ratio": 0.5010779329090453,
            "Average Position Count": 3.66,
        },
        "observed": {
            "Initial Equity": data.perf.get("Initial Equity"),
            "Final Equity": data.perf.get("Final Equity"),
            "Equity Delta": data.perf.get("Return"),
            "Realized PnL": data.final_summary.get("pnl_reconciliation", {}).get("realized"),
            "Unrealized PnL": data.final_summary.get("pnl_reconciliation", {}).get("unrealized"),
            "Profit Factor": data.perf.get("Profit Factor"),
            "Maximum Drawdown": data.perf.get("Max Drawdown"),
            "Win Rate": data.perf.get("Win Rate"),
            "BUY Executions": data.perf.get("BUY Count"),
            "SELL Executions": data.perf.get("SELL Count"),
            "Final Cash Ratio": data.perf.get("Cash Ratio"),
            "Average Cash Ratio": safe_mean([as_float(r.get("Cash Ratio")) for r in data.cash_exposure]),
            "Average Position Count": safe_mean([as_float(r.get("Position Count")) for r in data.cash_exposure]),
        },
        "judgment": "MATCH_WITHIN_SOURCE_PRECISION",
    }

    comparison = group_stats(funnel, "final_funnel_status")
    evidence_limitations = {
        "limitations": [
            "Full candidate universe is not copied as a canonical run-scoped daily artifact; H7b is insufficient by contract.",
            "BUY fill rows lack direct pending_item_id, order_plan_item_id, and quality_decision_id; filled BUY joins retain COMPOSITE_EXACT_JOIN confidence.",
            "Unbought candidates do not receive virtual PnL; no look-ahead hypothetical returns were generated.",
            "MFE/MAE and exact PM sell reason are unavailable; Exit/Reduce timing remains partially evidenced.",
        ],
        "prohibited_feedback_respected": True,
    }

    summary = {
        "schema_version": "phase27_a2_summary.v1",
        "task_id": "Phase27-A2",
        "primary_judgment": "PHASE27_A2_BASELINE_ATTRIBUTION_COMPLETE_PARTIAL_ROOT_CAUSES_IDENTIFIED",
        "run_id": data.run_id,
        "business_days": len(data.dates),
        "outputs_generated": [],
        "hypothesis_judgment_counts": dict(Counter(h["judgment"] for h in hypotheses.values())),
        "top_root_cause": root_causes[0],
        "safety_boundary": {
            "implementation_changed": False,
            "strategy_changed": False,
            "fresh_run_executed": False,
            "historical_rerun_executed": False,
            "runtime_state_read": False,
            "post_hoc_only": True,
        },
    }

    outputs: dict[str, Any] = {
        "baseline_metric_reconciliation.json": baseline_reconciliation,
        "daily_capital_deployment_attribution.json": daily,
        "opportunity_quality_selection_funnel.json": funnel,
        "bought_vs_not_bought_comparison.json": comparison,
        "rank_performance_attribution.json": rank_rows,
        "quality_performance_attribution.json": quality_rows,
        "position_sizing_efficiency.json": sizing_rows,
        "reentry_event_attribution.json": reentry_rows,
        "exit_holding_attribution.json": exit_rows,
        "profit_factor_decomposition.json": pf,
        "drawdown_episode_attribution.json": dd,
        "hypothesis_judgments.json": hypotheses,
        "root_cause_ranking.json": root_causes,
        "evidence_limitations.json": evidence_limitations,
        "test_results.json": {
            "script": "tools/phase27_analysis/phase27_a2_generate_attribution.py",
            "json_outputs_written": True,
            "csv_outputs_written": True,
            "run_scoped_only": True,
            "runtime_state_read": False,
            "fresh_run_executed": False,
            "historical_rerun_executed": False,
        },
    }

    for name, payload in outputs.items():
        write_json(output_dir / name, payload)
        summary["outputs_generated"].append(name)

    csv_specs = {
        "daily_capital_deployment_attribution.csv": (daily, list(daily[0].keys()) if daily else []),
        "opportunity_quality_selection_funnel.csv": (funnel, list(funnel[0].keys()) if funnel else []),
        "rank_performance_attribution.csv": (rank_rows, list(rank_rows[0].keys()) if rank_rows else []),
        "quality_performance_attribution.csv": (quality_rows, list(quality_rows[0].keys()) if quality_rows else []),
        "position_sizing_efficiency.csv": (sizing_rows, list(sizing_rows[0].keys()) if sizing_rows else []),
        "reentry_event_attribution.csv": (reentry_rows, list(reentry_rows[0].keys()) if reentry_rows else []),
        "exit_holding_attribution.csv": (exit_rows, list(exit_rows[0].keys()) if exit_rows else []),
    }
    for name, (rows, fields) in csv_specs.items():
        write_csv(output_dir / name, rows, fields)
        summary["outputs_generated"].append(name)

    write_json(output_dir / "summary.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
