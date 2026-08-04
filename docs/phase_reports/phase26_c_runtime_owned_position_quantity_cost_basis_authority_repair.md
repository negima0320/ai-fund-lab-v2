# Phase26-C Runtime-owned Position Quantity / Cost Basis Authority Repair

## Judgment

Primary Judgment:

`PHASE26_C_RUNTIME_OWNED_POSITION_QUANTITY_COST_BASIS_AUTHORITY_REPAIRED`

Secondary Judgments:

- Phase26-B cash / valuation repair preserved.
- Quantity / cost-basis validation remains fail-closed.
- No Historical-only bypass, fallback, or guard weakening was added.

User rerun readiness: `READY`

## Primary Root Cause

The first divergence occurred on the cumulative path from `2023-01-04` to `2023-01-18`.

Two producer/consumer rules were incomplete:

1. `HistoricalExecutionSnapshotProvider` produced target-date valuation rows for no-fill existing positions, but their `position_ref` could remain tied to the prior position `as_of`. Ledger dedup then skipped target-date valuation records for symbols such as `83060` and `94320`.
2. `project_runtime_owned_fills_to_current()` consumed the full Persistent Ledger execution history on every projection. On `2023-01-18`, it re-applied already-reflected `2023-01-04` BUY executions while also seeding from Current, causing quantity/cost-basis mismatch for `76470`, `83060`, and `94320`.

3BD passed because it did not exercise a later execution day with prior Runtime-owned positions plus same-day SELL REDUCE / BUY activity. The cumulative run failed when `2023-01-18` had both old positions and new accepted fills.

Broken edge:

`Historical market / valuation evidence -> HistoricalExecutionSnapshotProvider -> broker readonly snapshot -> ledger position records -> runtime-owned fill projection -> quantity/cost-basis validation -> Runtime-owned Current`

## Canonical Authorities

| Field | Canonical Authority |
|---|---|
| quantity | Runtime-owned Current quantity plus accepted execution deltas after Current `as_of` and up to target business date |
| average_price | Acquisition authority: existing Current average cost; BUY ADD weighted by accepted fill notional; SELL REDUCE preserves proportional cost |
| cost_basis | Acquisition authority: `average_price * active quantity`, seeded from Current and updated only by accepted fill notional |
| market_price | Target business-date valuation evidence from execution readonly position records |
| market_value | `quantity * target-date market price` from latest target-date ledger position evidence |
| unrealized_pnl | `market_value - cost_basis` |
| as_of | Target business date for valuation-bearing Current rows |
| source | `runtime_v2_runtime_owned_fill_projection` for projected Current |

Acquisition cost and market valuation are intentionally separated.

## Before / After

Before failure evidence:

| Symbol | State |
|---|---|
| `76470` | Current held `5400 @ 28`, SELL REDUCE `1700 @ 27`; projection reprocessed old BUY and current state together, causing mismatch |
| `83060` | Current held `100 @ 894`; no-fill target-date valuation row was skipped by stale ref dedup |
| `94320` | Current held `1000 @ 150.5`; no-fill target-date valuation row was skipped by stale ref dedup |

After targeted evidence:

| Symbol | Quantity | Average Price | Cost Basis | Market Value | Unrealized PnL | Date |
|---|---:|---:|---:|---:|---:|---|
| `76470` | 3700 | 28.0 | 103600.0 | 96200.0 | -7400.0 | 2023-01-18 |
| `83060` | 100 | 894.0 | 89400.0 | 95060.0 | 5660.0 | 2023-01-18 |
| `94320` | 1000 | 150.5 | 150500.0 | 149700.0 | -800.0 | 2023-01-18 |
| `93180` | 59600 | 3.0 | 178800.0 | 178800.0 | 0.0 | 2023-01-18 |

Function-level replay on copied failed ledger state:

- Projection status: `PASS`
- Projected cash: `476000.0`
- Position count: `4`
- Quantity/cost-basis mismatch: none

The copied failed ledger lacked target-date no-fill records for `83060` and `94320` because it was produced before the provider fix; the new provider test verifies date-scoped refs for no-fill valuation rows.

## Implementation

Changed:

- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`
  - Filters canonical execution events to `Current.as_of < event.business_date <= target business_date`.
  - Seeds acquisition cost from Current and applies only pending accepted fills.
  - Starts BUY ADD from existing Current quantity when a position already exists.
  - Keeps full EXIT out of active Current.
  - Adds fail-closed validation for `cost_basis != average_price * quantity`.

- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`
  - Date-scopes historical cash and position refs.
  - Date-scopes no-fill valuation position refs by target business date.
  - Keeps already-applied BUY evidence from being applied again.

- `tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py`
  - Adds no-fill valuation, SELL REDUCE, new BUY, BUY ADD, full EXIT, multi-day cumulative, Phase26-B non-regression, and negative mismatch tests.

## Reference Classification

- CANONICAL_PRODUCER:
  - `HistoricalExecutionSnapshotProvider`
  - `project_position_to_ledger_record`
  - `project_runtime_owned_fills_to_current`

- CANONICAL_CONSUMER:
  - `run_reconciliation`
  - Runtime Current consumers in planning / PM / reporting

- VALIDATION_ONLY:
  - `runtime_owned_quantity_cost_basis_mismatch`
  - `runtime_owned_cost_basis_average_price_mismatch`
  - `POSITION_MARKET_VALUE_MISMATCH`
  - `TOTAL_EQUITY_MISMATCH`

- OBSERVABILITY_ONLY:
  - runtime reports, `runtime_test.py` evidence extraction, phase reports

- TEST_ONLY:
  - `tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py`
  - existing reconciliation and Phase26-A tests

- DOCUMENTATION_ONLY:
  - architecture and phase report references

- INVALID_AUTHORITY_CONSUMER:
  - `0` found in Phase26-C changed surface.

## Safety Confirmation

- Validation weakened: false
- Fallback added: false
- Historical-only bypass added: false
- Strategy behavior changed: false
- Submit Guard weakened: false
- Safety Hard Maximum changed: false
- `target_position_count` reintroduced: false

## Regression

- Compile: PASS
- Targeted tests: PASS, `12 passed`
- Phase26-B non-regression: PASS, `18 passed`
- Phase26-A / target_position_count non-regression: PASS, `12 passed`
- Negative mismatch detection: PASS
- Fresh-run/resume/3BD/10BD/100BD: not executed

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
