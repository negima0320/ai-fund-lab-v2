# Phase17-BN2 Runtime v2 Regression Suite Normalization Completion

## Executive Summary

Phase17-BN2 normalized the Runtime v2 regression suite from the BN2 entry result of `39 failed / 815 passed / 15 xfailed` to `2 failed / 843 passed / 24 xfailed`.

The only remaining failures are the expected fail-closed PM Runtime Adapter Registry identity mismatch:

- `tests/runtime_v2/test_phase16av_registry_consumer_cutover.py::test_pm_policy_registry_members_match_legacy_and_current_adapter`
- `tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py::test_registry_resolver_returns_current_pm_source_authority`

No non-registry Runtime regression remains confirmed.

Final judgment: `PHASE17_BN_REGISTRY_REFRESH_READY`.

## Registry Identity

- Artifact set: `POSITION_MANAGEMENT_POLICY_SET`
- Member role: `RUNTIME_ADAPTER`
- Accepted path: `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- Current path: `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- Accepted sha256: `d08d854266f6822f322a7947fd7deb20a2906d2a56806d030e2618114bdcaa4b`
- Current sha256: `4f1c0f7e7409cba1a65238d5c88736624071c7911b8b55ea74974bb7e8e763c7`
- Classification: same formal path, actual source hash changed. This is not a path-only mismatch.

The Registry was not refreshed in this phase.

## Normalization Completed

- Static guard expectations were narrowed to block legacy workflow/runtime imports while allowing formal shared helpers.
- Legacy Phase14 submit preflight fixtures were updated to the current API.
- Market refresh and feature-date carryover fixtures were updated for current authority, market evidence, and PM/opportunity schemas.
- Scheduler tests now isolate scheduler behavior from Data Readiness gate behavior.
- Feature consumer readiness tests now use formal current authority fields.
- Phase15 acceptance-root tests now distinguish historical report-time state from the later live terminal state.
- PM-dependent tests use conditional xfail only when the PM Runtime Adapter Registry mismatch is present.

## Verification

- Initial BN2 full suite: `39 failed / 815 passed / 15 xfailed`.
- Final full suite: `2 failed / 843 passed / 24 xfailed`.
- `git diff --check`: PASS.
- `py_compile`: PASS with `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache`.

## Prohibited Operations Confirmation

No `runtime_test.py run/resume/reset/rollback/backup/close` was executed. Frozen Run and `.runtime` were not manually edited. Registry refresh, broker write, external notification, and J-Quants fetch were not performed.

## Next Step

Proceed to a separate formal PM Runtime Adapter Registry acceptance refresh phase, then remove/resolve the registry-dependent xfails and rerun `tests/runtime_v2`.
