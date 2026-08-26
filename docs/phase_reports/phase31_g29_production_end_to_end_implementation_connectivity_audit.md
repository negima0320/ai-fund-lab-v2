# Phase31-G29 - Production End-to-End Implementation Connectivity Audit

Task type: READ-ONLY + FOCUSED INTEGRATION ACCEPTANCE

Implementation changes: NO
Fresh run / resume / replay / long Historical: NO

## Primary Judgment

PRIMARY_JUDGMENT =
PHASE31_G29_RUNTIME_SUBMIT_EXECUTION_BOUNDARY_GAP_FOUND

G29 acceptance is stopped. Existing focused tests show the established
Strategy -> Runtime Planning -> Pending -> Submit -> Execution boundaries still
work for legacy-compatible BUY/SELL/no-action/safety paths, but the G24-G28
authoritative fields are not proven as exact serialized fields consumed through
Runtime Submit/Execution/Fill/Persistence.

This is not classified as a performance failure and not classified as a
strategy-behavior defect. It is an implementation-connectivity acceptance gap:
the current downstream path consumes materialized intent, priority, quantity,
price, cash, and safety fields, but does not carry the new authoritative
Market Quality / Risk Pacing / PC capital-competition field names through
Pending/Submit/Execution as G29 requires.

## Required SoT Read

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/phase_reports/phase31_g21_dual_path_implementation_planning_migration_sequencing_acceptance_gates.md`
- `docs/phase_reports/phase31_g22_market_quality_evidence_producer_schema_reason_codes.md`
- `docs/phase_reports/phase31_g23_portfolio_policy_risk_pacing_shadow_producer.md`
- `docs/phase_reports/phase31_g24_portfolio_construction_capital_competition_framework_authority_migration.md`
- `docs/phase_reports/phase31_g25_position_sizing_lot_residual_evidence_pc_reconsideration_integration.md`
- `docs/phase_reports/phase31_g26_reentry_semantic_eligibility_migration.md`
- `docs/phase_reports/phase31_g27_add_capital_competition_integration.md`
- `docs/phase_reports/phase31_g28_risk_pacing_authoritative_activation_shadow_cutover.md`

## Component Inventory

| Component | Authoritative Producer | Input artifact / field | Output artifact / field | Authoritative consumer | Current status |
| --- | --- | --- | --- | --- | --- |
| J-Quants PIT inputs | Data adapters | PIT source files | normalized market/feature inputs | Strategy feature materialization | CONNECTED_BY_EXISTING_RUNTIME |
| Market Context / Direction | Market Context | PIT market evidence | `market_context`, regime/direction | Portfolio Policy / Strategy | CONNECTED_BY_EXISTING_RUNTIME |
| Market Quality | Market Context | PIT market evidence | `market_quality_state`, reasons, as_of | Portfolio Policy | PRODUCED_AND_CONSUMED_UPSTREAM; NOT_CARRIED_TO_RUNTIME_BOUNDARY |
| Portfolio Policy / Risk Pacing | Portfolio Policy | Market Context / Quality | `risk_pacing_intent`, reasons, as_of, authority | Portfolio Construction | CONNECTED_TO_PC; NOT_CARRIED_TO_PENDING_SUBMIT_EXECUTION |
| BUY quality / candidate evidence | BUY Quality / Opportunity evidence | PIT candidate evidence | quality / eligibility fields | Portfolio Construction, Runtime Planning observability | CONNECTED |
| Position Management | PM | current positions / PM evidence | HOLD / ADD / REDUCE / EXIT | PC and Runtime Planning | CONNECTED |
| Portfolio Construction | PC | Policy, PM, BUY quality, sizing feedback | members, target weight, marginal priority, `capital_competition` | Position Sizing / Runtime Planning | PARTIAL: materialized members consumed; exact `capital_competition` fields not consumed downstream |
| Position Sizing | Position Sizing | PC members / targets | `quantity_delta_candidate`, target quantity, price authority | Runtime Planning | CONNECTED |
| Runtime Planning | `strategy.runtime_planning` | PC, PM, Position Sizing, current state | `planning_intent`, side, quantity, priority | Runtime Planning consumer / Pending | CONNECTED_FOR_LEGACY_COMPATIBLE_FIELDS |
| Pending | `runtime_v2.planning.strategy_authority` | Runtime Planning plans | `PendingOrderItem` | Submit | CONNECTED_FOR_ORDER_FIELDS; new G24-G28 authority fields absent |
| Submit | `runtime_v2.submit.pipeline` | Pending / approval / safety / policy | ledger order records, pending consume states | Execution / ledger | CONNECTED_FOR_ORDER_FIELDS |
| Execution | `runtime_v2.execution.readonly_pipeline` | submitted broker/order evidence | ledger executions, positions, cash, current state | Runtime current state | CONNECTED_FOR_ORDER_FIELDS |

FULL_PRODUCTION_COMPONENT_INVENTORY_COMPLETE = YES

## Field-Level Lineage Finding

Field continuity is complete only for the existing executable order surface:

- `business_date`
- `planning_intent`
- `order_side_intent`
- `target_quantity_candidate`
- `quantity_delta_candidate`
- `planned_quantity`
- price authority
- cash reservation / reserved notional
- safety context
- marginal-capital priority index / value class
- order side / order type
- pending item identity
- submitted order / ledger order identity
- execution / position / cash projection identity

Field continuity is not complete for the new G24-G28 authoritative evidence
surface required by G29:

- `market_quality_state`
- `market_quality_reason_codes`
- `market_quality_as_of`
- `risk_pacing_intent`
- `risk_pacing_reason_codes`
- `risk_pacing_as_of`
- `capital_competition`
- `canonical_add_competitor`
- `reentry_semantic_eligibility`
- `final_no_deployable_opportunity`
- `canonical_sizing_evidence`

Runtime Planning loads PC / Policy / PM / Sizing artifacts and records source
hashes, but its serialized `plans` are reduced to order-facing fields. The plan
payload built in `src/ai_fund_lab_v2/strategy/runtime_planning.py` contains
quantity, priority, quality, PM, and price fields, but not the exact
`capital_competition`, `risk_pacing`, `canonical_add_competitor`,
`reentry_semantic`, `final_no_deployable`, or `canonical_sizing_evidence`
fields.

The runtime consumer then constructs `PendingOrderItem` from those order-facing
fields. `PendingOrderItem` has fields for quantity, price, safety,
reservation, source decision type, and marginal priority, but no fields for the
new authority payloads.

FIELD_LEVEL_LINEAGE_COMPLETE = NO
AUTHORITATIVE_FIELD_CONTINUITY = FAIL
FIELD_NAME_MISMATCH_COUNT = 0
FIELD_TYPE_MISMATCH_COUNT = 0
SCHEMA_VERSION_MISMATCH_COUNT = 0

## Defect

DEFECT_ID = PHASE31_G29_E2E_AUTHORITY_FIELD_CONTINUITY_001

SOURCE_COMPONENT =
Portfolio Construction / Portfolio Policy / Market Context / Position Sizing

SOURCE_FIELD =
`market_quality_state`, `risk_pacing_intent`, `risk_pacing_reason_codes`,
`risk_pacing_as_of`, `capital_competition`, `canonical_add_competitor`,
`reentry_semantic_eligibility`, `final_no_deployable_opportunity`,
`canonical_sizing_evidence`

EXPECTED_CONSUMER =
Runtime Planning -> Pending -> Submit -> Execution / persistence

ACTUAL_BEHAVIOR =
Runtime Planning consumes upstream artifacts for materialized target/quantity
decisions and emits executable order-facing fields, but does not serialize the
new authoritative evidence fields into runtime plans. Pending materialization
then persists `PendingOrderItem` fields for executable order semantics only.
Submit and Execution receive and act on Pending order fields, not the exact
G24-G28 authority evidence fields.

BROKEN_BOUNDARY =
Strategy authority evidence surface -> Runtime Planning serialized plan ->
Pending item schema -> Submit/Execution focused E2E acceptance

BUSINESS_IMPACT =
The system may still run using materialized quantities and priorities, but G29
cannot prove that the new dual-path authority chain is production-connected
end-to-end before a long Historical run. This violates the G29 acceptance
principle that producer writes, serialized field, exact consumer read, branch
use, and downstream materialization must all be proven.

RECOMMENDED_REPAIR_SCOPE =
Create a scoped connectivity repair task that either carries the required
authority evidence through Runtime Planning/Pending as explicit lineage fields,
or creates an approved runtime lineage artifact consumed by Pending/Submit/
Execution acceptance. Then add focused production-equivalent E2E tests for
NEW_BUY, ADD, Re-entry, Cash optionality, lot reconsideration, final
NO_DEPLOYABLE, SELL, REDUCE, NO_ACTION, and Safety rejection without running
Historical.

## Boundary Audit

Runtime Planning:

- Loads PC / Policy / PM / Position Sizing artifacts and validates source
  hashes.
- Uses Position Sizing quantity first when canonical position sizing plan is
  available.
- Serializes order-facing plan fields: intent, side, quantity, priority, PM,
  price, quality, and safety-relevant fields.
- Does not serialize the exact G24-G28 authority evidence fields listed above.

Pending:

- Materializes `PendingOrderItem` from runtime plan fields.
- Preserves quantity contract, source decision type, marginal capital priority,
  reservation, price, safety, and policy fields.
- Does not have fields for `capital_competition`, `risk_pacing_evidence`,
  `canonical_add_competitor`, `reentry_semantic_eligibility`, or
  `canonical_sizing_evidence`.

Submit:

- Performs Pending validation, approval linkage, policy consistency, safety,
  market/broker feasibility, corporate-action and idempotency checks.
- Does not rerank candidates or recreate PC capital competition.
- Does not consume the exact new authority fields because they are absent from
  Pending.

Execution:

- Projects accepted submitted orders/fills into ledger/current state.
- Handles no-action and terminal submit authorities.
- Does not recreate Strategy allocation decisions.
- Does not consume the exact new authority fields because they are absent from
  Submit/Execution inputs.

## Focused Regression Results

Command run:

```bash
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py tests/runtime_v2/test_phase17_bv10_historical_sell_execution_projection.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py tests/runtime_v2/test_phase19_bi_empty_pending_no_action_contract.py
```

Result:

```text
312 passed
```

PY_COMPILE =
PASS with `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache-g29`

GIT_DIFF_CHECK =
PASS

## Required Output

PRIMARY_JUDGMENT =
PHASE31_G29_RUNTIME_SUBMIT_EXECUTION_BOUNDARY_GAP_FOUND

FULL_PRODUCTION_COMPONENT_INVENTORY_COMPLETE =
YES

FIELD_LEVEL_LINEAGE_COMPLETE =
NO

AUTHORITATIVE_FIELD_CONTINUITY =
FAIL

FIELD_NAME_MISMATCH_COUNT =
0

FIELD_TYPE_MISMATCH_COUNT =
0

SCHEMA_VERSION_MISMATCH_COUNT =
0

ORPHAN_AUTHORITATIVE_PRODUCER_COUNT =
5

DEAD_AUTHORITATIVE_CONSUMER_COUNT =
0

IMPLICIT_BUSINESS_FALLBACK_COUNT =
0

DUPLICATE_BUSINESS_AUTHORITY_COUNT =
0

END_TO_END_PIT_CONTRACT =
PASS_STATIC_AUDIT

FUTURE_INPUT_COUNT =
0

LATER_OUTCOME_FEEDBACK_COUNT =
0

PAPER_LEDGER_STRATEGY_INPUT_COUNT =
0

HISTORICAL_RESULT_STRATEGY_INPUT_COUNT =
0

AUDIT_RESULT_STRATEGY_INPUT_COUNT =
0

NEW_BUY_END_TO_END_CONNECTIVITY =
PARTIAL

ADD_END_TO_END_CONNECTIVITY =
PARTIAL

REENTRY_END_TO_END_CONNECTIVITY =
PARTIAL

REENTRY_BLOCK_SYMBOL_LOCAL =
PASS_UPSTREAM

CASH_OPTIONALITY_END_TO_END_CONNECTIVITY =
PARTIAL

DOWNSTREAM_FORCED_DEPLOYMENT_COUNT =
0

LOT_FAILURE_RECONSIDERATION_CONNECTIVITY =
PARTIAL

NO_DEPLOYABLE_END_TO_END_CONNECTIVITY =
PARTIAL

FINAL_NO_DEPLOYABLE_OWNER =
PORTFOLIO_CONSTRUCTION

DOWNSTREAM_NO_DEPLOYABLE_REDECISION_COUNT =
0

SELL_END_TO_END_CONNECTIVITY =
PASS_FOR_EXISTING_ORDER_FIELD_PATH

BUY_SELL_INDEPENDENCE =
PASS

REDUCE_END_TO_END_CONNECTIVITY =
PARTIAL

NO_ACTION_END_TO_END_CONNECTIVITY =
PASS

SAFETY_END_TO_END_CONNECTIVITY =
PASS_FOR_EXISTING_SAFETY_BOUNDARY

SAFETY_AUTHORITY =
SAFETY

CASH_ACCOUNTING_END_TO_END =
PASS_FOR_EXISTING_ORDER_FIELD_PATH

CASH_DOUBLE_USE_COUNT =
0

POSITION_QUANTITY_END_TO_END =
PASS_FOR_EXISTING_ORDER_FIELD_PATH

DOWNSTREAM_QUANTITY_REDECISION_COUNT =
0

PENDING_SCOPE_AUTHORITY =
PASS

BUY_PENDING_BLOCKS_UNRELATED_SELL =
NO

RUNTIME_REDECISION_COUNT =
0

RUNTIME_INPUT_CONNECTIVITY =
PARTIAL

SUBMIT_STRATEGY_REDECISION_COUNT =
0

SUBMIT_BOUNDARY_CONNECTIVITY =
PARTIAL

EXECUTION_STRATEGY_REDECISION_COUNT =
0

EXECUTION_BOUNDARY_CONNECTIVITY =
PARTIAL

STATE_PERSISTENCE_CONNECTIVITY =
PASS_FOR_EXISTING_ORDER_FIELD_PATH

PRICE_QUANTITY_BASIS_CONTRACT =
PASS_FOR_EXISTING_ORDER_FIELD_PATH

PERSISTED_ARTIFACT_RELOAD_COMPATIBILITY =
PARTIAL

AUTHORITATIVE_FIELD_LOSS_ON_RELOAD_COUNT =
5

LEGACY_BUSINESS_PATH_MATRIX_COMPLETE =
YES

PERMANENT_LEGACY_BUSINESS_FALLBACK_COUNT =
0

CORE_DECISION_COMPONENTS_MOCKED_OUT =
NO_FOR_FOCUSED_COMPONENT_TESTS; E2E_AUTHORITY_FIELD_COVERAGE_NOT_PRESENT

PRODUCTION_BRANCH_COVERAGE_EVIDENCE =
FAIL

G29_FOCUSED_E2E_TESTS =
FAIL

IMPLEMENTATION_CHANGE_EXECUTED =
NO

FRESH_RUN_EXECUTED =
NO

RESUME_EXECUTED =
NO

REPLAY_EXECUTED =
NO

LONG_HISTORICAL_EXECUTED =
NO

NEXT_TASK_RECOMMENDATION =
Repair Runtime/Pending lineage connectivity for G24-G28 authority fields and
add focused production-equivalent E2E tests before G30 or any long Historical
validation.
