# Phase20-O: Historical Fresh Run Initial Current Temporal Authority Correction

## 1. Executive Summary

Phase20-O corrected Historical Fresh Run Reset initial Current temporal authority. Reset no longer writes the wall-clock execution timestamp as the only usable Current `as_of` for an initial empty portfolio. Fresh Run now passes the first planned business date into Reset, and Reset writes explicit logical position authority fields.

Final judgment:

```text
PHASE20_O_INITIAL_CURRENT_TEMPORAL_AUTHORITY_CORRECTED_FRESH_RUN_REQUIRED
```

## 2. Scope and Non-goals

Scope was limited to Runtime Test Reset / Fresh Run initial Current metadata, temporal evidence, documentation, and targeted regression.

No AI, Opportunity, PM, Risk, Capital Allocation, Broker, Accepted Generation, Training, Calibration, Validation, long Historical run, or Full Backtest was changed.

## 3. Source Run and Failure Evidence

Source run:

```text
runtime-test-historical-extended-smoke-20260722T075820251188Z
```

Failure:

```text
business_date = 2026-06-15
job = market_refresh
Runtime CLI exit_code = 20
Fresh Run status = HALT
Fresh Run exit_code = 30
completed_days = 0
reason = consumer_schema_review_required:pm
direct PM consumer reason = current_position_state_as_of_after_feature_target_date
```

Market, Historical as-of, Candidate, Opportunity, and Capital evidence were ready. Position Feature alone stopped because Current position state appeared to be in the future.

## 4. Reset Ledger Evidence

Old Reset Current:

```text
source = runtime_test_reset
positions = []
current_positions_unknown = false
current_state_confirmed_empty = true
temporal_status = READY
review_required = false
cash = 1000000
total_equity = 1000000
business_date = ""
as_of = 2026-07-22T07:58:12.394517Z
position_state_as_of = MISSING
current_position_status = MISSING
no_position = MISSING
no_position_reason = MISSING
position_state_source = MISSING
```

Because explicit `position_state_as_of` was absent, the resolver used legacy `as_of`, which was a wall-clock timestamp after the 2026-06-15 feature target date.

## 5. Historical Logical Time vs Wall-clock Time

Logical time fields:

```text
business_date
as_of
position_state_as_of
```

Wall-clock fields:

```text
created_at
updated_at
reset_executed_at
```

Historical Runtime state must be bound to historical logical business dates. Artifact creation time remains real wall-clock evidence and is not used as position-state authority.

## 6. Reviewed Documents

- `docs/phase_reports/phase20_n_empty_position_authority_and_pm_consumer_continuity_correction.md`
- `docs/phase_reports/phase20_m_reduce_minimum_tradable_quantity_contract_correction.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/01_requirements/phase_roadmap.md`

## 7. Reviewed Implementation

- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/runtime_v2/current_position_authority.py`
- `src/ai_fund_lab_v2/paper_trading/feature_refresh.py`
- `src/ai_fund_lab_v2/runtime_v2/market_refresh/consumer_readiness.py`
- `tests/runtime_v2/test_phase17_k_runtime_test_runner.py`
- `tests/runtime_v2/test_phase17_ad_position_feature_current_authority.py`
- `tests/runtime_v2/test_phase15an_feature_consumer_readiness.py`

## 8. Fresh Run Lifecycle

Fresh Run already builds a plan preview before mutating state:

```text
status
backup
reset
plan
run
validate
close
```

The plan preview resolves `requested_start_date` before Reset. Phase20-O uses that first planned business date as Reset initial logical position date.

## 9. Existing Temporal Contract

The Temporal Freshness Contract states that `runtime_business_date`, `feature_date`, `position_state_as_of`, `valuation_as_of`, and artifact generation timestamps are separate concepts. It also retires the old rule:

```text
Current.as_of == business_date
```

Explicit temporal fields must be preferred over legacy `as_of`.

## 10. Initial Logical Date Resolution

Resolved policy:

```text
initial_date_policy = historical_fresh_run_first_business_date
resolved_initial_position_state_date = plan.requested_start_date
```

For the failed run:

```text
requested_start_date = 2026-06-15
resolved_initial_position_state_date = 2026-06-15
```

No user specification decision is required because the existing Temporal Contract and Fresh Run plan authority determine this.

## 11. Initial Position Authority Contract

Reset now writes:

```text
source = runtime_test_reset
positions = []
current_positions_unknown = false
current_state_confirmed_empty = true
current_position_status = READY
no_position = true
no_position_reason = runtime_test_initial_empty_portfolio
position_state_source = runtime_test_reset
position_state_as_of = resolved_initial_position_state_date
business_date = resolved_initial_position_state_date
as_of = resolved_initial_position_state_date
temporal_status = READY
review_required = false
```

## 12. Initial Valuation Contract

For an initial empty portfolio:

```text
market_value = 0
unrealized_pnl = 0
current_valuation_status = NOT_REQUIRED_EMPTY
valuation_as_of = ""
source_market_date = ""
```

No market valuation is fabricated. The empty market value is known from empty positions.

## 13. Root Cause

Reset wrote `created_at` wall-clock time to the legacy `as_of` field while omitting explicit logical `position_state_as_of`. Phase20-N correctly treated that fallback date as future state for the 2026-06-15 feature target.

## 14. Corrected Reset Producer

Changes:

- `reset` accepts optional `--initial-position-state-date`.
- `fresh-run` passes `plan_preview.requested_start_date` to `reset`.
- Reset writes explicit logical and wall-clock fields.
- Invalid initial date fails closed with `PRECONDITION_FAILURE`.

## 15. Reset / Plan Authority Ordering

Fresh Run keeps the existing Backup / Reset safety ordering. Plan preview is built before mutation and used only as request authority for Reset logical date. The formal persisted plan is still written after Reset.

## 16. Position Feature Continuity

With corrected Reset Current:

```text
current_authority_status = READY_EMPTY
Position Feature = schema-valid 0 rows
PM Consumer = NOT_REQUIRED evidence with pm_schema_status READY compatibility
Market Refresh = PASS in targeted fixture
```

The future-state guard remains active.

## 17. Fail-closed Cases

Still fail-closed:

```text
start date missing
invalid initial position state date
initial logical date unresolved
position_state_as_of after feature target date
positions not list
initial cash invalid
conflicting position metadata
reset artifact write failure
reset verification failure
```

Reset does not fallback to wall-clock as logical date when an explicit initial date is required.

## 18. Backward Compatibility

Reset without `--initial-position-state-date` retains legacy behavior for direct compatibility, but Fresh Run now supplies the logical date. Phase20-N READY_EMPTY / UNKNOWN separation is unchanged. Phase20-M REDUCE contract is unchanged.

## 19. User Specification Decision

```text
SPEC_DECISION_REQUIRED = false
```

Existing Temporal Contract and Fresh Run plan authority resolve the policy: Historical Fresh Run initial Current uses the first planned business date as logical initial position date.

## 20. Resume / Fresh Run Decision

Decision:

```text
ABANDON_AND_FRESH_RUN_REQUIRED
```

Reason: the halted run persisted Reset and Market Refresh evidence generated under the old initial temporal authority. Formal acceptance requires a fresh run with corrected Reset evidence from the start.

## 21. Remaining Gaps

- Direct `reset` can still be used without logical date for legacy workflows; Fresh Run is corrected.
- The reset CLI exposes `--initial-position-state-date`, but operators should normally use `fresh-run`.

## 22. Runtime Impact

Runtime impact is limited to Historical Fresh Run Reset initial Current temporal metadata and evidence.

## 23. Strategy Impact

No Strategy behavior changed.

## 24. Authority Impact

Authority is clarified:

```text
Plan preview requested_start_date = initial logical position authority
Reset created_at / updated_at / reset_executed_at = wall-clock evidence
Current Position Authority resolver = future-state guard remains enforced
```

## 25. Validation

Short validation executed:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_o_pycache python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase17_ad_position_feature_current_authority.py tests/runtime_v2/test_phase15an_feature_consumer_readiness.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_o_pycache python3 -m pytest -q tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py tests/runtime_v2/test_phase20_j_performance_observability.py tests/runtime_v2/test_phase20_k_performance_observability_consumer.py tests/runtime_v2/test_phase20_l_long_run_readiness_destructive.py
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_o_pycache python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/current_position_authority.py src/ai_fund_lab_v2/paper_trading/feature_refresh.py src/ai_fund_lab_v2/runtime_v2/market_refresh/consumer_readiness.py
python3 -m json.tool reports/phase_reports/phase20_o_historical_fresh_run_initial_current_temporal_authority_correction.json >/dev/null
git diff --check
```

Result:

```text
43 passed
25 passed
py_compile PASS
json validation PASS
git diff --check PASS
```

Long Historical, Broker, Training, Calibration, Validation, and Full Backtest were not executed.

## 26. Final Judgment

```text
PHASE20_O_INITIAL_CURRENT_TEMPORAL_AUTHORITY_CORRECTED_FRESH_RUN_REQUIRED
```
