# Phase32-CE — Single-Campaign Concentration x Unpredictable Loss Amplification READ-ONLY Audit

Target run:

`runtime-test-historical-extended-smoke-20260831T234344371102Z`

Evidence snapshot:

- run status at inspection: `RUNNING`
- latest completed business date used: `2023-06-01`
- completed business days used: `163`
- return intervals used: `162`
- next job observed but not touched: `2023-06-02:submit`

This audit used completed run artifacts only. No code, config, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run action was changed or executed.

## Preserved Prior Conclusions

CE preserves the accepted CA/CD/BY conclusions:

- upside capture is strong
- late normalized downside tail is materially worse than early
- high total exposure is not the primary cause
- position/notional scale and concentration are material
- SELL/HOLD/BQ broadening is not currently justified
- some losses are genuinely new-information / gap-type and cannot be reliably predicted
- HOLD -> REDUCE and BQ semantics are not reopened here

## Method

Daily concentration was calculated from each completed day's authoritative `current_valuation_refresh/current_valuation_manifest.json`, using `artifact.candidate_current.positions`, `market_value`, `cash`, and `total_equity`.

Daily PnL was calculated as current completed-day equity minus previous completed-day equity. Symbol contribution was reconstructed as:

`current market value + same-day SELL proceeds - prior market value - same-day BUY notional`

This is an audit attribution approximation over authoritative Runtime fills and valuation artifacts. It is not a Production metric and was not used to tune parameters.

## Concentration Time Series

| Population | N | Median max position / equity | Median top-3 / equity | Median HHI | Median exposure | Median position count |
|---|---:|---:|---:|---:|---:|---:|
| Early half | 81 | 16.68% | 45.41% | 0.0935 | 79.31% | 11 |
| Late half | 82 | 15.79% | 41.87% | 0.0835 | 80.43% | 10 |

The median late-day concentration is not higher than early. The tail is different: late max-position concentration reached `31.13%` versus early max `22.34%`. The late problem is therefore not broad persistent concentration across all days; it is episodic single-name concentration around large winners.

## Severe vs Ordinary Days

Severe loss definition used:

- normalized daily return `<= -3%`, or
- absolute daily loss `<= -50,000`

Large loss extension also tracked `<= -2%`.

| Population | N | Median prior max position / equity | Median prior top-3 / equity | Median HHI |
|---|---:|---:|---:|---:|
| Severe loss days | 4 | 23.30% | 44.24% | 0.1028 |
| Ordinary negative days | 61 | 16.19% | 45.57% | 0.0914 |
| Positive days | 97 | 16.20% | 42.24% | 0.0845 |
| All return days | 162 | 16.26% | 43.83% | 0.0886 |

Severe loss days have materially higher single-position concentration than ordinary negative days. Top-3 concentration is not consistently higher, which reinforces that the severe-tail shape is single-campaign dominated rather than broad portfolio exposure dominated.

## Large-Loss Events

| Date | PnL | Return | Prior max-position share | Dominant loss contributor | Contributor prior share | Contributor / daily loss |
|---|---:|---:|---:|---|---:|---:|
| 2022-10-11 | -21,930 | -2.05% | 22.27% | 70640 -12,750 | 22.27% | 58.1% |
| 2022-11-14 | -31,710 | -2.89% | 16.07% | 99840 -22,130 | 15.81% | 69.8% |
| 2022-12-07 | -30,130 | -2.64% | 20.91% | 79010 -21,330 | 20.91% | 70.8% |
| 2022-12-19 | -33,550 | -2.96% | 17.94% | 97310 -20,100 | 18.33% | 59.9% |
| 2023-03-29 | -61,660 | -4.08% | 21.40% | 59350 -61,400 | 21.40% | 99.6% |
| 2023-04-07 | -80,700 | -4.58% | 31.13% | 59350 -90,500 | 31.13% | 112.1% |
| 2023-04-11 | -144,950 | -8.21% | 25.19% | 67310 -100,000 | 22.65% | 69.0% |
| 2023-04-12 | -37,110 | -2.29% | 25.90% | 59350 -34,500 | 25.90% | 92.9% |
| 2023-04-18 | -37,450 | -2.29% | 26.67% | 59350 -40,000 | 26.67% | 106.8% |
| 2023-04-21 | -57,540 | -3.60% | 17.93% | 60220 -29,700 | 15.72% | 51.6% |
| 2023-05-12 | -39,680 | -2.43% | 13.79% | 93530 -15,500 | material but not dominant | 39.1% |
| 2023-05-15 | -45,380 | -2.85% | 13.16% | 62310 -30,000 | material | 66.1% |

For the four severe days, the dominant contributor explains a median `84.3%` and mean `83.1%` of the daily loss magnitude. In two cases the share is above 100% because other positions partially offset the dominant loss.

## Unpredictable / New-Information Subset

