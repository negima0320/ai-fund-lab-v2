# Phase24-HX Opportunity Ranking Semantics and Top-Rank Selection Trace Audit

## Primary Judgment

`PHASE24_HX_RANKING_CONSUMER_ALIGNMENT_DEFECT_CONFIRMED`

The `opportunity_buy_rank` generator is understood and is not itself judged defective in this audit. Rank is assigned from `expected_edge_score` descending with deterministic `code` tie-break, and the runtime opportunity artifact copies `expected_return = expected_edge_score`.

However, the downstream Strategy adapter used by Portfolio Construction can consume `candidate_rank` before `buy_rank` for opportunity rows. This makes `portfolio_construction.input_opportunity_rank` diverge from the canonical `opportunity_buy_rank`. The observed Rank 4 selections are partly explainable by existing holdings and sizing constraints, but a ranking-consumer alignment defect is confirmed and must be repaired before performance policy changes.

No code, configuration, threshold, design, roadmap, model, Runtime, fetch, broker write, or Strategy regeneration was performed.

## Scope

Audited run:

```text
runtime-test-historical-extended-smoke-20260731T212018566855Z
profile = historical-extended-smoke
period = 2022-07-01 to 2022-07-29
business_days = 20
BUY executions = 12
```

Evidence root:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T212018566855Z
```

Generated HX evidence:

```text
reports/phase24_hx_opportunity_ranking_semantics_and_top_rank_selection_trace_audit/
```

## Ranking Semantics

| Item | Judgment |
| --- | --- |
| Ranking producer | Runtime v2 BUY AI Producer using `opportunity_ai.inference.build_inference_output` |
| Ranking function | model score -> `expected_edge_score` -> `buy_rank` |
| Ranking input universe | `CandidateTop50_single_business_day` |
| Sort key | `expected_edge_score`, then `code` |
| Sort direction | `expected_edge_score DESC`, `code ASC` |
| Tie-break | `rank(method="first", ascending=False)` after deterministic sort |
| Missing treatment | required finite score/rank fields; invalid materialization is not accepted |
| Eligibility timing | `AFTER_RANKING` |
| Rank uniqueness | `YES` |
| `expected_return` | copied from `expected_edge_score` in runtime artifact |

Code evidence:

- `src/ai_fund_lab_v2/opportunity_ai/inference.py:317`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py:980`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py:828`

## Selection Order Contract

Observed contract:

```text
Pattern C:
ranking and portfolio scoring/selection are separate
```

Top-rank priority contract:

```text
ADVISORY
```

There is no confirmed contract that Rank 1 to Rank N must be bought in strict order. Portfolio Construction reconciles current positions, orders opportunity rows through its adapter, applies target-member capacity, then Position Sizing and Runtime Planning decide executable quantity.

Confirmed gap:

```text
strategy.shadow_runtime._candidate_downstream_rows
uses candidate_rank before buy_rank even when kind == opportunity
```

This causes Portfolio Construction embedded lineage to report an `input_opportunity_rank` that can differ from canonical `opportunity_buy_rank`.

## Focus Date Results

| Date | Rank 1 | Rank 1 reason | Rank 2 | Rank 2 reason | Rank 3 | Rank 3 reason | Rank 4 | Rank 4 outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022-07-15 | 94320 | already held | 79010 | lot/min-notional not viable | 17430 | lot/min-notional not viable | 23880 | BUY executed |
| 2022-07-21 | 94320 | already held | 17430 | lot/min-notional not viable | 23880 | already held | 79010 | not BUY eligible |
| 2022-07-25 | 94320 | already held | 23880 | already held | 17430 | lot/min-notional not viable | 66590 | pending generated, not BUY executed |
| 2022-07-26 | 94320 | already held | 23880 | BUY executed as ADD/PM path | 17430 | lot/min-notional not viable | 66590 | BUY executed |

Direct Rank 4 cause:

```text
Rank 4 became selected/executable after higher ranks were already held/current-position reconciled
and Rank 3 failed Position Sizing minimum-notional / quantity viability.
```

But because Portfolio Construction rank lineage can diverge from canonical `opportunity_buy_rank`, this is not closed as a clean expected-by-design result.

## Score Gap

| Date | Rank1 edge | Rank4 edge | Rank1 - Rank4 | Rank4 / Rank1 |
| --- | ---: | ---: | ---: | ---: |
| 2022-07-15 | 0.38674146 | 0.13997306 | 0.24676840 | 0.36192928 |
| 2022-07-21 | 0.30412144 | -0.03857940 | 0.34270084 | -0.12685525 |
| 2022-07-25 | 0.28319307 | 0.01211470 | 0.27107837 | 0.04277894 |
| 2022-07-26 | 0.26680734 | 0.01231113 | 0.25449621 | 0.04614240 |

For 2022-07-25 and 2022-07-26, Rank 4 `66590` had a materially lower score than Rank 1 and Rank 3. This is a performance policy concern, but not evidence by itself that the day-of decision used future information or that the ranking generator was inverted.

## 66590 Campaign Trace

| Entry date | Rank | Expected edge | Classification | Quantity | Entry | Exit | Realized PnL | Total PnL |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: |
| 2022-07-13 | 6 | 0.00310574 | BUY_NEW | 1000 | 145.0 | 2022-07-15 @ 122.0 | -23000.0 | -23000.0 |
| 2022-07-19 | 7 | 0.01983658 | RE_ENTRY | 1400 | 122.0 | 2022-07-21 @ 111.0 | -13300.0 | -13300.0 |
| 2022-07-25 | 4 | 0.01211470 | PLANNED_NOT_EXECUTED | 1600 | NOT_MATERIALIZED | NOT_MATERIALIZED | NOT_MATERIALIZED | NOT_MATERIALIZED |
| 2022-07-26 | 4 | 0.01231113 | RE_ENTRY | 1600 | 103.0 | 2022-07-28 @ 103.0 | 0.0 | 900.0 |

`66590` selection judgment:

```text
PERFORMANCE_POLICY_GAP_WITH_CONSUMER_ALIGNMENT_DEFECT_CONTEXT
```

The symbol was repeatedly selected or planned at low edge/rank. The correct next step is not to change Eligibility using hindsight, but to repair rank-consumer lineage first, then evaluate low-edge re-entry policy as a one-hypothesis/one-change experiment.

## Judgments

| Component | Judgment |
| --- | --- |
| Ranking generation | `EXPECTED_BY_DESIGN` |
| Ranking consumer alignment | `IMPLEMENTATION_DEFECT_OR_CONTRACT_GAP` |
| Portfolio Construction | `RANKING_CONSUMER_ALIGNMENT_DEFECT_CONFIRMED` |
| Position Sizing | `EXPECTED_BY_DESIGN` |
| Runtime Planning | `EXPECTED_BY_DESIGN_WITH_OBSERVABILITY_GAP` |
| Pending / Submit trace | `OBSERVABILITY_GAP` |
| 66590 selection quality | `PERFORMANCE_POLICY_GAP` |

## Observability Gaps

Confirmed:

- Portfolio Construction `input_opportunity_rank` can reflect adapter `candidate_rank`, not canonical `opportunity_buy_rank`.
- `planning_evidence.lineage` and saved `strategy/runtime_planning.json` can disagree for the same date/symbol.
- Daily pending snapshots are not preserved enough to fully explain 2022-07-25 pending generated but not submitted.
- Campaign events do not preserve stable `order_plan_item_id`, `pending_item_id`, or `source_decision_id`.

These gaps are not the same as Strategy performance defects, but the rank-consumer alignment issue can affect selection and should be repaired before policy tuning.

## Implementation Required

```text
YES
```

Required implementation is for ranking consumer alignment and observability, not for changing Ranking scores, Eligibility thresholds, Position Sizing, PM, or re-entry policy in this task.

## Performance Improvement Target

After the alignment repair:

```text
Low-edge re-entry policy and repeated symbol selection
```

must be evaluated under Phase24 one-hypothesis / one-change rules.

## Recommended Next Task

```text
Phase24-HY Ranking Consumer Alignment and Portfolio Construction Rank Authority Repair Contract
```

