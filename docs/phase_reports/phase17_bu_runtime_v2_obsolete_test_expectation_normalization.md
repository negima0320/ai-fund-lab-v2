# Phase17-BU Runtime v2 Obsolete Test Expectation Normalization

## Executive Summary

Phase17-BU normalized the five obsolete test expectations classified in Phase17-BT. The changes are limited to test expectation and isolation logic. Runtime body code, BS resolver, Ledger state, and Registry accepted identity were not changed.

Final judgment: `PHASE17_BU_TEST_NORMALIZATION_ACCEPTED`

## What Changed

| Test | Previous Defect | New Expectation |
| --- | --- | --- |
| `tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py::test_phase15bm_isolated_fixture_does_not_modify_existing_runtime_root` | Obsolete fixed baseline expectation over active shared Runtime state. | Run safety-blocked submit in tmp_path and verify protected shared .runtime snapshots are unchanged. |
| `tests/runtime_v2/test_phase15bs_demo_broker_write_preconditions_finalization.py::test_phase15bs_existing_runtime_hashes_are_preserved` | Fixed hash baseline over mutable accepted Runtime state; did not measure before/after preservation. | Capture protected shared .runtime snapshots in-test and assert unchanged after reading/report validation. |
| `tests/runtime_v2/test_phase15bt_explicit_demo_broker_write_execution.py::test_phase15bt_existing_runtime_hashes_remain_preserved` | Fixed hash baseline over mutable accepted Runtime state; did not measure before/after preservation. | Capture protected shared .runtime snapshots in-test and assert unchanged after reading/report validation. |
| `tests/runtime_v2/test_phase15bw_runtime_end_to_end_daily_system_test_review.py::test_phase15bw_existing_runtime_hashes_unchanged` | Fixed hash baseline over mutable accepted Runtime state; did not measure before/after preservation. | Capture protected shared .runtime snapshots in-test and assert unchanged after reading/report validation. |
| `tests/runtime_v2/test_phase16av_registry_consumer_cutover.py::test_feature_schema_registry_member_matches_legacy` | Obsolete legacy comparison between accepted Registry artifact and mutable operations artifact with different schema version. | Registry resolver returns accepted FEATURE_SCHEMA member with existing path, content hash match, correct identity, and schema contract readiness; legacy path is checked semantically only when present. |

## Runtime Preservation

The Phase15-family tests no longer embed old shared `.runtime` SHA256 baselines or fixed `target_session_date` values. They now capture protected shared Runtime paths at test start and assert those paths are unchanged after the test action or report validation.

Protected paths:

- `.runtime/pending_order_plan/pending_order_plan.json`
- `.runtime/runtime_state/safety/latest_safety_decision.json`
- `.runtime/persistent_ledger/state.json`
- `.runtime/runtime_state/current_state.json`

No `.runtime` manual edit, Ledger manual fix, or Runtime Test reset/run/resume/rollback/close was performed.

## Registry Semantic Verification

The Feature Schema Registry test now validates accepted Registry identity instead of byte equality with mutable legacy operations evidence.

- Artifact set: `features.shared.accepted_set`
- Member role: `FEATURE_SCHEMA`
- Accepted path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/artifacts/features/shared/schema/2026-07-10/sha256-83f34c493f00cd17/feature_schema.json`
- Accepted SHA256: `83f34c493f00cd17e5bd36b4650dc245673da90dc287704cf423cd03628bc818`
- Content hash matches Registry: `True`
- Accepted schema version: `runtime_v2_feature_contract_v1`
- Legacy path byte equality required: `False`
- Registry refresh performed: `False`

## Verification

- Targeted five tests: `5 passed, 0 failed, 0 xfailed`
- Related regression: `61 passed, 0 failed, 0 xfailed`
- Full Runtime v2 regression: `880 passed, 0 failed, 0 xfailed`
- `py_compile`: PASS
- `git diff --check`: PASS
- JSON validation: PASS

## Files Changed

- `tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py`
- `tests/runtime_v2/test_phase15bs_demo_broker_write_preconditions_finalization.py`
- `tests/runtime_v2/test_phase15bt_explicit_demo_broker_write_execution.py`
- `tests/runtime_v2/test_phase15bw_runtime_end_to_end_daily_system_test_review.py`
- `tests/runtime_v2/test_phase16av_registry_consumer_cutover.py`

## Evidence Files

- `reports/phase17_bu_runtime_v2_obsolete_test_expectation_normalization/summary.json`
- `reports/phase17_bu_runtime_v2_obsolete_test_expectation_normalization/test_change_inventory.json`
- `reports/phase17_bu_runtime_v2_obsolete_test_expectation_normalization/runtime_preservation_verification.json`
- `reports/phase17_bu_runtime_v2_obsolete_test_expectation_normalization/registry_semantic_verification.json`
- `reports/phase17_bu_runtime_v2_obsolete_test_expectation_normalization/full_regression_verification.json`
- `reports/phase_reports/phase17_bu_runtime_v2_obsolete_test_expectation_normalization.json`

## Prohibited Operations Confirmation

- `runtime_test.py run/resume/reset/rollback/close`: not executed
- Frozen Run editing: not performed
- `.runtime` manual edit: not performed
- Ledger manual fix: not performed
- Registry refresh: not performed
- accepted Registry hash change: not performed
- broker write / real submit: not performed
- external notification: not performed
- J-Quants fetch: not performed
- Runtime semantic change: not performed
- BS resolver / performance event contract change: not performed
- new fixed hash baseline: not added
- xfail / skip: not added

## Final Judgment

`PHASE17_BU_TEST_NORMALIZATION_ACCEPTED`
