# Phase30-AD2 - Post-AC 20BD Behavior / Winner Amplification Validation

Task ID: `Phase30-AD2`

Target run:

```text
runtime-test-historical-extended-smoke-20260816T045533779694Z
```

Boundary:

```text
READ_ONLY_AUDIT
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30-AD2
NO_TARGET_RUN_MUTATION
NO_REPLAY
NO_RESUME
NO_HISTORICAL_OUTCOME_FIT
```

## Primary Judgment

```text
PHASE30_AD2_BEHAVIOR_DIRECTION = MIXED
100BD_GATE = 100BD_ENTRY_BLOCKED
```

AC/AD1 fixed the critical HALT-class campaign identity gap enough for the 20BD
run to complete, and the post-AC run is materially better on return, drawdown,
and loss containment. However, the evidence is not yet clean enough for 100BD:
Portfolio Construction still shows blank `current_position_campaign_id` for
held positions across 19 days, and the main 2022-09-07 recovery is driven by
new 47600 same-day PnL rather than mature winner amplification.

## AC / AD1 Continuity

Run-state continuity:

```text
run_state.status = COMPLETED
completed_days = 20
final_runtime_judgment = PASS
accounting_state_judgment = PASS
trading_state_judgment = PASS
```

Close remains review-required:

```text
final_summary.final_judgment = REVIEW_REQUIRED
strategy_shadow_judgment = REVIEW_REQUIRED
strategy_review_required_dates = 9
```

AD1 bootstrap recurrence:

```text
PHASE30_AD1_BOOTSTRAP_DEFECT_RECURRENCE = NO
```

No held position was found with Strategy Intelligence lifecycle
`OPEN_HELD_POSITION` and missing campaign identity. The original AD0 failure
mode, where next-morning held positions had missing campaign identity and
halted the run, did not recur.

Remaining continuity gap:

```text
PORTFOLIO_CONSTRUCTION_CURRENT_CAMPAIGN_ID_PROPAGATION_GAP = YES
```

Portfolio Construction still has blank `current_position_campaign_id` for
current positions on 19 of 20 days. This did not halt the run, but it weakens
the proof that PC is fully using campaign identity for ADD / capital
concentration.

## Before / After Comparison

| Metric | AC-before | AC/AD1-after |
| --- | ---: | ---: |
| Final equity | 1,000,490 | 1,015,020 |
| Return | +0.05% | +1.50% |
| Max drawdown | -2.77% | -1.51% |
| Final cash | 434,990 | 711,100 |
| Final exposure | 56.52% | 29.94% |
| Average cash | 679,000 | 835,534 |
| Average exposure | 31.33% | 15.69% |
| Average position count | 6.05 | 4.45 |
| BUY fills | 36 | 24 |
| SELL fills | 35 | 31 |
| PM ADD actions | 11 | 14 |
| PM HOLD actions | 57 | 31 |
| PM REDUCE actions | 22 | 20 |
| PM EXIT actions | 23 | 19 |
| Closed campaigns | 23 | 19 |
| Win rate | 26.09% | 36.84% |
| Avg winner | +1,580 | +900 |
| Avg loser | -2,676 | -2,142 |
| Payoff ratio | 0.59 | 0.42 |
| Profit factor | 0.25 | 0.27 |

Interpretation:

- Loss containment improved: lower max DD, fewer closed losses, smaller average
  loser.
- Capital utilization became much more conservative.
- Payoff asymmetry did not improve; average winner fell and payoff ratio
  deteriorated.

## 94320

AC-before quantity path:

```text
200 -> 400 -> 700 -> 900 -> 1100 -> 1200
```

AC/AD1-after quantity path:

```text
200 -> 200 -> ... -> 200
```

AD1-after evidence:

| Date | Qty | PM action | Entry state / action | BUY fill |
| --- | ---: | --- | --- | ---: |
| 2022-08-10 | 200 after fill | BUY_NEW | CONTINUATION_WITH_CAUTION / BUY_NEW_REDUCED_ONLY | 200 |
| 2022-08-19 | 200 | ADD | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | 0 |
| 2022-08-30 | 200 | ADD | HEALTHY_CONTINUATION_ENTRY / ADD_ALLOWED | 0 |
| 2022-08-31 | 200 | ADD | REVERSAL_RISK_ENTRY / NO_ADD | 0 |
| 2022-09-07 | 200 | HOLD | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | 0 |

Final 94320 campaign:

```text
opened = 2022-08-10
qty = 200
final PnL = +280
observed MFE = +2.14%
observed giveback = 2.21%
```

Judgment:

```text
94320_NO_ADD_JUSTIFIED = MIXED
```

Avoiding the pre-AC ramp to 1,200 shares improved risk containment. But PM still
emitted repeated ADD actions, while PC/PS converted none into fills and PC
campaign id fields remained blank. So the observed no-ADD is directionally
useful, but not fully proven as clean campaign-aware NO_ADD.

## HOLD vs ADD

Observed:

```text
HOLD-worthy / no extra capital cases = 31
PM ADD actions = 14
executed ADD fills = 0
missing campaign review recurrence = 0
```

Judgment:

```text
HOLD_ADD_SEPARATION = PASS_WITH_PC_PROPAGATION_GAP
```

