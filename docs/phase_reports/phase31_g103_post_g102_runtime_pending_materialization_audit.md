# Phase31-G103 - Post-G102 Actual Runtime-to-Pending Materialization Audit

## PRIMARY_JUDGMENT

`G103_RUNTIME_PENDING_DEFECT_CONFIRMED_READY_FOR_NARROW_REPAIR`

Post-G102 actual artifacts from:

```text
runtime-test-historical-extended-smoke-20260825T004731313315Z
```

show that the primary anchor `2023-03-22 / 94320` no longer has the G101 item-scoped PC authority absence defect. G102 is active through PC, PS, Runtime Planning, and Pending:

```text
G97 positive
-> G61 LOT_EXECUTABLE_COMPATIBLE
-> PC discrete executable quantity authority PASS / quantity 200
-> PS consumes authority / quantity_delta 200
-> Runtime BUY_NEW 200
-> Pending BUY item 200 with embedded PC authority PASS
```

The anchor still did not reach holdings because Submit reclassified the Pending BUY item as item-scoped `REVIEW_REQUIRED`:

```text
canonical_discrete_quantity_submit_authority.status = REVIEW_REQUIRED
reason = pc_discrete_quantity_authority_lot_overshoot_unresolved
```

The first stopping boundary for the primary anchor is therefore:

```text
Pending BUY item -> Submit item-scoped feasibility
```

Separately, the previous G101 population issue still exists: runtime-visible G97/G99/G102 BUY rows not found as Submit BUY pending items remain present. Using the same G101-compatible item-scoped row basis, the `UNEXPLAINED_RUNTIME_TO_SUBMIT_ROWS = 17` condition reproduces after G102. This is a distinct Runtime-to-Pending/materialization visibility problem and should not be repaired by weakening Submit.

No code/config/run-state changes were made. No fresh-run/resume/replay/long Historical was executed by Codex.

## Target

```text
RUN_ID = runtime-test-historical-extended-smoke-20260825T004731313315Z
PRIMARY_ANCHOR = 2023-03-22 / 94320
AUDIT_MODE = READ_ONLY_ACTUAL_ARTIFACTS_ONLY
```

## Primary Anchor Trace

### 1. Portfolio Construction

Actual G102 authority is present.

```text
symbol = 94320
G61 compatibility_state = LOT_EXECUTABLE_COMPATIBLE
G61 projected_quantity_delta_evidence_only = 200
G61 trading_unit = 100
G61 reference_price = 161.8
G61 portfolio_value = 1,369,320
G61 lower_priority_execution_requires_explicit_residual_resolution = false

pc_positive_executable_quantity_authority.status = PASS
authority_type = PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY
final_allocated_quantity = 200
ps_must_consume_canonical_quantity = true
future_information_used = false
g102_item_scoped_pc_discrete_quantity_authority_propagated = true
```

The G102 repair is active in actual PC artifacts.

```text
POST_G102_20230322_94320_PC_AUTHORITY_PASS = YES
```

### 2. Position Sizing

PS consumes the item-scoped PC quantity authority and produces a positive discrete quantity.

```text
security_code = 94320
pc_discrete_quantity_authority_consumed = true
pc_discrete_authorized_quantity = 200
target_quantity_candidate = 200
current_quantity = 0
quantity_delta_candidate = 200
final_quantity_delta = 200
reason_codes includes PC_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY_CONSUMED
```

```text
POST_G102_20230322_94320_PS_QUANTITY = 200
```

### 3. Runtime Planning

Runtime Planning maps PS positive quantity to BUY_NEW and does not re-decide capital priority.

```text
security_code = 94320
planning_intent = BUY_NEW
planned_quantity = 200
quantity_status = RESOLVED_EXECUTABLE
quantity_delta_candidate = 200
target_quantity_candidate = 200
pending_eligibility = CANDIDATE_ONLY
reason_codes =
  - position_sizing_positive_quantity_delta_maps_to_buy_new
  - position_sizing_quantity_candidate_resolved
```

```text
POST_G102_20230322_94320_RUNTIME_BUY = YES
```

### 4. Pending

Pending materialization exists for the anchor.

```text
pending_item_id = strategy-d83c7b2b2fbcf383c9f6
symbol = 94320
side = BUY
quantity = 200
state = REVIEW_REQUIRED
approved = false
item_review_reason = pc_discrete_quantity_authority_lot_overshoot_unresolved
```

The Pending item's quantity contract embeds both:

```text
quantity_contract.phase29_l19_lot_resolution.pc_positive_executable_quantity_authority.status = PASS
quantity_contract.position_sizing_authority.phase29_l19_lot_resolution.pc_positive_executable_quantity_authority.status = PASS
```

Therefore the primary anchor is not stopped by Runtime-to-Pending materialization.

```text
POST_G102_20230322_94320_PENDING_BUY = YES
```

