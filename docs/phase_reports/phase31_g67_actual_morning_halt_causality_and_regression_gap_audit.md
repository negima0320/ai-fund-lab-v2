# Phase31-G67 — Actual Morning HALT Causality & Regression Gap Audit

## PRIMARY_JUDGMENT

PHASE31_G67_ACTUAL_MORNING_HALT_CAUSALITY_CONFIRMED_REGRESSION_GAP_IDENTIFIED

The 2022-10-03 morning HALT in
`runtime-test-historical-extended-smoke-20260823T135454942984Z` is the same
failure class as the previous G66 HALT run. The direct cause is not Position
Sizing logic itself and not Runtime Planning redecision. The first actual
state divergence is inside the final Portfolio Construction publication path:
the actual CLI-produced `lot_aware_final_reallocation.capital_competition`
is generated with an empty business-date / missing budget-envelope context,
so its top-level `canonical_multi_allocation_deployment_set.v1` contains zero
security allocations and zero G61 executable rows.

G67 is READ-ONLY. No code, Strategy, Runtime, threshold, weight, or Market
Quality semantics were changed.

## Target

```text
TARGET_RUN = runtime-test-historical-extended-smoke-20260823T135454942984Z
TARGET_BOUNDARY = 2022-10-03:morning
```

Previous comparison run:

```text
PREVIOUS_RUN = runtime-test-historical-extended-smoke-20260823T134411283008Z
```

## Direct HALT Evidence

For `runtime-test-historical-extended-smoke-20260823T135454942984Z`:

```text
fresh_run_summary.status = HALT
fresh_run_summary.exit_code = 30
fresh_run_summary.error = Runtime CLI stopped at 2022-10-03:morning with exit code 10
morning/cli_result.exit_code = 10
morning/planning_evidence.status = BLOCKED
morning/planning_evidence.reason = strategy_runtime_planning_blocked
morning/planning_evidence.planning_consumer_eligibility = BLOCKED
morning/planning_evidence.pending_commit_status = NOT_COMMITTED_BLOCKED_EMPTY_UNSCOPED
morning/planning_evidence.plan_count = 0
morning/planning_evidence.pending_item_count = 0
morning/planning_evidence.reason_codes =
  - G61_PS_CONSUMPTION_BLOCK
  - portfolio_add_candidate_maps_to_buy_new
  - portfolio_exclude_maps_to_no_plan
  - upstream_block_propagation:position_sizing_or_portfolio_construction
```

Therefore:

```text
MORNING_HALT_ROOT_CAUSE = strategy_runtime_planning_blocked caused by upstream G61_PS_CONSUMPTION_BLOCK
```

## Stage Trace

### Portfolio Policy

Portfolio Policy was not the first failure point. The later failure is due to
the final PC publication path losing or failing to pass the authoritative risk
pacing / budget-envelope context into the lot-aware final competition builder.

### Portfolio Construction

Actual accepted PC artifact:

```text
business_date = 2022-10-03
producer_result_status = PASS
runtime_consumer_eligibility = ELIGIBLE
artifact_lifecycle_status = ACCEPTED
allocation_decided = True
G66_LOT_AWARE_MULTI_ALLOCATION_PUBLISHED_TOP_LEVEL = present
pre_lot_capital_competition = present
```

Top-level published competition in the accepted PC artifact:

```text
canonical_multi_allocation_deployment_set.business_date = ""
lot_aware_allocation_to_sizing_compatibility.business_date = ""
security_allocations = 0
compatibility_rows = 0
lot_executable_count = 0
compatibility_state_distribution = {}
reason_codes include CAPITAL_BUDGET_ENVELOPE_MISSING
status = FAIL_CLOSED
available_incremental_budget = 0.0
```

Pre-lot competition preserved under `pre_lot_capital_competition`:

```text
canonical_multi_allocation_deployment_set.business_date = 2022-10-03
lot_aware_allocation_to_sizing_compatibility.business_date = 2022-10-03
security_allocations = 22
compatibility_rows = 22
lot_executable_count = 0
compatibility_state_distribution = {INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED: 22}
```

Actual `lot_aware_final_reallocation` evidence:

```text
status = PASS
business_date = missing
phase29_l19_reallocation_iterations = 22
phase29_l19_candidate_exhaustion_status = ALLOCATED_OR_NOT_APPLICABLE
capital_competition present = YES
capital_competition.authority.business_date = ""
capital_competition.canonical_multi_allocation_deployment_set.business_date = ""
capital_competition.canonical_multi_allocation_deployment_set.security_allocations = []
capital_competition.canonical_multi_allocation_deployment_set.lot_aware_allocation_to_sizing_compatibility.compatibility_rows = []
capital_competition.canonical_multi_allocation_deployment_set.lot_aware_allocation_to_sizing_compatibility.lot_executable_count = 0
capital_competition.canonical_multi_allocation_deployment_set.reason_codes include CAPITAL_BUDGET_ENVELOPE_MISSING
```

