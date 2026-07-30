# Phase23-AY AX Runtime Reproduction Gap and Sell Planning HALT Differential Audit

## Primary Judgment

`PHASE23_AY_AX_RUNTIME_DIFFERENTIAL_AUDIT_COMPLETE`

## Secondary Judgment

- `AX_SAFETY_BLOCKER_RECURRED = YES`
- `AX_SAFETY_METADATA_PRESENT_IN_RUNTIME = NO`
- `AX_CANONICAL_PATH_BOUND = NO`
- `ISOLATED_RUNTIME_PATH_EQUIVALENT = NO`
- `NEW_DOWNSTREAM_BLOCKER_FOUND = NO`
- `FIRST_INVALID_ARTIFACT = ACTIVE_PENDING_ORDER_PLAN_SAFETY_AUTHORITY`
- `CANONICAL_REPAIR_OWNER = Strategy Planning Authority pending producer / Pending Promotion boundary`
- `REPAIR_REQUIRED = YES`
- `READY_FOR_1BD_RERUN = NO`

## Scope

Read-only differential audit only. No Production code, tests, fixtures, Runtime rerun, fresh-run, resume, Broker Write, J-Quants fetch, or existing run artifact mutation was performed.

## Target Runs

| Role | Run ID | Status | Halt Stage | Inner Exit |
|---|---|---:|---|---:|
| AX後 New Run | `runtime-test-historical-smoke-20260730T033913848127Z` | `HALT` | `sell_planning` | `20` |
| AX前 Run | `runtime-test-historical-smoke-20260730T030213466506Z` | `HALT` | `sell_planning` | `20` |

Both runs completed `market_refresh`, `data_readiness`, and `morning`, then stopped at `sell_planning` before completing any business day.

## Mandatory First Check

| Reason | New Run Presence | Evidence |
|---|---|---|
| `historical_pending_safety_authority_mismatch` | `present` | `data_readiness.json /components/safety/pending_safety_authority/reason` |
| `historical_safety_temporal_authority_missing` | `present` | `sell_planning/runtime_manifest.json /reason` |
| `pending_safety_evidence_missing` | `present` | `sell_planning/runtime_manifest.json /data_readiness_review_reasons` |

## Direct HALT Reason

New Run direct HALT reason is `historical_safety_temporal_authority_missing`. The lowest pending-specific reason is `historical_pending_safety_authority_mismatch`; Data Readiness also reports `pending_safety_evidence_missing`.

Evidence:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T033913848127Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T033913848127Z/daily/2026-07-06/sell_planning/runtime_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T033913848127Z/daily/2026-07-06/data_readiness/data_readiness.json`

## Runtime Pending Metadata

New Run active pending evidence:

| Field | Value |
|---|---:|
| active pending | `True` |
| pending slot status | `APPROVED` |
| pending item count | `9` |
| pending symbols | `31330, 43780, 45640, 45960, 45970, 66340, 67400, 89180, 94320` |
| top-level `safety_context` | `None` |
| top-level `safety_decision_id` | `` |
| top-level `safety_policy_version` | `` |

All required item-level safety metadata counts are zero. Therefore AX Safety Authority metadata was not materialized into the actual runtime active pending artifact.

## Differential Result

AX前Run and AX後New Run are materially the same for the blocker:

- same halt stage: `sell_planning`
- same direct reason: `historical_safety_temporal_authority_missing`
- same review reasons: `historical_safety_temporal_authority_missing`, `pending_safety_evidence_missing`
- same 9 pending symbols
- same missing top-level `safety_context`
- same missing item safety metadata

The only observed differences are generated ids / hashes, not contract behavior.

## Isolated vs Runtime Gap

AX isolated reproduction passed with:

- `materialized_pending_safety_context_missing_count = 0`
- `historical_pending_safety_authority_reason = explicit_safety_decision_id_present`
- `pending_safety_evidence_missing = False`

Actual runtime path evidence identifies:

`runtime_v2.planning.strategy_authority.activate_strategy_planning_authority`

as the producer/consumer path for pending generation. That path generated 9 pending items, but Data Readiness observed no safety metadata on the active pending artifact.

## Canonical Path Finding

The AX helper is not proven on the canonical runtime path. Runtime evidence points to `runtime_v2.planning.strategy_authority.activate_strategy_planning_authority`, while AX materialization evidence validated an isolated pending reproduction with explicit safety metadata.

Current source review shows the common promotion helper can materialize safety context only when incoming pending items carry safety fields. The actual Strategy Planning Authority pending producer did not supply those fields and did not attach the runtime safety context after promotion.

## First Invalid Artifact

`ACTIVE_PENDING_ORDER_PLAN_SAFETY_AUTHORITY`

Run-scoped Data Readiness reports the active pending lifecycle state as `APPROVED`, but its pending safety authority has empty authority and empty `safety_context`, with mismatched fields:

`safety_context.runtime_test_evidence_root, safety_context.runtime_test_profile_id, safety_context.runtime_test_run_id, safety_context.safety_authority, safety_context.safety_business_date, safety_context.safety_decision, safety_context.safety_decision_id, safety_context.safety_policy_version, safety_context.safety_source`

Downstream sell planning artifacts were not reached as the first blocker; this is not yet a sell quantity, PM intent, trading unit, valuation, buy/sell conflict, or submit readiness blocker.

## Classification

- `AX_RUNTIME_BINDING_MISSING`
- `AX_HELPER_NOT_ON_CANONICAL_PATH`
- `SAFETY_BLOCKER_RECURRED`
- `AUTHORITY_UNRESOLVED`

## Repair Boundary

Canonical owner: Strategy Planning Authority pending producer / Pending Promotion boundary.

Repair should bind the runtime safety authority from morning Data Readiness / runtime safety decision into the actual Strategy Planning Authority pending producer so active pending carries `safety_context` and runtime identity metadata before sell_planning Data Readiness consumes it.

No Historical-only switch, silent default, forced BUY, Broker Write, or Runtime Switch should be introduced.

## Existing Run Preservation

All required existing run hashes are preserved: `True`.

## Deliverables

- Human: `docs/phase_reports/phase23_ay_ax_runtime_reproduction_gap_and_sell_planning_halt_differential_audit.md`
- Machine: `reports/phase_reports/phase23_ay_ax_runtime_reproduction_gap_and_sell_planning_halt_differential_audit.json`
- Evidence: `reports/phase23_ay_ax_runtime_reproduction_gap_and_sell_planning_halt_differential_audit`
- Evidence files: `ax_before_after_run_diff.json, canonical_producer_call_path.json, existing_run_hash_preservation.json, first_invalid_artifact.json, isolated_vs_runtime_path_diff.json, new_run_halt_reason.json, pending_safety_metadata_inventory.json, production_contract_classification.json, recommended_repair_boundary.json, safety_blocker_recurrence_check.json`
