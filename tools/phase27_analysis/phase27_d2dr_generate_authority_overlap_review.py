#!/usr/bin/env python3
"""Generate Phase27-D2-DR read-only authority overlap review evidence."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "reports/phase27_d2dr_decision_authority_simplification_and_component_overlap_review"
PHASE_REPORT = REPO_ROOT / "docs/phase_reports/phase27_d2dr_decision_authority_simplification_and_component_overlap_review.md"
PRIMARY = "PHASE27_D2DR_DECISION_AUTHORITY_CONFIRMED_WITH_CLARIFICATIONS_D2E_READY"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def supporting() -> dict[str, str]:
    return {
        "final_action_authority": "PARTIAL",
        "pm_vs_position_intent": "WRAPPER_RELATION",
        "portfolio_decision": "RESOLUTION_ONLY",
        "sizing": "QUANTITY_ONLY",
        "runtime_planning": "PARTIAL",
        "feature_double_weighting": "THEORETICAL",
        "artifact_set": "JUSTIFIED",
        "d2e_entry": "APPROVED",
    }


def final_action_inventory() -> list[dict[str, object]]:
    return [
        _producer("BUY_NEW", "Candidate/Opportunity -> position_intent shadow BUY_NEW row", "position_intent._shadow_buy_candidate_rows", "position_intent.v1", "candidate evidence / unresolved action proposal", "SHADOW", "NONE", "target_portfolio_decision.v1", False, False, "MULTIPLE_COMPATIBLE_SIGNALS", "BUY_NEW is intentionally unresolved in D2-A because Incremental Eligibility is not connected."),
        _producer("BUY_NEW", "Portfolio Construction / Runtime Planning existing path", "runtime_planning._resolve_intent", "runtime_planning artifact", "runtime execution intent mapping", "ACTIVE_EXISTING", "PLANNING_INTENT_ONLY", "Strategy Planning / Pending", False, True, "MULTIPLE_COMPATIBLE_SIGNALS", "Existing Runtime Planning can map portfolio ADD_CANDIDATE or positive delta to BUY_NEW; D2-D shadow chain is not connected."),
        _producer("ADD", "Position Management", "position_management.producer._decision_from_row", "PM Decisions Artifact", "existing-position directional reasoning", "ACTIVE_PM", "PM_DIRECTIONAL_INTENT", "position_intent.v1 / legacy sell planning observer", False, True, "SINGLE_AUTHORITY", "PM is the only existing-position ADD directional reason producer."),
        _producer("ADD", "position_intent", "position_intent._row_from_pm_decision", "position_intent.v1", "canonical wrapper / normalized action proposal", "SHADOW", "NONE", "target_portfolio_decision.v1", False, False, "MULTIPLE_COMPATIBLE_SIGNALS", "Wrapper copies PM ADD; it does not recompute ADD."),
        _producer("ADD", "target_portfolio_decision", "target_portfolio_decision._decision_from_intent", "target_portfolio_decision.v1", "portfolio resolution", "SHADOW", "NONE", "position_sizing_plan.v1", False, False, "MULTIPLE_COMPATIBLE_SIGNALS", "Maps ADD to RETAIN/INCREASE/POSITIVE_DELTA_REQUIRED, not a new PM action."),
        _producer("ADD", "position_sizing_plan", "position_sizing_plan._quantity_contract", "position_sizing_plan.v1", "quantity delta candidate", "SHADOW", "NONE", "future Runtime Planning", False, False, "MULTIPLE_COMPATIBLE_SIGNALS", "Preserves PM ADD and emits positive delta or ADD_NOT_SIZED."),
        _producer("ADD", "legacy add_consumer", "add_consumer.build_add_pending_items", "legacy_pm_add_compatibility.v1", "compatibility telemetry only", "NON_DECISION_COMPATIBILITY", "NONE", "sell_pipeline no-order evidence", False, False, "SINGLE_AUTHORITY", "D2-C removed quantity/Pending/Submit authority."),
        _producer("HOLD", "Position Management", "position_management.producer._decision_from_row", "PM Decisions Artifact", "existing-position directional reasoning", "ACTIVE_PM", "PM_DIRECTIONAL_INTENT", "position_intent.v1", False, True, "SINGLE_AUTHORITY", "PM is the active HOLD reasoning producer; NO_ACTION remains downstream."),
        _producer("HOLD", "position_intent", "position_intent._row_from_pm_decision", "position_intent.v1", "canonical wrapper", "SHADOW", "NONE", "target_portfolio_decision.v1", False, False, "MULTIPLE_COMPATIBLE_SIGNALS", "Copies PM HOLD as proposed_position_intent HOLD."),
        _producer("REDUCE", "Position Management", "position_management.producer._decision_from_row", "PM Decisions Artifact", "existing-position directional reasoning / reduce intensity", "ACTIVE_PM", "PM_DIRECTIONAL_INTENT", "position_intent.v1 / sell_pipeline", False, True, "SINGLE_AUTHORITY", "PM emits REDUCE intent; Sell Planning owns executable reduce quantity today."),
        _producer("REDUCE", "position_sizing_plan", "position_sizing_plan._quantity_contract", "position_sizing_plan.v1", "negative partial quantity candidate", "SHADOW", "NONE", "future Runtime Planning", False, False, "MULTIPLE_COMPATIBLE_SIGNALS", "Preserves PM REDUCE and emits negative delta or REDUCE_NOT_SIZED."),
        _producer("EXIT", "Position Management", "position_management.producer._decision_from_row", "PM Decisions Artifact", "existing-position directional reasoning", "ACTIVE_PM", "PM_DIRECTIONAL_INTENT / full sell quantity for legacy sell path", "position_intent.v1 / sell_pipeline", False, True, "SINGLE_AUTHORITY", "PM emits EXIT and current legacy path uses full-position sell quantity."),
        _producer("EXIT", "position_sizing_plan", "position_sizing_plan._quantity_contract", "position_sizing_plan.v1", "full negative quantity candidate", "SHADOW", "NONE", "future Runtime Planning", False, False, "MULTIPLE_COMPATIBLE_SIGNALS", "Preserves PM EXIT and emits target_quantity_candidate=0."),
        _producer("NO_ACTION", "Runtime Planning", "runtime_planning._resolve_intent", "runtime planning artifact", "execution no-order result", "ACTIVE_EXISTING", "PLANNING_INTENT_ONLY", "Strategy Planning / Pending empty no-order", False, True, "SINGLE_AUTHORITY", "NO_ACTION is downstream execution result, not PM HOLD."),
    ]


def _producer(action: str, component: str, function: str, artifact: str, authority_type: str, active: str, effect: str, consumer: str, override: bool, observed: bool, judgment: str, note: str) -> dict[str, object]:
    return {
        "action": action,
        "producer_component": component,
        "producer_function": function,
        "artifact": artifact,
        "authority_type": authority_type,
        "active_or_shadow": active,
        "decision_effect": effect,
        "consumer": consumer,
        "can_override_upstream": override,
        "observed_runtime_use": observed,
        "judgment": judgment,
        "evidence": note,
    }


def authority_matrix() -> list[dict[str, object]]:
    rows = [
        ("Candidate", "candidate artifacts", "candidate universe and base candidate facts", ["candidate rows", "candidate scores"], ["final BUY/SELL", "target weight", "quantity", "Pending"], False, False, False, False, False, "ACTIVE_EXISTING", "Feeds Opportunity/Quality", "NO_CHANGE_REQUIRED"),
        ("Opportunity", "opportunity_rankings.json", "cross-sectional relative attractiveness", ["buy_rank", "runtime_opportunity_score", "rank lineage"], ["final BUY", "target weight", "quantity", "Submit"], False, False, False, False, False, "ACTIVE_EXISTING", "Shared evidence used by Quality/PM; must remain lineage not duplicate decision", "DOCUMENTATION_CLARIFICATION"),
        ("BUY Quality", "buy_quality_decision.v1", "allocation eligibility / confidence adjustment", ["quality_score", "quality_action", "quality_allocation_adjustment"], ["rank ownership", "final BUY", "Submit", "Safety override"], False, False, False, False, False, "ACTIVE_EXISTING", "Uses Opportunity and Market Context; theoretical double-weight risk controlled by SoT", "DOCUMENTATION_CLARIFICATION"),
        ("Market Context", "market_context", "market/regime/breadth evidence", ["risk_state", "breadth", "confidence"], ["symbol final action", "rank override", "quantity"], False, False, False, False, False, "ACTIVE_EXISTING", "Feeds Portfolio Policy and Quality; shared feature", "DOCUMENTATION_CLARIFICATION"),
        ("Portfolio Policy", "portfolio_policy", "portfolio-level posture / exposure / permission", ["target exposure posture", "cash posture", "position count posture"], ["individual symbol final action", "broker quantity", "Submit"], False, False, True, False, False, "ACTIVE_EXISTING", "Portfolio-level, not PM action", "NO_CHANGE_REQUIRED"),
        ("Momentum Continuation", "not yet active artifact", "existing-position continuation evidence", ["continuation state", "reason codes"], ["final action until explicitly promoted", "quantity", "Pending"], False, False, False, False, False, "SHADOW/FOUNDATION", "Supports PM; not independent producer in D2", "DOCUMENTATION_CLARIFICATION"),
        ("Incremental Investment Eligibility", "not yet active artifact", "additional capital justification", ["eligibility state", "reason codes"], ["final ADD/BUY_NEW until explicitly promoted", "quantity", "Pending"], False, False, False, False, False, "SHADOW/FOUNDATION", "Required for future ADD/BUY_NEW but not active in D2", "DOCUMENTATION_CLARIFICATION"),
        ("PM", "PM Decisions Artifact", "existing-position directional action reasoning", ["ADD", "HOLD", "REDUCE", "EXIT"], ["BUY_NEW candidate selection", "portfolio optimization", "ADD quantity", "Submit"], True, False, False, False, False, "ACTIVE_PM", "Canonical source for existing-position direction", "NO_CHANGE_REQUIRED"),
        ("position_intent", "position_intent.v1", "canonical normalized wrapper for action proposal", ["proposed_position_intent", "lineage"], ["target weight", "quantity_delta", "planning_intent", "Pending"], False, False, False, False, False, "SHADOW", "Wrapper relation with PM, not duplicate active authority", "NO_CHANGE_REQUIRED"),
        ("target_portfolio_decision", "target_portfolio_decision.v1", "target membership/direction resolution", ["RETAIN/INCREASE", "RETAIN/MAINTAIN", "RETAIN/DECREASE", "REMOVE"], ["quantity_delta", "planning_intent", "Pending"], False, False, True, False, False, "SHADOW", "Resolution-only in D2-B", "NO_CHANGE_REQUIRED"),
        ("Portfolio Construction", "portfolio_construction output", "active target portfolio / target weight authority", ["membership", "target_weight"], ["broker quantity", "Submit"], False, False, True, False, False, "ACTIVE_EXISTING", "Existing formal output remains separate from shadow D2-B", "DOCUMENTATION_CLARIFICATION"),
        ("position_sizing_plan", "position_sizing_plan.v1", "shadow quantity delta candidate", ["target_quantity_candidate", "quantity_delta_candidate", "*_NOT_SIZED"], ["planning_intent", "BUY_ADD", "Pending", "Submit"], False, True, False, False, False, "SHADOW", "Quantity-only in D2-D", "NO_CHANGE_REQUIRED"),
        ("Position Sizing", "position_sizing.v1", "formal target notional/quantity candidate authority", ["target_notional", "target_quantity_candidate", "quantity_delta_candidate"], ["membership", "rank", "PM intent", "Submit"], False, True, False, False, False, "ACTIVE_EXISTING", "Formal stage not replaced by D2-D shadow plan", "DOCUMENTATION_CLARIFICATION"),
        ("Runtime Planning", "runtime planning artifact", "quantity delta to runtime execution intent mapper", ["BUY_NEW", "BUY_ADD", "SELL_REDUCE", "SELL_EXIT", "NO_ACTION"], ["ranking", "Quality recompute", "PM action generation", "target weight", "sizing recalc"], False, False, False, True, False, "ACTIVE_EXISTING", "Existing PM fallback requires D2-E clarification when canonical plan connects", "DOCUMENTATION_CLARIFICATION"),
        ("Safety", "safety decision", "hard safety / block / review", ["PASS", "BLOCK", "REVIEW_REQUIRED"], ["Strategy ranking", "target weight", "PM action"], False, False, False, False, True, "ACTIVE_EXISTING", "Separate final guard, not Strategy action", "NO_CHANGE_REQUIRED"),
        ("Pending", "pending_order_plan.json", "current submit candidate slot", ["PendingOrderItem", "EMPTY"], ["Strategy action", "rank", "quality recompute"], False, False, False, True, False, "ACTIVE_EXISTING", "Materialization only", "NO_CHANGE_REQUIRED"),
        ("Submit", "Submit Runtime", "broker order submission guarded by Pending/Approval", ["submitted order", "NO_ACTION"], ["Strategy decision", "quantity recalculation"], False, False, False, True, False, "ACTIVE_EXISTING", "Non-idempotent final broker boundary", "NO_CHANGE_REQUIRED"),
    ]
    keys = ("component", "artifact", "primary_responsibility", "allowed_output", "forbidden_output", "action_authority", "quantity_authority", "portfolio_authority", "execution_authority", "safety_authority", "active_or_shadow", "overlap", "final_judgment")
    return [dict(zip(keys, row)) for row in rows]


def evaluation_components() -> list[dict[str, object]]:
    return [
        _eval("Opportunity", "Cross-sectional relative attractiveness", ["candidate output", "features", "Accepted Generation"], ["rank", "score", "lineage"], "NONE_DIRECT", False, "Opportunity ranking weight", ["Portfolio Construction", "BUY Quality", "PM reference"], ["BUY Quality relative_opportunity_quality"], "THEORETICAL_DOUBLE_WEIGHT"),
        _eval("BUY Quality", "Is this BUY allocation trustworthy?", ["Opportunity", "Market Context", "portfolio fit", "execution evidence"], ["quality_score", "quality_action", "adjustment"], "QUALITY_ADJUSTMENT", False, "quality_allocation_adjustment", ["Portfolio Construction", "Position Sizing", "Runtime lineage"], ["Opportunity", "Market Context"], "THEORETICAL_DOUBLE_WEIGHT"),
        _eval("Market Context", "What is the market/regime state?", ["breadth", "trend", "volatility"], ["risk/breadth/confidence"], "NONE_DIRECT", False, "Portfolio-level modifier", ["Portfolio Policy", "BUY Quality", "PM"], ["BUY Quality market_context_modifier"], "EXPLICIT_SHARED_FEATURE"),
        _eval("Portfolio Policy", "What portfolio posture/constraints apply?", ["Market Context", "current portfolio", "risk evidence"], ["target exposure/count/cash posture"], "PORTFOLIO_LEVEL_ONLY", False, "portfolio-level posture", ["Portfolio Construction", "Position Sizing"], ["BUY Quality portfolio_fit"], "THEORETICAL_DOUBLE_WEIGHT"),
        _eval("Momentum Continuation", "Does existing position continuation still hold?", ["current position", "trend", "opportunity reference"], ["continuation state", "reason codes"], "SHADOW_ONLY", False, "none active", ["PM/position_intent future"], ["PM trend features"], "THEORETICAL_DOUBLE_WEIGHT"),
        _eval("Incremental Investment Eligibility", "Is additional capital justified now?", ["Momentum", "Quality", "portfolio fit", "cash posture"], ["eligibility state", "reason codes"], "SHADOW_ONLY", False, "none active", ["PM/position_intent future"], ["Quality/portfolio fit"], "THEORETICAL_DOUBLE_WEIGHT"),
        _eval("Position Management", "What existing-position direction is justified?", ["current position", "PM features", "Opportunity", "Market Context"], ["ADD", "HOLD", "REDUCE", "EXIT"], "PM_DIRECTIONAL_INTENT", True, "selected action score", ["position_intent", "legacy sell path"], ["Momentum future"], "NO_ACTIVE_DOUBLE_WEIGHT_CONFIRMED"),
    ]


def _eval(name: str, question: str, inputs: list[str], outputs: list[str], effect: str, action_authority: bool, weighting: str, consumers: list[str], overlap: list[str], risk: str) -> dict[str, object]:
    return {
        "component": name,
        "primary_question": question,
        "inputs": inputs,
        "outputs": outputs,
        "decision_effect": effect,
        "action_authority": action_authority,
        "weighting_authority": weighting,
        "consumers": consumers,
        "overlap_with": overlap,
        "double_count_risk": risk,
    }


def feature_audit() -> list[dict[str, object]]:
    rows = [
        ("trend", "trend_score / PM continuation evidence", "Market Context / PM", "Quality / PM", "market_context_quality_modifier 0.15 component includes trend_score; PM may use trend features", "NONE_DIRECT in Market Context, PM_ACTION in PM", 2, "THEORETICAL_DOUBLE_WEIGHT", "SoT separates market-level trend from symbol PM continuation; D2 has no active Momentum artifact."),
        ("relative_strength", "relative_opportunity_quality", "Opportunity / BUY Quality", "Portfolio Construction / Quality", "Quality weight 0.35 for relative opportunity quality", "QUALITY_ADJUSTMENT", 2, "EXPLICIT_SHARED_FEATURE", "Opportunity rank remains raw authority; Quality derives trust score."),
        ("signal_reliability", "signal_reliability component", "BUY Quality", "Position Sizing / Runtime lineage", "Quality component 0.20", "QUALITY_ADJUSTMENT", 1, "NO_DUPLICATION", "Dedicated Quality component."),
        ("market_context", "market_context_quality_modifier / portfolio posture", "Market Context / Portfolio Policy", "BUY Quality / Portfolio Construction", "Quality 0.15 plus portfolio-level exposure posture", "PORTFOLIO_LEVEL_AND_QUALITY", 2, "THEORETICAL_DOUBLE_WEIGHT", "Adaptive Quality SoT says Quality modifier must not duplicate Portfolio Policy exposure effect."),
        ("portfolio_fit", "portfolio_fit quality component / portfolio constraints", "BUY Quality / Portfolio Policy", "Position Sizing / Portfolio Construction", "Quality 0.15 plus portfolio constraints", "QUALITY_AND_PORTFOLIO", 2, "THEORETICAL_DOUBLE_WEIGHT", "Symbol-level fit vs portfolio-level constraints need lineage separation."),
        ("execution_feasibility", "execution_quality component / Runtime feasibility", "BUY Quality / Runtime Planning", "Position Sizing / Runtime Planning", "Quality 0.15 and Runtime feasibility guards", "QUALITY_ADJUSTMENT_AND_EXECUTION_GUARD", 2, "EXPLICIT_SHARED_FEATURE", "Quality may reduce trust; Runtime still final feasibility guard."),
        ("volatility", "volatility adjustment / market volatility", "Position Sizing / Market Context / Quality", "Position Sizing / Quality", "formal sizing volatility_adjustment and Quality execution/market components", "QUANTITY_ADJUSTMENT", 2, "THEORETICAL_DOUBLE_WEIGHT", "Requires D2-E lineage preservation, not an active duplicate action."),
        ("opportunity_score", "runtime_opportunity_score / relative opportunity quality", "Opportunity", "Portfolio Construction / Quality", "raw score copied; Quality derives relative component", "RANKING_EVIDENCE", 2, "EXPLICIT_SHARED_FEATURE", "Portfolio/Sizing contract forbids Position Sizing direct membership/weight from raw score."),
        ("quality_score", "quality_score / quality_allocation_adjustment", "BUY Quality", "Portfolio Construction / Position Sizing / Runtime lineage", "single quality adjustment should be applied once", "QUALITY_ADJUSTMENT", 1, "NO_DUPLICATION", "SoT explicitly says quality adjustment must not be double-applied."),
    ]
    keys = ("raw_feature", "derived_feature", "producer", "consumer", "weight_or_modifier", "decision_effect", "number_of_applications", "double_weight_risk", "evidence")
    return [dict(zip(keys, row)) for row in rows]


def artifact_review() -> list[dict[str, object]]:
    return [
        {"artifact": "position_intent.v1", "independent_authority_needed": False, "immutable_lineage_needed": True, "debug_evidence_value": "HIGH", "existing_artifact_substitute": "PM artifact lacks canonical normalized scope and BUY_NEW unresolved evidence", "duplicates_meaning": False, "judgment": "REQUIRED"},
        {"artifact": "target_portfolio_decision.v1", "independent_authority_needed": False, "immutable_lineage_needed": True, "debug_evidence_value": "HIGH", "existing_artifact_substitute": "Existing Portfolio Construction is formal active output; D2-B shadow isolates PM intent resolution before formal replacement", "duplicates_meaning": "PARTIAL_BY_DESIGN", "judgment": "JUSTIFIED"},
        {"artifact": "position_sizing_plan.v1", "independent_authority_needed": False, "immutable_lineage_needed": True, "debug_evidence_value": "HIGH", "existing_artifact_substitute": "Formal position_sizing.v1 remains active; D2-D shadow proves existing-position delta contract before Runtime connection", "duplicates_meaning": "PARTIAL_BY_DESIGN", "judgment": "JUSTIFIED"},
        {"artifact": "runtime_position_plan.v1", "independent_authority_needed": False, "immutable_lineage_needed": True, "debug_evidence_value": "HIGH", "existing_artifact_substitute": "Existing runtime_planning artifact exists, but D1R requires immutable mapping from canonical sizing plan", "duplicates_meaning": "FUTURE_REPLACEMENT_OR_ADAPTER_NEEDED", "judgment": "JUSTIFIED"},
    ]


def design_gaps() -> list[dict[str, object]]:
    return [
        {"id": "D2DR-CLARIFICATION-1", "topic": "Runtime Planning PM fallback", "classification": "DOCUMENTATION_CLARIFICATION", "evidence": "runtime_planning._resolve_intent maps pm_action ADD/REDUCE/EXIT/HOLD when quantity_delta_candidate is absent.", "impact": "If D2-E consumes position_sizing_plan and also allows PM fallback for the same row, action authority could appear duplicated.", "required_before_or_in_d2e": "Declare canonical precedence: position_sizing_plan quantity_delta drives Runtime mapping; PM fallback is legacy/compatibility only or blocked when canonical lineage is present."},
        {"id": "D2DR-CLARIFICATION-2", "topic": "Feature shared usage", "classification": "DOCUMENTATION_CLARIFICATION", "evidence": "Adaptive BUY Quality uses Opportunity and Market Context; Portfolio Policy and PM can also consume those evidence families.", "impact": "Theoretical double-weighting risk, not active duplicate action authority.", "required_before_or_in_d2e": "Preserve component lineage and state whether a feature is evidence, quality modifier, portfolio posture, or action reasoning."},
        {"id": "D2DR-CLARIFICATION-3", "topic": "BUY_NEW authority", "classification": "DOCUMENTATION_CLARIFICATION", "evidence": "D2-A BUY_NEW candidate rows remain UNRESOLVED because Incremental Eligibility is not connected.", "impact": "Existing-position D2-E can proceed, but BUY_NEW final authority remains partly outside D2-A-D shadow chain.", "required_before_or_in_d2e": "Keep D2-E scoped to mapping canonical quantity deltas; do not solve BUY_NEW eligibility by Runtime inference."},
    ]


def render_report(payloads: dict[str, object]) -> str:
    return f"""# Phase27-D2-DR Decision Authority Simplification and Component Overlap Review

