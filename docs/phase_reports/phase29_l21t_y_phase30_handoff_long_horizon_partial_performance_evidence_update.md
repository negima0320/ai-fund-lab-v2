# Phase29-L21T-Y Phase30 Handoff / Long-Horizon Partial Performance Evidence Update

## Scope

READ-ONLY EVIDENCE REVIEW / DOCUMENTATION UPDATE ONLY.

Codex did not run fresh-run, resume-run, replay, recovery, long Historical, or
runtime mutation.  Codex did not change Runtime, Strategy, Model, Config,
Threshold, Schema, Pending, Ledger, Current State, or Accepted Generation.

Target run:

```text
runtime-test-historical-smoke-20260812T212155604711Z
```

## Primary Judgment

`PHASE29_L21T_Y_PHASE30_HANDOFF_UPDATED_WITH_PARTIAL_LONG_HORIZON_PERFORMANCE_EVIDENCE`

## Documents Updated

- `docs/phase_reports/phase29_to_phase30_partial_long_horizon_performance_handoff.md`
- `docs/phase_reports/phase30_a_entry_gate_100bd_baseline_status.md`
- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase29_l21t_y_phase30_handoff_long_horizon_partial_performance_evidence_update.md`

## Evidence Reviewed

Mandatory / contextual documents reviewed included:

- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase30_a_entry_gate_100bd_baseline_status.md`
- `docs/phase_reports/phase29_l_multi_year_historical_validation_preflight_and_handoff.md`
- `docs/phase_reports/phase29_l21t_w_buy_item_scoped_review_pending_lifecycle_terminal_state_repair.md`
- `docs/phase_reports/phase29_l21t_x_historical_execution_reconciliation_authority_root_cause_and_repair.md`

Run evidence inspected read-only:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T212155604711Z/plan.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T212155604711Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T212155604711Z/daily/*`
- `.runtime/persistent_ledger/state.json`
- `.runtime/persistent_ledger/cash.jsonl`
- `.runtime/persistent_ledger/positions.jsonl`
- run-scoped `daily/*/execution/fills.json`
- run-scoped Strategy artifacts under `daily/*/strategy/`

## Status Separation

Runtime Validation Status:

```text
HALT / NOT CLOSED
```

Performance Evidence Status:

```text
PERFORMANCE_EVIDENCE_PARTIAL
```

Strategy Performance Judgment:

```text
CAPITAL_UTILIZATION_IMPROVED_BUT_RETURN_NOT_ENOUGH_PHASE30_ATTRIBUTION_REQUIRED
```

Long-Horizon Completion Status:

```text
FULL_LONG_HORIZON_NOT_COMPLETE
```

## Run State Evidence

`plan.json`:

```text
requested_start_date = 2022-08-10
requested_end_date = 2026-08-09
resolved_date_from = 2022-08-10
resolved_date_to = 2026-08-07
resolved_business_day_count = 977
initial_cash = 1,000,000 JPY
```

`run_state.json`:

```text
status = HALT
next_job = 2023-06-23:execution
completed_business_day_count = 213
first_completed_business_day = 2022-08-10
last_completed_business_day = 2023-06-22
halted_business_date = 2023-06-23
```

The run has 214 daily evidence directories through `2023-06-23`, but the final
977BD Historical validation is not complete.

## Partial Performance Evidence

Persistent ledger state as of `2023-06-23`:

| Metric | Value |
| --- | ---: |
| Cash | `129,890 JPY` |
| Buying power | `129,890 JPY` |
| Market value | `947,170 JPY` |
| Total equity | `1,077,060 JPY` |
| Observed partial return | `+7.706%` |
| Final cash ratio | `12.0597%` |
| Final gross exposure ratio | `87.9403%` |
| Position count | `8` |

Daily carry-forward ledger snapshot estimate across available daily evidence:

| Metric | Value |
| --- | ---: |
| Average cash | `436,597.34 JPY` |
| Average market value | `569,029.02 JPY` |
| Average cash ratio | `43.4813%` |
| Average gross exposure ratio | `56.5187%` |
| Carried-ledger MDD estimate | `-14.2728%` |

Run-scoped fills:

| Metric | Value |
| --- | ---: |
| Total fills | `145` |
| BUY fills | `62` |
| SELL fills | `83` |
| BUY notional | `6,673,860 JPY` |
| SELL notional | `5,803,750 JPY` |
| Fill dates | `100` |

Runtime Planning positive quantities:

| Intent | Count |
| --- | ---: |
| `BUY_NEW` | `184` |
| `BUY_ADD` | `19` |
| `SELL_EXIT` | `41` |
| `SELL_REDUCE` | `4` |

PM decisions:

| Decision | Count |
| --- | ---: |
| `HOLD` | `358` |
| `ADD` | `330` |
| `REDUCE` | `60` |
| `EXIT` | `41` |

## Phase30 Entry Evidence Status

Phase30 now has two distinct evidence channels:

```text
100BD Baseline Status:
  prior Phase29-K 100BD accepted baseline remains the completed 100BD reference.
  phase30_a_entry_gate_100bd_baseline_status.md now records the earlier
  incomplete 95BD/100BD gate as historical context, not the only entry evidence.

Long-Horizon Partial Evidence Status:
  available, partial, non-final, useful for Phase30 attribution scoping.

Long-Horizon Full Completion Status:
  not complete; target run remains halted and must not be treated as a full
  977BD result.
```

Phase30 may use this partial long-horizon evidence to scope read-only
attribution questions, but must not treat it as final long-horizon acceptance.

## Phase30 Analysis Focus

The central Phase30 question is:

```text
Capital Utilization improved but Return is not enough.
Distinguish capital deployment from deployed capital quality.
```

Mandatory attribution axes are recorded in the new Phase30 handoff document,
including capital utilization, cash/exposure, BUY_NEW/BUY_ADD conversion, ADD
effectiveness, position distribution, concentration, hold duration, REDUCE/EXIT,
re-entry, campaigns, turnover, realized/unrealized PnL, profit factor, win rate,
MDD, Return/MDD, opportunity rank conversion, skipped opportunities, and
lot/cap/cash constraints.

## Preservation

Runtime/Strategy/Model/Config changed:

```text
NO
```

Target run mutated:

```text
NO
```

Long Historical executed by Codex:

```text
NO
```

## Next Step

Proceed only to Phase30 read-only attribution using:

- the completed Phase29-K 100BD reference;
- the updated Phase30-A entry gate status;
- the new partial long-horizon evidence handoff;
- the explicit caveat that the 977BD Historical run is not complete.

Do not tune Strategy, thresholds, ranking, PM, BUY Quality, Runtime, Safety, or
Historical-specific behavior before attribution identifies the causal
bottleneck.
