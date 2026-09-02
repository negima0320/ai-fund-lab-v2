# Phase32-DC — Tick-Quantization-Aware Momentum / Trend Evidence Production Contract SHADOW Design

## Scope

Target run:

`runtime-test-historical-extended-smoke-20260901T223409325599Z`

This is a DESIGN / SHADOW report. No Production source, config, runtime state,
Pending, Ledger, replay, resume, recover, or fresh-run operation was executed.
No future price, future PnL, MFE/MAE, later campaign outcome, delisting, or
Historical profitability was used.

Audit evidence snapshot:

`2022-10-03` through `2023-04-18`, 134 completed business days available at
audit time.

## Accepted Premise

Phase32-DA and Phase32-DB established:

- Ultra-low-price securities are not categorically bad.
- Low price alone did not systematically produce high rank across all low-price
  buckets.
- Representative extreme-tick cases, especially 93180, can produce distorted
  percentage/trend evidence.
- Candidate/BQ/Entry lack a canonical upstream tick-quantization validator.
- PC already has `single_tick_pct`, tick-risk tier, liquidity evidence, and
  allocation caps.
- Downstream PC protection alone is insufficient because distorted opportunities
  can still consume Candidate rank, capital competition, and position slots.

`DESIGN_PRINCIPLE_PRESERVED = YES`

The contract must not implement `low price = bad`. It must implement:

```text
apparent momentum/trend must be robust enough to distinguish economically
meaningful movement from coarse tick quantization.
```

## Authority Placement

`NEW_COMPONENT_REQUIRED = NO`

Use existing authorities:

- Technical Features produce PIT tick-normalized facts.
- Strategy Intelligence interprets trend/momentum/microstructure semantics.
- Candidate consumes a confidence/reliability modifier.
- BQ independently validates whether rank/score strength survives tick
  qualification.
- Entry Admission materializes caution/review/wait semantics.
- PC preserves allocation and capacity authority.
- PS remains executable quantity materialization.

No parallel subsystem is justified at this stage.

## Canonical Evidence Set

`CANONICAL_TICK_EVIDENCE_SET`

Required PIT evidence:

| Evidence | Source | Role |
|---|---|---|
| `reference_price` | PIT technical / market evidence | denominator for tick exposure |
| `minimum_tick` | broker/exchange/tick authority | not a silent global assumption |
| `single_tick_pct` | `minimum_tick / reference_price` | materiality of one tick |
| `close_level_count_{5,10,20,60}d` | PIT OHLCV closes | close-level diversity |
| `close_level_entropy_{20,60}d` | PIT OHLCV closes | concentration in one/two levels |
| `ticks_traversed_{5,20,60}d` | `(max_close-min_close)/minimum_tick` | movement breadth in ticks |
| `net_tick_move_{5,20,60}d` | `(last_close-first_close)/minimum_tick` | directional tick movement |
| `directional_tick_persistence_{5,20,60}d` | PIT close deltas | persistence vs oscillation |
| `return_per_tick_resolution_{1,5,20}d` | return divided by single tick pct | whether % move exceeds one-tick scale |
| `ma_separation_ticks_{5_20,close_20}` | MA difference divided by tick size | MA support in tick units |
| `ma_separation_pct_vs_single_tick` | MA ratio edge divided by single tick pct | whether MA signal is smaller than resolution |
| `quantized_volatility_state` | close deltas in ticks plus volatility | volatility caused by coarse ticks |
| `gap_ticks` / `gap_pct_vs_single_tick` | OHLCV / reference price | gap robustness |
| `rolling_median_traded_value_20` | PIT OHLCV | tradability/capacity only |
| `liquidity_capacity_ratio` | PC-compatible authority | allocation risk, not trend truth |

No PnL-optimized thresholds are selected here.

## Trend Robustness Contract

`TICK_NORMALIZED_TREND_ROBUSTNESS_CONTRACT`

Authority name:

`TICK_NORMALIZED_TREND_ROBUSTNESS_AUTHORITY`

Owner:

Strategy Intelligence, backed by Technical Features.

Inputs:

- `single_tick_pct`
- close-level count and entropy
- ticks traversed
- net tick move
- directional tick persistence
- MA separation in ticks
- MA separation relative to one-tick percentage
- PIT coverage status

Semantic states:

| State | Meaning |
|---|---|
| `ROBUST` | Trend is supported by multi-level, multi-tick, directionally persistent movement; apparent percent strength is not dominated by one tick |
| `ACCEPTABLE` | Tick quantization exists but available PIT evidence does not make trend semantics unreliable |
| `QUANTIZED_CAUTION` | Apparent trend/MA support can be explained by one/two close levels or one-tick oscillation |
| `INSUFFICIENT_EVIDENCE` | Required price/tick/close evidence is missing, stale, or not run/date-bound |

Contract rule:

Raw MA/percentage trend remains evidence, but any consumer that treats trend as
positive quality must also consume this robustness state.

## Momentum Confidence Contract

`QUANTIZATION_AWARE_MOMENTUM_CONFIDENCE_CONTRACT`

Authority name:

`QUANTIZATION_AWARE_MOMENTUM_CONFIDENCE_AUTHORITY`

Question:

How much confidence should be placed in percentage momentum given the security's
tick resolution?

States:

| State | Meaning |
|---|---|
| `HIGH_CONFIDENCE` | Return horizons exceed tick resolution with persistent multi-tick support |
| `MODERATE_CONFIDENCE` | Some tick sensitivity exists, but movement has enough breadth/persistence |
| `LOW_CONFIDENCE_QUANTIZED` | Percentage momentum is mostly one-tick or two-level movement |
| `INSUFFICIENT_EVIDENCE` | Missing required PIT price/tick/close evidence |

Raw momentum is not replaced. It is qualified by confidence.

## Close-Level Diversity

`CLOSE_LEVEL_DIVERSITY_ROLE = CANONICAL_DECISION_EVIDENCE`

Close-level diversity must become canonical because it distinguishes:

```text
2 -> 3 -> 2 -> 3
```

from:

```text
20 -> 22 -> 24 -> 27 -> 30
```

Both can produce strong percentage features. They do not have the same economic
trend robustness.

## Relative Strength

`TICK_AWARE_RELATIVE_STRENGTH_CONTRACT`

Relative strength should keep the current market comparator semantics, but
qualify the symbol leg before interpreting the spread:

```text
symbol percentage return
-> symbol tick robustness / momentum confidence
-> stock-vs-market relative strength state
```

If the symbol leg is `LOW_CONFIDENCE_QUANTIZED`, relative strength may remain
observable evidence, but it must not become clean supportive evidence without a
separate explanation.

## Candidate Integration

`CANDIDATE_TICK_EVIDENCE_CONSUMPTION`

Candidate should consume tick evidence as:

- reliability modifier;
- evidence confidence;
- surface qualification;
- rank explanation;
- insufficiency/caution state where evidence is missing or quantized.

Forbidden:

- arbitrary low-price rank penalty;
- fixed price deduction;
- symbol blacklist;
- price-only rejection.

Expected Candidate surface additions:

- `tick_quantization_status`
- `tick_normalized_trend_state`
- `momentum_confidence_state`
- `close_level_diversity_state`
- `candidate_rank_tick_reliability`
- `candidate_surface_reason_codes` such as `candidate_surface_quantized_trend_caution`

Candidate may still rank a low-price security highly when the PIT evidence shows
multi-tick persistent movement.

## Truth vs Allocation Risk

`OPPORTUNITY_TRUTH_VS_ALLOCATION_RISK_SEPARATION = REQUIRED`

Separate:

| Question | Owner | Output |
|---|---|---|
| Is apparent momentum/trend economically meaningful? | Technical Features / Strategy Intelligence / Candidate / BQ / Entry | confidence, robustness, caution, review |
| How much capital can safely be allocated? | PC | target cap, liquidity capacity, allocation adjustment |
| Can the chosen target be expressed as executable quantity? | PS | executable lot/quantity |

The upstream contract must not duplicate PC's allocation penalty. It should
qualify opportunity truth and admission confidence.

## BQ Validation

`BQ_TICK_VALIDATION_CONTRACT`

BQ must add an independent validation component:

`tick_quantization_validation`

Inputs:

- Candidate tick evidence;
- SI tick-normalized trend robustness;
- quantization-aware momentum confidence;
- close-level diversity;
- current BQ momentum trajectory;
- current BQ relative opportunity quality.

Expected behavior:

- If Candidate rank is strong but tick robustness is `QUANTIZED_CAUTION`, BQ
  must not treat upstream rank as independent confirmation.
