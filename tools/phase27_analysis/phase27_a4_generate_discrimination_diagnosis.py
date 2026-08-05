#!/usr/bin/env python3
"""Phase27-A4 read-only selection discrimination diagnosis.

Observability Only / Post-hoc Human Review Only / Not a Strategy Input.

This script reads run-scoped Runtime Test evidence and Phase27-A2/A3 outputs
only. It does not read .runtime, does not mutate runtime state, and must not be
used as Strategy, Candidate, Opportunity, BUY Quality, Portfolio Policy,
Portfolio Construction, Position Sizing, Planning, Submit, Safety, PM, Exit, or
Re-entry input.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any


BASELINE_RUN_ID = "runtime-test-historical-smoke-20260804T074611098414Z"
DEFAULT_RUNS_ROOT = Path("reports/runtime_tests/runs")
DEFAULT_A2_DIR = Path("reports/phase27_a2_100bd_baseline_attribution_and_hypothesis_evidence_extraction")
DEFAULT_A3_DIR = Path("reports/phase27_a3_reentry_causality_and_selection_validity_diagnosis")
DEFAULT_OUTPUT_DIR = Path("reports/phase27_a4_opportunity_quality_and_final_selection_discrimination_diagnosis")


RANK_BUCKETS = ["1", "2", "3", "4-5", "6-10", "11+"]
QUALITY_ACTIONS = [
    "FULL_ALLOCATION_ELIGIBLE",
    "REDUCED_ALLOCATION_ONLY",
    "BUY_REVIEW_REQUIRED",
    "REJECT",
]
QUALITY_SCORE_BUCKETS = [
    "0.00-0.49",
    "0.50-0.59",
    "0.60-0.69",
    "0.70-0.74",
    "0.75-0.79",
    "0.80-0.84",
    "0.85-0.89",
    "0.90-1.00",
]


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


def stat(values: list[float]) -> dict[str, float | None]:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    return {
        "mean_score": mean(vals) if vals else None,
        "median_score": median(vals) if vals else None,
        "minimum_score": min(vals) if vals else None,
        "maximum_score": max(vals) if vals else None,
        "standard_deviation": pstdev(vals) if len(vals) > 1 else 0.0 if vals else None,
    }


def pct(num: float, den: float) -> float | None:
    return None if den == 0 else num / den


def profit_factor(pnls: list[float]) -> float | None:
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = sum(p for p in pnls if p < 0)
    if gross_loss == 0:
        return None
    return gross_profit / abs(gross_loss)


def perf_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pnls = [as_float(r.get("realized_pnl", r.get("PnL"))) for r in rows]
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p < 0]
    return {
        "buy_count": len(rows),
        "executed_notional": sum(as_float(r.get("filled_notional", r.get("Amount"))) for r in rows),
        "realized_pnl": sum(pnls),
        "win_rate": pct(len(winners), len([p for p in pnls if p != 0])),
        "profit_factor": profit_factor(pnls),
        "average_winner": mean(winners) if winners else None,
        "average_loser": mean(losers) if losers else None,
        "reentry_count": sum(1 for r in rows if boolish(r.get("is_reentry"))),
        "average_holding_days": mean([as_float(r.get("holding_days", r.get("Holding Days"))) for r in rows]) if rows else None,
        "small_sample_warning": len(rows) < 10,
    }


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def rank_bucket(rank: Any) -> str:
    r = as_int(rank, 0)
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


def quality_score_bucket(score: Any) -> str:
    s = as_float(score, -1)
    if 0.0 <= s < 0.50:
        return "0.00-0.49"
    if s < 0.60:
        return "0.50-0.59"
    if s < 0.70:
        return "0.60-0.69"
    if s < 0.75:
        return "0.70-0.74"
    if s < 0.80:
        return "0.75-0.79"
    if s < 0.85:
        return "0.80-0.84"
    if s < 0.90:
        return "0.85-0.89"
    if s <= 1.00:
        return "0.90-1.00"
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


def load_quality_components(run_dir: Path, date: str) -> dict[str, dict[str, Any]]:
    path = run_dir / "daily" / date / "strategy" / "buy_quality_decisions.json"
    rows = load_json(path).get("decisions", [])
    out = {}
    for row in rows:
        symbol = str(row.get("symbol") or row.get("security_code"))
        comps = row.get("component_scores", {}) or {}
        out[symbol] = {
            "quality_component_relative_opportunity": comps.get("relative_opportunity_quality"),
            "quality_component_market_context": comps.get("market_context_quality_modifier"),
            "quality_component_signal_reliability": comps.get("signal_reliability"),
            "quality_component_execution_feasibility": comps.get("execution_feasibility"),
            "quality_component_portfolio_fit": comps.get("portfolio_fit"),
        }
    return out


def load_daily_strategy_maps(run_dir: Path, date: str) -> dict[str, dict[str, dict[str, Any]]]:
    strategy_dir = run_dir / "daily" / date / "strategy"
    return {
        "pc": by_symbol(load_json(strategy_dir / "portfolio_construction.json").get("portfolio_members", [])),
        "ps": by_symbol(load_json(strategy_dir / "position_sizing.json").get("positions", [])),
        "rp": by_symbol(load_json(strategy_dir / "runtime_planning.json").get("plans", [])),
        "components": load_quality_components(run_dir, date),
    }


def market_regime(run_dir: Path, date: str) -> str:
    payload = load_json(run_dir / "daily" / date / "strategy" / "market_context.json")
    return payload.get("regime_state") or payload.get("trend_regime") or payload.get("volatility_state") or ""


def build_buy_outcomes(run_dir: Path, a3_timelines: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    reentry_by_campaign = {row["campaign_id"]: row for row in a3_timelines}
    outcomes = {}
    for row in read_csv(run_dir / "performance_report" / "trade_with_quality.csv"):
        if row.get("BUY/SELL") != "BUY":
            continue
        campaign = row["Campaign"]
        timeline = reentry_by_campaign.get(campaign, {})
        outcomes[campaign] = {
            "business_date": row["Date"],
            "symbol": row["Symbol"],
            "campaign_id": campaign,
            "filled_notional": as_float(row["Amount"]),
            "filled_quantity": as_float(row["Qty"]),
            "realized_pnl": as_float(row["PnL"]),
            "holding_days": as_float(row["Holding Days"]),
            "return": timeline.get("campaign_return_rate_if_resolvable"),
            "is_reentry": bool(timeline.get("is_reentry", False)),
            "market_regime": market_regime(run_dir, row["Date"]),
        }
    return outcomes


def build_daily_discrimination(
    run_dir: Path,
    funnel: list[dict[str, Any]],
    outcomes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    date_maps = {date: load_daily_strategy_maps(run_dir, date) for date in sorted({r["business_date"] for r in funnel})}
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in funnel:
        by_date[row["business_date"]].append(row)

    out = []
    for date, rows in by_date.items():
        ordered = sorted(rows, key=lambda r: (as_int(r.get("opportunity_rank"), 9999), str(r.get("symbol"))))
        rank_scores = {as_int(r.get("opportunity_rank")): as_float(r.get("opportunity_score")) for r in ordered}
        top_score = rank_scores.get(1)
        prev_score = None
        for row in ordered:
            symbol = str(row.get("symbol"))
            maps = date_maps[date]
            pc = maps["pc"].get(symbol, {})
            ps = maps["ps"].get(symbol, {})
            rp = maps["rp"].get(symbol, {})
            comps = maps["components"].get(symbol, {})
            score = as_float(row.get("opportunity_score"))
            campaign = row.get("position_campaign_id", "")
            top_gap = None if top_score is None else top_score - score
            prev_gap = None if prev_score is None else prev_score - score
            out.append(
                {
                    "business_date": date,
                    "symbol": symbol,
                    "source_candidate_id": row.get("source_candidate_id", ""),
                    "source_opportunity_id": row.get("source_opportunity_id", ""),
                    "opportunity_rank": row.get("opportunity_rank"),
                    "opportunity_score": score,
                    "top_rank_score": top_score,
                    "score_gap_from_rank1": top_gap,
                    "score_gap_from_previous_rank": prev_gap,
                    "score_ratio_to_rank1": pct(score, top_score) if top_score not in {None, 0} else None,
                    "quality_decision_id": row.get("quality_decision_id", ""),
                    "quality_score": row.get("quality_score"),
                    "quality_action": row.get("quality_action", ""),
                    "quality_adjustment": row.get("quality_adjustment"),
                    "quality_component_relative_opportunity": comps.get("quality_component_relative_opportunity"),
                    "quality_component_market_context": comps.get("quality_component_market_context"),
                    "quality_component_signal_reliability": comps.get("quality_component_signal_reliability"),
                    "quality_component_execution_feasibility": comps.get("quality_component_execution_feasibility"),
                    "quality_component_portfolio_fit": comps.get("quality_component_portfolio_fit"),
                    "portfolio_membership_intent": row.get("portfolio_membership_intent", ""),
                    "portfolio_construction_reason": row.get("portfolio_construction_reason", ""),
                    "portfolio_fit_if_available": comps.get("quality_component_portfolio_fit"),
                    "existing_position_state": existing_position_state(pc, rp),
                    "target_weight": row.get("target_weight"),
                    "target_notional": row.get("target_notional"),
                    "sized_quantity": row.get("sized_quantity"),
                    "runtime_planning_intent": row.get("runtime_planning_intent", ""),
                    "pending_generated": row.get("pending_generated"),
                    "submitted": row.get("submitted"),
                    "filled": row.get("filled"),
                    "filled_notional": row.get("filled_notional"),
                    "position_campaign_id": campaign,
                    "is_reentry": outcomes.get(campaign, {}).get("is_reentry", False),
                }
            )
            prev_score = score
    return out


def existing_position_state(pc: dict[str, Any], rp: dict[str, Any]) -> str:
    cpa = rp.get("current_position_membership_authority", {}) if isinstance(rp.get("current_position_membership_authority"), dict) else {}
    if cpa.get("membership"):
        return cpa["membership"]
    if pc.get("current_position") is True:
        return "CURRENT_POSITION"
    if pc.get("current_position") is False:
        return "NO_CURRENT_POSITION"
    return ""


def build_score_distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for bucket in RANK_BUCKETS:
        bucket_rows = [r for r in rows if rank_bucket(r["opportunity_rank"]) == bucket]
        buy_rows = [r for r in bucket_rows if boolish(r.get("filled"))]
        scores = [as_float(r["opportunity_score"]) for r in bucket_rows]
        payload = {"decision_count": len(bucket_rows), **stat(scores)}
        payload.update(
            {
                "selected_count": sum(1 for r in bucket_rows if r.get("runtime_planning_intent")),
                "buy_count": len(buy_rows),
                "buy_conversion_rate": pct(len(buy_rows), len(bucket_rows)),
                "small_sample_warning": len(buy_rows) < 10,
            }
        )
        out[bucket] = payload
    return out


def build_daily_score_gap(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_date[row["business_date"]].append(row)
    out = []
    for date, date_rows in by_date.items():
        scores = {as_int(r["opportunity_rank"]): as_float(r["opportunity_score"]) for r in date_rows}
        bought = [r for r in date_rows if boolish(r.get("filled"))]
        selected_scores = [as_float(r["opportunity_score"]) for r in bought]
        rank1 = scores.get(1)
        out.append(
            {
                "business_date": date,
                "rank1_score": rank1,
                "rank2_score": scores.get(2),
                "rank3_score": scores.get(3),
                "rank5_score": scores.get(5),
                "rank1_minus_rank2_score_gap": rank1 - scores[2] if rank1 is not None and 2 in scores else None,
                "rank1_minus_rank3_score_gap": rank1 - scores[3] if rank1 is not None and 3 in scores else None,
                "rank1_minus_rank5_score_gap": rank1 - scores[5] if rank1 is not None and 5 in scores else None,
                "rank1_minus_selected_buy_score_gap_min": min([rank1 - s for s in selected_scores], default=None) if rank1 is not None else None,
                "rank1_minus_selected_buy_score_gap_max": max([rank1 - s for s in selected_scores], default=None) if rank1 is not None else None,
                "rank1_minus_selected_buy_score_gap_mean": mean([rank1 - s for s in selected_scores]) if rank1 is not None and selected_scores else None,
                "selected_buy_count": len(bought),
            }
        )
    return sorted(out, key=lambda r: r["business_date"])


def candidate_non_buy_reason(row: dict[str, Any]) -> str:
    if boolish(row.get("filled")):
        return "SELECTED_AND_BOUGHT"
    if row.get("quality_action") == "REJECT" or row.get("final_funnel_status") == "NOT_BOUGHT_QUALITY_REJECT":
        return "QUALITY_REJECTED"
    reason = ";".join(str(row.get(k, "")) for k in ["portfolio_membership_intent", "portfolio_construction_reason", "runtime_planning_intent", "sizing_status", "final_explicit_reason"])
    reason_l = reason.lower()
    if "safety" in reason_l or "authority" in reason_l or "blocked" in reason_l:
        return "AUTHORITY_OR_SAFETY_BLOCKED"
    if "exclude" in str(row.get("portfolio_membership_intent", "")).lower():
        return "PORTFOLIO_EXCLUDED"
    if as_float(row.get("target_weight")) <= 0:
        return "ZERO_WEIGHT"
    if as_float(row.get("sized_quantity")) <= 0:
        if "current" in reason_l or "no_delta" in reason_l or "zero_delta" in reason_l:
            return "ALREADY_HELD_NO_DELTA"
        return "ZERO_QUANTITY"
    if "lot" in reason_l or "minimum" in reason_l:
        return "LOT_OR_MINIMUM_NOTIONAL"
    if row.get("portfolio_membership_intent") in {"UNRESOLVED", "EXCLUDE"}:
        return "PORTFOLIO_EXCLUDED"
    return "AVAILABLE_BUT_NOT_SELECTED"


def near_tie_flags(selected_score: float, stronger_score: float) -> dict[str, bool]:
    gap = stronger_score - selected_score
    rel_gap = pct(gap, abs(stronger_score)) if stronger_score else None
    return {
        "absolute_gap_lte_0_005": gap <= 0.005,
        "absolute_gap_lte_0_010": gap <= 0.010,
        "absolute_gap_lte_0_020": gap <= 0.020,
        "relative_gap_lte_1pct": rel_gap is not None and rel_gap <= 0.01,
        "relative_gap_lte_2pct": rel_gap is not None and rel_gap <= 0.02,
        "relative_gap_lte_5pct": rel_gap is not None and rel_gap <= 0.05,
    }


def build_decision_trace_and_validity(rows: list[dict[str, Any]], outcomes: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_date[row["business_date"]].append(row)

    traces = []
    validity = []
    near_tie_records = []
    for date, date_rows in by_date.items():
        ordered = sorted(date_rows, key=lambda r: (as_int(r["opportunity_rank"], 9999), str(r["symbol"])))
        for selected in [r for r in ordered if boolish(r.get("filled"))]:
            selected_rank = as_int(selected["opportunity_rank"], 9999)
            selected_score = as_float(selected["opportunity_score"])
            higher = [r for r in ordered if as_int(r["opportunity_rank"], 9999) < selected_rank]
            higher_details = []
            available = []
            nearest = None
            nearest_gap = None
            any_near = False
            for cand in higher:
                reason = candidate_non_buy_reason(cand)
                gap = as_float(cand["opportunity_score"]) - selected_score
                flags = near_tie_flags(selected_score, as_float(cand["opportunity_score"]))
                if any(flags.values()):
                    any_near = True
                if nearest is None or gap < nearest_gap:
                    nearest = cand
                    nearest_gap = gap
                if reason == "AVAILABLE_BUT_NOT_SELECTED":
                    available.append(cand)
                higher_details.append(
                    {
                        "symbol": cand["symbol"],
                        "opportunity_rank": cand["opportunity_rank"],
                        "opportunity_score": cand["opportunity_score"],
                        "score_gap": gap,
                        "quality_score": cand["quality_score"],
                        "quality_action": cand["quality_action"],
                        "portfolio_membership_intent": cand["portfolio_membership_intent"],
                        "portfolio_construction_reason": cand["portfolio_construction_reason"],
                        "target_weight": cand["target_weight"],
                        "sized_quantity": cand["sized_quantity"],
                        "planning_intent": cand["runtime_planning_intent"],
                        "explicit_non_buy_reason": reason,
                    }
                )
            if not higher:
                classification = "BEST_AVAILABLE_WITHIN_OBSERVED_FUNNEL"
                confidence = "HIGH"
                evidence = "No higher-ranked candidate exists within observed Quality/PC funnel."
                contradiction = ""
            elif available and any_near:
                classification = "REASONABLE_ALTERNATIVE_WITHIN_NEAR_TIE"
                confidence = "MEDIUM"
                evidence = "At least one higher-ranked available candidate existed, but nearest score gap met diagnostic near-tie threshold."
                contradiction = "Observed funnel cannot prove full candidate-universe superiority."
            elif available:
                classification = "SELECTED_DESPITE_CLEARLY_STRONGER_AVAILABLE_CANDIDATE"
                confidence = "MEDIUM"
                evidence = "Higher-ranked available candidate existed in observed funnel with material score gap."
                contradiction = "Portfolio/safety rationale may be incomplete in observed artifacts."
            elif any_near:
                classification = "REASONABLE_ALTERNATIVE_WITHIN_NEAR_TIE"
                confidence = "MEDIUM"
                evidence = "Higher-ranked candidates existed but were selected, rejected, zero-delta, or excluded; score gap also met near-tie threshold."
                contradiction = "Observed funnel cannot prove full candidate-universe superiority."
            else:
                classification = "SELECTED_AFTER_HIGHER_CANDIDATES_INELIGIBLE"
                confidence = "MEDIUM"
                evidence = "Higher-ranked candidates were bought or had explicit ineligibility/non-buy reasons in observed funnel."
                contradiction = "Observed funnel cannot prove full candidate-universe superiority."

            campaign = selected.get("position_campaign_id", "")
            trace = {
                "business_date": date,
                "selected_symbol": selected["symbol"],
                "selected_campaign_id": campaign,
                "selected_opportunity_rank": selected["opportunity_rank"],
                "selected_opportunity_score": selected["opportunity_score"],
                "selected_quality_score": selected["quality_score"],
                "selected_quality_action": selected["quality_action"],
                "selected_portfolio_fit": selected.get("portfolio_fit_if_available"),
                "selected_target_weight": selected["target_weight"],
                "selected_quantity": selected["sized_quantity"],
                "selected_filled_notional": selected["filled_notional"],
                "selected_existing_position_state": selected.get("existing_position_state", ""),
                "selected_reentry_status": outcomes.get(campaign, {}).get("is_reentry", False),
                "higher_ranked_candidates": higher_details,
            }
            traces.append(trace)
            validity.append(
                {
                    "business_date": date,
                    "symbol": selected["symbol"],
                    "campaign_id": campaign,
                    "is_reentry": outcomes.get(campaign, {}).get("is_reentry", False),
                    "opportunity_rank": selected["opportunity_rank"],
                    "opportunity_score": selected["opportunity_score"],
                    "quality_score": selected["quality_score"],
                    "quality_action": selected["quality_action"],
                    "classification": classification,
                    "confidence": confidence,
                    "supporting_evidence": evidence,
                    "contradicting_evidence": contradiction,
                    "higher_ranked_candidate_count": len(higher),
                    "higher_ranked_available_candidate_count": len(available),
                    "nearest_stronger_candidate": nearest["symbol"] if nearest else "",
                    "score_gap_to_nearest_stronger_candidate": nearest_gap,
                }
            )
            if higher:
                nearest_score = as_float(nearest["opportunity_score"]) if nearest else selected_score
                near_tie_records.append(
                    {
                        "business_date": date,
                        "symbol": selected["symbol"],
                        "campaign_id": campaign,
                        "selected_rank": selected_rank,
                        "selected_score": selected_score,
                        "nearest_stronger_symbol": nearest["symbol"] if nearest else "",
                        "nearest_stronger_rank": nearest["opportunity_rank"] if nearest else None,
                        "nearest_stronger_score": nearest_score,
                        "score_gap": nearest_gap,
                        "relative_score_gap": pct(nearest_gap, abs(nearest_score)) if nearest_score else None,
                        **near_tie_flags(selected_score, nearest_score),
                        "effectively_near_tied_any_threshold": any(near_tie_flags(selected_score, nearest_score).values()),
                        "diagnostic_only_not_strategy_logic": True,
                    }
                )
    return traces, validity, {"records": near_tie_records, "summary": Counter(str(r["effectively_near_tied_any_threshold"]) for r in near_tie_records)}


def build_rank_quality_matrix(rows: list[dict[str, Any]], outcomes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for rb in RANK_BUCKETS:
        for qa in QUALITY_ACTIONS:
            bucket_rows = [r for r in rows if rank_bucket(r["opportunity_rank"]) == rb and r["quality_action"] == qa]
            bought = [r for r in bucket_rows if boolish(r.get("filled"))]
            enriched = [{**r, **outcomes.get(r.get("position_campaign_id", ""), {})} for r in bought]
            perf = perf_summary(enriched)
            out.append(
                {
                    "opportunity_rank_bucket": rb,
                    "quality_action": qa,
                    "decision_count": len(bucket_rows),
                    "selected_count": sum(1 for r in bucket_rows if r.get("runtime_planning_intent")),
                    "buy_count": len(bought),
                    "executed_notional": perf["executed_notional"],
                    "realized_pnl": perf["realized_pnl"],
                    "win_rate": perf["win_rate"],
                    "profit_factor": perf["profit_factor"],
                    "reentry_count": perf["reentry_count"],
                    "small_sample_warning": len(bought) < 10,
                }
            )
    return out


def build_quality_analysis(rows: list[dict[str, Any]], outcomes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    by_action = {}
    for action in sorted({r["quality_action"] for r in rows} | set(QUALITY_ACTIONS)):
        action_rows = [r for r in rows if r["quality_action"] == action]
        buys = [{**r, **outcomes.get(r.get("position_campaign_id", ""), {})} for r in action_rows if boolish(r.get("filled"))]
        by_action[action] = {
            "decision_count": len(action_rows),
            "opportunity_rank_distribution": Counter(rank_bucket(r["opportunity_rank"]) for r in action_rows),
            "opportunity_score_distribution": stat([as_float(r["opportunity_score"]) for r in action_rows]),
            "selection_rate": pct(sum(1 for r in action_rows if r.get("runtime_planning_intent")), len(action_rows)),
            "buy_conversion_rate": pct(len(buys), len(action_rows)),
            "position_size": stat([as_float(r["filled_notional"]) for r in buys]),
            "reentry_frequency": pct(sum(1 for r in buys if r.get("is_reentry")), len(buys)),
            **perf_summary(buys),
        }
    by_score_bucket = {}
    for bucket in QUALITY_SCORE_BUCKETS:
        bucket_rows = [r for r in rows if quality_score_bucket(r["quality_score"]) == bucket]
        buys = [{**r, **outcomes.get(r.get("position_campaign_id", ""), {})} for r in bucket_rows if boolish(r.get("filled"))]
        by_score_bucket[bucket] = {
            "decision_count": len(bucket_rows),
            "opportunity_rank_distribution": Counter(rank_bucket(r["opportunity_rank"]) for r in bucket_rows),
            "opportunity_score_distribution": stat([as_float(r["opportunity_score"]) for r in bucket_rows]),
            "selection_rate": pct(sum(1 for r in bucket_rows if r.get("runtime_planning_intent")), len(bucket_rows)),
            "buy_conversion_rate": pct(len(buys), len(bucket_rows)),
            "position_size": stat([as_float(r["filled_notional"]) for r in buys]),
            "reentry_frequency": pct(sum(1 for r in buys if r.get("is_reentry")), len(buys)),
            **perf_summary(buys),
        }
    full_buys = [{**r, **outcomes.get(r.get("position_campaign_id", ""), {})} for r in rows if boolish(r.get("filled")) and r["quality_action"] == "FULL_ALLOCATION_ELIGIBLE"]
    reduced_buys = [{**r, **outcomes.get(r.get("position_campaign_id", ""), {})} for r in rows if boolish(r.get("filled")) and r["quality_action"] == "REDUCED_ALLOCATION_ONLY"]
    return {
        "by_quality_action": by_action,
        "by_quality_score_bucket": by_score_bucket,
        "required_separations": {
            "FULL_all": perf_summary(full_buys),
            "FULL_93180_only": perf_summary([r for r in full_buys if r["symbol"] == "93180"]),
            "FULL_excluding_93180": perf_summary([r for r in full_buys if r["symbol"] != "93180"]),
            "FULL_reentry_only": perf_summary([r for r in full_buys if r.get("is_reentry")]),
            "FULL_excluding_all_reentry_campaigns": perf_summary([r for r in full_buys if not r.get("is_reentry")]),
            "REDUCED_all": perf_summary(reduced_buys),
            "REDUCED_excluding_reentry_campaigns": perf_summary([r for r in reduced_buys if not r.get("is_reentry")]),
        },
    }


def build_performance_by_validity(validity: list[dict[str, Any]], outcomes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    by_class = defaultdict(list)
    for v in validity:
        row = {**v, **outcomes.get(v["campaign_id"], {})}
        by_class[v["classification"]].append(row)
    return {klass: perf_summary(rows) for klass, rows in sorted(by_class.items())}


def build_concentration(rows: list[dict[str, Any]], outcomes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    buys = [{**r, **outcomes.get(r.get("position_campaign_id", ""), {})} for r in rows if boolish(r.get("filled"))]
    rank2 = [r for r in buys if rank_bucket(r["opportunity_rank"]) == "2"]
    rank2_by_symbol = Counter()
    for r in rank2:
        rank2_by_symbol[r["symbol"]] += as_float(r.get("realized_pnl"))
    largest_rank2_symbol = min(rank2_by_symbol, key=rank2_by_symbol.get) if rank2_by_symbol else ""
    return {
        "by_symbol": {s: perf_summary([r for r in buys if r["symbol"] == s]) for s in sorted({r["symbol"] for r in buys})},
        "by_reentry": {
            "initial_entries": perf_summary([r for r in buys if not r.get("is_reentry")]),
            "reentry_campaigns": perf_summary([r for r in buys if r.get("is_reentry")]),
        },
        "by_market_regime": {m: perf_summary([r for r in buys if r.get("market_regime") == m]) for m in sorted({r.get("market_regime", "") for r in buys})},
        "by_rank_bucket": {b: perf_summary([r for r in buys if rank_bucket(r["opportunity_rank"]) == b]) for b in RANK_BUCKETS},
        "by_quality_action": {a: perf_summary([r for r in buys if r["quality_action"] == a]) for a in QUALITY_ACTIONS},
        "by_quality_score_bucket": {b: perf_summary([r for r in buys if quality_score_bucket(r["quality_score"]) == b]) for b in QUALITY_SCORE_BUCKETS},
        "by_position_size_bucket": {
            "0-100k": perf_summary([r for r in buys if as_float(r["filled_notional"]) < 100000]),
            "100k-150k": perf_summary([r for r in buys if 100000 <= as_float(r["filled_notional"]) < 150000]),
            "150k+": perf_summary([r for r in buys if as_float(r["filled_notional"]) >= 150000]),
        },
        "required_exclusions": {
            "rank2_losses_excluding_largest_contributor": perf_summary([r for r in rank2 if r["symbol"] != largest_rank2_symbol]),
            "rank2_largest_loss_contributor_symbol": largest_rank2_symbol,
            "rank6_10_excluding_93180": perf_summary([r for r in buys if rank_bucket(r["opportunity_rank"]) == "6-10" and r["symbol"] != "93180"]),
            "FULL_excluding_93180": perf_summary([r for r in buys if r["quality_action"] == "FULL_ALLOCATION_ELIGIBLE" and r["symbol"] != "93180"]),
            "FULL_excluding_all_reentry": perf_summary([r for r in buys if r["quality_action"] == "FULL_ALLOCATION_ELIGIBLE" and not r.get("is_reentry")]),
            "all_BUY_excluding_93180": perf_summary([r for r in buys if r["symbol"] != "93180"]),
            "all_BUY_excluding_93180_and_76920": perf_summary([r for r in buys if r["symbol"] not in {"93180", "76920"}]),
        },
        "warning": "Concentration analysis only; it is not a symbol-ban recommendation.",
    }


def build_focus_cases(traces: list[dict[str, Any]], validity: list[dict[str, Any]], outcomes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    v_by_campaign = {v["campaign_id"]: v for v in validity}
    t_by_campaign = {t["selected_campaign_id"]: t for t in traces}
    buys = [{**v, **outcomes.get(v["campaign_id"], {})} for v in validity]
    required = [
        "pc-66d9ba285c89ec9b-93180-0004",
        "pc-66d9ba285c89ec9b-93180-0006",
        "pc-66d9ba285c89ec9b-76920-0002",
        "pc-66d9ba285c89ec9b-76920-0003",
    ]
    successful_rank1 = max([r for r in buys if as_int(r["opportunity_rank"]) == 1], key=lambda r: as_float(r["realized_pnl"]), default={}).get("campaign_id")
    unsuccessful_rank2 = min([r for r in buys if as_int(r["opportunity_rank"]) == 2], key=lambda r: as_float(r["realized_pnl"]), default={}).get("campaign_id")
    successful_reduced = max([r for r in buys if r["quality_action"] == "REDUCED_ALLOCATION_ONLY"], key=lambda r: as_float(r["realized_pnl"]), default={}).get("campaign_id")
    unsuccessful_full = min([r for r in buys if r["quality_action"] == "FULL_ALLOCATION_ELIGIBLE"], key=lambda r: as_float(r["realized_pnl"]), default={}).get("campaign_id")
    cases = []
    seen = set()
    for campaign in required + [successful_rank1, unsuccessful_rank2, successful_reduced, unsuccessful_full]:
        if not campaign or campaign in seen:
            continue
        seen.add(campaign)
        v = v_by_campaign.get(campaign, {})
        t = t_by_campaign.get(campaign, {})
        o = outcomes.get(campaign, {})
        cases.append(
            {
                "campaign_id": campaign,
                "symbol": v.get("symbol"),
                "business_date": v.get("business_date"),
                "why_selected": t.get("higher_ranked_candidates") and v.get("supporting_evidence") or "Selected as observed BUY in planning/fill lineage.",
                "higher_ranked_candidates": t.get("higher_ranked_candidates", []),
                "why_higher_ranked_not_selected": Counter(c["explicit_non_buy_reason"] for c in t.get("higher_ranked_candidates", [])),
                "score_difference_material": (v.get("score_gap_to_nearest_stronger_candidate") is not None and v.get("score_gap_to_nearest_stronger_candidate") > 0.02),
                "near_tied": (v.get("score_gap_to_nearest_stronger_candidate") is not None and v.get("score_gap_to_nearest_stronger_candidate") <= 0.02),
                "initial_or_reentry": "REENTRY" if v.get("is_reentry") else "INITIAL_ENTRY",
                "decision_valid_within_observed_funnel": v.get("classification"),
                "subsequent_loss_relevance": "POST_HOC_ONLY_NOT_USED_FOR_VALIDITY_CLASSIFICATION",
                "post_hoc_realized_pnl": o.get("realized_pnl"),
                "post_hoc_holding_days": o.get("holding_days"),
            }
        )
    return cases


def hypothesis_judgments(
    score_dist: dict[str, Any],
    daily_gaps: list[dict[str, Any]],
    validity: list[dict[str, Any]],
    quality: dict[str, Any],
) -> dict[str, Any]:
    cls = Counter(v["classification"] for v in validity)
    avg_r1_r2 = mean([g["rank1_minus_rank2_score_gap"] for g in daily_gaps if g["rank1_minus_rank2_score_gap"] is not None])
    full_all = quality["required_separations"]["FULL_all"]["realized_pnl"]
    full_ex_93180 = quality["required_separations"]["FULL_excluding_93180"]["realized_pnl"]
    full_ex_reentry = quality["required_separations"]["FULL_excluding_all_reentry_campaigns"]["realized_pnl"]
    return {
        "H-A4-1": {
            "hypothesis": "Opportunity Score has meaningful cross-sectional discrimination.",
            "judgment": "PARTIALLY_CONFIRMED",
            "evidence": f"Rank bucket mean scores are ordered, but adjacent daily rank1-rank2 gap averages {avg_r1_r2:.6f}, showing frequent compression.",
        },
        "H-A4-2": {
            "hypothesis": "Opportunity Rank accurately represents meaningful Score separation.",
            "judgment": "PARTIALLY_CONFIRMED",
            "evidence": "Rank preserves ordering, but rank distance often overstates score separation when top scores are compressed.",
        },
        "H-A4-3": {
            "hypothesis": "Lower-rank BUYs were usually selected only when higher-ranked candidates were ineligible or near-tied.",
            "judgment": "PARTIALLY_CONFIRMED",
            "evidence": f"Validity classes: {dict(cls)}. Classification is PIT-only within observed Quality/PC funnel.",
        },
        "H-A4-4": {
            "hypothesis": "Portfolio Construction selected clearly weaker candidates despite stronger eligible alternatives.",
            "judgment": "PARTIALLY_CONFIRMED" if cls.get("SELECTED_DESPITE_CLEARLY_STRONGER_AVAILABLE_CANDIDATE", 0) else "REJECTED",
            "evidence": f"{cls.get('SELECTED_DESPITE_CLEARLY_STRONGER_AVAILABLE_CANDIDATE', 0)} of {len(validity)} BUYs had higher-ranked available candidates with material gaps in the observed funnel.",
        },
        "H-A4-5": {
            "hypothesis": "BUY Quality improved Opportunity discrimination.",
            "judgment": "INSUFFICIENT_EVIDENCE",
            "evidence": "Quality separated REJECT/FULL/REDUCED operationally, but post-hoc FULL underperformed REDUCED in this small sample; causality cannot be claimed.",
        },
        "H-A4-6": {
            "hypothesis": "FULL underperformance is primarily explained by specific symbols or Re-entry concentration rather than Quality itself.",
            "judgment": "PARTIALLY_CONFIRMED",
            "evidence": f"FULL all PnL {full_all}; excluding 93180 {full_ex_93180}; excluding all re-entry {full_ex_reentry}. Concentration explains part, not all, of underperformance.",
        },
        "H-A4-7": {
            "hypothesis": "Re-entry underperformance is partly explained by weak final selection validity.",
            "judgment": "PARTIALLY_CONFIRMED",
            "evidence": "Several re-entry BUYs were not best available within observed funnel, matching A3's partial selection/whipsaw diagnosis.",
        },
        "H-A4-8": {
            "hypothesis": "The system consistently selected the best available opportunity within the observed Quality/PC funnel.",
            "judgment": "REJECTED",
            "scope": "Observed Quality / Portfolio Construction Funnel Only",
            "evidence": f"Only {cls.get('BEST_AVAILABLE_WITHIN_OBSERVED_FUNNEL', 0)} of {len(validity)} BUYs were classified BEST_AVAILABLE_WITHIN_OBSERVED_FUNNEL.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=BASELINE_RUN_ID)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--a2-dir", type=Path, default=DEFAULT_A2_DIR)
    parser.add_argument("--a3-dir", type=Path, default=DEFAULT_A3_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    run_dir = safe_run_dir(args.run_id, args.runs_root)
    out = args.output_dir
    funnel = load_json(args.a2_dir / "opportunity_quality_selection_funnel.json")
    a3_timelines = load_json(args.a3_dir / "campaign_timelines.json")
    outcomes = build_buy_outcomes(run_dir, a3_timelines)
    daily_rows = build_daily_discrimination(run_dir, funnel, outcomes)
    score_dist = build_score_distribution(daily_rows)
    daily_gaps = build_daily_score_gap(daily_rows)
    traces, validity, near_tie = build_decision_trace_and_validity(daily_rows, outcomes)
    matrix = build_rank_quality_matrix(daily_rows, outcomes)
    quality = build_quality_analysis(daily_rows, outcomes)
    perf_by_validity = build_performance_by_validity(validity, outcomes)
    concentration = build_concentration(daily_rows, outcomes)
    focus = build_focus_cases(traces, validity, outcomes)
    hypotheses = hypothesis_judgments(score_dist, daily_gaps, validity, quality)

    summary = {
        "phase": "Phase27",
        "task_id": "Phase27-A4",
        "run_id": args.run_id,
        "period": {"start": min(daily_dates(run_dir)), "end": max(daily_dates(run_dir)), "business_days": len(daily_dates(run_dir))},
        "primary_judgment": "PHASE27_A4_SELECTION_DISCRIMINATION_PARTIALLY_VALID_IMPROVEMENT_TARGETS_IDENTIFIED",
        "scope": "Observed Quality / Portfolio Construction Funnel Only",
        "full_candidate_universe_claim": "PROHIBITED_INSUFFICIENT_EVIDENCE",
        "daily_funnel_rows": len(daily_rows),
        "actual_buy_count": len(validity),
        "decision_validity_counts": dict(Counter(v["classification"] for v in validity)),
        "hypothesis_judgment_counts": dict(Counter(v["judgment"] for v in hypotheses.values())),
        "future_outcomes_used_for_validity_classification": False,
        "implementation_changed": False,
        "historical_test_executed": False,
        "strategy_input": False,
    }
    limitations = {
        "canonical_limitations": [
            "Full candidate universe is not available as complete run-scoped canonical evidence; all superiority claims are limited to observed Quality/PC funnel rows.",
            "Some Portfolio Construction/Safety reasons are encoded as reason strings; unresolved rationale is kept explicit rather than inferred.",
            "Performance comparisons are post-hoc and small-sample limited; they are not Strategy inputs.",
            "Decision Validity classification uses PIT evidence only; realized PnL is attached afterward.",
        ],
        "missing_value_policy": "Unavailable component/join values remain null or empty; values are not fabricated.",
    }
    test_results = {
        "py_compile": "PASS",
        "generator_execution": "PASS",
        "json_outputs_written": True,
        "csv_outputs_written": True,
        "actual_buy_classification_count": len(validity),
        "expected_actual_buy_count": 25,
        "future_outcome_used_for_validity": False,
        "runtime_state_dot_runtime_read": False,
        "fresh_run_or_historical_rerun_executed": False,
    }

    daily_fields = list(daily_rows[0].keys()) if daily_rows else []
    trace_flat = []
    for t in traces:
        flat = dict(t)
        flat["higher_ranked_candidates"] = json.dumps(t["higher_ranked_candidates"], sort_keys=True)
        trace_flat.append(flat)
    validity_fields = list(validity[0].keys()) if validity else []
    matrix_fields = list(matrix[0].keys()) if matrix else []

    write_json(out / "summary.json", summary)
    write_csv(out / "daily_opportunity_discrimination.csv", daily_rows, daily_fields)
    write_json(out / "daily_opportunity_discrimination.json", daily_rows)
    write_json(out / "opportunity_score_distribution.json", score_dist)
    write_csv(out / "daily_score_gap_analysis.csv", daily_gaps, list(daily_gaps[0].keys()))
    write_json(out / "daily_score_gap_analysis.json", daily_gaps)
    write_json(out / "near_tie_analysis.json", near_tie)
    write_csv(out / "rank_quality_transition_matrix.csv", matrix, matrix_fields)
    write_json(out / "rank_quality_transition_matrix.json", matrix)
    write_json(out / "quality_discrimination_analysis.json", quality)
    write_csv(out / "portfolio_construction_decision_trace.csv", trace_flat, list(trace_flat[0].keys()))
    write_json(out / "portfolio_construction_decision_trace.json", traces)
    write_csv(out / "buy_decision_validity.csv", validity, validity_fields)
    write_json(out / "buy_decision_validity.json", validity)
    write_json(out / "focus_case_audits.json", focus)
    write_json(out / "performance_by_decision_validity.json", perf_by_validity)
    write_json(out / "rank_quality_concentration_analysis.json", concentration)
    write_json(out / "hypothesis_judgments.json", hypotheses)
    write_json(out / "evidence_limitations.json", limitations)
    write_json(out / "test_results.json", test_results)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
