# Phase32-BY — Post-BQ Long-Run Profit Retention / Large-Loss Mechanism READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- Audit mode: READ-ONLY
- Snapshot used for quantitative audit: completed evidence through `2023-04-18`
- Target requirement: through at least `2023-04-17`
- Run was still progressing while inspected; later evidence was not chased for this report.

No code, config, model, threshold, weight, PM/SELL/HOLD semantics, feature/model, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run mutation was performed. The running Historical validation was not interrupted.

Old baseline raw run artifacts were not present in `reports/runtime_tests/runs` at the time of this audit; old-baseline comparison is therefore limited to previously recorded report-level evidence and is not treated as a same-path counterfactual.

## Performance Shape

| Metric | Value |
|---|---:|
| Initial capital | 1,000,000 |
| First completed valuation equity, 2022-10-03 | 1,012,350 |
| Latest audited equity, 2023-04-18 | 1,601,100 |
| Current return vs initial capital | +60.11% |
| Peak equity/date | 1,766,350 on 2023-04-10 |
| Peak return vs initial capital | +76.64% |
| Maximum drawdown | -185,960 |
| Maximum drawdown percent | -10.53% from peak |
| Maximum drawdown trough/date | 1,580,390 on 2023-04-14 |
| Peak-to-latest audited giveback | -165,250 |
| Largest positive day | 2023-03-30, +94,850 |
| Largest negative day | 2023-04-11, -144,950 |

Top positive daily PnL days:

| Rank | Date | Daily PnL |
|---:|---|---:|
| 1 | 2023-03-30 | +94,850 |
| 2 | 2023-04-10 | +83,510 |
| 3 | 2023-04-03 | +82,880 |
| 4 | 2023-03-27 | +64,260 |
| 5 | 2023-04-06 | +59,760 |
| 6 | 2023-03-22 | +59,360 |
| 7 | 2023-03-31 | +59,270 |
| 8 | 2023-04-17 | +58,160 |
| 9 | 2023-03-16 | +47,230 |
| 10 | 2023-04-05 | +46,390 |

Top negative daily PnL days:

| Rank | Date | Daily PnL |
|---:|---|---:|
| 1 | 2023-04-11 | -144,950 |
| 2 | 2023-04-07 | -80,700 |
| 3 | 2023-03-29 | -61,660 |
| 4 | 2023-04-18 | -37,450 |
| 5 | 2023-04-12 | -37,110 |
| 6 | 2022-12-19 | -33,550 |
| 7 | 2022-11-14 | -31,710 |
| 8 | 2023-04-04 | -30,710 |
| 9 | 2022-12-07 | -30,130 |
| 10 | 2023-04-14 | -26,700 |

Distribution counts:

- Daily PnL `<= -20,000`: 11
- Daily PnL `<= -30,000`: 9
- Daily PnL `<= -50,000`: 3
- Daily PnL `<= -100,000`: 1
- Daily PnL `>= +20,000`: 20
- Daily PnL `>= +50,000`: 8
- Daily PnL `>= +100,000`: 0

Return distribution classification:

`MANY_LARGE_GAINS_PLUS_FEW_EXTREME_LOSSES`

Upside generation is not weak. The limiting shape is that a small set of very large negative days gives back a material portion of the strong March-April expansion.

## Upside Capture

Upside capture remains strong.

The March-April expansion is dominated by large winner campaigns, especially `59350` and `67310`.

Representative upside contributors:

- `2023-03-30`: +94,850 total; `59350` contributed about +47,100 from held-price appreciation and `68980` contributed about +47,700 from same-day buy-to-close valuation.
- `2023-04-03`: +82,880 total; `59350` contributed about +70,000, and `52470` contributed about +16,000 after BUY.
- `2023-04-06`: +59,760 total; `59350` contributed about +70,000, offset by `52470` sell slippage/loss.
- `2023-04-10`: +83,510 total; `67310` contributed about +100,000 on the entry day, offset by `59350` weakness and other smaller effects.

