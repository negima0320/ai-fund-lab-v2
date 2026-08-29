# Phase32-AW - Post-AU Fresh-Run Shadow Actual-Path Acceptance

## Executive Summary

READ-ONLY actual-path acceptance was performed for the Post-AU fresh run:

```text
runtime-test-historical-extended-smoke-20260828T000823285458Z
```

The run is still marked `RUNNING` in `run_state.json`; it was not stopped,
resumed, replayed, or rerun. Shadow frontier payloads were built in memory only
from same-day artifacts. No `diagnostic_shadow` files were written into the run
directory.

Coverage observed from available day artifacts:

```text
2022-10-03 through 2022-10-17
10 day directories with strategy/portfolio_construction.json
```

`strategy_shadow_manifest.json` lists 9 complete dates and marks
`2022-10-07` as `REVIEW_REQUIRED`; the strategy artifacts required for frontier
characterization exist for that date, so it is included below and separately
noted.

Primary result:

```text
AU Cash resolver is accepted on the fresh-run actual artifact path.
Cash resolved PASS on all 10 characterized days from current_valuation_refresh/valuation_projection.json.
No false insufficient-cash collapse was observed.
The common frontier, repeated ADD next-lot surface, and non-production boundary are preserved.
```

Because this is only 10 artifact days, ADD win-rate and performance are not
acceptance gates.

## Required Inputs

Read:

- `docs/phase_reports/phase32_au_shadow_frontier_cash_source_resolver_repair.md`
- `docs/phase_reports/phase32_at_shadow_marginal_capital_frontier_artifact_only_characterization.md`
- `docs/phase_reports/phase32_as_shadow_marginal_capital_frontier_implementation.md`

Actual run artifacts read:

- `run_state.json`
- `strategy_shadow_manifest.json`
- `strategy_shadow_summary.json`
- `daily/{date}/strategy/portfolio_construction.json`
- `daily/{date}/strategy/position_sizing.json`
- `daily/{date}/strategy/portfolio_policy.json`
- `daily/{date}/current_valuation_refresh/valuation_projection.json`
- `daily/{date}/current_valuation_refresh/safety_authority_decision.json`, when present
- `daily/{date}/morning/safety_decision.json`, fallback when present

No Historical future outcome, future return, later PnL, fresh-run, resume,
replay, backtest, production code, config, threshold, or runtime state mutation
was used.

## Run Identity

| Field | Value |
| --- | --- |
| Run id | `runtime-test-historical-extended-smoke-20260828T000823285458Z` |
| Evidence path | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T000823285458Z` |
| `run_state.status` | `RUNNING` |
| `run_state.completed_business_days` | 10 days |
| First characterized date | `2022-10-03` |
| Coverage end | `2022-10-17` |
| In-memory only | `YES` |

## Cash Resolver Actual-Path Evidence

| Metric | Value |
| --- | ---: |
| Characterized days | 10 |
| Cash source `PASS` days | 10 |
| Cash source `REVIEW_REQUIRED` days | 0 |
| Selected source role | `current_valuation_refresh.valuation_projection` on 10 days |
| Candidate rows with `REVIEW_REQUIRED` | 0 |
| False missing-Cash `INFEASIBLE_INSUFFICIENT_CASH` rows | 0 |

Examples:

| Date | Selected Cash source | Available Cash |
| --- | --- | ---: |
| `2022-10-03` | `current_valuation_refresh.valuation_projection` | 495,530 |
| `2022-10-04` | `current_valuation_refresh.valuation_projection` | 296,700 |
| `2022-10-05` | `current_valuation_refresh.valuation_projection` | 222,620 |

The resolver also preserved lower-priority lineage, including
`portfolio_construction.capital_competition.canonical_multi_allocation_deployment_set.available_incremental_budget`
where present. Those lower-priority values were not used as zero-Cash fallback.

## Common Frontier Counts

| Candidate type | Count |
| --- | ---: |
| `NEW_FIRST_LOT` | 387 |
| `REENTRY_FIRST_LOT` | 44 |
| `ADD_NEXT_LOT` | 24 |
| `CASH_OPTIONALITY` | 10 |
| Total | 465 |

Days with all four semantic types present:

```text
6 / 10
```

The first two days had only NEW and Cash; later days had REENTRY and ADD as the
fresh-run lifecycle generated those states.

## Winner / Runner-Up Counts

| Winner type | Days |
| --- | ---: |
| `NEW_FIRST_LOT` | 6 |
| `ADD_NEXT_LOT` | 4 |
| `REENTRY_FIRST_LOT` | 0 |
| `CASH_OPTIONALITY` | 0 |

| Runner-up type | Days |
| --- | ---: |
| `NEW_FIRST_LOT` | 6 |
| `ADD_NEXT_LOT` | 4 |

ADD winner days:

```text
2022-10-06
2022-10-11
2022-10-12
2022-10-13
```

This short sample confirms ADD can win the structured frontier. It is not a
performance or win-rate judgment.

## Dispositions

| Disposition | Count |
| --- | ---: |
| `SHADOW_WINNER` | 10 |
| `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 373 |
| `INFEASIBLE_CAP_BLOCKED` | 52 |
| `INFEASIBLE_INSUFFICIENT_CASH` | 30 |
| `REVIEW_REQUIRED` | 0 |

