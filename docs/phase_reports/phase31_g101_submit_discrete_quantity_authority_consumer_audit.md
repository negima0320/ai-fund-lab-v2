# Phase31-G101 - Submit Discrete Quantity Authority Consumer Audit

## PRIMARY_JUDGMENT

`G101_SUBMIT_AUTHORITY_DEFECT_CONFIRMED_READY_FOR_NARROW_REPAIR`

The post-G99 actual fresh-run confirms a narrow Submit-boundary defect:

```text
G97 authoritative positive
-> G61 LOT_EXECUTABLE_COMPATIBLE
-> Position Sizing quantity_delta > 0
-> Runtime BUY_NEW
-> Pending BUY item quantity > 0
-> Submit canonical_discrete_quantity_submit_authority = REVIEW_REQUIRED
   reason = pc_discrete_quantity_authority_not_pass
```

Submit is not rejecting because of Market Quality, Risk Pacing, G90, G97, G99 lot context, Runtime priority, Safety, or PS quantity calculation. It is rejecting because the Pending BUY item's item-scoped `position_sizing_authority.phase29_l19_lot_resolution.pc_positive_executable_quantity_authority` remains the ordinary top-level PC row authority:

```text
status = NOT_APPLICABLE
final_allocated_quantity = 0
ps_must_consume_canonical_quantity = false
```

even when the G97 reconsideration path has already produced a positive PS/Runtime quantity.

## Target

Run:

```text
runtime-test-historical-extended-smoke-20260824T203644021876Z
```

Primary anchor:

```text
2023-03-22 / 94320
```

No code/config/threshold/weight/run-state changes were made. No fresh-run/resume/replay/long Historical was executed by Codex.

## Submit Authority Contract

Submit evaluates BUY item feasibility in `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`.

The exact item-scoped evidence field is:

```text
planning_submit_feasibility.items[].canonical_discrete_quantity_submit_authority
```

It is produced at Submit feasibility time from:

```text
PendingOrderItem.quantity_contract.position_sizing_authority.phase29_l19_lot_resolution.pc_positive_executable_quantity_authority
```

The underlying PC authority field is:

```text
pc_positive_executable_quantity_authority
```

with:

```text
authority_type = PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY
status = PASS
final_allocated_quantity > 0
ps_must_consume_canonical_quantity = true
future_information_used = false
semantic_type in BUY_NEW / REENTRY / BUY_ADD
item.quantity == final_allocated_quantity
phase29_l19_lot_resolution final/executable/preflight quantities match
```

Submit fails closed when the authority exists but status is not `PASS`; the immediate predicate is:

```text
str(authority.get("status") or "") != "PASS"
```

which yields:

```text
pc_discrete_quantity_authority_not_pass
```

The producer of the raw authority is Portfolio Construction. Position Sizing consumes/preserves it. Runtime carries quantity and quantity contract into Pending. Submit revalidates it item-scoped; it does not infer from aggregate allocation or resize.

SELL uses separate quantity contracts, notably PM/Sell Planning `quantity_contract.final_sell_quantity`; this PC discrete BUY authority is not the SELL authority.

## Normal Successful BUY Comparison

Normal successful BUYs in the same run all carry the PC discrete authority through Pending into Submit.

| Date | Symbol | Intent | PC authority | PS qty | Pending qty | Submit canonical authority | Result |
|---|---:|---|---|---:|---:|---|---|
| 2022-10-03 | 33700 | BUY_NEW | PASS / final_allocated_quantity=100 / ps_must=true | 100 | 100 | PASS / authorized_quantity=100 / item_quantity=100 | filled BUY 100 |
| 2022-10-03 | 89180 | BUY_NEW | PASS / final_allocated_quantity=3700 / ps_must=true | 3700 | 3700 | PASS / authorized_quantity=3700 / item_quantity=3700 | filled BUY 3700 |
| 2023-03-22 | 67750 | BUY_NEW | PASS / final_allocated_quantity=100 / ps_must=true | 100 | 100 | PASS / authorized_quantity=100 / item_quantity=100 | filled BUY 100 |
| 2023-03-22 | 58200 | BUY_NEW | PASS / final_allocated_quantity=100 / ps_must=true | 100 | 100 | PASS / authorized_quantity=100 / item_quantity=100 | filled BUY 100 |
| 2022-10-12 | 94320 | BUY_ADD | PASS / final_allocated_quantity=100 / ps_must=true | 100 | 100 | PASS / authorized_quantity=100 / item_quantity=100 | filled BUY 100 |
| 2022-11-04 | 94320 | BUY_ADD | PASS / final_allocated_quantity=200 / ps_must=true | 200 | 200 | PASS / authorized_quantity=200 / item_quantity=200 | filled BUY 200 |

G97/G99 reconsideration BUY differs only at the item-scoped PC discrete authority:

| Date | Symbol | Intent | G97/G61/PS/Runtime | Pending qty | Pending PC authority | Submit canonical authority | Result |
|---|---:|---|---|---:|---|---|---|
| 2023-03-22 | 94320 | BUY_NEW | G97 positive, G61 executable, PS qty=200, Runtime BUY_NEW=200 | 200 | NOT_APPLICABLE / final_allocated_quantity=0 / ps_must=false | REVIEW_REQUIRED / reason=pc_discrete_quantity_authority_not_pass / authorized_quantity=0 / item_quantity=200 | not submitted |

## Primary Anchor: 2023-03-22 / 94320

Actual artifact values:

```text
PC top-level portfolio_members[94320].target_weight = 0.0
PC top-level phase29_l19_lot_resolution.semantic_type = NONE
PC top-level phase29_l19_lot_resolution.executable_quantity_delta = 200
PC top-level phase29_l19_lot_resolution.pc_positive_executable_quantity_authority.status = NOT_APPLICABLE
PC top-level phase29_l19_lot_resolution.pc_positive_executable_quantity_authority.final_allocated_quantity = 0
PC top-level phase29_l19_lot_resolution.pc_positive_executable_quantity_authority.ps_must_consume_canonical_quantity = false

G97 authorized allocation weight = 0.030303
G61 compatibility = LOT_EXECUTABLE_COMPATIBLE
G61 projected quantity = 200
PS target_weight = 0.024382
PS quantity_delta = 200
Runtime planning_intent = BUY_NEW
Runtime planned_quantity = 200
Pending item side = BUY
Pending item quantity = 200
Submit canonical_discrete_quantity_submit_authority.status = REVIEW_REQUIRED
Submit canonical_discrete_quantity_submit_authority.reason = pc_discrete_quantity_authority_not_pass
Submit canonical_discrete_quantity_submit_authority.authorized_quantity = 0
Submit canonical_discrete_quantity_submit_authority.item_quantity = 200
Fill = 0
```

Exact missing/invalid authority path:

```text
daily/2023-03-22/submit/runtime_manifest.json
  stages[12].details.components.pending.payload.items[3]
  .quantity_contract.position_sizing_authority.phase29_l19_lot_resolution
  .pc_positive_executable_quantity_authority.status

actual = NOT_APPLICABLE
required = PASS
```

Secondary invalid fields on the same authority:

```text
final_allocated_quantity = 0
ps_must_consume_canonical_quantity = false
semantic_type = NONE
```

The direct predicate causing rejection is the Submit check:

```text
authority.status != PASS
```

## Defect Classification

`SUBMIT_DISCRETE_AUTHORITY_DEFECT_CLASS = A`

Primary class:

```text
A. Producer gap
```

The G97/G99 path produces valid economic allocation, G61 compatibility, PS quantity, and Runtime quantity, but it does not produce/materialize the required item-scoped `PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY` as `PASS` on the Pending BUY item's consumed `position_sizing_authority.phase29_l19_lot_resolution`.

There is also a narrow propagation/materialization aspect:

```text
G97/G61 positive authority exists upstream as reconsideration/compatibility evidence,
but the Submit-required PC discrete authority remains the stale/top-level PC row authority.
```

However, Submit does not receive an equivalent `pc_positive_executable_quantity_authority=PASS` and ignore it. Therefore this is not primarily a consumer-recognition defect.

## Submit Join Key / Identity

Submit does not perform an independent join back to PC/G61/PS artifacts by allocation id, row index, G97 provenance, or symbol. The effective join key is the Pending item itself:

```text
PendingOrderItem
  pending_item_id
  symbol
  side
  quantity
  quantity_contract.position_sizing_authority.phase29_l19_lot_resolution
```

The discrete authority consumed by Submit is embedded in the Pending item's quantity contract. Normal BUY_NEW and BUY_ADD paths are compatible because the embedded PC authority is already `PASS`.

G97 reconsideration is only partially compatible:

```text
Pending item identity exists: YES
Pending item quantity exists: YES
G97/Runtme quantity is carried: YES
Submit-required embedded PC discrete authority is PASS: NO
```

## PS Quantity Authority

For G97/G99 rows, PS already has positive discrete quantity evidence sufficient to demonstrate lot feasibility and Runtime materialization:

```text
2023-03-22 / 94320:
canonical_sizing_evidence.quantity_delta = 200
target_weight = 0.024382
current_quantity = 0
G61 compatibility = LOT_EXECUTABLE_COMPATIBLE
Runtime planned_quantity = 200
```

But the active Submit contract does not treat PS quantity alone as the final discrete BUY submit authority. Submit requires the explicit PC discrete executable quantity authority embedded inside the Position Sizing authority. Thus:

```text
PS_ALREADY_PROVIDES_VALID_DISCRETE_QUANTITY_AUTHORITY = PARTIAL
```

It is valid evidence for PS/Runtime, but not complete evidence for the current Submit contract.

## Population Audit

G100 starting point:

```text
G97 positive = 39
G61 LOT_EXECUTABLE_COMPATIBLE = 27
PS quantity_delta > 0 = 27
Runtime BUY_NEW/BUY_ADD = 26
G97 fills = 0
```

