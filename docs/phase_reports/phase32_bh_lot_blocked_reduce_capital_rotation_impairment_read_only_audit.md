# Phase32-BH — Lot-Blocked REDUCE / Capital Rotation Impairment READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T003243720082Z`
- Snapshot used for aggregate interval analysis: completed valuation evidence through `2024-04-24`
- Completed valuation days in aggregate snapshot: `384`, from `2022-10-03` through `2024-04-24`
- Source commit recorded by run plan: `ff1d23157cced619c5820898f8317a7440e6092c`

This phase is READ-ONLY. No code, config, model, threshold, runtime state, Pending, Ledger, recovery, replay, resume, or fresh-run action was executed or changed.

The target run was still running while this audit was performed. Aggregate counts are therefore tied to the snapshot above and intentionally not updated after that point.

## Evidence Method

Lot-blocked REDUCE events were identified from actual-path `strategy/position_management.json` rows where:

- `action = REDUCE`
- `canonical_sell_semantic_evidence.episode_increment_evidence.zero_lot_reduce = true`
- `representability_family = DISCRETE_LOT`

Executable same-day REDUCE/SELL controls were identified from same-day `execution/fills.json`. Economic consequence intervals were grouped by campaign to avoid double-counting repeated unresolved REDUCE signals:

- interval start = first lot-blocked REDUCE after the previous executable sell boundary
- interval end = next actual executable SELL/REDUCE/EXIT for the same campaign, or snapshot end if still open
- consequence = next sell cash effect plus remaining market value, minus blocked-date position market value

Sign convention:

- Negative value = `BLOCKED_REDUCE_HARMFUL`
- Positive value = `BLOCKED_REDUCE_BENEFICIAL`
- Near zero, within +/-1,000 = `BLOCKED_REDUCE_NEUTRAL`

Where PM's pre-round desired reduction quantity was not serialized, it is marked unavailable. The canonical evidence does serialize the post-lot result as `final_reduce_quantity = 0.0`, so blocked status is authoritative even when raw desired shares are not recoverable.

## Event Enumeration

Actual-path PM REDUCE events:

| Category | Count |
| --- | ---: |
| Total PM REDUCE rows | 685 |
| Lot-blocked REDUCE rows | 628 |
| Same-day executable REDUCE/SELL rows | 57 |
| Other non-lot NO_ORDER REDUCE rows | 0 |

Lot-blocked REDUCE population:

| Position quantity class | Count |
| --- | ---: |
| 100-share / minimum-lot position | 566 |
| Larger position but desired partial REDUCE still below executable lot | 62 |

Lot-blocked events by PM state:

| PM state | Count |
| --- | ---: |
| `WEAKENING_BUT_INTACT` | 439 |
| `PERSISTENT_DETERIORATION` | 189 |

Lot-blocked events by severity:

| Severity | Count |
| --- | ---: |
| `PM_SEVERITY_CAUTION` | 494 |
| `PM_SEVERITY_DEFENSIVE` | 134 |

Lot-blocked events by regime:

| Regime | Count |
| --- | ---: |
| BULL | 303 |
| RANGE | 129 |
| RECOVERY | 97 |
| BEAR | 64 |
| CORRECTION | 35 |

Primary PM reasons:

- `risk_increased_but_trend_not_broken` + `strategy_intelligence_sell_side_evidence_connected`: 541
- `peak_drawdown_warning` + `strategy_intelligence_sell_side_evidence_connected`: 86
- `high_downside_risk_score` + `strategy_intelligence_sell_side_evidence_connected`: 1

Interpretation: PM is frequently detecting weakening, but its intermediate REDUCE action cannot become an executable order because the desired reduction resolves below the 100-share lot.

## Blocked Interval Consequences

Campaign-level non-overlapping blocked intervals:

| Classification | Count | Economic total |
| --- | ---: | ---: |
| `BLOCKED_REDUCE_HARMFUL` | 86 | -670,360 |
| `BLOCKED_REDUCE_BENEFICIAL` | 53 | +291,750 |
| `BLOCKED_REDUCE_NEUTRAL` | 204 | approximately -11,770 net residual |
| Net blocked REDUCE consequence | 343 intervals | -390,380 |
| Median consequence | 343 intervals | -100 |

This supports the hypothesis that lot-blocked REDUCE materially impairs capital rotation and loss control in aggregate. It does not support a blanket rule that every blocked REDUCE would have helped: 53 beneficial intervals show meaningful winner false-reduction risk.

## Major Harmful Campaigns

