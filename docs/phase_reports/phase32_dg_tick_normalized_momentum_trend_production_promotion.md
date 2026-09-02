# Phase32-DG - Tick-Normalized Momentum / Trend Production Promotion

## Scope

Phase32-DG promoted the Phase32-DC tick-quantization-aware trend / momentum
confidence contract into the Production evidence path, using the Phase32-DF
canonical PIT minimum-tick authority.

No fresh-run, resume, recover, replay, or long Historical command was executed.
The existing diagnostic run
`runtime-test-historical-extended-smoke-20260901T223409325599Z` was not mutated.
No future price, future return, later PnL, MFE/MAE, campaign outcome, delisting,
or symbol-specific production logic was used.

## Root Contract

`DESIGN_PRINCIPLE_PRESERVED = YES`

Production rule:

```text
low price != bad
large percentage movement != automatically strong momentum
apparent momentum/trend must be qualified by tick-normalized robustness
```

The implementation does not create:

- a hard minimum stock-price rule;
- a symbol blacklist;
- a generic low-price penalty;
- a PnL-derived threshold;
- a 93180-specific production branch.

## Implementation Summary

Files changed:

- `src/ai_fund_lab_v2/strategy/tick_quantization.py`
- `src/ai_fund_lab_v2/strategy/input_materialization.py`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `src/ai_fund_lab_v2/strategy/buy_quality.py`
- `src/ai_fund_lab_v2/strategy/strategy_intelligence.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase32_dg_tick_normalized_production.py`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`

Technical Features now materialize a compact PIT tick-normalized evidence set:

- `single_tick_pct`
- `close_level_count_5d`, `close_level_count_10d`,
  `close_level_count_20d`, `close_level_count_60d`
- `ticks_traversed_5d`, `ticks_traversed_20d`, `ticks_traversed_60d`
- `net_tick_move_5d`, `net_tick_move_20d`, `net_tick_move_60d`
- `directional_tick_persistence_5d`, `directional_tick_persistence_20d`,
  `directional_tick_persistence_60d`
- MA separation in ticks and relative to one tick percentage
- return relative to tick resolution
- `quantized_volatility_context`

`TICK_NORMALIZED_TECHNICAL_FEATURES_IMPLEMENTED = YES`

`FEATURE_SET_MINIMAL_AND_SUFFICIENT = YES`

The feature set is intentionally limited to the fields required for trend
robustness, momentum confidence, relative-strength qualification, BQ validation,
and Entry semantics.

## Strategy Intelligence

`TICK_NORMALIZED_TREND_ROBUSTNESS_IMPLEMENTED = YES`

Implemented authority:

`TICK_NORMALIZED_TREND_ROBUSTNESS_AUTHORITY`

States:

- `ROBUST`
- `ACCEPTABLE`
- `QUANTIZED_CAUTION`
- `INSUFFICIENT_EVIDENCE`

`QUANTIZATION_AWARE_MOMENTUM_CONFIDENCE_IMPLEMENTED = YES`

Implemented authority:

`QUANTIZATION_AWARE_MOMENTUM_CONFIDENCE_AUTHORITY`

States:

- `HIGH_CONFIDENCE`
- `MODERATE_CONFIDENCE`
- `LOW_CONFIDENCE_QUANTIZED`
- `INSUFFICIENT_EVIDENCE`

`CLOSE_LEVEL_DIVERSITY_PRODUCTION_EVIDENCE = YES`

Close-level diversity is now production evidence. A two-level series such as
`2 -> 3 -> 2 -> 3` is distinguished from a broader multi-level sequence even
when percentage returns appear large.

`TICK_AWARE_RELATIVE_STRENGTH_IMPLEMENTED = YES`

Relative strength now consumes the symbol-side tick robustness state. If the
symbol leg is `LOW_CONFIDENCE_QUANTIZED`, stock-vs-market spread remains
observable but is not clean supportive evidence by itself.

## Candidate / BQ / Entry

`CANDIDATE_TICK_EVIDENCE_INTEGRATION = PASS`

Candidate rows now preserve explicit tick evidence fields:

- `tick_quantization_status`
- `tick_normalized_trend_state`
- `momentum_confidence_state`
- `close_level_diversity_state`
- `candidate_rank_tick_reliability`
- tick caution / insufficient evidence reason codes

`CANDIDATE_RANK_RELIABILITY_SEPARATED_FROM_RAW_RANK = YES`

Raw Candidate rank and score remain visible. When tick-normalized evidence is
`QUANTIZED_CAUTION` or `LOW_CONFIDENCE_QUANTIZED`, Candidate records that rank /
score are not independent confirmation of the same quantized price move.

`BQ_TICK_VALIDATION_IMPLEMENTED = YES`

BQ now materializes `tick_quantization_validation`. It independently consumes
the tick evidence and does not let Candidate rank confirm itself.

`BQ_EXISTING_AUTHORITY_PRESERVED = YES`

BQ score weights, action boundaries, score semantics, and existing reject /
BUY_WAIT mechanics were not changed. Tick evidence acts as a reliability
constraint:

- `ROBUST` / `ACCEPTABLE`: normal BQ path.
- `QUANTIZED_CAUTION` / `LOW_CONFIDENCE_QUANTIZED`: submittable opportunities
  cannot become ordinary FULL solely from rank/percentage evidence; FULL is
  capped to reduced where applicable.
- `INSUFFICIENT_EVIDENCE`: item-scoped review when material.

`ENTRY_TICK_QUANTIZATION_INTEGRATION = PASS`

Entry admission now consumes the Strategy Intelligence tick states:

- `ROBUST` / `ACCEPTABLE`: normal existing Entry path.
- `QUANTIZED_CAUTION`: reduced admission unless other existing evidence already
  requires BUY_WAIT / review.
- `INSUFFICIENT_EVIDENCE`: symbol-scoped wait / review via the existing
  insufficiency path.

`TICK_REASON_CODES_MATERIALIZED = YES`

Reason codes distinguish:

- tick quantization caution;
- insufficient tick / momentum evidence;
- low-price but persistent tick-normalized trend.

## PC / PS Boundary

`OPPORTUNITY_TRUTH_VS_ALLOCATION_RISK_SEPARATION = PASS`

Technical Features / SI / Candidate / BQ / Entry answer whether apparent
opportunity quality is trustworthy. PC still answers how much capital to
allocate.

`PC_TICK_CAP_SEMANTICS_CHANGED = NO`

No changes were made to `PRICE_TICK_RISK_CAPS`, WATCH/ELEVATED/SEVERE/EXTREME
thresholds, concentration semantics, liquidity-capacity semantics, Cash policy,
or capital competition formulas. PC naturally sees eligibility/action changes
from upstream evidence.

`PS_AUTHORITY_CHANGED = NO`

Position Sizing remains executable quantity materialization only. Tick
provenance is preserved as context.

## DD Control Set

`DD_QUANTIZED_CONTROL_SET_PASS = PASS_FOCUSED`

Focused controls prove:

- 93180 / 2023-03-15-style two-level, one-yen tick evidence materializes
  `QUANTIZED_CAUTION` and `LOW_CONFIDENCE_QUANTIZED`.
- Candidate strong rank remains visible but is not independent confirmation.
- BQ does not pass the case through as ordinary robust FULL evidence.
- 89180 / 76470-style elevated tick caution is covered by the same generic
  evidence-quality path.
- 93180 / 2023-02-21-style non-positive rows are not resurrected by DG because
  non-positive / unusable BQ semantics remain unchanged.

`LOW_PRICE_POSITIVE_CONTROL_PASS = PASS_FOCUSED`

Focused controls prove that low price with acceptable tick persistence remains
eligible. DG does not impose a blanket low-price block. DD positive controls to
cover in fresh validation remain:

- 33500 / 2022-10-07
- 76470 / 2022-10-12
- 17570 / 2022-10-20
- 67400 / 2023-04-13

`NORMAL_PRICE_CONTROL_PASS = PASS_FOCUSED`

Focused materialization against existing evidence classified:

- 76920 / 2023-03-15: `ROBUST` / `HIGH_CONFIDENCE`
- 94320 / 2023-03-15: `ACCEPTABLE` / `HIGH_CONFIDENCE`
- 83060 / 2023-03-15: `ACCEPTABLE` / `MODERATE_CONFIDENCE`

Normal-price behavior is unchanged except for added explanatory evidence.

## 93180 / 2023-03-15 Reclassification

`93180_20230315_PRODUCTION_RECLASSIFICATION =`

Before DG, actual run evidence showed:

- raw Candidate rank: 2
- opportunity buy rank: 3
- opportunity score: `0.27460966`
- BQ: `HIGH` / `FULL_ALLOCATION_ELIGIBLE`
- Entry: `BUY_NEW_REDUCED_ONLY`
- PC target weight: `0.029412`
- Runtime planning: `BUY_NEW`, `planned_quantity = 11900`
- tick-normalized evidence: not materialized

DG focused materialization using the same PIT quote/listed-issues source showed:

- reference price: `3.0`
- canonical tick: `1.0`
- `single_tick_pct = 0.33333333`
- `close_level_count_20d = 2`
- trend robustness: `QUANTIZED_CAUTION`
- momentum confidence: `LOW_CONFIDENCE_QUANTIZED`
- rank reliability: `LOW_CONFIDENCE`

Expected DG behavior:

- raw rank remains observable;
- BQ cannot treat rank/score as independent tick confirmation;
- ordinary FULL evidence is capped/qualified;
- Entry materializes reduced/wait/review semantics through existing evidence;
- final order materialization depends on the fresh-run PC/PS path and must be
  validated by a user-operated fresh run.

No later outcome or PnL was used.

## Decision Impact Profile

`DG_DECISION_IMPACT_PROFILE = DD_COMPLETED_EVIDENCE_EXPECTED_PROFILE_PLUS_FOCUSED_POST_SOURCE_CONTROLS`

DD completed evidence profile used:

- Quantized-caution Candidate Top50: 252 observations / 5 symbols.
- Quantized-caution Candidate Top10: 137 observations / 2 symbols.
- Quantized-caution Candidate Top5: 120 observations / 2 symbols.
- Quantized-caution BQ HIGH: 90 observations / 2 symbols.
- Quantized-caution BQ FULL: 67 observations / 2 symbols.
- Quantized-caution Entry BUY_NEW_REDUCED_ONLY: 240 observations.
- Quantized-caution Entry ADD_REDUCED_ONLY: 9 observations.
- Quantized-caution Entry BUY_NEW_ALLOWED: 4 observations.

Post-DG full cross-sectional recomputation was attempted only as a read-only
static scan, but stopped due local Parquet read cost before completion. The
fresh validation run must provide final post-DG counts:

- unchanged;
- newly `QUANTIZED_CAUTION`;
- newly reduced;
- newly BUY_WAIT;
- newly REVIEW_REQUIRED;
- no longer eligible;
- still eligible low-price robust / acceptable.

The focused post-source controls are sufficient for code acceptance, but not a
substitute for the required fresh validation.

`NORMAL_PRICE_DECISION_CHANGE_COUNT = 0_IN_FOCUSED_CONTROLS; FULL_FRESH_COUNT_PENDING`

## Missing Tick / Hash / Safety

`MISSING_TICK_AUTHORITY_STRATEGY_POLICY = PASS`

If canonical minimum-tick authority is `INSUFFICIENT_EVIDENCE`, DG does not
assume robustness and does not silently use a default tick. The handling is
item-scoped evidence insufficiency.

`DG_MINIMUM_TICK_AUTHORITY_HASH_CONSISTENCY = PASS_FOCUSED`

Consumers use the Technical Features row-level `minimum_tick_authority_hash`.
Candidate/BQ/SI/PC preserve the upstream field rather than creating a second
consumer-local tick authority.

`G129_BUY_ADD_REGRESSION = PASS`

Existing focused G129-related test coverage passed.

`CW_REENTRY_REGRESSION = PASS`

Existing focused CW REENTRY regression coverage passed.

`CAMPAIGN_IDENTITY_REGRESSION = PASS`

DG does not alter campaign ID generation, campaign provenance, SELL/REDUCE/EXIT
identity propagation, or Runtime execution identity.

## Validation

Compile:

```text
PASS
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m py_compile
  src/ai_fund_lab_v2/strategy/tick_quantization.py
  src/ai_fund_lab_v2/strategy/input_materialization.py
  src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
  src/ai_fund_lab_v2/strategy/buy_quality.py
  src/ai_fund_lab_v2/strategy/strategy_intelligence.py
  src/ai_fund_lab_v2/strategy/portfolio_construction.py
  tests/strategy/test_phase32_dg_tick_normalized_production.py
