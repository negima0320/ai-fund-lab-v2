# AI Fund Lab vNext Phase4-F Candidate Real Data Loader Contract / Adapter Design Report

---

# 1. このレポートの目的

本レポートは、Phase4-F Candidate Real Data Loader Contract / Adapter Design の完了条件を確認する。

Phase4-Fの目的は、Phase1 Data Foundation の `daily_quotes_normalized` を Candidate Feature Builder の標準入力へ安全に差し替えるための loader contract / adapter / audit を固定することである。

Phase4-Fでは実データ全量feature生成は実装しない。

---

# 2. 読んだ資料

```text
docs/00_vision/investment_philosophy.md
docs/01_requirements/system_requirements.md
docs/01_requirements/success_metrics.md
docs/01_requirements/phase_roadmap.md
docs/02_architecture/system_architecture.md
docs/03_ai_design/candidate_ai_design.md
docs/03_ai_design/candidate_feature_catalog.md
docs/03_ai_design/candidate_training_data_design.md
docs/03_ai_design/candidate_feature_builder_design.md
docs/phase_reports/phase4a_candidate_ai_design.md
docs/phase_reports/phase4b_candidate_training_data_design.md
docs/phase_reports/phase4c_candidate_feature_builder_design.md
docs/phase_reports/phase4d_candidate_feature_builder_skeleton.md
docs/phase_reports/phase4e_candidate_feature_builder_mock.md
reports/phase_reports/phase4a_candidate_ai_design_audit.json
reports/phase_reports/phase4b_candidate_training_data_design_audit.json
reports/phase_reports/phase4c_candidate_feature_builder_design_audit.json
reports/phase_reports/phase4d_candidate_feature_builder_skeleton_audit.json
reports/phase_reports/phase4e_candidate_feature_builder_mock_audit.json
```

---

# 3. Phase4-F実装内容の要約

作成した要素:

```text
data_loader.py:
  daily_quotes_normalized adapter contract
  input schema validation
  as_of_date future row filtering
  source_snapshot_id / input hash rule

loader_manifest.py:
  loader manifest schema
  loader audit / manifest / rows dry-run output

scripts/check_candidate_real_data_loader_contract.py:
  small fixture based contract dry-run

scripts/audit_phase4f_candidate_real_data_loader_contract.py:
  Phase4-F completion audit
```

---

# 4. daily_quotes_normalized schema mapping

Phase1 normalized raw schema v2 の実列名を Candidate Feature Builder 標準入力へ変換する。

```text
Date -> date
Code -> code
Open -> open
High -> high
Low -> low
Close -> close
Volume -> volume
```

Candidate Feature Builder側の標準入力列:

```text
date
code
open
high
low
close
volume
```

Phase1側の `PriceSource` / `SchemaVersion` / `source_endpoint` / `target_date` / `business_key` は loader audit / manifest の追跡情報として扱い、Phase4-Fの feature builder 標準入力行には混ぜない。

---

# 5. loader contract

`adapt_daily_quotes_normalized()` は、`daily_quotes_normalized` record iterable を受け取り、Candidate Feature Builder 標準入力行へ変換する。

入力:

```text
records
as_of_date
lookback_rows
source_snapshot_id
input_source_path
input_manifest_path
input_hash_optional
```

出力:

```text
CandidateRealDataLoaderResult
  rows
  audit
```

`rows` は `build_candidate_features_mock()` に渡せる標準入力schemaである。

---

# 6. input schema validation

loaderは以下を検証する。

```text
Date が存在する
Code が存在する
Open が存在する
High が存在する
Low が存在する
Close が存在する
Volume が存在する
Date <= as_of_date の行だけを出力する
Code が空でない
Close が欠損していない
Volume が欠損していない
Open/High/Low/Close/Volume が数値として扱える
```

未来行はvalidation messageとauditに記録し、出力から除外する。

---

# 7. as_of_date window filtering

loaderは `as_of_date` より後の行を出力しない。

`date > as_of_date` の入力行は以下として記録する。

```text
dropped_future_row_count
```