| Symbol | Block date | Next sell | Consequence | Duration | Qty | Block notional | Block ratio | Entry date | Entry ratio | Regime | PM state | Severity |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- | --- |
| 67310 | 2023-04-24 | 2023-08-18 EXIT | -100,000 | 79BD | 100 | 300,000 | 19.71% | 2023-04-21 | 13.23% | RECOVERY | WEAKENING_BUT_INTACT | CAUTION |
| 62310 | 2023-05-01 | 2023-05-15 EXIT | -38,500 | 7BD | 100 | 214,500 | 13.78% | 2023-04-28 | 14.41% | RECOVERY | WEAKENING_BUT_INTACT | CAUTION |
| 34160 | 2024-03-05 | 2024-03-11 EXIT | -37,200 | 4BD | 100 | 144,400 | 8.33% | 2024-03-04 | 7.13% | BULL | WEAKENING_BUT_INTACT | CAUTION |
| 44140 | 2023-11-28 | 2023-12-08 EXIT | -36,750 | 8BD | 100 | 253,500 | 15.01% | 2023-11-13 | 13.42% | BULL | WEAKENING_BUT_INTACT | CAUTION |
| 41660 | 2023-04-13 | 2023-04-19 EXIT | -33,500 | 4BD | 100 | 168,500 | 11.34% | 2023-04-12 | 9.69% | RECOVERY | WEAKENING_BUT_INTACT | CAUTION |
| 52470 | 2023-04-03 | 2023-04-06 EXIT | -29,000 | 3BD | 100 | 290,000 | 17.97% | 2023-03-31 | 17.93% | RECOVERY | WEAKENING_BUT_INTACT | DEFENSIVE |
| 48840 | 2023-03-03 | 2023-03-14 EXIT | -20,600 | 7BD | 100 | 131,900 | 10.78% | 2023-03-02 | 9.15% | BULL | WEAKENING_BUT_INTACT | CAUTION |
| 78090 | 2023-12-13 | 2023-12-15 EXIT | -20,100 | 2BD | 100 | 174,100 | 10.73% | 2023-12-12 | 10.56% | RANGE | WEAKENING_BUT_INTACT | CAUTION |

Top3 harmful intervals total `-175,700`, dominated by `67310`.

## Major Beneficial Campaigns

| Symbol | Block date | Next sell | Consequence | Duration | Qty | Block notional | Block ratio | Entry date | Entry ratio | Regime | PM state | Severity |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- | --- |
| 74270 | 2023-08-14 | 2023-10-02 EXIT | +40,800 | 34BD | 100 | 116,800 | 7.47% | 2023-08-07 | 6.91% | RECOVERY | WEAKENING_BUT_INTACT | CAUTION |
| 62280 | 2023-12-22 | 2023-12-28 EXIT | +26,330 | 4BD | 100 | 301,000 | 18.45% | 2023-12-21 | 15.59% | RANGE | WEAKENING_BUT_INTACT | CAUTION |
| 92270 | 2022-10-24 | 2022-11-07 EXIT | +22,800 | 9BD | 100 | 114,500 | 10.95% | 2022-10-18 | 10.61% | RANGE | WEAKENING_BUT_INTACT | DEFENSIVE |
| 39760 | 2023-01-23 | 2023-01-24 EXIT | +15,000 | 1BD | 100 | 73,500 | 6.41% | 2023-01-20 | 6.55% | BULL | WEAKENING_BUT_INTACT | DEFENSIVE |
| 70680 | 2023-01-16 | 2023-02-20 EXIT | +11,500 | 25BD | 100 | 43,000 | 3.86% | 2023-01-13 | 3.26% | BEAR | WEAKENING_BUT_INTACT | CAUTION |
| 61440 | 2022-12-21 | 2023-03-24 EXIT | +10,700 | 62BD | 100 | 150,300 | 13.63% | 2022-12-08 | 13.30% | BEAR | WEAKENING_BUT_INTACT | CAUTION |

Top3 beneficial intervals total `+89,930`.

The beneficial control matters: a naive repair that forces all PM REDUCE signals into full exits would reject real recoveries and winners.

## Relationship to BG High-Notional Losers

BG major losers inspected:

| Symbol | Lot-blocked REDUCE before final loss? | Block interval consequence | Interpretation |
| --- | --- | ---: | --- |
| 55950 | NO | N/A | Entry oversizing / weak starter, not reduce granularity. PM went HOLD then EXIT. |
| 74770 | YES, 2023-10-04 | -4,900 | Minor amplification; primary loss was high-notional entry and fast deterioration. |
| 92460 | YES, 2023-10-10 | ~0 | Not material as reduce-granularity loss. |
| 60220 | YES, 2023-04-12 | -100 | Not material; primary loss already present by early deterioration. |
| 51890 | YES, 2023-04-14 | -3,750 | Minor amplification. |
| 36590 | NO | N/A | Direct EXIT path; not reduce granularity. |
| 44250 | NO | N/A | HOLD to EXIT; not reduce granularity. |
| 55860 | NO | N/A | HOLD to EXIT; not reduce granularity. |

