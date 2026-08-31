# Strategy Intelligence Architecture v1

Created: 2026-08-16

## 1. Authority And Scope

This document is the durable Architecture specification for next-generation
Strategy Decision Intelligence in AI Fund Lab v2.

It is a companion specification under:

- [Strategy Architecture v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_architecture_v1.md)
- [Strategy Decision Quality and Continuation Quality Contract](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_decision_quality_and_continuation_quality_contract.md)
- [Strategy Intelligence Production Migration Contract v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_intelligence_production_migration_contract_v1.md)
- [Strategy Intelligence Legacy Retirement Contract v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_intelligence_legacy_retirement_contract_v1.md)

This document designs the Production-common Strategy Intelligence architecture
for:

```text
Eligibility / Disqualifying Facts
Continuation Quality
Downside Risk
Expected Edge / Opportunity Cost
Lifecycle interpretation
Shadow-first migration and Production authority migration
```

It does not authorize implementation.

```text
NO STRATEGY / RUNTIME / CONFIG / MODEL / THRESHOLD CHANGE
NO BUY QUALITY / BUY_WAIT / ADD / HOLD / REDUCE / EXIT CHANGE
NO SAFETY CHANGE
NO IMPLEMENTATION AUTHORIZED BY PHASE30_I
```

## 2. Evidence Basis

The design is based on the clean Phase30-G/H evidence boundary:

```text
Run ID: runtime-test-historical-extended-smoke-20260815T061857447380Z
Clean period: 2022-08-10 -> 2023-10-26
Completed business days: 299
Decision rows: 14,950
Selected BUYs: 219
Failed 2023-10-27 valuation candidate: excluded
```

Phase30-G confirmed that current BUY Quality and opportunity ranking are
PIT-safe enough to research, but semantically weak for forward stock selection.
Phase30-H confirmed:

```text
Can PIT Data Materially Improve Strategy = STRONG_EVIDENCE
Strategy Redesign Evidence = REDESIGN_EVIDENCE_STRONG
```

The problem is not that the system cannot find stocks that have moved. The
problem is that it does not reliably distinguish:

```text
stocks that have risen strongly
```

from:

```text
stocks whose current PIT state suggests healthy future continuation with
manageable downside and attractive relative economic merit
```

## 3. Preserved Architecture

Phase30-I does not rewrite the Strategy stack. The Production-common authority
chain remains:

```text
J-Quants / PIT Source Authorities
        ↓
Feature Producers
        ↓
Strategy Evidence
        ↓
Candidate / Opportunity Intelligence
        ↓
Portfolio Construction
        ↓
Position Sizing
        ↓
Runtime Planning
        ↓
Strategy Planning Authority
        ↓
Safety
        ↓
Submit / Execution
        ↓
Current / Ledger / Campaign State
```

Closed contracts remain closed:

- Production / Demo / Historical common Strategy contracts
- PIT-only Runtime inputs
- fail-closed missing authority
- BUY / SELL independence
- PM remains existing-position directional Action Authority
- Portfolio Construction remains Target Portfolio Decision Authority
- Runtime Planning remains a pure mapper
- Strategy Planning Authority validates and materializes; it does not re-optimize
- Safety remains guardrail authority, not performance optimizer
- lot-aware sizing and residual capital recycling
- Strategy cap / Safety hard cap separation
- semantic REENTRY, cooldown, and recovery hurdle
- BUY_WAIT non-Pending semantics
- Execution NO_ACTION continuity
- price/quantity adjustment basis persistence
- Current/Ledger authority integrity

## 4. Current Decision Flow

Readable current flow:

```text
PIT Data
  -> Candidate model / Opportunity rank
  -> BUY Quality
  -> Portfolio Construction / PM
  -> Position Sizing
  -> Runtime Planning
  -> Strategy Planning Authority
  -> Safety / Execution
```

Current issues:

- `runtime_opportunity_score` is an uncalibrated relative model score, not
  expected return.
- BUY Quality HIGH/FULL does not reliably imply better forward outcomes.
- Multi-horizon trajectory exists but has zero weighted BUY Quality score
  influence and mainly acts as a BUY_WAIT veto.
- Downside risk exists as scattered evidence, not a first-class contract.
- Corporate/Event risk coverage is incomplete.
- ADD, REENTRY, HOLD, REDUCE, and EXIT need the same forward-continuation
  evidence with action-specific interpretation.

## 5. Target Strategy Intelligence Flow

Target flow:

```text
PIT Source Authorities
  -> Feature Producers
  -> Strategy Intelligence
       Eligibility
       Continuation Quality
       Downside Risk
       Expected Edge evidence
       Profit Protection evidence
       Lifecycle / campaign context
  -> Action-specific consumers
       BUY-side / Portfolio Construction
       PM existing-position decisions
  -> Position Sizing
  -> Runtime Planning
  -> Strategy Planning Authority
  -> Safety
  -> Submit / Execution
```

Authority ownership:

| Layer | Authority mode | Does not decide |
|---|---|---|
| Eligibility / Event Facts | Fact / review authority | Expected edge, target weight, PM action |
| Continuation Quality | Shared evidence authority | BUY/SELL action, sizing, Safety |
| Downside Risk | Shared probabilistic risk evidence | Hard block unless a disqualifying fact exists |
| Expected Edge | Interpretable economic merit evidence | Runtime order mapping, Safety override |
| Portfolio Construction | Target Portfolio Decision Authority | Broker quantity, Safety |
| PM / Position Management | Existing Position Intent Authority | New universe membership, order submission |
| Runtime Planning | Pure mapper | Re-optimization |
| Safety | Block / Review guardrail | Performance optimization |

Phase30-O fixes the Production migration target:

```text
ONE PRODUCTION STRATEGY AUTHORITY PATH
```

Strategy Intelligence is promoted only as evidence / semantic / lifecycle
context. It must not become order intent, target-weight, quantity, Runtime
mapping, or Safety authority. Replaced legacy consumers, fallbacks, schemas,
configs, tests, and durable docs must be retired under the Legacy Retirement
Contract after their Production reference count is zero.

## 6. Core Model

The model is:

```text
Eligibility / Disqualifying Facts
        ↓
Continuation Quality
        ↓
Downside Risk
        ↓
Expected Edge / Opportunity Cost
        ↓
Action-specific interpretation
        ↓
Portfolio Construction / PM
```

These concepts must remain semantically distinct.

### Eligibility

Eligibility answers:

```text
Is this security suitable and sufficiently authoritative to evaluate?
```

Eligibility handles authoritative facts, not probabilistic price outcomes.

### Continuation Quality

Continuation Quality answers:

```text
How healthy and persistent is the current upward continuation thesis?
```

It is not raw momentum, BUY Quality, rank, profit, or cash availability.

### Downside Risk

Downside Risk answers:

```text
How exposed is this candidate or position to material adverse movement,
failure, or thesis deterioration from the current PIT state?
```

It is probabilistic unless backed by a hard disqualifying fact.

### Expected Edge

Expected Edge answers:

```text
Is marginal capital economically justified here versus alternatives, including
Cash, after considering continuation opportunity, payoff potential, downside
risk, confidence, horizon, and turnover?
```

Expected Edge is not currently calibrated expected return.

## 7. Eligibility / Event Layer

The Eligibility layer separates:

```text
DISQUALIFYING_FACT
```

from:

```text
PROBABILISTIC_RISK
```

Disqualifying or review-required fact categories:

- unsupported security type
- no valid listing / product authority
- trading restriction
- supervision / alert / special caution status where source authority exists
- delisting pending or authoritative delisting risk
- unresolved corporate action that affects price/quantity basis or tradability
- TOB / material event where supported
- hard liquidity or tradability failure
- malformed or missing required authority

Probabilistic risk examples:

- high volatility
- short-term reversal after strong prior momentum
- weak participation
- microstructure fragility
- regime stress
- event coverage uncertainty

A probabilistic risk must not silently become a hard block. It may reduce edge,
reduce allocation, trigger BUY_WAIT, prevent ADD, or create PM risk evidence,
depending on consumer interpretation.

Event risk contract:

| Category | Semantics | Missing behavior |
|---|---|---|
| Authoritative event fact | Fact or review state from approved source | fail closed if required |
| Coverage authority | Whether the event source covers this class/date | missing coverage is uncertainty, not safe |
| Event uncertainty | Probabilistic risk caused by missing/stale/partial event source | feed downside risk and review evidence |

If J-Quants does not provide alert/supervision/delisting-warning/TOB coverage
for a class, the data foundation must record that gap. Missing event data must
not be converted to `SAFE`.

## 8. Continuation Quality Contract

Continuation Quality should be a structured PIT evidence object, not an opaque
scalar.

Conceptual schema:

```text
continuation_quality:
  schema_version
  as_of_business_date
  symbol
  status
  trend_health
  persistence
  acceleration_state
  exhaustion_risk
  participation_quality
  relative_strength
  regime_compatibility
  evidence_sufficiency
  missing_inputs
  confidence
  provenance
  future_information_used: false
```

Dimensions:

| Dimension | Meaning | Candidate PIT sources | Missing behavior | Consumers |
|---|---|---|---|---|
| Trend Health | Whether current price structure supports the upward thesis | adjusted OHLCV, MA state, trend features | insufficient if bars unavailable | BUY_NEW, ADD, HOLD |
| Persistence | Whether multi-horizon strength is steady rather than one-day spike | 1D/3D/5D/10D/20D/60D momentum | degrade confidence | BUY_NEW, REENTRY, ADD |
| Acceleration / Deceleration | Whether move is improving, stable, or fading | momentum deltas, trajectory metadata | degrade confidence | BUY_WAIT, ADD stop, PM |
| Exhaustion / Reversal | Whether prior strength is turning into failure risk | strong prior plus negative short returns, distance from MA, gaps | feed downside risk too | BUY_WAIT, REDUCE/EXIT evidence |
| Participation | Whether volume/traded value confirms price move | volume ratio, traded value, abnormal volume | explicit weak/unknown | BUY_NEW, ADD, HOLD |
| Relative Strength | Stock versus market/sector if source exists | market context, sector if available | data prerequisite if sector absent | Opportunity comparison |
| Regime Compatibility | Whether stock thesis fits current regime | market_context regime and transition state | require current regime authority | all consumers |

Normalization:

- No Phase30-I production thresholds are frozen.
- Each dimension may expose ordinal semantic states such as `SUPPORTIVE`,
  `MIXED`, `WEAK`, `INSUFFICIENT`, plus raw evidence fields.
- Scores may exist later, but raw evidence and semantic state must remain
  auditable.

## 9. Downside Risk Contract

Downside Risk is separate from Continuation Quality.

Conceptual schema:

```text
downside_risk:
  schema_version
  as_of_business_date
  symbol
  status
  reversal_risk
  volatility_risk
  exhaustion_risk
  participation_risk
  microstructure_risk
  regime_risk
  event_uncertainty
  evidence_sufficiency
  missing_inputs
  confidence
  provenance
  future_information_used: false
```

Dimensions:

| Dimension | Meaning | Phase30 evidence | Interpretation |
|---|---|---|---|
| Reversal Risk | Strong prior move followed by short-term negative structure | best narrow failure signature | candidate BUY_WAIT / edge reduction / PM risk |
| Volatility Expansion | Adverse movement likelihood and path instability | broad veto removes Winners | probabilistic, not single-factor block |
| Exhaustion Risk | Recent move may be late-stage rather than continuation | 78780-type issue | CQ deterioration plus downside risk |
| Participation Weakness | Price move lacks volume/traded-value support | underconsumed feature | edge confidence reduction |
| Microstructure Risk | Low price, tick ratio, lot notional, gap/liquidity fragility | low-price cap is not enough | sizing/risk input, avoid double penalty |
| Regime Risk | Current/transition regime makes signal less reliable | BEAR/CORRECTION noisy | regime-conditioned interpretation |
| Event Uncertainty | Source unavailable/stale/incomplete | 93180-type gap | uncertainty/review, not safe |

Probabilistic risk accumulation is required. The design must avoid broad
one-factor vetoes such as "high volatility -> reject."

## 10. Expected Edge Contract

Expected Edge is an interpretable decision contract:

```text
Expected Edge
  = continuation opportunity
  + payoff potential
  - downside risk
  - opportunity cost
```

This is conceptual, not a required linear formula.

Conceptual schema:

```text
expected_edge:
  schema_version
  as_of_business_date
  symbol
  status
  edge_contract: EXPECTED_EDGE_RESEARCH_CONTRACT
  calibration_status: UNCALIBRATED
  continuation_opportunity
  payoff_asymmetry
  downside_distribution_proxy
  confidence
  intended_horizon
  opportunity_cost_context
  turnover_consideration
  incremental_edge_for_add
  relative_edge_for_hold_vs_replacement
  provenance
  future_information_used: false
```

The first implementation generation must not call this calibrated expected
return. Formal calibration requires a later gate with time-respecting training,
stable horizon definitions, regime behavior, uncertainty, opportunity-cost
semantics, turnover effects, and no Historical result leakage.

## 11. runtime_opportunity_score Migration

`runtime_opportunity_score` remains:

```text
uncalibrated_relative_model_score
```

It must not be interpreted as expected return.

Migration role:

| Use | Phase30-I design |
|---|---|
| Delete score | Rejected. Existing consumers and evidence continuity matter. |
| Expected return | Rejected until explicit calibration. |
| Ranking evidence | Allowed. It may remain relative model/rank evidence. |
| Continuation Quality input | Allowed only as a model-derived supporting signal with raw PIT provenance and no economic units. |
| Expected Edge input | Allowed only as uncalibrated opportunity evidence, never as direct JPY/return expectation. |
| Shadow legacy evidence | Required during migration. |

Downstream artifacts must carry semantic metadata:

```text
score_semantics: uncalibrated_relative_model_score
calibration_applied: false
economic_units_available: false
```

## 12. Artifact Architecture Choice

Phase30-I chooses a unified Strategy Intelligence artifact with separated
sections.

Preferred durable artifact:

```text
strategy/strategy_intelligence.json
```

Rationale:

- one as-of boundary for CQ, downside, expected-edge, and event uncertainty,
- simpler lifecycle consumption by BUY and PM,
- less synchronization risk than three separate daily artifacts,
- semantic sections prevent monolith behavior if schemas remain distinct.

Rejected as first slice:

```text
strategy/continuation_quality.json
strategy/downside_risk.json
strategy/expected_edge.json
```

Separate artifacts may be introduced later if independent ownership becomes
necessary. For the first migration, synchronization risk is more dangerous than
section-level complexity.

Required top-level sections:

```text
strategy_intelligence:
  metadata
  eligibility_event_facts
  symbol_intelligence:
    <symbol>:
      continuation_quality
      downside_risk
      expected_edge
      current_decision
      lifecycle_context
      profit_protection_evidence
      strategy_intelligence_interpretation
      provenance
  run_level_sufficiency
  shadow_decision_comparison
```

Phase30-P promotes `strategy_intelligence_interpretation` to Production evidence
semantics. It preserves BUY_WAIT, ADD / BUY_ADD, PM REDUCE, and PM EXIT context
instead of collapsing them into generic BUY_NEW or HOLD wording. The former
backward-compatible `proposed_decision_if_authorized` alias is retired and must
not be used as a shadow action path.

Phase30-N clarifies Current / Campaign authority:

- Current / PM current-position adapter owns current position state: quantity,
  average price, market value, quantity basis, valuation price basis, and
  valuation-facing state.
- `positions/position_campaigns.json` is the canonical campaign identity and
  lifecycle-history authority.
- Strategy Intelligence joins these authorities; it does not create a second
  campaign ledger.
- ADD and partial SELL / REDUCE preserve the same canonical campaign identity.
- EXIT may use the canonical same-day closed campaign for EXIT-day lifecycle
  context, but the closed campaign is not treated as an open current holding on
  later days.
- REENTRY follows the existing campaign authority: a new open campaign identity
  is used when the canonical campaign file creates one; prior closed campaign
  MFE/giveback must not be inherited as current-campaign state.

## 13. Artifact Metadata

Any Strategy Intelligence artifact must include:

- schema version
- semantic version
- as-of business date
- generated_at
- PIT boundary
- producer
- source evidence references
- evidence sufficiency
- missing inputs
- confidence / quality status
- `future_information_used = false`
- symbol-level provenance
- accepted generation references where model output is consumed
- event coverage authority status

## 14. Lifecycle Consumers

The same shared evidence is consumed differently by each lifecycle decision.

### BUY_NEW

BUY_NEW should reason:

```text
Eligibility PASS
+ Continuation Quality
+ Downside Risk
+ Expected Edge / Opportunity Comparison
+ Portfolio constraints
```

It must not merely reward high historical momentum.

Conceptual decision matrix:

| CQ | Downside Risk | Edge | Interpretation |
|---|---|---|---|
| strong | manageable | attractive | BUY_NEW candidate |
| strong | elevated | attractive but uncertain | reduced allocation / review / shadow inspect |
| mixed | low | attractive | possible reduced allocation or wait for confirmation |
| mixed | high | unclear | BUY_WAIT or reject depending on evidence sufficiency |
| weak | high | any | reject or BUY_WAIT if thesis not invalid but timing poor |
| insufficient | any | any | fail closed or no decision if required evidence missing |

78780/67310/93180-type issues are handled as classes:

- exhaustion/reversal after strong move,
- high volatility plus negative short structure,
- event/microstructure uncertainty.

No anecdote-specific symbol rules are permitted.

### BUY_WAIT

BUY_WAIT remains:

- temporary,
- non-Pending,
- automatically re-evaluated next business day,
- independent from SELL authority,
- not applicable to existing-position SELL continuity.

BUY_WAIT should represent:

```text
continuation thesis not invalid, but current entry timing or evidence
sufficiency is not good enough for BUY_NEW today
```

FADING, OVERHEAT, strong-prior-short-reversal, unresolved trajectory, and event
uncertainty may feed BUY_WAIT, reduced sizing, or edge reduction depending on
the decision matrix. Phase30-I freezes no thresholds.

### ADD

ADD must answer:

```text
Is additional capital still justified now, relative to existing exposure,
downside risk, and alternatives?
```

ADD decision matrix:

| Incremental CQ | Downside Risk | Incremental Edge | Interpretation |
|---|---|---|---|
| strengthening | manageable | attractive | ADD candidate |
| healthy but flat | manageable | marginal | HOLD, no ADD |
| decelerating | any | marginal/weak | ADD stop |
| strong but high risk | elevated | attractive | possible small ADD only if PC/sizing confirms; shadow first |
| weak/breaking | high | any | no ADD; PM deterioration evidence |

### REENTRY

REENTRY is preserved. It is not blanket-banned.

REENTRY should distinguish:

```text
genuine recovery
```

from:

```text
churn / unresolved continuation
```

Cooldown and recovery hurdle remain. Continuation Quality refines recovery
confirmation; it does not erase semantic REENTRY.

### HOLD

HOLD means:

```text
If evaluated today from current PIT information, the position still has
sufficient continuation merit to justify keeping capital deployed here.
```

HOLD is not "not weak enough to sell."

HOLD-worthiness differs from ADD-worthiness:

| CQ health | Deterioration | Interpretation |
|---|---|---|
| healthy | none | HOLD; ADD may be evaluated separately |
| healthy | modest risk rise | HOLD; stop ADD |
| still positive | decelerating | HOLD with profit-protection watch |
| weak | material deterioration | REDUCE evidence |
| broken | thesis invalid | EXIT evidence |

Existing holdings must not be forced mechanically through BUY_NEW eligibility.
Hard tradability or corporate-action facts still apply via authoritative
fact/review layers.

### Profit Protection

Profit Protection is evidence, not an action authority.

It should consider PIT-safe facts:

- accumulated embedded profit,
- observed campaign high-water state,
- current observed MFE,
- drawdown from observed peak,
- CQ deterioration,
- Downside Risk increase,
- regime deterioration.

Future MFE/MAE is prohibited. Current MFE based on prices observed up to today
is PIT-safe.

Profit Protection matrix:

| Observed profit state | CQ deterioration | Downside Risk | Interpretation |
|---|---|---|---|
| low/none | none | manageable | normal HOLD/EXIT reasoning |
| meaningful | none | manageable | HOLD; no profit-taking rule |
| meaningful | decelerating | rising | profit protection evidence; stop ADD |
| large | material | high | REDUCE evidence |
| any | thesis broken | severe | EXIT evidence |

### REDUCE / EXIT

Lifecycle interpretation:

```text
HEALTHY
  -> HOLD / ADD candidate

still positive but decelerating
  -> HOLD / ADD stop

material deterioration
  -> Profit Protection / REDUCE evidence

thesis materially broken
  -> REDUCE / EXIT evidence
```

Design protections:

- no automatic REDUCE -> EXIT,
- no premature Winner exit from profit alone,
- no SELL suppression because BUY state is Pending/Review,
- no CQ evidence becoming PM action authority.

Phase32-BQ preserves these protections while allowing one explicit production materialization exception. A PM `REDUCE` that is unexecutable specifically because of discrete-lot granularity may be reconsidered as `PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT` only when same-date PIT Strategy Intelligence plus market context reproduce the BO `SHADOW_FULL_EXIT` semantics. Profit cushion remains contextual profit-protection evidence: it can contribute to `PROFIT_AT_RISK` when continuation deteriorates, but it is not standalone HOLD authority and it does not create an automatic REDUCE-to-EXIT rule.

## 15. Capital Concentration