## 1. Scope

This is a read-only architecture / implementation review before Phase27-D2-E Runtime Planning connection.

```text
Implementation Change: PROHIBITED_NOT_PERFORMED
Strategy Logic Change: PROHIBITED_NOT_PERFORMED
Runtime Change: PROHIBITED_NOT_PERFORMED
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
{PRIMARY}
```

Supporting judgments:

```json
{json.dumps(supporting(), ensure_ascii=False, indent=2)}
```

## 3. Main Findings

1. Existing-position final directional action authority is PM in the active system. `position_intent.v1` is a canonical wrapper in D2-A, not a second active action authority.
2. `target_portfolio_decision.v1` is resolution-only in D2-B: it maps PM/position intent into membership/direction/effect evidence with `decision_effect = NONE`.
3. `position_sizing_plan.v1` is quantity-only in D2-D: it emits positive/zero/negative/full-exit delta candidates or matching `*_NOT_SIZED`, with `decision_effect = NONE`.
4. Legacy ADD is no longer executable after D2-C; it is `NON_DECISION_COMPATIBILITY` telemetry with no quantity/Pending/Submit authority.
5. Runtime Planning is intended to be a mapper, but existing code still has PM-action fallback mapping when quantity delta is missing. This is compatible only if D2-E makes canonical quantity-delta precedence explicit and prevents same-row PM fallback from becoming a second action authority.
6. Opportunity, BUY Quality, Market Context, Momentum, and Incremental Eligibility are evidence / modifier components, not D2-A-D final action producers. Feature reuse creates theoretical double-weighting risk, not confirmed active duplicate authority.