Conclusion: BG high-notional loss concentration is mostly `ENTRY_OVERSIZING` / weak-starter failure, not `POST_ENTRY_REDUCE_GRANULARITY`. Lot-blocked REDUCE amplifies some high-notional losses, but it does not explain the largest BG starter losses such as `55950`, `55860`, `36590`, or `44250`.

## Winner Profit-Retention Relationship

### 67310

`67310` is the strongest case that BF's `WINNER_PROFIT_RETENTION_LATE` is amplified by lot-blocked REDUCE.

- First lot-blocked REDUCE: `2023-04-24`
- Block-date notional: `300,000`
- Block-date ratio: `19.71%`
- Next actual executable SELL/EXIT: `2023-08-18`
- Blocked interval duration: 79BD
- Consequence: `-100,000`
- PM state at block: `WEAKENING_BUT_INTACT`
- Severity at block: `PM_SEVERITY_CAUTION`

This is a decision-time path where PM saw deterioration, but the intermediate REDUCE action could not release any capital. The position remained fully exposed until later EXIT.

### 59350

`59350` is not primarily a lot-blocked REDUCE case in the inspected interval set. It is better characterized as profit-retention / late-exit behavior where PM had `profit_retention_break` and `EXIT_GRADE` evidence but did not convert that into earlier executable de-risking. Therefore BF's winner-retention problem is only partially explained by lot-blocked REDUCE.

### Beneficial winner controls

`62280`, `74270`, `92270`, and `61440` show that blocked REDUCE sometimes preserved profitable exposure. This prevents a simple "all blocked REDUCE should be forced executable" conclusion.

## Weak Starter Relationship

The repeated weak-starter sequence exists:

`BUY_NEW -> early deterioration -> PM REDUCE -> lot-blocked -> continued loss -> EXIT`

Examples include:

- `34160`: BUY_NEW `2024-03-04`, lot-blocked REDUCE `2024-03-05`, EXIT `2024-03-11`, interval consequence `-37,200`.
- `41660`: BUY_NEW `2023-04-12`, lot-blocked REDUCE `2023-04-13`, EXIT `2023-04-19`, interval consequence `-33,500`.
- `52470`: BUY_NEW `2023-03-31`, lot-blocked REDUCE `2023-04-03`, EXIT `2023-04-06`, interval consequence `-29,000`.
- `48840`: BUY_NEW `2023-03-02`, lot-blocked REDUCE `2023-03-03`, EXIT `2023-03-14`, interval consequence `-20,600`.

However, several BG weak starters did not have a lot-blocked REDUCE before exit. Therefore lot-blocked REDUCE amplifies weak-starter accumulation but is not the root explanation for all weak starter loss.

## Capital Rotation Impairment

Trapped capital is material but not precisely quantifiable from available serialized PM evidence:

- PM serializes the final lot-resolved reduction as `final_reduce_quantity = 0.0`.
- Raw desired share reduction / desired target notional is not consistently serialized in the PM artifact for these rows.
- Therefore exact intended released notional cannot be calculated without inventing missing evidence.

Bounded interpretation:

- For minimum-lot positions, any intended partial reduction below 100 shares released `0` notional.
- The blocked position notional at event time was often material: `67310` `300,000`, `62280` `301,000`, `52470` `290,000`, `44140` `253,500`, `51290` `234,500`.
- Event-time block ratios commonly exceeded 10% in the largest harmful intervals.

Contemporaneous opportunity displacement:

- `PARTIAL`.
- On representative block dates, contemporaneous buy-quality evidence contained many PIT candidates with nonzero quality scores.
- The evidence supports that capital remained tied up while alternative candidates existed, but it does not prove that those candidates should have displaced the held position without importing future outcomes.

## Capital-Scale Effect

Blocked interval consequence by event-time equity scale:

| Equity scale | Intervals | Harmful | Beneficial | Loss total | Gain total | Net |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `<1.2M` | 110 | 17 | 20 | -86,570 | +114,940 | +28,370 |
| `1.2M-1.4M` | 12 | 5 | 4 | -42,200 | +15,500 | -26,700 |
| `1.4M-1.6M` | 100 | 31 | 11 | -337,370 | +92,970 | -244,400 |
| `>=1.6M` | 121 | 33 | 18 | -244,260 | +96,610 | -147,650 |

