# Phase32-CX — Post-CW 2022-10-04 Morning HALT Root Cause Audit

## Executive Summary

Run `runtime-test-historical-extended-smoke-20260829T074417218406Z` completed `2022-10-03` and halted at `2022-10-04:morning`.

The direct HALT was not an import/schema crash and not a broker/submit/runtime mutation failure. The inner morning CLI exited `20` because Strategy Planning Authority returned `REVIEW_REQUIRED` with:

`strategy_planning_authority_unresolved`

The first semantic failing boundary is Position Management on `2022-10-04`. CW introduced the requirement that open campaigns compare current PM evidence against a campaign-scoped immutable entry premise. All eight `2022-10-03` BUY_NEW campaigns were present with valid campaign IDs on `2022-10-04`, but their `campaign_entry_premise_snapshot.v1` materialized as `REVIEW_REQUIRED` because the strict-prior execution/fill rows carried only execution quantities and sparse lineage:

`source_decision_id = MISSING`

and no entry admission / Buy Quality / target magnitude fields. PM therefore produced:

`entry_premise_delta_ambiguous_review_required`

for the live positions, which propagated to Portfolio Construction, Position Sizing, Runtime Planning, and finally Strategy Planning Authority.

Judgment: CW causal = YES. The fail-closed mechanism itself is partially valid, but its actual-path persistence/materialization is incomplete. A normal fresh campaign opened on `2022-10-03` cannot require human review on the next morning solely because the execution ledger did not preserve enough entry premise source fields.

## Run Identity

- Run: `runtime-test-historical-extended-smoke-20260829T074417218406Z`
- Evidence root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260829T074417218406Z`
- Source commit recorded by run: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Wrapper status: `HALT`
- Wrapper exit code: `30`
- Inner halted job: `2022-10-04:morning`
- Inner exit code: `20`
- Completed business days: `["2022-10-03"]`
- Fresh summary root reason: `morning pipeline review required: strategy_planning_authority_unresolved`

## Morning Stage Timeline

| Stage | Artifact | Status | Notes |
| --- | --- | --- | --- |
| 2022-10-03 EOD fills | `daily/2022-10-03/execution/fills.json` | PASS | 8 BUY fills generated. Fill rows contain campaign IDs but sparse source lineage. |
| 2022-10-03 campaign state | `daily/2022-10-03/positions/position_campaigns.json` | PASS / empty | `position_campaigns` length is 0 before next-day preload. |
| 2022-10-04 market refresh | `daily/2022-10-04/market_refresh/runtime_manifest.json` | exit 0 | Market/quote readiness passed. |
| 2022-10-04 data readiness | `daily/2022-10-04/data_readiness/runtime_manifest.json` | exit 0 | Readiness overall READY. Current state loaded from `2022-10-03`; pending slot terminal/consumed. |
| 2022-10-04 campaign preload | `daily/2022-10-04/positions/position_campaigns.json` | materialized | 8 open campaigns materialized with valid campaign IDs and quantities. Entry premise snapshot fields are not usable in the copied campaign rows. |
| 2022-10-04 Strategy Intelligence | `daily/2022-10-04/strategy/strategy_intelligence.json` | PASS | Lifecycle context propagates all 8 snapshots as `REVIEW_REQUIRED` with `entry_premise_source_evidence_missing`. |
| 2022-10-04 PM | `daily/2022-10-04/strategy/position_management.json` | REVIEW_REQUIRED | First semantic failing component. 8/8 positions have `entry_premise_snapshot_status=REVIEW_REQUIRED`; 7 become `UNRESOLVED`, 89180 preserves hard failure EXIT. |
| 2022-10-04 PC | `daily/2022-10-04/strategy/portfolio_construction.json` | REVIEW_REQUIRED | Includes `upstream_review_required:SOURCE_REVIEW_REQUIRED`. |
| 2022-10-04 PS | `daily/2022-10-04/strategy/position_sizing.json` | REVIEW_REQUIRED | `positions_sized=0`, `positions_withheld=51`; propagated PM/PC review required. |
| 2022-10-04 Runtime Planning | `daily/2022-10-04/strategy/runtime_planning.json` | REVIEW_REQUIRED | `plan_count=32`, `pending_written=false`; unresolved quantity authority for 25 symbols. |
| 2022-10-04 Strategy Planning Authority | `daily/2022-10-04/morning/strategy_planning_authority_evidence.json` | REVIEW_REQUIRED | `pending_item_count=0`, `pending_commit_status=NOT_COMMITTED_REVIEW_REQUIRED_EMPTY_UNSCOPED`. |
| 2022-10-04 CLI manifest | `daily/2022-10-04/morning/runtime_manifest.json` | exit 20 | `reason=morning pipeline review required: strategy_planning_authority_unresolved`. |

Last successful semantic boundary: Strategy Intelligence lifecycle propagation completed.

First failing semantic boundary: Position Management entry premise delta prerequisite.

First runtime HALT boundary: Strategy Planning Authority consumer, after PM/PC/PS had already marked the strategy source set as review required.

## Exact Failure

- `FIRST_FAILING_STAGE`: `2022-10-04 strategy / Position Management`
- `FIRST_FAILING_COMPONENT`: `strategy.position_management`
- `FIRST_FAILING_FUNCTION`: `_entry_premise_delta()` / `_apply_entry_premise_delta_context()` in `src/ai_fund_lab_v2/strategy/position_management.py`
- `FIRST_FAILING_CONTRACT`: `entry_premise_delta.v1` requires an available/pass `campaign_entry_premise_snapshot.v1` for an open campaign when `entry_premise_snapshot_status` is `MISSING` or `REVIEW_REQUIRED`.
- `DIRECT_RUNTIME_HALT_COMPONENT`: `runtime_v2.planning.strategy_authority.build_strategy_planning_authority()`
- `DIRECT_RUNTIME_HALT_CONTRACT`: Strategy planning may not commit pending when source strategy artifacts contain unresolved review-required planning evidence.
- `EXACT_ERROR`: `morning pipeline review required: strategy_planning_authority_unresolved`
- Root PM reason code: `entry_premise_delta_ambiguous_review_required`
- Snapshot source reason code: `entry_premise_source_evidence_missing`

Code evidence:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py` creates new campaigns from execution rows and calls `_campaign_entry_premise_snapshot_from_execution()`. If no entry evidence exists outside accepted quantity/notional, it returns `snapshot_status=REVIEW_REQUIRED` with `entry_premise_source_evidence_missing`.
- `src/ai_fund_lab_v2/strategy/position_management.py` treats a required but unavailable snapshot as `AMBIGUOUS_REVIEW_REQUIRED`; `_apply_entry_premise_delta_context()` maps that to `final_pm_action=UNRESOLVED`.
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py` writes `REVIEW_REQUIRED` with `strategy_planning_authority_unresolved` when planning reason codes exist and no pending items can be committed.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py` maps morning `REVIEW_REQUIRED` to inner exit code `20`.

