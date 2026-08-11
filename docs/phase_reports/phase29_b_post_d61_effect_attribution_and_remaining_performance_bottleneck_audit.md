# Phase29-B Post-D61 Effect Attribution and Remaining Performance Bottleneck Audit

## Primary Judgment

```text
PHASE29_B_POST_D61_EFFECT_ATTRIBUTION_PARTIAL_IMPROVEMENT_REMAINING_CAPITAL_GAPS
```

## Executive Answers

| Question | Answer | Evidence |
|---|---|---|
| Did Phase28-D61 solve the original ADD capital conversion problem? | PARTIAL | PM ADD propagation and positive incremental request formation improved, but executable BUY_ADD did not materially expand. |
| Did Cash / Exposure improve? | NO | Average cash ratio worsened from 44.03% to 44.71%; average exposure fell from 55.97% to 55.29%. |
| Did BUY_ADD increase? | PARTIAL | BUY_ADD fills increased from 3 to 4 and notional from 164,500 to 345,500 JPY, but Runtime BUY_ADD plans stayed 4. |
| Is Position Count behavior healthy? | PARTIAL | No fixed 5-position cap was observed; average positions fell from 4.25 to 3.90 and 1-2 position days increased from 8 to 9. |
| Can +12.34% to +13.97% be treated as D61 effect? | PARTIALLY_SUPPORTED | Return improved by 16,300 JPY, but causality is not proven; BUY_ADD notional improved while cash/exposure and re-entry worsened. |

Primary Performance Bottleneck:

```text
Lot/minimum-notional capital conversion for both ADD and BUY_NEW after PC positive/requested allocation
```

## Evidence Scope

This audit is READ_ONLY over existing run artifacts. No Production code, Strategy code, Runtime code, config, threshold, model, schema, Accepted Generation, Pending artifact, Runtime artifact, fresh-run, resume, 100BD, or long Historical command was changed or executed.

Machine-readable evidence:

- `reports/phase29_b_post_d61_effect_attribution_and_remaining_performance_bottleneck_audit/before_after_comparison.json`
- `reports/phase29_b_post_d61_effect_attribution_and_remaining_performance_bottleneck_audit/final_classification.json`
- `reports/phase29_b_post_d61_effect_attribution_and_remaining_performance_bottleneck_audit/add_target_current_collision_resolution.json`
- `reports/phase29_b_post_d61_effect_attribution_and_remaining_performance_bottleneck_audit/comparison_table.csv`
- `reports/phase29_b_post_d61_effect_attribution_and_remaining_performance_bottleneck_audit/before_daily_capital_position_series.csv`
- `reports/phase29_b_post_d61_effect_attribution_and_remaining_performance_bottleneck_audit/after_daily_capital_position_series.csv`
- `reports/phase29_b_post_d61_effect_attribution_and_remaining_performance_bottleneck_audit/before_fills.csv`
- `reports/phase29_b_post_d61_effect_attribution_and_remaining_performance_bottleneck_audit/after_fills.csv`

Important evidence caveat: local `run_state.json` for the After run is `COMPLETED` with 100 completed business days ending `2023-08-25`. The top-level `fresh_run_summary.json` still contains stale HALT metadata from `2023-05-09`. Therefore this audit uses `run_state.json` plus daily artifacts for completion/performance attribution and classifies the stale summary as observability debt.

## Run Comparison

| Metric | Before D61 | After D61 | Delta |
|---|---:|---:|---:|
| Run ID | `runtime-test-historical-smoke-20260809T010010445473Z` | `runtime-test-historical-smoke-20260809T065457596902Z` |  |
| Completed business days | 100 | 100 | 0 |
| Final equity | 1,123,400 | 1,139,700 | +16,300 |
| Return rate | +12.34% | +13.97% | +1.63pt |
| BUY executions | 24 | 25 | +1 |
| SELL executions | 35 | 27 | -8 |
| BUY notional | 2,413,150 | 2,619,850 | +206,700 |
| SELL notional | 1,987,490 | 2,198,890 | +211,400 |
| Max drawdown | -8.46% | -12.25% | worse |

The headline return improvement is real in the daily valuation artifacts, but causality is not fully proven. BUY_ADD contribution is directionally supportive, while lower churn, different SELL timing, concentration, and path effects also changed.

## Audit A/B: ADD Conversion Funnel

| Stage | Before | After | Judgment |
|---|---:|---:|---|
| PM ADD in PC artifacts | 190 | 190 | stable |
| D55-A PASS | 26 | 68 | improved in comparable artifact extraction |
| D55-A UNKNOWN / unresolved | 164 | 122 | improved but still large |
| PC ADD request positive | 26 | 190 | materially improved |
| PC positive incremental target | 26 | 60 | improved |
| PC lot-aware positive ADD | 11 | 4 | worse |
| PS positive BUY_ADD delta | 4 | 4 | unchanged |
| Runtime BUY_ADD plan | 4 | 4 | unchanged |
| BUY_ADD submit, aggregate day-level | 4 | 4 | unchanged |
| BUY_ADD fill | 3 | 4 | small improvement |
| BUY_ADD executed notional | 164,500 | 345,500 | improved |

