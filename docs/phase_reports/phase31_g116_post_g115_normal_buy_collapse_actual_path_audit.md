# Phase31-G116 — Post-G115 Normal BUY Collapse Actual-Path Regression Audit

## PRIMARY_JUDGMENT

G116_G115_NORMAL_BUY_REGRESSION_CONFIRMED_READY_FOR_NARROW_REPAIR

## Scope

- Task type: READ-ONLY actual-path regression audit
- Baseline run: `runtime-test-historical-extended-smoke-20260824T055234719725Z`
- Post-G115 run: `runtime-test-historical-extended-smoke-20260825T125851128489Z`
- Target date: `2022-10-03`
- Code/config/run mutation: NO
- Fresh-run/resume/replay/long Historical executed by this audit: NO
- Future PnL/outcome used as decision evidence: NO

## Executive Conclusion

The post-G115 2022-10-03 normal BUY collapse is a real regression.

The first common divergence is not Candidate generation, BUY eligibility, Portfolio Policy, Risk Pacing, or ADD marginal competition. Both runs have the same effective PC draft shape on 2022-10-03:

- PC members: 50
- PM ADD intents: 0
- positive NEW_BUY draft targets: 22
- total draft target: 0.733506

The divergence occurs at the final PC / lot-aware final reallocation boundary. Post-G115, normal NEW_BUY rows are skipped before final allocation iteration because `pre_lot_binding_result == CASH_PREFERRED` is treated as a hard skip for non-ADD rows. This yields:

- post-G115 final positive NEW_BUY targets: 0
- post-G115 final allocation iterations: 0
- post-G115 final Runtime BUY count: 2
- post-G115 filled BUY symbols: `37820`, `94340`

Baseline behavior on the same date produced 7 filled normal BUY holdings:

`33700:100`, `37820:400`, `83060:100`, `89180:3700`, `92420:100`, `93600:100`, `94340:200`

## Stage Comparison

| Stage | Baseline | Post-G115 | Divergence |
|---|---:|---:|---|
| PC draft members | 50 | 50 | NO |
| PM ADD intents | 0 | 0 | NO |
| positive NEW_BUY draft targets | 22 | 22 | NO |
| draft target total | 0.733506 | 0.733506 | NO |
| G115 ADD authority rows | absent | 0 | NO direct ADD effect |
| final positive NEW_BUY targets | 9 | 0 | YES |
| final allocation iterations | 9 | 0 | YES |
| Runtime BUY count | 9 | 2 | YES |
| filled baseline-anchor BUY count | 7 | 2 | YES |

## Per-Symbol Anchor Results

| Symbol | Baseline fill | Post-G115 result | First observed loss mode |
|---|---:|---|---|
| 33700 | 100 | no fill | final PC target zero; residual row then lot-infeasible |
| 37820 | 400 | fill 400 | preserved through residual / G61 / PS / Runtime |
| 83060 | 100 | no fill | final PC target zero; residual row then lot-infeasible |
| 89180 | 3700 | no fill | PS quantity exists, but Runtime NO_ORDER after upstream defeated/not-selected context |
| 92420 | 100 | no fill | final PC target zero; residual row then lot-infeasible |
| 93600 | 100 | no fill | skipped before baseline-style lot promotion; later concentration context remains zero |
| 94340 | 200 | fill 200 | preserved through residual / G61 / PS / Runtime |

## Root Cause Evidence

Post-G115 actual `lot_aware_final_reallocation` has:

- `phase29_l19_allocation_iterations = []`
- skipped rows for the baseline-anchor NEW_BUY symbols with:
  - `skip_reason = g43_binding_cash_preferred`
  - `pre_lot_binding_result = CASH_PREFERRED`
  - reason codes including `CAUTIOUS_COMPARABLE_MARGINAL_CASH_PREFERRED` and `CAUTIOUS_MARGINAL_LOST_TO_CASH`

