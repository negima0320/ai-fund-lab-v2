# Phase30-G — Stock Selection Intelligence / PIT Data / Feature Authority Deep Audit

## Task ID

`Phase30-G`

## Scope

Read-only Strategy Intelligence / PIT Data / Feature / Authority audit.

No Strategy, Runtime, config, model, threshold, Safety, BUY Quality, BUY_WAIT,
ADD, HOLD, REDUCE, EXIT, Corporate Event, Historical run, or 2023-10-27 HALT
repair change was authorized or performed.

---

## Primary Judgment

```text
PHASE30_G_STOCK_SELECTION_INTELLIGENCE_MULTI_CAUSAL_GAPS_CONFIRMED_CONTINUATION_QUALITY_DOWNSIDE_RISK_EXPECTED_EDGE_REDESIGN_RESEARCH_READY
```

The current system is PIT-safe enough to research stock-selection improvement,
but the present selection intelligence is not semantically aligned with the
Phase30 Continuation Quality contract.

The largest issue is not one missing threshold. It is a multi-causal decision
quality gap:

- the current BUY Quality aggregate is mechanically correct but does not
  reliably separate forward Winners from dangerous candidates,
- `runtime_opportunity_score` is treated as a strong relative input even though
  it is explicitly an uncalibrated relative model score, not expected return,
- useful multi-horizon trajectory evidence is produced and propagated, but its
  weighted contribution to BUY Quality is `0.0`,
- severe-loss risk is partially visible before Entry through volatility,
  reversal, trajectory, low-price/microstructure, and event-risk evidence, but
  not organized as an explicit Downside Risk authority,
- Corporate/Event eligibility remains materially incomplete for alert /
  supervision / delisting-risk style cases,
- ADD / REENTRY / HOLD need the same forward-continuation evidence, not a
  separate isolated tuning pass.

Recommended architecture direction:

```text
Option C — Redesign Stock Selection Intelligence around Continuation Quality /
Downside Risk / Expected Edge while preserving existing authority boundaries.
```

No implementation is authorized by this report.

---

## Evidence Boundary

| Item | Value |
|---|---|
| Run ID | `runtime-test-historical-extended-smoke-20260815T061857447380Z` |
| Clean period used | `2022-08-10` through `2023-10-26` |
| Completed business days | `299` |
| Candidate / BUY Quality decision rows | `14,950` |
| BUY fills | `219` |
| BUY_NEW | `104` |
| BUY_ADD | `33` |
| REENTRY | `82` |
| SELL fills | `231` |
| Campaigns | `186` |

Evidence after `2023-10-26` was not used as completed performance evidence.
The failed `2023-10-27` valuation candidate was not used as completed outcome
evidence.

Machine-readable artifacts:

```text
reports/phase_reports/phase30_g_stock_selection_intelligence_pit_data_feature_authority_deep_audit.json
reports/phase_reports/phase30_g/cohort_outcomes.json
reports/phase_reports/phase30_g/feature_inventory.json
reports/phase_reports/phase30_g/decision_authority_map.json
reports/phase_reports/phase30_g/previous_hypothesis_reconciliation.json
reports/phase_reports/phase30_g/improvement_candidate_ranking.json
```

---

## Current Stock Selection Architecture

Readable decision graph:

```text
J-Quants PIT market/listed data
-> normalized bars / listed issue authority
-> candidate feature artifact
-> buy_ai candidate_decisions.json
-> buy_ai opportunity_rankings.json
-> strategy/buy_quality_decisions.json
-> strategy/portfolio_construction.json
-> strategy/position_sizing.json
-> strategy/runtime_planning.json
-> Runtime Pending / Submit / Execution
-> Current / valuation / campaign evidence
```

Authority map:

| Stage | Producer / Artifact | Consumer | Influence |
|---|---|---|---|
| Universe / listed | J-Quants listed issues and normalized bars | Candidate feature builder, Corporate Event, PC broker eligibility | Can exclude unsupported/non-listed product classes; does not cover all event risk |
| Candidate model | `.runtime/runtime_state/buy_ai/<date>/candidate_decisions.json` | Opportunity ranking / BUY Quality | Candidate Top50 source |
| Opportunity score/rank | `.runtime/runtime_state/buy_ai/<date>/opportunity_rankings.json` | BUY Quality, Portfolio Construction | Strong rank/relative-score influence |
| BUY Quality | `strategy/buy_quality_decisions.json` | Portfolio Construction | FULL / REDUCED / BUY_WAIT / REJECT |
| Market Context | `strategy/market_context.json` | BUY Quality, PM, PC compatibility | 15% BUY Quality modifier; regime evidence |
| Corporate Event | `strategy/corporate_event.json` | BUY Quality / PC compatibility | Basic listed/corporate action authority; partial event coverage |
| Portfolio Construction | `strategy/portfolio_construction.json` | Position Sizing | Target Portfolio Authority; reentry, low-price cap, lot-aware allocation |
| Position Sizing | `strategy/position_sizing.json` | Runtime Planning | Quantity / delta materialization |
| Runtime Planning | `strategy/runtime_planning.json` | Runtime | Pure mapping to BUY_NEW / BUY_ADD / SELL / NO_ACTION |
| Safety | Safety artifacts | Runtime | Guardrail only; not optimization authority |

---

## Data Correctness

Primary PIT data correctness is broadly acceptable for research:

- normalized J-Quants daily bars are PIT-bound to each business date,
- BUY Quality artifacts record `future_information_used = false`,
- opportunity / candidate accepted-generation binding is run-scoped and fixed,
- market context declares no latest fallback and no previous-day context copy,
- Phase30-F found no pre-HALT valuation/basis contamination through
  `2023-10-26`.

Defects / limitations:

- model generation authority is fixed at run start and historically evaluated;
  acceptable for this run's locked evaluation, but not proof of future model
  calibration,
- Corporate/Event coverage is partial,
- some source roles are `DRAFT` / `NOT_ELIGIBLE` for runtime consumer status
  while calculation proceeds under controlled Historical evidence,
- score semantics are correct but strategically weak: `runtime_opportunity_score`
  is explicitly not expected return.

---

## Data Completeness

| Data family | Status | Judgment |
|---|---|---|
| Adjusted OHLCV / volume | `AVAILABLE_AND_CONSUMED` | Good enough for momentum, volatility, volume, liquidity research |
| Listed state / market segment | `AVAILABLE_AND_CONSUMED` | Basic listed/product class evidence exists |
| Corporate actions | `PARTIALLY_AVAILABLE_AND_CONSUMED` | Split/action framework exists, but coverage is incomplete |
| Earnings schedule | `NOT_AVAILABLE_IN_CURRENT_PIT_DATA` / limited calendar exception | Not reliable as full PIT event risk |
| Alert / special caution / supervision | `AVAILABLE_ONLY_EXTERNALLY` or `NOT_AVAILABLE_IN_CURRENT_DATA` | 93180-style gap remains material |
| Delisting risk | `PARTIAL` | Basic listed status is not enough for pre-delisting warning risk |
| TOB / material events | `PARTIAL_OR_NOT_AVAILABLE` | Not a complete decision input |
| Market Context / regime | `AVAILABLE_AND_CONSUMED` | Good market-wide context, not enough stock-relative edge |
| Sector / relative strength | `AVAILABLE_BUT_OPAQUE_OR_NOT_EXPLICITLY_CONSUMED` | In model feature contract, not explicit BUY Quality dimension |
| Volume confirmation | `AVAILABLE_BUT_UNDERWEIGHTED` | Present in features/trajectory detail, no direct score weight |
| Low-price / tick risk | `AVAILABLE_AND_CONSUMED_FOR_ALLOCATION` | PC caps allocation, but not full quality/downside semantics |

---

## Feature Inventory

