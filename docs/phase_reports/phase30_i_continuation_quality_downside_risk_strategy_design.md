# Phase30-I — Continuation Quality / Downside Risk Strategy Architecture Design

## Task ID

`Phase30-I`

## Status

```text
COMPLETE
STRATEGY ARCHITECTURE DESIGN / PRODUCTION-COMMON DESIGN FREEZE
DESIGN ONLY
NO PRODUCTION STRATEGY IMPLEMENTATION
NO STRATEGY / RUNTIME / CONFIG / MODEL / THRESHOLD CHANGE
NO BUY QUALITY / BUY_WAIT / ADD / HOLD / REDUCE / EXIT CHANGE
NO SAFETY CHANGE
NO IMPLEMENTATION AUTHORIZED BY PHASE30_I
```

## Primary Judgment

```text
PHASE30_I_STRATEGY_INTELLIGENCE_ARCHITECTURE_DESIGNED_PRODUCTION_COMMON_SHADOW_FIRST_IMPLEMENTATION_READY
```

## Design Scope

Phase30-I designs the durable Strategy Intelligence architecture for:

```text
Eligibility / Event Facts
Continuation Quality
Downside Risk
Expected Edge / Opportunity Cost
Lifecycle interpretation
Shadow-first migration
Regression gates
```

The durable authority is not this phase report alone. The design is
materialized into Architecture documents:

```text
docs/02_architecture/strategy_intelligence_architecture_v1.md
docs/02_architecture/strategy_intelligence_data_contract_v1.md
docs/02_architecture/strategy_intelligence_regression_contract_v1.md
docs/02_architecture/strategy_decision_quality_and_continuation_quality_contract.md
```

## Why Redesign Is Required

Phase30-G/H showed that current Strategy can identify stocks that have moved
strongly, but does not reliably distinguish healthy forward continuation from
exhausted or dangerous opportunity.

Key evidence:

```text
BUY Quality HIGH: mean 20BD return -4.47%, severe 42.41%
BUY Quality LOW:  mean 20BD return +0.07%, severe 38.69%
BUY_NEW LOW_CQ_HIGH_RISK: 80 of 104, mean -5.39%, median -11.27%, severe 55.84%
strong 20D momentum: mean -3.44%, severe 52.67%
strong prior momentum + short reversal: severe selected losers caught 37.21%, healthy winners lost 18.87%
```

Therefore the redesign must separate:

```text
Continuation Quality
Downside Risk
Expected Edge
```

and must not collapse them into one opaque score.

## What Existing Architecture Is Preserved

The existing Production-common authority chain is preserved:

```text
J-Quants / PIT Source Authorities
-> Feature Producers
-> Strategy Evidence
-> Candidate / Opportunity Intelligence
-> Portfolio Construction
-> Position Sizing
-> Runtime Planning
-> Strategy Planning Authority
-> Safety
-> Submit / Execution
-> Current / Ledger / Campaign State
```

PM remains existing-position directional Action Authority. Portfolio
Construction remains Target Portfolio Decision Authority. Runtime Planning
remains pure mapper. Safety remains guardrail authority.

## New Strategy Intelligence Architecture

Target architecture:

```text
PIT Data / Fact Authorities
        ↓
Eligibility / Event Facts
        ↓
Shared Strategy Intelligence
 ┌──────────────────────────────┐
 │ Continuation Quality         │
 │ Downside Risk                │
 │ Expected Edge / Opportunity  │
 └──────────────────────────────┘
        ↓                 ↓
 BUY-side consumers     PM existing-position consumers
        ↓                 ↓
 Portfolio Construction / PM
        ↓
 Position Sizing
        ↓
 Runtime Planning
        ↓
 Safety / Execution
```

The first artifact design is a unified `strategy/strategy_intelligence.json`
with distinct internal sections, chosen to keep a single as-of boundary while
preventing semantic mixing.

## Eligibility / Event Layer

The design separates:

```text
DISQUALIFYING_FACT
```

from:

```text
PROBABILISTIC_RISK
```

Unsupported security type, trading restriction, authoritative delisting risk,
unresolved corporate action, missing required authority, or hard tradability
failure can be disqualifying or review-required facts. Volatility, short-term
reversal, weak participation, microstructure fragility, regime stress, and
event coverage uncertainty are probabilistic risks unless backed by an
authoritative hard fact.

Missing event coverage must not mean safe.

## Continuation Quality Contract

Continuation Quality is a structured PIT evidence object answering:

```text
How healthy and persistent is the current upward continuation thesis?
```

Dimensions:

```text
Trend Health
Persistence
Acceleration / Deceleration
Exhaustion / Reversal
Participation / Volume Confirmation
Relative Strength
Regime Compatibility
```

It is not raw momentum, BUY Quality, rank, profit, or cash availability.

## Downside Risk Contract

Downside Risk is separate and answers:

```text
How exposed is this candidate/position to material adverse movement or failure?
```

Dimensions:

```text
Reversal Risk
Volatility Expansion Risk
Exhaustion Risk
Participation Weakness
Microstructure / Tick Fragility
Regime Stress
Event Uncertainty
```

The design supports probabilistic risk accumulation, not broad one-factor veto
logic.

## Expected Edge Contract

Expected Edge is an interpretable research contract:

```text
Continuation Opportunity
+ Payoff Potential
- Downside Risk
- Opportunity Cost
```

It is not a required linear formula and not calibrated expected return.
`runtime_opportunity_score` remains an uncalibrated relative model score unless
a later calibration gate proves otherwise.

## BUY_NEW Design

BUY_NEW should reason:

```text
Eligibility PASS
+ Continuation Quality
+ Downside Risk
+ Expected Edge / Opportunity Comparison
+ Portfolio constraints
```

It should not reward high historical momentum alone. Exhaustion/reversal,
high-volatility negative short structure, event uncertainty, and
microstructure weakness are handled as general evidence classes, not
symbol-specific anecdotes.

## BUY_WAIT Design

BUY_WAIT remains temporary, non-Pending, automatically re-evaluated, and
independent from SELL. It means:

```text
continuation thesis not invalid,
but current entry timing or evidence sufficiency is not good enough today
```

## ADD Design

ADD asks:

```text
Is additional capital still justified now, relative to existing exposure,
downside risk, and alternatives?
```

ADD requires incremental Continuation Quality and incremental Expected Edge.
It must not mean "stock went up after purchase, therefore add."

## REENTRY Design

REENTRY is preserved. The design distinguishes genuine recovery from churn /
unresolved continuation while keeping cooldown and recovery hurdle semantics.

## HOLD Design

HOLD means:

```text
the current PIT evidence still justifies keeping capital deployed here
```

It is distinct from ADD-worthiness. Existing holdings are not mechanically
forced through BUY_NEW eligibility semantics, though hard facts still apply.

## Profit Protection Design

Profit Protection is evidence, not action authority. It combines observed
embedded profit, PIT-safe observed MFE/giveback, CQ deterioration, Downside Risk
increase, and regime deterioration. It is not a fixed +10%/+20% take-profit or
fixed trailing stop.

## REDUCE / EXIT Design

Lifecycle interpretation:

```text
HEALTHY -> HOLD / ADD candidate
still positive but decelerating -> HOLD / ADD stop
material deterioration -> Profit Protection / REDUCE evidence
thesis broken -> REDUCE / EXIT evidence
```

The design prevents automatic REDUCE -> EXIT and prevents BUY state from
suppressing SELL continuity.

## Capital Concentration Design

Capital concentration should emerge from validated Winners:

```text
BUY -> HOLD -> ADD -> allow concentration within Strategy/Safety limits
```

No forced concentration, fixed full exposure, or fixed number of positions.
Cash remains valid.

## Opportunity Cost Design

Expected Edge compares:

```text
existing holding
new BUY candidate
ADD candidate
Cash
```

The marginal JPY should move only when relative economic merit is strong enough
after risk, confidence, and turnover.

## Shared Evidence vs Action Authority

```text
Shared intelligence != Shared action authority
```

CQ, Downside Risk, and Expected Edge are shared evidence. PM and Portfolio
Construction retain action and target authority.

## Data / Feature Lineage

Every new dimension must prove:

```text
Source
-> PIT Authority
-> Feature
-> Strategy Intelligence Artifact
-> Consumer
-> Decision influence
```

Producer existence alone is not implementation completion.

## Persistence / Current Design

Market-derived evidence is recomputed daily. Current does not become stale
market intelligence authority.

Persistable campaign-relative state may include entry thesis metadata,
observed high-water mark, observed MFE/giveback, ADD history, prior CQ state,
and deterioration transition timing.

## Leakage Firewall

Runtime must never consume future return, future price, future MFE/MAE, final
campaign outcome, Historical result, Paper Ledger performance, selected future
outcome, future regime, audit judgment, test result, or final return.

## Shadow Migration

Before authority migration, record:

```text
CURRENT_DECISION
PROPOSED_INTELLIGENCE_EVIDENCE
PROPOSED_DECISION_IF_AUTHORIZED
```

No Historical-only Strategy stack is allowed. Shadow logic must use the same
future Production-common producer path.

## Regression Contract

Regression coverage is specified in:

```text
docs/02_architecture/strategy_intelligence_regression_contract_v1.md
```

It covers data lineage, BUY lifecycle, ADD lifecycle, SELL lifecycle, REENTRY,
BUY_WAIT, NO_ACTION, Safety, closed-contract non-regression, and shadow drift.

## Multi-Day Regression

Mandatory minimum:

```text
Day 1 BUY
Day 2 HOLD
Day 3 ADD
Day 4 HOLD
Day 5 deterioration
Day 6 REDUCE
Day 7 partial position persists
Day 8 EXIT
```

Also required:

```text
BUY_WAIT while existing SELL executes
REENTRY after cooldown/recovery
no opportunity -> Cash
```

## Winner Preservation Gate

Future changes must report severe losers avoided, healthy Winners removed,
missed MFE, return, MAE, MFE preservation, turnover, exposure, and
concentration. No design is approved solely because it lowers MAE.

## Production Authority Migration Gate

Migration requires schema stability, PIT lineage, no leakage, multi-day
persistence proof, Winner Preservation pass, severe-loss reduction evidence,
closed-contract regression PASS, understood shadow/current comparison,
Production-common path proof, and no Historical-only behavior.

Phase30-I does not approve migration.

## Durable Architecture Documents

Created:

```text
docs/02_architecture/strategy_intelligence_architecture_v1.md
docs/02_architecture/strategy_intelligence_data_contract_v1.md
docs/02_architecture/strategy_intelligence_regression_contract_v1.md
docs/phase_reports/phase30_i_continuation_quality_downside_risk_strategy_design.md
```

Updated:

```text
docs/02_architecture/strategy_decision_quality_and_continuation_quality_contract.md
docs/01_requirements/phase_roadmap.md
```

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED BY PHASE30_I
```

## Recommended First Implementation Task

```text
Phase30-J — Strategy Intelligence Shadow Evidence Producer
```