The clearest new-information / gap case remains `67310` on `2023-04-11`.

Additional starter-risk / short-lag cases through this window include `51890` around `2023-04-11` to `2023-04-12` and later May starter losses, but their prior-day concentration evidence is weaker than `67310` because some exposure was newly created or short-lived.

Conclusion:

`UNPREDICTABLE_LOSS_CONCENTRATION_AMPLIFICATION = MATERIAL`

The 67310 shock was not cleanly avoidable by prior-day PIT EXIT authority, but its Portfolio damage was materially amplified by a `22.65%` pre-loss equity share. Concentration control would not make the shock predictable, but it would mechanically reduce its portfolio-level severity.

## 67310 Case Study

Observed lifecycle:

- `2023-04-10`: BUY 100 shares at `3,000`, notional `300,000`
- `2023-04-10` EOD valuation: 100 shares at `4,000`, market value `400,000`
- `2023-04-10` equity: `1,766,350`
- pre-loss position share: `22.65%`
- `2023-04-11`: PM `REDUCE`, reason `risk_increased_but_trend_not_broken`
- `2023-04-11`: BQ/lot-blocked reconsideration materialized to ordinary full `EXIT`
- `2023-04-11`: SELL 100 shares at `3,000`, proceeds `300,000`
- contribution to daily loss: `-100,000`
- total daily loss: `-144,950`

Prior CA/BY classification is preserved: this is `NEW_INFORMATION_OR_GAP_LOSS` / `NOT_PREDETECTABLE_FOR_67310_GAP_LOSS`. No clean pre-loss EXIT authority existed before the 2023-04-11 PIT evidence.

Mechanical sensitivity, holding all else constant:

| 67310 size | 67310 contribution | Mechanical portfolio PnL | Return on prior equity |
|---:|---:|---:|---:|
| 100% actual | -100,000 | -144,950 | -8.21% |
| 75% | -75,000 | -119,950 | -6.79% |
| 50% | -50,000 | -94,950 | -5.38% |
| 25% | -25,000 | -69,950 | -3.96% |

`67310_50_PERCENT_SIZE_MECHANICAL_LOSS = -94,950 total day PnL, with -50,000 from 67310`.

## Winner Concentration Benefit

High-concentration campaign screen:

- peak share `>= 15%` of equity, or
- peak market value `>= 250,000`

High-concentration winner campaign count: `26`

Classification counts:

- `CONCENTRATION_REWARDED`: 6
- `CONCENTRATION_COSTLY`: 9
- `MIXED`: 11

Representative campaigns:

| Symbol | Class | Peak MV | Peak date | Peak share | Positive contrib | Negative contrib | Net contrib | Worst day | Best day | ADD notional |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 59350 | MIXED | 549,000 | 2023-04-06 | 31.13% | 519,500 | -358,700 | 160,800 | -90,500 | 70,000 | 0 |
| 67310 | MIXED | 400,000 | 2023-04-10 | 22.65% | 100,000 | -100,000 | 0 | -100,000 | 100,000 | 0 |
| 68980 | REWARDED | 328,000 | 2023-03-30 | 21.22% | 57,200 | -22,500 | 34,700 | -22,000 | 47,700 | 0 |
| 88900 | REWARDED | 301,000 | 2023-06-01 | 18.59% | 41,600 | -8,300 | 33,300 | -3,600 | 21,200 | 0 |
| 64080 | REWARDED | 297,000 | 2023-04-24 | 18.99% | 30,400 | -9,700 | 20,700 | -9,700 | 19,000 | 0 |
| 51360 | MIXED | 295,400 | 2023-04-19 | 18.43% | 63,200 | -55,100 | 8,100 | -12,700 | 23,900 | 0 |
| 52470 | COSTLY | 292,500 | 2023-04-04 | 17.65% | 18,500 | -31,500 | -13,000 | -21,500 | 16,000 | 0 |
| 60220 | COSTLY | 251,000 | 2023-04-20 | 15.72% | 12,000 | -30,200 | -18,200 | -29,700 | 9,800 | 0 |
| 54010 | MIXED | 196,920 | 2023-03-09 | 15.43% | 54,770 | -48,030 | 6,740 | -8,880 | 7,080 | 118,330 |

The strongest single winner, `59350`, is the core tradeoff case. It produced repeated large positive contributions:

- `2023-03-27`: +60,000
- `2023-03-28`: +60,000
- `2023-03-31`: +70,000
- `2023-04-03`: +70,000
- `2023-04-05`: +70,000
- `2023-04-06`: +70,000
- `2023-04-17`: +70,000

But the same concentration also dominated several large down days:

- `2023-03-29`: -61,400
- `2023-04-07`: -90,500
- `2023-04-12`: -34,500
- `2023-04-18`: -40,000