G101 Submit-side population over completed target-run dates:

```text
Runtime-visible G97 BUY rows = 26
G97 BUY rows found as Submit BUY pending items = 9
G97 Submit item results with pc_discrete_quantity_authority_not_pass = 9
G97 Submit item results PASS = 0
G97 fills = 0
Runtime-visible G97 rows not found as Submit BUY pending items = 17
```

Rows observed with explicit Submit discrete authority failure:

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

Runtime-visible G97 rows not found as Submit BUY pending items:

```text
17
```

These are not evidence against the Submit discrete authority defect. They are a separate Runtime/Pending/Submit item materialization visibility gap and should not be repaired by weakening Submit.

## BUY_NEW vs BUY_ADD

The Submit discrete authority contract is common for BUY_NEW, REENTRY, and BUY_ADD:

```text
semantic_type in {"BUY_NEW", "REENTRY", "BUY_ADD"}
```

Normal BUY_ADD examples in this run pass the same authority check:

```text
2022-10-12 / 94320 / BUY_ADD / final_allocated_quantity=100 / Submit PASS / filled
2022-11-04 / 94320 / BUY_ADD / final_allocated_quantity=200 / Submit PASS / filled
```

The 26 Runtime-visible G97 rows observed in the population are BUY_NEW rows. No G97 BUY_ADD row reached the explicit Submit authority failure population in completed artifacts.

## Safety / SoT Conformance

Submit behavior is safety-preserving:

```text
missing/non-PASS PC discrete authority -> REVIEW_REQUIRED
quantity mismatch -> REVIEW_REQUIRED
future_information_used invalid -> REVIEW_REQUIRED
ps_must_consume_canonical_quantity false -> REVIEW_REQUIRED
invalid BUY semantic -> REVIEW_REQUIRED
```

This is correct fail-closed behavior. The repair should not weaken Submit or allow PS quantity alone to bypass the current contract unless the SoT is explicitly changed. The safe narrow repair is upstream: materialize the G97/G99 reconsideration-approved positive quantity as the same item-scoped PC discrete executable quantity authority that normal BUY_NEW/BUY_ADD already carry.

## Required Output

```text
PC_DISCRETE_QUANTITY_AUTHORITY_DEFINED = YES
PC_DISCRETE_QUANTITY_AUTHORITY_OWNER = PORTFOLIO_CONSTRUCTION
SUBMIT_ITEM_SCOPED_AUTHORITY_REQUIRED = YES
SUBMIT_DISCRETE_AUTHORITY_DEFECT_CLASS = A
SUBMIT_AUTHORITY_JOIN_KEY = PendingOrderItem.quantity_contract.position_sizing_authority.phase29_l19_lot_resolution.pc_positive_executable_quantity_authority
G97_RECONSIDERATION_JOIN_KEY_COMPATIBLE = PARTIAL
PS_ALREADY_PROVIDES_VALID_DISCRETE_QUANTITY_AUTHORITY = PARTIAL
RUNTIME_PRESERVES_SUBMIT_REQUIRED_AUTHORITY_LINEAGE = PARTIAL
G97_RUNTIME_BUY_ROWS_RECONCILED = NO
UNEXPLAINED_RUNTIME_TO_SUBMIT_ROWS = 17
BUY_NEW_DISCRETE_AUTHORITY_PATH = PARTIAL
BUY_ADD_DISCRETE_AUTHORITY_PATH = PASS
IMPLEMENTATION_SOT_CONFORMANCE = PARTIAL
SUBMIT_DISCRETE_QUANTITY_AUTHORITY_DEFECT_CONFIRMED = YES
SAFE_NARROW_REPAIR_POSSIBLE = YES
REPAIR_REQUIRED = YES
```

## Run Handling

```text
CODE_CHANGED = NO
CONFIG_CHANGED = NO
THRESHOLD_WEIGHT_SCORE_CHANGED = NO
RUN_MODIFIED = NO
FRESH_RUN_EXECUTED = NO
RESUME_EXECUTED = NO
REPLAY_EXECUTED = NO
LONG_HISTORICAL_EXECUTED = NO
G90_CHANGED = NO
G97_CHANGED = NO
G99_CHANGED = NO
MARKET_QUALITY_CHANGED = NO
RISK_PACING_CHANGED = NO
PS_QUANTITY_AUTHORITY_CHANGED = NO
RUNTIME_PRIORITY_CHANGED = NO
SUBMIT_SAFETY_WEAKENED = NO
FUTURE_PNL_USED = NO
```

## Next

Repair only the confirmed boundary:

```text
G97/G99 positive reconsideration quantity
-> item-scoped PC discrete executable quantity authority PASS
-> Position Sizing authority
-> Pending quantity_contract
-> Submit canonical_discrete_quantity_submit_authority PASS
```

Do not redesign G90/G97/G99, Market Quality, Risk Pacing, ADD semantics, Safety, PS quantity ownership, or Runtime priority.
