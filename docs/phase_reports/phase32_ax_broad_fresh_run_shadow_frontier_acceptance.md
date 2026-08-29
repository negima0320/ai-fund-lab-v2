# Phase32-AX - Broad Fresh-Run Shadow Frontier Acceptance

## Executive Summary

READ-ONLY broad characterization was performed for:

```text
runtime-test-historical-extended-smoke-20260828T000823285458Z
```

Scope:

```text
canonical_marginal_capital_frontier.v1
```

The run was not stopped, resumed, replayed, rerun, or backtested. Shadow payloads
were built in memory only from same-day artifacts; no files were written into
the run directory and no production behavior was changed.

Coverage:

```text
2022-10-03 through 2022-12-06
44 characterized day directories with strategy/portfolio_construction.json and strategy/position_sizing.json
```

Primary result:

```text
The AU Cash resolver remains stable on the broader fresh-run actual path.
NEW / REENTRY / ADD / Cash common frontier generation is stable across BEAR, RANGE, RECOVERY, BULL, and one CORRECTION day.
ADD next-lot #1/#2/#3+ generation is broad and deterministic.
ADD is not suppressed by the prior false-Cash gap, and guardrails remain active.
Production migration is design-ready only in part; activation is not yet justified.
```

## Required Inputs

Read:

- `docs/phase_reports/phase32_aw_post_au_fresh_run_shadow_actual_path_acceptance.md`
- `docs/phase_reports/phase32_au_shadow_frontier_cash_source_resolver_repair.md`
- `docs/phase_reports/phase32_at_shadow_marginal_capital_frontier_artifact_only_characterization.md`

Actual artifacts read:

- `run_state.json`
- `strategy_shadow_manifest.json`
- `daily/{date}/strategy/portfolio_construction.json`
- `daily/{date}/strategy/position_sizing.json`
- `daily/{date}/strategy/portfolio_policy.json`
- `daily/{date}/strategy/market_context.json`
- `daily/{date}/current_valuation_refresh/valuation_projection.json`
- `daily/{date}/current_valuation_refresh/safety_authority_decision.json`, when present
- `daily/{date}/morning/safety_decision.json`, fallback when present

No future return, later PnL, Historical outcome, score tuning, threshold
selection, production code, config, runtime state mutation, fresh-run, resume,
replay, or backtest was used.

## Run / Coverage