Target behavior:

```text
new candidate proves strong forward merit
  -> initial BUY

thesis remains strong
  -> HOLD

incremental edge strengthens
  -> ADD

winner continues
  -> allow capital concentration within Strategy/Safety limits

continuation deteriorates
  -> stop ADD

profit at risk
  -> PM profit-protection / REDUCE evidence

thesis breaks
  -> EXIT
```

No forced concentration. No fixed number of positions. No forced full exposure.
Cash remains a legitimate alternative.

## 16. Opportunity Cost

Expected Edge must compare:

```text
existing holding
new BUY candidate
ADD candidate
Cash
```

The marginal JPY should be deployed only where relative economic merit is
positive after risk, confidence, turnover, and opportunity cost. A noisy
slightly-higher candidate score must not force selling an existing Winner.

## 17. Shared Evidence Is Not Shared Action Authority

This is a closed boundary:

```text
Shared intelligence != Shared action authority
```

Continuation Quality, Downside Risk, and Expected Edge may be shared evidence.
They must not directly emit BUY_NEW, ADD, HOLD, REDUCE, or EXIT actions.

PM remains existing-position directional Action Authority. Portfolio
Construction remains Target Portfolio Decision Authority. Safety remains
guardrail authority. Runtime Planning remains mapper.

## 18. Persistence / Current Boundary

Default:

```text
market-derived Strategy Intelligence is recomputed daily from PIT data
```

It should not become stale Current truth.

Campaign-relative state may require persistence:

- entry thesis metadata,
- observed campaign high-water price and date,
- current observed MFE / giveback state,
- ADD history,
- prior CQ state descriptor,
- deterioration transition timing.

If persisted, ownership must be:

| State | Owner | Update rule |
|---|---|---|
| Current position and lots | Current/Ledger authority | execution/valuation contracts |
| Campaign high-water observations | Campaign/Current state producer | daily PIT observed price only |
| Entry thesis metadata | Strategy evidence at entry, copied with provenance | immutable except versioned annotation |
| Prior CQ descriptor | Strategy Intelligence producer or campaign evidence | daily recompute plus optional prior snapshot |

No persisted intelligence may override fresh PIT recomputation.

## 19. Regime-Conditioned Interpretation

Regime fields:

```text
regime
regime_transition_state
regime_compatibility
```

They must use PIT market context only. Future regime is prohibited.

Phase30-H found BULL/RANGE/RECOVERY separation was useful, while
BEAR/CORRECTION rebound optionality complicates broad risk interpretation.
Therefore the design supports regime-conditioned interpretation but freezes no
per-regime thresholds.

## 20. Relative Strength

Required transparent evidence where data exists:

- stock vs market,
- stock vs sector,
- sector vs market.

If sector data is unavailable or not production-authoritative, the artifact
must declare:

```text
relative_strength_status: DATA_FOUNDATION_INSUFFICIENT
```

Do not fabricate sector data.

## 21. Volume / Participation

Volume and participation must become explicit evidence, not incidental feature
data.

Candidate fields:

- volume trend,
- traded-value confirmation,
- abnormal volume,
- price-volume divergence,
- liquidity capacity.

No arbitrary volume threshold is frozen in Phase30-I. Missing or stale volume
evidence degrades confidence or sufficiency.

## 22. Low-Price / Microstructure

Do not introduce a hard minimum stock price in Phase30-I.

Microstructure risk should influence:

- Downside Risk,
- Position Sizing,
- PC low-price allocation cap,
- Eligibility only when there is a true hard tradability/liquidity failure.

Inputs:

- absolute price,
- tick/price ratio,
- lot notional,
- traded value,
- liquidity capacity,
- gap behavior,
- volatility.

The design must avoid double penalization. If PC allocation cap already reduces
capacity, Downside Risk should record the same source provenance so sizing does
not unknowingly penalize twice.

## 23. Winner Preservation Contract

Future Strategy Intelligence changes must report:

- severe losers avoided,
- healthy Winners removed,
- missed MFE,
- average/median forward return,
- MAE reduction,
- MFE preservation,
- turnover impact,
- exposure impact,
- concentration impact.

No design is approved solely because it lowers MAE.

Broad risk veto is explicitly rejected because Phase30-H showed it removes too
many healthy Winners.

## 24. Leakage Firewall

Runtime / Production Strategy must never consume:

- future return,
- future price,
- future MFE,
- future MAE,
- final campaign outcome,
- Historical result,
- Paper Ledger performance,
- selected/bought future outcome,
- future regime,
- audit judgment,
- test result,
- final return.

Offline research may use these only as labels.

## 25. Shadow Migration

Before Production authority migration, the system must be able to record for
the same PIT state:

```text
CURRENT_DECISION
PROPOSED_INTELLIGENCE_EVIDENCE
STRATEGY_INTELLIGENCE_INTERPRETATION
```

Strategy Intelligence logic must call the same Production-common evidence
producer. It must not become `strategy_v2_historical_only` or a permanent
parallel stack.

Required shadow comparisons:

- 78780-type exhaustion/reversal entries,
- 67310-type high volatility plus negative short structure,
- 93180-type event/microstructure uncertainty,
- healthy Winners,
- REENTRY,
- ADD,
- HOLD,
- giveback,
- REDUCE/EXIT.

Case studies cannot alone approve migration.

## 26. First Implementation Slice

Recommended first slice:

```text
Phase30-J — Strategy Intelligence Shadow Evidence Producer
```

Scope:

- create shared `strategy/strategy_intelligence.json` in shadow-only mode,
- populate Eligibility/Event coverage status, Continuation Quality, Downside
  Risk, and Expected Edge research contract sections from PIT-safe existing
  inputs,
- record current decision and proposed-if-authorized interpretation,
- no production decision influence,
- no Strategy thresholds frozen,
- no Runtime behavior change.

This maximizes observability and minimizes behavioral blast radius.

## 27. Production Authority Migration Gate

Shadow evidence may become Production decision authority only after:

1. schema stable,
2. PIT lineage proven,
3. no future leakage,
4. multi-day persistence proven,
5. Winner Preservation evaluation passed,
6. severe-loss reduction evidence proven,
7. closed-contract regression PASS,
8. shadow/current decision comparison understood,
9. Production-common execution path proven,
10. no Historical-only behavior.

Phase30-I does not approve migration.

## 28. Phase30-V Entry Admission And Quality-Adjusted One-Lot Design

Phase30-V adds a design amendment for Production-common repair of:

```text
Entry Intelligence Gap
One-Lot Capital Concentration Gap
```

This amendment is design-only. It does not authorize implementation, threshold
tuning, model retraining, Accepted Generation changes, Safety weakening, or
Historical outcome fitting.

### Entry Admission

BUY-side consumers need an entry-specific semantic interpretation of existing
Strategy Intelligence evidence. The purpose is to distinguish:

```text
strong trend / raw momentum
```

from:

```text
healthy forward continuation entry
```

Conceptual contract:

```text
entry_admission:
  lifecycle_intent: BUY_NEW | REENTRY | BUY_ADD
  entry_state
  admission_action
  allocation_quality_bias
  buy_wait_eligible
  evidence_sufficiency
  reason_codes
  future_information_used: false
```

Initial semantic states:

```text
HEALTHY_CONTINUATION_ENTRY
CONTINUATION_WITH_CAUTION
OVERHEATED_DECELERATING_ENTRY
REVERSAL_RISK_ENTRY
INSUFFICIENT_ENTRY_EVIDENCE
```

The key interaction to expose is:

```text
strong medium-term trend
+ short-term reversal
+ deceleration
+ elevated exhaustion / reversal / volatility risk
```

This interaction may produce BUY_WAIT, reduced allocation, reject, or review
semantics depending on evidence sufficiency, participation, relative
opportunity, regime compatibility, and opportunity cost. It must not become a
single broad downside-risk veto.

### Quality-Adjusted One-Lot Admission

Existing lot-aware sizing and residual recycling are preserved, but Safety hard
cap feasibility is not sufficient proof that Strategy wants the concentration.

The repair design separates:

```text
Strategy desired allocation
minimum executable lot
effective one-lot post-trade weight
Strategy concentration tolerance
Safety hard cap
```

Conceptual contract:

```text
one_lot_admission:
  status: PASS | DEFER | FAIL_CLOSED | REVIEW_REQUIRED
  lifecycle_intent: BUY_NEW | BUY_ADD | REENTRY
  continuous_target_weight
  minimum_executable_weight
  effective_post_trade_weight
  overshoot_weight
  overshoot_ratio_to_target
  strategy_concentration_tolerance
  safety_hard_cap_preserved
  entry_state
  add_worthiness_state
  relative_opportunity_state
  opportunity_cost_state
  residual_destination_if_skipped
  reason_codes
  future_information_used: false
```

For BUY_NEW / REENTRY with current quantity zero, Portfolio Construction may
also materialize a narrow `minimum_executable_one_lot_authority` when all
guards pass and the continuous positive PC target is below one executable
Japanese round lot. This authority is limited to `0 -> 1lot`; it does not apply
to BUY_ADD or second-lot-plus expansion.

```text
minimum_executable_one_lot_authority:
  authority_type: PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION
  decision: ADMIT
  reason: MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED
  intent: BUY_NEW | REENTRY
  current_quantity: 0
  original_pc_target_weight
  one_lot_weight
  target_to_one_lot_ratio
  projected_one_lot_portfolio_weight
  strategy_cap
  safety_cap
  final_promoted_target_weight
  ps_final_quantity
  future_information_used: false
```

Position Sizing may consume this authority only after PC has explicitly
promoted the final target weight. PS must not independently round a positive
sub-lot target up to one lot.

If one lot modestly exceeds Strategy target, admission may pass only when
quality and opportunity evidence justify the overshoot. If one lot extremely
exceeds Strategy target, Safety pass alone must not authorize capital
concentration.

### Residual Recycling And Cash

Phase29 residual recycling remains valid, but the recycling queue should become
quality-adjusted. Skipped/deferred capital may move to the next executable
BUY_NEW, BUY_ADD, or REENTRY candidate only when Production evidence supports
the marginal JPY. Otherwise Cash is a valid result.

```text
Cash < bad concentration
```

No forced investment, forced BUY count, or forced exposure target is introduced.

### ADD Preservation

HOLD-worthy and ADD-worthy remain distinct:

```text
HOLD-worthy != ADD-worthy
```

ADD requires incremental continuation quality, downside risk, opportunity cost,
existing exposure, lot feasibility, and no-loss-averaging evidence. Surviving a
campaign is not enough to authorize ADD.

### Authority Boundary

Strategy Intelligence may produce entry and one-lot interpretation evidence.
Portfolio Construction remains allocation and Strategy concentration authority.
Position Sizing remains executable quantity authority. Safety remains hard
guardrail authority. BUY-side repair must not change SELL / REDUCE / EXIT
authority or suppress SELL independence.

## 29. Phase30-W Implementation Status

Phase30-W implemented the Phase30-V design as a Production-common repair.

Implemented surfaces:

- `strategy/strategy_intelligence.json` semantic version `1.3.0` now
  materializes `entry_admission` per symbol.
- Portfolio Construction consumes `entry_admission` as BUY-side evidence and
  may map overheated / reversal / insufficient timing states to BUY_WAIT,
  reduced allocation, reject, or review semantics.
- Lot-aware final reallocation now materializes `one_lot_admission` and uses it
  before accepting Strategy soft-cap one-lot overshoot.
- Phase30-AK2 extends the same production one-lot path with
  `minimum_executable_one_lot_authority` for BUY_NEW / REENTRY `0 -> 1lot`
  only, preserving Strategy/Safety caps and PC/PS authority separation.
- Residual recycling remains active and now orders candidates by
  quality-adjusted entry / ADD evidence before priority and symbol tie-breaks.
- ADD and HOLD remain distinct; `NO_ADD` or failed ADD evidence can block a
  one-lot ADD overshoot while preserving the existing position baseline.

Preserved boundaries:

```text
NEW_AI_CREATED = NO
PRODUCTION_MODEL_RETRAINED = NO
ACCEPTED_GENERATION_CHANGED = NO
Expected Edge = UNCALIBRATED
SELL / REDUCE redesign = NO
Safety hard cap weakened = NO
forced investment = NO
forced exposure = NO
```

The implementation does not add symbol/date hard-codes and does not use
Historical outcomes as Runtime input or production parameter selection.

## 30. Phase30-Z REENTRY Genuine Recovery Authority

Phase30-Z tightens REENTRY authority without changing BUY_NEW, ADD, HOLD,
REDUCE, EXIT, Safety, model weights, Accepted Generation, or Expected Edge
calibration.

REENTRY remains allowed, but only when the prior campaign can be identified and
the previous EXIT cause is available with sufficient semantic context. A generic
`EXIT`, `SELL`, empty, or `UNKNOWN` prior reason is not evidence of genuine
recovery and must fail safe to review / wait semantics.

Genuine recovery requires all of the following Production-common evidence:

- cooldown satisfied
- prior campaign identity materialized from PIT ledger / campaign authority
- prior EXIT cause available
- prior EXIT cause sufficiently resolved by current evidence
- current Continuation Quality acceptable when provided
- current Downside Risk acceptable when provided
- Entry Admission does not return BUY_WAIT / REJECT / REVIEW / NO_ADD
- repeated unresolved churn is suppressed using prior same-symbol campaign
  history, not historical PnL outcomes

Recovery must match the prior EXIT cause. Trend or momentum alone is not enough
for a trend / momentum / hard-stop / corporate-action recovery. Trend recovery
requires trend evidence and momentum confirmation. Reversal / overheated exits
require current Entry Admission normalization. Portfolio-competition exits
require renewed relative opportunity strength.

Expected Edge remains:

```text
UNCALIBRATED
```

`runtime_opportunity_score` / Expected Edge is diagnostic-only for REENTRY and
is not converted into an optimized hard rejection threshold. Negative diagnostic
edge can coexist with genuine recovery when prior cause, CQ, risk, entry timing,
technical recovery, opportunity rank, quality, capacity, and corporate-action
evidence all pass.

## 31. Phase30-AB Canonical Campaign Lifecycle / HOLD-ADD Repair Design

Phase30-AB promotes campaign lifecycle connection from an underused evidence
surface to a Production-common pre-action requirement. The canonical campaign
authority remains:

```text
positions/position_campaigns.json
```

