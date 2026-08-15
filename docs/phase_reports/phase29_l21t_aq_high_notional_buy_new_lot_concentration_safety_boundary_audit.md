# Phase29-L21T-AQ - High-Notional BUY_NEW Lot / Concentration / Safety Boundary Audit

## Primary Judgment

`MULTI_CAUSAL_BOUNDARY_GAP_CONFIRMED`

The three audited entries are correctly classified as `BUY_NEW`, and the
high-notional fills are real 100-share fills.  L19 lot-aware authority is
working on its reference-price basis: one lot exceeds the Strategy single-name
cap `18%`, but reference one-lot notional is inside the Safety hard cap `25%`.

However, `78780` on `2022-08-24` and `2022-08-31` filled above the reference
price.  On actual fill notional divided by sizing equity, both exceed the
Safety hard cap.  This is not a performance defect and not a BUY semantic
classification defect.  It is a boundary gap between reference-price L19
Safety feasibility and actual execution-price notional.

This was a read-only Phase29 audit.  Phase30 was not entered.

## Scope

| Field | Value |
| --- | --- |
| Task ID | `Phase29-L21T-AQ` |
| Target Run | `runtime-test-historical-extended-smoke-20260814T054658313415Z` |
| Runtime mutation | `NO` |
| Strategy / Runtime / Config / Model / Threshold changed | `NO` |
| fresh-run / resume / replay / recovery / long Historical | `NO` |

## Design Baseline

Strategy and Safety caps are separate authorities:

```text
Strategy single-name cap = 0.18
Safety hard cap          = 0.25
```

L19 permits a one-lot Strategy soft-cap overshoot only when the one lot is
inside the independent Safety hard cap.  If one lot exceeds Safety hard cap,
the design is fail-closed.

The audited evidence confirms PC/PS use this reference-price boundary:

```text
boundary_classification =
DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX
```

## Entry Trace

| Entry | Semantic | Prior Holding | Campaign | Ref Price | Fill Price | Qty | Ref One-Lot Notional | Actual Notional |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `2022-08-24 78780` | `BUY_NEW` | `NO` | `pc-621096eda48ce715-78780-0001` | `2,420` | `2,860` | `100` | `242,000` | `286,000` |
| `2022-08-31 78780` | `BUY_NEW` | `NO` | `pc-621096eda48ce715-78780-0002` | `2,285` | `2,525` | `100` | `228,500` | `252,500` |
| `2022-09-06 53800` | `BUY_NEW` | `NO` | `pc-621096eda48ce715-53800-0001` | `2,020` | `2,250` | `100` | `202,000` | `225,000` |

`78780` on `2022-08-31` is a separate new campaign, not ADD.  The previous
`78780` campaign was already absent before the second entry.

All three positions are absent on the next completed day in Current valuation
evidence, and campaign snapshots show the target campaigns as `CLOSED` in the
next snapshot.

## Boundary Results

| Entry | Sizing Equity | Ref One-Lot Weight | Actual Notional / Sizing Equity | EOD Position Weight | Strategy Cap | Safety Cap | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `2022-08-24 78780` | `992,770` | `24.376%` | `28.808%` | `25.673%` | `18%` | `25%` | `REFERENCE_PASS_ACTUAL_FILL_SAFETY_BREACH` |
| `2022-08-31 78780` | `966,680` | `23.638%` | `26.120%` | `24.242%` | `18%` | `25%` | `REFERENCE_PASS_ACTUAL_FILL_SAFETY_BREACH` |
| `2022-09-06 53800` | `941,260` | `21.461%` | `23.904%` | `22.294%` | `18%` | `25%` | `ONE_LOT_OVERSHOOT_SAFETY_PRESERVED` |

For all three:

| Field | Value |
| --- | --- |
| `maximum_strategy_feasible_lots` | `0` |
| `maximum_safety_feasible_lots` | `1` |
| `one_lot_fallback_applied` | `true` |
| `strategy_cap_overshoot_applied` | `true` |
| `lot_overshoot_reason` | `ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP` |

The important distinction is basis:

- reference-price L19 Safety feasibility: `PASS` for all three;
- actual fill notional Safety feasibility: `FAIL` for both `78780` entries;
- actual fill notional Safety feasibility: `PASS` for `53800`.

## PC / PS / Runtime / Execution

| Entry | Requested BUY_NEW Weight | Accepted BUY_NEW Weight | Lot-Aware Weight | Planned Qty | Symbol-Level Submitted Qty | Filled Qty |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| `2022-08-24 78780` | `2.5641%` | `2.5641%` | `24.3762%` | `100` | `NOT_RETAINED_ORDER_DETAIL_OPTIONAL_MISSING` | `100` |
| `2022-08-31 78780` | `2.5641%` | `2.5641%` | `23.6376%` | `100` | `NOT_RETAINED_ORDER_DETAIL_OPTIONAL_MISSING` | `100` |
| `2022-09-06 53800` | `2.3256%` | `2.3256%` | `21.4606%` | `100` | `NOT_RETAINED_ORDER_DETAIL_OPTIONAL_MISSING` | `100` |

Execution fill evidence confirms:

```text
actual_notional = actual_fill_price * filled_quantity
```

No execution notional attribution error was found.

## Required Questions

| Question | Answer |
| --- | --- |
| A. 78780 2022-08-24 is one BUY_NEW fill? | `YES` |
| B. 78780 2022-08-31 is separate campaign / REENTRY / ADD? | `Separate BUY_NEW campaign; not ADD` |
| C. 53800 2022-09-06 is one BUY_NEW fill? | `YES` |
| D. Portfolio equity ratio? | `28.808%`, `26.120%`, `23.904%` on actual fill notional / sizing equity |
| E. Strategy cap overshoot explicitly allowed? | `YES`, as one-lot Strategy soft-cap overshoot within reference Safety cap |
| F. Safety cap exceeded why passed? | `Reference one-lot notional was <=25%; actual fill price later exceeded that basis for 78780` |
| G. One lot > Strategy cap but <= Safety cap allowed? | `YES` |
| H. One lot > Safety hard cap fail-closed? | `YES by L19 design/code path; not exercised by these three entries` |
| I. L19 separation working in actual runtime? | `PARTIAL`: PC/PS reference-basis authority works; execution-price safety boundary gap remains |

## Classification

| Category | Judgment |
| --- | --- |
| Designed lot overshoot | `YES`, reference basis |
| Strategy cap overshoot allowed but Safety preserved | `YES` for reference basis; `NO` for actual fill basis on 78780 |
| Safety cap violation | `YES`, actual fill basis for `78780` on `2022-08-24` and `2022-08-31` |
| Artifact interpretation error | `NO` |
| BUY_NEW / ADD / REENTRY classification error | `NO` |
| Execution notional attribution error | `NO` |

## Artifacts

```text
reports/phase29_l21t_aq_high_notional_buy_new_lot_concentration_safety_boundary_audit/summary.json
reports/phase29_l21t_aq_high_notional_buy_new_lot_concentration_safety_boundary_audit/per_entry.csv
```

## Next Step

Create a separate repair/design task for execution-price concentration safety:

```text
Pre-submit / pre-execution concentration feasibility should evaluate MARKET BUY
reservation or execution price authority against Safety hard cap, not only
reference one-lot notional.
```

Do not classify the poor forward performance itself as the defect.  The defect
is the safety boundary basis mismatch for high-price one-lot BUY_NEW fills.
