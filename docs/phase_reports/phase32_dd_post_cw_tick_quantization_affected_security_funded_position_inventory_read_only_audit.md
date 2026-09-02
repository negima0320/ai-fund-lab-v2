# Phase32-DD — Post-CW Tick-Quantization Affected Security / Funded Position Inventory READ-ONLY Audit

## Scope

Target run:

`runtime-test-historical-extended-smoke-20260901T223409325599Z`

This is a READ-ONLY impact inventory. No Production source, config, runtime
state, Pending, Ledger, replay, resume, recover, or fresh-run operation was
executed. No future returns, PnL, MFE/MAE, later campaign outcomes, or
symbol-specific blacklist logic were used.

Completed evidence used at audit time:

`2022-10-03` through `2023-04-21`, 137 completed business days.

## Classification Basis

`DC_SHADOW_SEMANTICS_REUSED = YES`

Phase32-DC states reused without PnL tuning:

- `ROBUST`
- `ACCEPTABLE`
- `QUANTIZED_CAUTION`
- `INSUFFICIENT_EVIDENCE`

The SHADOW classifier used PIT reference price, available minimum-tick evidence
or the existing PC-compatible tick value, `single_tick_pct`, close-level
diversity, ticks traversed, directional close changes, and existing PIT
momentum/MA features. It did not create a Production rule.

## Security-Level Inventory

`TICK_QUANTIZATION_SECURITY_INVENTORY`

Materiality-sorted inventory:

| Symbol | Price range | Median tick pct | Candidate obs | Top10 | Top5 | Positive score | BQ HIGH | BQ FULL | Entry admit | PC positive | QC obs | BUY fills | QC funded fills | BUY notional |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 93180 | 1-5 | 33.33% | 137 | 136 | 130 | 131 | 67 | 58 | 137 | 58 | 102 | 1 | 1 | 23,800 |
| 89180 | 9-11 | 10.00% | 115 | 0 | 0 | 0 | 0 | 0 | 115 | 1 | 88 | 1 | 1 | 37,000 |
| 76470 | 26-29 | 3.70% | repeated | 35 QC top10 | 23 QC top5 | mixed | 34 QC HIGH | 20 QC FULL | repeated reduced/allowed | 3 QC positive | 53 | funded outside QC case | 0 | not material as QC funded |
| 21340 | low/elevated | limited | limited | limited | limited | mixed | limited | limited | reduced | 0 | 7 | 0 | 0 | 0 |
| 17570 | low/elevated | limited | limited | limited | limited | mixed | limited | limited | reduced | 0 | 2 | funded outside QC case | 0 | not material as QC funded |
| Normal controls | >50 | <1% | broad | broad | broad | broad | broad | broad | broad | broad | 0 | many | 0 | broad |

Important clarification:

The low-price universe is small. DD does not find that every low-price security
is materially distorted. The actual funded tick-caution inventory is narrow.

## Materiality Classification

`SECURITY_LEVEL_TICK_MATERIALITY_CLASSIFICATION`

| Symbol | Classification | Basis |
|---|---|---|
| 93180 | `HIGH_MATERIALITY_TICK_DISTORTION` | Repeated extreme-tick `QUANTIZED_CAUTION`, 136/137 Top10, 130/137 Top5, 67 BQ HIGH, 58 BQ FULL, 58 PC-positive rows, one funded BUY_NEW and long position-slot presence |
| 89180 | `POTENTIAL_TICK_DISTORTION` | Extreme tick and one funded BUY_NEW, but no Top10/Top5, no positive opportunity-score rows, no BQ HIGH/FULL; impact is mostly a small initial low-confidence funded case |
| 76470 | `POTENTIAL_TICK_DISTORTION_NONFUNDED_RANK_POLLUTION` | Multiple QC Top10/Top5 and BQ HIGH/FULL observations, but no QC funded fill observed in the audited run |
| 21340 / 17570 / 17730 | `LOW_PRICE_NOT_MATERIAL` | QC observations exist but limited rank/capital impact |
| 33500 / 67400 and similar elevated low-price funded rows | `LOW_PRICE_ROBUST_OR_ACCEPTABLE_CONTROL_CANDIDATES` | Funded at low/elevated prices without DC QC classification in the actual fill case |

## Actually Funded Tick-Caution Cases

`QUANTIZED_CAUTION_FUNDED_CASES`

