# Phase23-BC BB Runtime Binding and Submit HALT Differential Audit

## Primary Judgment

`PHASE23_BC_BB_RUNTIME_DIFFERENTIAL_AUDIT_COMPLETE`

## Scope

Read-only audit only. No Production code, tests, fixtures, Runtime rerun, broker write, J-Quants fetch, Runtime Switch, or existing run artifact mutation was performed.

## Target Runs

| Role | Run ID | Business Date | Observed result |
|---|---|---:|---|
| BB後Run | `runtime-test-historical-smoke-20260730T050344341520Z` | 2026-07-06 | HALT at submit, inner exit 20, aggregate exit 30 |
| BB前Run | `runtime-test-historical-smoke-20260730T042431441297Z` | 2026-07-06 | HALT at submit by plan-level policy mismatch |
| Safety reference | `runtime-test-historical-smoke-20260730T033913848127Z` | 2026-07-06 | read-only hash preservation target |

## Direct HALT Reason

BB後Runのdirect / lowest observed reasonは `opportunity_evidence_missing`。`run_state.halt_summary.root_reason` も `opportunity_evidence_missing` で、Submit manifestでは9件すべてのBUY itemが `opportunity_buy_eligibility` により `BLOCKED`。

## BB Binding Result

BBのSubmit Policy Authority修正はplan-levelの実Runtime pathへ接続済み。`submit_policy_consistency.comparison_authority = submit_policy_authority`、`policy_consistency_status = PASS`、`policy_mismatch_reason = ""`。

一方、active pendingのitem-levelでは `submit_policy_version/source/hash` が空で、`listed_info = null`。top-levelとapprovalにはBB fieldsがmaterializeされているため、今回のSubmit HALTはBB前のpolicy mismatch再発ではなく、次のitem-level authority gapへ進んだもの。

## Before / After Diff

| Check | BB前Run | BB後Run |
|---|---|---|
| Plan-level policy comparison | legacy `pending_policy_*` vs active capital policy | canonical `pending_submit_policy_*` / `approval_submit_policy_*` vs active capital policy |
| Plan-level result | `REVIEW_REQUIRED` | `PASS` |
| Policy mismatch | `policy_mismatch:pending_policy_version,pending_policy_source,pending_policy_hash` | absent |
| Submit Guard item evidence | not reached | reached, 9 items blocked |
| First failing check | plan-level policy consistency | item-level Opportunity BUY eligibility |
| Historical adapter | not reached | not reached |

## Historical Manifest / Asof Status

Run-scoped `logical_input_manifest.json` exists at `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T050344341520Z/daily/2026-07-06/market_refresh/inputs/historical_asof/2026-07-06/logical_input_manifest.json` and is `PASS`. `historical_asof_view.json` also exists and is `PASS`. No `historical logical source manifest missing` / `historical_logical_source_manifest_missing` reason is present in the BB後Run evidence inspected.

Therefore the known non-BB test gap is not the direct blocker in this run. Submit stopped before historical adapter / as-of hash validation.

## Production Contract Classification

- `BB_CANONICAL_PATH_BOUND`: YES
- `POLICY_MISMATCH_RESOLVED`: YES
- `POLICY_MISMATCH_RECURRED`: NO
- `BB_SERIALIZATION_GAP`: YES, item-level fields remain empty
- `NEW_ITEM_LEVEL_SUBMIT_BLOCKER`: YES, `opportunity_evidence_missing`
- `AUTHORITY_UNRESOLVED`: YES, item-level Opportunity BUY eligibility authority
- `EXPECTED_FAIL_CLOSED`: YES, Submit blocked before broker boundary
- `HISTORICAL_LOGICAL_SOURCE_MANIFEST_MISSING`: NO for this run
- `HISTORICAL_ADAPTER_BINDING_FAILURE`: NOT_REACHED

## Root Cause

`Strategy Planning Authority -> PendingOrderItem` materialization does not carry Opportunity BUY eligibility authority / `listed_info` into BUY items. Although `.runtime/runtime_state/buy_ai/2026-07-06/opportunity_rankings.json` exists and contains 50 rankings, the strategy-planning order plan and promoted pending items have no opportunity artifact path/hash or row-level opportunity evidence for Submit Guard to revalidate.

## Recommended Repair Boundary

Next repair should be owned by `runtime_v2.planning.strategy_authority.activate_strategy_planning_authority` and the Runtime Planning -> Pending adapter contract. It should propagate canonical item-level Opportunity BUY eligibility authority into pending items without bypassing Submit Guard, forcing BUY, adding historical-only fallback, or changing broker behavior.

## Evidence

- `reports/phase23_bc_bb_runtime_binding_and_submit_halt_differential_audit/new_run_submit_halt_reason.json`
- `reports/phase23_bc_bb_runtime_binding_and_submit_halt_differential_audit/bb_before_after_run_diff.json`
- `reports/phase23_bc_bb_runtime_binding_and_submit_halt_differential_audit/pending_policy_authority_inventory.json`
- `reports/phase23_bc_bb_runtime_binding_and_submit_halt_differential_audit/submit_guard_comparison_trace.json`
- `reports/phase23_bc_bb_runtime_binding_and_submit_halt_differential_audit/submit_execution_stage_trace.json`
- `reports/phase23_bc_bb_runtime_binding_and_submit_halt_differential_audit/historical_logical_source_manifest_trace.json`
- `reports/phase23_bc_bb_runtime_binding_and_submit_halt_differential_audit/run_scoped_asof_authority_trace.json`
- `reports/phase23_bc_bb_runtime_binding_and_submit_halt_differential_audit/previous_blocker_recurrence_check.json`
- `reports/phase23_bc_bb_runtime_binding_and_submit_halt_differential_audit/first_invalid_artifact.json`
- `reports/phase23_bc_bb_runtime_binding_and_submit_halt_differential_audit/production_contract_classification.json`
- `reports/phase23_bc_bb_runtime_binding_and_submit_halt_differential_audit/recommended_repair_boundary.json`
- `reports/phase23_bc_bb_runtime_binding_and_submit_halt_differential_audit/existing_run_hash_preservation.json`

## Final Gate

`READY_FOR_REPAIR = YES`

`READY_FOR_1BD_RERUN = NO`