Conversion rates:

| Conversion | Before | After |
|---|---:|---:|
| PM ADD -> D55-A PASS | 13.68% | 35.79% |
| D55-A PASS -> PC positive | 100.00% | 88.24% |
| PC positive -> PS positive | 15.38% | 6.67% |
| PS positive -> Runtime BUY_ADD | 100.00% | 100.00% |
| Runtime BUY_ADD -> Fill | 75.00% | 100.00% |
| PM ADD -> Fill | 1.58% | 2.11% |

D61-specific target/current collision evidence:

| Metric | Before | After |
|---|---:|---:|
| D55-A PASS rows with legacy desired increment zero | 0 | 44 |
| Repaired to positive actual request | 0 | 44 |
| Actual requested increment zero | 0 | 0 |
| Positive request but lot-aware zero | 15 | 64 |

Interpretation: D61 did its narrow job. Cases that would previously have collided at `base target - current_weight` now become positive ADD requests. The remaining bottleneck moved downstream: 64 of 68 After D55-A PASS rows requested positive ADD but became lot-aware/final-target zero.

## Audit C: Capital Deployment

| Metric | Before | After | Direction |
|---|---:|---:|---|
| Average cash | 463,279 | 478,749 | worse |
| Median cash | 461,280 | 493,805 | worse |
| Final cash | 574,340 | 579,040 | slightly worse |
| Average cash ratio | 44.03% | 44.71% | worse |
| Median cash ratio | 43.33% | 46.27% | worse |
| Final cash ratio | 51.13% | 50.81% | slight improvement |
| Average gross exposure | 55.97% | 55.29% | worse |
| Median gross exposure | 56.67% | 53.73% | worse |
| Max gross exposure | 76.83% | 77.95% | slight improvement |
| Final gross exposure | 48.87% | 49.19% | slight improvement |

Capital deployment was not materially improved over the full 100BD window. Final exposure improved slightly, but average and median deployment worsened.

## Audit D: Dynamic Position Count

| Metric | Before | After |
|---|---:|---:|
| Average positions | 4.25 | 3.90 |
| Median positions | 4 | 4 |
| Min positions | 2 | 2 |
| Max positions | 7 | 6 |
| Final positions | 4 | 4 |
| 0-position days | 0 | 0 |
| 1-2 position days | 8 | 9 |
| 3-5 position days | 75 | 88 |
| 6+ position days | 17 | 3 |

No evidence supports `legacy max_positions=5` as an active hard constraint. In the After run, `target_position_count_decision_authority = DEPRECATED_METADATA_ONLY` was observed on all 100 days where target weight authority exposed it, and the portfolio reached 6 positions. This is not a fixed-5 defect.

However, low-position deployment remains a performance concern: After had 9 days with 1-2 positions while 3+ positive opportunity rows existed in PC artifacts.

## Audit E: BUY_NEW Capital Allocation

| Stage | Before | After |
|---|---:|---:|
| BUY_NEW candidate rows | 145 | 155 |
| PC requested BUY_NEW positive | 145 | 155 |
| PC accepted BUY_NEW positive | 115 | 102 |
| PC lot-aware BUY_NEW positive | 31 | 29 |
| PS positive BUY_NEW | 25 | 24 |
| Runtime BUY_NEW | 25 | 24 |
| BUY_NEW fill | 21 | 21 |
| BUY_NEW notional | 2,248,650 | 2,274,350 |

After BUY_NEW dropout buckets:

| Bucket | Count |
|---|---:|
| lot/minimum-notional/zero-delta | 126 |
| broker eligibility | 5 |

High-rank BUY_NEW examples repeatedly show positive requested/accepted weights but `lot_aware_weight = 0`, commonly with `minimum_lot_exceeds_concentration_cap` or `incremental_budget_zero_allocation`. BUY_NEW under-allocation remains unresolved and shares the same practical bottleneck as ADD.

## Audit F/G: Re-entry and HOLD / EXIT Quality

PM action counts:

| Action | Before | After |
|---|---:|---:|
| HOLD | 185 | 155 |
| ADD | 190 | 190 |
| REDUCE | 29 | 24 |
| EXIT | 17 | 17 |

Short-term same-symbol SELL -> BUY:

| Window | Before | After |
|---|---:|---:|
| 1BD | 1 | 3 |
| 2BD | 1 | 5 |
| 3BD | 1 | 5 |
| 5BD | 3 | 5 |
| 10BD | 3 | 5 |

Observed After examples include `59550` 2023-06-02 -> 2023-06-05, `21340` 2023-06-07 -> 2023-06-08, `40520` 2023-06-14 -> 2023-06-16, and `37790` 2023-08-15/16 -> 2023-08-17.

