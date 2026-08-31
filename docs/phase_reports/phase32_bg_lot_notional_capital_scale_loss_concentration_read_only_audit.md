# Phase32-BG — Lot Notional / Capital-Scale Loss Concentration READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T003243720082Z`
- Snapshot inspected: 2026-09-01 05:54:00 JST
- Run state at snapshot: `RUNNING`
- Current continuation point at snapshot: `2024-04-23:submit`
- Completed evidence used: 382 completed valuation days, `2022-10-03` through `2024-04-22`
- Source commit recorded by run plan: `ff1d23157cced619c5820898f8317a7440e6092c`

This is READ-ONLY. No code, config, model, threshold, runtime state, Pending, Ledger, replay, resume, recover, or fresh-run action was executed or changed.

## Method

For each campaign whose first entry was a BUY_NEW fill, this audit calculated:

`entry_lot_notional = execution_price * executed_quantity`

`entry_notional_ratio = entry_lot_notional / decision-time portfolio equity`

Primary entry-time equity authority was `strategy/position_sizing.json` field `portfolio_total_equity` when present. The closed-campaign outcome was measured from run-scoped realized slices. Open campaigns were excluded from win/loss rate and realized PnL statistics.

This is not a parameter-selection exercise. Historical PnL is used only to characterize scale, concentration, and economic magnitude.

## Campaign Population

- BUY_NEW campaigns observed: `562`
- Closed campaigns with realized slice evidence: `557`
- Open campaigns at snapshot: `5`
- Minimum-lot entries: dominant in high-ratio buckets. All entries in `5-10%`, `10-15%`, `15-20%`, and `>20%` were effectively 100-share lot entries in this completed evidence.

## Notional Ratio Buckets

| Entry notional / equity | Campaigns | Closed | Winners | Losers | Win rate | Realized PnL | Loss total | Avg PnL | Median PnL | Avg duration |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `<5%` | 331 | 328 | 139 | 173 | 42.4% | +93,280 | -390,900 | +284 | -155 | 5.6BD |
| `5-10%` | 134 | 133 | 62 | 67 | 46.6% | +324,120 | -333,910 | +2,437 | -100 | 6.4BD |
| `10-15%` | 61 | 60 | 26 | 33 | 43.3% | +320,840 | -245,130 | +5,347 | -300 | 11.6BD |
| `15-20%` | 30 | 30 | 13 | 16 | 43.3% | -72,230 | -259,460 | -2,408 | -500 | 6.1BD |
| `>20%` | 6 | 6 | 2 | 4 | 33.3% | -145,200 | -171,200 | -24,200 | -16,150 | 3.0BD |

Interpretation:

- The strongest adverse bucket is `>20%`: small sample, poor win rate, poor median, and negative total PnL.
- `15-20%` is also negative in aggregate.
- `10-15%` is strongly positive because high-notional winners exist.
- Therefore the evidence supports tail risk from very high entry-notional ratio, but not a simple monotonic "higher notional always worse" rule.

## Major Loser Notional Ratios

