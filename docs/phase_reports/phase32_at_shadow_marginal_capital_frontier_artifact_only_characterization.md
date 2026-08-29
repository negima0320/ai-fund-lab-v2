# Phase32-AT - Shadow Marginal Capital Frontier Artifact-Only Characterization

## Executive Summary

Scope: READ-ONLY / artifact-only characterization of the Phase32-AS shadow implementation:

```text
canonical_marginal_capital_frontier.v1
```

Target run:

```text
runtime-test-historical-extended-smoke-20260827T093649849074Z
```

Coverage observed during AT:

```text
2022-10-03 through 2024-01-15
315 completed strategy days with portfolio_construction.json and position_sizing.json
```

AT generated the shadow frontier in memory only. No shadow artifact was written into the run directory, and no production target weight, Position Sizing, Runtime Planning, Pending, Orders, Execution, Safety, REDUCE, EXIT, Cash, fresh-run, resume, replay, or backtest path was changed.

Primary result:

```text
The AS frontier is semantically useful for explaining the missing ADD target-gap layer.
It materializes NEW, REENTRY, ADD next-lot, and Cash on one common shadow frontier.
It also reveals a shadow source-adapter readiness issue: broad day materialization must resolve real decision-time Cash from portfolio_policy / valuation artifacts, not only top-level PC.
```

With decision-time Cash supplied from existing `portfolio_policy.json` / valuation artifacts, AT characterized:

| Metric | Value |
| --- | ---: |
| In-memory shadow rows characterized | 15,081 |
| Days characterized | 315 |
| Days passing non-production consumer guard | 315 |
| Days with NEW + ADD + Cash common frontier | 294 |
| ADD next-lot candidates | 1,047 |
| Days with ADD next-lot candidates | 294 |
| Days with ADD lot #2/#3 candidates | 294 |
| Shadow ADD winner days | 5 |
| Shadow NEW winner days | 145 |
| Shadow REENTRY winner days | 165 |
| Shadow Cash winner days | 0 |

Interpretation:

```text
The shadow layer changes observability materially.
It does not justify production activation yet.
```

## Required Inputs

Read and used:

- `docs/phase_reports/phase32_as_shadow_marginal_capital_frontier_implementation.md`
- `docs/phase_reports/phase32_aq_add_scarcity_marginal_capital_value_target_gap_root_architecture_audit.md`
- `docs/phase_reports/phase32_ap_add_vs_reduce_capital_response_asymmetry_deep_audit.md`
- `src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T093649849074Z`

Run artifacts read per day where available:

- `strategy/portfolio_construction.json`
- `strategy/position_sizing.json`
- `strategy/runtime_planning.json`
- `strategy/portfolio_policy.json`
- `current_valuation_refresh/valuation_projection.json`
- `current_valuation_refresh/safety_authority_decision.json`
- `execution/fills.json`

No Historical outcome, future return, future winner status, or later PnL was used to score, tune, or select frontier parameters.

## Method

AT called:

```text
build_canonical_marginal_capital_frontier_payload()
```

in memory for each completed strategy day. The characterization script supplied existing decision-time Cash evidence from:

- `strategy/portfolio_policy.json#current_cash_summary`
- `strategy/portfolio_policy.json#portfolio_policy_allocation_authority.cash_context`
- `current_valuation_refresh/valuation_projection.json`

This matters because a first pass with no cash resolver made nearly every security candidate fail as `INFEASIBLE_INSUFFICIENT_CASH` and Cash won every day. With existing decision-time Cash supplied, the frontier became informative.

This is not a production behavior defect because no production consumer uses the shadow artifact. It is a shadow materialization-readiness finding:

```text
future broad shadow materialization should read portfolio_policy / valuation Cash evidence explicitly.
```

## Candidate Counts

| Semantic type | Candidate rows |
| --- | ---: |
| `NEW_FIRST_LOT` | 5,407 |
| `REENTRY_FIRST_LOT` | 8,312 |
| `ADD_NEXT_LOT` | 1,047 |
| `CASH_OPTIONALITY` | 315 |
| Total | 15,081 |

ADD next-lot observations:

