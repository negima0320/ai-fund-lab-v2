# Phase31-F0 — SELL / Position Management Profit-Retention Causal Audit

Status: COMPLETE
Task type: READ-ONLY PIT / POSITION-MANAGEMENT AUDIT

## PRIMARY_JUDGMENT

```text
PHASE31_F0_SELL_SIDE_PRIMARY_CAUSE_REDUCE_UNREPRESENTABLE_PERSISTENCE
```

F0 audited the SELL / Position Management side of the Phase31 return-degradation family using existing artifacts only. No implementation, SELL threshold change, REDUCE/EXIT rule change, fresh-run, resume, replay, or long Historical execution was performed.

The primary SELL-side defect is not that PM never detects deterioration. PM emits REDUCE and EXIT intents. The material structural gap is that REDUCE is commonly non-representable as an executable sell quantity under discrete-lot / minimum-notional constraints, and the system repeatedly preserves the position without a PM-owned escalation rule that can distinguish transient recovery from persistent deterioration.

## EVIDENCE SCOPE

```text
TARGET_RUN_OR_ARTIFACT = reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260820T120909096218Z
SUPPORTING_COMPARISON_RUN = reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z
TARGET_WINDOW = 2022-08-10 through 2022-10-12
BUSINESS_DAYS_AUDITED = 42
```

Primary evidence came from the current completed run:

- `daily/*/strategy/position_management.json`
- `daily/*/strategy/position_sizing.json`
- `daily/*/strategy/runtime_planning.json`
- `daily/*/execution/fills.json`
- `daily/*/strategy/market_context.json`

Supporting comparison used previously documented C0/E0 evidence from the older development run where Alternative G shadow artifacts existed. The current target run does not contain materialized Alternative G shadow artifacts, so Alternative G is evaluated as a structural fit, not as a current-run behavioral result.

## SELL FUNNEL

| Layer | Observation |
|---|---:|
| PM HOLD decisions | 211 |
| PM REDUCE decisions | 154 |
| PM EXIT decisions | 60 |
| PM ADD decisions | 33 |
| PS REDUCE rows | 154 |
| PS EXIT rows | 60 |
| Runtime SELL_EXIT plans | 60 |
| Runtime SELL_REDUCE plans | 0 |
| SELL EXIT fills | 60 |
| SELL REDUCE fills | 15 |

The 15 REDUCE fills are pending/existing reduce executions, not evidence that same-day PM REDUCE intents became positive executable REDUCE plans. In the audited current window, every PS REDUCE row had final sell quantity zero.

## REDUCE EXECUTABILITY

```text
PM_REDUCE_COUNT = 154
PS_REDUCE_COUNT = 154
POSITIVE_REDUCE_QUANTITY_COUNT = 0
ZERO_REDUCE_QUANTITY_COUNT = 154
REDUCE_FILL_COUNT = 15
```

All 154 PM REDUCE intents survived into PS as REDUCE candidates, but none produced a positive current-run `reduce_final_sell_quantity` / negative `final_quantity_delta`.

Zero-quantity REDUCE causes:

| Cause | Count |
|---|---:|
| REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT | 139 |
| REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL | 15 |

```text
ONE_LOT_REDUCE_UNREPRESENTABLE_COUNT = 131
PERSISTENT_REDUCE_CAMPAIGN_COUNT = 29
PERSISTENT_ZERO_REDUCE_CAMPAIGN_COUNT = 29
```

Representative persistent zero-REDUCE campaigns:

| Symbol | REDUCE rows | First | Last | Quantity | Cause |
|---|---:|---|---|---:|---|
| 61750 | 19 | 2022-09-13 | 2022-10-12 | 100 | DISCRETE_LOT |
| 83060 | 9 | 2022-08-16 | 2022-08-26 | 100 | DISCRETE_LOT |
| 43760 | 8 | 2022-08-26 | 2022-09-06 | 100 | DISCRETE_LOT |
| 32710 | 8 | 2022-09-07 | 2022-09-22 | 100 | DISCRETE_LOT |
| 68360 | 8 | 2022-09-07 | 2022-09-16 | 100 | DISCRETE_LOT |
| 54010 | 7 | 2022-08-16 | 2022-08-26 | 100 | DISCRETE_LOT |
| 39890 | 7 | 2022-08-31 | 2022-09-09 | 100 | DISCRETE_LOT |
| 89180 | 6 | 2022-08-12 | 2022-08-19 | 5000 | MINIMUM_NOTIONAL |
| 33500 | 6 | 2022-09-30 | 2022-10-11 | 500 | MINIMUM_NOTIONAL |

This is a structural representation problem: PM can say "reduce risk", but for many positions the requested partial sell cannot be represented as a valid market order.

## PM SELL EVIDENCE

PM SELL-side evidence was connected in the target run:

```text
STRATEGY_INTELLIGENCE_CONNECTED_REDUCE_COUNT = 154
STRATEGY_INTELLIGENCE_CONNECTED_EXIT_COUNT = 60
```