| Symbol | Entry | Exit | Realized PnL | Entry price | Qty | Entry notional | Entry equity | Ratio | Bucket | Capital scale | Min lot |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| 55950 | 2024-03-07 | 2024-03-11 | -86,500 | 4,170 | 100 | 417,000 | 1,714,080 | 24.33% | `>20%` | `>=1.6M` | YES |
| 55860 | 2024-03-13 | 2024-03-15 | -56,300 | 2,413 | 100 | 241,300 | 1,651,070 | 14.61% | `10-15%` | `>=1.6M` | YES |
| 74770 | 2023-10-02 | 2023-10-05 | -52,400 | 3,475 | 100 | 347,500 | 1,660,310 | 20.93% | `>20%` | `>=1.6M` | YES |
| 51890 | 2023-04-10 | 2023-04-17 | -47,750 | 2,965 | 100 | 296,500 | 1,592,530 | 18.62% | `15-20%` | `1.4-1.6M` | YES |
| 60220 | 2023-04-11 | 2023-04-13 | -45,500 | 3,000 | 100 | 300,000 | 1,605,530 | 18.69% | `15-20%` | `>=1.6M` | YES |
| 62310 | 2023-04-28 | 2023-05-15 | -32,700 | 2,087 | 100 | 208,700 | 1,542,490 | 13.53% | `10-15%` | `1.4-1.6M` | YES |
| 36590 | 2024-02-08 | 2024-02-09 | -26,150 | 2,902 | 100 | 290,200 | 1,691,930 | 17.15% | `15-20%` | `>=1.6M` | YES |
| 90820 | 2023-10-24 | 2023-10-25 | -25,500 | 1,410 | 100 | 141,000 | 1,650,720 | 8.54% | `5-10%` | `>=1.6M` | YES |
| 69420 | 2024-02-13 | 2024-02-15 | -24,500 | 1,445 | 100 | 144,500 | 1,661,140 | 8.70% | `5-10%` | `>=1.6M` | YES |
| 44250 | 2024-03-12 | 2024-03-18 | -21,900 | 2,649 | 100 | 264,900 | 1,612,120 | 16.43% | `15-20%` | `>=1.6M` | YES |
| 92460 | 2023-10-06 | 2023-10-11 | -21,500 | 3,465 | 100 | 346,500 | 1,681,150 | 20.61% | `>20%` | `>=1.6M` | YES |
| 40750 | 2023-06-20 | 2023-06-26 | -21,000 | 1,542 | 100 | 154,200 | 1,688,380 | 9.13% | `5-10%` | `>=1.6M` | YES |

Major loser interpretation:

- Four of the top twelve losers are `15-20%`; three are `>20%`; three are `5-10%`; two are `10-15%`.
- The largest single loser, `55950`, was a 100-share minimum-lot position with a 24.33% entry ratio.
- The high-ratio losers mostly occur after capital had grown to `>=1.6M`, supporting a capital-scale / effective-universe expansion hypothesis.
- However, several material losers are below 10%, so weak-starter accumulation is not fully explained by high notional alone.

## Winner Control Group

High notional also produced important winners:

| Symbol | Entry | Exit | Realized PnL | Entry notional | Ratio | Bucket | Notes |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| 59350 | 2023-03-22 | 2023-04-20 | +188,600 | 184,400 | 14.31% | `10-15%` | Largest winner and also a BF profit-retention giveback case. |
| 62280 | 2023-12-21 | 2023-12-28 | +78,330 | 249,000 | 15.70% | `15-20%` | High-notional winner. |
| 66780 | 2023-07-06 | 2023-12-05 | +41,800 | 193,400 | 12.49% | `10-15%` | Durable winner. |
| 88900 | 2023-05-22 | 2023-07-14 | +28,400 | 267,700 | 18.82% | `15-20%` | High-ratio winner. |
| 70640 | 2022-10-04 | 2022-10-13 | +18,000 | 203,750 | 20.13% | `>20%` | High-ratio winner even at low capital. |

Winner control result:

- High notional does not merely create losers. It creates both tails.
- The `10-15%` bucket is net strongly positive, largely because high-ratio winners offset many small losses.
- A blunt notional-ratio cap would have rejected or reduced some of the best winners, especially `59350`, `62280`, `66780`, and `88900`.
- Winner false-rejection risk is HIGH for any simple cap below about 15-20%.

## Capital-Scale Buckets

| Entry-time equity | BUY_NEW | Closed | Winners | Losers | Win rate | Realized PnL | Loss total | Large losses <= -20k | Avg entry price | Median price | Avg notional | Median notional | Avg ratio | Median ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `<1.2M` | 188 | 188 | 91 | 87 | 48.4% | +351,600 | -214,540 | 0 | 610 | 459 | 64,150 | 45,875 | 5.8% | 3.9% |
| `1.2M-1.4M` | 12 | 12 | 2 | 10 | 16.7% | +153,420 | -40,680 | 0 | 1,115 | 1,178 | 113,542 | 117,800 | 8.8% | 9.1% |
| `1.4M-1.6M` | 153 | 149 | 68 | 74 | 45.6% | +319,880 | -390,950 | 3 | 828 | 578 | 90,967 | 63,800 | 6.0% | 4.2% |
| `>=1.6M` | 209 | 208 | 81 | 122 | 38.9% | -304,090 | -754,430 | 10 | 902 | 635 | 98,429 | 66,900 | 5.9% | 4.1% |

