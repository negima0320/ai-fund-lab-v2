# Phase30-D Strategy Research Direction and Continuation Quality Thesis

Primary Judgment:

```text
PHASE30_D_STRATEGY_RESEARCH_DIRECTION_CONTINUATION_QUALITY_THESIS_DOCUMENTED_LONG_HORIZON_VALIDATION_REQUIRED
```

Task ID: `Phase30-D`

Task type:

```text
DOCUMENTATION / RESEARCH DIRECTION FREEZE
```

Status:

```text
COMPLETE
DOCUMENTATION ONLY
NO STRATEGY REDESIGN IMPLEMENTED
NO STRATEGY / RUNTIME / CONFIG / MODEL / THRESHOLD CHANGE
NO SAFETY / BUY QUALITY / BUY_WAIT / ADD / HOLD / REDUCE / EXIT CHANGE
NO CURRENT 977BD HISTORICAL MUTATION
NO IMPLEMENTATION AUTHORIZED BY PHASE30-D
```

## Purpose

Phase30 is moving from isolated performance tuning toward evidence-based
reassessment of Strategy Decision Quality.

The central hypothesis is that stock selection, ADD, HOLD, profit protection,
REDUCE, and EXIT may need to share a common forward-looking PIT thesis:

```text
Does this stock, given everything legitimately knowable now, still have a
relatively strong case for continuing upward from here?
```

This hypothesis is provisionally named:

```text
Continuation Quality / Forward Edge
```

This document records the research direction. It does not prove the thesis and
does not authorize production redesign.

## Current Long-Horizon Run

Current clean long-horizon Historical:

```text
runtime-test-historical-extended-smoke-20260815T061857447380Z
```

Contract:

```text
requested period: 2022-08-10 through 2026-08-09
resolved trading period: 2022-08-10 through 2026-08-07
expected business days: 977
```

Read-only observed status while preparing this document:

```text
run_state.status: RUNNING
latest observed completed date: 2023-04-12
latest observed completed business days: 165
halted_job: null
error: null
```

The current run must continue independently. Full long-horizon conclusions are
pending completion of this clean 977BD baseline.

## Project Strategy Goal

AI Fund Lab v2 is a Japanese equity, long-only, cash-equity,
momentum-oriented swing trading system.

Long-term project goal:

```text
Annualized Return +50%
```

This goal must not be used to justify arbitrary Historical threshold tuning.
The strategy philosophy is:

- identify stocks likely to continue rising,
- enter after sufficient confirmation rather than trying to buy the absolute bottom,
- continue HOLD while the upward thesis remains valid,
- ADD when incremental capital still has positive relative merit,
- avoid unnecessary churn,
- protect substantial Winner profits when continuation quality deteriorates,
- REDUCE / EXIT when the continuation thesis materially weakens or breaks,
- allow Cash when valid opportunity is absent.

Fixed exposure is not a goal. Cash remains valid when opportunity quality is
not sufficient.

## Core Phase30 Problem

The central Phase30 question is no longer simply:

```text
How do we buy more?
```

or:

```text
How do we sell earlier?
```

The more fundamental question is:

```text
How should the system determine whether a stock is still a high-quality
forward opportunity from the current PIT state?
```

Current concern:

```text
The system may be better at identifying stocks that have risen strongly than
stocks that are likely to continue rising.
```

That distinction must become explicit before Strategy redesign.

## Definition Of Good Stock

A "good stock" for AI Fund Lab v2 is not merely a stock that has risen
recently.

Research definition:

```text
A good stock is a stock whose current PIT-observable state suggests that future
upward continuation has relatively favorable probability, magnitude,
persistence, and risk-adjusted economic value compared with available
alternatives.
```

This is a research definition. The current system is not assumed to estimate it
correctly.

## Confirmed Phase30-A Evidence

Phase30-A confirmed clean 20BD measurement integrity:

```text
measurement_integrity: PASS
performance evidence: VALID_FOR_PHASE30_PERFORMANCE_ATTRIBUTION
valuation / basis contamination recurrence: not observed
20BD result: -2.749%
```