This proves that the G66 top-level promotion hook is present, but it promotes
an already invalid / under-bound final competition payload.

### Position Sizing

Actual PS artifact:

```text
producer_result_status = BLOCK
runtime_consumer_eligibility = NOT_ELIGIBLE
artifact_lifecycle_status = DRAFT
reason_codes = [G61_COMPATIBILITY_DATE_MISMATCH]
positive_quantity_count = 0
positions = 50
```

G61 consumption summary:

```text
status = BLOCK
business_date = 2022-10-03
allocation_count = 0
lot_executable_count = 0
g61_compatibility_consumed_by_ps = False
reason_codes = [G61_COMPATIBILITY_DATE_MISMATCH]
canonical_multi_allocation_set_hash = 7b23e81fd43d3dafc20fec6a2eba2228ffe43600e61f04d5e12a572b439c8747
compatibility_hash = 57a39d7bd2bbf4f5810886a032f0591fe0ae25321e5ca046d8fdfe7513a6c93d
```

PS is correctly fail-closing because the PC top-level G61 compatibility is not
date-bound.

### Runtime Planning

Actual Runtime Planning artifact:

```text
producer_result_status = BLOCK
runtime_consumer_eligibility = ELIGIBLE
artifact_lifecycle_status = DRAFT
plan_count = 22
positive BUY_NEW / BUY_ADD planned quantity count = 0
reason_codes =
  - G61_PS_CONSUMPTION_BLOCK
  - portfolio_add_candidate_maps_to_buy_new
  - portfolio_exclude_maps_to_no_plan
  - upstream_block_propagation:position_sizing_or_portfolio_construction
```

Runtime Planning is propagating the PS block and does not independently
redecide capital priority.

## Previous Run Comparison

The previous run,
`runtime-test-historical-extended-smoke-20260823T134411283008Z`, has the same
stage shape:

```text
morning/planning_evidence.status = BLOCKED
morning/planning_evidence.reason = strategy_runtime_planning_blocked
PC accepted artifact has G66 reason code = YES
top-level canonical_multi_allocation_deployment_set.business_date = ""
top-level G61 compatibility.business_date = ""
top-level security_allocations = 0
top-level lot_executable_count = 0
PS producer_result_status = BLOCK
PS reason_codes = [G61_COMPATIBILITY_DATE_MISMATCH]
Runtime Planning reason_codes include G61_PS_CONSUMPTION_BLOCK
Runtime BUY/ADD positive planned quantity count = 0
```

Therefore:

```text
SAME_AS_PREVIOUS_G66_HALT = YES
NEW_DEGRADATION_EVIDENCE = NO
```

The run-to-run hashes differ, but the semantic failure is identical.

## First Divergence Stage

```text
FIRST_DIVERGENCE_STAGE =
  Portfolio Construction final lot-aware publication:
  _produce_lot_aware_final_portfolio_construction()
  -> apply_lot_aware_final_reallocation()
  -> lot_aware_final_reallocation.capital_competition
```

The first artifact state that violates the expected contract is not the
accepted PC top-level replacement itself. It is the payload being promoted:
`lot_aware_final_reallocation.capital_competition` is already missing the date
and budget-envelope context needed for `canonical_multi_allocation_deployment_set`
and G61 compatibility.

Actual orchestration code path:

```text
shadow_runtime._produce_lot_aware_final_portfolio_construction()
  calls apply_lot_aware_final_reallocation(
    members=...,
    lot_feasibility_rows=...,
    target_gross_exposure=...,
    single_name_cap=...,
  )
```

The actual call does not pass:

```text
business_date
risk_pacing_evidence / incremental_capital_budget_envelope
```

Inside `apply_lot_aware_final_reallocation()`, the final capital competition is
rebuilt with `risk_pacing_evidence={}`. Consequently
`_canonical_multi_allocation_deployment_set()` sees no authoritative
`incremental_capital_budget_envelope`, returns `CAPITAL_BUDGET_ENVELOPE_MISSING`,
sets available budget to zero, and emits no security allocations or G61
compatibility rows.

## G66 Regression Gap

Regression inspected:

```text
tests/strategy/test_phase31_g66_publication_path_integration.py
```

The regression is useful but not actual CLI equivalent.

