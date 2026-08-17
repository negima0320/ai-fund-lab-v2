# Phase30-Y - Strategy Behavior Conformance Review

Task ID: `Phase30-Y`

Target run:

```text
runtime-test-historical-extended-smoke-20260816T023934342407Z
```

Boundary:

```text
READ_ONLY_REVIEW
NO_STRATEGY_RUNTIME_CONFIG_MODEL_THRESHOLD_CHANGE
NO_TARGET_RUN_MUTATION
NO_100BD_EXECUTION
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_Y
```

## Primary Judgment

```text
STRATEGY_BEHAVIOR_CONFORMANCE = PARTIAL
100BD_GATE = 100BD_ENTRY_BLOCKED_BY_BEHAVIOR_GAP
```

The current low 20BD return is not simply a clean outcome of the intended
Strategy. The SELL / REDUCE, Entry Admission, and one-lot concentration repairs
are broadly behaving as intended, but the Production behavior still has material
gaps against the intended investment lifecycle:

- REENTRY accepts "recovery" too easily relative to the architecture.
- ADD / winner amplification exists, but remains incomplete and concentrated in
  one modest winner.
- Capital allocation still relies on uncalibrated relative opportunity evidence
  and cautious Entry Admission rather than proven forward edge.
- Closed-campaign payoff asymmetry is opposite of the intended structure.

The dominant blocking gap is REENTRY conformance. It is sufficiently concrete
in this 20BD run to repair before treating 100BD as a clean long-horizon
Strategy behavior validation.

## Intended Strategy Behavior

The durable architecture defines the Production Strategy as Japanese equity
swing / momentum-follow investing. It should buy stocks that are not merely
past winners, but whose PIT-observable state suggests healthy future
continuation with manageable downside and attractive relative economic merit.

Required lifecycle semantics:

| Stage | Intended behavior |
| --- | --- |
| Selection | Rank and select future-continuation opportunity, not raw momentum alone. |
| Entry | Use CQ, Downside Risk, Relative Strength, and entry timing; BUY_WAIT when overheated, reversing, decelerating, or insufficient. |
| HOLD | Active decision that current PIT evidence still justifies deployed capital. |
| ADD | Distinct from HOLD; incremental capital only when ADD-worthy versus alternatives and current exposure. |
| REDUCE | Trim when risk / deterioration increases while optionality remains. |
| EXIT | Close when thesis / opportunity / expected edge breaks. |
| REENTRY | Re-enter only after genuine recovery, cooldown, prior-exit context, and churn suppression. |
| Capital reallocation | Route released cash to higher-quality BUY_NEW / ADD / genuine REENTRY, or Cash if no opportunity. |
| Portfolio outcome | Accept many small losses only if fewer winners become large enough to dominate payoff. |

Expected Edge remains:

```text
UNCALIBRATED
```

It may be relative opportunity evidence, not calibrated expected return.

## Selection

```text
SELECTION_CONFORMANCE = PARTIAL
```

Conforming evidence:

- Portfolio Construction consumes canonical opportunity rank / score authority
  and preserves rank lineage.
- Strategy Intelligence adds Continuation Quality, Downside Risk, Relative
  Strength, and Entry Admission evidence to PC members.
- `OVERHEATED_DECELERATING_ENTRY / BUY_WAIT` candidates did not leak into actual
  BUY fills in the 20BD run.

Gap evidence:

- Actual BUY fills were dominated by `CONTINUATION_WITH_CAUTION`, not clearly
  `HEALTHY_CONTINUATION_ENTRY`.
- Several actual entries carried negative uncalibrated `runtime_opportunity_score`
  while still passing reduced-allocation / one-lot mechanics.
- `runtime_opportunity_score` remains uncalibrated relative evidence; it cannot
  prove forward economic edge.

Classification:

```text
DATA_GAP / DESIGN_GAP
Priority = MEDIUM
```

Selection has better evidence than before Phase30-W, but the system still does
not fully prove that selected names are high-quality forward opportunities.

## Entry

```text
ENTRY_CONFORMANCE = PASS
```

Phase30-W Entry Admission is materially conforming:

| Entry state / action across 20BD | Count |
| --- | ---: |
| CONTINUATION_WITH_CAUTION / BUY_NEW_REDUCED_ONLY | 754 |
| CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | 103 |
| OVERHEATED_DECELERATING_ENTRY / BUY_WAIT | 94 |
| HEALTHY_CONTINUATION_ENTRY / BUY_NEW_ALLOWED | 42 |
| HEALTHY_CONTINUATION_ENTRY / ADD_ALLOWED | 4 |
| OVERHEATED_DECELERATING_ENTRY / NO_ADD | 5 |
| REVERSAL_RISK_ENTRY / BUY_WAIT | 1 |
| REVERSAL_RISK_ENTRY / NO_ADD | 1 |

Actual BUY fills in `BUY_WAIT` / `REVERSAL_RISK_ENTRY BUY_WAIT`:

```text
0
```

BUY_WAIT remained non-Pending, next-PIT reevaluable, SELL-independent, and not a
future commitment. This matches the durable Entry design.

## HOLD

```text
HOLD_CONFORMANCE = PARTIAL
```

Conforming evidence:

- PM HOLD decisions are active decisions with reason evidence such as
  `trend_continuation`, `positive_expected_edge`, and `downside_risk_contained`.
- Winners such as 94320 and 27880 were not automatically sold because of noise.
- Profit alone was not treated as EXIT authority.

Gap evidence:

- Final book still retained weak or flat survivors: 36600 `-1,300`, 67860
  `-4,200`, 94340 `-630`, 93180 `0`.
- Strategy Intelligence lifecycle context for some held symbols remained
  campaign-partial, so HOLD-worthiness is not fully connected to campaign
  identity and observed giveback / MFE evidence.

Classification:

```text
OBSERVABILITY_GAP / DATA_GAP
Priority = MEDIUM
```

HOLD is not merely inertia, but HOLD-worthiness is still not fully proven for
all retained weak positions.

## ADD / Winner Amplification

```text
ADD_CONFORMANCE = PARTIAL
WINNER_AMPLIFICATION_CONFORMANCE = PARTIAL
```

Conforming evidence:

- 94320 was repeatedly ADDed under PM `ADD_BY_STRONG_TREND_AND_RANK`.
- 2022-08-31 94320 `REVERSAL_RISK_ENTRY / NO_ADD` was blocked by one-lot
  admission with `FAIL_CLOSED`, showing HOLD-worthy and ADD-worthy separation.
- Phase30-W one-lot repair prevented Safety-pass-alone Strategy overshoot.

Gap evidence:

- ADD was concentrated in 94320, and final 94320 campaign PnL was only `+300`.
- 2022-09-07 recovery was mainly 47600 same-day gain `+29,700`, not an existing
  winner that had been amplified over multiple days.
- 93180 re-entered multiple times but was not a clean winner-amplification case.
- Expected Edge remains uncalibrated, so ADD is still based on relative evidence
  and PM score semantics rather than a calibrated marginal-payoff estimate.

Classification:

```text
DESIGN_GAP / DATA_GAP
Priority = MEDIUM
```

The mechanism exists and blocks weak ADDs, but the winner-amplification system
is not yet complete enough to prove the intended asymmetric payoff behavior.

## REDUCE / EXIT

```text
REDUCE_EXIT_CONFORMANCE = PASS
```

20BD behavior conforms to the architecture:

- `risk_increased_but_trend_not_broken` and `peak_drawdown_warning` produced
  REDUCE behavior.
- `trend_and_opportunity_broken`, `hard_stop_current_return`, and
  `profit_retention_break` produced EXIT behavior.
- REDUCE remained distinct from EXIT.
- SELL / REDUCE did not depend on BUY-side Entry Admission success.

This is a preserved improvement and should not be repaired unless a separate
future audit proves a regression.

## REENTRY

```text
REENTRY_CONFORMANCE = FAIL
```

The REENTRY path is the dominant conformance gap.

Intended architecture:

```text
REENTRY requires genuine recovery, cooldown, prior campaign context,
CQ/risk normalization, and churn suppression.
```

Observed actual REENTRY buys:

| Date | Symbol | Campaign | Cooldown | Recovery | Rank | Edge | Technical recovery | Result |
| --- | --- | --- | --- | --- | ---: | ---: | --- | ---: |
| 2022-08-22 | 23880 | 0002 | PASS | PASS | 5 | -0.0039 | trend PASS / momentum PASS | -4,200 |
| 2022-08-23 | 93180 | 0002 | PASS | PASS | 5 | -0.0204 | trend PASS / momentum PASS | 0 |
| 2022-08-26 | 37770 | 0002 | PASS | PASS | 9 | -0.1830 | trend PASS / momentum PASS | +4,800 |
| 2022-08-26 | 89180 | 0002 | PASS | PASS | 10 | -0.2173 | trend PASS / momentum PASS | 0 |
| 2022-08-31 | 93180 | 0003 | PASS | PASS | 3 | -0.0092 | mixed | 0 open |
| 2022-08-31 | 94340 | 0002 | PASS | PASS | 7 | -0.1125 | mixed | -630 open |
| 2022-09-05 | 23880 | 0003 | PASS | PASS | 3 | +0.0049 | trend FAIL / momentum PASS | -1,400 |
| 2022-09-06 | 37820 | 0002 | PASS | PASS | 2 | +0.2295 | trend PASS / momentum FAIL | -5,700 |

The current PC recovery function can pass REENTRY when either trend recovery or
momentum recovery passes. It also records `reentry_score_gate_status =
DIAGNOSTIC_ONLY`, so negative uncalibrated edge is visible but not a hard gate.
Prior exit reason was often `UNKNOWN / GENERIC`.

This allowed repeated same-symbol re-entry that was not convincingly genuine
recovery:

- 23880: `-4,600 -> -4,200 -> -1,400`
- 37820: `-2,800 -> -5,700`
- 93180: `-6,000 -> 0 -> 0 open`

Gap classification:

```text
IMPLEMENTATION_GAP
DATA_GAP
Priority = HIGH
```

Exact cause:

```text
REENTRY recovery evidence is too permissive relative to the durable
"genuine recovery" architecture. Prior-exit causal context is weak, Expected
Edge is diagnostic-only, and partial technical recovery can qualify re-entry.
```

Affected behavior:

```text
REENTRY quality
payoff asymmetry
capital quality
loss containment burden
```

## Capital Reallocation

```text
CAPITAL_REALLOCATION_CONFORMANCE = PARTIAL
```

Conforming evidence:

- Cash remained a valid destination.
- SELL proceeds were not forced into full exposure.
- PC/PS preserved Strategy target vs Safety hard cap separation.
- One-lot admission and residual recycling were active.

Gap evidence:

- Capital did flow to mixed REENTRY names after cooldown/recovery PASS.
- Capital concentration was partly in winners, but also retained several weak /
  flat open positions.
- The 20BD payoff depended on 47600 one-day gain rather than a durable
  reallocation chain from losers into maturing winners.

Classification:

```text
IMPLEMENTATION_GAP / DATA_GAP
Priority = MEDIUM
```

## Payoff Asymmetry

```text
PAYOFF_ASYMMETRY_CONFORMANCE = FAIL
```

Observed closed-campaign payoff:

```text
Closed campaigns = 23
Winners = 6
Losses = 14
Win rate = 26.09%
Average winner = +1,580
Average loser = -2,675.71
Payoff ratio = 0.59
Profit factor = 0.25
```

Why Average Winner < Average Loser despite the intended architecture:

- Re-entry losses are repeated and material.
- Winners are not yet large enough or mature enough to dominate closed losses.
- ADD exists, but winner amplification did not generate large realized payoff
  in this 20BD window.
- Entry was mostly `CONTINUATION_WITH_CAUTION`, not clearly healthy entry.
- Expected Edge is still uncalibrated and cannot yet enforce payoff asymmetry.

The 20BD sample may be too short for winner maturation, but the REENTRY gap is
real enough that this cannot be classified as a clean no-gap outcome.

## Authority Chain