The `-2.749%` result was a real Strategy outcome, not an accounting error.
No valuation/basis contamination was found in the clean 20BD run.

Phase30-A evidence supported these research priorities:

- Entry Quality received strong research support.
- SELL Timing / Exit Outcome Separability received strong research support.
- Winner Profit Retention received moderate support.
- Executed BUY forward outcomes were negative on average over observable short horizons.
- ADD evidence was weak / inconclusive.
- BUY_WAIT evidence was mixed.
- BULL itself was not proven to be the problem.

Important limitation:

```text
20BD evidence is valid for attribution, but not sufficient for final
long-horizon Strategy redesign.
```

## Preliminary Phase30-C Evidence

Phase30-C is preliminary because the 977BD run was incomplete.

Snapshot evidence:

```text
completed-window BUY fills: 137
BUY_NEW: 74
BUY_ADD: 16
REENTRY: 47
unique BUY symbols: 74
total BUY notional: 5,560,900 JPY
```

### BUY Quality / Rank

Current BUY Quality score and Opportunity Rank did not meaningfully separate
material Winners from Losers in the Phase30-C audit snapshot.

This does not prove those authorities are useless across 977BD. It is
preliminary evidence that they are insufficient as standalone selection
authorities.

### Trajectory

`MIXED_OR_UNRESOLVED` was heavily represented in the loser cohort. This matters
because Runtime already had information indicating unresolved trajectory.

### 78780

`78780` demonstrated:

- very strong 20D / 10D / 5D historical momentum,
- negative 1D movement,
- strong momentum deceleration,
- high volatility,
- `MIXED_OR_UNRESOLVED`,
- HIGH / FULL allocation eligibility.

This is a strong example of:

```text
historical strength != continuation quality
```

It is still only one case study, not a universal conclusion.

### 93180

`93180` demonstrated a different issue:

- very-low-price microstructure,
- repeated exposure,
- contemporaneous public JPX alert information,
- Runtime consumption of that alert status not proven.

This is a Corporate/Event Eligibility research gap, not solely a Momentum
problem.

## HOLD / SELL Evidence

Phase30-C showed that the system can identify real Winners but may fail to
retain sufficient profit.

Material MFE giveback examples included:

```text
83060
47600
99840
42630
```

This is not proof that every SELL should be earlier.

Correct research question:

```text
Was meaningful continuation deterioration observable using PIT information
before substantial MFE giveback occurred?
```

This must remain separate from hindsight peak prediction.

## Continuation Quality Thesis

Continuation Quality means:

```text
A PIT-based estimate of how healthy, persistent, and economically attractive
the current upward continuation thesis remains.
```

It is not an implemented score. No production threshold is authorized here.

Candidate research dimensions:

- trend persistence,
- multi-horizon momentum structure,
- acceleration / deceleration,
- relative strength,
- volatility quality,
- liquidity / microstructure quality,
- overheat / exhaustion risk,
- Market Context compatibility,
- regime-transition state,
- Corporate/Event eligibility and risk,
- existing relative model score,
- calibrated forward economic edge if later validated.

These are candidate research dimensions, not approved Runtime inputs.

## Lifecycle Unification

### BUY

Research question:

```text
Is this stock currently one of the relatively strongest forward-continuation
opportunities?
```

Not:

```text
Has this stock risen the most?
```

### ADD

Research question:

```text
After Entry, has the continuation thesis remained sufficiently strong or
improved such that incremental capital still has favorable marginal merit?
```

Not:

```text
Did the stock go up after we bought it?
```

### HOLD

Research question:

```text
If evaluated again today from current PIT information, is the continuation
thesis still strong enough to justify keeping this capital deployed here?
```

### ADD STOP / HOLD

A stock may remain HOLD-worthy while no longer deserving incremental ADD
capital. This separation is important.

### PROFIT PROTECTION / REDUCE

Research question:

```text
Is the stock still strong, but is continuation quality deteriorating enough
that protecting part of accumulated Winner profit is warranted?
```

### EXIT

Research question:

```text
Has the continuation thesis broken sufficiently that capital should be removed?
```

These are conceptual research relationships, not authorized production rules.

## Candidate State Progression

Current hypothesis:

```text
HEALTHY_WINNER
-> STRONG_BUT_DECELERATING
-> TOPPING_RISK
-> BREAKDOWN
```

Possible conceptual action mapping:

```text
HEALTHY_WINNER          -> HOLD / ADD candidate
STRONG_BUT_DECELERATING -> HOLD / ADD-stop / profit-protection research candidate
TOPPING_RISK            -> REDUCE research candidate
BREAKDOWN               -> REDUCE / EXIT research candidate
```

These are not final semantics and must not be implemented from this document.

## Why This Could Improve BUY And SELL

Current potential failure pattern:

```text
Strong historical momentum
-> late BUY
-> continuation already decelerating
-> HOLD while price still appears strong
-> large giveback
-> REDUCE / EXIT after weakness becomes obvious
```

Shared continuation thesis hypothesis:

```text
High historical momentum + healthy continuation structure
-> BUY

High continuation quality maintained
-> HOLD / ADD

Continuation decelerates
-> stop ADD

Topping risk increases
-> protect profit / REDUCE candidate

Thesis breaks
-> EXIT
```

The same thesis could connect Entry Quality, ADD Quality, HOLD quality, profit
retention, and Exit Outcome Separability.

## Formal Expected Edge Calibration

Current `runtime_opportunity_score` is not an economic expected return. It is an
uncalibrated relative model score.

Formal Expected Edge Calibration means researching whether PIT-observable
features and relative scores can be mapped to economically meaningful forward
outcome distributions:

- expected forward return,
- probability of positive return,
- expected MFE,
- expected MAE,
- risk-adjusted continuation value,
- downside-adjusted edge.

Future outcome may be used only as an offline read-only research label. It must
not become future leakage into Runtime.

Expected Edge should be treated as a potential complement to Continuation
Quality, not assumed to be the same concept.

## Continuation Quality vs Expected Edge

Continuation Quality primarily asks:

```text
Is the current upward trend structurally healthy and likely to persist?
```

Expected Edge primarily asks:

```text
Given current information, is allocating capital here economically attractive
relative to risk and alternatives?
```

A stock could have high continuation probability but small economic upside. A
different stock could have lower continuation probability but larger positive
payoff asymmetry. Phase30 research should determine whether these concepts
should remain separate or be combined.

## Event / Eligibility Layer

Not all risks should be forced into Continuation Quality.

Potential architecture:

```text
Universe
-> Eligibility / Event Risk Gate
-> Continuation Quality
-> Expected Edge / Opportunity Comparison
-> Portfolio Construction
-> Position Management
```

Research candidates for upstream eligibility or constraints:

- exchange warning designations,
- supervision,
- delisting risk,
- extreme low-price microstructure,
- unresolved corporate actions.

No new gates are authorized by Phase30-D.

## Low-Price / Microstructure Research

Phase30-C found preliminary concern around very-low-price names.

Do not introduce an arbitrary minimum share-price threshold. Research questions:

- Does low price create excessive tick sensitivity?
- Does low-priced momentum produce unstable continuation?
- Is ranking distorted by percentage moves in low-price stocks?
- Does 100-share lot structure interact badly with 1M JPY capital?
- Does volatility-adjusted continuation quality sufficiently handle this?
- Should microstructure risk affect eligibility, score, or sizing?

## Research Dataset Required After 977BD

After the clean 977BD run completes, Phase30 should prepare an offline
read-only research dataset.

Recommended units:

```text
symbol x business date
campaign x decision date
```

Initial PIT feature set should use existing authoritative features only.

Outcome labels may include:

- 1BD forward return,
- 3BD forward return,
- 5BD forward return,
- 10BD forward return,
- 20BD forward return,
- MFE,
- MAE,
- future peak timing,
- giveback,
- campaign final outcome.

Outcome labels are research-only. They must not be exposed to runtime decision
paths.

## Primary Research Questions After 977BD