| Feature | Producer | Consumer | Current Influence | Empirical Separation | Issue |
|---|---|---|---|---|---|
| `runtime_opportunity_score` | buy_ai opportunity | BUY Quality / PC | 35% relative opportunity component | Weak / unstable | `FALSE_OR_WEAK_INTELLIGENCE_RISK` |
| Opportunity Rank | buy_ai opportunity | BUY Quality / PC | Relative quality and opportunity-cost order | Rank1 is safer, but no broad monotonicity | `OVERTRUSTED_RELATIVE_ORDER` |
| BUY Quality aggregate | Strategy BUY Quality | PC | FULL / REDUCED / REJECT | Weak / inverse at high bands | `SEMANTIC_MISMATCH` |
| Multi-horizon trajectory | BUY Quality | BUY Quality / PC | BUY_WAIT veto; score weight `0.0` | Strong in executed BUY split | `UNDERWEIGHTED_INTELLIGENCE` |
| Volatility | candidate features / BUY Quality | execution feasibility / trajectory | Partial downside proxy | Moderate severe-loss signal | `UNDERWEIGHTED_DOWNSIDE_RISK` |
| Liquidity / traded value | candidate features / PC | execution feasibility / low-price cap | Partial | Moderate | `PARTIAL_CONSUMPTION` |
| Low-price tick risk | PC | PC | Allocation cap | Systematic issue in cases | `ALLOCATION_ONLY_MAY_BE_INSUFFICIENT` |
| Market Context / regime | market_context | BUY Quality / PM | 15% modifier | Useful but broad | `SEMANTICALLY_WEAK_FOR_STOCK_RELATIVE_SELECTION` |
| Corporate/Event | corporate_event | BUY Quality / PC | Basic block/compatibility | 93180 gap confirmed | `MISSING_SOURCE_DATA` |
| Relative strength | feature contract | model score only | Opaque indirect influence | Partially ready | `PROPAGATION_GAP` |
| Volume confirmation | candidate features | trajectory details | No direct score weight | Plausible | `UNDERWEIGHTED_INTELLIGENCE` |
| ADD incremental value | PM / PC | PC ADD bridge | Partial | Weak / insufficient | `EXPECTED_EDGE_NOT_FORMALIZED` |
| REENTRY recovery | PC semantic reentry | PC | Cooldown / recovery gate | Partially supported | `CHURN_RISK_REMAINS` |

---

## BUY Quality / Rank Result

Current BUY Quality does not reliably separate future outcomes over the clean
299BD sample.

Candidate-universe 20BD forward outcome:

| Bucket | Count | Mean 20BD return | Median | Win rate | Severe adverse <= -5% |
|---|---:|---:|---:|---:|---:|
| HIGH band | 1,495 | `-4.55%` | `-2.00%` | `35.5%` | `42.6%` |
| MEDIUM band | 5,522 | `-0.53%` | `-1.76%` | `40.7%` | `39.7%` |
| LOW band | 2,226 | `+0.06%` | `-1.32%` | `43.2%` | `38.7%` |
| FULL allocation eligible | 1,037 | `-4.43%` | `-0.34%` | `36.1%` | `40.6%` |
| REDUCED allocation only | 8,195 | `-0.63%` | `-1.78%` | `41.0%` | `39.9%` |

Score deciles are not monotonic. The top BUY Quality decile had mean 20BD
return `-4.79%`, while several lower deciles were near flat or positive.

Opportunity Rank has some useful local behavior, especially Rank1:

| Rank bucket | Count | Mean 20BD return | Win rate | Severe adverse <= -5% |
|---|---:|---:|---:|---:|
| Rank1 | 299 | `+0.29%` | `57.3%` | `14.0%` |
| Rank2-3 | 598 | `+0.39%` | `44.4%` | `24.5%` |
| Rank4-5 | 598 | `-1.99%` | `32.9%` | `45.0%` |
| Rank6-10 | 1,495 | `-4.23%` | `36.0%` | `45.1%` |
| Rank11-20 | 2,990 | `-2.56%` | `36.9%` | `47.5%` |
| Rank21+ | 8,970 | `+0.32%` | `41.3%` | `39.7%` |

Rank1 is not useless, but the rank architecture should not be treated as an
uncalibrated expected-return ladder. The evidence does not support auto-buy
Rank1 or fixed Top-N logic.

Classification:

```text
BUY_QUALITY_FORWARD_SEPARATION = WEAK_OR_INVERSE
OPPORTUNITY_RANK_FORWARD_SEPARATION = PARTIAL_NON_MONOTONIC
```

---

## Momentum / Trajectory Result

The system is still partly confusing historical strength with forward
continuation quality.

Evidence:

- top 20D momentum decile: mean 20BD return `-1.96%`, median `-3.97%`,
  severe adverse `48.6%`,
- strong 20D momentum plus negative 1D reversal: mean `-4.21%`, median
  `-7.94%`, severe adverse `55.3%`,
- moderate 20D momentum with healthy trajectory: mean `+0.52%`, median
  `-1.10%`, severe adverse `37.5%`.

