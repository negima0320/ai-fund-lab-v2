# Phase17-BL Feature Date Authority Unification Fix

## Executive Summary

Phase17-BL fixes the Day4 Feature Date authority split that caused PM to reject the Morning BUY Opportunity artifact with `pm_opportunity_contract_mismatch`.

The Runtime now treats the materialized normal Feature Date Contract for the runtime `business_date` as the single formal authority. Runtime Test Runner, Data Readiness, and Position Management use that same selected feature date. The profile `accepted_feature_dates` remains an assertion, not an authority.

Final judgment: `PHASE17_BL_FEATURE_DATE_AUTHORITY_UNIFICATION_ACCEPTED`

## Root Cause

Day4 had two different interpretations of Feature Date authority:

- Runtime Test command selected `feature_date=2026-07-08`.
- Morning produced BUY Opportunity under runtime `business_date=2026-07-09` with `feature_date=2026-07-08`.
- Materialized `.runtime/operations/feature_date_contract/2026-07-09.json` incorrectly carried `selected_feature_date=2026-07-09`.
- Data Readiness and PM used the bad materialized value and PM expected Opportunity rows for `2026-07-09`.
- PM then rejected the correct Morning artifact as `opportunity.contract:target date mismatch`.

## Contract After Fix

- The normal materialized Feature Date Contract for the runtime `business_date` is the only Feature Date authority.
- Runtime Test Runner loads `.runtime/operations/feature_date_contract/{business_date}.json`.
- Runtime Test profile `accepted_feature_dates` is checked only as an assertion.
- Data Readiness rejects CLI `--feature-date` if it differs from the materialized contract.
- If a required normal contract is missing, Data Readiness returns `REVIEW_REQUIRED`; explicit CLI feature date is not promoted to authority.
- PM resolves the BUY Opportunity artifact by runtime `business_date` directory, while validating the artifact `feature_date` and ranking row `target_date` against the selected Feature Date.
- PM validates artifact `business_date` against runtime `business_date`, not against selected `feature_date`.

## Implementation

- `scripts/runtime_test.py`
  - `resolve_feature_date()` now reads the materialized normal contract.
  - `validate_plan_entry_gate()` requires `source=normal_feature_date_contract`, `contract_materialized=true`, and an existing contract path.
  - Profile expected date remains `selected_matches_profile_expected`.

- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
  - `_feature_date_contract_payload()` loads the normal contract by `business_date`.
  - CLI/contract mismatch is `REVIEW_REQUIRED` with `reason=feature_date_authority_mismatch`.
  - Missing normal contract with explicit CLI date is `REVIEW_REQUIRED` with `reason=feature_date_contract_missing`.
  - PM Opportunity default path is `.runtime/runtime_state/buy_ai/{business_date}/opportunity_rankings.json`.

- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
  - Runtime PM Opportunity default path uses `business_date`.
  - PM Opportunity JSON contract checks `payload.business_date == runtime business_date`.
  - PM Opportunity JSON contract checks `payload.feature_date == selected feature_date`.
  - Ranking rows still fail closed if `target_date != selected feature_date`.

## Common Runtime Scope

This is a common Runtime contract for Production, Demo, and Historical. No Phase17-specific, historical-smoke-specific, profile-specific, or run-id-specific business logic was added.

Environment differences remain external-effect differences. Feature Date authority, PM Opportunity validation, and Data Readiness fail-closed behavior are shared.

## Fail-Closed Conditions Preserved

- Missing normal Feature Date Contract remains `REVIEW_REQUIRED`.
- CLI feature date mismatch remains `REVIEW_REQUIRED`.
- Profile expected date mismatch remains plan precondition failure.
- PM Opportunity `business_date` mismatch remains `HALT`.
- PM Opportunity `feature_date` or row `target_date` mismatch remains `HALT`.
- No invalid/missing Opportunity artifact is treated as valid carryover.

## Evidence

Added:

- `tests/runtime_v2/test_phase17_bl_feature_date_authority_unification.py`

Covered:

- Runner uses normal materialized contract, not profile, as authority.
- Data Readiness blocks CLI/contract Feature Date mismatch.
- PM accepts runtime business-date Opportunity artifact with previous selected Feature Date.
- PM fails closed when Opportunity Feature Date differs from selected Feature Date.

## Commands Executed

- `python3 -m pytest -q tests/runtime_v2/test_phase17_bl_feature_date_authority_unification.py`
  - PASS: 4 passed.
- `python3 -m pytest -q tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py`
  - PASS: 10 passed.
- `python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase17_l_historical_asof_and_evidence_isolation.py tests/runtime_v2/test_phase17_bl_feature_date_authority_unification.py`
  - PASS: 23 passed.
- `python3 -m pytest -q tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py tests/runtime_v2/test_phase17_bf_empty_pending_submit_contract.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase17_bh_current_valuation_refresh_temporal_contract.py`
  - PASS: 37 passed.
- `PYTHONPYCACHEPREFIX=/private/tmp/phase17_bl_pycache python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/data_readiness.py src/ai_fund_lab_v2/runtime_v2/position_management/producer.py tests/runtime_v2/test_phase17_bl_feature_date_authority_unification.py`
  - PASS.
- `git diff --check`
  - PASS.
- `python3 -m pytest -q tests/runtime_v2`
  - FAIL: 69 failed, 800 passed.
  - Failures include pre-existing Phase13/14/15 guard expectations and `.runtime` PM Registry accepted hash mismatch after the PM producer source changed.

## Registry Identity Note

The PM producer source hash changed as part of the formal PM Feature Date contract fix. The current SHA256 is:

`4f1c0f7e7409cba1a65238d5c88736624071c7911b8b55ea74974bb7e8e763c7`

The existing `.runtime` Registry still contains an older accepted `POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER` hash. Because Phase17-BL prohibits Frozen Run and `.runtime` manual mutation, the registry was not manually rewritten in this phase. A formal registry acceptance refresh is required before a real resume/run that executes PM registry resolution.

## Resume Boundary

Codex did not run `runtime_test.py run`, `resume`, `reset`, `rollback`, `backup`, or `close`.

Existing Frozen Run state was not edited. `.runtime` runtime state, Pending, Ledger, Current, and Frozen evidence were not manually edited.

Resume boundary assessment:

- Code-level Feature Date authority split is fixed.
- Resume should not be attempted until the PM Runtime Adapter registry identity is refreshed through the formal registry acceptance procedure, because current source hash differs from accepted registry hash.
- After formal registry refresh, restart from the operator-approved clean baseline sequence rather than mutating Frozen Run evidence.

## Files Inspected / Modified

Modified:

- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py`
- `tests/runtime_v2/test_phase17_bl_feature_date_authority_unification.py`

Inspected:

- `docs/phase_reports/phase17_bk_day4_pm_opportunity_contract_mismatch_root_cause.md`
- Runtime Test Runner feature-date resolution
- Data Readiness feature-date contract resolution
- Position Management Opportunity contract validation
- Existing Phase17 Runner/Data Readiness/PM regression tests

## Prohibited Operations Confirmation

Not executed:

- `runtime_test.py run`
- `runtime_test.py resume`
- `runtime_test.py reset`
- `runtime_test.py rollback`
- `runtime_test.py backup`
- `runtime_test.py close`
- Frozen Run edits
- `.runtime` manual state edits
- broker write
- external notification delivery
- J-Quants fetch

