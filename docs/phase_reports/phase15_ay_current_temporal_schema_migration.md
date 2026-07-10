# Phase15-AY Current Temporal Schema Migration Implementation

作成日: 2026-07-11

## 目的

Phase15-AYでは、Runtime-owned Currentを単一の曖昧な `as_of` から、Position State / Valuation State / Execution-Reconcile Stateを分離したTemporal Schemaへ安全に移行するための読み書き契約とmigration基盤を実装した。

このPhaseでは実Runtime Currentへのmigration apply、Current valuation refresh、Broker API、Safety実運用、Morning、Submit、Executionは行っていない。

## Source / Target Schema

Legacy source:

```text
schema_version=1
as_of
updated_at
positions
cash
buying_power
market_value
```

Target:

```text
temporal_schema_version=runtime_v2_current_temporal_v1
schema_version=runtime_v2_current_temporal_v1
position_state_as_of
valuation_as_of
source_market_date
last_execution_date
last_reconciled_at
updated_at
temporal_status
position_state_source
valuation_source
valuation_generated_at
no_fill
legacy_as_of_used
legacy_migration_status
production_equivalent
current_position_status
current_valuation_status
```

## 実装

追加:

- `src/ai_fund_lab_v2/runtime_v2/current_state/temporal.py`
- `tests/runtime_v2/test_phase15ay_current_temporal_schema_migration.py`

更新:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`

## Reader / Writer Contract

Reader:

```text
read_current_temporal()
build_current_temporal_candidate()
```

Legacy `as_of` を読める。ただし、派生した場合は以下を必ず出す。

```text
legacy_as_of_used=true
legacy_migration_status=LEGACY_DERIVED
derived_position_state_as_of
derived_valuation_as_of
production_equivalent=false
review_required=true
```

Writer:

```text
write_current_temporal_state()
```

以下を呼出元が明示しない場合は書かない。

```text
position_state_as_of
valuation_as_of
source_market_date
last_execution_date
last_reconciled_at
updated_at
```

Writerは現在日付を勝手に補完しない。

## Migration Model

定義:

```text
CurrentTemporalMetadata
CurrentMigrationResult
CurrentTemporalState
```

`CurrentTemporalState` はPhase15-AV Temporal Foundationのmodelを利用している。

## Evidence Priority

Temporal fieldの根拠priority:

1. Runtime-owned execution ledger
2. Current existing explicit temporal fields
3. accepted Market Evidence
4. legacy `as_of`

Broker-only snapshotはPosition State根拠にしない。

## Migration Rules

Positionあり:

- Runtime-owned execution ledgerがあれば `position_state_as_of` と `last_execution_date` に使う。
- execution根拠がなければlegacy `as_of` 派生として `REVIEW_REQUIRED`。

Valuation:

- Market Evidenceがあれば `valuation_as_of` / `source_market_date` に使う。
- Market Evidenceがなければlegacy `as_of` 派生として `REVIEW_REQUIRED`。

Positionなし:

- 明示的empty Currentとして読める。
- legacy派生ならProduction equivalentとはしない。

No-fill:

```text
position_state_as_of != business_date
valuation_as_of == business_date
```

を正常に表現できる。quantity / average_price / ownership / last_execution_dateはvaluation-onlyでは変更しない。

## CLI Job

追加:

```text
--job current_temporal_migration
```

default:

```text
dry-run / review-only
```

applyには明示optionが必要。

```text
--apply-current-migration
```

Phase15-AYでは実Runtimeにapplyしていない。Regressionのapply確認はtmp Runtime rootのみで実施した。

## Migration Artifact

生成:

```text
.runtime/runtime_state/current_migration/<business_date>/current_temporal_migration.json
```

最低限含む:

```text
business_date
generated_at
source_current_path
source_schema_version
target_schema_version
migration_status
apply_requested
apply_executed
legacy_as_of_used
derived_fields
missing_evidence
warnings
review_required
backup_path
candidate_current
next_operator_action
```

## Atomic Write / Backup

Apply時の契約:

```text
validation
↓
history / backup保存
↓
atomic temp write
↓
replace
↓
post-write validation
```

Backup path:

```text
.runtime/persistent_ledger/history/current/<timestamp>.json
```

既存Currentを無言上書きしない。

## Temporal Foundation Integration

利用:

- `CurrentTemporalState`
- `FreshnessStatus`
- `evaluate_current_position_freshness()`
- `evaluate_current_valuation_freshness()`

独自Temporal statusは追加していない。

## Data Readiness / Report / Notification Compatibility

Migration manifestは以下を出す。

```text
current_position_status
current_valuation_status
position_state_as_of
valuation_as_of
source_market_date
```

Report / Notification payloadには要約のみ追加した。

```text
current_temporal_migration_status
current_temporal_migration_reason
```

Notification real sendは行っていない。

## Regression

AY:

```text
python3 -m pytest tests/runtime_v2/test_phase15ay_current_temporal_schema_migration.py
```

Result:

```text
13 passed
```

Retention:

```text
python3 -m pytest tests/runtime_v2/test_phase15ay_current_temporal_schema_migration.py tests/runtime_v2/test_phase15av_runtime_temporal_contract_foundation.py tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py tests/runtime_v2/test_phase15ap_position_management_input_contract.py tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py
```

Result:

```text
63 passed
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase15ay python3 -m compileall src/ai_fund_lab_v2/runtime_v2/current_state/temporal.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py tests/runtime_v2/test_phase15ay_current_temporal_schema_migration.py
```

Result:

```text
passed
```

## 実Runtime未変更確認

Phase15-AYでは実Runtime Currentにapplyしていない。

確認:

```text
git status --short .runtime/persistent_ledger/state.json
```

Result:

```text
no output
```

## 非実施事項

以下は行っていない。

- 実Runtime Current migration apply
- Current直接編集
- Current valuation refresh運用
- Broker positionsのCurrent取り込み
- Market Refresh実運用
- Broker API接続
- Safety実運用
- Morning
- SELL Planning
- Submit
- Execution実運用
- Broker Write
- 注文
- Notification real send
- launchd変更
- 日付だけの書換え

## 最終判定

```text
PHASE15AY_CURRENT_TEMPORAL_SCHEMA_MIGRATION_COMPLETE
```