| Date | Symbol | Action | Reference price | Execution price | Tick evidence | `single_tick_pct` | Shares | Notional | Target weight | Candidate rank | Buy rank / score | BQ | Entry | DC state | Campaign |
|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---|---|---|---|---|
| 2022-10-03 | 89180 | BUY_NEW | 9.0 | 10.0 | PC field/authority | 11.11% | 3,700 | 37,000 | 0.033636 | 22 | 25 / -0.33896623 | MEDIUM / REDUCED | BUY_NEW_REDUCED_ONLY | QUANTIZED_CAUTION | pc-843fbc56e8560b30-89180-0001 |
| 2023-03-15 | 93180 | BUY_NEW | 3.0 | 2.0 | PC field/authority | 33.33% | 11,900 | 23,800 | 0.029412 | 2 | 3 / 0.27460966 | HIGH / FULL | BUY_NEW_REDUCED_ONLY | QUANTIZED_CAUTION | pc-762ddee5bae0f9e4-93180-0001 |

No actual REENTRY or BUY_ADD fill was found with `QUANTIZED_CAUTION` at the fill
date in the completed evidence.

`QUANTIZED_CAUTION_FUNDED_UNIQUE_SYMBOL_COUNT = 2`

`QUANTIZED_CAUTION_FUNDED_UNIQUE_SYMBOLS = [89180, 93180]`

## Position Slot Impact

`QUANTIZED_CAUTION_POSITION_CAMPAIGN_COUNT = 2`

Campaigns:

- `pc-843fbc56e8560b30-89180-0001`
- `pc-762ddee5bae0f9e4-93180-0001`

`QUANTIZED_CAUTION_POSITION_SLOT_DAYS = AT_LEAST_27_CONFIRMED`

Evidence:

- 93180 campaign slot days confirmed from position campaign snapshots: 26
  completed business days from `2023-03-16` through `2023-04-21`.
- 89180 is at least one funded campaign/slot event on `2022-10-03`; sustained
  slot-day continuity was not confirmed from the later position campaign
  snapshots.

This is conservative. It counts observed slot presence, not future performance.

## Capital Impact

`QUANTIZED_CAUTION_CAPITAL_ALLOCATION_PROFILE`

| Metric | Value |
|---|---:|
| Total BUY fills in completed evidence | 225 |
| Total BUY notional | 14,169,160 JPY |
| QC funded BUY notional | 60,800 JPY |
| QC funded share of BUY notional | 0.4291% |
| QC funded average initial target weight | 3.1524% |
| QC funded symbols | 2 |
| Dominant QC slot case | 93180 |

Capital notional impact is small. Position-slot and rank/capital-competition
pollution are the material issues.

## 93180 Relative Materiality

`93180_RELATIVE_MATERIALITY = DOMINANT_CASE`

93180 is the dominant funded and rank-pollution case:

- It accounts for 102 `QUANTIZED_CAUTION` observations.
- It accounts for 97 QC Candidate Top5 observations.
- It accounts for 56 QC BQ HIGH observations.
- It accounts for 47 QC BQ FULL observations.
- It accounts for 50 QC PC-positive rows.
- It has the only confirmed sustained QC position slot presence.

89180 is a confirmed non-93180 QC funded case, but not a strong-rank/BQ
confirmation case.

`NON_93180_MATERIAL_TICK_DISTORTION_SECURITIES = 89180_CONFIRMED_FUNDED_SMALL; 76470_CONFIRMED_RANK_BQ_POLLUTION_NONFUNDED`

No additional non-93180 high-materiality funded tick-distortion security was
confirmed.

## High-Rank Non-Funded Cases

`QUANTIZED_CAUTION_HIGH_RANK_NONFUNDED_CASES`

Representative rows:

| Date | Symbol | Price | Tick pct | Candidate rank | Buy rank / score | BQ | Entry | Target |
|---|---|---:|---:|---:|---|---|---|---:|
| 2022-10-03 | 93180 | 3 | 33.33% | 3 | 4 / -0.07958341 | UNUSABLE / REJECT | BUY_NEW_REDUCED_ONLY | 0 |
| 2022-10-21 | 93180 | 4 | 25.00% | 2 | 3 / 0.0836403 | HIGH / FULL | BUY_NEW_REDUCED_ONLY | 0.030667 |
| 2022-11-15 | 76470 | 26 | 3.85% | 6 | 4 / 0.22529895 | HIGH / FULL | BUY_NEW_REDUCED_ONLY | 0 |
| 2022-11-22 | 76470 | 27 | 3.70% | 4 | 2 / 0.27782837 | HIGH / FULL | BUY_NEW_REDUCED_ONLY | 0 |
| 2022-11-25 | 76470 | 27 | 3.70% | 4 | 2 / 0.27806976 | HIGH / FULL | BUY_NEW_ALLOWED | 0.032258 |