Interpretation:

- Loss concentration worsens materially once entry-time equity is `>=1.6M`.
- Large losses of `<= -20k` appear mainly in the higher-capital regimes: 10 cases at `>=1.6M`, 3 cases at `1.4-1.6M`, none below `1.4M`.
- Average entry price and notional are higher after capital grows, but median entry ratio remains near 4%.
- The capital-scale effect is therefore not only a ratio effect. It is a mixture of larger absolute lot notionals, more executable high-price names, and starter-quality/churn conditions.

## Affordability Transition

The evidence supports a partial affordability-transition mechanism:

`CAPITAL_GROWTH -> more high-price 100-share lots become practically deployable -> larger absolute starter losses`

Support:

- Top high-ratio losers after equity exceeded `1.6M` include `55950`, `74770`, `60220`, `36590`, `44250`, and `92460`.
- These are 100-share minimum-lot positions where the minimum executable notional was large in absolute terms.
- The `>=1.6M` capital bucket has the worst aggregate result and largest count of `<= -20k` losses.

Limits:

- High-ratio winners existed even below `1.2M`, such as `70640` at a 20.13% ratio.
- The system did buy high-ratio names at lower capital too; they were not universally impossible.
- Median ratio did not rise with capital. Capital growth made more large absolute notional trades tolerable, but did not automatically force all entries into high-ratio buckets.

Conclusion: `CAPITAL_SCALE_AFFORDABILITY_EFFECT_SUPPORTED` as a contributing mechanism, not as the sole root cause.

## 100-Share Lot Constraint

The 100-share lot constraint is material for tail risk:

- All `>20%` entries were minimum-lot entries.
- All top high-ratio major losers were 100-share minimum-lot entries.
- The largest loser `55950` had a single-lot notional of `417,000`, 24.33% of entry equity.
- Larger quantity entries with low price, such as `97040` and `21340`, often fell below 5% ratio despite large share quantity; this confirms that price * lot notional, not share count, is the capital-scale issue.

This is a design/economic characteristic, not a correctness defect.

## Large Daily PnL Tails

High-notional positions explain some, but not all, large daily tails.

Examples:

- `2024-03-08` Equity delta `-62,430`: top contributors included `55950 -31,000` and `34160 -17,400`. This is consistent with high notional starter loss.
- `2024-03-14` Equity delta `-88,040`: top contributors included `44250 -70,000` and `55860 -29,900`. High-ratio 100-share positions dominated.
- `2024-03-15` Equity delta `-57,040`: broad high-price starter/position losses, including `44250`, `55860`, and `23970`.
- Many `2023-04` large daily moves were dominated by `59350`, a high-ratio winner/giveback campaign.
- Many `2023-05` to `2023-08` large daily moves were dominated by `67310`; this is not a high entry-notional ratio problem because its entry was `200,000` at about 13-14% depending on entry equity, but the observed daily oscillation pattern is more related to campaign basis/valuation and profit-retention evidence.

Conclusion:

- High-notional starters are a real contributor to jagged negative tails.
- They do not fully explain the jagged Equity curve, because large Winner giveback and campaign-specific valuation movement also dominate some days.

## Relationship to Phase32-BF

BF's `WEAK_STARTER_ACCUMULATION = HIGH` is a mixture:

- General starter-quality failure: SUPPORTED.
- High-notional starter failure: SUPPORTED, especially after equity exceeded `1.6M`.
- Capital-scale affordability effect: SUPPORTED as partial.
- Discrete-lot sizing distortion: SUPPORTED for the most extreme `>20%` and many `15-20%` starters.
- Position-sizing distortion: MATERIAL in the sense that 100-share minimum lots create large unavoidable entry ratios. Not proven as a code correctness defect.

BF's `WINNER_PROFIT_RETENTION_LATE` is mostly independent:

- `59350` and `67310` are profit-retention / late-exit examples.
- `59350` was high-ratio and also a major winner, so notional caps would have cut a large winner.
- `67310` is better explained by profit-retention / campaign lifecycle behavior than by newly affordable high-notional starter failure.

## Required Final Answers

