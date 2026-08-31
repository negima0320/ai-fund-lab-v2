# Phase32-AT - BULL vs RANGE / RECOVERY Equity Growth Mechanism READ-ONLY Characterization

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Trusted evidence window: `2022-10-03` through `2023-10-10`
- Covered business days: 252
- PnL basis: daily change in `cash + new_total_market_value` from `current_valuation_refresh/valuation_projection.json`
- First day PnL: excluded from daily PnL statistics because no prior trusted in-run equity point exists
- Audit mode: READ-ONLY characterization

No code, config, runtime state, Strategy parameter, threshold, weight, cap, Regime, Risk Pacing, Market Quality, Cash, BUY_NEW, or BUY_ADD behavior was changed. No fresh-run, resume, replay, recover, or long Historical command was executed.

## Evidence Used

Primary artifacts:

- `daily/*/strategy/market_context.json`
- `daily/*/strategy/portfolio_policy.json`
- `daily/*/strategy/buy_quality_decisions.json`
- `daily/*/strategy/portfolio_construction.json`
- `daily/*/strategy/source_manifest.json`
- `daily/*/current_valuation_refresh/valuation_projection.json`
- `daily/*/positions/position_campaigns.json`
- `daily/*/execution/fills.json`
- PIT sector source referenced by source manifests: `raw/jquants/listed_issues/data.parquet`

Future outcomes were used only for post-hoc characterization of realized daily equity movement. They were not used to derive Production rules, thresholds, weights, or recommendations.

## A - Regime Performance

Regime performance over the trusted window:

| Regime | BD | Cumulative daily PnL | Mean daily PnL | Median daily PnL | Positive-day rate | Mean positive day | Mean negative day | P90 positive | P95 positive | Largest positive | Largest negative | Avg exposure | Median exposure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BULL | 111 | 45,950 | 413.96 | 2,800 | 58.56% | 18,905 | -25,715 | 47,120 | 94,348 | 113,600 | -124,200 | 0.812103 | 0.855313 |
| RANGE | 46 | 584,670 | 12,710.22 | 7,050 | 67.39% | 35,872 | -35,157 | 96,470 | 98,620 | 100,900 | -103,820 | 0.790139 | 0.808030 |
| RECOVERY | 46 | 169,200 | 3,678.26 | 3,740 | 65.22% | 24,331 | -35,045 | 86,166 | 99,032 | 123,900 | -116,600 | 0.807056 | 0.832182 |
| BEAR | 33 | 3,950 | 123.44 | -230 | 50.00% | 14,769 | -14,523 | 38,965 | 48,670 | 59,890 | -79,360 | 0.570916 | 0.571883 |
| CORRECTION | 16 | -161,570 | -10,098.12 | 4,920 | 56.25% | 27,747 | -58,756 | 77,504 | 88,572 | 99,640 | -123,280 | 0.741005 | 0.774371 |

Findings:

- Highest cumulative PnL: RANGE.
- Highest mean daily PnL: RANGE.
- Highest median daily PnL: RANGE.
- Largest positive day: RECOVERY, `2023-06-09`, +123,900 JPY.
- BULL is not loss-making overall, but its cumulative contribution is much smaller than RANGE / RECOVERY in this 252BD window.
- CORRECTION has positive median PnL but large negative tails dominate cumulative PnL.

## B - Equity Acceleration Episodes

Post-hoc descriptive state used for characterization only:

- `STRONG_UP`: daily positive PnL at or above the observed positive-day P90.
- `SLOW_UP`: positive daily PnL below that P90.
- `FLAT`: near-zero daily movement.
- `DRAWDOWN`: negative movement outside the flat band.

Positive-day P90: 85,860 JPY.
Positive-day P95: 98,170 JPY.

`STRONG_UP` days:

| Date | Regime | Daily PnL |
| --- | --- | ---: |
| 2023-06-09 | RECOVERY | 123,900 |
| 2023-07-03 | BULL | 113,600 |
| 2023-05-01 | RECOVERY | 108,630 |
| 2023-05-26 | RANGE | 100,900 |
| 2023-06-21 | BULL | 100,700 |
| 2023-05-31 | RANGE | 100,200 |
| 2023-07-14 | CORRECTION | 99,640 |
| 2023-07-06 | BULL | 99,300 |
| 2023-07-10 | RANGE | 97,040 |
| 2023-06-27 | BULL | 96,560 |
| 2023-08-02 | RANGE | 96,470 |
| 2023-08-07 | RANGE | 92,540 |
| 2023-07-21 | RANGE | 91,050 |
| 2023-04-21 | RECOVERY | 87,300 |
| 2023-04-03 | RECOVERY | 86,040 |
| 2023-08-28 | RANGE | at or above P90 threshold |

March-April 2023:

- Covered days: 42.
- Regime composition: BULL 16, RANGE 11, RECOVERY 9, CORRECTION 3, BEAR 3.
- Cumulative PnL: +263,070 JPY.
- Strong-up dates in this interval: `2023-04-03` and `2023-04-21`, both RECOVERY.

Interpretation:

RANGE and RECOVERY do produce many of the large acceleration days. However, the largest daily jumps are not a clean regime-wide phenomenon; they are strongly affected by a repeated single-security adjusted valuation movement.

## C - Candidate Supply

Candidate supply by regime:

| Regime | Candidates/day | HIGH/day | HIGH rate | FULL/day | FULL rate | Positive-edge/day | Deployable/day | Strong security rows/day |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BULL | 50.00 | 7.87 | 15.75% | 4.69 | 9.39% | 5.64 | 2.95 | 3.62 |
| RANGE | 50.00 | 6.30 | 12.61% | 4.67 | 9.35% | 5.74 | 3.91 | 3.50 |
| RECOVERY | 50.00 | 6.39 | 12.78% | 3.89 | 7.78% | 5.15 | 3.13 | 3.09 |
| BEAR | 50.00 | 4.18 | 8.36% | 3.48 | 6.97% | 5.67 | 3.33 | 3.33 |
| CORRECTION | 50.00 | 6.56 | 13.13% | 5.00 | 10.00% | 6.25 | 2.38 | 3.56 |

Finding:

`IS_BULL_CANDIDATE_QUALITY_HIGHEST = YES`

BULL has the highest HIGH/day and tied-high FULL/day substrate. That does not automatically translate into highest realized equity growth.

## D - Candidate Abundance / Selection Difficulty

Strong candidate selection / rejection:

| Regime | Strong rows | Selected | Selected rate | Rejected strong | REENTRY/continuation blocked | BUY_WAIT | Lot/cap | Lost to competition |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BULL | 402 | 111 | 27.61% | 291 | 204 | 62 | 21 | 2 |
| RANGE | 161 | 48 | 29.81% | 113 | 77 | 19 | 16 | 1 |
| RECOVERY | 142 | 33 | 23.24% | 109 | 89 | 11 | 9 | 0 |
| BEAR | 110 | 34 | 30.91% | 76 | 60 | 9 | 7 | 0 |
| CORRECTION | 57 | 6 | 10.53% | 51 | 40 | 4 | 5 | 1 |

Strong candidate rank dispersion:

| Regime | Avg rank among strong rows | P90 rank among strong rows |
| --- | ---: | ---: |
| BULL | 3.40 | 6 |
| RANGE | 3.27 | 6 |
| RECOVERY | 2.94 | 6 |
| BEAR | 3.11 | 6 |
| CORRECTION | 3.86 | 7 |

Finding:

`IS_BULL_CANDIDATE_ABUNDANCE_CAUSING_SELECTION_DIFFICULTY = WEAK / NOT PROVEN`

BULL has more strong rows, but the direct loss-to-competition count among strong rows is only 2. Most rejected strong rows fail REENTRY / continuation, BUY_WAIT, or lot/cap boundaries. Candidate abundance may contribute to ordinary capital competition pressure, but it is not the primary proven mechanism in current artifacts.

## E - Top Candidate Separation

Existing opportunity score separation:

| Regime | Mean rank1-rank2 score gap | Mean rank1-rank5 score gap |
| --- | ---: | ---: |
| BULL | 0.086789 | 0.289359 |
| RANGE | 0.103869 | 0.318388 |
| RECOVERY | 0.070995 | 0.312928 |
| BEAR | 0.104053 | 0.350083 |
| CORRECTION | 0.084289 | 0.353652 |

Finding:

`ARE_RANGE_RECOVERY_TOP_OPPORTUNITIES_MORE_CLEARLY_SEPARATED = RANGE YES, RECOVERY MIXED`

RANGE shows a larger rank1-rank2 and rank1-rank5 separation than BULL. RECOVERY has a smaller rank1-rank2 gap than BULL but a larger rank1-rank5 gap. This supports clearer RANGE top separation, but not a broad RANGE/RECOVERY claim.

## F - Capital Concentration

Portfolio concentration and capital state:

| Regime | Avg open position count | 100-share position share | Top1 position weight | Top3 position weight | Avg cash | Avg exposure | NEW fills | ADD fills |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BULL | 11.7 | 84.2% | 0.1684 | 0.4206 | 265,851 | 0.8121 | 172 | 5 |
| RANGE | 9.9 | 87.9% | 0.1735 | 0.4227 | 279,245 | 0.7901 | 81 | 2 |
| RECOVERY | 10.8 | 85.8% | 0.1684 | 0.4197 | 274,297 | 0.8071 | 73 | 0 |
| BEAR | 7.6 | 78.2% | 0.1709 | 0.3753 | 535,713 | 0.5709 | 56 | 2 |
| CORRECTION | 9.8 | 96.1% | 0.1669 | 0.4121 | 391,981 | 0.7410 | 13 | 0 |

Finding:

`DOES_BULL_HOLD_MORE_FRAGMENTED_PORTFOLIOS = PARTIAL`

BULL holds more positions on average than RANGE and BEAR, but Top1 / Top3 position weights are similar across BULL, RANGE, and RECOVERY. Fragmentation is present as higher position count and high 100-share share, but not enough to explain RANGE outperformance alone.

## G - Portfolio Momentum Breadth

Held-position momentum / continuation evidence:

| Regime | Held continuation PASS rate | Capital-weighted continuation PASS | Held strong-state rate | Capital-weighted strong-state |
| --- | ---: | ---: | ---: | ---: |
| BULL | 1.000 | 0.797 | 0.109 | 0.061 |
| RANGE | 1.000 | 0.751 | 0.103 | 0.041 |
| RECOVERY | 1.000 | 0.769 | 0.076 | 0.033 |
| BEAR | 0.970 | 0.558 | 0.117 | 0.039 |
| CORRECTION | 1.000 | 0.738 | 0.022 | 0.010 |

Finding:

`WHICH_REGIME_HAS_HIGHEST_PORTFOLIO_MOMENTUM_BREADTH = BULL by capital-weighted continuation; BEAR by count-based strong-state rate`

RANGE / RECOVERY do not show higher held-position strong-state breadth than BULL. BULL has the highest capital-weighted continuation evidence.

## H - Internal Portfolio Cohesion

Internal cohesion:

- Held continuation PASS is near-universal in BULL/RANGE/RECOVERY/CORRECTION.
- Capital-weighted continuation is highest in BULL.
- Strong-state breadth is not materially higher in RANGE / RECOVERY.

Finding:

`DO_RANGE_RECOVERY_HAVE_HIGHER_INTERNAL_COHESION = NO`

The evidence does not support the idea that RANGE / RECOVERY produce fewer but more directionally coherent holdings. Their equity acceleration is better explained by event concentration / valuation contribution and some RANGE top-candidate separation, not broad internal momentum cohesion.

## I - Sector / Industry Concentration

PIT sector evidence was available via J-Quants listed issues referenced by `source_manifest.json`.

Sector concentration by regime:

| Regime | Avg sectors represented | Top1 sector weight | Top3 sector weight |
| --- | ---: | ---: | ---: |
| BULL | 8.34 | 0.240 | 0.535 |
| RANGE | 6.28 | 0.291 | 0.582 |
| RECOVERY | 7.52 | 0.254 | 0.544 |
| BEAR | 5.58 | 0.211 | 0.444 |
| CORRECTION | 6.69 | 0.261 | 0.543 |

