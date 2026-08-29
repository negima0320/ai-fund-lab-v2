# Phase32-BU — Post-BT NEW Allocation Semantic Drift Audit

## Executive Summary

This was a READ-ONLY comparison audit of Post-BT run
`runtime-test-historical-extended-smoke-20260828T223340854231Z`
against the prior Production-shaped fresh run
`runtime-test-historical-extended-smoke-20260828T000823285458Z`.

The day-0 divergence is confirmed as a NEW allocation semantic drift introduced by
the BG/BT common marginal frontier consumer path. Candidate, Buy Quality, and
legacy Portfolio Construction evidence for the compared day-0 symbols did not
materially change. The first semantic divergence is at the active
`canonical_marginal_capital_frontier_authority.v1` / BF aggregated PS-boundary
target source, which now admits PS-consumable NEW first-lot targets for rows that
legacy PC left at `target_weight = 0`.

The old 2022-10-03 path generated 7 BUY_NEW fills. The Post-BT path generated 11
BUY_NEW fills. The new path also dropped two names that old Production bought
despite positive legacy PC target weight, because the new budget-bounded frontier
ranked other first-lot candidates above them.

This does not imply old Production was globally correct or that returns should be
reproduced. It does show that the consumer switch changed existing NEW allocation
semantics more broadly than intended while preserving the ADD/common-frontier
machinery. A narrow production repair is justified at the NEW first-lot admission
and PS-consumer boundary, not in PM, PS arithmetic, Runtime, Safety, Cash,
Risk Pacing, REDUCE, EXIT, or performance-based thresholds.

## Run Identity

| Role | Run |
| --- | --- |
| Old Production comparison | `runtime-test-historical-extended-smoke-20260828T000823285458Z` |
| Post-BT target | `runtime-test-historical-extended-smoke-20260828T223340854231Z` |
| Exact day traced | `2022-10-03` |
| Characterization window | `2022-10-03` to `2022-10-14` |

The Post-BT run had daily artifacts through at least `2022-10-19` at audit time.
This report uses only existing artifacts. No production code, config, threshold,
model, runtime state, fresh-run, resume, replay, or backtest was changed or run.

## 2022-10-03 Exact Trace

### Boundary Summary

| Boundary | Old Production | Post-BT |
| --- | ---: | ---: |
| Legacy PC `BUY_NEW` rows with `target_weight > 0` | 9 | 9 |
| Legacy PC `BUY_NEW` rows with `target_weight = 0` | 41 | 41 |
| Marginal authority accepted NEW targets | n/a | 20 |
| BF aggregated targets | n/a | 20 |
| PS nonzero BUY rows | 9 | 11 |
| Submitted BUY orders | 7 | 11 |
| Actual BUY_NEW fills | 7 | 11 |
| Cash after day valuation | 495,530 | 699,290 |
| Position count after day | 7 | 11 |
| Approx exposure after day | 51.05% | 30.88% |

Candidate and Buy Quality evidence for the day-0 added/removed names was stable
between runs. Legacy PC positive-target membership was also stable: both runs had
the same nine positive-target NEW symbols:

`94340`, `37820`, `93600`, `33700`, `83060`, `92420`, `58200`, `89180`, `76470`.

Therefore the first material semantic divergence is not candidate generation,
Buy Quality, rank, trend, momentum, or legacy PC row evidence. It is the active
BG consumer path:

`canonical_marginal_capital_frontier_authority.v1`
-> BF aggregated PS-boundary targets
-> Position Sizing switched target source.

### Day-0 Fill Delta

