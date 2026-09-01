# Phase32-CA — Early-vs-Late Large-Loss Scaling × HOLD Confirmation Lag READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- Audit mode: READ-ONLY
- Latest completed actual Runtime day used: `2023-04-27`
- Completed business days used: 141 days, `2022-10-03` through `2023-04-27`
- Return rows used: 140 daily deltas

No code, config, PM/HOLD/SELL semantics, threshold, weight, model, feature, BO/BQ behavior, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run action was executed or changed.

Phase32-BY and Phase32-BZ conclusions are preserved:

- Upside capture is strong.
- BQ broadening is not justified.
- BZ recurrent BQ `SHADOW_INSUFFICIENT_EVIDENCE` / `SHADOW_HOLD` later-loss refinement remains a separate deferred SHADOW task.
- This report focuses on early/late scaling, PM/HOLD confirmation lag, and large-loss normalization.

The requested later dates `2023-08-04`, `2023-08-08`, `2023-08-17`, `2023-10-04`, `2024-03-08`, `2024-03-14`, `2024-03-15`, and `2024-05-24` are not present as completed `daily/<date>` actual artifacts in this target run at the inspection snapshot. They appear in plan/shadow references and in prior reports from other run snapshots, but CA's primary target-run actual evidence cannot audit those dates yet. They are therefore treated as `INSUFFICIENT_TARGET_RUN_ACTUAL_EVIDENCE`.

