# Phase32-BE - Run-Scoped Feature-Date Resume Entry-Gate Repair

## Objective

Repair the Phase32-BD defect where `runtime_test resume` could not discover materialized feature-date authority from a prior `market_refresh` job before retrying a failed `data_readiness` job.

Target run:

`runtime-test-historical-extended-smoke-20260831T003243720082Z`

Current continuation point:

`2023-10-12:data_readiness`

Execution restriction followed:

- `runtime_test resume`: not executed
- resume dry-run: not executed
- recover/replay/fresh-run: not executed
- target run mutation: not performed
- 2023-10-11 replay/alteration: not performed

## Root Cause

`runtime_test resume` validates `plan.json` through `validate_plan_entry_gate(..., resume=True)` before entering the job loop.

For `COMPLETED` and `FAILED` days, the entry gate requires run-scoped materialized feature-date authority. The failed day `2023-10-12` was classified as `FAILED`, but its failed job was `data_readiness`. That creates a circularity when the preferred discoverable authority is normally published by the same `data_readiness` job that resume is trying to retry.

The predecessor `market_refresh/runtime_manifest.json` already held materialized PIT feature-date information, but it did not expose the normalized authority shape recognized by `_run_scoped_feature_date_contract_evidence`.

## Repair Performed

Changed `scripts/runtime_test.py` only in the run-scoped feature-date discovery / validation path.

Added:

- `_market_refresh_feature_date_contract_evidence(...)`
- market-refresh normalization inside `_run_scoped_feature_date_contract_evidence(...)`
- resume validation checks:
  - `run_scoped_selected_not_future`
  - `run_scoped_run_binding_current`

The new normalization accepts `market_refresh/runtime_manifest.json` as run-scoped feature-date authority only when:

- the manifest is a `market_refresh` job artifact;
- the `runtime_v2_market_refresh_pipeline` stage has a selected feature date and feature-date contract path;
- the referenced materialized contract exists;
- the contract can be read as JSON;
- selected date is non-empty;
- selected date is not after the business date;
- manifest selected date matches the materialized contract selected date;
- contract requested date matches the business date;
- contract status is propagated and must pass the resume entry checks;
- runtime-test run binding matches the current run when present.

The plan's `runtime_test_plan_schedule_expectation` remains non-authoritative.

## Files Changed

- `scripts/runtime_test.py`
- `tests/runtime_v2/test_phase17_bp_clean_reset_plan_feature_date_entry_gate.py`
- `docs/phase_reports/phase32_be_run_scoped_feature_date_resume_entry_gate_repair.md`

No Runtime trading source, Strategy, PM, PC, PS, Pending state, Ledger state, or target run evidence was intentionally modified by BE.

## Focused Tests

Passed:

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase17_bp_clean_reset_plan_feature_date_entry_gate.py -q
13 passed
```

Passed:

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py -q
60 passed
```

Passed:

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase17_k_runtime_test_runner.py -q
51 passed
```

Coverage:

- failed-at-`data_readiness` resume entry discovers valid prior `market_refresh` materialized feature-date authority;
- plan-expectation-only evidence still fails;
- missing materialized contract fails;
- contract `status != PASS` fails;
- selected feature date mismatch fails;
- future selected date fails;
- stale/cross-run market-refresh evidence fails;
- completed-day feature-date validation remains compatible;
- normal plan/fresh-run expectation path remains unchanged;
- Phase32-BC Pending lifecycle regressions remain PASS.

Total focused validation in BE:

`124 passed`

## Target Run Read-Only Assessment

Current target run state:

- `status`: `HALT`
- `next_job`: `2023-10-12:data_readiness`
- completed tail: `... 2023-10-06, 2023-10-10, 2023-10-11`
- live Pending: prior-day `REVIEW_REQUIRED` / `MIXED_SELL_ITEM_SCOPED_REVIEW` / `target_session_date=2023-10-11`
- `2023-10-12/submit`: absent
- `2023-10-12/execution`: absent

Read-only gate evaluation under repaired source:

- expected gate result: `PASS`
- selected feature date: `2023-10-12`
- requested feature date: `2023-10-12`
- status: `PASS`
- feature-date authority source: `normal_feature_date_contract`
- contract source: `materialized_feature_date_contract`
- contract path: `.runtime/operations/feature_date_contract/2023-10-12.json`
- run-scoped evidence path currently discoverable: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T003243720082Z/daily/2023-10-12/data_readiness/data_readiness.json`
- all repaired resume feature-date checks: PASS

Because the target run already contains a `data_readiness.json` artifact inconsistent with authoritative `run_state` and live Pending, BE also verified the repair against a copied target run with the `2023-10-12/data_readiness` artifacts removed. In that copy, discovery fell back to:

`daily/2023-10-12/market_refresh/runtime_manifest.json`

and still returned:

- expected gate result: `PASS`
- source: `runtime_test_run_scoped_market_refresh`
- feature-date authority source: `normal_feature_date_contract`
- selected feature date: `2023-10-12`
- status: `PASS`
- runtime-test run binding: `PASS`

This proves the BD circularity is repaired without relying on the partially present `data_readiness.json`.

## PIT and Fail-Closed Semantics

Preserved:

- plan expectation is not accepted as authority;
- missing materialized contract fails;
- non-PASS contract fails;
- selected feature date mismatch fails;
- selected feature date after business date fails;
- cross-run market-refresh evidence fails;
- selected date must match plan/profile expectation;
- no future data selection is allowed.

No Strategy or Runtime trading semantics were changed.

## Target Run Continuation Assessment

Safe continuation point:

`2023-10-12:data_readiness`

Same-run continuation expected:

YES. Under repaired source, the resume entry gate should no longer block before `2023-10-12:data_readiness`. The Phase32-BC Pending lifecycle repair should then be able to expire the prior-day mixed review residual at the data-readiness boundary.

Fresh-run required:

NO by BE evidence.

Replay 2023-10-11 required:

NO. 2023-10-11 and 92460 should remain preserved exactly as-is.

## Required Final Answers

- `ROOT_CAUSE_REPAIRED`: YES.
- `FEATURE_DATE_AUTHORITY_DISCOVERY_REPAIRED`: YES.
- `PLAN_EXPECTATION_ACCEPTED_AS_AUTHORITY`: NO.
- `PIT_FAIL_CLOSED_PRESERVED`: YES.
- `CROSS_RUN_STALE_EVIDENCE_REJECTED`: YES.
- `FOCUSED_REGRESSION_RESULT`: PASS, `124 passed`.
- `TARGET_RUN_READ_ONLY_ENTRY_GATE_EXPECTED_RESULT`: PASS.
- `SAFE_CONTINUATION_POINT`: `2023-10-12:data_readiness`.
- `SAME_RUN_CONTINUATION_EXPECTED`: YES.
- `FRESH_RUN_REQUIRED`: NO.
- `RESUME_EXECUTED`: NO.
- `RUNTIME_STATE_MUTATED`: NO.

## Final Judgment

`PHASE32_BE_RUN_SCOPED_FEATURE_DATE_RESUME_ENTRY_GATE_REPAIRED_TARGET_RUN_READY_FOR_USER_RESUME`

The resume entry-gate circularity identified in Phase32-BD is repaired by canonical run-scoped feature-date evidence normalization from `market_refresh`, backed by the materialized feature-date contract. The target run is expected to pass the repaired entry gate from `2023-10-12:data_readiness` without replaying 2023-10-11 or altering 92460.
