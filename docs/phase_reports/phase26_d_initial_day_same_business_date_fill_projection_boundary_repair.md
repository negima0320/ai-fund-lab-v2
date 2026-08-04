# Phase26-D Initial-Day / Same-Business-Date Fill Projection Boundary Repair

## Primary Judgment

`PHASE26_D_INITIAL_DAY_SAME_BUSINESS_DATE_FILL_PROJECTION_BOUNDARY_REPAIRED`

## Primary Root Cause

Phase26-C fixed cumulative replay by filtering execution events with a date boundary. That exposed an initial-day boundary defect:

- Initial Current could be stamped with `as_of == target_business_date` while still being pre-fill.
- Same-business-date executions were then excluded from cash projection.
- Position rows still came from target-date broker/ledger position evidence, so positions appeared while cash stayed pre-fill.

This produced double-counted total equity on `2023-01-04`.

Failure run:

- `runtime-test-historical-smoke-20260804T003024820830Z`
- `2023-01-04:execution`
- exit code `20`
- reason `reconciliation findings=3`

## Broken Edge

`Current pre-fill state -> canonical execution event selection -> runtime-owned fill projection -> Current cash / positions -> reconciliation`

The broken boundary was date-only. It could not distinguish:

- same-date pre-fill Current, where fills must be applied
- same-date post-fill Current, where fills must not be replayed
- mixed same-date Current, where only missing execution identities must be applied

## Reconciliation Findings

From the failed Current and broker snapshot:

| Finding | Expected | Actual |
|---|---:|---:|
| `CASH_MISMATCH` | 1000000.0 | 608900.0 |
| `BUYING_POWER_MISMATCH` | 1000000.0 | 608900.0 |
| `TOTAL_EQUITY_MISMATCH` | 1391100.0 | 1000000.0 |

## Before / After

Before:

- accepted BUY cash effect total: `-391100`
- projected cash: `1000000`
- projected market_value: `391100`
- projected total_equity: `1391100`
- projected positions: `3`

After:

- projected cash: `608900`
- projected market_value: `391100`
- projected total_equity: `1000000`
- projected positions: `3`
- applied execution identities recorded: `3`

Position after repair:

| Symbol | Quantity | Average Price | Cost Basis | Market Value |
|---|---:|---:|---:|---:|
| `83060` | 100 | 894.0 | 89400.0 | 89400.0 |
| `76470` | 5400 | 28.0 | 151200.0 | 151200.0 |
| `94320` | 1000 | 150.5 | 150500.0 | 150500.0 |

## Canonical Boundary

Projection now uses immutable execution identity as the primary boundary.

An execution is applied only when:

```text
execution.business_date <= target_business_date
AND execution identity is not already in Current runtime_owned_projection.applied_execution_* metadata
AND execution is not earlier than the Current as_of boundary
```

Same-date events are allowed for pre-fill Current. Same-date events are skipped if explicit applied execution metadata is present. For legacy post-fill Current without identity metadata, `runtime_v2_runtime_owned_fill_projection` source plus active positions is treated as already projected for that same date to preserve Phase26-C replay protection.

## Idempotency Proof

The focused test invokes same-date projection twice:

1. First call applies three BUY fills and records three applied execution dedup keys.
2. Second call sees the same identities in Current metadata and applies zero additional fills.

Cash, positions, and total equity remain unchanged on the second call.

Partial same-date Current is also covered: if one execution identity is already present, only the two missing identities are applied.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`
- `tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py`

## Safety Confirmation

- Strategy behavior changed: false
- Submit Guard weakened: false
- Safety weakened: false
- Reconciliation weakened: false
- Fallback added: false
- Historical-only bypass added: false
- `target_position_count` reintroduced: false

## Regression

- Compile: PASS
- Projection / Phase26-B / Phase26-C / Phase26-D targeted tests: PASS
- Reconciliation regression: PASS
- Phase26-A target_position_count non-regression: PASS
- fresh-run / resume / 3BD / 10BD / 100BD: not executed

## User Rerun Command

Codex did not execute this command.

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --date-from 2023-01-04 \
  --business-days 100 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```