Executed BUY split is much clearer:

| Trajectory at BUY | Count | Mean 20BD return | Median | Win rate | Severe adverse <= -5% | Median MAE |
|---|---:|---:|---:|---:|---:|---:|
| `HEALTHY_CONTINUATION` | 46 | `+6.86%` | `+1.32%` | `53.3%` | `20.0%` | `-3.85%` |
| `MIXED_OR_UNRESOLVED` | 170 | `-2.24%` | `-3.45%` | `37.7%` | `45.5%` | `-14.24%` |
| `FADING_PRIOR_WINNER` | 2 | `-29.41%` observable | `-29.41%` | `0.0%` | `100.0%` | `-22.70%` |

The current system calculates useful trajectory information and propagates it,
but:

```text
momentum_trajectory_quality weight = 0.0
```

Trajectory can trigger `BUY_WAIT` for FADING / OVERHEAT, but once a candidate
is BUY-eligible, the weighted BUY Quality score does not reward or penalize the
trajectory state.

Classification:

```text
USEFUL_SIGNAL_UNDERWEIGHTED_OR_NOT_CONSUMED
```

---

## Severe-Loss Result

The clean evidence supports a dedicated Downside Risk research layer.

BUY_NEW is the largest problem:

| BUY type | Count | Mean 20BD return | Win rate | Severe adverse <= -5% | Median MAE |
|---|---:|---:|---:|---:|---:|
| BUY_NEW | 104 | `-3.78%` | `38.6%` | `49.5%` | `-15.23%` |
| REENTRY | 82 | `+4.37%` | `41.5%` | `39.0%` | `-10.81%` |
| BUY_ADD | 33 | `-2.23%` | `48.4%` | `12.9%` | `-3.70%` |

Worst 10% campaign MAE threshold was approximately `-20.2%`. These worst-MAE
campaigns were concentrated in `MIXED_OR_UNRESOLVED` entry evidence.

Severe-loss predictors visible before outcome include:

- `MIXED_OR_UNRESOLVED` trajectory,
- negative 1D reversal after large 20D momentum,
- extreme volatility / recent move volatility,
- high tick sensitivity / very low absolute price,
- weak or ambiguous volume confirmation,
- missing Corporate/Event risk state,
- rank / score overconfidence despite downside evidence.

### 78780 Case

`78780` was bought on `2022-08-24`:

| Field | Value |
|---|---:|
| BUY price | `2,860` |
| Rank | `3` |
| Quality score | `0.777044` |
| Band/action | `HIGH` / `FULL_ALLOCATION_ELIGIBLE` |
| Trajectory | `MIXED_OR_UNRESOLVED` |
| 1D momentum | `-15.75%` |
| 5D momentum | `+42.98%` |
| 20D momentum | `+228.00%` |
| 20D volatility | `0.127143` |
| 20BD forward return | `-32.08%` |
| 20BD MAE | `-34.18%` |

Before the BUY, `78780` had already shown an extreme prior move, a sharp 1D
reversal, high volatility, and trajectory instability. The system recognized
the trajectory as not clean, but still allowed FULL allocation because the
aggregate BUY Quality score remained high.

### 67310 Case

`67310` was bought on `2023-05-23`:

| Field | Value |
|---|---:|
| BUY price | `3,000` |
| Quantity | `100` |
| Rank | `4` |
| Quality score | `0.782903` |
| Band/action | `HIGH` / `FULL_ALLOCATION_ELIGIBLE` |
| Trajectory | `MIXED_OR_UNRESOLVED` |
| 3D momentum | `-33.33%` |
| 5D momentum | `-33.33%` |
| 20D momentum | `0.00%` |
| 20D volatility | `0.231391` |
| Volume 5D ratio | `0.799445` |
| Phase30-E same-day entry loss | `-100,000 JPY` |

Phase30-E proved this was genuine market/Strategy PnL. Phase30-G adds that
before the BUY, PIT evidence already showed `MIXED_OR_UNRESOLVED`, very high
volatility, negative 3D/5D structure, and weak volume confirmation. A reasonable
PIT-based Downside Risk signal could have identified elevated risk.

Classification:

```text
SEVERE_LOSS_PREVENTION_RESEARCH_SUPPORTED
```

---

## Winner Result