Strong-up vs flat:

| State | Days | Avg sectors | Top1 sector weight | Top3 sector weight |
| --- | ---: | ---: | ---: | ---: |
| STRONG_UP | 16 | 6.56 | 0.263 | 0.574 |
| FLAT | 53 | 8.25 | 0.231 | 0.504 |

Finding:

`IS_SECTOR_CONCENTRATION_MATERIALLY_DIFFERENT = YES, MODEST`

RANGE and STRONG_UP periods are modestly more sector-concentrated than BULL/FLAT. This supports a weak-to-moderate sector/theme concentration mechanism, but not as a standalone causal proof.

Representative top sectors on large positive days:

| Date | Regime | Daily PnL | Top sectors by equity weight |
| --- | --- | ---: | --- |
| 2023-06-09 | RECOVERY | 123,900 | 情報・通信業 25.6%, サービス業 21.1%, 電気機器 18.6% |
| 2023-07-03 | BULL | 113,600 | 情報・通信業 20.8%, 不動産業 18.3%, 電気機器 18.2% |
| 2023-05-01 | RECOVERY | 108,630 | 電気機器 23.8%, 倉庫・運輸関連業 17.0%, 機械 13.8% |
| 2023-05-26 | RANGE | 100,900 | 電気機器 19.4%, 不動産業 18.9%, 情報・通信業 12.7% |
| 2023-05-31 | RANGE | 100,200 | 電気機器 18.9%, 不動産業 18.6%, サービス業 14.7% |

## J - Large Positive Day Attribution

Largest positive days are dominated by a few securities, usually one security.

Refined contribution method:

- Compare previous-day and current-day open campaign `current_market_value` for common held symbols.
- Separate new position market value and exited prior value from common-position mark-to-market movement.
- Treat `quantity_basis=ADJUSTED` and `valuation_price_basis=ADJUSTED` as adjusted-basis valuation evidence, not raw corporate-action-free price movement.

Top large-day attribution:

| Date | Regime | PnL | Common-position delta | Dominant symbol | Dominant delta | Classification |
| --- | --- | ---: | ---: | --- | ---: | --- |
| 2023-06-09 | RECOVERY | 123,900 | 103,600 | 67310 | +100,000 | ONE_SECURITY_DOMINATED |
| 2023-07-03 | BULL | 113,600 | 106,100 | 67310 | +100,000 | ONE_SECURITY_DOMINATED |
| 2023-05-01 | RECOVERY | 108,630 | 101,830 | 67310 | +100,000 | ONE_SECURITY_DOMINATED |
| 2023-05-26 | RANGE | 100,900 | 93,600 | 67310 | +100,000 | ONE_SECURITY_DOMINATED |
| 2023-06-21 | BULL | 100,700 | 98,400 | 67310 | +100,000 | ONE_SECURITY_DOMINATED |
| 2023-05-31 | RANGE | 100,200 | 98,300 | 67310 | +100,000 | ONE_SECURITY_DOMINATED |
| 2023-07-14 | CORRECTION | 99,640 | 94,840 | 67310 | +100,000 | ONE_SECURITY_DOMINATED |
| 2023-07-06 | BULL | 99,300 | 90,700 | 67310 | +100,000 | ONE_SECURITY_DOMINATED |

`67310` repeatedly moved from adjusted valuation price 2,000 to 3,000 for 100 shares on large positive days, contributing approximately +100,000 JPY. This explains much of the visual acceleration pattern.

Finding:

`ARE_LARGE_POSITIVE_DAYS_BROAD_OR_FEW_SECURITY_DOMINATED = ONE_SECURITY_DOMINATED / FEW_SECURITY_DOMINATED`

`HOW_MUCH_OF_LARGE_DAY_BEHAVIOR_IS_VALUATION_ARTIFACT = MATERIAL`

This does not reopen Phase32-Y measurement trust. It means large-day behavior should be characterized as adjusted-basis / single-security dominated rather than broad regime-driven portfolio acceleration.