### RQ1 - Winner vs Loser at Entry

What PIT characteristics distinguish future Winners from future Losers?

### RQ2 - Continuation vs Exhaustion

Can the system distinguish strong continuation, fading prior winner,
acceleration / overheat, and unresolved trajectory before outcome is known?

### RQ3 - Winner Persistence

What PIT characteristics remain stable while a Winner continues rising?

### RQ4 - Winner Deceleration

Which PIT changes reliably precede large profit giveback?

### RQ5 - Entry vs SELL Failure

How much loss comes from wrong stock selection, late Entry, bad ADD, or late
HOLD/SELL response?

### RQ6 - Event Risk

Can known contemporaneous public risk materially improve eligibility without
hindsight leakage?

### RQ7 - Regime Dependence

Does Continuation Quality behave differently in BULL, RANGE, BEAR, RECOVERY,
CORRECTION, and especially during transitions?

## Research Discipline

Phase30-D explicitly prohibits overfitting.

Do not:

- optimize to individual symbols,
- define thresholds from a single 20BD or 160BD sample,
- use contaminated Phase29 long-run performance as tuning authority,
- use future outcomes as runtime inputs,
- use Annualized Return +50% as justification for arbitrary threshold tuning.

Require where practical:

- cohort analysis,
- sufficient sample size,
- multiple market regimes,
- temporal splits,
- walk-forward or equivalent time-respecting validation,
- sensitivity analysis,
- stability across subperiods,
- clear separation between research labels and Runtime features.

The current long Historical is not strict OOS AI performance. This limits claims
about predictive validity.

## Strategy Redesign Decision Gate

Do not automatically redesign Strategy after the 977BD run.

Strategy Decision Architecture redesign becomes justified only if clean evidence
shows that:

1. current BUY Quality / rank authorities have inadequate forward separation,
2. alternative PIT features provide reproducible forward separation,
3. Winner continuation and deterioration can be distinguished before outcome,
4. the same conceptual authority can improve lifecycle consistency without
   harming valid Winners,
5. changes can be implemented Production-common,
6. future leakage is avoided,
7. closed Safety / Runtime contracts remain intact.

If evidence is weak, retain current architecture and make narrower improvements
instead.

## What Must Not Be Reopened

Without new evidence, do not reopen:

- BUY / SELL independence,
- Production-common Runtime,
- fail-closed,
- PM ADD -> Runtime BUY_ADD,
- lot-aware sizing,
- residual capital recycling,
- semantic REENTRY,
- cooldown / recovery hurdle,
- BUY_WAIT non-Pending semantics,
- Strategy cap / Safety hard cap separation,
- Price / Quantity Adjustment Basis Contract,
- basis persistence,
- Execution NO_ACTION continuity.

The potential redesign concerns Strategy Decision Quality, not these closed
Runtime contracts.

## Current Work State

Completed:

- Phase30-A clean 20BD integrity and attribution.
- Phase30-B long-horizon preflight.
- Phase30-C in-flight BUY Selection Quality audit.

Running:

```text
runtime-test-historical-extended-smoke-20260815T061857447380Z
```

Deferred until the long run completes:

- full Winner / Loser separation,
- full HOLD / SELL timing attribution,
- full MFE retention analysis,
- regime-transition attribution,
- full ADD quality,
- Continuation Quality feature research,
- Formal Expected Edge Calibration,
- Strategy redesign decision.

## Current Direction

Phase30 should research whether BUY / ADD / HOLD / REDUCE / EXIT can be
organized around a coherent common thesis:

```text
Select stocks that have a relatively high probability / expected quality of
continuing upward from the current PIT state, continue allocating capital while
that thesis remains strong, and protect or exit capital as that thesis
deteriorates.
```

This is the principal research thesis. It is not yet proven.

## Implementation Status

```text
NO STRATEGY REDESIGN IMPLEMENTED
NO IMPLEMENTATION AUTHORIZED BY PHASE30-D
```

## Next Operational Action

```text
CONTINUE CURRENT CLEAN 977BD HISTORICAL
```