### 5. Submit

Submit sees the Pending item and evaluates it item-scoped.

```text
canonical_discrete_quantity_submit_authority.authority_type =
  PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY
canonical_discrete_quantity_submit_authority.authorized_quantity = 200
canonical_discrete_quantity_submit_authority.item_quantity = 200
canonical_discrete_quantity_submit_authority.ps_final_quantity = 200
canonical_discrete_quantity_submit_authority.status = REVIEW_REQUIRED
canonical_discrete_quantity_submit_authority.reason =
  pc_discrete_quantity_authority_lot_overshoot_unresolved
```

Submit item result:

```text
pending_item_id = strategy-d83c7b2b2fbcf383c9f6
symbol = 94320
side = BUY
quantity = 200
submitted = false
blocked = false
rejected = false
reason = pc_discrete_quantity_authority_lot_overshoot_unresolved
```

The direct Submit predicate is in `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`:

```text
if str(lot_resolution.get("lot_overshoot_reason") or "") and not strategy_soft_cap_overshoot_authorized:
    REVIEW_REQUIRED / pc_discrete_quantity_authority_lot_overshoot_unresolved
```

The embedded lot resolution carries:

```text
lot_overshoot_reason = G102_G97_G99_ITEM_SCOPED_PC_DISCRETE_QUANTITY_AUTHORITY
strategy_cap_preserved = true
safety_hard_cap_preserved = true
one_lot_feasibility_status = PASS
one_lot_quantity = 100
final_allocated_quantity = 200
executable_quantity_delta = 200
preflight_executable_quantity_delta = 200
semantic_type = BUY_NEW
```

But `G102_G97_G99_ITEM_SCOPED_PC_DISCRETE_QUANTITY_AUTHORITY` is not one of the Submit-recognized soft-cap/lot-overshoot authorization reasons. Submit therefore fail-closes the BUY item even though the PC discrete quantity authority itself is PASS.

```text
POST_G102_20230322_94320_SUBMIT_RESULT = REVIEW_REQUIRED / pc_discrete_quantity_authority_lot_overshoot_unresolved
```

### 6. Execution / Fill / Holding

No order or fill exists for 94320 on 2023-03-22.

```text
order exists = NO
fill exists = NO
holding effect = NO
```

```text
POST_G102_20230322_94320_FILL = NO
```

## Primary Stopping Boundary

```text
POST_G102_PRIMARY_STOPPING_BOUNDARY =
  Pending BUY item -> Submit item-scoped feasibility

POST_G102_DEFECT_CLASS = E
```

Class E means:

```text
Pending-to-Submit visibility/consumer interpretation gap
```

The anchor's Pending item is visible to Submit, so this is not a missing Pending item for 94320. The gap is narrower: Submit consumes the embedded authority but treats the new G102 lot-overhang reason as unresolved because that reason is outside the current authorized overshoot contract.

## Population Funnel

Using completed target-run dates with G97/G99/G102 reconsideration rows and an item-scoped dedupe compatible with the G101 population basis:

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

Drop points:

```text
PC -> G61 not executable = 20
PC discrete -> PS positive = 4
PS -> Runtime BUY = 1
Runtime BUY -> Pending BUY missing = 17
Pending BUY -> Submit not submitted = 7
Pending BUY -> Submit visibility missing = 2
```

The broader post-G102 run therefore has two unresolved populations:

1. Runtime-visible rows that do not appear as Submit BUY Pending items.
2. Pending BUY rows that reach Submit but are item-scoped reviewed for `pc_discrete_quantity_authority_lot_overshoot_unresolved`.

The first population reproduces the G101 `UNEXPLAINED_RUNTIME_TO_SUBMIT_ROWS = 17` condition. The primary anchor belongs to the second population.

## Runtime-to-Pending Contract

The Runtime-to-Pending contract is defined.

Component creating `PendingOrderItem`:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py
  activate_strategy_planning_authority()
  -> _pending_item_from_strategy_plan()
  -> promote_order_plan_to_pending()