| Field | Value |
| --- | --- |
| Run id | `runtime-test-historical-extended-smoke-20260828T000823285458Z` |
| Evidence path | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T000823285458Z` |
| Characterized days | 44 |
| Coverage start | `2022-10-03` |
| Coverage end | `2022-12-06` |
| In-memory shadow generation only | `YES` |

`strategy_shadow_manifest.json` currently shows 44 generated dates, 40 complete
dates, and 4 review-required dates:

```text
2022-10-07
2022-10-27
2022-11-08
2022-11-18
```

Those review-required dates had the required same-day strategy artifacts for
this shadow characterization and were included.

## Cash Resolver Acceptance

| Metric | Value |
| --- | ---: |
| Cash source `PASS` days | 44 |
| Cash source `REVIEW_REQUIRED` days | 0 |
| Selected source role | `current_valuation_refresh.valuation_projection` on 44 days |
| Candidate rows with `REVIEW_REQUIRED` | 0 |
| False missing-Cash insufficient-cash rows | 0 |

The actual insufficient-cash rows are genuine feasibility outcomes: candidate
notional exceeded resolved decision-time Cash. Examples:

| Date | Symbol | Type | Notional | Resolved Cash |
| --- | --- | --- | ---: | ---: |
| `2022-10-05` | `49340` | `NEW_FIRST_LOT` | 258,900 | 222,620 |
| `2022-10-05` | `91010` | `NEW_FIRST_LOT` | 261,000 | 222,620 |
| `2022-10-06` | `66190` | `NEW_FIRST_LOT` | 145,900 | 80,840 |
| `2022-10-06` | `70780` | `NEW_FIRST_LOT` | 119,500 | 80,840 |

## Candidate Counts

| Candidate type | Count |
| --- | ---: |
| `NEW_FIRST_LOT` | 1,350 |
| `REENTRY_FIRST_LOT` | 509 |
| `ADD_NEXT_LOT` | 141 |
| `CASH_OPTIONALITY` | 44 |
| Total | 2,044 |

Days with all four candidate types:

```text
38 / 44
```

The early lifecycle days before ADD / REENTRY emergence account for most
non-common-frontier days.

## Winner / Runner-Up Counts

| Winner type | Days |
| --- | ---: |
| `NEW_FIRST_LOT` | 33 |
| `REENTRY_FIRST_LOT` | 7 |
| `ADD_NEXT_LOT` | 4 |
| `CASH_OPTIONALITY` | 0 |

| Runner-up type | Days |
| --- | ---: |
| `NEW_FIRST_LOT` | 29 |
| `REENTRY_FIRST_LOT` | 10 |
| `ADD_NEXT_LOT` | 5 |

ADD winner days:

| Date | Regime | Symbol | Lot | Campaign |
| --- | --- | --- | ---: | --- |
| `2022-10-06` | `RANGE` | `94340` | 1 | `pc-993d47f0f8d7e622-94340-0001` |
| `2022-10-11` | `BEAR` | `94340` | 1 | `pc-993d47f0f8d7e622-94340-0001` |
| `2022-10-12` | `BEAR` | `94320` | 1 | `pc-e0c5da196f07ea55-94320-0001` |
| `2022-10-13` | `BEAR` | `94340` | 1 | `pc-993d47f0f8d7e622-94340-0001` |

All ADD winners were lot #1. Lot #2/#3+ are generated and compared, but the
structured diminishing context keeps them behind the strongest first-lot
alternative in this sample.

## ADD Lot Surface

| ADD lot bucket | Candidate count | Winner count |
| --- | ---: | ---: |
| lot #1 | 47 | 4 |
| lot #2 | 47 | 0 |
| lot #3+ | 47 | 0 |

| Metric | Value |
| --- | ---: |
| Days with ADD candidates | 38 |
| Days with multi-lot ADD candidates | 38 |
| Production target-gap=0 and shadow ADD candidate days | 38 |
| Production target-gap=0 and shadow ADD winner days | 4 |

This confirms the shadow surface exposes marginal ADD even when production
target-gap authority is zero. It also shows repeated ADD is not currently
overpowering the frontier.

## ADD Loss Classification

| Primary ADD non-winner reason | Count |
| --- | ---: |
| weaker than `NEW_FIRST_LOT` | 57 |
| cap blocked and insufficient Cash | 44 |
| weaker than `REENTRY_FIRST_LOT` | 15 |
| weaker than `ADD_NEXT_LOT` | 11 |
| cap blocked | 10 |

Interpretation:

- ADD is sometimes the best frontier candidate, so it is not categorically
  suppressed.
- Most feasible ADD losses are to stronger NEW / REENTRY alternatives.
- Later ADD lots also lose to earlier ADD lots, which is the expected
  diminishing marginal behavior.
- Some ADD rows are blocked by concentration/headroom and Cash feasibility,
  preserving guardrails.

## Persistent Campaign Traces

94320 remained a useful persistent ADD example:

| Date | Lot | Disposition | Strongest alternative | Cash before | Cash after | Post weight | Headroom after |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| `2022-10-07` | 1 | rejected | `NEW_FIRST_LOT` | 79,440 | 63,570 | 0.044558 | 0.205442 |
| `2022-10-07` | 2 | rejected | `NEW_FIRST_LOT` | 63,570 | 47,700 | 0.059360 | 0.190640 |
| `2022-10-07` | 3 | rejected | `NEW_FIRST_LOT` | 47,700 | 31,830 | 0.074163 | 0.175837 |
| `2022-10-12` | 1 | winner | `ADD_NEXT_LOT` | 335,080 | 319,280 | 0.045821 | 0.204179 |
| `2022-10-12` | 2 | rejected | `ADD_NEXT_LOT` | 319,280 | 303,480 | 0.060966 | 0.189034 |
| `2022-10-12` | 3 | rejected | `ADD_NEXT_LOT` | 303,480 | 287,680 | 0.076112 | 0.173888 |
| `2022-10-19` | 1 | rejected | `NEW_FIRST_LOT` | 194,160 | 178,060 | 0.061634 | 0.188366 |
| `2022-10-19` | 2 | rejected | `NEW_FIRST_LOT` | 178,060 | 161,960 | 0.077072 | 0.172928 |
| `2022-10-19` | 3 | rejected | `NEW_FIRST_LOT` | 161,960 | 145,860 | 0.092509 | 0.157491 |

94340 produced three ADD winner days and repeated #1/#2/#3 generation. 76470
appeared later as a persistent ADD surface, but its ADD lots were rejected
against REENTRY on `2022-11-24` through `2022-11-28` and against NEW afterward.

## Guardrails

| Guardrail / block evidence | Count |
| --- | ---: |
| `cap_blocked` reason occurrences | 524 |
| `insufficient_cash` reason occurrences | 1,170 |
| `INFEASIBLE_CAP_BLOCKED` candidates | 262 |
| `INFEASIBLE_INSUFFICIENT_CASH` candidates | 358 |
| Safety blocked candidates | 0 |
| Risk Pacing blocked candidates | 0 |
| Review-required candidates | 0 |

Guardrails are preserved. The lack of Safety / Risk Pacing blocks means those
guards did not fire in this sample, not that they were bypassed.

## Regime Behavior

Regime source:

```text
daily/{date}/strategy/market_context.json#regime_state
```

| Regime | Days |
| --- | ---: |
| `BULL` | 19 |
| `RANGE` | 11 |
| `BEAR` | 7 |
| `RECOVERY` | 6 |
| `CORRECTION` | 1 |

Winners by regime:

| Regime | NEW | REENTRY | ADD | Cash |
| --- | ---: | ---: | ---: | ---: |
| `BEAR` | 4 | 0 | 3 | 0 |
| `RANGE` | 8 | 2 | 1 | 0 |
| `RECOVERY` | 5 | 1 | 0 | 0 |
| `BULL` | 15 | 4 | 0 | 0 |
| `CORRECTION` | 1 | 0 | 0 | 0 |

The frontier remains semantically stable across observed regimes. ADD wins are
clustered early in BEAR / RANGE conditions, while later BULL and RECOVERY days
favor NEW / REENTRY. This is descriptive only and does not use later outcome to
choose parameters.

## High-Position / One-Lot-Heavy Behavior

High-position-count days observed:

```text
36 days with position_count >= 8
```

One-lot-heavy days observed:

```text
43 days with at least 50% of held positions at one lot
```

The frontier did not break under these conditions:

- high-position days included NEW, REENTRY, and ADD winners;
- one-lot-heavy days did not make repeated ADD overpower the frontier;
- cap and Cash blocks remained visible.

## Semantic Judgment

Cross-type comparison:

```text
PARTIAL
```

Rationale: the frontier compares NEW, REENTRY, ADD, and Cash on one structured
surface and all non-Cash security types can win. However, this is still a
shadow partial-order artifact, not a production-authoritative common cardinal
value object.

Structured ordering bias:

```text
NO material bias observed
```

Rationale: ADD can win; lot #2/#3+ are generated but naturally trail earlier
ADD or stronger NEW / REENTRY alternatives; ADD infeasibility is explained by
Cash/headroom instead of disappearing.

ADD suppression:

```text
No unfair ADD suppression observed in the characterized artifacts.
```

Repeated ADD excess:

```text
No repeated-ADD excess observed.
```

Production migration:

```text
PARTIAL
```

The evidence supports moving to a production-migration design phase. It does
not support direct production activation yet.

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

## Final Judgments

PHASE32_AX_COVERAGE_END = 2022-12-06

PHASE32_AX_CHARACTERIZED_DAYS = 44

PHASE32_AX_NEW_WINNER_DAYS = 33

PHASE32_AX_REENTRY_WINNER_DAYS = 7

PHASE32_AX_ADD_WINNER_DAYS = 4

PHASE32_AX_CASH_WINNER_DAYS = 0

PHASE32_AX_MULTI_LOT_ADD_CONFIRMED = YES

PHASE32_AX_PRODUCTION_ZERO_GAP_SHADOW_ADD_WIN_DAYS = 4

PHASE32_AX_CROSS_TYPE_COMPARISON_FAIR = PARTIAL

PHASE32_AX_STRUCTURED_ORDERING_BIAS = NO

PHASE32_AX_GUARDRAILS_PRESERVED = YES

PHASE32_AX_PRODUCTION_CONSUMER_COUNT = 0

PHASE32_AX_PRODUCTION_MIGRATION_READY = PARTIAL

PHASE32_AX_LONG_RUN_CONTINUE = YES

PHASE32_AX_NEXT_STEP = Continue the long run while preparing a narrow production-migration design for common marginal capital value authority; do not activate production consumption without an explicit later acceptance phase.
