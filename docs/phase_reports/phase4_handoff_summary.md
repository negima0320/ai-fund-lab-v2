# AI Fund Lab vNext Phase4 Handoff Summary

作成日: 2026-06-13

## 1. この資料の目的

Phase4 Candidate AI vNext が A から AA まで進み、設計、mock履歴、controlled execution、real runtime監査が混ざって見えにくくなってきた。

この資料は、次の作業者が以下をすぐ把握できるようにするための引き継ぎである。

- ここまでの全体の流れ
- Phase1からPhase3の土台
- Phase4で何を作り、何をまだ作っていないか
- 現在の到達点
- 次にやるべきこと
- 絶対に越えてはいけない境界

## 2. vNext全体の現在地

正式ロードマップ上の現在地は以下。

```text
Phase4 Candidate AI vNext
```

Phase4の目的は以下。

```text
全銘柄から「見る価値がある上昇候補」を抽出する
```

Candidate AIはまだ以下をしていない。

```text
買い判断
売却判断
期待値判断
購入金額判断
資金配分
Portfolio更新
Paper Trading
発注
Broker実API接続
```

Phase4は、ここまで「Candidate AI本体を作る前の、feature生成と監査の土台作り」に集中している。

## 3. Phase1からPhase3の土台

### Phase1 Data Foundation

目的:

```text
市場データ基盤
```

主な成果:

- J-Quants client基盤
- raw ingestion
- Market Data Store
- runtime path管理
- `.runtime` 集約
- manifest
- Parquet / JSONL storage backend
- trading calendar
- raw quality check
- daily_quotes normalized schema v2
- `.runtime/data/raw_normalized/jquants/` の導入

重要な注意:

- Phase1 completion report上の判定は一部 `NG / 条件付き` だが、以後のPhaseでは `daily_quotes_normalized` を入力として使う方針で進めている。
- raw v1 daily quotesは source evidence として保持する。
- Feature入力は raw v1 ではなく normalized raw を使う。
- future labelはPhase1では生成していない。

主な参照:

- `docs/phase_reports/phase1_completion_report.md`
- `src/ai_fund_lab_v2/data_quality/normalization.py`
- `src/ai_fund_lab_v2/data_store/`
- `src/ai_fund_lab_v2/runtime/paths.py`

### Phase2 Broker Foundation

目的:

```text
実API未接続のBroker stub / mock基盤
```

主な成果:

- broker settings
- secret sanitizer
- read-only CLMID allowlist
- mock transport
- Tachibana request builder
- read-only client skeleton
- response envelope
- normalized broker models
- snapshot writer
- mock broker sync
- mock-only CLI

重要な注意:

- 立花証券は未契約前提。
- live modeは作っていない。
- 実login/logoutはしていない。
- 発注系CLMIDは禁止。
- snapshotはPortfolio State更新前inputの形まで。

主な参照:

- `docs/phase_reports/phase2_broker_foundation_completion_audit.md`
- `src/ai_fund_lab_v2/broker/`

### Phase3 Safety Foundation

目的:

```text
Broker状態とPortfolio状態の照合、安全停止、手動復旧の土台
```

主な成果:

- PortfolioState / BrokerState
- reconciliation
- SafetyStatus OK / WARNING / HALT
- TradingLock
- SafetyReport
- Broker snapshot adapter
- dry-run safety flow
- manual review
- manual unlock request / approval / apply
- OperationGuard latest lock state判定

重要な原則:

```text
分からない時は止まる
Broker状態を正とする
Broker Sync不一致はHALT
HALT時は新規買い禁止
自動復旧は禁止
復旧には人間承認が必要
```

主な参照:

- `docs/phase_reports/phase3_safety_foundation_completion_audit.md`
- `src/ai_fund_lab_v2/safety/`

## 4. Phase4の大きな流れ

Phase4は大きく4つの流れに分かれる。

### 4.1 設計固定: Phase4-AからC

目的:

```text
Candidate AIを作る前に、責務、feature、training data、feature builder設計を固定する
```

完了したこと:

- Phase4-A: Candidate AI Design
- Phase4-B: Candidate Training Data Design
- Phase4-C: Candidate Feature Builder Design

固定した責務:

```text
Candidate AIは上昇候補抽出のみ
買うかどうかは決めない
期待値順位は作らない
購入金額は決めない
保有判断、売却判断はしない
```

禁止feature:

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

主な参照:

- `docs/03_ai_design/candidate_ai_design.md`
- `docs/03_ai_design/candidate_feature_catalog.md`
- `docs/03_ai_design/candidate_training_data_design.md`
- `docs/03_ai_design/candidate_feature_builder_design.md`
- `docs/phase_reports/phase4a_candidate_ai_design.md`
- `docs/phase_reports/phase4b_candidate_training_data_design.md`
- `docs/phase_reports/phase4c_candidate_feature_builder_design.md`

### 4.2 Skeleton / mock feature builder: Phase4-DからK

目的:

```text
実AIや学習に進まず、Candidate feature生成のcontractとmock dry-runを作る
```

完了したこと:

- Phase4-D: candidate_ai package skeleton
- Phase4-E: mock feature builder
- Phase4-F: real data loader contract
- Phase4-G: real normalized dry-run / trading calendar window
- Phase4-H: real feature dry-run
- Phase4-I: readiness audit。履歴不足で `BLOCKED_BY_DATA_WINDOW`
- Phase4-J: prepared dry-run準備
- Phase4-K: mock normalized history拡張。prepared dry-runがREADY

Phase4-Kの重要結果:

```text
readiness_status = READY_FOR_FULL_RANGE_FEATURE_DRY_RUN
eligible_count = 30
schema validation = OK
leakage audit = OK
data_source_type = mock
```

重要な注意:

- Phase4-Kの履歴は mock normalized history。
- real J-Quants由来とは扱わない。
- このmock履歴を使って、以後のfull-range実行の安全性だけを育てた。

主な参照:

- `src/ai_fund_lab_v2/candidate_ai/`
- `scripts/build_candidate_features_mock.py`
- `scripts/build_candidate_features_real_dry_run.py`
- `scripts/build_candidate_features_real_prepared_dry_run.py`
- `scripts/prepare_phase4k_normalized_history.py`
- `docs/phase_reports/phase4k_normalized_history_readiness.md`

### 4.3 Full-range feature dry-run安全化: Phase4-LからV

目的:

```text
全期間feature生成の前に、chunk、manifest、resume、failure、controlled executionを安全にする
```

完了したこと:

- Phase4-L: full-range feature dry-run design
- Phase4-M: chunk plan / manifest / resume skeleton
- Phase4-N: no-write gate
- Phase4-O: controlled execution。最小1chunkでtmp -> final atomic move確認
- Phase4-P: failure / resume audit
- Phase4-Q: resume-aware controlled runner
- Phase4-R: controlled batch readiness audit
- Phase4-S: first controlled batch execution
- Phase4-T: post-batch integrity audit
- Phase4-U: controlled batch expansion
- Phase4-V: post-expansion readiness audit

到達点:

```text
controlled executionは、mock/runtime小規模chunkで安全に実行できる
schema validation OK
leakage audit OK
tmp -> final atomic move OK
SUCCESS skip / FAILED rerun / missing run / partial tmp warning / inconsistency block を確認済み
```

Phase4-Vの重要結果:

```text
readiness_status = READY_FOR_FULL_CONTROLLED_FEATURE_GENERATION
```

ただし:

```text
これはmock/runtime controlled batchの話
real_runtime十分履歴でのfull feature生成許可ではない
```

主な参照:

- `src/ai_fund_lab_v2/candidate_ai/full_range.py`
- `scripts/build_candidate_features_full_range_dry_run.py`
- `scripts/build_candidate_features_full_range_controlled.py`
- `scripts/build_candidate_features_full_range_resume_controlled.py`
- `scripts/build_candidate_features_first_controlled_batch.py`
- `scripts/build_candidate_features_controlled_batch_expansion.py`
- `docs/phase_reports/phase4v_post_expansion_readiness.md`

### 4.4 real_runtime履歴の分岐: Phase4-WからAA

目的:

```text
mock履歴ではなく、実J-Quants由来のreal_runtime normalizedを安全に扱う準備
```

完了したこと:

- Phase4-W: real_runtime coverage audit。既存 normalized は mock 扱いで、real_runtimeなし
- Phase4-X: raw J-Quants daily quotes から real_runtime normalized を再構築可能か監査
- Phase4-Y: isolated rebuild plan
- Phase4-Z: isolated real_runtime normalized rebuild。no-promotionで実行
- Phase4-AA: coverage gap / fetch-normalize plan

Phase4-Zの重要結果:

```text
data_source_type = real_runtime
api_call_performed = false
promotion_status = not_promoted
promotion_performed = false
default_mock_path_unchanged = true
mock_history_overwritten = false
row_count = 4231
code_count = 4231
date_min = 2026-06-01
date_max = 2026-06-01
business_day_count = 1
coverage_status = ISOLATED_REAL_RUNTIME_NORMALIZED_READY
```

Phase4-AAの重要結果:

```text
readiness_status = READY_FOR_REAL_RUNTIME_HISTORY_FETCH_PLAN
current_business_day_count = 1
required_business_day_count = 60
missing_business_day_count = 59
fetch_range_start = 2026-03-03
fetch_range_end = 2026-06-01
preferred_training_start_date = 2021-06-01
```

重要な注意:

- `.runtime/data/raw_normalized_real_runtime/...` は isolated real_runtime。
- `.runtime/data/raw_normalized/...` のmock normalized pathは上書きしていない。
- reader switchはしていない。
- promotionはしていない。
- 実API fetchはしていない。
- 1営業日分なのでCandidate feature generationにはまだ不足。

主な参照:

- `docs/phase_reports/phase4w_real_runtime_coverage.md`
- `docs/phase_reports/phase4x_real_runtime_normalized_source.md`
- `docs/phase_reports/phase4y_real_runtime_normalized_rebuild_plan.md`
- `docs/phase_reports/phase4z_real_runtime_normalized_isolated.md`
- `docs/phase_reports/phase4aa_real_runtime_coverage_gap_plan.md`
- `reports/candidate_ai/full_range/phase4aa_real_runtime_coverage_gap_plan_summary.json`

## 5. 現在の重要な状態

### mock系

mock normalized historyを使ったCandidate feature dry-runの実行安全性はかなり固まっている。

確認済み:

- chunk plan
- manifest
- resume / restart
- failure handling
- controlled execution
- batch expansion
- post-batch integrity

ただし、これはCandidate AI学習や推論ではない。

### real_runtime系

real_runtime normalizedは隔離パスに1営業日分だけ存在する。

```text
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet
```

まだ不足:

```text
60営業日lookback
2021-06以降のtraining history
post-fetch coverage audit
promotion approval
reader switch approval
```

### default mock path

以下は維持する。

```text
.runtime/data/raw_normalized/jquants/equities_bars_daily/
```

このpathはmock履歴として扱う。real_runtimeとして誤認しない。

## 6. 次に行うこと

推奨する次フェーズ:

```text
Phase4-AB No-live Real Runtime History Fetch Plan
```

目的:

```text
実fetchを行う前に、60営業日以上のreal_runtime履歴を作るためのfetch計画を正確に固定する
```

やること:

- trading calendarから必要営業日を算出
- target_end_date / target_start_dateを確定
- J-Quants `/v2/equities/bars/daily` のrequest planを作る
- Light plan 60 req/minのrate limit planを明記
- endpoint / date / pagination / max_pages のdry-run planを出す
- 保存先は `.runtime/data/raw/jquants/equities_bars_daily/`
- normalize先は `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/`
- manifest/provenance必須項目を確認
- mock path上書き禁止を監査
- fetch後に必要なcoverage audit条件を定義

まだやらないこと:

- J-Quants API呼び出し
- 実fetch
- reader switch
- promotion
- Candidate feature full generation
- label生成
- dataset builder
- model training
- inference
- backtest
- trading

Phase4-ABの次に進むなら:

```text
Phase4-AC Real Runtime History Fetch Dry-run CLI
```

さらにその後、明示承認がある場合のみ:

```text
Phase4-AD Controlled Real Runtime History Fetch
Phase4-AE Real Runtime Normalize Coverage Audit
```

## 7. 絶対に守る境界

Phase4で今守るべき境界:

```text
Candidate AIは候補抽出だけ
買い判断はしない
売却判断はしない
資金配分はしない
Portfolio更新はしない
発注はしない
Broker実APIへ接続しない
```

