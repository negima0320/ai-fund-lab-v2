# Phase15-AP Position Management AI Input Contract

Date: 2026-07-10

## Objective

Phase15-AP implements a formal Runtime input contract and fail-closed validation for the regular Position Management AI path.

The scope is:

```text
Current
+
PM Feature
+
Opportunity Evidence
↓
Position Management AI
↓
SELL Planning
```

This phase does not change Position Management AI model logic, thresholds, training, or the meaning of HOLD / EXIT / REDUCE / ADD.

## Final Judgment

```text
PHASE15AP_POSITION_MANAGEMENT_AI_INPUT_CONTRACT_COMPLETE
```

## Implementation Summary

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
```

Implemented:

- Canonical PM input schema:

```text
schema_name=runtime_v2_pm_input
schema_version=runtime_v2_pm_input_v1
```

- Runtime pre-validation before `run_position_management_inference()`.
- Fixed-path `REVIEW_REQUIRED` artifact on schema / freshness / dependency mismatch:

```text
.runtime/runtime_state/position_management/<business_date>/position_management_decisions.json
```

- Current freshness validation.
- Current position required-field validation.
- PM feature row coverage validation for held symbols.
- Opportunity dependency validation.
- Hidden default prevention for:

```text
holding_days missing -> 0
peak_return missing -> current_return
current_price missing -> average_price
Opportunity missing -> empty row
PM feature missing -> default feature
```

- Derived field evidence in artifact and manifest.
- PM input evidence in report / notification summary path.

## Canonical PM Input Contract

| Field Area | Contract | Classification |
|---|---|---|
| `symbol` | required per Current position | REQUIRED |
| `quantity` | required per Current position | REQUIRED |
| `as_of` | required per Current position and must align with business date | REQUIRED |
| `source` | required per Current position | REQUIRED |
| `average_price` | required as entry price source | REQUIRED |
| `current_price` | allowed from explicit current price, price, or `market_value / quantity` | DERIVABLE_WITH_EVIDENCE |
| `position_size` | derived from Current quantity | DERIVABLE_WITH_EVIDENCE |
| `current_return` | derived from entry price and current price | DERIVABLE_WITH_EVIDENCE |
| `unrealized_pnl` | Current or formula-backed derived field | DERIVABLE_WITH_EVIDENCE |
| `market_value` | Current valuation evidence | DERIVABLE_WITH_EVIDENCE |
| `holding_days` | must exist from holding history / position evidence | REQUIRED |
| `peak_return` | must exist from position history / valuation history | REQUIRED |
| missing `holding_days` default `0` | not allowed | FORBIDDEN_DEFAULT |
| missing `peak_return` default current return | not allowed | FORBIDDEN_DEFAULT |
| missing `current_price` default average price | not allowed | FORBIDDEN_DEFAULT |

## Current Contract

Current source:

```text
.runtime/persistent_ledger/state.json
```

Required:

```text
symbol
quantity
as_of
source
average_price
```

Freshness:

```text
current.as_of == business_date
current.updated_at exists
```

If stale:

```text
status=REVIEW_REQUIRED
reason=pm_input_stale_artifacts
stale_artifacts=["current"]
```

## PM Feature Contract

If Current has positions:

```text
position_feature_input / pm_feature artifact must include a row for every held symbol.
```

If any held symbol is missing:

```text
status=REVIEW_REQUIRED
reason=pm_feature_rows_missing_for_current_positions
missing_symbols=[...]
```

If Current has no positions:

```text
0 PM feature rows are allowed only when no_position_reason exists.
```

Without `no_position_reason`:

```text
status=REVIEW_REQUIRED
reason=pm_no_position_reason_missing
```

## Opportunity Dependency Contract

When Current has positions, Opportunity evidence is required.

Validated:

```text
artifact exists
status
review_required
model_version when JSON artifact
generated_at when JSON artifact
feature_date
held symbol coverage
required columns
```

If Opportunity artifact is missing:

```text
status=REVIEW_REQUIRED
reason=pm_opportunity_artifact_missing
```

If Opportunity artifact is `REVIEW_REQUIRED`:

```text
PM status=REVIEW_REQUIRED
pm_opportunity_status=REVIEW_REQUIRED
```

## REVIEW_REQUIRED Artifact

On contract failure, Runtime writes:

```text
.runtime/runtime_state/position_management/<business_date>/position_management_decisions.json
```

Fields include:

```text
schema_version
business_date
runtime_id
status=REVIEW_REQUIRED
review_required=true
review_reason
current_source
current_as_of
pm_feature_source
pm_feature_row_count
opportunity_source
missing_fields
missing_symbols
stale_artifacts
derived_fields
defaulted_fields
decisions=[]
generated_at
input_contract
```

## SELL Planning Consumer Contract

Runtime CLI already stops before SELL Planning if PM producer returns `REVIEW_REQUIRED`.

Verified behavior:

```text
PM input contract failure
↓
position_management_ai_runtime_producer = REVIEW_REQUIRED
↓
final_state = REVIEW_REQUIRED
↓
sell_planning_pending_pipeline is not executed
```

Emergency liquidation / operational cleanup remains outside this PM AI decision contract.

## Manifest Evidence

PM manifest now includes:

```text
pm_input_schema_status
pm_current_source
pm_current_as_of
pm_current_freshness
pm_feature_source
pm_feature_row_count
pm_feature_date
pm_opportunity_source
pm_opportunity_status
pm_missing_fields
pm_missing_symbols
pm_derived_fields
pm_defaulted_fields
pm_review_required
pm_review_reason
```

## Report / Notification

Report Position Management evidence now includes:

- PM Input Status
- Current freshness
- Feature coverage
- Opportunity dependency
- Derived fields
- Missing fields
- Review reason

Notification remains summary-only through `position_management_summary`; real send was not performed.

## Regression

Added:

```text
tests/runtime_v2/test_phase15ap_position_management_input_contract.py
```

Coverage:

- fresh Current + held symbol PM feature rows + valid Opportunity -> PASS
- stale Current -> `REVIEW_REQUIRED`
- Current positions + PM feature 0 rows -> `REVIEW_REQUIRED`
- partial held-symbol feature coverage -> `REVIEW_REQUIRED`
- Current empty + `no_position_reason` -> no-position ready
- Current empty without `no_position_reason` -> `REVIEW_REQUIRED`
- Opportunity missing -> `REVIEW_REQUIRED`
- Opportunity `REVIEW_REQUIRED` -> PM `REVIEW_REQUIRED`
- hidden default fields are not used
- fixed-path PM `REVIEW_REQUIRED` artifact remains
- SELL Planning does not run after PM `REVIEW_REQUIRED`

Retention fixture updates:

- `tests/runtime_v2/test_phase15af_position_management_runtime_connection.py`
- `tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py`

Pass fixtures now provide explicit `holding_days`, `peak_return`, and valuation evidence instead of relying on hidden Runtime defaults.

## Verification

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase15ap_position_management_input_contract.py tests/runtime_v2/test_phase15af_position_management_runtime_connection.py tests/runtime_v2/test_phase15an_feature_consumer_readiness.py tests/runtime_v2/test_phase15ao_candidate_opportunity_controlled_schema_validation.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py
```

Result:

```text
48 passed
```

Executed:

```text
env PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase15ap python3 -m compileall src/ai_fund_lab_v2/runtime_v2/position_management/producer.py src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py tests/runtime_v2/test_phase15ap_position_management_input_contract.py tests/runtime_v2/test_phase15af_position_management_runtime_connection.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py
```

Result:

```text
PASS
```

## Remaining Scope

Not included in Phase15-AP:

- PM model change
- PM retraining
- HOLD / EXIT / REDUCE / ADD logic change
- Runtime Data Readiness Gate
- Pending lifecycle remediation
- Broker Write / Submit / Execution

## Prohibited Actions Confirmation

This phase did not perform:

- PM model change
- PM retraining
- HOLD / EXIT / REDUCE / ADD logic change
- missing field hidden default adoption
- SELL real operation
- Submit
- Execution
- Broker Write
- order
- Notification real send
- launchd change
- Current direct edit

## Completion String

```text
PHASE15AP_POSITION_MANAGEMENT_AI_INPUT_CONTRACT_COMPLETE
```