PM REDUCE reason codes:

| Reason | Count |
|---|---:|
| strategy_intelligence_sell_side_evidence_connected | 154 |
| risk_increased_but_trend_not_broken | 135 |
| peak_drawdown_warning | 19 |

PM EXIT reason codes:

| Reason | Count |
|---|---:|
| strategy_intelligence_sell_side_evidence_connected | 60 |
| trend_and_opportunity_broken | 22 |
| weak_hold_score | 18 |
| profit_retention_break | 15 |
| hard_stop_current_return | 11 |

PM therefore has a visible distinction between lighter REDUCE states and stronger EXIT states. The missing piece is the state-machine behavior after repeated unrepresentable REDUCE.

## RECOVERY SEPARABILITY

```text
RECOVERY_SEPARABILITY = PARTIAL
```

Current artifacts show both recovery and persistence after REDUCE:

| Post-REDUCE campaign pattern | Count |
|---|---:|
| Later HOLD or ADD observed | 17 |
| Later REDUCE persistence observed | 17 |
| Later EXIT observed | 6 |

This supports the core caution from C0: immediate unconditional REDUCE -> EXIT would be unsafe, because some REDUCE campaigns later recover into HOLD/ADD. However, repeated zero-quantity REDUCE with no executable partial sell is also real. A future repair should require a PM-owned persistence / recovery gate rather than blindly escalating every unrepresentable REDUCE.

## ALTERNATIVE G FIT

```text
ALTERNATIVE_G_STRUCTURAL_FIT = PARTIAL
```

Alternative G fits the observed failure family: one-lot or otherwise unrepresentable REDUCE can be shadow-classified, recovery-blocked, or escalated only after persistence. C0E already showed no PIT proof failures on the older development run and found:

- `UNREPRESENTABLE_REDUCE_COUNT = 324`
- `ONE_LOT_UNREPRESENTABLE_COUNT = 309`
- `G1_IMMEDIATE_STRUCTURAL_COUNT = 1`
- `G2_PERSISTENT_STRUCTURAL_COUNT = 225`
- `RECOVERY_BLOCKED_COUNT = 2`
- `PARAMETER_UNRESOLVED_COUNT = 225`

For F0, the fit is `PARTIAL` rather than `PASS` because the current target run does not contain current-run Alternative G shadow artifacts. The current run nevertheless reproduces the same structural pattern: all 154 current-window REDUCE candidates are zero-quantity, and 29 campaigns persist.

## EXIT SEPARABILITY

```text
EXIT_SEPARABILITY = PARTIAL
```

PM EXIT is not absent: 60 EXIT decisions became 60 SELL_EXIT plans and 60 EXIT fills. EXIT reasons include broken trend/opportunity, weak hold score, profit-retention break, and hard stop. That is enough to separate direct EXIT from light REDUCE states in many cases.

The unresolved part is timing: current artifacts can show that EXIT occurs, and can show observed PIT drawdown/giveback, but F0 does not use later outcome to declare the exact threshold early or late. A repair should focus first on unrepresentable REDUCE persistence before retuning EXIT thresholds.

## GIVEBACK ATTRIBUTION

```text
TOTAL_GIVEBACK = 120,631 JPY PIT-observed proxy
TOTAL_GIVEBACK_USAGE = attribution_only
```

The proxy sums each campaign's maximum PIT-observed `observed_giveback * quantity * average_price` across the audited window. This is not used to select SELL parameters or judge a same-day SELL decision. It is used only to show that profit-retention evidence is present and economically non-trivial.

Largest PIT-observed giveback proxies:

| Symbol | Date | PM action | Giveback proxy |
|---|---|---|---:|
| 88910 | 2022-09-28 | EXIT | 15,000 |
| 44220 | 2022-09-29 | EXIT | 9,070 |
| 40800 | 2022-08-26 | HOLD | 9,000 |
| 94320 | 2022-10-04 | ADD | 7,331 |
| 92420 | 2022-10-12 | HOLD | 7,300 |

## MARKET CONTEXT SELL AUTHORITY

```text
MARKET_CONTEXT_SELL_AUTHORITY = NONE
```

Canonical Market Context artifacts exist for each day, for example `regime_state = RECOVERY` on 2022-09-13 from `strategy/market_context.json`. However, audited PM decision rows had empty `market_context_reference` for all 458 PM rows, and audited PS SELL rows did not carry populated Market Context / regime fields.

Therefore Market Context is available elsewhere in Strategy, but F0 found no evidence that SELL / PM authority consumes it as a canonical SELL decision input in the target run.

## 61750 CONTROL

```text
61750_CONTROL_JUDGMENT = CONFIRMS_UNREPRESENTABLE_PERSISTENT_REDUCE
```

61750 is the clean control case:

- first current-window REDUCE: 2022-09-13
- last current-window REDUCE: 2022-10-12
- REDUCE rows: 19
- current quantity: 100
- trading unit: 100
- final sell quantity: 0 on every REDUCE row
- execution semantic: `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`
- PM reason: `risk_increased_but_trend_not_broken`

