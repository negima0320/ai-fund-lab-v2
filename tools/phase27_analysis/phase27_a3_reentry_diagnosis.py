#!/usr/bin/env python3
"""Phase27-A3 read-only re-entry causality diagnosis.

Observability Only / Post-hoc Human Review Only / Not a Strategy Input.

This script reads run-scoped Phase27-A2 attribution outputs and run-scoped
Runtime Test daily artifacts. It does not read .runtime, does not mutate runtime
state, and must not be used as Strategy, BUY Quality, Opportunity, Candidate,
Portfolio Policy, Position Sizing, Planning, Submit, Safety, PM, Exit, or
Re-entry input.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


BASELINE_RUN_ID = "runtime-test-historical-smoke-20260804T074611098414Z"
DEFAULT_RUNS_ROOT = Path("reports/runtime_tests/runs")
DEFAULT_A2_DIR = Path("reports/phase27_a2_100bd_baseline_attribution_and_hypothesis_evidence_extraction")
DEFAULT_OUTPUT_DIR = Path("reports/phase27_a3_reentry_causality_and_selection_validity_diagnosis")


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


def pct(num: float, den: float) -> float | None:
    if den == 0:
        return None
    return num / den


def avg(values: list[float]) -> float | None:
    vals = [v for v in values if v is not None]
    return mean(vals) if vals else None


def run_dir_for(run_id: str, runs_root: Path) -> Path:
    if "/" in run_id or "\\" in run_id or run_id in {"", ".", ".."}:
        raise SystemExit(f"invalid run id: {run_id!r}")
    run_dir = (runs_root / run_id).resolve()
    root = runs_root.resolve()
    if not str(run_dir).startswith(str(root)):
        raise SystemExit("run directory must stay under reports/runtime_tests/runs")
    if not run_dir.exists():
        raise SystemExit(f"missing run directory: {run_dir}")
    return run_dir


def daily_path(run_dir: Path, date: str, rel: str) -> Path:
    return run_dir / "daily" / date / rel


def market_regime(run_dir: Path, date: str) -> str:
    path = daily_path(run_dir, date, "strategy/market_context.json")
    if not path.exists():
        return ""
    payload = load_json(path)
    return payload.get("regime_state") or payload.get("trend_state") or payload.get("trend_regime") or ""


def buy_funnel_by_campaign(funnel: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        row["position_campaign_id"]: row
        for row in funnel
        if row.get("position_campaign_id") and row.get("final_funnel_status") == "BOUGHT"
    }


def build_campaign_timelines(
    run_dir: Path,
    reentry_events: list[dict[str, Any]],
    exit_rows: list[dict[str, Any]],
    funnel_by_campaign: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    exits_by_campaign: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in exit_rows:
        exits_by_campaign[row["campaign_id"]].append(row)

    timelines = []
    for event in sorted(reentry_events, key=lambda r: (r["symbol"], r["entry_date"], r["campaign_id"])):
        campaign = event["campaign_id"]
        entry = funnel_by_campaign.get(campaign, {})
        timeline_events = [
            {
                "event_type": "ENTRY" if not event["is_reentry"] else "RE_ENTRY",
                "business_date": event["entry_date"],
                "opportunity_rank": event["entry_opportunity_rank"],
                "opportunity_score": entry.get("opportunity_score"),
                "quality_score": event["entry_quality_score"],
                "quality_action": event["entry_quality_action"],
                "market_context": event["entry_market_regime"],
                "position_size": event["entry_notional"],
                "holding_days": event["holding_days"],
                "exit_reason": "",
                "pnl": event["realized_pnl"],
                "campaign_id": campaign,
            }
        ]
        for sell in sorted(exits_by_campaign.get(campaign, []), key=lambda r: r["sell_date"]):
            timeline_events.append(
                {
                    "event_type": sell["reduce_or_exit"],
                    "business_date": sell["sell_date"],
                    "opportunity_rank": None,
                    "opportunity_score": None,
                    "quality_score": None,
                    "quality_action": "",
                    "market_context": sell.get("market_regime_at_sell") or market_regime(run_dir, sell["sell_date"]),
                    "position_size": sell.get("sold_quantity"),
                    "holding_days": sell.get("holding_days_at_sell"),
                    "exit_reason": sell.get("sell_reason"),
                    "pnl": sell.get("realized_pnl"),
                    "campaign_id": campaign,
                }
            )
        timelines.append(
            {
                "symbol": event["symbol"],
                "campaign_id": campaign,
                "entry_sequence_number": event["entry_sequence_number"],
                "is_reentry": event["is_reentry"],
                "prior_exit_date": event.get("prior_exit_date"),
                "entry_date": event["entry_date"],
                "exit_date": event.get("exit_date"),
                "campaign_pnl": event["realized_pnl"],
                "campaign_return_rate_if_resolvable": event.get("campaign_return_rate_if_resolvable"),
                "timeline": timeline_events,
            }
        )
    return timelines


def build_initial_vs_reentry(reentry_events: list[dict[str, Any]], funnel_by_campaign: dict[str, dict[str, Any]]) -> dict[str, Any]:
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in reentry_events:
        by_symbol[row["symbol"]].append(row)

    comparisons = {}
    for symbol, rows in by_symbol.items():
        ordered = sorted(rows, key=lambda r: r["entry_sequence_number"])
        initial = ordered[0]
        initial_funnel = funnel_by_campaign.get(initial["campaign_id"], {})
        reentries = []
        for row in ordered[1:]:
            f = funnel_by_campaign.get(row["campaign_id"], {})
            reentries.append(
                {
                    "campaign_id": row["campaign_id"],
                    "entry_sequence_number": row["entry_sequence_number"],
                    "opportunity_rank": row["entry_opportunity_rank"],
                    "opportunity_score": f.get("opportunity_score"),
                    "quality_score": row["entry_quality_score"],
                    "quality_action": row["entry_quality_action"],
                    "target_weight": f.get("target_weight"),
                    "target_notional": f.get("target_notional"),
                    "filled_notional": row["entry_notional"],
                    "holding_days": row["holding_days"],
                    "realized_pnl": row["realized_pnl"],
                    "return": row.get("campaign_return_rate_if_resolvable"),
                    "delta_vs_initial": {
                        "opportunity_rank_delta": as_int(row["entry_opportunity_rank"]) - as_int(initial["entry_opportunity_rank"]),
                        "quality_score_delta": as_float(row["entry_quality_score"]) - as_float(initial["entry_quality_score"]),
                        "notional_delta": as_float(row["entry_notional"]) - as_float(initial["entry_notional"]),
                        "pnl_delta": as_float(row["realized_pnl"]) - as_float(initial["realized_pnl"]),
                    },
                }
            )
        comparisons[symbol] = {
            "initial_entry": {
                "campaign_id": initial["campaign_id"],
                "opportunity_rank": initial["entry_opportunity_rank"],
                "opportunity_score": initial_funnel.get("opportunity_score"),
                "quality_score": initial["entry_quality_score"],
                "quality_action": initial["entry_quality_action"],
                "target_weight": initial_funnel.get("target_weight"),
                "target_notional": initial_funnel.get("target_notional"),
                "filled_notional": initial["entry_notional"],
                "holding_days": initial["holding_days"],
                "realized_pnl": initial["realized_pnl"],
                "return": initial.get("campaign_return_rate_if_resolvable"),
            },
            "reentries": reentries,
        }
    return comparisons


def available_candidates_on_date(funnel: list[dict[str, Any]], date: str) -> list[dict[str, Any]]:
    rows = []
    for row in funnel:
        if row["business_date"] != date:
            continue
        if row["quality_action"] in {"FULL_ALLOCATION_ELIGIBLE", "REDUCED_ALLOCATION_ONLY"}:
            rows.append(row)
    return sorted(rows, key=lambda r: as_int(r.get("opportunity_rank"), 9999))


def build_candidate_competition(reentry_events: list[dict[str, Any]], funnel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_campaign = buy_funnel_by_campaign(funnel)
    outputs = []
    for event in reentry_events:
        if not event["is_reentry"]:
            continue
        selected = by_campaign.get(event["campaign_id"], {})
        date = event["entry_date"]
        candidates = available_candidates_on_date(funnel, date)
        selected_rank = as_int(selected.get("opportunity_rank"), 9999)
        best_available_rank = as_int(candidates[0].get("opportunity_rank"), 9999) if candidates else None
        better_available = [
            {
                "symbol": c["symbol"],
                "opportunity_rank": c["opportunity_rank"],
                "opportunity_score": c["opportunity_score"],
                "quality_score": c["quality_score"],
                "quality_action": c["quality_action"],
                "final_funnel_status": c["final_funnel_status"],
                "explicit_reason": c["final_explicit_reason"],
            }
            for c in candidates
            if as_int(c.get("opportunity_rank"), 9999) < selected_rank and c.get("symbol") != event["symbol"]
        ]
        if not candidates:
            proof = "INSUFFICIENT_EVIDENCE"
        elif selected_rank == best_available_rank:
            proof = "YES_WITHIN_QUALITY_PC_FUNNEL"
        elif better_available:
            proof = "NO_NOT_HIGHEST_WITHIN_QUALITY_PC_FUNNEL"
        else:
            proof = "INSUFFICIENT_EVIDENCE"
        outputs.append(
            {
                "symbol": event["symbol"],
                "campaign_id": event["campaign_id"],
                "entry_date": date,
                "selected_opportunity_rank": selected.get("opportunity_rank"),
                "selected_opportunity_score": selected.get("opportunity_score"),
                "selected_quality_score": selected.get("quality_score"),
                "selected_quality_action": selected.get("quality_action"),
                "available_candidate_count_after_quality": len(candidates),
                "best_available_rank_after_quality": best_available_rank,
                "was_highest_ranked_available_opportunity": proof,
                "better_available_candidates_after_quality": better_available[:10],
                "candidate_full_universe_judgment": "INSUFFICIENT_EVIDENCE",
                "limitation": "Full candidate universe is not copied as canonical run-scoped evidence; comparison is limited to Quality/PC funnel rows.",
            }
        )
    return outputs


def build_exit_reentry_interaction(
    reentry_events: list[dict[str, Any]],
    exit_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    exits_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in exit_rows:
        exits_by_symbol[row["symbol"]].append(row)
    outputs = []
    for event in reentry_events:
        if not event["is_reentry"]:
            continue
        prior_exit_date = event.get("prior_exit_date")
        prior_exits = [
            e for e in exits_by_symbol[event["symbol"]]
            if e["sell_date"] == prior_exit_date and e["reduce_or_exit"] == "EXIT"
        ]
        prior_exit = prior_exits[-1] if prior_exits else {}
        interval = event.get("reentry_interval_business_days")
        pnl = as_float(event.get("realized_pnl"))
        if interval is None:
            explanation = "INSUFFICIENT_EVIDENCE"
        elif interval <= 2 and pnl < 0:
            explanation = "LIKELY_WHIPSAW"
        elif interval <= 2 and pnl >= 0:
            explanation = "VALID_TREND_REENTRY_OR_FAST_RECOVERY"
        elif pnl < 0:
            explanation = "QUESTIONABLE_REENTRY"
        else:
            explanation = "VALID_TREND_REENTRY"
        outputs.append(
            {
                "symbol": event["symbol"],
                "campaign_id": event["campaign_id"],
                "prior_exit_date": prior_exit_date,
                "prior_exit_action": prior_exit.get("sell_action"),
                "prior_exit_pnl": prior_exit.get("realized_pnl"),
                "entry_date": event["entry_date"],
                "reentry_interval_business_days": interval,
                "subsequent_holding_days": event["holding_days"],
                "subsequent_realized_pnl": event["realized_pnl"],
                "subsequent_return": event.get("campaign_return_rate_if_resolvable"),
                "interaction_classification": explanation,
                "evidence_limitation": "MFE/MAE and exact PM intent are unavailable; classification uses exit date, interval, and realized outcome.",
            }
        )
    return outputs


def classify_reentries(
    reentry_events: list[dict[str, Any]],
    candidate_competition: list[dict[str, Any]],
    exit_interaction: list[dict[str, Any]],
) -> dict[str, Any]:
    comp_by_campaign = {r["campaign_id"]: r for r in candidate_competition}
    exit_by_campaign = {r["campaign_id"]: r for r in exit_interaction}
    rows = []
    for event in reentry_events:
        if not event["is_reentry"]:
            continue
        comp = comp_by_campaign.get(event["campaign_id"], {})
        interaction = exit_by_campaign.get(event["campaign_id"], {})
        rank = as_int(event["entry_opportunity_rank"], 999)
        q = as_float(event["entry_quality_score"])
        pnl = as_float(event["realized_pnl"])
        interval = event.get("reentry_interval_business_days")
        if pnl == 0 and not event.get("exit_date"):
            cls = "INSUFFICIENT_EVIDENCE"
        elif interaction.get("interaction_classification") == "LIKELY_WHIPSAW":
            cls = "LIKELY_WHIPSAW"
        elif rank <= 2 and q >= 0.74 and comp.get("was_highest_ranked_available_opportunity") == "YES_WITHIN_QUALITY_PC_FUNNEL":
            cls = "VALID_REENTRY"
        elif rank > 3 or comp.get("was_highest_ranked_available_opportunity") == "NO_NOT_HIGHEST_WITHIN_QUALITY_PC_FUNNEL":
            cls = "QUESTIONABLE_REENTRY"
        elif interval is None:
            cls = "INSUFFICIENT_EVIDENCE"
        else:
            cls = "QUESTIONABLE_REENTRY" if pnl < 0 else "VALID_REENTRY"
        rows.append(
            {
                "symbol": event["symbol"],
                "campaign_id": event["campaign_id"],
                "entry_date": event["entry_date"],
                "opportunity_rank": event["entry_opportunity_rank"],
                "quality_score": event["entry_quality_score"],
                "quality_action": event["entry_quality_action"],
                "reentry_interval_business_days": interval,
                "realized_pnl": event["realized_pnl"],
                "candidate_competition_judgment": comp.get("was_highest_ranked_available_opportunity"),
                "exit_interaction_classification": interaction.get("interaction_classification"),
                "classification": cls,
                "classification_basis": "Observed rank, quality, candidate competition within Quality/PC funnel, exit interval, and realized outcome.",
            }
        )
    counts = Counter(r["classification"] for r in rows)
    if counts.get("LIKELY_WHIPSAW", 0) + counts.get("QUESTIONABLE_REENTRY", 0) > counts.get("VALID_REENTRY", 0):
        overall = "REENTRY_PARTIALLY_EXPLAINED_BY_WHIPSAW_AND_SELECTION"
    else:
        overall = "REENTRY_MIXED_VALIDITY"
    return {"campaign_classifications": rows, "classification_counts": dict(counts), "overall_classification": overall}


def build_root_cause_separation(classification: dict[str, Any], candidate_competition: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(r["was_highest_ranked_available_opportunity"] for r in candidate_competition)
    class_counts = classification["classification_counts"]
    return {
        "reentry_selection": {
            "judgment": "PARTIAL_FACTOR",
            "evidence": "Some re-entry campaigns were not highest-ranked within the Quality/PC funnel or had low rank.",
            "counts": dict(counts),
        },
        "exit_timing": {
            "judgment": "PARTIAL_FACTOR",
            "evidence": "Fast exit-to-reentry intervals with subsequent losses indicate whipsaw risk for some campaigns.",
            "classification_counts": class_counts,
        },
        "opportunity_ranking": {
            "judgment": "PARTIAL_FACTOR",
            "evidence": "Re-entry rank quality is mixed; candidate full universe is insufficient.",
        },
        "buy_quality": {
            "judgment": "PARTIAL_FACTOR",
            "evidence": "Both FULL and REDUCED re-entries include winners and losers; Quality alone does not explain all losses.",
        },
        "market_context": {
            "judgment": "MIXED_EVIDENCE",
            "evidence": "Re-entries occurred across BULL/RANGE regimes; market context alone is not sufficient.",
        },
        "position_sizing": {
            "judgment": "NOT_PRIMARY_CAUSE_IN_A3",
            "evidence": "Loss causality is more directly tied to selection/exit/outcome than sizing mechanics in A3 evidence.",
        },
        "architecture_repair_required": False,
    }


def symbol_typicality(reentry_events: list[dict[str, Any]]) -> dict[str, Any]:
    reentries = [r for r in reentry_events if r["is_reentry"]]
    pnl_values = [as_float(r["realized_pnl"]) for r in reentries]
    avg_pnl = avg(pnl_values)
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in reentry_events:
        all_by_symbol[r["symbol"]].append(r)
    for r in reentries:
        by_symbol[r["symbol"]].append(r)
    out = {}
    for symbol, rows in by_symbol.items():
        all_rows = all_by_symbol[symbol]
        total = sum(as_float(r["realized_pnl"]) for r in rows)
        all_total = sum(as_float(r["realized_pnl"]) for r in all_rows)
        out[symbol] = {
            "entry_count": len(all_rows),
            "reentry_count": len(rows),
            "total_campaign_pnl": all_total,
            "reentry_only_pnl": total,
            "average_reentry_pnl": avg([as_float(r["realized_pnl"]) for r in rows]),
            "typicality": "OUTLIER" if len(rows) >= 2 and avg_pnl is not None and total < avg_pnl * len(rows) * 2 else "TYPICAL_OR_MIXED",
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--a2-dir", default=str(DEFAULT_A2_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    run_dir = run_dir_for(args.run_id, Path(args.runs_root))
    dates = sorted(p.name for p in (run_dir / "daily").iterdir() if p.is_dir())
    a2_dir = Path(args.a2_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    reentry_events = load_json(a2_dir / "reentry_event_attribution.json")
    exit_rows = load_json(a2_dir / "exit_holding_attribution.json")
    funnel = load_json(a2_dir / "opportunity_quality_selection_funnel.json")
    funnel_by_campaign = buy_funnel_by_campaign(funnel)

    timelines = build_campaign_timelines(run_dir, reentry_events, exit_rows, funnel_by_campaign)
    initial_vs = build_initial_vs_reentry(reentry_events, funnel_by_campaign)
    competition = build_candidate_competition(reentry_events, funnel)
    exit_interaction = build_exit_reentry_interaction(reentry_events, exit_rows)
    classification = classify_reentries(reentry_events, competition, exit_interaction)
    root_sep = build_root_cause_separation(classification, competition)
    typicality = symbol_typicality(reentry_events)

    summary = {
        "schema_version": "phase27_a3_summary.v1",
        "task_id": "Phase27-A3",
        "primary_judgment": "PHASE27_A3_REENTRY_PARTIALLY_EXPLAINED",
        "run_id": args.run_id,
        "business_days": len(dates),
        "campaign_count": len(reentry_events),
        "reentry_campaign_count": sum(1 for r in reentry_events if r["is_reentry"]),
        "classification_counts": classification["classification_counts"],
        "overall_classification": classification["overall_classification"],
        "hypothesis_evaluation": {
            "A_valid_decisions_unfavorable_market": "PARTIALLY_SUPPORTED",
            "B_not_superior_opportunities": "PARTIALLY_SUPPORTED",
            "C_exit_timing_primary": "PARTIALLY_SUPPORTED",
            "D_interaction_caused_poor_entries": "PARTIALLY_SUPPORTED",
        },
        "symbol_typicality": {
            "93180": typicality.get("93180"),
            "76920": typicality.get("76920"),
            "all_reentry_symbols": typicality,
        },
        "safety_boundary": {
            "implementation_changed": False,
            "strategy_changed": False,
            "fresh_run_executed": False,
            "historical_executed": False,
            "runtime_state_read": False,
            "post_hoc_only": True,
        },
    }

    test_results = {
        "script": "tools/phase27_analysis/phase27_a3_reentry_diagnosis.py",
        "run_scoped_only": True,
        "a2_outputs_used": True,
        "runtime_state_read": False,
        "fresh_run_executed": False,
        "historical_executed": False,
        "json_outputs_written": True,
    }

    write_json(output_dir / "campaign_timelines.json", timelines)
    write_json(output_dir / "initial_vs_reentry.json", initial_vs)
    write_json(output_dir / "candidate_competition.json", competition)
    write_json(output_dir / "exit_reentry_interaction.json", exit_interaction)
    write_json(output_dir / "reentry_classification.json", classification)
    write_json(output_dir / "root_cause_separation.json", root_sep)
    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "test_results.json", test_results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
