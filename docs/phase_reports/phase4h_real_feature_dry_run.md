# AI Fund Lab vNext Phase4-H Real Feature Dry-run Report

---

# 1. このレポートの目的

本レポートは、Phase4-H Real Feature Dry-run の完了条件を確認する。

Phase4-Hの目的は、Phase4-Gの real normalized data reader output を Phase4-Eの Candidate Feature Builder に接続し、小範囲の実 `daily_quotes_normalized` から Candidate feature table を dry-run 生成することである。

Phase4-Hでは実データ全量feature生成は実装しない。

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
docs/phase_reports/phase4f_candidate_real_data_loader_contract.md
docs/phase_reports/phase4g_real_normalized_dry_run.md
reports/phase_reports/phase4a_candidate_ai_design_audit.json
reports/phase_reports/phase4b_candidate_training_data_design_audit.json
reports/phase_reports/phase4c_candidate_feature_builder_design_audit.json
reports/phase_reports/phase4d_candidate_feature_builder_skeleton_audit.json
reports/phase_reports/phase4e_candidate_feature_builder_mock_audit.json
reports/phase_reports/phase4f_candidate_real_data_loader_contract_audit.json
reports/phase_reports/phase4g_real_normalized_dry_run_audit.json
```

---

# 3. Phase4-H実装内容の要約

作成した要素:

```text
scripts/build_candidate_features_real_dry_run.py:
  normalized reader -> loader adapter -> feature builder 接続
  small-range real feature dry-run
  schema validation
  leakage audit
  feature / manifest / audit / summary output
  SKIPPED安全終了

scripts/audit_phase4h_real_feature_dry_run.py:
  Phase4-H completion audit
```

---

# 4. real feature dry-run条件

default条件:

```text
lookback_business_days = 60
max_codes = 10
max_rows = 1000
input_format = auto
```

小範囲制限は必須であり、実データ全量feature生成は行わない。

---

# 5. normalized reader -> loader -> feature builder 接続

処理順:

```text
1. daily_quotes_normalizedをRuntimePaths経由でdiscovery
2. trading calendar windowでas_of_dateを正規化
3. max_codes / max_rowsでsmall-range read
4. Phase4-F loader adapterで標準入力schemaへ変換
5. Phase4-E feature builderへ渡す
6. schema validationを実行
7. leakage auditを実行
8. feature / manifest / audit / summaryを保存
```

---

# 6. 生成feature一覧

Phase4-HではPhase4-Eの最小featureだけを生成する。

```text
price_momentum_return_5d
price_momentum_return_20d
volume_momentum_ratio_5d
volatility_return_std_20d
trend_close_over_ma_20d
liquidity_avg_volume_20d
missing_flags_insufficient_lookback
```

必要lookback不足の銘柄:

```text
universe_eligible = False
excluded_reason = insufficient_lookback
```

---

# 7. as_of_date / future exclusion

Feature計算には `as_of_date` より後の行を使わない。

Phase4-G readerがsource rowsへfuture rowを含めた場合でも、Phase4-F adapterが以下を行う。

```text
date > as_of_date の行を除外
dropped_future_row_count をauditへ記録
dropped_future_row_count をmanifestへ記録
```

feature row の `data_end_date` は `normalized_as_of_date` 以下でなければならない。

---

# 8. runtime出力先

Feature dry-run生成物:

```text
.runtime/candidate_ai/features/candidate_features_real_dry_run_{as_of_date}.json
.runtime/candidate_ai/manifests/candidate_features_real_dry_run_manifest_{as_of_date}.json
.runtime/candidate_ai/audit/candidate_features_real_dry_run_audit_{as_of_date}.json
reports/candidate_ai/phase4h_real_feature_dry_run_summary.json
```

loader側のdry-run rows / manifest / audit もPhase4-G同様に `.runtime/candidate_ai/` 配下へ保存する。

---

# 9. schema validation / leakage audit

Feature tableはPhase4-Dのschema validationを通す。

確認内容:

```text
必須列
許可feature prefix
禁止feature列なし
as_of_date <= target_date
universe_eligible bool-like
```

Leakage auditでは以下を検出対象にする。

```text
future_return_*
future_max_return_*
future_max_drawdown_*
top_decile_*
downside_bad_*
label
backtest/trade/portfolio/cash/order
profit/loss/pnl
```

---

# 10. SKIPPED安全終了

実 normalized data が存在しない環境では落とさず、以下のsummaryを出す。

```text
status = SKIPPED
reason = normalized data not found
```

---

# 11. Phase4-E / Phase4-G互換確認

以下が引き続き通ることを確認する。

```bash
python3 scripts/build_candidate_features_mock.py
python3 scripts/audit_phase4e_candidate_feature_builder_mock.py
python3 scripts/check_candidate_real_normalized_dry_run.py
python3 scripts/audit_phase4g_real_normalized_dry_run.py
```

---

# 12. 禁止事項

Phase4-Hでは以下を実装しない。

```text
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
実データ全量feature生成は実装しない
```

---

# 13. Phase4-H完了条件

```text
real feature dry-run scriptがある
normalized reader -> loader adapter -> feature builder が接続されている
small-range制限がある
feature tableが出力される、またはnormalized dataなしならSKIPPEDで安全終了する
必須featureが生成される
schema validationを通している
leakage auditを通している
as_of_dateより後の行をfeature計算に使わない
dropped_future_row_countを記録する
manifest JSONが出力される
audit JSONが出力される
summary JSONが出力される
Phase4-E / Phase4-G互換が維持されている
label生成、学習、推論、backtest、売買系に進んでいない
```

---

# 14. Phase4-Iへの引き継ぎ

Phase4-I案:

```text
Candidate Feature Dry-run Quality Review / Readiness Audit
```

検討事項:

```text
実feature dry-runのeligible/excluded分布確認
insufficient_lookbackの多発原因確認
as_of_date選択ルール
feature_version更新ルール
実feature tableの品質レポート
次にdataset/label設計へ進む前のleakage監査強化
```
