# Phase32-FI - One-Yen Tick / Low-Price Quantization Protection Regression READ-ONLY Audit

## Scope

Target run:

`runtime-test-historical-extended-smoke-20260903T213011268067Z`

This was a READ-ONLY audit. No source, config, schema, runtime state,
Pending, Ledger, replay, resume, recover, or fresh-run operation was
executed. A phase report was created as the only file change. No future
price, future return, MFE/MAE, campaign outcome, SELL result, or Historical
PnL was used for Production judgment.

Audit snapshot:

| Item | Value |
| --- | --- |
| Run status at final snapshot | `RUNNING` |
| Completed business days scanned | 175 |
| Covered dates | `2022-10-03` through `2023-06-19` |
| Next job at snapshot | `2023-06-20:submit` |
| Run source baseline commit | `1f64f49ee9a8dd48280007e4df656e5f03e231ca` |
| Current workspace commit observed | `04ded4ca66a9a6308be2bc395c0e26ba1a98b8bf` |
| Historical evaluation authority validation | `PASS` |
| Run accepted generation | `phase19_aq_accepted_generation_641e6e313543f013` |

Because the target run was active while this audit read artifacts, counts are
reported as of the final audit snapshot above.

## Historical Repair Reconstruction

`HISTORICAL_ONE_YEN_TICK_REPAIR_FOUND = YES`

The historical repair lineage is:

| Phase | Role |
| --- | --- |
| Phase32-DA | Root-cause audit for 93180 ultra-low-price momentum/entry attribution. |
| Phase32-DB | Cross-sectional / multi-period SHADOW audit showing extreme one-yen tick cases could inflate apparent percentage/trend evidence. |
| Phase32-DC | SHADOW design for tick-quantization-aware momentum/trend evidence. |
| Phase32-DE | Production authority design for PIT minimum tick. |
| Phase32-DF | Production implementation of canonical PIT minimum-tick authority. |
| Phase32-DG | Production promotion of tick-normalized momentum/trend confidence into Candidate/BQ/Entry. |
| Phase32-DI | Repair ensuring BQ consumes current-run materialized tick evidence rather than empty placeholders. |

`HISTORICAL_REPAIR_PHASE = Phase32-DF / Phase32-DG / Phase32-DI`

`HISTORICAL_REPAIR_EXACT_SEMANTIC`

The accepted semantic is not a hard low-price ban. It is:

```text
low price != bad
large percentage movement != automatically strong momentum
apparent momentum/trend must be qualified by PIT minimum-tick-normalized robustness
```

Required effects:

- `QUANTIZED_CAUTION` or `LOW_CONFIDENCE_QUANTIZED` may remain eligible, but must not be treated as full independent confirmation of Candidate rank/score.
- BQ must cap FULL allocation into `REDUCED_ALLOCATION_ONLY`.
- Entry/SI must materialize caution such as `tick_quantization_caution_entry_reduced`.
- PC/PS still own target-weight and executable quantity; no hard minimum price filter or symbol blacklist is introduced.
- Missing/stale/non-authoritative tick evidence must be explicit item-scoped insufficiency/review, not a silent default or global bypass.

## Current Source Binding

`HISTORICAL_REPAIR_STILL_PRESENT_IN_SOURCE = YES`

Source reference graph:

| Boundary | Current source evidence |
| --- | --- |
| PIT minimum tick | `src/ai_fund_lab_v2/strategy/minimum_tick_authority.py` resolves `minimum_tick_authority.v1`, validates status, symbol/date/run binding, and rejects hash/future mismatches. |
| Technical Features | `src/ai_fund_lab_v2/strategy/input_materialization.py` resolves minimum tick from PIT security metadata and builds tick-normalized evidence into daily technical rows. |
| Tick semantics | `src/ai_fund_lab_v2/strategy/tick_quantization.py` emits `QUANTIZED_CAUTION`, `LOW_CONFIDENCE_QUANTIZED`, `ROBUST`, `ACCEPTABLE`, and reason codes. |
| Candidate | `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py` carries tick states into Candidate PIT quality surface and downgrades quantized cases to caution surface. |
| Strategy Intelligence / Entry | `src/ai_fund_lab_v2/strategy/strategy_intelligence.py` consumes tick robustness/momentum confidence; quantized caution forces reduced entry/admission. |
| BUY Quality | `src/ai_fund_lab_v2/strategy/buy_quality.py` turns quantized caution into `REDUCED_ALLOCATION_ONLY` and marks rank/score as non-independent confirmation. |
| Portfolio Construction | `src/ai_fund_lab_v2/strategy/portfolio_construction.py` preserves BQ tick states and applies low-price/tick/liquidity caps using canonical minimum tick when status is `KNOWN`. |
| Position Sizing / Runtime / Fill | PS preserves tick pct/tier and source lineage. Fill does not duplicate every tick semantic field, but carries source IDs back to BQ/PC authority. |

