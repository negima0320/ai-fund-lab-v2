# Phase32-D Post-Phase32-C Morning HALT Authority Repair

## Final Judgment

`PHASE32_D_POST_PHASE32C_MORNING_HALT_REPAIRED`

## Target Run

- Run: `runtime-test-historical-extended-smoke-20260829T204358327307Z`
- Profile: `historical-extended-smoke`
- Start date: `2022-10-03`
- Business days: `100`
- Initial cash: `1000000`
- Observed result: `HALT`, `exit_code=30`, completed days `[]`

No fresh-run, resume, replay, or long Historical validation was executed by Codex.

## Root Cause

The first canonical failure was a PM Runtime Adapter authority mismatch:

`artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`

This occurred before Strategy planning. The target run evidence records:

- `planning_evidence.json`: `position management unavailable before strategy planning: artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`
- `runtime_manifest.json`: `pm_status=HALT`, `pm_input_schema_status=HALT`, `pm_reason=artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`
- `.runtime/runtime_state/position_management/2022-10-03/position_management_decisions.json`: same PM authority halt reason, `decision_count=0`

Classification: `source/artifact authority mismatch`, implemented as an intentional fail-closed safety gate.

## Failure Path

1. Runtime CLI started `2022-10-03:morning`.
2. PM authority preflight resolved active `POSITION_MANAGEMENT_POLICY_SET`.
3. Active accepted PM set pointed to the Phase32-A reactivated generation:
   `control.position_management.accepted_set@sha256-fd83589a6f000156`
4. That generation accepted `RUNTIME_ADAPTER` hash:
   `36f081ee0c3c9ec1b39e00ed83d01e931af8cfc0754d47303deb548dd8df04db`
5. Current executing source hash of `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` was:
   `3da7e3014eeb01770feca63655f9f3aa2bfed882cee050f633423bf85d4eab5a`
6. Runtime halted with exit code `30` before Strategy planning.

## Relation To Phase32-C

Source rollback causality from Phase32-A is no longer the active cause. Phase32-C intentionally changed `producer.py` to preserve campaign identity through PM SELL/EXIT materialization:

`position_campaign_id=str(item.get("position_campaign_id") or item.get("campaign_id") or "")`

That source change correctly changed the Runtime Adapter source hash from `36f081...` to `3da7e301...`. Architecture requires a new formal acceptance for any PM accepted-current-path source change. Therefore Phase32-C caused the new authority mismatch by changing the accepted-current-path source after Phase32-A synchronization.

Phase32-C implementation regression: `NO`. The failure was the expected fail-closed result of source/artifact authority drift, not a provenance/campaign behavior regression.

## Authority Hashes

- Current source commit: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Current `producer.py` hash: `3da7e3014eeb01770feca63655f9f3aa2bfed882cee050f633423bf85d4eab5a`
- Pre-repair active PM set: `control.position_management.accepted_set@sha256-fd83589a6f000156`
- Pre-repair accepted `RUNTIME_ADAPTER` hash: `36f081ee0c3c9ec1b39e00ed83d01e931af8cfc0754d47303deb548dd8df04db`
- Existing accepted evidence for `3da7e301...` before repair: `NO`
- New accepted PM set: `control.position_management.accepted_set@sha256-bad32f7db66db926`
- New accepted PM set hash: `bad32f7db66db926f5c1db2c300ac7713a51224b51c2096675550641bb7a0579`
- New accepted `RUNTIME_ADAPTER` hash: `3da7e3014eeb01770feca63655f9f3aa2bfed882cee050f633423bf85d4eab5a`

## Repair Performed

A new formally accepted PM accepted-current-path generation was created using the existing canonical Phase17 PM authority functions:

- manifest validation
- acceptance evidence bundle validation
- approvals
- append-only `ARTIFACT_DISCOVERED` / `ARTIFACT_VALIDATED` / `ARTIFACT_LEGACY` / `ARTIFACT_ACCEPTED` registry events
- registry index build
- checkpoint creation
- Runtime resolver and source hash preflight
- genuine mismatch fail-closed check

No hashes were manually patched. Hash validation and fail-closed behavior were not weakened. The previous Phase32-A active PM generation became `LEGACY`; it was not reactivated because it did not represent the current source.

## Files And Artifacts Changed

- `scripts/phase32_d_pm_authority_acceptance_repair.py`
- `.runtime/artifact_registry/events/registry_events.jsonl`
- `.runtime/artifact_registry/index/registry_index.json`
- `.runtime/artifact_registry/checkpoints/latest.json`
- `.runtime/artifact_registry/checkpoints/checkpoint-*.json`
- `.runtime/artifact_registry/evidence/*/control_position_management_accepted_current_path_phase32_d/*`
- `reports/phase32_d_post_phase32c_morning_halt_authority_repair/*`
- `docs/phase_reports/phase32_d_post_phase32c_morning_halt_authority_repair.md`

No Strategy, parameter, threshold, weight, Cash policy, Risk Pacing, Re-entry rule, or G129 BUY_ADD semantic change was made in Phase32-D.

## Focused Validation

PASS:

- PM authority resolves for current source:
  accepted hash `3da7e301...` equals executing source hash `3da7e301...`
- Accepted evidence bundle validation: `PASS`
- Registry full-log validation after accepted event: `PASS`
- Registry index build after accepted event: `PASS`
- Registry checkpoint after accepted event: `PASS`
- Genuine hash mismatch fail-closes with `PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH`
- Focused pytest:
  `PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase32d_pycache python3 -m pytest -q tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py tests/runtime_v2/test_phase31_g30_authority_lineage.py tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews`
  Result: `14 passed`

Note: the base Phase17 script initially invoked the broad `tests/artifact_registry` suite after registry append. That broad suite failed on unrelated formal-registration dry-run prerequisites, including missing `.runtime/operations/feature_consumer_readiness/2026-07-10.json`; it was not a PM authority failure and was not used as Phase32-D acceptance evidence.

## Strategy And Regression Judgment

- Strategy semantic change: `NO`
- Phase32-C regression: `NO`
- G129 regression: `NO`
- Runtime/control impact: `YES`, PM authority preflight blocked Runtime until registry acceptance was synchronized
- Repair required: `YES`, because current source had never been accepted as the active PM Runtime Adapter hash

## Exact User Fresh-Run Command

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-10-03 \
  --business-days 100 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```
