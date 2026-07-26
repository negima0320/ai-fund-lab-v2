# Phase20-N: Empty Position Authority and PM Consumer Continuity Correction

## 1. Executive Summary

Phase20-N corrected the empty-position authority path after a valid full liquidation. Runtime now separates:

```text
NON_EMPTY_READY
READY_EMPTY
UNKNOWN
```

A confirmed empty Runtime-owned portfolio is no longer treated as unknown position authority. Position Feature can produce a schema-valid 0-row artifact, PM consumer remains ready with PM inference `NOT_REQUIRED`, and Market Refresh can continue.

Final judgment:

```text
PHASE20_N_PM_CONSUMER_CONTINUITY_CORRECTED_FRESH_RUN_REQUIRED
```

## 2. Scope and Non-goals

Scope was limited to Current Position Authority resolution, Position Feature empty-state handling, Feature Consumer Readiness PM evidence, Market Refresh continuity, documentation, and targeted regression.

No AI, Opportunity, PM policy, Risk, Capital Allocation, Broker, Accepted Generation, Training, Calibration, Validation, long Historical run, or Full Backtest was changed.

## 3. Source Run and Failure Evidence

Source run:

```text
runtime-test-historical-extended-smoke-20260722T073209419857Z
```

Failure:

```text
business_date = 2026-07-01
job = market_refresh
Runtime CLI exit_code = 20
Fresh Run status = HALT
Fresh Run exit_code = 30
reason = consumer_schema_review_required:pm
pm_schema_status = REVIEW_REQUIRED
consumer_ready = false
```

## 4. 2026-06-30 Exit and Empty State Evidence

On 2026-06-30, the last Runtime-owned position was sold:

```text
symbol = 45640
side = SELL
quantity = 8500
source_decision_type = EXIT
fill_count = 1
executions_count = 1
projected_position_count = 0
projected_market_value = 0
projected_cash = 931300.0
current_apply_status = APPLIED
runtime_owned_projection_status = PASS
reconcile_status = PASS
```

## 5. Persistent Ledger Authority

The Persistent Ledger Current state was an authoritative empty state, not unknown:

```text
business_date = 2026-06-30
as_of = 2026-06-30
current_position_status = READY
current_positions_unknown = false
positions = []
no_position = true
no_position_reason = current_has_no_runtime_owned_positions
position_state_as_of = 2026-06-30
position_state_source = runtime_owned_execution_ledger
temporal_status = READY
review_required = false
market_value = 0
current_valuation_status = READY
```

`current_state_confirmed_empty=false` did not override this Runtime-owned Ledger authority.

## 6. Current Valuation Authority

Current Valuation already treated the same state as ready:

```text
current_position_status = READY
current_valuation_position_count = 0
current_valuation_valued_position_count = 0
current_valuation_market_value = 0
current_valuation_refresh_status = READY
current_valuation_review_required = false
current_valuation_refresh_reason = current_has_no_runtime_owned_positions
```

## 7. 2026-07-01 Misclassification

Position Feature / Consumer Readiness misclassified the empty state:

```text
position status = FEATURE_REFRESH_REQUIRED
reason = current_positions_unknown
current_authority_status = UNKNOWN
current_position_count = 0
input_symbol_count = 0
output_row_count = 0
no_fill_carry_used = true
```

This contradicted Persistent Ledger and Current Valuation authority.

## 8. Reviewed Documents

- `docs/phase_reports/phase20_m_reduce_minimum_tradable_quantity_contract_correction.md`
- `docs/phase_reports/phase20_l_long_run_readiness_destructive_review.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/position_management_reduce_quantity_contract.md`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/01_requirements/phase_roadmap.md`

## 9. Reviewed Implementation

- `src/ai_fund_lab_v2/paper_trading/feature_refresh.py`
- `src/ai_fund_lab_v2/runtime_v2/market_refresh/consumer_readiness.py`
- `src/ai_fund_lab_v2/runtime_v2/current_position_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `tests/runtime_v2/test_phase17_ad_position_feature_current_authority.py`
- `tests/runtime_v2/test_phase15an_feature_consumer_readiness.py`

## 10. Empty / Non-empty / Unknown Contract

`NON_EMPTY_READY`:

```text
positions is a non-empty list
current_positions_unknown = false
current_position_status is READY or VALID_CARRYOVER when present
temporal_status is READY or VALID_CARRYOVER when present
review_required = false
position_state_as_of is not after feature target date
```

`READY_EMPTY`:

```text
positions = []
current_positions_unknown = false
no_position = true or current_state_confirmed_empty = true
position_state_as_of is valid
temporal_status is READY or VALID_CARRYOVER when present
review_required = false
```

`UNKNOWN` / `REVIEW_REQUIRED`:

```text
Ledger missing or unreadable
positions missing or not a list
current_positions_unknown = true
current_position_status not ready
temporal_status not ready
review_required = true
conflicting empty/non-empty metadata
position_state_as_of after feature target date
```