Meaningful Winners were not defined simply by high aggregate BUY Quality.

Campaign-level evidence:

| Entry trajectory | Campaigns | Mean campaign PnL | Median campaign PnL | Win rate |
|---|---:|---:|---:|---:|
| `HEALTHY_CONTINUATION` | 34 | `+6,641 JPY` | `+700 JPY` | `70.6%` |
| `MIXED_OR_UNRESOLVED` | 152 | `-823 JPY` | `-800 JPY` | `27.0%` |

Winner-defining PIT characteristics appear more related to:

- healthy multi-horizon continuation,
- smaller MAE during early holding,
- less violent recent reversal,
- continuation that survives beyond Entry,
- favorable regime context without relying solely on market beta,
- ability to remain healthy during HOLD / before MFE.

Loser exclusion alone is not enough. The same evidence suggests the system
needs to recognize forward persistence and thesis health, then use that
evidence for Entry, ADD, and HOLD.

---

## Event / Eligibility Result

`93180` remains the canonical Event / Eligibility gap.

Observed Phase30-G evidence:

- repeated buys and reentries occurred in a very low-price name,
- many entries had HIGH / FULL BUY Quality despite `MIXED_OR_UNRESOLVED`
  trajectory and high tick sensitivity,
- Phase30-C found that public JPX alert / supervision style risk was available
  before the initial BUY, but not proven as Runtime input,
- current `corporate_event.json` taxonomy includes `SUPERVISION_STATUS`,
  `DELISTING_PENDING`, `TOB`, and other event types, but the actual source
  coverage is partial and `external_non_jquants_source_used = false`.

Coverage classification:

| Event data | Classification |
|---|---|
| Listed state | `AVAILABLE_AND_CONSUMED` |
| Market segment | `AVAILABLE_AND_CONSUMED` |
| Corporate action | `PARTIALLY_AVAILABLE_AND_CONSUMED` |
| Earnings schedule | `NOT_AVAILABLE_IN_CURRENT_PIT_DATA` / limited calendar exception |
| Supervision / alert / special caution | `AVAILABLE_ONLY_EXTERNALLY_OR_NOT_AVAILABLE_IN_CURRENT_DATA` |
| Delisting risk | `PARTIAL` |
| TOB / material events | `PARTIAL_OR_NOT_AVAILABLE` |
| Trading halt / restriction | `NOT_PROVEN_CONSUMED` |

Classification:

```text
EVENT_ELIGIBILITY_GAP_CONFIRMED
```

---

## Low-Price / Microstructure Result

This is a genuine systematic issue, not only an anecdote.

Evidence basis:

- Phase30-C identified low-price names among worst PIT selection cases,
- `93180` repeatedly entered at `2-6 JPY`, where one tick is economically huge,
- PC has a low-price allocation cap, which proves the system recognizes the
  risk at allocation time,
- the cap is not the same as a stock-selection / downside-risk semantic model.

Low-price risk appears to belong primarily in:

```text
Downside Risk + Position Sizing + Eligibility/Event completeness
```

It should not become an arbitrary minimum-price rule in Phase30-G.

---

## Relative Strength / Volume / Volatility Result

Relative strength:

- stock-vs-sector and sector features exist in the accepted model feature
  contract,
- Market Context has sector contexts and market-wide breadth/regime,
- BUY Quality does not expose stock-vs-sector strength as a transparent
  standalone decision dimension,
- any relative-strength effect is mostly opaque through model score.

Volume:

- volume momentum features exist,
- volume details reach trajectory snapshots,
- volume is not a direct weighted BUY Quality dimension,
- winner/exhaustion separation remains plausible but not yet fully isolated.

Volatility:

- volatility exists and is PIT-safe,
- high volatility appears in 78780 / 67310 and the high-momentum adverse
  cohorts,
- volatility is currently partial downside evidence, not a formal severe-loss
  probability.

Classification:

```text
RELATIVE_STRENGTH = AVAILABLE_BUT_OPAQUE_OR_UNDERCONSUMED
VOLUME_CONFIRMATION = AVAILABLE_BUT_UNDERWEIGHTED
VOLATILITY_EXHAUSTION = AVAILABLE_AND_EMPIRICALLY_RELEVANT_BUT_NOT_FORMAL_DOWNSIDE_RISK
```

