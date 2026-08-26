# Phase31-C0A — Discrete-Lot REDUCE Persistence / EXIT Escalation Audit

Status: COMPLETE
Task type: READ-ONLY performance / Strategy semantics audit

## Executive Conclusion

This is not a Phase29/Phase30 lot-regression and not a Runtime Planning defect.

The current common contract is behaving as designed: PM emits `REDUCE`, PC/PS/Sell Planning attempt a partial de-risk quantity, discrete-lot rounding floors the desired partial sell to zero, and Runtime Planning preserves the PM intent as an intentional `NO_ORDER` rather than silently escalating to `EXIT`.

The performance issue is real but semantic: the system can repeatedly express a correct directional de-risk intent while being unable to represent it at the broker lot boundary. In the target run, every PM `REDUCE` row in the completed usable window was lot-zeroed.

Recommended classification:

```text
EXPECTED_EXISTING_BEHAVIOR_WITH_MATERIAL_STRATEGY_SEMANTIC_GAP
```

Recommended next design direction:

```text
STRATEGY/PM-owned persistence + existing-feature-confirmed escalation authority
```

Do not move this authority into PC, PS, Runtime Planning, Sell Planning, Submit Guard, or lot rounding.

## Audit Scope

Target run:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z
```

Completed usable evidence window:

```text
2022-08-10 through 2022-12-15
```

The 2022-12-16 HALT day is excluded from performance aggregation because Phase31-A6 already found a legitimate current-valuation halt for 61750. This audit uses only existing artifacts and short read-only inspection scripts. No fresh run, resume, replay, Strategy mutation, Runtime mutation, configuration mutation, test mutation, or fixture mutation was performed.

## Canonical REDUCE Semantics

PM_REDUCE_AUTHORITY:

```text
Position Management owns HOLD / ADD / REDUCE / EXIT investment decision authority.
```

Evidence:

- `docs/02_architecture/position_management_reduce_quantity_contract.md:7-19`
- `docs/02_architecture/position_management_reduce_quantity_contract.md:21-30`

PM_REDUCE_SEMANTIC:

```text
REDUCE is partial exposure reduction while preserving position membership / optionality.
It is not EXIT and must not implicitly become EXIT.
```

Evidence:

- `docs/02_architecture/position_management_reduce_quantity_contract.md:75-85`
- `docs/02_architecture/position_management_reduce_quantity_contract.md:136-145`

PM_REDUCE_STRENGTH_FIELD:

```text
reduce_intensity
```

Canonical values:

```text
LIGHT  = 0.25
MEDIUM = 0.33
STRONG = 0.50
```

Evidence:

- `docs/02_architecture/position_management_reduce_quantity_contract.md:32-38`
- `src/ai_fund_lab_v2/strategy/reduce_intensity_authority.py:7-19`

PM_REDUCE_TARGET_FIELD:

```text
PM: reduce_intensity
PC/PS: target_weight, target_reduce_ratio, raw_reduce_quantity, rounded_reduce_quantity,
       reduce_final_sell_quantity, target_quantity_candidate, quantity_delta_candidate
Runtime Planning: planning_intent, planned_quantity, no_order_reason, reduce_execution_semantic
```

## REDUCE To Discrete Quantity Trace

The canonical path is:

```text
PM REDUCE intent
  -> PC lower target weight / preserve membership
  -> PS/Sell Planning resolve target_reduce_ratio and raw_reduce_quantity
  -> floor to tradable unit
  -> zero executable quantity if sub-lot
  -> Runtime Planning NO_ORDER with REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