1. `HIGH_ENTRY_NOTIONAL_RATIO_ASSOCIATED_WITH_LOSS`: YES, but non-monotonic. The strongest signal is `>20%` and some `15-20%` minimum-lot entries.
2. `LOSS_RATE_BY_NOTIONAL_RATIO_BUCKET`: `<5%` 52.7% losers among closed non-flat campaigns; `5-10%` 50.4%; `10-15%` 55.0%; `15-20%` 53.3%; `>20%` 66.7%.
3. `PNL_BY_NOTIONAL_RATIO_BUCKET`: `<5%` +93,280; `5-10%` +324,120; `10-15%` +320,840; `15-20%` -72,230; `>20%` -145,200.
4. `MAJOR_LOSER_NOTIONAL_RATIOS`: top major losers include `55950` 24.33%, `74770` 20.93%, `92460` 20.61%, `60220` 18.69%, `51890` 18.62%, `36590` 17.15%, `44250` 16.43%, `55860` 14.61%.
5. `WINNER_CONTROL_RESULT`: high-notional winners are material; `59350`, `62280`, `66780`, `88900`, and `70640` show that high ratio creates both positive and negative tails.
6. `HIGH_NOTIONAL_WINNER_FALSE_REJECTION_RISK`: HIGH for blunt caps, especially below 15-20%.
7. `DOES_EFFECTIVE_UNIVERSE_CHANGE_WITH_CAPITAL_SCALE`: YES, partially. Higher capital allows more high-price 100-share lots to be deployed with less immediate affordability pressure.
8. `DO_NEWLY_AFFORDABLE_SECURITIES_UNDERPERFORM`: PARTIAL / MIXED. The `>=1.6M` bucket underperformed and contains most large losses, but high-notional winners also exist.
9. `IS_100_SHARE_LOT_CONSTRAINT_MATERIAL`: YES. It is central to the extreme ratio tails.
10. `IS_POSITION_SIZING_DISTORTION_MATERIAL`: YES as an economic sizing/design issue; NO as a proven correctness defect.
11. `DO_HIGH_NOTIONAL_POSITIONS_EXPLAIN_LARGE_DAILY_PNL_TAILS`: PARTIAL. They explain several 2024-03 negative tails and some 2023-10 losses, but not the full curve.
12. `IS_BF_WEAK_STARTER_ACCUMULATION_EXPLAINED_BY_THIS`: PARTIAL. High-notional starter failure is an important submechanism, not the whole weak-starter problem.
13. `IS_WINNER_PROFIT_RETENTION_LATE_INDEPENDENT`: YES, mostly independent; it overlaps in `59350` but not in the core `67310` mechanism.
14. `ECONOMIC_MAGNITUDE`: `15-20%` and `>20%` buckets together produced `-217,430` realized PnL; the `>=1.6M` capital bucket produced `-304,090` realized PnL with `-754,430` loss total and 10 large losses of `<= -20k`.
15. `IS_THIS_A_CORRECTNESS_DEFECT`: NO. This is an economic/design characteristic of lot sizing, not evidence of authority/ledger/valuation correctness failure.
16. `IS_DESIGN_CHANGE_JUSTIFIED`: YES for a shadow design study; not enough for immediate Production change.
17. `IS_PRODUCTION_CHANGE_JUSTIFIED_NOW`: NO.
18. `NEXT_RECOMMENDED_STEP`: design a shadow, PIT-only lot-notional risk overlay that distinguishes high-notional weak starters from high-notional winners; evaluate alongside BF profit-retention and starter-throttle mechanisms without selecting thresholds from this window.
19. `FINAL_JUDGMENT`: `PHASE32_BG_MIXED_CAPITAL_SCALE_AFFORDABILITY_AND_LOT_SIZING_DISTORTION_SUPPORTED_HIGH_NOTIONAL_TAIL_RISK_REAL_BUT_WINNER_FALSE_REJECTION_RISK_HIGH_NO_PRODUCTION_CHANGE`

## No Change Confirmation

- Code change: NO
- Config/model/threshold change: NO
- Runtime state mutation: NO
- Resume/recover/replay/fresh-run: NO
- Production behavior change: NO
- Future information used as decision-time evidence: NO