Actual CLI path:

```text
portfolio_construction_draft
-> position_sizing_preflight
-> _produce_lot_aware_final_portfolio_construction()
-> apply_lot_aware_final_reallocation()
-> promote_final_portfolio_construction_for_production()
-> position_sizing
-> runtime_planning
```

G66 focused regression path:

```text
read actual accepted PC artifact
-> build_capital_competition_framework(
     business_date=BUSINESS_DATE,
     incremental_budget_evidence=pc_actual.incremental_budget_reconciliation,
     risk_pacing_evidence=pc_actual.portfolio_policy_allocation_authority.risk_pacing_evidence,
   )
-> inject that repaired competition into lot_aware_final_reallocation
-> promote_final_portfolio_construction_for_production()
-> build_position_sizing_payload()
-> build_runtime_planning_payload()
```

Specific gap:

```text
REGRESSION_COVERAGE_GAP = YES
G66_FOCUSED_REGRESSION_ACTUAL_CLI_EQUIVALENT = NO
```

Why it missed the HALT:

- Missing orchestration step coverage: the test does not call
  `_produce_lot_aware_final_portfolio_construction()`.
- Wrong publication input: the test injects a newly rebuilt, date-bound,
  budget-bound `capital_competition` instead of validating the competition
  produced by `apply_lot_aware_final_reallocation()` under actual CLI inputs.
- Date binding timing gap: the test supplies `business_date=2022-10-03`
  directly to `build_capital_competition_framework()`, while actual
  orchestration does not pass `business_date` into final reallocation.
- Budget-envelope propagation gap: the test supplies
  `portfolio_policy_allocation_authority.risk_pacing_evidence`, while actual
  final reallocation receives no risk pacing / envelope evidence.
- Consumer path mismatch: the test verifies PS/RP after replacing the broken
  final competition, so it proves the downstream consumer path can work, but
  not that actual CLI publishes the same payload.

This is not a generic fixture difference. It is a specific orchestration
publication-input gap at the final PC producer boundary.

## Required Conclusions

MORNING_HALT_ROOT_CAUSE =
`strategy_runtime_planning_blocked` caused by PS `G61_COMPATIBILITY_DATE_MISMATCH`,
propagated as Runtime Planning `G61_PS_CONSUMPTION_BLOCK`.

SAME_AS_PREVIOUS_G66_HALT = YES

FIRST_DIVERGENCE_STAGE =
`Portfolio Construction final lot-aware publication / apply_lot_aware_final_reallocation capital_competition build`

G66_PUBLICATION_REPAIR_PRESENT_IN_ACTUAL_ARTIFACT = YES

TOP_LEVEL_PC_DATE_BOUND = NO

G61_DATE_BOUND = NO

G61_SECURITY_ALLOCATIONS_GT_0 = NO

G61_LOT_EXECUTABLE_GT_0 = NO

PS_POSITIVE_QUANTITY_GT_0 = NO

RUNTIME_BUY_PLAN_GT_0 = NO

G66_FOCUSED_REGRESSION_ACTUAL_CLI_EQUIVALENT = NO

REGRESSION_COVERAGE_GAP = YES

NEW_DEGRADATION_EVIDENCE = NO

## Minimal Repair Boundary For Next Task

Owner:

```text
Portfolio Construction publication orchestration
```

Boundary:

```text
shadow_runtime._produce_lot_aware_final_portfolio_construction()
-> portfolio_construction.apply_lot_aware_final_reallocation()
-> lot_aware_final_reallocation.capital_competition
```

Minimal next repair should make the actual final PC producer pass the same
canonical decision-time context used by the focused regression:

- `business_date`
- authoritative risk pacing evidence containing
  `incremental_capital_budget_envelope`
- any required incremental budget / lot sizing context already present in the
  draft or policy authority

The repair should not change Market Quality, Risk Pacing semantics, candidate
ranking, eligibility, thresholds, weights, PS quantity ownership, Runtime
capital priority, or BUY/SELL independence.

## Safety / Execution Flags

IMPLEMENTATION_CHANGED = NO

CODE_CHANGED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

FUTURE_INFORMATION_USED = NO

HISTORICAL_OUTCOME_STRATEGY_INPUT_USED = NO

## NEXT_TASK_RECOMMENDATION

Repair only the final PC production publication boundary so actual
`_produce_lot_aware_final_portfolio_construction()` produces a date-bound,
budget-envelope-bound `lot_aware_final_reallocation.capital_competition`.

Then update the G66/G67 regression so it exercises the actual final PC producer
path rather than injecting a rebuilt competition directly.
