# Phase17-BN Runtime v2 Regression Suite Normalization

## Executive Summary

Final judgment:

```text
PHASE17_BN_REGRESSION_FIX_REQUIRED
```

Phase17-BN was partially executed. The BL Feature Date Contract drift group was normalized: BM B1 now reports `23 passed, 6 xfailed`. The xfailed cases are PM review-only / promotion / apply flows that now correctly reach the formal PM Runtime Adapter Registry identity guard and stop on the accepted artifact hash mismatch. Registry refresh was not performed.

The full Runtime v2 suite is not yet normalized:

```text
39 failed
815 passed
15 xfailed
```

## Actions Completed

- Added `tests/runtime_v2/feature_date_contract_helpers.py` to materialize normal Feature Date Contracts through the production resolver.
- Updated obsolete morning/data-readiness fixtures to create normal Feature Date Contracts and current required feature artifacts.
- Updated review-only fixtures for current human review expiry and PM feature schema requirements.
- Updated submit CLI fixture pre-gate authorities for current Data Readiness requirements.
- Updated Phase17-AE/AL plan-gate expectations to current fail-closed `PRECONDITION_FAILURE` behavior.

## Remaining Work

B2/D/E failures remain, including static guard expectation drift, legacy submit preflight API drift, market refresh feature generation fixture drift, PM/Registry-dependent tests, and shared acceptance runtime state drift.

## Prohibited Operations Confirmation

No `runtime_test.py run/resume/reset/rollback/backup/close` was executed for Runtime evidence. Frozen Run was not edited. `.runtime` was not manually edited. Registry accepted hash was not refreshed. No broker write, external notification, or J-Quants fetch was performed.

## Verification

- BM B1 subset: `23 passed, 6 xfailed`
- Full Runtime v2 suite: `39 failed, 815 passed, 15 xfailed`
- `py_compile` on changed test files: PASS
- `git diff --check`: PASS
