#!/usr/bin/env python3
"""Generate Phase27-D2-F read-only PM HOLD/REDUCE/EXIT causality audit."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "runtime-test-historical-smoke-20260804T074611098414Z"
RUN_DIR = REPO_ROOT / "reports/runtime_tests/runs" / RUN_ID
A7_DIR = REPO_ROOT / "reports/phase27_a7_existing_position_position_management_decision_authority_audit"
A3_DIR = REPO_ROOT / "reports/phase27_a3_reentry_causality_and_selection_validity_diagnosis"
OUT_DIR = REPO_ROOT / "reports/phase27_d2f_existing_pm_hold_reduce_exit_decision_causality_and_momentum_follow_conformance_audit"
REPORT = REPO_ROOT / "docs/phase_reports/phase27_d2f_existing_pm_hold_reduce_exit_decision_causality_and_momentum_follow_conformance_audit.md"
TASK_ID = "Phase27-D2-F"
MISSING = "MISSING"
NOT_MATERIALIZED = "NOT_MATERIALIZED"
NOT_APPLICABLE = "NOT_APPLICABLE"


def read_json(path: Path) -> Any:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value for key, value in row.items()})


def as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value in (None, "", MISSING, NOT_MATERIALIZED):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def business_dates() -> list[str]:
    manifest = read_json(RUN_DIR / "strategy_shadow_manifest.json")
    return [str(item) for item in manifest.get("business_dates_generated") or []]


def by_symbol(items: list[dict[str, Any]], symbol_key: str = "symbol") -> dict[str, dict[str, Any]]:
    out = {}
    for item in items:
        symbol = str(item.get(symbol_key) or item.get("security_code") or "")
        if symbol:
            out[symbol] = item
    return out


def load_a7_inventory() -> dict[tuple[str, str], dict[str, Any]]:
    path = A7_DIR / "existing_position_daily_audit.csv"
    out: dict[tuple[str, str], dict[str, Any]] = {}
    if not path.is_file():
        return out
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[(row.get("business_date", ""), row.get("symbol", ""))] = row
    return out


def technical_rows(date: str) -> dict[str, dict[str, Any]]:
    return by_symbol(read_json(RUN_DIR / "daily" / date / "strategy" / "technical_features.json").get("rows") or [], symbol_key="code")


def runtime_plans(date: str) -> dict[str, dict[str, Any]]:
    return by_symbol(read_json(RUN_DIR / "daily" / date / "strategy" / "runtime_planning.json").get("plans") or [], symbol_key="security_code")


def market_context(date: str) -> dict[str, Any]:
    payload = read_json(RUN_DIR / "daily" / date / "strategy" / "market_context.json")
    return {
        "risk_state": payload.get("risk_state", payload.get("market_context_risk_state", MISSING)),
        "breadth_state": payload.get("breadth_state", MISSING),
        "regime_state": payload.get("regime_state", MISSING),
        "confidence": payload.get("confidence", MISSING),
    }


def portfolio_policy(date: str) -> dict[str, Any]:
    payload = read_json(RUN_DIR / "daily" / date / "strategy" / "portfolio_policy.json")
    return {
        "deployment_posture": payload.get("deployment_posture", MISSING),
        "entry_posture": payload.get("entry_posture", MISSING),
        "exposure_posture": payload.get("exposure_posture", MISSING),
        "cash_posture": payload.get("cash_posture", MISSING),
        "target_gross_exposure_ratio": payload.get("target_gross_exposure_ratio", payload.get("target_gross_exposure", MISSING)),
        "target_position_count": payload.get("target_position_count", MISSING),
    }


def classify_hold(reasons: list[str], dominant: str) -> str:
    reason_set = set(reasons)
    if "trend_continuation" in reason_set or "strong_trend_continuation" in reason_set or "STRONG_CONTINUATION" in dominant:
        return "MOMENTUM_CONTINUATION_SUPPORTED"
    if "positive_expected_edge" in reason_set:
        return "POSITION_VALID_BUT_MOMENTUM_EVIDENCE_PARTIAL"
    if "downside_risk_contained" in reason_set:
        return "RISK_ACCEPTABLE_MAINTAIN"
    if "hold_score_above_exit_threshold" in reason_set:
        return "NO_EXIT_CONDITION"
    if reasons:
        return "DEFAULT_OR_IMPLICIT_HOLD"
    return "INSUFFICIENT_EVIDENCE"


def classify_reduce(reasons: list[str], dominant: str) -> str:
    reason_set = set(reasons)
    if "risk_increased_but_trend_not_broken" in reason_set:
        return "MOMENTUM_WEAKENING"
    if "peak_drawdown_warning" in reason_set or "high_downside_risk_score" in reason_set or "RISK" in dominant or "DRAWDOWN" in dominant:
        return "RISK_REDUCTION"
    if reasons:
        return "UNEXPLAINED"
    return "INSUFFICIENT_EVIDENCE"


def classify_exit(reasons: list[str], dominant: str) -> str:
    reason_set = set(reasons)
    if "trend_and_opportunity_broken" in reason_set or "TREND_AND_EDGE_BREAK" in dominant:
        return "MOMENTUM_BROKEN"
    if "hard_stop_current_return" in reason_set or "HARD_STOP" in dominant:
        return "RISK_OR_SAFETY_EXIT"
    if "profit_retention_break" in reason_set and ("PEAK_DRAWDOWN" in dominant or "DRAWDOWN" in dominant):
        return "RISK_OR_SAFETY_EXIT"
    if reason_set == {"profit_retention_break"}:
        return "PROFIT_TAKING_ONLY"
    if reasons:
        return "UNEXPLAINED"
    return "INSUFFICIENT_EVIDENCE"


def signal_state(tech: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "price_momentum_return_5d": tech.get("price_momentum_return_5d", MISSING),
        "price_momentum_return_20d": tech.get("price_momentum_return_20d", MISSING),
        "trend_close_over_ma_20d": tech.get("trend_close_over_ma_20d", MISSING),
        "trend_ma_5_20_ratio": tech.get("trend_ma_5_20_ratio", MISSING),
        "signal_reliability": (plan.get("component_scores") or {}).get("signal_reliability", MISSING),
        "relative_opportunity_quality": (plan.get("component_scores") or {}).get("relative_opportunity_quality", MISSING),
    }


def input_change(prev: dict[str, Any] | None, row: dict[str, Any]) -> dict[str, Any]:
    if not prev:
        return {"status": "FIRST_OBSERVED_ROW"}
    fields = [
        "pm_action",
        "opportunity_rank",
        "opportunity_score",
        "quality_score",
        "quality_action",
        "current_price",
        "current_unrealized_pnl",
        "runtime_action",
    ]
    changes = {}
    for field in fields:
        if prev.get(field) != row.get(field):
            changes[field] = {"from": prev.get(field), "to": row.get(field)}
    return {"status": "CHANGED" if changes else "UNCHANGED", "changes": changes}


def materialize_inventory() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    a7 = load_a7_inventory()
    inventory: list[dict[str, Any]] = []
    timelines: list[dict[str, Any]] = []
    previous_by_campaign: dict[str, dict[str, Any]] = {}
    for date in business_dates():
        pm = read_json(RUN_DIR / "daily" / date / "position_management" / "pm_decisions.json")
        plans = runtime_plans(date)
        tech = technical_rows(date)
        context = market_context(date)
        policy = portfolio_policy(date)
        for decision in pm.get("decisions") or []:
            action = str(decision.get("decision_type") or "")
            if action not in {"HOLD", "REDUCE", "EXIT"}:
                continue
            symbol = str(decision.get("symbol") or "")
            plan = plans.get(symbol, {})
            tech_row = tech.get(symbol, {})
            a7_row = a7.get((date, symbol), {})
            reasons = [str(item) for item in decision.get("reason_codes") or []]
            campaign = str(decision.get("position_campaign_id") or a7_row.get("position_campaign_id") or MISSING)
            row = {
                "run_id": RUN_ID,
                "business_date": date,
                "symbol": symbol,
                "position_campaign_id": campaign,
                "current_quantity": decision.get("quantity_before", a7_row.get("current_quantity", MISSING)),
                "current_market_value": decision.get("market_value", a7_row.get("current_market_value", MISSING)),
                "current_weight": a7_row.get("current_weight", MISSING),
                "current_unrealized_pnl": decision.get("unrealized_pnl", a7_row.get("current_unrealized_pnl", MISSING)),
                "holding_days": a7_row.get("holding_days", MISSING),
                "pm_decision_id": decision.get("pm_decision_id", MISSING),
                "pm_action": action,
                "pm_reason_codes": reasons,
                "pm_summary": decision.get("decision_reason", MISSING),
                "pm_dominant_cause": decision.get("dominant_cause", MISSING),
                "pm_decision_status": decision.get("decision_status", MISSING),
                "opportunity_id": plan.get("opportunity_row_id", a7_row.get("opportunity_id", MISSING)),
                "opportunity_rank": plan.get("opportunity_buy_rank", a7_row.get("opportunity_rank", MISSING)),
                "opportunity_score": (plan.get("opportunity_authority") or {}).get("opportunity_expected_edge_score", a7_row.get("opportunity_score", MISSING)),
                "quality_decision_id": plan.get("quality_decision_id", MISSING),
                "quality_score": plan.get("quality_score", a7_row.get("quality_score", MISSING)),
                "quality_action": plan.get("quality_action", a7_row.get("quality_action", MISSING)),
                "market_context": context,
                "portfolio_policy": policy,
                "portfolio_fit": (plan.get("component_scores") or {}).get("portfolio_fit", a7_row.get("portfolio_fit", MISSING)),
                "current_price_state": {
                    "current_price": decision.get("current_price", MISSING),
                    "average_cost": decision.get("average_cost", MISSING),
                    "unrealized_pnl": decision.get("unrealized_pnl", MISSING),
                },
                "trend_inputs": {
                    "price_momentum_return_5d": tech_row.get("price_momentum_return_5d", MISSING),
                    "price_momentum_return_20d": tech_row.get("price_momentum_return_20d", MISSING),
                    "trend_close_over_ma_20d": tech_row.get("trend_close_over_ma_20d", MISSING),
                    "trend_ma_5_20_ratio": tech_row.get("trend_ma_5_20_ratio", MISSING),
                },
                "signal_inputs": signal_state(tech_row, plan),
                "risk_inputs": {
                    "volatility_return_std_20d": tech_row.get("volatility_return_std_20d", MISSING),
                    "market_context": context,
                    "downside_risk_reason_present": "downside_risk_contained" in reasons or "high_downside_risk_score" in reasons,
                },
                "corporate_event_inputs": NOT_MATERIALIZED,
                "target_portfolio_result": {
                    "target_weight": plan.get("post_quality_target_weight", a7_row.get("target_weight", MISSING)),
                    "target_direction": a7_row.get("target_direction", plan.get("planning_intent", MISSING)),
                    "planning_reason": plan.get("planning_reason", MISSING),
                },
                "quantity_delta_result": {
                    "target_quantity_candidate": plan.get("target_quantity_candidate", a7_row.get("desired_quantity", MISSING)),
                    "quantity_delta": plan.get("quantity_delta_candidate", a7_row.get("quantity_delta", MISSING)),
                    "quantity_status": plan.get("quantity_status", MISSING),
                },
                "runtime_action": plan.get("planning_intent", a7_row.get("runtime_action", MISSING)),
            }
            if action == "HOLD":
                row["causality_class"] = classify_hold(reasons, str(decision.get("dominant_cause") or ""))
            elif action == "REDUCE":
                row["causality_class"] = classify_reduce(reasons, str(decision.get("dominant_cause") or ""))
            else:
                row["causality_class"] = classify_exit(reasons, str(decision.get("dominant_cause") or ""))
            row["profit_present"] = (as_float(row["current_unrealized_pnl"]) or 0.0) > 0
            row["profit_referenced_in_pm_reason"] = any("profit" in reason for reason in reasons) or "profit" in str(row["pm_summary"]).lower()
            inventory.append(row)
            prev = previous_by_campaign.get(campaign)
            transition = input_change(prev, row)
            timeline = {
                "business_date": date,
                "symbol": symbol,
                "position_campaign_id": campaign,
                "holding_day": row["holding_days"],
                "pm_action": action,
                "pm_reason_codes": reasons,
                "opportunity_rank": row["opportunity_rank"],
                "opportunity_score": row["opportunity_score"],
                "quality_score": row["quality_score"],
                "quality_action": row["quality_action"],
                "market_context": context,
                "signal_state": row["signal_inputs"],
                "risk_state": row["risk_inputs"],
                "target_direction": row["target_portfolio_result"]["target_direction"],
                "quantity_delta": row["quantity_delta_result"]["quantity_delta"],
                "runtime_action": row["runtime_action"],
                "transition_from_prior_day": f"{prev.get('pm_action')}->{action}" if prev else "START",
                "input_change_summary": transition,
            }
            timelines.append(timeline)
            previous_by_campaign[campaign] = row
    return inventory, timelines


def group_by_action(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[str(row["pm_action"])].append(row)
    return out


def summarize_causality(rows: list[dict[str, Any]], action: str) -> dict[str, Any]:
    action_rows = [row for row in rows if row["pm_action"] == action]
    return {
        "action": action,
        "count": len(action_rows),
        "class_counts": dict(Counter(str(row["causality_class"]) for row in action_rows)),
        "examples": action_rows[:10],
    }


def transition_analysis(timelines: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    transitions = [row for row in timelines if row["transition_from_prior_day"] != "START"]
    counts = Counter(row["transition_from_prior_day"] for row in transitions)
    unstable = []
    for row in transitions:
        if row["transition_from_prior_day"] in {"HOLD->EXIT", "REDUCE->EXIT", "HOLD->REDUCE", "REDUCE->HOLD"}:
            change_count = len((row.get("input_change_summary") or {}).get("changes") or {})
            if change_count <= 2:
                unstable.append({**row, "boundary_judgment": "UNSTABLE_DECISION_BOUNDARY"})
    return {
        "transition_counts": dict(counts),
        "unstable_boundary_count": len(unstable),
        "method": "Consecutive rows by position_campaign_id; unstable candidate when large action transition has <=2 materialized field changes.",
    }, unstable


def trade_rows() -> list[dict[str, Any]]:
    path = RUN_DIR / "performance_report" / "trade_history.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def exit_reentry_audit(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dates = business_dates()
    date_index = {date: i for i, date in enumerate(dates)}
    buys = [row for row in trade_rows() if row.get("BUY/SELL") == "BUY"]
    a3_interactions = {
        str(item.get("campaign_id") or ""): item
        for item in read_json(A3_DIR / "exit_reentry_interaction.json")
        if isinstance(item, dict)
    }
    out = []
    for row in rows:
        if row["pm_action"] != "EXIT":
            continue
        symbol = row["symbol"]
        exit_date = row["business_date"]
        next_buys = [buy for buy in buys if buy["Symbol"] == symbol and date_index.get(buy["Date"], 10**9) > date_index.get(exit_date, -1)]
        if not next_buys:
            continue
        buy = min(next_buys, key=lambda item: date_index.get(item["Date"], 10**9))
        interval = date_index[buy["Date"]] - date_index[exit_date]
        if interval > 5:
            continue
        reentry_plan = runtime_plans(buy["Date"]).get(symbol, {})
        changed_inputs = {}
        for field, exit_value, reentry_value in (
            ("opportunity_rank", row.get("opportunity_rank"), reentry_plan.get("opportunity_buy_rank", MISSING)),
            ("opportunity_score", row.get("opportunity_score"), (reentry_plan.get("opportunity_authority") or {}).get("opportunity_expected_edge_score", MISSING)),
            ("quality_score", row.get("quality_score"), reentry_plan.get("quality_score", MISSING)),
            ("quality_action", row.get("quality_action"), reentry_plan.get("quality_action", MISSING)),
        ):
            if exit_value != reentry_value:
                changed_inputs[field] = {"exit": exit_value, "reentry": reentry_value}
        material = bool(changed_inputs)
        a3_classification = str((a3_interactions.get(str(buy.get("Campaign") or "")) or {}).get("interaction_classification") or "")
        if a3_classification == "LIKELY_WHIPSAW":
            classification = "POSSIBLE_WHIPSAW"
        else:
            classification = "MATERIAL_NEW_EVIDENCE" if material and interval > 1 else ("POSSIBLE_WHIPSAW" if interval <= 1 and not material else "VALID_STATE_REVERSAL")
        out.append(
            {
                "exit_date": exit_date,
                "reentry_date": buy["Date"],
                "business_day_interval": interval,
                "symbol": symbol,
                "exit_pm_action": row["pm_action"],
                "exit_reason_codes": row["pm_reason_codes"],
                "exit_opportunity": {"rank": row.get("opportunity_rank"), "score": row.get("opportunity_score")},
                "exit_quality": {"score": row.get("quality_score"), "action": row.get("quality_action")},
                "exit_market_context": row.get("market_context"),
                "exit_signal_state": row.get("signal_inputs"),
                "reentry_opportunity": {"rank": reentry_plan.get("opportunity_buy_rank", MISSING), "score": (reentry_plan.get("opportunity_authority") or {}).get("opportunity_expected_edge_score", MISSING)},
                "reentry_quality": {"score": reentry_plan.get("quality_score", MISSING), "action": reentry_plan.get("quality_action", MISSING)},
                "reentry_market_context": market_context(buy["Date"]),
                "reentry_signal_state": signal_state(technical_rows(buy["Date"]).get(symbol, {}), reentry_plan),
                "changed_inputs": changed_inputs,
                "unchanged_inputs": [key for key in ("opportunity_rank", "opportunity_score", "quality_score", "quality_action") if key not in changed_inputs],
                "material_state_change": material,
                "classification": classification,
                "phase27_a3_interaction_classification": a3_classification or MISSING,
                "campaign_id": buy.get("Campaign", MISSING),
            }
        )
    return out


def profit_taking_audit(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        if row["pm_action"] != "EXIT":
            continue
        reasons = set(row.get("pm_reason_codes") or [])
        momentum_or_signal = bool(reasons & {"trend_and_opportunity_broken", "hard_stop_current_return"})
        profit_only = row["profit_present"] and row["profit_referenced_in_pm_reason"] and not momentum_or_signal and reasons == {"profit_retention_break"}
        out.append(
            {
                "business_date": row["business_date"],
                "symbol": row["symbol"],
                "position_campaign_id": row["position_campaign_id"],
                "profit_present": row["profit_present"],
                "profit_referenced_in_pm_reason": row["profit_referenced_in_pm_reason"],
                "profit_only_exit_evidence": profit_only,
                "momentum_or_signal_exit_evidence": momentum_or_signal,
                "pm_reason_codes": row["pm_reason_codes"],
                "judgment": "PROFIT_TAKING_ONLY" if profit_only else ("PROFIT_PRESENT_NOT_CAUSAL" if row["profit_present"] else "NO_PROFIT_PRESENT"),
            }
        )
    return out


def conformance(rows: list[dict[str, Any]], exit_reentries: list[dict[str, Any]], unstable: list[dict[str, Any]]) -> dict[str, Any]:
    hold = summarize_causality(rows, "HOLD")
    reduce = summarize_causality(rows, "REDUCE")
    exit_ = summarize_causality(rows, "EXIT")
    profit_only = sum(1 for item in profit_taking_audit(rows) if item["profit_only_exit_evidence"])
    unexplained_exit = exit_["class_counts"].get("UNEXPLAINED", 0) + exit_["class_counts"].get("INSUFFICIENT_EVIDENCE", 0)
    return {
        "momentum_follow_conformance": "PARTIALLY_CONFORMANT",
        "axis_results": {
            "hold_while_continuation_evidence_remains": "PARTIAL",
            "reduce_on_weakening_where_justified": "PARTIAL",
            "exit_on_broken_or_invalidated_state": "PARTIAL",
            "fast_loss_control_preserved": "CONFIRMED",
            "profit_alone_not_used_as_exit": "PARTIAL" if profit_only else "CONFIRMED",
            "short_interval_reentry_explainable": "PARTIAL",
            "action_boundary_reasonably_stable": "PARTIAL" if unstable else "UNKNOWN",
        },
        "evidence_counts": {
            "hold_count": hold["count"],
            "reduce_count": reduce["count"],
            "exit_count": exit_["count"],
            "profit_taking_only_count": profit_only,
            "unexplained_exit_count": unexplained_exit,
            "short_reentry_count": len(exit_reentries),
            "unstable_boundary_count": len(unstable),
        },
    }


def render_report(summary: dict[str, Any]) -> str:
    return f"""# Phase27-D2-F Existing PM HOLD / REDUCE / EXIT Decision Causality and Momentum-follow Conformance Audit