This is not automatically a defect, but it worsened and is not explained away by the ADD repair. Premature EXIT remains `INSUFFICIENT_EVIDENCE` pending a focused post-exit price/reason review.

## Audit H: Concentration / Capital Quality

| Metric | Before | After | Direction |
|---|---:|---:|---|
| Avg largest position weight | 17.39% | 18.37% | higher |
| Max largest position weight | 20.73% | 24.23% | higher |
| Avg top2 concentration | 33.03% | 34.23% | higher |
| Max top2 concentration | 37.71% | 40.91% | higher |
| Avg top3 concentration | 44.62% | 46.20% | higher |
| Max top3 concentration | 54.39% | 55.82% | higher |

Cash did not fall materially, but concentration rose. This argues against treating "more BUY_ADD notional" as clean capital deployment improvement.

## Audit I: Performance Attribution

Performance improved by 16,300 JPY. BUY_ADD notional improved by 181,000 JPY and BUY_ADD fills improved by one, so D61 is directionally supported. Still, D61 causality is not confirmed because:

- Runtime BUY_ADD plan count did not increase.
- Average cash/exposure worsened.
- SELL count dropped by 8, changing path dependence.
- Re-entry increased.
- Concentration increased.
- Strict symbol-level submit lineage is incomplete.

Classification:

```text
PARTIALLY_SUPPORTED
```

## Audit J/L: Market Context and Evaluation Shadow

Market Context could not be classified into reliable risk-on / neutral / risk-off buckets from the sampled daily `market_context.json` top-level fields, so defensive deployment quality is `INSUFFICIENT_EVIDENCE`.

D64 remains separated as `EVALUATION_SHADOW_DEFECT`. Existing Phase28 judgment remains unchanged:

```text
Production Strategy affected = NO
Ranking affected = NO
PM affected = NO
D61 affected = NO
Current performance numbers affected = NO evidence found
```

## Audit K: REVIEW_REQUIRED Separation

Local evidence shows:

- After `run_state.json`: `COMPLETED`, 100 business days, last day `2023-08-25`.
- After top-level `fresh_run_summary.json`: stale `HALT` at `2023-05-09`.
- No local `final_summary.json` / `close_summary.json` exists for After.
- Final daily valuation on `2023-08-25`: cash 579,040; market value 560,660; equity 1,139,700; position_count 4.

Classification of reported review items:

| Item | Classification | Judgment |
|---|---|---|
| RUN_EVIDENCE_INCOMPLETE | K3 / K4 | Evidence/observability or close summarization limitation, not proven Production Strategy defect. |
| FINAL_STATE_HASH_NOT_AVAILABLE | K3 / K4 | Final close artifact gap. |
| CURRENT_RUNTIME_ROOT_LEDGER_NOT_USED_FOR_PAST_RUN | K4 | Historical past-run/current-root semantic limitation. |
| SELL_PLAN_SOURCE_DECISION_NOT_TRACEABLE | K3 | Observability lineage gap. |
| LIFECYCLE_CONSISTENCY_REVIEW_REQUIRED | K3 / K5 | Review required, not proven blocking performance defect. |
| PM REDUCE unresolved = 19 | K3 pending further focused audit | Not confirmed from local top-level summary artifacts. |
| Current Positions = 0 | K4 / stale summary conflict | Contradicted by final daily valuation; local final position_count is 4. |

Do not mix these observability issues with the 100BD completion/performance comparison. They should be cleaned up, but they do not invalidate the daily valuation performance result by themselves.

## Final Classification

| Topic | Classification |
|---|---|
| PM ADD propagation | RESOLVED |
| ADD eligibility | PARTIALLY_RESOLVED |
| ADD Capital Conversion | PARTIALLY_RESOLVED |
| lot-aware ADD | NOT_RESOLVED |
| BUY_ADD Runtime formation | RESOLVED |
| BUY_ADD Fill | RESOLVED |
| Cash over-retention | NOT_RESOLVED |
| Exposure under-deployment | NOT_RESOLVED |
| low Position Count | PARTIALLY_RESOLVED |
| legacy max_positions residual constraint | NOT_APPLICABLE |
| BUY_NEW under-allocation | NOT_RESOLVED |
| short-term Re-entry | NOT_RESOLVED |
| premature EXIT | INSUFFICIENT_EVIDENCE |
| HOLD quality | PARTIALLY_RESOLVED |
| excessive concentration | PARTIALLY_RESOLVED |
| Market Context defensive behavior | INSUFFICIENT_EVIDENCE |
| Evidence/Lifecycle observability | NOT_RESOLVED |

## Recommended Phase29-C

```text
Phase29-C Lot/Minimum-Notional Capital Conversion Bottleneck Root Cause Audit
```

Scope should remain evidence-first and production-common: diagnose why positive PC requested/accepted ADD and BUY_NEW allocations are repeatedly lost at lot-aware/minimum-notional/final-target conversion, without threshold tuning, fixed position count, forced cash deployment, or historical-only repair.
