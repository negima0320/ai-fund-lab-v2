# Phase12.5 Positions API Safe Diagnosis

作成日: 2026-07-04

## Summary

Broker Positions API が本当に空なのか、または normalizer が key を拾えていないのかを切り分けるため、Positions API取得直後の safe diagnosis を追加した。

Unified Ledger実装、Broker Orders fallback実装、Submit/Broker注文/Production接続は行っていない。

## 実装内容

`run_tachibana_broker_snapshot()` で以下の直後に診断を保存するようにした。

```text
cash_response = cash_fetch.value
margin_response = margin_fetch.value
```

保存先:

```text
.runtime/operations/broker_readonly_reports/YYYY-MM-DD/positions_safe_diagnosis.json
```

`operations` 経由では `reports_dir` が `.runtime/operations/broker_readonly_reports/<trade-date>/` になるため、上記パスに保存される。

## 保存項目

保存するのは key names と count / match rate のみ。

- `top_level_keys`
- `list_key_hits`
- `row_count`
- `row_key_names`
- `candidate_key_presence`
- `candidate_key_hit_counts`
- `candidate_key_match_rate`
- `combined.candidate_key_match_rate`

候補key group:

- `issue_code`
- `quantity`
- `market_value`
- `price`

## 保存しないもの

- raw response
- raw values
- secret
- 注文番号
- 口座番号
- URL
- token
- session
- 銘柄コード値
- 数量値
- 価格値

診断artifactにも以下を明示する。

```json
{
  "raw_response_saved": false,
  "raw_values_saved": false,
  "secret_saved": false,
  "order_number_saved": false,
  "account_identifier_saved": false,
  "url_saved": false,
  "token_saved": false,
  "session_saved": false,
  "issue_code_value_saved": false,
  "quantity_value_saved": false,
  "price_value_saved": false
}
```

## 変更ファイル

- `src/ai_fund_lab_v2/broker/tachibana_broker_snapshot.py`
- `tests/broker/test_tachibana_phase10c_session_foundation.py`
- `docs/phase_reports/phase12_5_positions_safe_diagnosis.md`
- `reports/phase_reports/phase12_5_positions_safe_diagnosis.json`

## 実装詳細

追加helper:

- `build_positions_api_safe_diagnosis()`
- `_position_response_key_diagnosis()`
- `_position_rows_for_diagnosis()`
- `_combined_candidate_match_rate()`

`positions_safe_diagnosis.json` のpathは以下にも残す。

- broker snapshot report: `positions_safe_diagnosis_path`
- snapshot health: `health.positions.safe_diagnosis_path`
- snapshot health: `health.positions.candidate_key_match_rate`
- broker snapshot: `positions_api_safe_diagnosis_path`

## テスト

実行:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py -q
PYTHONPATH=src python3 -m pytest tests/phase12/test_phase12_5_production_equivalent_guards.py -q
```

結果:

```text
94 passed
6 passed
```

追加確認:

- raw値が保存されない
- key名だけ保存される
- candidate match率が保存される
- secret値が保存されない
- snapshot/reportから diagnosis path を追える

## 禁止事項の遵守

- Submit実行なし
- Broker注文なし
- Production接続なし
- Production注文なし
- artifact削除なし
- notification送信なし
- secret保存なし
- raw response保存なし
- Unified Ledger実装なし
- Broker Orders fallback実装なし

## 残課題

次回のBroker ReadOnly実行後に、生成された `positions_safe_diagnosis.json` で以下を確認する。

- raw top-level list key が想定通りか
- row key names に normalizer未対応keyがあるか
- `issue_code` / `quantity` / `market_value` / `price` のmatch rateが0なのか
- match rateが0でないのに broker_positions が0なら、値が空/ゼロなのか normalizer後段filterなのかを追加監査する

今回の実装は診断のみであり、Positions APIのmapping修正やfallback projectionはまだ行っていない。