Baseline actual `lot_aware_final_reallocation` has allocation iterations for:

`94340`, `37820`, `93600`, `33700`, `83060`, `92420`, `58200`, `89180`, `76470`

The relevant current implementation boundary is `src/ai_fund_lab_v2/strategy/portfolio_construction.py` in `apply_lot_aware_final_reallocation()`:

- final risk pacing evidence is propagated into pre-lot competition
- pre-lot interaction results are bound by symbol
- rows with `pre_lot_binding_result in {"CASH_PREFERRED", "FAIL_CLOSED", "BLOCKED"}` are skipped unless the row is `BUY_ADD` with `CASH_PREFERRED`

That exception is ADD-specific. Normal NEW_BUY rows therefore become hard-deferred by `CASH_PREFERRED` before the old final lot-aware allocation loop can execute.

## ADD Control

2022-10-03 has no ADD candidates in the actual PC path:

- `20221003_ADD_CANDIDATE_COUNT = 0`
- G115 shadow `canonical_add_marginal_capital_competition`:
  - `shadow_increment_count = 0`
  - `add_count = 0`
  - `new_buy_count = 0`
  - `security_frontier_symbols = []`
- G115 authoritative `canonical_add_marginal_capital_competition_authority`:
  - `authority_rows = 0`
  - `authorized_increment_count = 0`
  - `remaining_budget_after_authority = 0.74`

Therefore the 2022-10-03 collapse is not caused by repeated ADD increments consuming budget. It is caused by the G115-era final PC path applying CASH_PREFERRED pre-lot binding to normal NEW_BUY allocation scope.

## Required Classifications

- `REGRESSION_PRESENT_BEFORE_REPEATED_ADD = YES`
- `FIRST_COMMON_REGRESSION_BOUNDARY = final PC allocation / lot-aware final reallocation`
- `NEW_BUY_NORMALIZATION_CHANGED_TOTAL_BUY_AUTHORITY = YES`
- `NEW_BUY_INCORRECTLY_LIMITED_TO_ONE_INCREMENT = NO`
- `NEW_BUY_INCORRECTLY_USING_ADD_CLASS_SEMANTICS = NO`
- `G115_AUTHORITY_SCOPE = ENTIRE_SECURITY_ALLOCATION`
- `G115_SCOPE_EXCEEDS_G114_CONTRACT = YES`
- `BUDGET_LOOP_TERMINATED_PREMATURELY = YES`
- `20221003_ADD_CANDIDATE_COUNT = 0`
- `G115_ACTUAL_CONFORMS_TO_G114 = NO`
- `G116_ROOT_CAUSE_CLASS = D`
- `SAFE_NARROW_REPAIR_POSSIBLE = YES`
- `REPAIR_REQUIRED = YES`

## Root Cause Class

`G116_ROOT_CAUSE_CLASS = D`

Cash / residual preference is winning as a hard pre-lot skip for normal NEW_BUY rows, before the final lot-aware allocation loop can perform the prior normal security allocation comparison. Secondary symptoms match:

- B: G115-era implementation scope affects whole security allocation, not only ADD marginal competition.
- C: the allocation loop is effectively terminated before any final allocations are attempted.
- F: NEW_BUY final frontier population is lost.

The narrowest confirmed repair boundary is the final PC / lot-aware final reallocation pre-lot binding predicate. A repair should preserve G115 ADD staged-frontier behavior while preventing ADD-specific CASH_PREFERRED handling from suppressing normal NEW_BUY allocation authority.

## Constraints Confirmation

- `CODE_CHANGED = NO`
- `CONFIG_CHANGED = NO`
- `RUN_MODIFIED = NO`
- `FRESH_RUN_EXECUTED = NO`
- `RESUME_EXECUTED = NO`
- `REPLAY_EXECUTED = NO`
- `LONG_HISTORICAL_EXECUTED = NO`
- `FUTURE_INPUT_COUNT = 0`
- `HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0`
