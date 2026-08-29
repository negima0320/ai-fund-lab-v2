# Phase32-V PM Runtime Adapter Accepted Artifact Registry Refresh

## Executive Summary

Phase32-V refreshed only the formal accepted artifact registry identity for `POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`.

The inherited Phase32-U HALT was caused by an accepted artifact member hash mismatch on 2022-10-03 morning in `runtime-test-historical-extended-smoke-20260827T032942118416Z`. The active accepted registry member still referenced `36f081ee0c3c9ec1b39e00ed83d01e931af8cfc0754d47303deb548dd8df04db`, while the current Phase32-T `producer.py` source hash was `96b55567877f26f12444439261c00c2afa5105d97512be2c2306283e474a14a2`.

The existing append-only PM adapter acceptance writer workflow was used with Phase32-V evidence identity. No PM strategy logic, REENTRY logic, Cash, PC/MCC, Risk Pacing, sizing, SELL behavior, model, threshold, runtime state, resume, replay, fresh-run, or backtest was changed or executed.

## Inherited HALT

- Run: `runtime-test-historical-extended-smoke-20260827T032942118416Z`
- Halt boundary: `2022-10-03:morning`
- Exit code: `30`
- Exact reason: `position management unavailable before strategy planning: artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`
- Phase32-U source: `docs/phase_reports/phase32_u_post_t_fresh_run_day0_morning_halt_root_cause_audit.md`

## Registry Authority

| Item | Value |
|---|---|
| Artifact set type | `POSITION_MANAGEMENT_POLICY_SET` |
| Artifact set id | `control.position_management.accepted_set` |
| Member role | `RUNTIME_ADAPTER` |
| Registered physical path | `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` |
| Authority mode | `ACCEPTED_CURRENT_PATH` |
| Old accepted PM set | `control.position_management.accepted_set@sha256-fd83589a6f000156` |
| New accepted PM set | `control.position_management.accepted_set@sha256-c3849b55a8a4f9f4` |
| New accepted event | `event-6fd3be5e-3ef9-4510-9fe9-4f14ef137b23-a7cf03f768be3e1f` |
| Registry root | `.runtime/artifact_registry` |
| Formal evidence id | `control_position_management_accepted_current_path_phase32_v` |

## Hash Refresh

| Field | Before | After |
|---|---:|---:|
| Accepted `RUNTIME_ADAPTER` hash | `36f081ee0c3c9ec1b39e00ed83d01e931af8cfc0754d47303deb548dd8df04db` | `96b55567877f26f12444439261c00c2afa5105d97512be2c2306283e474a14a2` |
| Actual `producer.py` hash | `96b55567877f26f12444439261c00c2afa5105d97512be2c2306283e474a14a2` | `96b55567877f26f12444439261c00c2afa5105d97512be2c2306283e474a14a2` |
| Runtime adapter hash match | `NO` | `YES` |

Related PM set member verification after refresh:

| Member | Hash Match |
|---|---|
| `BEHAVIOR_CONTRACT` | `YES` |
| `CODE_POLICY` | `YES` |
| `CONSUMER_COMPATIBILITY` | `YES` |
| `FEATURE_VERSION` | `YES` |
| `POLICY_VERSION` | `YES` |
| `REGRESSION_EVIDENCE` | `YES` |
| `RUNTIME_ADAPTER` | `YES` |

Only the accepted `RUNTIME_ADAPTER` identity changed. The other resolved member hashes still match their physical artifacts.

## Formal Refresh Workflow