- BQ may emit `FULL_ALLOCATION_ELIGIBLE` only when strong rank is supported by
  acceptable/robust tick semantics or when momentum is not materially part of
  the positive thesis.
- If tick evidence is missing and material, BQ emits `BUY_WAIT` or
  `REVIEW_REQUIRED`, scoped to the symbol.
- BQ reason codes must state whether low-price momentum was robust, acceptable,
  quantized, or insufficient.

This is a validation of evidence reliability, not an allocation cap.

## Entry Admission

`ENTRY_TICK_QUANTIZATION_CONTRACT`

Entry should consume BQ/SI tick states and materialize:

| Inputs | Entry outcome |
|---|---|
| Candidate strong, BQ pass, tick robustness ROBUST/ACCEPTABLE | normal existing Entry flow |
| Candidate strong, BQ otherwise pass, tick state QUANTIZED_CAUTION | reduced admission, wait, or review depending on other evidence |
| Tick evidence missing but material | `BUY_WAIT` / `REVIEW_REQUIRED`, symbol scoped |
| Low price but persistent multi-tick evidence | eligible; do not auto-suppress |

Entry must explicitly distinguish:

- `entry_reduced_due_to_tick_quantization_caution`
- `entry_wait_due_to_tick_momentum_insufficient`
- `entry_allowed_low_price_persistent_tick_trend`

Low price alone is not a hard rejection.

## PC And PS Preservation

`PC_LOW_PRICE_AUTHORITY_PRESERVATION = YES`

PC remains owner of:

- `single_tick_pct`
- tick tier
- liquidity capacity
- target caps
- capital allocation and reallocation

Promotion should reuse PC-compatible evidence fields but move the evidence
producer upstream to Technical Features / Strategy Intelligence so Candidate,
BQ, and Entry can consume it before position-slot admission.

`PS_AUTHORITY_PRESERVED = YES`

Position Sizing remains executable quantity materialization. It must not become
Strategy re-ranking or low-price eligibility authority.

## Liquidity Semantics

`LIQUIDITY_VS_MOMENTUM_SEMANTIC_SEPARATION = REQUIRED`

Traded value and volume answer:

```text
Can this be traded/capacity-managed?
```

They do not answer:

```text
Is the apparent momentum economically meaningful?
```

Liquidity should support tradability and allocation capacity, not serve as a
standalone confirmation of trend truth.

## SHADOW Reclassification

The following SHADOW states use PIT OHLCV/reference price only. They are
diagnostic, not Production thresholds.

`93180_SHADOW_RECLASSIFICATION`

| Case | Production evidence | SHADOW tick classification |
|---|---|---|
| 93180 2023-03-15 admitted case | price 3, Candidate rank 2, buy rank 3, BQ HIGH/FULL, Entry reduced, target positive | `QUANTIZED_CAUTION` because 20-day closes use only 2/3 JPY levels and MA support is within coarse tick structure |
| 93180 2023-02-16 one-tick +50% case | price 3, Candidate rank 1, BQ HIGH, Entry reduced, target positive | `QUANTIZED_CAUTION` because 1d/5d 50% move is a one-tick move |
| 93180 2023-02-21 rejected case | price 2, Candidate rank 1, BQ UNUSABLE/REJECT, target 0 | `ACCEPTABLE` in the narrow sense that BQ already rejected; tick evidence still records EXTREME exposure |
| 93180 2023-03-06 flat-close/supportive-MA case | price 3, returns mostly 0, MA support around 1.15, BQ HIGH/reduced | `QUANTIZED_CAUTION` because supportive trend is explainable by the 2/3 JPY mixture |

The design does not require every 93180 row to be rejected. It requires the
evidence to say why confidence is low when trend/momentum is tick-quantized.

## Controls

`LEGITIMATE_LOW_PRICE_POSITIVE_CONTROLS`

Potential positive controls must be selected PIT-only from low-price observations
with:

- more than two close levels across lookbacks;
- multi-tick range and net movement;
- directional persistence;
- adequate traded value;
- no stale/missing corporate-action or broker authority.

Available representative control from DB/DC sample:

- 76470 on 2022-10-03: price 27, 20-day closes `[27,28,29]`, range 2 ticks,
  BQ MEDIUM/REDUCED, PC positive. This is still only an elevated-tick partial
  control, not a fully robust positive control.

`NORMAL_PRICE_NEGATIVE_CONTROLS`

Normal-price controls:

- 76920 on 2023-03-15: price 563.7, 19 distinct 20-day close levels, BQ
  HIGH/FULL; SHADOW `ROBUST`.
- 94320 on 2023-03-15: price 157.9, low single-tick pct, BQ HIGH/reduced;
  expected to remain in ordinary path.

The new evidence should be inert or merely explanatory for normal-price names
where tick quantization is negligible.

## SHADOW Distribution

`SHADOW_TICK_SEMANTIC_DISTRIBUTION`

Across 134 completed days and 7,251 joined Candidate/BQ/PC observations:

| SHADOW state | Count |
|---|---:|
| `ROBUST` | 6,172 |
| `ACCEPTABLE` | 831 |
| `QUANTIZED_CAUTION` | 248 |
| `INSUFFICIENT_EVIDENCE` | 0 |

By price bucket:

| Price bucket | Obs | ROBUST | ACCEPTABLE | QUANTIZED_CAUTION |
|---|---:|---:|---:|---:|
| `<=5` | 134 | 0 | 35 | 99 |
| `6-10` | 109 | 0 | 27 | 82 |
| `11-20` | 23 | 0 | 7 | 16 |
| `21-50` | 215 | 0 | 164 | 51 |
| `>50` | 6,770 | 6,172 | 598 | 0 |

By tick tier:

| Tick tier | Obs | ROBUST | ACCEPTABLE | QUANTIZED_CAUTION |
|---|---:|---:|---:|---:|
| `EXTREME` | 243 | 0 | 62 | 181 |
| `SEVERE` | 23 | 0 | 7 | 16 |
| `ELEVATED` | 215 | 0 | 164 | 51 |
| `WATCH` | 284 | 0 | 284 | 0 |
| `NORMAL` | 6,486 | 6,172 | 314 | 0 |

Low-price strong-evidence impact:

| Subset | Count | QUANTIZED_CAUTION | ACCEPTABLE | Main buckets |
|---|---:|---:|---:|---|
| Candidate top-5 | 181 | 116 | 65 | mostly `<=5` and `21-50` |
| Candidate top-10 | 217 | 132 | 85 | mostly `<=5` and `21-50` |
| Opportunity buy top-5 | 170 | 104 | 66 | mostly `<=5` and `21-50` |
| BQ HIGH | 154 | 88 | 66 | `<=5` and `21-50` |
| BQ FULL | 115 | 65 | 50 | `<=5` and `21-50` |
| PC positive target | 94 | 54 | 40 | mostly `<=5` and `21-50` |

These numbers are SHADOW diagnostics only. They show that a tick contract would
be targeted: most normal-price observations remain `ROBUST`, while low-price
strong-rank cases receive additional caution.

## SHADOW Impacts

`SHADOW_CANDIDATE_IMPACT`

Expected Candidate treatment:

- `ROBUST` / `ACCEPTABLE`: unchanged ranking path with additional evidence.
- `QUANTIZED_CAUTION`: rank can remain observable, but confidence should be
  reduced/qualified and reason-coded.
- `INSUFFICIENT_EVIDENCE`: symbol-scoped caution/review; no silent normal-price
  assumption.

`SHADOW_BQ_IMPACT`

BQ would stop treating strong Candidate rank as independent confirmation when
tick robustness is weak. 93180-style HIGH/FULL rows would require explicit
explanation or be reduced/waited/reviewed depending on the rest of the evidence.

`SHADOW_ENTRY_IMPACT`

Entry would materialize tick-quantization caution before position-slot admission.
An extreme-tick security could still enter if PIT evidence shows persistent
multi-tick opportunity, but a two-level 2/3 JPY pattern would no longer look like
ordinary trend support.

`SHADOW_POSITION_SLOT_EFFECT`

The design should reduce low-confidence tick-quantized opportunities consuming
slots while preserving genuine low-price opportunities. It does this at
Candidate/BQ/Entry admission, not by duplicating PC's notional cap.

## Minimum Tick Authority

`MINIMUM_TICK_AUTHORITY`

Current source uses:

```text
DEFAULT_MINIMUM_TICK = 1.0
minimum_tick = row.minimum_tick or row.tick_size or row.price_tick or default
```

This is adequate for SHADOW analysis of the audited 2-50 JPY examples, but it is
not sufficient as a Production-grade authority for all JPX securities/price
bands if actual tick size can vary by price band, market, or security type.

