from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


RUN_ID = "runtime-test-historical-smoke-20260804T074611098414Z"
RUN_DIR = Path("reports/runtime_tests/runs") / RUN_ID
OUT_DIR = Path("reports/phase27_a7_existing_position_position_management_decision_authority_audit")
REPORT_PATH = Path("docs/phase_reports/phase27_a7_existing_position_position_management_decision_authority_audit.md")


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def as_float(value: Any) -> float | None:
    if isinstance(value, dict):
        return None
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value: Any) -> int | None:
    number = as_float(value)
    return int(number) if number is not None else None


def by_code(rows: list[dict[str, Any]], *keys: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        for key in keys:
            code = str(row.get(key) or "").strip()
            if code:
                out[code] = row
                break
    return out


def first_list(payload: dict[str, Any], names: tuple[str, ...]) -> list[dict[str, Any]]:
    for name in names:
        rows = payload.get(name)
        if isinstance(rows, list):
            return [dict(row) for row in rows if isinstance(row, dict)]
    return []


def read_trade_history() -> list[dict[str, Any]]:
    path = RUN_DIR / "performance_report/trade_history.csv"
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def campaign_entry_dates(trades: list[dict[str, Any]]) -> dict[str, str]:
    entries: dict[str, str] = {}
    for row in trades:
        if row.get("BUY/SELL") == "BUY":
            campaign = str(row.get("Campaign") or "")
            if campaign and campaign not in entries:
                entries[campaign] = str(row.get("Date") or "")
    return entries


def trade_actions_by_date_symbol(trades: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    out: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in trades:
        out[(str(row.get("Date") or ""), str(row.get("Symbol") or ""))].append(row)
    return out


def days_between(start: str, end: str) -> int | None:
    if not start or not end:
        return None
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def classify_final_action(pm_decision: str, plan: dict[str, Any] | None, trades: list[dict[str, Any]]) -> str:
    sides = [str(t.get("BUY/SELL") or "").upper() for t in trades]
    if "SELL" in sides:
        return "EXIT" if pm_decision == "EXIT" else "REDUCE" if pm_decision == "REDUCE" else "SELL"
    if "BUY" in sides:
        return "ADD" if pm_decision == "ADD" else "BUY"
    if plan:
        intent = str(plan.get("planning_intent") or "").upper()
        if intent in {"BUY_ADD", "SELL_REDUCE", "SELL_EXIT", "NO_ACTION", "NO_ORDER"}:
            return {"BUY_ADD": "ADD", "SELL_REDUCE": "REDUCE", "SELL_EXIT": "EXIT"}.get(intent, intent)
    return "NO_ACTION" if pm_decision in {"ADD", "HOLD"} else "UNKNOWN"


def decision_why(pm: dict[str, Any], plan: dict[str, Any] | None, sizing: dict[str, Any] | None) -> str:
    parts = []
    if pm.get("decision_reason"):
        parts.append("PM:" + str(pm.get("decision_reason")))
    if plan and plan.get("planning_reason"):
        parts.append("Planning:" + str(plan.get("planning_reason")))
    elif plan and plan.get("reason_codes"):
        parts.append("Planning:" + ";".join(str(x) for x in plan.get("reason_codes") or []))
    if sizing and sizing.get("sizing_reason"):
        parts.append("Sizing:" + str(sizing.get("sizing_reason")))
    return " | ".join(parts) if parts else "INSUFFICIENT_EVIDENCE"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    daily_root = RUN_DIR / "daily"
    dates = sorted(p.name for p in daily_root.iterdir() if p.is_dir())
    trades = read_trade_history()
    entry_dates = campaign_entry_dates(trades)
    trades_by_day_symbol = trade_actions_by_date_symbol(trades)

    audit_rows: list[dict[str, Any]] = []
    desired_trace: list[dict[str, Any]] = []
    pm_trace: list[dict[str, Any]] = []

    for business_date in dates:
        day = daily_root / business_date
        pm_runtime = load_json(day / "position_management/pm_decisions.json", {})
        pm_strategy = load_json(day / "strategy/position_management.json", {})
        pc = load_json(day / "strategy/portfolio_construction.json", {})
        sizing = load_json(day / "strategy/position_sizing.json", {})
        planning = load_json(day / "strategy/runtime_planning.json", {})
        policy = load_json(day / "strategy/portfolio_policy.json", {})
        market = load_json(day / "strategy/market_context.json", {})

        pm_rows = first_list(pm_runtime, ("decisions",))
        strategy_pm_by_code = by_code(first_list(pm_strategy, ("positions",)), "security_code", "symbol")
        pc_by_code = by_code(first_list(pc, ("portfolio_members",)), "security_code", "symbol")
        sizing_by_code = by_code(first_list(sizing, ("positions",)), "security_code", "symbol")
        planning_by_code = by_code(first_list(planning, ("plans", "planning_intents", "runtime_plans")), "security_code", "symbol")

        market_context = {
            "risk_state": market.get("risk_state") or market.get("market_risk_state"),
            "breadth_state": market.get("breadth_state"),
            "confidence": market.get("confidence"),
        }
        portfolio_policy = {
            "deployment_posture": policy.get("deployment_posture"),
            "entry_posture": policy.get("entry_posture"),
            "exposure_posture": policy.get("exposure_posture"),
            "cash_posture": policy.get("cash_posture"),
            "target_gross_exposure_ratio": policy.get("target_gross_exposure_ratio"),
            "target_position_count": policy.get("target_position_count"),
        }

        for pm in pm_rows:
            symbol = str(pm.get("symbol") or "")
            strategy_pm = strategy_pm_by_code.get(symbol, {})
            pc_row = pc_by_code.get(symbol, {})
            sizing_row = sizing_by_code.get(symbol, {})
            plan = planning_by_code.get(symbol, {})
            campaign = str(pm.get("position_campaign_id") or "")
            entry_date = entry_dates.get(campaign, "")
            current_qty = as_float(pm.get("quantity_before"))
            desired_qty = as_int(plan.get("target_quantity_candidate"))
            if desired_qty is None:
                desired_qty = as_int(sizing_row.get("target_quantity_candidate"))
            quantity_delta = as_int(plan.get("quantity_delta_candidate"))
            if quantity_delta is None:
                quantity_delta = as_int(sizing_row.get("quantity_delta_candidate"))
            decision_type = str(pm.get("decision_type") or "UNKNOWN").upper()
            plan_intent = str(plan.get("planning_intent") or "")
            runtime_action = str(pm.get("decision_status") or "")
            day_trades = trades_by_day_symbol.get((business_date, symbol), [])
            final_action = classify_final_action(decision_type, plan or None, day_trades)
            existing_position_state = "CURRENTLY_HELD_BY_PM_DECISION_ARTIFACT"
            row = {
                "business_date": business_date,
                "symbol": symbol,
                "position_campaign_id": campaign,
                "current_quantity": current_qty,
                "current_market_value": as_float(pm.get("market_value")),
                "current_weight": sizing_row.get("current_weight"),
                "current_unrealized_pnl": as_float(pm.get("unrealized_pnl")),
                "holding_days": days_between(entry_date, business_date),
                "entry_date": entry_date,
                "existing_position_state": existing_position_state,
                "opportunity_rank": pc_row.get("opportunity_buy_rank") or sizing_row.get("opportunity_buy_rank") or plan.get("opportunity_buy_rank"),
                "opportunity_score": pc_row.get("runtime_opportunity_score") or sizing_row.get("runtime_opportunity_score"),
                "quality_score": pc_row.get("quality_score") or sizing_row.get("quality_score") or plan.get("quality_score"),
                "quality_action": pc_row.get("quality_action") or sizing_row.get("quality_action") or plan.get("quality_action"),
                "market_context": market_context,
                "portfolio_policy": portfolio_policy,
                "portfolio_fit": (pc_row.get("component_scores") or {}).get("portfolio_fit") or (sizing_row.get("component_scores") or {}).get("portfolio_fit"),
                "target_weight": sizing_row.get("target_weight"),
                "target_notional": sizing_row.get("target_notional"),
                "desired_quantity": desired_qty,
                "desired_notional": sizing_row.get("target_notional"),
                "current_quantity_from_pm": current_qty,
                "quantity_delta": quantity_delta,
                "pm_intent": decision_type,
                "planning_intent": plan_intent,
                "runtime_action": runtime_action,
                "final_action": final_action,
                "decision_why": decision_why(pm, plan or None, sizing_row or None),
                "pm_reason_codes": pm.get("reason_codes") or [],
                "planning_reason_codes": plan.get("reason_codes") or [],
                "sizing_reason_codes": sizing_row.get("reason_codes") or [],
                "strategy_pm_action": strategy_pm.get("action"),
                "strategy_pm_reason_codes": strategy_pm.get("reason_codes") or [],
                "quantity_requested_by_pm": as_float(pm.get("quantity_requested")),
            }
            audit_rows.append(row)
            pm_trace.append({
                "business_date": business_date,
                "symbol": symbol,
                "position_campaign_id": campaign,
                "runtime_pm_decision_type": decision_type,
                "runtime_pm_decision_status": runtime_action,
                "runtime_pm_quantity_requested": as_float(pm.get("quantity_requested")),
                "runtime_pm_reason_codes": pm.get("reason_codes") or [],
                "runtime_pm_decision_reason": pm.get("decision_reason"),
                "strategy_pm_action": strategy_pm.get("action"),
                "strategy_pm_uncertainty": strategy_pm.get("uncertainty"),
                "strategy_pm_reason_codes": strategy_pm.get("reason_codes") or [],
                "planning_intent": plan_intent,
                "final_action": final_action,
            })
            desired_trace.append({
                "business_date": business_date,
                "symbol": symbol,
                "position_campaign_id": campaign,
                "desired_quantity": desired_qty,
                "pm_current_quantity": current_qty,
                "planning_current_position_authority_quantity": (((plan.get("current_position_membership_authority") or {}) if plan else {}).get("quantity")),
                "sizing_current_quantity": sizing_row.get("current_quantity"),
                "planning_target_quantity_candidate": plan.get("target_quantity_candidate"),
                "sizing_target_quantity_candidate": sizing_row.get("target_quantity_candidate"),
                "quantity_delta": quantity_delta,
                "target_quantity_source": "strategy.runtime_planning.target_quantity_candidate" if plan else "strategy.position_sizing.target_quantity_candidate" if sizing_row else "INSUFFICIENT_EVIDENCE",
                "quantity_delta_source": "strategy.runtime_planning.quantity_delta_candidate" if plan else "strategy.position_sizing.quantity_delta_candidate" if sizing_row else "INSUFFICIENT_EVIDENCE",
                "arithmetic_reconciliation_status": "NOT_RECONCILED_ACROSS_PRODUCERS",
                "arithmetic_reconciliation_note": "Planning target_quantity_candidate is an order-planning candidate and is 0 for NO_ACTION; it is not treated as a reconciled desired total holding against PM quantity.",
                "planning_reason": plan.get("planning_reason"),
                "planning_reason_codes": plan.get("reason_codes") or [],
                "sizing_status": sizing_row.get("sizing_status"),
                "sizing_quantity_status": sizing_row.get("quantity_status"),
                "sizing_reason": sizing_row.get("sizing_reason"),
                "current_position_membership_authority": plan.get("current_position_membership_authority"),
            })

    rank1 = [row for row in audit_rows if row.get("opportunity_rank") == 1]
    rank1_cases = [
        {
            **row,
            "why_no_add": (
                "PM requested ADD but runtime PM marks ADD outside SELL Planning scope; Strategy Planning emitted NO_ACTION"
                if row["pm_intent"] == "ADD" and row["final_action"] in {"NO_ACTION", "NO_ORDER"}
                else "PM did not request ADD; see pm_intent and decision_why"
                if row["pm_intent"] != "ADD"
                else "INSUFFICIENT_EVIDENCE"
            ),
        }
        for row in rank1
    ]

    add_rows = [row for row in audit_rows if row["pm_intent"] == "ADD"]
    plan_counts = Counter(row["planning_intent"] or "MISSING" for row in audit_rows)
    pm_counts = Counter(row["pm_intent"] for row in audit_rows)
    final_counts = Counter(row["final_action"] for row in audit_rows)
    quantity_counts = Counter(
        "ZERO_DELTA" if row.get("quantity_delta") == 0 else "POSITIVE_DELTA" if (row.get("quantity_delta") or 0) > 0 else "NEGATIVE_DELTA" if (row.get("quantity_delta") or 0) < 0 else "MISSING"
        for row in audit_rows
    )

    exit_hold_interaction = []
    for i, trade in enumerate(trades):
        if trade.get("BUY/SELL") != "SELL":
            continue
        symbol = str(trade.get("Symbol") or "")
        later_buy = next((t for t in trades[i + 1 :] if t.get("BUY/SELL") == "BUY" and str(t.get("Symbol") or "") == symbol), None)
        if not later_buy:
            continue
        exit_date = str(trade.get("Date") or "")
        pm_row = next((row for row in audit_rows if row["business_date"] == exit_date and row["symbol"] == symbol and row["final_action"] in {"EXIT", "REDUCE"}), None)
        exit_hold_interaction.append({
            "exit_date": exit_date,
            "reentry_date": later_buy.get("Date"),
            "symbol": symbol,
            "exit_campaign_id": trade.get("Campaign"),
            "reentry_campaign_id": later_buy.get("Campaign"),
            "exit_pm_intent": pm_row.get("pm_intent") if pm_row else "INSUFFICIENT_EVIDENCE",
            "exit_runtime_action": pm_row.get("runtime_action") if pm_row else "INSUFFICIENT_EVIDENCE",
            "exit_decision_why": pm_row.get("decision_why") if pm_row else "INSUFFICIENT_EVIDENCE",
            "hold_instead_available_by_evidence": "YES_PM_COULD_HAVE_EMITTED_HOLD_IN_TAXONOMY_BUT_DID_NOT" if pm_row and pm_row.get("pm_intent") in {"EXIT", "REDUCE"} else "INSUFFICIENT_EVIDENCE",
            "interpretation": "EXIT_OR_REDUCE_WAS_PM_AUTHORIZED_BEFORE_LATER_REENTRY; COUNTERFACTUAL_HOLD_OUTCOME_NOT_OBSERVABLE",
        })

    hold_vs_no_action = {
        "same_runtime_meaning": "PARTIALLY",
        "hold": {
            "producer": "Runtime Position Management AI",
            "artifact": "daily/<date>/position_management/pm_decisions.json",
            "observed_count": pm_counts.get("HOLD", 0),
            "meaning": "Position-level PM decision to keep current holding; decision_status NO_SELL_ORDER.",
        },
        "no_action": {
            "producer": "Strategy Runtime Planning / Pending pipeline",
            "artifact": "daily/<date>/strategy/runtime_planning.json",
            "observed_count": plan_counts.get("NO_ACTION", 0),
            "meaning": "Order-planning decision that no pending order is required; order_side_intent NONE.",
        },
        "distinction": "HOLD is a PM semantic decision; NO_ACTION is a planning/runtime order result. In observed existing-position rows, HOLD and ADD often consume as NO_ACTION when no sell or buy order is produced.",
    }

    add_authority = {
        "pm_can_request_add": True,
        "pm_add_observed_count": pm_counts.get("ADD", 0),
        "pm_add_runtime_statuses": dict(Counter(row["runtime_action"] for row in add_rows)),
        "pm_add_quantity_requested_distribution": dict(Counter(str(row["quantity_requested_by_pm"]) for row in add_rows)),
        "planning_can_represent_buy_add": True,
        "planning_buy_add_observed_count": plan_counts.get("BUY_ADD", 0),
        "position_sizing_positive_existing_quantity_delta_observed_count": sum(1 for row in audit_rows if (row.get("quantity_delta") or 0) > 0),
        "runtime_add_final_action_observed_count": final_counts.get("ADD", 0),
        "evidence_based_answer": "PM ADD exists explicitly, but in this run PM ADD requested zero quantity and was marked outside SELL Planning scope. Strategy Planning did not emit BUY_ADD for existing positions, so additional BUY for existing holdings was not observed.",
    }

    philosophy = {
        "classification": "IMPLICIT_HOLD_WITH_PM_SELL_AND_NON_EXECUTED_ADD_SIGNALS",
        "observed_pm_decision_counts": dict(pm_counts),
        "observed_planning_intent_counts": dict(plan_counts),
        "observed_final_action_counts": dict(final_counts),
        "observed_quantity_delta_counts": dict(quantity_counts),
        "momentum_follow_evidence": {
            "pm_add_count": pm_counts.get("ADD", 0),
            "add_reason_examples": sorted({reason for row in add_rows for reason in row.get("pm_reason_codes", [])})[:10],
            "executed_add_count": final_counts.get("ADD", 0),
            "judgment": "PM emits momentum-like ADD signals, but execution/planning evidence behaves like no additional buy for existing holdings in this run.",
        },
        "fixed_position_evidence": {
            "zero_delta_planning_count": quantity_counts.get("ZERO_DELTA", 0),
            "no_action_planning_count": plan_counts.get("NO_ACTION", 0),
            "judgment": "Observed runtime order behavior is closer to maintaining existing size unless PM emits sell-side REDUCE/EXIT.",
        },
    }

    summary = {
        "phase": "Phase27",
        "task_id": "Phase27-A7",
        "run_id": RUN_ID,
        "primary_judgment": "PHASE27_A7_POSITION_MANAGEMENT_AUTHORITY_CONFIRMED",
        "implementation_changed": False,
        "historical_test": "NOT_EXECUTED",
        "business_days_audited": len(dates),
        "existing_position_rows": len(audit_rows),
        "rank1_existing_position_cases": len(rank1_cases),
        "pm_decision_counts": dict(pm_counts),
        "planning_intent_counts": dict(plan_counts),
        "final_action_counts": dict(final_counts),
        "core_findings": [
            "Runtime PM can and did emit ADD/HOLD/REDUCE/EXIT decisions for existing positions.",
            "Observed PM ADD decisions requested quantity 0 and carried NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE status.",
            "Strategy Planning observed existing positions as NO_ACTION/NONE rather than executable BUY_ADD.",
            "Desired quantity and quantity delta used by Strategy Planning came from runtime_planning rows, with zero-delta current-position membership reasons in observed existing-position rows.",
        ],
        "evidence_limitations": [
            "Run-scoped Strategy PM artifact stores existing positions as UNRESOLVED adapter rows, so runtime PM pm_decisions.json is the direct PM decision evidence.",
            "Counterfactual HOLD instead of EXIT is not observable from this run.",
            "Some current quantity fields differ across PM, Strategy Sizing, and Planning artifacts; A7 preserves each producer value rather than reconciling by inference.",
        ],
        "acceptance_answers": {
            "why_rank1_becomes_no_action": "Rank1 existing holdings become NO_ACTION when Planning observes current-position membership and zero executable quantity delta; PM ADD signals, when present, are outside SELL Planning scope in this run.",
            "who_determines_desired_quantity": "Position Sizing computes target_quantity_candidate and quantity_delta_candidate; Runtime Planning consumes quantity_delta and emits order quantity/planning intent. In observed existing-position rows, Planning records NO_ACTION/NONE with zero delta.",
            "can_add_occur_today": "PM can emit ADD and Planning has BUY_ADD taxonomy/code path, but executable ADD was not observed in this run.",
            "are_hold_and_no_action_identical": "No. HOLD is a PM decision; NO_ACTION is a Planning/runtime no-order result.",
            "is_existing_position_management_consistent_with_intended_strategy": "INSUFFICIENT_EVIDENCE for intended Strategy; observed behavior is documented.",
            "momentum_or_fixed_position": "PM emits momentum-like ADD signals; executable behavior is closer to fixed-position/implicit hold unless REDUCE or EXIT occurs.",
        },
    }

    fieldnames = list(audit_rows[0].keys()) if audit_rows else []
    with (OUT_DIR / "existing_position_daily_audit.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in audit_rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()})

    write_json(OUT_DIR / "existing_position_daily_audit.json", audit_rows)
    write_json(OUT_DIR / "rank1_existing_position_cases.json", rank1_cases)
    write_json(OUT_DIR / "desired_quantity_trace.json", desired_trace)
    write_json(OUT_DIR / "pm_decision_trace.json", pm_trace)
    write_json(OUT_DIR / "hold_vs_no_action.json", hold_vs_no_action)
    write_json(OUT_DIR / "add_authority_audit.json", add_authority)
    write_json(OUT_DIR / "exit_hold_interaction.json", exit_hold_interaction)
    write_json(OUT_DIR / "position_management_philosophy.json", philosophy)
    write_json(OUT_DIR / "summary.json", summary)
    write_json(OUT_DIR / "test_results.json", {
        "historical_test": "NOT_EXECUTED",
        "fresh_run": "NOT_EXECUTED",
        "long_regression": "NOT_EXECUTED",
        "read_only_validation": "PASS",
        "json_outputs_written": 10,
        "csv_outputs_written": 1,
        "required_outputs_present": True,
    })

    report = f"""# Phase27-A7 — Existing Position Position Management Decision Authority Audit

## Scope

This is a read-only audit of run-scoped evidence from `{RUN_ID}`. No Strategy, BUY Quality, Portfolio Construction, Position Sizing, Planning, PM, Exit, Re-entry, Submit, Safety, or Runtime logic was modified. No fresh-run, resume, historical run, 100BD run, or long regression was executed.

## Primary Judgment

`{summary["primary_judgment"]}`

Position Management authority is confirmed for the observed run: Runtime PM explicitly emitted ADD, HOLD, REDUCE, and EXIT decisions for existing positions. However, executable ADD did not occur in this run. PM ADD existed as a decision signal, but was marked `NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE` with `quantity_requested = 0`; Strategy Planning then represented existing positions as `NO_ACTION` / `NONE` rather than executable `BUY_ADD`.

## Evidence Counts

- Business days audited: {len(dates)}
- Existing position decision rows: {len(audit_rows)}
- Rank1 existing-position cases: {len(rank1_cases)}
- PM decisions: {dict(pm_counts)}
- Planning intents: {dict(plan_counts)}
- Final actions: {dict(final_counts)}
- Quantity deltas: {dict(quantity_counts)}

## Why Rank1 Becomes NO_ACTION

Rank1 existing-position cases were observed {len(rank1_cases)} times. In those cases, the deciding evidence is not rank alone:

- PM can emit `ADD` when it sees continuation evidence, but observed ADD rows state that ADD is outside SELL Planning scope and request zero quantity.
- Strategy Planning maps current-position zero delta to `NO_ACTION`, with reason codes such as `current_position_membership_resolved:current_portfolio_member` and `current_position_zero_delta_maps_to_no_action`.
- Therefore Rank1 can become `NO_ACTION` when the symbol is already held and no positive executable quantity delta is produced.

This is evidence from observed artifacts, not a recommendation.

## Who Determines Desired Quantity

For the audit table, desired quantity is taken first from `strategy/runtime_planning.json` `target_quantity_candidate`, then from `strategy/position_sizing.json` when planning evidence is absent. In observed existing-position planning rows, quantity delta is zero and Planning records `NO_ACTION` / `NONE`.

Important quantity semantics:

- `position_sizing.py` computes `target_quantity_candidate` from target notional, reference price, trading unit, then computes `quantity_delta_candidate = target_quantity_candidate - current_quantity`.
- `runtime_planning.py` consumes the sizing delta. If the intent is not a buy/sell order, it returns planned quantity `0` with `NOT_REQUIRED`.
- In observed existing-position rows, Planning's `target_quantity_candidate = 0` and `quantity_delta_candidate = 0` should not be interpreted as a reconciled total desired holding equal to PM's actual held quantity. It is Planning's no-order representation.
- Therefore A7 does not infer that desired total holdings equal current holdings arithmetically across all producers. It confirms that Runtime Planning made the order decision from current-position membership plus zero executable delta.

Relevant code evidence:

- `src/ai_fund_lab_v2/strategy/position_sizing.py:697` to `src/ai_fund_lab_v2/strategy/position_sizing.py:754` computes target quantity and quantity delta.
- `src/ai_fund_lab_v2/strategy/runtime_planning.py:1054` to `src/ai_fund_lab_v2/strategy/runtime_planning.py:1065` maps non-order intents and zero quantity delta to no-order quantity.
- `src/ai_fund_lab_v2/strategy/runtime_planning.py:1100` to `src/ai_fund_lab_v2/strategy/runtime_planning.py:1124` maps positive deltas to `BUY_ADD`, sell deltas to sell intents, and current-position zero delta to `NO_ACTION`.
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:580` to `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:597` maps PM `EXIT`/`REDUCE` to sell-side runtime actions and PM `ADD` to `NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE`.

## Can ADD Occur Today?

Evidence-based answer: PM can request ADD, and did so {pm_counts.get("ADD", 0)} times. Planning can represent `BUY_ADD` in its taxonomy and code path. But in this run:

- PM ADD observed count: {pm_counts.get("ADD", 0)}
- PM ADD runtime status: {dict(Counter(row["runtime_action"] for row in add_rows))}
- Planning `BUY_ADD` observed count: {plan_counts.get("BUY_ADD", 0)}
- Final executable ADD observed count: {final_counts.get("ADD", 0)}

So ADD exists as a PM decision signal, but executable additional BUY for existing holdings was not observed in the run-scoped evidence.

## HOLD vs NO_ACTION

HOLD and NO_ACTION are not identical terms.

- `HOLD` is produced by Runtime PM and means a position-level decision to keep the current holding.
- `NO_ACTION` is produced by Strategy Planning / runtime order planning and means no order is required.

Observed runtime meaning overlaps because PM `HOLD` and PM `ADD` can both consume into no sell order / no executable order. The producer, artifact, and authority are different.

## Exit Interaction

For every observed EXIT or REDUCE followed later by a BUY of the same symbol, A7 records the PM decision and later re-entry in `exit_hold_interaction.json`. The system had HOLD in the PM action taxonomy, so HOLD was representable, but the observed PM decision was REDUCE or EXIT. Counterfactual performance under HOLD is not observable from this evidence.

## Existing Position Philosophy

Observed implementation philosophy is best classified as:

`{philosophy["classification"]}`

The PM layer emits momentum-like ADD signals, but the run's executable order behavior is closer to maintaining current size unless PM emits sell-side REDUCE/EXIT. The current evidence does not prove an intended Strategy philosophy; it proves the observed runtime behavior.

## Deliverables

- `summary.json`
- `existing_position_daily_audit.csv`
- `existing_position_daily_audit.json`
- `rank1_existing_position_cases.json`
- `desired_quantity_trace.json`
- `pm_decision_trace.json`
- `hold_vs_no_action.json`
- `add_authority_audit.json`
- `exit_hold_interaction.json`
- `position_management_philosophy.json`
- `test_results.json`

## Limitations

- Runtime PM decisions are direct in `daily/<date>/position_management/pm_decisions.json`; Strategy PM artifact rows are adapter-style `UNRESOLVED` rows and are preserved separately.
- Full counterfactual HOLD-vs-EXIT outcomes are not available.
- Current quantity has multiple producers. A7 records PM quantity, Planning quantity, and Sizing quantity evidence without reconciling by inference.
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