| Metric | Value |
| --- | ---: |
| ADD next-lot candidate rows | 1,047 |
| Days with any ADD next-lot candidate | 294 |
| Days with ADD lot #2 / #3 generated | 294 |
| Shadow multi-lot ADD candidate observed | Yes |
| Shadow ADD winner days | 5 |

The important distinction:

```text
multi-lot ADD candidate surface exists in shadow,
but accepted shadow ADD winners remain rare under v1 structured ordering.
```

## Dispositions

| Semantic type | Disposition | Count |
| --- | --- | ---: |
| `ADD_NEXT_LOT` | `SHADOW_WINNER` | 5 |
| `ADD_NEXT_LOT` | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 913 |
| `ADD_NEXT_LOT` | `INFEASIBLE_CAP_BLOCKED` | 107 |
| `ADD_NEXT_LOT` | `INFEASIBLE_INSUFFICIENT_CASH` | 22 |
| `NEW_FIRST_LOT` | `SHADOW_WINNER` | 145 |
| `NEW_FIRST_LOT` | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 3,906 |
| `NEW_FIRST_LOT` | `INFEASIBLE_CAP_BLOCKED` | 687 |
| `NEW_FIRST_LOT` | `INFEASIBLE_INSUFFICIENT_CASH` | 669 |
| `REENTRY_FIRST_LOT` | `SHADOW_WINNER` | 165 |
| `REENTRY_FIRST_LOT` | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 7,694 |
| `REENTRY_FIRST_LOT` | `INFEASIBLE_CAP_BLOCKED` | 73 |
| `REENTRY_FIRST_LOT` | `INFEASIBLE_INSUFFICIENT_CASH` | 380 |
| `CASH_OPTIONALITY` | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 315 |

Winner distribution:

| Winner type | Days |
| --- | ---: |
| `NEW_FIRST_LOT` | 145 |
| `REENTRY_FIRST_LOT` | 165 |
| `ADD_NEXT_LOT` | 5 |
| `CASH_OPTIONALITY` | 0 |

Runner-up distribution:

| Runner-up type | Days |
| --- | ---: |
| `NEW_FIRST_LOT` | 125 |
| `REENTRY_FIRST_LOT` | 184 |
| `ADD_NEXT_LOT` | 6 |

Top winner / runner-up patterns:

| Winner -> runner-up | Days |
| --- | ---: |
| `REENTRY_FIRST_LOT -> REENTRY_FIRST_LOT` | 124 |
| `NEW_FIRST_LOT -> NEW_FIRST_LOT` | 84 |
| `NEW_FIRST_LOT -> REENTRY_FIRST_LOT` | 60 |
| `REENTRY_FIRST_LOT -> NEW_FIRST_LOT` | 41 |
| `ADD_NEXT_LOT -> ADD_NEXT_LOT` | 5 |
| `NEW_FIRST_LOT -> ADD_NEXT_LOT` | 1 |

## Guardrails

Block counts:

| Block / infeasibility | Count |
| --- | ---: |
| `INFEASIBLE_CAP_BLOCKED` | 867 |
| `INFEASIBLE_INSUFFICIENT_CASH` | 1,071 |
| Safety blocked | 0 |
| Risk Pacing blocked | 0 |
| Lot infeasible | 0 |

Guardrail interpretation:

```text
Guardrails are preserved in the shadow artifact.
Cap and Cash constraints remain visible and block candidates.
Safety / Risk Pacing did not produce blocked candidates in the characterized artifacts.
```

The artifact preserves desirability separately from infeasibility. For example, ADD / NEW / REENTRY rows can be attractive enough to exist but still receive `INFEASIBLE_CAP_BLOCKED` or `INFEASIBLE_INSUFFICIENT_CASH`.

## Production vs Shadow Divergence

AQ found the production ADD bottleneck:

```text
97.06% of ADD rows: target_minus_current = 0
96.47% of ADD rows: accepted_incremental_weight = 0
```

AT observed:

| Divergence measure | Value |
| --- | ---: |
| Days with production ADD zero target gap and shadow ADD candidates | 281 |
| Shadow ADD candidate rows on ADD days | 1,047 |
| Shadow ADD winner days where production ADD gap was zero | 1 |
| Production guard days still non-authoritative | 315 / 315 |