## K - BULL Underperformance Mechanism

Classification:

`MIXED, WITH VALUATION_ARTIFACT_AND_NORMAL_VARIANCE_MORE EVIDENCED_THAN SELECTION_DIFFICULTY`

Mechanism evidence:

| Mechanism | Evidence status | Notes |
| --- | --- | --- |
| CANDIDATE_ABUNDANCE_SELECTION_DIFFICULTY | Weak / not primary | BULL strong rows are numerous, but direct lost-to-competition among strong rows is only 2. |
| CAPITAL_FRAGMENTATION | Partial | BULL has more open positions, but Top1/Top3 weights are similar to RANGE/RECOVERY. |
| HIGH_EXPOSURE_DOWNSIDE | Present | BULL has high exposure and several large negative days, including -124,200 and -120,270. |
| WEAK_INTERNAL_COHESION | Not supported | BULL has the highest capital-weighted continuation evidence. |
| SECTOR_DILUTION | Partial | BULL has more sectors represented and lower top-sector concentration than RANGE. |
| WINNER_GRADUATION_WEAKNESS | Background limitation | Already recorded in Phase32-AR, but not uniquely explanatory for BULL vs RANGE here. |
| NORMAL_VARIANCE | Plausible | 252BD window and large single-security effects make attribution noisy. |
| NOT_ACTUALLY_UNDERPERFORMING | No | BULL cumulative and mean daily PnL are lower than RANGE / RECOVERY. |

## L - RANGE / RECOVERY Strength Mechanism

Classification:

`MIXED`

Evidence:

- RANGE has highest cumulative, mean, and median daily PnL.
- RANGE has stronger top-candidate separation than BULL.
- RANGE / STRONG_UP days show modestly higher sector concentration.
- RECOVERY contains the single largest positive day and March-April strong-up dates.
- Large positive days are heavily influenced by `67310` adjusted-basis jumps.

Mechanism classification:

| Mechanism | Classification |
| --- | --- |
| CLEARER_TOP_OPPORTUNITY | RANGE supported, RECOVERY mixed |
| BETTER_PORTFOLIO_COHESION | Not supported |
| STRONGER_SECTOR_CONCENTRATION | Modestly supported |
| LOWER_SELECTION_NOISE | Weakly supported for RANGE only |
| BETTER_CAPITAL_CONCENTRATION | Not strongly supported by Top1/Top3 position weights |
| TRANSITION_MOMENTUM_CAPTURE | Plausible for RECOVERY March-April, not proven |
| VALUATION_ARTIFACT | Material |
| MIXED | Best classification |

## M - STRONG_UP vs FLAT

STRONG_UP vs FLAT comparison:

| Metric | STRONG_UP | FLAT |
| --- | ---: | ---: |
| Days | 16 | 53 |
| Regime composition | RANGE 7, RECOVERY 4, BULL 4, CORRECTION 1 | BULL 27, RECOVERY 12, BEAR 11, RANGE 2, CORRECTION 1 |
| Avg HIGH/day | 7.19 | about 7.10 |
| Avg FULL/day | 4.75 | about 4.76 |
| Strong selected rate | 24.07% | about 21.74% |
| Held continuation PASS rate | 1.000 | about 1.000 |
| Held strong-state rate | 0.126 | about 0.072 |
| Avg position count | 9.9 | about 11.4 |
| 100-share starter share | 0.867 | about 0.898 |
| Top1 position weight | 0.1853 | about 0.1607 |
| Top3 position weight | 0.4577 | about 0.4061 |
| Avg exposure | 0.7832 | about 0.786 |
| Avg cash | 348,800 | about 287,890 |
| Avg sectors represented | 6.56 | 8.25 |
| Top3 sector weight | 0.574 | 0.504 |

Finding:

STRONG_UP is distinguished less by raw candidate supply and more by:

- fewer positions;
- modestly stronger position concentration;
- higher held strong-state rate;
- higher sector concentration;
- single-security adjusted-basis jumps.

Exposure is not materially higher in STRONG_UP than FLAT.

## N - Falsification

### H0 - Regime itself explains most Equity-growth differences.

