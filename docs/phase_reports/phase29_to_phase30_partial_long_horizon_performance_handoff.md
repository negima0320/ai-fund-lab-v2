# Phase29 to Phase30 Partial Long-Horizon Performance Handoff

Task ID: `Phase29-L21T-Y`

Status:

```text
READ_ONLY DOCUMENTATION HANDOFF
PERFORMANCE_EVIDENCE_PARTIAL
LONG_HORIZON_FULL_COMPLETION_PENDING
NO RUNTIME / STRATEGY / MODEL / CONFIG CHANGE
NO TARGET RUN MUTATION
NO FRESH-RUN / RESUME / REPLAY / RECOVERY
```

Primary Judgment:

```text
PHASE29_L21T_Y_PHASE30_HANDOFF_UPDATED_WITH_PARTIAL_LONG_HORIZON_PERFORMANCE_EVIDENCE
```

## Evidence Source

Target run:

```text
runtime-test-historical-smoke-20260812T212155604711Z
```

Read-only sources inspected:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T212155604711Z/plan.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T212155604711Z/run_state.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T212155604711Z/daily/*
.runtime/persistent_ledger/state.json
.runtime/persistent_ledger/cash.jsonl
.runtime/persistent_ledger/positions.jsonl
```

The run is not a completed 4-year Historical baseline.  It is partial
long-horizon evidence only.

## Status Separation

Runtime Validation Status:

```text
HALT / NOT CLOSED
```

`run_state.json` records:

```text
status = HALT
next_job = 2023-06-23:execution
completed_business_day_count = 213
first_completed_business_day = 2022-08-10
last_completed_business_day = 2023-06-22
halted_business_date = 2023-06-23
```

Performance Evidence Status:

```text
PERFORMANCE_EVIDENCE_PARTIAL
```

The run has usable partial evidence through the halted 2023-06-23 evidence
boundary, but the full 977BD plan is incomplete.

Strategy Performance Judgment:

```text
CAPITAL_UTILIZATION_IMPROVED_BUT_RETURN_NOT_ENOUGH_PHASE30_ATTRIBUTION_REQUIRED
```

Long-Horizon Completion Status:

```text
FULL_LONG_HORIZON_NOT_COMPLETE
```

Plan evidence:

```text
requested_start_date = 2022-08-10
requested_end_date = 2026-08-09
resolved_date_from = 2022-08-10
resolved_date_to = 2026-08-07
resolved_business_day_count = 977
initial_cash = 1,000,000 JPY
```

## Partial Performance Evidence

Using the runtime-owned persistent ledger state as of `2023-06-23`:

| Metric | Partial Value |
| --- | ---: |
| Initial cash | `1,000,000 JPY` |
| Cash | `129,890 JPY` |
| Buying power | `129,890 JPY` |
| Market value | `947,170 JPY` |
| Total equity | `1,077,060 JPY` |
| Observed partial return | `+7.706%` |
| Final cash ratio | `12.0597%` |
| Final gross exposure ratio | `87.9403%` |
| Open position count | `8` |
| Realized PnL | `4,900 JPY` |
| Runtime-owned unrealized PnL field | `113,830.489174 JPY` |

Using daily carry-forward from persistent ledger cash/position snapshots across
the 214 available daily directories (`2022-08-10` through `2023-06-23`):

| Metric | Partial Value |
| --- | ---: |
| Average cash | `436,597.34 JPY` |
| Average market value | `569,029.02 JPY` |
| Average cash ratio | `43.4813%` |
| Average gross exposure ratio | `56.5187%` |
| Carried-ledger max drawdown estimate | `-14.2728%` |

Position count distribution from the same carried-ledger series:

| Position count | Days |
| ---: | ---: |
| 1 | `8` |
| 2 | `24` |
| 3 | `84` |
| 4 | `36` |
| 5 | `40` |
| 6 | `14` |
| 7 | `3` |
| 8 | `5` |

Observed fills from run-scoped `daily/*/execution/fills.json`:

| Fill Metric | Partial Value |
| --- | ---: |
| Total fills | `145` |
| BUY fills | `62` |
| SELL fills | `83` |
| BUY notional | `6,673,860 JPY` |
| SELL notional | `5,803,750 JPY` |
| Dates with fills | `100` |

Strategy artifact observations across the available partial window:

| Artifact Metric | Partial Value |
| --- | ---: |
| Runtime Planning positive `BUY_NEW` plans | `184` |
| Runtime Planning positive `BUY_ADD` plans | `19` |
| Runtime Planning positive `SELL_EXIT` plans | `41` |
| Runtime Planning positive `SELL_REDUCE` plans | `4` |
| Position Management `HOLD` decisions | `358` |
| Position Management `ADD` decisions | `330` |
| Position Management `REDUCE` decisions | `60` |
| Position Management `EXIT` decisions | `41` |

These are partial run-observability counts, not final Phase30 attribution.

## Phase30 Interpretation

The partial evidence should be treated as:

```text
Capital utilization improved, especially by the final observed state.
Return is not sufficient relative to deployed capital and drawdown.
Phase30 must separate capital deployment from deployed capital quality.
```

The final observed cash ratio of `12.0597%` and gross exposure ratio of
`87.9403%` show that the stack can reach high deployment.  The average cash
ratio of `43.4813%` and average exposure of `56.5187%` show that deployment was
not consistently high across the whole partial window.  The observed return of
`+7.706%` through roughly the first 214 daily evidence directories is not enough
to justify declaring the Strategy performance problem solved.

## Phase30 Required Analysis Axes

Phase30 attribution should measure at least:

- capital utilization;
- average cash;
- average gross exposure;
- final cash and gross exposure;
- BUY_NEW conversion;
- BUY_ADD conversion;
- ADD notional and effectiveness;
- position count distribution;
- concentration;
- winner and loser hold duration;
- REDUCE frequency;
- EXIT timing;
- re-entry count and interval;
- campaign duration and campaign PnL;
- turnover;
- realized and unrealized PnL;
- profit factor when derivable;
- win rate;
- average winner and average loser;
- max drawdown;
- Return/MDD;
- opportunity rank attribution;
- top-ranked opportunity conversion;
- skipped opportunity attribution;
- lot, cap, cash, and concentration constraints.

Center question:

```text
Capital Utilization improved but Return is not enough.
Distinguish capital deployment from deployed capital quality.
```

## Constraints For Phase30

Phase30 must start with read-only attribution.  Do not change Strategy,
Runtime, model, config, thresholds, Safety, Pending, Ledger, Current, Accepted
Generation, or Historical-specific behavior before the attribution evidence
explains the bottleneck.

This handoff does not authorize direct resume of the target run and does not
resolve the 2023-06-23 Runtime HALT.