Winner type on production ADD-zero-gap days:

| Shadow winner type | Days |
| --- | ---: |
| `NEW_FIRST_LOT` | 123 |
| `REENTRY_FIRST_LOT` | 157 |
| `ADD_NEXT_LOT` | 1 |

Judgment:

```text
PRODUCTION_SHADOW_DIVERGENCE = MATERIAL
```

Reason: shadow candidate representation materially changes observability by creating explicit ADD next-lot candidates and cross-type alternatives on days where production target gap is zero. However, accepted shadow ADD projection divergence is limited: only one production-zero-gap day had an ADD shadow winner under v1.

## ADD And NEW Same-Day Competition

AT observed same-day ADD and NEW frontier presence on 294 days.

Representative rows:

| Date | Production ADD rows | NEW rows | Shadow ADD next-lot rows | Shadow winner | Runner-up | Cash |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| 2022-10-05 | 1 | 43 | 3 | `NEW_FIRST_LOT 94320` | `NEW_FIRST_LOT` | JPY 222,620 |
| 2022-10-06 | 1 | 42 | 3 | `ADD_NEXT_LOT 94340` | `ADD_NEXT_LOT` | JPY 80,840 |
| 2022-10-07 | 2 | 40 | 6 | `NEW_FIRST_LOT 66630` | `NEW_FIRST_LOT` | JPY 79,440 |
| 2022-10-11 | 1 | 39 | 3 | `ADD_NEXT_LOT 94340` | `ADD_NEXT_LOT` | JPY 338,340 |
| 2022-10-12 | 2 | 41 | 6 | `ADD_NEXT_LOT 94320` | `ADD_NEXT_LOT` | JPY 335,080 |
| 2022-10-13 | 1 | 42 | 3 | `ADD_NEXT_LOT 94340` | `ADD_NEXT_LOT` | JPY 719,260 |
| 2022-10-24 | 1 | 39 | 3 | `REENTRY_FIRST_LOT 66190` | `NEW_FIRST_LOT` | JPY 431,060 |

Interpretation:

```text
The common frontier exists and is explainable.
ADD can win, NEW can win, and REENTRY can win on days with ADD present.
Cash remains visible.
```

## Persistent 94320 Trace

`94320` is the clearest persistent ADD campaign family from AQ/AP.

Early trace:

| Date | Campaign | Lot | Shadow disposition | Pre -> post qty | Pre -> post wt | Production gap | Production accepted inc | Winner |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | --- |
| 2022-10-07 | `pc-b946a79c4c1eb894-94320-0001` | 1 | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 200 -> 300 | 2.976% -> 4.456% | 0.000% | 0.000% | `NEW_FIRST_LOT 66630` |
| 2022-10-07 | same | 2 | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 300 -> 400 | 4.456% -> 5.936% | 0.000% | 0.000% | `NEW_FIRST_LOT 66630` |
| 2022-10-07 | same | 3 | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 400 -> 500 | 5.936% -> 7.416% | 0.000% | 0.000% | `NEW_FIRST_LOT 66630` |
| 2022-10-12 | `pc-b946a79c4c1eb894-94320-0001` | 1 | `SHADOW_WINNER` | 200 -> 300 | 3.068% -> 4.582% | 1.515% | 2.176% | `ADD_NEXT_LOT 94320` |
| 2022-10-12 | same | 2 | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 300 -> 400 | 4.582% -> 6.097% | 1.515% | 2.176% | `ADD_NEXT_LOT 94320` |
| 2022-10-12 | same | 3 | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 400 -> 500 | 6.097% -> 7.611% | 1.515% | 2.176% | `ADD_NEXT_LOT 94320` |
| 2022-10-24 | same | 1 | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 300 -> 400 | 4.682% -> 6.226% | 0.000% | 0.000% | `REENTRY_FIRST_LOT 66190` |

Late trace for persistent campaign `pc-091f6fd4e6c166be-94320-0002`:

| Date | Lot | Shadow disposition | Pre -> post qty | Pre -> post wt | Production gap | Winner |
| --- | ---: | --- | --- | --- | ---: | --- |
| 2024-01-10 | 1 | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 200 -> 300 | 2.043% -> 3.075% | 0.000% | `REENTRY_FIRST_LOT 94340` |
| 2024-01-10 | 2 | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 300 -> 400 | 3.075% -> 4.106% | 0.000% | `REENTRY_FIRST_LOT 94340` |
| 2024-01-10 | 3 | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 400 -> 500 | 4.106% -> 5.138% | 0.000% | `REENTRY_FIRST_LOT 94340` |
| 2024-01-15 | 1 | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 200 -> 300 | 2.090% -> 3.167% | 0.000% | `REENTRY_FIRST_LOT 83060` |
| 2024-01-15 | 2 | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 300 -> 400 | 3.167% -> 4.245% | 0.000% | `REENTRY_FIRST_LOT 83060` |
| 2024-01-15 | 3 | `SHADOW_REJECTED_STRONGER_ALTERNATIVE` | 400 -> 500 | 4.245% -> 5.322% | 0.000% | `REENTRY_FIRST_LOT 83060` |

94320 interpretation:

```text
The shadow frontier exposes repeated ADD next-lot candidates even when production target gap is zero.
Most 94320 lots lose to NEW or REENTRY under v1; on 2022-10-12 lot #1 wins but later lots lose.
This is exactly the AR starter / confirmation / scale shape.
```

## Released-Capital Shadow Destination

AT used same-day SELL fills as an artifact-only proxy for released-capital days. The run has 257 days with SELL fills in the characterized coverage.

Shadow winner destination on those days:

| Destination | Days |
| --- | ---: |
| `NEW_FIRST_LOT` | 121 |
| `REENTRY_FIRST_LOT` | 132 |
| `ADD_NEXT_LOT` | 4 |
| `CASH_OPTIONALITY` | 0 |

Representative released-capital days:

| Date | SELL fill count | Shadow destination | Winner | Runner-up |
| --- | ---: | --- | --- | --- |
| 2022-10-04 | 3 | `NEW_FIRST_LOT` | 94320 | `NEW_FIRST_LOT` |
| 2022-10-11 | 3 | `ADD_NEXT_LOT` | 94340 | `ADD_NEXT_LOT` |
| 2022-10-12 | 1 | `ADD_NEXT_LOT` | 94320 | `ADD_NEXT_LOT` |
| 2022-10-24 | 3 | `REENTRY_FIRST_LOT` | 66190 | `NEW_FIRST_LOT` |
| 2022-10-27 | 2 | `NEW_FIRST_LOT` | 62660 | `NEW_FIRST_LOT` |

Interpretation:

```text
AP's production observation remains directionally visible: released capital rarely points to ADD under v1 shadow comparison.
AT improves explainability by showing whether the same-day frontier preferred NEW, REENTRY, ADD, or Cash.
```

## High-Position-Count / One-Lot-Heavy Days

AT identified 193 high-buy-count or one-lot-heavy days from production runtime planning artifacts.

Shadow winner destination on those days:

| Destination | Days |
| --- | ---: |
| `NEW_FIRST_LOT` | 102 |
| `REENTRY_FIRST_LOT` | 89 |
| `ADD_NEXT_LOT` | 2 |
| `CASH_OPTIONALITY` | 0 |

Representative days:

| Date | Production BUY plans | One-lot BUY plans | Shadow winner | ADD next-lot rows |
| --- | ---: | ---: | --- | ---: |
| 2022-10-03 | 9 | 5 | `NEW_FIRST_LOT 94320` | 0 |
| 2022-10-04 | 7 | 6 | `NEW_FIRST_LOT 94320` | 0 |
| 2022-10-05 | 6 | 2 | `NEW_FIRST_LOT 94320` | 3 |
| 2022-10-06 | 4 | 4 | `ADD_NEXT_LOT 94340` | 3 |
| 2022-10-13 | 6 | 5 | `ADD_NEXT_LOT 94340` | 3 |
| 2022-10-24 | 8 | 7 | `REENTRY_FIRST_LOT 66190` | 3 |