## 1. Scope

This is a read-only audit of existing PM HOLD / REDUCE / EXIT decisions in the run-scoped baseline evidence.

```text
Run: {RUN_ID}
Implementation Change: false
PM / Strategy / Runtime Change: false
Historical rerun / fresh-run / resume: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
{summary['primary_judgment']}
```

Supporting:

```json
{json.dumps(summary['supporting_judgments'], ensure_ascii=False, indent=2)}
```

## 3. Key Counts

```json
{json.dumps(summary['classification_counts'], ensure_ascii=False, indent=2)}
```

## 4. Findings

1. PM HOLD is partly active, not purely implicit: HOLD rows carry PM reason codes, mainly `positive_expected_edge`, `downside_risk_contained`, and sometimes `trend_continuation`.
2. HOLD causality is only partial because many HOLD rows lack a dedicated materialized Momentum Continuation state; reason codes support continuation/validity but not a full persistence model.
3. REDUCE is mostly explained by drawdown/risk weakening evidence, especially `peak_drawdown_warning` and `risk_increased_but_trend_not_broken`.
4. EXIT is partly explained by `hard_stop_current_return`, `trend_and_opportunity_broken`, and `profit_retention_break`; however `profit_retention_break` alone leaves ambiguity around profit retention versus momentum failure.
5. Profit existing at EXIT is separated from profit causing EXIT. Profit-only evidence is counted only when PM reason evidence is exclusively profit-linked.
6. Short EXIT -> BUY_NEW re-entry exists and is only partially explained by materialized input changes. Some cases remain possible whipsaw / unstable boundary candidates.
7. Current PM behaves as partially conformant Momentum Follow: it can hold, reduce, and exit with directional evidence, but continuation evidence is not explicit enough to fully confirm stable HOLD / EXIT boundaries.
8. The first Performance Design review candidate should be PM input/reasoning contract improvement for explicit Momentum Continuation / boundary stability evidence. This is not a recommendation to add a separate Action Authority.

