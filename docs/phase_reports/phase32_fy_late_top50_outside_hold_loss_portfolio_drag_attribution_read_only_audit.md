# Phase32-FY — LATE Top50-Outside HOLD Loss / Portfolio Drag Attribution READ-ONLY Audit

## Scope

- Primary long run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Main period: LATE, `2023-06-01` through completed freeze `2023-08-04`
- LATE completed business days: `46`
- Primary classification source: same-day `strategy/portfolio_construction.json` materialized `input_opportunity_rank`
- Daily position value source: `current_valuation_refresh/current_valuation_manifest.json`
- Execution adjustment source: `execution/fills.json`

READ-ONLY confirmation:

- Production changed: NO
- SHADOW changed: NO
- Source/config/schema changed: NO
- Runtime/Pending/Ledger state mutated: NO
- fresh-run/resume/replay/recover executed: NO
- Historical outcome used only for actual attribution: YES
- Historical outcome used to choose SELL/dropout/profit/stop thresholds: NO

## Attribution Method

For each LATE business date, position-level contribution was reconstructed symbol-wise as:

```text
current marked market value
+ same-day SELL gross notional
- prior completed day marked market value
- same-day BUY gross notional
```

New-only BUY symbols without prior holding were excluded from holding PnL attribution. This avoids counting capital deployment itself as PnL.

Each start-held symbol was classified from same-day PC:

- `IN_TOP50`: current held row has `input_opportunity_rank <= 50`
- `OUTSIDE_TOP50`: current held row is represented but has no valid Top50 rank
- `UNRESOLVED`: no stable same-day classification

Unresolved contribution was `0` in the inspected LATE attribution.

## LATE Aggregate Attribution

| Cohort | Gross profit | Gross loss | Net PnL | Rows |
|---|---:|---:|---:|---:|
| Top50-IN | `656,900` | `-714,900` | `-58,000` | 526 |
| Top50-OUT | `120,120` | `-125,550` | `-5,430` | 159 |
| Total holdings | `777,020` | `-840,450` | `-63,430` | 685 |

Required values:

- `LATE_TOP50_IN_GROSS_PROFIT = 656,900`
- `LATE_TOP50_IN_GROSS_LOSS = -714,900`
- `LATE_TOP50_IN_NET_PNL = -58,000`
- `LATE_TOP50_OUT_GROSS_PROFIT = 120,120`
- `LATE_TOP50_OUT_GROSS_LOSS = -125,550`
- `LATE_TOP50_OUT_NET_PNL = -5,430`

## Negative Drag Share

- `OUTSIDE_TOP50_GROSS_LOSS_SHARE_OF_TOTAL_HOLDING_GROSS_LOSS = 14.94%`
- LATE total holding PnL: `-63,430`
- Top50-OUT net PnL: `-5,430`
- `OUTSIDE_TOP50_NET_DRAG_SHARE_OF_LATE_PORTFOLIO_PNL = 8.56% of holding net loss`

Interpretation:

Top50-OUT negative drag exists, but it does not explain most LATE holding losses. The larger LATE losses came from holdings that were still Top50-IN on the relevant dates.

## Down-Day Attribution

LATE down days:

- Down days: `22`
- Total down-day holding loss: `-483,760`
- Top50-OUT contribution on down days: `-63,760`
- `OUTSIDE_TOP50_DOWN_DAY_LOSS_SHARE = 13.18%`

Again, Top50-OUT holdings contributed to downside, but were not the dominant down-day loss engine.

## Top 10 Negative LATE Days

`LATE_TOP10_NEGATIVE_DAY_OUTSIDE_TOP50_CONTRIBUTION`:

| Date | Total holding PnL | Top50-OUT | Top50-IN | OUT share | Largest negative contributors |
|---|---:|---:|---:|---:|---|
| 2023-06-08 | -115,920 | -4,100 | -111,820 | 3.5% | 67310 IN -100,000; 88900 OUT -4,100; 76470 IN -2,900 |
| 2023-06-30 | -106,460 | 500 | -106,960 | -0.5% | 67310 IN -100,000; 40520 IN -7,200; 76470 IN -2,900 |
| 2023-06-01 | -34,980 | -10,800 | -24,180 | 30.9% | 30410 IN -29,800; 59550 IN -12,400; 66560 OUT -10,800 |
| 2023-07-06 | -31,270 | 800 | -32,070 | -2.6% | 31330 IN -15,000; 99840 IN -6,600; 21340 IN -5,000 |
| 2023-07-07 | -27,510 | -1,000 | -26,510 | 3.6% | 31330 IN -10,000; 37780 IN -5,600; 99840 IN -4,160 |
| 2023-06-22 | -24,080 | 800 | -24,880 | -3.3% | 99840 IN -7,500; 21340 IN -7,500; 40520 IN -7,200 |
| 2023-06-27 | -20,090 | -100 | -19,990 | 0.5% | 21340 IN -7,500; 76470 IN -5,800; 99840 IN -5,200 |
| 2023-06-20 | -19,800 | -18,600 | -1,200 | 93.9% | 88900 OUT -18,900; 21340 IN -5,000; 59550 IN -2,500 |
| 2023-08-02 | -15,270 | -750 | -14,520 | 4.9% | 99840 IN -13,340; 45700 IN -1,700; 94320 IN -1,400 |
| 2023-07-20 | -13,010 | -5,700 | -7,310 | 43.8% | 38910 OUT -3,800; 45720 IN -4,000; 75270 OUT -1,200 |

Only `2023-06-20` is primarily explained by Top50-OUT. The two largest LATE negative days, `2023-06-08` and `2023-06-30`, were dominated by Top50-IN contributions, especially `67310`.

## Month Split

| Month | Days | Total holding PnL | Top50-OUT net | Top50-IN net | OUT down-day loss |
|---|---:|---:|---:|---:|---:|
| June | 22 | `-50,560` | `-15,980` | `-34,580` | `-39,800` |
| July | 20 | `-1,590` | `3,570` | `-5,160` | `-16,100` |
| August completed | 4 | `-11,280` | `6,980` | `-18,260` | `-7,860` |

Required values:

- `JUNE_TOP50_OUT_NET_PNL = -15,980`
- `JULY_TOP50_OUT_NET_PNL = 3,570`
- `AUGUST_TOP50_OUT_NET_PNL = 6,980`

Outside-Top50 was negative in June, but positive in July and early August. This weakens a claim that outside-Top50 holdings were the dominant LATE stagnation cause.

## Negative Dropout Campaign Ranking

From the FW campaign-deduped dropout episode set:

- `NEGATIVE_DROPOUT_CAMPAIGN_COUNT = 26`
- FW gross-loss cohort total: `-97,190`

Top 15 negative dropout episodes:

| Rank | Dropout date | Symbol | Campaign | Duration | Notional at dropout | Post-dropout PnL | Giveback | HOLD days | End |
|---:|---|---:|---|---:|---:|---:|---:|---:|---|
| 1 | 2023-01-30 | 87890 | `pc-daa37422a61c374c-87890-0001` | 28 | 35,400 | -21,400 | 4,400 | 25 | SELL/EXIT |
| 2 | 2022-11-04 | 37770 | `pc-3d630247f7ec5050-37770-0001` | 7 | 23,400 | -15,600 | 0 | 0 | SELL/EXIT |
| 3 | 2023-04-10 | 43880 | `pc-64642ec31e0f55ef-43880-0001` | 1 | 272,200 | -12,000 | 0 | 0 | SELL/EXIT |
| 4 | 2023-05-08 | 60160 | `pc-87c45f2cef5a7977-60160-0001` | 4 | 73,870 | -8,640 | 8,640 | 3 | SELL/EXIT |
| 5 | 2022-12-23 | 91070 | `pc-800aa5ec4cfcdd46-91070-0001` | 7 | 98,670 | -7,140 | 5,770 | 6 | SELL/EXIT |
| 6 | 2023-06-14 | 30410 | `pc-f464e928cc9847ea-30410-0001` | 2 | 138,000 | -6,000 | 6,100 | 1 | SELL/EXIT |
| 7 | 2023-05-31 | 49370 | `pc-aa2f7d4ba1cc0d41-49370-0001` | 1 | 166,700 | -5,100 | 0 | 0 | SELL/EXIT |
| 8 | 2022-12-01 | 78860 | `pc-28eff802cdbfca54-78860-0001` | 5 | 132,200 | -4,000 | 16,600 | 3 | SELL/EXIT |
| 9 | 2023-04-07 | 29700 | `pc-54af6d7794e66365-29700-0001` | 1 | 44,400 | -3,900 | 3,900 | 1 | Top50 re-entry |
| 10 | 2023-06-19 | 51310 | `pc-67de994ccf4e6c53-51310-0001` | 15 | 37,200 | -2,500 | 3,700 | 14 | SELL/EXIT |
| 11 | 2023-02-22 | 45940 | `pc-1a522253682fb207-45940-0001` | 3 | 20,600 | -1,700 | 1,200 | 2 | SELL/EXIT |
| 12 | 2023-08-02 | 47550 | `pc-386de51400eac2b8-47550-0001` | 3 | 56,000 | -1,700 | 2,090 | 3 | Run end / held |
| 13 | 2023-03-16 | 14000 | `pc-52eb4347d88fdead-14000-0001` | 1 | 44,100 | -1,500 | 0 | 0 | SELL/EXIT |
| 14 | 2023-08-01 | 75780 | `pc-ea5ad1d6317d8b35-75780-0001` | 4 | 37,700 | -1,300 | 1,300 | 4 | Run end / held |
| 15 | 2023-02-10 | 77710 | `pc-b9ac5b2d340179ea-77710-0001` | 3 | 21,400 | -1,000 | 0 | 2 | SELL/EXIT |

## Loss Concentration

Using the FW `-97,190` gross-loss cohort:

- `NEGATIVE_DROPOUT_WORST_1_SHARE = 22.0%`
- `NEGATIVE_DROPOUT_WORST_3_SHARE = 50.4%`
- `NEGATIVE_DROPOUT_WORST_5_SHARE = 66.7%`
- `NEGATIVE_DROPOUT_WORST_10_SHARE = 88.8%`

This is concentrated. The problem is not a broad uniform small HOLD bias across all dropout episodes; most realized dropout loss is concentrated in a relatively small number of campaigns.

`LOSS_STRUCTURE = FEW_LARGE_SELL_FAILURES with secondary broad HOLD-bias symptoms`

## Giveback Concentration

Using the FW `139,750` giveback total:

- `GIVEBACK_WORST_1_SHARE = 16.9%`
- `GIVEBACK_WORST_3_SHARE = 42.2%`
- `GIVEBACK_WORST_5_SHARE = 61.0%`
- `GIVEBACK_WORST_10_SHARE = 83.6%`

Giveback is also concentrated. The largest giveback cases are not always the largest net-loss cases, which supports separating profit retention from outright post-dropout loss.

## Persistent vs Temporary Dropout

FW dropout episodes by duration:

| Duration | Episodes | Gross loss | Net PnL | Giveback |
|---|---:|---:|---:|---:|
| 1BD | 23 | -24,350 | -21,920 | 24,350 |
| 2BD | 3 | -6,000 | -4,830 | 6,120 |
| 3-5BD | 9 | -18,440 | -18,350 | 33,200 |
| 6-10BD | 9 | -23,500 | 1,120 | 28,340 |
| 11+BD | 8 | -24,900 | 2,500 | 83,200 |

Required:

- `PERSISTENT_DROPOUT_GROSS_LOSS = -72,840` for duration `>1BD`
- `PERSISTENT_DROPOUT_NET_PNL = -19,560` for duration `>1BD`

