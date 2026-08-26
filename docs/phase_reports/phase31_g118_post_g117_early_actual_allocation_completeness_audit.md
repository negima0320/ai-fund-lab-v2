# Phase31-G118 — Post-G117 Early Actual Capital Allocation Completeness Audit

## PRIMARY_JUDGMENT

G118_EARLY_ACTUAL_ALLOCATION_DEFECT_CONFIRMED_READY_FOR_REPAIR

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260825T131857659091Z`
- Baseline run: `runtime-test-historical-extended-smoke-20260824T055234719725Z`
- Audit window: `2022-10-03`, `2022-10-04`, `2022-10-05`, `2022-10-06`, `2022-10-07`, `2022-10-11`, `2022-10-12`
- Completed immutable daily evidence only: YES
- Fresh-run/resume/replay/long Historical executed: NO
- Run/code/config mutation: NO
- PnL used as policy validation: NO

## Executive Conclusion

G117 restored the 2022-10-03 normal `NEW_BUY` actual path end-to-end. The first day exactly matches the baseline anchor fills and holdings.

However, the early window is not allocation-complete. The 2022-10-12 `65500:100` difference is not a legitimate G115 marginal competition loss and not a Submit/Pending/Execution leak. `65500` reaches PC final lot-aware allocation with a positive discrete authority:

- PC final target weight: `0.018564`
- PC final allocated quantity: `100`
- PC positive executable quantity authority: `PASS`
- `ps_must_consume_canonical_quantity = True`

Then Position Sizing zeroes it:

- PS target weight: `0.0`
- PS quantity delta: `0`
- `pc_discrete_authorized_quantity = 100`
- `pc_discrete_quantity_authority_consumed = False`
- `canonical_deployment_set_sizing_eligibility = DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION`
- `canonical_deployment_set_binding.cash_winner = True`

Runtime therefore emits `NO_ORDER`, and no Pending/Submit/Fill exists for `65500`.

The same internal PC-final-positive → PS-zero pattern appears in 15 normal `NEW_BUY` rows across the window. This is a PC final allocation / canonical deployment-set binding / PS consumption inconsistency, not an ADD leakage problem.

## Completed-Date Evidence

All requested dates have `day_completion.status = PASS` in the post-G117 run and are listed in `run_state.completed_business_days`.

`COMPLETED_DATE_EVIDENCE_ONLY = YES`

## 2022-10-03 Restoration

Baseline and post-G117 fills match exactly:

| Symbol | Baseline fill | Post-G117 fill | PC qty | PS qty | Runtime | Submit |
|---|---:|---:|---:|---:|---|---|
| 33700 | 100 | 100 | 100 | 100 | BUY_NEW 100 | PASS |
| 37820 | 400 | 400 | 400 | 400 | BUY_NEW 400 | PASS |
| 83060 | 100 | 100 | 100 | 100 | BUY_NEW 100 | PASS |
| 89180 | 3700 | 3700 | 3700 | 3700 | BUY_NEW 3700 | PASS |
| 92420 | 100 | 100 | 100 | 100 | BUY_NEW 100 | PASS |
| 93600 | 100 | 100 | 100 | 100 | BUY_NEW 100 | PASS |
| 94340 | 200 | 200 | 200 | 200 | BUY_NEW 200 | PASS |

- `20221003_NORMAL_BUY_RESTORATION_COMPLETE = YES`
- `UNEXPLAINED_20221003_ROW_LOSS_COUNT = 0`

## Early Window Divergence Ledger

Through `2022-10-12`, baseline-vs-post-G117 external differences are limited to `65500`:

| Date | Event | Symbol | Baseline | Post-G117 |
|---|---|---|---:|---:|
| 2022-10-12 | fill quantity | 65500 | 100 | 0 |
| 2022-10-12 | cumulative holding quantity | 65500 | 100 | 0 |

`EARLY_WINDOW_DIVERGENCE_EVENT_COUNT = 2`

## 2022-10-12 65500 Trace

| Stage | Baseline | Post-G117 |
|---|---|---|
| Candidate / draft present | YES | YES |
| Draft target weight | 0.021765 | 0.021765 |
| Construction priority | 9 | 9 |
| Runtime opportunity score | 0.02445178 | 0.02445178 |
| PC final target weight | 0.018564 | 0.018564 |
| Final allocation attempted | YES | YES |
| Final allocation iteration | BUY_NEW, accepted 0.018564 | BUY_NEW, accepted 0.018564 |
| PC final allocated quantity | 100 | 100 |
| PC quantity authority | PASS | PASS |
| PS quantity | 100 | 0 |
| Runtime quantity | 100 | 0 |
| Pending selected | YES | NO |
| Submit status | PASS | ABSENT |
| Fill quantity | 100 | 0 |

Required fields:

- `65500_CANDIDATE_PRESENT = YES`
- `65500_PC_DRAFT_POSITIVE = YES`
- `65500_FINAL_FRONTIER_PRESENT = YES`
- `65500_FINAL_ALLOCATION_ATTEMPTED = YES`
- `65500_FINAL_PC_QUANTITY = 100`
- `65500_PS_QUANTITY = 0`
- `65500_RUNTIME_QUANTITY = 0`
- `65500_PENDING_QUANTITY = 0`
- `65500_SUBMIT_STATUS = ABSENT`
- `65500_FILL_QUANTITY = 0`
- `65500_DIFFERENCE_CLASS = G`

Classification `G = PC -> PS quantity leakage`.

## 2022-10-12 ADD Behavior

Both actual ADD rows are valid one-increment G115 paths.

| Symbol | PM ADD | G115 status | Requested weight | Authorized weight | PC qty | PS qty | Runtime | Fill |
|---|---|---|---:|---:|---:|---:|---|---:|
| 94320 | YES | AUTHORITATIVE_STAGED_PC_BINDING | 0.021765 | 0.015042 | 100 | 100 | BUY_ADD 100 | 100 |
| 94340 | YES | AUTHORITATIVE_STAGED_PC_BINDING | 0.021765 | 0.013975 | 100 | 100 | BUY_ADD 100 | 100 |

- `94320_G115_ACTUAL_ADD_PATH_VALID = YES`
- `94340_G115_ACTUAL_ADD_PATH_VALID = YES`
- `UNAUTHORIZED_ADD_QUANTITY_LEAK_TO_PS = 0`
- `UNAUTHORIZED_ADD_QUANTITY_LEAK_TO_RUNTIME = 0`
- `UNAUTHORIZED_ADD_QUANTITY_FILL_COUNT = 0`

## Normal BUY Completeness

Across the requested post-G117 window:

- Positive normal `NEW_BUY` draft rows: `68`
- `g43_binding_cash_preferred` hard-skip rows: `0`
- PC-final-positive but PS/Runtime-zero rows: `15`

Rows with PC final quantity > 0 but PS/Runtime quantity 0:

| Date | Symbol | PC qty | PS qty | Runtime qty | PS reason |
|---|---|---:|---:|---:|---|
| 2022-10-04 | 41650 | 100 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |
| 2022-10-04 | 76470 | 1300 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |
| 2022-10-04 | 59860 | 100 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |
| 2022-10-04 | 44870 | 100 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |
| 2022-10-05 | 33500 | 800 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |
| 2022-10-05 | 41650 | 100 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |
| 2022-10-05 | 76470 | 1200 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |
| 2022-10-06 | 65500 | 100 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |
| 2022-10-06 | 44220 | 100 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |
| 2022-10-06 | 45750 | 100 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |
| 2022-10-07 | 36000 | 100 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |
| 2022-10-07 | 33500 | 1000 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |
| 2022-10-11 | 76470 | 1100 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |
| 2022-10-12 | 65500 | 100 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |
| 2022-10-12 | 76470 | 800 | 0 | 0 | DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION |

The rows do not disappear at PC final allocation. They are internally contradicted after PC final allocation because PS consumes canonical deployment-set defeat / Cash winner evidence instead of the positive PC final discrete authority.

- `NORMAL_NEW_BUY_POSITIVE_DRAFT_COUNT = 68`
- `NORMAL_NEW_BUY_UNEXPLAINED_DROP_COUNT = 15`
- `PC_FINAL_ALLOCATION_OR_EXPLICIT_DEFERRAL_COVERAGE = 77.94%`

## G117 Scope Verification

The original G116 regression is repaired in actual evidence:

- `NORMAL_NEW_BUY_CASH_PREFERRED_HARD_SKIP_COUNT = 0`
- `G117_ACTUAL_SCOPE_REPAIR_EFFECTIVE = YES`

Normal `NEW_BUY` rows with `CASH_PREFERRED` are no longer automatically skipped by `g43_binding_cash_preferred`; they can enter PC final lot-aware allocation. The remaining defect is downstream of that restoration.

## G115 Scope Verification

G115 ADD staged authority itself behaves correctly. However, actual top-level canonical deployment-set binding still overrides some normal `NEW_BUY` rows after PC final allocation by marking them `DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION` / `cash_winner = True`.

`G115_ACTUAL_AUTHORITY_SCOPE = OTHER`

This is not `ENTIRE_SECURITY_ALLOCATION` in the original G116 sense, because PC final allocation does select normal `NEW_BUY` rows. It is also not fully `ADD_PLUS_NEW_BUY_COMPARISON_ONLY`, because PS still receives a contradictory whole-allocation defeat signal for selected normal `NEW_BUY` rows.

## Cash Delta

The observed 2022-10-12 cash delta is fully explained by missing `65500` execution:

- Baseline `65500` fill: BUY 100 at 196.0
- Baseline `65500` cash effect: `-19,600`
- Post-G117 `65500` fill: absent

- `CASH_DELTA = 19600`
- `CASH_DELTA_EXPLAINED_BY_65500 = YES`
- `OTHER_CASH_DELTA_CAUSES = []`

The +100 equity observation is not used as policy validation.

## Required Judgments

- `20221003_NORMAL_BUY_RESTORATION_COMPLETE = YES`
- `EARLY_WINDOW_DIVERGENCE_EVENT_COUNT = 2`
- `65500_DIFFERENCE_CLASS = G`
- `94320_G115_ACTUAL_ADD_PATH_VALID = YES`
- `94340_G115_ACTUAL_ADD_PATH_VALID = YES`
- `UNAUTHORIZED_ADD_QUANTITY_LEAK_TO_PS = 0`
- `UNAUTHORIZED_ADD_QUANTITY_LEAK_TO_RUNTIME = 0`
- `UNAUTHORIZED_ADD_QUANTITY_FILL_COUNT = 0`
- `NORMAL_NEW_BUY_UNEXPLAINED_DROP_COUNT = 15`
- `PC_FINAL_ALLOCATION_OR_EXPLICIT_DEFERRAL_COVERAGE = 77.94%`
- `G117_ACTUAL_SCOPE_REPAIR_EFFECTIVE = YES`
- `NORMAL_NEW_BUY_CASH_PREFERRED_HARD_SKIP_COUNT = 0`
- `G115_ACTUAL_AUTHORITY_SCOPE = OTHER`
- `CASH_DELTA_EXPLAINED_BY_65500 = YES`
- `PNL_USED_AS_POLICY_VALIDATION = NO`
- `REPAIR_REQUIRED = YES`

## Repair Boundary

Narrow repair should target the PC final allocation / canonical deployment-set binding / PS consumer boundary:

PC final selected security rows with `pc_positive_executable_quantity_authority.status = PASS` and `ps_must_consume_canonical_quantity = True` must not be presented to PS as `DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION` solely via stale or contradictory deployment-set Cash-winner binding.

Do not change G117's normal `NEW_BUY` hard-skip repair. Do not change G115 ADD staged one-increment semantics.

## Final Decision

G118_EARLY_ACTUAL_ALLOCATION_DEFECT_CONFIRMED_READY_FOR_REPAIR