The artifact must be available to the pre-action Strategy path before Strategy
Intelligence, Position Management, Portfolio Construction, and Position Sizing
consume it. Strategy Intelligence joins campaign truth; it does not own a
second campaign ledger.

Required pre-action lifecycle facts include `position_campaign_id`, opened
business date, campaign age, ADD history, REDUCE history, entry thesis/state,
observed MFE, observed giveback, and current campaign-relative return. These
facts must be produced from Ledger executions known before the decision cut,
Current / valuation state available at decision time, and PIT market prices.
Same-day future execution, EOD-only reconstruction, future MFE / MAE, final
campaign outcome, Historical outcome, and audit results are prohibited runtime
inputs.

HOLD remains a PM action. Strategy Intelligence may provide HOLD-worthiness
evidence using campaign age, current return, observed MFE/giveback, CQ
deterioration, Downside Risk rise, Relative Strength, ADD/REDUCE history, and
Profit Protection evidence. Missing canonical campaign authority for an open
held position must be explicit insufficiency or review evidence.

ADD remains distinct from HOLD:

```text
HOLD-worthy != ADD-worthy
```

ADD-worthiness requires incremental CQ, current risk, Relative Strength,
campaign maturity, observed MFE/giveback, prior ADD history, current exposure,
opportunity cost, no-loss-averaging, and one-lot feasibility. Weak survivors
must not receive additional capital merely because the campaign is still open;
long campaign age alone is not ADD authority.

Profit Protection remains evidence, not a fixed take-profit rule. PM may consume
embedded return, observed MFE, observed giveback, deterioration connection, and
risk-rise connection, while SELL / REDUCE / EXIT authority stays in PM and is
not redesigned by this lifecycle repair.

Legacy campaign adapters, EOD-only pre-action proxies, broad HOLD/ADD
heuristics, and duplicated lifecycle state must be migrated to this single
canonical path and then removed once reference counts are zero:

```text
DUPLICATE_CAMPAIGN_AUTHORITY = NO
LEGACY_CAMPAIGN_FALLBACK_REFERENCE_COUNT = 0
OBSOLETE_HOLD_ADD_HEURISTIC_REFERENCE_COUNT = 0
ONE_PRODUCTION_CAMPAIGN_LIFECYCLE_PATH = YES
```

## 32. Phase30-AC Implementation Status

Phase30-AC implements the Phase30-AB lifecycle repair in the Production-common
path.

Implementation status:

```text
PHASE30_AC_CAMPAIGN_LIFECYCLE_HOLD_ADD_WINNER_AMPLIFICATION_REPAIR_IMPLEMENTED
ONE_PRODUCTION_CAMPAIGN_LIFECYCLE_PATH = YES
DUPLICATE_CAMPAIGN_AUTHORITY = NO
```

The Strategy shadow / Production evidence chain now materializes
`positions/position_campaigns.json` for the pre-action decision point from the
latest prior canonical campaign snapshot and decision-time Current state. The
artifact records temporal safety flags and explicitly rejects same-day EOD
campaign reconstruction, future execution, future MFE/giveback, Historical
outcome, and test/audit inputs as Runtime evidence.

Phase30-AD1 completes fresh-run campaign continuity. When a decision-time
Current position has no prior canonical open campaign, the pre-action
materializer may bootstrap a new open campaign only from strict-prior completed
Ledger executions that prove an open BUY campaign before the current decision
business date. Same-day executions, same-day EOD reconstruction, future prices,
future MFE/giveback, Historical outcome, and test/audit judgments remain
forbidden. If strict-prior Ledger cannot prove the open campaign, the held
position remains explicit missing campaign authority and downstream consumers
fail closed.

Campaign lifecycle semantics remain single-owner:

- `BUY_NEW` with no prior open quantity creates one deterministic canonical
  `position_campaign_id` in `positions/position_campaigns.json`.
- Additional BUY executions while the ledger campaign is open are ADD evidence
  on the same campaign, not a new campaign.
- Partial SELL / REDUCE keeps the same campaign open and records REDUCE /
  SELL history.
- Full EXIT closes the same campaign.
- REENTRY after a ledger-proven full EXIT starts a new deterministic campaign
  identity under the same canonical authority.

Phase31-G122 clarifies the ADD event-history materialization contract:

- Initial BUY starts the campaign and is counted in `buy_history_summary`.
- A later ledger-proven BUY while the same ledger campaign is still OPEN is a
  BUY_ADD event on the same `position_campaign_id`.
- BUY_ADD must append a canonical BUY event to `events`, increment
  `buy_history_summary`, and increment `add_history_summary`.
- `buy_history_summary` counts all BUY executions in the campaign.
- `add_history_summary` excludes the initial BUY and counts only additional BUY
  executions while the campaign is already open.
- Quantity increase alone must not synthesize ADD; canonical strict-prior
  execution / ledger evidence is required.
- Materialization is idempotent: the same execution must not append duplicate
  events or double-increment summaries.
- Event ordering is deterministic chronological execution order.
- A BUY after the symbol was flat following a ledger-proven EXIT remains REENTRY
  / new campaign identity and must not be merged into the prior closed campaign.

Strategy Intelligence consumes canonical campaign state and exposes campaign
age, campaign-relative return, observed MFE, observed giveback, and campaign
history summaries. Missing campaign identity for an open held position is
explicit missing authority, not silent partial fallback.

Position Management consumes structured HOLD / ADD / Profit Protection evidence
while remaining Action Authority. Portfolio Construction consumes campaign-aware
ADD-worthiness fields for winner amplification and residual reallocation while
remaining allocation authority. Position Sizing remains quantity authority and
Safety remains guardrail authority.

Legacy PM/current lifecycle campaign authority, status-only HOLD heuristics,
CQ-only ADD heuristics, and Current-only MFE/giveback assumptions are retired
from code and tests. Reference counts for the retired Strategy campaign /
HOLD-ADD authority strings are zero.

## 33. Phase30-AH Selection Quality / Opportunity Capture Repair Design

Phase30-AH designs a Production-common repair for the Selection Coverage gap
confirmed by Phase30-AG. It does not create a new AI, retrain a model, add a
parallel Selection engine, change Runtime authority, force exposure, or tune
thresholds from Historical outcomes.

The existing Selection chain remains canonical:

```text
Market Universe
-> Candidate Generation
-> Opportunity Ranking
-> BUY Quality / Strategy Intelligence
-> Entry Admission
-> Portfolio Construction
-> Position Sizing
-> Runtime Planning
```

The repair introduces a shared Selection Quality Comparator vocabulary as
evidence consumed by existing components:

```text
HIGH_QUALITY_CONTINUATION
VALID_CONTINUATION
CAUTION_CONTINUATION
INSUFFICIENT_QUALITY
REJECT
```

The comparator uses existing PIT evidence:

- 5D / 20D trend structure;
- MA5 / MA20 structure;
- momentum acceleration / deceleration;
- Continuation Quality;
- Relative Strength;
- Downside Risk;
- volatility;
- participation / volume;
- regime compatibility;
- Entry Admission;
- BUY Quality;
- opportunity rank / score as supporting evidence.

Opportunity rank remains valid evidence, but its role changes:

```text
OPPORTUNITY_RANK_ROLE = SUPPORTING
EXPECTED_EDGE_ROLE = UNCALIBRATED_SUPPORTING
```