```

Admission predicates observed in code:

```text
planning_intent not in NO_ACTION / NO_ORDER
order_side_intent in BUY / SELL
planned_quantity > 0
price authority PASS
for SELL: canonical listed_info required
```

For BUY, `_pending_item_from_strategy_plan()` creates a `PendingOrderItem` with:

```text
pending_item_id = strategy-{hash(business_date, symbol, intent, side, planning_id)}
symbol
side
quantity = planned_quantity
quantity_contract = _planning_quantity_contract(...)
strategy_authority_lineage
```

The quantity contract embeds:

```text
position_sizing_authority
phase29_l19_lot_resolution
pc_positive_executable_quantity_authority
```

Normal successful Runtime BUY -> Pending -> Submit -> Fill examples remain intact in this same actual run:

```text
2022-10-03 / 94340 / BUY_NEW / Runtime 200 -> Pending item -> Submit true
2022-10-03 / 37820 / BUY_NEW / Runtime 400 -> Pending item -> Submit true
2022-10-03 / 93600 / BUY_NEW / Runtime 100 -> Pending item -> Submit true
2022-10-03 / 33700 / BUY_NEW / Runtime 100 -> Pending item -> Submit true
2022-10-03 / 83060 / BUY_NEW / Runtime 100 -> Pending item -> Submit true
```

Therefore:

```text
RUNTIME_TO_PENDING_CONTRACT_DEFINED = YES
NORMAL_RUNTIME_BUY_TO_PENDING_PATH_CHANGED = NO
```

For G97/G99/G102 rows:

```text
G97_G99_G102_RUNTIME_BUY_COMPATIBLE_WITH_PENDING_CONTRACT = PARTIAL
```

Reason:

```text
2023-03-22 / 94320 is compatible and materializes.
17 runtime-visible rows still do not materialize as Submit BUY Pending items.
```

## G101 Reproduction Check

```text
UNEXPLAINED_RUNTIME_TO_SUBMIT_ROWS_REPRODUCES_AFTER_G102 = YES
UNEXPLAINED_RUNTIME_TO_SUBMIT_ROWS = 17
```

This is not the primary 94320 stopping boundary, but it remains a real population defect. The safe follow-up should not collapse it into the Submit lot-overshoot issue.

## Defect Classification

Primary anchor:

```text
POST_G102_DEFECT_CLASS = E
```

Population residual:

```text
RUNTIME_TO_PENDING_MATERIALIZATION_DEFECT_CLASS = D / PARTIAL
```

The actual post-G102 state is:

```text
A = G102 PC authority not actually active: NO
B = PS authority consumption gap: NO
C = Runtime quantity-contract propagation gap: NO for anchor
D = Runtime-to-Pending admission/materialization gap: YES for residual 17-row population
E = Pending-to-Submit visibility gap: YES for primary anchor
F = legitimate existing contract rejection: PARTIAL
G = other: NO
```

`F` is only partial because Submit is correctly fail-closing under its current contract. However, the G102 authority reason represents a newly introduced item-scoped PC discrete authority path that appears intended to be consumable by Submit when all quantity/cap/safety checks pass. That makes a narrow consumer-contract repair plausible rather than a performance or Strategy redesign.

## Required Output

```text
POST_G102_20230322_94320_PC_AUTHORITY_PASS = YES
POST_G102_20230322_94320_PS_QUANTITY = 200
POST_G102_20230322_94320_RUNTIME_BUY = YES
POST_G102_20230322_94320_PENDING_BUY = YES
POST_G102_20230322_94320_SUBMIT_RESULT = REVIEW_REQUIRED / pc_discrete_quantity_authority_lot_overshoot_unresolved
POST_G102_20230322_94320_FILL = NO

POST_G102_PRIMARY_STOPPING_BOUNDARY = Pending BUY item -> Submit item-scoped feasibility
POST_G102_DEFECT_CLASS = E

RUNTIME_TO_PENDING_CONTRACT_DEFINED = YES
G97_G99_G102_RUNTIME_BUY_COMPATIBLE_WITH_PENDING_CONTRACT = PARTIAL
NORMAL_RUNTIME_BUY_TO_PENDING_PATH_CHANGED = NO

SAFE_NARROW_REPAIR_POSSIBLE = YES
REPAIR_REQUIRED = YES

FINAL_DECISION =
G103_RUNTIME_PENDING_DEFECT_CONFIRMED_READY_FOR_NARROW_REPAIR
```

## Constraints

```text
READ_ONLY = YES
CODE_CHANGED = NO
CONFIG_CHANGED = NO
RUN_MODIFIED = NO
FRESH_RUN_EXECUTED = NO
RESUME_EXECUTED = NO
REPLAY_EXECUTED = NO
LONG_HISTORICAL_EXECUTED = NO
PERFORMANCE_TUNING = NO
FUTURE_PNL_OR_OUTCOME_USED_AS_DECISION_EVIDENCE = NO
```

## Next Boundary

The next repair should be narrow and should not bypass Pending or weaken Submit globally.

Two separate boundaries should be kept distinct:

1. Primary anchor repair:

```text
Submit item-scoped discrete quantity authority must recognize the G102/G97/G99 PC discrete quantity authority only when:
  - pc_positive_executable_quantity_authority.status = PASS
  - item quantity equals authorized quantity
  - final/executable/preflight quantities match
  - strategy cap and safety hard cap are preserved
  - future_information_used = false
  - semantic_type is BUY_NEW / REENTRY / BUY_ADD
  - lot context remains canonical
```

2. Residual population audit/repair:

```text
The 17 Runtime BUY rows still missing as Submit BUY Pending items require a separate Runtime-to-Pending materialization investigation. They should not be hidden by changing Submit.
```