These are rank/capital-competition pollution examples even where no fill
occurred in that security/date.

## Positive And Normal Controls

`LEGITIMATE_LOW_PRICE_POSITIVE_CONTROLS`

Funded low/elevated-price cases that must not be automatically suppressed by
Phase33:

| Date | Symbol | Reference price | Tick tier | Action | Notional | Entry / rank |
|---|---|---:|---|---|---:|---|
| 2022-10-07 | 33500 | 39.8 | ELEVATED | BUY_NEW | 35,100 | BUY_NEW_REDUCED_ONLY / rank 21 |
| 2022-10-12 | 76470 | 28.0 | ELEVATED | BUY_NEW | 21,600 | BUY_NEW_REDUCED_ONLY / rank 15 |
| 2022-10-20 | 17570 | 26.0 | ELEVATED | BUY_NEW | 28,800 | BUY_NEW_REDUCED_ONLY / rank 17 |
| 2023-04-13 | 67400 | 50.0 | ELEVATED | BUY_NEW | 46,000 | BUY_NEW_ALLOWED / rank 39 |

These controls are low/elevated price but were not classified as QC on their
actual fill date. Future implementation must preserve the ability to fund such
cases when PIT tick structure is acceptable.

`NORMAL_PRICE_CONTROL_CASES`

Representative normal-price controls:

- 76920 on `2023-03-15`: price 563.7, normal tick tier, BQ HIGH/FULL,
  Entry BUY_NEW_REDUCED_ONLY, DC state ROBUST.
- 94320 on `2023-03-15`: price 157.9, normal tick tier, BQ HIGH/reduced,
  Entry ADD_REDUCED_ONLY, DC state ROBUST/ACCEPTABLE ordinary path.
- 83060 across the run: normal-price funded repeated BUY/ADD activity, no QC
  observations.

## Price Level vs Tick Structure

`PRICE_LEVEL_VS_TICK_STRUCTURE_CAUSAL_ASSESSMENT = TICK_STRUCTURE_NOT_PRICE_BUCKET_ALONE`

Evidence:

- 93180 at 1-5 JPY is high-materiality because it combines extreme
  `single_tick_pct`, low close-level diversity, repeated strong rank/BQ, and
  actual funding.
- 89180 at 9-11 JPY is extreme tick but not strong-ranked and only small
  materiality.
- 6-10 and 11-20 buckets did not generally produce Top10/Top5 or BQ HIGH/FULL.
- Some 21-50 JPY/elevated-tick rows, especially 76470, show rank/BQ pollution
  even though price is not ultra-low.

Price alone is not the defect. Tick structure plus weak robustness is the causal
shape.

## Pollution Profiles

`QUANTIZED_CAUTION_CANDIDATE_RANK_POLLUTION`

| QC subset | Security-date observations | Unique symbols | Dominant symbols |
|---|---:|---:|---|
| Candidate Top50 | 252 | 5 | 93180, 89180, 76470 |
| Candidate Top10 | 137 | 2 | 93180, 76470 |
| Candidate Top5 | 120 | 2 | 93180, 76470 |

`QUANTIZED_CAUTION_BQ_CONFIRMATION_PROFILE`

| QC subset | Security-date observations | Unique symbols | Dominant symbols |
|---|---:|---:|---|
| BQ HIGH | 90 | 2 | 93180 56, 76470 34 |
| BQ FULL | 67 | 2 | 93180 47, 76470 20 |

`QUANTIZED_CAUTION_ENTRY_ADMISSION_PROFILE`

| Entry action | QC observations | Unique symbols |
|---|---:|---:|
| BUY_NEW_REDUCED_ONLY | 240 | 6 |
| ADD_REDUCED_ONLY | 9 | 3 |
| BUY_NEW_ALLOWED | 4 | 2 |

BQ/Entry pollution is concentrated in repeated 93180 and 76470 observations.
Only 93180 converted that strong-rank/QC shape into a confirmed sustained funded
position in this completed evidence.

## Existing PC Protection

`EXISTING_PC_PROTECTION_EFFECT`

Existing PC protection was active and useful:

- `single_tick_pct` / tier evidence was present for funded QC cases.
- Both funded QC cases were `EXTREME`.
- Low-price authority status was `PASS` because PIT liquidity/capacity evidence
  was present.
- Tick caps existed: 5% for EXTREME.
- Actual target weights were below the 5% cap: 89180 at 3.3636%, 93180 at
  2.9412%.

Interpretation:

PC mitigated capital risk but did not solve upstream opportunity-quality risk.
The remaining issue is rank/BQ/Entry confidence and position-slot admission, not
oversized notional.

## DC Shadow Funded Reclassification

`DC_SHADOW_FUNDED_CASE_RECLASSIFICATION`

| Case | Current Production | DD/DC SHADOW |
|---|---|---|
| 89180 2022-10-03 | BUY_NEW_REDUCED_ONLY, BQ MEDIUM/reduced, small funded notional | `reduced confidence`; possibly still reduced admission because rank was not strong and capital was small |
| 93180 2023-03-15 | BUY_NEW_REDUCED_ONLY, BQ HIGH/FULL, funded and sustained slot | `BUY_WAIT or REVIEW_REQUIRED candidate` would be reasonable under DC because strong rank/BQ depends on two-level 2/3 JPY tick structure; final action remains conditional for Phase33 |

DD does not force a Production action. It identifies which funded cases require
Phase33 validation coverage.

## Tick Authority Limitation

`DEFAULT_TICK_ASSUMPTION_CASE_COUNT = 555 joined observations`

Funded QC cases used available PC field/authority evidence for `single_tick_pct`.
Across the broader joined sample, 555 observations required the default
`1.0 / reference_price` fallback for SHADOW analysis.

`DD_TICK_AUTHORITY_LIMITATION = MATERIAL_FOR_PRODUCTION_PROMOTION`

The DD inventory is sufficient for READ-ONLY impact analysis, but Production
promotion still requires the DC prerequisite: explicit run/date-bound minimum
tick authority. The current default `1.0` is not enough to claim Production-grade
precision for all JPX price bands/security types.

## Phase33 Control Set

`PHASE33_TICK_IMPLEMENTATION_CONTROL_SET`

Minimum PIT-only control set:

| Class | Case |
|---|---|
| 93180 admitted quantized case | 93180, 2023-03-15, BUY_NEW filled, BQ HIGH/FULL, QC |
| 93180 rejected case | 93180, 2023-02-21, BQ UNUSABLE/REJECT, target 0 |
| Non-93180 funded QC case | 89180, 2022-10-03, BUY_NEW filled, BQ MEDIUM/reduced, QC |
| Non-93180 rank/BQ pollution | 76470, 2022-11-22 or 2022-11-25, BQ HIGH/FULL, QC, not confirmed funded that date |
| Legitimate low/elevated positive controls | 33500 2022-10-07, 76470 2022-10-12, 67400 2023-04-13 |
| Normal-price controls | 76920 2023-03-15, 94320 2023-03-15, 83060 funded normal-price rows |

## Phase32 Closure

`NEW_PHASE32_CLOSURE_BLOCKER_FOUND = NO`

