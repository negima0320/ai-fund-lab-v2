# AI Fund Lab vNext Phase4-L Full-range Feature Dry-run Design

---

# 1. このレポートの目的

Phase4-Lは、Candidate AI本体・学習・推論に進む前に、full-range feature dry-run の設計を固定する段階である。

Phase4-Lでは設計と監査のみを行う。full-range feature generation本体、label生成、dataset builder、Candidate AI本体、学習、推論、backtest、売買、Paper Trading、Broker実API、発注、Portfolio自動更新は実装しない。

---

# 2. 読んだドキュメント/コード

```text
docs/phase_reports/phase4j_real_feature_prepared_dry_run.md
docs/phase_reports/phase4k_normalized_history_readiness.md
reports/phase_reports/phase4k_normalized_history_readiness_audit.json
reports/candidate_ai/phase4k_mock_normalized_history_manifest.json
src/ai_fund_lab_v2/candidate_ai/
scripts/build_candidate_features_real_prepared_dry_run.py
docs/03_ai_design/candidate_feature_builder_design.md
docs/03_ai_design/candidate_training_data_design.md
```

---

# 3. Phase4の責務境界

Phase4 Candidate AI vNext の目的:

```text
上昇候補抽出
4000銘柄 -> 50銘柄程度
```

Candidate AIがやること:

```text
全銘柄から見る価値がある上昇候補を抽出する
candidate_scoreを出す
candidate_reasonを出す
excluded_reasonを出す
```

Candidate AIがやらないこと:

```text
買い判断
売却判断
期待値判断
購入金額判断
保有判断
資金配分
Paper Trading
発注
売買
Portfolio更新
```

---

# 4. Phase4-Kからの前提

Phase4-Kの状態:

```text
data_source_type = mock
daily_quotes_normalized storage = .runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet
date_min = 2026-03-02
date_max = 2026-06-01
business_day_count = 66
code_count = 30
row_count = 1980
prepared readiness_status = READY_FOR_FULL_RANGE_FEATURE_DRY_RUN
eligible_count = 30
schema validation = OK
leakage audit = OK
```

重要な解釈:

```text
Phase4-Kはmock normalized historyでREADYを確認した。
したがってPhase4-L設計では mock normalized history と real_runtime normalized history を明確に分離する。
J-Quants API由来 normalized history は将来の入力種別として扱うが、Phase4-Lでは実APIを使わない。
```

---

# 5. Full-range Feature Generation Scope

full-range feature dry-run の対象は、Candidate Feature Builderが扱うfeature table生成である。

対象:

```text
daily_quotes_normalized を中心にした価格・出来高・流動性・trend feature
as_of_date時点で観測可能な情報のみ
universe_eligible / excluded_reason
feature_version
source_snapshot_id
data_source_type
manifest
audit
summary
```

対象外:

```text
label生成
training dataset作成
Candidate AI学習
Candidate AI推論
backtest
売買判断
発注
Portfolio更新
```

---

# 6. 対象期間設計

対象期間は `daily_quotes_normalized` の分布から決める。

ルール:

```text
date_min は normalized history 内の最小営業日
date_max は normalized history 内の最大営業日
as_of_date は trading calendar 上の営業日
各as_of_dateは lookback_business_days 以上の履歴を持つ場合だけfeature生成対象
最初のlookback不足期間は skipped または excluded_reason=insufficient_history として扱う
```

Phase4-L時点の推奨:

```text
lookback_business_days = 60
first_generatable_as_of_date = 60営業日分の履歴が揃う最初の日
date chunk は月単位を第一候補とする
```

---

# 7. Universe設計

universeは、各as_of_date時点で観測可能な銘柄のみで作る。

Phase4-Lのdry-run設計では以下を採用する。

```text
primary universe source = daily_quotes_normalized に存在する code
future extension = listed issue master による上場/市場/監理/整理銘柄filter
```

除外方針:

```text
履歴不足 -> excluded_reason=insufficient_history
価格・出来高欠損 -> excluded_reason=missing_price_or_volume
流動性不足 -> excluded_reason=low_liquidity
上場状態不明 -> excluded_reason=unknown_listing_status
```

Candidate AIの責務上、universeは「見る価値がある候補抽出」のための入力であり、買い判断や期待値ランキングではない。

---

# 8. Chunking Strategy

全期間・全銘柄を一括処理しない。

推奨chunk:

```text
primary chunk = month chunk
secondary split = code chunk
```

chunk粒度:

```text
date_start
date_end
code_start
code_end
max_codes_per_chunk
max_rows_per_chunk
```

各chunkが保持するmetadata:

```text
chunk_id
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
data_source_type
feature_version
schema_version
source_snapshot_id
status
error_message
```

chunk_id例:

```text
candidate_features_full_range__2026-03__codes_000001_000500__v1
```

---

# 9. Resume / Restart Strategy

中断・再実行に耐える設計にする。

ルール:

```text
既存chunk検出を行う
成功済みchunkはskipする
失敗chunkは再実行対象にする
manifest整合性を確認する
partial outputはfinal outputと分離する
tmp -> final atomic moveを使う
```

保存の流れ:

```text
1. chunk planを作る
2. chunk status manifestを読む
3. status=SUCCESS かつ output/audit/manifest checksum一致ならskip
4. status=FAILED または checksum不一致なら再実行
5. 一時出力を .runtime/candidate_ai/tmp/full_range/ に保存
6. schema/leakage audit OK後に final pathへatomic move
7. chunk manifestへ SUCCESS/FAILED/SKIPPED を追記
```