`runtime_opportunity_score` remains an uncalibrated relative score and must not
be interpreted as expected return. `below_opportunity_top20` and
`non_positive_expected_edge_score` may remain soft relative reasons, but they
must not be the sole hard rejection authority for a high-quality PIT
opportunity while Expected Edge is uncalibrated.

Portfolio Construction remains target portfolio and allocation authority. The
quality comparator may allow high-quality or valid continuation candidates into
PC competition, but it must not bypass Entry Admission, Downside Risk,
concentration, opportunity cost, ADD-worthiness, capital constraints, broker
eligibility, corporate-action authority, one-lot admission, Position Sizing, or
Safety hard guardrails.

Market Context remains posture and confidence evidence. Market-level caution may
reduce allocation or confidence, but it must not automatically suppress an
individual opportunity with supportive Relative Strength, healthy Continuation
Quality, contained Downside Risk, and healthy Entry Admission. This is not a
risk bypass; any hard blocker still wins.

Position Sizing remains executable quantity authority. The comparator and PC do
not override lot constraints. PC-positive to PS-zero outcomes must be classified
using explicit reasons such as:

```text
GENUINE_LOT_INFEASIBILITY
MINIMUM_MEANINGFUL_NOTIONAL
CONCENTRATION_HEADROOM_LIMIT
ZERO_INCREMENTAL_TARGET
RESIDUAL_CAPITAL_TOO_SMALL
QUALITY_DEFERRED_TO_CASH
```

Cash remains a valid allocation. BUY_NEW, BUY_ADD, genuine REENTRY, and Cash may
be compared using the shared quality vocabulary, but capital is deployed only
when quality, lifecycle, opportunity cost, PC, PS, Runtime, and Safety evidence
all support it.

Preserved:

```text
HOLD-worthy != ADD-worthy
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_AC_CAMPAIGN_LIFECYCLE_PRESERVED = YES
PHASE30_AD1_BOOTSTRAP_PRESERVED = YES
PHASE30_AE1_ADD_CONVERSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
SELL_REDUCE_EXIT_PRESERVED = YES
BUY_SELL_INDEPENDENCE = PASS
PHASE29_LOT_FIRST_RESIDUAL_RECYCLING_PRESERVED = YES
SAFETY_HARD_GUARDRAILS_PRESERVED = YES
ONE_PRODUCTION_SELECTION_PATH = YES
```

Legacy retirement target:

- keep Market Universe / Eligibility, Entry Admission, PC authority, PS
  authority, Runtime mapper, Safety hard guardrails;
- modify Candidate Top50 coverage evidence, Opportunity rank consumption, BUY
  Quality consumption, CQ / RS / Risk action-effectiveness, and Market Context
  individual-quality interaction;
- deprecate score-only hard rejection from `below_opportunity_top20` and
  `non_positive_expected_edge_score`;
- remove obsolete ranking fallback and duplicated quality-tier logic after
  migration reference counts reach zero.

## 34. Phase30-AI Selection Quality / Opportunity Capture Implementation

Phase30-AI implements the Phase30-AH design inside the existing
Production-common Strategy Intelligence -> Portfolio Construction -> Position
Sizing path. It does not add a parallel Selection engine, new model, threshold
tuning, forced exposure, Runtime authority change, or Historical outcome
feedback.

Strategy Intelligence now materializes
`selection_quality_comparator.v1` per symbol and
`selection_quality_comparator_summary.v1` at run level. The comparator emits:

```text
HIGH_QUALITY_CONTINUATION
VALID_CONTINUATION
CAUTION_CONTINUATION
INSUFFICIENT_QUALITY
REJECT
```

The comparator consumes only existing PIT evidence: trend, persistence,
acceleration, participation, Relative Strength, regime, Downside Risk, Entry
Admission, BUY Quality, and opportunity rank / score as supporting metadata.
Expected Edge remains:

```text
EXPECTED_EDGE_ROLE = UNCALIBRATED_SUPPORTING
```

Portfolio Construction consumes the comparator as allocation evidence. When
quality tiers are present, target-member competition prioritizes
`HIGH_QUALITY_CONTINUATION` before lower tiers, but this does not override Entry
Admission, BUY Quality wait/reject, hard Downside Risk, broker eligibility,
concentration, opportunity cost, ADD-worthiness, no-loss averaging, one-lot,
Position Sizing, Runtime Planning, or Safety.

`below_opportunity_top20` and `non_positive_expected_edge_score` remain
observable soft relative metadata while Expected Edge is uncalibrated. They are
not standalone hard BUY_NEW rejection authority for high-quality PIT
opportunities. Economic hard rejection remains allowed only when calibrated
economic units are explicitly available.

Position Sizing now materializes `pc_ps_zero_delta_taxonomy.v1` for resolved
zero-delta outcomes:

```text
GENUINE_LOT_INFEASIBILITY
MINIMUM_MEANINGFUL_NOTIONAL
CONCENTRATION_HEADROOM_LIMIT
ZERO_INCREMENTAL_TARGET
RESIDUAL_CAPITAL_TOO_SMALL
QUALITY_DEFERRED_TO_CASH
```

Cash remains a valid allocation result. `HOLD-worthy != ADD-worthy` remains
preserved, and BUY_NEW quality tier cannot authorize ADD without canonical
campaign, PM, PC, PS, and Runtime BUY_ADD continuity evidence.

Implemented invariants:

```text
ONE_PRODUCTION_SELECTION_PATH = YES
PARALLEL_SELECTION_PATH_CREATED = NO
PHASE30_AE1_ADD_CONVERSION_PRESERVED = YES
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
PHASE30_S_HANDOFF_PRESERVED = YES
EXPECTED_EDGE_STATUS = UNCALIBRATED
```

## 35. Phase31-G129 BUY_ADD Actual-Path Contract Amendment

BUY_ADD quantity authority is order-increment scoped at Submit. The canonical
order-increment field for G115/G119/G129 staged ADD is:

```text
pc_positive_executable_quantity_authority.final_allocated_quantity
```

For `semantic_type = BUY_ADD`, Submit validates the pending item quantity
against that order increment. Position-scope or cumulative fields such as
`executable_quantity_delta` and `preflight_executable_quantity_delta` may carry
larger stateful quantities and must not be treated as equivalent to the
submitted order increment unless their producer explicitly defines them as the
same authority. True mismatches between item quantity and canonical order
increment remain `REVIEW_REQUIRED`.

BUY_NEW and REENTRY retain the existing quantity contract. Submit continues to
fail closed for missing authority, malformed quantity, reserved/dynamic cash
violation, corporate-action quarantine, lot infeasibility, pending conflict,
and Safety/Data Readiness violations.

BUY_ADD fill materialization requires an actual BUY fill and canonical campaign
identity proof. A BUY fill may append to an existing open campaign only when
Runtime/Pending/PS lineage, the strict-prior ledger, or another canonical
action provenance field proves the open `position_campaign_id`. Same-symbol
quantity movement alone is not sufficient. A BUY after a flat / closed campaign
starts a new or re-entry campaign and must not be merged into the prior closed
campaign.