## 10/03 Campaign Snapshot Audit

10/03 produced 8 BUY fills. All fills have `position_campaign_id`, quantity, price, and execution id. All fills have `source_decision_id=MISSING`, `pending_item_id=MISSING`, `order_plan_item_id=MISSING`, and `quality_decision_id=MISSING`; no entry admission or Buy Quality premise fields are present on the fill rows.

| Symbol | Campaign ID | 10/04 Qty | Snapshot Status in SI | Snapshot Reason | Source Decision |
| --- | --- | ---: | --- | --- | --- |
| 33500 | `pc-45d445518a3c42f5-33500-0001` | 400 | REVIEW_REQUIRED | `entry_premise_source_evidence_missing` | empty / missing |
| 37820 | `pc-47a1ceb8e589920d-37820-0001` | 300 | REVIEW_REQUIRED | `entry_premise_source_evidence_missing` | empty / missing |
| 67860 | `pc-b7d270d14d0e7e29-67860-0001` | 200 | REVIEW_REQUIRED | `entry_premise_source_evidence_missing` | empty / missing |
| 76470 | `pc-7345976a165d347d-76470-0001` | 700 | REVIEW_REQUIRED | `entry_premise_source_evidence_missing` | empty / missing |
| 82540 | `pc-728c4cc2c67f59ac-82540-0001` | 100 | REVIEW_REQUIRED | `entry_premise_source_evidence_missing` | empty / missing |
| 89180 | `pc-41eece8699c41379-89180-0001` | 2100 | REVIEW_REQUIRED | `entry_premise_source_evidence_missing` | empty / missing |
| 94340 | `pc-803e6b53f7f3bfb5-94340-0001` | 200 | REVIEW_REQUIRED | `entry_premise_source_evidence_missing` | empty / missing |
| 96100 | `pc-6953de90f1c14e57-96100-0001` | 100 | REVIEW_REQUIRED | `entry_premise_source_evidence_missing` | empty / missing |

