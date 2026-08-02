# Phase24-F Opportunity Ranking and Entry Quality Attribution Audit

## 1. Primary Judgment

`PHASE24_F_ENTRY_QUALITY_AUDIT_COMPLETE_MULTI_LAYER_PERFORMANCE_GAPS`

Phase24-F reviewed the existing 20BD historical runtime evidence only. No Runtime, Strategy, PM, sizing, threshold, source, authority, or performance parameter was changed.

Primary finding: the observed loss is not explained by a single opportunity-ranking failure. The dominant performance gap is multi-layered: Position Management / Exit Timing and repeated re-entry into volatile losing symbols are primary, while opportunity/selection quality and single-name capital concentration are contributing factors. Observability gaps prevent a fully stable source-decision lineage for every campaign, but do not block the main attribution judgment.

## 2. Scope

| Item | Scope |
| --- | --- |
| Task ID | `Phase24-F` |
| Source run | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T033807973583Z` |
| Period | 2022-07-01 to 2022-07-29 |
| Business days | 20 |
| Allowed action | Evidence-only audit and attribution |
| Forbidden action | Runtime/Strategy/PM/sizing/threshold/source/authority change |

This report uses post-hoc forward returns only for attribution. They are not strategy inputs, learning inputs, or runtime decision inputs.

## 3. Reviewed Evidence

| Evidence | Result |
| --- | ---: |
| Daily Top10 opportunity rows | 200 |
| Actual BUY executions | 15 |
| Position campaigns | 14 |
| SELL executions | 10 |
| PM decision rows | 51 |
| Top-ranked not-bought rows | 35 |
| Observability gaps | 6 |

Primary generated evidence directory:

`reports/phase24_f_opportunity_ranking_and_entry_quality_attribution_audit/`

Machine-readable summary:

`reports/phase_reports/phase24_f_opportunity_ranking_and_entry_quality_attribution_audit.json`

## 4. Performance Overview

| Metric | Value |
| --- | ---: |
| Initial equity | 1,000,000 |
| Final equity | 935,780 |
| Total return | -64,220 |
| Total return % | -6.422% |
| Realized PnL | -58,800 |
| Unrealized PnL | -57,380 |
| Final cash | 282,130 |
| Final market value | 653,650 |

Loss attribution is concentrated. `66590` contributed -92,600, and `23880` contributed -33,200. `24370` was a positive counterexample at +13,100.

## 5. Daily Opportunity Ranking Audit

The audit materialized daily Top10 opportunity rows across all 20 business days into `daily_top10_opportunities.json`.

Ranking evidence confirms that high-ranked candidates existed, but the Phase21/Phase24 boundary still applies: ranking is an opportunity-ordering input, not an automatic BUY command. BUY selection is mediated by eligibility, portfolio construction, capital deployment, sizing, current holdings, and submit safety.

For actual BUY entries with available 5BD post-hoc returns, descriptive correlation was:

| Relationship | n | Pearson | Interpretation |
| --- | ---: | ---: | --- |
| Entry rank vs 5BD return | 9 | -0.5585 | Lower numeric rank tended to align with better 5BD return in the small sample |
| Expected edge vs 5BD return | 9 | 0.4504 | Higher expected edge tended to align with better 5BD return in the small sample |

This does not support a global conclusion that opportunity ranking was inverted or unusable. It does support narrower selection-quality concerns for specific losing entries, especially low-edge `66590` entries.

## 6. Actual BUY Lineage

All 15 BUY executions were traced from submit guard evidence, fills, portfolio construction, and campaign materialization.

Actual BUY lineage was materialized in `actual_buy_lineage.json`. The lineage includes business date, symbol, rank at decision time, expected edge, eligibility status, allocation amount, execution quantity, submit pending item ID, campaign ID where derivable, and source artifacts.

The campaign layer does not preserve stable `order_plan_item_id`, `pending_item_id`, or `source_decision_id` in `positions/position_campaigns.json`. Therefore, campaign linkage is partly inferred by date, symbol, execution, and submit evidence. This is a partial observability gap, not evidence of a runtime correctness failure.

## 7. Top Ranked Not Bought Analysis

Top-ranked not-bought evidence was materialized in `top_ranked_not_bought.json`.

| Classification | Count |
| --- | ---: |
| `DUPLICATE_OR_ALREADY_HELD` | 14 |
| `CASH_OR_EXPOSURE_CONSTRAINT` | 13 |
| `ELIGIBILITY_REJECT` | 4 |
| `UNKNOWN` | 4 |

The not-bought cases are not explained by a single suppression mechanism. The largest classes are existing membership / duplicate exposure and cash or exposure constraints. Candidate eligibility rejection exists but is not the dominant not-bought cause in this run.

## 8. Entry Quality Analysis

Entry quality is mixed.

Positive evidence:

- `94320` entered at rank 1 with strong expected edge; campaign PnL was small negative at -3,480.
- `24370` produced positive total campaign PnL of +13,100.
- Rank and expected edge show directionally reasonable post-hoc correlation in the available small sample.

Negative evidence:

- `66590` was repeatedly bought at ranks 6, 7, and 4 with low early expected edges.
- `66590` generated -92,600 total PnL, including a final open unrealized loss of -65,600.
- `23880` generated -33,200 total PnL despite several rank 2-4 entries.

Judgment: opportunity ranking is not the sole primary root cause. Entry selection quality is a secondary root cause and a material contributor for `66590` and `23880`.

## 9. Campaign Entry Quality

Campaign-level entry quality was materialized in `campaign_entry_quality.json`.

| Symbol | Campaigns | Total PnL | Judgment |
| --- | ---: | ---: | --- |
| `66590` | 5 | -92,600 | Poor entry/PM combination; dominant loss concentration |
| `23880` | 5 | -33,200 | Mixed entries, repeated re-entry, large first-campaign loss |
| `24370` | 2 | +13,100 | Positive counterexample; gave back some favorable excursion |
| `94320` | 1 | -3,480 | High-ranked entry with small loss |
| `94340` | 1 | 0 | Neutral |

The two largest losing symbols account for almost all negative contribution before offsets. This points to symbol-level concentration and repeated lifecycle handling, not broad opportunity-ranking collapse.

## 10. Position Sizing Attribution

Position sizing attribution was materialized in `position_sizing_attribution.json`.

Allocation amounts were large enough for single-symbol losses to dominate total run performance. Example entry allocations include approximately 140,300 to 179,200 across audited campaigns.

No evidence shows a sizing contract breach. However, sizing contributes to realized performance because repeated entries in `66590` and `23880` received meaningful notional allocations. Position sizing is therefore classified as contributing, not primary.

Some sizing fields remain `NOT_OBSERVABLE`, including calculated target position count, safety hard maximum, and strategy maximum at campaign granularity. This limits fine-grained sizing causality.

## 11. Position Management Timeline

PM timeline was materialized in `pm_timeline.json`.

| PM action | Count |
| --- | ---: |
| `HOLD` | 28 |
| `ADD` | 12 |
| `EXIT` | 10 |
| `REDUCE` | 1 |

PM evidence shows major profit-retention and exit-timing issues:

- `66590` was held after a favorable move of +14.4828%, then exited two days later at -15.8621%.
- `23880` first campaign reached material favorable excursion, then exited at a large loss.
- Several losing symbols were re-entered after hard-stop exits.
- `24370` was profitable but still gave back a large favorable excursion before exit.

Judgment: Position Management / Exit Timing is the primary performance root cause in this run.

## 12. Symbol 23880 Timeline

`symbol_23880_timeline.json` contains 5 campaigns.

| Entry date | Rank | Edge | Exit date | Campaign PnL | Notes |
| --- | ---: | ---: | --- | ---: | --- |
| 2022-07-11 | 4 | 0.04045175 | 2022-07-14 | -26,600 | Large first loss after favorable excursion |
| 2022-07-15 | 4 | 0.13997306 | 2022-07-19 | +2,800 | Small recovery |
| 2022-07-20 | 3 | 0.10962238 | 2022-07-21 | +2,800 | Small positive |
| 2022-07-22 | 3 | 0.08608751 | 2022-07-25 | -13,500 | Re-entry loss |
| 2022-07-26 | 2 | 0.11641615 | 2022-07-29 | +1,300 | Small positive |

Judgment: `23880` is a mixed entry-quality and PM case. The largest loss came from one campaign, but repeated re-entry kept the symbol in the loss path.

## 13. Symbol 66590 Timeline

`symbol_66590_timeline.json` contains 5 campaigns.

| Entry date | Rank | Edge | Exit date | Campaign PnL | Notes |
| --- | ---: | ---: | --- | ---: | --- |
| 2022-07-13 | 6 | 0.00310574 | 2022-07-15 | -23,000 | Held after +14.4828%, then hard-stop/profit-retention break |
| 2022-07-19 | 7 | 0.01983658 | 2022-07-20 | -5,600 | Low-ranked re-entry loss |
| 2022-07-25 | 4 | 0.01211470 | 2022-07-26 | +1,600 | Small positive |
| 2022-07-27 | 4 | 0.04351024 | 2022-07-28 | 0 | Neutral |
| 2022-07-29 | 4 | 0.07148693 | OPEN | -65,600 | Dominant final open unrealized loss |

Judgment: `66590` is the strongest root-cause evidence. The issue is a combination of low early entry quality, repeated re-entry, PM exit timing, and large notional exposure.

## 14. Symbol 24370 Timeline

`symbol_24370_timeline.json` contains 2 campaigns.

| Entry date | Rank | Edge | Exit date | Campaign PnL | Notes |
| --- | ---: | ---: | --- | ---: | --- |
| 2022-07-19 | 5 | 0.11287416 | 2022-07-26 | +1,400 | Positive but gave back large favorable excursion |
| 2022-07-28 | 5 | 0.00366777 | OPEN | +11,700 | Positive open campaign |

Judgment: `24370` is a positive counterexample. It weakens the hypothesis that ranking or entry policy was globally defective, while still showing PM profit-retention observability should be improved.

## 15. Root Cause Classification

| Component | Classification | Rationale |
| --- | --- | --- |
| Position Management | `PRIMARY` | PM decisions held/gave back gains and repeatedly re-entered volatile losers |
| Exit Timing | `PRIMARY` | Losses include sharp reversals after favorable excursions |
| Opportunity Ranking Quality | `SECONDARY` | Some losing entries were low-ranked/low-edge, but sample does not show global rank failure |
| Portfolio Construction | `CONTRIBUTING` | Selection allowed repeated symbol participation |
| Position Sizing | `CONTRIBUTING` | Allocations amplified symbol-level losses without evidence of contract breach |
| Capital Deployment | `CONTRIBUTING` | Exposure was materially deployed into losing symbols |
| Market Regime Mismatch | `CONTRIBUTING` | Relative benchmark source is missing, so beta/regime separation is incomplete |
| Candidate Eligibility | `NOT_SUPPORTED_AS_PRIMARY` | Eligibility rejection count is small versus other mechanisms |
| Corporate Event Handling | `NOT_SUPPORTED` | No evidence supports corporate-event handling as current loss cause |
| Observability Gap | `CONTRIBUTING` | Stable lineage and PM peak/drawdown fields are missing |
| Insufficient Sample | `CONTRIBUTING` | 20BD sample limits statistical confidence |

## 16. Runtime Correctness vs Performance

No Runtime correctness breach is identified by this audit.

Performance causes include:

- Entry quality
- PM quality
- Exit timing
- Re-entry behavior
- Cash / exposure deployment
- Single-name concentration
- Profit retention

The following are outside the Phase24-F performance attribution finding unless independently evidenced:

- HALT
- Authority欠損
- Cash不整合
- Ledger不整合
- Future leakage
- Safety violation

## 17. Observability Gaps

`observability_gaps.json` contains 6 gaps.

| Gap | Blocking | Impact |
| --- | --- | --- |
| Stable order/pending/source decision IDs absent in campaign buy observability | `PARTIAL_BLOCKING` | Requires date/symbol inference for BUY-to-campaign lineage |
| Candidate eligibility canonical fields incomplete in strategy trace | `PARTIAL_BLOCKING` | Limits eligibility vs construction separation |
| Corporate event state absent in per-symbol trace | `NON_BLOCKING_CURRENT_RUN` | Limits corporate-event attribution |
| PM peak_return and drawdown_from_peak absent | `PARTIAL_BLOCKING` | Limits profit-retention timing analysis |
| closed_business_date empty for closed campaigns | `NON_BLOCKING` | Exit date must be derived from events |
| Benchmark return source missing | `NON_BLOCKING` | Relative return/regime separation incomplete |

## 18. Evidence Artifacts

Generated Phase24-F artifacts:

- `reports/phase24_f_opportunity_ranking_and_entry_quality_attribution_audit/daily_top10_opportunities.json`
- `reports/phase24_f_opportunity_ranking_and_entry_quality_attribution_audit/actual_buy_lineage.json`
- `reports/phase24_f_opportunity_ranking_and_entry_quality_attribution_audit/top_ranked_not_bought.json`
- `reports/phase24_f_opportunity_ranking_and_entry_quality_attribution_audit/campaign_entry_quality.json`
- `reports/phase24_f_opportunity_ranking_and_entry_quality_attribution_audit/position_sizing_attribution.json`
- `reports/phase24_f_opportunity_ranking_and_entry_quality_attribution_audit/pm_timeline.json`
- `reports/phase24_f_opportunity_ranking_and_entry_quality_attribution_audit/symbol_23880_timeline.json`
- `reports/phase24_f_opportunity_ranking_and_entry_quality_attribution_audit/symbol_66590_timeline.json`
- `reports/phase24_f_opportunity_ranking_and_entry_quality_attribution_audit/symbol_24370_timeline.json`
- `reports/phase24_f_opportunity_ranking_and_entry_quality_attribution_audit/observability_gaps.json`
- `reports/phase24_f_opportunity_ranking_and_entry_quality_attribution_audit/phase24f_evidence.json`
- `reports/phase_reports/phase24_f_opportunity_ranking_and_entry_quality_attribution_audit.json`

## 19. Recommended Next Task

Recommended next task:

`Phase24-G PM Profit Retention and Re-entry Control Contract`

Purpose:

- Define evidence-only contract for PM profit retention, re-entry cooldown, and repeated-symbol loss attribution.
- Do not implement changes until the contract is reviewed.
- Require one-hypothesis/one-change experiment design per Phase24-A before any runtime or strategy modification.

Before any improvement implementation, close the partial observability gaps for stable BUY-to-campaign lineage and explicit PM peak/drawdown fields, or mark the experiment as attribution-limited.

