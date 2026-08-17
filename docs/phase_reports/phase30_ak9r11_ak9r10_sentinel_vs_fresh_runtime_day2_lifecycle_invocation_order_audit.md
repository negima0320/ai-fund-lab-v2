# Phase30-AK9R11 - AK9R10 Sentinel vs Fresh Runtime Day2 Lifecycle Invocation-Order Audit

## Primary Judgment

```text
AK9R11_ROOT_CAUSE_CLASSIFICATION = RUNTIME_LIFECYCLE_INVOCATION_ORDER_GAP
Secondary = [
  AK9R8_AUTHORITY_NOT_WIRED_TO_FRESH_RUNTIME_PRE_DATA_READINESS,
  AK9R10_TEST_ORCHESTRATION_FIDELITY_GAP,
  DATA_READINESS_LIFECYCLE_CIRCULAR_DEPENDENCY
]

KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = YES
IMPLEMENTATION_REPAIR_REQUIRED = YES
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK9R11
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

The AK9R8 expiration semantic is present in `runtime_v2.pending.lifecycle_runner`,
but the fresh Runtime does not invoke it before Day2 `data_readiness` evaluates
the stale residual `BUY_ITEM_SCOPED_REVIEW` Pending. AK9R10 passed because it
manually invoked `run_pending_lifecycle_review()` before Day2 Data Readiness.
The fresh Runtime executes Day2 `market_refresh` then Day2 `data_readiness`;
no Day2 `pending_lifecycle` job or artifact exists before the HALT.

## Fresh Failure

Target run:

```text
runtime-test-historical-extended-smoke-20260817T090440719415Z
```

Observed:

```text
status = HALT
completed_business_days = ["2022-08-10"]
failed job = 2022-08-12:data_readiness
exit_code = 20
```

Required outputs:

```text
HALT_DIRECT_REASON = historical_safety_temporal_authority_missing
DATA_READINESS_REVIEW_REASONS = [
  "historical_safety_temporal_authority_missing",
  "pending_review_required"
]
ACTIVE_PENDING_STATE_AT_DAY2_ENTRY = REVIEW_REQUIRED
ACTIVE_PENDING_TARGET_SESSION_DATE = 2022-08-10
RESIDUAL_REVIEW_BUY_COUNT = 4
STALE_RESIDUAL_EXPIRED_BEFORE_DATA_READINESS = NO
```

Residual reviewed BUY symbols:

```text
38410, 39950, 47770, 83060
```

The active Pending at Day2 entry has:

```text
review_scope = BUY_ITEM_SCOPED_REVIEW
approved_buy_item_ids = 9
review_required_buy_item_ids = 4
review_required_sell_item_ids = 0
item states = {
  CONSUMED: 9,
  REVIEW_REQUIRED: 4
}
```

This is the same root class as AK9R7: stale residual review-only BUY Pending
from 2022-08-10 blocks 2022-08-12 morning Data Readiness.

## Fresh Runtime Invocation Order

The actual run state and plan show:

```text
FRESH_DAY2_ACTUAL_INVOCATION_ORDER = [
  "2022-08-12:market_refresh",
  "2022-08-12:data_readiness",
  "HALT"
]
```

The planned day order is:

```text
market_refresh
data_readiness
morning
sell_planning
submit
execution
current_valuation_refresh
runtime_state_refresh
```

No `pending_lifecycle` job is in the day plan before `data_readiness`.

Within the failed `run_daily_operation --job data_readiness`, the relevant
order is:

```text
cli_start
environment_composition
operation_contract
runtime_state_refresh
runtime_data_readiness_gate
HALT / REVIEW_REQUIRED
```

Historical Safety is resolved inside Data Readiness and rejects the stale
Pending temporal authority:

```text
safety.reason = historical_safety_temporal_authority_missing
safety.pending_safety_authority.target_session_date = 2022-08-10
safety.pending_safety_authority.safety_business_date_expected = 2022-08-12
safety.pending_safety_authority.mismatched_fields includes pending_lifecycle_state
```

## AK9R8 Invocation Evidence

```text
AK9R8_LIFECYCLE_RUNNER_INVOKED_BEFORE_DATA_READINESS = NO
AK9R8_EXPIRATION_AUTHORITY_EVALUATED = NO
AK9R8_EXPIRATION_ARTIFACT_MATERIALIZED = NO
FIRST_REASON_LIFECYCLE_NOT_INVOKED =
  Fresh runtime has no pre-Day2-data_readiness pending_lifecycle invocation.
  The runtime_test automatic lifecycle hook only runs after an execution job
  when execution/pending_terminalization_evidence.json reports
  PENDING_LIFECYCLE_REQUIRED. Day1 execution reported NOT_REQUIRED.
