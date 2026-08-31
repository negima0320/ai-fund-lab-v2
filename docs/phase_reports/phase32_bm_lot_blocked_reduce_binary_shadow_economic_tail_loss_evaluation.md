# Phase32-BM - Lot-Blocked REDUCE Binary SHADOW Economic & Tail-Loss Evaluation

## Scope

Target run:

`runtime-test-historical-extended-smoke-20260831T003243720082Z`

This was a READ-ONLY evaluation. No source, config, model, threshold, weight, Runtime state, Pending, Ledger, recover, replay, resume, or fresh-run action was performed.

The run continued while this audit was being read. For direct comparison with Phase32-BJ/BK, this report fixes the evaluation window at the same cutoff:

- comparable completed window: `2022-10-03` through `2024-05-01`
- comparable completed business days: `388`
- actual run had progressed to at least `2024-05-16` during this audit, but post-cutoff days are excluded from BJ/BK comparison tables

Historical outcomes are used only for evaluation, not as shadow decision inputs.

## Method

Phase32-BL shadow decisions were reproduced in memory from completed run artifacts:

- `strategy/position_management.json`
- `strategy/position_sizing.json`
- `strategy/runtime_planning.json`
- `strategy/strategy_intelligence.json`
- `strategy/market_context.json`
- `execution/fills.json`
- final cutoff `positions/position_campaigns.json`
- current valuation projections for daily PnL

No BL shadow artifact was written into the run.

Episode definition:

- first eligible lot-blocked REDUCE per campaign
- repeated blocked REDUCE rows in the same campaign are not double-counted
- neutral threshold: absolute economic effect <= `1,000`, matching BJ/BK

Economic effect:

`Full EXIT at first blocked REDUCE value - actual subsequent campaign value`

Positive means Full EXIT would have helped. Negative means HOLD/current path preserved gain or recovery.

## BL Shadow Reproduction

All eligible lot-blocked REDUCE rows before episode de-duplication:

| Shadow decision | Rows |
|---|---:|
| `SHADOW_FULL_EXIT` | 38 |
| `SHADOW_HOLD` | 57 |
| `SHADOW_INSUFFICIENT_EVIDENCE` | 537 |

First non-overlapping episodes:

| Shadow decision | Episodes |
|---|---:|
| `SHADOW_FULL_EXIT` | 22 |
| `SHADOW_HOLD` | 23 |
| `SHADOW_INSUFFICIENT_EVIDENCE` | 298 |
| Total | 343 |

Production invariance check:

- production actual action remained unchanged
- shadow order authority: false
- shadow submit authority: false
- shadow execution authority: false
- `action_score` was diagnostic only
- future outcome / future PnL / final campaign outcome was not used by the shadow decision

## Economic Outcome

### SHADOW_FULL_EXIT

| Metric | Value |
|---|---:|
| Episodes | 22 |
| Helped | 13 |
| Hurt / false exits | 1 |
| Neutral | 8 |
| Avoided subsequent loss | 80,300 |
| Forfeited subsequent gain | 2,530 |
| Net Full EXIT effect | +77,770 |

This is high precision but low recall. The design avoids most false-exit cost, but captures only a small part of the harmful population.

### SHADOW_HOLD

| Metric | Value |
|---|---:|
| Episodes | 23 |
| Correctly protected beneficial cases | 9 |
| Harmful holds | 7 |
| Neutral | 7 |
| Preserved gain / recovery | 83,430 |
| Avoidable loss left uncut | 41,100 |
| Net HOLD value vs Full EXIT | +42,330 |

`SHADOW_HOLD` has real protection value, but also leaves material avoidable loss uncut.

### SHADOW_INSUFFICIENT_EVIDENCE

| Metric | Value |
|---|---:|
| Episodes | 298 |
| Harmful unresolved | 118 |
| Beneficial unresolved | 52 |
| Neutral | 128 |
| Avoided loss if Full EXIT had been applied | 783,920 |
| Forfeited gain if Full EXIT had been applied | 452,820 |
| Net unresolved Full EXIT effect | +331,100 |

Ambiguity cost is material. Most of Policy A's economic opportunity remains in `SHADOW_INSUFFICIENT_EVIDENCE`.

## Policy A Comparison

BJ mechanical Policy A baseline:

| Metric | Value |
|---|---:|
| Avoided loss | 863,980 |
| False-exit / forfeited gain cost | 518,140 |
| Net | +345,840 |

BL `SHADOW_FULL_EXIT` production-equivalent subset:

| Metric | Value |
|---|---:|
| Avoided loss retained vs Policy A | 80,300 / 863,980 = 9.29% |
| False-exit cost | 2,530 |
| False-exit cost reduction vs Policy A | 515,610 |
| Net | +77,770 |
| Net delta vs Policy A | -268,070 |

Harmful-case capture rate:

`13 / 138 = 9.42%`

Beneficial-case protection rate by explicit `SHADOW_HOLD`:

`9 / 62 = 14.52%`

Interpretation:

BL is conservative and avoids most false exits, but it does not preserve most of Policy A's loss avoidance. It does not outperform mechanical Policy A economically in this completed window.

## Large Daily Loss Tail

Daily PnL was computed from `current_valuation_refresh/valuation_projection.json` as:

`equity = cash + new_total_market_value`

`daily_pnl = equity(D) - equity(previous completed business day)`

Days with `DAILY_PNL <= -100,000`:

| Date | Daily PnL | Dominant loss symbol | Dominant contribution | Prior lot-blocked REDUCE | Earliest BL shadow |
|---|---:|---|---:|---|---|
| 2023-05-11 | -120,270 | 49370 | -157,100 | NO | none |
| 2023-06-08 | -116,600 | 67310 | -100,000 | YES | 2023-04-24 `SHADOW_INSUFFICIENT_EVIDENCE` |
| 2023-06-20 | -124,200 | 93410 | -216,000 | NO | none |
| 2023-06-26 | -108,350 | 67310 | -100,000 | YES | 2023-04-24 `SHADOW_INSUFFICIENT_EVIDENCE` |
| 2023-06-30 | -100,930 | 67310 | -100,000 | YES | 2023-04-24 `SHADOW_INSUFFICIENT_EVIDENCE` |
| 2023-07-18 | -108,800 | 88900 | -296,800 | NO | none |
| 2023-07-26 | -102,760 | 67310 | -100,000 | YES | 2023-04-24 `SHADOW_INSUFFICIENT_EVIDENCE` |
| 2023-08-08 | -103,820 | 67310 | -100,000 | YES | 2023-04-24 `SHADOW_INSUFFICIENT_EVIDENCE` |
| 2023-08-17 | -123,280 | 67310 | -100,000 | YES | 2023-04-24 `SHADOW_INSUFFICIENT_EVIDENCE` |

Summary:

| Metric | Value |
|---|---:|
| `DAILY_PNL <= -100,000` days | 9 |
| With prior lot-blocked REDUCE on dominant position | 6 |
| Pre-identified by `SHADOW_FULL_EXIT` | 0 |
| Estimated large-loss tail reduction by BL `SHADOW_FULL_EXIT` | 0 |
| Residual large-loss days not addressable by this BL design | 9 |

Critical read:

The large loss tail is heavily connected to `67310`, but BL classified the first `67310` blocked REDUCE as `SHADOW_INSUFFICIENT_EVIDENCE`, not `SHADOW_FULL_EXIT`, because substantial profit cushion created mixed evidence. Therefore BL as implemented does not materially reduce the `<= -100k` daily loss tail.

## BF Relationship

`WINNER_PROFIT_RETENTION_LATE`:

- `67310` was the central BF/BH example.
- BL did not classify it as `SHADOW_FULL_EXIT`.
- Tail-loss and giveback improvement from BL is therefore not confirmed.

Classification: `NO_MATERIAL_IMPROVEMENT_CONFIRMED`.

`WEAK_STARTER_ACCUMULATION`:

- Some smaller harmful cases are captured, including `36670`.
- Major harmful controls such as `62310`, `74770`, `34160`, and `51890` remain ambiguous.

Classification: `LIMITED_IMPROVEMENT_ONLY`.

Capital release:

- `SHADOW_FULL_EXIT` cases would release `1,367,670` notional in aggregate.
- Average days earlier than actual exit: `1.27`
- Maximum days earlier: `4`
- No assumption is made that freed cash earns future profit.

Classification: `DESCRIPTIVELY_MATERIAL_BUT_SHORT_HORIZON`.

## Control Cases

### BK Beneficial Controls

| Symbol | First blocked REDUCE | BL decision | Actual effect of Full EXIT | Protection read |
|---|---:|---|---:|---|
| 62280 | 2023-12-22 | `SHADOW_INSUFFICIENT_EVIDENCE` | -54,660 | Protected from false exit only because ambiguity blocks action, not explicit HOLD. |
| 74270 | 2023-08-14 | `SHADOW_INSUFFICIENT_EVIDENCE` | -41,100 | Protected by ambiguity, not explicit HOLD. |
| 92270 | 2022-10-24 | `SHADOW_INSUFFICIENT_EVIDENCE` | -30,000 | Protected by ambiguity, not explicit HOLD. |
| 72140 | 2023-05-25 | `SHADOW_INSUFFICIENT_EVIDENCE` | -24,000 | Protected by ambiguity, not explicit HOLD. |
| 83040 | 2024-02-21 | `SHADOW_INSUFFICIENT_EVIDENCE` | -23,050 | Protected by ambiguity, not explicit HOLD. |
| 69730 | 2022-11-04 | `SHADOW_HOLD` | -19,900 | Explicitly protected. |

The most important false-exit controls are not converted to `SHADOW_FULL_EXIT`, which is good. However only one of six is positively classified as `SHADOW_HOLD`.