Formal workflow used:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/phase32v_pycache PYTHONPATH=src python3 - <<'PY'
# Loaded scripts/phase17_b1i_b_pm_adapter_authority_resolution.py
# Set Phase32-V VERSION, REPORT_ROOT, PHASE_DOC, PHASE_JSON,
# EVIDENCE_ID=control_position_management_accepted_current_path_phase32_v,
# PREVIOUS_ACCEPTED_ADAPTER_HASH=36f081ee0c3c9ec1b39e00ed83d01e931af8cfc0754d47303deb548dd8df04db,
# then executed module.main().
PY
```

The workflow produced DRAFT and VALIDATED events for the new PM set, then atomically appended LEGACY for the old accepted PM set and ACCEPTED for the new PM set. It also rebuilt the materialized registry index and checkpoint, and ran resolver/authority validation. No registry JSON hash was manually edited.

Formal writer output:

- Final judgment: `PHASE17_B1I_B_PM_ADAPTER_AUTHORITY_ACCEPTED`
- New PM set: `control.position_management.accepted_set@sha256-c3849b55a8a4f9f4`
- Source hash: `96b55567877f26f12444439261c00c2afa5105d97512be2c2306283e474a14a2`
- Event log after replacement hash: `a806b30f0556ac43a337afc11151408dd22d6b557f03494aa1facdf6bbe6130c`

## Changed Files

Formal registry/evidence outputs:

- `.runtime/artifact_registry/events/registry_events.jsonl`
- `.runtime/artifact_registry/index/registry_index.json`
- `.runtime/artifact_registry/checkpoints/latest.json`
- `.runtime/artifact_registry/evidence/manifests/control_position_management_accepted_current_path_phase32_v/artifact_set_manifest.json`
- `.runtime/artifact_registry/evidence/manifests/control_position_management_accepted_current_path_phase32_v/artifact_set_manifest.draft.json`
- `.runtime/artifact_registry/evidence/acceptance/control_position_management_accepted_current_path_phase32_v/acceptance_report.json`
- `.runtime/artifact_registry/evidence/bundles/control_position_management_accepted_current_path_phase32_v/evidence_bundle.json`
- `.runtime/artifact_registry/evidence/approvals/control_position_management_accepted_current_path_phase32_v/*.json`
- `.runtime/artifact_registry/evidence/lineage/control_position_management_accepted_current_path_phase32_v/lineage_review.json`
- `.runtime/artifact_registry/evidence/freeze/control_position_management_accepted_current_path_phase32_v/freeze_manifest.json`
- `.runtime/artifact_registry/evidence/compatibility/control_position_management_accepted_current_path_phase32_v/consumer_compatibility.json`

Formal reports:

- `reports/phase32_v_pm_runtime_adapter_accepted_artifact_registry_refresh/formal_writer_summary.json`
- `reports/phase32_v_pm_runtime_adapter_accepted_artifact_registry_refresh/acceptance_validation_result.json`
- `reports/phase32_v_pm_runtime_adapter_accepted_artifact_registry_refresh/registry_consistency.json`
- `reports/phase32_v_pm_runtime_adapter_accepted_artifact_registry_refresh/protected_state_hashes.json`
- `reports/phase32_v_pm_runtime_adapter_accepted_artifact_registry_refresh/regression_evidence.json`
- `reports/phase32_v_pm_runtime_adapter_accepted_artifact_registry_refresh/consumer_compatibility.json`
- `docs/phase_reports/phase32_v_pm_runtime_adapter_accepted_artifact_registry_refresh.writer.md`
- `docs/phase_reports/phase32_v_pm_runtime_adapter_accepted_artifact_registry_refresh.md`

No production source file was edited during Phase32-V.

## Focused Verification

Pre-refresh integrity:

```text
py_compile producer.py: PASS
tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py: 20 passed
tests/runtime_v2/test_phase20_j_performance_observability.py::test_phase20_j_writes_campaign_fills_realized_slices_and_pm_snapshot
tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py
tests/strategy/test_phase29_l21k_prior_exit_materialization.py: 42 passed
```

Formal writer verification:

```text
PM adapter registry identity/input/consumer tests: 33 passed
Historical submit guard and fill tests: 20 passed
Phase32-T preservation subset: 42 passed
Registry event log: PASS
Registry index: PASS
Registry checkpoint: PASS
Exactly one active eligible PM set: PASS
PM source hash preflight: PASS
PM source hash mismatch fail-closed test: PASS
```

Post-refresh authority check:

```text
accepted_path = src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
accepted_hash = 96b55567877f26f12444439261c00c2afa5105d97512be2c2306283e474a14a2
executing_source_hash = 96b55567877f26f12444439261c00c2afa5105d97512be2c2306283e474a14a2
artifact_instance_id = control.position_management.accepted_set@sha256-c3849b55a8a4f9f4
authority_mode = ACCEPTED_CURRENT_PATH
```

## Phase32-T Regression Preservation

The Phase32-T producer diff remained limited to PM provenance extraction for sell-exit materialization:

- `decision_id` fallback to `pm_decision_id`
- `source_business_date` materialization from item or payload business date
- `position_campaign_id` materialization

The focused regression set covering PM provenance extraction, pending lineage, persistent order/execution provenance, strict-prior bridge, and idempotency passed. Registry refresh did not alter production behavior; it synchronized the accepted artifact identity to the already-reviewed source bytes.

## User Fresh-Validation Recommendation

Do not resume or reuse the halted `runtime-test-historical-extended-smoke-20260827T032942118416Z` as acceptance evidence.

The next validation should be a user-operated new short fresh Historical validation from the current registry state. Codex did not execute a fresh run, replay, resume, or backtest in Phase32-V.

## Final Judgments

PHASE32_V_REGISTRY_REFRESH_REQUIRED = YES

PHASE32_V_FORMAL_REFRESH_WORKFLOW_USED = YES

PHASE32_V_RUNTIME_ADAPTER_HASH_MATCH = YES

PHASE32_V_PM_RUNTIME_ADAPTER_AUTHORITY_PASS = YES

PHASE32_V_UNRELATED_REGISTRY_MEMBERS_CHANGED = NO

PHASE32_V_PHASE32_T_BEHAVIOR_CHANGED = NO

PHASE32_V_REENTRY_LOGIC_CHANGED = NO

PHASE32_V_CASH_LOGIC_CHANGED = NO

PHASE32_V_PC_MCC_CHANGED = NO

PHASE32_V_RISK_PACING_CHANGED = NO

PHASE32_V_REGRESSION_STATUS = PASS

PHASE32_V_SHORT_FRESH_VALIDATION_READY = YES

PHASE32_V_NEXT_STEP = User-operated new short fresh Historical validation; do not resume the Phase32-U halted run.