自動復旧ではなく、feature生成dry-runの再開制御である。

---

# 10. Storage Format

出力先設計:

```text
.runtime/candidate_ai/features/full_range/
.runtime/candidate_ai/manifests/full_range/
.runtime/candidate_ai/audit/full_range/
.runtime/candidate_ai/tmp/full_range/
reports/candidate_ai/full_range/
```

保存形式:

```text
feature rows = parquet preferred
feature rows = jsonl optional
json summary required
chunk manifest = json
chunk audit = json
run summary = json required
human report = markdown optional
```

Phase4-Lでは設計のみで、full-range feature rowsの実保存は行わない。

---

# 11. Manifest Strategy

run manifest:

```text
run_id
created_at
phase
feature_version
schema_version
data_source_type
input_storage_path
input_storage_format
input_date_min
input_date_max
input_code_count
input_row_count
chunk_count
successful_chunk_count
failed_chunk_count
skipped_chunk_count
summary_path
```

chunk manifest:

```text
chunk_id
run_id
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
checksum
status
created_at
finished_at
```

---

# 12. Audit Strategy

各chunkで必ず監査する。

```text
future系feature混入なし
backtest/trade/portfolio/order/cash混入なし
as_of_dateより未来データ使用なし
required feature columns存在
eligible_count > 0 または excluded_reason coverageあり
excluded_reason coverage
candidate_reason生成準備
feature_version固定
source_snapshot_id記録
data_source_type記録
```

run全体で監査する。

```text
chunk manifestの欠損なし
成功chunkと出力ファイルの対応
schema_version統一
feature_version統一
data_source_type統一または明示的な混在記録
FAILED chunkがある場合はREADYにしない
```

---

# 13. Performance Guard

full-range dry-runでは性能ガードを必須にする。

```text
max_codes_per_chunk
max_dates_per_chunk
max_rows_per_chunk
max_runtime_seconds_per_chunk
max_output_file_size_mb
progress logging
```

Phase4-M実装時の初期値案:

```text
max_dates_per_chunk = 1ヶ月
max_codes_per_chunk = 500
max_rows_per_chunk = 500 * 80
```

---

# 14. Memory Guard

メモリガード:

```text
全期間・全銘柄を一括でmaterializeしない
chunk単位で読み込み・変換・書き込みを行う
必要なlookback windowだけを読み込む
chunk完了後に中間rowsを破棄する
large summaryには集計値のみを保持する
```

dry-run実装では、chunkごとに `input_row_count` と `memory_guard_estimated_rows` をmanifestへ残す。

---

# 15. Data Source Type Handling

Phase4-Lでは以下を明確に分ける。

```text
mock normalized history:
  Phase4-Kで生成したmock。full-range設計確認には使えるが、学習品質評価には使わない。

real_runtime normalized history:
  runtime内に保存済みのnormalized data。由来が不明な場合はmanifestで確認する。

J-Quants API由来 normalized history:
  将来の実データ。Phase4-Lでは実API取得しない。

skipped:
  normalized dataがない、または読み取り不可。
```

data_source_typeはrun manifest、chunk manifest、audit、summaryへ必ず記録する。

---

# 16. Feature Version Strategy

feature_versionはfull-range run全体で固定する。

初期案:

```text
feature_version = candidate_features_full_range_dry_run_v1
feature_set_name = candidate_feature_builder_mock
schema_version = candidate_feature_table_v1
```

feature定義を変更した場合:

```text
feature_versionを上げる
旧version出力と混在させない
manifestにfeature_versionを必ず記録する
```

---

# 17. Schema Version Strategy

schema_versionはCandidate Feature Schema Contractと対応させる。

必須列:

```text
as_of_date
target_date
code
feature_version
source_snapshot_id
feature_set_name
created_at
data_start_date
data_end_date
universe_eligible
excluded_reason
```

schema変更時:

```text
schema_versionを上げる
audit scriptでrequired columnsを再確認する
既存chunkとの混在をmanifestで禁止する
```

---

# 18. Leakage Audit強化

chunk auditで禁止列・禁止語を確認する。

禁止:

```text
future_return_*
future_max_return_*
future_max_drawdown_*
top_decile_*
downside_bad_*
backtest result
trade result
selected
bought
sold
cash
portfolio
annual_return
final_assets
paper_trade
position
allocation
order
execution
profit
loss
pnl
```

未来データ監査:

```text
各feature rowのdata_end_date <= as_of_date
source rowsのDate <= as_of_date
財務情報はdisclosed_date <= as_of_date
label tableを読まない
```

---

# 19. Candidate Dataset前のReadiness条件

full-range feature dry-runが次へ進める条件:

```text
all chunks status = SUCCESS または明示的SKIPPED
failed_chunk_count = 0
eligible_count total > 0
excluded_reason coverage >= 99%
schema_validation_status = OK
leakage_audit_status = OK
feature_version fixed
schema_version fixed
source_snapshot_id present
data_source_type present
run summary json exists
chunk manifests complete
```

mock dataの場合:

```text
Candidate dataset builderには進まない
実データ品質評価には使わない
full-range dry-runの制御設計確認に限定する
```

---

# 20. Phase4-Lでやらないこと

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

# 21. Phase4-Mへの引き継ぎ

Phase4-M案:

```text
Full-range Feature Dry-run Skeleton
```

実装する場合の候補:

```text
chunk plan builder
chunk manifest model
resume/restart checker
full_range output path resolver
dry-run only CLI
mock/real_runtime source type validation
no-write plan mode
```

Phase4-Mでも、label生成・学習・推論・売買系には進まない。