Interpretation:

- The effect worsens materially after equity exceeds `1.4M`.
- It remains negative at `>=1.6M`, directly relating to BG's higher-capital loss concentration.
- The single biggest interval, `67310`, starts around `1.52M` equity and dominates the `1.4M-1.6M` bucket.

## Entry Oversizing vs Reduce Granularity

The evidence supports a split:

- BG high-notional starter losses are mostly entry-size / minimum-lot exposure problems.
- BH lot-blocked REDUCE is a separate post-entry capital-rotation problem.
- They overlap when a high-notional minimum-lot position deteriorates and PM can only express soft de-risking as an unexecutable partial REDUCE.
- Winner profit-retention late is partially amplified by lot-blocked REDUCE, most strongly in `67310`, but remains broader than this mechanism.

## Required Final Answers

1. `LOT_BLOCKED_REDUCE_EVENT_COUNT`: `628`
2. `AFFECTED_CAMPAIGN_COUNT`: `342`
3. `HARMFUL_BLOCKED_INTERVAL_COUNT`: `86`
4. `BENEFICIAL_BLOCKED_INTERVAL_COUNT`: `53`
5. `TOTAL_POST_BLOCK_ADDITIONAL_LOSS`: `-670,360`
6. `TOTAL_POST_BLOCK_ADDITIONAL_GAIN`: `+291,750`
7. `NET_BLOCKED_REDUCE_CONSEQUENCE`: `-390,380`
8. `MAJOR_HARMFUL_CAMPAIGNS`: `67310`, `62310`, `34160`, `44140`, `41660`, `52470`, `48840`, `78090`
9. `MAJOR_BENEFICIAL_CAMPAIGNS`: `74270`, `62280`, `92270`, `39760`, `70680`, `61440`
10. `HIGH_NOTIONAL_LOSSES_EXPLAINED_BY_REDUCE_GRANULARITY`: PARTIAL. Some high-notional losses were amplified, but several largest BG losers had no blocked REDUCE before EXIT.
11. `WEAK_STARTER_ACCUMULATION_AMPLIFIED_BY_LOT_BLOCK`: YES / PARTIAL. The sequence is reproduced, but not universal.
12. `WINNER_PROFIT_RETENTION_LATE_AMPLIFIED_BY_LOT_BLOCK`: YES / PARTIAL. Strong for `67310`, weaker or absent for `59350`.
13. `TRAPPED_CAPITAL_MATERIAL`: YES, qualitatively and by blocked notional; exact intended release is `INSUFFICIENT_EVIDENCE` because raw desired reduction is not serialized.
14. `CONTEMPORANEOUS_OPPORTUNITY_DISPLACEMENT_SUPPORTED`: PARTIAL. Candidate evidence existed, but future winner outcomes were not used to claim displacement certainty.
15. `DOES_EFFECT_WORSEN_WITH_CAPITAL_SCALE`: YES after `1.4M`, with negative net consequence in `1.4M-1.6M` and `>=1.6M`.
16. `ENTRY_OVERSIZING_VS_REDUCE_GRANULARITY`: MIXED. Entry oversizing explains much of BG; reduce granularity separately impairs post-entry de-risking and capital rotation.
17. `IS_THIS_A_CORRECTNESS_DEFECT`: NO. This is an economic/design expressiveness gap, not evidence of ledger, authority, or runtime correctness failure.
18. `IS_CAPITAL_ROTATION_DESIGN_GAP_SUPPORTED`: YES.
19. `IS_DESIGN_CHANGE_JUSTIFIED`: YES for a shadow/design phase that preserves beneficial blocked cases and avoids blunt forced exits.
20. `IS_PRODUCTION_CHANGE_JUSTIFIED_NOW`: NO.
21. `NEXT_RECOMMENDED_STEP`: design a PIT-only shadow contract for lot-aware de-risking alternatives, such as full-exit confirmation for minimum-lot deteriorators, starter sizing/eligibility guard for high-notional lots, and capital-rotation pressure that uses existing PM deterioration evidence without importing future PnL.
22. `FINAL_JUDGMENT`: `PHASE32_BH_LOT_BLOCKED_REDUCE_CAPITAL_ROTATION_IMPAIRMENT_SUPPORTED_MATERIAL_DESIGN_GAP_NO_CORRECTNESS_DEFECT_NO_PRODUCTION_CHANGE`

## No Change Confirmation

- Code change: NO
- Config/model/threshold change: NO
- Runtime state mutation: NO
- Resume/recover/replay/fresh-run: NO
- Production behavior change: NO
- Future information used as decision-time evidence: NO