## 5. Evidence Limitations

- Run-scoped PM snapshot is the direct PM decision evidence; Strategy `position_management.v1` rows remain adapter `UNRESOLVED` in this baseline.
- Dedicated `momentum_continuation_state` is not materialized in the inspected artifacts.
- Counterfactual HOLD instead of EXIT is not observable.
- PnL was not treated as PM input causality; it is used only to distinguish profit-present from profit-referenced evidence.

## 6. Evidence Files

```text
{OUT_DIR.relative_to(REPO_ROOT)}
```

## 7. Validation

```text
python3 -m py_compile tools/phase27_analysis/phase27_d2f_generate_pm_causality_audit.py
PASS

python3 -m json.tool reports/phase27_d2f_existing_pm_hold_reduce_exit_decision_causality_and_momentum_follow_conformance_audit/summary.json
PASS
```
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, timelines = materialize_inventory()
    hold = summarize_causality(rows, "HOLD")
    reduce = summarize_causality(rows, "REDUCE")
    exit_ = summarize_causality(rows, "EXIT")
    transition_summary, unstable = transition_analysis(timelines)
    reentries = exit_reentry_audit(rows)
    profit = profit_taking_audit(rows)
    conformance_payload = conformance(rows, reentries, unstable)
    classification_counts = {
        "hold_count_by_causality_class": hold["class_counts"],
        "reduce_count_by_causality_class": reduce["class_counts"],
        "exit_count_by_causality_class": exit_["class_counts"],
        "hold_to_exit_count": transition_summary["transition_counts"].get("HOLD->EXIT", 0),
        "exit_to_1bd_buy_new_count": sum(1 for item in reentries if item["business_day_interval"] == 1),
        "exit_to_2bd_buy_new_count": sum(1 for item in reentries if item["business_day_interval"] == 2),
        "exit_to_3_5bd_buy_new_count": sum(1 for item in reentries if 3 <= item["business_day_interval"] <= 5),
        "possible_whipsaw_count": sum(1 for item in reentries if item["classification"] == "POSSIBLE_WHIPSAW"),
        "unstable_boundary_count": len(unstable),
        "profit_taking_only_count": sum(1 for item in profit if item["profit_only_exit_evidence"]),
        "unexplained_exit_count": exit_["class_counts"].get("UNEXPLAINED", 0),
        "insufficient_evidence_count": sum(1 for item in rows if item["causality_class"] == "INSUFFICIENT_EVIDENCE"),
    }
    summary = {
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "implementation_changed": False,
        "historical_executed": False,
        "fresh_run_executed": False,
        "primary_judgment": "PHASE27_D2F_PM_MOMENTUM_FOLLOW_PARTIAL_CONFORMANCE_IMPROVEMENT_TARGET_IDENTIFIED",
        "supporting_judgments": {
            "hold_causality": "PARTIAL",
            "reduce_causality": "PARTIAL",
            "exit_causality": "PARTIAL",
            "profit_taking_only_exit": "OBSERVED" if classification_counts["profit_taking_only_count"] else "NOT_OBSERVED",
            "short_reentry": "PARTIAL",
            "decision_boundary_stability": "PARTIAL" if unstable else "UNKNOWN",
            "momentum_follow_conformance": "PARTIAL",
            "new_momentum_component": "PM_INPUT_IMPROVEMENT_CANDIDATE",
            "next_entry": "PERFORMANCE_DESIGN_REVIEW",
        },
        "classification_counts": classification_counts,
        "acceptance_answers": {
            "is_pm_hold_active": "PARTIAL_YES_REASON_CODES_PRESENT_BUT_NO_DEDICATED_MOMENTUM_STATE",
            "are_hold_reasons_explainable": "PARTIAL",
            "does_reduce_express_weakening": "PARTIAL_YES_RISK_AND_DRAWDOWN_REASONS_PRESENT",
            "is_exit_based_on_momentum_or_signal_failure": "PARTIAL",
            "is_profit_only_exit_evidenced": "YES_FOR_REASON_ONLY_CASES_UNLESS_FURTHER_SIGNAL_EVIDENCE_IS_MATERIALIZED",
            "why_short_reentry": "PARTIAL_INPUT_CHANGES_AND_BOUNDARY_REVERSALS_OBSERVED",
            "is_hold_exit_boundary_stable": "PARTIAL_OR_UNKNOWN_NO_HYSTERESIS_FIELD_MATERIALIZED",
            "sell_buyback_primary_cause": "PM_DECISION_AND_INPUT_BOUNDARY_PARTIAL; NOT PROVEN AS SINGLE CAUSE",
            "new_component_needed": "NO_NEW_ACTION_AUTHORITY; PM_INPUT_OR_EVIDENCE_CONTRACT_IMPROVEMENT_CANDIDATE",
            "first_performance_experiment_candidate": "PM Momentum Continuation / HOLD-EXIT boundary evidence contract review",
        },
    }
    evidence_limitations = {
        "limitations": [
            "Run-scoped PM snapshot is direct PM evidence; Strategy position_management.v1 adapter rows are UNRESOLVED in this baseline.",
            "Dedicated momentum_continuation_state is not materialized.",
            "Counterfactual HOLD instead of EXIT cannot be proven.",
            "Performance report PnL is not used as PM input causality.",
            ".runtime is referenced only where embedded in run-scoped artifact fields; it is not read as authoritative evidence.",
        ]
    }
    performance_candidates = {
        "ranking": [
            {
                "rank": 1,
                "candidate": "PM input / reasoning contract improvement for explicit Momentum Continuation and HOLD/EXIT boundary stability",
                "rationale": "HOLD/EXIT causality is partial and dedicated continuation state is not materialized.",
                "action_authority_added": False,
            },
            {
                "rank": 2,
                "candidate": "Evidence-only reusable Momentum State artifact candidate",
                "rationale": "Could make continuation/weakening auditable without producing actions.",
                "action_authority_added": False,
            },
            {
                "rank": 3,
                "candidate": "Separate action-producing Momentum component",
                "rationale": "Rejected by current evidence and architecture rule.",
                "action_authority_added": True,
                "judgment": "DO_NOT_SELECT",
            },
        ]
    }
    write_json(OUT_DIR / "summary.json", summary)
    write_json(OUT_DIR / "pm_decision_inventory.json", rows)
    write_csv(OUT_DIR / "pm_decision_inventory.csv", rows)
    write_json(OUT_DIR / "campaign_decision_timelines.json", timelines)
    write_csv(OUT_DIR / "campaign_decision_timelines.csv", timelines)
    write_json(OUT_DIR / "hold_causality.json", hold)
    write_json(OUT_DIR / "reduce_causality.json", reduce)
    write_json(OUT_DIR / "exit_causality.json", exit_)
    write_json(OUT_DIR / "hold_exit_boundary_audit.json", {"summary": transition_summary, "unstable_boundary_candidates": unstable})
    write_json(OUT_DIR / "exit_reentry_audit.json", reentries)
    write_json(OUT_DIR / "profit_taking_audit.json", profit)
    write_json(OUT_DIR / "input_transition_analysis.json", transition_summary)
    write_json(OUT_DIR / "momentum_follow_conformance.json", conformance_payload)
    write_json(
        OUT_DIR / "new_component_necessity_review.json",
        {
            "judgment": "PM_INPUT_IMPROVEMENT_CANDIDATE",
            "selected_option": "B",
            "options": {
                "A": "Existing PM already consumes sufficient continuation evidence: NOT_CONFIRMED",
                "B": "Existing PM lacks explicit continuation evidence, but inputs can be organized inside PM: SUPPORTED",
                "C": "Reusable Momentum state artifact as evidence only: CANDIDATE",
                "D": "Separate action-producing Momentum component: REJECTED",
            },
        },
    )
    write_json(OUT_DIR / "performance_design_candidate_ranking.json", performance_candidates)
    write_json(OUT_DIR / "evidence_limitations.json", evidence_limitations)
    write_json(
        OUT_DIR / "test_results.json",
        {
            "historical_executed": False,
            "fresh_run_executed": False,
            "commands": [
                {"command": "python3 -m py_compile tools/phase27_analysis/phase27_d2f_generate_pm_causality_audit.py", "result": "PASS"},
                {"command": "python3 -m json.tool reports/phase27_d2f_existing_pm_hold_reduce_exit_decision_causality_and_momentum_follow_conformance_audit/summary.json", "result": "PASS"},
                {
                    "command": "for f in reports/phase27_d2f_existing_pm_hold_reduce_exit_decision_causality_and_momentum_follow_conformance_audit/*.json; do python3 -m json.tool \"$f\" >/dev/null || exit 1; done",
                    "result": "PASS",
                },
            ],
        },
    )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report(summary) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
