# Phase29-C Lot / Minimum-Notional Capital Conversion Root Cause Audit

Status:

```text
COMPLETE
READ_ONLY ROOT CAUSE AUDIT
```

Primary Judgment:

```text
PHASE29_C_LOT_MINIMUM_NOTIONAL_CAPITAL_CONVERSION_ROOT_CAUSE_MULTI_CAUSAL_CONFIRMED
```

## 1. Scope

This audit used only existing artifacts from the completed post-D61 historical
smoke run:

```text
runtime-test-historical-smoke-20260809T065457596902Z
```

No production code, strategy logic, runtime state, schema, model, Accepted
Generation, Pending, Registry, or configuration was changed. No fresh,
resume, 100BD, or historical execution was run.

Evidence was read from:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260809T065457596902Z/daily/*/strategy/portfolio_construction_draft.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260809T065457596902Z/daily/*/strategy/position_sizing_preflight.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260809T065457596902Z/daily/*/strategy/portfolio_construction.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260809T065457596902Z/daily/*/strategy/position_sizing.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260809T065457596902Z/daily/*/current_valuation_refresh/valuation_projection.json
```

Generated audit evidence:

```text
reports/phase29_c_lot_minimum_notional_capital_conversion_root_cause_audit/root_cause_summary.json
reports/phase29_c_lot_minimum_notional_capital_conversion_root_cause_audit/add_zero_conversion_cases.csv
reports/phase29_c_lot_minimum_notional_capital_conversion_root_cause_audit/buy_new_zero_conversion_cases.csv
reports/phase29_c_lot_minimum_notional_capital_conversion_root_cause_audit/zero_conversion_bucket_summary.json
reports/phase29_c_lot_minimum_notional_capital_conversion_root_cause_audit/lot_feasibility_distribution.json
reports/phase29_c_lot_minimum_notional_capital_conversion_root_cause_audit/capital_recycling_audit.json
reports/phase29_c_lot_minimum_notional_capital_conversion_root_cause_audit/concentration_headroom_audit.json
reports/phase29_c_lot_minimum_notional_capital_conversion_root_cause_audit/daily_unused_deployable_capital.csv
reports/phase29_c_lot_minimum_notional_capital_conversion_root_cause_audit/allocation_competition_trace.csv
```

## 2. Primary Root Cause

The remaining capital conversion bottleneck is multi-causal, but the center is:

```text
Continuous target-weight allocation on roughly 1M JPY capital creates sub-lot
and over-cap allocation intents. Lot-aware final conversion then legitimately
zeros many intents because the minimum executable 100-share lot exceeds
single-name concentration headroom or remaining deployment budget. Residual
cash is preserved rather than fully recycled into later or larger feasible
allocations.
```

This is primarily an architecture/design gap plus a legitimate market/lot-size
constraint, not a confirmed production defect.

## 3. Observed Funnel

Across the 100 completed business days:

| Action | PC positive request | PC positive accept | Lot positive accept | Lot zero after positive accept | Request positive but accepted zero |
|---|---:|---:|---:|---:|---:|
| ADD | 68 | 60 | 4 | 56 | 8 |
| BUY_NEW | 155 | 102 | 29 | 73 | 53 |

The Phase29-B BUY_NEW dropout count of 126 is reproduced when measured from
positive request to final non-conversion:

```text
BUY_NEW request-positive dropout = 53 competition losses + 73 lot-aware zeroes
                                = 126
```

## 4. Root Cause Buckets

Zero conversion after positive PC accept:

| Action | Bucket | Count |
|---|---|---:|
| ADD | B2_CONCENTRATION_CAP_INFEASIBLE | 52 |
| ADD | B5_CASH_RESERVATION_CONSUMED | 4 |
| BUY_NEW | B2_CONCENTRATION_CAP_INFEASIBLE | 67 |
| BUY_NEW | B5_CASH_RESERVATION_CONSUMED | 5 |
| BUY_NEW | B10_SAFETY_OR_BROKER_CONSTRAINT | 1 |

Zero conversion after positive PC request:

| Action | Bucket | Count |
|---|---|---:|
| ADD | B2_CONCENTRATION_CAP_INFEASIBLE | 52 |
| ADD | B5_CASH_RESERVATION_CONSUMED | 4 |
| ADD | B6_COMPETITION_LOSS | 8 |
| BUY_NEW | B2_CONCENTRATION_CAP_INFEASIBLE | 67 |
| BUY_NEW | B5_CASH_RESERVATION_CONSUMED | 5 |
| BUY_NEW | B6_COMPETITION_LOSS | 53 |
| BUY_NEW | B10_SAFETY_OR_BROKER_CONSTRAINT | 1 |

No B7 rounding/conversion defect, B8 target-weight contract mismatch, or B9
legacy constraint interference was confirmed from the inspected artifacts.

## 5. Lot Feasibility

Position Sizing preflight shows the structural lot mismatch directly:

| Action | Preflight rows | Lot feasible | Lot infeasible |
|---|---:|---:|---:|
| ADD | 60 | 4 | 56 |
| BUY_NEW | 102 | 18 | 84 |

ADD pre-lot deltas were typically too small for a 100-share lot:

```text
ADD median draft delta notional: 18,795.69 JPY
ADD median minimum executable weight: 0.045575
ADD median concentration headroom: 0.017673
```

BUY_NEW also shares the same mismatch, especially for higher-priced names:

```text
BUY_NEW median draft target weight: 0.107143
BUY_NEW median minimum executable weight: 0.268313
BUY_NEW one-lot-exceeds-headroom count: 80 / 155 request-positive rows
```

Important nuance: B3_REQUEST_TOO_SMALL_FOR_ONE_LOT is not the dominant terminal
bucket because the D55/D61 lot-aware path can promote a small accepted request
up to `minimum_executable_weight`. Many cases then fail at the next constraints:
the promoted 1-lot weight exceeds the 0.18 single-name cap or the remaining
lot-aware deployment budget. Economically, this is still the same 1-lot
granularity mismatch.

## 6. Capital Recycling

Capital recycling status:

```text
PARTIAL
```

Evidence:

```text
days_with_lot_skips: 78 / 100
days_with_lot_promotions: 11 / 100
total_lot_skipped_count: 129
total_lot_promoted_count: 11
days_with_unused_deployable_capital_after_lot: 96 / 100
average_unused_deployable_capital_jpy: 178,537.41
sum_unused_deployable_capital_jpy: 17,853,740.54
```

The implementation can skip infeasible high-priority rows and fund lower-ranked
feasible rows. Tests explicitly cover that behavior. However, run artifacts show
that residual deployment capacity commonly remains after skips. The current
authority preserves unallocated cash rather than performing a deeper portfolio-
level recycle/rebatch pass that can intentionally aggregate capital into fewer
lot-feasible names.

## 7. Concentration Headroom

Concentration is the largest observed terminal blocker:

```text
ADD one_lot_exceeds_headroom: 58 / 68 request-positive rows
BUY_NEW one_lot_exceeds_headroom: 80 / 155 request-positive rows
```

This does not prove the 0.18 strategy single-name cap is wrong. It proves that
with roughly 1M JPY capital and 100-share lots, a cap-respecting portfolio often
cannot express the continuous target weights that PC initially requests.

## 8. Cash Under-Deployment

The Phase29-B post-D61 run ended with average cash ratio worsening from 44.03%
to 44.71%, despite ADD request formation improving. Phase29-C explains a large
part of that gap: after PC forms positive ADD/BUY_NEW intents, lot-aware final
conversion repeatedly leaves residual deployment capacity as cash.

This does not mean opportunity shortage has no role. It means opportunity
shortage alone is not a sufficient explanation for the observed cash level.

## 9. Repair Possibility Classification

| Classification | Judgment | Reason |
|---|---|---|
| A Production Defect | NO_CONFIRMED | Observed zeroes match documented lot-aware, concentration, budget, and broker gates. |
| B Architecture/Design Gap | YES | Continuous weights are decided before discrete-lot feasibility is fully budget-aware. Residual capital is only partially recycled. |
| C Legitimate Constraint | YES_MEANINGFUL_SHARE | 100-share lots, minimum executable notional, and single-name caps genuinely make many allocations infeasible. |
| D Policy Question | YES | Repair direction requires deciding whether to concentrate more, hold more cash, widen names, reduce lot pressure, or rebatch allocations. |
| E Insufficient Evidence | LIMITED | Broker and intraday reservation details are limited, but they are not the primary observed blocker. |

## 10. Hypothesis Answers

1. D61-after problem is discrete lot conversion, not ADD request formation:
   YES. ADD PC positive accept reached 60, but only 4 became lot-positive.
2. BUY_NEW shares the same issue:
   YES. BUY_NEW PC positive accept reached 102, but 73 became lot-zero.
3. 1M JPY plus weight allocations are too granular for 100-share lots:
   YES. Median BUY_NEW minimum executable weight is 0.268313, above the 0.18 cap.
4. Unused capital from infeasible allocations is not sufficiently recycled:
   PARTIAL/YES. Recycling exists, but 96 days retained unused deployable capital.
5. Around 45% cash cannot be explained by opportunity shortage alone:
   YES. Lot conversion contributes materially.
6. Concentration cap blocks many 1-lot buys; blocking does not prove cap wrong:
   YES. It is a constraint-policy tradeoff.
7. Legacy `max_positions=5` / `max_exposure` is not primary:
   YES. No primary B9 evidence was found; Phase29-B already classified active
   fixed-5 authority as deprecated metadata only.

## 11. Recommended Repair Direction

Recommended next work should not be a narrow rounding fix. It should design a
lot-first allocation/recycling policy that explicitly chooses among:

```text
1. preserve cash when 1-lot deployment would violate concentration policy;
2. aggregate capital into fewer lot-feasible names;
3. alter single-name cap or minimum deployment policy;
4. perform a second-pass rebatch after lot skips;
5. expose "cash intentionally retained due to lot/cap infeasibility" as first-class evidence.
```

Recommended Phase29-D:

```text
Phase29-D Lot-First Capital Recycling and Concentration Policy Repair Design
```

