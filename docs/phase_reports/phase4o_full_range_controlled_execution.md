# AI Fund Lab vNext Phase4-O Full-range Feature Dry-run Controlled Execution

---

# 1. このレポートの目的

Phase4-Oは、full-range feature generation本番の前に、最小chunkだけで安全なfeature output書き込み、tmp -> final atomic move、chunk manifest、run manifest更新を確認する段階である。

今回も以下には進まない。

```text
全chunk feature generation
全期間feature generation
label生成
dataset builder
Candidate AI本体
学習
推論
backtest
売買
Paper Trading
Broker実API
発注
Portfolio自動更新
```

---

# 2. 読んだドキュメント/コード

```text
docs/phase_reports/phase4l_full_range_feature_dry_run_design.md
docs/phase_reports/phase4m_full_range_feature_dry_run_skeleton.md
docs/phase_reports/phase4n_full_range_no_write_gate.md
reports/phase_reports/phase4m_full_range_feature_dry_run_skeleton_audit.json
reports/phase_reports/phase4n_full_range_no_write_gate_audit.json
reports/candidate_ai/full_range/phase4m_full_range_dry_run_summary.json
reports/candidate_ai/full_range/phase4n_full_range_no_write_summary.json
src/ai_fund_lab_v2/candidate_ai/full_range.py
src/ai_fund_lab_v2/candidate_ai/feature_builder.py
src/ai_fund_lab_v2/candidate_ai/validation.py
src/ai_fund_lab_v2/candidate_ai/leakage_audit.py
```

---

# 3. Controlled Execution範囲

Phase4-Oの実行範囲:

```text
max_chunks_to_execute = 1
max_codes_per_chunk <= 30
date chunk = 1 chunkのみ
data_source_type = mock または existing runtime
```

全chunk・全期間処理は禁止する。

---

# 4. 実装内容

追加した処理:

```text
execute_full_range_chunk_controlled()
promote_tmp_to_final()
build_full_range_controlled_summary()
scripts/build_candidate_features_full_range_controlled.py
```

処理順:

```text
1. Phase4-N no-write gateを確認
2. chunk planを生成
3. 最小chunkを1つ選ぶ
4. chunk入力を読む
5. feature builderを実行
6. schema validationを実行
7. leakage auditを実行
8. tmpへfeature outputを書く
9. audit JSONを書く
10. validation/audit OKなら tmp -> final atomic move
11. chunk manifest SUCCESS/FAILEDを書く
12. run manifestを更新
13. summary JSONを書く
```

---

# 5. 出力先

summary:

```text
reports/candidate_ai/full_range/phase4o_full_range_controlled_summary.json
```

feature output:

```text
.runtime/candidate_ai/features/full_range/{run_id}/{chunk_id}.json
```

tmp output:

```text
.runtime/candidate_ai/tmp/full_range/{run_id}/{chunk_id}.tmp.json
```

chunk manifest:

```text
.runtime/candidate_ai/manifests/full_range/{run_id}_{chunk_id}_manifest.json
```

chunk audit:

```text
.runtime/candidate_ai/audit/full_range/{run_id}_{chunk_id}_audit.json
```

run manifest:

```text
.runtime/candidate_ai/manifests/full_range/{run_id}_run_manifest.json
```

---

# 6. Atomic Move方針

ルール:

```text
feature rowsはまずtmpへ書く
schema validation OKかつleakage audit OKの場合だけfinalへ移動する
失敗時はfinalを書かない
失敗時はchunk manifestをFAILEDにする
```

Phase4-Oの成功時:

```text
tmp_to_final_atomic_move = true
tmp output path is moved away
final output exists
```

---

# 7. Chunk Manifest結果

SUCCESS時の必須項目:

```text
status = SUCCESS
row_count
eligible_count
excluded_count
schema_validation_status = OK
leakage_audit_status = OK
output_path
audit_path
```

FAILED時の方針:

```text
status = FAILED
error_message
final outputなし
tmp output隔離
```

---

# 8. Run Manifest更新

run manifestに以下を反映する。

```text
completed_chunk_count
failed_chunk_count
skipped_chunk_count
readiness_status
last_updated_at
```

Phase4-O controlled executionでは、成功時に以下となる。

```text
completed_chunk_count = 1
failed_chunk_count = 0
skipped_chunk_count = total_chunk_count - 1
readiness_status = CONTROLLED_EXECUTION_DONE
```

---

# 9. 実行結果

Phase4-K mock runtimeでのcontrolled execution結果:

```text
status = OK
controlled_status = CONTROLLED_EXECUTION_COMPLETED
executed_chunk_count = 1
max_chunks_to_execute = 1
schema_validation_status = OK
leakage_audit_status = OK
row_count = 30
eligible_count = 30
excluded_count = 0
feature_output_written = true
tmp_to_final_atomic_move = true
```

---

# 10. 禁止事項遵守

Phase4-Oでは以下を実装しない。

```text
全chunk feature generation
全期間feature generation
label生成
dataset builder
Candidate AI本体
学習
推論
backtest
Historical Evaluation
Opportunity AI
Position Management AI
Capital Allocation
Paper Trading
Order Manager
Broker実API接続
発注
売買
Portfolio自動更新
秘密情報の保存・出力
```

---

# 11. Phase4-Pへの引き継ぎ

Phase4-P案:

```text
Controlled Execution Failure / Resume Audit
```

候補:

```text
validation失敗chunkでfinalを書かないことのfixture確認
既存SUCCESS manifestによるskip動作
FAILED manifestによるrerun候補化
複数chunkへ広げる前のresume安全性監査
```
