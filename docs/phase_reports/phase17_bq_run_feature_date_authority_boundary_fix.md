# Phase17-BQ Runtime Test Run Feature Date Authority Boundary Fix

## Executive Summary

Phase17-BQ investigated the new Historical Smoke halt at:

```text
runtime-test-historical-smoke-20260715T230352237816Z
2026-07-09:data_readiness
exit code 20
reason=feature_date_authority_mismatch
```

Root cause is confirmed and fixed. Phase17-BP correctly downgraded profile-derived Feature Date values to non-authoritative Plan schedule expectations, but the saved Plan job commands still embedded those expectation values as `--feature-date`. Run then reused the saved command verbatim. On Day4, the plan expected carryover `2026-07-08`, while normal Runtime `market_refresh` materialized the authoritative contract as `selected_feature_date=2026-07-09`; Data Readiness correctly failed closed on the mismatch.

Final judgment:

```text
PHASE17_BQ_RUN_FEATURE_DATE_AUTHORITY_FIX_ACCEPTED
```

## Halt Evidence

Observed Evidence:

- Plan Day4 business date: `2026-07-09`
- Plan schedule expectation: `2026-07-08`
- Plan command passed: `--feature-date 2026-07-08`
- Materialized Runtime contract: `.runtime/operations/feature_date_contract/2026-07-09.json`
- Contract selected feature date: `2026-07-09`
- Data Readiness reason: `feature_date_authority_mismatch`
- Mismatch fields: `cli_feature_date`, `contract.selected_feature_date`

Safety was not the failing component. Day4 Data Readiness showed:

```text
previous_empty_pending_present=true
previous_empty_pending_ignored_as_safety_authority=true
safety_authority_type=HISTORICAL_DAILY_NEUTRAL
safety_authority_business_date=2026-07-09
safety_status=READY
```

## Root Cause

The remaining authority split was at the Runtime Test Run boundary:

1. `build_plan()` calculated a non-authoritative schedule expectation.
2. `runtime_cli_command()` embedded that expected date into job commands for `data_readiness`, `morning`, `sell_planning`, and `submit`.
3. `run_command()` and `resume_command()` executed the saved command directly.
4. After `market_refresh`, the official Feature Date Contract could differ from the plan expectation.
5. The following `data_readiness` job still received the stale Plan expectation as CLI input.

Data Readiness behaved correctly by detecting the mismatch and returning `REVIEW_REQUIRED`.

## Fix Boundary

Updated `scripts/runtime_test.py`:

- Added `resolve_run_job_command()`.
- Added `command_with_option()` and `command_without_option()`.
- `run_command()` and `resume_command()` now re-resolve commands immediately before execution.
- For jobs requiring feature dates, the runner reads the materialized normal Feature Date Contract for that business date.
- If present, `--feature-date` is set from `contract.selected_feature_date`.
- If absent, stale Plan expectation is removed rather than promoted to authority.
- Completed job records now include:
  - `planned_command`
  - actual `command`
  - `feature_date_command_resolution`

This keeps the official authority as the materialized Runtime contract and does not weaken Data Readiness mismatch detection.

## Authority Contract

Plan:

- May contain schedule expectation.
- May record carryover expectation.
- Must not become Runtime authority.

Run:

- Must use the materialized Feature Date Contract after `market_refresh`.
- Must not pass stale Plan expectation as `--feature-date`.
- Must preserve fail-closed behavior if CLI and contract truly disagree.

Data Readiness:

- Still returns `REVIEW_REQUIRED` for real CLI/contract mismatch.
- The `feature_date_authority_mismatch` guard was not relaxed.

## Tests

Targeted:

```bash
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase17_bq_run_feature_date_authority_boundary.py tests/runtime_v2/test_phase17_bp_clean_reset_plan_feature_date_entry_gate.py tests/runtime_v2/test_phase17_bl_feature_date_authority_unification.py tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py -q
```

Result:

```text
15 passed
```

Related regression:

```bash
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase17_ae_reset_scope_plan_gate.py tests/runtime_v2/test_phase17_al_runtime_test_clean_baseline_guard.py tests/runtime_v2/test_phase17_l_historical_asof_and_evidence_isolation.py tests/runtime_v2/test_phase17_bh_current_valuation_refresh_temporal_contract.py tests/runtime_v2/test_phase17_m_consumer_wiring_and_feature_temporal_authority.py -q
```

Result:

```text
37 passed
```

Full Runtime v2 regression:

```bash
PYTHONPATH=src python3 -m pytest tests/runtime_v2 -q
```

Result:

```text
874 passed
```

Static checks:

```bash
git diff --check
```

Result: PASS.

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=.pytest_pycache python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/data_readiness.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
```

Result: PASS.

## Runtime Operation Recommendation

Do not resume `runtime-test-historical-smoke-20260715T230352237816Z`.

Reason: the halted run was produced with saved commands containing the old Plan expectation boundary. Although the code now re-resolves commands at execution time, the cleanest audit trail for the 5BD Historical Smoke is a new formal sequence from clean baseline.

Recommended next operator action:

```text
close/rollback-or-reset/backup/plan/run as a new clean Historical Smoke
```

Codex did not run `runtime_test.py run`, `resume`, `reset`, `rollback`, or `close` during Phase17-BQ.

## Prohibited Operations Confirmation

Not performed:

- `runtime_test.py run`
- `runtime_test.py resume`
- `runtime_test.py reset`
- `runtime_test.py rollback`
- `runtime_test.py close`
- Frozen Run editing
- `.runtime` manual editing
- Feature Date Contract manual generation
- Broker write
- order submit
- external notification
- J-Quants fetch
- Registry refresh