```

DISCRETE_LOT_ZEROING_OWNER:

```text
Position Sizing / Sell Planning quantity contract materialization.
```

MINIMUM_LOT_SOURCE:

```text
tradable_unit = 100 shares
```

ROUNDING_POLICY:

```text
floor_to_tradable_unit_to_avoid_oversell
```

ZERO_REDUCE_REASON:

```text
REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
```

Compatibility reason:

```text
REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY
```

Evidence:

- Contract formula and default lot: `docs/02_architecture/position_management_reduce_quantity_contract.md:75-85`
- Non-executable result: `docs/02_architecture/position_management_reduce_quantity_contract.md:87-106`
- No ceil / no forced debt / next-day fresh reevaluation: `docs/02_architecture/position_management_reduce_quantity_contract.md:136-145`
- PS floor and intentional no-order materialization: `src/ai_fund_lab_v2/strategy/position_sizing.py:930-956`
- Sell Planning quantity contract: `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:1648-1729`
- Sell Planning non-executable contract: `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:1732-1755`

## Run-Wide Inventory

Read-only aggregation over `strategy/position_sizing.json` for completed usable days:

| Metric | Value |
|---|---:|
| Business dates inspected | 86 |
| PM REDUCE rows | 344 |
| Executable REDUCE rows | 0 |
| Lot-zeroed REDUCE rows | 344 |
| LOT_ZEROED_REDUCE_RATE | 100.0% |
| Affected symbols / campaigns | 82 |
| Row-sum notional under zeroed REDUCE | 21,271,788 JPY |
| First-zero notional by symbol | 4,878,020 JPY |
| Current quantity <= one lot cases | 309 |

Reduce-intensity distribution:

| Intensity | Rows | Target ratio |
|---|---:|---:|
| LIGHT | 297 | 0.25 |
| MEDIUM | 23 | 0.33 |
| STRONG | 24 | 0.50 |

Regime distribution at decision time:

| Regime | Rows |
|---|---:|
| BULL | 138 |
| RANGE | 74 |
| RECOVERY | 64 |
| BEAR | 48 |
| CORRECTION | 20 |

Persistence distribution by symbol:

| Zeroed REDUCE row count | Symbols |
|---:|---:|
| 1 | 19 |
| 2 | 21 |
| 3 | 13 |
| 4 | 6 |
| 5 | 8 |
| 6 | 3 |
| 7 | 1 |
| 8 | 2 |
| 9 | 4 |
| 10 | 4 |
| 63 | 1 |

The issue is therefore family-wide, not a single 61750 anomaly.

## 61750 Exact Trace

61750 is the strongest persistence case.

First observed lot-zeroed REDUCE:

```text
date = 2022-09-13
quantity = 100
current_notional ~= 89,800 JPY
reduce_intensity = LIGHT
target_reduce_ratio = 0.25
raw_reduce_quantity = 25
rounded_reduce_quantity = 0
final_sell_quantity = 0
reduce_execution_semantic = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
regime = RECOVERY
```

Runtime Planning on 2022-09-13:

```text
source_pm_action = REDUCE
source_pm_decision_id = pm-2022-09-13-61750-reduce
planning_intent = NO_ORDER
planned_quantity = 0
quantity_delta_candidate = 0
target_quantity_candidate = 100
no_order_reason = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
full_liquidation_authority_present = false
full_liquidation_authority_source = NONE
```

Persistence:

```text
61750 zeroed REDUCE rows = 63
first zeroed REDUCE date = 2022-09-13
last completed usable date = 2022-12-15
last completed usable notional ~= 89,800 JPY
```

61750 regime distribution during zeroed REDUCE:

| Regime | Rows |
|---|---:|
| BULL | 19 |
| RANGE | 16 |
| BEAR | 12 |
| RECOVERY | 11 |
| CORRECTION | 5 |

61750 supports the persistence concern: PM repeatedly asked to de-risk 25 shares, but the 100-share trading unit made that impossible. It does not by itself prove that an immediate full EXIT would always be correct, because 61750 was a LIGHT reduce case, remained near flat through 2022-12-15, and had mixed-to-supportive point-in-time continuation features on some dates. It is evidence for a persistence-aware Strategy authority, not for blind Runtime escalation.

## Recovery And Winner Damage Control Group

A pure "exit every lot-zeroed REDUCE immediately" rule would release capital and avoid some losses, but it would also destroy winners.

Read-only outcome proxy from existing artifacts:

```text
campaigns with later HOLD/ADD recovery after first zeroed REDUCE = 57
campaigns with no later HOLD/ADD recovery in usable window = 25
winning immediate-exit false-positive cases observed = 24
estimated winner profit foregone under immediate first-zero EXIT proxy = 133,310 JPY
```

Representative winner-damage cases:

| Symbol | First zeroed REDUCE | Zero rows | Later recovery | Proxy positive delta |
|---|---|---:|---|---:|
| 40800 | 2022-08-19 | 2 | HOLD on 2022-08-23 | +27,000 |
| 27670 | 2022-08-25 | 3 | HOLD on 2022-08-26 | +18,650 |
| 92270 | 2022-11-01 | 1 | HOLD on 2022-11-02 | +16,900 |
| 66330 | 2022-10-26 | 9 | HOLD on 2022-11-07 | +6,800 |
| 32050 | 2022-11-30 | 10 | HOLD on 2022-12-14 | +2,100 |

This control group is the main reason immediate automatic EXIT is too aggressive.

## Persistent Deterioration And Avoidable Loss Proxy

Read-only outcome proxy from existing artifacts:

```text
loss cases after first zeroed REDUCE = 56
gross avoidable loss proxy = 380,660 JPY
median loss case = 1,725 JPY
winner damage proxy = 133,310 JPY
net immediate-exit proxy = +247,350 JPY
```

Representative loss cases:

| Symbol | First zeroed REDUCE | Zero rows | Proxy negative delta |
|---|---|---:|---:|
| 23700 | 2022-08-19 | 1 | -44,400 |
| 23230 | 2022-08-17 | 2 | -41,340 |
| 89180 | 2022-08-12 | 6 | -36,800 |
| 36640 | 2022-08-15 | 3 | -32,400 |
| 33500 | 2022-09-29 | 1 | -30,290 |
| 21340 | 2022-11-29 | 2 | -27,000 |
| 87890 | 2022-11-21 | 8 | -25,000 |
| 92540 | 2022-10-21 | 2 | -20,300 |
| 49370 | 2022-12-09 | 3 | -13,800 |

These are outcome-evaluation numbers only. They must not be used as Runtime inputs or as threshold selection evidence without a separate point-in-time validation design.

## Strength And Persistence

The observed strength evidence is descriptive:

```text
LIGHT rows = 297
MEDIUM rows = 23
STRONG rows = 24
```

Most zeroing occurs at `LIGHT`, because a 25% reduction of a one-lot position is almost always sub-lot. `MEDIUM` and `STRONG` cases exist and should be analyzed, but sample size is much smaller in this run.

The persistence evidence is more actionable than strength alone:

- 19 symbols had exactly one zeroed REDUCE row.
- 21 symbols had two rows.
- 42 symbols had three or more rows.
- 61750 had 63 rows.

This supports an escalation design that treats repeated unrepresentable REDUCE as evidence, while still requiring Strategy-owned confirmation before converting to EXIT.

## Regime Attribution

The issue appears across all observed regimes:

```text
BULL=138, RANGE=74, RECOVERY=64, BEAR=48, CORRECTION=20
```

This is not a BEAR-only or CORRECTION-only failure. Any future design should consume the canonical point-in-time market context only as one Strategy feature among others. It should not use later regime labels or outcome classifications.

## Counterfactual Alternatives

Alternative A: no escalation

```text
Safety: best
Performance: weak
Finding: preserves Phase29/Phase30 correctness but leaves repeated REDUCE pressure inert.
```

Alternative B: magnitude-only escalation

```text
Safety: weak
Performance: uncertain
Finding: target_reduce_ratio alone cannot distinguish temporary de-risk from true liquidation need.
```

Alternative C: persistence-only escalation

```text
Safety: moderate
Performance: plausible
Finding: materially better than immediate exit, but still vulnerable to false positives in recovered campaigns.
```

Alternative D: magnitude + persistence

```text
Safety: better
Performance: plausible
Finding: useful, but it still treats PM repeated pressure mostly as a mechanical signal.
```

Alternative E: persistence + existing point-in-time feature confirmation

```text
Safety: best practical candidate
Performance: best practical candidate
Finding: preferred. Use repeated unrepresentable REDUCE as a Strategy observation, then require existing PIT deterioration evidence before PM emits EXIT.
```

Preferred ranking:

```text
E > D > C > B > A
```

No numeric threshold is selected in this audit.

## Architecture Owner

REDUCE_EXIT_ESCALATION_OWNER:

```text
Strategy / Position Management
```

Reason:

- PM owns `REDUCE` versus `EXIT`.
- PC/PS/Sell Planning own allocation and executable quantity materialization, not investment-intent escalation.
- Runtime Planning maps canonical quantity deltas and preserves intent evidence.
- Submit Guard validates safety before broker writes; it is not a Strategy authority.

The right future shape is:

```text
PS/Sell Planning emits lot-unrepresentable REDUCE evidence
Runtime preserves the intentional no-order evidence
Strategy/PM consumes historical PIT persistence + existing PIT feature deterioration evidence
PM may emit EXIT on a later business date when Strategy authority says full liquidation is justified
```

This preserves Phase29/Phase30 lot safety while making repeated unrepresentable de-risk pressure visible to the correct owner.

## Relation To Phase29 / Phase30 Lot Work

This audit does not invalidate Phase29-L21T or Phase30 lot work.

The current behavior matches the accepted semantic contract:

- do not ceil sub-lot REDUCE to one lot;
- do not silently convert REDUCE to EXIT;
- do not persist hidden reduce debt;
- preserve the original PM intent;
- force fresh PM reevaluation on the next business day.

The gap is upstream Strategy semantics: PM currently lacks an explicit authority that can use repeated lot-unrepresentable REDUCE pressure plus existing PIT deterioration evidence to decide that the correct future action is `EXIT`.

## Final Recommendation

Proceed to a design phase for:

```text
PM-owned REDUCE_UNREPRESENTABLE_PERSISTENCE_EXIT_ESCALATION_AUTHORITY
```

Design constraints:

- point-in-time only;
- no future outcome, final PnL, future regime, or later classification as input;
- consume existing `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT` evidence;
- consume existing Strategy Intelligence / continuation / downside / selection evidence only if PIT and already produced by Runtime-common Strategy;
- preserve current PC/PS/Sell Planning lot rounding;
- preserve Runtime Planning no-order observability for non-escalated REDUCE;
- no immediate blind EXIT on first zeroed REDUCE;
- no threshold implementation from this report.

Performance priority:

```text
HIGH, but design-first.
```

This is material enough to prioritize as a focused Strategy semantics candidate before broad C0 mutation work, but not enough to justify mutating Runtime or lot contracts directly.