`lookback_rows` はPhase4-F時点では per-code の行数上限である。Phase4-G以降で trading calendar と接続し、営業日windowへ厳密化する。

---

# 8. source_snapshot_id / manifest / hash rule

loader audit / manifest は以下を保持する。

```text
source_snapshot_id
input_source_path
input_manifest_path
input_row_count
filtered_row_count
dropped_future_row_count
input_hash_optional
schema_version
loader_version
```

`source_snapshot_id` が未指定の場合は以下の形式で生成する。

```text
daily_quotes_normalized:{as_of_date}:{input_hash_prefix}
```

`input_hash_optional` はsha256 hashであり、Phase4-Fでは軽量な証跡として扱う。将来、実data manifest hashやsnapshot hashへ差し替え可能にする。

---

# 9. trading calendar rule

lookbackは営業日ベースで扱う方針とする。

Phase4-Fでは本格calendar integrationは行わない。現時点の実装は `lookback_rows` による per-code 行数上限であり、営業日windowの厳密化はPhase4-G以降へ引き継ぐ。

方針:

```text
lookbackは営業日ベース
as_of_dateが非営業日の場合は直前営業日に正規化、または明確なエラーにする
target_dateは同日または次営業日相当
```

Phase4-Fでは、非営業日判定の自動正規化はまだ実装しない。

---

# 10. runtime path rule

contract checkの生成物はruntime dir配下に保存する。

```text
.runtime/candidate_ai/tmp/
.runtime/candidate_ai/manifests/
.runtime/candidate_ai/audit/
```

Phase4-Fの dry-run rows は `.runtime/candidate_ai/tmp/` に保存する。feature本番生成物として `.runtime/candidate_ai/features/` へ保存しない。

---

# 11. real data dry-run design

`scripts/check_candidate_real_data_loader_contract.py` は小さなfixtureを使ってcontractを検証する。

このscriptは以下を行う。

```text
small daily_quotes_normalized-like fixtureを作る
adapterに渡す
future rowを除外する
loader rows / manifest / audit をruntime配下へ保存する
summaryをstdoutへ出す
```

実データ全量読み込み、parquet/CSV読み込み、J-Quants API呼び出しは行わない。

---

# 12. Phase4-E mock builder互換

Phase4-FはPhase4-E mock builderを壊さない。

以下が引き続き通ることを確認する。

```bash
python3 scripts/build_candidate_features_mock.py
python3 scripts/audit_phase4e_candidate_feature_builder_mock.py
```

---

# 13. 禁止事項

Phase4-Fでは以下を実装しない。

```text
実データ全量feature生成は実装しない
実fins_summary結合は実装しない
実market index処理は実装しない
実sector aggregation処理は実装しない
label生成は実装しない
dataset builderは実装しない
Candidate AI本体は実装しない
学習は実装しない
推論は実装しない
backtestは実装しない
Historical Evaluationは実装しない
Paper Tradingは実装しない
Opportunity AIは実装しない
Position Management AIは実装しない
Capital Allocationは実装しない
Order Managerは実装しない
Broker実API接続は実装しない
発注は実装しない
売買は実装しない
Portfolio自動更新は実装しない
```

---

# 14. Phase4-F完了条件

```text
real data loader contractがある
daily_quotes_normalized adapterがある
schema mappingが明記されている
input schema validationがある
as_of_dateより後の行を除外できる
dropped_future_row_countをaudit/manifestに記録できる
source_snapshot_id ruleがある
input manifest / hash ruleがある
trading calendar window ruleが明記されている
real data dry-run scriptがある
Phase4-E mock builderが壊れていない
実feature生成本番、label生成、学習、推論、backtest、売買系に進んでいない
```

---

# 15. Phase4-Gへの引き継ぎ

Phase4-G案:

```text
Candidate Feature Builder Real Data Dry-run Integration
```

検討事項:

```text
RuntimePaths経由の daily_quotes_normalized loader
jsonl/parquet input adapter
trading calendar serviceとの営業日window接続
as_of_date非営業日の扱い
source manifest hashの実data manifest連携
実データ小範囲dry-runからmock feature builderへの接続
```
