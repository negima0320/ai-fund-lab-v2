# Phase32-DA — 9318 Ultra-Low-Price Momentum / Entry Quality Attribution READ-ONLY Audit

## Scope

Target run:

`runtime-test-historical-extended-smoke-20260901T223409325599Z`

Primary decision date:

`2023-03-15`

This audit is READ-ONLY. No source, config, runtime state, Pending, Ledger, replay,
resume, recover, or fresh-run operation was executed. The run continued externally
while this audit was being prepared; the evidence window used here is frozen to
the already reviewed March snapshot through `2023-03-28`, and the entry-quality
classification for 9318/93180 uses only decision-time/PIT evidence available as
of `2023-03-15`.

## References Read

- `docs/phase_reports/phase32_cz_post_cw_march_upside_capture_capital_allocation_causal_read_only_audit.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_data_contract_v1.md`
- `docs/02_architecture/strategy_intelligence_regression_contract_v1.md`
- `docs/phase_reports/phase29_l12_93180_universe_eligibility_low_price_opportunity_root_cause_audit.md`
- `docs/phase_reports/phase29_l13_low_price_reentry_allocation_guard_design.md`
- `docs/phase_reports/phase29_l14_low_price_liquidity_reentry_threshold_calibration_and_implementation_readiness.md`
- Current source:
  - `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
  - `src/ai_fund_lab_v2/strategy/strategy_intelligence.py`
  - `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

