# Phase5-D Opportunity Dataset Builder

作成日: 2026-06-14

## 1. 目的

Phase5-D では、Phase4 Candidate AI が出力した Candidate Top50 を母集団として、Opportunity AI 学習用 dataset を作成する builder を実装した。

Opportunity AI は Candidate Top50 の中で期待値を順位付けする AI である。全銘柄から候補を抽出せず、保有判断、売却判断、購入株数、資金配分、発注、Broker API、Paper Trading は行わない。

## 2. 実装範囲

追加実装:

```text
src/ai_fund_lab_v2/opportunity_ai/dataset_builder.py
scripts/build_phase5d_opportunity_dataset.py
tests/opportunity_ai/test_phase5d_opportunity_dataset_builder.py
```

出力候補:

```text
reports/opportunity_ai/phase5d/opportunity_dataset.parquet
reports/opportunity_ai/phase5d/opportunity_dataset_summary.json
reports/opportunity_ai/phase5d/opportunity_dataset_audit.json
```

## 3. Dataset Builder の処理

処理内容:

```text
1. Candidate Top50 output を読み込む
2. Phase5-C feature schema に従って feature を結合する
3. Phase5-B label schema に従って label を結合する
4. feature columns と label columns を prefix で分離する
5. train / validation / test split を target_date 単位で作る
6. leakage audit を実行する
7. dataset summary / audit を出力する
```

列 prefix:

```text
feature__: 学習入力 feature
label__: 学習・評価 label
```

## 4. Leakage Guard

feature として利用禁止:

```text
future_return_*
future_max_return_*
future_max_drawdown_*
downside_bad_*
top_decile_*
expected_edge_label_*
risk_adjusted_future_return_*
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
paper_trading
pm_multiplier
opportunity_output
candidate_evaluation
```

future 系列は `label__` としてのみ dataset に入る。推論 dataset では label table を読まない構造にする。

## 5. Split Rule

split は target_date 単位で作る。

```text
target_date <= 2024-12-31: train
2025-01-01 <= target_date <= 2025-12-31: validation
target_date >= 2026-01-01: test
```

同じ target_date が複数 split にまたがらないことを audit する。

## 6. Current Data Note

Phase4 の最新 Candidate Top50 は `2026-06-12` で、Phase4 label table は `2026-05-15` までのため、現時点の正式 artifact をそのまま使うと join coverage が不足する可能性がある。

この場合、builder は Phase4 成果物を破壊せず、summary に `BLOCKED_BY_JOIN_COVERAGE` を出す。学習へ進むには、Candidate Top50 と label table の target_date + code が重なる Phase5-D dataset artifact が必要である。

## 7. 禁止事項

Phase5-D では以下を行っていない。

```text
学習
推論
backtest
Paper Trading
Broker API
発注
資金配分
promotion
reader switch
Phase4 成果物の上書き
mock path の上書き
```

## 8. Phase5-E への引き継ぎ

Phase5-E Training は、`leakage_audit_status == OK` かつ `readiness_status == READY_FOR_OPPORTUNITY_TRAINING` の dataset を入力にする。