`BQ_WINNER_CAPTURE_IMPAIRMENT_FOUND = NO_CONCRETE_EVIDENCE`

BQ/BV SELL behavior did not prevent the run from generating large winners. The evidence instead shows strong upside capture followed by concentrated giveback.

## Large Loss Episodes

### Episode A: 2023-03-28 -> 2023-03-29

- Equity: `1,512,760 -> 1,451,100`
- Loss: `-61,660`

Dominant contributors:

- `59350`: about `-61,400`, held 100 shares, price `3238 -> 2624`
- `43880`: about `-6,800`
- `37870`: about `-3,100`
- `70660`: about `-2,100`
- Offset: `52460` about `+7,900`

PIT/action context:

- `59350` had very strong prior upside and large unrealized profit.
- On 2023-03-27 and 2023-03-28, PM evidence included `positive_expected_edge` and `profit_retention_break`.
- On 2023-03-29, after the loss, PM still held with `strong_trend_continuation`, `opportunity_rank_still_high`, and `no_loss_averaging`.

Classification: `WINNER_PROFIT_RETENTION_LATE` and `HOLD_CONFIRMATION_LAG`.

### Episode B: 2023-04-06 -> 2023-04-07

- Equity: `1,763,540 -> 1,682,840`
- Loss: `-80,700`

Dominant contributors:

- `59350`: about `-90,500`, held 100 shares, price `5490 -> 4585`
- Offset: `43880` about `+8,700`

PIT/action context:

- `59350` was still held despite extremely large unrealized profit.
- 2023-04-06 PM evidence included `positive_expected_edge` and `profit_retention_break`.
- 2023-04-07 PM evidence switched to `trend_continuation` and `positive_expected_edge`, still HOLD.

Classification: `WINNER_PROFIT_RETENTION_LATE` and `HOLD_CONFIRMATION_LAG`.

### Episode C: 2023-04-10 -> 2023-04-11

- Equity: `1,766,350 -> 1,621,400`
- Loss: `-144,950`

Dominant contributors:

- `67310`: about `-100,000`, bought/valued at 4000 on 2023-04-10 and sold at 3000 on 2023-04-11
- `59350`: about `-25,000`, held 100 shares, price `4450 -> 4200`
- `51890`: about `-19,000`, bought on 2023-04-11 and valued lower by close

PIT/action context:

- `67310` was not a long-held pre-warning case in this run. It generated a large 2023-04-10 upside contribution and was BQ FULL EXIT on 2023-04-11 after PM REDUCE.
- `67310` BQ evidence on 2023-04-11: PM `REDUCE`, raw reduce `25`, lot-blocked, `SHADOW_FULL_EXIT`, SELL quantity `100`.
- The `67310` loss is not counted as clearly avoidable by prior-day PIT evidence because the main price gap occurred before the 2023-04-11 sell materialization could avoid it.
- `59350` remained the continuing winner-retention lag contributor.

Classification: `NOT_PREDETECTABLE_FOR_67310_GAP_LOSS`, plus continuing `WINNER_PROFIT_RETENTION_LATE` for `59350`.

## Other Material Givebacks

Other material negative days:

- `2023-04-12`: `-37,110`; includes `51890` deterioration after 2023-04-11 entry, then 2023-04-12 REDUCE lot-block/BQ insufficient and 2023-04-13 native EXIT.
- `2023-04-18`: `-37,450`; includes continuing post-peak weakness and a 2023-04-13 `41660` lot-blocked REDUCE with BQ `SHADOW_HOLD`, followed by material decline.
- `2022-12-19`: `-33,550`; characterized in Phase32-BX, with `97310` as strongest pre-detected under-materialized case.

## Earliest PIT Detectability

Material contributors:

| Symbol | Earliest deterioration | Earliest PM REDUCE | Earliest PM EXIT | Earliest BQ eval | BQ outcome | Classification |
|---:|---|---|---|---|---|---|
| 59350 | profit-retention warning context present by 2023-03-27 | not observed before the major 3/29 and 4/7 losses | not observed in audited loss window | not applicable | not applicable | `HOLD_CONFIRMATION_LAG` / `WINNER_PROFIT_RETENTION_LATE` |
| 67310 | 2023-04-11 | 2023-04-11 | BQ-promoted EXIT on 2023-04-11 | 2023-04-11 | `SHADOW_FULL_EXIT` | `PREDETECTED_AND_MANAGED_AFTER_NEW_INFORMATION`; gap loss not clearly avoidable |
| 97310 | 2022-12-14 | 2022-12-14 | 2022-12-20 | 2022-12-14 | `SHADOW_INSUFFICIENT_EVIDENCE` | `BQ_INSUFFICIENT_LATER_LOSS` |
| 51890 | 2023-04-12 | 2023-04-12 | 2023-04-13 | 2023-04-12 | `SHADOW_INSUFFICIENT_EVIDENCE` | `PREDETECTED_BUT_UNDER_MATERIALIZED`, short lag |
| 52470 | 2023-04-05 | 2023-04-05 | 2023-04-06 | 2023-04-05 | `SHADOW_INSUFFICIENT_EVIDENCE` | `PREDETECTED_BUT_UNDER_MATERIALIZED`, short lag |
| 41660 | 2023-04-13 | 2023-04-13 | not observed by 2023-04-18 | 2023-04-13 | `SHADOW_HOLD` | `BQ_HOLD_LATER_LOSS` |

## BQ Actual Effectiveness

Through the 2023-04-18 audit snapshot:

- Actual BQ FULL EXIT promotions: `31`
- Non-promoted lot-blocked REDUCE cases: `220`
- Non-promoted BQ outcomes:
  - `SHADOW_INSUFFICIENT_EVIDENCE`: `201`
  - `SHADOW_HOLD`: `18`
  - unpaired/blank: `1`

Short-horizon descriptive outcome for BQ-promoted events with available sell fill and market data:

- Avoided-loss-like: `8`
- Rebound/false-exit-like: `6`
- Mixed volatile: `1`
- Insufficient horizon/data: `13`

This indicates BQ is active and sometimes protective, but not a complete tail-loss solution.

## 97310-Type Repetition

Structural pattern searched:

PM REDUCE -> lot-blocked -> BQ `SHADOW_INSUFFICIENT_EVIDENCE` or `SHADOW_HOLD` -> NO_ORDER -> later material loss.

Candidates with later five-business-day loss of at least about 10,000:

| Warning date | Symbol | BQ | Approx later loss | Worst date | Notes |
|---|---:|---|---:|---|---|
| 2022-12-02 | 78860 | `SHADOW_INSUFFICIENT_EVIDENCE` | -18,400 | 2022-12-07 | recurrent pre-BQ-insufficient tail |
| 2022-12-14 | 97310 | `SHADOW_INSUFFICIENT_EVIDENCE` | -24,500 to -30,200 depending baseline | 2022-12-20 | strongest BX case |
| 2023-02-24 | 14000 | `SHADOW_INSUFFICIENT_EVIDENCE` | -17,400 | 2023-03-02 | repeated campaign warning |
| 2023-03-01 | 14000 | `SHADOW_INSUFFICIENT_EVIDENCE` | -15,800 | 2023-03-02 | same campaign, do not double-count fully |
| 2023-04-05 | 52470 | `SHADOW_INSUFFICIENT_EVIDENCE` | -10,000 | 2023-04-06 | short lag to native EXIT |
| 2023-04-13 | 41660 | `SHADOW_HOLD` | -32,100 | 2023-04-18 | most important post-peak recurrence |

`97310_PATTERN_RECURRENT = YES`

It is not isolated, though the strongest audited cases are concentrated in a handful of campaigns.

## HOLD Confirmation Lag

