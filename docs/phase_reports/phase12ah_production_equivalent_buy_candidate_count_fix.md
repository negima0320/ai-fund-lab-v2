# Phase12-AH Production-equivalent BUY Candidate Count Fix

## Status

```text
PHASE12AH_PRODUCTION_EQUIVALENT_BUY_CANDIDATE_COUNT_FIX_COMPLETE
```

Phase12-AH removed the implicit one-BUY-item cap from Operations daily plan generation and replaced it with explicit Production-equivalent Operations defaults.

No Demo order, Production order, Production unlock, LINE actual send, AI retraining, backtest, raw request save, raw response save, secret save, Phase9 change, or existing 2026-06-30 runtime artifact modification was executed.

## Root Cause

BUY was limited to one item by:

```text
src/ai_fund_lab_v2/operations/market_refresh.py
load_feature_buy_candidates(..., max_items: int = 1)
```

`run_daily_plan` called this without arguments, so eligible candidates were reduced to `head(1)`.

This was not an AI decision, not an Approval decision, and not a capital constraint.

## Fix

Added explicit Operations defaults:

```text
max_buy_orders_per_day=5
max_new_positions_per_day=5
max_positions=5
max_total_exposure_ratio=0.85
candidate_count_environment_specific=false
```

Updated daily plan to call:

```text
load_feature_buy_candidates(..., max_items=operations_runtime_config.max_buy_orders_per_day)
```

Demo and Production candidate count logic is the same. There is no `if demo` / `if production` candidate-count branch.

## Capital Allocation Status

Capital Allocation AI is not fully connected to Operations daily plan.

Phase12-AH intentionally implements the minimum safe correction:

```text
Step 1: explicit max_buy_orders_per_day=5
Step 2: submit-side per-item notional normalization, MAX_EXPOSURE, buying_power, duplicate guard
Step 3: full Capital Allocation AI connection deferred to Phase13 or next design phase
```

Deferred reason:

```text
Full capital allocation integration changes portfolio construction and should be reviewed as a separate design phase.
```

## Approval / Submit

Approval already supports multiple approved item ids.

Phase12-AH added / confirmed:

```text
auto approval checks total BUY notional against max_notional and buying_power
submit processes items sequentially
remaining_approval_budget is decremented after an accepted BUY item
projected_exposure is accumulated after an accepted BUY item
projected_buying_power_usage is accumulated after an accepted BUY item
duplicate active order blocks only the matching item
failed item status is BLOCKED_ITEM
```

Submit still blocks before Broker API when:

```text
approval budget exceeded
buying power exceeded
MAX_EXPOSURE exceeded
duplicate active same-side same-code order exists
broker issue code normalization fails
limit_price / notional is not positive on wire path
```

## Today Artifact Policy

Existing 2026-06-30 artifacts were not regenerated, edited, deleted, or superseded:

```text
.runtime/operations/order_plan/2026-06-30/order_plan.json
.runtime/operations/approval_artifact/2026-06-30/approval_artifact.json
```

The change applies to the next `run_daily_plan` execution for future trade dates, or to an explicitly requested regenerated date.

## Tests

Executed:

```bash
python3 -m pytest tests/phase12/test_operations_market_refresh.py tests/phase12/test_phase12_approval.py tests/phase12/test_phase12_demo_submit_guard.py -q
python3 -m pytest tests/phase12 -q
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/operations/market_refresh.py src/ai_fund_lab_v2/operations/operations.py scripts/run_daily_plan.py scripts/run_approval_prepare.py scripts/run_demo_submit.py
```

Results:

```text
targeted pytest: 15 passed
phase12 pytest: 69 passed
py_compile: PASS
```

## Remaining Gaps

```text
Capital Allocation AI is not fully connected to Operations daily plan
max_positions is recorded as runtime config but not yet enforced as a full portfolio-construction constraint
daily buy notional is guarded by approval max_notional / buying_power / MAX_EXPOSURE, but no separate max_daily_buy_notional config exists yet
first live daily_plan after this change has not yet been observed
```

