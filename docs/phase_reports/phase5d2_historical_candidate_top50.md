# Phase5-D2 Historical Candidate Top50 Dataset Generation

作成日: 2026-06-14

## 1. 目的

Phase5-D dataset builder は実装済みだが、latest formal Candidate Top50 は `2026-06-12`、Phase4 label table は `2026-05-15` までであり、`target_date + code` の join が成立しない。

Phase5-D2 では、label が存在する過去 `target_date` 群に対して、Phase4 Candidate AI の formal model / feature / inference logic を再利用し、Historical Candidate Top50 snapshot を生成する。

## 2. 実装

追加実装:

```text
src/ai_fund_lab_v2/opportunity_ai/historical_candidates.py
scripts/build_phase5d2_historical_candidate_top50.py
tests/opportunity_ai/test_phase5d2_historical_candidate_top50.py
```

出力:

```text
reports/opportunity_ai/phase5d2/historical_candidate_top50.parquet
reports/opportunity_ai/phase5d2/historical_candidate_top50_summary.json
reports/opportunity_ai/phase5d2/historical_candidate_top50_audit.json
```

## 3. Snapshot Selection

初期実装では軽量モードとして monthly snapshot をデフォルトにした。

```text
frequency=monthly:
  label table と feature table の共通 target_date から各月の最終営業日を選ぶ

frequency=weekly:
  共通 target_date からおおむね5営業日ごとに選ぶ

frequency=all:
  共通 target_date をすべて使う
```

## 4. Candidate Generation

各 target_date について:

```text
1. Phase4 long-history feature table から target_date の rows を読む
2. universe_eligible == true かつ excluded_reason == "" の銘柄を対象にする
3. Phase4 formal Candidate model で candidate_score を計算する
4. score 降順、code 昇順で順位付けする
5. Top50 を Candidate snapshot として保存する
```

出力 schema:

```text
target_date
code
candidate_score
candidate_rank
candidate_reason
excluded_reason
model_version
feature_version
feature_snapshot_id
inference_run_id
created_at
```

## 5. Leakage Guard

Candidate 生成 feature として禁止:

```text
future_return_*
future_max_return_*
future_max_drawdown_*
downside_bad_*
top_decile_*
trade_result
trade_profit
selected
bought
sold
cash
portfolio
annual_return
final_assets
backtest
Paper Trading results
PM倍率
AI評価結果
```

Phase5-D2 は future label を Candidate Top50 生成に使わない。label table は target_date 選定と join coverage audit にのみ使う。

## 6. Audit

監査項目:

```text
candidate_snapshot_count
target_date_count
candidate_rows
candidate_count_per_date_min
candidate_count_per_date_max
label_joinable_target_date_count
label_join_coverage_rate
future_feature_column_count
forbidden_feature_column_count
trade_result_column_count
portfolio_column_count
backtest_column_count
ai_output_leakage_column_count
```

## 7. 禁止事項

Phase5-D2 では以下を行わない。

```text
Phase4 Candidate AI 自体の修正
future label を使った Candidate 生成
backtest
Paper Trading
Broker API
発注
資金配分
promotion
reader switch
Phase4 artifact の上書き
mock path の上書き
```

## 8. Phase5-D / Phase5-E への引き継ぎ

`historical_candidate_top50.parquet` を Phase5-D dataset builder の `--candidate-path` に渡すことで、Phase5 Opportunity training dataset を生成できる。

Phase5-E Training は、Phase5-D dataset summary が `READY_FOR_OPPORTUNITY_TRAINING` になってから実行する。