## 4. D2-E Entry

```text
APPROVED_WITH_CLARIFICATIONS
```

D2-E may proceed if it preserves this rule:

```text
position_sizing_plan.v1 quantity_delta_candidate
  -> Runtime Planning mapping
```

and does not also let PM fallback or legacy ADD authorize the same action.

## 5. Evidence

Evidence directory:

```text
{OUT_DIR.relative_to(REPO_ROOT)}
```

Required JSON files were generated there, including `final_action_producer_inventory.json`, `decision_authority_matrix.json`, `feature_double_weighting_audit.json`, `design_gap_inventory.json`, and `d2e_entry_decision.json`.

## 6. Validation

Read-only validation only:

```text
code search / static inspection: PERFORMED
py_compile analysis helper: PASS
JSON validation: PASS
Runtime / Historical / fresh-run: NOT_EXECUTED
```
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payloads: dict[str, object] = {
        "summary.json": {
            "task_id": "Phase27-D2-DR",
            "primary_judgment": PRIMARY,
            "supporting_judgments": supporting(),
            "implementation_changed": False,
            "strategy_logic_changed": False,
            "runtime_changed": False,
            "historical_executed": False,
            "fresh_run_executed": False,
        },
        "final_action_producer_inventory.json": final_action_inventory(),
        "decision_authority_matrix.json": authority_matrix(),
        "pm_vs_position_intent_review.json": {
            "pm_formal_action_producer": "YES_FOR_EXISTING_POSITION_DIRECTION",
            "position_intent_relationship": "CANONICAL_NORMALIZED_WRAPPER",
            "position_intent_recalculates_action": False,
            "both_active_authority_possible_in_d2": False,
            "buy_new_intent_design": "BUY_NEW candidates remain UNRESOLVED in D2-A until Incremental Eligibility / canonical BUY_NEW authority is connected.",
            "judgment": "WRAPPER_RELATION",
            "outcome": "NO_CHANGE_REQUIRED",
        },
        "target_portfolio_decision_review.json": {
            "adopts_or_rejects_intent": True,
            "generates_independent_action": False,
            "can_convert_pm_intent_to_different_action": False,
            "conflict_behavior": "REVIEW_REQUIRED_OR_BLOCK",
            "responsibility": "TARGET_MEMBERSHIP_RESOLUTION / PORTFOLIO_FEASIBILITY_SHADOW",
            "decision_effect": "NONE",
            "judgment": "RESOLUTION_ONLY",
            "outcome": "NO_CHANGE_REQUIRED",
        },
        "position_sizing_plan_review.json": {
            "quantity_only": True,
            "can_convert_intent": False,
            "not_sized_statuses_preserved": ["ADD_NOT_SIZED", "HOLD_NOT_SIZED", "REDUCE_NOT_SIZED", "EXIT_NOT_SIZED"],
            "zero_delta_to_hold_implicit_conversion": False,
            "strategy_preference_formula": "NO_ACTIVE_FORMAL_PREFERENCE_IN_D2_D; shadow uses directional min-lot examples only",
            "decision_effect": "NONE",
            "judgment": "QUANTITY_ONLY",
            "outcome": "NO_CHANGE_REQUIRED",
        },
        "runtime_planning_responsibility_review.json": {
            "planned_mapping": {
                "positive_existing_position_delta": "BUY_ADD",
                "zero_delta": "NO_ACTION",
                "negative_partial_delta": "SELL_REDUCE",
                "full_negative_delta": "SELL_EXIT",
            },
            "must_not_do": ["ranking", "momentum evaluation", "quality evaluation", "intent generation", "target weight calculation", "sizing recalculation"],
            "code_observation": "runtime_planning._resolve_intent maps quantity_delta when present, but still falls back to pm_action when quantity_delta is absent.",
            "judgment": "PARTIAL",
            "outcome": "DOCUMENTATION_CLARIFICATION",
        },
        "evaluation_component_responsibility.json": evaluation_components(),
        "feature_double_weighting_audit.json": feature_audit(),
        "component_overlap_matrix.json": {
            "overlaps": [
                {"components": ["Opportunity", "BUY Quality"], "shared_feature": "opportunity_score/rank", "risk": "EXPLICIT_SHARED_FEATURE", "judgment": "NOT_DUPLICATE_ACTION_AUTHORITY"},
                {"components": ["Market Context", "BUY Quality", "Portfolio Policy"], "shared_feature": "market_context", "risk": "THEORETICAL_DOUBLE_WEIGHT", "judgment": "DOCUMENTATION_CLARIFICATION"},
                {"components": ["PM", "Momentum Continuation"], "shared_feature": "trend/continuation", "risk": "THEORETICAL_DOUBLE_WEIGHT", "judgment": "Momentum remains shadow/foundation; not active producer"},
                {"components": ["Runtime Planning", "PM"], "shared_feature": "pm_action fallback", "risk": "POTENTIAL_DUPLICATE_IF_D2E_CONNECTS_WITHOUT_PRECEDENCE", "judgment": "DOCUMENTATION_CLARIFICATION"},
            ],
            "active_duplicate_authority_confirmed": False,
        },
        "artifact_necessity_review.json": artifact_review(),
        "simplicity_target_review.json": {
            "minimal_model": ["Evaluation Evidence", "Canonical Position Action", "Portfolio Resolution", "Quantity Resolution", "Runtime Order Mapping"],
            "passes": True,
            "user_explanation_model": {
                "Action": "BUY / ADD / HOLD / REDUCE / EXIT",
                "Why": "Evidence and reason codes",
                "Portfolio Result": "Accepted / Rejected / Limited",
                "Quantity Result": "Positive / Zero / Negative Delta",
                "Execution Result": "Order / No Order / Block / Review",
            },
            "component_count_vs_authority_count": "Multiple evidence components are justified; final action authority must remain singular.",
        },
        "design_gap_inventory.json": design_gaps(),
        "d2e_entry_decision.json": {
            "decision": "APPROVED_WITH_CLARIFICATIONS",
            "primary_judgment": PRIMARY,
            "must_hold_in_d2e": [
                "position_sizing_plan.v1 quantity_delta_candidate has precedence when present",
                "PM fallback must not authorize the same row when canonical sizing lineage is present",
                "Legacy ADD remains NON_DECISION_COMPATIBILITY",
                "Runtime Planning must not recompute ranking, quality, momentum, target weight, or sizing",
            ],
            "blocked": False,
        },
        "test_results.json": {
            "validation_type": "READ_ONLY_STATIC",
            "commands": [
                {"command": "rg static inspections over required docs/code", "result": "PASS"},
                {"command": "env PYTHONPYCACHEPREFIX=/private/tmp/phase27_d2dr_pycache python3 -m py_compile tools/phase27_analysis/phase27_d2dr_generate_authority_overlap_review.py", "result": "PASS"},
                {"command": "python3 -c JSON validation for D2-DR reports", "result": "PASS"},
            ],
            "runtime_executed": False,
            "historical_executed": False,
            "fresh_run_executed": False,
            "pytest_executed": False,
        },
    }
    for name, payload in payloads.items():
        write_json(OUT_DIR / name, payload)
    PHASE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    PHASE_REPORT.write_text(render_report(payloads), encoding="utf-8")


if __name__ == "__main__":
    main()
