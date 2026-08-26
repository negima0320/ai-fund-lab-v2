# Phase31-E0 — Return Degradation Causal Decomposition Audit

Status: COMPLETE
Task type: READ-ONLY CAUSAL AUDIT

## PRIMARY_JUDGMENT

```text
PHASE31_E0_RETURN_DEGRADATION_PRIMARY_CAUSES_IDENTIFIED
```

E0 compared the prior higher-return run and the current lower-return run using existing run artifacts only. No implementation, Strategy/PM/PC/PS/Runtime change, threshold tuning, fresh-run, resume, replay, or long Historical execution was performed.

The primary degradation evidence is portfolio composition and timing, visible from the first trading day. The two runs start from the same 2022-08-10 period, but the first day already differs by holdings, cash, exposure, and executed BUY_NEW set. By 2022-10-12, the old run is ahead by 61,250 JPY. Symbol-level realized/unrealized attribution reconstructs that gap exactly from existing fills plus PIT close prices.

REDUCE execution is structurally weak in both runs: PM emitted many REDUCE decisions, while actual REDUCE fills were few. However, the evaluation-only loss proxy does not support REDUCE failure as the primary cause of the current return gap. Several REDUCE-afterward names would have benefited from earlier exit, but several winners would have been damaged by immediate exit. 61750 is a clear structural REDUCE-unrepresentable case, but it contributed only about +200 JPY through the comparison end and is not the return-gap driver.

## OLD_RUN_ID

```text
runtime-test-historical-extended-smoke-20260818T015851711672Z
```

Evidence:

- `run_state.json` exists.
- profile: `historical-extended-smoke`
- status: `HALT` at 2022-12-16 current valuation refresh.
- target equity checkpoints matched:
  - 2022-08-10: `396,920 cash + 599,950 market = 996,870`
  - 2022-09-12: `63,550 cash + 1,033,510 market = 1,097,060`
  - 2022-10-06: `149,760 cash + 964,050 market = 1,113,810`

## CURRENT_RUN_ID

```text
runtime-test-historical-extended-smoke-20260820T120909096218Z
```

Evidence:

- `run_state.json` exists.
- profile: `historical-extended-smoke`
- status: `HALT` at 2022-10-13 market refresh.
- target equity checkpoints matched:
  - 2022-08-10: `556,520 cash + 436,280 market = 992,800`
  - 2022-09-12: `227,590 cash + 813,690 market = 1,041,280`
  - 2022-10-06: `232,110 cash + 806,390 market = 1,038,500`
  - 2022-10-12: `292,210 cash + 726,250 market = 1,018,460`

## COMPARISON_WINDOW

```text
2022-08-10 through 2022-10-12
```

The old run continues beyond 2022-10-12, but current run evidence halts on 2022-10-13. The comparison therefore uses the common completed daily valuation window.

## RETURN GAP

| Metric | Old | Current | Gap |
|---|---:|---:|---:|
| start equity proxy | 1,000,000 | 1,000,000 | 0 |
| 2022-10-12 equity | 1,079,710 | 1,018,460 | 61,250 |
| return at end | +7.971% | +1.846% | +6.125 pp old over current |

```text
OLD_RETURN_AT_END = +7.971%
CURRENT_RETURN_AT_END = +1.846%
RETURN_GAP = 61,250 JPY / 6.125 percentage points
```

## RETURN GAP TIMELINE

| Date | Old equity | Current equity | Gap | Old cash | Current cash | Old exposure | Current exposure | Pos old/current |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022-08-10 | 996,870 | 992,800 | 4,070 | 396,920 | 556,520 | 60.18% | 43.94% | 11 / 9 |
| 2022-08-12 | 1,009,830 | 1,006,120 | 3,710 | 389,810 | 328,830 | 61.40% | 67.32% | 11 / 12 |
| 2022-08-15 | 1,025,380 | 1,003,660 | 21,720 | 392,730 | 365,340 | 61.70% | 63.60% | 12 / 13 |
| 2022-09-12 | 1,097,060 | 1,041,280 | 55,780 | 63,550 | 227,590 | 94.21% | 78.14% | 14 / 13 |
| 2022-10-06 | 1,113,810 | 1,038,500 | 75,310 | 149,760 | 232,110 | 86.55% | 77.65% | 10 / 10 |
| 2022-10-12 | 1,079,710 | 1,018,460 | 61,250 | 231,760 | 292,210 | 78.53% | 71.31% | 9 / 8 |

