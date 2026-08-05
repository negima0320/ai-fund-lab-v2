# Phase27-A9 — Canonical BUY_ADD Authority Unification and Legacy Consumer Disposition Design Review

## Scope

This is a read-only Architecture / Contract Design Review. No Runtime, Strategy, PM, Portfolio Construction, Position Sizing, Runtime Planning, `add_consumer`, `sell_pipeline`, Pending, Submit, or Safety logic was modified. No fresh-run, resume, Historical run, 100BD, 1-year, or long regression was executed.

## Primary Judgment

`PHASE27_A9_BUY_ADD_AUTHORITY_CONTRACT_GAP_CONFIRMED_REPAIR_REQUIRED`

Supporting judgments:

- Canonical BUY_ADD Path: `PARTIAL`
- Legacy ADD Consumer: `ACTIVE`
- Double-authority Risk: `THEORETICAL`
- Architecture Repair: `REQUIRED`
- Performance Design: `DEFERRED_TO_PHASE27_B`

## Core Conclusion

Production Architecture defines a conditional BUY_ADD path, but it is not cleanly unified in the current architecture and implementation evidence.

Canonical contract:

```text
Existing Position
  -> PM ADD / HOLD / REDUCE / EXIT intent
  -> Portfolio Construction target membership / target weight
  -> Position Sizing target notional / target quantity / quantity delta
  -> Runtime Planning BUY_ADD if existing-position quantity_delta_candidate > 0
  -> Strategy Planning Authority
  -> Pending
  -> Approval
  -> Submit
  -> Execution
```

PM ADD is not itself a BUY order. Quantity and executable BUY_ADD are downstream authorities.

## A7 / A8 Evidence

Observed in A7:

- Existing-position rows: 364
- PM ADD: 145
- Planning BUY_ADD: 0
- Executable ADD: 0
- Planning NO_ACTION: 364 / 364

Observed in A9 Portfolio Construction inspection:

- Strategy Portfolio Construction artifact statuses: `{'DRAFT/NOT_ELIGIBLE/PASS': 100}`
- PM rows seen by Portfolio Construction: `{'UNRESOLVED/UNRESOLVED/UNRESOLVED': 364}`
- Runtime PM ADD observed as Portfolio Construction ADD/RETAIN/INCREASE: `0`

This means the A7 run's Runtime PM ADD decisions did not reach canonical Portfolio Construction as ADD.

## Authority Ownership

- PM ADD Intent: Position Management
- Portfolio Membership: Portfolio Construction
- Target Weight: Portfolio Construction
- Target Notional: Position Sizing
- Target Quantity: Position Sizing
- Quantity Delta: Position Sizing
- BUY_ADD Planning Intent: Runtime Planning
- Pending Generation: Strategy Planning Authority / Pending Materialization
- Submit Permission: Approval + Submit Guard + Safety
- Execution: Broker / Execution

See `decision_authority_matrix.json` for the full matrix.

## PM ADD To Portfolio Construction

Code-level contract exists:

- `portfolio_construction.py` reads PM rows from the position management artifact.
- `ADD` maps to `RETAIN / INCREASE`.
- `HOLD` maps to `RETAIN / MAINTAIN`.

Observed runtime contract is not proven:

- A7 run had 145 Runtime PM ADD decisions.
- Portfolio Construction observed 0 `ADD / RETAIN / INCREASE` PM rows.
- Portfolio Construction observed 364 `UNRESOLVED / UNRESOLVED / UNRESOLVED` PM rows.

Judgment:

`DEFINED_IN_CODE_BUT_NOT_PROVEN_CONNECTED_TO_RUNTIME_PM_ADD`

## Existing-position Positive Delta

The positive delta contract exists:

- `target_quantity_candidate` is total desired holding candidate from Position Sizing.
- `quantity_delta_candidate` is target quantity minus current quantity.
- Runtime Planning maps positive delta on an already-held symbol to `BUY_ADD`.
- Runtime Planning maps zero current-position delta to `NO_ACTION`.

A7's 0 executable ADD is therefore contract-explainable for the zero-delta Planning result, but not sufficient to prove PM ADD is correctly connected to the canonical PM -> Portfolio Construction edge.

## Legacy ADD Consumer

Legacy path:

```text
sell_pipeline
  -> add_consumer
  -> pm_add_order_plan.json
  -> pending_order_plan.json
  -> approval
  -> submit
```

Disposition:

`DEPRECATED_BUT_ACTIVE`

Why:

- It is not dead code: code and Phase23 tests/reports show it can produce BUY Pending items with `source_decision_type=ADD`.
- It is not observability-only: it can write `pm_add_order_plan.json`, approval, and pending artifacts.
- It is not cleanly canonical under current Strategy SoT, which defines BUY_ADD through Portfolio Construction / Position Sizing / Runtime Planning.

## Double-authority Risk

Risk classification:

`THEORETICAL_RISK`

If canonical Runtime Planning emits BUY_ADD and legacy `add_consumer` also accepts PM ADD for the same business date/symbol/campaign, both paths can target BUY Pending generation. A7 did not observe this, and Submit/Pending guards may stop some duplicated states, but A9 did not find an explicit canonical-vs-legacy mutual exclusion contract.

## Production / Demo / Historical

Mode review judgment:

`PRODUCTION_COMMON_INTENT_CONFIRMED_FOR_CONTRACT; FULL_MODE_PARITY_FOR_BUY_ADD_NOT_PROVEN_BY_A7_RUN`

No historical-only ADD producer was found in the reviewed files. Phase23-BS describes the repaired PM ADD pending policy propagation as Production / Demo / Historical common. Demo broker capability may differ, but that is separate from BUY_ADD authority.

## Architecture vs Performance

Architecture / Contract:

- ADD Producer / Consumer responsibility
- Canonical path
- Legacy path disposition
- Quantity Authority
- Pending / Submit Authority
- Mode parity
- Double-authority prevention

Performance Design, deferred to Phase27-B:

- when to ADD
- ADD amount
- momentum conditions
- HOLD vs ADD boundary
- concentration thresholds
- Rank / Quality / Market Context conditions

## Repair Scope

Architecture Repair is required, but A9 does not propose implementation details or Performance Design.

Minimum responsibility scope:

- Declare one canonical BUY_ADD producer/consumer chain.
- Classify legacy `add_consumer` / `sell_pipeline` ADD path as retired, compatibility-only, or canonical adapter.
- Define explicit mutual exclusion / deduplication authority if legacy path remains callable.
- Clarify which PM ADD artifact Portfolio Construction consumes.
- Preserve separation: PM owns intent, Portfolio Construction owns target portfolio, Position Sizing owns quantity delta, Runtime Planning owns BUY_ADD mapping.

## Deliverables

- `summary.json`
- `decision_authority_matrix.json`
- `canonical_buy_add_contract.json`
- `canonical_buy_add_contract_graph.json`
- `pm_add_to_portfolio_construction_edge.json`
- `existing_position_positive_delta_contract.json`
- `legacy_add_consumer_inventory.json`
- `legacy_add_consumer_disposition.json`
- `double_authority_risk_review.json`
- `production_common_mode_review.json`
- `architecture_performance_boundary.json`
- `architecture_gap_inventory.json`
- `recommended_repair_scope.json`
- `test_results.json`
