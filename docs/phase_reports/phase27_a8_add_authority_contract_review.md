# Phase27-A8 — ADD Authority Contract and Existing Position Execution Path Review

## Scope

This is a read-only Architecture / Contract Review. No Strategy, Runtime, Planning, PM, Portfolio Construction, Position Sizing, Submit, Safety, or Execution logic was modified. No fresh-run, resume, Historical, 100BD, or long regression was executed.

Run-scoped observed behavior comes from `runtime-test-historical-smoke-20260804T074611098414Z` and Phase27-A7 outputs.

## Primary Judgment

`PHASE27_A8_ADD_AUTHORITY_RUNTIME_PARTIAL_CONFORMANCE`

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
PM ADD observed: 145
Planning BUY_ADD observed: 0
Executable ADD observed: 0
Planning NO_ACTION observed: 364 / 364
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

In the A7 run, Planning emitted `NO_ACTION` for all 364 existing-position rows. The evidence-supported reason is:

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