---

## BUY_WAIT Result

BUY_WAIT is helping as a timing filter, but it is not a complete solution.

BUY_WAIT candidate rows:

| Count | Mean 20BD return | Median | Win rate | Severe adverse <= -5% | Median MFE | Median MAE |
|---:|---:|---:|---:|---:|---:|---:|
| 3,348 | `-0.71%` | `-3.04%` | `39.6%` | `43.9%` | `+11.24%` | `-10.28%` |

BUY_WAIT catches many FADING / OVERHEAT cases with poor median outcomes, but
the positive MFE distribution means it may also delay or miss some future
Winners. Phase30-G does not authorize changing BUY_WAIT. The next step should
measure conversion, time-to-entry, avoided losses, and missed Winners.

---

## ADD Result

ADD is not yet proven to concentrate capital into genuine Winners.

Observed BUY_ADD:

| Count | Mean 20BD return | Median | Win rate | Severe adverse <= -5% | Median MFE | Median MAE |
|---:|---:|---:|---:|---:|---:|---:|
| 33 | `-2.23%` | `0.00%` | `48.4%` | `12.9%` | `+5.91%` | `-3.70%` |

ADD appears safer than BUY_NEW on MAE, but the forward return evidence does not
prove that ADD is adding into the strongest continuation opportunities. ADD
still needs incremental Expected Edge / Continuation Quality evidence.

---

## REENTRY Result

REENTRY should not be blanket-banned.

Observed REENTRY:

| Count | Mean 20BD return | Median | Win rate | Severe adverse <= -5% | Median MFE | Median MAE |
|---:|---:|---:|---:|---:|---:|---:|
| 82 | `+4.37%` | `0.00%` | `41.5%` | `39.0%` | `+12.90%` | `-10.81%` |

Trajectory-conditioned REENTRY matters:

| REENTRY trajectory | Count | Mean 20BD return | Win rate | Severe adverse <= -5% | Median MAE |
|---|---:|---:|---:|---:|---:|
| `HEALTHY_CONTINUATION` | 18 | `+12.82%` | `61.1%` | `16.7%` | `-1.65%` |
| `MIXED_OR_UNRESOLVED` | 64 | `+2.00%` | `35.9%` | `45.3%` | `-13.46%` |

The current reentry recovery/cooldown work is partially supported, but REENTRY
quality still depends strongly on continuation state.

---

## HOLD / SELL Implication

The same PIT signals appear useful after Entry.

Implications:

- Entry trajectory separates campaign-level Winner / Loser outcomes,
- deterioration / reversal / volatility appear before giveback in major cases,
- MFE/giveback analysis suggests Continuation Quality can become shared
  lifecycle evidence,
- PM should remain Action Authority for existing positions,
- Continuation Quality should be evidence, not a new BUY/SELL command authority.

Classification:

```text
CONTINUATION_QUALITY_CAN_PLAUSIBLY_BECOME_SHARED_LIFECYCLE_EVIDENCE
```

---

## Previous Improvement Hypothesis Reconciliation

| Hypothesis | Current classification | Status |
|---|---|---|
| Opportunity Rank / Opportunity Score calibration | `IMPLEMENTED_BUT_WEAK_EMPIRICAL_SEPARATION` | Still relevant |
| Adaptive BUY Quality | `IMPLEMENTED_BUT_INEFFECTIVE_AS_FORWARD_SEPARATOR` | Still relevant |
| Multi-horizon momentum trajectory | `PARTIALLY_SUPPORTED_UNDERWEIGHTED_OR_NOT_CONSUMED` | Confirmed important |
| Formal Expected Edge | `STILL_UNTESTED` | High priority |
| Re-entry suppression / recovery hurdle | `PARTIALLY_SUPPORTED` | Do not blanket-ban |
| Low-price / liquidity risk | `CONFIRMED_BY_NEW_CLEAN_EVIDENCE` | High priority |
| Corporate/Event eligibility | `PARTIALLY_SUPPORTED_EVENT_DATA_GAP_REMAINS` | High priority |
| ADD incremental expected edge | `IMPLEMENTED_BUT_EFFECTIVENESS_UNPROVEN_TO_WEAK` | High priority |
| HOLD / Profit Protection / giveback | `STILL_RELEVANT_PARTIALLY_SUPPORTED` | High priority |
| Lot-aware capital allocation | `ALREADY_IMPLEMENTED_BUT_SELECTION_QUALITY_GAP_REMAINS` | Secondary |