Longer duration correlates more clearly with giveback/capital lock than with net loss. The 11+BD cohort had positive net PnL but very large giveback, showing why hard exit from duration alone would be hindsight-prone.

## Deterioration Interaction

FW outside-Top50 + deterioration HOLD episode subset:

- Gross profit: `53,280`
- Gross loss: `-61,990`
- Net PnL: `-8,710`
- Giveback: `155,610` by recomputed deterioration subset mark-to-end scan
- Episode count: `31`

Required:

- `OUTSIDE_TOP50_PLUS_DETERIORATION_HOLD_GROSS_LOSS = -61,990`
- `OUTSIDE_TOP50_PLUS_DETERIORATION_HOLD_NET_PNL = -8,710`

The deterioration-HOLD subset is economically negative, but still not dominant versus the full LATE holding loss.

## Positive Offset

Top50-OUT LATE holdings generated:

- gross profit `120,120`
- gross loss `-125,550`
- net `-5,430`

Therefore winning Top50-OUT rows offset `95.7%` of Top50-OUT gross losses in LATE. This does not make the negative drag irrelevant, but it does mean the net LATE drag from the full Top50-OUT cohort is small relative to total holding losses.

## LATE Stagnation Window

Characterization window selected from the evidence as `2023-07-10` through `2023-08-04`, where FW showed outside-Top50 exposure rising materially in the final stretch.

Within that window:

- Days: `19`
- Total holding PnL: `22,490`
- Top50-OUT net PnL: `1,850`
- `LATE_STAGNATION_WINDOW_TOP50_OUT_NET_PNL = 1,850`
- `LATE_STAGNATION_WINDOW_TOP50_OUT_DRAG_SHARE = not a drag; positive 8.2% contribution to holding PnL`

The late-window capital lock was real, but the actual Top50-OUT mark-to-market contribution was not the source of net stagnation in this sub-window.

## Capital Lock vs Economic Drag

Phase32-FW found:

- Outside-Top50 notional-days: `30,540,790`
- Average daily outside-Top50 equity share: `21.24%`
- LATE average outside-Top50 equity share: `20.48%`
- Final 10 completed days outside-Top50 equity share: `33.63%`

Phase32-FY adds:

- LATE Top50-OUT gross loss share: `14.94%`
- LATE Top50-OUT net drag share: `8.56%`
- LATE down-day loss share: `13.18%`

Conclusion:

Top50-OUT capital lock is material as an allocation/rotation phenomenon, but actual LATE loss attribution shows it was not the dominant loss engine. The larger direct LATE drawdown came from positions still classified Top50-IN.

## Fresh June Comparison Metric Contract

Fresh June run comparison was not required. For future same-day comparison, preserve:

- long Top50-OUT legacy exposure;
- fresh equivalent exposure;
- long-only legacy Top50-OUT contribution;
- long-only legacy capital lock;
- same-day Top50-IN direct loss contribution;
- same-day strong alternative count;
- cash scarcity state.

This separates actual drag from opportunity-cost hypotheses without running a counterfactual replay.

## SELL Root-Cause Materiality

`SELL_ROOT_CAUSE_MATERIALITY = MATERIAL_BUT_SECONDARY`

Rationale:

- Outside-Top50 negative drag exists and is measurable.
- It explains about `15%` of LATE holding gross loss and `13%` of down-day loss.
- It does not explain the largest LATE negative days.
- It is more material as profit giveback / capital lock / rotation design evidence than as the direct dominant PnL loss driver.

`PROFIT_RETENTION_COMPONENT_MATERIAL = YES`

`CAPITAL_ROTATION_COMPONENT_MATERIAL = YES`

## Production Judgment

