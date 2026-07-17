# Phase17-BK Day4 PM Opportunity Contract Mismatch Root Cause

## Executive Summary

Final judgment:

```text
PHASE17_BK_ROOT_CAUSE_CONFIRMED
```

Day4 `2026-07-09:sell_planning` stopped before Position Management producer execution because Data Readiness pre-gate selected a different Feature Date authority than the Runtime Test Runner command.

This is not a PM parquet column defect. Both `2026-07-08` and `2026-07-09` PM feature parquet files have the required PM columns, five held symbols, no null required fields, and no duplicate target-date/symbol rows.

The exact failure is an authority split:

1. Runtime Test Runner command passed `--feature-date 2026-07-08`.
2. Data Readiness loaded `.runtime/operations/feature_date_contract/2026-07-09.json` and selected `2026-07-09`, ignoring the explicit `--feature-date` because a materialized business-date contract existed.
3. Data Readiness resolved PM inputs from the selected `2026-07-09` contract:
   - PM feature: `.runtime/operations/feature_artifacts/2026-07-09/position_feature_input.parquet`
   - PM opportunity: `.runtime/runtime_state/buy_ai/2026-07-09/opportunity_rankings.json`
4. The `2026-07-09` Opportunity ranking artifact exists, but it was generated as business-date `2026-07-09` using carryover feature-date `2026-07-08`; its top-level `feature_date` and ranking row `target_date` are `2026-07-08`.
5. PM contract validation was invoked with expected `feature_date=2026-07-09`, so `_pm_opportunity_contract()` raised `ValueError("target date mismatch")`, surfaced as:

```text
pm_missing_fields=["opportunity.contract:target date mismatch"]
pm_opportunity_status=HALT
pm_reason=pm_opportunity_contract_mismatch
```

## Halt Evidence

Target:

```text
run_id=runtime-test-historical-smoke-20260715T111433056797Z
business_date=2026-07-09
halted_job=sell_planning
exit_code=20
reason=pm_opportunity_contract_mismatch
```

Observed READY components:

```text
Current=READY
Current Valuation=READY
Market=READY
Quote=READY
Feature=READY
Pending=READY / EMPTY
Historical Safety=READY
Runtime Environment=READY
```

Stopping component:

```text
pm_status=REVIEW_REQUIRED
pm_input_schema_status=REVIEW_REQUIRED
pm_opportunity_status=HALT
pm_reason=pm_opportunity_contract_mismatch
```