### BK Harmful Controls

| Symbol | First blocked REDUCE | BL decision | Full EXIT benefit | Capture read |
|---|---:|---|---:|---|
| 67310 | 2023-04-24 | `SHADOW_INSUFFICIENT_EVIDENCE` | +100,000 | Missed; major tail/giveback case remains ambiguous. |
| 62310 | 2023-05-01 | `SHADOW_INSUFFICIENT_EVIDENCE` | +35,600 | Missed. |
| 74770 | 2023-10-04 | `SHADOW_INSUFFICIENT_EVIDENCE` | +29,900 | Missed. |
| 34160 | 2024-03-05 | `SHADOW_INSUFFICIENT_EVIDENCE` | +25,300 | Missed. |
| 36670 | 2023-06-16 | `SHADOW_FULL_EXIT` | +25,000 | Captured. |
| 51890 | 2023-04-14 | `SHADOW_INSUFFICIENT_EVIDENCE` | +24,250 | Missed. |

Only one of six mandatory harmful controls was captured.

## Production Readiness Judgment

Classification:

`MECHANICAL_POLICY_A_REMAINS_BETTER`

with an important caveat:

Policy A remains better only as a descriptive economic counterfactual. Its false-exit cost is still too large for direct Production acceptance. BL reduces false exits strongly, but gives up too much loss avoidance and does not improve the large daily-loss tail.

Production activation is not justified now.

## Required Final Answers

1. `SHADOW_FULL_EXIT_COUNT`: `22` first episodes; `38` raw eligible rows.
2. `SHADOW_HOLD_COUNT`: `23` first episodes; `57` raw eligible rows.
3. `SHADOW_INSUFFICIENT_EVIDENCE_COUNT`: `298` first episodes; `537` raw eligible rows.
4. `SHADOW_FULL_EXIT_AVOIDED_LOSS`: `80,300`.
5. `SHADOW_FULL_EXIT_FORFEITED_GAIN`: `2,530`.
6. `SHADOW_FULL_EXIT_NET_EFFECT`: `+77,770`.
7. `SHADOW_HOLD_PRESERVED_GAIN`: `83,430`.
8. `SHADOW_HOLD_AVOIDABLE_LOSS_LEFT_UNCUT`: `41,100`.
9. `HARMFUL_CASE_CAPTURE_RATE`: `13 / 138 = 9.42%`.
10. `BENEFICIAL_CASE_PROTECTION_RATE`: explicit `SHADOW_HOLD` protection `9 / 62 = 14.52%`.
11. `POLICY_A_NET_BASELINE`: `+345,840`.
12. `SHADOW_NET_VS_POLICY_A`: `-268,070` versus Policy A.
13. `POLICY_A_FALSE_EXIT_COST_REDUCTION`: `515,610`.
14. `LARGE_LOSS_DAY_COUNT_LE_100K`: `9`.
15. `LARGE_LOSS_DAYS_WITH_PRIOR_LOT_BLOCKED_REDUCE`: `6`.
16. `LARGE_LOSS_DAYS_PREVENTABLE_BY_SHADOW_FULL_EXIT`: `0`.
17. `ESTIMATED_LARGE_LOSS_TAIL_REDUCTION`: `0`.
18. `BF_WINNER_RETENTION_IMPROVEMENT`: `NO_MATERIAL_IMPROVEMENT_CONFIRMED`.
19. `BF_WEAK_STARTER_IMPROVEMENT`: `LIMITED_IMPROVEMENT_ONLY`.
20. `AMBIGUITY_COST_MATERIAL`: YES.
21. `CAPITAL_RELEASE_MATERIAL`: `DESCRIPTIVELY_MATERIAL_BUT_SHORT_HORIZON`; `1,367,670` notional, average `1.27` business days earlier.
22. `FUTURE_INFORMATION_USED`: NO.
23. `PRODUCTION_BEHAVIOR_CHANGED`: NO.
24. `IS_SHADOW_DESIGN_ECONOMICALLY_SUPPORTED`: PARTIAL for observation only; NOT sufficient for Production.
25. `IS_PRODUCTION_CHANGE_JUSTIFIED_NOW`: NO.
26. `NEXT_RECOMMENDED_STEP`: keep BL as diagnostic shadow only; design a follow-up read-only/SHADOW refinement focused on reducing the `SHADOW_INSUFFICIENT_EVIDENCE` ambiguity cost, especially 67310-like profit-cushion-with-deterioration cases, without fitting on outcomes.
27. `FINAL_JUDGMENT`: see below.

## Final Judgment

`PHASE32_BM_BL_BINARY_SHADOW_EVALUATED_MECHANICAL_POLICY_A_REMAINS_ECONOMICALLY_STRONGER_BL_NOT_READY_FOR_PRODUCTION_LARGE_LOSS_TAIL_NOT_REDUCED_AMBIGUITY_COST_MATERIAL`
