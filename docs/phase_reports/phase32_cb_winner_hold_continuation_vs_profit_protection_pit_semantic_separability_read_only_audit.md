# Phase32-CB — Winner HOLD Continuation vs Profit-Protection Escalation PIT Semantic Separability READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- Audit mode: READ-ONLY
- Latest completed actual Runtime day used: `2023-05-08`
- Population source: PM `HOLD` rows from target-run `strategy/position_management.json`

No source, config, PM/HOLD/SELL semantics, threshold, weight, model, feature, BO/BQ behavior, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run action was executed or changed.

Phase32-CA, Phase32-BY, and Phase32-BZ conclusions are preserved:

- Upside capture is strong.
- `profit cushion alone -> HOLD` regression was not found.
- CA's main mechanism is `HOLD_CONFIRMATION_LAG_AMPLIFIED_BY_CAPITAL_SCALE`.
- BZ's BQ refinement is separate and remains deferred.
- CB does not redesign BQ or map protection candidates to REDUCE/FULL EXIT/caps.

The run advanced while the audit was being performed. The extraction used for this report is fixed at `2023-05-08` and is not chased further.

## Evidence Sources

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<date>/strategy/position_management.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<date>/current_valuation_refresh/current_valuation_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<date>/execution/fills.json`
- `.runtime/runtime_state/position_management/<date>/position_management_decisions.json`
- `docs/phase_reports/phase32_ca_early_vs_late_large_loss_scaling_hold_confirmation_lag_read_only_audit.md`
- `docs/phase_reports/phase32_by_post_bq_long_run_profit_retention_large_loss_mechanism_read_only_audit.md`
- `docs/phase_reports/phase32_bz_recurrent_bq_insufficient_hold_later_loss_pit_separability_read_only_audit.md`

PIT matrix construction used only same-day PM/strategy artifacts. Later valuation/fill evidence was added only after PIT grouping to label outcome.

## Winner HOLD Population

Winner HOLD event rule, fixed before outcome labeling:

- PM final action is `HOLD`
- and either current campaign return `>= +5%` or observed campaign MFE `>= +10%`

Counts:

| Scope | Count |
|---|---:|
| Winner HOLD events | 577 |
| Winner campaigns | 69 |

Event outcome labels use +10 completed business days where available:

- `MATERIAL_GIVEBACK_AFTER_HOLD`: worst +10BD value/fill decline `<= -20,000` or `<= -10%` of event-date position value.
- `GAIN_RETAINED_OR_EXTENDED`: best +10BD value/fill gain `>= +20,000` and no material giveback by the rule above.
- `NEUTRAL`: neither material giveback nor material gain extension.
- `INSUFFICIENT_OUTCOME`: insufficient +10BD evidence in the fixed snapshot.

Event labels:

| Label | Event count |
|---|---:|
| `MATERIAL_GIVEBACK_AFTER_HOLD` | 68 |
| `GAIN_RETAINED_OR_EXTENDED` | 31 |
| `NEUTRAL` | 473 |
| `INSUFFICIENT_OUTCOME` | 5 |

Campaign labels use worst-precedence across each campaign's Winner HOLD events:

| Label | Campaign count |
|---|---:|
| `MATERIAL_GIVEBACK_AFTER_HOLD` | 25 |
| `GAIN_RETAINED_OR_EXTENDED` | 7 |
| `NEUTRAL` | 37 |

This broad population intentionally includes small and moderate campaigns. It avoids selecting only eventual losers, but it also means not every material giveback row is a PM/HOLD redesign candidate; BZ and starter-loss mechanisms are separated below.

## 59350 Lifecycle

`59350` is reproduced.

| Date | PM action | Sell state | Current return | MFE | Giveback | PM reasons | Deterioration states | Outcome label |
|---|---|---|---:|---:|---:|---|---|---|
| 2023-03-24 | HOLD | `HEALTHY_OR_RECOVERING` | -5.1% | -5.1% | 0.0% | downside contained, positive expected edge, trend continuation | DECELERATING, ELEVATED_RISK | not Winner by rule |
| 2023-03-27 | HOLD | `EXIT_GRADE` | -4.0% | -4.0% | 0.0% | positive expected edge, profit retention break | DECELERATING, ELEVATED_RISK | not Winner by rule |
| 2023-03-28 | HOLD | `EXIT_GRADE` | +24.3% | +24.3% | 0.0% | positive expected edge, profit retention break | DECELERATING, ELEVATED_RISK | `MATERIAL_GIVEBACK_AFTER_HOLD` |
| 2023-03-29 | ADD | `HEALTHY_OR_RECOVERING` | +52.6% | +52.6% | 0.0% | strong trend, opportunity rank high | DECELERATING, ELEVATED_RISK | outside HOLD population |
| 2023-03-30 | HOLD | `EXIT_GRADE` | +23.7% | +52.6% | 28.9% | positive expected edge, profit retention break | DECELERATING | `GAIN_RETAINED_OR_EXTENDED` |
| 2023-03-31 | HOLD | `EXIT_GRADE` | +45.9% | +52.6% | 28.9% | positive expected edge, profit retention break | ELEVATED_RISK | `GAIN_RETAINED_OR_EXTENDED` |
| 2023-04-03 | HOLD | `EXIT_GRADE` | +78.8% | +78.8% | 28.9% | positive expected edge, profit retention break | DECELERATING, ELEVATED_RISK | `MATERIAL_GIVEBACK_AFTER_HOLD` |
| 2023-04-04 | HOLD | `HEALTHY_OR_RECOVERING` | +111.8% | +111.8% | 28.9% | positive expected edge, trend continuation | DECELERATING, ELEVATED_RISK | `MATERIAL_GIVEBACK_AFTER_HOLD` |
| 2023-04-05 | HOLD | `EXIT_GRADE` | +92.7% | +111.8% | 28.9% | positive expected edge, profit retention break | DECELERATING, ELEVATED_RISK | `MATERIAL_GIVEBACK_AFTER_HOLD` |
| 2023-04-06 | HOLD | `EXIT_GRADE` | +125.7% | +125.7% | 28.9% | positive expected edge, profit retention break | DECELERATING, ELEVATED_RISK | `MATERIAL_GIVEBACK_AFTER_HOLD` |
| 2023-04-07 | HOLD | `HEALTHY_OR_RECOVERING` | +158.7% | +158.7% | 28.9% | positive expected edge, trend continuation | DECELERATING, ELEVATED_RISK | `MATERIAL_GIVEBACK_AFTER_HOLD` |
| 2023-04-10 | HOLD | `HEALTHY_OR_RECOVERING` | +116.1% | +158.7% | 42.6% | downside contained, positive expected edge, trend continuation | DECELERATING, ELEVATED_RISK | `MATERIAL_GIVEBACK_AFTER_HOLD` |
| 2023-04-11 | HOLD | `HEALTHY_OR_RECOVERING` | +109.7% | +158.7% | 49.0% | downside contained, positive expected edge, trend continuation | DECELERATING, ELEVATED_RISK | `MATERIAL_GIVEBACK_AFTER_HOLD` |
| 2023-04-12 | HOLD | `HEALTHY_OR_RECOVERING` | +97.9% | +158.7% | 60.8% | downside contained, trend continuation | ELEVATED_RISK | `GAIN_RETAINED_OR_EXTENDED` |
| 2023-04-13 | HOLD | `HEALTHY_OR_RECOVERING` | +81.7% | +158.7% | 77.0% | downside contained, trend continuation | ELEVATED_RISK | `GAIN_RETAINED_OR_EXTENDED` |
| 2023-04-14 | HOLD | `HEALTHY_OR_RECOVERING` | +79.3% | +158.7% | 79.4% | downside contained, trend continuation | ELEVATED_RISK, WEAK | `GAIN_RETAINED_OR_EXTENDED` |
| 2023-04-17 | HOLD | `EXIT_GRADE` | +73.0% | +158.7% | 85.8% | positive expected edge, profit retention break | ELEVATED_RISK, WEAK | `MATERIAL_GIVEBACK_AFTER_HOLD` |
| 2023-04-18 | HOLD | `HEALTHY_OR_RECOVERING` | +105.9% | +158.7% | 85.8% | downside contained, positive expected edge, trend continuation | DECELERATING, ELEVATED_RISK, WEAK | `MATERIAL_GIVEBACK_AFTER_HOLD` |
| 2023-04-19 | HOLD | `HEALTHY_OR_RECOVERING` | +87.1% | +158.7% | 85.8% | downside contained, trend continuation | DECELERATING, ELEVATED_RISK, WEAK | `NEUTRAL` |
| 2023-04-20 | EXIT | `EXIT_GRADE` | +78.1% | +158.7% | 85.8% | profit retention break, sell-side evidence connected | ELEVATED_RISK, WEAK | actual exit |

Fills:

- BUY: `2023-03-23`, 100 shares at 2,122, notional 212,200.
- SELL: `2023-04-20`, 100 shares at 3,730, notional 373,000.

### 59350 Continuation Control Period

Selling too early would clearly have destroyed substantial legitimate upside:

- `2023-03-30` HOLD: +10BD best gain `+239,500` by `2023-04-06`.
- `2023-03-31` HOLD: +10BD best gain `+169,500` by `2023-04-06`.
- `2023-04-04` HOLD still had +1BD gain `+70,000` and +10BD best gain `+140,000`.

These are mandatory false-protection controls. `EXIT_GRADE` plus `profit_retention_break` is not sufficient by itself.

### 59350 Protection Transition Candidate

The strongest PIT-only protection candidate appears around `2023-04-05` to `2023-04-06`:

- Current return was very high: +92.7% to +125.7%.
- Position notional was very high: 479,000 to 549,000.
- `EXIT_GRADE` and `profit_retention_break` were present.
- Deterioration had multiple PIT dimensions: DECELERATING and ELEVATED_RISK.
- Positive expected edge still remained, so this is not terminal EXIT confirmation.

`2023-04-06` is the clearest semantic transition candidate because the same PIT conflict had become large-notional, high-MFE, high-profit-risk, and repeatedly unresolved. This conclusion does not use the next price as decision input; the later -182,000 +10BD label is used only to classify the consequence after the PIT state is identified.

## Additional Controls And Harmful Cases

Additional gain-retained Winner controls found:

| Symbol | Campaign | Representative date | Best +10BD gain | PIT notes |
|---:|---|---|---:|---|
| 44440 | `pc-67bdf759e2357cd6-44440-0001` | 2023-03-17 / 2023-03-20 | +58,000 | Even `EXIT_GRADE` plus `profit_retention_break` on 2023-03-20 did not imply immediate failure. |
| 78860 | `pc-4abc6670738d0096-78860-0001` | 2022-11-18 | +34,800 | Deterioration states existed, but HOLD continuation preserved later upside before BZ non-promotion loss. |
| 99840 | `pc-d6cacadc60246e75-99840-0001` | 2022-10-24 | +29,900 | Profitable winner with supportive HOLD evidence and later extension. |
| 69730 | `pc-b472b9124381fcf9-69730-0001` | 2022-11-02 | +23,200 | Trend continuation / structured HOLD remained useful. |
| 92270 | `pc-0bfe3b54b0849ee3-92270-0001` | 2022-10-20 | +21,700 | Small but valid continuation control. |
| 64240 | `pc-12946a66faafe88f-64240-0001` | 2023-03-17 | +20,700 | Valid profitable HOLD extension. |
| 51360 | `pc-e082e0671e5bd4a6-51360-0001` | 2023-04-14 | +20,800 | Later-window gain-retained control. |

Additional material giveback Winner HOLD campaigns found include:

- `67400`, `37770`, `52470`, `97310`, `87890`, `17570`, `43880`, `41660`, `76470`, `92520`, `13840`, and others.

Important separation:

- `97310`, `52470`, `41660`, and related lot-blocked REDUCE cases overlap with BZ and should not be used to redesign PM/HOLD directly.
- `59350` is the strongest pure PM/HOLD profit-retention case in the current target-run actual evidence through `2023-05-08`.

## Separability

Judgment:

```text
PARTIALLY_SEPARABLE
```

Why not stronger:

- `continuation_quality_status = PASS`, `downside_risk_status = PASS`, `recovery_state = RECOVERY_PRESENT`, `exit_confirmation_state = DEFENSIVE_ONLY`, `hard_deterioration_present = false`, and `pm_severity = PM_SEVERITY_NORMAL` appear across harmful, successful, and neutral Winner HOLD rows.
- `structured_hold_worthiness_pass` is almost universal: 65 of 68 harmful rows, 31 of 31 gain-retained rows, and 472 of 473 neutral rows.
- `EXIT_GRADE` and `profit_retention_break` capture important harmful cases, but also appear in gain-retained controls: `59350` on 2023-03-30/31 and `44440` on 2023-03-20.

Why it is at least partial:

- Material harmful rows have higher median current return than gain-retained/neutral rows: harmful event median +20.1%, gain-retained +10.0%, neutral +10.2%.
- Harmful rows have higher median MFE: harmful +23.7%, gain-retained +12.4%, neutral +13.1%.
- The largest harmful case has exceptional notional and profit-risk concentration: `59350` at 479,000 to 549,000 notional with repeated `EXIT_GRADE` / `profit_retention_break`.
- The most dangerous state is not a single warning; it is repeated conflict:

```text
large winner + large notional + high MFE/giveback + EXIT_GRADE/profit_retention_break + DECELERATING/ELEVATED_RISK + positive expected edge still preserving HOLD
```

## Continuation Evidence

Most informative continuation dimensions:

- `structured_hold_worthiness_pass`
- `trend_continuation`
- `positive_expected_edge`
- `downside_risk_contained`
- recovery state `RECOVERY_PRESENT`
- `HEALTHY_OR_RECOVERING`

However, these dimensions are not clean protection blockers. They are present in both successful continuation and harmful giveback cases. Their best use is as false-protection controls: if a future SHADOW state is proposed, it must prove that it does not simply punish every winner with trend continuation plus profit-retention warning.

## Protection Evidence

Most informative protection dimensions:

- repeated `EXIT_GRADE`
- repeated `profit_retention_break`
- high observed campaign MFE
- high observed giveback
- large position notional / capital at risk
- multi-dimensional deterioration states, especially DECELERATING + ELEVATED_RISK, later ELEVATED_RISK + WEAK
- absence of terminal hard deterioration, which explains why current PM keeps HOLD but also identifies the conflict state needing explicit shadow materialization

`position notional` is not direction authority. It is consequence/severity context. It can prioritize review or shadow escalation severity, but it should not decide SELL direction by itself.

## Conflict-State Analysis

Conflict state:

```text
positive continuation evidence + profit-retention/deterioration evidence
```

Classification:

- Continuation clearly dominant: early `99840`, `78860`, `69730`, and `59350` on 2023-03-30/31.
- Protection clearly dominant candidate: `59350` around 2023-04-05/06 and again 2023-04-17/18.
- Genuinely ambiguous: `59350` on 2023-04-03/04, `44440` 2023-03-20, and many small/mid notional Winner HOLD rows with DECELERATING/ELEVATED_RISK but no large consequence.

The conflict state is separable enough for a SHADOW semantic state, but not enough for direct Production action mapping.

## HOLD Confirmation Lag

For `59350`:

- first PIT warning: `2023-03-27` (`EXIT_GRADE`, `profit_retention_break`, but not yet profitable by current-return rule)
- first Winner HOLD warning: `2023-03-28`
- protection transition candidate: `2023-04-05` to `2023-04-06`
- first PM REDUCE: not observed before exit
- first PM EXIT: `2023-04-20`
- actual exit: `2023-04-20`
- warning -> actual exit lag: about 16 completed business days from `2023-03-28`
- transition candidate -> actual exit lag: about 10 completed business days from `2023-04-06`

Successful controls often recover or extend within +10BD, and many do not show a long unresolved conflict at comparable notional. The harmful `59350` case shows materially longer persistence of conflicting HOLD states than the cleanest gain-retained controls.

## False-Protection Risk

False-protection risk:

```text
HIGH
```

Examples:

- `59350` on `2023-03-30` and `2023-03-31` had `EXIT_GRADE` / `profit_retention_break`, yet continued HOLD preserved very large upside by `2023-04-06`.
- `44440` on `2023-03-20` had `EXIT_GRADE` / `profit_retention_break` and still produced gain-retained behavior.
- `78860`, `99840`, `69730`, `92270`, `64240`, and `51360` show valid Winner continuation controls.

A candidate semantic is unacceptable if it mainly protects historical profit by destroying these continuation states.

## Production / Shadow Implications

Production change justified:

```text
NO
```

New threshold justified:

```text
NO_FOR_PRODUCTION
```

New model required:

```text
NO_CONCRETE_EVIDENCE
```

New feature / semantic state justified:

```text
YES_FOR_SHADOW
```

The next task should design a SHADOW-only `PROFIT_PROTECTION_ESCALATION_CANDIDATE` state. It should not decide immediate REDUCE or FULL EXIT. It should materialize the conflict state and test false-protection controls before any action mapping.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-05-08`
2. `WINNER_HOLD_EVENT_COUNT = 577`
3. `WINNER_CAMPAIGN_COUNT = 69`
4. `GAIN_RETAINED_OR_EXTENDED_COUNT = 31_EVENTS / 7_CAMPAIGNS`
5. `MATERIAL_GIVEBACK_AFTER_HOLD_COUNT = 68_EVENTS / 25_CAMPAIGNS`
6. `59350_REPRODUCED = YES`
7. `59350_VALID_CONTINUATION_CONTROL_PERIOD_FOUND = YES; 2023-03-30_TO_2023-04-04_ESPECIALLY`
8. `59350_PROTECTION_TRANSITION_CANDIDATE_FOUND = YES; STRONGEST_ON_2023-04-05_TO_2023-04-06`
9. `ADDITIONAL_GAIN_RETAINED_WINNER_CONTROLS_FOUND = YES; 44440_78860_99840_69730_92270_64240_51360`
10. `ADDITIONAL_HARMFUL_HOLD_LAG_CAMPAIGNS_FOUND = YES; BUT MANY_OVERLAP_WITH_BZ_OR_SMALLER_STARTER/WINNER_CASES; PURE_PM_HOLD_MAIN_CASE_IS_59350`
11. `WINNER_CONTINUATION_VS_PROTECTION_PIT_SEPARABILITY = PARTIALLY_SEPARABLE`
12. `MOST_INFORMATIVE_CONTINUATION_DIMENSIONS = STRUCTURED_HOLD_WORTHINESS_PASS, TREND_CONTINUATION, POSITIVE_EXPECTED_EDGE, DOWNSIDE_RISK_CONTAINED, RECOVERY_PRESENT, HEALTHY_OR_RECOVERING`
13. `MOST_INFORMATIVE_PROTECTION_DIMENSIONS = REPEATED_EXIT_GRADE, PROFIT_RETENTION_BREAK, HIGH_MFE, HIGH_GIVEBACK, LARGE_NOTIONAL, DECELERATING/ELEVATED_RISK/WEAK_DETERIORATION, UNRESOLVED_CONFLICT_DURATION`
14. `CONFLICT_STATE_SEPARABLE = PARTIAL; GOOD_ENOUGH_FOR_SHADOW_STATE_NOT_FOR_PRODUCTION_ACTION`
15. `HARMFUL_HOLD_LAG_LONGER_THAN_SUCCESSFUL_CONTROLS = YES_FOR_59350`
16. `POSITION_NOTIONAL_AS_DIRECTION_AUTHORITY_JUSTIFIED = NO`
17. `POSITION_NOTIONAL_AS_SEVERITY_CONTEXT_JUSTIFIED = YES`
18. `PROFIT_CUSHION_ALONE_HOLD_REGRESSION_FOUND = NO`
19. `FALSE_PROTECTION_RISK = HIGH`
20. `NEW_FEATURE_REQUIRED = YES_FOR_SHADOW_SEMANTIC_STATE_OR_COMPOSITE_CONFLICT_FEATURE`
21. `NEW_MODEL_REQUIRED = NO_CONCRETE_EVIDENCE`
22. `NEW_THRESHOLD_JUSTIFIED = NO_FOR_PRODUCTION; ONLY_SHADOW_EXPLORATION_IF_USED`
23. `PROFIT_PROTECTION_SEMANTIC_STATE_JUSTIFIED = YES_SHADOW_ONLY`
24. `PRODUCTION_CHANGE_JUSTIFIED = NO`
25. `SHADOW_DESIGN_JUSTIFIED = YES`
26. `NEXT_RECOMMENDED_STEP = Design a SHADOW-only PROFIT_PROTECTION_ESCALATION_CANDIDATE state for Winner HOLD conflict, with mandatory gain-retained controls and no BQ redesign.`
27. `FINAL_JUDGMENT = PHASE32_CB_WINNER_HOLD_CONTINUATION_VS_PROFIT_PROTECTION_PARTIALLY_PIT_SEPARABLE_SHADOW_PROFIT_PROTECTION_STATE_JUSTIFIED_PRODUCTION_CHANGE_NOT_JUSTIFIED`

