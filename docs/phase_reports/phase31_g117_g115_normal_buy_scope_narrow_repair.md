# Phase31-G117 — G115 Normal NEW_BUY Scope Regression Narrow Repair

## PRIMARY_JUDGMENT

G117_G115_NORMAL_BUY_SCOPE_REPAIR_ACCEPTED

## Scope

- Phase: Phase31
- Repair owner: PORTFOLIO_CONSTRUCTION
- Repaired boundary: `apply_lot_aware_final_reallocation()`
- Fresh-run/resume/replay/long Historical: NO
- Strategy parameter / Market Quality / Risk Pacing / ranking changes: NO
- Pending / Submit / Execution / Safety changes: NO

## Repair Summary

G116 confirmed that normal `NEW_BUY` rows with `pre_lot_binding_result = CASH_PREFERRED` were being hard-skipped before the canonical final lot-aware allocation loop. G117 narrows the predicate so only true terminal pre-lot states remain hard-skipped:

- `FAIL_CLOSED`
- `BLOCKED`

`CASH_PREFERRED` remains decision-time competition evidence, but it is no longer treated as a Safety-like terminal skip for normal `NEW_BUY` rows. The row can now enter the canonical final lot-aware allocation loop, where Cash can still remain as residual or win through the normal final competition path.

G115 ADD staged marginal behavior is preserved. `BUY_ADD` still receives the one-increment staged authority and does not authorize a full requested block.

## Code Changes

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
  - Removed `CASH_PREFERRED` from the terminal hard-skip set in `apply_lot_aware_final_reallocation()`.
  - Kept `FAIL_CLOSED` / `BLOCKED` fail-closed behavior unchanged.

## Regression Coverage

Added:

- `tests/strategy/test_phase31_g117_normal_buy_scope_repair.py`

Updated existing expectations:

- `tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py`
  - Normal `NEW_BUY` `CASH_PREFERRED` is no longer expected to be terminal skipped.
- `tests/strategy/test_phase22_e_portfolio_construction.py`
  - ADD rebatch expectation now reflects G115 staged one-increment authority.

## 2022-10-03 Actual-Shaped Gate

The new G117 regression models the confirmed actual shape:

- 22 positive `NEW_BUY` draft targets
- 0 ADD candidates
- `CASH_PREFERRED` pre-lot evidence present
- final allocation iterations nonzero
- multiple normal `NEW_BUY` allocations survive
- no `g43_binding_cash_preferred` hard-skip reason

Result:

`20221003_NORMAL_BUY_ACTUAL_PATH_GATE = PASS`

## G115 ADD Preservation

The separate G117 ADD fixture confirms:

- `BUY_ADD` with `CASH_PREFERRED` still enters the G115 staged frontier guard
- authorized increment is one executable lot
- full requested block is not authorized
- PS quantity owner remains Position Sizing

Result:

`G115_ADD_BEHAVIOR_PRESERVATION_GATE = PASS`

## Required Judgments

- `G117_NORMAL_NEW_BUY_SCOPE_REPAIRED = YES`
- `G115_AUTHORITY_SCOPE_AFTER_REPAIR = ADD_PLUS_NEW_BUY_COMPARISON_ONLY`
- `NORMAL_NEW_BUY_CASH_PREFERRED_HARD_SKIP = NO`
- `NORMAL_NEW_BUY_CAN_STILL_BE_ALLOCATED_IF_CANONICAL_FINAL_COMPETITION_ALLOWS = YES`
- `BUDGET_LOOP_TERMINATED_PREMATURELY = NO`
- `20221003_NORMAL_BUY_ACTUAL_PATH_GATE = PASS`
- `G115_ADD_BEHAVIOR_PRESERVATION_GATE = PASS`
- `ADD_MARGINAL_PREFERRED_ONE_INCREMENT = YES`
- `COMPARABLE_FULL_BLOCK_FORBIDDEN = YES`
- `NORMAL_BUY_CANDIDATE_SELECTION_CHANGED = NO`
- `NORMAL_BUY_RANKING_CHANGED = NO`
- `G97_RECONSIDERATION_PARTICIPATION_PRESERVED = YES`
- `G93_DEAD_END_RETURNED = NO`
- `G110_CAMPAIGN_LIFECYCLE_PRESERVED = YES`
- `SAFETY_CHANGED = NO`
- `SAFETY_TERMINAL_RESURRECTION_COUNT = 0`
- `FUTURE_INFORMATION_USED = NO`
- `HISTORICAL_OUTCOME_USED = NO`
- `G117_ACCEPTED = YES`

## Test Results

PASS:

- `PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g117_normal_buy_scope_repair.py`
  - `2 passed`
- `PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g117_normal_buy_scope_repair.py tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase31_g90_cash_preferred_aggregate_resolver.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase22_e_portfolio_construction.py`
  - `139 passed`
- `PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g113_add_marginal_competition_shadow.py -k 'not actual' tests/strategy/test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py -k 'not actual'`
  - `5 passed, 2 deselected`
- `PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase31_g62_position_sizing_g61_binding.py tests/safety/test_reconciliation.py tests/safety/test_lock_state_resolver.py`
  - `175 passed`
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m compileall -q src tests/strategy/test_phase31_g117_normal_buy_scope_repair.py`
  - PASS
- `git diff --check`
  - PASS

Skipped / unavailable:

- `tests/strategy/test_phase31_g110_actual_path_campaign_activation.py`
  - `1 skipped`
- Artifact-dependent actual-run tests in G113/G99/G102 could not be fully executed because their referenced run artifacts are not present in this workspace. This was an artifact availability issue, not a behavioral assertion failure.

Initial compile note:

- Running `compileall` without `PYTHONPYCACHEPREFIX` failed because Python attempted to write pycache files under sandbox-restricted `~/Library/Caches`. Re-running with a writable pycache prefix passed.

## Final Decision

G117_G115_NORMAL_BUY_SCOPE_REPAIR_ACCEPTED