Evidence files inspected:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/daily/2026-07-09/sell_planning/runtime_manifest.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/daily/2026-07-09/sell_planning/sell_planning_manifest.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/daily/2026-07-09/sell_planning/position_management_evidence.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/daily/2026-07-09/sell_planning/data_readiness_authority.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/daily/2026-07-09/sell_planning/pending_continuity_evidence.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/daily/2026-07-09/data_readiness/data_readiness.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/run_state.json
```

## Exact Missing Field

The exact PM missing field is:

```text
opportunity.contract:target date mismatch
```

Other PM fields:

```text
pm_missing_symbols=[]
missing_columns=["opportunity.contract:target date mismatch"]
pm_defaulted_fields=[]
pm_stale_artifacts=[]
```

This is not a missing parquet column and not a missing held symbol. It is a contract exception raised while parsing the Opportunity ranking JSON as PM opportunity context.

## Expected PM Feature Schema

Design and consumer readiness agree that PM feature input requires:

```text
target_date
position_state_as_of
entry_date
code
broker_issue_code
holding_days
average_price
current_price
unrealized_return
quantity
feature_version
data_until
created_at
```

Both inspected PM parquet files also include:

```text
no_position_reason
```

## 2026-07-08 / 2026-07-09 Parquet Comparison

Both files exist:

```text
.runtime/operations/feature_artifacts/2026-07-08/position_feature_input.parquet
.runtime/operations/feature_artifacts/2026-07-09/position_feature_input.parquet
```

Comparison:

| Item | 2026-07-08 | 2026-07-09 |
|---|---:|---:|
| row count | 5 | 5 |
| symbol set | 36670, 45640, 66590, 67400, 81050 | 36670, 45640, 66590, 67400, 81050 |
| target_date | 2026-07-08 | 2026-07-09 |
| data_until | 2026-07-08 | 2026-07-09 |
| position_state_as_of | 2026-07-06 | 2026-07-06 |
| entry_date | 2026-07-06 | 2026-07-06 |
| required-column null counts | 0 for all required columns | 0 for all required columns |
| duplicate target_date/code | 0 | 0 |
| column set equal | yes | yes |

Conclusion:

```text
The failing field is not absent from either parquet.
No required PM feature field exists only on 2026-07-08.
No required PM feature field is null on 2026-07-09.
No column-name conversion removed the failing field.
```

## Opportunity Artifact Comparison

Both Opportunity ranking artifacts exist:

```text
.runtime/runtime_state/buy_ai/2026-07-08/opportunity_rankings.json
.runtime/runtime_state/buy_ai/2026-07-09/opportunity_rankings.json
```

Observed:

| Item | 2026-07-08 artifact | 2026-07-09 artifact |
|---|---|---|
| schema_version | runtime_v2_opportunity_ranking_v1 | runtime_v2_opportunity_ranking_v1 |
| schema_name | runtime_v2_buy_opportunity_ranking | runtime_v2_buy_opportunity_ranking |
| artifact_role | BUY_OPPORTUNITY_RANKING | BUY_OPPORTUNITY_RANKING |
| business_date | 2026-07-08 | 2026-07-09 |
| feature_date | 2026-07-08 | 2026-07-08 |
| ranking_count | 50 | 50 |
| ranking row target_date | 2026-07-08 | 2026-07-08 |
| opportunity_feature_path | `.runtime/operations/feature_artifacts/2026-07-08/opportunity_feature_input.parquet` | `.runtime/operations/feature_artifacts/2026-07-08/opportunity_feature_input.parquet` |

The Day4 artifact is internally expressing a carryover decision flow:

```text
runtime business_date=2026-07-09
feature_date=2026-07-08
ranking target_date=2026-07-08
```

PM validation, however, was called with expected `feature_date=2026-07-09`.

## Feature Date Authority

Design evidence:

- `runtime_temporal_freshness_contract.md`: Candidate AI, Opportunity AI, and PM AI must use the same `feature_date` for the same Runtime decision flow.
- `runtime_test_specification.md`: carryover must be resolved by the normal Feature Date Contract; profile expected values are acceptance checks, not alternate authority.
- `historical_runtime_test_contract.md`: Historical run entry requires `PASS` Feature Date Contracts from normal authority; profile expected dates must never be authority.
- Phase17-P audit specifically records `2026-07-09` as an accepted carryover scenario with `selected_feature_date=2026-07-08`.

Actual authority split:

| Source | Day4 value |
|---|---|
| Historical smoke profile `accepted_feature_dates` | `2026-07-09 -> 2026-07-08` |
| Runtime Test Runner command | `--feature-date 2026-07-08` |
| `.runtime/operations/feature_date_contract/2026-07-09.json` | `selected_feature_date=2026-07-09` |
| Data Readiness sell_planning evidence | `selected_feature_date=2026-07-09` |
| Day4 Morning Opportunity artifact | `business_date=2026-07-09`, `feature_date=2026-07-08` |

Therefore the correct Day4 authority for this historical smoke window is expected to be the normal Feature Date Contract selecting `2026-07-08`; however the live `.runtime` materialized contract selected `2026-07-09`, and the Runner still passed `2026-07-08` from profile-derived plan evidence. The system proceeded with competing authorities instead of failing closed before Runtime invocation.

## Producer / Consumer Data Flow

Runtime Test Runner:

```text
config/runtime_tests/historical_smoke_5bd.json
accepted_feature_dates["2026-07-09"]="2026-07-08"
scripts/runtime_test.py build_plan()
-> command includes --feature-date 2026-07-08
```

CLI Data Readiness:

```text
run_daily_operation.py
-> evaluate_runtime_data_readiness(... feature_date=args.feature_date ...)
```

Data Readiness resolver:

```text
_feature_date_contract_payload()
-> load_feature_date_contract(requested_feature_date=business_date)
-> if materialized business_date contract exists, use it
-> explicit_feature_date is only used when business-date contract is absent
```

PM input path resolver:

```text
_resolve_pm_input_paths_from_feature_contract()
-> pm_feature = feature_contract.generated_feature_artifacts["position_feature_input.parquet"]
-> pm_opportunity = .runtime/runtime_state/buy_ai/<selected_feature_date>/opportunity_rankings.json
```

PM consumer:

```text
validate_position_management_input_contract()
->_pm_opportunity_status()
->_pm_opportunity_contract(opportunity_path, feature_date)
```

Failure point:

```text
_pm_opportunity_contract()
payload_feature_date = "2026-07-08"
expected feature_date = "2026-07-09"
raise ValueError("target date mismatch")
```

## PM Opportunity Dependency

The PM Opportunity dependency is formal when Current has positions. `opportunity_model_status=NOT_REQUIRED` only means Data Readiness does not need to run Opportunity Model inference during sell_planning. It does not mean PM can ignore existing Opportunity context.

The PM consumer uses Opportunity ranking/context to provide buy-side/opportunity context for held symbols. Missing ranked symbols are not fatal by themselves: the contract records `missing_symbol_semantics=symbol_not_ranked_is_valid_pm_context_default` when the Opportunity artifact is valid but does not rank every held symbol. Therefore the dependency is not an accidental column dependency; the stop occurred because the artifact contract date was invalid for the expected feature date.

## Why Day4

Day4 is the first day in this run where the smoke profile expects feature carryover:

```text
2026-07-06 -> 2026-07-06
2026-07-07 -> 2026-07-07
2026-07-08 -> 2026-07-08
2026-07-09 -> 2026-07-08
2026-07-10 -> 2026-07-10
```

Earlier days did not expose the authority split because `business_date == selected_feature_date`.

## Test Gap

Existing tests did not catch a multi-day case where:

```text
runtime_business_date != selected_feature_date
materialized Feature Date Contract disagrees with Runner-selected feature_date
DayN Morning writes Opportunity under business_date with carryover feature_date
DayN Sell Planning Data Readiness re-resolves PM input paths independently
PM Opportunity JSON has business_date != feature_date
```

Needed regression coverage:

- Historical 5BD Day4 carryover: `business_date=2026-07-09`, `selected_feature_date=2026-07-08`.
- Data Readiness must not override explicit/accepted feature authority with a stale or conflicting materialized business-date contract.
- Runtime Test runner must fail closed if normal Feature Date Contract and profile expected selected date disagree.
- Morning and Sell Planning must use the same feature_date authority for Candidate, Opportunity, and PM.
- PM Opportunity contract must explicitly support or reject carryover artifacts by a documented rule; current behavior is implicit and contradictory.

## Root Cause

Root Cause classification:

```text
Authority Bug / Integration Bug
```

Exact Root Cause:

```text
Feature Date authority split between Runtime Test Runner, Data Readiness, materialized Feature Date Contract, and PM Opportunity contract validation.
```

Direct implementation cause:

```text
data_readiness._feature_date_contract_payload() prefers the materialized business-date Feature Date Contract over explicit feature_date when the contract exists. For Day4 this selected 2026-07-09 even though the Runtime Test Runner command passed 2026-07-08.
```

Secondary contract issue:

```text
PM Opportunity validation currently treats the expected feature_date as the single date for top-level business_date, top-level feature_date, and row target_date. That is incompatible with Day4 carryover evidence where business_date=2026-07-09 and feature_date/target_date=2026-07-08 unless a formal carryover contract says this shape is valid.
```

## Fail-Closed Assessment

The stop is a valid fail-closed outcome. PM had positions and its Opportunity context contract date did not match the date authority Data Readiness supplied. Continuing would have mixed Day4 PM features with Day3/Day4 Opportunity authority ambiguity.

The failure is not acceptable as a final Runtime behavior because the upstream authorities should never have diverged this far. The system should either:

- select a single accepted Feature Date authority before invoking Runtime jobs, or
- halt earlier with a clear Feature Date authority mismatch.

## Recommended Correction Boundary

Do not loosen PM missing fields or ignore `pm_opportunity_contract_mismatch`.

Recommended boundary for the next phase:

1. Establish one shared Feature Date authority resolver for Runtime Test Runner, Data Readiness, Morning, Sell Planning, and PM.
2. Fail closed if materialized `.runtime/operations/feature_date_contract/<business_date>.json` conflicts with the accepted plan/profile expectation for Historical smoke.
3. Ensure `--feature-date` passed to Runtime CLI, Data Readiness `selected_feature_date`, PM feature path, and PM Opportunity path are derived from the same authority.
4. Define PM Opportunity carryover semantics explicitly:
   - either PM reads the business-date Opportunity artifact and allows `feature_date != business_date` when the shared Feature Date Contract proves carryover, or
   - PM reads the selected-feature-date Opportunity artifact and requires business_date/feature_date/target_date all equal to selected feature date.
5. Add multi-day carryover regression tests before resuming the run.

## Non-Recommended Fixes

Do not:

- ignore `pm_missing_fields`
- convert `pm_opportunity_contract_mismatch` to PASS
- blindly use previous-day artifacts
- blindly use current-day artifacts
- fill missing Opportunity fields with null/default values
- add Historical-only exception paths
- remove PM Opportunity dependency without design proof
- delete date checks from `_pm_opportunity_contract()`

## Production / Demo Impact

This is not Historical-only in principle. Production/Demo can also face a publication-window or carryover day where feature_date and business_date differ. The fix must be a shared Feature Date authority contract, while environment differences remain limited to external effects and broker behavior.

Production impact if left unfixed:

- PM could halt on valid carryover days.
- Or worse, separate components could consume different feature dates in the same decision flow.

## Resume Conditions

The existing run was not resumed. Resume should wait until:

- Feature Date authority is unified.
- Day4 `2026-07-09` normal Feature Date Contract is consistent with accepted carryover authority.
- Data Readiness, Morning, Sell Planning, and PM Opportunity resolve the same date/path contract.
- Regression tests cover Day4 carryover and PM Opportunity validation.

## Prohibited Operations Confirmation

Not executed:

- `scripts/runtime_test.py run`
- `scripts/runtime_test.py resume`
- `scripts/runtime_test.py reset`
- `scripts/runtime_test.py rollback`
- `scripts/runtime_test.py backup`
- `scripts/runtime_test.py close`
- Frozen Run edits
- `.runtime` manual edits
- broker write
- external notification
- J-Quants fetch
- order submit
- code fix

