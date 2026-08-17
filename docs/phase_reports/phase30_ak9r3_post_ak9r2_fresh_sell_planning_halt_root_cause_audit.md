# Phase30-AK9R3 - Post-AK9R2 Fresh Sell-Planning HALT Root-Cause Audit

## Scope

Task ID: `Phase30-AK9R3`

Type: `READ_ONLY_FRESH_RUNTIME_ROOT_CAUSE_AUDIT`

Target run:

```text
runtime-test-historical-extended-smoke-20260817T061136142544Z
```

Observed:

```text
failed job = 2022-08-10:sell_planning
completed_days = []
Runtime CLI exit code = 20
```

No implementation, rollback, replay, resume, fresh run, target-run mutation,
Strategy change, Pending schema change, or Sell Planning semantic change was
performed.

## Primary Judgment

```text
POST_AK9R2_SELL_PLANNING_HALT_CLASSIFICATION =
  AK9R1_PENDING_STATE_COMPATIBILITY_REGRESSION

KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = YES
IMPLEMENTATION_REPAIR_REQUIRED = YES
```

The first fresh blocker after AK9R2 readiness is a Sell Planning pre-pipeline
Data Readiness / Historical Safety authority incompatibility with the AK9R1
partial-approved `BUY_ITEM_SCOPED_REVIEW` pending shape.

AK9R1 created a valid new pending shape:

```text
state = REVIEW_REQUIRED
review_scope = BUY_ITEM_SCOPED_REVIEW
plan_overall_status = APPROVED_WITH_BUY_ITEM_SCOPED_REVIEW
approved_buy_item_ids = 9
review_required_buy_item_ids = 4
sell_continuation_allowed = true
```

The historical Sell Planning safety/readiness gate still recognizes
`BUY_ITEM_SCOPED_REVIEW` continuation only when `approved_buy_item_ids` is empty,
matching the older Phase24-IE batch-atomic pending shape. Therefore it classified
the pending as `pending_review_required`, which made historical neutral safety
resolution fail with `historical_safety_temporal_authority_missing`.

## Exact HALT Producer

```text
HALT_DIRECT_PRODUCER =
  runtime_v2.data_readiness / historical safety temporal authority gate for
  run_daily_operation --job sell_planning

HALT_DIRECT_REASON = historical_safety_temporal_authority_missing

FIRST_NON_PASS_LAYER =
  sell_planning pre-pipeline Data Readiness / Safety authority

HALT_DIRECT_ARTIFACT =
  reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260817T061136142544Z/daily/2022-08-10/sell_planning/runtime_manifest.json
```

Supporting artifacts:

```text
sell_planning/cli_result.json:
  exit_code = 20

sell_planning/runtime_manifest.json:
  final_state = REVIEW_REQUIRED
  final_safety_status = REVIEW_REQUIRED
  final_safety_reason = historical_safety_temporal_authority_missing
  data_readiness_status = REVIEW_REQUIRED
  data_readiness_review_reasons =
    historical_safety_temporal_authority_missing
    pending_review_required

sell_planning/data_readiness_authority.json:
  status = REVIEW_REQUIRED
  reason = historical_safety_temporal_authority_missing
  review_reasons =
    historical_safety_temporal_authority_missing
    pending_review_required
```

Sell Planning pipeline evidence did not execute:

```text
sell_planning/pending_continuity_evidence.json:
  status = NOT_EXECUTED
  reason = historical_safety_temporal_authority_missing
```

## Morning State Before Sell Planning

Morning completed and wrote same-day Pending:

```text
morning/planning_evidence.json:
  status = PASS
  pending_commit_status = COMMITTED_CURRENT
  pending_item_count = 13
  plan_count = 19
```

Current pending:

```text
PRE_SELL_BUY_PENDING_COUNT = 13
PRE_SELL_APPROVED_BUY_COUNT = 9
PRE_SELL_REVIEW_BUY_COUNT = 4
```

Pending state:

```text
pending_plan_id = pending-strategy-plan-historical-2022-08-10-73935657fc0f9296
state = REVIEW_REQUIRED
review_scope = BUY_ITEM_SCOPED_REVIEW
plan_overall_status = APPROVED_WITH_BUY_ITEM_SCOPED_REVIEW
buy_items_status = REVIEW_REQUIRED
sell_items_status = NOT_PRESENT
sell_continuation_allowed = true
target_session_date = 2022-08-10
```

Approved BUY symbols:

```text
23700, 23880, 47840, 61980, 66590, 76470, 89180, 93180, 94320
```

Reviewed BUY symbols:

```text
38410, 39950, 47770, 83060
```

The pending contains AK9R1B evidence such as
`canonical_discrete_quantity_submit_authority` for approved BUY items. Those
payloads are not read by the Sell Planning composition gate and are not the
direct blocker.

## Sell Signal State

```text
SELL_SIGNAL_COUNT = 0
SELL_ITEM_COUNT = 0
MANDATORY_SELL_COUNT = 0
```

Evidence:

```text
position_management/pm_decisions.json:
  pm_status = NO_POSITION
  pm_reason = current_position_missing
  pm_decision_count = 0
  decisions = []

strategy/position_management.json:
  positions = []
```

This is a no-position / no-SELL day. The expected behavior is no-signal
preservation of the existing BUY pending, not composition with SELL items.

## AK8R Pending Composition

```text
AK8R_EXISTING_BUY_PENDING_READ = NO
AK8R_BUY_PENDING_PRESERVABLE = NOT_APPLICABLE
AK8R_COMPOSITION_ATTEMPTED = NO
AK8R_COMPOSITION_STATUS =
  NOT_EXECUTED_PRE_PIPELINE_DATA_READINESS_REVIEW_REQUIRED
```

