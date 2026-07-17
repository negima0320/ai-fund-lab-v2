# Phase17-BV9 Historical Sell Submit Quantity Authority Fix

## Executive Summary

Phase17-BV9 fixed the Historical Submit SELL quantity authority contract.

The halted run `runtime-test-historical-extended-smoke-20260716T073342891117Z` stopped at `2026-07-01:submit` with exit code `20` because Submit Guard required Broker ReadOnly confirmation even in `historical_simulated` mode.

The target SELL order had sufficient Runtime-owned quantity:

- symbol: `70630`
- sell_quantity: `2500`
- current_quantity: `2500`
- broker_available_quantity: `2500`
- broker_restricted_quantity: `0`

The failure was not quantity insufficiency. It was an authority classification mismatch:

- observed source: `historical_runtime_owned_current`
- observed checked: `false`
- observed status: `BROKER_AVAILABLE_NOT_READONLY`

BV9 introduces the explicit Historical quantity authority source:

- `historical_simulated_broker_authority`

This source is accepted only for Historical Submit. Production and Demo still require Broker ReadOnly evidence.

Final judgment:

`PHASE17_BV9_HISTORICAL_SELL_QUANTITY_AUTHORITY_ACCEPTED`

Fresh rerun status:

`FRESH_RERUN_SAFE`

## Root Cause

Submit Pipeline already had a Historical quantity path, but `_sell_guard_evidence()` treated only `broker_readonly` as a checked available-quantity source.

The old effective condition was:

```python
broker_available_quantity_checked = broker_available_quantity_source == "broker_readonly"
```

Therefore Historical quantity evidence could carry the correct available quantity and still be rejected before submit.

The target run manifest confirms this:

- `final_state=REVIEW_REQUIRED`
- `blocked_count=1`
- `submitted_count=0`
- `broker_environment=historical_simulated`
- `broker_write=false`
- `sell_quantity_guard_status=BROKER_AVAILABLE_NOT_READONLY`
- `guard_reason=sell broker available quantity not confirmed by Broker ReadOnly evidence`

## Fix

Changed file:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`

The Historical SELL available quantity resolver now:

- reads Runtime-owned Current quantity from the Submit current summary
- computes restricted Historical SELL quantity from `persistent_ledger/orders.jsonl` minus filled Historical SELL executions in `persistent_ledger/executions.jsonl`
- exposes source `historical_simulated_broker_authority`
- sets `checked=true` only when Current quantity and broker issue-code normalization are valid
- keeps `production_equivalent=false`

Submit Guard now recognizes checked quantity sources:

- `broker_readonly`
- `historical_simulated_broker_authority`

Production/Demo continue to use the Broker ReadOnly path and fail closed when Broker ReadOnly evidence is missing.

## Environment Quantity Authority Contract

Production/Demo:

- Runtime-owned Current quantity must be sufficient.
- Broker ReadOnly available quantity must be present and sufficient.
- Missing Broker ReadOnly, stale Broker ReadOnly, symbol mismatch, and insufficient availability remain blocked/review-required.

Historical:

- Tachibana Broker ReadOnly is not used.
- Runtime-owned Historical Broker state, Persistent Ledger positions, and Historical open/restricted SELL order state are the quantity authority.
- Full liquidation is allowed when `sell_quantity == available_quantity`.
- Existing unfilled Historical SELL orders restrict available quantity.

## Full Liquidation Contract

For the target shape:

- current quantity: `2500`
- restricted quantity: `0`
- available quantity: `2500`
- sell quantity: `2500`

Submit Guard now returns:

- `broker_available_quantity_checked=true`
- `broker_available_quantity_source=historical_simulated_broker_authority`
- `sell_quantity_guard_status=PASS`
- `manual_review_required=false`

## Fail-Closed Conditions Preserved

BV9 does not relax these conditions:

- `sell_quantity > current_quantity`
- `sell_quantity > available_quantity`
- missing Current position
- issue-code normalization failure
- restricted quantity from existing SELL orders
- Production/Demo missing Broker ReadOnly
- Safety decision block
- Pending policy mismatch
- Pending/approval contract mismatch
- broker write guard

## Target Run Read-Only Preflight

No runtime_test run/resume/reset/rollback/close was executed.

The existing target run was inspected read-only. After the code fix, a read-only preflight using the target pending shape and an equivalent ALLOW safety decision shows:

- source: `historical_simulated_broker_authority`
- checked: `true`
- current_quantity: `2500`
- available_quantity: `2500`
- restricted_quantity: `0`
- guard_decision: `PASS`
- sell_quantity_guard_status: `PASS`
- manual_review_required: `false`

The existing halted run should not be resumed as the primary acceptance path. The safer operator path is close/reset/backup/plan/run from a clean baseline.

## Verification

Targeted BV9 tests:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv9_historical_sell_quantity_authority.py
5 passed
```

Related submit/sell guard regression:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase17_bv9_historical_sell_quantity_authority.py \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py \
  tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py \
  tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py \
  tests/runtime_v2/test_phase14d14_demo_sell_guarded_preflight.py \
  tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py
29 passed
```

Static checks:

```text
py_compile PASS
git diff --check PASS
```

Full runtime_v2 regression:

```text
918 passed, 5 failed
```

The five failures are pre-existing/unrelated Sell Planning PM fixture failures observed outside the BV9 Submit quantity authority call path. They do not involve `submit/pipeline.py` or the Historical quantity source added in BV9.

## Prohibited Operations Confirmation

Not executed:

- `runtime_test.py run`
- `runtime_test.py resume`
- `runtime_test.py reset`
- `runtime_test.py rollback`
- `runtime_test.py close`
- Frozen Run mutation
- `.runtime` manual edit
- Ledger manual edit
- Broker write
- Order submit against a real broker
- External notification
- J-Quants fetch

## Next Operator Action

Use a fresh rerun rather than resuming the halted target run.

Recommended operator sequence:

1. close the halted run
2. reset `historical-extended-smoke`
3. backup the clean baseline
4. plan the target range
5. run from the beginning

Do not use the existing halted run as the acceptance run.
