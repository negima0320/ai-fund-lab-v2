# Phase32-AU - 67310 Campaign PnL / HOLD Justification READ-ONLY Audit

Target run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`

Trusted window: `2022-10-03` through `2023-10-10`

Audit mode: READ-ONLY. No source, config, runtime state, Strategy parameter, threshold, weight, HOLD/REDUCE/EXIT, corporate-action, or valuation rule changes were made. No fresh-run, resume, replay, recover, or long Historical command was executed.

Future-information policy: no future price, future return, future regime, final outcome, MFE/MAE hindsight, or Historical profitability was used to judge decision-time HOLD correctness. Post-hoc interpretation is separated in Section I.

## A. Full Campaign Timeline

Canonical campaign:

- Symbol: `67310`
- Campaign ID: `pc-47f89bc0fb3b790c-67310-0001`
- First BUY fill: `2023-04-21`
- BUY source decision: `rp-2023-04-21-67310-buy_new-db176c0db170e399`
- BUY order/pending item: `strategy-dadb12c66b4ebfb171ab`
- BUY quantity: `100`
- BUY execution price: `2000`
- BUY gross notional / cash effect: `200000` / `-200000`
- Source decision type: `BUY_NEW`
- Open in position campaign artifacts: `2023-04-24` through `2023-08-18`
- SELL/EXIT fill: `2023-08-18`
- SELL source decision: `rp-2023-08-18-67310-sell_exit-1bff0058b09249dc`
- SELL PM decision: `pm-2023-08-18-67310-exit`
- SELL order/pending item: `strategy-c6ba85ff5b759e12d049`
- SELL quantity: `100`
- SELL execution price: `2000`
- SELL gross notional / cash effect: `200000` / `+200000`
- Source decision type: `SELL_EXIT`
- Final trusted-window state on `2023-10-10`: campaign closed, quantity `0`, market value `0`

Actual fills show no executed ADD or REDUCE. PM produced ADD and REDUCE intents during the holding period, but no additional BUY_ADD fill and no partial REDUCE fill were executed.

Corporate-event evidence for sampled campaign-relevant dates (`2023-04-21`, `2023-04-24`, `2023-04-28`, `2023-05-01`, `2023-08-18`, `2023-10-10`) reports `67310` as `KNOWN_NO_EVENT`. The observed valuation-price transitions are therefore not explained by a canonical corporate-action event in the available artifacts.

## B. Economic PnL Reconciliation

Cash-flow / realized accounting:

- Total cash paid: `200000`
- Total cash received: `200000`
- Runtime realized slice allocated cost basis: `200000`
- Runtime realized slice gross realized PnL: `0`
- Net realized PnL: `NOT_AVAILABLE` because fees/tax are missing/not available in the fill evidence
- Unrealized PnL at `2023-10-10`: `0`, because the campaign is closed with quantity `0`
- Total gross economic PnL: `0`
- Campaign gross cash return: `0.0%`

Basis-aware acquisition cost is `200000`: `100` adjusted-basis shares at execution price `2000`.

`ECONOMIC_PNL` is zero on gross cash accounting. `DAILY_VALUATION_BASIS_SWING` is separate: while open, the adjusted valuation price repeatedly moved between `2000` and `3000`, producing visible `+/-100000` daily mark-to-market movements for `100` shares. Those presentation/accounting swings do not establish realized economic profit because the campaign eventually sold at the same `2000` price as its acquisition basis.

Answer: `DID_67310_ACTUALLY_MAKE_MONEY = NO_ON_GROSS_ECONOMIC_PNL` (`BREAK_EVEN`; net after unavailable costs is unknown and cannot be positive from available evidence).

## C. Daily +/-100000 Movement Explanation

The requested large movements are all explained by `100` adjusted-basis shares multiplied by a `1000` adjusted valuation-price change, except `2023-08-08` where the next available comparison remains flat.

| Dates | Qty | Price Basis | Valuation Price | Market Value | Delta | Classification |
| --- | ---: | --- | --- | ---: | ---: | --- |
| `2023-04-28 -> 2023-05-01` | `100 -> 100` | `ADJUSTED -> ADJUSTED` | `2000 -> 3000` | `200000 -> 300000` | `+100000` | `DAILY_VALUATION_BASIS_SWING` |
| `2023-06-08 -> 2023-06-09` | `100 -> 100` | `ADJUSTED -> ADJUSTED` | `2000 -> 3000` | `200000 -> 300000` | `+100000` | `DAILY_VALUATION_BASIS_SWING` |
| `2023-06-20 -> 2023-06-21` | `100 -> 100` | `ADJUSTED -> ADJUSTED` | `2000 -> 3000` | `200000 -> 300000` | `+100000` | `DAILY_VALUATION_BASIS_SWING` |
| `2023-06-26 -> 2023-06-27` | `100 -> 100` | `ADJUSTED -> ADJUSTED` | `2000 -> 3000` | `200000 -> 300000` | `+100000` | `DAILY_VALUATION_BASIS_SWING` |
| `2023-06-30 -> 2023-07-03` | `100 -> 100` | `ADJUSTED -> ADJUSTED` | `2000 -> 3000` | `200000 -> 300000` | `+100000` | `DAILY_VALUATION_BASIS_SWING` |
| `2023-07-05 -> 2023-07-06` | `100 -> 100` | `ADJUSTED -> ADJUSTED` | `2000 -> 3000` | `200000 -> 300000` | `+100000` | `DAILY_VALUATION_BASIS_SWING` |
| `2023-07-07 -> 2023-07-10` | `100 -> 100` | `ADJUSTED -> ADJUSTED` | `2000 -> 3000` | `200000 -> 300000` | `+100000` | `DAILY_VALUATION_BASIS_SWING` |
| `2023-07-11 -> 2023-07-12` | `100 -> 100` | `ADJUSTED -> ADJUSTED` | `2000 -> 3000` | `200000 -> 300000` | `+100000` | `DAILY_VALUATION_BASIS_SWING` |
| `2023-08-04 -> 2023-08-07` | `100 -> 100` | `ADJUSTED -> ADJUSTED` | `2000 -> 3000` | `200000 -> 300000` | `+100000` | `DAILY_VALUATION_BASIS_SWING` |
| `2023-08-08 -> 2023-08-09` | `100 -> 100` | `ADJUSTED -> ADJUSTED` | `2000 -> 2000` | `200000 -> 200000` | `0` | `NO_DAILY_SWING_ON_NEXT_AVAILABLE_COMPARISON` |

These `100000` moves should be treated as valuation-basis / mark-to-market characterization events, not as realized economic profit. They net out economically by the `2023-08-18` sale at `2000`.

## D. HOLD Decision Timeline

Held open business days: `80`, from `2023-04-24` through `2023-08-18`.

PM action counts while held:

- `HOLD`: `35`
- `REDUCE`: `29`
- `ADD`: `15`
- `EXIT`: `1`

Dominant cause counts:

- `HOLD_BY_PARTIAL_CONTINUATION`: `23`
- `REDUCE_BY_RISK_INCREASED_BUT_TREND_NOT_BROKEN`: `22`
- `ADD_BY_STRONG_TREND_AND_RANK`: `15`
- `HOLD_BY_STRONG_CONTINUATION`: `12`
- `REDUCE_BY_WEAK_HOLD_SCORE`: `6`
- `REDUCE_BY_HIGH_DOWNSIDE_RISK`: `1`
- `EXIT_BY_HARD_STOP`: `1`

Reason-code counts:

- `positive_expected_edge`: `35`
- `risk_increased_but_trend_not_broken`: `28`
- `downside_risk_contained`: `18`
- `profit_retention_break`: `17`
- `strong_trend_continuation`: `15`
- `opportunity_rank_still_high`: `15`
- `no_loss_averaging`: `15`
- `trend_continuation`: `2`
- `high_downside_risk_score`: `1`
- `hard_stop_current_return`: `1`

PC quality/action counts for `67310` while held:

- `MEDIUM / REDUCED_ALLOCATION_ONLY`: `47`
- `UNUSABLE / REJECT`: `29`
- `HIGH / FULL_ALLOCATION_ELIGIBLE`: `4`

Representative phases:

- `2023-04-24` to early May: repeated REDUCE consideration due `risk_increased_but_trend_not_broken`, interleaved with HOLD where `positive_expected_edge` and `downside_risk_contained` were present.
- Mid May to early July: several ADD intents (`ADD_BY_STRONG_TREND_AND_RANK`) and strong/partial continuation HOLDs. Evidence was not stale or absent; it repeatedly carried `strong_trend_continuation`, `opportunity_rank_still_high`, `no_loss_averaging`, and `positive_expected_edge`.
- Late July to mid August: weaker/reduction states became more frequent; PM still often classified deterioration as reduce-level or partial-continuation rather than full EXIT.
- `2023-08-18`: PM emitted `EXIT_BY_HARD_STOP` with `hard_stop_current_return|profit_retention_break`; SELL planning and submit accepted the full SELL_EXIT and execution closed the campaign.

## E. Why Kept?

Decision-time holding episodes classify as:

- `STRONG_HOLD`: days with `ADD_BY_STRONG_TREND_AND_RANK` or `HOLD_BY_STRONG_CONTINUATION`; contemporaneous evidence included strong continuation/rank/no-loss-averaging.
- `HEALTHY_CONTINUATION`: HOLD days with `positive_expected_edge` and `downside_risk_contained`.
- `REDUCE_CONSIDERED_BUT_NOT_AUTHORIZED`: 29 PM REDUCE days. PC target weights frequently moved below current weight, but actual position was only `100` shares, so partial reduction could not materialize as a valid 100-share executable decrement without becoming a full exit. The current contract did not authorize full EXIT until `2023-08-18`.
- `PASSIVE_HOLD_WITHOUT_FRESH_STRENGTH`: not the dominant pattern. Available evidence shows repeated continuation/edge/risk classifications rather than purely obsolete evidence.

The system kept holding `67310` because PM usually classified the position as either continuation-supported or reduce-worthy but not trend-broken enough for full EXIT. The eventual full EXIT was triggered once hard-stop/profit-retention-break evidence reached the EXIT contract.

## F. Missed Exit / Reduce Audit

Material weakening existed. The clearest weakenings were the 29 REDUCE decisions, including one `REDUCE_BY_HIGH_DOWNSIDE_RISK`, and the final `EXIT_BY_HARD_STOP` on `2023-08-18`.

No evidence shows a valid current-contract full EXIT signal was ignored before `2023-08-18`. The REDUCE signals were preserved into PC as `pm_action:REDUCE`; they were not silently erased. They did not become executed partial sells because the position size was one 100-share lot. Under the observed contract, partial REDUCE was infeasible without selling the entire position, and full EXIT authority arrived on `2023-08-18`.

Answer: `WAS_ANY_CURRENT_CONTRACT_EXIT_OR_REDUCE_SIGNAL_IGNORED = NO_CONCRETE_IGNORED_SIGNAL_OBSERVED`.

## G. Capital Occupancy

Open duration: `80` business days.

Capital occupancy:

- Average market value while open: `257500`
- Min / max market value while open: `100000` / `300000`
- PC average current weight while open: `0.16535345`
- PC max current weight while open: `0.200657`
- PC min current weight while open: `0.06872`
- Average remaining cash weight from PC cash competitor evidence while held: `0.162183575`

The campaign materially occupied portfolio capital. However, current artifacts do not show a concrete valid opportunity rejected specifically because `67310` occupied capital. Other member block/reject reasons were dominated by cash preference, quality reduction, reentry blocks, lot/residual mechanics, and liquidity-cap style constraints; no other-member blocker explicitly referenced `67310`.

Answer: `DID_IT_MATERIALLY_BLOCK_OTHER_VALID_OPPORTUNITIES = NOT_PROVEN_BY_CURRENT_EVIDENCE`.

## H. Economic Value vs Holding Duration

The long hold consumed about `80` business days and roughly `20.6M` market-value capital-days (`257500 * 80`) while producing `0` gross realized economic PnL.

The early/mid campaign generated large positive mark-to-market states at adjusted valuation price `3000`, but those gains were not monetized. By `2023-08-18`, the campaign sold at `2000`, equal to its basis-aware acquisition price.

Long holding was decision-time explainable, but not economically useful in realized gross cash terms for the completed campaign.

## I. POST_HOC Characterization Only

Post-hoc, `67310` looks like a campaign that repeatedly appeared as a large positive wave in daily equity characterization but ultimately realized no gross profit. This is useful for interpreting regime/large-positive/momentum statistics, not for changing decision-time correctness judgments in this READ-ONLY audit.

The available evidence supports a separation:

- Decision-time HOLD/ADD/REDUCE evidence was contemporaneous and not judged by future outcome.
- Completed-campaign economics were gross break-even.
- Large daily equity moves were mark-to-market valuation swings, not realized wealth creation.

## J. Measurement Interpretation

`67310` should remain included in final equity, campaign, regime, large-positive-day, and momentum-wave characterization metrics, because those metrics reflect actual runtime valuation artifacts in the trusted window.

However, reports must distinguish:

- `economic accounting`: cash paid, cash received, realized/unrealized PnL, closed-campaign gross return.
- `characterization metrics`: adjusted-basis daily valuation movement, momentum-wave contribution, regime-day contribution.

Adjusted-basis swings should not be excluded from valuation/equity time series if the time series is intended to represent runtime account valuation, but they should be labeled separately from realized economic profit and should not be described as proof that the campaign made money.

## K. Final Classification

Final classification:

`ECONOMICALLY_NEUTRAL_CAPITAL_OCCUPANCY_QUESTION`

Rationale: `67310` did not create positive gross economic PnL, but HOLD was not unsupported by current evidence and no ignored full EXIT/valid REDUCE execution authority was observed. The open campaign did materially occupy capital for 80 business days, so it remains a performance-design characterization question rather than a correctness defect.

## Required Final Answers

1. `WHEN_WAS_67310_BOUGHT`: `2023-04-21`, BUY_NEW, `100` shares at `2000`.
2. `WHAT_WAS_THE_BASIS_AWARE_ACQUISITION_COST`: `200000`.
3. `WAS_IT_EVER_ADDED_OR_REDUCED`: PM emitted ADD/REDUCE intents, but actual fills show no executed ADD or REDUCE.
4. `WAS_IT_STILL_OPEN_ON_2023_10_10`: No. It was closed by SELL_EXIT on `2023-08-18`.
5. `WHAT_IS_REALIZED_PNL`: gross realized PnL `0`; net unavailable because fees/tax are missing.
6. `WHAT_IS_UNREALIZED_PNL`: `0` at `2023-10-10`, because the position was closed.
7. `WHAT_IS_TOTAL_ECONOMIC_PNL`: gross total economic PnL `0`.
8. `DID_67310_ACTUALLY_MAKE_MONEY`: No on gross economic PnL; break-even.
9. `WHY_DID_DAILY_EQUITY_MOVE_BY_ABOUT_100K`: `100` shares times adjusted valuation price changes of about `1000`.
10. `DID_THOSE_100K_SWINGS_NET_OUT`: Yes economically; the campaign sold at the same `2000` price as its acquisition basis.
11. `WHY_DID_THE_SYSTEM_KEEP_HOLDING_67310`: PM saw positive expected edge / continuation / strong trend on many days, and on weaken days produced REDUCE rather than full EXIT until hard-stop EXIT on `2023-08-18`.
12. `WAS_ANY_VALID_REDUCE_OR_EXIT_SIGNAL_IGNORED`: No concrete ignored current-contract signal observed.
13. `HOW_LONG_WAS_THE_POSITION_HELD`: `80` open business days in position artifacts (`2023-04-24` through `2023-08-18`), with BUY fill on `2023-04-21`.
14. `WHAT_WAS_AVERAGE_AND_MAX_PORTFOLIO_WEIGHT`: PC average current weight `0.16535345`; max `0.200657`.
15. `DID_IT_MATERIALLY_BLOCK_OTHER_VALID_OPPORTUNITIES`: Not proven by current evidence.
16. `WAS_LONG_HOLDING_ECONOMICALLY_USEFUL`: No in realized gross cash terms; it was decision-time explainable but ended gross break-even.
17. `SHOULD_ADJUSTED_BASIS_SWINGS_BE_EXCLUDED_FROM_MOMENTUM_WAVE_CHARACTERIZATION`: No, but they must be labeled as valuation-basis/mark-to-market swings and separated from realized economic profit.
18. `IS_ANY_CORRECTNESS_DEFECT_PRESENT`: No concrete correctness defect found in this audit.
19. `IS_ANY_PRODUCTION_CHANGE_JUSTIFIED`: No production change is justified by this READ-ONLY audit alone.
20. `FINAL_CLASSIFICATION`: `ECONOMICALLY_NEUTRAL_CAPITAL_OCCUPANCY_QUESTION`.

## Final Judgment

`PHASE32_AU_67310_ECONOMICALLY_NEUTRAL_HOLD_DECISION_TIME_EXPLAINABLE_CAPITAL_OCCUPANCY_QUESTION_NO_CORRECTNESS_DEFECT`
