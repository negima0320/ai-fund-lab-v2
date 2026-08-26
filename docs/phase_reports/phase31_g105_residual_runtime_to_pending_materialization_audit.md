# Phase31-G105 - Residual Runtime-to-Pending Materialization Audit

## PRIMARY_JUDGMENT

`G105_RUNTIME_TO_PENDING_AMBIGUOUS_NEEDS_NARROWER_AUDIT`

G105 could not complete the required row-exact residual audit because the target actual run artifacts are not present in the current workspace:

```text
TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260825T004731313315Z
TARGET_RUN_ARTIFACT_PRESENT = NO
```

The retained G101/G103 reports establish that a 17-row residual existed at the time of those audits:

```text
UNEXPLAINED_RUNTIME_TO_SUBMIT_ROWS = 17
```

However, G105 requires reconstructing every residual row from the actual post-G102 run artifacts, including strategy-authority input/output, pending identity, dedupe/lifecycle state, price authority, and quantity contract. The summarized G101/G103 reports do not contain enough per-row persisted evidence to satisfy that requirement without the target run directory.

No code/config/run-state changes were made. No fresh-run/resume/replay/long Historical was executed.

## Target Evidence Availability

Command-level workspace inspection found no directory matching the target run under `reports/runtime_tests`:

```text
find reports/runtime_tests -maxdepth 4 -type d -name '*20260825T004731313315Z*'
result = empty
```

Currently present historical-extended-smoke run directories are:

```text
runtime-test-historical-extended-smoke-20260823T140946562431Z
runtime-test-historical-extended-smoke-20260823T230627195532Z
runtime-test-historical-extended-smoke-20260823T232301910860Z
runtime-test-historical-extended-smoke-20260824T003228930947Z
runtime-test-historical-extended-smoke-20260824T032350824281Z
runtime-test-historical-extended-smoke-20260824T055234719725Z
```

Therefore:

```text
RESIDUAL_RUNTIME_TO_PENDING_ROW_COUNT =
  EVIDENCE_UNAVAILABLE_FROM_CURRENT_WORKSPACE

LAST_REPORTED_RESIDUAL_RUNTIME_TO_PENDING_ROW_COUNT =
  17, from G101/G103 retained reports
```

## Retained G101/G103 Evidence

G103 reported the post-G102 funnel:

```text
G97 positive = 51
G61 executable = 31
PC discrete authority PASS = 31
PS positive = 27
Runtime BUY = 26
Pending BUY = 9
Submit PASS / submitted order = 0
Fill = 0
Holding effect = 0
```

G103 also reported drop points:

```text
PC -> G61 not executable = 20
PC discrete -> PS positive = 4
PS -> Runtime BUY = 1
Runtime BUY -> Pending BUY missing = 17
Pending BUY -> Submit not submitted = 7
Pending BUY -> Submit visibility missing = 2
```

The retained G103 examples of missing Runtime BUY -> Pending BUY rows include:

| Date | Symbol | Reported Surface |
|---|---:|---|
| 2022-11-11 | 76470 | CANDIDATE_ONLY |
| 2022-11-28 | 76470 | CANDIDATE_ONLY |
| 2022-11-29 | 76470 | CANDIDATE_ONLY |
| 2022-11-30 | 76470 | CANDIDATE_ONLY |
| 2022-12-01 | 76470 | CANDIDATE_ONLY |
| 2023-01-23 | 94320 | CANDIDATE_ONLY |
| 2023-02-20 | 93180 | CANDIDATE_ONLY |
| 2023-02-21 | 94320 | CANDIDATE_ONLY |
| 2023-02-27 | 93180 | CANDIDATE_ONLY |
| 2023-03-02 | 93180 | CANDIDATE_ONLY |
| 2023-03-03 | 93180 | CANDIDATE_ONLY |

This is not a complete 17-row reconstruction. It is retained-report evidence only.

G101 separately listed nine Runtime-visible G97 rows that did become Pending BUY items but were stopped at Submit before G104:

```text
2022-11-21 / 76470 / BUY_NEW / qty 400
2022-11-22 / 76470 / BUY_NEW / qty 1000
2022-11-24 / 76470 / BUY_NEW / qty 200
2022-11-25 / 76470 / BUY_NEW / qty 500
2022-12-05 / 76470 / BUY_NEW / qty 300
2022-12-09 / 76470 / BUY_NEW / qty 500
2022-12-13 / 76470 / BUY_NEW / qty 500
2023-03-07 / 94320 / BUY_NEW / qty 200
2023-03-22 / 94320 / BUY_NEW / qty 200
```

Those nine rows are a separate Pending-to-Submit recognition population and are not the residual 17-row Runtime-to-Pending population.

## Runtime-to-Pending Contract

The Runtime-to-Pending owner is:

```text
RUNTIME_TO_PENDING_OWNER =
  src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py
  activate_strategy_planning_authority()
  -> _pending_item_from_strategy_plan()
  -> promote_order_plan_to_pending()
```

```text
RUNTIME_TO_PENDING_CONTRACT_DEFINED = YES
```

The code path is:

1. `activate_strategy_planning_authority()` iterates `runtime_planning_payload["plans"]`.
2. Each plan is passed to `_pending_item_from_strategy_plan()`.
3. Generated items are decorated with accepted-generation, submit-policy, and safety context.
4. BUY items are sorted by `_canonical_marginal_capital_pending_order()`.
5. `_cash_feasible_buy_batch()` evaluates BUY feasibility sequentially and can prune cash/buying-power-infeasible BUY rows.
6. Only the remaining `pending_items` are written to the order plan and passed to `promote_order_plan_to_pending()`.
7. `promote_order_plan_to_pending()` materializes the Pending plan from that post-prune item list.

Code references:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:235-285
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:287-320
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:332-413
src/ai_fund_lab_v2/runtime_v2/pending/promotion.py:31-119
```

## Pending Construction Predicates

`_pending_item_from_strategy_plan()` creates a `PendingOrderItem` when:

```text
planning_intent not in NO_ACTION / NO_ORDER
order_side_intent in BUY / SELL
planned_quantity schema resolves
planned_quantity > 0
price authority status = PASS
SELL only: canonical listed_info is present
```

For BUY, the code does not require listed-info availability at this boundary.

Direct code references:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:631-688
```

The pending item identity is deterministic:

```text
pending_item_id =
  strategy-{sha256(business_date|symbol|intent|side|planning_id)[:20]}
```

Direct code reference:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:676-678
```

The pending item carries:

```text
symbol
side
quantity = planned_quantity
quantity_contract
strategy_authority_lineage
source_decision_type = planning_intent
canonical_marginal_capital_priority_index
marginal_capital_value_authority
```

Direct code references:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:698-750
```

The quantity contract embeds Position Sizing and PC lot-resolution authority for BUY:

```text
quantity_contract.position_sizing_authority
quantity_contract.phase29_l19_lot_resolution
quantity_contract.pc_positive_executable_quantity_authority
```

Direct code references:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:787-940
```

## Critical Post-Construction Prune Boundary

The code has an important boundary between item construction and final Pending persistence:

```text
_cash_feasible_buy_batch()
```

If an item-level submit-feasibility check fails specifically on `cash` or `buying_power`, the item is not included in the final active Pending items:

```text
source_violated_policy in {cash, buying_power}
decision = PRUNE
reason = DEFERRED_INSUFFICIENT_RESERVED_CASH
```

Direct code references:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:547-579
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:580-615
```

This means a row can be visible in `runtime_planning_payload["plans"]`, can satisfy `_pending_item_from_strategy_plan()`, can appear in `strategy_item_lineage` as `pending_item_generated = true`, and still not appear in final Pending if `_cash_feasible_buy_batch()` prunes it.

Because the target run artifacts are absent, G105 cannot determine whether the residual 17 rows were:

```text
never constructed
constructed then cash-pruned
constructed then deduped
constructed then lifecycle-hidden
suppressed by price/quantity/semantic predicates
```

## Runtime Surface vs Pending Surface

```text
G103_RUNTIME_BUY_POPULATION_SURFACE =
  retained G103 summary of runtime-visible G97/G99/G102 BUY rows
  from the post-G102 target run
```

G105 cannot re-open the exact artifact path/surface because the target run directory is missing.

```text
PENDING_CONSUMES_SAME_RUNTIME_SURFACE = PARTIAL
```

Reason:

The code consumes `runtime_planning_payload["plans"]`, but final Pending persistence consumes only the post-`_cash_feasible_buy_batch()` item list. Therefore a runtime-visible BUY row and a persisted Pending BUY item are not guaranteed to be the same population unless the strategy-authority order-plan artifact proves the row survived the cash-feasible batch.

## Normal Successful Comparison

G103 retained normal successful examples from the same target run:

| Date | Symbol | Intent | Retained Trace |
|---|---:|---|---|
| 2022-10-03 | 94340 | BUY_NEW | Runtime 200 -> Pending item -> Submit true |
| 2022-10-03 | 37820 | BUY_NEW | Runtime 400 -> Pending item -> Submit true |
| 2022-10-03 | 93600 | BUY_NEW | Runtime 100 -> Pending item -> Submit true |
| 2022-10-03 | 33700 | BUY_NEW | Runtime 100 -> Pending item -> Submit true |
| 2022-10-03 | 83060 | BUY_NEW | Runtime 100 -> Pending item -> Submit true |

These could not be revalidated field-by-field in G105 because the target run artifacts are absent.

## Primary Anchor Selection

G105 required at least three exact anchors from the residual 17 rows:

```text
earliest missing row
mid-period missing row
latest missing row
```

This cannot be completed from current evidence. Candidate examples retained from G103 are insufficient because they do not include all required fields:

```text
planning_id
Runtime authority lineage
G97/G99/G102 provenance
current holding quantity
target quantity
strategy-authority item generation status
cash_feasible_buy_batch decision
pending identity collision/dedupe state
pending lifecycle state
```

## Required Count Fields

Because the target artifacts are unavailable, the following counts cannot be measured without fabricating evidence:

| Field | G105 Result |
|---|---|
| PENDING_ID_COLLISION_COUNT | EVIDENCE_UNAVAILABLE |
| PENDING_DEDUPE_SUPPRESSION_COUNT | EVIDENCE_UNAVAILABLE |
| PENDING_ALREADY_EXISTS_SUPPRESSION_COUNT | EVIDENCE_UNAVAILABLE |
| BUY_NEW_WITH_EXISTING_POSITION_COUNT | EVIDENCE_UNAVAILABLE |
| BUY_ADD_WITH_ZERO_POSITION_COUNT | EVIDENCE_UNAVAILABLE |
| SEMANTIC_POSITION_STATE_MISMATCH_COUNT | EVIDENCE_UNAVAILABLE |
| STRATEGY_AUTHORITY_INPUT_ROWS | EVIDENCE_UNAVAILABLE |
| STRATEGY_AUTHORITY_OUTPUT_BUY_ROWS | EVIDENCE_UNAVAILABLE |
| RESIDUAL_17_ENTER_STRATEGY_AUTHORITY | EVIDENCE_UNAVAILABLE |
| RESIDUAL_17_SURVIVE_STRATEGY_AUTHORITY | EVIDENCE_UNAVAILABLE |
| STRATEGY_AUTHORITY_SUPPRESSION_COUNT | EVIDENCE_UNAVAILABLE |
| PRICE_AUTHORITY_FAIL_COUNT | EVIDENCE_UNAVAILABLE |
| PRICE_AUTHORITY_MISSING_COUNT | EVIDENCE_UNAVAILABLE |
| PRICE_AUTHORITY_PASS_COUNT | EVIDENCE_UNAVAILABLE |
| QUANTITY_CONTRACT_INVALID_COUNT | EVIDENCE_UNAVAILABLE |
| QUANTITY_CONTRACT_MISSING_COUNT | EVIDENCE_UNAVAILABLE |
| QUANTITY_CONTRACT_VALID_COUNT | EVIDENCE_UNAVAILABLE |
| CREATED_THEN_TERMINATED_COUNT | EVIDENCE_UNAVAILABLE |
| CREATED_THEN_MERGED_COUNT | EVIDENCE_UNAVAILABLE |
| CREATED_THEN_DEFERRED_COUNT | EVIDENCE_UNAVAILABLE |
| NEVER_CREATED_COUNT | EVIDENCE_UNAVAILABLE |

