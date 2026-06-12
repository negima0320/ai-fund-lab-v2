# AI Fund Lab vNext Phase4-N Full-range Feature Dry-run Plan Audit / No-write Execution

---

# 1. このレポートの目的

Phase4-Nは、full-range feature generation本体に進む前の最終ゲートをno-writeで確認する段階である。

実装対象は以下に限定する。

```text
chunk plan distribution audit
no-write chunk validation
resume/restart abnormal case tests
final gate before full-range execution
summary/audit/report output
pytest
```

---

# 2. 読んだドキュメント/コード

```text
docs/phase_reports/phase4l_full_range_feature_dry_run_design.md
docs/phase_reports/phase4m_full_range_feature_dry_run_skeleton.md
reports/phase_reports/phase4m_full_range_feature_dry_run_skeleton_audit.json
reports/candidate_ai/full_range/phase4m_full_range_dry_run_summary.json
src/ai_fund_lab_v2/candidate_ai/full_range.py
scripts/build_candidate_features_full_range_dry_run.py
```

---

# 3. Phase4責務境界

Phase4 Candidate AI vNext の目的:

```text
上昇候補抽出
4000銘柄 -> 50銘柄程度
```

Phase4-Nでは、買い判断、売却判断、資金配分、Paper Trading、発注、Portfolio更新は実装しない。

---

# 4. Chunk Plan Distribution Audit

`audit_chunk_plan_distribution()` を追加した。

確認項目:

```text
chunk_count
date_chunk_count
code_chunk_count
date_start/date_end coverage
code_count distribution
expected row distribution
empty chunk detection
overlap detection
gap detection
duplicate chunk_id detection
data_source_type consistency
feature_version consistency
schema_version consistency
```

Phase4-K mock runtimeでの結果:

```text
chunk_count = 4
date_chunk_count = 4
code_chunk_count = 1
empty_chunk_ids = []
overlap_count = 0
gap_count = 0
duplicate_chunk_id_count = 0
data_source_type_consistent = true
feature_version_consistent = true
schema_version_consistent = true
```

---

# 5. No-write Chunk Validation

`validate_chunks_no_write()` を追加した。

確認項目:

```text
input rows can be selected
as_of_date/date range is valid
code list is non-empty
lookback requirement is checkable
schema validation can be invoked in no-write mode
leakage audit can be invoked in no-write mode
output paths can be resolved
tmp/final paths are separated
```

重要:

```text
feature outputは書かない
chunk feature生成はしない
```

Phase4-K mock runtimeでの結果:

```text
status = OK
checked_chunk_count = 4
chunks_with_input_rows = 4
chunks_with_empty_inputs = 0
schema_validation_status = OK
leakage_audit_status = OK
feature_output_written = false
```

---

# 6. Resume / Restart Abnormal Case

Phase4-Nでは `check_resume_restart()` の異常系確認を強化した。

確認対象:

```text
completed chunk exists -> skip candidate
failed chunk exists -> rerun candidate
missing chunk -> run candidate
partial tmp output exists -> warning
manifest path points to missing output -> inconsistency
duplicate chunk manifest -> inconsistency
unknown status -> inconsistency
```

実rerunはしない。

---

# 7. Final Gate

`evaluate_no_write_final_gate()` を追加した。

gate status:

```text
READY_FOR_FULL_RANGE_EXECUTION
BLOCKED_BY_CHUNK_PLAN
BLOCKED_BY_RESUME_STATE
BLOCKED_BY_NO_WRITE_VALIDATION
BLOCKED_BY_SCHEMA
BLOCKED_BY_LEAKAGE
SKIPPED_NO_DATA
```

READY条件:

```text
chunk plan has no gaps/overlaps/duplicates
chunk count > 0
no empty chunks unless explicitly skipped
resume/restart state consistent
no-write validation OK
schema/leakage no-write checks OK
data_source_type recorded
feature_version/schema_version fixed
```

Phase4-K mock runtimeでの判定:

```text
gate_status = READY_FOR_FULL_RANGE_EXECUTION
```

---

# 8. No-write CLI

CLI:

```bash
python3 scripts/check_candidate_features_full_range_no_write.py
```

実行内容:

```text
Phase4-M chunk plan生成
chunk plan distribution audit
no-write chunk validation
resume/restart check
final gate判定
summary JSON出力
```

出力先:

```text
reports/candidate_ai/full_range/phase4n_full_range_no_write_summary.json
```

---

# 9. 禁止事項遵守

Phase4-Nでは以下を実装しない。

```text
full-range feature generation本体
feature output chunk書き込み
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

# 10. Phase4-Oへの引き継ぎ

Phase4-O案:

```text
Full-range Feature Dry-run Controlled Execution
```

候補:

```text
no-write gate READYを前提に、最小chunkだけfeature rowsを書き出すcontrolled execution
tmp -> final atomic moveの実装
chunk manifest SUCCESS/FAILED実記録
feature output監査の実データ適用
```

Phase4-Oでも、label生成、学習、推論、売買系には進まない。
