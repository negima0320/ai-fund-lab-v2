# Phase22-PW Strategy Shadow Authority and Observability Repair

## Executive Summary

Primary Judgment: `PHASE22_PW_REPAIR_COMPLETE_EXPECTED_SAFE_BLOCK_REMAINS`

Phase22-PVで確認したStrategy Shadow実装不具合と観測性不備を修正した。今回の修正はStrategy ShadowのBLOCKを解除するための緩和ではない。Feature Date Authority、Position Sizing reason code、Source Manifest blocker classification、Strategy Shadow evidence mapping、system-status contract/test isolationを正しく分離した。

Runtime Switchは実行していない。Active Runtime Consumer Eligibilityは変更していない。Artifact Acceptanceの自動昇格も行っていない。

## Evidence

Evidence directory:

`reports/phase22_pw_strategy_shadow_authority_and_observability_repair/`

Key files:

- `executive_summary.json`
- `modified_files.json`
- `feature_date_authority_contract.json`
- `position_sizing_reason_code_contract.json`
- `source_manifest_classification_contract.json`
- `strategy_evidence_mapping.json`
- `system_status_contract.json`
- `existing_5bd_offline_reassessment.json`
- `test_results.json`

## Root Cause Confirmation

PVの根本原因は再確認済み。

1. Strategy Shadowはrun/resume経路でplan-time `day.feature_date` を直接渡していたため、2026-07-09のようにRuntime jobがmaterialized contractで再解決した場合にShadow authorityが古くなり得た。

2. Position Sizingは実ポジションweight超過ではなく、configured maxとSafety capの不整合を `strategy_position_weight_above_safety_cap` と記録していた。

3. Source ManifestはPIT PASSでもreason文字列から `DIRECT_SOURCE_PIT_VIOLATION` を付け得た。

4. Strategy Shadowの監査証跡は複数artifactに分散し、canonical evidence indexが無かった。

5. system-statusのPhase19-era testは、Runtime overview statusとStrategy Shadow readinessを一体のexit 10として期待していた。

## Modified Files

- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/source_manifest.py`
- `tests/runtime_v2/test_phase17_bq_run_feature_date_authority_boundary.py`
- `tests/runtime_v2/test_phase19_ax_system_status.py`
- `tests/strategy/test_phase22_j_position_sizing.py`
- `tests/strategy/test_phase22_ps_source_manifest.py`

## Feature Date Authority Contract

Strategy ShadowのFeature Date Authority priority:

1. Completed Runtime Job `feature_date_command_resolution.selected_feature_date`
2. Materialized Feature Date Contract `selected_feature_date`
3. Plan feature date, only as `REVIEW_REQUIRED` fallback when materialized runtime authority is unavailable

Conflicting completed Runtime job resolutions are `BLOCK`.

Strategy Shadow input manifest and summary now record:

- `planned_feature_date`
- `materialized_feature_date`
- `selected_feature_date`
- `feature_date_authority_source`
- `planned_matches_materialized`
- `feature_date_contract_path`
- full `feature_date_authority`

Run and resume both call the same resolver before `generate_strategy_shadow_for_day`.

## Position Sizing Reason-Code Contract

New reason-code separation:

- `configured_max_position_weight_above_safety_cap`
- `produced_position_weight_above_safety_cap`
- `aggregate_target_weight_above_exposure_cap`

Replaced ambiguous codes:

- `strategy_position_weight_above_safety_cap`
- `target_weight_above_safety_concentration_cap`
- `total_target_weight_above_target_gross_exposure`

The zero-position / zero-weight case no longer reads as produced overweight.

## Source Manifest Classification Contract

Source Manifest blocker records now include:

- `primary_blocker_class`
- `primary_reason_code`
- `secondary_blockers`
- `pit_validation_status`

Added/used classification separation:

- `DIRECT_SOURCE_PIT_VIOLATION`
- `ARTIFACT_ACCEPTANCE_NOT_ELIGIBLE`
- `SOURCE_COVERAGE_INCOMPLETE`
- `CONFIG_SAFETY_CONTRACT_VIOLATION`
- `DOWNSTREAM_COMPONENT_REVIEW_REQUIRED`
- `TEMPORAL_AUTHORITY_MISMATCH`
- `SCHEMA_CONTRACT_VIOLATION`

When `pit_validation.status = PASS`, component blocker classes do not retain `DIRECT_SOURCE_PIT_VIOLATION`.

## Strategy Evidence Mapping

Strategy Shadow now writes:

`strategy_evidence_index.json`

The index maps:

- top-level judgment
- judgment reasons
- Accepted Generation resolution
- Feature Date authority
- PIT validation
- schema/component judgments
- runtime mutation result
- consumer eligibility
- runtime switch result
- source/input manifests

This uses Option B from PW: canonical evidence index, without duplicating all artifacts.

## system-status Contract

Confirmed current contract:

- Overview status reports Runtime/system inspection.
- Strategy Shadow readiness is separate in `strategy_shadow_readiness`.
- Overview may PASS while Strategy Shadow readiness is BLOCK because `production_readiness_impact = NONE_SHADOW_ONLY`.
- Temporary evidence roots without latest closed run are isolated and may return REVIEW_REQUIRED/BLOCK based on current runtime root inspection.
- `--write-evidence` must not mutate accepted generation/current/pending authority.

Phase19-era exit 10 expectation was updated because it conflated model-health review and Shadow readiness with overall Runtime inspection status.

## Existing 5BD Offline Reassessment

No new 5BD fresh-run was executed.

For existing run `runtime-test-historical-smoke-20260728T004341907286Z`:

- 2026-07-09 now resolves Strategy Shadow feature date from completed Runtime job resolutions.
- Planned feature date: `2026-07-08`
- Selected/materialized feature date: `2026-07-09`
- Authority source: `completed_runtime_job_feature_date_command_resolution`
- Authority status: `PASS`

Position Sizing old evidence still contains the old reason code because existing artifacts were not rewritten. Under the repaired producer contract, the equivalent cause is `configured_max_position_weight_above_safety_cap`, not produced overweight.

Expected remaining result: Strategy Shadow may remain `BLOCK` or `REVIEW_REQUIRED` because artifacts are still `DRAFT / NOT_ELIGIBLE` and downstream review conditions remain. That is expected and safe.

## Test Results

PASS:

- `PYTHONPATH=src python3 -m pytest tests/strategy -q`
  - `134 passed`
- `PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase17_bq_run_feature_date_authority_boundary.py tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py tests/runtime_v2/test_phase19_ax_system_status.py tests/runtime_v2/test_phase22_m_strategy_summarize_scope.py tests/runtime_v2/test_phase22_pu_historical_submit_source_identity.py -q`
  - `21 passed`
- `PYTHONPYCACHEPREFIX=/private/tmp/phase22_pw_pycache python3 -m compileall scripts/runtime_test.py src/ai_fund_lab_v2/strategy src/ai_fund_lab_v2/runtime_v2/historical_support`
  - PASS

## Remaining Blockers

- Strategy artifacts remain `DRAFT / NOT_ELIGIBLE`.
- Corporate Event source coverage remains partial.
- Runtime consumer promotion has not been performed.
- Accepted Generation historical PIT authority remains a Runtime Switch review item.
- Long validation has not been run by the operator.
- Human Runtime Switch approval has not been given.

## Required Operator Validation

Operator may run the existing 5BD command again if desired, but Codex did not and must not execute it in PW.

Required next validation remains operator-owned:

- 5BD historical fresh-run after PW
- then longer validation only after review

No Broker connection or Runtime Switch should be performed by default.

## Closure and Runtime Switch Eligibility

Phase22 Closure: `NO`

Runtime Switch Ready: `NO`

Runtime Switch Approved: `NO`

Strategy Production Ready: `NO`

PW repair is complete for authority and observability, but Strategy Shadow remains shadow-only and non-production-consumable.

## Recommended Next Task

Recommended:

`Phase22-PX - Operator 5BD Shadow Validation Review`

Scope:

- Operator reruns 5BD fresh-run.
- Audit regenerated `strategy_evidence_index.json`.
- Confirm 2026-07-09 feature authority.
- Confirm new Position Sizing reason codes.
- Confirm Source Manifest no longer reports PIT violation when PIT PASS.
- Keep Runtime Switch disabled.