- `TOP50_HARD_EXIT_JUSTIFIED = NO`
- `TOP50_SOFT_EVIDENCE_REVIEW_JUSTIFIED = YES`
- `SELL_ROTATION_DESIGN_REVIEW_JUSTIFIED = YES`
- `CORRECTNESS_DEFECT_FOUND = NO`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`
- `DESIGN_REFINEMENT_JUSTIFIED = YES`

`NEXT_DESIGN_DIRECTION = opportunity-cost-aware SELL/rotation review that treats Top50 dropout as soft relative evidence, while separately protecting temporary dropout recovery and valid winner retention`

## Required Final Answers

- `LATE_TOP50_IN_GROSS_PROFIT = 656,900`
- `LATE_TOP50_IN_GROSS_LOSS = -714,900`
- `LATE_TOP50_IN_NET_PNL = -58,000`
- `LATE_TOP50_OUT_GROSS_PROFIT = 120,120`
- `LATE_TOP50_OUT_GROSS_LOSS = -125,550`
- `LATE_TOP50_OUT_NET_PNL = -5,430`
- `OUTSIDE_TOP50_GROSS_LOSS_SHARE_OF_TOTAL_HOLDING_GROSS_LOSS = 14.94%`
- `OUTSIDE_TOP50_DOWN_DAY_LOSS_SHARE = 13.18%`
- `LATE_TOP10_NEGATIVE_DAY_OUTSIDE_TOP50_CONTRIBUTION = mostly secondary; only 2023-06-20 was primarily OUT-driven`
- `NEGATIVE_DROPOUT_CAMPAIGN_COUNT = 26`
- `NEGATIVE_DROPOUT_WORST_1_SHARE = 22.0%`
- `NEGATIVE_DROPOUT_WORST_3_SHARE = 50.4%`
- `NEGATIVE_DROPOUT_WORST_5_SHARE = 66.7%`
- `NEGATIVE_DROPOUT_WORST_10_SHARE = 88.8%`
- `GIVEBACK_WORST_1_SHARE = 16.9%`
- `GIVEBACK_WORST_3_SHARE = 42.2%`
- `GIVEBACK_WORST_5_SHARE = 61.0%`
- `GIVEBACK_WORST_10_SHARE = 83.6%`
- `PERSISTENT_DROPOUT_GROSS_LOSS = -72,840`
- `PERSISTENT_DROPOUT_NET_PNL = -19,560`
- `OUTSIDE_TOP50_PLUS_DETERIORATION_HOLD_GROSS_LOSS = -61,990`
- `OUTSIDE_TOP50_PLUS_DETERIORATION_HOLD_NET_PNL = -8,710`
- `JUNE_TOP50_OUT_NET_PNL = -15,980`
- `JULY_TOP50_OUT_NET_PNL = 3,570`
- `AUGUST_TOP50_OUT_NET_PNL = 6,980`
- `LATE_STAGNATION_WINDOW_TOP50_OUT_NET_PNL = 1,850`
- `LATE_STAGNATION_WINDOW_TOP50_OUT_DRAG_SHARE = not a drag; positive contribution`
- `SELL_ROOT_CAUSE_MATERIALITY = MATERIAL_BUT_SECONDARY`
- `LOSS_STRUCTURE = FEW_LARGE_SELL_FAILURES`
- `PROFIT_RETENTION_COMPONENT_MATERIAL = YES`
- `CAPITAL_ROTATION_COMPONENT_MATERIAL = YES`
- `TOP50_HARD_EXIT_JUSTIFIED = NO`
- `TOP50_SOFT_EVIDENCE_REVIEW_JUSTIFIED = YES`
- `SELL_ROTATION_DESIGN_REVIEW_JUSTIFIED = YES`
- `CORRECTNESS_DEFECT_FOUND = NO`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`
- `DESIGN_REFINEMENT_JUSTIFIED = YES`
- `NEXT_DESIGN_DIRECTION = opportunity-cost-aware SELL/rotation review, no hard Top50 exit`

Final Judgment: `PHASE32_FY_TOP50_OUTSIDE_NEGATIVE_DRAG_MATERIAL_BUT_SECONDARY_LATE_STAGNATION_NOT_DOMINANT_NO_CORRECTNESS_DEFECT`