Campaign identity itself is not the main defect: the 8 campaign IDs are stable enough to join positions into PM and Strategy Intelligence. The missing part is the entry premise payload/lineage that CW now requires.

## PM Decision Effects

All 8 PM rows consumed `entry_premise_snapshot_status=REVIEW_REQUIRED`.

| Symbol | PM Action | PM Context Class | Delta Status | Key PM / Delta Reasons |
| --- | --- | --- | --- | --- |
| 94340 | UNRESOLVED | AMBIGUOUS_REVIEW_REQUIRED | REVIEW_REQUIRED | `entry_premise_snapshot_missing_or_unavailable`, `entry_premise_source_evidence_missing`; original HOLD evidence existed. |
| 37820 | UNRESOLVED | AMBIGUOUS_REVIEW_REQUIRED | REVIEW_REQUIRED | `trend_and_opportunity_broken` plus missing entry premise. |
| 89180 | EXIT | HARD_FAILURE | PASS | `hard_stop_current_return`; hard failure correctly preserved despite missing premise. |
| 76470 | UNRESOLVED | AMBIGUOUS_REVIEW_REQUIRED | REVIEW_REQUIRED | `weak_hold_score` plus missing entry premise. |
| 33500 | UNRESOLVED | AMBIGUOUS_REVIEW_REQUIRED | REVIEW_REQUIRED | `risk_increased_but_trend_not_broken` plus missing entry premise. |
| 82540 | UNRESOLVED | AMBIGUOUS_REVIEW_REQUIRED | REVIEW_REQUIRED | `risk_increased_but_trend_not_broken` plus missing entry premise. |
| 67860 | UNRESOLVED | AMBIGUOUS_REVIEW_REQUIRED | REVIEW_REQUIRED | `trend_and_opportunity_broken` plus missing entry premise. |
| 96100 | UNRESOLVED | AMBIGUOUS_REVIEW_REQUIRED | REVIEW_REQUIRED | `trend_and_opportunity_broken` plus missing entry premise. |

This confirms CW preserved hard failure behavior for 89180, but caused ordinary open campaigns to become unresolved when the entry premise snapshot could not be reconstructed from sparse execution rows.

## Propagation Evidence

`source_manifest.json`:

- `position_management.status = REVIEW_REQUIRED`
- `position_management.primary_reason_code = entry_premise_delta_ambiguous_review_required`
- `portfolio_construction.status = REVIEW_REQUIRED`
- `portfolio_construction.primary_reason_code = upstream_review_required:SOURCE_REVIEW_REQUIRED`
- `position_sizing.status = REVIEW_REQUIRED`
- `position_sizing.reason_codes = portfolio_construction_review_required:REVIEW_REQUIRED, position_management_review_required:REVIEW_REQUIRED`
- `runtime_planning.status = REVIEW_REQUIRED`

`position_sizing.json`:

- `producer_result_status = REVIEW_REQUIRED`
- `positions_sized = 0`
- `positions_withheld = 51`
- `marginal_capital_frontier_switch_consumption.status = PASS`
- `accepted_boundary_target_count = 0`
- `legacy_target_gap_fallback_used = false`
- `legacy_zero_fallback_used = false`

`runtime_planning.json`:

- `producer_result_status = REVIEW_REQUIRED`
- `plan_count = 32`
- `pending_written = false`
- `submit_generated = false`
- primary direct reason family: `review_required_quantity_authority:*:REVIEW_REQUIRED_AUTHORITY_UNRESOLVED`

`strategy_planning_authority_evidence.json`:

- `status = REVIEW_REQUIRED`
- `reason = strategy_planning_authority_unresolved`
- `pending_item_count = 0`
- `pending_commit_status = NOT_COMMITTED_REVIEW_REQUIRED_EMPTY_UNSCOPED`
- `atomic_commit_decision = SKIP_CURRENT_PENDING_COMMIT`

## CW Causality

CW is causal.

The regression path is:

1. 10/03 actual BUY fills are generated with campaign IDs but sparse entry premise source fields.
2. 10/04 pre-action position campaign materialization bootstraps open campaigns from strict-prior ledger execution evidence.
3. CW snapshot logic attempts to materialize `campaign_entry_premise_snapshot.v1` from those execution rows.
4. Because the rows do not contain entry admission / rank / opportunity / Buy Quality / target magnitude evidence, the snapshot is `REVIEW_REQUIRED`.
5. Strategy Intelligence propagates `entry_premise_snapshot_status=REVIEW_REQUIRED`.
6. PM treats required-but-unavailable entry premise as `AMBIGUOUS_REVIEW_REQUIRED`.
7. PM output becomes `REVIEW_REQUIRED`, causing PC/PS/runtime planning review-required propagation.
8. Strategy Planning Authority refuses to commit pending and the morning CLI exits `20`; wrapper records HALT `30`.

This is not explained by market/data/preflight, Safety, schema import, cash/budget, cap, PS arithmetic, Runtime mapping, Pending submit, or broker execution.

## Backward / Schema Compatibility

No schema constructor/import failure was observed. The artifacts are valid JSON, expected files exist, and producer outputs materialized.

The defect is a contract compatibility gap between:

- new CW requirement: PM requires entry premise snapshot for open campaign comparison; and
- existing actual execution/fill rows: BUY execution lineage does not carry enough entry premise fields for snapshot materialization.

It is therefore a CW integration/materialization regression rather than a low-level schema compatibility defect.

## State Integrity

The halted job reached strategy planning but did not generate submit artifacts or fills for `2022-10-04`.

- 10/04 data readiness: PASS / READY.
- 10/04 pending lifecycle: prior pending already terminal/consumed.
- 10/04 Strategy Planning Authority: `pending_commit_status=NOT_COMMITTED_REVIEW_REQUIRED_EMPTY_UNSCOPED`.
- 10/04 Runtime Planning: `pending_written=false`, `submit_generated=false`.
- 10/04 morning `pending_generation_evidence.json`: wrote a review-required pending shell/evidence, but no executable pending items.

Runtime state was partially materialized in the normal evidence sense: 10/04 strategy/positions artifacts exist and encode REVIEW_REQUIRED. There is no evidence of order/fill mutation after the HALT boundary.

## Repair Readiness

Minimal repair boundary:

Materialize the campaign entry premise from authoritative same-run, strict-prior entry decision artifacts before PM requires it. The repair should stay inside campaign entry premise persistence / lifecycle source resolution and should not alter PM thresholds, REDUCE/EXIT semantics, Safety, Risk Pacing, PC/PS arithmetic, Runtime mapping, or Pending/Execution behavior.

Candidate authority sources for repair:

- 10/03 BF / PS / Runtime Planning lineage attached to accepted BUY_NEW/REENTRY target rows.
- 10/03 Buy Quality decisions and PC entry admission lineage referenced by runtime planning / position sizing.
- Pending/order plan lineage if available before execution normalization.
- Execution rows only if they are formally enriched with the existing entry premise snapshot at fill time.

Do not silently reconstruct from symbol-only latest state. The join must remain campaign-scoped or decision-lineage-scoped and PIT-safe.

## Resume / Fresh-Run Recommendation

Resume after repair is likely technically safe because the failed boundary is `2022-10-04:morning` before submit/fill generation, and the run summary reports pending already terminal. However, for acceptance of the repair, a new short fresh validation is recommended because the causal defect is entry snapshot materialization across the day-0 fill to day-1 PM boundary.

## Final Judgments

PHASE32_CX_HALT_STAGE = 2022-10-04:morning strategy_planning_authority after Position Management REVIEW_REQUIRED propagation

PHASE32_CX_DIRECT_CAUSE = strategy_planning_authority_unresolved caused by entry_premise_delta_ambiguous_review_required from Position Management

PHASE32_CX_CW_CAUSAL = YES

PHASE32_CX_ENTRY_PREMISE_PERSISTENCE_VALID = PARTIAL

PHASE32_CX_CAMPAIGN_IDENTITY_VALID = YES

PHASE32_CX_FAIL_CLOSED_BEHAVIOR_VALID = PARTIAL

PHASE32_CX_PRODUCTION_REGRESSION = YES

PHASE32_CX_REPAIR_REQUIRED = YES

PHASE32_CX_RESUME_AFTER_REPAIR_ALLOWED = YES

PHASE32_CX_FRESH_RERUN_REQUIRED_AFTER_REPAIR = YES

PHASE32_CX_NEXT_STEP = Narrow repair: ensure BUY_NEW/REENTRY campaign_entry_premise_snapshot.v1 is materialized from authoritative same-run entry decision lineage before PM day+1 delta evaluation; preserve hard failure/true breakdown fail-closed behavior.