## Classification

G105 required every residual row to receive exactly one classification:

```text
A = legitimate pre-Pending contract rejection
B = duplicate/idempotent suppression
C = strategy authority suppression
D = price authority failure
E = quantity-contract invalidity
F = BUY_NEW/BUY_ADD semantic mismatch
G = Pending lifecycle visibility/artifact issue
H = true Runtime-to-Pending consumer gap
I = other confirmed
```

This cannot be performed row-exactly without the target artifacts.

Current classification counts:

| Class | Count |
|---|---:|
| A | EVIDENCE_UNAVAILABLE |
| B | EVIDENCE_UNAVAILABLE |
| C | EVIDENCE_UNAVAILABLE |
| D | EVIDENCE_UNAVAILABLE |
| E | EVIDENCE_UNAVAILABLE |
| F | EVIDENCE_UNAVAILABLE |
| G | EVIDENCE_UNAVAILABLE |
| H | EVIDENCE_UNAVAILABLE |
| I | EVIDENCE_UNAVAILABLE |

The strongest code-level candidate boundary is:

```text
Runtime plan -> _pending_item_from_strategy_plan()
-> _cash_feasible_buy_batch()
-> final post-prune Pending items
```

But G105 does not classify the residual 17 as cash-pruned because the required `cash_feasible_buy_batch.items[]` evidence for those rows is not available.

## Material Defect Population

```text
LEGITIMATE_NON_MATERIALIZATION_COUNT = EVIDENCE_UNAVAILABLE
TRUE_RUNTIME_TO_PENDING_DEFECT_COUNT = EVIDENCE_UNAVAILABLE
VISIBILITY_ONLY_COUNT = EVIDENCE_UNAVAILABLE
```

```text
RUNTIME_TO_PENDING_DEFECT_CONFIRMED = PARTIAL
```

Reason:

G101/G103 establish that a residual population existed. G105 cannot confirm the exact defect class for that population from current artifacts.

## Safe Narrow Repair Assessment

```text
SAFE_NARROW_REPAIR_POSSIBLE = PARTIAL
```

A narrow repair may be possible if the missing rows are proven to be created and then incorrectly pruned or hidden at one common boundary. The likely audit focus is:

```text
producer/consumer boundary =
  strategy_authority runtime plan consumption
  -> _pending_item_from_strategy_plan()
  -> _cash_feasible_buy_batch()
  -> promote_order_plan_to_pending()

required predicate to inspect =
  cash_feasible_buy_batch.items[].decision
  cash_feasible_buy_batch.items[].reason
  cash_feasible_buy_batch.items[].source_submit_feasibility_status
  cash_feasible_buy_batch.items[].source_violated_policy
```

No repair is authorized from G105 alone because the residual rows are not classified.

## Short E2E Holding Gate

```text
SHORT_E2E_HOLDING_GATE_DEFINED = YES
```

Before any long Historical recommendation after a future repair, at least one repaired residual anchor must prove the full path:

```text
PC
-> G61
-> PS
-> Runtime
-> Strategy Authority
-> Pending
-> Submit
-> Execution
-> Fill
-> Holding
```

This gate must be short/focused and must not be replaced by schema/lineage-only acceptance.

