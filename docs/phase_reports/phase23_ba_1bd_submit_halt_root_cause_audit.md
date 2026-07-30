# Phase23-BA 1BD Submit HALT Root Cause Audit

## Primary Judgment

```text
PHASE23_BA_SUBMIT_HALT_ROOT_CAUSE_AUDIT_COMPLETE
```

## Target Run

- run_id: `runtime-test-historical-smoke-20260730T042431441297Z`
- business_date: `2026-07-06`
- status: `HALT`
- halt_stage: `submit`
- runtime_test_exit_code: `30`
- inner_runtime_cli_exit_code: `20`
- completed_days: `[]`

## Direct Root Cause

Submit stopped at the plan-level Submit Guard policy consistency check before item-level guard/preflight.

```text
policy_mismatch:pending_policy_version,pending_policy_source,pending_policy_hash
```

The lowest-level failing consumer is:

```text
runtime_v2.submit.pipeline.run_submit_pipeline
  -> _policy_consistency_evidence
```

The pending producer/consumer contract mismatch is:

| Field | Pending Actual | Submit Active Expected |
|---|---|---|
| policy_version | `phase22_strategy_planning_authority` | `capital_deployment_v1` |
| policy_source | `rp-2026-07-06-31330-buy_new-b4902c667ef8f3e2` | `configs/runtime_v2/capital_deployment.json` |
| pending_policy_hash | `sha256:ead3d36e5d1b636251813c6724a6a83c2659dc74ba6fd8fba49b749f16bb5ccb` | `sha256:ff549e05089b771dc859bab4e12691ff1492c8ae284acccaca86e206d8c8cadf` |

## First Invalid Artifact

```text
.runtime/pending_order_plan/pending_order_plan.json
```

The artifact is structurally readable and active, but its policy authority fields are semantically invalid for the Submit consumer. `strategy_authority` writes Strategy Planning lineage into pending policy fields, while Submit Guard reads those fields as active Capital Deployment / Submit Guard policy authority.

## Pending Submit Input

- pending state: `APPROVED`
- pending_plan_id: `pending-strategy-plan-historical-2026-07-06-5a90f8bcb1723448`
- target_session_date: `2026-07-06`
- intended_submit_date: `2026-07-06`
- item count: `9`
- approved item count: `9`
- symbols: `31330, 43780, 45640, 45960, 45970, 66340, 67400, 89180, 94320`
- safety decision: `NEUTRAL`
- safety decision id: `historical-neutral-safety:2026-07-06`

All pending items are BUY / MARKET with positive quantities. The item-level Submit Guard was not reached because policy consistency failed first.

## Sell Planning Confirmation

Sell Planning completed with exit_code 0.

```text
sell planning no position: existing pending continuity preserved
```

Evidence:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T042431441297Z/daily/2026-07-06/sell_planning/runtime_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T042431441297Z/daily/2026-07-06/sell_planning/pending_continuity_evidence.json`

## Previous Blocker Check

| Reason | Presence | Direct Submit HALT |
|---|---:|---:|
| `target_weight_authority_unresolved` | `absent` | `False` |
| `invalid_quality_score` | `absent` | `False` |
| `review_required_quantity_authority` | `absent` | `False` |
| `REVIEW_REQUIRED_MISSING_PRICE` | `absent` | `False` |
| `strategy_plan_quantity_unresolved` | `absent` | `False` |
| `historical_trading_calendar_authority_missing` | `absent` | `False` |
| `current_valuation_previous_trading_date_missing` | `absent` | `False` |
| `historical_pending_safety_authority_mismatch` | `present` | `False` |
| `historical_safety_temporal_authority_missing` | `absent` | `False` |
| `pending_safety_evidence_missing` | `absent` | `False` |


`historical_pending_safety_authority_mismatch` is present only as nested Data Readiness/Morning component detail for the initial EMPTY pending state. The effective statuses are READY and it is not the Submit HALT reason.

## Classification

- Root Cause categories: `SCHEMA_MISMATCH`, `AUTHORITY_UNRESOLVED`, `EXPECTED_FAIL_CLOSED`
- Domain: `Submit Guard`, `Pending Generation Binding`
- Production Contract Violation: `YES`
- Historical-only problem: `NO`
- Production/Demo/Historical common issue: `YES`
- Expected fail-closed: `YES`

## Canonical Authority Owner

Submit Guard active Capital Deployment policy authority and Strategy Planning per-item lineage are separate authorities. The current pending schema/producer path collapses them into one policy field family, causing Submit to compare Strategy Planning lineage against the active Submit Guard policy.

## Recommended Repair Boundary

Next repair should be Production-common and should split or explicitly map:

```text
planning lineage policy authority
submit guard / capital deployment policy authority
```

Do not bypass Submit Guard or disable policy consistency. The fix should preserve both lineages and make Submit compare the canonical Submit Guard policy authority only.

## Evidence

Evidence directory:

```text
reports/phase23_ba_1bd_submit_halt_root_cause_audit/
```

Machine report:

```text
reports/phase_reports/phase23_ba_1bd_submit_halt_root_cause_audit.json
```

## Existing Run Preservation

Existing run hash preservation: `True`

Protected runs:

- `runtime-test-historical-smoke-20260730T042431441297Z`
- `runtime-test-historical-smoke-20260730T033913848127Z`
- `runtime-test-historical-smoke-20260730T030213466506Z`

## Final Gate

```text
REPAIR_REQUIRED = YES
READY_FOR_REPAIR = YES
READY_FOR_1BD_RERUN = NO
```
