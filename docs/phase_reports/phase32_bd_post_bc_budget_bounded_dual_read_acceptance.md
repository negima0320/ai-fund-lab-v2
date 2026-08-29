# Phase32-BD Post-BC Budget-Bounded Dual-Read Acceptance

## Executive Summary

READ-ONLY dual-read acceptance was performed for:

```text
runtime-test-historical-extended-smoke-20260828T000823285458Z
```

The Phase32-BC budget-bounded authority was applied in memory only:

```text
canonical_marginal_capital_frontier_authority.v1
```

No production code, PC/PS/Runtime/Pending/Orders/Execution state, consumer
switch, fresh-run, resume, replay, or backtest was changed or executed.

Primary result:

```text
BC budget authority actual path PASS: 50 / 50 days
BC capital conservation PASS: 50 / 50 days
Accepted targets: 301
Production-zero / BC-positive cases: 190
Explicit Cash allocation: 50 / 50 days
```

Compared with BA:

```text
BA accepted targets: 490
BC accepted targets: 301
BA Production-zero / Authority-positive: 374
BC Production-zero / Authority-positive: 190
```

BC naturally suppresses over-breadth through finite budget exhaustion and
explicit Cash allocation. It does not suppress ADD categorically.

## Required Inputs

Read:

- `docs/phase_reports/phase32_bc_budget_bounded_frontier_acceptance_implementation.md`
- `docs/phase_reports/phase32_ba_marginal_capital_authority_dual_read_acceptance.md`
- `docs/phase_reports/phase32_bb_production_capital_allocation_budget_acceptance_boundary_design.md`

Actual artifacts read:

- `daily/{date}/strategy/portfolio_construction.json`
- `daily/{date}/strategy/position_sizing.json`
- `daily/{date}/strategy/portfolio_policy.json`
- `daily/{date}/current_valuation_refresh/valuation_projection.json`
- `daily/{date}/current_valuation_refresh/safety_authority_decision.json`
- `daily/{date}/morning/safety_decision.json`, fallback only

## Coverage