real_runtime履歴についての境界:

```text
mock pathを上書きしない
isolated real_runtime pathにだけ書く
promotion_status = approved までreader switch禁止
coverage audit OKまでfeature full generation禁止
secretをstdout/log/report/manifestに出さない
```

future leakage境界:

```text
future_return_* はfeatureに使わない
future_max_return_* はfeatureに使わない
future_max_drawdown_* はfeatureに使わない
top_decile_* はfeatureに使わない
downside_bad_* はfeatureに使わない
trade/backtest/portfolio/order/cash/pnl系はfeatureに使わない
```

## 8. よく間違えやすい点

### Phase4-KのREADYとPhase4-AAのREADYは意味が違う

Phase4-K:

```text
mock normalized historyでfull-range feature dry-runに進める
```

Phase4-AA:

```text
real_runtime履歴fetch計画に進める
```

どちらも「AI学習に進める」ではない。

### Phase4-VのREADYはreal_runtimeではない

Phase4-Vは controlled batch execution の安全性のREADYであり、実J-Quants履歴が足りたという意味ではない。

### Phase4-Zのreal_runtimeは1営業日だけ

Phase4-Zはisolated rebuildが成功しただけ。60営業日lookbackには不足している。

### default normalized pathはmockとして扱う

現時点で以下をreal_runtimeとして扱わない。

```text
.runtime/data/raw_normalized/jquants/equities_bars_daily/
```

real_runtimeは以下。

```text
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/
```

## 9. 主要コマンド

Phase4-AA現在地確認:

```bash
python3 scripts/audit_phase4aa_real_runtime_coverage_gap_plan.py
python3 -m pytest tests/test_phase4aa_real_runtime_coverage_gap_plan.py
python3 -m pytest -q
```

Phase4-Z再確認:

```bash
python3 scripts/audit_phase4z_real_runtime_normalized_isolated.py
```

Controlled batch系を再確認する場合:

```bash
python3 scripts/audit_phase4v_post_expansion_readiness.py
python3 -m pytest tests/test_phase4v_post_expansion_readiness.py
```

## 10. 引き継ぎ時点のpytest

直近確認:

```text
python3 -m pytest -q
392 passed
```

## 11. 作業再開時のおすすめ順序

1. `docs/phase_reports/phase4_handoff_summary.md` を読む。
2. `docs/phase_reports/phase4aa_real_runtime_coverage_gap_plan.md` を読む。
3. `reports/candidate_ai/full_range/phase4aa_real_runtime_coverage_gap_plan_summary.json` を確認する。
4. `scripts/audit_phase4aa_real_runtime_coverage_gap_plan.py` を実行する。
5. Phase4-ABとして no-live fetch plan を作る。
6. 実APIやfetchに進む場合は、必ず別フェーズで明示承認を取る。

## 12. Phase4-ABの最小成果物案

作成候補:

```text
docs/phase_reports/phase4ab_no_live_real_runtime_fetch_plan.md
docs/phase_reports/phase4ab_no_live_real_runtime_fetch_plan_audit.md
reports/candidate_ai/full_range/phase4ab_no_live_real_runtime_fetch_plan_summary.json
reports/phase_reports/phase4ab_no_live_real_runtime_fetch_plan_audit.json
scripts/audit_phase4ab_no_live_real_runtime_fetch_plan.py
tests/test_phase4ab_no_live_real_runtime_fetch_plan.py
```

Phase4-ABで固定すること:

- exact target date range
- expected business days
- J-Quants request count estimate
- endpoint params
- pagination policy
- rate limit policy
- dry-run output format
- raw save path
- isolated normalize path
- post-fetch coverage audit gate
- no-promotion rule
- no-reader-switch rule

Phase4-ABでも禁止:

```text
実API呼び出し
実fetch
promotion
reader switch
feature full generation
label generation
training
inference
backtest
trading
```

## 13. 結論

Phase4は重くなっているが、到達点は整理できる。

```text
mock系: feature generation execution safetyはかなり進んだ
real_runtime系: isolated rebuildはできたが履歴が1営業日で不足
次: real_runtimeを60営業日以上へ拡張するためのno-live fetch plan
```

次に進むべきは、実fetchそのものではなく、まず Phase4-AB で fetch plan を固めること。
