# Phase12.5 Positions Safe Diagnosis Result

作成日: 2026-07-04

## Summary

前回実装した `positions_safe_diagnosis.json` について、既存の Broker ReadOnly artifact を確認した。

判定は `BLOCK`。

理由は、`.runtime/operations/broker_readonly_reports/*/positions_safe_diagnosis.json` がまだ生成されていないため。既存の2026-07-03 Broker ReadOnly artifactは `2026-07-03 15:40:06 +0900` 作成で、`src/ai_fund_lab_v2/broker/tachibana_broker_snapshot.py` のsafe diagnosis実装mtime `2026-07-04 05:44:45 +0900` より前の実行結果だった。

したがって、Positions APIが本当に空なのか、normalizer key不足なのか、writer filterなのかは今回のartifactからまだ確定できない。Unified Ledger Phase Bへは進めない。

## 確認対象

- `.runtime/operations/broker_readonly_reports/*/positions_safe_diagnosis.json`
- `.runtime/operations/broker_positions/2026-07-03/positions.json`
- `.runtime/operations/broker_snapshot/2026-07-03/broker_snapshot.json`
- `.runtime/operations/broker_readonly_reports/2026-07-03/broker_readonly_snapshot_report.json`

## 1. positions_safe_diagnosis.json生成有無

未生成。

確認結果:

```text
find .runtime/operations/broker_readonly_reports -name positions_safe_diagnosis.json
```

出力なし。

既存日付別確認:

| date | diagnosis exists | report status | report positions count | snapshot source positions | broker_positions count |
|---|---:|---|---:|---:|---:|
| 2026-06-29 | false | FAILED_READONLY | 7 | 7 | 0 |
| 2026-06-30 | false | FAILED_READONLY | 8 | 8 | 0 |
| 2026-07-01 | false | PASS_WITH_WARNINGS | 7 | 7 | 0 |
| 2026-07-03 | false | FAILED_BROKER_READONLY_FETCH | 12 | 12 | 0 |

## 2. cash / margin top_level_keys

未確認。

`positions_safe_diagnosis.json` が存在しないため、safe diagnosisとしての `cash.top_level_keys` / `margin.top_level_keys` は確認できない。

## 3. list_key_hits

未確認。

同じく `positions_safe_diagnosis.json` 未生成のため、raw取得直後の list key hit は確認できない。

## 4. row_count

safe diagnosis上の row_count は未確認。

既存artifactで確認できるのは、normalizer後のsource countのみ。

- 2026-07-03 report `health.positions.count = 12`
- 2026-07-03 broker_snapshot `source_counts.positions = 12`
- 2026-07-03 broker_snapshot `counts.positions = 0`
- 2026-07-03 broker_positions `positions = []`

## 5. row_key_names

未確認。

既存の `broker_readonly_source/tachibana_demo_snapshot.json` はraw responseではなくnormalized後snapshotであるため、API取得直後のrow key namesは確認できない。

## 6. candidate_key_match_rate

未確認。

`issue_code` / `quantity` / `market_value` / `price` の candidate match rate は `positions_safe_diagnosis.json` に出る設計だが、まだ生成されていない。

## 7. match rate が0なのか

未確認。

match rate artifactが未生成のため、0かどうか判定不可。

## 8. match rate があるのに broker_positions が0なのか

未確認。

2026-07-03時点では以下の状態。

- Broker ReadOnly report positions count: `12`
- Broker snapshot source positions: `12`
- Broker positions artifact: `0`

ただし、match rateが存在しないため、「候補keyがhitしていたのにwriter filterで0になった」のか、「候補keyがhitしていないためnormalizerで空になった」のかは切り分け不能。

## 9. 原因分類

現時点では未確定。

| candidate | 判定 | 理由 |
|---|---|---|
| APIが空 | 未確定 | raw取得直後のkey診断がまだない。 |
| normalizer key不足 | 未確定 | row_key_names / candidate match rate がまだない。 |
| writer filter | 未確定 | match rateがあるかどうか不明。 |

ただし、既存の2026-07-03 artifactからは、normalizer後source positionsは12行あるが broker_positions writer後は0件、という差分だけは確認済み。

## 10. Unified Ledger Phase Bへ進めてよいか

進めない。

`positions_safe_diagnosis.json` が未生成のため、Positions API root causeはまだ確定していない。ここでUnified Ledger Phase B、特に broker_orders fallback projection や保有projectionに進むと、normalizer/key mapping不具合を隠す可能性が残る。

## 禁止事項の遵守

- 修正なし
- Submit実行なし
- Broker注文なし
- Production接続なし
- Production注文なし
- artifact削除なし
- notification送信なし

## 判定

`BLOCK`

次に必要なのは、許可された通常Broker ReadOnly実行後に生成される `positions_safe_diagnosis.json` を再確認すること。今回の既存artifactだけでは、API空 / normalizer key不足 / writer filter の原因分類はできない。
