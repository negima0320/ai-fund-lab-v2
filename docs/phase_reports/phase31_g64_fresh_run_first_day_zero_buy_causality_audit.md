# Phase31-G64 — Fresh-Run First-Day Zero-BUY Causality Audit

## PRIMARY_JUDGMENT

PHASE31_G64_FIRST_DAY_ZERO_BUY_CAUSED_BY_G61_LOT_CONTEXT_PROPAGATION_GAP

The first-day 2022-10-03 Cash 100% / Exposure 0% / Position 0 result in
`runtime-test-historical-extended-smoke-20260823T131305201581Z` was not caused by
Market Quality directly suppressing BUY, Submit rejecting orders, or Runtime
re-deciding capital priority.

The direct causal chain is:

Candidate evidence produced BUY opportunities
-> Portfolio Policy produced authoritative incremental budget
-> PC multi-allocation produced non-zero shadow security allocations
-> G61 lot-aware compatibility received insufficient lot sizing context for all
allocated securities and fail-closed all rows
-> Position Sizing consumed G61 compatibility and produced zero quantity for all
BUY candidates
-> Runtime Planning bound to PS zero quantity and emitted only NO_ORDER plans
-> Submit correctly produced NO_SUBMISSION_REQUIRED
-> Execution produced zero fills and zero ledger mutations.

`G61_EXPLICIT_RESIDUAL_RESOLUTION_REQUIRED` was not the direct Runtime
suppression reason for all BUYs. Runtime guard suppression count was zero.
The direct Runtime no-order reason was `zero_quantity_delta` for all plans. The
upstream reason for that zero quantity was the G61 compatibility state
`INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED` on all 22 PC security allocations.

## Target

- TARGET_RUN_ID: `runtime-test-historical-extended-smoke-20260823T131305201581Z`
- TARGET_DATE: `2022-10-03`
- EXECUTION_MODE: READ_ONLY_ACTUAL_ARTIFACT_AUDIT
- CODE_CHANGED: NO
- FRESH_RUN_EXECUTED_BY_CODEX: NO
- RESUME_EXECUTED_BY_CODEX: NO
- REPLAY_EXECUTED_BY_CODEX: NO
- LONG_HISTORICAL_EXECUTED_BY_CODEX: NO
- FUTURE_INFORMATION_USED: NO
- HISTORICAL_OUTCOME_PARAMETER_SELECTION_USED: NO

## Evidence Paths

- Candidate / quality:
  `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T131305201581Z/daily/2022-10-03/strategy/buy_quality_decisions.json`
- Portfolio Policy:
  `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T131305201581Z/daily/2022-10-03/strategy/portfolio_policy.json`
- Portfolio Construction:
  `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T131305201581Z/daily/2022-10-03/strategy/portfolio_construction.json`
- Position Sizing:
  `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T131305201581Z/daily/2022-10-03/strategy/position_sizing.json`
- Runtime Planning:
  `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T131305201581Z/daily/2022-10-03/strategy/runtime_planning.json`
- Submit authority:
  `.runtime/runtime_state/run_manifest/2022-10-03/runtime-v2-submit-2022-10-03-20260823T131507.041542+0000.json`
- Execution submitted-order authority:
  `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T131305201581Z/daily/2022-10-03/execution/submitted_order_authority.json`
- Execution fills:
  `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T131305201581Z/daily/2022-10-03/execution/fills.json`
- Ledger append evidence:
  `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T131305201581Z/daily/2022-10-03/execution/ledger_append_evidence.json`

## Causal Counts