## Required Final Judgments

```text
RESIDUAL_RUNTIME_TO_PENDING_ROW_COUNT =
  EVIDENCE_UNAVAILABLE_FROM_CURRENT_WORKSPACE

LAST_REPORTED_RESIDUAL_RUNTIME_TO_PENDING_ROW_COUNT = 17

RUNTIME_TO_PENDING_OWNER =
  runtime_v2.planning.strategy_authority.activate_strategy_planning_authority

RUNTIME_TO_PENDING_CONTRACT_DEFINED = YES

G103_RUNTIME_BUY_POPULATION_SURFACE =
  retained G103 summary of runtime-visible G97/G99/G102 BUY rows

PENDING_CONSUMES_SAME_RUNTIME_SURFACE = PARTIAL

PENDING_ID_COLLISION_COUNT = EVIDENCE_UNAVAILABLE
PENDING_DEDUPE_SUPPRESSION_COUNT = EVIDENCE_UNAVAILABLE
SEMANTIC_POSITION_STATE_MISMATCH_COUNT = EVIDENCE_UNAVAILABLE

STRATEGY_AUTHORITY_SUPPRESSION_COUNT = EVIDENCE_UNAVAILABLE
PRICE_AUTHORITY_FAIL_COUNT = EVIDENCE_UNAVAILABLE
QUANTITY_CONTRACT_INVALID_COUNT = EVIDENCE_UNAVAILABLE

CREATED_THEN_TERMINATED_COUNT = EVIDENCE_UNAVAILABLE
CREATED_THEN_MERGED_COUNT = EVIDENCE_UNAVAILABLE
CREATED_THEN_DEFERRED_COUNT = EVIDENCE_UNAVAILABLE
NEVER_CREATED_COUNT = EVIDENCE_UNAVAILABLE

LEGITIMATE_NON_MATERIALIZATION_COUNT = EVIDENCE_UNAVAILABLE
TRUE_RUNTIME_TO_PENDING_DEFECT_COUNT = EVIDENCE_UNAVAILABLE
VISIBILITY_ONLY_COUNT = EVIDENCE_UNAVAILABLE

RUNTIME_TO_PENDING_DEFECT_CONFIRMED = PARTIAL
SAFE_NARROW_REPAIR_POSSIBLE = PARTIAL
SHORT_E2E_HOLDING_GATE_DEFINED = YES

REPAIR_REQUIRED = NO_DECISION_EVIDENCE_INSUFFICIENT
```

## Decision

```text
G105_RUNTIME_TO_PENDING_AMBIGUOUS_NEEDS_NARROWER_AUDIT
```

## Next

Do not implement a repair from G105 alone.

The next safe step is to restore or regenerate only the missing diagnostic evidence for the already-known target population without running long Historical, then rerun the G105 row-exact audit. The required artifacts are the target run's daily strategy-authority order plans, pending plans, submit manifests, and especially `cash_feasible_buy_batch` evidence for the residual 17 rows.

## Constraint Confirmation

```text
CODE_CHANGED = NO
CONFIG_CHANGED = NO
RUN_MODIFIED = NO
FRESH_RUN_EXECUTED = NO
RESUME_EXECUTED = NO
REPLAY_EXECUTED = NO
LONG_HISTORICAL_EXECUTED = NO
FUTURE_INFORMATION_USED = NO
HISTORICAL_OUTCOME_USED_AS_DECISION_EVIDENCE = NO
G90_REVISITED = NO
G97_SEMANTICS_REVISITED = NO
G99_REVISITED = NO
G102_REVISITED = NO
G104_REVISITED = NO
MARKET_QUALITY_CHANGED = NO
RISK_PACING_CHANGED = NO
CANDIDATE_RANKING_CHANGED = NO
ADD_COMPETITION_CHANGED = NO
SAFETY_CHANGED = NO
PS_QUANTITY_OWNERSHIP_CHANGED = NO
RUNTIME_PRIORITY_CHANGED = NO
```