```

Fresh artifact evidence:

```text
DAY2_PENDING_LIFECYCLE_ARTIFACTS_PRESENT = []
DAY2_EXPIRATION_HISTORY_PRESENT = NO
DAY2_ACTIVE_PENDING_SLOT_CLEARED = NO
```

Day1 execution evidence:

```text
daily/2022-08-10/execution/pending_terminalization_evidence.json:
  status = NOT_REQUIRED
  pending_plan_present = true
  pending_item_count = 13
  pending_consumed = false
  pending_mutated = false
  item_lifecycle_authority.reason = not_mixed_submitted_and_blocked
```

Day1 completion therefore did not trigger the runtime_test automatic
`pending_lifecycle` hook.

## AK9R10 Sentinel Order

The AK9R10 sentinel Day2 sequence is:

```text
AK9R10_SENTINEL_DAY2_INVOCATION_ORDER = [
  "run_pending_lifecycle_review(DAY2)",
  "assert stale residual BUY review EXPIRED",
  "write Day2 runtime operation state fixture",
  "write Day2 market/safety/broker/feature fixtures",
  "evaluate_runtime_data_readiness(DAY2, sell_planning)",
  "run_sell_planning_pending_pipeline(DAY2)"
]
```

The critical difference:

```text
SENTINEL_FRESH_INVOCATION_ORDER_MATCH = NO
FIRST_SENTINEL_VS_FRESH_ORDER_DIVERGENCE =
  AK9R10 explicitly invokes run_pending_lifecycle_review before Day2
  Data Readiness. Fresh runtime executes Day2 data_readiness without first
  invoking pending_lifecycle.
```

## Test Fidelity

```text
AK9R10_ORCHESTRATION_FIDELITY = COMPONENT_REAL_ORDER_SYNTHETIC
```

AK9R10 exercises real Production-common components, including the real
Pending lifecycle runner and real Data Readiness evaluator. It does not
exercise the real runtime daily orchestration entrypoint or the actual
fresh-run job order. Therefore it proves the component semantic works when
called in the correct order, but it does not prove the fresh Runtime invokes
that semantic at the needed boundary.

## Runtime Orchestration Authority

```text
CANONICAL_NEXT_DAY_PENDING_LIFECYCLE_INVOCATION_OWNER =
  runtime_v2.pending.lifecycle_runner owns Pending state transition authority;
  runtime_test daily driver / run_daily_operation job dispatch owns invocation.

EXPECTED_INVOCATION_POINT =
  before consumers that require lifecycle-resolved Pending state, specifically
  before Day2 data_readiness/morning when an active stale Pending slot exists.

ACTUAL_INVOCATION_POINT =
  explicit run_daily_operation --job pending_lifecycle only, or runtime_test
  auto-hook after execution when pending_terminalization_evidence reports
  PENDING_LIFECYCLE_REQUIRED. No pre-Day2-data_readiness invocation exists.
```

## Circular Dependency

```text
DATA_READINESS_PENDING_LIFECYCLE_CIRCULAR_DEPENDENCY = YES
```

Current fresh runtime has this cycle:

```text
Day2 data_readiness requires stale Pending to already be lifecycle-resolved.
The only automatic runtime_test lifecycle hook runs after execution, which is
after data_readiness/morning/submit for that day and cannot be reached while
Day2 data_readiness is halted.
```

## Existing Stale APPROVED Path

```text
EXISTING_STALE_APPROVED_RUNTIME_INVOCATION_PATH =
  runtime_v2.pending.lifecycle_runner can expire APPROVED stale Pending via
  target_session_date_elapsed / approval_expired. In fresh runtime orchestration
  it is invoked either as explicit run_daily_operation --job pending_lifecycle
  or by runtime_test's post-execution _maybe_run_required_pending_lifecycle hook
  when execution/pending_terminalization_evidence.json reports
  PENDING_LIFECYCLE_REQUIRED.

AK9R8_USES_SAME_RUNTIME_INVOCATION_PATH = PARTIAL
```

AK9R8 added the residual-review expiration to the same lifecycle runner, but the
fresh runtime's automatic trigger does not identify this Day1 partial-submitted
residual review shape as requiring next-day lifecycle before Day2 Data
Readiness. Thus AK9R8 shares the state-transition authority path, but not an
effective fresh pre-consumer invocation path.

## Why AK9R10 Passed While Fresh Failed

```text
WHY_AK9R10_PASSED_WHILE_FRESH_FAILED =
  AK9R10 manually sequenced run_pending_lifecycle_review before Day2
  evaluate_runtime_data_readiness, clearing the stale residual Pending slot.
  Fresh runtime_test did not schedule or auto-run pending_lifecycle before
  2022-08-12:data_readiness, so Data Readiness evaluated the still-active
  stale 2022-08-10 REVIEW_REQUIRED Pending and correctly halted.