```text
FIRST_ANY_EQUITY_DIVERGENCE_DATE = 2022-08-10
FIRST_MATERIAL_DIVERGENCE_DATE = 2022-08-15
```

`FIRST_MATERIAL_DIVERGENCE_DATE` uses a 10,000 JPY evidence threshold. Portfolio divergence starts earlier.

## PORTFOLIO DIVERGENCE

```text
FIRST_PORTFOLIO_DIVERGENCE_DATE = 2022-08-10
```

Initial holdings after 2022-08-10 fills:

| Class | Symbols |
|---|---|
| common | `23700`, `23880`, `66590`, `76470`, `89180` |
| old-only | `38410`, `39950`, `47770`, `47840`, `61980`, `83060` |
| current-only | `93180`, `94320`, `94340`, `95010` |

Later portfolio divergence examples:

| Date | Common | Old-only | Current-only | Quantity differences |
|---|---:|---|---|---|
| 2022-09-12 | 10 | `41650`, `44410`, `45960`, `78780` | `33700`, `68360`, `88910` | `94320`: old 1,000 vs current 1,100 |
| 2022-10-06 | 8 | `45410`, `70640` | `33500`, `70780` | none |
| 2022-10-12 | 6 | `45410`, `70640`, `82540` | `70780`, `92710` | none |

## SYMBOL-LEVEL ATTRIBUTION

At 2022-10-12, fills plus PIT close valuation reconcile exactly:

```text
OLD_SYMBOL_CONTRIBUTION_SUM = +79,710
CURRENT_SYMBOL_CONTRIBUTION_SUM = +18,460
RECONSTRUCTED_GAP = 61,250
```

Top old-minus-current symbol gaps:

| Symbol | Old contribution | Current contribution | Gap |
|---|---:|---:|---:|
| `93600` | 0 | +19,000 | -19,000 |
| `92420` | -6,700 | +12,200 | -18,900 |
| `70640` | +17,250 | 0 | +17,250 |
| `21380` | +3,000 | -12,700 | +15,700 |
| `78780` | +14,500 | 0 | +14,500 |
| `40800` | +42,300 | +31,200 | +11,100 |
| `41650` | -4,700 | +4,000 | -8,700 |
| `47770` | +7,800 | 0 | +7,800 |
| `33700` | -2,700 | +4,900 | -7,600 |
| `45750` | +2,900 | -3,700 | +6,600 |

Interpretation: both runs have winners and losers. The degradation is not one bad symbol; it is mixed composition/timing with old-only winners and current common-timing losers outweighing current-only winners.

## BUY_NEW ATTRIBUTION

BUY fill summary through 2022-10-12:

| Metric | Old | Current |
|---|---:|---:|
| total BUY fills | 79 | 73 |
| total SELL fills | 77 | 75 |
| initial 2022-08-10 BUY fills | 11 | 9 |

Contribution by symbol membership at 2022-10-12:

| Group | Count | Old contribution | Current contribution | Old-minus-current gap |
|---|---:|---:|---:|---:|
| old-only bought symbols | 15 | +45,800 | 0 | +45,800 |
| current-only bought symbols | 9 | 0 | +8,250 | -8,250 |
| common bought symbols | 59 | +33,910 | +10,210 | +23,700 |

Initial-day old-only buys contributed +10,640 by 2022-10-12. Initial-day current-only buys contributed +4,420. The initial composition gap alone was not the full degradation, but portfolio divergence began there and compounded via later timing.

```text
BUY_NEW_RETURN_GAP_CONTRIBUTION = approximately 37,550 JPY net old-only/current-only composition, plus 23,700 JPY common-symbol timing/size gap
BUY_COMPOSITION_CAUSALITY = PRIMARY
```

This is attribution only, not a rule-selection or tuning recommendation.

## BUY_ADD / B10 ATTRIBUTION

Evidence:

- old runtime planning rows with B10 marginal-capital fields: `0`
- current runtime planning rows with B10 marginal-capital fields: `1,292`
- PM ADD decisions: old `34`, current `33`
- actual repeated BUY exposure into `94320` was nearly equal:
  - old `94320` total buy notional: 196,410, contribution +8,990
  - current `94320` total buy notional: 196,000, contribution +9,400

```text
BUY_ADD_RETURN_GAP_CONTRIBUTION = NOT_SUPPORTED_AS_NEGATIVE_DRIVER; 94320 was slightly current-positive by about 410 JPY
B10_CAUSALITY = PARTIAL
```

B10 clearly changed current-run capital-ordering evidence. The audit does not show B10 creating entry eligibility; it changed ordering/allocation among already admitted candidates. Its net effect is mixed: current-only `93600` helped materially, while old-only `70640`/`78780` and common timing differences hurt current.

## REDUCE EXECUTION AUDIT

| Metric | Old | Current |
|---|---:|---:|
| PM_REDUCE_COUNT | 136 | 154 |
| PM_EXIT_COUNT | 65 | 60 |
| PM_ADD_COUNT | 34 | 33 |
| PM_HOLD_COUNT | 238 | 211 |
| ACTUAL_REDUCE_FILL_COUNT | 12 | 15 |
| ACTUAL_EXIT_FILL_COUNT | 65 | 60 |

REDUCE fill symbols:

| Run | REDUCE fill symbols |
|---|---|
| old | `89180` x6, `36640` x2, `23230` x2, `23700` x1, `33500` x1 |
| current | `89180` x6, `36640` x2, `23230` x2, `33500` x2, `93180` x1, `78590` x1, `23700` x1 |

Old C0 shadow evidence was present and showed:

```text
reduce_decision_count = 136
unrepresentable_reduce_count = 124
representable_reduce_count = 0
parameter_unresolved_count = 74
persistent_branch_structural_count = 74
immediate_branch_structural_count = 1
recovery_blocked_count = 1
```

Current run did not contain `diagnostic_shadow/unrepresentable_reduce_exit_shadow.json` artifacts in the common window, so exact current lot-zero classification is inferred only from PM REDUCE vs actual REDUCE fills, not from C0 shadow.

## LOT-ZEROED REDUCE LOSS PROXY

Evaluation-only proxy: for each first PM REDUCE symbol, compare first REDUCE-date close to eventual exit date or 2022-10-12 close, multiplied by quantity before first REDUCE. This is not a claim that immediate EXIT was correct.

| Metric | Old | Current |
|---|---:|---:|
| LOT_ZEROED_REDUCE_GROSS_LOSS_PROXY | 48,990 | 37,490 |
| WINNER_DAMAGE_IF_IMMEDIATE_EXIT_PROXY | 88,380 | 118,490 |

Current top loss-proxy cases:

| Symbol | First REDUCE | End/exit | Qty proxy | Price change | Loss proxy |
|---|---|---|---:|---:|---:|
| `93180` | 2022-08-15 | 2022-08-16 | 8,300 | 6.0 to 5.0 | 8,300 |
| `15180` | 2022-08-23 | 2022-09-01 | 100 | 752.0 to 710.0 | 4,200 |
| `23230` | 2022-08-17 | 2022-08-19 | 1,000 | 67.7 to 63.8 | 3,900 |
| `88910` | 2022-09-27 | 2022-09-28 | 100 | 1439.0 to 1405.0 | 3,400 |
| `71380` | 2022-09-14 | 2022-09-16 | 100 | 347.0 to 317.2 | 2,980 |

Current top winner-damage cases if immediate exit were assumed:

| Symbol | First REDUCE | End/exit | Qty proxy | Price change | Foregone gain proxy |
|---|---|---|---:|---:|---:|
| `93600` | 2022-09-05 | 2022-09-12 | 100 | 1462.0 to 1740.0 | 27,800 |
| `40800` | 2022-08-19 | 2022-09-01 | 100 | 1458.0 to 1720.0 | 26,200 |
| `27670` | 2022-08-29 | 2022-10-04 | 100 | 664.5 to 914.0 | 24,950 |
| `33700` | 2022-09-09 | 2022-09-16 | 100 | 260.0 to 338.0 | 7,800 |
| `78590` | 2022-08-16 | 2022-08-19 | 200 | 263.0 to 301.0 | 7,600 |

