# Phase31-G120 — Post-G119 Long-Horizon Performance / Capital Allocation Characterization

## PRIMARY_JUDGMENT

PHASE31_G120_POST_G119_PERFORMANCE_CHARACTERIZED_NEXT_BOUNDARY_IDENTIFIED

## Scope

- Task type: READ-ONLY CHARACTERIZATION
- Primary run: `runtime-test-historical-extended-smoke-20260825T135619843503Z`
- Audit cutoff: run-state completed list read while run was still `RUNNING`
- Completed business dates audited: `215`
- Completed window: `2022-10-03` through `2023-08-16`
- Next job observed at cutoff: `2023-08-17:strategy_shadow_generation`
- Comparison baseline requested: `runtime-test-historical-extended-smoke-20260824T055234719725Z`
- Baseline artifact availability in this workspace: `NOT_FOUND`

No code, config, threshold, score, weight, run state, fresh-run, resume, replay, or Historical execution was changed or executed for this audit.

## Evidence Sources

Primary evidence was read from immutable completed artifacts under:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T135619843503Z
```

Main artifacts used:

- `run_state.json`
- `daily/<date>/strategy_eod_shadow/position_sizing.json`
- `daily/<date>/current_valuation_refresh/current_valuation_manifest.json`
- `daily/<date>/strategy/market_context.json`
- `daily/<date>/strategy/portfolio_policy.json`
- `daily/<date>/strategy/portfolio_construction.json`
- `daily/<date>/strategy/position_sizing.json`
- `daily/<date>/execution/fills.json`
- `daily/<date>/positions/position_campaigns.json`

The requested baseline run ID was searched under `reports/` and `reports/runtime_tests/runs/`; no matching artifact directory was present, so baseline divergence is limited to stated prior anchors and cannot be fully recomputed in G120.

## Measurement Integrity

MEASUREMENT_INTEGRITY = PASS_WITH_CAMPAIGN_ATTRIBUTION_LIMITATION

The EOD equity source matched the visible anchor values:

| Date | Equity | Cash | Market value | Positions | Exposure |
|---|---:|---:|---:|---:|---:|
| 2023-04-10 | 1,479,100 | 984,700 | 494,400 | 4 | 33.43% |
| 2023-04-21 | 1,299,890 | 818,520 | 481,370 | 7 | 37.03% |
| 2023-06-19 | 1,457,310 | 397,530 | 1,059,780 | 12 | 72.72% |
| 2023-08-08 | 1,411,530 | 556,350 | 855,180 | 9 | 60.59% |
| 2023-08-16 | 1,432,820 | 403,620 | 1,029,200 | 10 | 71.83% |

Campaign-level PnL is usable for characterization via campaign relative return and BUY event cost basis, but closed campaign event records are observability reconstructions, not a complete accounting ledger. Equity and fill-level cash/equity metrics are treated as primary.

## Overall Performance

CURRENT_PERFORMANCE_QUALITY = STRONG_BUT_PROFIT_RETENTION_AND_ADD_SCALING_LIMITED

| Metric | Value |
|---|---:|
| Initial cash basis | 1,000,000 |
| Final completed equity | 1,432,820 |
| Total return | +43.28% |
| Peak equity | 1,479,100 |
| Peak return | +47.91% |
| Peak date | 2023-04-10 |
| Max drawdown | -12.53% |
| MDD peak | 2023-04-10 |
| MDD trough | 2023-05-15 |
| Current drawdown from ATH | -3.13% |
| Average exposure | 71.84% |
| Median exposure | 75.97% |
| Average cash | 359,219 |

Position-count distribution:

```text
10:36, 12:32, 11:25, 13:19, 7:16, 9:16, 8:16, 14:14,
15:11, 5:9, 16:8, 6:6, 4:3, 17:2, 18:1, 2:1
```

Monthly returns:

| Month | Completed BD | Return | Ending equity |
|---|---:|---:|---:|
| 2022-10 | 20 | +5.94% | 1,059,370 |
| 2022-11 | 20 | +5.10% | 1,113,410 |
| 2022-12 | 22 | +2.35% | 1,139,590 |
| 2023-01 | 19 | +8.36% | 1,234,890 |
| 2023-02 | 19 | +0.91% | 1,246,120 |
| 2023-03 | 22 | +15.30% | 1,436,830 |
| 2023-04 | 20 | -7.60% | 1,327,650 |
| 2023-05 | 20 | +3.84% | 1,378,580 |
| 2023-06 | 22 | +1.63% | 1,401,020 |
| 2023-07 | 20 | +0.32% | 1,405,480 |
| 2023-08 | 11 | +1.95% | 1,432,820 |

## Regime / Market Quality Characterization

Regime counts:

| Regime | Days | Average exposure | BUY_NEW | BUY_ADD | SELL_REDUCE | SELL_EXIT |
|---|---:|---:|---:|---:|---:|---:|
| BULL | 93 | 74.74% | 149 | 9 | 22 | 82 |
| RANGE | 42 | 76.33% | 81 | 1 | 2 | 39 |
| RECOVERY | 41 | 74.56% | 60 | 3 | 14 | 28 |
| BEAR | 28 | 53.17% | 51 | 5 | 2 | 38 |
| CORRECTION | 11 | 67.64% | 19 | 0 | 1 | 13 |

Market Quality counts:

```text
CONFLICTED_MARKET_STRUCTURE: 70
SHORT_TERM_BREADTH_BREAKDOWN: 51
HEALTHY_EXPANSION: 41
RECOVERY_CONFIRMATION_INCOMPLETE: 40
SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH: 12
HEALTHY_RECOVERY: 1
```

Risk Pacing intent counts:

```text
CAUTIOUS_DEPLOYMENT: 133
GRADUAL_REDEPLOYMENT: 40
NORMAL_DEPLOYMENT: 42
```

Average target gross exposure by Market Quality:

| Market Quality | Days | Avg target gross exposure | Median |
|---|---:|---:|---:|
| SHORT_TERM_BREADTH_BREAKDOWN | 51 | 0.903 | 1.000 |
| CONFLICTED_MARKET_STRUCTURE | 70 | 0.937 | 1.000 |
| RECOVERY_CONFIRMATION_INCOMPLETE | 40 | 1.000 | 1.000 |
| HEALTHY_EXPANSION | 41 | 1.000 | 1.000 |
| SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH | 12 | 1.000 | 1.000 |
| HEALTHY_RECOVERY | 1 | 1.000 | 1.000 |

Interpretation: Market Quality / Risk Pacing is not a hard BUY gate in this run; BUYs occur across BEAR, RANGE, RECOVERY, BULL, and CORRECTION. However, by the observed cutoff the pacing target is often 1.0 even in conflicted/weak states, so the realized behavior is more participation-heavy than strongly defensive.

## Major Performance Phases

MAJOR_PERFORMANCE_PHASES:

| Phase | Window | Return | Avg exposure | Fill characterization |
|---|---|---:|---:|---|
| Initial growth | 2022-10-03 to 2023-04-10 | +47.91% | 74.79% | 218 BUY_NEW, 9 symbol-level BUY_ADD, 20 REDUCE, 130 EXIT |
| April drawdown | 2023-04-11 to 2023-04-21 | -12.12% | 52.46% | 16 BUY_NEW, 3 symbol-level BUY_ADD, 1 REDUCE, 12 EXIT |
| Recovery | 2023-04-24 to 2023-06-19 | +12.11% | 65.14% | 60 BUY_NEW, 6 symbol-level BUY_ADD, 13 REDUCE, 31 EXIT |
| Post-recovery degradation | 2023-06-20 to 2023-08-16 | -1.68% from 2023-06-19 | about 73% | continued BUY_NEW with limited campaign-level scaling |

The system preserved a strong early profit engine through March, suffered a concentrated April drawdown, recovered materially by June, then moved sideways/down mildly while still holding relatively high exposure.

## Trading / Campaign Characterization

Fill-derived counts:

| Fill class | Count | Gross notional |
|---|---:|---:|
| BUY_NEW | 360 | 29,533,610 |
| BUY_ADD, symbol-level reconstructed | 18 | 655,770 |
| SELL_REDUCE | 41 | 357,030 |
| SELL_EXIT | 200 | 16,679,270 |
| SELL_OTHER | 163 | 12,556,700 |

Campaign snapshot at cutoff:

| Metric | Value |
|---|---:|
| Campaigns | 296 |
| Closed | 285 |
| Open | 11 |
| Campaigns with more than one BUY event | 0 |
| Gross profit estimate | 945,225 |
| Gross loss estimate | -527,276 |
| Profit Factor estimate | 1.79 |
| Win rate estimate | 48.99% |
| Net campaign contribution estimate | 417,949 |

Top positive campaign contributors:

| Symbol | Open | Closed | PnL est | Return | BUY events | Giveback |
|---|---|---|---:|---:|---:|---:|
| 44440 | 2023-03-16 | 2023-03-22 | +56,000 | +51.19% | 1 | 0.00% |
| 64240 | 2023-03-16 | 2023-03-23 | +41,400 | +30.58% | 1 | 0.00% |
| 80290 | 2022-11-15 | 2022-12-20 | +39,700 | +17.88% | 1 | 2.07% |
| 72140 | 2023-05-22 | 2023-05-26 | +29,900 | +22.55% | 1 | 0.00% |
| 88900 | 2023-05-22 | 2023-07-14 | +29,100 | +10.87% | 1 | 8.78% |
| 69730 | 2022-10-25 | 2022-12-05 | +28,600 | +19.07% | 1 | 8.53% |
| 40520 | 2023-06-15 | 2023-07-14 | +28,100 | +27.52% | 1 | 23.11% |
| 93410 | 2023-05-30 | 2023-06-19 | +27,900 | +14.83% | 1 | 9.94% |
| 95560 | 2023-04-03 | 2023-04-05 | +26,000 | +8.35% | 1 | 0.00% |
| 78860 | 2022-11-14 | 2022-12-07 | +24,500 | +23.22% | 1 | 15.73% |

Top negative campaign contributors:

| Symbol | Open | Closed | PnL est | Return | Giveback |
|---|---|---|---:|---:|---:|
| 60220 | 2023-04-11 | 2023-04-13 | -45,400 | -15.13% | 0.00% |
| 51890 | 2023-04-10 | 2023-04-17 | -44,000 | -14.84% | 25.30% |
| 51320 | 2023-01-30 | 2023-02-01 | -21,660 | -9.70% | 0.00% |
| 40750 | 2023-06-20 | 2023-06-26 | -21,200 | -13.75% | 14.85% |
| 30410 | 2023-05-25 | 2023-06-02 | -19,326 | -14.42% | 15.77% |
| 36670 | 2023-06-09 | 2023-06-19 | -17,500 | -21.88% | 28.12% |
| 59350 | 2023-03-06 | 2023-03-13 | -17,000 | -8.33% | 9.31% |
| 39450 | 2023-02-16 | 2023-02-20 | -16,800 | -10.15% | 0.00% |
| 41990 | 2022-11-09 | 2022-11-14 | -15,300 | -9.87% | 3.94% |
| 73690 | 2023-07-26 | 2023-08-02 | -12,500 | -9.86% | 14.19% |

Profit concentration remains high: the top 10 positive campaign contributors explain about 79% of estimated net campaign contribution. This is consistent with a winner-driven engine, but also means profit retention and winner scaling remain material.

## G115 / G119 ADD Effectiveness

G115_SUPPRESSES_ALL_ADD = NO

STRONG_WINNER_MULTI_INCREMENT_SURVIVES_ACTUAL = NO

ADD_CAPITAL_BECAME_MORE_SELECTIVE = PARTIAL

Observed:

- Symbol-level repeated BUY fills exist: `18`.
- Campaign lifecycle multi-BUY campaigns at cutoff: `0`.
- Top symbol-level repeated BUY names include `94340`, `94320`, `48330`, `76470`, `37790`, `45410`, `54010`, `93180`, `45860`, `77760`, `21340`, and `59550`.
- G115 staged strings are present in PC artifacts, including `ADD_MARGINAL_PREFERRED`, `G115_STAGED_ADD_MARGINAL_ONE_INCREMENT_AUTHORIZED`, `COMPARABLE_MARGINAL_RESIDUAL_SHOULDER_ONE_INCREMENT_AUTHORIZED`, and `CASH_MARGINAL_PREFERRED`.

Interpretation:

G115 did not suppress all ADD-like BUY activity, but actual campaign-level winner scaling did not materialize as repeated BUY events within the same campaign identity. The strategy still finds large winners, but the canonical lifecycle does not show the desired:

```text
small initial position -> confirmation -> ADD -> scaled winner -> REDUCE/EXIT
```

pattern as a robust actual-path behavior.

## Winner Scaling

WINNER_SCALING_BEHAVIOR_PRESENT = WEAK

Evidence:

- Large winners exist: `44440`, `64240`, `80290`, `72140`, `88900`, `69730`, `40520`, `93410`.
- Those top contributors show `BUY events = 1` in the campaign snapshot.
- Symbol-level repeated BUYs exist, but they do not appear as multi-increment campaign scaling in the canonical campaign lifecycle.

This means the current profit engine is more accurately described as:

```text
many single-entry campaigns + occasional symbol re-entry
```

rather than canonical winner amplification through repeated ADD within active campaigns.

## April Drawdown Decomposition

APRIL_DRAWDOWN_PRIMARY_SOURCE = NEWLY_ENTERED_SHORT_LOSERS_PLUS_INCUMBENT_GIVEBACK

The primary visible drawdown was:

```text
2023-04-10 equity 1,479,100
2023-04-21 equity 1,299,890
Delta -179,210
```

Material contributors include:

- Newly entered short losers: `60220` opened 2023-04-11 and closed 2023-04-13 at about `-45,400`; `39200`, `66560`, `38100`, and related short-lived entries also contributed.
- Incumbent / peak-adjacent giveback: `51890` opened 2023-04-10 and closed 2023-04-17 at about `-44,000`; `43880` had material giveback by its 2023-04-10 exit.
- Broad de-risking occurred: exposure averaged only `52.46%` in the drawdown window versus `74.79%` in initial growth, but the drawdown was not purely under-deployment; realized campaign losses and exits were material.

The April event therefore looks like a mixed drawdown: a peak-date/near-peak entry loss cluster plus retained exposure to weakening incumbents, not an accounting or submit/execution artifact.

## Profit Retention / Giveback

PROFIT_RETENTION = PARTIAL

Largest observed giveback ratios:

| Symbol | MFE | Final/cutoff return | Giveback | PnL est |
|---|---:|---:|---:|---:|
| 21340 | 123.53% | 70.59% | 52.94% | +21,600 |
| 59550 | 36.52% | -12.17% | 48.70% | -5,600 |
| 70680 | 69.59% | 40.46% | 29.12% | +15,700 |
| 36670 | 6.25% | -21.88% | 28.12% | -17,500 |
| 27620 | 22.12% | -3.37% | 25.48% | -1,400 |
| 51890 | 10.46% | -14.84% | 25.30% | -44,000 |
| 43880 | 29.32% | 19.49% | 23.53% | +22,200 |
| 40520 | 46.33% | 27.52% | 23.11% | +28,100 |

Giveback is not universally destructive; several campaigns still exit profitably. But giveback is material enough that the highest-value next audit should focus on profit retention / campaign continuation after initial success, not on adding another entry filter first.

## Capital Allocation / Plumbing

CAPITAL_ALLOCATION_PLUMBING_STATUS = NO_CONFIRMED_SYSTEMIC_BLOCKER_IN_COMPLETED_ARTIFACTS

Observed:

- Submit non-PASS artifacts across completed dates: `0`.
- Filled BUY_NEW count: `360`.
- Filled symbol-level BUY_ADD count: `18`.
- Filled SELL_REDUCE count: `41`.
- Filled SELL_EXIT count: `200`.
- G119 intended to repair stale deployment-set Cash winner zeroing in PS. The completed run shows broad BUY materialization and no Submit-level blocking pattern.

Important limitation:

This G120 characterization did not attempt to prove every individual PC final row reached Runtime. The observed evidence does not show a run-stopping or performance-dominant PC->PS->Runtime->Submit blocker, but a narrower lineage audit would be required to classify every raw row-level mismatch as explained or unexplained.

PC_TO_PS_UNEXPLAINED_GAP_COUNT = 0_CONFIRMED

PS_TO_RUNTIME_UNEXPLAINED_GAP_COUNT = 0_CONFIRMED_ROW_LEVEL_FULL_AUDIT_NOT_PERFORMED

RUNTIME_TO_PENDING_UNEXPLAINED_GAP_COUNT = 0_CONFIRMED

PENDING_TO_SUBMIT_UNEXPLAINED_GAP_COUNT = 0_CONFIRMED

SUBMIT_NONPASS_COUNT = 0

## Baseline Divergence

BASELINE_RUN_ARTIFACT_FOUND = NO

The requested baseline run:

```text
runtime-test-historical-extended-smoke-20260824T055234719725Z
```

was not present under `reports/`. Therefore G120 cannot produce a full artifact-to-artifact baseline divergence table. The primary post-G119 run itself is materially profitable through the cutoff, with +43.28% return and peak +47.91%, but the exact contribution of G115/G117/G119 versus the missing baseline cannot be quantified from local artifacts in this task.

## Strengths

1. Strong early profit engine: +47.91% peak by 2023-04-10.
2. Broad BUY materialization preserved after G119: 360 BUY_NEW fills and no Submit non-PASS pattern.
3. Market Quality is not acting as a hard BUY gate; BUYs occur in all observed regimes.
4. Profit Factor estimate remains positive at about 1.79 despite a material April drawdown.
5. Recovery after April drawdown was meaningful: 2023-04-21 to 2023-06-19 recovered about +12.11%.

## Weaknesses

1. Campaign-level ADD/winner scaling is weak: `0` multi-BUY campaigns in canonical campaign lifecycle despite 18 symbol-level repeated BUY fills.
2. Profit concentration is high: top 10 positive campaigns explain about 79% of estimated net campaign contribution.
3. April drawdown was large and fast: -12.53% MDD from the April peak.
4. Post-recovery period shows high exposure without renewed equity highs by the cutoff.
5. Profit retention is only partial; several campaigns show material giveback from observed MFE.

## Required Final Fields

POST_HOC_OUTCOME_USED_AS_PRODUCTION_DECISION_AUTHORITY = NO

CODE_CHANGED = NO

CONFIG_CHANGED = NO

RUN_MUTATED_BY_CODEX = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

PRIMARY_RUN_STATUS_AT_AUDIT = RUNNING

COMPLETED_DATES_AUDITED = 215

FINAL_COMPLETED_DATE = 2023-08-16

FINAL_EQUITY = 1,432,820

TOTAL_RETURN = +43.28%

PEAK_EQUITY = 1,479,100

PEAK_RETURN = +47.91%

PEAK_DATE = 2023-04-10

MAX_DRAWDOWN = -12.53%

CURRENT_DRAWDOWN = -3.13%

AVERAGE_EXPOSURE = 71.84%

MEDIAN_EXPOSURE = 75.97%

PROFIT_FACTOR_ESTIMATE = 1.79

WIN_RATE_ESTIMATE = 48.99%

G115_SUPPRESSES_ALL_ADD = NO

STRONG_WINNER_MULTI_INCREMENT_SURVIVES_ACTUAL = NO

WINNER_SCALING_BEHAVIOR_PRESENT = WEAK

APRIL_DRAWDOWN_PRIMARY_SOURCE = NEWLY_ENTERED_SHORT_LOSERS_PLUS_INCUMBENT_GIVEBACK

BASELINE_ARTIFACT_AVAILABLE = NO

BASELINE_DIVERGENCE_QUANTIFIED = NO

## Highest-Value Next Investigation

HIGHEST_VALUE_NEXT_INVESTIGATION = CAMPAIGN_LEVEL_ADD_IDENTITY_AND_WINNER_SCALING_BINDING

The most material next boundary is not another Market Quality redesign or a BUY filter. The completed artifacts show that the system can buy, recover, and find winners, but canonical campaign-level ADD scaling is effectively absent. The next audit should determine why symbol-level repeated BUY activity does not become active-campaign ADD/winner amplification, and whether that is an identity/provenance issue, PM ADD intent sparsity, PC marginal competition selectivity, or PS/Runtime ADD materialization semantics.