This supports `CONCENTRATION_MATERIAL_BUT_MIXED`, not `CONCENTRATION_NOT_MATERIAL` and not a clean `CONCENTRATION_EXCESSIVE_UNCOMPENSATED` finding.

## Concentration Mechanism Attribution

### Initial Sizing

`INITIAL_SIZING_CONCENTRATION_MATERIAL = YES`

Japan round-lot plus high share price created large first-position notionals. The clearest example is `67310`, which entered at `300,000` notional and immediately became `22.65%` of equity after the same-day mark to `400,000`.

### Organic Winner Concentration

`ORGANIC_WINNER_CONCENTRATION_MATERIAL = YES`

`59350` had one BUY, no ADD, and grew from a high but plausible initial notional into a `549,000` / `31.13%` peak position through price appreciation. This is the dominant concentration mechanism behind the late severe tail.

### ADD-Driven Concentration

`ADD_DRIVEN_CONCENTRATION_MATERIAL = WEAK_NOT_PRIMARY`

Among the high-concentration set, `54010` is the notable ADD-driven case, with `118,330` ADD notional and a `15.43%` peak share. But the severe loss contributors `59350`, `67310`, and `60220` were not ADD-driven in this evidence window. ADD did not explain the late severe-tail concentration.

## Existing Caps

Current authoritative cap contracts inspected:

- Strategy single-name soft cap: `configs/strategy/portfolio_policy.json#single_name_weight_cap = 0.18`
- Strategy maximum position weight config: `configs/strategy/position_sizing.json#strategy_maximum_position_weight = 0.18`
- Safety hard single-name concentration cap: `configs/safety/portfolio_limits.json#concentration.maximum_position_weight = 0.25`
- Position-count safety hard cap: none; `configs/safety/portfolio_limits.json#position_count.safety_hard_maximum = null`
- Legacy capital deployment config still contains `max_positions = 5`, but Architecture says Runtime must not treat hidden fixed max positions as routine authority unless policy-manifested.

Observed position-share cap breaches:

- `59350` exceeded 25% of equity on 7 completed days: `2023-04-03`, `2023-04-05`, `2023-04-06`, `2023-04-07`, `2023-04-10`, `2023-04-11`, `2023-04-17`
- maximum observed: `31.13%` on `2023-04-06`

`CURRENT_CAPS_VIOLATED = YES_AS_EOD_POSITION_SHARE_FOR_59350`

This is not evidence of a submit-time cap bypass by itself; it is evidence that retained organic appreciation can leave EOD position weight above the 25% safety concentration level.

## Tail Sensitivity

Mechanical dominant-position scaling for severe days:

| Date | Actual PnL | Dominant contributor | 75% size PnL | 50% size PnL | 25% size PnL |
|---|---:|---|---:|---:|---:|
| 2023-03-29 | -61,660 | 59350 -61,400 | -46,310 | -30,960 | -15,610 |
| 2023-04-07 | -80,700 | 59350 -90,500 | -58,075 | -35,450 | -12,825 |
| 2023-04-11 | -144,950 | 67310 -100,000 | -119,950 | -94,950 | -69,950 |
| 2023-04-21 | -57,540 | 60220 -29,700 | -50,115 | -42,690 | -35,265 |

Concentration control would materially reduce the measured tail. A 50% dominant-position mechanical scaling would reduce these severe losses by about `14,850` to `50,000` per day, depending on event.

## Upside Sensitivity

The same mechanical scaling would also remove major winner upside:

- `67310` 2023-04-10 contribution +100,000 becomes +50,000 at 50% size
- `59350` repeated +60,000 to +70,000 daily contributions would lose about +30,000 to +35,000 each at 50% size
- for the listed large positive `59350` days alone, a 50% exposure cut would mechanically remove about `235,000` of upside

`DOWNSIDE_REDUCTION_VS_UPSIDE_LOSS_TRADEOFF = MATERIAL_TWO_SIDED`

The same concentration that creates tail damage also creates a large portion of the observed upside capture.

## Capital Scale And Regime

Later losses became larger mainly because positions became larger in yen and sometimes larger as a share of equity.

- Notional scale effect: `YES`; late severe contributors reached `400,000` to `549,000` notional.
- Position-share effect: `YES`; severe-day median prior max share was `23.30%` versus ordinary negative `16.19%`.
- Total exposure was not primary; severe-day median prior exposure was materially lower than ordinary-negative median exposure in the broader CA/BY findings, and in this CE snapshot the severe cases remain single-name dominated.

Regime around severe events:

- `2023-03-29`: `RECOVERY`
- `2023-04-07`: `BEAR`
- `2023-04-11`: `CORRECTION`
- `2023-04-21`: `RECOVERY`
- May large losses: `BULL` with `CONFLICTED_MARKET_STRUCTURE`