```text
REDUCE_NOT_WORKING_CAUSALITY = MATERIAL
```

REDUCE is structurally material, but it is not supported as the primary return-degradation cause because immediate-exit counterfactual damage is larger than the gross loss proxy in this window.

## 61750 DEEP DIVE

| Metric | Old | Current |
|---|---:|---:|
| first BUY | 2022-08-17 | 2022-08-17 |
| first BUY quantity | 100 | 100 |
| first BUY price | 897 | 897 |
| first REDUCE | 2022-09-13 | 2022-09-13 |
| PM REDUCE count | 19 | 19 |
| actual REDUCE fill count | 0 | 0 |
| end quantity | 100 | 100 |
| 2022-10-12 contribution | +200 | +200 |

61750 is a clean REDUCE-unrepresentable persistence example: repeated REDUCE intent on a 100-share position did not produce execution. It is not a meaningful old-vs-current return-gap contributor in this window because both runs held the same 100 shares and had the same +200 contribution.

## WINNER GIVEBACK / EXIT TIMING

Evaluation-only symbol MFE giveback proxy:

| Metric | Old | Current | Gap |
|---|---:|---:|---:|
| TOTAL_WINNER_GIVEBACK | 115,650 | 100,050 | old higher by 15,600 |

Top giveback examples:

| Run | Symbol | MFE | End contribution | Giveback |
|---|---|---:|---:|---:|
| old | `92420` | 53,700 | -6,700 | 60,400 |
| old | `70640` | 46,250 | 17,250 | 29,000 |
| current | `92420` | 72,600 | 12,200 | 60,400 |
| current | `70780` | 27,800 | 2,200 | 25,600 |
| current | `65500` | 3,900 | -1,200 | 5,100 |

```text
WINNER_GIVEBACK_GAP = -15,600 JPY old-minus-current
EXIT_TIMING_RETURN_GAP_CONTRIBUTION = MIXED / NOT_PRIMARY
EXIT_GIVEBACK_CAUSALITY = MATERIAL
```

Winner giveback is real, but current did not have worse aggregate giveback than old under this proxy. It is a material architecture family to audit, not the dominant explanation for this specific old-vs-current degradation.

## EXPOSURE / CASH ATTRIBUTION

| Metric | Old | Current | Difference |
|---|---:|---:|---:|
| average exposure | 77.25% | 77.16% | +0.09 pp old |
| average cash | 240,385 | 231,635 | +8,750 old |
| days exposure > 90% | 8 | 7 | +1 old |
| days exposure < 60% | 2 | 4 | +2 current |

Exposure was not consistently lower in current. The largest visible exposure gap was timing-specific, especially 2022-09-12 and late September when current held more cash or lower exposure.

```text
EXPOSURE_DIFFERENCE = average exposure nearly equal; timing-specific cash drag is secondary
EXPOSURE_DIFFERENCE_CONTRIBUTION = SECONDARY / not independently isolated
```

## REGIME ATTRIBUTION

Using canonical `strategy/market_context.json` `regime_state` from the current run:

| Regime | Days | Old daily PnL sum | Current daily PnL sum | Old-minus-current gap |
|---|---:|---:|---:|---:|
| BULL | 11 | +9,550 | -32,340 | +41,890 |
| RANGE | 12 | +68,920 | +31,260 | +37,660 |
| CORRECTION | 5 | -18,830 | -24,630 | +5,800 |
| RECOVERY | 6 | +57,580 | +59,070 | -1,490 |
| BEAR | 8 | -37,510 | -14,900 | -22,610 |

```text
WORST_GAP_REGIME = BULL
```

Current underperformed most during BULL/RANGE dates, not during BEAR dates. This supports composition/timing and profit-capture explanations more than broad market-regime exposure failure.

## CAUSAL DECOMPOSITION

These estimates overlap; E0 does not force 100% allocation.