| Symbol | Old Fill | Post-BT Fill | Old PC Target | Post-BT Authority Gap | Rank | Buy Quality | Interpretation |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 83060 | YES | YES | 0.064800 | 0.064800 | 20 | 0.612652 | Preserved fill |
| 37820 | YES | YES | 0.033636 | 0.006800 | 6 | 0.716582 | Preserved, smaller one-lot target |
| 94340 | YES | YES | 0.033636 | 0.014410 | 3 | 0.765860 | Preserved, smaller one-lot target |
| 89180 | YES | YES | 0.033636 | 0.000900 | 25 | 0.585257 | Preserved, much smaller quantity |
| 33700 | YES | YES | 0.034100 | 0.034100 | 17 | 0.644242 | Preserved fill |
| 76470 | NO | YES | 0.033636 | 0.002700 | n/a | n/a | Legacy positive target became filled |
| 92420 | YES | NO | 0.137500 | n/a | 21 | 0.615140 | Legacy positive target dropped by frontier |
| 93600 | YES | NO | 0.191100 | n/a | 10 | 0.690580 | Legacy positive target dropped by frontier |
| 41920 | NO | YES | 0.000000 | 0.078800 | 24 | 0.594423 | New authority admitted legacy-zero NEW |
| 45750 | NO | YES | 0.000000 | 0.067600 | 27 | 0.574196 | New authority admitted legacy-zero NEW |
| 33500 | NO | YES | 0.000000 | 0.004130 | 29 | 0.557743 | New authority admitted legacy-zero NEW |
| 67860 | NO | YES | 0.000000 | 0.008000 | 37 | 0.482751 | New authority admitted legacy-zero NEW |
| 82540 | NO | YES | 0.000000 | 0.030200 | 35 | 0.513128 | New authority admitted legacy-zero NEW |

The decisive pattern is that Post-BT emits PS-consumable accepted target gaps for
several symbols that old PC classified with `target_weight = 0`. Those symbols
were not newly stronger in the upstream evidence artifacts; they became buyable
because the new authority is now the active target source.

## Authority Evidence

On 2022-10-03, Post-BT `canonical_marginal_capital_frontier_authority.v1` was
active and produced 20 accepted `NEW_FIRST_LOT` targets under a 740,000 notional
allocation budget. Examples include:

| Symbol | Accepted Gap | Capital Value |
| --- | ---: | ---: |
| 94320 | 0.015350 | 0.756666 |
| 76920 | 0.014580 | 0.611821 |
| 94340 | 0.014410 | 0.572231 |
| 37820 | 0.006800 | 0.458701 |
| 33700 | 0.034100 | 0.403881 |
| 89180 | 0.000900 | 0.403814 |
| 76470 | 0.002700 | 0.400269 |
| 83060 | 0.064800 | 0.377163 |
| 82540 | 0.030200 | 0.367219 |
| 45750 | 0.067600 | 0.363401 |
| 41920 | 0.078800 | 0.363161 |

The new authority compares candidates by bounded marginal capital value and then
accepts sequential first-lot targets while budget, Cash, cap, Safety, and Risk
Pacing constraints permit. That is a coherent common-frontier mechanism, but it
does not preserve the old NEW acceptance boundary that made legacy PC
`target_weight = 0` non-deployable for PS.

## 2022-10-03 to 2022-10-14 Characterization

| Date | Old PC Positive NEW | Old BUY Fills | Old Sells | Old Cash | Old Positions | New Authority Targets | New BUY Fills | New Sells | New Cash | New Positions |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 2022-10-03 | 9 | 7 | 0 | 495,530 | 7 | NEW 20 | 11 | 0 | 699,290 | 11 |
| 2022-10-04 | 7 | 3 | 3 | 296,700 | 7 | NEW 13 | 8 | 5 | 307,340 | 14 |
| 2022-10-05 | 6 | 2 | 2 | 222,620 | 7 | NEW 6, ADD 3 | 3 | 8 | 485,860 | 9 |
| 2022-10-06 | 3 | 4 | 0 | 80,840 | 10 | NEW 6, ADD 3 | 6 | 3 | 264,160 | 11 |
| 2022-10-07 | 3 | 1 | 1 | 79,440 | 10 | NEW 3, ADD 6 | 2 | 2 | 197,460 | 11 |
| 2022-10-11 | 1 | 0 | 3 | 338,340 | 8 | NEW 3 | 0 | 1 | 272,860 | 10 |
| 2022-10-12 | 1 | 2 | 1 | 335,080 | 7 | NEW 4, ADD 3 | 1 | 2 | 454,860 | 9 |
| 2022-10-13 | 5 | 2 | 3 | 719,260 | 5 | NEW 7 | 2 | 3 | 539,760 | 8 |
| 2022-10-14 | 6 | 5 | 0 | 444,060 | 10 | NEW 7 | 2 | 3 | 482,960 | 7 |