By type:

| Type / Disposition | Count |
| --- | ---: |
| `ADD_NEXT_LOT / SHADOW_WINNER` | 4 |
| `ADD_NEXT_LOT / SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 20 |
| `NEW_FIRST_LOT / SHADOW_WINNER` | 6 |
| `NEW_FIRST_LOT / SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 299 |
| `NEW_FIRST_LOT / INFEASIBLE_CAP_BLOCKED` | 52 |
| `NEW_FIRST_LOT / INFEASIBLE_INSUFFICIENT_CASH` | 30 |
| `REENTRY_FIRST_LOT / SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 44 |
| `CASH_OPTIONALITY / SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 10 |

The observed insufficient-cash rows are not false Cash-source failures. Example
rows have resolved Cash and security notional greater than available Cash:

| Date | Symbol | Type | Notional | Available Cash |
| --- | --- | --- | ---: | ---: |
| `2022-10-05` | `49340` | `NEW_FIRST_LOT` | 258,900 | 222,620 |
| `2022-10-05` | `91010` | `NEW_FIRST_LOT` | 261,000 | 222,620 |
| `2022-10-06` | `66190` | `NEW_FIRST_LOT` | 145,900 | 80,840 |

## ADD Next-Lot Surface

| ADD lot index | Count |
| ---: | ---: |
| 1 | 8 |
| 2 | 8 |
| 3 | 8 |

ADD candidate days:

```text
6 / 10
```

Multi-lot ADD surface observed:

```text
YES
```

Production target-gap-zero with shadow ADD candidate days:

```text
6
```

This confirms the AS/AU shadow surface exposes ADD marginal candidates even when
production target-gap authority remains zero.

## Repeated ADD Recalculation

Representative 94320 trace:

| Date | Lot | Pre qty | Post qty | Pre weight | Post weight | Cash before | Cash after | Headroom before | Headroom after | Disposition |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `2022-10-07` | 1 | 200 | 300 | 0.029755 | 0.044558 | 79,440 | 63,570 | 0.220245 | 0.205442 | rejected vs NEW |
| `2022-10-07` | 2 | 300 | 400 | 0.044558 | 0.059360 | 63,570 | 47,700 | 0.205442 | 0.190640 | rejected vs NEW |
| `2022-10-07` | 3 | 400 | 500 | 0.059360 | 0.074163 | 47,700 | 31,830 | 0.190640 | 0.175837 | rejected vs NEW |
| `2022-10-12` | 1 | 200 | 300 | 0.030675 | 0.045821 | 335,080 | 319,280 | 0.219325 | 0.204179 | winner |
| `2022-10-12` | 2 | 300 | 400 | 0.045821 | 0.060966 | 319,280 | 303,480 | 0.204179 | 0.189034 | rejected vs ADD |
| `2022-10-12` | 3 | 400 | 500 | 0.060966 | 0.076112 | 303,480 | 287,680 | 0.189034 | 0.173888 | rejected vs ADD |

Representative 94340 trace also showed lot #1/#2/#3 generation on
`2022-10-05`, `2022-10-06`, and `2022-10-07`, with Cash, weight, and headroom
recomputed after each hypothetical lot.