Interpretation:

```text
One-lot-heavy production days are not invisible to the shadow frontier.
The frontier provides same-day explanation for whether breadth, re-entry, ADD scale, or Cash would be preferred.
```

## Sideways / Cautious Period Characterization

Using available policy text labels such as `BALANCED`, `CAUTIOUS`, `RANGE`, and `PRESERVE_OPTIONALITY`, all 315 characterized days carried at least one cautious/range/cash-related policy signal.

Shadow winner destination:

| Destination | Days |
| --- | ---: |
| `NEW_FIRST_LOT` | 145 |
| `REENTRY_FIRST_LOT` | 165 |
| `ADD_NEXT_LOT` | 5 |
| `CASH_OPTIONALITY` | 0 |

Interpretation:

```text
The v1 structured ordering currently makes Cash observable but not competitive enough to win when security candidates are feasible.
This is acceptable for characterization, but not sufficient for production activation.
```

Cash first-class candidate presence is accepted. Cash preference calibration is unresolved and must not be tuned from future return.

## Explainability

Accepted:

- each candidate records why it exists through semantic type and lineage;
- desirability and feasibility are separate sections;
- cap/Cash blocks are explicit;
- winner and strongest alternative are available;
- Cash comparison is recorded for non-Cash candidates;
- all 315 days passed the shadow non-production consumer guard.

Limitations:

- no scalar cardinal value exists, by design;
- broad day helper needs a stronger built-in Cash source resolver before unattended large-scale materialization;
- current v1 ordering often selects REENTRY/NEW from existing classification/rank semantics and may understate Cash preference;
- released-capital attribution uses same-day SELL fill presence as a proxy, not a dedicated released-capital artifact.

Judgment:

```text
EXPLAINABILITY_ACCEPTED = PARTIAL
```

The artifact is explainable enough for shadow characterization, not enough for production authority.

## Production Boundary

Verified in-memory payloads:

| Boundary | Result |
| --- | --- |
| `production_consumer_count` | 0 |
| `feeds_position_sizing` | false |
| `feeds_runtime_planning` | false |
| `feeds_pending` | false |
| `feeds_orders` | false |
| `feeds_execution` | false |
| `feeds_safety_authority` | false |
| `production_target_weight_changed` | false |
| `production_behavior_changed` | false |

No shadow JSON was written into:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T093649849074Z
```

## Recommendation

Production activation is not ready.

Recommended next step:

```text
Phase32-AU - Shadow Frontier Cash Source Resolver + Artifact Materialization Readiness Repair
```

AU should remain shadow-only. It should teach the AS day-level materializer to load decision-time Cash from `portfolio_policy.json` / valuation artifacts and add focused tests proving broad materialization does not collapse security candidates into false `INFEASIBLE_INSUFFICIENT_CASH`. It should not change target weights, PS, Runtime, Pending, Orders, Execution, Safety, REDUCE, EXIT, Cash policy, or thresholds.

## Final Judgments

```text
PHASE32_AT_SHADOW_ROWS_MATERIALIZED = 15081_IN_MEMORY_ONLY
PHASE32_AT_ADD_NEXT_LOT_OBSERVED = YES
PHASE32_AT_MULTI_LOT_ADD_SHADOW_OBSERVED = YES
PHASE32_AT_NEW_ADD_COMMON_FRONTIER_OBSERVED = YES
PHASE32_AT_CASH_FIRST_CLASS_OBSERVED = YES

PHASE32_AT_PRODUCTION_SHADOW_DIVERGENCE = MATERIAL
PHASE32_AT_GUARDRAILS_PRESERVED = YES
PHASE32_AT_EXPLAINABILITY_ACCEPTED = PARTIAL
PHASE32_AT_SHADOW_DESIGN_SEMANTICALLY_USEFUL = YES
PHASE32_AT_PRODUCTION_ACTIVATION_READY = NO
PHASE32_AT_LONG_RUN_CONTINUE = YES
PHASE32_AT_NEXT_STEP = Phase32-AU - Shadow Frontier Cash Source Resolver + Artifact Materialization Readiness Repair
```