Concentrated losses are not isolated to one regime. They cluster around RECOVERY/CORRECTION/BEAR transitions and conflicted BULL structure, but CE does not justify a regime-based cap change.

## Risk-Adjusted Tradeoff

`CONCENTRATION_RISK_COMPENSATED = MIXED_PARTIALLY_COMPENSATED`

Evidence supports:

- concentration is material to severe downside
- concentration is also material to upside capture
- high concentration winners are not uniformly rewarded: 6 rewarded, 9 costly, 11 mixed
- the dominant late-tail case `59350` remains net positive but with severe giveback
- the clearest unpredictable gap case `67310` is net flat after +100,000 then -100,000

This is not a correctness defect and not a direct Production-rule justification. It is a strong SHADOW study candidate.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-06-01`
2. `EARLY_MEDIAN_MAX_POSITION_SHARE = 16.68%`
3. `LATE_MEDIAN_MAX_POSITION_SHARE = 15.79%`
4. `SEVERE_LOSS_MEDIAN_MAX_POSITION_SHARE = 23.30%`
5. `ORDINARY_NEGATIVE_MEDIAN_MAX_POSITION_SHARE = 16.19%`
6. `SEVERE_LOSS_CONCENTRATION_HIGHER = YES`
7. `TOP1_LOSS_CONTRIBUTOR_SHARE_OF_SEVERE_LOSSES = MEDIAN_84.3%; MEAN_83.1%`
8. `UNPREDICTABLE_LOSS_CONCENTRATION_AMPLIFICATION = MATERIAL`
9. `67310_PRELOSS_POSITION_SHARE = 22.65%`
10. `67310_LOSS_CONTRIBUTION = -100,000`
11. `67310_PRELOSS_PREDICTABLE = NO_CLEAN_PRELOSS_EXIT_AUTHORITY; NEW_INFORMATION_OR_GAP_LOSS`
12. `67310_50_PERCENT_SIZE_MECHANICAL_LOSS = -94,950 total day PnL; -50,000 from 67310`
13. `HIGH_CONCENTRATION_WINNER_CAMPAIGN_COUNT = 26`
14. `CONCENTRATION_REWARDED_COUNT = 6`
15. `CONCENTRATION_COSTLY_COUNT = 9`
16. `CONCENTRATION_MIXED_COUNT = 11`
17. `ORGANIC_WINNER_CONCENTRATION_MATERIAL = YES`
18. `INITIAL_SIZING_CONCENTRATION_MATERIAL = YES`
19. `ADD_DRIVEN_CONCENTRATION_MATERIAL = WEAK_NOT_PRIMARY`
20. `CURRENT_SINGLE_POSITION_CAP = Strategy soft 18%; Safety hard 25%`
21. `CURRENT_CAPS_VIOLATED = YES_AS_EOD_POSITION_SHARE_FOR_59350`
22. `LATE_NOTIONAL_SCALE_EFFECT = YES`
23. `LATE_POSITION_SHARE_EFFECT = YES_FOR_SEVERE_SINGLE_NAME_TAIL; NO_FOR_LATE_MEDIAN_ALL_DAYS`
24. `DOWNSIDE_REDUCTION_VS_UPSIDE_LOSS_TRADEOFF = MATERIAL_TWO_SIDED`
25. `CONCENTRATION_RISK_COMPENSATED = MIXED_PARTIALLY_COMPENSATED`
26. `UNPREDICTABLE_LOSS_IMPACT_REDUCIBLE_BY_CONCENTRATION_CONTROL = MATERIAL`
27. `PRIMARY_CONCENTRATION_MECHANISM = ORGANIC_WINNER_CONCENTRATION_PLUS_HIGH_NOTIONAL_INITIAL_LOT_ENTRY; ADD_NOT_PRIMARY`
28. `PRODUCTION_CHANGE_JUSTIFIED = NO`
29. `SHADOW_FOLLOWUP_JUSTIFIED = YES`
30. `NEXT_RECOMMENDED_STEP = READ-ONLY/SHADOW risk-allocation study using existing PC/PS/cap architecture to test concentration-aware retention/sizing diagnostics, with explicit upside-retention controls for 59350-style winners and gap-risk controls for 67310-style high-notional starters.`
31. `FINAL_JUDGMENT = PHASE32_CE_SINGLE_CAMPAIGN_CONCENTRATION_MATERIAL_MIXED_REWARDED_AND_COSTLY_SHADOW_RISK_ALLOCATION_STUDY_JUSTIFIED_PRODUCTION_CHANGE_NOT_JUSTIFIED`

## Final Judgment

`PHASE32_CE_SINGLE_CAMPAIGN_CONCENTRATION_MATERIAL_MIXED_REWARDED_AND_COSTLY_SHADOW_RISK_ALLOCATION_STUDY_JUSTIFIED_PRODUCTION_CHANGE_NOT_JUSTIFIED`