## Guardrails

| Guardrail / block | Count |
| --- | ---: |
| cap blocked | 52 |
| insufficient Cash | 30 |
| Safety blocked | 0 |
| Risk Pacing blocked | 0 |
| review-required candidates | 0 |

Guardrails are preserved. Cap and Cash remain hard feasibility constraints.
Safety and Risk Pacing did not block any characterized row in this short sample.

## High Position Count / Sideways Behavior

High-position-count days observed:

| Date | Position count | Candidate count | Winner |
| --- | ---: | ---: | --- |
| `2022-10-07` | 10 | 47 | `NEW_FIRST_LOT` |
| `2022-10-11` | 10 | 44 | `ADD_NEXT_LOT` |
| `2022-10-12` | 8 | 50 | `ADD_NEXT_LOT` |
| `2022-10-17` | 10 | 41 | `NEW_FIRST_LOT` |

Sideways / range regime evidence was visible in same-day artifacts on:

```text
2022-10-04
2022-10-05
2022-10-06
2022-10-07
```

Winners in that subset:

| Winner type | Days |
| --- | ---: |
| `NEW_FIRST_LOT` | 3 |
| `ADD_NEXT_LOT` | 1 |

The sample is too short for a regime conclusion.

## ADD Loss Classification

Observed ADD rejected rows:

| Primary reason | Count |
| --- | ---: |
| weaker than `ADD_NEXT_LOT` | 11 |
| weaker than `NEW_FIRST_LOT` | 9 |

No ADD row failed for Cash, cap, Safety, Risk Pacing, missing campaign identity,
or missing Cash evidence in this 10-day sample. The dominant observed pattern is
legitimate structured-frontier ordering: later ADD lots often lose to the first
ADD lot from the same or another campaign, and some ADD lots lose to stronger
NEW candidates.

This does not prove the structured comparison is production-ready; it only shows
that, in this short actual-path sample, ADD is not being suppressed by the
former Cash-source gap.

## Production Boundary

Every in-memory payload preserved:

```text
artifact_mode = SHADOW_NON_AUTHORITATIVE
production_consumer_count = 0
feeds_position_sizing = false
feeds_runtime_planning = false
feeds_pending = false
feeds_orders = false
feeds_execution = false
feeds_safety_authority = false
production_behavior_changed = false
```

No production behavior was changed by AW.

## Acceptance Judgment

Actual-path shadow acceptance is granted for AU Cash resolver behavior and AS
frontier surface on the available early fresh-run artifacts.

Limitations:

- only 10 artifact days are available;
- `2022-10-07` is marked `REVIEW_REQUIRED` in `strategy_shadow_manifest.json`,
  although its strategy artifacts are present and usable for this shadow
  characterization;
- ADD win-rate and performance are not acceptance gates.

Production migration is not ready. Longer shadow characterization is still
needed before any authority migration decision.

## Final Judgments

PHASE32_AW_RUN_ID = runtime-test-historical-extended-smoke-20260828T000823285458Z

PHASE32_AW_COVERAGE_END = 2022-10-17

PHASE32_AW_CASH_RESOLVER_ACTUAL_PATH_PASS = YES

PHASE32_AW_FALSE_INSUFFICIENT_CASH = NO

PHASE32_AW_COMMON_FRONTIER_OBSERVED = YES

PHASE32_AW_ADD_NEXT_LOT_OBSERVED = YES

PHASE32_AW_MULTI_LOT_ADD_SURFACE_OBSERVED = YES

PHASE32_AW_GUARDRAILS_PRESERVED = YES

PHASE32_AW_FAIL_CLOSED_BEHAVIOR = PASS

PHASE32_AW_PRODUCTION_CONSUMER_COUNT = 0

PHASE32_AW_PRODUCTION_BEHAVIOR_CHANGED = NO

PHASE32_AW_ACTUAL_PATH_ACCEPTED = YES

PHASE32_AW_PRODUCTION_MIGRATION_READY = NO

PHASE32_AW_LONG_RUN_CONTINUE = YES

PHASE32_AW_NEXT_STEP = Continue the current long run and repeat broad artifact-only shadow characterization after more completed days accumulate.
