# Phase32-U — Acceleration Activation + Winner Retention Joint Root-Cause Audit

## Scope

Target run:

`runtime-test-historical-extended-smoke-20260830T045550298045Z`

This was a READ-ONLY root-cause characterization audit. No source, config,
Strategy parameter, threshold, weight, Risk Pacing, Cash, PM, PS, Runtime, or
G129 behavior was changed. No fresh-run, resume, replay, or long Historical was
executed by Codex.

Audit snapshot:

- run status: `RUNNING`
- completed business days audited: 72
- audited range: 2022-10-03 through 2023-01-18
- next run job at audit time: `2023-01-19:market_refresh`
- current source commit recorded by run: `4ff63ba05a0012c60fce50741a946eed672f8990`
- source dirty recorded by run: `True`

Future price paths are used only in the `CHARACTERIZATION_ONLY` counterfactual
section. Decision-time SELL quality and production correctness classification
do not use future outcomes.

## Regime Coverage

| Regime | Days |
| --- | ---: |
| BEAR | 25 |
| BULL | 19 |
| RANGE | 16 |
| RECOVERY | 10 |
| CORRECTION | 2 |

Risk Pacing:

| Intent | Days |
| --- | ---: |
| `CAUTIOUS_DEPLOYMENT` | 54 |
| `GRADUAL_REDEPLOYMENT` | 10 |
| `NORMAL_DEPLOYMENT` | 8 |

## ADD Tier Distribution

| Tier | Count |
| --- | ---: |
| `NO_ACCELERATION` | 33 |
| `NORMAL_ADD` | 13 |
| `STRONG_ADD` | 0 |
| `EXCEPTIONAL_ADD` | 0 |

Regime-tier matrix:

| Regime | NO_ACCELERATION | NORMAL_ADD | STRONG_ADD | EXCEPTIONAL_ADD |
| --- | ---: | ---: | ---: | ---: |
| BEAR | 6 | 5 | 0 | 0 |
| BULL | 12 | 4 | 0 | 0 |
| RANGE | 9 | 2 | 0 | 0 |
| RECOVERY | 4 | 2 | 0 | 0 |
| CORRECTION | 2 | 0 | 0 | 0 |

## ADD Funnel

| Stage | Count |
| --- | ---: |
| PM ADD | 46 |
| PC positive ADD increment | 13 |
| PC uplift over pre-acceleration baseline | 0 |
| PS positive ADD quantity | 8 |
| PS multi-lot ADD, `>=200` shares | 0 |
| Runtime `BUY_ADD` | 8 |
| `BUY_ADD` fills | 7 |

Quantity distributions:

- PS ADD quantity: 8 events, all 100 shares.
- Runtime ADD quantity: all positive events 100 shares.
- BUY_ADD fill quantity: 7 events, all 100 shares.

## BULL Acceleration Audit

BULL-period PM ADD rows: 16.

| Final Tier | Count |
| --- | ---: |
| `NO_ACCELERATION` | 12 |
| `NORMAL_ADD` | 4 |
| `STRONG_ADD` | 0 |
| `EXCEPTIONAL_ADD` | 0 |

First blocking reason in BULL:

| Blocking Reason | Count |
| --- | ---: |
| `BUY_QUALITY_REDUCTION` | 15 |
| `INCREMENTAL_VALUE_NOT_POSITIVE` | 1 |

In BULL, no PM ADD row reached complete security-level strong evidence before
Risk Pacing. The main BULL brake is therefore not PS, Runtime, or hidden
one-lot materialization. It is earlier: Buy Quality reduced allocation and one
incremental-value failure prevent strong/exceptional ADD eligibility.

## Risk Pacing Interaction

Across all regimes, three rows reached security-level strong evidence before
Risk Pacing:

| Date | Symbol | Regime | Risk Pacing | Final Tier | Pre Increment | Tier Increment | PS Qty |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 2022-10-06 | 94340 | RANGE | `CAUTIOUS_DEPLOYMENT` | `NORMAL_ADD` | 0.035714 | 0.035714 | 100 |
| 2022-10-11 | 94340 | BEAR | `CAUTIOUS_DEPLOYMENT` | `NORMAL_ADD` | 0.029600 | 0.029600 | 100 |
| 2022-10-12 | 94340 | BEAR | `CAUTIOUS_DEPLOYMENT` | `NORMAL_ADD` | 0.021765 | 0.021765 | 100 |