HOLD and ADD are behaviorally separated: held campaigns were not blindly
amplified. The remaining gap is not the old over-ADD behavior; it is incomplete
campaign identity propagation into PC fields and opaque PM ADD-to-PS conversion.

## Winner Amplification

Open winners at close:

| Symbol | Opened | Final PnL | Comment |
| --- | --- | ---: | --- |
| 47600 | 2022-09-07 | +29,700 | Same-day BUY_NEW spike |
| 27880 | 2022-08-29 | +5,200 | Preserved winner |
| 94320 | 2022-08-10 | +280 | Mature but not amplified |

Open losers / flats:

| Symbol | Final PnL |
| --- | ---: |
| 36600 | -2,300 |
| 32710 | -600 |

Judgment:

```text
WINNER_AMPLIFICATION = MIXED
```

The run improved because it avoided repeated 94320 ADDs and preserved 27880,
but the dominant gain was 47600 on its entry day. That is recovery by new-entry
spike, not proof of mature winner amplification.

## 2022-09-07 PnL Decomposition

Daily PnL:

```text
+27,500 JPY
```

| Symbol | Contribution | Action / state |
| --- | ---: | --- |
| 47600 | +29,700 | BUY_NEW same-day spike |
| 27880 | +1,900 | HOLD mature open winner |
| 94320 | +300 | HOLD mature campaign |
| 32710 | -900 | HOLD early position |
| 36600 | -3,500 | HOLD open loser |

Judgment:

```text
RECOVERY_SOURCE = MIXED_WITH_NEW_ENTRY_SPIKE_DOMINANT
```

## Cash / Exposure

Average cash was `83.55%` of equity and average exposure was `15.69%`.
Cash exceeded 85% on 12 of 20 days.

Selection coverage still found PC-positive names most days:

```text
average PC-positive candidates/day = 9.8
average PS-positive candidates/day = 1.2
actual BUY fills = 24
```

Classification:

```text
LOW_EXPOSURE_JUDGMENT = MULTI_CAUSAL
```

Drivers:

- campaign-aware no-ADD / reduced exposure after AC
- Entry Admission caution
- PS / lot / capital conversion filtering
- unresolved PC campaign id propagation for current positions
- no evidence of catastrophic capital defect

## Selection Opportunity Coverage

Daily candidate counts were stable at 50-51. Most candidates were
`CONTINUATION_WITH_CAUTION`; `HEALTHY_CONTINUATION_ENTRY` existed on several
days but was sparse. PC-positive candidates existed even when no BUY filled,
so some cash is attributable to downstream conversion / lot / caution, not pure
opportunity scarcity.

## REENTRY

There was no clear repeated same-symbol churn comparable to the pre-Z concern
in this 20BD after-run. REENTRY behavior is improved mostly by suppression and
lower churn, not by many profitable genuine recovery cases.

```text
REENTRY_DIRECTION = IMPROVING
```

## Payoff Structure

AC/AD1-after closed campaigns:

| Metric | Value |
| --- | ---: |
| Closed campaigns | 19 |
| Winners | 7 |
| Losers | 11 |
| Flat | 1 |
| Win rate | 36.84% |
| Avg winner | +900 |
| Avg loser | -2,142 |
| Median winner | +1,200 |
| Median loser | -2,000 |
| Largest winner | +1,700 |
| Largest loser | -6,000 |
| Payoff ratio | 0.42 |
| Profit factor | 0.27 |

Compared with AC-before, profit factor slightly improved, but payoff ratio
worsened. The intended asymmetric structure is not proven.

## Direction Flags

```text
CAMPAIGN_LIFECYCLE_DIRECTION = IMPROVING
HOLD_DIRECTION = IMPROVING
ADD_DIRECTION = MIXED
WINNER_AMPLIFICATION_DIRECTION = MIXED
REENTRY_DIRECTION = IMPROVING
CAPITAL_UTILIZATION_DIRECTION = MIXED
PAYOFF_ASYMMETRY_DIRECTION = NOT_IMPROVING
PHASE30_AD2_BEHAVIOR_DIRECTION = MIXED
```

## Legacy / Production Integrity

```text
LEGACY_CAMPAIGN_FALLBACK_REFERENCE_COUNT = 0
OBSOLETE_HOLD_ADD_HEURISTIC_REFERENCE_COUNT = 0
DUPLICATE_CAMPAIGN_AUTHORITY = NO
ONE_PRODUCTION_CAMPAIGN_LIFECYCLE_PATH = YES
PHASE30_Z_REENTRY_PRESERVED = YES
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
```

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED BY PHASE30-AD2
```

## 100BD Gate

```text
100BD_ENTRY_BLOCKED
```

Dominant remaining behavior gap:

```text
PC_CURRENT_CAMPAIGN_ID_PROPAGATION_AND_ADD_CONVERSION_GAP
```

The next repair should not tune Strategy. It should prove why PM ADD evidence
does or does not become PC/PS executable ADD, and ensure current-position
campaign identity is not blank in PC when SI lifecycle identity is COMPLETE.

## Evidence

```text
reports/phase_reports/phase30_ad2/analysis_evidence.json
```

## Recommended Next Task

```text
Phase30-AE0 - PC Current Campaign Identity Propagation / ADD Conversion Gap Audit
```