## Evidence Sources

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<date>/current_valuation_refresh/valuation_projection.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<date>/current_valuation_refresh/current_valuation_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<date>/position_management/pm_decisions.json`
- `.runtime/runtime_state/position_management/<date>/position_management_decisions.json`
- `.runtime/runtime_state/sell_pipeline/<date>/order_plan.json`
- `docs/phase_reports/phase32_by_post_bq_long_run_profit_retention_large_loss_mechanism_read_only_audit.md`
- `docs/phase_reports/phase32_bz_recurrent_bq_insufficient_hold_later_loss_pit_separability_read_only_audit.md`

Daily equity is calculated as:

```text
cash + new_total_market_value
```

Normalized daily return is:

```text
daily_pnl / prior_business_day_equity
```

Position-level contributors are approximate economic attribution from prior valuation, current valuation, same-day sell proceeds, and same-day buy cash effects. This is sufficient for mechanism characterization, not a ledger replacement.

## Early vs Late Windows

Primary split uses the first half and second half of the available daily return rows. Boundaries were not selected to maximize the hypothesis.

| Window | Rows | Dates |
|---|---:|---|
| Early | 70 | `2022-10-04` through `2023-01-17` |
| Late | 70 | `2023-01-18` through `2023-04-27` |

## Normalized Return Comparison

| Metric | Early | Late |
|---|---:|---:|
| Mean daily return | +0.154% | +0.506% |
| Median daily return | +0.228% | +0.515% |
| Standard deviation | 1.180% | 2.304% |
| Downside deviation | 0.782% | 1.445% |
| Worst day | -2.956% | -8.206% |
| 5th percentile | -1.848% | -3.012% |
| 1st percentile | -2.914% | -5.701% |
| Count `<= -1%` | 8 | 14 |
| Count `<= -2%` | 4 | 6 |
| Count `<= -3%` | 0 | 4 |
| Count `<= -5%` | 0 | 1 |
| Absolute loss `<= -20,000` | 4 | 8 |
| Absolute loss `<= -50,000` | 0 | 4 |
| Absolute loss `<= -100,000` | 0 | 1 |

Answer:

```text
Late-run losses are worse after normalization, not only larger in yen terms.
```

Late return distribution is also more positively skewed on average because large upside days appear in the same period. This preserves BY's conclusion that upside capture is strong: the issue is wider tails, especially downside tails around retained winners and post-growth high-notional positions.

## Capital-Scale Buckets

| Prior equity bucket | Rows | Mean return | Worst | `<= -2%` | `<= -3%` | Absolute `<= -50k` |
|---|---:|---:|---:|---:|---:|---:|
| `<1.25M` | 100 | +0.262% | -2.956% | 4 | 0 | 0 |
| `1.25M-1.50M` | 19 | +1.132% | -1.433% | 0 | 0 | 0 |
| `>1.50M` | 21 | -0.071% | -8.206% | 6 | 4 | 4 |

Capital scale is material, but not sufficient. Above `1.50M`, the run has both larger absolute yen tails and worse percentage tails.

## Large-Loss Event Population

Large-loss event rule:

- daily return `<= -2%`, or
- absolute daily loss `<= -50,000`

| Date | Prior equity | Daily PnL | Return | Regime | Prior exposure | Prior positions | Dominant negative contributors |
|---|---:|---:|---:|---|---:|---:|---|
| 2022-10-11 | 1,068,640 | -21,930 | -2.05% | BEAR | 0.862 | 9 | 70640 -12,750; 92420 -7,300 |
| 2022-11-14 | 1,095,460 | -31,710 | -2.89% | RECOVERY | 0.912 | 13 | 99840 -22,130; 69730 -5,200; 72020 -5,000 |
| 2022-12-07 | 1,142,980 | -30,130 | -2.64% | RANGE | 0.946 | 12 | 79010 -21,330; 37790 -6,000 |
| 2022-12-19 | 1,134,800 | -33,550 | -2.96% | CORRECTION | 0.903 | 12 | 97310 -20,100; 31500 -7,500 |
| 2023-03-29 | 1,512,760 | -61,660 | -4.08% | RECOVERY | 0.835 | 10 | 59350 -61,400; 43880 -6,800 |
| 2023-04-07 | 1,763,540 | -80,700 | -4.58% | BEAR | 0.491 | 4 | 59350 -90,500; offset 43880 +8,700 |
| 2023-04-11 | 1,766,350 | -144,950 | -8.21% | CORRECTION | 0.659 | 7 | 67310 -100,000; 59350 -25,000; 51890 -19,000 |
| 2023-04-12 | 1,621,400 | -37,110 | -2.29% | BULL | 0.658 | 7 | 59350 -34,500; 51890 -29,500; offsets elsewhere |
| 2023-04-18 | 1,638,550 | -37,450 | -2.29% | BULL | 0.806 | 9 | 59350 -40,000; 41660 -6,700 |
| 2023-04-21 | 1,596,290 | -57,540 | -3.60% | RECOVERY | 0.678 | 9 | 60220 -29,700; 38100 -15,000; 51360 -8,100 |

Severe / extreme counts:

- `<= -2%`: 10 events
- `<= -3%`: 4 events
- `<= -5%`: 1 event
- absolute `<= -50,000`: 4 events

## Pre-Loss PIT Timelines

### 2022-12-19 / 97310

- Dominant loss: approximately `-20,100`
- Earliest material deterioration / PM REDUCE: `2022-12-14`
- PM reason: `peak_drawdown_warning`
- BQ: `SHADOW_INSUFFICIENT_EVIDENCE`, `NOT_PROMOTED`
- Actual exit: `2022-12-20`
- REDUCE -> actual exit lag: 4 completed business days
- Classification: `PREDETECTED_BUT_REDUCE_UNDER_MATERIALIZED` / BZ mechanism

This belongs to the BQ under-materialization track, not the HOLD-confirmation track.

### 2023-03-29 / 59350

- Dominant loss: approximately `-61,400`
- Earliest pre-loss warning in inspected T-5 window: `2023-03-27`
- PM action on `2023-03-27` and `2023-03-28`: `HOLD`
- PM reasons: `positive_expected_edge`, `profit_retention_break`
- Loss-day PM action on `2023-03-29`: `ADD`
- Actual exit: `2023-04-20`
- Warning -> actual exit lag: about 16 completed business days
- Classification: `PREDETECTED_BUT_HOLD_PERSISTED`

HOLD remained authoritative because positive expected edge and trend/opportunity continuation still outweighed profit-retention warning evidence.

### 2023-04-07 / 59350

- Dominant loss: approximately `-90,500`
- Earliest warning in inspected window: `2023-03-31`
- PM repeatedly held with `positive_expected_edge` and `profit_retention_break`
- On `2023-04-07`, PM reasons switched to `trend_continuation`, `positive_expected_edge`
- Actual exit: `2023-04-20`
- Warning -> actual exit lag: about 13 completed business days
- Classification: `PREDETECTED_BUT_HOLD_PERSISTED`

This is the cleanest current target-run HOLD confirmation-lag example.

### 2023-04-11 / 67310, 59350, 51890

- `67310`: approximately `-100,000`; PM REDUCE and BQ `SHADOW_FULL_EXIT` occurred on the loss day; sell fill occurred the same day. Classification: `NEW_INFORMATION_OR_GAP_LOSS` for the main drop, with prompt current-day BQ management after the new PIT evidence existed.
- `59350`: approximately `-25,000`; still HOLD with `trend_continuation`, `positive_expected_edge`, `downside_risk_contained`. Classification: `PREDETECTED_BUT_HOLD_PERSISTED`.
- `51890`: approximately `-19,000` same-day starter mark-to-market loss after BUY. Classification: `NEW_INFORMATION_OR_GAP_LOSS` / starter risk, not a pre-loss HOLD-lag case.

### 2023-04-12 / 59350 and 51890

- `59350`: approximately `-34,500`; PM remained HOLD with `trend_continuation`, `downside_risk_contained`; actual exit `2023-04-20`. Classification: `PREDETECTED_BUT_HOLD_PERSISTED`.
- `51890`: approximately `-29,500`; PM REDUCE on `2023-04-12`, BQ `SHADOW_INSUFFICIENT_EVIDENCE`, actual exit `2023-04-13`. Classification: `PREDETECTED_BUT_REDUCE_UNDER_MATERIALIZED`, short-lag BZ-adjacent mechanism.

### 2023-04-18 / 59350 and 41660

- `59350`: approximately `-40,000`; PM had `profit_retention_break` on `2023-04-17`, then HOLD again on `2023-04-18`; actual exit `2023-04-20`. Classification: `PREDETECTED_BUT_HOLD_PERSISTED`.
- `41660`: smaller contributor in this daily event, but BZ identified `2023-04-13` `SHADOW_HOLD` followed by material later loss. Classification: BZ mechanism, not central CA HOLD redesign evidence.

### 2023-04-21 / 60220

- Dominant loss: approximately `-29,700`
- PM REDUCE on `2023-04-21`
- BQ: `SHADOW_INSUFFICIENT_EVIDENCE`, `NOT_PROMOTED`
- Actual exit: `2023-04-24`
- REDUCE -> actual exit lag: 1 completed business day
- Classification: `PREDETECTED_BUT_REDUCE_UNDER_MATERIALIZED`, short-lag BZ-adjacent mechanism

## HOLD Authority Audit

Central answer:

```text
HOLD was often supported by current positive continuation / expected-edge evidence, not merely by missing SELL evidence.
```

For `59350`, the artifact path shows:

- `2023-04-06` PM `HOLD`
- decision reason codes: `positive_expected_edge`, `profit_retention_break`
- canonical reason codes: `expected_edge_adequate`, `peak_drawdown_profit_retention_risk`
- dominant cause: `HOLD_BY_STRONG_CONTINUATION`
- expected-edge assessment: adequate for current HOLD while risk review is present
- reason-code semantics explicitly say `profit_retention_break` must not be interpreted as profit-taking action authority

This means the lag is not an obvious correctness bug. It is a Strategy semantics/design bottleneck:

```text
profit-retention risk is visible, but positive continuation can keep HOLD authoritative until terminal EXIT confirmation arrives.
```

Weak or inertia-like HOLD support also appears:

- `hold_score_above_exit_threshold` on `97310` after the earlier REDUCE warning.
- `downside_risk_contained` on some early losses.
- lack of terminal EXIT confirmation after `profit_retention_break`.

The most important recurrent CA case is not pure inertia. It is conflict between strong continuation evidence and profit-retention protection evidence.

## Profit / Winner Interaction

Judgment:

```text
MATERIAL_ASSOCIATION
```

Evidence:

- The largest target-run HOLD-lag contributor is `59350`, a highly profitable winner whose market value reached `549,000` and whose unrealized profit reached roughly `336,800` before later giveback.
- PM evidence repeatedly contained both positive continuation and profit-retention warning.
- The actual exit did not occur until `2023-04-20`, after repeated large drawdowns.
- Early profitable winners also show HOLD/ADD persistence under positive continuation, for example `99840` on `2022-11-14`, but early absolute and percentage tails are smaller than the late `59350` / April window.

No evidence shows regression to the old forbidden semantic:

```text
profit cushion alone -> HOLD
```

The observed authority is not profit alone. It is positive expected edge, trend continuation, downside containment, and/or structural continuation competing with profit-retention warning. Profit can contextualize the conflict, but it is not observed as standalone HOLD authority.

## Capital Scale vs Decision Lag

| Mechanism | Importance | Evidence |
|---|---|---|
| Capital scale | MODERATE | Above `1.50M`, absolute tails become larger and percentage tails also worsen. |
| Position/notional scale | HIGH | Late severe events are dominated by one or two large market-value positions, especially `59350` and `67310`; BY/BG also show high-notional starter tails in later completed long evidence from related runs. |
| Decision lag | HIGH | `59350` had PIT-visible `profit_retention_break` before several large losses and exited much later. |
| Concentration | HIGH | 2023-03-29, 2023-04-07, and 2023-04-11 are each dominated by one or two campaigns. |
| High exposure | LOW_TO_MODERATE as primary | Severe `<= -3%` days average exposure `0.666`, lower than ordinary negative days `0.808`; high exposure alone is not the primary cause. |

Exposure comparison:

| Population | Count | Avg prior exposure | Median prior exposure | Avg positions |
|---|---:|---:|---:|---:|
| severe `<= -3%` | 4 | 0.666 | 0.668 | 7.5 |
| large `<= -2%` | 10 | 0.775 | 0.820 | 9.2 |
| ordinary negative | 51 | 0.808 | 0.834 | 11.3 |
| all daily rows | 140 | 0.786 | 0.811 | 10.9 |

High exposure co-occurs with some losses, but it is not sufficient and not primary in the target-run normalized severe tail.

## Early vs Late Mechanism Comparison

The same broad weakness exists early, but late capital and winner scale make it economically larger.

Early examples:

- `99840` on `2022-11-14` remained `ADD` with `strong_trend_continuation`, `opportunity_rank_still_high`, `no_loss_averaging`; the one-day contribution was about `-22,130`.
- `97310` on `2022-12-19` had earlier PM REDUCE/BQ insufficient evidence, but the dominant daily loss was about `-20,100`.

Late examples:

- `59350` on `2023-03-29`, `2023-04-07`, `2023-04-11`, `2023-04-12`, and `2023-04-18` generated much larger single-campaign drawdowns after profit-retention warning evidence.
- `67310` produced the extreme `2023-04-11` loss, but BQ acted on the loss-day PIT evidence; this is not a pre-loss HOLD-lag case.

Answer:

```text
The system did not clearly become behaviorally worse later within the current completed target-run evidence. An existing weakness became economically larger as capital, winner notional, and campaign concentration grew.
```

The late period also shows worse normalized tails, so the effect is not capital-scale-only.

## BQ Separation

Large-loss contributor classes:

- PM never REDUCED before loss: `70640`, `99840`, `79010`, `59350` before the major March/April losses, `38100`
- PM REDUCED and BQ FULL EXIT: `67310` on `2023-04-11`; managed promptly after current-day evidence
- PM REDUCED and BQ INSUFFICIENT: `97310`, `51890`, `60220`
- PM REDUCED and BQ HOLD: `41660`, material in BZ but smaller in the `2023-04-18` daily attribution
- Native EXIT only: observed after several cases, usually after the large loss had already begun

Implication:

- `59350`-style loss belongs to PM/HOLD authority / winner profit-retention design.
- `97310/51890/60220/41660` belong to the deferred BZ SHADOW refinement.
- `67310` on `2023-04-11` is best treated as gap/new-information plus prompt same-day BQ management, not as a BQ failure in this target-run window.

## Preventability

Estimated pre-detected avoidable-loss pool in the current CA window:

- PM/HOLD confirmation lag, mainly `59350`: approximately `185,900` using the visible large-loss contributions after pre-loss `profit_retention_break` (`61,400 + 90,500 + 25,000 + 34,500 + 40,000`, with overlap caveat because these are daily contributions during one campaign lifecycle).
- BQ under-materialization: keep BZ's stricter campaign-level pool separate. Through `2023-04-18`, BZ directly supports approximately `102,400` campaign-level / `108,000` BY broader supported pool. Within CA's `2023-04-27` large-event window, the visible BQ-adjacent contributors are `97310`, `51890`, and `60220`, plus smaller `41660`.

This is not a proposed exit rule. It is a consequence estimate after PIT classification. Actual avoidability would need a SHADOW design that can preserve winner capture and control false exits.

## Primary Judgment

Best-supported explanation:

```text
HOLD_CONFIRMATION_LAG_AMPLIFIED_BY_CAPITAL_SCALE
```

Secondary mechanisms:

- `WINNER_PROFIT_RETENTION_LATE`
- `POSITION_NOTIONAL_SCALE`
- `BQ_UNDER_MATERIALIZATION` as a separate BZ track
- `UNPREDICTABLE_GAP_RISK` for `67310` on `2023-04-11`

Not selected as primary:

- `CAPITAL_SCALE_ONLY`: late percentage tails are worse too.
- `HIGH_EXPOSURE`: severe days do not have higher exposure than ordinary negative days.
- `BQ_UNDER_MATERIALIZATION`: real but not the dominant CA HOLD-lag mechanism.
- `NO_CLEAR_MECHANISM`: the evidence is clear enough to characterize.

## Production / Shadow Implications

Production change justified:

```text
NO
```

SHADOW follow-up justified:

```text
YES
```

The narrowest next task should be a READ-ONLY/SHADOW design around PM HOLD profit-retention escalation:

```text
When profit-retention risk / observed giveback / EXIT_GRADE is PIT-visible, determine whether positive expected edge and trend continuation should continue to dominate HOLD, or whether a shadow capital-protection state should be materialized.
```

This should not import BZ's BQ refinement or broaden BQ. The SHADOW design should include gain-retained winner controls to avoid killing `59350`-type upside too early.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-04-27`
2. `EARLY_WINDOW = 2022-10-04_TO_2023-01-17; 70_DAILY_RETURN_ROWS`
3. `LATE_WINDOW = 2023-01-18_TO_2023-04-27; 70_DAILY_RETURN_ROWS`
4. `EARLY_WORST_NORMALIZED_DAY = 2022-12-19; -33,550; -2.956%`
5. `LATE_WORST_NORMALIZED_DAY = 2023-04-11; -144,950; -8.206%`
6. `LATE_LOSS_TAIL_WORSE_AFTER_NORMALIZATION = YES`
7. `CAPITAL_SCALE_EFFECT = MODERATE`
8. `POSITION_NOTIONAL_SCALE_EFFECT = HIGH`
9. `HIGH_EXPOSURE_PRIMARY_CAUSE = NO`
10. `PRELOSS_PIT_WARNING_COMMON = YES_FOR_LATE_DOMINANT_WINNER_AND_BQ_ADJACENT_CASES; NO_FOR_ALL_EVENTS`
11. `HOLD_CONFIRMATION_LAG_RECURRENT = YES`
12. `MEDIAN_DETERIORATION_TO_EXIT_LAG = APPROX_13_TO_16BD_FOR_59350_HOLD_LAG_CASES; SHORT_1_TO_4BD_FOR_BQ_UNDER_MATERIALIZATION_CASES`
13. `PROFITABLE_WINNER_HOLD_LAG_ASSOCIATION = MATERIAL_ASSOCIATION`
14. `PROFIT_CUSHION_ALONE_HOLD_REGRESSION = NO`
15. `WINNER_PROFIT_RETENTION_LATE_RECURRENT = YES_WITHIN_CURRENT_WINDOW_PRIMARILY_59350; BROADER_PRIOR_REPORTS_SUPPORT_MORE_CASES`
16. `WINNER_RETENTION_LAG_CAMPAIGN_COUNT = 1_CONFIRMED_CURRENT_TARGET_RUN_CAMPAIGN_BY_2023-04-27; 59350`
17. `BQ_UNDER_MATERIALIZATION_SHARE = SECONDARY; 3_OF_10_LARGE_EVENTS_HAVE_DOMINANT_OR_MATERIAL_BQ_INSUFFICIENT_CONTRIBUTOR, PLUS_SMALL_41660_BQ_HOLD_CONTEXT`
18. `PM_HOLD_AUTHORITY_SHARE = PRIMARY_FOR_LATE_SEVERE_TAIL; 59350_DOMINATES_4_OF_4_<=-3%_EVENTS_DIRECTLY_OR_AS_SECONDARY`
19. `UNPREDICTABLE_LOSS_SHARE = MATERIAL_FOR_2023-04-11_67310_AND_SOME_STARTER_LOSSES; NOT_PRIMARY_OVERALL`
20. `ESTIMATED_PREDETECTED_AVOIDABLE_LOSS = APPROX_185,900_PM_HOLD_LAG_DAILY_CONTRIBUTIONS_WITH_OVERLAP_CAVEAT; BZ_BQ_POOL_SEPARATELY_APPROX_102,400_TO_108,000`
21. `EARLY_VS_LATE_BEHAVIORAL_CHANGE = EXISTING_WEAKNESS_AMPLIFIED_BY_WINNER/CAPITAL/NOTIONAL_SCALE; NOT_PROVEN_BEHAVIORAL_REGRESSION`
22. `PRIMARY_LATE_LOSS_MECHANISM = HOLD_CONFIRMATION_LAG_AMPLIFIED_BY_CAPITAL_SCALE`
23. `PRODUCTION_CHANGE_JUSTIFIED = NO`
24. `SHADOW_FOLLOWUP_JUSTIFIED = YES`
25. `NEXT_RECOMMENDED_STEP = READ-ONLY/SHADOW PM HOLD profit-retention escalation design with gain-retained winner controls; keep BZ BQ refinement separate.`
26. `FINAL_JUDGMENT = PHASE32_CA_LATE_LOSS_TAIL_WORSE_AFTER_NORMALIZATION_HOLD_CONFIRMATION_LAG_AMPLIFIED_BY_WINNER_NOTIONAL_AND_CAPITAL_SCALE_CHARACTERIZED_READ_ONLY_SHADOW_FOLLOWUP_JUSTIFIED`