All three were down-tiered by Risk Pacing. This is not a correctness defect
under the current SoT, because Phase31-G140 keeps Risk Pacing architecturally
necessary. It is a performance architecture finding: Risk Pacing consumption in
ADD acceleration currently prevents uplift when market-level posture is
cautious, even when security-level evidence is strong.

Classification:

- ADD tier guardrail: `ARCHITECTURE_LIMITATION`
- Risk Pacing consumption: `PERFORMANCE_INITIATIVE_CANDIDATE`
- correctness defect: NO

## Representative Campaign 76470

76470 had two separate campaigns in the audited window.

First campaign:

| Date | Event |
| --- | --- |
| 2022-10-12 | BUY_NEW fill, 800 shares, BEAR, `CAUTIOUS_DEPLOYMENT` |
| 2022-10-14 | SELL_EXIT fill, 800 shares, reason `weak_hold_score` |

Second campaign:

| Date | Event |
| --- | --- |
| 2022-11-30 | BUY_NEW fill, 300 shares, BULL, `CAUTIOUS_DEPLOYMENT` |
| 2022-12-29 | PM ADD, `NO_ACCELERATION`, PS 0 |
| 2023-01-04 | PM ADD, `NORMAL_ADD`, BUY_ADD fill 100 |
| 2023-01-05 | PM ADD, `NORMAL_ADD`, BUY_ADD fill 100 |
| 2023-01-06 | PM ADD, `NO_ACCELERATION`, PS 0 |
| 2023-01-10 | PM ADD, `NO_ACCELERATION`, PS 0 |
| 2023-01-11 | PM ADD, `NO_ACCELERATION`, PS 0 |
| 2023-01-12 | PM ADD, `NO_ACCELERATION`, PS 0 |

Positive 76470 ADD details:

| Date | Regime | Risk | Tier | Pre Increment | Tier Increment | Lot-Aware Increment | PS Qty |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 2023-01-04 | BEAR | `CAUTIOUS_DEPLOYMENT` | `NORMAL_ADD` | 0.021143 | 0.021143 | 0.002465 | 100 |
| 2023-01-05 | BEAR | `CAUTIOUS_DEPLOYMENT` | `NORMAL_ADD` | 0.020556 | 0.020556 | 0.002555 | 100 |

Why 76470 mostly grew by +100 shares:

- 76470 never reached `STRONG_ADD` or `EXCEPTIONAL_ADD`.
- Positive ADD rows were `NORMAL_ADD` only.
- Risk Pacing was `CAUTIOUS_DEPLOYMENT`.
- Buy Quality was reduced in the relevant later campaign.
- Lot-aware accepted increment resolved to a single 100-share executable ADD.
- Runtime consumed PS quantity exactly; no Runtime loss or redecision was found.

## Winner Capitalization Speed

Campaign-level fill characterization:

| Metric | Value |
| --- | ---: |
| Campaigns with initial BUY_NEW/REENTRY fill | 117 |
| Campaigns with BUY_ADD fill | 3 |
| Campaigns that doubled initial quantity | 2 |
| Median days to first BUY_ADD among campaigns with ADD | 16 BD |
| Median BUY_ADD shares per event | 100 |
| Median SELL shares per event | 100 |

BUY_ADD distribution:

| Shares | Count |
| --- | ---: |
| 100 | 7 |

SELL distribution:

| Shares | Count |
| --- | ---: |
| 100 | 92 |
| 200 | 11 |
| 300 | 6 |
| 400 | 1 |
| 500 | 1 |
| 600 | 1 |
| 700 | 1 |
| 800 | 1 |
| 3700 | 1 |
| 6500 | 1 |

Representative campaign speed:

| Campaign | Symbol | Initial | ADDs | Max Qty | Sells | Max Weight |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `pc-bcb290f73c9b57a2-94340-0001` | 94340 | 200 | 3 x 100 | 500 | 500 exit | 0.070815 |
| `pc-8d95d2887b97aae0-94320-0001` | 94320 | 200 | 2 x 100 | 400 | 100, 300 | 0.060504 |
| `pc-527c0458bbead901-76470-0001` | 76470 | 300 | 2 x 100 | 500 | 0 | 0.012808 |

Winner capitalization is still slow. Actual ADD fills are sparse, single-lot,
and often delayed; only 3 of 117 filled campaigns received any BUY_ADD.

## REDUCE / EXIT Distribution

PM sell-side decisions:

| Action | Count |
| --- | ---: |
| REDUCE | 88 |
| EXIT | 107 |

Decision-time SELL quality classification:

| Class | Count |
| --- | ---: |
| `DEFENSIVE_BUT_TREND_INTACT` | 88 |
| `POSSIBLE_PREMATURE_DEACCELERATION` | 107 |

Reason distribution highlights:

- `risk_increased_but_trend_not_broken` is the dominant REDUCE reason.
- `pm_discrete_control_persistent_deterioration_exit` frequently escalates
  repeated defensive/reduce evidence into EXIT.
- `trend_and_opportunity_broken`, `weak_hold_score`, `hard_stop_current_return`,
  and `profit_retention_break` also appear on EXIT rows.

These classifications are decision-time only. They indicate that many sell-side
decisions occur while canonical evidence still reports continuation quality
`PASS` and campaign identity complete. That is not automatically wrong, but it
is the strongest observed source of fast deacceleration pressure.

## SELL By Regime

| Regime | REDUCE | EXIT |
| --- | ---: | ---: |
| BULL | 23 | 19 |
| BEAR | 35 | 47 |
| RANGE | 21 | 28 |
| RECOVERY | 8 | 11 |
| CORRECTION | 1 | 2 |

BULL had 42 PM sell-side decisions versus 16 PM ADD rows. This supports a
BULL-period retention concern: even during favorable market regimes, the system
removes or marks capital for removal more often than it accelerates winners.

## Counterfactual HOLD Characterization

This section uses future price path only as `CHARACTERIZATION_ONLY`.

Post REDUCE/EXIT price path labels:

| Characterization | Count |
| --- | ---: |
| `continued_strength` | 39 |
| `rebound_or_mild_strength` | 21 |
| `flat_mixed` | 49 |
| `immediate_or_sustained_adverse` | 47 |
| `insufficient_future_artifact` | 39 |

Potential HOLD retention misses:

- count: 60
- definition: decision-time classification was
  `DEFENSIVE_BUT_TREND_INTACT` or `POSSIBLE_PREMATURE_DEACCELERATION`, and
  characterization layer later showed `continued_strength` or
  `rebound_or_mild_strength`.

Representative examples:

| Date | Symbol | Action | Decision-Time Class | Later Characterization |
| --- | --- | --- | --- | --- |
| 2022-10-04 | 92420 | REDUCE | `DEFENSIVE_BUT_TREND_INTACT` | `continued_strength` |
| 2022-10-05 | 41650 | EXIT | `POSSIBLE_PREMATURE_DEACCELERATION` | `continued_strength` |
| 2022-10-20 | 66190 | REDUCE | `DEFENSIVE_BUT_TREND_INTACT` | `continued_strength` |
| 2022-10-21 | 66190 | EXIT | `POSSIBLE_PREMATURE_DEACCELERATION` | `continued_strength` |
| 2022-11-07 | 92270 | EXIT | `POSSIBLE_PREMATURE_DEACCELERATION` | `continued_strength` |
| 2022-11-22 | 15180 | EXIT | `POSSIBLE_PREMATURE_DEACCELERATION` | `rebound_or_mild_strength` |

This does not prove those sells were incorrect. It does show that the current
system often cuts exposure in states where decision-time continuation evidence
is not fully broken, and a meaningful subset later continued or rebounded.

## ADD vs Deacceleration Speed

Observed asymmetry:

- BUY_ADD fills: 7.
- SELL fills: substantially more frequent, with many full exits.
- ADD quantity: always 100 shares.
- SELL quantity: commonly 100 shares, but also 200, 300, 400, 500, 600, 700,
  800, 3700, and 6500 shares.
- Only 3 filled campaigns received any ADD.
- 107 PM EXIT decisions occurred.

Conclusion:

`SLOW_ACCELERATION_FAST_DEACCELERATION_ASYMMETRY` is present as a performance
architecture characterization.

## BULL Winner Retention

BULL period:

- days: 19
- PM ADD rows: 16
- `NORMAL_ADD`: 4
- `NO_ACCELERATION`: 12
- `STRONG_ADD` / `EXCEPTIONAL_ADD`: 0
- REDUCE decisions: 23
- EXIT decisions: 19

BULL retention diagnosis:

- ADD is present but does not accelerate beyond normal.
- BULL ADD blockers are mostly Buy Quality reduction.
- Sell-side pressure remains active in BULL.
- Net effect is limited winner thickening and continued exposure turnover.

Classification:

`BULL_CAPITALIZATION_LIMIT` is structurally supported by current actual
artifacts.

## Root-Cause Classification