DD found no new Runtime correctness blocker beyond the DB/DC-confirmed Strategy
architecture gap. The issue remains appropriate for Phase33 carry-forward unless
Phase32 scope is explicitly expanded.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-04-21`
2. `DC_SHADOW_SEMANTICS_REUSED = YES`
3. `TICK_QUANTIZATION_SECURITY_INVENTORY = material inventory led by 93180, then 89180 funded-small, 76470 nonfunded rank/BQ pollution, then limited low-materiality cases`
4. `SECURITY_LEVEL_TICK_MATERIALITY_CLASSIFICATION = 93180 HIGH_MATERIALITY_TICK_DISTORTION; 89180 POTENTIAL_TICK_DISTORTION funded-small; 76470 POTENTIAL_TICK_DISTORTION_NONFUNDED_RANK_POLLUTION; others LOW_PRICE_NOT_MATERIAL or positive controls`
5. `QUANTIZED_CAUTION_FUNDED_CASES = 89180 2022-10-03 BUY_NEW 3700 shares 37000 JPY; 93180 2023-03-15 BUY_NEW 11900 shares 23800 JPY`
6. `QUANTIZED_CAUTION_FUNDED_UNIQUE_SYMBOL_COUNT = 2`
7. `QUANTIZED_CAUTION_FUNDED_UNIQUE_SYMBOLS = [89180, 93180]`
8. `QUANTIZED_CAUTION_POSITION_CAMPAIGN_COUNT = 2`
9. `QUANTIZED_CAUTION_POSITION_SLOT_DAYS = AT_LEAST_27_CONFIRMED; 93180 26 confirmed, 89180 at least funded campaign event`
10. `QUANTIZED_CAUTION_CAPITAL_ALLOCATION_PROFILE = 60800 JPY, 0.4291% of 14169160 JPY total BUY notional, average initial target weight 3.1524%`
11. `93180_RELATIVE_MATERIALITY = DOMINANT_CASE`
12. `NON_93180_MATERIAL_TICK_DISTORTION_SECURITIES = 89180 confirmed funded-small; 76470 confirmed nonfunded rank/BQ pollution; no additional high-materiality funded case confirmed`
13. `QUANTIZED_CAUTION_HIGH_RANK_NONFUNDED_CASES = repeated 93180 rejected/zero-target rows and 76470 2022-11-15/22/24/25 rank/BQ rows`
14. `LEGITIMATE_LOW_PRICE_POSITIVE_CONTROLS = 33500 2022-10-07, 76470 2022-10-12, 17570 2022-10-20, 67400 2023-04-13`
15. `NORMAL_PRICE_CONTROL_CASES = 76920 2023-03-15, 94320 2023-03-15, 83060 normal-price funded rows`
16. `PRICE_LEVEL_VS_TICK_STRUCTURE_CAUSAL_ASSESSMENT = tick structure and robustness, not price bucket alone`
17. `QUANTIZED_CAUTION_CANDIDATE_RANK_POLLUTION = Top50 252 obs/5 symbols; Top10 137 obs/2 symbols; Top5 120 obs/2 symbols`
18. `QUANTIZED_CAUTION_BQ_CONFIRMATION_PROFILE = BQ HIGH 90 obs/2 symbols; BQ FULL 67 obs/2 symbols`
19. `QUANTIZED_CAUTION_ENTRY_ADMISSION_PROFILE = BUY_NEW_REDUCED_ONLY 240, ADD_REDUCED_ONLY 9, BUY_NEW_ALLOWED 4`
20. `EXISTING_PC_PROTECTION_EFFECT = capital-risk mitigation present; upstream opportunity-quality and slot-admission gap remains`
21. `DC_SHADOW_FUNDED_CASE_RECLASSIFICATION = 89180 reduced confidence; 93180 likely BUY_WAIT/REVIEW_REQUIRED candidate under Phase33 contract, final action conditional`
22. `FUTURE_PNL_USED_FOR_MATERIALITY = NO`
23. `DEFAULT_TICK_ASSUMPTION_CASE_COUNT = 555`
24. `DD_TICK_AUTHORITY_LIMITATION = current default tick is acceptable for SHADOW inventory but insufficient for Production promotion`
25. `PHASE33_TICK_IMPLEMENTATION_CONTROL_SET = 93180 admitted, 93180 rejected, 89180 funded QC, 76470 nonfunded BQ/rank pollution, 33500/76470/67400 low-price controls, 76920/94320/83060 normal controls`
26. `NEW_PHASE32_CLOSURE_BLOCKER_FOUND = NO`
27. `PRODUCTION_CHANGE_EXECUTED = NO`
28. `TARGET_RUN_MUTATED = NO`
29. `NEXT_RECOMMENDED_STEP = carry DD control set into Phase33 tick-quantization implementation; first formalize minimum-tick authority, then add Technical Features/SI/Candidate/BQ/Entry evidence propagation and focused controls`
30. `FINAL_JUDGMENT = PHASE32_DD_TICK_QUANTIZATION_FUNDED_IMPACT_INVENTORIED_93180_DOMINANT_89180_SMALL_NON93180_CASE_CONFIRMED_PHASE33_CONTROL_SET_READY`

## Final Judgment

`PHASE32_DD_TICK_QUANTIZATION_FUNDED_IMPACT_INVENTORIED_93180_DOMINANT_89180_SMALL_NON93180_CASE_CONFIRMED_PHASE33_CONTROL_SET_READY`

93180 is effectively the dominant material funded extreme-tick case in the
current Post-CW run. A second non-93180 funded QC case, 89180 on 2022-10-03, is
confirmed but small and not a strong-rank/BQ confirmation case. 76470 is the main
nonfunded rank/BQ pollution control. DD finds no new Phase32 Runtime correctness
blocker and makes no Production change. The correct next step is Phase33
implementation planning using the compact control set above, with explicit
minimum-tick authority resolved first.
