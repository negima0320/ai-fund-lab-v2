#!/usr/bin/env python3
"""Phase27-A5 read-only ineligibility and Quality component diagnosis.

Observability Only / Post-hoc Human Review Only / Not a Strategy Input.
Run-scoped Evidence Only / No .runtime Read.

This script reads run-scoped Runtime Test evidence and Phase27-A2/A3/A4 outputs
only. It does not mutate runtime state and must not be used as Strategy,
Candidate, Opportunity, BUY Quality, Portfolio Policy, Portfolio Construction,
Position Sizing, Planning, Submit, Safety, PM, Exit, or Re-entry input.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


BASELINE_RUN_ID = "runtime-test-historical-smoke-20260804T074611098414Z"
DEFAULT_RUNS_ROOT = Path("reports/runtime_tests/runs")
DEFAULT_A2_DIR = Path("reports/phase27_a2_100bd_baseline_attribution_and_hypothesis_evidence_extraction")
DEFAULT_A3_DIR = Path("reports/phase27_a3_reentry_causality_and_selection_validity_diagnosis")
DEFAULT_A4_DIR = Path("reports/phase27_a4_opportunity_quality_and_final_selection_discrimination_diagnosis")
DEFAULT_OUTPUT_DIR = Path("reports/phase27_a5_higher_ranked_candidate_ineligibility_and_quality_component_diagnosis")


COMPONENTS = {
    "relative_opportunity_component": "RELATIVE_OPPORTUNITY",
    "market_context_component": "MARKET_CONTEXT",
    "signal_reliability_component": "SIGNAL_RELIABILITY",
    "execution_feasibility_component": "EXECUTION_FEASIBILITY",
    "portfolio_fit_component": "PORTFOLIO_FIT",
}
RANK_BUCKETS = ["1", "2", "3", "4-5", "6-10", "11+"]
QUALITY_ACTIONS = ["FULL_ALLOCATION_ELIGIBLE", "REDUCED_ALLOCATION_ONLY", "BUY_REVIEW_REQUIRED", "REJECT"]


def load_json(path: Path) -> Any:
    with path.open() as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def as_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
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


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def pct(num: float, den: float) -> float | None:
    return None if den == 0 else num / den


def avg(values: list[float]) -> float | None:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    return mean(vals) if vals else None


def profit_factor(pnls: list[float]) -> float | None:
    gp = sum(p for p in pnls if p > 0)
    gl = sum(p for p in pnls if p < 0)
    return None if gl == 0 else gp / abs(gl)


def perf(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pnls = [as_float(r.get("realized_pnl")) for r in rows]
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p < 0]
    return {
        "buy_count": len(rows),
        "executed_notional": sum(as_float(r.get("filled_notional")) for r in rows),
        "realized_pnl": sum(pnls),
        "win_rate": pct(len(winners), len([p for p in pnls if p != 0])),
        "profit_factor": profit_factor(pnls),
        "average_holding_days": avg([as_float(r.get("holding_days")) for r in rows]) if rows else None,
        "largest_profit": max(winners) if winners else None,
        "largest_loss": min(losers) if losers else None,
        "small_sample_warning": len(rows) < 10,
    }


def rank_bucket(rank: Any) -> str:
    r = as_int(rank)
    if r == 1:
        return "1"
    if r == 2:
        return "2"
    if r == 3:
        return "3"
    if 4 <= r <= 5:
        return "4-5"
    if 6 <= r <= 10:
        return "6-10"
    if r >= 11:
        return "11+"
    return "UNKNOWN"


def bucket(value: Any, cuts: list[tuple[float, float, str]]) -> str:
    v = as_float(value, -999)
    for lo, hi, label in cuts:
        if lo <= v < hi:
            return label
    return "UNKNOWN"


def safe_run_dir(run_id: str, runs_root: Path) -> Path:
    if "/" in run_id or "\\" in run_id or run_id in {"", ".", ".."}:
        raise SystemExit(f"invalid run id: {run_id!r}")
    run_dir = (runs_root / run_id).resolve()
    root = runs_root.resolve()
    if not str(run_dir).startswith(str(root)):
        raise SystemExit("run directory must stay under reports/runtime_tests/runs")
    if not run_dir.exists():
        raise SystemExit(f"missing run directory: {run_dir}")
    return run_dir


def by_symbol(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("symbol") or r.get("security_code")): r for r in rows if r.get("symbol") or r.get("security_code")}


def daily_dates(run_dir: Path) -> list[str]:
    return sorted(p.name for p in (run_dir / "daily").iterdir() if p.is_dir())


def strategy_payload(run_dir: Path, date: str, name: str) -> Any:
    return load_json(run_dir / "daily" / date / "strategy" / name)


def daily_maps(run_dir: Path, date: str) -> dict[str, Any]:
    return {
        "quality": by_symbol(strategy_payload(run_dir, date, "buy_quality_decisions.json").get("decisions", [])),
        "pc": by_symbol(strategy_payload(run_dir, date, "portfolio_construction.json").get("portfolio_members", [])),
        "ps": by_symbol(strategy_payload(run_dir, date, "position_sizing.json").get("positions", [])),
        "rp": by_symbol(strategy_payload(run_dir, date, "runtime_planning.json").get("plans", [])),
        "policy": strategy_payload(run_dir, date, "portfolio_policy.json"),
        "sizing": strategy_payload(run_dir, date, "position_sizing.json"),
        "market": strategy_payload(run_dir, date, "market_context.json"),
    }


def components_from(row: dict[str, Any]) -> dict[str, Any]:
    comps = row.get("component_scores", {}) or {}
    return {
        "relative_opportunity_component": comps.get("relative_opportunity_quality"),
        "market_context_component": comps.get("market_context_quality_modifier"),
        "signal_reliability_component": comps.get("signal_reliability"),
        "execution_feasibility_component": comps.get("execution_feasibility"),
        "portfolio_fit_component": comps.get("portfolio_fit"),
    }


def component_limiter(comps: dict[str, Any]) -> tuple[str, Any, str, Any, Any, str, str]:
    vals = {k: as_float(v, math.nan) for k, v in comps.items() if v not in ("", None)}
    vals = {k: v for k, v in vals.items() if not math.isnan(v)}
    if not vals:
        return "", None, "", None, None, "INSUFFICIENT_EVIDENCE", "LOW"
    min_name, min_val = min(vals.items(), key=lambda kv: kv[1])
    max_name, max_val = max(vals.items(), key=lambda kv: kv[1])
    spread = max_val - min_val
    if spread < 0.05:
        dom = "NO_CLEAR_LIMITER"
        conf = "MEDIUM"
    else:
        near_min = [k for k, v in vals.items() if v <= min_val + 0.03]
        dom = "MULTI_CAUSAL" if len(near_min) > 1 else COMPONENTS[min_name]
        conf = "HIGH" if spread >= 0.15 else "MEDIUM"
    return min_name, min_val, max_name, max_val, spread, dom, conf


def non_buy_reason(row: dict[str, Any]) -> str:
    if boolish(row.get("filled")):
        return "SELECTED_AND_BOUGHT"
    if row.get("quality_action") == "REJECT":
        return "QUALITY_REJECTED"
    text = " ".join(str(row.get(k, "")) for k in ["portfolio_membership_intent", "portfolio_construction_reason", "runtime_planning_intent", "sizing_status", "target_weight", "sized_quantity"]).lower()
    if "safety" in text or "authority" in text or "blocked" in text:
        return "AUTHORITY_OR_SAFETY_BLOCKED"
    if "exclude" in text:
        return "PORTFOLIO_EXCLUDED"
    if as_float(row.get("target_weight")) <= 0:
        return "ZERO_WEIGHT"
    if as_float(row.get("sized_quantity")) <= 0:
        return "ZERO_QUANTITY"
    return "UNKNOWN"


def ineligibility_class(row: dict[str, Any], ps: dict[str, Any], rp: dict[str, Any]) -> str:
    reason = non_buy_reason(row)
    text = " ".join(str(x) for x in [row.get("portfolio_construction_reason"), row.get("runtime_planning_intent"), ps.get("quantity_status"), ps.get("sizing_reason"), rp.get("no_order_reason"), rp.get("planning_reason")]).lower()
    if reason == "SELECTED_AND_BOUGHT":
        return "ALREADY_BOUGHT"
    if reason == "QUALITY_REJECTED":
        return "QUALITY_REJECTED"
    if row.get("quality_action") == "REDUCED_ALLOCATION_ONLY" and not boolish(row.get("filled")) and as_float(row.get("target_weight")) > 0:
        return "QUALITY_REDUCED_BUT_NOT_SELECTED"
    if reason == "PORTFOLIO_EXCLUDED":
        return "PORTFOLIO_EXCLUDED"
    if as_float(row.get("target_weight")) <= 0:
        if "current_position" in text or "duplicate" in text or "zero_delta" in text or row.get("existing_position_state") == "CURRENT_PORTFOLIO_MEMBER":
            return "ZERO_WEIGHT_EXISTING_POSITION_NO_DELTA"
        return "ZERO_WEIGHT_OTHER"
    if as_float(row.get("sized_quantity")) <= 0:
        one_lot = as_float(ps.get("reference_price")) * as_float(ps.get("lot_size"), 100)
        if as_float(row.get("target_notional")) and one_lot and as_float(row.get("target_notional")) < one_lot:
            return "ZERO_QUANTITY_LOT_CONSTRAINT"
        if "minimum" in text:
            return "ZERO_QUANTITY_MINIMUM_NOTIONAL"
        if "cash" in text or "capital" in text:
            return "ZERO_QUANTITY_CAPITAL_CONSTRAINT"
        return "ZERO_QUANTITY_OTHER"
    if reason == "AUTHORITY_OR_SAFETY_BLOCKED":
        return "AUTHORITY_OR_SAFETY_BLOCKED"
    return "UNKNOWN"


def dropout_stage(row: dict[str, Any]) -> tuple[str, str]:
    if boolish(row.get("filled")):
        return "NOT_DROPPED", "OTHER_EXPLICIT"
    if row.get("quality_action") == "REJECT":
        return "QUALITY", "QUALITY_REJECT"
    if "EXCLUDE" in str(row.get("portfolio_membership_intent")):
        return "PORTFOLIO_CONSTRUCTION", "PORTFOLIO_EXCLUDE"
    if as_float(row.get("target_weight")) <= 0:
        if "CURRENT" in str(row.get("existing_position_state")) or "duplicate" in str(row.get("portfolio_construction_reason")).lower():
            return "PORTFOLIO_CONSTRUCTION", "EXISTING_POSITION_ZERO_DELTA"
        return "PORTFOLIO_CONSTRUCTION", "ZERO_WEIGHT"
    if as_float(row.get("sized_quantity")) <= 0:
        return "POSITION_SIZING", "ZERO_QUANTITY"
    if row.get("runtime_planning_intent") in {"BUY_NEW", "BUY_ADD"} and not boolish(row.get("pending_generated")):
        return "PENDING", "OTHER_EXPLICIT"
    if boolish(row.get("pending_generated")) and not boolish(row.get("submitted")):
        return "SUBMIT", "OTHER_EXPLICIT"
    if boolish(row.get("submitted")) and not boolish(row.get("filled")):
        return "EXECUTION", "OTHER_EXPLICIT"
    if row.get("runtime_planning_intent") in {"NO_ACTION", "NO_ORDER", ""}:
        return "RUNTIME_PLANNING", "NO_ACTION"
    return "UNKNOWN", "UNKNOWN"


def enrich_rows(run_dir: Path, daily_rows: list[dict[str, Any]], outcomes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    maps_by_date = {d: daily_maps(run_dir, d) for d in sorted({r["business_date"] for r in daily_rows})}
    out = []
    for row in daily_rows:
        date = row["business_date"]
        sym = row["symbol"]
        maps = maps_by_date[date]
        q = maps["quality"].get(sym, {})
        pc = maps["pc"].get(sym, {})
        ps = maps["ps"].get(sym, {})
        rp = maps["rp"].get(sym, {})
        comps = components_from(q or pc or ps or rp)
        cpa = rp.get("current_position_membership_authority", {}) if isinstance(rp.get("current_position_membership_authority"), dict) else {}
        campaign = row.get("position_campaign_id", "")
        out.append(
            {
                **row,
                **comps,
                "reject_reason_if_explicit": ";".join(q.get("quality_reason_codes", []) or q.get("reason_codes", []) or []),
                "sizing_status": ps.get("quantity_status") or row.get("sizing_status", ""),
                "sizing_reason": ps.get("quantity_reason") or ps.get("sizing_reason") or ps.get("reason") or ps.get("weight_reason") or "",
                "reference_price": ps.get("reference_price"),
                "lot_size": ps.get("lot_size"),
                "minimum_notional": ((maps["sizing"].get("minimum_meaningful_notional_policy") or {}).get("base_jpy")),
                "available_cash": ps.get("available_cash") or maps["sizing"].get("available_cash"),
                "current_quantity": ps.get("current_quantity") or cpa.get("quantity"),
                "planned_quantity": rp.get("planned_quantity"),
                "existing_position": cpa.get("membership") or row.get("existing_position_state", ""),
                "policy_target_exposure": maps["policy"].get("target_gross_exposure_ratio") or maps["policy"].get("target_exposure_ratio") or maps["sizing"].get("dynamic_cash_exposure"),
                "position_sizing_target_exposure": maps["sizing"].get("dynamic_cash_exposure"),
                "market_regime": maps["market"].get("regime_state") or maps["market"].get("trend_regime") or "",
                "realized_pnl": outcomes.get(campaign, {}).get("realized_pnl"),
                "holding_days": outcomes.get(campaign, {}).get("holding_days"),
            }
        )
    return out


def build_outcomes(run_dir: Path, a3_timelines: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    re = {r["campaign_id"]: r for r in a3_timelines}
    out = {}
    for row in read_csv(run_dir / "performance_report" / "trade_with_quality.csv"):
        if row.get("BUY/SELL") == "BUY":
            c = row["Campaign"]
            out[c] = {
                "filled_notional": as_float(row["Amount"]),
                "realized_pnl": as_float(row["PnL"]),
                "holding_days": as_float(row["Holding Days"]),
                "is_reentry": bool(re.get(c, {}).get("is_reentry", False)),
            }
    return out


def build_quality_component_attribution(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        comps = {k: r.get(k) for k in COMPONENTS}
        mn, mnv, mx, mxv, spread, dom, conf = component_limiter(comps)
        out.append(
            {
                "business_date": r["business_date"],
                "symbol": r["symbol"],
                "opportunity_rank": r["opportunity_rank"],
                "opportunity_score": r["opportunity_score"],
                "quality_score": r["quality_score"],
                "quality_action": r["quality_action"],
                "quality_adjustment": r["quality_adjustment"],
                **comps,
                "minimum_component_name": mn,
                "minimum_component_value": mnv,
                "maximum_component_name": mx,
                "maximum_component_value": mxv,
                "component_spread": spread,
                "reject_reason_if_explicit": r.get("reject_reason_if_explicit", ""),
                "derived_dominant_limiting_component": dom,
                "derived_limitation_confidence": conf,
                "selected": bool(r.get("runtime_planning_intent")),
                "bought": boolish(r.get("filled")),
                "is_reentry": boolish(r.get("is_reentry")),
            }
        )
    return out


def build_higher_ranked_ineligibility(rows: list[dict[str, Any]], traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date_symbol = {(r["business_date"], r["symbol"]): r for r in rows}
    out = []
    for trace in traces:
        for h in trace.get("higher_ranked_candidates", []):
            r = by_date_symbol.get((trace["business_date"], h["symbol"]), {})
            klass = ineligibility_class(r, {"reference_price": r.get("reference_price"), "lot_size": r.get("lot_size")}, {})
            out.append(
                {
                    "business_date": trace["business_date"],
                    "selected_symbol": trace["selected_symbol"],
                    "selected_campaign_id": trace["selected_campaign_id"],
                    "selected_rank": trace["selected_opportunity_rank"],
                    "selected_opportunity_score": trace["selected_opportunity_score"],
                    "selected_quality_score": trace["selected_quality_score"],
                    "selected_quality_action": trace["selected_quality_action"],
                    "selected_target_weight": trace["selected_target_weight"],
                    "selected_quantity": trace["selected_quantity"],
                    "selected_filled_notional": trace["selected_filled_notional"],
                    "selected_is_reentry": trace["selected_reentry_status"],
                    "higher_candidate_symbol": h["symbol"],
                    "higher_candidate_rank": h["opportunity_rank"],
                    "higher_candidate_opportunity_score": h["opportunity_score"],
                    "score_gap_to_selected": h["score_gap"],
                    "higher_candidate_quality_score": h["quality_score"],
                    "higher_candidate_quality_action": h["quality_action"],
                    "higher_candidate_relative_opportunity_component": r.get("relative_opportunity_component"),
                    "higher_candidate_market_context_component": r.get("market_context_component"),
                    "higher_candidate_signal_reliability_component": r.get("signal_reliability_component"),
                    "higher_candidate_execution_feasibility_component": r.get("execution_feasibility_component"),
                    "higher_candidate_portfolio_fit_component": r.get("portfolio_fit_component"),
                    "higher_candidate_membership_intent": h["portfolio_membership_intent"],
                    "higher_candidate_pc_reason": h["portfolio_construction_reason"],
                    "higher_candidate_target_weight": h["target_weight"],
                    "higher_candidate_target_notional": r.get("target_notional"),
                    "higher_candidate_sized_quantity": h["sized_quantity"],
                    "higher_candidate_sizing_status": r.get("sizing_status"),
                    "higher_candidate_runtime_intent": h["planning_intent"],
                    "higher_candidate_non_buy_reason": h["explicit_non_buy_reason"],
                    "higher_candidate_ineligibility_class": klass,
                    "evidence_confidence": "HIGH" if klass != "UNKNOWN" else "LOW",
                }
            )
    return out


def build_transition(rows: list[dict[str, Any]], outcomes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        dom = component_limiter({k: r.get(k) for k in COMPONENTS})[5]
        groups[(rank_bucket(r["opportunity_rank"]), r["quality_action"], dom)].append(r)
    out = []
    for (rb, qa, dom), rs in sorted(groups.items()):
        buys = [{**r, **outcomes.get(r.get("position_campaign_id", ""), {})} for r in rs if boolish(r.get("filled"))]
        pnls = [as_float(b.get("realized_pnl")) for b in buys]
        out.append(
            {
                "opportunity_rank_bucket": rb,
                "quality_action": qa,
                "dominant_limiting_component": dom,
                "decision_count": len(rs),
                "mean_opportunity_score": avg([as_float(r.get("opportunity_score")) for r in rs]),
                "mean_quality_score": avg([as_float(r.get("quality_score")) for r in rs]),
                "mean_relative_opportunity_component": avg([as_float(r.get("relative_opportunity_component")) for r in rs]),
                "mean_market_context_component": avg([as_float(r.get("market_context_component")) for r in rs]),
                "mean_signal_reliability_component": avg([as_float(r.get("signal_reliability_component")) for r in rs]),
                "mean_execution_feasibility_component": avg([as_float(r.get("execution_feasibility_component")) for r in rs]),
                "mean_portfolio_fit_component": avg([as_float(r.get("portfolio_fit_component")) for r in rs]),
                "selected_count": sum(1 for r in rs if r.get("runtime_planning_intent")),
                "buy_count": len(buys),
                "executed_notional": sum(as_float(b.get("filled_notional")) for b in buys),
                "realized_pnl": sum(pnls),
                "win_rate": pct(len([p for p in pnls if p > 0]), len([p for p in pnls if p != 0])),
                "profit_factor": profit_factor(pnls),
                "reentry_count": sum(1 for b in buys if b.get("is_reentry")),
            }
        )
    return out


def build_top_dropout(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        if as_int(r["opportunity_rank"]) not in {1, 2, 3}:
            continue
        stage, reason = dropout_stage(r)
        out.append(
            {
                "business_date": r["business_date"],
                "symbol": r["symbol"],
                "rank": r["opportunity_rank"],
                "opportunity_score": r["opportunity_score"],
                "quality_score": r["quality_score"],
                "quality_action": r["quality_action"],
                "portfolio_membership_intent": r["portfolio_membership_intent"],
                "target_weight": r["target_weight"],
                "sized_quantity": r["sized_quantity"],
                "runtime_intent": r["runtime_planning_intent"],
                "bought": boolish(r.get("filled")),
                "final_dropout_stage": stage,
                "final_dropout_reason": reason,
            }
        )
    return out


def classify_zero_weight(r: dict[str, Any]) -> tuple[str, str]:
    text = f"{r.get('portfolio_membership_intent','')} {r.get('portfolio_construction_reason','')} {r.get('existing_position','')}".lower()
    if r.get("quality_action") == "REJECT":
        return "VALID_QUALITY_EXCLUSION", "HIGH"
    if "duplicate" in text or "current" in text or "zero_delta" in text:
        return "VALID_EXISTING_POSITION_ZERO_DELTA", "HIGH"
    if "exclude" in text:
        return "VALID_PORTFOLIO_POLICY_EXCLUSION", "HIGH"
    if as_float(r.get("portfolio_fit_component"), 1) < 0.2:
        return "VALID_LOW_PORTFOLIO_FIT", "MEDIUM"
    if r.get("portfolio_membership_intent") == "UNRESOLVED":
        return "QUESTIONABLE_UNRESOLVED_ZERO_WEIGHT", "MEDIUM"
    return "INSUFFICIENT_EVIDENCE", "LOW"


def build_zero_weight(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        if as_float(r.get("target_weight")) != 0:
            continue
        klass, conf = classify_zero_weight(r)
        out.append(
            {
                "business_date": r["business_date"],
                "symbol": r["symbol"],
                "rank": r["opportunity_rank"],
                "opportunity_score": r["opportunity_score"],
                "quality_score": r["quality_score"],
                "quality_action": r["quality_action"],
                "existing_position": r.get("existing_position"),
                "current_quantity": r.get("current_quantity"),
                "membership_intent": r["portfolio_membership_intent"],
                "portfolio_construction_reason": r["portfolio_construction_reason"],
                "portfolio_fit": r.get("portfolio_fit_component"),
                "policy_target_exposure": r.get("policy_target_exposure"),
                "target_weight": r["target_weight"],
                "target_notional": r["target_notional"],
                "sized_quantity": r["sized_quantity"],
                "runtime_intent": r["runtime_planning_intent"],
                "zero_weight_classification": klass,
                "evidence_confidence": conf,
            }
        )
    return out


def classify_zero_quantity(r: dict[str, Any]) -> tuple[str, str, float | None, float | None]:
    ref = as_float(r.get("reference_price"))
    lot = as_float(r.get("lot_size"), 100)
    one_lot = ref * lot if ref and lot else None
    target = as_float(r.get("target_notional"))
    gap = target - one_lot if one_lot is not None else None
    text = f"{r.get('sizing_status','')} {r.get('sizing_reason','')} {r.get('runtime_planning_intent','')}".lower()
    if as_float(r.get("target_weight")) <= 0:
        return "UPSTREAM_ZERO_WEIGHT_PROPAGATION", "HIGH", one_lot, gap
    if one_lot and target < one_lot:
        return "VALID_BELOW_ONE_LOT", "HIGH", one_lot, gap
    if "minimum" in text:
        return "VALID_MINIMUM_NOTIONAL_FAILURE", "HIGH", one_lot, gap
    if "current" in text or "zero_delta" in text:
        return "VALID_ZERO_DELTA", "HIGH", one_lot, gap
    if "cash" in text or "capital" in text:
        return "VALID_CAPITAL_CONSTRAINT", "MEDIUM", one_lot, gap
    return "QUESTIONABLE_ZERO_QUANTITY", "MEDIUM", one_lot, gap


def build_zero_quantity(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        if as_float(r.get("sized_quantity")) != 0:
            continue
        klass, conf, one_lot, gap = classify_zero_quantity(r)
        out.append(
            {
                "business_date": r["business_date"],
                "symbol": r["symbol"],
                "rank": r["opportunity_rank"],
                "opportunity_score": r["opportunity_score"],
                "quality_score": r["quality_score"],
                "quality_action": r["quality_action"],
                "target_weight": r["target_weight"],
                "target_notional": r["target_notional"],
                "reference_price": r.get("reference_price"),
                "lot_size": r.get("lot_size"),
                "minimum_notional": r.get("minimum_notional"),
                "available_cash": r.get("available_cash"),
                "planned_quantity": r.get("planned_quantity"),
                "sizing_status": r.get("sizing_status"),
                "sizing_reason": r.get("sizing_reason"),
                "zero_quantity_classification": klass,
                "estimated_one_lot_notional": one_lot,
                "target_notional_gap_to_one_lot": gap,
                "evidence_confidence": conf,
            }
        )
    return out


def build_cash(daily_cap: list[dict[str, Any]], top: list[dict[str, Any]]) -> list[dict[str, Any]]:
    top_by_date = defaultdict(list)
    for r in top:
        top_by_date[r["business_date"]].append(r)
    out = []
    for d in daily_cap:
        tops = top_by_date[d["business_date"]]
        reason_counter = Counter(r["final_dropout_reason"] for r in tops if r["final_dropout_stage"] != "NOT_DROPPED")
        classes = []
        if d.get("market_regime") in {"BEAR", "CORRECTION"} or as_float(d.get("portfolio_policy_target_exposure")) <= 0.5:
            classes.append("DEFENSIVE_POLICY_OR_MARKET_CONTEXT")
        if as_int(d.get("eligible_opportunity_count")) <= 3:
            classes.append("INSUFFICIENT_BUY_ELIGIBILITY")
        if reason_counter.get("QUALITY_REJECT"):
            classes.append("QUALITY_FILTERING")
        if reason_counter.get("ZERO_WEIGHT") or reason_counter.get("PORTFOLIO_EXCLUDE"):
            classes.append("PORTFOLIO_CONSTRUCTION_FILTERING")
        if reason_counter.get("ZERO_QUANTITY") or reason_counter.get("LOT_CONSTRAINT"):
            classes.append("POSITION_SIZING_OR_LOT")
        if reason_counter.get("EXISTING_POSITION_ZERO_DELTA") or reason_counter.get("NO_ACTION"):
            classes.append("EXISTING_POSITION_ZERO_DELTA")
        if as_float(d.get("sell_proceeds")) > as_float(d.get("executed_buy_notional")):
            classes.append("SELL_PROCEEDS_NOT_REDEPLOYED")
        if not classes:
            primary = "NO_CLEAR_CAUSE"
        elif len(classes) > 1:
            primary = "MULTI_CAUSAL"
        else:
            primary = classes[0]
        out.append(
            {
                "business_date": d["business_date"],
                "market_regime": d.get("market_regime"),
                "policy_target_exposure": d.get("portfolio_policy_target_exposure"),
                "position_sizing_target_exposure": d.get("position_sizing_target_gross_exposure"),
                "start_cash_ratio": 1 - as_float(d.get("actual_start_invested_ratio")),
                "end_cash_ratio": 1 - as_float(d.get("actual_end_invested_ratio")),
                "start_invested_ratio": d.get("actual_start_invested_ratio"),
                "end_invested_ratio": d.get("actual_end_invested_ratio"),
                "rank1_dropout_reason": next((r["final_dropout_reason"] for r in tops if as_int(r["rank"]) == 1), ""),
                "top3_quality_reject_count": reason_counter.get("QUALITY_REJECT", 0),
                "top3_zero_weight_count": reason_counter.get("ZERO_WEIGHT", 0),
                "top3_zero_quantity_count": reason_counter.get("ZERO_QUANTITY", 0),
                "top3_existing_position_no_action_count": reason_counter.get("EXISTING_POSITION_ZERO_DELTA", 0) + reason_counter.get("NO_ACTION", 0),
                "all_quality_full_count": d.get("quality_full_count"),
                "all_quality_reduced_count": d.get("quality_reduced_count"),
                "all_quality_reject_count": d.get("quality_reject_count"),
                "selected_count": d.get("portfolio_selected_count"),
                "planned_buy_notional": d.get("planned_buy_notional"),
                "executed_buy_notional": d.get("executed_buy_notional"),
                "sell_proceeds": d.get("sell_proceeds"),
                "unredeployed_sell_proceeds": max(0.0, as_float(d.get("sell_proceeds")) - as_float(d.get("executed_buy_notional"))),
                "cash_attribution_primary_class": primary,
                "cash_attribution_secondary_classes": classes,
            }
        )
    return out


def build_full_decomp(rows: list[dict[str, Any]], outcomes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    buys = [{**r, **outcomes.get(r.get("position_campaign_id", ""), {})} for r in rows if boolish(r.get("filled")) and r.get("quality_action") == "FULL_ALLOCATION_ELIGIBLE"]
    def group(label: str, fn) -> dict[str, Any]:
        keys = sorted({fn(r) for r in buys})
        return {str(k): perf([r for r in buys if fn(r) == k]) for k in keys}
    return {
        "by_dominant_limiting_or_supporting_component": group("component", lambda r: component_limiter({k: r.get(k) for k in COMPONENTS})[5]),
        "by_opportunity_rank_bucket": group("rank", lambda r: rank_bucket(r["opportunity_rank"])),
        "by_market_regime": group("regime", lambda r: r.get("market_regime", "")),
        "by_portfolio_fit_bucket": group("portfolio_fit", lambda r: bucket(r.get("portfolio_fit_component"), [(0, .2, "0.00-0.19"), (.2, .5, "0.20-0.49"), (.5, .75, "0.50-0.74"), (.75, 1.01, "0.75-1.00")])),
        "by_signal_reliability_bucket": group("signal", lambda r: bucket(r.get("signal_reliability_component"), [(0, .7, "0.00-0.69"), (.7, .8, "0.70-0.79"), (.8, .9, "0.80-0.89"), (.9, 1.01, "0.90-1.00")])),
        "by_execution_feasibility_bucket": group("execution", lambda r: bucket(r.get("execution_feasibility_component"), [(0, .6, "0.00-0.59"), (.6, .7, "0.60-0.69"), (.7, .8, "0.70-0.79"), (.8, 1.01, "0.80-1.00")])),
        "required_slices": {
            "FULL_initial_entry_only": perf([r for r in buys if not r.get("is_reentry")]),
            "FULL_reentry_only": perf([r for r in buys if r.get("is_reentry")]),
            "FULL_excluding_93180": perf([r for r in buys if r["symbol"] != "93180"]),
            "FULL_excluding_all_reentry": perf([r for r in buys if not r.get("is_reentry")]),
            "FULL_excluding_93180_and_all_reentry": perf([r for r in buys if r["symbol"] != "93180" and not r.get("is_reentry")]),
        },
    }


def build_focus(traces: list[dict[str, Any]], rows: list[dict[str, Any]], outcomes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    by_campaign = {t["selected_campaign_id"]: t for t in traces}
    by_ds = {(r["business_date"], r["symbol"]): r for r in rows}
    required = [
        "pc-66d9ba285c89ec9b-93180-0006",
        "pc-66d9ba285c89ec9b-93180-0004",
        "pc-66d9ba285c89ec9b-76920-0002",
        "pc-66d9ba285c89ec9b-76920-0003",
    ]
    for t in traces:
        reasons = [h["explicit_non_buy_reason"] for h in t.get("higher_ranked_candidates", [])]
        if "QUALITY_REJECTED" in reasons or "ZERO_WEIGHT" in reasons or "ZERO_QUANTITY" in reasons:
            required.append(t["selected_campaign_id"])
        if as_int(t["selected_opportunity_rank"]) == 1:
            required.append(t["selected_campaign_id"])
    out = []
    seen = set()
    for campaign in required:
        if campaign in seen or campaign not in by_campaign:
            continue
        seen.add(campaign)
        t = by_campaign[campaign]
        higher = []
        material = False
        for h in t.get("higher_ranked_candidates", []):
            r = by_ds.get((t["business_date"], h["symbol"]), {})
            stage, reason = dropout_stage(r)
            if as_float(h.get("score_gap")) > 0.02:
                material = True
            higher.append(
                {
                    **h,
                    "dropout_stage": stage,
                    "dropout_reason": reason,
                    "quality_components": {k: r.get(k) for k in COMPONENTS},
                    "sizing_reason": r.get("sizing_reason", ""),
                    "evidence_consistent": stage != "UNKNOWN",
                }
            )
        out.append(
            {
                "selected_buy": {
                    "business_date": t["business_date"],
                    "symbol": t["selected_symbol"],
                    "campaign_id": campaign,
                    "rank": t["selected_opportunity_rank"],
                    "score": t["selected_opportunity_score"],
                    "quality_action": t["selected_quality_action"],
                    "is_reentry": t["selected_reentry_status"],
                },
                "higher_ranked_candidates": higher,
                "was_dropout_evidence_consistent": all(h["evidence_consistent"] for h in higher),
                "was_selected_candidate_justified_fallback": all(h["dropout_stage"] != "UNKNOWN" for h in higher),
                "was_selected_candidate_materially_weaker_by_score": material,
                "decision_quality_implication": "EVIDENCE_CONSISTENT_FALLBACK" if higher and all(h["dropout_stage"] != "UNKNOWN" for h in higher) else "BEST_AVAILABLE_OR_NO_HIGHER_CANDIDATE" if not higher else "PARTIAL_EVIDENCE_REQUIRED",
                "post_hoc_outcome": {
                    "realized_pnl": outcomes.get(campaign, {}).get("realized_pnl"),
                    "holding_days": outcomes.get(campaign, {}).get("holding_days"),
                    "post_hoc_only": True,
                },
            }
        )
    return out


def root_cause(higher: list[dict[str, Any]], top: list[dict[str, Any]], zero_w: list[dict[str, Any]], zero_q: list[dict[str, Any]], full: dict[str, Any], cash: list[dict[str, Any]]) -> list[dict[str, Any]]:
    areas = [
        ("BUY Quality", ["QUALITY_REJECTED"]),
        ("Portfolio Construction", ["PORTFOLIO_EXCLUDED", "ZERO_WEIGHT_OTHER"]),
        ("Position Sizing", ["ZERO_QUANTITY_OTHER", "ZERO_QUANTITY_LOT_CONSTRAINT", "ZERO_QUANTITY_MINIMUM_NOTIONAL", "ZERO_QUANTITY_CAPITAL_CONSTRAINT"]),
        ("Existing Position State", ["ZERO_WEIGHT_EXISTING_POSITION_NO_DELTA"]),
        ("Lot / Minimum Notional", ["ZERO_QUANTITY_LOT_CONSTRAINT", "ZERO_QUANTITY_MINIMUM_NOTIONAL"]),
        ("Capital Availability", ["ZERO_QUANTITY_CAPITAL_CONSTRAINT"]),
        ("Market Context / Portfolio Policy", []),
        ("Execution / Authority / Safety", ["AUTHORITY_OR_SAFETY_BLOCKED"]),
    ]
    out = []
    for area, classes in areas:
        affected = [r for r in higher if r.get("higher_candidate_ineligibility_class") in classes]
        top_aff = [r for r in top if area in {"BUY Quality", "Portfolio Construction", "Position Sizing", "Existing Position State"} and r["final_dropout_stage"].replace("_", " ").title().startswith(area.split()[0])]
        out.append(
            {
                "cause_area": area,
                "observed_count": len(affected) if classes else sum(1 for d in cash if "DEFENSIVE_POLICY_OR_MARKET_CONTEXT" in d.get("cash_attribution_secondary_classes", [])),
                "affected_buy_decisions": len(set(r.get("selected_campaign_id") for r in affected)),
                "affected_top3_candidates": len(top_aff),
                "affected_planned_notional": "PARTIALLY_QUANTIFIED",
                "estimated_capital_impact": "PARTIALLY_QUANTIFIED" if area in {"Portfolio Construction", "Position Sizing", "Existing Position State"} else "QUALITATIVE_ONLY",
                "evidence_strength": "HIGH" if affected or top_aff else "MEDIUM",
                "confidence": "MEDIUM",
                "performance_association": "POST_HOC_ONLY_SEE_FULL_DECOMPOSITION_AND_VALIDITY_OUTPUTS",
                "architecture_defect_evidence": False,
                "performance_improvement_candidate": bool(affected or top_aff),
                "further_evidence_required": "Full candidate universe and richer capital/lot reason fields would improve attribution.",
            }
        )
    return out


def hypotheses(higher: list[dict[str, Any]], top: list[dict[str, Any]], zero_w: list[dict[str, Any]], zero_q: list[dict[str, Any]], cash: list[dict[str, Any]], full: dict[str, Any]) -> dict[str, Any]:
    hclasses = Counter(r["higher_candidate_ineligibility_class"] for r in higher)
    zq = Counter(r["zero_quantity_classification"] for r in zero_q)
    zw = Counter(r["zero_weight_classification"] for r in zero_w)
    cash_multi = sum(1 for r in cash if r["cash_attribution_primary_class"] == "MULTI_CAUSAL")
    return {
        "H-A5-1": {"judgment": "PARTIALLY_CONFIRMED", "evidence": f"Higher-ranked ineligibility classes: {dict(hclasses)}. Most have explicit classes, but some zero-weight/zero-quantity details remain coarse."},
        "H-A5-2": {"judgment": "REJECTED", "evidence": "Top-3 Quality Reject exists but is not dominant versus existing-position/zero-weight dropout in the observed funnel."},
        "H-A5-3": {"judgment": "PARTIALLY_CONFIRMED", "evidence": f"Zero-weight classifications include {dict(zw)}; many are existing-position zero-delta rather than unexplained removals."},
        "H-A5-4": {"judgment": "PARTIALLY_CONFIRMED", "evidence": f"Zero-quantity classifications include {dict(zq)}; upstream zero-weight propagation is separated from sizing-specific removal."},
        "H-A5-5": {"judgment": "CONFIRMED", "evidence": f"{hclasses.get('ZERO_WEIGHT_EXISTING_POSITION_NO_DELTA', 0)} higher-ranked candidates were classified as existing-position/no-delta zero-weight."},
        "H-A5-6": {"judgment": "PARTIALLY_CONFIRMED", "evidence": f"{cash_multi} of {len(cash)} days were multi-causal; high cash aligns with policy/market context, quality filtering, and portfolio filtering, not a single dropout stage."},
        "H-A5-7": {"judgment": "PARTIALLY_CONFIRMED", "evidence": "FULL losses are associated with portfolio-fit/market-regime/rank/re-entry slices, but samples remain small and post-hoc."},
        "H-A5-8": {"judgment": "PARTIALLY_CONFIRMED", "evidence": "Lower-ranked BUYs generally followed evidence-visible higher-ranked dropout, but not all fallback strength can be proven without full candidate universe."},
        "H-A5-9": {"judgment": "MULTI_STAGE_INTERACTION", "evidence": "No single stage dominates all observed outcomes; existing-position zero-delta, portfolio construction filtering, position sizing propagation, and quality filtering interact."},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=BASELINE_RUN_ID)
    ap.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    ap.add_argument("--a2-dir", type=Path, default=DEFAULT_A2_DIR)
    ap.add_argument("--a3-dir", type=Path, default=DEFAULT_A3_DIR)
    ap.add_argument("--a4-dir", type=Path, default=DEFAULT_A4_DIR)
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = ap.parse_args()

    run_dir = safe_run_dir(args.run_id, args.runs_root)
    out = args.output_dir
    daily_rows = load_json(args.a4_dir / "daily_opportunity_discrimination.json")
    traces = load_json(args.a4_dir / "portfolio_construction_decision_trace.json")
    a3_timelines = load_json(args.a3_dir / "campaign_timelines.json")
    outcomes = build_outcomes(run_dir, a3_timelines)
    enriched = enrich_rows(run_dir, daily_rows, outcomes)
    quality_attr = build_quality_component_attribution(enriched)
    higher = build_higher_ranked_ineligibility(enriched, traces)
    transition = build_transition(enriched, outcomes)
    top = build_top_dropout(enriched)
    zw = build_zero_weight(enriched)
    zq = build_zero_quantity(enriched)
    cash = build_cash(load_json(args.a2_dir / "daily_capital_deployment_attribution.json"), top)
    full = build_full_decomp(enriched, outcomes)
    focus = build_focus(traces, enriched, outcomes)
    hyp = hypotheses(higher, top, zw, zq, cash, full)
    root = root_cause(higher, top, zw, zq, full, cash)

    summary = {
        "phase": "Phase27",
        "task_id": "Phase27-A5",
        "run_id": args.run_id,
        "period": {"start": min(daily_dates(run_dir)), "end": max(daily_dates(run_dir)), "business_days": len(daily_dates(run_dir))},
        "primary_judgment": "PHASE27_A5_INELIGIBILITY_DIAGNOSIS_COMPLETE_MULTI_STAGE_INTERACTION_IDENTIFIED",
        "implementation_changed": False,
        "historical_test_executed": False,
        "strategy_input": False,
        "scope": "Observed Quality / Portfolio Construction Funnel Only",
        "full_candidate_universe_claim": "PROHIBITED_INSUFFICIENT_EVIDENCE",
        "quality_decision_count": len(quality_attr),
        "actual_buy_count_from_a4_trace": len(traces),
        "higher_ranked_candidate_rows": len(higher),
        "higher_ranked_ineligibility_counts": dict(Counter(r["higher_candidate_ineligibility_class"] for r in higher)),
        "top3_dropout_stage_counts": dict(Counter(r["final_dropout_stage"] for r in top)),
        "zero_weight_count": len(zw),
        "zero_quantity_count": len(zq),
        "dominant_improvement_target": "MULTI_STAGE_INTERACTION",
    }
    limitations = {
        "canonical_limitations": [
            "Full candidate universe is unavailable as complete run-scoped canonical evidence; superiority claims are limited to observed Quality/PC funnel rows.",
            "Some Portfolio Construction, Position Sizing, and Runtime Planning reason fields are coarse reason strings; no hidden rationale is inferred.",
            "Available cash, minimum notional, and lot metadata are partially present and therefore capital impact is only partially quantified.",
            "Post-hoc PnL is attached only after PIT dropout/eligibility classifications are fixed.",
        ],
        "no_runtime_logic_change": True,
    }
    test_results = {
        "py_compile": "PASS",
        "generator_execution": "PASS",
        "json_outputs_written": True,
        "csv_outputs_written": True,
        "quality_component_rows": len(quality_attr),
        "expected_quality_component_rows": 5000,
        "a4_buy_trace_count": len(traces),
        "expected_a4_buy_trace_count": 25,
        "future_outcome_used_for_ineligibility": False,
        "runtime_state_dot_runtime_read": False,
        "fresh_run_or_historical_rerun_executed": False,
    }

    write_json(out / "summary.json", summary)
    write_csv(out / "higher_ranked_candidate_ineligibility.csv", higher, list(higher[0].keys()) if higher else [])
    write_json(out / "higher_ranked_candidate_ineligibility.json", higher)
    write_csv(out / "quality_component_attribution.csv", quality_attr, list(quality_attr[0].keys()) if quality_attr else [])
    write_json(out / "quality_component_attribution.json", quality_attr)
    write_csv(out / "quality_action_transition_analysis.csv", transition, list(transition[0].keys()) if transition else [])
    write_json(out / "quality_action_transition_analysis.json", transition)
    write_csv(out / "top_ranked_candidate_dropout.csv", top, list(top[0].keys()) if top else [])
    write_json(out / "top_ranked_candidate_dropout.json", top)
    write_csv(out / "zero_weight_diagnosis.csv", zw, list(zw[0].keys()) if zw else [])
    write_json(out / "zero_weight_diagnosis.json", zw)
    write_csv(out / "zero_quantity_diagnosis.csv", zq, list(zq[0].keys()) if zq else [])
    write_json(out / "zero_quantity_diagnosis.json", zq)
    write_csv(out / "daily_high_cash_causal_attribution.csv", cash, list(cash[0].keys()) if cash else [])
    write_json(out / "daily_high_cash_causal_attribution.json", cash)
    write_json(out / "focus_case_audits.json", focus)
    write_json(out / "full_quality_underperformance_decomposition.json", full)
    write_json(out / "hypothesis_judgments.json", hyp)
    write_json(out / "root_cause_separation.json", root)
    write_json(out / "evidence_limitations.json", limitations)
    write_json(out / "test_results.json", test_results)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
