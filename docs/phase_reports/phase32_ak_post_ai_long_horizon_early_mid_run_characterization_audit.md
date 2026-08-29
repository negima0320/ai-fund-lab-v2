# Phase32-AK — Post-AI Long-Horizon Early/Mid-Run Characterization Audit

## Executive Summary

The latest Post-AI long Historical fresh-run artifact is `runtime-test-historical-extended-smoke-20260827T093649849074Z`. The run is still live; this audit freezes coverage at the latest valuation-ready day observed during the read-only scan: `2023-08-29`. A partial `2023-08-30` directory exists, but valuation was not ready, so it is excluded from quantified coverage.

Long-horizon REENTRY repair is functioning on the actual path. Through `2023-08-29`, the run has:

- `5,075` semantic REENTRY rows.
- `2,017` strict/non-GENERIC prior-context rows.
- `12` final `REENTRY_ELIGIBLE` rows.
- `14` actual REENTRY fills across `14` unique symbols.
- All REENTRY fills are second campaigns (`*-0002`), with no observed repeated same-symbol REENTRY loop yet.

Cash behavior is improved versus the old "never redeploys later" failure mode, but only partially. The system can redeploy after high-cash drawdowns: exposure fell to `15.44%` on `2023-04-25`, then later reached `74.92%` on `2023-05-09`, `93.11%` on `2023-06-07`, and `98.78%` on `2023-08-29`. However, high-cash days still occur, and the main observed blocker is not a broken REENTRY semantic bridge. It is mostly PC/MCC cash optionality/no-valid-competitor behavior after sell-driven de-risking, often with recovery-incomplete, concentration, lot-residual, or cautious-market reason codes.

The `2023-04-07` large daily loss is measurement-clean. Cash, quantity, and realized PnL are unchanged; market value drops by exactly `189,380`, driven mainly by `67310` and `59350`, and all inspected valuation rows use adjusted basis with corporate-action ambiguity `CLEAR` and valuation price authority `PASS`.

## Run Identity / Coverage