AK8R composition itself was not reached. The blocker is earlier:
Sell Planning Data Readiness rejected the active pending and safety authority
before `read_active_buy_pending()` / no-signal preservation could execute.

## Pending State Compatibility

```text
AK9R1_PENDING_STATE_COMPATIBLE_WITH_SELL_PLANNING = NO
```

The incompatible shape is:

```text
state = REVIEW_REQUIRED
review_scope = BUY_ITEM_SCOPED_REVIEW
approved_buy_item_ids != []
review_required_buy_item_ids != []
sell_continuation_allowed = true
```

Existing historical readiness helper `_pending_buy_item_scoped_sell_continuation_ready`
still has the older Phase24-IE assumption:

```text
if payload.get("approved_buy_item_ids") not in ([], (), None):
    return False
```

The pending composition helper has the same older assumption:

```text
if plan.approved_buy_item_ids or any(
    item.side.upper() == "BUY" and item.pending_item_id in set(plan.approved_item_ids)
    for item in plan.items
):
    return False
```

That older contract was correct for batch-atomic `BUY_ITEM_SCOPED_REVIEW` where
all BUY ids were non-submittable. AK9R1 intentionally introduced a narrower
partial-approved shape where PASS BUY ids are submittable and reviewed BUY ids
remain fail-closed. Sell Planning readiness has not been migrated to understand
that shape.

## AK9R1B Payload Compatibility

```text
AK9R1B_PAYLOAD_COMPATIBLE_WITH_SELL_PLANNING = YES
```

AK9R1B evidence is present in Pending feasibility payloads, but the direct
failure occurs before Sell Planning parses or composes those item payloads. The
failure condition is the top-level AK9R1 partial-approved pending state, not the
canonical discrete quantity payload itself.

## First Synthetic vs Fresh Divergence

```text
FIRST_SYNTHETIC_VS_FRESH_DIVERGENCE =
  Fresh runtime feeds a BUY-only Pending with state=REVIEW_REQUIRED,
  review_scope=BUY_ITEM_SCOPED_REVIEW, non-empty approved_buy_item_ids, and
  non-empty review_required_buy_item_ids into Sell Planning data readiness on a
  no-position / no-SELL day. AK9R2 did not include this exact Sell Planning
  pre-pipeline readiness sentinel.
```

AK9R2 covered:

- AK9R1 partial BUY submission at Submit;
- AK9R1B selected-position double authority removal;
- AK8R mixed BUY+SELL pending composition;
- older BUY item-scoped review no-signal preservation.

It did not cover:

```text
BUY-only partial-approved BUY_ITEM_SCOPED_REVIEW Pending
-> Sell Planning data readiness
-> no-position / no-SELL path
-> preserve original pending without HALT
```

## Fresh State Integrity

```text
FRESH_STATE_INTEGRITY = PASS
```

Evidence:

```text
plan.json:
  baseline_compatibility_status = PASS
  pending_active = false
  pending_state = EMPTY
  ledger_date = 2022-08-10
  initial cash = 1,000,000
  initial positions = 0
  initial pending = 0

fresh_run_summary.json:
  backup_result = PASS
  completed_days = []
  completed_business_day_count = 0
```

The HALT was produced inside the fresh run after morning pending generation,
not inherited from stale initial pending or stale positions.

## Why AK9R2 Missed This

```text
WHY_AK9R2_SUITE_MISSED_THIS =
  Missing sentinel for AK9R1 partial-approved BUY_ITEM_SCOPED_REVIEW Pending
  entering Sell Planning data readiness on a BUY-only/no-position/no-SELL day.
  Existing sentinels covered older all-reviewed BUY_ITEM_SCOPED_REVIEW no-signal
  preservation and mixed BUY+SELL composition, but not non-empty
  approved_buy_item_ids under plan-level REVIEW_REQUIRED before Sell Planning.
```

## Required Final Judgments

```text
HALT_DIRECT_PRODUCER =
  runtime_v2.data_readiness / historical safety temporal authority gate for sell_planning

HALT_DIRECT_REASON = historical_safety_temporal_authority_missing
FIRST_NON_PASS_LAYER = sell_planning pre-pipeline Data Readiness / Safety authority
PRE_SELL_BUY_PENDING_COUNT = 13
PRE_SELL_APPROVED_BUY_COUNT = 9
PRE_SELL_REVIEW_BUY_COUNT = 4
SELL_SIGNAL_COUNT = 0
SELL_ITEM_COUNT = 0
AK8R_EXISTING_BUY_PENDING_READ = NO
AK8R_COMPOSITION_STATUS = NOT_EXECUTED_PRE_PIPELINE_DATA_READINESS_REVIEW_REQUIRED
AK9R1_PENDING_STATE_COMPATIBLE_WITH_SELL_PLANNING = NO
AK9R1B_PAYLOAD_COMPATIBLE_WITH_SELL_PLANNING = YES
FIRST_SYNTHETIC_VS_FRESH_DIVERGENCE =
  BUY-only partial-approved BUY_ITEM_SCOPED_REVIEW Pending entered Sell Planning data readiness
POST_AK9R2_SELL_PLANNING_HALT_CLASSIFICATION = AK9R1_PENDING_STATE_COMPATIBILITY_REGRESSION
FRESH_STATE_INTEGRITY = PASS
WHY_AK9R2_SUITE_MISSED_THIS =
  Missing no-position/no-SELL Sell Planning readiness sentinel for partial-approved BUY_ITEM_SCOPED_REVIEW
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = YES
IMPLEMENTATION_REPAIR_REQUIRED = YES
```

## Implementation Authorization

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK9R3
```

## Recommended Next Task

```text
Phase30-AK9R4 - AK9R1 Partial-Approved BUY_ITEM_SCOPED_REVIEW Sell-Planning Readiness Repair
```
