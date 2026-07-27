# Phase21-C Position Management Artifact Authority Refresh

## 一次判定

```text
PHASE21_C_ARTIFACT_AUTHORITY_REFRESH_PASS
```

Phase21-BでProduction共通コードとして変更した `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` が、Accepted Artifact Registry上の `POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER` member hashと不一致になっていた。

本Phaseではhash検証を回避せず、既存の正式PM Runtime Adapter Acceptance writerを用いて、Artifact生成、Validation、Acceptance、Registry index、checkpointを更新した。

## Authority Inventory

| 項目 | 値 |
|---|---|
| Artifact type | `POSITION_MANAGEMENT_POLICY_SET` |
| Artifact set id | `control.position_management.accepted_set` |
| Runtime member | `RUNTIME_ADAPTER` |
| Runtime adapter path | `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` |
| Authority mode | `ACCEPTED_CURRENT_PATH` |
| Runtime consumer | Position Management Producer / Sell Planning |
| Registry path | `.runtime/artifact_registry/events/registry_events.jsonl` |
| Registry index | `.runtime/artifact_registry/index/registry_index.json` |
| Checkpoint | `.runtime/artifact_registry/checkpoints/latest.json` |
| Manifest path | `.runtime/artifact_registry/evidence/manifests/control_position_management_accepted_current_path_v11/artifact_set_manifest.json` |
| Acceptance report | `.runtime/artifact_registry/evidence/acceptance/control_position_management_accepted_current_path_v11/acceptance_report.json` |
| Evidence bundle | `.runtime/artifact_registry/evidence/bundles/control_position_management_accepted_current_path_v11/evidence_bundle.json` |
| Hash algorithm | ファイルbytesに対するSHA-256 |

## Accepted Generation

| 項目 | 値 |
|---|---|
| Accepted set before | `control.position_management.accepted_set@sha256-cec533ce8c03de7f` |
| Accepted event before | `event-1c801648-a4ba-49a8-bc7f-9694d9ce9f60-47609547f5d5838c` |
| Accepted adapter hash before | `ac2e7f6a3e9e184889551a8884a0e779ffb37292e8b26daf1e25e1610bba739c` |
| New accepted set | `control.position_management.accepted_set@sha256-25c992cee292cf7a` |
| New accepted event | `event-f7a4ed14-b7d2-477e-a045-407b18486510-1c8d1a8c33e55390` |
| New adapter hash | `a14658fbf5e2fd421512a82c13159408ed88b8c1d704e597ce9ecf1c0709e157` |

前のgenerationはappend-only Registry event log上で `LEGACY` として保持されている。将来の正式Acceptanceまたはrollback eventによりrollback可能である。Registry、checkpoint、accepted manifestの手編集は行っていない。

## Member Hash Attribution

Detailed machine-readable attribution:

```text
reports/phase21_c_position_management_artifact_authority_refresh/member_hash_attribution.json
```

要約:

| Artifact member | Changed by Phase21-B | Expected mismatch | Action |
|---|---:|---:|---|
| `BEHAVIOR_CONTRACT` | no | no | none |
| `CODE_POLICY` | no | no | none |
| `CONSUMER_COMPATIBILITY` | no | no | none |
| `FEATURE_VERSION` | no | no | none |
| `POLICY_VERSION` | no | no | none |
| `REGRESSION_EVIDENCE` | no | no | none |
| `RUNTIME_ADAPTER` | yes | yes | formal acceptance refresh |

直接原因:

```text
Phase21-B changed producer.py so PM ADD decisions are retained as Planning candidates.
```

This is a Production common Runtime Adapter source change, so the correct action was to create a replacement accepted artifact set, not to bypass hash validation.

## Formal Lifecycle

実行:

```bash
PYTHONPATH=src python3 scripts/phase21_c_pm_runtime_adapter_acceptance_refresh.py
```

The wrapper reuses the existing formal PM Runtime Adapter Acceptance writer and sets Phase21-C evidence output, evidence id, previous accepted hash, and Phase21-B regression gates.

Lifecycle result:

- DRAFT event created or reused
- VALIDATED event created
- previous ACCEPTED event marked LEGACY
- new ACCEPTED event appended
- Registry full log validation PASS
- Registry index build PASS
- checkpoint PASS
- Runtime resolver PASS
- Runtime adapter authority hash PASS
- mismatch fail-closed test PASS

## Validation Results

Formal writer summary:

```text
reports/phase21_c_position_management_artifact_authority_refresh/formal_writer_summary.json
```

Post validation:

```text
Registry full log: PASS
Registry index: PASS
Registry checkpoint: PASS
Runtime lookup: PASS
PM Runtime Adapter authority: PASS
```

No strategy values, model, calibration, J-Quants features, PM thresholds, ranking, max positions, max exposure, target investment ratio, cash buffer, or position sizing policy values were changed.

## Regression Results

実行:

```text
tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py
tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py
tests/runtime_v2/test_phase20_v_pm_runtime_adapter_equivalence.py
tests/runtime_v2/test_phase17_ah_pm_adapter_registry_identity_guard.py
tests/runtime_v2/test_phase15ap_position_management_input_contract.py
tests/runtime_v2/test_phase16av_registry_consumer_cutover.py
tests/artifact_registry/test_phase16ac_full_event_log_validator.py
tests/artifact_registry/test_phase16ad_materialized_index_builder.py
tests/artifact_registry/test_phase16ag_checkpoint_writer.py
tests/artifact_registry/test_phase16au_registry_resolver.py
```

結果:

```text
109 passed
```

## Process Gap

Phase21-B unit and targeted regression tests did not pass through the accepted Registry authority path. Therefore the `RUNTIME_ADAPTER` accepted current-path source hash was stale after the Production common `producer.py` change.

Confirmed gaps:

- Phase21-B acceptance criteria did not explicitly require PM Runtime Adapter Artifact refresh.
- Unit tests verified behavior but not accepted artifact authority.
- CI / targeted regression did not include stale accepted member detection after Production common PM source changes.

Remediation:

- Added Phase21-C wrapper for formal PM adapter refresh.
- Added Phase21-B regression gates into the acceptance wrapper.
- Updated `docs/02_architecture/artifact_acceptance_contract.md` to state accepted current-path Runtime adapter source changes require formal refresh.

## Prohibited Operations Confirmation

未使用:

```text
hash check bypass
accepted artifact direct edit
registry entry direct edit
checkpoint direct edit
historical-only authority branch
strategy value change
model training
calibration change
long Historical Run
```

## User-run 5BD Command

Codexはこのコマンドを実行していない。

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --business-days 5 \
  --start-date 2022-09-01 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

## 5BD Acceptance Checks

- `status = PASS`
- `final_judgment = PASS`
- `completed_days = 5営業日`
- Position Management artifact HALTなし
- artifact member hash mismatchなし
- BUY Pending preservation成立
- Composite Pending成立
- ADD-derived BUY lineageあり
- Submit canonical authority維持
- duplicate order 0
- Lifecycle consistency PASS
- findings 0

## Phase21-B Runtime Re-Acceptance Status

```text
PHASE21_B_RUNTIME_RE_ACCEPTED_READY_FOR_USER_5BD
```

## Strategy Design Return Status

```text
PHASE21_READY_TO_RETURN_TO_STRATEGY_ARCHITECTURE_DESIGN_AFTER_USER_5BD_ACCEPTANCE
```