```

## Repair Boundary

```text
RECOMMENDED_REPAIR_BOUNDARY =
  Phase30-AK9R12 - Fresh Runtime Pending Lifecycle Invocation Wiring Focused Repair
```

Minimum correct boundary:

```text
Wire the existing canonical Pending lifecycle authority into the fresh
Production-common runtime orchestration before Data Readiness consumers that
require lifecycle-resolved Pending state. The repair should invoke existing
runtime_v2.pending.lifecycle_runner semantics and preserve fail-closed behavior.
```

The repair must not:

```text
weaken Data Readiness
ignore stale Pending
carry stale BUY authority
auto-approve reviewed BUY
auto-submit reviewed BUY
create Historical-only behavior
change Strategy / Candidate / PM / PC / PS / sizing / thresholds / caps / Safety
```

## Sentinel Correction

```text
AK9R10_SENTINEL_CORRECTION_REQUIRED = YES
RECOMMENDED_SENTINEL_ENTRYPOINT =
  runtime_test fresh daily orchestration entrypoint, or a narrow orchestration
  integration test that executes the real Day2 job dispatch order including
  the pre-data_readiness pending_lifecycle invocation boundary.
```

The corrected sentinel should prove not only that the components work, but that
the real fresh runtime invokes them in the production order required to advance
from Day1 residual review to Day2 Data Readiness.

## Final Required Judgments

```text
HALT_DIRECT_REASON = historical_safety_temporal_authority_missing
DATA_READINESS_REVIEW_REASONS = [
  "historical_safety_temporal_authority_missing",
  "pending_review_required"
]
ACTIVE_PENDING_STATE_AT_DAY2_ENTRY = REVIEW_REQUIRED
ACTIVE_PENDING_TARGET_SESSION_DATE = 2022-08-10
RESIDUAL_REVIEW_BUY_COUNT = 4
STALE_RESIDUAL_EXPIRED_BEFORE_DATA_READINESS = NO
FRESH_DAY2_ACTUAL_INVOCATION_ORDER = [
  "2022-08-12:market_refresh",
  "2022-08-12:data_readiness",
  "HALT"
]
AK9R8_LIFECYCLE_RUNNER_INVOKED_BEFORE_DATA_READINESS = NO
AK9R8_EXPIRATION_AUTHORITY_EVALUATED = NO
AK9R8_EXPIRATION_ARTIFACT_MATERIALIZED = NO
AK9R10_SENTINEL_DAY2_INVOCATION_ORDER = [
  "run_pending_lifecycle_review",
  "evaluate_runtime_data_readiness",
  "run_sell_planning_pending_pipeline"
]
SENTINEL_FRESH_INVOCATION_ORDER_MATCH = NO
FIRST_SENTINEL_VS_FRESH_ORDER_DIVERGENCE =
  sentinel runs pending_lifecycle before Day2 data_readiness; fresh does not
AK9R10_ORCHESTRATION_FIDELITY = COMPONENT_REAL_ORDER_SYNTHETIC
CANONICAL_NEXT_DAY_PENDING_LIFECYCLE_INVOCATION_OWNER =
  lifecycle_runner owns transition; runtime orchestration owns invocation
EXPECTED_INVOCATION_POINT = before Day2 data_readiness when stale active Pending exists
ACTUAL_INVOCATION_POINT = none before Day2 data_readiness; only explicit job or post-execution hook
DATA_READINESS_PENDING_LIFECYCLE_CIRCULAR_DEPENDENCY = YES
EXISTING_STALE_APPROVED_RUNTIME_INVOCATION_PATH =
  explicit pending_lifecycle job or runtime_test post-execution required hook
AK9R8_USES_SAME_RUNTIME_INVOCATION_PATH = PARTIAL
DAY2_PENDING_LIFECYCLE_ARTIFACTS_PRESENT = []
DAY2_EXPIRATION_HISTORY_PRESENT = NO
DAY2_ACTIVE_PENDING_SLOT_CLEARED = NO
WHY_AK9R10_PASSED_WHILE_FRESH_FAILED =
  manual pre-data_readiness lifecycle invocation in sentinel, absent in fresh runtime
AK9R11_ROOT_CAUSE_CLASSIFICATION = RUNTIME_LIFECYCLE_INVOCATION_ORDER_GAP
RECOMMENDED_REPAIR_BOUNDARY =
  Fresh Runtime Pending Lifecycle Invocation Wiring Focused Repair
AK9R10_SENTINEL_CORRECTION_REQUIRED = YES
RECOMMENDED_SENTINEL_ENTRYPOINT =
  real runtime_test fresh daily orchestration / job dispatch entrypoint
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = YES
IMPLEMENTATION_REPAIR_REQUIRED = YES
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

## Recommended Next Task

```text
Phase30-AK9R12 - Fresh Runtime Pending Lifecycle Invocation Wiring Focused Repair
```
