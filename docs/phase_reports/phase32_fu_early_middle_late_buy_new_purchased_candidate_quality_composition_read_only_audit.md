# Phase32-FU Early / Middle / Late BUY_NEW Purchased Candidate Quality Composition READ-ONLY Audit

## Scope

Target run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`

Completed-day evidence used: `2022-10-03` through `2023-08-04`, 208 completed business days.

The run also contains partial `2023-08-07` evidence, but `2023-08-07` is excluded from purchased BUY_NEW composition because run_state does not list it as completed and execution returned exit code 20. This avoids mixing moving or partial artifacts.

Compared periods:

| Period | Date range | Completed BD |
|---|---:|---:|
| EARLY | 2022-10-03 to 2023-02-28 | 100 |
| MIDDLE | 2023-03-01 to 2023-05-31 | 62 |
| LATE | 2023-06-01 to 2023-08-04 | 46 |

Evidence sources:

- `daily/<date>/execution/fills.json`
- `daily/<date>/strategy/portfolio_construction.json`
- `daily/<date>/strategy/portfolio_policy.json`
- `daily/<date>/strategy/market_context.json`
- `run_state.json`

BUY_NEW fill to PC member joins were complete: missing joined members = 0.

No future return, MFE/MAE, later SELL result, campaign outcome, or Historical PnL was used to define quality.

## Actual BUY_NEW Population

| Metric | EARLY | MIDDLE | LATE |
|---|---:|---:|---:|
| BUY_NEW fills | 191 | 111 | 79 |
| Unique symbols | 119 | 70 | 59 |
| BUY_NEW notional | ¥10,272,390 | ¥9,465,160 | ¥5,934,280 |
| BUY_NEW fills / BD | 1.910 | 1.790 | 1.717 |

BUY_ADD was not included in the main population.

## Purchased Rank Distribution

| Metric | EARLY | MIDDLE | LATE |
|---|---:|---:|---:|
| Median purchased rank | 15.0 | 16.0 | 21.0 |
| p25 | 10.0 | 11.0 | 12.5 |
| p75 | 23.5 | 23.0 | 28.5 |
| p90 | 37.0 | 27.0 | 39.0 |
| Deepest purchased rank | 43 | 44 | 44 |
| Top10 capital share | 24.8% | 27.5% | 31.4% |
| Rank20+ capital share | 36.3% | 25.7% | 42.8% |

Rank bucket notional share:

| Bucket | EARLY | MIDDLE | LATE |
|---|---:|---:|---:|
| Top5 | 6.0% | 18.8% | 20.8% |
| Top10 | 18.8% | 8.7% | 10.6% |
| 11-20 | 38.9% | 46.8% | 25.8% |
| 21-30 | 14.5% | 19.9% | 27.8% |
| 31-40 | 13.5% | 3.2% | 11.8% |
| 41-50 | 8.4% | 2.6% | 3.2% |

Interpretation: LATE purchased rank depth widened versus MIDDLE and slightly versus EARLY. However, rank was not quality by itself.

## BQ Composition

Normalized BQ composition:

| BQ bucket | EARLY count / notional | MIDDLE count / notional | LATE count / notional |
|---|---:|---:|---:|
| HIGH | 55 / 24.5% | 30 / 29.8% | 23 / 39.2% |
| REDUCED | 136 / 75.5% | 81 / 70.2% | 56 / 60.8% |

Exact `quality_action`:

| quality_action | EARLY | MIDDLE | LATE |
|---|---:|---:|---:|
| `REDUCED_ALLOCATION_ONLY` | 190 / 99.7% notional | 111 / 100.0% | 78 / 98.0% |
| `FULL_ALLOCATION_ELIGIBLE` | 1 / 0.3% | 0 / 0.0% | 1 / 2.0% |

The `HIGH` normalized bucket mostly reflects `quality_band=HIGH`; exact action remained overwhelmingly `REDUCED_ALLOCATION_ONLY`.

## Entry Composition

| Entry state | EARLY count / notional | MIDDLE count / notional | LATE count / notional |
|---|---:|---:|---:|
| `CONTINUATION_WITH_CAUTION` | 146 / 70.1% | 100 / 89.1% | 61 / 73.2% |
| `HEALTHY_CONTINUATION_ENTRY` | 45 / 29.9% | 11 / 10.9% | 18 / 26.8% |

LATE did not show a monotonic collapse in Entry quality; MIDDLE was the weakest period by Entry composition.

## Opportunity Quality / MCV Composition

Opportunity Quality:

| Class | EARLY | MIDDLE | LATE |
|---|---:|---:|---:|
| `STRONG` | 12 / 8.8% notional | 4 / 4.3% | 8 / 14.1% |
| `COMPARABLE_HIGH` | 33 / 21.1% | 7 / 6.7% | 10 / 12.7% |
| `COMPARABLE_MARGINAL` | 146 / 70.1% | 100 / 89.1% | 61 / 73.2% |

MCV:

| Class | EARLY | MIDDLE | LATE |
|---|---:|---:|---:|
| `ELIGIBLE_STRONG` | 45 / 29.9% notional | 11 / 10.9% | 18 / 26.8% |
| `ELIGIBLE_COMPARABLE` | 146 / 70.1% | 100 / 89.1% | 61 / 73.2% |

Existing strong semantic exists: YES.

Canonical definition used here: `canonical_opportunity_quality_class in {STRONG, COMPARABLE_HIGH}` or legacy coarse `marginal_capital_value_class = ELIGIBLE_STRONG`. This is existing Production/MCV semantic, not a new threshold.

Strong cohort share:

| Metric | EARLY | MIDDLE | LATE |
|---|---:|---:|---:|
| Count share | 23.6% | 9.9% | 22.8% |
| Notional share | 29.9% | 10.9% | 26.8% |

Weak-but-admitted semantic identifiable: YES.

Definition used here: bought BUY_NEW with existing semantics not classified as strong/high, typically `COMPARABLE_MARGINAL` / `ELIGIBLE_COMPARABLE`, usually paired with `REDUCED_ALLOCATION_ONLY` and/or `CONTINUATION_WITH_CAUTION`.

Weak-but-admitted share:

| Metric | EARLY | MIDDLE | LATE |
|---|---:|---:|---:|
| Count share | 76.4% | 90.1% | 77.2% |
| Notional share | 70.1% | 89.1% | 73.2% |

## Momentum / Trend / Risk Composition

Momentum confidence:

| State | EARLY | MIDDLE | LATE |
|---|---:|---:|---:|
| `HIGH_CONFIDENCE` | 45.0% count / 54.4% notional | 55.9% / 57.1% | 49.4% / 47.3% |
| `MODERATE_CONFIDENCE` | 46.1% / 40.6% | 38.7% / 39.5% | 44.3% / 48.5% |
| `LOW_CONFIDENCE_QUANTIZED` | 8.9% / 5.0% | 5.4% / 3.4% | 6.3% / 4.2% |

Momentum trajectory:

| State | EARLY | MIDDLE | LATE |
|---|---:|---:|---:|
| `HEALTHY_CONTINUATION` | 40.8% count / 46.2% notional | 27.9% / 29.0% | 43.0% / 45.1% |
| `MIXED_OR_UNRESOLVED` | 59.2% / 53.8% | 72.1% / 71.0% | 57.0% / 54.9% |

Trend:

| State | EARLY | MIDDLE | LATE |
|---|---:|---:|---:|
| `ROBUST` | 53.4% count / 67.5% notional | 49.5% / 55.8% | 55.7% / 54.1% |
| `ACCEPTABLE` | 37.7% / 27.5% | 45.0% / 40.8% | 38.0% / 41.7% |
| `QUANTIZED_CAUTION` | 8.9% / 5.0% | 5.4% / 3.4% | 6.3% / 4.2% |

Downside risk status was `PASS` for all 381 purchased BUY_NEW fills. Tick quantization status was `PASS` for all fills.

Conclusion: LATE does not show a broad increase in bought names with weak momentum/trend versus EARLY. MIDDLE is weaker by momentum trajectory.

## Combination Matrix

Top BQ x Entry combinations by period:

| Combination | EARLY | MIDDLE | LATE |
|---|---:|---:|---:|
| REDUCED + CAUTION_REDUCED | 93 / 46.2% notional | 71 / 59.7% | 39 / 36.0% |
| HIGH + CAUTION_REDUCED | 53 / 23.9% | 29 / 29.3% | 22 / 37.2% |
| REDUCED + HEALTHY_OR_FULL | 43 / 29.3% | 10 / 10.5% | 17 / 24.8% |
| HIGH + HEALTHY_OR_FULL | 2 / 0.6% | 1 / 0.5% | 1 / 2.0% |

The dominant purchased population in every period is not pure high-confidence full allocation. It is reduced/caution-compatible BUY_NEW admitted by current Production semantics.

## Entry Lift / MCV Compression

Broad lineage-level definition:

- Entry lift: non-strong or BQ-reduced evidence still admitted by `HEALTHY_CONTINUATION_ENTRY` or `CONTINUATION_WITH_CAUTION`.
- MCV compression: non-strong or BQ-reduced evidence represented by coarse `ELIGIBLE_STRONG` / `ELIGIBLE_COMPARABLE`.

| Metric | EARLY | MIDDLE | LATE |
|---|---:|---:|---:|
| Entry lift count share | 99.0% | 99.1% | 98.7% |
| Entry lift notional share | 99.4% | 99.5% | 98.0% |
| MCV compression count share | 99.0% | 99.1% | 98.7% |
| MCV compression notional share | 99.4% | 99.5% | 98.0% |

This does not prove a correctness defect. It shows the current BUY_NEW eligibility surface is broad by design: `REDUCED_ALLOCATION_ONLY` and `CONTINUATION_WITH_CAUTION` still frequently reach actual BUY_NEW.

## Capital Reach vs Quality

Across all periods:

| Purchased rank bucket | Count | Strong share | Weak-but-admitted share | Opportunity Quality mix |
|---|---:|---:|---:|---|
| Top5 | 35 | 2.9% | 97.1% | 34 COMPARABLE_MARGINAL, 1 COMPARABLE_HIGH |
| Top10 | 62 | 1.6% | 98.4% | 61 COMPARABLE_MARGINAL, 1 STRONG |
| 11-20 | 140 | 9.3% | 90.7% | 127 COMPARABLE_MARGINAL, 9 COMPARABLE_HIGH, 4 STRONG |
| 21-30 | 86 | 19.8% | 80.2% | 69 COMPARABLE_MARGINAL, 13 COMPARABLE_HIGH, 4 STRONG |
| 31-40 | 39 | 64.1% | 35.9% | 17 COMPARABLE_HIGH, 14 COMPARABLE_MARGINAL, 8 STRONG |
| 41-50 | 19 | 89.5% | 10.5% | 10 COMPARABLE_HIGH, 7 STRONG, 2 COMPARABLE_MARGINAL |

Deep rank strong cases exist: YES.

Representative cases:

- 2022-10-20 `69930`, rank 42, `STRONG`, `ELIGIBLE_STRONG`
- 2022-10-31 `47810`, rank 41, `STRONG`, `ELIGIBLE_STRONG`
- 2022-12-09 `43510`, rank 33, `STRONG`, `ELIGIBLE_STRONG`
- 2023-06-16 `50250`, rank 23, `STRONG`, `ELIGIBLE_STRONG`
- 2023-07-07 `65180`, rank 39, `STRONG`, `ELIGIBLE_STRONG`
- 2023-07-12 `75270`, rank 44, `COMPARABLE_HIGH`, `ELIGIBLE_STRONG`

Top rank non-strong cases exist: YES.

Representative cases:

- 2022-10-03 `37820`, rank 6, `COMPARABLE_MARGINAL`, `ELIGIBLE_COMPARABLE`
- 2022-10-05 `94320`, rank 1, `COMPARABLE_MARGINAL`, `ELIGIBLE_COMPARABLE`
- 2022-10-14 `92540`, rank 7, `COMPARABLE_MARGINAL`, `ELIGIBLE_COMPARABLE`
- 2023-06-05 `67310`, rank 5, `COMPARABLE_MARGINAL`, `ELIGIBLE_COMPARABLE`
- 2023-08-04 `79110`, rank 9, `COMPARABLE_MARGINAL`, `ELIGIBLE_COMPARABLE`

Therefore rank is not a sufficient quality proxy in either direction.

## Same-Regime Comparison

| Regime | EARLY strong / weak | MIDDLE strong / weak | LATE strong / weak |
|---|---:|---:|---:|
| BULL | 34.2% / 65.8% | 7.0% / 93.0% | 15.0% / 85.0% |
| RANGE | 23.7% / 76.3% | 9.5% / 90.5% | 50.0% / 50.0% |
| RECOVERY | 31.8% / 68.2% | 12.0% / 88.0% | 24.0% / 76.0% |
| CORRECTION | 0.0% / 100.0% | 25.0% / 75.0% | 0.0% / 100.0% |
| BEAR | 7.5% / 92.5% | none | none |

Same-regime LATE quality is weaker than EARLY in BULL and RECOVERY, stronger in RANGE, and inconclusive in CORRECTION due to only two LATE rows.

## Equity / Cash Association

Using daily cash and gross exposure fields from `portfolio_policy.incremental_capital_budget_envelope` as a contemporaneous size proxy:

| Period | BUY_NEW days | Avg cash | Avg equity proxy | Median deepest purchased rank | Avg weak share / BUY day |
|---|---:|---:|---:|---:|---:|
| EARLY | 89 | ¥286,199 | ¥1,163,445 | 23 | 71.1% |
| MIDDLE | 53 | ¥291,918 | ¥1,460,286 | 22 | 90.1% |
| LATE | 36 | ¥282,385 | ¥1,708,904 | 26 | 74.8% |

Equity proxy increases while median deepest purchased rank expands by LATE. Cash level itself is similar across periods. This is consistent with capital scale reaching farther into the eligible set, but not conclusive by itself.

## Unlimited-Capital / Eligibility vs Priority

`UNLIMITED_CAPITAL_INVESTMENT_ELIGIBILITY_SEMANTIC`: PARTIAL.

The current artifacts have actual target membership, BQ action, Entry admission, MCV class, and PC target/lot feasibility. They identify what Production admitted under current constraints. They do not cleanly state that every admitted BUY_NEW is an equally desirable "buy aggressively if unlimited capital" investment option.

`ELIGIBILITY_AND_PRIORITY_CURRENTLY_CLEANLY_SEPARATED`: PARTIAL/NO.

Evidence shows the same coarse buy path admits both `ELIGIBLE_STRONG` and `ELIGIBLE_COMPARABLE`, and exact BQ action is overwhelmingly `REDUCED_ALLOCATION_ONLY`. Capital priority exists, but the artifact semantics still blur:

- admissible reduced participation
- current opportunity quality
- capital priority among alternatives
- notional sizing actually purchased

This supports further design analysis but not a correctness repair.

## Candidate Admission Widening Judgment

Classification: `MIXED`.

Supporting observations:

- `LATE_STRONG_SHARE_DECLINES` versus EARLY by count share: 23.6% to 22.8%, only slightly; notional 29.9% to 26.8%.
- MIDDLE is the clear weak-quality trough: strong notional only 10.9%, weak-but-admitted notional 89.1%.
- LATE rank depth widens: median rank 21, rank20+ notional 42.8%.
- Weak-but-admitted remains large in all periods, but does not monotonically increase into LATE.
- Entry lift and MCV compression are high across all periods, not a LATE-only phenomenon.

## Capital-Scale Hypothesis Relevance

`CAPITAL_SCALE_HYPOTHESIS_RELEVANCE`: PARTIALLY_SUPPORTED.

The evidence is consistent with larger equity reaching deeper into the eligible set by LATE: average equity proxy rises and median deepest purchased rank rises. However, average cash does not rise materially and LATE strong share partially recovers from MIDDLE, so the 1M run alone does not prove capital scale causality.

10M follow-up metrics to freeze:

- strong cohort share
- weak-but-admitted share
- Entry lift share
- MCV compression share
- purchased rank depth
- BUY_NEW notional share
- position breadth
- Cash / Exposure
- same-regime strong/weak composition

## Required Answers

- `EARLY_BUY_NEW_COUNT`: 191
- `MIDDLE_BUY_NEW_COUNT`: 111
- `LATE_BUY_NEW_COUNT`: 79
- `EARLY_MEDIAN_PURCHASED_RANK`: 15.0
- `MIDDLE_MEDIAN_PURCHASED_RANK`: 16.0
- `LATE_MEDIAN_PURCHASED_RANK`: 21.0
- `EARLY_DEEPEST_PURCHASED_RANK`: 43
- `MIDDLE_DEEPEST_PURCHASED_RANK`: 44
- `LATE_DEEPEST_PURCHASED_RANK`: 44
- `EARLY_TOP10_CAPITAL_SHARE`: 24.8%
- `MIDDLE_TOP10_CAPITAL_SHARE`: 27.5%
- `LATE_TOP10_CAPITAL_SHARE`: 31.4%
- `EARLY_RANK20PLUS_CAPITAL_SHARE`: 36.3%
- `MIDDLE_RANK20PLUS_CAPITAL_SHARE`: 25.7%
- `LATE_RANK20PLUS_CAPITAL_SHARE`: 42.8%
- `BQ_COMPOSITION_EARLY_MIDDLE_LATE`: HIGH 24.5% / 29.8% / 39.2% notional; REDUCED 75.5% / 70.2% / 60.8% notional. Exact action remains REDUCED_ALLOCATION_ONLY at 99.7% / 100.0% / 98.0% notional.
- `ENTRY_COMPOSITION_EARLY_MIDDLE_LATE`: HEALTHY_OR_FULL 29.9% / 10.9% / 26.8% notional; CAUTION_REDUCED 70.1% / 89.1% / 73.2% notional.
- `MCV_COMPOSITION_EARLY_MIDDLE_LATE`: ELIGIBLE_STRONG 29.9% / 10.9% / 26.8% notional; ELIGIBLE_COMPARABLE 70.1% / 89.1% / 73.2% notional.
- `EXISTING_STRONG_OPPORTUNITY_SEMANTIC_EXISTS`: YES
- `STRONG_COHORT_SHARE_EARLY_MIDDLE_LATE`: count 23.6% / 9.9% / 22.8%; notional 29.9% / 10.9% / 26.8%
- `WEAK_BUT_ADMITTED_SEMANTIC_IDENTIFIABLE`: YES
- `WEAK_BUT_ADMITTED_SHARE_EARLY_MIDDLE_LATE`: count 76.4% / 90.1% / 77.2%; notional 70.1% / 89.1% / 73.2%
- `ENTRY_LIFT_SHARE_EARLY_MIDDLE_LATE`: notional 99.4% / 99.5% / 98.0%, broad lineage-level
- `MCV_COMPRESSION_SHARE_EARLY_MIDDLE_LATE`: notional 99.4% / 99.5% / 98.0%, broad lineage-level
- `DEEP_RANK_STRONG_CASES_EXIST`: YES
- `TOP_RANK_NON_STRONG_CASES_EXIST`: YES
- `SAME_REGIME_LATE_QUALITY_WEAKER`: MIXED
- `EQUITY_CASH_ASSOCIATED_WITH_QUALITY_BREADTH`: PARTIALLY_SUPPORTED for equity proxy, not supported by cash alone
- `UNLIMITED_CAPITAL_INVESTMENT_ELIGIBILITY_SEMANTIC`: PARTIAL
- `ELIGIBILITY_AND_PRIORITY_CURRENTLY_CLEANLY_SEPARATED`: PARTIAL/NO
- `CANDIDATE_ADMISSION_WIDENING_JUDGMENT`: MIXED
- `CAPITAL_SCALE_HYPOTHESIS_RELEVANCE`: PARTIALLY_SUPPORTED
- `CORRECTNESS_DEFECT_FOUND`: NO
- `DESIGN_REFINEMENT_JUSTIFIED`: YES
- `PRODUCTION_REPAIR_JUSTIFIED`: NO
- `NEXT_DESIGN_DIRECTION`: BOTH_ELIGIBILITY_AND_PRIORITY_NEED_REVIEW
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE`: YES, no Runtime/authority correctness defect found by this audit

## Controls

- `PRODUCTION_CHANGED`: NO
- `SHADOW_CHANGED`: NO
- `TARGET_RUN_MUTATED`: NO
- `RUNTIME_STATE_MUTATED`: NO
- `FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT`: NO

## Final Judgment

`PHASE32_FU_BUY_NEW_PURCHASED_QUALITY_COMPOSITION_CHANGED_MIXED_RANK_DEPTH_WIDENED_WEAK_ADMITTED_BROAD_ALL_PERIODS_NO_CORRECTNESS_DEFECT_DESIGN_REFINEMENT_JUSTIFIED`
