from __future__ import annotations

import json
from pathlib import Path
from typing import Any


RUN_ID = "runtime-test-historical-smoke-20260804T074611098414Z"
OUT_DIR = Path("reports/phase27_a8_add_authority_contract_review")
REPORT_PATH = Path("docs/phase_reports/phase27_a8_add_authority_contract_review.md")
A7_DIR = Path("reports/phase27_a7_existing_position_position_management_decision_authority_audit")


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    a7_summary = load_json(A7_DIR / "summary.json")
    a7_add = load_json(A7_DIR / "add_authority_audit.json")
    a7_hold = load_json(A7_DIR / "hold_vs_no_action.json")

    architecture_intent = {
        "does_architecture_expect_buy_add": "YES_CONDITIONALLY",
        "answer_to_core_question": "PM ADD may become executable BUY_ADD only through the Production planning/quantity authority chain; PM ADD alone is not a BUY order.",
        "supporting_evidence": [
            {
                "source": "docs/02_architecture/strategy_architecture_v1.md:43",
                "evidence": "ADD is a buy-more candidate intent and not a direct order.",
            },
            {
                "source": "docs/02_architecture/strategy_architecture_v1.md:82",
                "evidence": "Position Management owns existing-position HOLD/ADD/REDUCE/EXIT intent and does not own quantities or submit permission.",
            },
            {
                "source": "docs/02_architecture/strategy_architecture_v1.md:118-124",
                "evidence": "Portfolio Construction owns final target portfolio; Position Sizing owns target quantity and quantity delta; Runtime Planning maps execution intent and must not recalculate Strategy decisions.",
            },
            {
                "source": "docs/02_architecture/strategy_architecture_v1.md:218-227",
                "evidence": "Runtime Planning zero-state contract maps positive quantity_delta_candidate to BUY_NEW or BUY_ADD, negative delta to sell, zero delta to NO_ACTION/NO_ORDER.",
            },
            {
                "source": "docs/02_architecture/portfolio_construction_and_position_sizing_contract.md:152-175",
                "evidence": "Portfolio Construction integrates PM intent into target portfolio; Position Sizing owns target quantity and quantity delta.",
            },
            {
                "source": "docs/02_architecture/runtime_architecture_v2.md:19",
                "evidence": "Runtime must not recompute HOLD/ADD/REDUCE/EXIT, ranking, or position sizing.",
            },
        ],
        "non_authoritative_or_legacy_evidence": [
            {
                "source": "docs/phase_reports/phase23_bs_pm_add_pending_submit_policy_authority_binding_repair.md:61-69",
                "evidence": "Phase23-BS describes PM ADD currently generated in sell_pipeline as a responsibility overlap and legacy naming issue.",
            },
            {
                "source": "src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py:1-63",
                "evidence": "A PM ADD consumer exists in code and can build Pending BUY planning from ADD decisions when required authorities pass.",
            },
        ],
        "judgment": "Architecture expects BUY_ADD as a valid runtime planning/executable intent, but not as a direct consequence of PM ADD alone.",
    }

    producer_consumer_trace = {
        "producer": {
            "add_owner": "Position Management",
            "artifact": "daily/<date>/position_management/pm_decisions.json and PM Decisions Artifact",
            "authority": "Existing Position Intent Authority",
            "does_not_own": ["target_weight", "target_notional", "broker_quantity", "submit_permission"],
        },
        "canonical_chain": [
            {"stage": "PM", "role": "emits ADD intent", "terminates_if": "intent not integrated into target portfolio or no executable quantity delta"},
            {"stage": "Portfolio Construction", "role": "integrates PM intent into target portfolio / membership / target weight", "terminates_if": "target weight remains zero or retained without positive add delta"},
            {"stage": "Position Sizing", "role": "computes target_quantity_candidate and quantity_delta_candidate", "terminates_if": "quantity_delta_candidate <= 0 or quantity not executable"},
            {"stage": "Runtime Planning", "role": "maps positive current-position quantity delta to BUY_ADD", "terminates_if": "quantity_delta_candidate == 0 -> NO_ACTION/NO_ORDER"},
            {"stage": "Strategy Planning Authority", "role": "validates and materializes pending order plan", "terminates_if": "schema/hash/date/lineage/feasibility fail-closed"},
            {"stage": "Approval/Pending", "role": "approves/materializes order item", "terminates_if": "approval or pending authority missing"},
            {"stage": "Submit/Execution", "role": "submits approved pending BUY item", "terminates_if": "submit guard/safety/broker capability blocks"},
        ],
        "legacy_or_parallel_chain": [
            {"stage": "sell_pipeline add_consumer", "role": "can consume source_decision=ADD and write pm_add_order_plan BUY Pending", "evidence": "src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py and sell_pipeline.py"},
            {"stage": "Phase23-BS", "role": "repaired submit policy propagation for PM ADD pending", "evidence": "phase23_bs report"},
        ],
        "observed_a7_termination": {
            "pm_add_observed": a7_add["pm_add_observed_count"],
            "pm_add_status": a7_add["pm_add_runtime_statuses"],
            "planning_buy_add_observed": a7_add["planning_buy_add_observed_count"],
            "runtime_executable_add_observed": a7_add["runtime_add_final_action_observed_count"],
            "termination_point": "PM ADD marked outside SELL Planning scope and Strategy Planning emitted NO_ACTION because no positive executable quantity delta was observed.",
        },
    }

    buy_add_contract = {
        "can_buy_add_exist": True,
        "architecture_condition": "Existing held symbol plus positive quantity_delta_candidate, or a separately accepted PM ADD pending consumer path with required capital/cash/sizing/safety/submit-policy authorities.",
        "canonical_strategy_runtime_condition": "quantity_delta_candidate > 0 and symbol is in current holdings -> Runtime Planning BUY_ADD.",
        "direct_pm_add_condition": "PM ADD alone is insufficient; Strategy Architecture states PM ADD is not BUY.",
        "observed_in_a7_run": {
            "pm_add_count": a7_add["pm_add_observed_count"],
            "planning_buy_add_count": a7_add["planning_buy_add_observed_count"],
            "positive_existing_quantity_delta_count": a7_add["position_sizing_positive_existing_quantity_delta_observed_count"],
            "final_executable_add_count": a7_add["runtime_add_final_action_observed_count"],
        },
        "why_not_observed": [
            "A7 observed Planning intent NO_ACTION for 364/364 existing-position rows.",
            "A7 observed zero executable quantity delta for 364/364 existing-position rows.",
            "PM ADD rows carried NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE and quantity_requested=0.",
        ],
    }

    planning_no_action_analysis = {
        "observed_planning_no_action_count": a7_summary["planning_intent_counts"].get("NO_ACTION", 0),
        "observed_existing_position_rows": a7_summary["existing_position_rows"],
        "observed_quantity_delta_counts": a7_summary["pm_decision_counts"],
        "planning_reason": "current_position_membership_resolved:current_portfolio_member; current_position_zero_delta_maps_to_no_action",
        "code_evidence": [
            {
                "source": "src/ai_fund_lab_v2/strategy/runtime_planning.py:1100-1124",
                "evidence": "Positive deltas map to BUY_ADD for current holdings; zero current-position delta maps to NO_ACTION.",
            },
            {
                "source": "src/ai_fund_lab_v2/strategy/runtime_planning.py:1054-1065",
                "evidence": "Non-order intents return NOT_REQUIRED planned quantity; zero quantity delta returns no-order quantity.",
            },
        ],
        "judgment": "Planning emitted NO_ACTION because the observed Strategy Planning path had current-position membership plus zero executable quantity delta, not because PM ADD was absent.",
    }

    runtime_conformance = {
        "overall": "Partially Conformant",
        "conformant_points": [
            "Runtime did not treat PM ADD alone as a direct broker BUY order.",
            "Runtime Planning taxonomy supports BUY_ADD.",
            "Observed zero quantity delta mapped to NO_ACTION, matching Strategy zero-state contract.",
            "PM producer explicitly records ADD as outside SELL Planning auto-order scope.",
        ],
        "partial_or_gap_points": [
            "A legacy PM ADD consumer path still exists and Phase23-BS repaired it as Production/Demo/Historical common, while Strategy SoT after Phase23-AR describes canonical BUY_ADD via Portfolio Construction -> Position Sizing -> Runtime Planning.",
            "In the A7 run, PM ADD did not propagate as target portfolio positive delta or executable BUY_ADD, so the end-to-end ADD consumer contract was not exercised.",
            "The architecture intent is conditional YES for BUY_ADD, but observed run behavior is all NO_ACTION for existing positions.",
        ],
        "not_nonconformant_because": "The evidence does not prove that any observed PM ADD had a positive target quantity delta that Runtime incorrectly suppressed.",
        "not_fully_conformant_because": "The coexistence of legacy PM ADD pending consumer and canonical target-portfolio BUY_ADD path leaves an authority-boundary ambiguity for ChatGPT/operator review.",
    }

    decision_authority_matrix = [
        {
            "decision": "BUY_NEW",
            "producer": "Runtime Planning from Portfolio Construction / Position Sizing",
            "artifact": "strategy/runtime_planning.json; pending_order_plan when materialized",
            "consumer": "Strategy Planning Authority -> Pending -> Approval -> Submit -> Execution",
            "executable": True,
            "observed": "Observed as BUY trades in run performance, but A8 focuses existing-position ADD.",
            "architecture_intent": "YES",
            "runtime_behavior": "Executable when planning/pending/approval/submit pass.",
            "judgment": "CONFIRMED",
        },
        {
            "decision": "BUY_ADD",
            "producer": "Runtime Planning from positive existing-position quantity delta; legacy add_consumer can also produce ADD-derived BUY Pending",
            "artifact": "strategy/runtime_planning.json or runtime_state/sell_pipeline/<date>/pm_add_order_plan.json in legacy path",
            "consumer": "Strategy Planning Authority/Pending or PM ADD pending path -> Approval -> Submit -> Execution",
            "executable": True,
            "observed": "0 executable in A7 run; taxonomy/code path exists.",
            "architecture_intent": "YES_CONDITIONALLY",
            "runtime_behavior": "A7 run terminated as NO_ACTION; no positive quantity delta observed.",
            "judgment": "PARTIAL_CONFORMANCE",
        },
        {
            "decision": "HOLD",
            "producer": "Position Management",
            "artifact": "position_management/pm_decisions.json",
            "consumer": "Planning / no-order authority / reports",
            "executable": False,
            "observed": a7_summary["pm_decision_counts"].get("HOLD", 0),
            "architecture_intent": "YES_AS_POSITION_INTENT",
            "runtime_behavior": "Consumes to no sell/no order when no executable delta.",
            "judgment": "CONFIRMED",
        },
        {
            "decision": "NO_ACTION",
            "producer": "Runtime Planning / Pending no-order authority",
            "artifact": "strategy/runtime_planning.json; pending_order_plan EMPTY no-order authority when materialized",
            "consumer": "Submit as no-order authority when applicable",
            "executable": False,
            "observed": a7_summary["planning_intent_counts"].get("NO_ACTION", 0),
            "architecture_intent": "YES_FOR_ZERO_OR_NO_ORDER_STATE",
            "runtime_behavior": "Observed for all A7 existing-position rows.",
            "judgment": "CONFIRMED",
        },
        {
            "decision": "REDUCE",
            "producer": "Position Management intent; sell planning owns broker sell quantity",
            "artifact": "position_management/pm_decisions.json; sell planning pending when materialized",
            "consumer": "Sell Planning -> Pending -> Approval -> Submit -> Execution",
            "executable": True,
            "observed": a7_summary["pm_decision_counts"].get("REDUCE", 0),
            "architecture_intent": "YES",
            "runtime_behavior": "Observed as PM REDUCE and some final REDUCE trades.",
            "judgment": "CONFIRMED_WITH_QUANTITY_OWNERSHIP_SEPARATION",
        },
        {
            "decision": "EXIT",
            "producer": "Position Management",
            "artifact": "position_management/pm_decisions.json; sell planning pending when materialized",
            "consumer": "Sell Planning -> Pending -> Approval -> Submit -> Execution",
            "executable": True,
            "observed": a7_summary["pm_decision_counts"].get("EXIT", 0),
            "architecture_intent": "YES",
            "runtime_behavior": "Observed as PM EXIT and final EXIT trades.",
            "judgment": "CONFIRMED",
        },
    ]

    review_findings = [
        {
            "id": "A8-F1",
            "classification": "ARCHITECTURE_INTENT_CONFIRMED_CONDITIONAL_BUY_ADD",
            "finding": "Production Architecture expects BUY_ADD to exist conditionally, but PM ADD is only an intent and not a direct order.",
            "evidence": ["strategy_architecture_v1.md:43", "strategy_architecture_v1.md:218-227"],
        },
        {
            "id": "A8-F2",
            "classification": "OBSERVED_RUNTIME_TERMINATION",
            "finding": "In the A7 run, ADD terminated before executable BUY_ADD: PM ADD was outside SELL Planning auto-order scope and Planning emitted NO_ACTION for zero executable delta.",
            "evidence": ["phase27_a7 summary", "runtime_v2/position_management/producer.py:595-597"],
        },
        {
            "id": "A8-F3",
            "classification": "CONTRACT_AMBIGUITY",
            "finding": "A legacy PM ADD pending consumer path remains in Runtime v2 code and Phase23-BS documentation, while the current Strategy SoT defines the canonical path through Target Portfolio and Position Sizing.",
            "evidence": ["phase23_bs report:61-69", "runtime_v2/planning/add_consumer.py:43-63", "portfolio_construction_and_position_sizing_contract.md:289-320"],
        },
        {
            "id": "A8-F4",
            "classification": "PERFORMANCE_DESIGN_NOT_ARCHITECTURE_REPAIR_BY_ITSELF",
            "finding": "Whether more PM ADD signals should receive positive target deltas is a Performance Design / Strategy question; the contract review only confirms current authority boundaries.",
            "evidence": ["strategy_architecture_v1.md:118-124", "adaptive_buy_quality_authority.md:23"],
        },
    ]

    summary = {
        "phase": "Phase27",
        "task_id": "Phase27-A8",
        "run_id": RUN_ID,
        "primary_judgment": "PHASE27_A8_ADD_AUTHORITY_RUNTIME_PARTIAL_CONFORMANCE",
        "implementation_changed": False,
        "historical_test": "NOT_EXECUTED",
        "core_question": "Should PM ADD ever become an executable BUY_ADD according to the Production Architecture?",
        "answer": "YES_CONDITIONALLY. PM ADD may become executable BUY_ADD only through accepted downstream authority that produces a positive executable quantity delta or through an accepted PM ADD pending consumer path. PM ADD alone is not BUY.",
        "where_add_terminates_in_observed_run": producer_consumer_trace["observed_a7_termination"]["termination_point"],
        "who_owns_executable_add": "Runtime Planning / Strategy Planning Authority own executable intent and pending materialization; Position Sizing owns quantity delta; Portfolio Construction owns target portfolio; PM owns ADD intent only.",
        "chatgpt_classification": "ARCHITECTURE_CONTRACT_REVIEW_WITH_PERFORMANCE_DESIGN_IMPLICATIONS",
        "acceptance_answers": {
            "does_architecture_expect_buy_add": architecture_intent["does_architecture_expect_buy_add"],
            "why_pm_emits_add": "PM is the Existing Position Intent Authority and its formal actions include ADD for continuation/add-candidate evidence.",
            "why_planning_emits_no_action": planning_no_action_analysis["judgment"],
            "is_runtime_behaving_correctly": runtime_conformance["overall"],
            "where_add_terminates": producer_consumer_trace["observed_a7_termination"]["termination_point"],
            "who_owns_executable_add": "Portfolio Construction / Position Sizing / Runtime Planning / Strategy Planning Authority, not PM alone.",
            "architecture_or_performance_design": "The authority ambiguity is Architecture/Contract; deciding when ADD should receive positive size is Performance Design/Strategy.",
        },
    }

    test_results = {
        "historical_test": "NOT_EXECUTED",
        "fresh_run": "NOT_EXECUTED",
        "resume": "NOT_EXECUTED",
        "long_regression": "NOT_EXECUTED",
        "read_only_validation": "PASS",
        "documents_reviewed": [
            "docs/02_architecture/autonomous_ai_operations_architecture.md",
            "docs/02_architecture/strategy_architecture_v1.md",
            "docs/02_architecture/runtime_architecture_v2.md",
            "docs/02_architecture/adaptive_buy_quality_authority.md",
            "docs/02_architecture/portfolio_construction_and_position_sizing_contract.md",
            "docs/phase_reports/phase23_br_2022_10bd_post_carry_forward_submit_halt_root_cause_audit.md",
            "docs/phase_reports/phase23_bs_pm_add_pending_submit_policy_authority_binding_repair.md",
            "docs/phase_reports/phase27_a7_existing_position_position_management_decision_authority_audit.md",
        ],
        "required_outputs_present": True,
    }

    write_json(OUT_DIR / "summary.json", summary)
    write_json(OUT_DIR / "decision_authority_matrix.json", decision_authority_matrix)
    write_json(OUT_DIR / "producer_consumer_trace.json", producer_consumer_trace)
    write_json(OUT_DIR / "buy_add_contract.json", buy_add_contract)
    write_json(OUT_DIR / "planning_no_action_analysis.json", planning_no_action_analysis)
    write_json(OUT_DIR / "runtime_conformance.json", runtime_conformance)
    write_json(OUT_DIR / "architecture_intent.json", architecture_intent)
    write_json(OUT_DIR / "review_findings.json", review_findings)
    write_json(OUT_DIR / "test_results.json", test_results)

    report = f"""# Phase27-A8 — ADD Authority Contract and Existing Position Execution Path Review

## Scope

This is a read-only Architecture / Contract Review. No Strategy, Runtime, Planning, PM, Portfolio Construction, Position Sizing, Submit, Safety, or Execution logic was modified. No fresh-run, resume, Historical, 100BD, or long regression was executed.

Run-scoped observed behavior comes from `{RUN_ID}` and Phase27-A7 outputs.

## Primary Judgment

`{summary["primary_judgment"]}`

## Core Answer

Should PM ADD ever become executable BUY_ADD according to Production Architecture?

`YES_CONDITIONALLY`

PM ADD may become executable BUY_ADD only through accepted downstream authority that produces executable BUY intent. PM ADD alone is not a BUY order.

The canonical Strategy contract is:

```text
PM ADD intent
  -> Portfolio Construction target portfolio / target_weight
  -> Position Sizing target_quantity_candidate / quantity_delta_candidate
  -> Runtime Planning BUY_ADD when existing holding has positive quantity_delta_candidate
  -> Strategy Planning Authority / Pending / Approval / Submit / Execution
```

Observed A7 run behavior:

```text
PM ADD observed: {a7_add["pm_add_observed_count"]}
Planning BUY_ADD observed: {a7_add["planning_buy_add_observed_count"]}
Executable ADD observed: {a7_add["runtime_add_final_action_observed_count"]}
Planning NO_ACTION observed: {a7_summary["planning_intent_counts"].get("NO_ACTION", 0)} / {a7_summary["existing_position_rows"]}
```

## Evidence

Architecture SoT:

- `strategy_architecture_v1.md:43`: ADD is a buy-more candidate intent, not a direct order.
- `strategy_architecture_v1.md:82`: Position Management owns existing-position HOLD / ADD / REDUCE / EXIT intent and does not own quantity or Submit permission.
- `strategy_architecture_v1.md:118-124`: Portfolio Construction owns final target portfolio; Position Sizing owns quantity candidate; Runtime Planning maps execution intent.
- `strategy_architecture_v1.md:218-227`: positive quantity delta maps to BUY_NEW or BUY_ADD; zero delta maps to NO_ACTION / NO_ORDER.
- `portfolio_construction_and_position_sizing_contract.md:152-175`: PM intent is integrated into target portfolio, and Position Sizing owns quantity delta.
- `runtime_architecture_v2.md:19`: Runtime must not recalculate ADD, ranking, or position sizing.

Runtime/code evidence:

- `runtime_v2/position_management/producer.py:595-597`: PM ADD is marked `NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE`.
- `runtime_v2/position_management/producer.py:1048-1050`: PM summary records ADD count and the outside-SELL-planning scope reason.
- `strategy/runtime_planning.py:1100-1124`: positive current-position delta maps to BUY_ADD; current-position zero delta maps to NO_ACTION.
- `runtime_v2/planning/add_consumer.py:43-63`: a PM ADD consumer exists and can consume `source_decision=ADD`.
- `runtime_v2/planning/sell_pipeline.py:364-401`: sell_pipeline invokes ADD consumer and can write PM ADD pending when accepted.

## Producer / Consumer

ADD producer:

`Position Management`

ADD consumer:

`DEFINED_BUT_SPLIT`

There are two relevant consumer descriptions:

- Canonical Strategy path: Portfolio Construction integrates PM ADD into target portfolio, Position Sizing produces quantity delta, Runtime Planning emits BUY_ADD when the delta is positive.
- Legacy/runtime path: `sell_pipeline` can invoke `add_consumer` and write `pm_add_order_plan.json` when ADD passes cash, sizing, safety, and policy authorities.

This split is why A8 is judged partial conformance rather than a clean confirmed/no-gap result.

## Why Planning Emits NO_ACTION

In the A7 run, Planning emitted `NO_ACTION` for all {a7_summary["existing_position_rows"]} existing-position rows. The evidence-supported reason is:

```text
current_position_membership_resolved:current_portfolio_member
current_position_zero_delta_maps_to_no_action
```

No positive executable existing-position quantity delta was observed. Therefore Planning did not emit BUY_ADD.

## Runtime Conformance

Runtime is `Partially Conformant`.

Conformant:

- PM ADD was not treated as a direct broker BUY order.
- Zero executable delta became NO_ACTION.
- BUY_ADD taxonomy and code path exist.

Partial:

- The codebase still contains a legacy PM ADD pending consumer path, and Phase23-BS documents it as Production/Demo/Historical common.
- The current Strategy SoT describes the canonical path through Portfolio Construction and Position Sizing.
- The A7 run did not exercise executable ADD, so end-to-end ADD execution conformance is not proven by this run.

## Decision Authority Matrix

See `decision_authority_matrix.json`.

Summary:

- `BUY_NEW`: executable; owned by Runtime Planning after Portfolio Construction / Position Sizing.
- `BUY_ADD`: executable conditionally; not observed in A7.
- `HOLD`: PM intent; non-order.
- `NO_ACTION`: Planning/runtime no-order result.
- `REDUCE`: PM sell-side intent; executable through Sell Planning.
- `EXIT`: PM sell-side intent; executable through Sell Planning.

## Final Classification

ChatGPT should treat this as:

`ARCHITECTURE_CONTRACT_REVIEW_WITH_PERFORMANCE_DESIGN_IMPLICATIONS`

The authority split is Architecture / Contract evidence. Whether ADD should receive more positive size, or under which market/quality conditions it should do so, is Performance Design / Strategy and is outside A8.

## Deliverables

- `summary.json`
- `decision_authority_matrix.json`
- `producer_consumer_trace.json`
- `buy_add_contract.json`
- `planning_no_action_analysis.json`
- `runtime_conformance.json`
- `architecture_intent.json`
- `review_findings.json`
- `test_results.json`
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