| Stage | Result |
|---|---:|
| BUY quality decision count | 50 |
| BUY quality `FULL_ALLOCATION_ELIGIBLE` | 1 |
| BUY quality `REDUCED_ALLOCATION_ONLY` | 22 |
| BUY quality valid allocation-like decisions | 23 |
| PC portfolio members | 50 |
| PC `ADD_CANDIDATE` members | 22 |
| PC multi-allocation security allocations | 22 |
| PC non-zero security allocation rows | 22 |
| PC total security allocation weight | 0.733506 |
| PC cash allocation weight | 0.006494 |
| PC available incremental budget | 0.74 |
| G61 compatibility rows | 22 |
| G61 lot-executable rows | 0 |
| G61 compatibility-executable rows | 0 |
| G61 unexecutable rows | 22 |
| G61 `INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED` rows | 22 |
| G61 lower-priority rows requiring explicit residual resolution | 21 |
| PS positions | 50 |
| PS G61-consumed rows | 22 |
| PS positive `quantity_delta_candidate` rows | 0 |
| PS positive `final_quantity_delta` rows | 0 |
| PS positive `discrete_authorized_quantity` rows | 0 |
| Runtime plans | 22 |
| Runtime BUY_NEW plans | 0 |
| Runtime BUY_ADD plans | 0 |
| Runtime NO_ORDER plans | 22 |
| Runtime NO_ORDER `zero_quantity_delta` | 22 |
| G63 runtime guard suppression count | 0 |
| Submit submitted count | 0 |
| Execution submitted order count | 0 |
| Execution fill count | 0 |
| Ledger order append count | 0 |
| Ledger execution append count | 0 |
| Ledger cash append count | 0 |
| Ledger position append count | 0 |

## Candidate / Opportunity

`buy_quality_decisions.json` produced 50 decisions:

- `FULL_ALLOCATION_ELIGIBLE`: 1
- `REDUCED_ALLOCATION_ONLY`: 22
- `BUY_WAIT`: 16
- `REJECT`: 11

Therefore the first-day zero BUY was not caused by absence of valid BUY
opportunities. The quality layer exposed 23 allocation-like BUY candidates.

PC narrowed this to 22 `ADD_CANDIDATE` members. The one additional
`REDUCED_ALLOCATION_ONLY` quality row, `21380`, became PC `EXCLUDE` because
entry / Strategy Intelligence evidence remained `BUY_WAIT`; it is not part of
the later all-22 suppression path.

## Portfolio Policy

`portfolio_policy.json` produced
`incremental_capital_budget_envelope` with:

- `authority_status`: `AUTHORITATIVE`
- `owner`: `PORTFOLIO_POLICY`
- `deployment_capacity_semantic`: `SELECTIVE_DEPLOYMENT_CAPACITY`
- `risk_pacing_intent`: `CAUTIOUS`
- reason codes including:
  - `CAPITAL_BUDGET_STATE_SELECTIVE_DEPLOYMENT_CAPACITY`
  - `CASH_STATE_EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP`
  - `DEPLOYMENT_INTENSITY_NOT_SECURITY_ADMISSION`
  - `EXPLORATION_PARTICIPATION_RISK_PRESERVED`
  - `MARKET_QUALITY_CONTEXT_SHORT_TERM_BREADTH_BREAKDOWN`
  - `PROFIT_ENGINE_PRESERVATION_CONTEXT`
  - `RISK_PACING_CAUTIOUS`

This is not a hard BUY gate. The policy envelope provided deployment capacity
and explicitly carried the contract that deployment intensity is not security
admission.

## PC Multi-Allocation

`portfolio_construction.json` produced
`canonical_multi_allocation_deployment_set.v1` with:

- `authority_status`: `SHADOW_NON_AUTHORITATIVE`
- `allocation_cardinality_contract`: `MULTI_ALLOCATION`
- `security_allocation_count`: 22
- non-zero `authorized_allocation_weight` rows: 22
- total security allocation weight: `0.733506`
- authorized cash allocation weight: `0.006494`
- `available_incremental_budget`: `0.74`
- `cash_winner_takes_all_contract`: `False`
- `single_path_remains_only_authoritative_trading_path`: `True`

All 22 allocated securities carried non-zero shadow security allocation. This
confirms:

PC_MULTI_ALLOCATION_NONZERO = YES

## G61 Lot-Aware Compatibility

The G61 compatibility payload in PC produced:

- `schema_version`: `portfolio_construction.lot_aware_allocation_to_sizing_compatibility.v1`
- `authority_status`: `SHADOW_NON_AUTHORITATIVE`
- `allocation_count`: 22
- `compatibility_executable_count`: 0
- `lot_executable_count`: 0
- `unexecutable_count`: 22
- `unexecutable_residual_weight`: `0.733506`
- `residual_capital_weight`: `0.733506`
- `all_zero_collapse`: True
- `minimum_executable_lot_basis`: `100_SHARE_LOT_OR_CANONICAL_TRADING_UNIT`
- `reason_codes`:
  - `G61_SHADOW_LOT_AWARE_COMPATIBILITY_LAYER`
  - `PS_QUANTITY_AUTHORITY_PRESERVED`
  - `LOWER_PRIORITY_IMPLICIT_PROMOTION_PROHIBITED`
  - `RESIDUAL_CAPITAL_EXPLICIT`

Every compatibility row was:

- `compatibility_state`: `INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED`
- `minimum_executable_weight`: null
- `cap_weight`: null
- `cap_headroom_weight`: null
- `executable_before_residual_reallocation`: false
- reason code: `INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED`

The first-ranked row `94340` demonstrates the propagation gap:

- PC member evidence contains `phase29_l19_lot_resolution.one_lot_weight = 0.01441`
- PC member evidence contains `phase29_l19_lot_resolution.executable_quantity_delta = 200`
- PC member evidence contains `lot_aware_final_target_weight = 0.033636`
- but the G61 compatibility row for `94340` has `minimum_executable_weight = null`,
  `cap_weight = null`, and `portfolio_value = null`

Thus the G61 layer did not receive or resolve the available lot sizing context
when producing the compatibility row. It fail-closed rather than projecting an
executable quantity.

For lower-ranked rows, G61 also set
`lower_priority_execution_requires_explicit_residual_resolution = true` on 21
rows after the first unresolved higher-priority row. This preserved priority
semantics, but it was not the Runtime suppression reason.

## Position Sizing

`position_sizing.json` consumed G61:

- `g61_compatibility_consumed_by_ps`: True
- `status`: `PASS`
- `allocation_count`: 22
- `lot_executable_count`: 0
- `executable_multi_security`: False
- `lower_priority_rows_requiring_explicit_residual_resolution`: 21
- `unresolved_higher_priority_allocation_count`: 0
- `residual_capital_weight`: `0.733506`

All PS quantities were zero:

- `positions`: 50
- `ADD_CANDIDATE` positions: 22
- positive `quantity_delta_candidate`: 0
- positive `final_quantity_delta`: 0
- positive `discrete_authorized_quantity`: 0
- `quantity_status`: `RESOLVED_ZERO_DELTA` for 50 positions

Therefore:

PS_POSITIVE_QUANTITY_EXISTS = NO

Important distinction: `position_sizing_preflight.json` shows all 22 preflight
rows as `lot_feasible = true`. That means the broader pipeline had enough
evidence to classify lot feasibility elsewhere, but the G61 compatibility
payload itself did not carry the required `minimum_executable_weight` /
headroom context into the PC -> PS binding evidence.

## Runtime Planning

`runtime_planning.json` consumed PS and G61:

- `pc_ps_runtime_executable_binding`: `PASS`
- `g61_compatibility_consumed_by_runtime`: True
- `ps_quantity_binds_runtime`: True
- `runtime_capital_priority_redecision`: False
- `cash_winner_redecision_runtime`: False
- `ps_authorized_quantity_reoptimized_by_runtime`: False
- `implicit_promotion_blocked_plan_count`: 0
- `runtime_buy_plan_count`: 0
- `runtime_add_plan_count`: 0

Plans:

- `plan_count`: 22
- `planning_intent = NO_ORDER`: 22
- `order_side_intent = NONE`: 22
- `no_order_reason = zero_quantity_delta`: 22
- positive `planned_quantity`: 0

Runtime did not independently suppress BUY via the G63 guard. It simply bound
to the PS zero quantities.