Market-Candidate-Cash interaction remains a capital pacing / Cash optionality
authority, not a blanket ADD evidence eraser. For ADD marginal competition,
canonical positive/PASS ADD investment evidence and PASS opportunity-cost
evidence must remain visible to the ADD-vs-Cash frontier. Missing, invalid, or
conflicting ADD evidence remains fail-closed, and Cash remains a first-class
allocation destination.

## 36. Phase31-G136 High-Resolution Capital Value Evidence Boundary

The permanent architecture SoT for future high-resolution marginal capital value
and portfolio-wide rotation is:

```text
docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md
```

Strategy Intelligence, Expected Edge, Entry Quality, PM continuation evidence,
and ADD investment evidence remain evidence producers unless a later accepted
SoT explicitly changes their authority mode. They must not independently emit
BUY_NEW, BUY_ADD, HOLD, REDUCE, EXIT, target weight, target notional, quantity,
Cash preference, or rotation actions.

Future high-resolution Capital Value may consume these evidence families to
evaluate the next executable capital increment, but it must preserve raw
evidence lineage and PIT / anti-leakage metadata. It must not use later return,
future price, campaign final outcome, MFE/MAE, Paper Ledger result, or
Historical profitability to select features, weights, thresholds, ranking
rules, or rotation rules.

## 37. Phase32-S PC-Owned Evidence-Tiered ADD Acceleration Contract

Portfolio Construction owns ADD acceleration tiering and continuous marginal
capital magnitude. Position Management remains the directional ADD intent owner;
Position Sizing remains the discrete executable quantity owner; Runtime remains
an exact consumer of the PS-bound order increment and must not redecide quantity.

The canonical PC ADD acceleration states are:

```text
NO_ACCELERATION
NORMAL_ADD
STRONG_ADD
EXCEPTIONAL_ADD
```

PC may produce `STRONG_ADD` or `EXCEPTIONAL_ADD` only from strict-prior,
already-materialized evidence: PM ADD, campaign/current-position authority PASS,
expected edge IMPROVING, incremental investment value POSITIVE, opportunity cost
PASS, no-loss averaging PASS, Buy Quality eligible, available cap/headroom,
Risk Pacing compatibility, Safety PASS, broker eligibility PASS, corporate
action PASS, and liquidity feasibility. Missing, UNKNOWN, conflicting, or
blocked authority remains fail-closed. CAUTIOUS / preserve-optionality Risk
Pacing may down-tier acceleration to normal ADD, but unknown Risk Pacing is not
compatible evidence.

Acceleration magnitude is derived from the existing PC incremental capital unit
and bounded by single-name cap, target gross exposure, available headroom, and
Risk Pacing. This contract does not introduce fixed lot multipliers and does not
select parameters from Historical PnL, future returns, future prices, future
regime, campaign final outcome, or MFE/MAE.

BUY_WAIT and explicit zero `quality_allocation_adjustment` keep incremental ADD
at zero. Reduced Buy Quality allocation can preserve normal ADD only; it cannot
re-expand into unrestricted strong/exceptional acceleration.

BUY_NEW, accepted REENTRY initial sizing, REDUCE, EXIT, Cash optionality, and
NEW / ADD / Cash competition remain separate authorities. Strong ADD can compete
for capital but does not automatically win. PS may convert the PC continuous
target into zero, one, or multiple 100-share lots under its existing discrete
feasibility authority.

## 38. Phase32-AR Accepted Graduation Baseline and Deferred Research Tracks

Phase32-AR durably records the Phase32-AQ accepted current specification:

```text
CURRENT_SPEC_ACCEPTED_WITH_DEFERRED_IMPROVEMENT_RESEARCH
```

The accepted current graduation baseline is:

```text
persistent eligibility + PC/PS/G129 per-order authority
```

This means ADD does not require a mandatory fresh-event or Production
Graduation Episode semantic. Persistent valid eligibility may remain observable,
but every actual BUY_ADD still requires existing Portfolio Construction
allocation authority, Position Sizing discrete quantity authority, and G129
order-increment Runtime / Submit authority.

Graduation consideration is not capital entitlement. Cash, NEW, Risk Pacing,
Buy Quality, no-loss averaging, concentration / headroom, lot feasibility,
prior ADD safeguards, Safety, broker, and corporate-action gates remain
authoritative. This section does not introduce a new Production state named
Graduation Episode and does not change Strategy, PM, SI, BQ, PC, PS, Runtime,
thresholds, weights, caps, or accepted artifacts.

Known current performance architecture limitation:

```text
REPLACE_HEAVY_HYBRID / WEAK_WINNER_GRADUATION / STARTER_SATURATION
NO_CORRECTNESS_DEFECT_CONFIRMED
```

Evidence from the Phase32 AN-AQ audits:

- many initial positions are one-lot / starter-sized;
- most weak or non-durable starters correctly remain small;
- durable winners are a small sample in the current 252BD evidence;
- durable winners rarely grow materially;
- existing architecture can graduate winners under valid conditions, including
  `94340` and `76470`;
- current evidence does not justify Production behavior changes.

Deferred / open tracks:

```text
Model 2 - PM Position Lifecycle + PC ADD Consideration
Status: DEFERRED / ON HOLD
Rejected: NO
Production activation: NOT AUTHORIZED
Shadow: PARTIALLY_VALIDATED
Scope: semantic / lifecycle clarity and PM/SI/PC ADD consideration routing
Not proven to solve: Graduation Episode lifecycle, NEW/ADD/Cash marginal
capital comparison, or Winner capitalization by itself
```

```text
Starter-to-Winner Graduation Contract
Status: OPEN / SHADOW_ONLY
Rejected: NO
Production activation: NOT AUTHORIZED
Current conservative contract: PARTIAL
Accepted finding: safe shadow graduation consideration is partially
reconstructable, but deterministic Production-ready fresh / renewed episode
boundary is not available from current PIT evidence. Mandatory freshness is not
part of the current accepted baseline.
```

```text
High-resolution NEW / ADD / Cash marginal capital comparison
Status: DEFERRED
Production comparator change: NOT AUTHORIZED
Known concern: current NEW / ADD / Cash comparison is not fully expressed in
one calibrated marginal-JPY value unit, and current evidence is insufficient to
justify redesign.
```

Non-negotiable preservation constraints for any future research:

- weak starters staying small;
- no-loss averaging protection;
- Cash optionality;
- Risk Pacing;
- BUY_NEW quality gates;
- Winner retention improvements;
- SELL independence;
- concentration / headroom controls;
- lot feasibility;
- fail-closed behavior;
- Portfolio Construction final capital allocation authority;
- Position Sizing discrete quantity authority;
- Runtime exact consumption;
- G129 BUY_ADD order-increment semantics;
- broker / corporate-action / Safety boundaries.

Deferred Winner Graduation, Model 2, and marginal-comparator work may be
revisited only when new independent evidence materially strengthens the case:
longer Historical windows, multiple years, multiple regimes, larger
durable-winner samples, repeated weak graduation across independent periods,
repeated high fragmentation / starter saturation, or repeated Cash / NEW capital
destination while valid incumbents remain undercapitalized. A single Historical
window must not tune Production rules.

Next operational step:

```text
LONG_HISTORICAL_EVIDENCE_ACCUMULATION_WITH_CURRENT_ACCEPTED_SPEC
```

No Strategy changes are authorized before that validation. Performance outcome
alone must not retroactively redefine Production logic.
