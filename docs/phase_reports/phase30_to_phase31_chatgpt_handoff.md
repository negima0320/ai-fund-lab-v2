# Phase30 to Phase31 ChatGPT Handoff

## Start Here

Read in this order:

1. `docs/phase_reports/phase30_to_phase31_chatgpt_handoff.md`
2. `docs/phase_reports/phase30_final_summary_and_phase31_handoff.md`
3. `docs/01_requirements/phase_roadmap.md`
4. `docs/phase_reports/phase30_ak9r31_real_orchestration_conformance_final_architecture_gate.md`
5. `docs/phase_reports/phase30_ak9r32_fresh_25bd_close_review_required_acceptance_audit.md`
6. `docs/phase_reports/phase30_ak9r27_central_pending_review_scope_authority_contract_repair.md`
7. `docs/phase_reports/phase30_ak9r28_historical_safety_temporal_authority_consumer_centralization.md`
8. `docs/phase_reports/phase30_ak9r29_runtime_system_guard_taxonomy_review_reason_normalization.md`

## System Purpose

This repository is a Japanese-stock AI-assisted automated trading system.

Core operating assumptions:

- initial capital: `1,000,000 JPY`
- asset class: cash equities only
- Strategy and Runtime must be Production-common across Production, Demo, and
  Historical
- long-term goal: aggressive but evidence-driven return improvement
- annual `+50%` remains aspirational, not assumed achieved

## Current Phase

```text
CURRENT_PHASE = Phase31
PHASE30_CLOSED = YES
PHASE31_ENTRY_APPROVED = YES
PHASE31_PERFORMANCE_IMPLEMENTATION_AUTHORIZED_AT_ENTRY = NO
```

Phase30 is formally closed. Phase31 begins with clean long-horizon evidence
collection and characterization, not immediate Strategy tuning.

## Phase30 Final Status

```text
PHASE30_RUNTIME_ARCHITECTURE_CONFORMANT = YES
PHASE30_CRITICAL_CONFORMANCE_GAPS = 0
PHASE30_HIGH_CONFORMANCE_GAPS = 0
PHASE30_FINAL_FRESH_25BD_ACCEPTED = YES
PHASE30_FINAL_RETURN_PCT = 8.162
PHASE30_FINAL_AVERAGE_EXPOSURE_PCT = 82.248
PHASE30_FINAL_SYSTEM_CAUSED_REVIEW_COUNT = 0
PHASE30_FINAL_INTERNAL_SYSTEM_CONSISTENCY_REVIEW_COUNT = 0
MID_RUN_HALT = NO
```

Final accepted Phase30 fresh run:

`runtime-test-historical-extended-smoke-20260817T222423827667Z`

Period:

`2022-08-10` through `2022-09-14`

Requested / completed:

`25 / 25 business days`

Final metrics:

```text
FINAL_EQUITY = 1081620
FINAL_RETURN = +8.162%
FINAL_CASH = 103710
FINAL_MARKET_VALUE = 977910
FINAL_EXPOSURE = 90.4116%
AVERAGE_EXPOSURE = 82.2480%
BUY_FILL_COUNT = 60
SELL_FILL_COUNT = 55
TOTAL_BUY_FILLED_NOTIONAL = 3219850
TOTAL_SELL_FILLED_NOTIONAL = 2323560
PNL_RECONCILIATION = PASS
FINAL_PENDING = EMPTY
2022_09_07_PREVIOUS_FAILURE_BOUNDARY = PASS
```

The final close status was `REVIEW_REQUIRED`, but this was classified as:

```text
CLOSE_REASON = strategy_shadow_review_required_non_blocking
CLASSIFICATION = NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING
```

It was not a Runtime defect, authority defect, Safety defect, data integrity
defect, accounting defect, or trading-state defect.

Reference earlier run:

`runtime-test-historical-extended-smoke-20260817T115935581273Z`

This is useful as a pre-final-chain comparison but is not the canonical Phase30
final validation target. It was abandoned after 19 completed business days.

## What Phase30 Actually Did

Phase30 began as clean evidence based performance improvement after Phase29
invalidated the old long Historical baseline due to valuation / capital
authority contamination.

As capital deployment improved, Runtime authority defects became visible:
correct upstream PC/PS quantities and item-scoped reviews were being
misinterpreted by downstream consumers. Phase30 therefore expanded into
Production-common Runtime authority conformance repair.

Major repaired areas:

- candidate and capital deployment evidence foundation;
- lot-aware executable quantity and PC -> PS handoff;
- `selected_position_amount` duplicate sizing authority at Submit;
- Strategy soft-cap discrete-lot overshoot consumption by PS and Submit;
- Final-PC remaining-budget comparison using canonical discrete executable
  requirement;
- BUY/SELL independent Pending composition;
- item-scoped BUY review partial submission;
- same-day and next-day residual Pending lifecycle;
- mixed BUY/SELL residual reviewed BUY expiration;
- Sell Planning, Submit Data Readiness, and Current Valuation compatibility
  with item-scoped review;
- Pending Review Scope Authority centralization;
- Historical Safety Temporal Authority centralization;
- typed Runtime Guard Taxonomy;
- final real-orchestration conformance gate.

## Important Runtime Contracts

### Pending Review Scope Authority

Canonical owner:

`runtime_v2.pending.review_scope_authority`

Owns only Pending structure, review scope, executable/reviewed item sets,
item-vs-batch semantics, partial submit eligibility, sell continuation
eligibility, and reviewed-items-must-not-submit.

Does not own cash, quantity, Strategy cap, Safety hard cap, broker feasibility,
valuation, PM, PC, or PS.

### Historical Safety Temporal Authority

Canonical owner:

`runtime_v2.historical_support.safety_temporal_authority`

Owns shared Historical Safety / temporal binding and consumes Pending review
scope. It does not reconstruct Pending membership, cash, quantity, PM, sizing,
or valuation semantics.

### Runtime Guard Taxonomy

Canonical owner:

`runtime_v2.guard_taxonomy`

Normal Safety, execution Safety, data integrity, internal system consistency,
item-scoped review, and batch-level failure must remain typed and distinct.
`INTERNAL_SYSTEM_CONSISTENCY` is fail-closed and must not be treated as market
risk or ordinary opportunity rejection.

### Quantity Lineage

```text
PC discrete executable quantity
-> PS consume
-> Runtime Planning
-> Pending
-> Submit consistency validation
-> Execution / Fill
```

Submit validates consistency and execution safety. Submit must not resize or
re-decide Strategy quantity.

### Cash Semantics

Keep these distinct:

```text
Strategy deployable budget
PC residual allocation budget
Current cash / buying power
Pending reserved notional
Submit aggregate cash
broker buying power
post-fill cash
```

Do not collapse them into one generic cash authority.

### BUY / SELL Independence

Reviewed BUY must not block valid SELL. Valid SELL must not drop valid BUY.
Reviewed BUY remains fail-closed for BUY execution. Reviewed SELL remains
fail-closed.

## Things That Must Not Happen

- no Historical-specific Strategy;
- no fail-open weakening;
- no future information;
- no Historical outcome parameter selection;
- no Paper Ledger / selected / bought / fill outcome as training feature;
- no forced investment;
- no fixed exposure target purely for backtest performance;
- no duplicate authority redecision;
- no BUY/SELL coupling;
- no reviewed BUY auto-approval;
- no Strategy tuning from a single short run;
- no long Historical execution by Codex.

## Phase31 First Action

```text
PHASE31_FIRST_TASK = USER_OPERATED_FRESH_100BD_VALIDATION
```

Recommended run shape:

```text
start-date = 2022-08-10
business-days = 100
initial-cash = 1000000
```

The user runs it. Codex does not run long Historical. After the user provides
evidence, perform a READ-ONLY performance characterization before any Strategy
change.

## Phase31 Research Targets

- winner HOLD and profit retention;
- ADD quality and ADD timing;
- SELL / REDUCE timing;
- short-hold churn;
- Re-entry quality and churn;
- BUY-time detectability of early-exit candidates using PIT-only predictors and
  control groups;
- regime attribution;
- Expected Edge calibration;
- MDD, turnover, exposure, campaign metrics, and capital deployment quality.

## Phase31 Defect Handling

If a Runtime, authority, data, temporal, or Safety defect appears during
Phase31 validation:

- do not call it Strategy failure;
- do not tune Strategy to bypass it;
- classify the defect separately;
- repair only with focused evidence;
- resume performance research after integrity is restored.

## Phase31 Command Rule

Do not append `--json` to CLI commands unless the user explicitly asks for JSON
output. Long-running validation commands must be user-operated.

## Recommended Next Task

```text
Phase31-A - User-Operated Fresh 100BD Validation
```