61750 shows a PM-level desire to reduce risk that cannot be executed as a partial sale. Without an escalation contract, the system can repeatedly emit non-executable REDUCE while retaining the full one-lot position.

## WINNER PROTECTION

```text
WINNER_PROTECTION_JUDGMENT = IMMEDIATE_REDUCE_TO_EXIT_UNSAFE_ALTERNATIVE_G_STYLE_GATE_REQUIRED
```

The current run contains 17 campaigns where a REDUCE state later moved to HOLD or ADD. PM also produced 211 HOLD decisions and 33 ADD decisions with connected Strategy Intelligence evidence. That means a simple rule converting every unrepresentable REDUCE into EXIT would likely damage recoveries and winners.

The next design should preserve the C0 principle: escalation must be PM-owned, PIT-only, persistence-aware, and recovery-blocked.

## REQUIRED OUTPUT

```text
PRIMARY_JUDGMENT = PHASE31_F0_SELL_SIDE_PRIMARY_CAUSE_REDUCE_UNREPRESENTABLE_PERSISTENCE
PM_HOLD_COUNT = 211
PM_REDUCE_COUNT = 154
PM_EXIT_COUNT = 60
REDUCE_FILL_COUNT = 15
ZERO_REDUCE_QUANTITY_COUNT = 154
ONE_LOT_REDUCE_UNREPRESENTABLE_COUNT = 131
PERSISTENT_REDUCE_CAMPAIGN_COUNT = 29
RECOVERY_SEPARABILITY = PARTIAL
ALTERNATIVE_G_STRUCTURAL_FIT = PARTIAL
EXIT_SEPARABILITY = PARTIAL
TOTAL_GIVEBACK = 120,631 JPY PIT-observed proxy, attribution_only
MARKET_CONTEXT_SELL_AUTHORITY = NONE
61750_CONTROL_JUDGMENT = CONFIRMS_UNREPRESENTABLE_PERSISTENT_REDUCE
WINNER_PROTECTION_JUDGMENT = IMMEDIATE_REDUCE_TO_EXIT_UNSAFE_ALTERNATIVE_G_STYLE_GATE_REQUIRED
PRIMARY_SELL_SIDE_CAUSE = REDUCE intents are structurally non-representable as executable partial sells, then can persist without a PM-owned escalation contract
SECONDARY_SELL_SIDE_CAUSES = market_context_not_consumed_by_sell_authority; exit_timing_threshold_unresolved; current_run_alternative_g_shadow_absent; reduce_fill_observability_mixed_with_pending_continuation
REPAIR_CANDIDATES = Phase31-F1 PM-owned unrepresentable REDUCE -> EXIT escalation design with persistence and recovery guards; add current-run shadow materialization before mutation; document Market Context SELL authority gap separately
FUTURE_INFORMATION_USED_FOR_SELL_DECISION_JUDGMENT = NO
OUTCOME_USED_FOR_PARAMETER_SELECTION = NO
IMPLEMENTATION_CHANGED = NO
LONG_HISTORICAL_EXECUTED = NO
```

## NEXT_TASK_RECOMMENDATION

```text
Phase31-F1 unrepresentable REDUCE -> EXIT escalation design
```

F1 should not tune SELL thresholds first. It should specify a PM-owned Alternative-G-style contract for unrepresentable REDUCE persistence, with explicit recovery protection and PIT evidence requirements. Current behavior changes should still wait for validation/shadow evidence.

## FINAL QUESTIONS

1. REDUCE最大の非実行理由は何か？

   `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT` が最大です。154件中139件でした。

2. 100株REDUCE unrepresentableはどの規模か？

   131件です。REDUCE全体154件の大部分を占めます。

3. persistent REDUCE no EXITは実在するか？

   Yes. 29 campaigns had repeated zero-quantity REDUCE; 61750 aloneで19回継続しました。

4. PITでrecoveryとpersistent deteriorationを区別できるか？

   Partially. 現artifact上、REDUCE後にHOLD/ADDへ戻るcampaignとREDUCE継続・EXITへ進むcampaignを分けられます。ただし本番採用できる閾値契約はF0では設計していません。

5. Alternative Gはwinner protectionしながら使えそうか？

   Structurally yes, but current-run materialized shadowがないためF0判定はPARTIALです。即時全EXITではなく、persistence + recovery guard型が必要です。

6. EXIT early/late structural casesはあるか？

   Partial. EXITは60件すべてplanning/fillに到達していますが、早すぎる/遅すぎる閾値判定はfuture outcomeを使わないと確定できないため、F0では未解決です。

7. Market Contextは十分に伝播しているか？

   No for SELL authority. Market Context artifact自体は存在しますが、PM SELL rowsの`market_context_reference`は全件空で、PS SELL rowsにもcanonical regime消費の証跡は見つかりませんでした。

8. F1優先か？

   Yes. まずF1でPM-owned unrepresentable REDUCE -> EXIT escalation designを行うのが妥当です。