| Finding | Classification |
| --- | --- |
| ADD tier guardrail prevents uplift when evidence incomplete | `INTENDED_DEFENSIVE_BEHAVIOR` |
| Risk Pacing down-tiers all complete security-level strong candidates | `PERFORMANCE_INITIATIVE_CANDIDATE` |
| Buy Quality reduction blocks most BULL strong ADD eligibility | `ARCHITECTURE_LIMITATION` |
| one-lot observed BUY_ADD materialization | `ARCHITECTURE_LIMITATION` in actual path, not a proven structural PS cap |
| REDUCE aggressiveness while trend intact | `PERFORMANCE_INITIATIVE_CANDIDATE` |
| EXIT aggressiveness after defensive/persistent deterioration evidence | `PERFORMANCE_INITIATIVE_CANDIDATE` |
| composed ADD caution plus SELL speed | `PERFORMANCE_INITIATIVE_CANDIDATE` |

Correctness defect found: NO.

Repair required: NO.

Performance initiative required before expecting long-horizon equity growth
change: YES.

## Primary Plateau Hypothesis

Primary:

`NO_SINGLE_CAUSE`

The plateau mechanism is composed conservatism:

- `ADD_ACCELERATION_NOT_ACTIVATING`
- `RISK_PACING_OVER_DOWN_TIERING`
- `PC_WINNER_CAPITAL_AUTHORIZATION_LIMIT`
- `EARLY_REDUCE`
- `EARLY_EXIT`
- `FAST_DEACCELERATION`

Secondary:

- `PS_LOT_LIMIT` is observed in actual path because all BUY_ADD fills are
  single-lot, but no hidden structural one-lot cap was reproduced in this audit.
- `CAPITAL_FRAGMENTATION` is plausible because 117 filled campaigns exist while
  only 3 received ADD, but this audit did not isolate it as the primary cause.

## Recommended Next Action

Prioritize a user-approved performance design task for:

`Winner retention / deacceleration pacing before further ADD magnitude tuning`

Rationale:

- Phase32-S acceleration is active but rarely reaches strong eligibility.
- BULL ADD is mainly blocked by Buy Quality reduction.
- Security-level strong ADD candidates are down-tiered by Risk Pacing, but only
  3 such rows exist.
- SELL/REDUCE pressure is large across regimes, including BULL.
- 60 characterization-only potential HOLD retention misses were observed.

A good next design should separate:

- correctness-preserving PM sell authority,
- retention throttle / persistence requirements,
- reduce-to-exit escalation pacing,
- and later ADD acceleration calibration.

## NO CODE CHANGE

Confirmed. Phase32-U did not modify source or config.

## Future Information Separation

Decision-time classifications use only actual run artifacts and decision-time
evidence. Future price movement is used only in the explicitly labeled
`CHARACTERIZATION_ONLY` counterfactual HOLD section and is not used to infer
Production thresholds, weights, tiers, or parameter changes.

## Final Judgment

1. `HAS_PHASE32_S_STRONG_OR_EXCEPTIONAL_ACCELERATION_ACTIVATED`: NO.
2. `IF_NOT_OR_RARE, WHAT_IS_THE_PRIMARY_BLOCKER`: In BULL, Buy Quality reduction
   is the primary blocker; across all regimes, only 3 security-level strong
   candidates appeared and all were Risk-Pacing-down-tiered.
3. `IS_RISK_PACING_OVER_DOWN_TIERING_VALID_STRONG_ADD_CANDIDATES`: YES as a
   performance architecture characterization, not a correctness defect.
4. `IS_WINNER_CAPITALIZATION_STILL_TOO_SLOW`: YES.
5. `ARE_REDUCE_OR_EXIT_DECISIONS_SYSTEMATICALLY_TOO_EARLY`: UNCONFIRMED as a
   correctness claim, but YES as a performance/retention concern.
6. `HOW_MANY_POTENTIAL_HOLD_RETENTION_MISSES_EXIST`: 60 characterization-only
   candidates.
7. `IS_SLOW_ACCELERATION_FAST_DEACCELERATION_ASYMMETRY_PRESENT`: YES.
8. `WHAT_IS_THE_PRIMARY_LONG_HORIZON_PLATEAU_MECHANISM`: composed conservatism,
   with ADD acceleration not activating plus fast defensive deacceleration.
9. `IS_ANY_CORRECTNESS_REPAIR_REQUIRED`: NO.
10. `WHICH_NEXT_PERFORMANCE_INITIATIVE_SHOULD_BE_PRIORITIZED`: Winner retention
    and deacceleration pacing, then revisit ADD/Risk-Pacing acceleration
    calibration with user approval.
