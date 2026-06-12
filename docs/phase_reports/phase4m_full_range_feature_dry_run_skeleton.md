# AI Fund Lab vNext Phase4-M Full-range Feature Dry-run Skeleton

---

# 1. このレポートの目的

Phase4-Mは、Phase4-L設計に従い、full-range feature generation本体に進む前のskeletonを実装する段階である。

実装対象は以下に限定する。

```text
chunk plan builder
chunk manifest model
run manifest model
resume/restart checker
full_range path resolver
dry-run only CLI
phase audit
pytest
```

---

# 2. 読んだドキュメント/コード

```text
docs/phase_reports/phase4l_full_range_feature_dry_run_design.md
docs/phase_reports/phase4l_full_range_feature_dry_run_design_audit.md
reports/phase_reports/phase4l_full_range_feature_dry_run_design_audit.json
docs/phase_reports/phase4k_normalized_history_readiness.md
reports/phase_reports/phase4k_normalized_history_readiness_audit.json
src/ai_fund_lab_v2/candidate_ai/
scripts/build_candidate_features_real_prepared_dry_run.py
scripts/audit_phase4j_real_feature_prepared_dry_run.py
```

---

# 3. 作成したskeleton

```text
src/ai_fund_lab_v2/candidate_ai/full_range.py
scripts/build_candidate_features_full_range_dry_run.py
scripts/audit_phase4m_full_range_feature_dry_run_skeleton.py
```

Phase4-Mではfeature rowsを生成しない。

---

# 4. Chunk Plan Builder仕様

`build_full_range_chunk_plan()` は、normalized recordsから月単位date chunk + code chunkを作る。

chunk plan項目:

```text
run_id
chunk_id
date_start
date_end
code_start
code_end
codes
code_count
expected_input_rows_optional
status
data_source_type
feature_version
schema_version
```

statusは `PLANNED` のみであり、feature生成は実行しない。

---

# 5. Full-range Path Resolver

`resolve_full_range_paths()` は以下を返す。

```text
.runtime/candidate_ai/features/full_range/
.runtime/candidate_ai/manifests/full_range/
.runtime/candidate_ai/audit/full_range/
.runtime/candidate_ai/tmp/full_range/
reports/candidate_ai/full_range/
```

---

# 6. Run / Chunk Manifest仕様

run manifest:

```text
run_id
created_at
data_source_type
feature_version
schema_version
date_min
date_max
code_count
chunk_count
completed_chunk_count
failed_chunk_count
skipped_chunk_count
readiness_status
```

chunk manifest model:

```text
run_id
chunk_id
status
date_start
date_end
code_count
row_count
eligible_count
excluded_count
schema_validation_status
leakage_audit_status
output_path
manifest_path
audit_path
error_message
```

Phase4-Mではchunk manifest modelを定義し、dry-run CLIではchunk plan JSONを出力する。

---

# 7. Resume / Restart Checker仕様

`check_resume_restart()` は以下を判定する。

```text
existing chunk manifest
completed chunk -> skip候補
failed chunk -> rerun候補
missing chunk -> run候補
partial tmp output
manifest inconsistency
```

実rerunはしない。

---

# 8. Dry-run Only CLI

CLI:

```bash
python3 scripts/build_candidate_features_full_range_dry_run.py
```

実行内容:

```text
normalized data discovery
date/code分布取得
chunk plan生成
run manifest生成
resume/restart summary生成
summary JSON出力
```

出力:

```text
reports/candidate_ai/full_range/phase4m_full_range_dry_run_summary.json
.runtime/candidate_ai/manifests/full_range/{run_id}_run_manifest.json
.runtime/candidate_ai/manifests/full_range/{run_id}_chunk_plan.json
```

normalized dataがない場合は `SKIPPED` で安全終了する。

---

# 9. Dry-run CLI結果

Phase4-K mock normalized historyが存在する場合の例:

```text
status = OK
mode = dry_run_only
feature_generation_executed = false
data_source_type = mock
chunk_count = 4
```

---

# 10. 禁止事項遵守

Phase4-Mでは以下を実装しない。

```text
full-range feature generation本体
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

# 11. Phase4-Nへの引き継ぎ

Phase4-N案:

```text
Full-range Feature Dry-run Plan Audit / No-write Execution
```

候補:

```text
chunk planの対象期間・銘柄分布レビュー
resume/restart判定の異常系fixture追加
chunkごとのno-write validation
full-range feature generation本体前のfinal gate
```