## 11. Root Cause

Position Feature and Feature Consumer Readiness used separate authority interpretations and required `current_state_confirmed_empty=true` for empty `positions=[]`. Runtime-owned Ledger empty evidence using `no_position=true` was therefore misclassified as `UNKNOWN`.

## 12. Corrected Authority Resolution

Added shared resolver:

```text
src/ai_fund_lab_v2/runtime_v2/current_position_authority.py
```

It returns `READY`, `READY_EMPTY`, `UNKNOWN`, `MISSING`, or `REVIEW_REQUIRED` with explicit reason and evidence fields. Feature Refresh and Consumer Readiness now use this shared authority interpretation.

## 13. Position Feature Contract

For `READY_EMPTY`, `position_feature_input.parquet` is generated with required columns and 0 rows.

Evidence:

```text
current_authority_status = READY_EMPTY
position_feature_status = READY_EMPTY
position_feature_reason = current_positions_confirmed_empty
position_feature_row_count = 0
```

No dummy symbol or fabricated position row is generated.

## 14. PM Consumer Contract

For `READY_EMPTY`, PM schema compatibility remains `READY` for existing consumers, while evidence records:

```text
pm_consumer_status = NOT_REQUIRED
pm_inference_required = false
input_symbol_count = 0
output_row_count = 0
runtime_continuation_status = PASS
```

PM Producer already maps an empty holding set to `NO_POSITION`.

## 15. Market Refresh Continuity

When Candidate and Opportunity are ready, Position is `READY_EMPTY`, and Capital is ready, Feature Consumer Readiness is `consumer_ready=true` and Runtime Market Refresh can return `PASS`.

## 16. Temporal / No-fill Carry Semantics

Previous-business-day empty carry is valid when `position_state_as_of` is not after the feature target date and authority is otherwise ready. The evidence records `no_fill_carry_used=true`.

## 17. Fail-closed Cases

Still fail-closed:

```text
missing Ledger
unreadable JSON
positions key missing
positions not list
current_positions_unknown = true
review_required = true
current_position_status not ready
temporal_status not ready
position_state_as_of after feature target date
positions=[] with explicit no_position=false and no confirmed-empty authority
positions non-empty with no_position=true
```

## 18. Backward Compatibility

Non-empty Position Feature generation is unchanged. Legacy `current_state_confirmed_empty=true` empty state remains accepted. Current Valuation behavior is unchanged. Phase20-M REDUCE contract is unchanged.

## 19. Resume / Fresh Run Decision

Decision:

```text
ABANDON_AND_FRESH_RUN_REQUIRED
```

Reason: the halted run persisted a `REVIEW_REQUIRED` Market Refresh manifest and Consumer Readiness artifact under the old authority contract. Because Current Position Authority semantics changed, formal acceptance should use a fresh run rather than mixing old failure evidence with corrected consumer behavior.

## 20. Remaining Gaps

- `pm_schema_status` remains `READY` for compatibility while `pm_consumer_status=NOT_REQUIRED` carries the empty-state semantics.
- Symbol-level lot-size or broker-derived empty confirmation is not added in this phase.
- Existing halted run artifacts remain old evidence until a fresh run is executed.

## 21. Runtime Impact

Runtime impact is limited to Market Refresh / Position Feature / PM consumer continuity for confirmed empty Runtime-owned portfolios.

## 22. Strategy Impact

No Strategy behavior was changed. No PM inference is forced for empty portfolios.

## 23. Authority Impact

Authority is clarified:

```text
Persistent Ledger Current = Position Authority
Current Valuation = consistent empty valuation consumer
Position Feature = 0-row READY_EMPTY artifact producer
PM Consumer = NOT_REQUIRED semantics in evidence
Market Refresh = can continue when empty authority is confirmed
```

## 24. Validation

Short validation executed:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_n_pycache python3 -m pytest -q tests/runtime_v2/test_phase17_ad_position_feature_current_authority.py tests/runtime_v2/test_phase15an_feature_consumer_readiness.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_n_pycache python3 -m pytest -q tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py tests/runtime_v2/test_phase20_j_performance_observability.py tests/runtime_v2/test_phase20_k_performance_observability_consumer.py tests/runtime_v2/test_phase20_l_long_run_readiness_destructive.py
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_n_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/current_position_authority.py src/ai_fund_lab_v2/paper_trading/feature_refresh.py src/ai_fund_lab_v2/runtime_v2/market_refresh/consumer_readiness.py
python3 -m json.tool reports/phase_reports/phase20_n_empty_position_authority_and_pm_consumer_continuity_correction.json
git diff --check
```

Result:

```text
26 passed
25 passed
py_compile PASS
json validation PASS
git diff --check PASS
```

Long Historical, Broker, Training, Calibration, Validation, and Full Backtest were not executed.

## 25. Final Judgment

```text
PHASE20_N_PM_CONSUMER_CONTINUITY_CORRECTED_FRESH_RUN_REQUIRED
```