G63_RUNTIME_GUARD_SUPPRESSION_COUNT = 0

## Submit / Execution

Submit authority:

- `exit_code`: 0
- `halt_required`: False
- `safety_status`: `PASS`
- `submit_action`: `NO_SUBMISSION_REQUIRED`
- `no_order_authority_status`: `PASS`
- `no_order_authority_reason`: `strategy_planning_no_order_authorized`
- `submitted_count`: 0

Execution:

- `submitted_order_count`: 0
- `orders_count`: 0
- `fills`: 0
- `ledger_orders_appended`: 0
- `ledger_executions_appended`: 0
- `ledger_cash_appended`: 0
- `ledger_positions_appended`: 0
- `broker_order_api_calls`: 0

FINAL_BUY_ORDER_COUNT = 0

## G58 Shadow vs Actual Authoritative Path

G58 real-PIT sanity reported 2022-10-03 as the empty / near-empty bootstrap
participation witness. It observed non-zero security allocation and Cash
coexistence in shadow evidence, and concluded:

- `VALID_OPPORTUNITY_ZERO_ALLOCATION_COLLAPSE = NO`
- `MULTI_SECURITY_REAL_PIT_OBSERVED = YES`
- `BOOTSTRAP_PARTICIPATION_REAL_PIT = YES`

The actual fresh-run authoritative path still produced non-zero PC
multi-allocation on 2022-10-03, so the semantic gap is not at Portfolio Policy
or PC allocation creation. The gap appears after PC allocation, at G61
compatibility context propagation into PS/Runtime binding. G61 represented all
allocated capital as explicit residual because every compatibility row lacked
minimum executable lot context and failed closed.

SHADOW_TO_AUTHORITATIVE_SEMANTIC_GAP = YES

## Required Answers

MARKET_QUALITY_DIRECT_SUPPRESSION = NO

PC_MULTI_ALLOCATION_NONZERO = YES

PS_POSITIVE_QUANTITY_EXISTS = NO

G63_RUNTIME_GUARD_SUPPRESSION_COUNT = 0

FINAL_BUY_ORDER_COUNT = 0

SHADOW_TO_AUTHORITATIVE_SEMANTIC_GAP = YES

G63_ACCEPTANCE_GAP = YES

## Root Cause

The root cause is a PC -> G61 -> PS evidence propagation gap:

G61 compatibility is supposed to preserve G59/G61 capital priority while
projecting lot-aware executable feasibility without taking quantity authority
away from PS. In the 2022-10-03 actual fresh-run artifact, PC member evidence
already contains lot-aware executable context for at least top candidates
(`94340` has one-lot weight and an executable 200-share quantity), and PS
preflight also classifies 22 rows as lot feasible. However, the
`canonical_multi_allocation_deployment_set.v1` embedded G61 compatibility rows
do not receive `minimum_executable_weight`, cap/headroom, or portfolio value
context. G61 therefore fail-closes every security allocation as
`INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED`.

Because PS consumes that G61 compatibility, all candidate quantities become
zero. Runtime then correctly binds to PS zero quantities and produces
NO_ORDER/NO_SUBMISSION_REQUIRED. Submit and Execution are downstream correct
for the zero-order plan.

## Not Root Cause

- Market Quality direct hard BUY gate: NO
- Absence of valid candidates: NO
- Cash winner-takes-all redecision in Runtime: NO
- Runtime independent capital priority redecision: NO
- Submit safety block: NO
- Broker/order/fill side-effect failure: NO
- `G61_EXPLICIT_RESIDUAL_RESOLUTION_REQUIRED` as direct Runtime suppression of
  all BUYs: NO

## Next Task Recommendation

PHASE31_G65_G61_LOT_CONTEXT_PROPAGATION_REPAIR

Repair should be scoped to preserving and consuming canonical lot sizing
context in the PC multi-allocation -> G61 compatibility -> PS binding path.
The repair should not change Market Quality semantics, candidate eligibility,
thresholds, weights, or submit/execution behavior.