This reconciles Phase20-F, Phase24-H/G, Phase26-G/H, Phase27 Expected Edge,
Phase28 ADD/Re-entry work, Phase29 multi-horizon trajectory / opportunity
score work, and Phase30-A/C/D/E/F evidence.

---

## Ignored Intelligence

| Intelligence | Classification | Evidence |
|---|---|---|
| Multi-horizon trajectory | `UNDERWEIGHTED_INTELLIGENCE` | Strong executed BUY separation; score weight `0.0` |
| Relative strength | `PROPAGATION_GAP` / `OPAQUE_INTELLIGENCE` | Feature contract has stock-vs-sector fields, but BUY Quality does not expose them |
| Volume confirmation | `UNDERWEIGHTED_INTELLIGENCE` | Present in snapshots, not direct score dimension |
| Volatility / exhaustion | `UNDERWEIGHTED_DOWNSIDE_RISK` | 78780/67310 and high-momentum reversal cohorts |
| Corporate alert/supervision state | `MISSING_SOURCE_DATA` | 93180 gap |
| ADD incremental value | `SEMANTIC_MISMATCH` | ADD bridge exists, but no formal incremental edge |

---

## False / Weak Intelligence

| Signal | Classification | Evidence |
|---|---|---|
| BUY Quality aggregate | `INVERSE_OR_UNSTABLE_SEPARATION` | HIGH/FULL underperformed lower bands |
| Runtime opportunity score | `NO_CLEAR_SEPARATION` | top score deciles not reliably better |
| Opportunity Rank | `MODERATE_LOCAL_SUPPORT_BUT_NON_MONOTONIC` | Rank1 safer; broader buckets unstable |
| Historical 20D momentum alone | `INVERSE_OR_UNSTABLE_SEPARATION` | highest momentum deciles had worse severe-adverse rates |
| Market-wide regime alone | `WEAK_STOCK_SELECTION_SIGNAL` | useful context but insufficient for relative stock choice |

---

## Root Cause Ranking

1. `FEATURE_SEMANTIC_DEFECT` / `MODEL_SCORE_LIMITATION`:
   BUY Quality and runtime opportunity score do not mean forward continuation
   quality or expected return.
2. `FEATURE_UNDERWEIGHTED`:
   trajectory, volatility, volume, and downside evidence are present but not
   organized into the final quality score.
3. `DECISION_ARCHITECTURE_LIMITATION`:
   stock selection lacks explicit Continuation Quality / Downside Risk /
   Expected Edge dimensions.
4. `MISSING_SOURCE_DATA` / `ELIGIBILITY_GAP`:
   Corporate/Event risk is incomplete, especially alert / supervision /
   delisting-risk information.
5. `PORTFOLIO_ALLOCATION_GAP`:
   low-price and lot-aware allocation mitigate but do not fully solve
   microstructure selection risk.
6. `POSITION_MANAGEMENT_GAP`:
   ADD and HOLD need continuation evidence, not only current PM action logic.
7. `UNAVOIDABLE_UNCERTAINTY`:
   Some losses are genuine market outcomes, but the current evidence shows
   avoidable risk concentration before many of them.

---

## Improvement Candidate Ranking

| Priority | Area | Evidence | Next |
|---|---|---|---|
| P0 | Continuation Quality / trajectory consumption | HEALTHY executed BUYs materially outperform MIXED | Offline CQ / downside research |
| P0 | BUY Quality / Opportunity Score semantic redesign | HIGH/FULL score does not separate | Redesign research, not tuning |
| P0 | Severe-loss / high-MAE risk layer | BUY_NEW severe adverse `49.5%`; 78780/67310 PIT risk visible | Downside Risk labels |
| P1 | Corporate/Event eligibility | 93180 and partial event coverage | Data/feature gap design |
| P1 | Low-price / microstructure | repeated low-price risk; allocation cap only | Downside + sizing research |
| P1 | ADD incremental value | BUY_ADD not proven as Winner concentration | ADD-specific expected edge |
| P1 | Relative strength | available but opaque | Explicit offline separation |
| P2 | BUY_WAIT effectiveness | helpful but missed-Winner risk | conversion/time-to-entry study |
| P2 | REENTRY recovery | healthy reentries better than mixed | condition on continuation evidence |