`HISTORICAL_REPAIR_STILL_BINDING = YES`

The target run artifacts show the contract binding in actual Production path:

| Metric | Count |
| --- | ---: |
| BQ rows scanned | 8,750 |
| BQ rows with `QUANTIZED_CAUTION` / `LOW_CONFIDENCE_QUANTIZED` | 493 |
| Quantized BQ rows by action | 401 `REDUCED_ALLOCATION_ONLY`, 86 `REJECT`, 6 `BUY_WAIT` |
| Quantized BQ rows that remained `FULL_ALLOCATION_ELIGIBLE` | 0 |
| PC rows retaining quantized state | 498 |
| PC quantized rows with positive target-like weight | 222 |
| Quantized BUY fills | 35 |
| Quantized BUY fills by source type | 26 `BUY_NEW`, 9 `BUY_ADD` |
| Quantized BUY fill notional | JPY 1,006,700 |
| Max quantized fill quantity | 8,400 shares |

The non-zero fill count is not itself a regression because the accepted
contract does not prohibit low-price/one-yen-tick securities. The regression
question is whether quantized evidence was allowed to act as FULL or
independent confirmation. In the scanned artifacts, it was not.

## Quantized Population

`QUANTIZED_CAUTION_POPULATION = 493 BQ rows / 10 symbols`

| Symbol | Quantized BQ rows | BQ action profile |
| --- | ---: | --- |
| 89180 | 153 | 152 reduced, 1 reject |
| 93180 | 137 | 71 reduced, 66 reject |
| 76470 | 135 | 133 reduced, 2 buy-wait |
| 21340 | 20 | 17 reduced, 3 reject |
| 17570 | 17 | 14 reduced, 3 reject |
| 37820 | 14 | 2 reduced, 1 buy-wait, 11 reject |
| 51030 | 9 | 8 reduced, 1 buy-wait |
| 65740 | 3 | 2 reduced, 1 buy-wait |
| 67400 | 3 | 1 reduced, 2 reject |
| 33500 | 2 | 1 reduced, 1 buy-wait |

`QUANTIZED_CAUTION_BUY_FILL_COUNT = 35`

`LOW_CONFIDENCE_QUANTIZED_BUY_FILL_COUNT = 35`

Representative large-share / low-price quantized BUY fills:

| Date | Symbol | Type | Qty | Price | Notional | BQ | Tick evidence | PC target |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | ---: |
| 2022-11-08 | 93180 | BUY_NEW | 8,400 | 4 | 33,600 | reduced | extreme; close levels 3; ticks traversed 2 | 0.030303 |
| 2023-01-17 | 93180 | BUY_NEW | 7,900 | 3 | 23,700 | reduced | extreme; close levels 2; ticks traversed 1 | 0.020000 |
| 2022-10-25 | 93180 | BUY_NEW | 6,500 | 5 | 32,500 | reduced | extreme; close levels 3; ticks traversed 2 | 0.031250 |
| 2023-06-12 | 89180 | BUY_NEW | 6,400 | 9 | 57,600 | reduced | extreme; close levels 2; ticks traversed 1 | 0.030303 |
| 2023-05-24 | 21340 | BUY_NEW | 4,300 | 10 | 43,000 | reduced | extreme; close levels 4; ticks traversed 3 | 0.025564 |
| 2022-10-26 | 89180 | BUY_NEW | 3,900 | 10 | 39,000 | reduced | extreme; close levels 2; ticks traversed 1 | 0.037037 |
| 2023-04-21 | 76470 | BUY_NEW | 3,800 | 26 | 98,800 | reduced | elevated; close levels 2; ticks traversed 1 | 0.071429 |
| 2022-10-03 | 89180 | BUY_NEW | 3,700 | 10 | 37,000 | reduced | extreme; close levels 3; ticks traversed 2 | 0.033636 |
| 2023-01-20 | 89180 | BUY_NEW | 3,400 | 10 | 34,000 | reduced | extreme; close levels 2; ticks traversed 1 | 0.028571 |
| 2023-01-13 | 89180 | BUY_NEW | 3,200 | 9 | 28,800 | reduced | extreme; close levels 3; ticks traversed 2 | 0.024667 |

