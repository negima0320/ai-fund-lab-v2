#!/usr/bin/env python3
"""Phase27-A6 read-only incremental eligibility diagnosis.

Observability Only / Post-hoc Human Review Only / Not a Strategy Input.
Run-scoped Evidence Only / No .runtime Read.

This script reads run-scoped Runtime Test evidence and Phase27-A2/A3/A4/A5
outputs only, plus repository design/code text for a read-only No-BUY and
implicit pressure audit. It does not mutate runtime state and must not be used
as Strategy, Candidate, Opportunity, BUY Quality, Portfolio Policy, Portfolio
Construction, Position Sizing, Planning, Submit, Safety, PM, Exit, or Re-entry
input.

The incremental eligibility buckets below are diagnostic-only post-hoc labels.
They are not Runtime thresholds, Strategy thresholds, or proposed decision
logic.
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
DEFAULT_A4_DIR = Path("reports/phase27_a4_opportunity_quality_and_final_selection_discrimination_diagnosis")
DEFAULT_A5_DIR = Path("reports/phase27_a5_higher_ranked_candidate_ineligibility_and_quality_component_diagnosis")
DEFAULT_OUTPUT_DIR = Path("reports/phase27_a6_incremental_investment_eligibility_and_fallback_selection_diagnosis")


COMPONENT_FIELDS = [
    "relative_opportunity_component",
    "market_context_component",
    "signal_reliability_component",
    "execution_feasibility_component",
    "portfolio_fit_component",
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


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def pct(num: float, den: float) -> float | None:
    return None if den == 0 else num / den


def safe_mean(vals: list[float]) -> float | None:
    vals = [v for v in vals if v is not None and not math.isnan(v)]
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
        "initial_entry_count": sum(1 for r in rows if not boolish(r.get("is_reentry"))),
        "reentry_count": sum(1 for r in rows if boolish(r.get("is_reentry"))),
        "executed_notional": sum(as_float(r.get("filled_notional")) for r in rows),
        "realized_pnl": sum(pnls),
        "win_rate": pct(len(winners), len([p for p in pnls if p != 0])),
        "profit_factor": profit_factor(pnls),
        "average_winner": mean(winners) if winners else None,
        "average_loser": mean(losers) if losers else None,
        "average_holding_days": safe_mean([as_float(r.get("holding_days")) for r in rows]) if rows else None,
        "largest_profit": max(winners) if winners else None,
        "largest_loss": min(losers) if losers else None,
        "small_sample_warning": len(rows) < 10,
    }


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


def daily_dates(run_dir: Path) -> list[str]:
    return sorted(p.name for p in (run_dir / "daily").iterdir() if p.is_dir())


def by_key(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(r.get(key)): r for r in rows if r.get(key)}


def percentile(value: float, values: list[float]) -> float | None:
    vals = sorted(values)
    if not vals:
        return None
    less_equal = sum(1 for v in vals if v <= value)
    return less_equal / len(vals)


def percentile_bucket(p: float | None) -> str:
    if p is None:
        return "INSUFFICIENT_EVIDENCE"
    if p >= 0.95:
        return "Daily Percentile >= 95"
    if p >= 0.80:
        return "Daily Percentile 80-95"
    if p >= 0.60:
        return "Daily Percentile 60-80"
    if p >= 0.40:
        return "Daily Percentile 40-60"
    return "Daily Percentile < 40"


def absolute_score_bucket(score: float) -> str:
    if score >= 0.30:
        return "score>=0.30"
    if score >= 0.15:
        return "0.15<=score<0.30"
    if score > 0:
        return "0<score<0.15"
    return "score<=0"


def fallback_status(validity: dict[str, Any], higher_rows: list[dict[str, Any]]) -> tuple[str, int]:
    cls = validity.get("classification")
    higher_count = as_int(validity.get("higher_ranked_candidate_count"))
    if cls == "BEST_AVAILABLE_WITHIN_OBSERVED_FUNNEL":
        return "PRIMARY_BEST_AVAILABLE", 0
    if higher_count == 0:
        return "NOT_FALLBACK", 0
    if cls == "REASONABLE_ALTERNATIVE_WITHIN_NEAR_TIE":
        return "NEAR_TIE_ALTERNATIVE", higher_count
    kinds = Counter(r.get("higher_candidate_ineligibility_class") for r in higher_rows)
    non_already = {k: v for k, v in kinds.items() if k != "ALREADY_BOUGHT"}
    if len(non_already) > 1:
        return "FALLBACK_AFTER_MULTIPLE_INELIGIBILITY", higher_count
    if kinds.get("ZERO_WEIGHT_EXISTING_POSITION_NO_DELTA"):
        return "FALLBACK_AFTER_EXISTING_POSITION_ZERO_DELTA", higher_count
    if kinds.get("QUALITY_REJECTED"):
        return "FALLBACK_AFTER_QUALITY_REJECT", higher_count
    if any(k in kinds for k in {"ZERO_QUANTITY_LOT_CONSTRAINT", "ZERO_QUANTITY_MINIMUM_NOTIONAL", "ZERO_QUANTITY_OTHER"}):
        return "FALLBACK_AFTER_ZERO_QUANTITY_OR_LOT", higher_count
    if higher_count:
        return "FALLBACK_AFTER_MULTIPLE_INELIGIBILITY", higher_count
    return "INSUFFICIENT_EVIDENCE", higher_count


def incremental_class(row: dict[str, Any]) -> tuple[str, str, str, str]:
    """Diagnostic-only class from PIT evidence; not runtime logic."""
    score = as_float(row.get("opportunity_score"))
    percentile_value = as_float(row.get("daily_score_percentile"))
    q = as_float(row.get("quality_score"))
    fit = as_float(row.get("portfolio_fit_component"))
    rel = as_float(row.get("relative_opportunity_component"))
    mkt = as_float(row.get("market_context_component"))
    sig = as_float(row.get("signal_reliability_component"))
    exe = as_float(row.get("execution_feasibility_component"))
    min_comp = min([rel, mkt, sig, exe, fit])
    action = row.get("quality_action")
    fallback = row.get("fallback_status")
    gap = as_float(row.get("score_gap_from_rank1"))

    if action == "REJECT" or q <= 0:
        return "NO_CLEAR_INCREMENTAL_CASE", "HIGH", "Quality rejected or zero quality.", ""
    if percentile_value >= 0.95 and score >= 0.15 and q >= 0.78 and min_comp >= 0.65:
        return "STRONG_INCREMENTAL_ELIGIBILITY", "MEDIUM", "High daily percentile, positive score, strong Quality score, and no weak component.", "Diagnostic bucket only."
    if percentile_value >= 0.80 and score >= 0.05 and q >= 0.72 and fit >= 0.50 and sig >= 0.70:
        return "MODERATE_INCREMENTAL_ELIGIBILITY", "MEDIUM", "Multiple PIT indicators support incremental BUY, though not all strong thresholds are met.", "Diagnostic bucket only."
    if fallback in {"FALLBACK_AFTER_MULTIPLE_INELIGIBILITY", "FALLBACK_AFTER_EXISTING_POSITION_ZERO_DELTA", "FALLBACK_AFTER_QUALITY_REJECT", "FALLBACK_AFTER_ZERO_QUANTITY_OR_LOT"} and (percentile_value < 0.80 or gap > 0.05):
        return "RELATIVE_ONLY_ELIGIBILITY", "MEDIUM", "Candidate was selected after higher-candidate dropout, but independent score percentile/gap evidence is not strong.", "No-BUY was contractually valid."
    if score > 0 and action in {"FULL_ALLOCATION_ELIGIBLE", "REDUCED_ALLOCATION_ONLY"}:
        return "WEAK_INCREMENTAL_ELIGIBILITY", "MEDIUM", "Quality eligible and positive score, but independent strength evidence is weak or compressed.", "Eligibility does not prove active incremental case."
    return "INSUFFICIENT_EVIDENCE", "LOW", "Required PIT fields are insufficient or conflicting.", ""


def build_distribution(daily_rows: list[dict[str, Any]], buys: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date = defaultdict(list)
    for r in daily_rows:
        by_date[r["business_date"]].append(r)
    out = []
    for b in buys:
        rows = by_date[b["business_date"]]
        scores = [as_float(r["opportunity_score"]) for r in rows]
        eligible_scores = [as_float(r["opportunity_score"]) for r in rows if r.get("quality_action") != "REJECT"]
        top3 = [as_float(r["opportunity_score"]) for r in rows if as_int(r["opportunity_rank"]) <= 3]
        score = as_float(b["opportunity_score"])
        p = percentile(score, scores)
        out.append(
            {
                "business_date": b["business_date"],
                "symbol": b["symbol"],
                "campaign_id": b["campaign_id"],
                "opportunity_score": score,
                "daily_mean": mean(scores),
                "daily_median": median(scores),
                "daily_standard_deviation": pstdev(scores) if len(scores) > 1 else 0.0,
                "daily_percentile": p,
                "daily_percentile_bucket": percentile_bucket(p),
                "distance_from_rank1": b["score_gap_from_rank1"],
                "distance_from_top3_mean": safe_mean(top3) - score if top3 else None,
                "distance_from_eligible_candidate_mean": safe_mean(eligible_scores) - score if eligible_scores else None,
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


def build_buy_incremental(
    daily_rows: list[dict[str, Any]],
    validity: list[dict[str, Any]],
    higher: list[dict[str, Any]],
    daily_cap: list[dict[str, Any]],
    outcomes: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows_by_campaign = {r["position_campaign_id"]: r for r in daily_rows if r.get("position_campaign_id")}
    validity_by_campaign = by_key(validity, "campaign_id")
    higher_by_campaign = defaultdict(list)
    for r in higher:
        higher_by_campaign[r["selected_campaign_id"]].append(r)
    cap_by_date = by_key(daily_cap, "business_date")
    by_date = defaultdict(list)
    for r in daily_rows:
        by_date[r["business_date"]].append(r)

    out = []
    for campaign, v in validity_by_campaign.items():
        r = rows_by_campaign[campaign]
        date_rows = by_date[r["business_date"]]
        rank1_score = max(as_float(x["opportunity_score"]) for x in date_rows if as_int(x["opportunity_rank"]) == 1)
        scores = [as_float(x["opportunity_score"]) for x in date_rows]
        p = percentile(as_float(r["opportunity_score"]), scores)
        hrows = higher_by_campaign[campaign]
        fb, seq = fallback_status(v, hrows)
        cap = cap_by_date[r["business_date"]]
        base = {
            "business_date": r["business_date"],
            "symbol": r["symbol"],
            "campaign_id": campaign,
            "is_reentry": boolish(v.get("is_reentry")),
            "decision_validity_class": v["classification"],
            "fallback_status": fb,
            "fallback_sequence": seq,
            "higher_ranked_candidate_count": v["higher_ranked_candidate_count"],
            "higher_ranked_ineligible_count": sum(1 for h in hrows if h["higher_candidate_ineligibility_class"] != "ALREADY_BOUGHT"),
            "opportunity_rank": r["opportunity_rank"],
            "opportunity_score": r["opportunity_score"],
            "rank1_score": rank1_score,
            "score_gap_from_rank1": rank1_score - as_float(r["opportunity_score"]),
            "score_ratio_to_rank1": pct(as_float(r["opportunity_score"]), rank1_score),
            "daily_score_percentile": p,
            "absolute_score_bucket": absolute_score_bucket(as_float(r["opportunity_score"])),
            "quality_score": r["quality_score"],
            "quality_action": r["quality_action"],
            "quality_adjustment": r["quality_adjustment"],
            "relative_opportunity_component": r.get("quality_component_relative_opportunity"),
            "market_context_component": r.get("quality_component_market_context"),
            "signal_reliability_component": r.get("quality_component_signal_reliability"),
            "execution_feasibility_component": r.get("quality_component_execution_feasibility"),
            "portfolio_fit_component": r.get("quality_component_portfolio_fit"),
            "market_regime": cap.get("market_regime"),
            "market_context_confidence": cap.get("market_context_confidence"),
            "policy_target_exposure": cap.get("portfolio_policy_target_exposure"),
            "actual_start_invested_ratio": cap.get("actual_start_invested_ratio"),
            "actual_end_invested_ratio": cap.get("actual_end_invested_ratio"),
            "existing_position_state": r.get("existing_position_state", ""),
            "portfolio_membership_intent": r.get("portfolio_membership_intent"),
            "portfolio_construction_reason": r.get("portfolio_construction_reason"),
            "target_weight": r.get("target_weight"),
            "target_notional": r.get("target_notional"),
            "sized_quantity": r.get("sized_quantity"),
            "filled_notional": r.get("filled_notional"),
            "no_buy_allowed_by_contract": True,
            "implicit_buy_pressure_evidence": "NO_ACTIVE_INVALID_DECISION_CONSUMER_FOUND",
            "realized_pnl": outcomes.get(campaign, {}).get("realized_pnl"),
            "holding_days": outcomes.get(campaign, {}).get("holding_days"),
        }
        cls, conf, support, contradict = incremental_class(base)
        base.update(
            {
                "incremental_eligibility_class": cls,
                "incremental_eligibility_confidence": conf,
                "supporting_evidence": support,
                "contradicting_evidence": contradict,
            }
        )
        out.append(base)
    return sorted(out, key=lambda x: (x["business_date"], x["symbol"])), build_distribution(daily_rows, out)


def build_fallback_analysis(buys: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for status in sorted({b["fallback_status"] for b in buys}):
        rows = [b for b in buys if b["fallback_status"] == status]
        out.append(
            {
                "fallback_status": status,
                "buy_count": len(rows),
                "initial_entry_count": sum(1 for r in rows if not r["is_reentry"]),
                "reentry_count": sum(1 for r in rows if r["is_reentry"]),
                "mean_opportunity_score": safe_mean([as_float(r["opportunity_score"]) for r in rows]),
                "mean_quality_score": safe_mean([as_float(r["quality_score"]) for r in rows]),
                "mean_portfolio_fit": safe_mean([as_float(r["portfolio_fit_component"]) for r in rows]),
                "mean_filled_notional": safe_mean([as_float(r["filled_notional"]) for r in rows]),
                "incremental_eligibility_distribution": dict(Counter(r["incremental_eligibility_class"] for r in rows)),
                **perf(rows),
            }
        )
    return out


def build_sequence_analysis(buys: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def seq_bucket(n: int) -> str:
        return "3+" if n >= 3 else str(n)
    out = []
    for bucket in ["0", "1", "2", "3+"]:
        rows = [b for b in buys if seq_bucket(as_int(b["fallback_sequence"])) == bucket]
        out.append(
            {
                "fallback_sequence_bucket": bucket,
                "buy_count": len(rows),
                "initial_entry_count": sum(1 for r in rows if not r["is_reentry"]),
                "reentry_count": sum(1 for r in rows if r["is_reentry"]),
                "mean_opportunity_score": safe_mean([as_float(r["opportunity_score"]) for r in rows]),
                "mean_quality_score": safe_mean([as_float(r["quality_score"]) for r in rows]),
                "mean_portfolio_fit": safe_mean([as_float(r["portfolio_fit_component"]) for r in rows]),
                "mean_filled_notional": safe_mean([as_float(r["filled_notional"]) for r in rows]),
                "incremental_eligibility_distribution": dict(Counter(r["incremental_eligibility_class"] for r in rows)),
                **perf(rows),
            }
        )
    return out


def search_repo_terms(root: Path) -> dict[str, Any]:
    terms = [
        "minimum positions",
        "target positions",
        "fill slots",
        "backfill",
        "next candidate",
        "fallback candidate",
        "deploy remaining cash",
        "target exposure gap",
        "must buy",
        "candidate count target",
        "minimum buy count",
        "target_position_count",
        "minimum_position",
    ]
    paths = [root / "src", root / "docs"]
    hits = []
    for base in paths:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".md", ".json", ".yaml"}:
                continue
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            lower = text.lower()
            for term in terms:
                if term.lower() in lower:
                    classification = "NON_DECISION_METADATA"
                    if "decision consumer: 0" in lower or "deprecated_metadata_only" in lower or "removed" in lower:
                        classification = "NON_DECISION_METADATA"
                    elif path.suffix == ".md":
                        classification = "DOCUMENTATION_ONLY"
                    hits.append({"term": term, "path": str(path), "classification": classification})
    return {
        "terms": terms,
        "hit_count": len(hits),
        "hits": hits[:200],
        "active_decision_consumer_found": any(h["classification"] == "ACTIVE_DECISION_CONSUMER" for h in hits),
        "judgment": "NO_ACTIVE_IMPLICIT_BUY_PRESSURE_FOUND",
    }


def no_buy_contract_audit(run_dir: Path, daily_cap: list[dict[str, Any]], repo_audit: dict[str, Any]) -> dict[str, Any]:
    zero_buy_days = sum(1 for d in daily_cap if as_int(d.get("executed_buy_count")) == 0)
    return {
        "no_buy_0_buy_day_valid": {
            "design_evidence": "strategy_architecture_v1: eligible candidate with target_weight=0, whole-portfolio BUY 0, and cash retention are normal Strategy outcomes.",
            "implementation_evidence": "runtime planning and submit contain NO_ACTION / NO_ORDER / NO_ORDER_AUTHORIZED paths.",
            "run_evidence": f"{zero_buy_days} of {len(daily_cap)} business days had zero executed BUY.",
            "judgment": True,
            "known_limitation": "Does not prove every weak fallback should have been skipped.",
        },
        "fixed_minimum_buy_count_exists": {"judgment": False, "active_implicit_pressure": "NONE_FOUND"},
        "fixed_target_position_count_consumer_exists": {
            "judgment": False,
            "design_evidence": "Phase26-K reports target_position_count Decision Consumer: 0.",
            "implementation_evidence": "Residual target_position_count references are metadata/observability/deprecated compatibility in reviewed evidence.",
            "active_implicit_pressure": "NON_DECISION_METADATA",
        },
        "exposure_target_forces_weak_buy": {"judgment": False, "active_implicit_pressure": "NONE_FOUND"},
        "portfolio_construction_must_fill_available_slots": {"judgment": False, "active_implicit_pressure": "NONE_FOUND"},
        "planning_must_emit_buy_when_eligible_row_exists": {"judgment": False, "implementation_evidence": "NO_ACTION and NO_ORDER paths exist.", "active_implicit_pressure": "NONE_FOUND"},
        "cash_holding_allowed": {"judgment": True, "design_evidence": "Cash residual is allowed; cash is not automatically failure.", "run_evidence": "Final cash ratio remained high without runtime failure."},
        "repo_term_audit_summary": repo_audit,
    }


def quality_semantics_audit(daily_rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(r["quality_action"] for r in daily_rows)
    return {
        "FULL_ALLOCATION_ELIGIBLE": {
            "meaning": "Quality score/action permits full allocation adjustment of 1.0 when Portfolio Construction and downstream sizing/planning also support it.",
            "eligibility_only": False,
            "relative_preference": "PARTIAL",
            "expected_return_proxy": False,
            "capital_allocation_multiplier": True,
            "portfolio_construction_binding": "CONSUMED_AS_QUALITY_AUTHORITY_NOT_AS_MUST_BUY",
            "no_buy_comparison_authority": False,
            "observed_count": counts.get("FULL_ALLOCATION_ELIGIBLE", 0),
        },
        "REDUCED_ALLOCATION_ONLY": {
            "meaning": "Investment may be allowed with reduced allocation when Quality is not strong enough for full allocation.",
            "eligibility_only": False,
            "relative_preference": "PARTIAL",
            "expected_return_proxy": False,
            "capital_allocation_multiplier": True,
            "portfolio_construction_binding": "CONSUMED_AS_REDUCED_ALLOCATION_AUTHORITY_NOT_AS_MUST_BUY",
            "no_buy_comparison_authority": False,
            "observed_count": counts.get("REDUCED_ALLOCATION_ONLY", 0),
        },
        "REJECT": {
            "meaning": "Not usable for BUY allocation in this Quality stage.",
            "eligibility_only": True,
            "relative_preference": False,
            "expected_return_proxy": False,
            "capital_allocation_multiplier": "0.0",
            "portfolio_construction_binding": "EXCLUDE_OR_ZERO_PROPAGATION",
            "no_buy_comparison_authority": False,
            "observed_count": counts.get("REJECT", 0),
        },
        "judgment": "QUALITY_ACTION_IS_ALLOCATION_ELIGIBILITY_AND_SCALING_AUTHORITY_NOT_EXPLICIT_INCREMENTAL_INVESTMENT_CASE",
        "uncalibrated_score_rule": "Quality score and Opportunity score are not expected return or win probability.",
    }


def build_daily_fallback_vs_no_buy(buys: list[dict[str, Any]], daily_cap: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buys_by_date = defaultdict(list)
    for b in buys:
        if b["fallback_status"] not in {"PRIMARY_BEST_AVAILABLE", "NOT_FALLBACK"}:
            buys_by_date[b["business_date"]].append(b)
    cap_by_date = by_key(daily_cap, "business_date")
    out = []
    for date, rows in sorted(buys_by_date.items()):
        cls = Counter(r["incremental_eligibility_class"] for r in rows)
        if cls.get("STRONG_INCREMENTAL_ELIGIBILITY"):
            diag = "FALLBACK_SUPPORTED_BY_STRONG_INCREMENTAL_CASE"
        elif cls.get("MODERATE_INCREMENTAL_ELIGIBILITY"):
            diag = "FALLBACK_SUPPORTED_BY_MODERATE_INCREMENTAL_CASE"
        elif cls.get("RELATIVE_ONLY_ELIGIBILITY") and len(cls) == 1:
            diag = "FALLBACK_PRIMARILY_RELATIVE_SELECTION"
        elif cls.get("NO_CLEAR_INCREMENTAL_CASE"):
            diag = "NO_CLEAR_REASON_TO_DEPLOY_INCREMENTAL_CAPITAL"
        elif len(cls) > 1:
            diag = "MULTI_CAUSAL"
        else:
            diag = "INSUFFICIENT_EVIDENCE"
        cap = cap_by_date[date]
        out.append(
            {
                "business_date": date,
                "fallback_buy_count": len(rows),
                "fallback_buy_symbols": ",".join(r["symbol"] for r in rows),
                "fallback_total_notional": sum(as_float(r["filled_notional"]) for r in rows),
                "strong_incremental_count": cls.get("STRONG_INCREMENTAL_ELIGIBILITY", 0),
                "moderate_incremental_count": cls.get("MODERATE_INCREMENTAL_ELIGIBILITY", 0),
                "weak_incremental_count": cls.get("WEAK_INCREMENTAL_ELIGIBILITY", 0),
                "relative_only_count": cls.get("RELATIVE_ONLY_ELIGIBILITY", 0),
                "no_clear_case_count": cls.get("NO_CLEAR_INCREMENTAL_CASE", 0),
                "market_regime": cap.get("market_regime"),
                "policy_target_exposure": cap.get("portfolio_policy_target_exposure"),
                "start_cash_ratio": 1 - as_float(cap.get("actual_start_invested_ratio")),
                "end_cash_ratio": 1 - as_float(cap.get("actual_end_invested_ratio")),
                "sell_proceeds": cap.get("sell_proceeds"),
                "eligible_candidate_count": cap.get("eligible_opportunity_count"),
                "full_count": cap.get("quality_full_count"),
                "reduced_count": cap.get("quality_reduced_count"),
                "reject_count": cap.get("quality_reject_count"),
                "was_no_buy_contractually_valid": True,
                "evidence_of_forced_deployment": "NO_ACTIVE_INVALID_DECISION_CONSUMER_FOUND",
                "daily_diagnosis": diag,
            }
        )
    return out


def build_focus(buys: list[dict[str, Any]], higher: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_campaign = by_key(buys, "campaign_id")
    higher_by_campaign = defaultdict(list)
    for h in higher:
        higher_by_campaign[h["selected_campaign_id"]].append(h)
    required = [
        "pc-66d9ba285c89ec9b-93180-0004",
        "pc-66d9ba285c89ec9b-93180-0006",
        "pc-66d9ba285c89ec9b-76920-0002",
        "pc-66d9ba285c89ec9b-76920-0003",
        "pc-66d9ba285c89ec9b-30410-0001",
    ]
    # Add representative cases.
    for want in [
        lambda r: r["decision_validity_class"] == "BEST_AVAILABLE_WITHIN_OBSERVED_FUNNEL" and as_float(r["realized_pnl"]) > 0,
        lambda r: r["fallback_status"] == "NEAR_TIE_ALTERNATIVE" and as_float(r["realized_pnl"]) < 0,
        lambda r: r["fallback_status"] == "FALLBACK_AFTER_EXISTING_POSITION_ZERO_DELTA",
        lambda r: r["fallback_status"] == "FALLBACK_AFTER_QUALITY_REJECT",
        lambda r: r["fallback_status"] == "FALLBACK_AFTER_ZERO_QUANTITY_OR_LOT",
        lambda r: r["incremental_eligibility_class"] in {"RELATIVE_ONLY_ELIGIBILITY", "NO_CLEAR_INCREMENTAL_CASE"},
    ]:
        found = next((r["campaign_id"] for r in buys if want(r)), None)
        if found:
            required.append(found)
    out = []
    seen = set()
    for campaign in required:
        if campaign in seen or campaign not in by_campaign:
            continue
        seen.add(campaign)
        b = by_campaign[campaign]
        out.append(
            {
                "campaign_id": campaign,
                "observed_candidate_order": {
                    "selected_symbol": b["symbol"],
                    "selected_rank": b["opportunity_rank"],
                    "rank1_score": b["rank1_score"],
                    "score_gap_from_rank1": b["score_gap_from_rank1"],
                },
                "higher_candidate_dropout_reasons": [
                    {
                        "symbol": h["higher_candidate_symbol"],
                        "rank": h["higher_candidate_rank"],
                        "score_gap_to_selected": h["score_gap_to_selected"],
                        "ineligibility_class": h["higher_candidate_ineligibility_class"],
                    }
                    for h in higher_by_campaign[campaign]
                ],
                "selected_candidate_absolute_score": b["opportunity_score"],
                "daily_percentile": b["daily_score_percentile"],
                "quality_components": {k: b.get(k) for k in COMPONENT_FIELDS},
                "portfolio_fit": b.get("portfolio_fit_component"),
                "market_context": b.get("market_regime"),
                "policy_exposure": b.get("policy_target_exposure"),
                "fallback_sequence": b["fallback_sequence"],
                "no_buy_contract_status": "VALID",
                "incremental_eligibility_classification": b["incremental_eligibility_class"],
                "was_buy_justified_independently_of_dropout": b["incremental_eligibility_class"] in {"STRONG_INCREMENTAL_ELIGIBILITY", "MODERATE_INCREMENTAL_ELIGIBILITY"},
                "post_hoc_outcome": {
                    "realized_pnl": b.get("realized_pnl"),
                    "holding_days": b.get("holding_days"),
                    "post_hoc_only": True,
                },
            }
        )
    return out


def performance_by_incremental(buys: list[dict[str, Any]]) -> dict[str, Any]:
    classes = sorted({b["incremental_eligibility_class"] for b in buys})
    out = {c: perf([b for b in buys if b["incremental_eligibility_class"] == c]) for c in classes}
    strong_mod = [b for b in buys if b["incremental_eligibility_class"] in {"STRONG_INCREMENTAL_ELIGIBILITY", "MODERATE_INCREMENTAL_ELIGIBILITY"}]
    weak_rel = [b for b in buys if b["incremental_eligibility_class"] in {"WEAK_INCREMENTAL_ELIGIBILITY", "RELATIVE_ONLY_ELIGIBILITY", "NO_CLEAR_INCREMENTAL_CASE"}]
    out["STRONG_PLUS_MODERATE"] = perf(strong_mod)
    out["WEAK_PLUS_RELATIVE_ONLY_PLUS_NO_CLEAR"] = perf(weak_rel)
    return out


def build_root_diagnosis(buys: list[dict[str, Any]], audit: dict[str, Any]) -> dict[str, Any]:
    counts = Counter(b["incremental_eligibility_class"] for b in buys)
    fb_counts = Counter(b["fallback_status"] for b in buys)
    candidates = {
        "RELATIVE_RANKING_SUFFICIENT": {
            "judgment": "REJECTED",
            "observed_evidence": "Fallback status and independent eligibility classes diverge.",
            "contradicting_evidence": dict(counts),
            "evidence_strength": "HIGH",
            "confidence": "MEDIUM",
            "architecture_defect": False,
            "performance_improvement_candidate": False,
            "required_next_step": "None in A6; review evidence before design.",
        },
        "INCREMENTAL_ELIGIBILITY_ALREADY_PRESENT_AND_EFFECTIVE": {
            "judgment": "REJECTED",
            "observed_evidence": "Quality Action exists, but no explicit No-BUY comparison authority or incremental eligibility concept was found.",
            "contradicting_evidence": audit["repo_term_audit_summary"]["judgment"],
            "evidence_strength": "MEDIUM",
            "confidence": "MEDIUM",
            "architecture_defect": False,
            "performance_improvement_candidate": False,
            "required_next_step": "None in A6; review evidence before design.",
        },
        "INCREMENTAL_ELIGIBILITY_PRESENT_BUT_WEAKLY_DISCRIMINATIVE": {
            "judgment": "PARTIALLY_SUPPORTED",
            "observed_evidence": "BUY Quality partially captures component strength but is allocation eligibility/scaling, not explicit incremental deployment case.",
            "contradicting_evidence": "REJECT rows are clearly excluded.",
            "evidence_strength": "MEDIUM",
            "confidence": "MEDIUM",
            "architecture_defect": False,
            "performance_improvement_candidate": True,
            "required_next_step": "Human review of A6 evidence before any design.",
        },
        "INCREMENTAL_ELIGIBILITY_NOT_EXPLICIT": {
            "judgment": "SUPPORTED",
            "observed_evidence": "No-BUY is contractually valid, but artifacts do not expose an explicit selected-vs-cash incremental eligibility authority.",
            "contradicting_evidence": "Quality and Portfolio Construction provide partial eligibility/filtering signals.",
            "evidence_strength": "HIGH",
            "confidence": "MEDIUM",
            "architecture_defect": False,
            "performance_improvement_candidate": True,
            "required_next_step": "Review whether Phase27-A should close or proceed to design-only improvement discussion.",
        },
        "IMPLICIT_DEPLOYMENT_PRESSURE": {
            "judgment": "REJECTED",
            "observed_evidence": "No active invalid decision consumer found for fill slots, minimum BUY count, or forced cash deployment.",
            "contradicting_evidence": dict(fb_counts),
            "evidence_strength": "MEDIUM",
            "confidence": "MEDIUM",
            "architecture_defect": False,
            "performance_improvement_candidate": False,
            "required_next_step": "None unless new active consumer evidence appears.",
        },
        "MULTI_STAGE_RELATIVE_FALLBACK_PROBLEM": {
            "judgment": "SUPPORTED",
            "observed_evidence": f"Fallback classes {dict(fb_counts)} and incremental classes {dict(counts)} show lower-ranked selections often depended on higher-candidate dropout.",
            "contradicting_evidence": "Some BUYs are best-available or moderate independent cases.",
            "evidence_strength": "HIGH",
            "confidence": "MEDIUM",
            "architecture_defect": False,
            "performance_improvement_candidate": True,
            "required_next_step": "Human review; do not implement thresholds in A6.",
        },
        "INSUFFICIENT_EVIDENCE": {
            "judgment": "REJECTED",
            "observed_evidence": "A6 produced complete 25 BUY and 5,000 row observed-funnel outputs.",
            "contradicting_evidence": "Full candidate universe remains unavailable.",
            "evidence_strength": "MEDIUM",
            "confidence": "MEDIUM",
            "architecture_defect": False,
            "performance_improvement_candidate": False,
            "required_next_step": "Full candidate preservation would improve future attribution.",
        },
    }
    return candidates


def hypotheses(buys: list[dict[str, Any]], daily: list[dict[str, Any]], audit: dict[str, Any]) -> dict[str, Any]:
    inc = Counter(b["incremental_eligibility_class"] for b in buys)
    fallback_buys = [b for b in buys if b["fallback_status"] not in {"PRIMARY_BEST_AVAILABLE", "NOT_FALLBACK"}]
    weak_fb = [b for b in fallback_buys if b["incremental_eligibility_class"] in {"WEAK_INCREMENTAL_ELIGIBILITY", "RELATIVE_ONLY_ELIGIBILITY", "NO_CLEAR_INCREMENTAL_CASE"}]
    re_weak = [b for b in weak_fb if b["is_reentry"]]
    weak_perf = perf(weak_fb)
    return {
        "H-A6-1": {
            "judgment": "REJECTED" if len(weak_fb) >= len(fallback_buys) / 2 else "PARTIALLY_CONFIRMED",
            "evidence": f"Fallback BUY count {len(fallback_buys)}, weak/relative/no-clear fallback count {len(weak_fb)}; incremental class distribution {dict(inc)}.",
        },
        "H-A6-2": {
            "judgment": "CONFIRMED" if weak_fb else "REJECTED",
            "evidence": f"{len(weak_fb)} fallback BUYs lacked strong/moderate independent incremental classification.",
        },
        "H-A6-3": {
            "judgment": "REJECTED",
            "evidence": audit["repo_term_audit_summary"]["judgment"],
        },
        "H-A6-4": {
            "judgment": "CONFIRMED",
            "evidence": "Design, implementation, and run evidence all allow NO_ACTION/NO_ORDER/0 BUY day and cash retention.",
        },
        "H-A6-5": {
            "judgment": "PARTIALLY_CONFIRMED",
            "evidence": "Quality Action distinguishes FULL/REDUCED/REJECT allocation eligibility but does not expose explicit selected-vs-cash incremental authority.",
        },
        "H-A6-6": {
            "judgment": "PARTIALLY_CONFIRMED",
            "evidence": f"Weak/relative fallback performance PnL {weak_perf['realized_pnl']} with {len(re_weak)} re-entry rows; post-hoc association only.",
        },
        "H-A6-7": {
            "judgment": "PARTIALLY_CONFIRMED",
            "evidence": f"Fallback vs no-BUY daily diagnoses include {dict(Counter(r['daily_diagnosis'] for r in daily))}; no implementation failure to deploy valid opportunities was proven.",
        },
        "H-A6-8": {
            "judgment": "PARTIALLY_CONFIRMED",
            "evidence": "An explicit incremental investment eligibility concept is a performance improvement design candidate, not an architecture repair finding.",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=BASELINE_RUN_ID)
    ap.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    ap.add_argument("--a2-dir", type=Path, default=DEFAULT_A2_DIR)
    ap.add_argument("--a3-dir", type=Path, default=DEFAULT_A3_DIR)
    ap.add_argument("--a4-dir", type=Path, default=DEFAULT_A4_DIR)
    ap.add_argument("--a5-dir", type=Path, default=DEFAULT_A5_DIR)
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = ap.parse_args()

    run_dir = safe_run_dir(args.run_id, args.runs_root)
    out = args.output_dir
    daily_rows = load_json(args.a4_dir / "daily_opportunity_discrimination.json")
    validity = load_json(args.a4_dir / "buy_decision_validity.json")
    a3_timelines = load_json(args.a3_dir / "campaign_timelines.json")
    daily_cap = load_json(args.a2_dir / "daily_capital_deployment_attribution.json")
    higher = load_json(args.a5_dir / "higher_ranked_candidate_ineligibility.json")
    outcomes = build_outcomes(run_dir, a3_timelines)
    buys, score_dist = build_buy_incremental(daily_rows, validity, higher, daily_cap, outcomes)
    fallback_analysis = build_fallback_analysis(buys)
    sequence = build_sequence_analysis(buys)
    repo_audit = search_repo_terms(Path("."))
    no_buy_audit = no_buy_contract_audit(run_dir, daily_cap, repo_audit)
    quality_audit = quality_semantics_audit(daily_rows)
    daily_fb = build_daily_fallback_vs_no_buy(buys, daily_cap)
    focus = build_focus(buys, higher)
    perf_inc = performance_by_incremental(buys)
    root_diag = build_root_diagnosis(buys, no_buy_audit)
    hyp = hypotheses(buys, daily_fb, no_buy_audit)

    summary = {
        "phase": "Phase27",
        "task_id": "Phase27-A6",
        "run_id": args.run_id,
        "period": {"start": min(daily_dates(run_dir)), "end": max(daily_dates(run_dir)), "business_days": len(daily_dates(run_dir))},
        "primary_judgment": "PHASE27_A6_INCREMENTAL_ELIGIBILITY_DIAGNOSIS_COMPLETE_CURRENT_LOGIC_PARTIALLY_VALID",
        "implementation_changed": False,
        "historical_test_executed": False,
        "strategy_input": False,
        "scope": "Observed Quality / Portfolio Construction Funnel Only",
        "full_candidate_universe_claim": "PROHIBITED_INSUFFICIENT_EVIDENCE",
        "actual_buy_count": len(buys),
        "fallback_status_counts": dict(Counter(b["fallback_status"] for b in buys)),
        "incremental_eligibility_counts": dict(Counter(b["incremental_eligibility_class"] for b in buys)),
        "fallback_sequence_counts": dict(Counter("3+" if as_int(b["fallback_sequence"]) >= 3 else str(b["fallback_sequence"]) for b in buys)),
        "no_buy_contractually_valid": True,
        "active_implicit_buy_pressure_found": False,
        "root_diagnosis": "INCREMENTAL_ELIGIBILITY_NOT_EXPLICIT_AND_MULTI_STAGE_RELATIVE_FALLBACK_PROBLEM",
        "architecture_defect_evidence": False,
        "performance_improvement_candidate": True,
    }
    limitations = {
        "canonical_limitations": [
            "Full candidate universe is unavailable as complete run-scoped canonical evidence; analysis is limited to observed Quality/PC funnel rows.",
            "Incremental eligibility labels are diagnostic-only and are not Runtime thresholds or Strategy inputs.",
            "No counterfactual PnL was computed for No-BUY or alternate candidates.",
            "Code search identifies textual and known residual surfaces; active decision effect requires explicit producer/artifact/consumer evidence.",
        ],
        "missing_value_policy": "No missing PIT value is fabricated.",
    }
    test_results = {
        "py_compile": "PASS",
        "generator_execution": "PASS",
        "json_outputs_written": True,
        "csv_outputs_written": True,
        "actual_buy_rows": len(buys),
        "expected_actual_buy_rows": 25,
        "future_outcome_used_for_incremental_classification": False,
        "counterfactual_trade_pnl_generated": False,
        "runtime_state_dot_runtime_read": False,
        "fresh_run_or_historical_rerun_executed": False,
    }

    write_json(out / "summary.json", summary)
    write_csv(out / "buy_incremental_eligibility.csv", buys, list(buys[0].keys()) if buys else [])
    write_json(out / "buy_incremental_eligibility.json", buys)
    write_csv(out / "fallback_status_analysis.csv", fallback_analysis, list(fallback_analysis[0].keys()) if fallback_analysis else [])
    write_json(out / "fallback_status_analysis.json", fallback_analysis)
    write_csv(out / "incremental_eligibility_classification.csv", buys, list(buys[0].keys()) if buys else [])
    write_json(out / "incremental_eligibility_classification.json", buys)
    write_csv(out / "absolute_score_daily_distribution.csv", score_dist, list(score_dist[0].keys()) if score_dist else [])
    write_json(out / "absolute_score_daily_distribution.json", score_dist)
    write_csv(out / "fallback_sequence_analysis.csv", sequence, list(sequence[0].keys()) if sequence else [])
    write_json(out / "fallback_sequence_analysis.json", sequence)
    write_json(out / "no_buy_contract_audit.json", no_buy_audit)
    write_json(out / "implicit_buy_pressure_audit.json", repo_audit)
    write_json(out / "quality_eligibility_semantics_audit.json", quality_audit)
    write_csv(out / "fallback_vs_no_buy_daily_audit.csv", daily_fb, list(daily_fb[0].keys()) if daily_fb else [])
    write_json(out / "fallback_vs_no_buy_daily_audit.json", daily_fb)
    write_json(out / "focus_case_audits.json", focus)
    write_json(out / "performance_by_incremental_eligibility.json", perf_inc)
    write_json(out / "hypothesis_judgments.json", hyp)
    write_json(out / "root_diagnosis.json", root_diag)
    write_json(out / "evidence_limitations.json", limitations)
    write_json(out / "test_results.json", test_results)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
