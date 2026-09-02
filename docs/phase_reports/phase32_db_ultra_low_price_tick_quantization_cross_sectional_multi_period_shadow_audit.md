# Phase32-DB — Ultra-Low-Price Tick Quantization Cross-Sectional / Multi-Period SHADOW Audit

## Scope

Target run:

`runtime-test-historical-extended-smoke-20260901T223409325599Z`

This is a READ-ONLY / SHADOW audit. No Production source, config, runtime state,
Pending, Ledger, replay, resume, recover, or fresh-run operation was executed.
No future price, future PnL, MFE/MAE, later campaign outcome, delisting, or
Historical profitability was used to classify Candidate/BQ/Entry correctness.

Completed evidence used at audit time:

`2022-10-03` through `2023-04-11`, 129 completed business days.

## Inputs Read

Phase reports and SoT:

- `docs/phase_reports/phase32_da_9318_ultra_low_price_momentum_entry_quality_attribution_read_only_audit.md`
- `docs/phase_reports/phase32_cz_post_cw_march_upside_capture_capital_allocation_causal_read_only_audit.md`
- `docs/phase_reports/phase29_l12_93180_universe_eligibility_low_price_opportunity_root_cause_audit.md`
- `docs/phase_reports/phase29_l13_low_price_reentry_allocation_guard_design.md`
- `docs/phase_reports/phase29_l14_low_price_liquidity_reentry_threshold_calibration_and_implementation_readiness.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_data_contract_v1.md`
- `docs/02_architecture/strategy_intelligence_regression_contract_v1.md`

Current source:

- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `src/ai_fund_lab_v2/strategy/buy_quality.py`
- `src/ai_fund_lab_v2/strategy/strategy_intelligence.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

Run evidence:

- Daily `strategy/technical_features.json`
- Daily `strategy/buy_quality_decisions.json`
- Daily `strategy/portfolio_construction.json`
- Daily `.runtime/runtime_state/buy_ai/<date>/candidate_decisions.json`
- Daily `.runtime/runtime_state/buy_ai/<date>/opportunity_rankings.json`
- Daily J-Quants PIT normalized bars under each `market_refresh/inputs/historical_asof/<date>/raw_normalized/jquants/equities_bars_daily/data.parquet`

## Current Low-Price Authority Map

`CURRENT_LOW_PRICE_AUTHORITY_MAP`

| Boundary | Low-price / tick evidence status | Decision role |
|---|---|---|
| Universe / broker tradability | Product/listing eligibility produced and consumed; no hard low-price exclusion found | Decision material only for listing/product tradability, not price level |
| Technical features | Produces percentage returns, MA ratios, volatility, volume ratios, rolling traded value, reference price | Produced; tick ratio not normalized into Candidate features |
| Candidate | Consumes percentage returns, MA ratios, acceleration, volume, volatility, liquidity volume | Decision material; no explicit tick-ratio normalization found |
| Opportunity ranking | Consumes Candidate score/surface; emits uncalibrated relative score/rank | Decision material; score is explicitly not economic expected return |
| Strategy Intelligence | Produces trend, persistence, acceleration, participation, relative strength, volatility, microstructure risk | Microstructure is produced, mostly diagnostic/risk context |
| Downside Risk | Consumes volatility/exhaustion/participation/microstructure style evidence | Partial compensation; not a hard low-price no-buy authority |
| BUY Quality | Consumes opportunity rank/score and propagated features; momentum trajectory can classify, but observed 93180 HIGH was not driven by momentum weight | Decision material; independent tick validation absent/partial |
| Entry Admission | Consumes SI and BQ evidence; can reduce/caution | Decision material; recognizes caution but does not materially normalize tick quantization |
| Portfolio Construction | Computes `single_tick_pct`, `price_tick_risk_tier`, liquidity capacity, and target cap | CAP_ONLY / decision material for allocation, not upstream candidate admission |
| Position Sizing | Materializes PC target weight to executable lots/quantity | CONSUMED; not semantic low-price authority |
| Submit / broker | Final safety and product/eligibility guard | Not Strategy low-price selection authority |

Source confirmation:

- Candidate surface uses `price_momentum_return_*`, `trend_close_over_ma_20d`, `trend_ma_5_20_ratio`, `momentum_5d_vs_20d_delta`, volume, volatility, and liquidity volume.
- BQ momentum trajectory consumes the same return/MA/volatility/gap family of features.
- Strategy Intelligence microstructure records `reference_price`, `standard_lot_notional`, and traded value as `OBSERVED`.
- PC computes `single_tick_pct = minimum_tick / reference_price`; with default tick `1.0`, tiers are NORMAL `<1%`, WATCH `1-2%`, ELEVATED `2-5%`, SEVERE `5-10%`, EXTREME `>=10%`; caps are 12%, 10%, 8%, and 5%.

## Analysis Buckets

`LOW_PRICE_ANALYSIS_BUCKETS`

Analysis-only price buckets:

- `<=5` JPY
- `6-10` JPY
- `11-20` JPY
- `21-50` JPY
- `>50` JPY

Continuous tick exposure:

`single_tick_pct = 1.0 / reference_price`

These are descriptive audit buckets only. They are not proposed Production
thresholds.

## Multi-Period Sample

`MULTI_PERIOD_LOW_PRICE_SAMPLE`

Completed run coverage:

| Period | Dates | Joined Candidate/BQ/PC observations | Unique symbols | `<=50` obs | `<=20` obs | Extreme tick obs | Low top-5 | Low PC-positive |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Early | 40 | 2,087 | 313 | 167 | 91 | 78 | 51 | 37 |
| Mid | 60 | 3,389 | 528 | 215 | 125 | 116 | 95 | 32 |
| March | 22 | 1,157 | 122 | 68 | 37 | 37 | 13 | 21 |
| Post-April | 7 | included in total | included in total | limited | limited | limited | observed | observed |
| Total | 129 | 6,993 | 784 | 465 | 260 | 238 | 261 | 90 |

Universe-level PIT price distribution from J-Quants latest close per date:

| Price bucket | Universe security-date rows | Unique symbols | Avg per day | Min/day | Max/day |
|---|---:|---:|---:|---:|---:|
| `<=5` | 349 | 3 | 2.71 | 2 | 3 |
| `6-10` | 161 | 2 | 1.25 | 0 | 2 |
| `11-20` | 518 | 9 | 4.02 | 2 | 6 |
| `21-50` | 1,760 | 24 | 13.64 | 11 | 17 |
| `>50` | 544,048 | 4,268 | 4,217.43 | 4,172 | 4,261 |

The ultra-low universe is tiny, but Candidate/BQ evidence repeatedly included
the same extreme-tick symbols, especially 93180.

## Candidate Admission Profile

`LOW_PRICE_CANDIDATE_ADMISSION_PROFILE`

Joined Candidate/BQ/PC observations:

| Price bucket | Observations | Unique symbols | Candidate rows | Candidate top-50 | Candidate top-10 | Candidate top-5 |
|---|---:|---:|---:|---:|---:|---:|
| `<=5` | 129 | 1 | 129 | 129 | 128 | 122 |
| `6-10` | 109 | 1 | 109 | 109 | 0 | 0 |
| `11-20` | 22 | 4 | 22 | 21 | 0 | 0 |
| `21-50` | 205 | 10 | 202 | 193 | 84 | 54 |
| `>50` | 6,528 | 773 | 5,988 | 4,981+ | 1,078 | 469 |

The `<=5` result is not broad low-price population evidence; it is effectively
repeated 93180 evidence. It is still architecturally significant because one
extreme-tick symbol repeatedly reached the strongest ranks.

## Candidate Rank Profile

`LOW_PRICE_CANDIDATE_RANK_PROFILE`

| Price bucket | Median candidate rank | Avg candidate score | Median buy rank | Avg opportunity score | Positive opportunity-score rate |
|---|---:|---:|---:|---:|---:|
| `<=5` | 2.0 | 0.9548 | 4.0 | 0.1501 | 95.35% |
| `6-10` | 20.0 | 0.6079 | 20.0 | -0.4067 | 0.00% |
| `11-20` | 31.0 | 0.5460 | 37.5 | -0.5314 | 0.00% |
| `21-50` | 18.0 | 0.6984 | 17.0 | -0.1834 | 29.70% |
| `>50` | 26.0 | 0.5752 | 27.0 | -0.4120 | 9.79% |

Tick-bucket profile:

| Tick bucket | Obs | Unique symbols | Top-5 | Top-10 | BQ HIGH | BQ FULL | PC positive | Median buy rank | Avg opportunity score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EXTREME `>=10%` | 238 | 2 | 104+ | 124+ | 67 | 58 | 59 | 7.0 | -0.1061 |
| SEVERE `5-10%` | 22 | 4 | 0 | 0 | 0 | 0 | 0 | 37.5 | -0.5314 |
| ELEVATED `2-5%` | 205 | 10 | 54+ | 87+ | 84 | 57 | 31 | 17.0 | -0.1834 |
| WATCH `1-2%` | 283 | 24 | 16 | 68 | 13 | 9 | 68 | 21.0 | -0.3742 |
| NORMAL `<1%` | 6,245+ | 773+ | 460+ | 1,001+ | 643+ | 410+ | 1,560+ | 27.0 | -0.4146 |

`SYSTEMATIC_LOW_PRICE_RANK_INFLATION = PARTIAL`

Reason:

The sample confirms repeated high-rank inflation for 93180 and some elevated
representation in `21-50` / ELEVATED tick observations. It does not prove all
low-price securities are systematically inflated: `6-10` and `11-20` buckets
were not top-ranked and had no BQ HIGH/FULL rows. The defect shape is therefore
not "low price = high rank"; it is "extreme tick quantization can survive into
strong Candidate/rank without a complete upstream normalization authority."

## Tick-Sensitive Feature Map

`TICK_SENSITIVE_FEATURE_MAP`

| Feature family | Tick sensitivity | Existing normalization |
|---|---|---|
| Percentage returns `1d/3d/5d/10d/20d/60d` | High at low price; 1 JPY at 2-3 JPY equals 33-50% | No Candidate/BQ tick-normalized return resolution found |
| MA ratios / price-over-MA | High when MA is a mixture of 2/3/4 JPY closes | No explicit tick-level MA robustness authority found |
| Acceleration deltas | High because deltas are differences of percentage returns | No tick-ratio normalization found |
| Breakout/gap features | High; gap percentage can be one tick | BQ accepts gap fields where present, but no low-price quantization materiality found |
| Relative strength | Inherits symbol percentage returns; market comparator does not remove tick granularity | Partial only; no tick-normalized relative strength found |
| Volatility | Captures instability, but can treat tick oscillation as risk observation rather than disqualifying low-quality momentum | Partial risk compensation |
| Volume / traded value | Confirms tradability/capacity, not momentum quality | Liquidity normalized as capacity, not trend truth |
| Candidate composite score | Uses accepted model/rank plus feature surface | No explicit low-price quantization modifier found |
| BQ composite | Reuses rank/score and propagated features; 93180 momentum component weight was `0.0` | Independent tick validator absent/partial |
| PC low-price cap | Directly uses `single_tick_pct` | Present, but downstream allocation cap only |

## Quantization Robustness Shadow

`LOW_PRICE_QUANTIZATION_ROBUSTNESS_SHADOW`

Representative PIT cases:

| Date | Symbol | Price | 20-day close levels | Range ticks | Nonzero close changes | Interpretation |
|---|---|---:|---|---:|---:|---|
| 2023-03-15 | 93180 | 3 | `[2, 3]` | 1 | 3 | Tick-quantized / not robust persistent economic trend |
| 2023-02-16 | 93180 | 3 | `[2, 3]` | 1 | 8 | Tick-quantized oscillation, but Candidate rank 1 and BQ HIGH |
| 2023-02-21 | 93180 | 2 | `[2, 3]` | 1 | 9 | Correctly BQ-rejected despite Candidate rank 1 |
| 2023-03-15 | 89180 | 9 | `[9, 10]` | 1 | 8 | Extreme tick exposure, not high-ranked |
| 2022-10-03 | 76470 | 27 | `[27, 28, 29]` | 2 | 10 | Low-price/elevated tick, larger turnover and less extreme pct |
| 2023-03-15 | 76920 | 563.7 | 19 distinct levels | 381.7 | 19 | Normal-price comparator; percentage moves are not one-tick artifacts |

The current artifacts make this shadow distinction possible after the fact, but
the distinction is not a canonical Candidate/BQ/Entry decision authority.

## Trend And Momentum Semantics

`LOW_PRICE_TREND_STATE_DISTORTION = CONFIRMED_FOR_REPRESENTATIVE_EXTREME_TICK_CASES`

93180 repeatedly had supportive MA states from a close series containing only
2 and 3 JPY levels. Examples:

- `2023-03-15`: all recent returns were `0.0`, but `trend_close_over_ma_20d=1.071429` and `trend_ma_5_20_ratio=1.071429`.
- `2023-03-06` to `2023-03-08`: returns were mostly `0.0`, but MA ratios remained around `1.153846`.
- `2023-02-27`: `price_momentum_return_1d=0.5`, `20d=0.5`, and `trend_close_over_ma_20d=1.22449`; this is a one-tick move from 2 to 3 JPY.

`LOW_PRICE_MOMENTUM_DISTORTION = PARTIAL_CONFIRMED`

Direct return distortion is confirmed for 93180. It was not always converted to
BQ pass: BQ rejected some 2 JPY rows even with Candidate rank 1. The remaining
gap is indirect propagation: Candidate/opportunity score can remain very strong
and repeatedly top-ranked, while BQ/Entry treat risk mostly as reduction/caution
instead of requiring economic-momentum robustness.

## BQ Propagation

`LOW_PRICE_BQ_PROPAGATION_PROFILE`

| Price bucket | BQ rows | HIGH | FULL | Main action profile |
|---|---:|---:|---:|---|
| `<=5` | 129 | 67 | 58 | 58 REJECT, 58 FULL, 13 REDUCED |
| `6-10` | 109 | 0 | 0 | 109 REDUCED |
| `11-20` | 22 | 0 | 0 | 21 REDUCED, 1 REJECT |
| `21-50` | 202 | 84 | 57 | 117 REDUCED, 57 FULL, 16 BUY_WAIT, 12 REJECT |

For 93180 on `2023-03-15`, BQ HIGH/FULL came from:

- `relative_opportunity_quality`: score `0.731051`, weight `0.35`
- `signal_reliability`: score `0.8296`, weight `0.25`
- `portfolio_fit`: score `1.0`, weight `0.15`
- `market_context_quality_modifier`: score `0.692834`, weight `0.15`
- `execution_feasibility`: score `0.6475`, weight `0.10`
- `momentum_trajectory_quality`: score `0.5`, weight `0.0`

`BQ_LOW_PRICE_INDEPENDENT_VALIDATION = PARTIAL_FAIL`

BQ sometimes rejects extreme-tick rows, so it is not a blind pass-through.
However, no evidence was found that BQ independently validates whether low-price
momentum/trend is economically meaningful in tick units. It primarily consumes
upstream rank/score and propagated percentage features.

## Entry Admission

`LOW_PRICE_ENTRY_ADMISSION_PROFILE`

| Price bucket | Entry action profile |
|---|---|
| `<=5` | 121 `BUY_NEW_REDUCED_ONLY`, 8 `ADD_REDUCED_ONLY` |
| `6-10` | 108 `BUY_NEW_REDUCED_ONLY`, 1 `ADD_REDUCED_ONLY` |
| `11-20` | 20 `BUY_NEW_REDUCED_ONLY`, 2 `BUY_NEW_ALLOWED` |
| `21-50` | 173 `BUY_NEW_REDUCED_ONLY`, 17 `ADD_REDUCED_ONLY`, 8 `BUY_NEW_ALLOWED`, 6 `BUY_WAIT`, 1 `NO_ADD` |

`ENTRY_TICK_QUANTIZATION_MATERIALITY = PARTIAL`

Entry consistently recognizes caution, but it does not separately materialize
"apparent trend is tick-quantized" as a canonical admission reason. For 93180,
Entry reduced rather than rejected; the position slot could still be consumed.

## PC / Sizing Protection

`LOW_PRICE_PC_SIZING_PROTECTION_PROFILE`

| Price bucket | Auth rows | Status | Tier profile | Target positive | Normal already below cap | Final below normal |
|---|---:|---|---|---:|---:|---:|
| `<=5` | 129 | 129 PASS | 129 EXTREME | 58 | 127 | 3 |
| `6-10` | 109 | 109 PASS | 109 EXTREME | 1 | 107 | 107 |
| `11-20` | 22 | 22 PASS | 22 SEVERE | 0 | 22 | 6 |
| `21-50` | 205 | 205 PASS | 202 ELEVATED, 3 UNKNOWN | 31 | 202 | 133 |

PC protection is real and PIT-bound:

- It computes `single_tick_pct`.
- It records price/tick tier.
- It requires rolling traded value evidence.
- It caps target weight.

But most low-price proposed targets were already below the cap. Therefore the
cap often limited maximum damage rather than preventing the upstream admission
or position-slot cost.

`DOWNSTREAM_ONLY_PROTECTION_SUFFICIENT = NO`

Reason: PC/sizing protection can reduce notional exposure, but cannot fully
prevent a tick-distorted Candidate/BQ/Entry from occupying a position slot or
competing against normal opportunities.

## Position Slot And Liquidity

`LOW_PRICE_POSITION_SLOT_INTERACTION = MATERIAL`

Low-price positive PC rows:

- `<=5`: 58 positive target rows, all 93180.
- `6-10`: 1 positive target row.
- `21-50`: 31 positive target rows.

Average notional can remain small because price is tiny and PC caps are active,
but a position slot is still consumed. Phase32-CZ already observed 93180 used
11,900 shares at only about 2.9% weight, so the issue is not oversized notional;
it is slot/capital-competition admission quality.

`LOW_PRICE_LIQUIDITY_CONFIRMATION_SUFFICIENCY = PARTIAL_NOT_SUFFICIENT`

93180 had rolling traded value around 40-50M JPY, and 89180 had even higher
traded value in some observations. That confirms tradability/capacity, not that
the observed percentage momentum or MA support is economically meaningful.

`LOW_PRICE_RELATIVE_STRENGTH_ROBUSTNESS = PARTIAL_FAIL_FOR_EXTREME_TICK`

Relative strength uses symbol percentage returns against market returns. At
2-3 JPY, the symbol leg can be dominated by one-tick moves, so the metric can
inherit quantization distortion unless separately normalized.

`LOW_PRICE_RISK_COMPENSATION_EFFECTIVENESS = PARTIAL`

Volatility, participation, downside, microstructure, and Entry caution are
present. They are not strong enough to prevent repeated extreme-tick Candidate
top ranks and reduced admissions. BQ rejection of some 2 JPY rows proves partial
compensation, but not complete authority.

## Representative Cases

`REPRESENTATIVE_LOW_PRICE_CASES`

| Class | Case | Evidence |
|---|---|---|
| Ultra-low ranked HIGH and admitted | 93180, 2023-03-15 | price 3, single tick 33.33%, candidate rank 2, buy rank 3, BQ HIGH/FULL, Entry BUY_NEW_REDUCED_ONLY, target 2.9412% |
| Ultra-low correctly rejected | 93180, 2023-02-21 | price 2, single tick 50%, candidate rank 1, BQ UNUSABLE/REJECT, target 0 |
| Low-price not top-ranked | 89180, 2023-03-15 | price 9, buy rank 34, BQ MEDIUM/REDUCED, target 0 |
| Low-price tick-inflated candidate | 93180, 2023-02-16 | price 3, 1d/5d returns 50%, candidate rank 1, BQ HIGH, Entry reduced |
| Lower-price persistent-looking but still tick coarse | 76470, 2022-10-03 | price 27, three 20-day close levels, elevated tick tier, BQ MEDIUM/REDUCED |
| Normal-price comparator | 76920, 2023-03-15 | price 563.7, 19 distinct 20-day close levels, BQ HIGH/FULL, not one-tick driven |

## 9318 Recontextualization

`9318_RELATIVE_TO_LOW_PRICE_POPULATION = EXTREME_OUTLIER_WITH_REPEATED_STRONG_RANK`

93180 is not typical of all low-price symbols. In the completed evidence, the
`<=5` Candidate/BQ sample was effectively all 93180, while `6-10` and `11-20`
low-price symbols were not strongly ranked. 93180 is therefore an outlier within
a small ultra-low-price universe, but it is a highly relevant architecture
stress case because it repeatedly passed the pipeline as a strong candidate.

## Generic Architecture Gap

`GENERIC_TICK_QUANTIZATION_ARCHITECTURE_GAP = CONFIRMED`

Confirmed chain:

```text
tick-quantized price structure
-> percentage/trend feature amplification
-> strong Candidate/rank for at least representative extreme-tick cases
-> BQ/Entry admission or reduced admission
-> PC cap/diagnostic authority recognizes low-price risk downstream
```

The general problem is not that all low-priced stocks are bad or all are
inflated. The problem is that the system lacks a canonical upstream distinction
between genuine persistent opportunity and coarse-tick percentage artifacts.

## Correct Semantic Target

`GENERIC_REPAIR_SEMANTIC_TARGET`

Preferred future repair direction:

- Promote existing Strategy Intelligence / Candidate / BQ low-price evidence
  rather than inventing a separate subsystem first.
- Add or materialize tick-normalized trend evidence.
- Add minimum meaningful movement in ticks and number-of-close-levels evidence.
- Add quantization-aware momentum confidence.
- Add Candidate reliability modifier for extreme `single_tick_pct`.
- Add BQ independent microstructure validator that does not merely reuse rank.
- Make Entry caution materialize tick-quantization explicitly, with symbol-level
  REVIEW/REDUCE/WAIT semantics where evidence is insufficient.
- Preserve PC's allocation authority and avoid double-penalizing the same risk.

No numeric Production threshold is selected in DB.

`LEGITIMATE_LOW_PRICE_OPPORTUNITY_PRESERVATION = REQUIRED`

Low price must not mean bad. It must mean apparent momentum requires evidence
that the move is economically meaningful rather than a coarse tick artifact.

`HARD_MINIMUM_PRICE_THRESHOLD_JUSTIFIED = NO_FROM_DB`

`SYMBOL_BLACKLIST_JUSTIFIED = NO`

## Production Repair Decision

`PRODUCTION_REPAIR_REQUIRED = YES_ARCHITECTURE`

This is not an immediate symbol-specific correctness bug and not a reason to
blacklist 9318. It is a generic architecture gap in upstream evidence semantics:
current PC/sizing controls cap exposure after admission, but Candidate/BQ/Entry
do not fully normalize or independently validate tick-quantized trend/momentum.

`NEW_COMPONENT_REQUIRED = NO_NOT_FIRST_CHOICE`

Existing Candidate, Strategy Intelligence, BQ, Entry, and PC authorities are the
right first extension points.

`NEW_MODEL_REQUIRED = UNCONFIRMED`

The audit supports new canonical evidence and possibly a model feature/reliability
modifier. It does not prove a full replacement model is required.

`NEW_FEATURE_REQUIRED = YES`

Required feature family:

- `single_tick_pct` upstream propagation
- close-level count / price-level diversity over lookbacks
- movement measured in ticks as well as percentage
- tick-normalized MA/trend robustness
- quantization-aware relative strength and momentum confidence
- liquidity-capacity evidence kept separate from momentum truth

`PHASE32_CLOSURE_IMPACT = PHASE33_CARRY_FORWARD_ALLOWED`

Rationale:

This is a Strategy architecture quality gap, not a Runtime correctness blocker.
The encoded baseline is behaving according to current accepted contracts. A
future repair should be designed as a generic PIT-safe evidence promotion, not
as an emergency threshold patch from Historical outcomes.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-04-11`
2. `CURRENT_LOW_PRICE_AUTHORITY_MAP = Candidate consumes percentage/trend features without tick normalization; SI produces diagnostic microstructure; BQ partially consumes/reranks but lacks independent tick validator; Entry cautions/reduces; PC computes single_tick_pct and caps allocation; PS materializes quantity; broker handles tradability only`
3. `LOW_PRICE_ANALYSIS_BUCKETS = <=5, 6-10, 11-20, 21-50, >50 JPY plus continuous single_tick_pct = 1/reference_price`
4. `MULTI_PERIOD_LOW_PRICE_SAMPLE = 129 completed days, 6,993 joined observations, 784 unique symbols; universe price rows include <=5 n=349/3 symbols, 6-10 n=161/2, 11-20 n=518/9, 21-50 n=1,760/24, >50 n=544,048/4,268`
5. `LOW_PRICE_CANDIDATE_ADMISSION_PROFILE = <=5: 129 candidate rows, 128 top10, 122 top5; 6-10: 109 candidate rows, no top10; 11-20: 22 rows, no top10; 21-50: 202 rows, 84 top10, 54 top5`
6. `LOW_PRICE_CANDIDATE_RANK_PROFILE = <=5 median candidate rank 2 and positive opportunity-score rate 95.35%; 6-10 and 11-20 weak; 21-50 elevated but mixed; >50 median candidate rank 26`
7. `SYSTEMATIC_LOW_PRICE_RANK_INFLATION = PARTIAL`
8. `TICK_SENSITIVE_FEATURE_MAP = percentage returns, MA ratios, acceleration deltas, gap features, relative strength, volatility, and composites are tick-sensitive; explicit tick normalization exists materially in PC cap, not upstream Candidate/BQ rank`
9. `LOW_PRICE_QUANTIZATION_ROBUSTNESS_SHADOW = possible from PIT OHLCV/close-level/tick traversal evidence, but not canonical Production authority`
10. `LOW_PRICE_TREND_STATE_DISTORTION = CONFIRMED_FOR_REPRESENTATIVE_EXTREME_TICK_CASES`
11. `LOW_PRICE_MOMENTUM_DISTORTION = PARTIAL_CONFIRMED`
12. `LOW_PRICE_BQ_PROPAGATION_PROFILE = <=5 BQ rows 129 with 67 HIGH and 58 FULL; 6-10 and 11-20 no HIGH/FULL; 21-50 has 84 HIGH and 57 FULL`
13. `BQ_LOW_PRICE_INDEPENDENT_VALIDATION = PARTIAL_FAIL`
14. `LOW_PRICE_ENTRY_ADMISSION_PROFILE = low-price rows mostly BUY_NEW_REDUCED_ONLY; Entry recognizes caution but still admits/reduces`
15. `ENTRY_TICK_QUANTIZATION_MATERIALITY = PARTIAL`
16. `LOW_PRICE_PC_SIZING_PROTECTION_PROFILE = PC single_tick/tier/cap/liquidity authority present and PASS for sampled low rows; many proposed targets already below cap`
17. `DOWNSTREAM_ONLY_PROTECTION_SUFFICIENT = NO`
18. `LOW_PRICE_POSITION_SLOT_INTERACTION = MATERIAL`
19. `LOW_PRICE_LIQUIDITY_CONFIRMATION_SUFFICIENCY = PARTIAL_NOT_SUFFICIENT`
20. `LOW_PRICE_RELATIVE_STRENGTH_ROBUSTNESS = PARTIAL_FAIL_FOR_EXTREME_TICK`
21. `LOW_PRICE_RISK_COMPENSATION_EFFECTIVENESS = PARTIAL`
22. `REPRESENTATIVE_LOW_PRICE_CASES = 93180 2023-03-15 admitted HIGH/FULL; 93180 2023-02-21 rejected; 89180 2023-03-15 not top-ranked; 76470 2022-10-03 low/elevated comparator; 76920 normal-price comparator`
23. `9318_RELATIVE_TO_LOW_PRICE_POPULATION = EXTREME_OUTLIER_WITH_REPEATED_STRONG_RANK`
24. `GENERIC_TICK_QUANTIZATION_ARCHITECTURE_GAP = CONFIRMED`
25. `GENERIC_REPAIR_SEMANTIC_TARGET = extend existing SI/Candidate/BQ/Entry/PC authority with tick-normalized trend, movement-in-ticks, quantization-aware confidence, and independent BQ/Entry microstructure validation`
26. `LEGITIMATE_LOW_PRICE_OPPORTUNITY_PRESERVATION = REQUIRED`
27. `HARD_MINIMUM_PRICE_THRESHOLD_JUSTIFIED = NO_FROM_DB`
28. `SYMBOL_BLACKLIST_JUSTIFIED = NO`
29. `PRODUCTION_REPAIR_REQUIRED = YES_ARCHITECTURE`
30. `NEW_COMPONENT_REQUIRED = NO_NOT_FIRST_CHOICE`
31. `NEW_MODEL_REQUIRED = UNCONFIRMED`
32. `NEW_FEATURE_REQUIRED = YES`
33. `PHASE32_CLOSURE_IMPACT = PHASE33_CARRY_FORWARD_ALLOWED`
34. `FUTURE_OUTCOME_USED = NO`
35. `PRODUCTION_CHANGE_EXECUTED = NO`
36. `TARGET_RUN_MUTATED = NO`
37. `NEXT_RECOMMENDED_STEP = create a generic PIT-safe low-price/tick-quantization evidence-promotion design task; do not blacklist 9318 and do not introduce a hard minimum price`
38. `FINAL_JUDGMENT = PHASE32_DB_GENERIC_TICK_QUANTIZATION_ARCHITECTURE_GAP_CONFIRMED_SHADOW_ONLY_PHASE33_CARRY_FORWARD`

## Final Judgment

`PHASE32_DB_GENERIC_TICK_QUANTIZATION_ARCHITECTURE_GAP_CONFIRMED_SHADOW_ONLY_PHASE33_CARRY_FORWARD`

DB confirms DA's single-name concern generalizes to an architecture gap: the
system has downstream low-price/tick caps and diagnostics, but upstream
Candidate/BQ/Entry can still admit or repeatedly rank an extreme-tick security
without canonical proof that apparent momentum/trend is economically meaningful
rather than quantized. The evidence does not justify a hard minimum price,
symbol blacklist, or PnL-derived threshold. The correct next move is a generic,
PIT-safe evidence-promotion design that preserves legitimate low-price
opportunities.