| Family | Evidence estimate | Causal rank |
|---|---:|---|
| BUY_NEW composition / timing | +37,550 net old-only/current-only plus +23,700 common timing-size gap | PRIMARY |
| BUY_ADD / capital allocation | `94320` current-positive by about 410; B10 allocation changed but mixed | MINOR / PARTIAL |
| lot-zeroed REDUCE | current gross loss proxy 37,490, but immediate-exit winner damage proxy 118,490 | MATERIAL |
| EXIT timing / winner giveback | current giveback lower than old by 15,600, but top current giveback exists | MATERIAL |
| exposure / cash | average exposure almost equal; current had more low-exposure days | SECONDARY |
| other / unexplained | 0 at symbol attribution level; causal family overlap remains | MINOR |

```text
BUY_NEW_RETURN_GAP_CONTRIBUTION = approximately 61,250 JPY across composition/timing attribution, with overlap to later exit/cash timing
BUY_ADD_RETURN_GAP_CONTRIBUTION = NOT_SUPPORTED_AS_NEGATIVE_DRIVER
LOT_ZEROED_REDUCE_GROSS_LOSS_PROXY = 37,490 JPY current evaluation-only
EXIT_TIMING_RETURN_GAP_CONTRIBUTION = MIXED / NOT_PRIMARY
WINNER_GIVEBACK_GAP = -15,600 JPY old-minus-current
UNEXPLAINED_RETURN_GAP = 0 JPY at symbol-level realized/unrealized reconciliation; causal-family overlap remains
```

## CAUSAL RANKING

```text
BUY_COMPOSITION_CAUSALITY = PRIMARY
B10_CAUSALITY = PARTIAL
REDUCE_NOT_WORKING_CAUSALITY = MATERIAL
EXIT_GIVEBACK_CAUSALITY = MATERIAL
EXPOSURE_CASH_CAUSALITY = SECONDARY
```

## TOP_5_CAUSAL_SYMBOLS

By absolute old-minus-current contribution gap:

```text
93600  current-only winner, current +19,000, reduces gap by 19,000
92420  common timing/exit difference, current +12,200 vs old -6,700, reduces gap by 18,900
70640  old-only winner, old +17,250
21380  common timing difference, old +3,000 vs current -12,700, adds 15,700 gap
78780  old-only winner, old +14,500
```

Because the top two helped current, the degradation is not simply "current bought worse names." The old run also captured old-only winners and avoided some current timing losses.

## CONSTRAINT CHECK

```text
FUTURE_INFORMATION_USED_FOR_PRODUCTION_DECISION = NO
IMPLEMENTATION_CHANGED = NO
LONG_HISTORICAL_EXECUTED = NO
FRESH_RUN_EXECUTED = NO
RUNTIME_REPLAY_EXECUTED = NO
PARAMETER_TUNING_PERFORMED = NO
```

Historical outcomes were used only for read-only attribution.

## NEXT_TASK_RECOMMENDATION

```text
mixed multi-causal follow-up
```

Recommended focus order:

1. Phase31-E1 BUY Quality / portfolio composition audit
2. Phase31-E1 winner giveback / exit timing audit
3. REDUCE/EXIT focused repair only after separating unrepresentable REDUCE from immediate-exit winner damage

## FINAL QUESTIONS

1. 収益低下の最大原因は何か？
   BUY_NEW composition / timing が最大。初日からportfolioが違い、old-only/current-only/common timing差で61,250円gapを説明できる。

2. REDUCEが実行できていないことはreturn gapの主因か？
   主因とは言えない。構造的にはmaterialだが、currentの即EXIT仮定は損失回避37,490円に対し、勝ち銘柄毀損118,490円のproxyがあり、単純修正は危険。

3. BUY_NEW構成差はどの程度影響したか？
   old-only/current-onlyで約37,550円、common symbolの買い時点/サイズ差で約23,700円。重複を含むが主因級。

4. B10は改善・悪化どちらへ寄与したか？
   PARTIAL。currentにB10 ordering evidenceはあるが、`94320`はcurrent微プラス、`93600`もcurrentを助けた。一方でold-only winnersを取り逃しており、B10単独悪化とは断定できない。

5. Winner giveback / EXIT遅延はmaterialか？
   materialだがprimaryではない。currentのaggregate givebackはoldより小さい一方、`92420`/`70780`など個別には大きい。

6. 次に最優先で直すべきfamilyはどれか？
   BUY Quality / portfolio composition auditを優先し、その後にwinner giveback / exit timing、REDUCE/EXITを分離して扱うのが妥当。