`MINIMUM_TICK_AUTHORITY_REPAIR_REQUIRED = YES_BEFORE_PRODUCTION_PROMOTION`

Before Production implementation, minimum tick must become explicit, PIT-bound,
and sourced from canonical broker/exchange/security metadata or a validated
price-band tick table. The system must not silently assume `1.0` JPY when the
contract is being promoted upstream.

## Missing Evidence Policy

`TICK_EVIDENCE_MISSING_POLICY`

| Missing condition | Policy |
|---|---|
| Missing `reference_price` | `INSUFFICIENT_EVIDENCE`; symbol-scoped review/wait when buy admission depends on trend/momentum |
| Missing `minimum_tick` and tick materiality cannot be proven negligible | `INSUFFICIENT_EVIDENCE`; do not silently assume normal-price behavior |
| Missing close history below required lookback | use shorter-window state only if explicitly marked; otherwise `INSUFFICIENT_EVIDENCE` |
| Stale/cross-run evidence | reject as invalid authority |
| Missing traded value | capacity review/cap under PC semantics; do not infer momentum truth |

Fail-closed must be proportional and symbol-scoped. It should not halt the whole
run when a single BUY candidate lacks tick evidence unless the global evidence
contract itself is malformed.

`PIT_SAFETY = PASS`

All proposed evidence is computable from decision-time OHLCV, reference price,
tick authority, listed/broker/corporate-action metadata, and existing PIT
artifacts.

`HARD_MINIMUM_PRICE_USED = NO`

`SYMBOL_BLACKLIST_USED = NO`

`HISTORICAL_PNL_USED_FOR_DESIGN = NO`

## Production Readiness

`TICK_QUANTIZATION_PRODUCTION_CONTRACT_READY = CONDITIONAL`

The semantic contract is ready enough to freeze as SHADOW/SoT. Production
promotion requires:

- explicit minimum-tick authority;
- artifact schema for canonical tick evidence;
- Candidate/BQ/Entry consumer contracts;
- focused tests proving normal-price path is unchanged;
- low-price positive-control tests proving legitimate multi-tick opportunities
  are not automatically suppressed;
- fail-closed tests for missing/stale tick evidence;
- no PnL-derived threshold selection.

`PHASE32_IMPLEMENTATION_NECESSITY = PHASE33_IMPLEMENTATION_RECOMMENDED_NOT_PHASE32_CLOSURE_BLOCKER`

Reason:

This is a Strategy evidence-quality architecture gap, not a Runtime correctness
blocker. Phase32 may close with this design frozen as SoT if the project accepts
carry-forward risk. Production implementation should be a Phase33 task unless
Phase32 scope is explicitly extended.

## Required Final Answers