```

Focused regression:

```text
PASS - 316 passed
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest -q
  tests/strategy/test_phase32_dg_tick_normalized_production.py
  tests/strategy/test_phase32_df_minimum_tick_authority.py
  tests/runtime_v2/test_phase30_aj2_candidate_pit_quality_surface.py
  tests/strategy/test_phase26_h_adaptive_buy_quality.py
  tests/strategy/test_phase30_j_strategy_intelligence.py
  tests/strategy/test_phase22_e_portfolio_construction.py
  tests/strategy/test_phase22_j_position_sizing.py
  tests/runtime_v2/test_phase26_step4_position_sizing_authority.py
  tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py
  tests/strategy/test_phase32_cw_minimal_residual_reentry.py
  tests/strategy/test_phase32_x_recoverable_deterioration_episode.py
```

Read-only focused materialization:

```text
PASS
Existing 2023-03-15 PIT quote/listed-issues evidence was materialized to
/private/tmp only. Runtime run state was not mutated.
```

Observed focused classifications:

| Symbol | Reference price | Tick pct | 20d levels | Trend | Momentum | Rank reliability |
| --- | ---: | ---: | ---: | --- | --- | --- |
| 93180 | 3.0 | 33.333333% | 2 | QUANTIZED_CAUTION | LOW_CONFIDENCE_QUANTIZED | LOW_CONFIDENCE |
| 89180 | 9.0 | 11.111111% | 2 | QUANTIZED_CAUTION | LOW_CONFIDENCE_QUANTIZED | LOW_CONFIDENCE |
| 76470 | 26.0 | 3.846154% | 3 | QUANTIZED_CAUTION | LOW_CONFIDENCE_QUANTIZED | LOW_CONFIDENCE |
| 76920 | 563.7 | 0.177399% | 19 | ROBUST | HIGH_CONFIDENCE | RELIABLE |
| 94320 | 157.9 | 0.063331% | 16 | ACCEPTABLE | HIGH_CONFIDENCE | QUALIFIED |
| 83060 | 861.5 | 0.011608% | 20 | ACCEPTABLE | MODERATE_CONFIDENCE | QUALIFIED |

Sandbox emitted pyarrow `sysctlbyname` warnings during Parquet reads; outputs
completed and were not Runtime failures.

## Required Final Answers

1. `DESIGN_PRINCIPLE_PRESERVED = YES`
2. `TICK_NORMALIZED_TECHNICAL_FEATURES_IMPLEMENTED = YES`
3. `FEATURE_SET_MINIMAL_AND_SUFFICIENT = YES`
4. `TICK_NORMALIZED_TREND_ROBUSTNESS_IMPLEMENTED = YES`
5. `QUANTIZATION_AWARE_MOMENTUM_CONFIDENCE_IMPLEMENTED = YES`
6. `CLOSE_LEVEL_DIVERSITY_PRODUCTION_EVIDENCE = YES`
7. `TICK_AWARE_RELATIVE_STRENGTH_IMPLEMENTED = YES`
8. `CANDIDATE_TICK_EVIDENCE_INTEGRATION = PASS`
9. `CANDIDATE_RANK_RELIABILITY_SEPARATED_FROM_RAW_RANK = YES`
10. `BQ_TICK_VALIDATION_IMPLEMENTED = YES`
11. `BQ_EXISTING_AUTHORITY_PRESERVED = YES`
12. `ENTRY_TICK_QUANTIZATION_INTEGRATION = PASS`
13. `TICK_REASON_CODES_MATERIALIZED = YES`
14. `OPPORTUNITY_TRUTH_VS_ALLOCATION_RISK_SEPARATION = PASS`
15. `PC_TICK_CAP_SEMANTICS_CHANGED = NO`
16. `PS_AUTHORITY_CHANGED = NO`
17. `DD_QUANTIZED_CONTROL_SET_PASS = PASS_FOCUSED`
18. `LOW_PRICE_POSITIVE_CONTROL_PASS = PASS_FOCUSED`
19. `NORMAL_PRICE_CONTROL_PASS = PASS_FOCUSED`
20. `93180_20230315_PRODUCTION_RECLASSIFICATION = raw rank preserved; BQ HIGH/FULL ordinary evidence is now qualified by QUANTIZED_CAUTION / LOW_CONFIDENCE_QUANTIZED; fresh PC/PS order materialization pending user validation`
21. `DG_DECISION_IMPACT_PROFILE = DD expected impact profile recorded; full post-DG fresh counts pending`
22. `NORMAL_PRICE_DECISION_CHANGE_COUNT = 0 in focused controls; full fresh count pending`
23. `MISSING_TICK_AUTHORITY_STRATEGY_POLICY = PASS`
24. `DG_MINIMUM_TICK_AUTHORITY_HASH_CONSISTENCY = PASS_FOCUSED`
25. `G129_BUY_ADD_REGRESSION = PASS`
26. `CW_REENTRY_REGRESSION = PASS`
27. `CAMPAIGN_IDENTITY_REGRESSION = PASS`
28. `FUTURE_OUTCOME_USED = NO`
29. `SYMBOL_BLACKLIST = NO`
30. `HARD_MINIMUM_PRICE_RULE = NO`
31. `SYMBOL_SPECIFIC_BRANCH = NO`
32. `HISTORICAL_PNL_USED_FOR_THRESHOLDS = NO`
33. `ARCHITECTURE_SOT_UPDATED = YES`
34. `FOCUSED_REGRESSION_RESULT = PASS; 316 passed`
35. `PRODUCTION_CHANGE_EXECUTED = YES`
36. `TARGET_RUN_MUTATED = NO`
37. `DG_PRODUCTION_REPAIR_ACCEPTED = YES_FOCUSED; FRESH_VALIDATION_REQUIRED`
38. `FRESH_VALIDATION_REQUIRED = YES`
39. `FRESH_VALIDATION_COMMAND = PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-extended-smoke --start-date 2022-10-03 --business-days 650 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state`
40. `NEXT_RECOMMENDED_STEP = user-operated fresh Historical validation with DG source; compare first divergence and DD control cases without using future outcome for parameter selection`
41. `FINAL_JUDGMENT = PHASE32_DG_TICK_NORMALIZED_MOMENTUM_TREND_PRODUCTION_PROMOTION_ACCEPTED_FOCUSED_VALIDATION_PASS_FRESH_VALIDATION_REQUIRED`

## Final Judgment

`PHASE32_DG_TICK_NORMALIZED_MOMENTUM_TREND_PRODUCTION_PROMOTION_ACCEPTED_FOCUSED_VALIDATION_PASS_FRESH_VALIDATION_REQUIRED`

DG is accepted at focused implementation level. It promotes tick-normalized
trend / momentum reliability into Production evidence without price blacklists,
hard minimum-price rules, PnL tuning, PC cap changes, PS authority changes, G129
changes, or CW REENTRY changes. A new user-operated fresh Historical run is
required because Candidate/BQ/Entry semantics can now legitimately diverge from
pre-DG runs.