Primary run evidence:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260901T223409325599Z/daily/2023-03-15/strategy/buy_quality_decisions.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260901T223409325599Z/daily/2023-03-15/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260901T223409325599Z/daily/2023-03-15/strategy/runtime_planning.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260901T223409325599Z/daily/2023-03-15/strategy/strategy_intelligence.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260901T223409325599Z/daily/2023-03-15/strategy/technical_features.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260901T223409325599Z/daily/2023-03-15/execution/fills.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260901T223409325599Z/daily/2023-03-15/market_refresh/inputs/historical_asof/2023-03-15/raw_normalized/jquants/equities_bars_daily/data.parquet`
- `.runtime/runtime_state/buy_ai/2023-03-15/candidate_decisions.json`
- `.runtime/runtime_state/buy_ai/2023-03-15/opportunity_rankings.json`

## 9318 Actual Path

The actual runtime symbol is `93180`.

Observed path:

| Date | Artifact | Status |
|---|---|---|
| 2023-03-15 | Candidate / Opportunity | candidate rank `2`, quality-aware rank `3`, buy rank `3`, score `0.27460966` |
| 2023-03-15 | BUY Quality | `HIGH`, `FULL_ALLOCATION_ELIGIBLE`, score `0.781943` |
| 2023-03-15 | Entry / PC | `CONTINUATION_WITH_CAUTION`, `BUY_NEW_REDUCED_ONLY`, target weight `0.029412` |
| 2023-03-15 | Runtime planning | `BUY_NEW`, planned quantity `11900`, reference price `3.0` |
| 2023-03-15 | Execution fill | BUY_NEW `11900` shares, execution price `2.0`, gross notional `23800.0`, campaign `pc-762ddee5bae0f9e4-93180-0001` |

Phase32-CZ later lifecycle context is consistent: 93180 occupied a position slot
and was a very low-price/microstructure-risk example, but it did not consume
dominant portfolio capital.

## PIT Price / Trend Profile

J-Quants normalized daily bars available as of `2023-03-15` show the recent
price regime:

| Date range | Observed profile |
|---|---|
| 2023-01-18 to 2023-03-15 sample tail | daily close oscillates between `2.0` and `3.0` JPY |
| 2023-03-01 to 2023-03-15 | close remains `3.0` JPY every sampled trading day |
| 2023-03-15 | open `2.0`, high `3.0`, low `2.0`, close `3.0`, volume `14,845,000` |
| 20-day rolling traded value | `46,474,050` JPY |
| one tick percentage | `1 / 3 = 0.33333333` |

Technical feature snapshot on `2023-03-15`:

| Feature | Value |
|---|---:|
| `price_momentum_return_1d` | `0.0` |
| `price_momentum_return_3d` | `0.0` |
| `price_momentum_return_5d` | `0.0` |
| `price_momentum_return_10d` | `0.0` |
| `price_momentum_return_20d` | `0.0` |
| `price_momentum_return_60d` | `0.0` |
| `trend_close_over_ma_20d` | `1.071429` |
| `trend_ma_5_20_ratio` | `1.071429` |
| `trend_ma_20_60_ratio` | `1.012048` |
| `volatility_return_std_20d` | `0.189297` to `0.194215` depending artifact precision |
| `volume_momentum_ratio_1d_20d` | `0.931511` |
| `volume_momentum_ratio_5d` | `0.944882` |

Interpretation:

93180 was not admitted because short-window percentage returns were positive on
the decision day; those returns were all `0.0`. It was admitted despite weak
persistence and elevated volatility because the candidate/opportunity model
ranked it highly, moving-average structure looked supportive, liquidity evidence
was present, and downstream Entry/PC reduced allocation rather than rejecting.

However, the trend ratios are materially exposed to tick quantization. At a
3 JPY reference price, a 1 JPY tick is 33.33%. A small change in the 2/3 JPY
mix inside moving averages can create apparently meaningful percentage trend
ratios even when the raw close has been flat at 3 JPY for recent days.

## Candidate / Opportunity Attribution

Candidate evidence for 93180 on `2023-03-15`:

| Field | Value |
|---|---|
| `candidate_score` | `0.97496671` |
| `candidate_rank` | `2` |
| `quality_aware_candidate_rank` | `3` |
| `candidate_reason` | `high_candidate_score|liquidity_available` |
| `score_evidence_class` | `STRONG_DISCOVERY_SCORE` |
| `surface_state` | `CAUTION_MOMENTUM_SURFACE` |
| `candidate_pit_quality_surface.reason_codes` | supportive MA, supportive long trend, supportive acceleration, weak participation, elevated volatility, trend not confirmed |

Opportunity evidence:

| Field | Value |
|---|---|
| `buy_rank` | `3` |
| `runtime_opportunity_score` | `0.27460966` |
| `score_semantic_role` | `uncalibrated_relative_model_score` |
| `economic_units_available` | `false` |
| `calibration_applied` | `false` |
| `reason` | `opportunity_top5|positive_expected_edge|candidate_prior_available|downside_risk_not_extreme` |

The score is explicitly not a calibrated economic expected return. The rank
driver is mainly the accepted candidate/opportunity model output plus same-day
relative ordering, not an independently normalized low-price economic edge.

## BUY Quality Attribution

BUY Quality for 93180:

| Component | Score | Weight | Status |
|---|---:|---:|---|
| `execution_feasibility` | `0.6475` | `0.10` | `PASS` |
| `market_context_quality_modifier` | `0.692834` | `0.15` | `PASS` |
| `momentum_trajectory_quality` | `0.5` | `0.00` | `PASS_WITH_REDUCTION` |
| `portfolio_fit` | `1.0` | `0.15` | `PASS` |
| `relative_opportunity_quality` | `0.731051` | `0.35` | `PASS` |
| `signal_reliability` | `0.8296` | `0.25` | `PASS` |

`momentum_trajectory_quality` was not the numerical driver because its weight
was `0.0`. BQ HIGH came mostly from relative opportunity quality, signal
reliability, portfolio fit, market context, and execution feasibility. This is
important: the 93180 high-quality classification is not explained by a direct
positive recent-return momentum reading, but it still inherits the upstream
candidate/opportunity score surface that uses percentage momentum and trend
features without a full low-price quantization authority.

## Entry Admission / Security Quality

Strategy Intelligence and PC did not treat 93180 as clean continuation:

| Dimension | Value |
|---|---|
| `entry_state` | `CONTINUATION_WITH_CAUTION` |
| `entry_action` | `BUY_NEW_REDUCED_ONLY` |
| `trend_health` | `SUPPORTIVE` |
| `participation_quality` | `WEAK` |
| `participation_risk` | `ELEVATED_RISK` |
| `persistence` | `WEAK` |
| `relative_strength` | `MIXED` |
| `volatility_risk` | `OBSERVED` |
| `downside_risk_status` | `PASS` |
| `microstructure_risk` | `OBSERVED` |
| `event_status` | `KNOWN_NO_EVENT` |
| `broker_eligibility_status` | `PASS` |
| `corporate_action_status` | `NO_EVENT` |

Security-quality evidence therefore captured caution, volatility, weak
participation, and microstructure observation. It did not convert low-price/tick
distortion into a hard no-buy authority.

## Low-Price Authority Boundary

Architecture recognizes microstructure risk as low price, tick ratio, lot
notional, gap/liquidity fragility, and says it should influence Downside Risk,
Position Sizing, PC low-price allocation cap, and Eligibility only on true hard
tradability/liquidity failure. It also explicitly says not to introduce a hard
minimum stock price without calibration.

Current source reflects that boundary:

- `strategy_intelligence._microstructure_risk` records `reference_price`,
  `standard_lot_notional`, and rolling traded value as `OBSERVED`.
- `portfolio_construction._resolve_low_price_reentry_allocation_guard` computes
  `single_tick_pct`, maps it to a tier, requires liquidity evidence when needed,
  and caps buy-side allocation.
- At `reference_price=3.0`, `single_tick_pct=0.33333333`, tier `EXTREME`, and
  `price_tick_cap_weight=0.05`.
- 93180's final PC target `0.029412` was below the 5% extreme tick cap, so the
  cap did not further reduce it.

This means ultra-low-price authority exists partially as evidence and allocation
cap, but not as a complete Candidate/BQ/Entry normalization layer that separates
true economic momentum from 1-yen tick quantization.

## Cross-Sectional 2023-03-15 Low-Price Sample

BUY Quality rows with price joined from PIT market evidence:

| Price bucket | Rows | HIGH | FULL | Avg rank | Median rank | Avg score |
|---|---:|---:|---:|---:|---:|---:|
| `<=5` | 1 | 1 | 1 | 3.0 | 3.0 | 0.2746 |
| `<=10` | 2 | 1 | 1 | 18.5 | 18.5 | -0.0541 |
| `<=20` | 2 | 1 | 1 | 18.5 | 18.5 | -0.0541 |
| `>20` | 48 | 4 | 2 | 25.79 | 25.5 | -0.2107 |

Low-price rows observed:

| Symbol | Price | Rank | Score | BQ band/action | Notes |
|---|---:|---:|---:|---|---|
| 93180 | 3.0 | 3 | 0.27460966 | HIGH / FULL | extreme tick pct, weak persistence, supportive MA, high discovery score |
| 89180 | 9.0 | 34 | -0.3827837 | MEDIUM / REDUCED | mixed/unresolved, not top-ranked |

This one-day sample does not prove systematic low-price rank inflation across
the whole system. It does prove that the admitted ultra-low-price case can rank
top-3 and receive BQ HIGH/FULL while the active authority treats tick distortion
mainly as a PC allocation cap and diagnostic risk evidence.

## Findings

### 9318 Entry Quality

`9318_ENTRY_QUALITY_JUDGMENT = PIT_SUPPORTED_BUT_MICROSTRUCTURE_UNDER_NORMALIZED`

The 2023-03-15 entry was supported by canonical PIT evidence under the current
baseline: current listing, broker/product eligibility, no corporate event,
liquidity evidence, high candidate/opportunity rank, BQ HIGH, Entry caution, and
PC reduced allocation.

It was not a clean high-quality trend continuation in economic terms. The PIT
evidence itself marked weak participation, weak persistence, elevated volatility,
and microstructure risk. The root concern is that current Candidate/BQ/Entry
authority can treat ultra-low-price trend/score evidence as comparable to normal
price securities without explicitly separating true momentum from one-tick
percentage artifacts.

### Ultra-Low-Price Root Cause

`ULTRA_LOW_PRICE_ENTRY_ROOT_CAUSE = PARTIAL_LOW_PRICE_AUTHORITY_AT_PC_SIZING_LAYER_NOT_FULL_CANDIDATE_BQ_ENTRY_NORMALIZATION`

Root cause:

1. Candidate/opportunity model accepted 93180 as a strong discovery score and
   top-ranked opportunity.
2. Candidate surface used percentage momentum/trend features and identified
   supportive MA/long-trend/acceleration alongside caution flags.
3. BQ consumed rank/score and feature evidence, but `momentum_trajectory_quality`
   had zero numerical weight and there was no independent low-price tick
   quantization normalization in the HIGH/FULL decision.
4. Entry/PC correctly reduced allocation and exposed caution, but did not make
   ultra-low price itself a no-buy condition.
5. PC low-price authority capped allocation and required liquidity evidence, but
   93180's reduced target was already below the cap and its traded-value evidence
   passed.

## Required Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-03-28 audit snapshot; 93180 entry classification uses PIT evidence through 2023-03-15 only`
2. `9318_ACTUAL_PATH_REVALIDATED = YES`
3. `9318_DECISION_FEATURE_ATTRIBUTION = candidate rank 2 / opportunity buy rank 3 / score 0.27460966; BQ HIGH driven mainly by relative_opportunity_quality, signal_reliability, portfolio_fit, market_context, execution_feasibility; Entry reduced on caution`
4. `9318_PIT_PRICE_TREND_PROFILE = 2-3 JPY ultra-low price regime; recent March closes flat at 3 JPY; 1 tick = 33.333333% of reference price`
5. `9318_TREND_STATE_AT_ENTRY = SUPPORTIVE_MA_STRUCTURE_WITH_WEAK_PERSISTENCE_AND_ELEVATED_VOLATILITY`
6. `ONE_TICK_PERCENTAGE_MOMENTUM_DISTORTION_PRESENT = YES_STRUCTURALLY_FOR_93180`
7. `ULTRA_LOW_PRICE_NORMALIZATION_AUTHORITY = PARTIAL_PC_ALLOCATION_AND_DIAGNOSTIC_MICROSTRUCTURE_ONLY`
8. `9318_RANK_DRIVERS = strong candidate discovery score, top5 opportunity rank, positive uncalibrated relative model score, liquidity available, downside risk not extreme`
9. `9318_BQ_HIGH_ATTRIBUTION = relative_opportunity_quality 0.731051 weight 0.35; signal_reliability 0.8296 weight 0.25; portfolio_fit 1.0 weight 0.15; market_context 0.692834 weight 0.15; execution_feasibility 0.6475 weight 0.10; momentum_trajectory weight 0.0`
10. `9318_CANDIDATE_BQ_EVIDENCE_INDEPENDENCE = PARTIAL; BQ is a second-stage consumer but reuses candidate/opportunity rank and same propagated PIT features, not an independent tick-normalized low-price validator`
11. `9318_ENTRY_ADMISSION_ATTRIBUTION = BUY_NEW_REDUCED_ONLY because entry evidence was CONTINUATION_WITH_CAUTION: trend supportive, participation weak/elevated risk, persistence weak, relative strength mixed`
12. `9318_SECURITY_QUALITY_PROFILE_AT_ENTRY = PASS_WITH_CAUTION; current listed, Standard market, product/security type 011, broker PASS, corporate NO_EVENT, microstructure OBSERVED`
13. `GENERIC_LOW_PRICE_SAFETY_AUTHORITY_FOUND = PARTIAL_NON_BLOCKING`
14. `LOW_PRICE_SAFETY_LEGACY_STATUS = design and prior calibration work exist; current Production has PC low-price cap/liquidity authority, not a hard low-price exclusion`
15. `ULTRA_LOW_PRICE_CANDIDATE_SAMPLE = 2023-03-15 BQ rows: <=5 price n=1, 93180 rank 3 HIGH/FULL; <=20 price n=2, only 93180 HIGH/FULL`
16. `LOW_PRICE_VS_NORMAL_PRICE_FEATURE_COMPARISON = low-price sample too small for distributional proof; 93180 has much larger single_tick_pct and volatility than normal-priced top rows`
17. `LOW_PRICE_SYSTEMATIC_RANK_INFLATION = NOT_PROVEN_BY_ONE_DAY_SAMPLE; structurally plausible and previously documented, but DA evidence proves concrete 93180 susceptibility rather than full-system rate`
18. `ULTRA_LOW_PRICE_ENTRY_RATE_PROFILE = one <=5 JPY BQ row on 2023-03-15 and it entered as reduced BUY_NEW; no broad entry-rate conclusion from this single date`
19. `MOMENTUM_VS_TICK_QUANTIZATION_DISTINGUISHABLE = PARTIAL; raw OHLCV and single_tick_pct expose the issue, but Candidate/BQ HIGH does not fully normalize the distinction`
20. `LOW_PRICE_VOLUME_CONFIRMATION_EFFECTIVE = PARTIAL; rolling traded value passed and supports tradability, but does not prove economic momentum quality`
21. `LOW_PRICE_DOWNSIDE_RISK_CAPTURE = PARTIAL; microstructure/volatility/participation caution captured, but not promoted to complete Entry/BQ low-price safety`
22. `9318_ENTRY_QUALITY_JUDGMENT = PIT_SUPPORTED_BUT_MICROSTRUCTURE_UNDER_NORMALIZED`
23. `ULTRA_LOW_PRICE_ENTRY_ROOT_CAUSE = partial low-price authority exists downstream, but Candidate/BQ/Entry can still admit a 2-3 JPY name from uncalibrated relative score plus MA structure without a full tick-quantization authority`
24. `PRODUCTION_REPAIR_REQUIRED = CONDITIONAL_YES_FOR_GENERIC_ARCHITECTURE_IF_LOW_PRICE_ENTRY_CONTROL_IS_IN_SCOPE; do not patch 9318 alone`
25. `9318_SYMBOL_BLACKLIST_JUSTIFIED = NO`
26. `NEW_COMPONENT_REQUIRED = UNCONFIRMED; likely an extension of existing Strategy Intelligence / Candidate / BQ / PC low-price authority is preferable before inventing a new component`
27. `NEW_MODEL_REQUIRED = UNCONFIRMED`
28. `NEW_FEATURE_REQUIRED = YES_OR_EXISTING_FEATURE_PROMOTION_REQUIRED: explicit tick/price quantization, gap behavior, low-price trend robustness, and liquidity-capacity interaction should become canonical evidence if promoted`
29. `FUTURE_OUTCOME_USED_TO_CLASSIFY_9318_ENTRY = NO`
30. `PRODUCTION_CHANGE_EXECUTED = NO`
31. `TARGET_RUN_MUTATED = NO`
32. `NEXT_RECOMMENDED_STEP = design a generic low-price/tick-quantization authority audit or shadow refinement using multiple symbols/periods; do not blacklist 9318 and do not set a hard minimum price from this case alone`
33. `FINAL_JUDGMENT = PHASE32_DA_9318_ENTRY_PIT_SUPPORTED_BUT_ULTRA_LOW_PRICE_TICK_QUANTIZATION_AUTHORITY_INCOMPLETE`

## Final Judgment

`PHASE32_DA_9318_ENTRY_PIT_SUPPORTED_BUT_ULTRA_LOW_PRICE_TICK_QUANTIZATION_AUTHORITY_INCOMPLETE`

93180's 2023-03-15 BUY_NEW was not a runtime/provenance defect and was not
classified using later performance. It was a canonical PIT-supported entry under
the current accepted baseline, but the evidence shows a real architecture gap:
ultra-low-price/tick-quantized securities can receive high Candidate/BQ treatment
from relative model score and MA/trend surface while low-price protection remains
mostly diagnostic or sizing-level. A symbol blacklist is not justified. Any
repair should be generic, PIT-safe, multi-symbol calibrated, and should extend
existing low-price/microstructure authority rather than add an ad-hoc 9318 rule.
