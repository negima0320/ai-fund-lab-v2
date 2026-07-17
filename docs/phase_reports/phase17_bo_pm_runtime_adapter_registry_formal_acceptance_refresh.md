# Phase17-BO PM Runtime Adapter Registry Formal Acceptance Refresh

## Executive Summary

Final judgment: `PHASE17_BO_PM_RUNTIME_ADAPTER_REGISTRY_ACCEPTED`

The formal Registry acceptance refresh for `POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER` completed through the append-only Registry acceptance procedure. The PM Runtime Adapter path stayed unchanged and the accepted source identity was refreshed to the current Phase17-BL implementation hash.

## Registry Before / After

- Path before: `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- Path after: `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- SHA256 before: `d08d854266f6822f322a7947fd7deb20a2906d2a56806d030e2618114bdcaa4b`
- SHA256 after: `4f1c0f7e7409cba1a65238d5c88736624071c7911b8b55ea74974bb7e8e763c7`
- Classification: same formal path, source identity changed.
- Active PM set after: `control.position_management.accepted_set@sha256-ca33e52e6a73b8af`
- Accepted event after: `event-6c1a4f29-c6e7-41c7-aafa-8b1f570f3e88-2fb3747fd2bfb30c`

## Producer Change Audit

The source diff is limited to the Phase17-BL Feature Date authority unification:

- Default PM Opportunity lookup uses runtime `business_date`.
- Opportunity payload `business_date` is validated against runtime `business_date`.
- Opportunity `feature_date` and ranking row `target_date` remain validated against selected Feature Date.
- Missing/mismatched artifacts still fail closed.
- No Production/Demo/Historical split or test-only authority was added.

## Registry Refresh Procedure

Command:

```bash
PYTHONPATH=src python3 scripts/phase17_bo_pm_runtime_adapter_registry_acceptance_refresh.py
```

The wrapper uses the existing formal B1I-B append-only acceptance machinery: evidence bundle creation, DRAFT/VALIDATED/LEGACY/ACCEPTED event flow, full log validation, index build, checkpoint, resolver check, and fail-closed mismatch test. No manual Registry JSON edit was performed.

## Verification

- Targeted Registry tests: `2 passed`.
- PM / Registry related subset: `64 passed`.
- Full Runtime v2 suite: `869 passed, 0 failed, 0 xfailed, 2 warnings`.
- `git diff --check`: PASS.
- `py_compile` for changed Python files: PASS.
- Registry JSON / phase JSON validation: PASS.

## Xfail Resolution

All 24 BN2 Registry-dependent xfails were removed or resolved. Full suite now reports zero xfail/skipped tests.

## Clean Baseline Eligibility

Clean baseline eligibility: `PASS`.

Do not resume `runtime-test-historical-smoke-20260715T111433056797Z`; it contains BL-before Day4 evidence. The next operator action is a new clean Historical Smoke phase from an approved clean baseline.

## Prohibited Operations Confirmation

Not executed: `runtime_test.py run/resume/reset/rollback/backup/close`, Frozen Run edit, `.runtime` manual trading-state edit, broker write, order submit, external notification, J-Quants fetch, unvalidated hash direct-write, or xfail-based failure hiding.