- Run id: `runtime-test-historical-extended-smoke-20260827T093649849074Z`
- Run root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T093649849074Z`
- Profile: `historical-extended-smoke`
- Run status at inspection: `RUNNING`
- Next job in `run_state.json`: `2023-08-30:sell_planning`
- Quantified valuation-ready coverage: `2022-10-03` through `2023-08-29`
- Valuation-ready business days counted: `224`
- Source baseline: `source_dirty=true` as recorded in run state

User milestone reconciliation passed for the cited checkpoints:

| Date | Equity | Cash | Exposure | Positions |
| --- | ---: | ---: | ---: | ---: |
| 2023-03-31 | 1,713,510 | 599,210 | 65.03% | 7 |
| 2023-04-03 | 1,776,740 | 121,910 | 93.14% | 9 |
| 2023-04-06 | 1,851,480 | 526,510 | 71.56% | 7 |
| 2023-04-07 | 1,662,100 | 526,510 | 68.32% | 7 |
| 2023-04-12 | 1,514,100 | 123,090 | 91.87% | 9 |
| 2023-04-24 | 1,473,350 | 1,214,660 | 17.56% | 4 |
| 2023-04-25 | 1,479,720 | 1,251,260 | 15.44% | 5 |
| 2023-05-09 | 1,526,270 | 382,760 | 74.92% | 13 |
| 2023-06-07 | 1,588,580 | 109,430 | 93.11% | 11 |
| 2023-06-12 | 1,609,390 | 109,930 | 93.17% | 11 |
| 2023-07-10 | 1,624,440 | 95,980 | 94.09% | 12 |
| 2023-07-25 | 1,601,350 | 171,460 | 89.29% | 16 |
| 2023-08-14 | 1,549,700 | 221,150 | 85.73% | 14 |
| 2023-08-22 | 1,637,760 | 361,480 | 77.93% | 12 |

## REENTRY Funnel

Canonical day-symbol REENTRY funnel through `2023-08-29`:

| Stage | Count |
| --- | ---: |
| Semantic REENTRY rows | 5,075 |
| Unique semantic REENTRY symbols | 260 |
| Strict prior context | 2,017 |
| Non-GENERIC prior context | 2,017 |
| Cooldown PASS | 4,417 |
| Recovery PASS | 19 |
| Safety PASS | 5,075 |
| Final `REENTRY_ELIGIBLE` | 12 |
| Positive target | 12 |
| Selected | 4,801 |
| PC competitor selected | observed on selected/positive rows |
| PS executable quantity > 0 | 25 |
| Actual REENTRY fills | 14 |
| Unique filled REENTRY symbols | 14 |
| Second campaign fills | 14 |
| Third-or-later campaign fills | 0 |

The main narrowing point is recovery/requalification, not safety. Safety passed on every semantic REENTRY row observed after Phase32-AI.

## Monthly REENTRY Funnel

| Month | Semantic | Strict/Non-GENERIC | Recovery PASS | REENTRY_ELIGIBLE | Positive | REENTRY fills | REENTRY notional |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10 | 164 | 109 | 2 | 2 | 2 | 1 | 71,150 |
| 2022-11 | 283 | 132 | 0 | 0 | 0 | 1 | 7,800 |
| 2022-12 | 319 | 165 | 0 | 0 | 0 | 2 | 29,500 |
| 2023-01 | 383 | 182 | 1 | 1 | 1 | 1 | 30,360 |
| 2023-02 | 417 | 139 | 0 | 0 | 0 | 0 | 0 |
| 2023-03 | 504 | 180 | 2 | 1 | 1 | 0 | 0 |
| 2023-04 | 621 | 201 | 1 | 1 | 1 | 2 | 114,600 |
| 2023-05 | 653 | 240 | 1 | 1 | 1 | 2 | 128,700 |
| 2023-06 | 667 | 266 | 9 | 4 | 4 | 3 | 252,950 |
| 2023-07 | 513 | 189 | 0 | 0 | 0 | 0 | 0 |
| 2023-08 | 551 | 214 | 3 | 2 | 2 | 2 | 438,510 |

REENTRY is increasing in semantic universe and strict context through mid-run, but final eligibility and fills are lumpy. The repair effect is positive, not yet dominant in capital deployment.

## Monthly NEW / REENTRY / ADD BUY Mix

| Month | BUY_NEW fills | REENTRY fills | BUY_ADD fills | BUY_NEW notional | REENTRY notional | BUY_ADD notional | REENTRY share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10 | 43 | 1 | 5 | 2,817,180 | 71,150 | 76,140 | 2.4% |
| 2022-11 | 26 | 1 | 3 | 1,553,300 | 7,800 | 48,670 | 0.5% |
| 2022-12 | 30 | 2 | 0 | 1,655,780 | 29,500 | 0 | 1.8% |
| 2023-01 | 36 | 1 | 0 | 2,571,070 | 30,360 | 0 | 1.2% |
| 2023-02 | 37 | 0 | 1 | 2,308,900 | 0 | 58,640 | 0.0% |
| 2023-03 | 32 | 0 | 0 | 3,665,470 | 0 | 0 | 0.0% |
| 2023-04 | 31 | 2 | 0 | 3,928,370 | 114,600 | 0 | 2.8% |
| 2023-05 | 28 | 2 | 2 | 2,390,090 | 128,700 | 152,900 | 4.8% |
| 2023-06 | 34 | 3 | 0 | 2,994,020 | 252,950 | 0 | 7.8% |
| 2023-07 | 41 | 0 | 0 | 4,091,730 | 0 | 0 | 0.0% |
| 2023-08 | 30 | 2 | 0 | 2,848,360 | 438,510 | 0 | 13.3% |

BUY_NEW remains the main redeployment engine. REENTRY contributes real capital, especially in June and August, but it is not the primary source of exposure restoration.

## Cash / Exposure Characterization

Overall across valuation-ready days:

- Average exposure: `73.40%`
- Median exposure: `77.09%`
- Cash >= 30% days: `78`
- Cash >= 40% days: `42`
- Cash >= 50% days: `20`
- Cash >= 70% days: `9`

Observed runtime deployment-posture groups:

| Posture | Days | Average Cash | Median Cash | Average Exposure | Median Exposure |
| --- | ---: | ---: | ---: | ---: | ---: |
| `DEPLOY` | 196 | 24.34% | 20.75% | 75.66% | 79.25% |
| `BALANCED_DEPLOYMENT` | 28 | 42.39% | 39.07% | 57.61% | 60.93% |

The artifact set did not expose the requested BULL/RECOVERY/RANGE/CORRECTION/BEAR labels as direct top-level daily regime labels in the scanned PC valuation summary. The available canonical deployment posture is used instead.

## High-Cash Root-Cause Attribution

Cash >= 50% days are concentrated around April and a few later sell clusters:

| Month | Cash >= 50% days | Primary first deployment blocker |
| --- | ---: | --- |
| 2022-10 | 1 | PC/MCC cash optionality |
| 2022-12 | 1 | PC/MCC cash optionality |
| 2023-01 | 2 | PC/MCC cash optionality |
| 2023-04 | 8 | mixed, primarily PC/MCC cash optionality after sell-driven de-risking |
| 2023-05 | 5 | PC/MCC cash optionality / no valid competitor |
| 2023-06 | 2 | PC/MCC cash optionality |
| 2023-08 | 1 | PC/MCC cash optionality |

The most repeated authoritative blockers/reasons on high-cash days are:

- `CASH_PRE_FINAL_INTERACTION_WINNER`
- `MARGINAL_OPPORTUNITY_SET`
- `NO_VALID_COMPETITOR`
- `RECOVERY_INCOMPLETE_OPTIONALITY_ELEVATED`
- `CONCENTRATION_BLOCK`
- `CONCENTRATION_OPTIONALITY`
- `CAUTIOUS_MARKET_OPTIONALITY_ELEVATED`
- `LOT_RESIDUAL_OPTIONALITY`
- `UNAVOIDABLE_LOT_RESIDUAL`

This is not a pure candidate-scarcity diagnosis: candidates and some positive targets still exist on most high-cash days. It is also not primarily a REENTRY safety false-positive diagnosis: REENTRY safety is always `PASS`, but final REENTRY recovery/eligibility is rare.

## April Deep Dive

| Date | Equity | Cash | Exposure | Pos | Candidates | Final eligible | REENTRY eligible | Positive | PS exec | BUY_NEW | REENTRY BUY | SELL | PC/PS winner |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2023-04-03 | 1,776,740 | 121,910 | 93.14% | 9 | 52 | 44 | 0 | 13 | 5 | 2 | 0 | 0 | CASH/CASH |
| 2023-04-05 | 1,778,210 | 1,020,910 | 42.59% | 4 | 51 | 19 | 0 | 8 | 6 | 0 | 0 | 3 | CASH/CASH |
| 2023-04-07 | 1,662,100 | 526,510 | 68.32% | 7 | 52 | 37 | 0 | 9 | 3 | 0 | 0 | 0 | CASH/CASH |
| 2023-04-10 | 1,655,780 | 1,034,790 | 37.50% | 4 | 52 | 19 | 0 | 9 | 8 | 1 | 0 | 4 | CASH/CASH |
| 2023-04-19 | 1,485,960 | 881,160 | 40.70% | 5 | 50 | 21 | 0 | 5 | 4 | 0 | 0 | 4 | CASH/CASH |
| 2023-04-20 | 1,478,160 | 1,074,960 | 27.28% | 6 | 50 | 17 | 0 | 6 | 5 | 3 | 0 | 3 | NEW/NEW |
| 2023-04-21 | 1,466,700 | 1,009,960 | 31.14% | 6 | 50 | 19 | 0 | 6 | 2 | 1 | 0 | 1 | CASH/CASH |
| 2023-04-24 | 1,473,350 | 1,214,660 | 17.56% | 4 | 51 | 19 | 0 | 5 | 2 | 0 | 0 | 2 | CASH/CASH |
| 2023-04-25 | 1,479,720 | 1,251,260 | 15.44% | 5 | 51 | 17 | 0 | 7 | 3 | 2 | 0 | 1 | CASH/CASH |
| 2023-05-09 | 1,526,270 | 382,760 | 74.92% | 13 | 53 | 37 | 0 | 15 | 3 | 3 | 0 | 0 | NEW/NEW |

April classification: `F. mixed`. The largest drivers are genuine drawdown/PM sell-down plus PC/MCC cash optionality and recovery-incomplete/no-valid-competitor behavior. REENTRY residual suppression contributes to low REENTRY redeployment, but it is not the primary April cash cause because NEW redeployment also becomes selective and cash wins repeatedly even with positive candidates.

## Re-Deployment After April

The exposure rebuild from `15.44%` on `2023-04-25` to `74.92%` on `2023-05-09` and >90% in June is explained by the actual artifacts as follows:

- Eligible/positive candidate breadth recovers enough for BUY_NEW to become the capital winner on key days.
- NEW fills dominate redeployment capital: `28` BUY_NEW fills in May and `34` in June.
- REENTRY participates but is secondary: `2` REENTRY fills in May and `3` in June.
- Position count expands from `5` on `2023-04-25` to `13` on `2023-05-09`, then remains capable of >90% exposure in June.
- The system does not remain trapped in cash; PC/PS winners switch back to `NEW_BUY` on deployment days.

The actual causal path is therefore: sell-driven cash increase -> cautious/cash optionality while opportunity/recovery is weak -> NEW-led redeployment as positive executable candidates return -> additional REENTRY participation where recovery fully qualifies.

## April Drawdown

Peak/trough within the April drawdown window:

- Peak equity: `1,851,480` on `2023-04-06`
- Trough equity: `1,466,700` on `2023-04-21`
- Peak-to-trough drawdown: `-20.78%`

Segment `2023-04-03` through `2023-04-28`:

- Start equity: `1,776,740`
- End equity: `1,498,190`
- Segment return: `-15.68%`
- Average exposure: `55.23%`
- Median exposure: `59.88%`
- BUY_NEW fills: `31`
- REENTRY fills: `2`
- SELL fills: `32`

Diagnosis: the April drawdown is a mix of market/position shock and subsequent PM de-risking. The most material single-day loss is `2023-04-07`; subsequent high cash is largely the consequence of sell activity plus selective redeployment, not a valuation contamination symptom.

## 2023-04-07 Reconciliation

`2023-04-07` reconciles cleanly:

- Cash delta from `2023-04-06`: `0`
- Realized PnL delta: `0`
- Market value delta: `-189,380`
- Equity delta: `-189,380`
- Fill count: `0`

Symbol mark-to-market contributors:

| Symbol | Quantity | 2023-04-06 price | 2023-04-07 price | Market-value delta |
| --- | ---: | ---: | ---: | ---: |
| 67310 | 100 | 4,000.0 | 3,000.0 | -100,000 |
| 59350 | 100 | 5,490.0 | 4,585.0 | -90,500 |
| 79970 | 100 | 722.0 | 648.0 | -7,400 |
| 97340 | 100 | 1,193.0 | 1,191.0 | -200 |
| 94320 | 200 | 157.6 | 157.2 | -80 |
| 73180 | 100 | 255.5 | 256.5 | +100 |
| 43880 | 100 | 1,274.0 | 1,361.0 | +8,700 |

All inspected rows report:

- `corporate_action_ambiguity_status=CLEAR`
- `valuation_price_authority=PASS`
- adjusted execution/fill/quantity/valuation basis
- fresh current quote status

Measurement reconciliation judgment: `PASS`.

## Segment Performance

| Segment | Dates | Start Eq | End Eq | Return | Max Eq | Max DD | Avg Exp | Med Exp | Avg Cash | BUY_NEW | REENTRY | ADD | SELL |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 2022-10-03 to 2022-12-30 | 1,012,350 | 1,129,150 | +11.54% | 1,158,370 | -4.71% | 77.84% | 80.49% | 239,868 | 99 | 4 | 8 | 102 |
| B | 2023-01-04 to 2023-03-31 | 1,126,090 | 1,713,510 | +52.16% | 1,713,510 | -4.94% | 77.28% | 79.63% | 287,544 | 105 | 1 | 1 | 118 |
| C | 2023-04-03 to 2023-04-28 | 1,776,740 | 1,498,190 | -15.68% | 1,851,480 | -20.78% | 55.23% | 59.88% | 692,408 | 31 | 2 | 0 | 32 |
| D | 2023-05-01 to 2023-06-30 | 1,506,030 | 1,630,210 | +8.25% | 1,680,970 | -5.75% | 65.09% | 69.68% | 540,238 | 62 | 5 | 2 | 88 |
| E | 2023-07-03 to 2023-08-29 | 1,643,470 | 1,653,120 | +0.59% | 1,653,120 | -7.44% | 78.51% | 78.83% | 341,834 | 71 | 2 | 0 | 68 |

This is not a monotonic late-run cash freeze. It is a sharp April drawdown and high-cash phase followed by partial redeployment in May/June and high exposure again by late August.

## Optional Pre/Post Comparison

No appropriate complete Pre-AI long-horizon run with the same coverage was present under the active `reports/runtime_tests/runs` artifact root. This audit therefore does not force a pre/post performance comparison. The characterization is based on the current actual Post-AI run only.

## REENTRY Campaign Descriptive Quality

Observed REENTRY fills:

| Date | Symbol | Campaign | Quantity | Notional |
| --- | --- | --- | ---: | ---: |
| 2022-10-26 | 83060 | `pc-3b0b0ca173235416-83060-0002` | 100 | 71,150 |
| 2022-11-11 | 76470 | `pc-491b476ad402b5d3-76470-0002` | 300 | 7,800 |
| 2022-12-07 | 67210 | `pc-6dd221aff11c0db3-67210-0002` | 100 | 14,700 |
| 2022-12-19 | 94340 | `pc-1d050773f794160f-94340-0002` | 100 | 14,800 |
| 2023-01-23 | 94320 | `pc-091f6fd4e6c166be-94320-0002` | 200 | 30,360 |
| 2023-04-12 | 45860 | `pc-d3cd9711fc4a037f-45860-0002` | 300 | 51,000 |
| 2023-04-18 | 27210 | `pc-8933d080b9ab7d82-27210-0002` | 200 | 63,600 |
| 2023-05-15 | 76010 | `pc-d617ae61a9d3b317-76010-0002` | 300 | 76,200 |
| 2023-05-30 | 21340 | `pc-872515279e4deee9-21340-0002` | 2,100 | 52,500 |
| 2023-06-13 | 44920 | `pc-0489e13d1ed31785-44920-0002` | 100 | 45,600 |
| 2023-06-16 | 37820 | `pc-5f2ebf1cc776493d-37820-0002` | 900 | 44,100 |
| 2023-06-20 | 99840 | `pc-a3fa757ad25cf898-99840-0002` | 100 | 163,250 |
| 2023-08-04 | 65260 | `pc-38d0744a7b27f4db-65260-0002` | 100 | 375,000 |
| 2023-08-14 | 65730 | `pc-aaf5a539a76e4072-65730-0002` | 300 | 63,510 |

Descriptive outcome state:

- Closed REENTRY campaigns observed: `12`
- Still open at coverage end: `2` (`94320`, `65730`)
- Same-day closed REENTRY campaigns: `0`
- Next-day closed REENTRY campaigns: `2`
- 2-5BD closed REENTRY campaigns: `3`
- 6-10BD closed REENTRY campaigns: `3`
- 11BD+ closed REENTRY campaigns: `4`
- Repeated same-symbol REENTRY fills: `0`

No material repeated REENTRY churn loop is observed through the audited coverage.

## Position-Count Contract Check

Maximum observed position count is `17` on `2023-01-26`, `2023-08-28`, and `2023-08-29`.

Current safety/config evidence:

- `configs/safety/portfolio_limits.json` has `position_count.safety_hard_maximum=null`.
- `position_count.authority="No routine fixed position-count safety cap"`.
- Safety controls are concentration, no-leverage cash/equity boundary, lot feasibility, pending reservation, and explicit emergency review gates.
- `configs/strategy/position_sizing.json` has `strategy_maximum_position_weight=0.18`.
- Safety concentration cap is `0.25`.

Therefore `17` positions is contract-compatible under the current SoT. It is not a violation of the old legacy `max_positions=5` concept.

## Cash-Problem Reassessment

Classification: `PARTIALLY_IMPROVED`.

Evidence for improvement:

- REENTRY context materializes long-horizon: `2,017` strict/non-GENERIC rows.
- REENTRY actual fills occur beyond `83060`: `14` fills across `14` symbols.
- The run can return from high cash to high exposure after April.
- Late observed exposure reaches `98.78%` on `2023-08-29`.

Evidence for remaining bottleneck:

- Final `REENTRY_ELIGIBLE` remains only `12` rows out of `5,075` semantic rows.
- Cash >= 50% still occurs on `20` days.
- High-cash days repeatedly show PC/MCC cash optionality, `NO_VALID_COMPETITOR`, recovery-incomplete optionality, concentration, and lot-residual reasons.
- BUY_NEW, not REENTRY, remains the dominant redeployment mechanism.

## Defects / Residual Risks

No new mandatory production defect is established by this read-only audit.

Residual risks to monitor:

- REENTRY recovery qualification may still be materially narrow even though semantic context and safety are repaired.
- PC/MCC cash optionality can dominate after sell-downs even when some positive executable candidates exist.
- `NO_VALID_COMPETITOR` appears during high-cash periods and deserves continued attribution.
- Fill lineage/campaign parity caveats from Phase32-AJ should continue to be monitored, although they did not block this characterization.

## Next Monitoring Points

Continue the user-operated long run. The next useful monitoring point is after a post-`2023-08-29` window with another high-cash episode or another 50-100 business days, whichever comes first. Focus on:

- Whether REENTRY final eligibility rises with the restored universe.
- Whether PC/MCC cash optionality still creates extended cash plateaus.
- Whether high exposure remains recoverable after future sell-driven de-risking.
- Whether third-or-later campaigns begin to appear, and whether they create churn.

## Final Judgments

PHASE32_AK_RUN_ID = runtime-test-historical-extended-smoke-20260827T093649849074Z

PHASE32_AK_COVERAGE_END = 2023-08-29

PHASE32_AK_REENTRY_SEMANTIC_TOTAL = 5075

PHASE32_AK_REENTRY_ELIGIBLE_TOTAL = 12

PHASE32_AK_REENTRY_FILL_TOTAL = 14

PHASE32_AK_REENTRY_UNIQUE_FILLED_SYMBOLS = 14

PHASE32_AK_REENTRY_INCREASING_OVER_TIME = PARTIAL

PHASE32_AK_AVERAGE_EXPOSURE = 73.40%

PHASE32_AK_BULL_AVERAGE_EXPOSURE = UNRESOLVED_NO_BULL_LABEL_IN_SCANNED_ARTIFACTS

PHASE32_AK_CASH_GE_50_DAYS = 20

PHASE32_AK_APRIL_HIGH_CASH_PRIMARY_CAUSE = MIXED_PC_MCC_CASH_OPTIONALITY_AFTER_SELL_DRIVEN_DERISKING_WITH_RECOVERY_INCOMPLETE_AND_NO_VALID_COMPETITOR_SIGNALS

PHASE32_AK_REDEPLOYMENT_CAUSE = BUY_NEW_LED_REDEPLOYMENT_WITH_SECONDARY_REENTRY_PARTICIPATION_AFTER_ELIGIBLE_POSITIVE_EXECUTABLE_CANDIDATES_RETURNED

PHASE32_AK_APRIL_PEAK_TO_TROUGH_DRAWDOWN = -20.78%

PHASE32_AK_2023_04_07_MEASUREMENT_RECONCILIATION = PASS

PHASE32_AK_REENTRY_CHURN_MATERIAL = NO

PHASE32_AK_POSITION_COUNT_CONTRACT = PASS

PHASE32_AK_REENTRY_REPAIR_LONG_HORIZON_EFFECT = POSITIVE

PHASE32_AK_CASH_PROBLEM_STATUS = PARTIALLY_IMPROVED

PHASE32_AK_NEW_MANDATORY_DEFECT_FOUND = NO

PHASE32_AK_PRODUCTION_REPAIR_JUSTIFIED_NOW = NO

PHASE32_AK_LONG_RUN_CONTINUE = YES

PHASE32_AK_NEXT_MONITORING_POINT = Next high-cash episode or next 50-100 completed business days; monitor REENTRY eligibility, PC/MCC cash optionality, NO_VALID_COMPETITOR, and campaign churn.
