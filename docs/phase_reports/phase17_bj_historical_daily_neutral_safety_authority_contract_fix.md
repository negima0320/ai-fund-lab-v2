# Phase17-BJ Historical Daily Neutral Safety Authority Contract Fix

## Executive Summary

Phase17-BJ implements the correction boundary confirmed in Phase17-BI.

Historical Data Readiness no longer reuses a previous-session `EMPTY / no-action` Pending slot as the current business day's Safety authority. The previous `EMPTY` Pending remains a valid terminal Pending state, but it is ignored as a Safety authority candidate when `target_session_date < business_date`. In that case, Data Readiness resolves a current-day Historical daily neutral Safety authority with explicit audit fields.

Final judgment:

```text
PHASE17_BJ_HISTORICAL_DAILY_NEUTRAL_SAFETY_AUTHORITY_ACCEPTED
```

## Root Cause Addressed

The target run halted at:

```text
runtime-test-historical-smoke-20260715T111433056797Z
2026-07-08:data_readiness
reason=historical_safety_temporal_authority_missing
```

Day2 left a fixed Pending slot in terminal no-action state:

```text
state=EMPTY
active_pending=false
target_session_date=2026-07-07
safety_context.safety_business_date=2026-07-07
```

Day3 Data Readiness evaluated that Pending safety context as a candidate for `2026-07-08`, detected the date mismatch, and had no separate current-day Historical neutral Safety authority resolver.

## Contract Implemented

Historical Data Readiness now distinguishes:

- Same-day Pending Safety context: still usable for same-day `EMPTY / no-action` audit propagation.
- Previous-session `EMPTY / no-action` Pending: Pending remains `READY`, but Safety does not adopt its `safety_context`.
- Current-day Historical daily neutral Safety authority: generated/resolved by Data Readiness only under Historical replay constraints.
- ACTIVE / APPROVED / CONSUMED Pending: their Safety context remains authoritative and mismatches continue to fail closed.
- Production / Demo: missing `latest_safety_decision.json` remains `REVIEW_REQUIRED`; Historical neutral authority is not applied.

The Historical daily neutral resolver validates:

- `mode == historical`
- `broker_environment == historical_simulated`
- `business_date` is the current resolver scope
- `broker_write == false`
- `external_delivery == false`
- runtime test `run_id`, `profile_id`, and `evidence_root` are present in evidence
- Pending lifecycle is compatible with daily neutral Safety resolution

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
  - Added Historical Safety authority constants.
  - Added previous EMPTY Pending detection.
  - Added Historical daily neutral Safety authority resolver.
  - Preserved same-day Pending Safety authority behavior.
  - Added Data Readiness evidence fields for Safety authority source, business date, policy version, previous EMPTY handling, external-effect flags, and runtime test identity.

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
  - Added the new Data Readiness Safety fields to job manifest summary extraction.

- `tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py`
  - Added regression coverage for previous EMPTY, same-day EMPTY, ACTIVE/APPROVED fail-closed, Production/Demo missing Safety, and Historical external-effect fail-closed behavior.

## Evidence Fields

Data Readiness now emits:

```text
safety_authority_type
safety_authority_business_date
safety_authority_source
safety_authority_policy_version
previous_empty_pending_present
previous_empty_pending_ignored_as_safety_authority
historical_neutral_authority_generated_or_resolved
broker_write
external_delivery
runtime_test_run_id
runtime_test_profile_id
runtime_test_evidence_root
final_safety_status
final_safety_reason
```

For the Day3 fixture equivalent:

```text
pending_status=READY
safety_status=READY
previous_empty_pending_present=true
previous_empty_pending_ignored_as_safety_authority=true
historical_neutral_authority_generated_or_resolved=true
safety_authority_type=HISTORICAL_DAILY_NEUTRAL
safety_authority_business_date=2026-07-08
```

## Fail-Closed Preservation

The fix does not relax:

- ACTIVE Pending date/Safety context validation
- APPROVED Pending date/Safety context validation
- CONSUMED Pending Safety context validation
- Production/Demo Safety decision requirements
- broker write prohibition for Historical replay
- external delivery prohibition for Historical replay
- runtime identity evidence requirements for generated Historical neutral authority

`CONSUMED` Pending with mismatched run identity, profile identity, evidence root, safety business date, or missing Safety context still returns `REVIEW_REQUIRED`.

## Production / Demo / Historical Scope

Historical-specific neutral authority is limited to Historical replay mode and `historical_simulated` broker environment. It is not a Runtime Test shortcut and does not use run identity as a trading permission. The identity fields are evidence requirements for replay traceability.

Production and Demo continue to require real Runtime Safety decision evidence. Missing `latest_safety_decision.json` remains `REVIEW_REQUIRED`.

## Tests

Executed:

```text
python3 -m pytest -q tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py
```

Result:

```text
6 passed
```

Executed related regression suite:

```text
python3 -m pytest -q \
  tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py \
  tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py \
  tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py \
  tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py \
  tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py \
  tests/runtime_v2/test_phase17_bf_empty_pending_submit_contract.py \
  tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py \
  tests/runtime_v2/test_phase17_bh_current_valuation_refresh_temporal_contract.py
```

Result:

```text
58 passed
```

Executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase17_bj_pycache python3 -m py_compile \
  src/ai_fund_lab_v2/runtime_v2/data_readiness.py \
  src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py \
  tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py
```

Result:

```text
PASS
```

Executed:

```text
git diff --check
```

Result:

```text
PASS
```

## Prohibited Operations Confirmation

Not executed:

- `runtime_test.py run`
- `runtime_test.py resume`
- `runtime_test.py reset`
- `runtime_test.py rollback`
- `runtime_test.py backup`
- `runtime_test.py close`
- Frozen Run edits
- `.runtime` manual edits
- broker write
- external notification
- J-Quants fetch

## Existing Run Resume Assessment

The target Frozen Run was not resumed or mutated. Based on fixture regression, the Day3 `2026-07-08:data_readiness` blocker is corrected for a future operator-controlled resume or clean rerun. Codex did not perform that resume.

