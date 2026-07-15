# Phase17-AD Day2 Position Feature Current Authority Blocker Closure

## Judgment

`PHASE17_AD_DAY2_POSITION_FEATURE_CURRENT_AUTHORITY_ACCEPTED`

Frozen Run `runtime-test-historical-smoke-20260715T015929082437` was read-only. I did not run, resume, reset, rollback, backup, close, or mutate that run.

## Root Cause

The Day2 blocker was an integration/runtime contract bug.

`market_refresh` tied Feature artifact generation to J-Quants API fetch permission. In the Historical Runtime Test, `allow_api_fetch=false` correctly prevented external fetch, but it also made Feature Refresh run as:

```text
dry_run: true
execute: false
feature_generation_executed: false
```

As a result, Day2 audited an existing empty `position_feature_input.parquet` instead of regenerating Position Feature rows from Runtime-owned Current. Consumer readiness then correctly saw that `.runtime/persistent_ledger/state.json` had five positions and halted:

```text
reason: consumer_schema_review_required:pm
pm reason: pm_feature_empty_with_current_positions
```

The older evidence only had `position_feature_empty_no_current_positions`, so producer-side Current resolution was ambiguous.

## Fix

Updated `src/ai_fund_lab_v2/operations/market_refresh.py`:

- Decoupled local Feature artifact generation from J-Quants API fetch.
- `allow_api_fetch=false` still blocks external fetch, but Feature Refresh now executes against local normalized inputs.
- Added a runtime-root resolver that supports both `.runtime` and `.runtime/operations` roots.

Updated `src/ai_fund_lab_v2/paper_trading/feature_refresh.py`:

- Position Feature now resolves Current through the Runtime v2 Asset SoT pointer.
- `current_state.json` is not treated as Asset SoT; `asset_state_source=persistent_ledger/state.json` is resolved.
- Evidence now records Current authority path, Current position count, position as-of, feature target date, no-fill carry, input/matched/output counts, and reason.
- Current with positions but zero PM output fails closed as `position_feature_current_output_mismatch`.
- Confirmed empty Current remains a valid zero-row READY case.

Updated `src/ai_fund_lab_v2/runtime_v2/market_refresh/consumer_readiness.py`:

- PM consumer readiness uses the same Asset SoT authority.
- Missing/unknown Current remains review-required.
- Current/output mismatch is reported explicitly.

Updated `scripts/runtime_test.py`:

- `run --run-id` now requires an existing exact plan directory.
- `plan.json.run_id` must exactly match requested `--run-id`.
- Missing trailing `Z` is rejected; similar candidates may be shown but are not auto-selected.

## Contract

- Formal Asset SoT: `.runtime/persistent_ledger/state.json`
- Runtime state pointer: `.runtime/runtime_state/current_state.json` with `asset_state_source=persistent_ledger/state.json`
- Day2 target date: `2026-07-07`
- Position authority as-of: `2026-07-06`
- No-fill carry: allowed when Current is READY and position authority is previous business day
- Expected PM rows after fix: `5`
- Broker snapshot, demo initial holdings, paper ledger PnL, cash, total equity, safety result, and runtime-test status are not PM AI inputs.

## Run ID Issue

The trailing `Z` mismatch is classified separately as a Runner identity issue.

Frozen evidence contains:

```text
plan.json.run_id: runtime-test-historical-smoke-20260715T015929082437
run_state.run_id: runtime-test-historical-smoke-20260715T015929082437
```

No `runtime-test-historical-smoke-20260715T015929082437Z` evidence directory exists. The fix makes future `--run-id` execution exact-match only.

## Schema Cleanup Relation

The Frozen Run still contains legacy schema values such as `phase17_k_run_state_v1`. Those artifacts predate Phase17-AC cleanup and were not modified. This phase does not mix schema cleanup with the Position Feature blocker fix.

## Verification

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_ad_position_feature_current_authority.py
```

Result: `6 passed`

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_ad_position_feature_current_authority.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py
```

Result: `39 passed`

Passed:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/phase17ad_pycache python3 -m py_compile src/ai_fund_lab_v2/paper_trading/feature_refresh.py src/ai_fund_lab_v2/runtime_v2/market_refresh/consumer_readiness.py src/ai_fund_lab_v2/operations/market_refresh.py scripts/runtime_test.py tests/runtime_v2/test_phase17_ad_position_feature_current_authority.py
```

## Evidence

Evidence directory:

`reports/phase17_ad_day2_position_feature_current_authority_blocker_closure/`

Files:

- `frozen_run_inventory.json`
- `day1_current_authority.json`
- `day2_position_feature_failure.json`
- `position_feature_current_resolution_trace.json`
- `asset_sot_path_audit.json`
- `no_fill_carry_contract.json`
- `symbol_alignment_audit.json`
- `forbidden_ai_input_audit.json`
- `run_id_exact_match_audit.json`
- `test_results.json`
- `external_effect_audit.json`

Machine-readable summary:

`reports/phase_reports/phase17_ad_day2_position_feature_current_authority_blocker_closure.json`

## External Effects

- Frozen Evidence modified: no
- Runtime Test run/resume/reset/rollback/backup/close: no
- Runtime state mutation: no
- Pending mutation: no
- Persistent Ledger mutation: no
- Submit/execution/current valuation apply: no
- J-Quants API fetch: no
- Demo broker write: no
- Production broker access: no
- External notification: no
- Artifact Registry update: no
- AI model retraining: no

Next clean Runtime Test rerun is allowed from the beginning of the prescribed lifecycle.