Evidence for:

- RANGE has highest cumulative / mean / median PnL.
- STRONG_UP composition is RANGE-heavy.

Evidence against:

- BULL also contributes major STRONG_UP days.
- Large jumps are dominated by the same security across regimes.
- Portfolio state and valuation effects cut across regimes.

Verdict: `PARTIAL`

### H1 - Candidate abundance / selection difficulty explains BULL behavior.

Evidence for:

- BULL has the highest HIGH supply.
- BULL has many rejected strong rows.

Evidence against:

- Direct lost-to-competition among BULL strong rows is only 2.
- BULL selected strong rate is close to RANGE and above RECOVERY.
- Rejections are mostly lifecycle/BQ/lot-cap, not abundance itself.

Verdict: `WEAK`

### H2 - Portfolio momentum breadth / cohesion explains the difference.

Evidence for:

- STRONG_UP has higher held strong-state rate than FLAT.

Evidence against:

- RANGE/RECOVERY do not exceed BULL in capital-weighted continuation.
- Held continuation is almost universally PASS across regimes.

Verdict: `PARTIAL`

### H3 - Capital concentration / fragmentation explains the difference.

Evidence for:

- STRONG_UP has fewer positions and higher Top1/Top3 position weights than FLAT.
- BULL has more positions than RANGE.

Evidence against:

- Regime-level Top1/Top3 position weights are similar among BULL/RANGE/RECOVERY.

Verdict: `PARTIAL`

### H4 - Sector/theme concentration explains the difference.

Evidence for:

- RANGE has fewer sectors and higher Top1/Top3 sector weight than BULL.
- STRONG_UP has higher Top3 sector concentration than FLAT.

Evidence against:

- Sector concentration is modest, and large-day attribution is more security-specific than sector-wide.

Verdict: `PARTIAL`

### H5 - RANGE/RECOVERY transition timing captures momentum waves better.

Evidence for:

- March-April acceleration strong-up dates are RECOVERY.
- RANGE has the best cumulative and mean daily PnL.

Evidence against:

- No causal rule can be inferred from PnL.
- Large positive days are dominated by adjusted-basis `67310` behavior.

Verdict: `PLAUSIBLE_NOT_PROVEN`

### H6 - Observed difference is largely valuation artifact / noise.

Evidence for:

- Top positive days repeatedly include `67310` +100,000 JPY adjusted valuation movement.
- The same large contribution appears across RECOVERY, RANGE, BULL, and CORRECTION.

Evidence against:

- RANGE also has better median PnL and positive-day rate, not only one day.

Verdict: `MATERIAL_BUT_NOT_SOLE`

### H7 - Mixed interaction is required.

Evidence for:

- Regime, top-candidate separation, sector concentration, position concentration, and adjusted valuation effects all explain part of the pattern.
- No single mechanism fully explains BULL vs RANGE/RECOVERY.

Evidence against:

- None strong enough to reject mixed interpretation.

Verdict: `BEST_SUPPORTED`

## O - Decision

Decision:

`MIXED_INTERACTION`

Secondary characterization:

`PORTFOLIO_INTERNAL_STATE_AND_VALUATION_ARTIFACT_MORE_EXPLANATORY_THAN_REGIME_ALONE`

No Production change is justified.

## Required Final Answers

1. `WHICH_REGIME_HAS_HIGHEST_CUMULATIVE_PNL`
   - RANGE.

2. `WHICH_HAS_HIGHEST_MEAN_AND_MEDIAN_DAILY_PNL`
   - RANGE for both mean and median.

3. `WHICH_REGIME_PRODUCES_THE_LARGEST_POSITIVE_DAYS`
   - The single largest positive day is RECOVERY. The STRONG_UP set is RANGE-heavy.

4. `IS_BULL_CANDIDATE_QUALITY_HIGHEST`
   - YES. BULL has the highest HIGH/day and tied-high FULL/day supply.

5. `IS_BULL_CANDIDATE_ABUNDANCE_CAUSING_SELECTION_DIFFICULTY`
   - WEAK / NOT PROVEN as primary mechanism.