| Field | Value |
| --- | --- |
| Run id | `runtime-test-historical-extended-smoke-20260828T000823285458Z` |
| Evidence path | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T000823285458Z` |
| Characterized days | 50 |
| Coverage start | `2022-10-03` |
| Coverage end | `2022-12-14` |
| In-memory authority generation only | `YES` |

## Budget Authority

| Metric | Count |
| --- | ---: |
| Authority result `PASS` | 50 |
| Allocation budget `PASS` | 50 |
| Capital conservation `PASS` | 50 |
| Budget source: `portfolio_construction.available_incremental_budget` | 50 |
| Determinism mismatches | 0 |
| Forbidden future/outcome fields | 0 |

BC used the existing PC budget authority on every characterized day:

```text
portfolio_construction.available_incremental_budget
```

No missing or conflicting budget source was observed on the actual path.
Focused BC regression remains the proof for injected missing/conflicting budget
fail-closed cases.

## Accepted Targets

| Accepted type | BA pre-BC | BC budget-bounded |
| --- | ---: | ---: |
| `NEW_FIRST_LOT` | 262 | 182 |
| `REENTRY_FIRST_LOT` | 134 | 26 |
| `ADD_NEXT_LOT` | 94 | 93 |
| Total | 490 | 301 |

Days observed:

| Accepted type | Days |
| --- | ---: |
| `NEW_FIRST_LOT` | 46 |
| `REENTRY_FIRST_LOT` | 22 |
| `ADD_NEXT_LOT` | 31 |

ADD accepted lot counts:

| ADD lot | Accepted |
| --- | ---: |
| lot #1 | 32 |
| lot #2 | 31 |
| lot #3 | 30 |

## Production Dual-Read Divergence

| Metric | Count |
| --- | ---: |
| BC accepted targets compared to production PS rows | 301 |
| Same target-gap weight | 3 |
| Different target-gap weight | 298 |
| Same projected quantity as production quantity | 111 |
| Different projected quantity from production quantity | 190 |

Production gap `0` while BC gap `> 0`:

| Type | Count |
| --- | ---: |
| `NEW_FIRST_LOT` | 100 |
| `REENTRY_FIRST_LOT` | 24 |
| `ADD_NEXT_LOT` | 66 |
| Total | 190 |

Representative examples:

| Date | Symbol | Type | Lot | BC gap | Production qty | BC qty | Capital value |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `2022-10-03` | `94320` | `NEW_FIRST_LOT` | 1 | 0.0153500000 | 0 | 100 | 0.7590540840 |
| `2022-10-03` | `76920` | `NEW_FIRST_LOT` | 1 | 0.0145800000 | 0 | 100 | 0.6140894310 |
| `2022-10-05` | `94340` | `ADD_NEXT_LOT` | 1 | 0.0141075990 | 0 | 100 | 0.4450407914 |
| `2022-10-05` | `94340` | `ADD_NEXT_LOT` | 2 | 0.0141075990 | 0 | 100 | 0.4393977518 |
| `2022-10-07` | `94320` | `ADD_NEXT_LOT` | 1 | 0.0148027236 | 0 | 100 | 0.6391167296 |

Interpretation:

- BC materially reduces BA's over-breadth.
- BC still differs materially from current Production, especially in positive
  ADD / NEW target-gap cases.
- This is acceptable for disabled dual-read acceptance.
- Consumer switch is not ready without further migration validation.

## Acceptance Sequence Examples

`2022-10-03`:

| Step | Decision | Symbol | Type | Value | Budget before | Budget after |
| ---: | --- | --- | --- | ---: | ---: | ---: |
| 1 | `ACCEPT_INCREMENTAL_TARGET` | `94320` | `NEW_FIRST_LOT` | 0.759054 | 0.495530 | 0.480180 |
| 2 | `ACCEPT_INCREMENTAL_TARGET` | `76920` | `NEW_FIRST_LOT` | 0.614089 | 0.480180 | 0.465600 |
| 3 | `ACCEPT_INCREMENTAL_TARGET` | `94340` | `NEW_FIRST_LOT` | 0.568708 | 0.465600 | 0.436780 |
| 8 | `ACCEPT_INCREMENTAL_TARGET` | `33700` | `NEW_FIRST_LOT` | 0.409185 | 0.283510 | 0.249410 |

`2022-10-05`:

| Step | Decision | Symbol | Type | Lot | Value | Budget before | Budget after |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `ACCEPT_INCREMENTAL_TARGET` | `94320` | `NEW_FIRST_LOT` | 1 | 0.748360 | 0.212205 | 0.181874 |
| 2 | `ACCEPT_INCREMENTAL_TARGET` | `76920` | `NEW_FIRST_LOT` | 1 | 0.516209 | 0.181874 | 0.152171 |
| 3 | `ACCEPT_INCREMENTAL_TARGET` | `44220` | `NEW_FIRST_LOT` | 1 | 0.452511 | 0.152171 | 0.120077 |
| 4 | `ACCEPT_INCREMENTAL_TARGET` | `94340` | `ADD_NEXT_LOT` | 1 | 0.445041 | 0.120077 | 0.105969 |
| 5 | `ACCEPT_INCREMENTAL_TARGET` | `94340` | `ADD_NEXT_LOT` | 2 | 0.439398 | 0.105969 | 0.091861 |
| 6 | `ACCEPT_INCREMENTAL_TARGET` | `94340` | `ADD_NEXT_LOT` | 3 | 0.433755 | 0.091861 | 0.077754 |

All 50 characterized days ended with:

```text
STOP_BUDGET_EXHAUSTED_TO_CASH
```

and published explicit Cash allocation.

## Explicit Cash / Capital Conservation

| Metric | Value |
| --- | ---: |
| Acceptance sequence rows | 351 |
| `ACCEPT_INCREMENTAL_TARGET` steps | 301 |
| `STOP_BUDGET_EXHAUSTED_TO_CASH` steps | 50 |
| Days with explicit Cash allocation | 50 |
| Minimum authorized Cash weight | 0.0003619528 |
| Maximum authorized Cash weight | 0.1195906722 |

Capital conservation:

```text
PASS: 50 / 50 days
security_allocation + authorized_cash_allocation = available_incremental_budget
```

## Why ADD Stayed 94 -> 93

ADD remained almost unchanged because accepted ADD candidates were genuinely
competitive under the BC value ordering and finite budget:

- ADD rows were already strong enough to enter the high-value portion of the
  frontier.
- ADD lots were small enough to fit remaining budget on many days.
- ADD lot #2/#3 did not inherit lot #1 acceptance; each appeared in a later
  sequence step and consumed recomputed remaining budget.
- Later ADD lots show diminishing value as headroom declines, but most accepted
  ADD chains still remained above Cash and inside budget.

Representative 94320 accepted sequence:

| Date | Lot | Disposition | Capital value | Incremental weight | Post weight |
| --- | ---: | --- | ---: | ---: | ---: |
| `2022-10-07` | 1 | `ACCEPTED_INCREMENTAL_TARGET` | 0.6391167296 | 0.0148027236 | 0.0445577236 |
| `2022-10-07` | 2 | `ACCEPTED_INCREMENTAL_TARGET` | 0.6331956401 | 0.0148027236 | 0.0593604473 |
| `2022-10-07` | 3 | `ACCEPTED_INCREMENTAL_TARGET` | 0.6272745506 | 0.0148027236 | 0.0741631709 |
| `2022-10-12` | 1 | `ACCEPTED_INCREMENTAL_TARGET` | 0.7008361859 | 0.0151455603 | 0.0458205603 |
| `2022-10-12` | 2 | `ACCEPTED_INCREMENTAL_TARGET` | 0.6947779617 | 0.0151455603 | 0.0609661207 |
| `2022-10-12` | 3 | `ACCEPTED_INCREMENTAL_TARGET` | 0.6887197376 | 0.0151455603 | 0.0761116810 |

This is semantically justified in this sample. It is not evidence of ADD type
bias by itself.

## Why NEW / REENTRY Decreased

Budget bounding primarily removed tail candidates that were individually
feasible but no longer fit the shared remaining budget after stronger
candidates consumed earlier increments.

Rejected feasible non-accepted candidate counts:

| Type | Count |
| --- | ---: |
| `NEW_FIRST_LOT` | 798 |
| `REENTRY_FIRST_LOT` | 466 |
| `ADD_NEXT_LOT` | 6 |

NEW and REENTRY decreased more because they had a wider tail of feasible
candidates. ADD had far fewer total candidates and many appeared early enough
in the value ordering to consume budget before exhaustion.

## Type / Ordering Bias Check

No direct type or ordering bias was observed:

- The value contract does not use semantic-type multipliers.
- Accepted targets include NEW, REENTRY, and ADD.
- ADD is not categorically first: on `2022-10-05`, three NEW candidates were
  accepted before the first ADD lot.
- ADD lot #2/#3 re-enter the sequence as separate steps and carry lower
  capital value when headroom declines.
- Cash remains explicit and receives residual allocation every day.

Residual risk:

```text
PARTIAL: consumer switch still needs broader dual-read validation after BC
because Production quantity divergence remains material.
```

## Guardrails

| Guardrail | Count |
| --- | ---: |
| Cap blocked candidates | 279 |
| Cash blocked candidates | 426 |
| Safety blocked candidates | 0 |
| Risk Pacing blocked candidates | 0 |
| No-loss-averaging blocked candidates | 0 |

Guardrails are preserved. Safety and Risk Pacing did not fire in this sample;
they were not bypassed.

## Deterministic / PIT / Fail-Closed

Actual-path checks:

- deterministic rerun hash: PASS, 50 / 50;
- stable payload hash: PASS, 50 / 50;
- forbidden future/outcome field scan: PASS, 0 findings;
- budget authority: PASS, 50 / 50;
- Cash source: PASS, 50 / 50;
- capital conservation: PASS, 50 / 50.

Focused BC regression remains the evidence for injected missing/conflicting
budget fail-closed behavior:

```text
28 passed in 0.13s
```

## Production Boundary

No production consumer was enabled:

```text
production_consumer_enabled = false
production_consumer_count = 0
feeds_position_sizing = false
feeds_runtime_planning = false
feeds_pending = false
feeds_orders = false
feeds_execution = false
feeds_safety_authority = false
production_behavior_changed = false
```

## Final Judgments

```text
PHASE32_BD_BUDGET_AUTHORITY_ACTUAL_PATH_PASS = YES
PHASE32_BD_ACCEPTED_TARGET_TOTAL = 301
PHASE32_BD_NEW_ACCEPTED = 182
PHASE32_BD_REENTRY_ACCEPTED = 26
PHASE32_BD_ADD_ACCEPTED = 93
PHASE32_BD_MULTI_LOT_ADD_ACCEPTED = YES
PHASE32_BD_ADD_RETENTION_SEMANTICALLY_JUSTIFIED = YES
PHASE32_BD_TYPE_OR_ORDERING_BIAS = NO
PHASE32_BD_EXPLICIT_CASH_PASS = YES
PHASE32_BD_CAPITAL_CONSERVATION = PASS
PHASE32_BD_GUARDRAILS_PRESERVED = YES
PHASE32_BD_PS_COMPATIBLE = YES
PHASE32_BD_CONSUMER_SWITCH_READY = PARTIAL
PHASE32_BD_PRODUCTION_BEHAVIOR_CHANGED = NO
PHASE32_BD_NEXT_STEP = Run a second READ-ONLY dual-read over longer fresh-run coverage or implement a consumer-switch dry-run validator that proves PS quantity compatibility, capital conservation, and acceptable Production divergence before enabling consumers.
```