Large share count is mostly arithmetic from very low prices. It is not, by
itself, evidence that quantization protection failed.

## 21340 Actual Path

`21340_IS_LOW_PRICE_QUANTIZATION_CASE = YES_FOR_2023_05_24; NO_FOR_2023_06_05_TO_2023_06_08`

### 2023-05-24 BUY_NEW

`21340_ACTUAL_PATH_EXPLAINED = YES`

Decision-time evidence:

| Boundary | Evidence |
| --- | --- |
| Technical Features | reference price 10, minimum tick 1, `single_tick_pct=0.10`, `QUANTIZED_CAUTION`, `LOW_CONFIDENCE_QUANTIZED`, 20d close levels 4, ticks traversed 3, net tick move -2 |
| BQ | `MEDIUM`, `REDUCED_ALLOCATION_ONLY`, `quality_score=0.682540`; reason codes include `tick_quantization_caution_caps_full_allocation` and `candidate_rank_score_not_independent_confirmation_under_tick_caution` |
| Entry/SI lineage | `tick_quantization_caution_entry_reduced` |
| PC | `BUY_NEW`, target 0.025564, accepted buy-new 0.025564, `price_tick_risk_tier=EXTREME`, `liquidity_capacity_cap_applied` |
| PS | adjusted target 0.017448; positive discrete executable quantity |
| Fill | BUY_NEW 4,300 shares at 10, JPY 43,000, campaign `pc-baa7e37cff833248-21340-0001` |
| Next day | 2023-05-25 PM EXIT and SELL_EXIT of the same 4,300 shares/campaign |

Judgment: 5/24 is a true one-yen-tick quantization case, but the actual path
shows caution materialized. The BUY was allowed only through reduced/capped
allocation and discrete sizing. This is consistent with the historical
contract.

### 2023-06-05 Through 2023-06-08

Decision-time evidence changed:

| Date | Ref price | single tick pct | Trend state | Momentum confidence | 20d close levels | 20d ticks traversed | BQ action | Fill |
| --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| 2023-06-05 | 24 | 0.041667 | `ACCEPTABLE` | `MODERATE_CONFIDENCE` | 10 | 16 | `FULL_ALLOCATION_ELIGIBLE` | BUY_NEW 2,400 at 17 |
| 2023-06-06 | 21 | 0.047619 | `ACCEPTABLE` | `MODERATE_CONFIDENCE` | 10 | 16 | `FULL_ALLOCATION_ELIGIBLE` | none |
| 2023-06-07 | 22 | 0.045455 | `ACCEPTABLE` | `MODERATE_CONFIDENCE` | 10 | 16 | `FULL_ALLOCATION_ELIGIBLE` | none |
| 2023-06-08 | 22 | 0.045455 | `ACCEPTABLE` | `MODERATE_CONFIDENCE` | 10 | 16 | `FULL_ALLOCATION_ELIGIBLE` | none |

This later path is low-price/elevated tick, but not `QUANTIZED_CAUTION` under
the current PIT evidence because close-level diversity and multi-tick movement
were materially stronger. BQ reason codes include
`low_price_but_tick_persistent_trend` and
`tick_normalized_evidence_preserves_normal_buy_quality_semantics`.

`21340_VIOLATES_HISTORICAL_CONTRACT = NO`

## Downstream / Runtime Regression Check

`OTHER_SIMILAR_CASES_FOUND = YES`

Similar low-price or high-share cases exist, especially 89180, 93180, 76470,
17570, 51030, and 37820. In all sampled quantized BUY fills, the BQ action was
`REDUCED_ALLOCATION_ONLY`; none were FULL.

`QUANTIZATION_EVIDENCE_LOST_DOWNSTREAM = NO_FOR_DECISION_AUTHORITY`

Details:

- All 493 quantized BQ rows were retained into PC with the quantized state.
- PS retained `single_tick_pct` / `price_tick_risk_tier` for the same rows.
- Fill artifacts do not duplicate every tick semantic field, but they preserve
  `source_decision_id`, `source_decision_type`, `order_plan_item_id`,
  `pending_item_id`, and campaign ID, allowing the tick authority to be traced
  back to BQ/PC.

This is acceptable for current decision authority. A future observability
improvement could copy compact tick semantic labels into fill context, but FI
did not find a correctness failure.

`RISK_ON_PACING_CONTRIBUTES = INDIRECT`

Risk-on / cash pacing can make small reduced/caution allocations executable
when budget exists. It did not override BQ tick caution into FULL, did not
erase item-scoped caution, and did not make Candidate rank independent under
tick caution. Any risk-on pacing redesign should remain separate from the
one-yen-tick correctness contract.

## Source / Registry / Rollback

`SOURCE_ROLLBACK_INVOLVED = NO_CONCRETE_EVIDENCE`

The run was created with source baseline commit
`1f64f49ee9a8dd48280007e4df656e5f03e231ca`, while the current workspace HEAD
observed during the audit was `04ded4ca66a9a6308be2bc395c0e26ba1a98b8bf`.
That difference reflects source movement after the run baseline was captured;
it is not evidence that the target run consumed the wrong source. The current
source still contains the DF/DG/DI tick contract.

`ACCEPTED_GENERATION_MISMATCH_INVOLVED = NO`

The run's `historical_evaluation_authority_validation.status` is `PASS`; the
fixed accepted generation is resolved and committed. No artifact/hash mismatch
was observed in the audited path.

## Classification

| Question | Judgment |
| --- | --- |
| Historical repair regressed? | `NO` |
| Correctness defect found? | `NO` |
| Production repair justified? | `NO` |
| Long-horizon validation safe to continue? | `YES` |

`HISTORICAL_REPAIR_REGRESSION_CONFIRMED = NO`

`CORRECTNESS_DEFECT_FOUND = NO`

`PRODUCTION_REPAIR_JUSTIFIED = NO`

`LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE = YES`

## Required Answers

| Required item | Answer |
| --- | --- |
| `HISTORICAL_ONE_YEN_TICK_REPAIR_FOUND` | `YES` |
| `HISTORICAL_REPAIR_PHASE` | `Phase32-DF / Phase32-DG / Phase32-DI` |
| `HISTORICAL_REPAIR_EXACT_SEMANTIC` | PIT minimum-tick-normalized trend/momentum robustness; no hard low-price ban; quantized caution caps FULL and makes rank non-independent |
| `HISTORICAL_REPAIR_STILL_PRESENT_IN_SOURCE` | `YES` |
| `HISTORICAL_REPAIR_STILL_BINDING` | `YES` |
| `QUANTIZED_CAUTION_POPULATION` | `493 BQ rows / 10 symbols` |
| `QUANTIZED_CAUTION_BUY_FILL_COUNT` | `35` |
| `LOW_CONFIDENCE_QUANTIZED_BUY_FILL_COUNT` | `35` |
| `21340_IS_LOW_PRICE_QUANTIZATION_CASE` | `YES_FOR_2023_05_24; NO_FOR_2023_06_05_TO_2023_06_08` |
| `21340_ACTUAL_PATH_EXPLAINED` | `YES` |
| `21340_VIOLATES_HISTORICAL_CONTRACT` | `NO` |
| `OTHER_SIMILAR_CASES_FOUND` | `YES` |
| `QUANTIZATION_EVIDENCE_LOST_DOWNSTREAM` | `NO_FOR_DECISION_AUTHORITY` |
| `RISK_ON_PACING_CONTRIBUTES` | `INDIRECT` |
| `SOURCE_ROLLBACK_INVOLVED` | `NO_CONCRETE_EVIDENCE` |
| `ACCEPTED_GENERATION_MISMATCH_INVOLVED` | `NO` |
| `HISTORICAL_REPAIR_REGRESSION_CONFIRMED` | `NO` |
| `CORRECTNESS_DEFECT_FOUND` | `NO` |
| `PRODUCTION_REPAIR_JUSTIFIED` | `NO` |
| `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE` | `YES` |

## Final Judgment

`PHASE32_FI_QUANTIZATION_CAUTION_ACTIVE_AND_BEHAVIOR_INTENDED`