| Evidence | Producer | Artifact | Consumer | Action influence | Conformance |
| --- | --- | --- | --- | --- | --- |
| CQ | Strategy Intelligence | `strategy/strategy_intelligence.json` | PC / SI interpretation | Entry Admission, quality ordering, ADD/NO_ADD context | PARTIAL |
| Downside Risk | Strategy Intelligence | `strategy/strategy_intelligence.json` | PC / SI interpretation | BUY_WAIT / reduced allocation / NO_ADD context | PASS |
| Entry Admission | Strategy Intelligence | `entry_admission.v1` | Portfolio Construction | BUY_WAIT, reduced-only, allowed, NO_ADD | PASS |
| BUY Quality | BUY Quality Resolver | `buy_quality_decisions.json` | PC / PS / Runtime Planning | eligibility / scaling / wait | PARTIAL |
| PM HOLD/ADD/REDUCE/EXIT | Position Management | `pm_decisions.json` | Sell Planning / PC / Runtime Planning | existing-position action intent | PASS |
| REENTRY | Portfolio Construction | PC member fields | PC / PS / Runtime Planning | semantic REENTRY and cooldown/recovery gate | FAIL |
| Portfolio Construction | PC producer | `portfolio_construction.json` | Position Sizing | target membership / target weights | PARTIAL |
| Position Sizing | PS producer | `position_sizing.json` | Runtime Planning | quantities / deltas | PASS |
| Runtime Planning | Runtime planning producer | `runtime_planning.json` | Strategy Planning Authority | maps upstream quantities, does not optimize | PASS_WITH_REVIEW |
| Safety | Safety layer | safety evidence | Submit / execution boundary | guardrail review/block only | PASS |

Dead or under-reflected evidence:

- REENTRY expected edge is recorded but diagnostic-only.
- Prior exit reason context is frequently `UNKNOWN / GENERIC`.
- SI lifecycle/campaign context is partial for some held names.
- Expected Edge exists as a contract but remains uncalibrated and not economic
  units.

## Confirmed Behavior Gaps

| Gap | Classification | Priority | Exact cause | Affected behavior |
| --- | --- | --- | --- | --- |
| REENTRY genuine recovery not strict enough | IMPLEMENTATION_GAP / DATA_GAP | HIGH | Recovery can pass with negative diagnostic edge, generic prior-exit reason, and partial technical recovery | REENTRY, payoff, capital quality |
| Payoff asymmetry not achieved | DESIGN_GAP / DATA_GAP | HIGH | Winner maturation / ADD / calibrated edge not strong enough to dominate repeated small losses | portfolio outcome |
| ADD amplification incomplete | DESIGN_GAP / DATA_GAP | MEDIUM | ADD exists but mostly 94320, with limited final payoff and no calibrated incremental edge | winner amplification |
| HOLD campaign context partial | OBSERVABILITY_GAP / DATA_GAP | MEDIUM | Some SI held-position lifecycle fields lack full campaign identity / MFE / giveback context | HOLD, ADD, profit protection |
| Selection still partly uncalibrated | DATA_GAP | MEDIUM | Candidate ranking and Expected Edge remain relative / uncalibrated | selection, capital allocation |

## Preserved Improvements

Do not repair without new evidence:

```text
Phase30-W Entry Admission = PRESERVED
One-lot concentration repair = PRESERVED
SELL / REDUCE behavior = PRESERVED
Loss containment direction = PRESERVED
BUY / SELL independence = PRESERVED
Phase30-P authority migration = PRESERVED
```

## Leakage / Integrity

From target run Strategy Intelligence / close evidence:

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
ONE_PRODUCTION_STRATEGY_AUTHORITY_PATH = YES
LEGACY_STRATEGY_PATH_REINTRODUCED = NO
EXPECTED_EDGE_STATUS = UNCALIBRATED
```

The close `REVIEW_REQUIRED` remains operational / non-mutating Strategy Shadow
review, not a proven Runtime execution defect.

## Required Final Judgments

```text
SELECTION_CONFORMANCE = PARTIAL
ENTRY_CONFORMANCE = PASS
HOLD_CONFORMANCE = PARTIAL
ADD_CONFORMANCE = PARTIAL
WINNER_AMPLIFICATION_CONFORMANCE = PARTIAL
REDUCE_EXIT_CONFORMANCE = PASS
REENTRY_CONFORMANCE = FAIL
CAPITAL_REALLOCATION_CONFORMANCE = PARTIAL
PAYOFF_ASYMMETRY_CONFORMANCE = FAIL
STRATEGY_BEHAVIOR_CONFORMANCE = PARTIAL
```

## 100BD Gate

```text
100BD_ENTRY_BLOCKED_BY_BEHAVIOR_GAP
```

Blocking reason:

```text
REENTRY_CONFORMANCE = FAIL
```

The next task should repair the dominant REENTRY conformance gap before a 100BD
run is treated as clean Strategy behavior validation.

Recommended next task:

```text
Phase30-Z - REENTRY Genuine Recovery Authority Repair
```