1. `DESIGN_PRINCIPLE_PRESERVED = YES`
2. `NEW_COMPONENT_REQUIRED = NO`
3. `CANONICAL_TICK_EVIDENCE_SET = reference_price, explicit minimum_tick, single_tick_pct, close_level_count/entropy, ticks_traversed, net_tick_move, directional_tick_persistence, return_per_tick_resolution, MA separation in ticks, MA separation vs single_tick_pct, quantized_volatility_state, gap_ticks, traded value, liquidity capacity`
4. `TICK_NORMALIZED_TREND_ROBUSTNESS_CONTRACT = ROBUST / ACCEPTABLE / QUANTIZED_CAUTION / INSUFFICIENT_EVIDENCE authority owned by SI with Technical Features backing`
5. `QUANTIZATION_AWARE_MOMENTUM_CONFIDENCE_CONTRACT = HIGH_CONFIDENCE / MODERATE_CONFIDENCE / LOW_CONFIDENCE_QUANTIZED / INSUFFICIENT_EVIDENCE; raw momentum remains evidence`
6. `CLOSE_LEVEL_DIVERSITY_ROLE = CANONICAL_DECISION_EVIDENCE`
7. `TICK_AWARE_RELATIVE_STRENGTH_CONTRACT = qualify symbol return leg with tick robustness before treating stock-vs-market spread as supportive`
8. `CANDIDATE_TICK_EVIDENCE_CONSUMPTION = reliability modifier, evidence confidence, surface qualification, rank explanation, and symbol-scoped insufficiency/caution`
9. `OPPORTUNITY_TRUTH_VS_ALLOCATION_RISK_SEPARATION = REQUIRED`
10. `BQ_TICK_VALIDATION_CONTRACT = independent BQ validation component; strong rank cannot confirm itself when tick robustness is weak`
11. `ENTRY_TICK_QUANTIZATION_CONTRACT = allow/reduce/wait/review based on tick robustness; low price alone is not rejection`
12. `PC_LOW_PRICE_AUTHORITY_PRESERVATION = YES`
13. `PS_AUTHORITY_PRESERVED = YES`
14. `LIQUIDITY_VS_MOMENTUM_SEMANTIC_SEPARATION = REQUIRED`
15. `93180_SHADOW_RECLASSIFICATION = admitted and +50% one-tick cases become QUANTIZED_CAUTION; rejected 2 JPY case remains non-positive with tick exposure recorded`
16. `LEGITIMATE_LOW_PRICE_POSITIVE_CONTROLS = REQUIRED; 76470 2022-10-03 is a partial low-price control, fuller multi-tick controls required before Production thresholds`
17. `NORMAL_PRICE_NEGATIVE_CONTROLS = 76920 and 94320 on 2023-03-15 remain ordinary-path controls`
18. `SHADOW_TICK_SEMANTIC_DISTRIBUTION = ROBUST 6172, ACCEPTABLE 831, QUANTIZED_CAUTION 248, INSUFFICIENT_EVIDENCE 0 over 7251 joined observations`
19. `SHADOW_CANDIDATE_IMPACT = unchanged for robust/acceptable; confidence reduced/caution for quantized; review/wait for insufficient evidence`
20. `SHADOW_BQ_IMPACT = BQ gains independent tick validator and no longer treats reused rank as independent confirmation`
21. `SHADOW_ENTRY_IMPACT = tick caution materialized before position-slot admission`
22. `SHADOW_POSITION_SLOT_EFFECT = expected reduction in low-confidence tick-quantized slot consumption without suppressing robust low-price opportunities`
23. `NEW_FEATURE_REQUIRED = YES`
24. `NEW_MODEL_REQUIRED = NO_NOT_INITIALLY`
25. `MINIMUM_TICK_AUTHORITY = currently default 1.0 or row field if present; not sufficient for full Production promotion`
26. `MINIMUM_TICK_AUTHORITY_REPAIR_REQUIRED = YES_BEFORE_PRODUCTION_PROMOTION`
27. `TICK_EVIDENCE_MISSING_POLICY = symbol-scoped INSUFFICIENT_EVIDENCE / BUY_WAIT / REVIEW_REQUIRED when material; no silent normal assumption`
28. `PIT_SAFETY = PASS`
29. `HARD_MINIMUM_PRICE_USED = NO`
30. `SYMBOL_BLACKLIST_USED = NO`
31. `HISTORICAL_PNL_USED_FOR_DESIGN = NO`
32. `TICK_QUANTIZATION_PRODUCTION_CONTRACT_READY = CONDITIONAL`
33. `PHASE32_IMPLEMENTATION_NECESSITY = PHASE33_IMPLEMENTATION_RECOMMENDED_NOT_PHASE32_CLOSURE_BLOCKER`
34. `PRODUCTION_CHANGE_EXECUTED = NO`
35. `TARGET_RUN_MUTATED = NO`
36. `NEXT_RECOMMENDED_STEP = freeze this as SoT, then create Phase33 implementation for explicit minimum-tick authority plus Technical Features/SI/Candidate/BQ/Entry tick evidence propagation and focused tests`
37. `FINAL_JUDGMENT = PHASE32_DC_TICK_QUANTIZATION_AWARE_EVIDENCE_CONTRACT_DESIGNED_SHADOW_ONLY_CONDITIONAL_FOR_PRODUCTION_PROMOTION`

## Final Judgment

`PHASE32_DC_TICK_QUANTIZATION_AWARE_EVIDENCE_CONTRACT_DESIGNED_SHADOW_ONLY_CONDITIONAL_FOR_PRODUCTION_PROMOTION`

The proposed contract preserves legitimate low-price opportunities and avoids
hard price floors or symbol blacklists. It addresses the DB-confirmed gap by
promoting tick-normalized trend robustness and quantization-aware momentum
confidence into existing Technical Features / Strategy Intelligence / Candidate
/ BQ / Entry authorities while preserving PC allocation caps and PS quantity
materialization. Production promotion is conditional on explicit minimum-tick
authority and focused tests; it is recommended for Phase33 rather than required
to close Phase32 Runtime correctness.
