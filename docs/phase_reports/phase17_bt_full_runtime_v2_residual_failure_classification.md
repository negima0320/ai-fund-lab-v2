# Phase17-BT Full Runtime v2 Residual Failure Classification

## Executive Summary

Phase17-BT classified the five residual full `tests/runtime_v2` failures observed after Phase17-BS.

Final judgment: `PHASE17_BT_RESIDUALS_CLASSIFIED_FIX_READY`

No BS genuine regression was found. All five failures reproduce individually and are independent of full-suite ordering. The target `.runtime` / Registry files were not mutated by reproduction. The correction scope is limited to test expectation/isolation cleanup; Registry refresh is not justified by the evidence gathered here.

## Classification Summary

- Full regression context: 875 passed, 5 failed
- BS-related failures: 0
- Individual reproduction: 5/5 reproduced in isolated pytest selection
- Order dependence: none confirmed; failures reproduce without full suite ordering
- Code fixes required: 0
- Test fixes required: 5
- Registry refresh required: 0

| Test | Classification | BS Dependency | Requires Test Fix | Requires Registry Refresh |
| --- | --- | --- | --- | --- |
| `tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py::test_phase15bm_isolated_fixture_does_not_modify_existing_runtime_root` | `OBSOLETE_FIXED_BASELINE_EXPECTATION` | `NONE_CONFIRMED` | true | false |
| `tests/runtime_v2/test_phase15bs_demo_broker_write_preconditions_finalization.py::test_phase15bs_existing_runtime_hashes_are_preserved` | `OBSOLETE_FIXED_BASELINE_EXPECTATION` | `NONE_CONFIRMED` | true | false |
| `tests/runtime_v2/test_phase15bt_explicit_demo_broker_write_execution.py::test_phase15bt_existing_runtime_hashes_remain_preserved` | `OBSOLETE_FIXED_BASELINE_EXPECTATION` | `NONE_CONFIRMED` | true | false |
| `tests/runtime_v2/test_phase15bw_runtime_end_to_end_daily_system_test_review.py::test_phase15bw_existing_runtime_hashes_unchanged` | `OBSOLETE_FIXED_BASELINE_EXPECTATION` | `NONE_CONFIRMED` | true | false |
| `tests/runtime_v2/test_phase16av_registry_consumer_cutover.py::test_feature_schema_registry_member_matches_legacy` | `OBSOLETE_LEGACY_COMPARISON` | `NONE_CONFIRMED` | true | false |

## Phase15 Hash Preservation Failures

Four Phase15-family failures are obsolete fixed baseline expectations over the shared repository `.runtime`:

- `pending_order_plan.json` currently has `state=EMPTY`, `active_pending=false`, `target_session_date=2026-07-10`.
- The old tests allow only `""`, `2026-07-08`, or `2026-07-09`, or hard-code SHA256 values from an older Phase15 state.
- Current accepted Historical Smoke Day5 state is legitimate active Runtime state drift, not a BS mutation.
- The tests do not compute before/after hashes around their isolated scenario; they compare against old constants.

Recommended fix: convert these tests into mutation preservation checks that capture the current shared `.runtime` hash before execution and compare after execution, or move the assertions to isolated temp runtime roots. Do not update fixed hashes blindly.

## Registry Failure

The Feature Schema failure is classified as `OBSOLETE_LEGACY_COMPARISON`.

- Artifact set: `features.shared.accepted_set`
- Member role: `FEATURE_SCHEMA`
- Accepted path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/artifacts/features/shared/schema/2026-07-10/sha256-83f34c493f00cd17/feature_schema.json`
- Accepted SHA256: `83f34c493f00cd17e5bd36b4650dc245673da90dc287704cf423cd03628bc818`
- Registry content hash match: `True`
- Legacy path: `.runtime/operations/feature_consumer_readiness/2026-07-10.json`
- Legacy SHA256: `fa443471afa228c54a28a0a1e6041ea1a93b97f68b6b8e175e35fa4817c0ff63`
- Accepted schema version: `runtime_v2_feature_contract_v1`
- Legacy schema version: `runtime_v2_feature_contract_v2`
- Path match: `False`
- Hash match: `False`

The Registry accepted member is internally consistent. The failing assertion compares the accepted Registry member to a mutable legacy operations readiness artifact. This is not a Registry identity failure caused by BS and does not currently meet formal refresh criteria.

Recommended fix: validate Registry resolver integrity against the accepted member content hash and acceptance evidence. If legacy compatibility still matters, compare semantic compatibility explicitly instead of requiring byte equality with `.runtime/operations/feature_consumer_readiness/2026-07-10.json`.

## BS Isolation

BS changed files:

- `src/ai_fund_lab_v2/runtime_v2/ledger/performance_events.py`
- `src/ai_fund_lab_v2/runtime_v2/ledger/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `tests/runtime_v2/test_phase17_bs_canonical_performance_event_contract.py`

The five failing tests do not import these code paths for their failing assertions, and their compared paths are shared `.runtime` files or Registry/legacy feature schema artifacts, not BS-changed files.

## Evidence Files

- `reports/phase17_bt_full_runtime_v2_residual_failure_classification/summary.json`
- `reports/phase17_bt_full_runtime_v2_residual_failure_classification/failure_inventory.json`
- `reports/phase17_bt_full_runtime_v2_residual_failure_classification/hash_comparison_matrix.json`
- `reports/phase17_bt_full_runtime_v2_residual_failure_classification/registry_identity_audit.json`
- `reports/phase17_bt_full_runtime_v2_residual_failure_classification/bs_dependency_matrix.json`
- `reports/phase_reports/phase17_bt_full_runtime_v2_residual_failure_classification.json`

## Commands Executed

- Individual pytest reproduction for the five failing tests
- Read-only SHA256 collection for compared paths
- Source inspection with `sed`, `rg`, and `git log`
- Registry resolver inspection via `resolve_feature_schema_artifacts()`
- JSON validation with `python3 -m json.tool`

## Prohibited Operations Confirmation

- `runtime_test.py run/resume/reset/rollback/close`: not executed
- Frozen Run editing: not performed
- `.runtime` manual edit: not performed
- Ledger manual fix: not performed
- Registry refresh: not performed
- broker write / real submit: not performed
- external notification: not performed
- J-Quants fetch: not performed
- baseline hash unconditional update: not performed
- xfail/assertion removal/code fix before classification: not performed

## Final Judgment

`PHASE17_BT_RESIDUALS_CLASSIFIED_FIX_READY`
