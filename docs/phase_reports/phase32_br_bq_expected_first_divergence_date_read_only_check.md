# Phase32-BR — BQ Expected First Divergence Date READ-ONLY Check

## Scope

Target baseline run:

```text
runtime-test-historical-extended-smoke-20260831T003243720082Z
```

This was a READ-ONLY check before starting a post-BQ long Historical run. No source, config, runtime state, Pending, Ledger, fresh-run, resume, recover, replay, or long Historical command was executed.

Historical outcome was not used as Production decision authority. The purpose was only to identify the first date where a same-condition fresh-run is expected to diverge after BQ Production materialization.

## Method

The BO shadow decisions were reconstructed in memory from existing run artifacts only:

- `strategy/position_management.json`
- `strategy/position_sizing.json`
- `strategy/runtime_planning.json`
- `strategy/strategy_intelligence.json`
- `strategy/market_context.json`

The in-memory builder was `build_unrepresentable_reduce_exit_shadow_payload`. No shadow artifact was written.

Episode definition:

```text
first lot-blocked REDUCE row per campaign,
then classify that first row's BO shadow decision
```

This distinction matters. Counting the first later `SHADOW_FULL_EXIT` per campaign produces a larger set, but that is not the BO/BP first-episode definition. The reproduced BO first-episode count is `23`.

## Reproduction Counts

| Population | Count |
|---|---:|
| raw lot-blocked REDUCE rows inspected | 646 |
| first lot-blocked REDUCE campaign episodes | 352 |
| raw BO `SHADOW_FULL_EXIT` rows | 46 |
| BO `SHADOW_FULL_EXIT` first episodes | 23 |

The `23` first episodes reproduce the BO/BP accepted population for `SHADOW_FULL_EXIT`.

## BO SHADOW_FULL_EXIT First Episodes

| # | business_date | symbol | campaign_id | original PM action / reason | lot-block evidence | BO decision | old Production outcome | BQ expected outcome |
|---:|---|---|---|---|---|---|---|---|
| 1 | 2022-10-07 | 45750 | `pc-e73fb1778127074d-45750-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 2 | 2022-11-08 | 88480 | `pc-b09efe6028acc290-88480-0001` | `REDUCE`; `peak_drawdown_warning;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `33.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 3 | 2022-11-16 | 35280 | `pc-d73615076f792d5e-35280-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 4 | 2022-12-05 | 94320 | `pc-76716bcc6d81f122-94320-0001` | `REDUCE`; `peak_drawdown_warning;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `99.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 5 | 2022-12-07 | 47520 | `pc-5d5a16b759e88045-47520-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 6 | 2022-12-19 | 14910 | `pc-8e474d627d164e98-14910-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 7 | 2022-12-23 | 78360 | `pc-516acd42fb6c56a6-78360-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `50.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 8 | 2023-01-27 | 94210 | `pc-7bb0b97073b769b8-94210-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 9 | 2023-02-15 | 78410 | `pc-7de32ea3384a99a2-78410-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 10 | 2023-03-13 | 39450 | `pc-81bd21fc41f0b4a5-39450-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 11 | 2023-03-27 | 76700 | `pc-32a0fe43da80cc1f-76700-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 12 | 2023-04-18 | 39610 | `pc-0b866c7b5ff80613-39610-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 13 | 2023-04-24 | 67310 | `pc-fb5e618430d49416-67310-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 14 | 2023-05-12 | 76020 | `pc-3d7fba25228aedf1-76020-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `50.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 15 | 2023-05-22 | 76010 | `pc-e261b4ac5af96919-76010-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `50.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 16 | 2023-06-16 | 36670 | `pc-193c02379d3ee9d8-36670-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 17 | 2023-06-30 | 40140 | `pc-c9a80058fc6746be-40140-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 18 | 2023-09-07 | 60290 | `pc-b65c5c3ba9aa3073-60290-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 19 | 2023-11-09 | 98120 | `pc-f95e6c2d0bfdf33f-98120-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 20 | 2023-12-13 | 78090 | `pc-70c91650da3962e4-78090-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 21 | 2023-12-27 | 24590 | `pc-229b01bdc05fc708-24590-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `50.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 22 | 2024-02-22 | 43760 | `pc-e3e1864302f96cbd-43760-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |
| 23 | 2024-03-27 | 70220 | `pc-cb0e1d5187ea42fe-70220-0001` | `REDUCE`; `risk_increased_but_trend_not_broken;strategy_intelligence_sell_side_evidence_connected` | `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`; raw `25.0`; rounded `0.0`; final `0.0`; unit `100.0` | `SHADOW_FULL_EXIT` | `NO_ORDER qty=0.0` | `SELL_EXIT` |

## Earliest Expected Divergence

Earliest BO `SHADOW_FULL_EXIT` first episode:

```text
business_date = 2022-10-07
symbol = 45750
campaign_id = pc-e73fb1778127074d-45750-0001
old Production outcome = NO_ORDER qty=0.0
BQ expected outcome = SELL_EXIT
```

Therefore:

```text
EXPECTED_FIRST_BQ_DIVERGENCE_DATE = 2022-10-07
```

## 67310 / 2023-04-24 Position

`67310 / 2023-04-24` is BO `SHADOW_FULL_EXIT` first episode number:

```text
13 of 23
```

Its old Production outcome was `NO_ORDER qty=0.0`; under BQ, if the same PIT evidence and authority bindings are reproduced in a fresh-run, the expected outcome is ordinary `SELL_EXIT`.

## Final Judgment

`PHASE32_BR_EXPECTED_FIRST_BQ_DIVERGENCE_DATE_IDENTIFIED_2022_10_07`