HOLD confirmation lag is recurrent and material.

Evidence:

- `59350` remained held through very large unrealized profit and repeated large down days. PM reason codes alternated among `positive_expected_edge`, `profit_retention_break`, `trend_continuation`, and `downside_risk_contained`. The presence of `profit_retention_break` inside HOLD contexts indicates warning evidence existed, but it did not become sell authority before the largest losses.
- `99840`, `23350`, `61440`, `72730`, and `45410` in BX showed similar late transition characteristics around 2022-12-20.
- `41660` showed a later 2023-04 pattern: PM REDUCE with `peak_drawdown_warning`, BQ `SHADOW_HOLD`, then material decline.

This is not labeled a correctness defect by itself. It is a performance bottleneck characterization: the system can retain winners long enough to capture upside, but often waits for stronger terminal confirmation before materially reducing exposure.

## Profit Retention

`WINNER_PROFIT_RETENTION_LATE_SUPPORTED = YES`

Key examples:

- `59350`:
  - 2023-03-27 unrealized PnL: about `+51,600`
  - 2023-03-28 unrealized PnL: about `+111,600`
  - 2023-04-06 unrealized PnL: about `+336,800`
  - 2023-04-14 unrealized PnL: about `+154,800`
  - Approx campaign giveback from 2023-04-06 to 2023-04-14: `-182,000`
  - PM still recorded HOLD-type evidence after major drops.
- `67310`:
  - 2023-04-10 contributed about `+100,000`.
  - 2023-04-11 BQ FULL EXIT sold at 3000 after prior valuation at 4000, producing about `-100,000`.
  - This looks more like one-day gap risk than pre-detected late retention.

Remaining performance limitation is materially connected to late winner profit retention, especially `59350`.

## Regime/Transition Characterization

Large givebacks cluster around deterioration/transition-like windows:

- 2022-12-15 -> 2022-12-20: exposure expanded, then sharp risk reduction.
- 2023-03-28 -> 2023-03-29: post-surge giveback after a major winner jump.
- 2023-04-06 -> 2023-04-14: peak-to-drawdown window after strong expansion.

The system appears strong inside the expansion itself, but slower around deterioration transitions and post-winner giveback zones.

`TRANSITION_GIVEBACK_CLUSTER_SUPPORTED = YES`

This conclusion is based on PIT decision/action timing and contribution concentration, not regime labels alone.

## Old Baseline Comparison

The pre-BQ baseline raw run directory was not available in the current workspace, so a full current-vs-old comparison through 2023-04-18 is `INSUFFICIENT_EVIDENCE`.

Available prior report-level comparison from Phase32-BW:

- On 2022-11-16, current post-BQ/BV run equity was higher than old baseline by `+9,810`.
- Current cash was higher by `+142,810`, and market value lower by `-133,000`.

No reliable old-baseline large-loss count or max-drawdown comparison through 2023-04-18 could be recomputed from raw evidence in this audit.

## Primary Bottleneck Judgment

Selected bottleneck:

`MIXED`

Components:

- `LARGE_LOSS_TAIL_DOMINANT`
- `WINNER_PROFIT_RETENTION_LATE`
- `BQ_INSUFFICIENT_EVIDENCE_GAP`
- `PM_HOLD_CONFIRMATION_LAG`

Not selected:

- `UPSIDE_CAPTURE_INSUFFICIENT`: upside capture is strong.
- `NO_CLEAR_BOTTLENECK`: bottlenecks are visible enough to characterize.

## Avoidable-Loss Estimate

Strongly supported avoidable-loss pool from pre-detected lot-blocked REDUCE/BQ non-promotion:

- `97310`: about `30,200` from Phase32-BX episode framing.
- `78860`: about `18,400`.
- `14000`: about `17,400` campaign-level, avoiding double-counting the later repeated warning.
- `52470`: about `10,000`.
- `41660`: about `32,100`.

Approximate supported pool: `~108,000`.