6. `ARE_RANGE_RECOVERY_TOP_OPPORTUNITIES_MORE_CLEARLY_SEPARATED`
   - RANGE YES; RECOVERY MIXED.

7. `DOES_BULL_HOLD_MORE_FRAGMENTED_PORTFOLIOS`
   - PARTIAL. BULL has more positions and more sector dispersion, but similar Top1/Top3 position weights.

8. `WHICH_REGIME_HAS_HIGHEST_PORTFOLIO_MOMENTUM_BREADTH`
   - BULL by capital-weighted continuation; BEAR by count-based held strong-state rate.

9. `DO_RANGE_RECOVERY_HAVE_HIGHER_INTERNAL_COHESION`
   - NO.

10. `IS_SECTOR_CONCENTRATION_MATERIALLY_DIFFERENT`
    - YES, modestly. RANGE and STRONG_UP are more sector-concentrated than BULL/FLAT.

11. `ARE_LARGE_POSITIVE_DAYS_BROAD_OR_FEW_SECURITY_DOMINATED`
    - ONE_SECURITY_DOMINATED / FEW_SECURITY_DOMINATED, usually dominated by `67310`.

12. `HOW_MUCH_OF_LARGE_DAY_BEHAVIOR_IS_VALUATION_ARTIFACT`
    - MATERIAL. Repeated adjusted-basis `67310` movements explain much of the largest daily jumps.

13. `WHAT_DISTINGUISHES_STRONG_UP_FROM_FLAT`
    - Higher held strong-state rate, fewer positions, higher Top1/Top3 position concentration, higher sector concentration, and single-security adjusted valuation jumps. Raw candidate quality is similar.

14. `IS_MARKET_REGIME_OR_PORTFOLIO_INTERNAL_STATE_MORE_EXPLANATORY`
    - Portfolio internal state plus valuation artifact is more explanatory than regime alone.

15. `WHICH_HYPOTHESIS_H0_H7_BEST_EXPLAINS_THE_EVIDENCE`
    - H7 mixed interaction, with H6 valuation artifact material and H3/H4 partial.

16. `IS_ANY_CORRECTNESS_DEFECT_PRESENT`
    - NO. This is characterization only; no new measurement defect was identified.

17. `IS_ANY_PRODUCTION_CHANGE_JUSTIFIED`
    - NO.

18. `WHAT_SHOULD_BE_RETESTED_ON_THE_650BD_RUN`
    - RANGE vs BULL median/mean PnL persistence.
    - Whether strong-up days remain single-security adjusted-basis dominated.
    - Whether sector concentration remains higher in RANGE / STRONG_UP.
    - Whether BULL strong-candidate rejection remains lifecycle/BQ/lot-driven rather than competition-driven.
    - Whether portfolio-state metrics explain equity acceleration better than regime labels.

## No Change Confirmation

- NO CODE CHANGE.
- NO CONFIG CHANGE.
- NO RUNTIME STATE CHANGE.
- NO STRATEGY CHANGE.
- NO THRESHOLD / WEIGHT / CAP CHANGE.
- NO PRODUCTION RECOMMENDATION.
- NO fresh-run / resume / replay / recover / long Historical executed by Codex.

## Final Judgment

`PHASE32_AT_BULL_RANGE_RECOVERY_GROWTH_MECHANISM_MIXED_INTERACTION_NO_CORRECTNESS_DEFECT_NO_PRODUCTION_CHANGE`

The current 252BD evidence distinguishes:

- measured regime performance: RANGE strongest cumulative / mean / median;
- candidate substrate: BULL strongest HIGH/FULL supply;
- portfolio internal state: STRONG_UP has higher held strong-state and concentration than FLAT, but RANGE/RECOVERY do not have clearly higher cohesion than BULL;
- capital concentration: modest STRONG_UP advantage, not regime-sufficient;
- sector concentration: modest RANGE / STRONG_UP concentration advantage;
- valuation artifacts: material, with repeated `67310` adjusted-basis single-security jumps;
- causal hypotheses: regime alone and BULL selection difficulty are unproven; mixed interaction is best supported.