---

## Can Data Improve Stock Selection?

```text
STRONG_EVIDENCE_IMPROVABLE
```

This does not mean future profitability is guaranteed. It means the clean 299BD
evidence shows PIT-available data dimensions that separate better and worse
outcomes more meaningfully than the current aggregate BUY Quality score:

- executed `HEALTHY_CONTINUATION` BUYs outperformed `MIXED_OR_UNRESOLVED`,
- worst-MAE campaigns were concentrated in weak/mixed trajectory evidence,
- high historical momentum plus short-term reversal had poor forward outcomes,
- 78780 and 67310 both had visible PIT risk features before large adverse
  outcomes,
- REENTRY quality improves materially when continuation is healthy.

---

## Strategy Architecture Recommendation

```text
Option C
```

Redesign Stock Selection Intelligence around:

```text
Continuation Quality
Downside Risk
Expected Edge
Opportunity Cost
Lifecycle reuse for ADD / HOLD evidence
```

while preserving:

- Production-common Strategy,
- BUY / SELL independence,
- fail-closed behavior,
- PIT-only Runtime inputs,
- PM Action Authority,
- Portfolio Construction Target Portfolio Authority,
- Runtime Planning pure mapping,
- Strategy Planning Authority validation/materialization boundary,
- Safety non-optimization role.

Option A is too narrow because current BUY Quality semantics are weak.
Option B is directionally plausible but under-specifies the needed separation
between continuation, downside, and expected edge. Option D is not appropriate:
the 299BD evidence is sufficient for the next research/design step.

---

## Continuation Quality Readiness

```text
CONTINUATION_QUALITY_RESEARCH_READY_WITH_DATA_GAPS
```

Available now:

- trend persistence,
- multi-horizon momentum,
- acceleration/deceleration,
- volatility quality,
- volume confirmation,
- liquidity/microstructure,
- Market Context,
- regime state and transitions.

Gaps:

- explicit stock-vs-sector / stock-vs-market decision dimension,
- complete Corporate/Event risk,
- calibrated severe-loss probability,
- lifecycle labels for ADD / HOLD / giveback.

---

## Expected Edge Readiness

```text
EXPECTED_EDGE_RESEARCH_PARTIALLY_READY
```

Ready:

- 1/3/5/10/20BD forward labels can be built,
- MFE / MAE / severe-loss labels can be built,
- BUY_NEW / ADD / REENTRY can be separated,
- campaign-level outcomes exist through `2023-10-26`.

Not ready:

- current model score is not calibrated expected return,
- opportunity cost among chosen vs available alternatives needs stronger
  candidate retention tables,
- Corporate/Event missingness must be explicitly represented,
- holding-horizon stability and turnover-adjusted labels need formalization.

---

## Architecture Safety Review

Tempting but unsafe actions:

- arbitrary minimum stock price,
- arbitrary momentum thresholds,
- auto-buy Rank1,
- forced Top-N buys,
- blanket REENTRY ban,
- treating model score as expected return,
- optimizing thresholds against the 299BD sample,
- using future MFE/MAE as Runtime input,
- allowing Continuation Quality to bypass PM or Safety authority.

All future work must remain PIT-only and evidence-authoritative.

---

## Final Answer

Given the 299BD clean evidence and prior Strategy investigations, AI Fund Lab
v2 should learn to recognize:

```text
the difference between a stock that has already moved strongly and a stock
whose forward continuation thesis remains healthy, persistent, liquid,
event-safe, and worth the downside risk relative to alternatives.
```

More specifically, it does not yet recognize well enough:

- unstable prior winners that are already reversing,
- high-score candidates whose downside risk overwhelms continuation quality,
- low-price / tick-sensitive moves where percentage momentum is distorted,
- event-risk candidates whose public risk state is not in current PIT inputs,
- ADD opportunities where incremental capital is truly supported by improved
  forward edge,
- HOLD states where the original continuation thesis has deteriorated before
  major giveback.

Phase30-G therefore recommends the next task be research/design, not
implementation.

---

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED BY PHASE30_G
```

## Recommended Next Task

```text
Phase30-H — Continuation Quality / Downside Risk Offline Research
```