This is not a proposed trading rule and does not assume perfect exit timing. It is an evidence-backed characterization of loss that occurred after explicit PM REDUCE warning and failed or non-promoted BQ materialization.

Larger winner-retention giveback, especially `59350`, is economically material but not included in the same avoidable-loss number because it lacks an earlier explicit PM sell-side action; it belongs to HOLD/profit-retention design analysis.

## Required Final Answers

1. `LATEST_COMPLETED_DATE = 2023-04-18_FOR_THIS_AUDIT_SNAPSHOT`
2. `CURRENT_RETURN = +60.11%`
3. `PEAK_RETURN = +76.64%`
4. `MAX_DRAWDOWN = -185,960 / -10.53%`
5. `LARGEST_POSITIVE_DAY = 2023-03-30 +94,850`
6. `LARGEST_NEGATIVE_DAY = 2023-04-11 -144,950`
7. `LARGE_GAIN_DAYS_COUNT = 20_DAYS_>=+20,000; 8_DAYS_>=+50,000; 0_DAYS_>=+100,000`
8. `LARGE_LOSS_DAYS_COUNT = 11_DAYS_<=-20,000; 9_DAYS_<=-30,000; 3_DAYS_<=-50,000; 1_DAY_<=-100,000`
9. `UPSIDE_CAPTURE_STRONG = YES`
10. `BQ_WINNER_CAPTURE_IMPAIRMENT_FOUND = NO_CONCRETE_EVIDENCE`
11. `ACTUAL_BQ_FULL_EXIT_COUNT = 31`
12. `BQ_INSUFFICIENT_LATER_MATERIAL_LOSS_COUNT = 5_CAMPAIGN_LEVEL_CANDIDATES_PLUS_1_REPEATED_WARNING`
13. `97310_PATTERN_RECURRENT = YES`
14. `HOLD_CONFIRMATION_LAG_RECURRENT = YES`
15. `WINNER_PROFIT_RETENTION_LATE_SUPPORTED = YES`
16. `TRANSITION_GIVEBACK_CLUSTER_SUPPORTED = YES`
17. `AVOIDABLE_LOSS_MATERIAL = YES_PARTIAL`
18. `ESTIMATED_AVOIDABLE_LOSS = APPROX_108,000_FOR_PM_REDUCE_LOT_BLOCKED_BQ_NON_PROMOTION_POOL`
19. `OLD_BASELINE_CURRENT_EQUITY_DIFFERENCE = INSUFFICIENT_RAW_BASELINE_EVIDENCE_FOR_2023_04_18; PHASE32_BW_RECORDED_+9,810_ON_2022_11_16`
20. `OLD_BASELINE_LARGE_LOSS_DIFFERENCE = INSUFFICIENT_RAW_BASELINE_EVIDENCE`
21. `PRIMARY_PERFORMANCE_BOTTLENECK = MIXED_LARGE_LOSS_TAIL_DOMINANT_PLUS_WINNER_PROFIT_RETENTION_LATE_PLUS_BQ_INSUFFICIENT_EVIDENCE_GAP_PLUS_PM_HOLD_CONFIRMATION_LAG`
22. `PRODUCTION_CHANGE_JUSTIFIED_NOW = NO_READ_ONLY_CHARACTERIZATION_ONLY`
23. `NEXT_RECOMMENDED_STEP = Run a narrow READ-ONLY/SHADOW design study separating two mechanisms: 1) PM REDUCE lot-blocked BQ insufficient/hold later-loss population; 2) 59350-style winner profit-retention HOLD confirmation lag. Do not tune from historical PnL directly.`
24. `FINAL_JUDGMENT = PHASE32_BY_POST_BQ_LONG_RUN_BOTTLENECK_MIXED_LARGE_LOSS_TAIL_AND_WINNER_RETENTION_LATE_WITH_RECURRENT_BQ_INSUFFICIENT_GAP_CHARACTERIZED_READ_ONLY`