Window totals:

| Metric | Old Production | Post-BT |
| --- | ---: | ---: |
| BUY fills | 26 | 35 |
| SELL fills | 13 | 27 |

The broader window shows materially higher early NEW breadth and materially
higher short-hold turnover after the switch. In the Post-BT run, multiple day-0
buys were sold quickly: five day-0 symbols sold on `2022-10-04`, four more on
`2022-10-05`, and one on `2022-10-11`. This is consistent with broader one-lot
NEW admission, not with changed upstream evidence.

ADD authority targets are present in the Post-BT window on `2022-10-05`,
`2022-10-06`, `2022-10-07`, and `2022-10-12`. The ADD/common-frontier improvement
is therefore still observable and separable from the NEW drift.

## Semantic Drift Judgment

The old NEW path had at least two production semantics that the active common
frontier weakened:

1. Legacy PC positive target was a deployability boundary for NEW. Post-BT allows
   PS-consumable NEW targets even when legacy PC `target_weight = 0`.
2. Legacy target-weight magnitude influenced PS quantity. Post-BT often reduces
   accepted names to one-lot or small bounded authority gaps, changing both
   breadth and per-name sizing.

The new path still uses decision-time rank, quality, opportunity, headroom, Cash,
cap, Safety, and Risk Pacing evidence. The drift is therefore not a total loss of
quality/rank semantics. It is a consumer-boundary semantic loss: old PC
non-deployability and target-weight authority no longer constrain NEW first-lot
deployment once BG is active.

## ADD Preservation

The ADD improvement is preservable. The repair boundary should be narrow:

- preserve BC/BF/BT multi-lot ADD authority and lot-by-lot cap enforcement;
- preserve common capital competition for ADD/Cash and valid first-lot candidates;
- restore an explicit NEW first-lot production admission contract before PS
  consumption.

A reasonable next repair should require NEW/REENTRY first-lot authority rows to
carry an explicit deployable legacy-PC admission, positive target-gap authority,
or other existing PC-owned production admission proof before BF/BG can emit a
PS-consumable target. This should not tune rank, quality, marginal value weights,
thresholds, or use future outcomes.

## Defect / No-Defect Judgment

Defect classification: production semantic drift at the active BG PC-to-PS
consumer boundary.

This is not a Candidate, Buy Quality, PM, PS arithmetic, Runtime, Pending, Order,
Execution, Cash resolver, Risk Pacing, REDUCE, or EXIT defect based on the
available artifacts. It is also not an outcome/PnL failure criterion. The defect
is that the migration changed existing NEW allocation semantics and broadened
first-lot deployment beyond the previous PC deployability boundary.

## Final Judgments

PHASE32_BU_NEW_ALLOCATION_SEMANTIC_DRIFT = YES

PHASE32_BU_OLD_NEW_FILL_COUNT_DAY0 = 7

PHASE32_BU_NEW_NEW_FILL_COUNT_DAY0 = 11

PHASE32_BU_PRIMARY_DIVERGENCE_BOUNDARY = BG_ACTIVE_MARGINAL_FRONTIER_AUTHORITY_TO_BF_PS_TARGET_CONSUMER

PHASE32_BU_OLD_NEW_SEMANTIC_LOSS = YES

PHASE32_BU_ADD_IMPROVEMENT_PRESERVABLE = YES

PHASE32_BU_PRODUCTION_REPAIR_JUSTIFIED = YES

PHASE32_BU_LONG_RUN_CONTINUE = YES

PHASE32_BU_NEXT_STEP = Narrowly repair NEW/REENTRY first-lot production admission at the marginal authority/BF consumer boundary so legacy PC non-deployable rows cannot become PS-consumable targets, while preserving ADD multi-lot common-frontier behavior and without threshold or performance tuning.
