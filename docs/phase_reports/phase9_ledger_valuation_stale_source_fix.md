# Phase9 Ledger Valuation Stale Source Fix

Status:

```text
PHASE9_LEDGER_VALUATION_STALE_SOURCE_FIX_COMPLETE
```

## BUG原因

2026-06-17のPaper Trading runで、Ledger Valuationが2026-06-17終値ではなく2026-06-16終値を再利用していた。

原因:

- Unified Runnerが`--allow-api-fetch`付きでもmarket data refreshを実行していなかった。
- canonical quotesの最新日付が2026-06-16のままだった。
- `resolve_business_dates()`がcanonical quotesの最新日付へフォールバックし、2026-06-17 runでも`data_target_date=2026-06-16`になった。
- Ledger Valuationも`valuation_date=2026-06-16`で再実行された。
- その状態でも`LEDGER_VALUATION_UPDATED`になり、最新評価のように見えていた。

## 修正内容

実装した修正:

- stale source検出をLedger Valuationに追加。
- stale時は通常の`LEDGER_VALUATION_UPDATED`を返さず、`LEDGER_VALUATION_STALE_SOURCE`を返す。
- stale時は`latest.json`を書き換えない。
- stale時はvaluation outputに`stale_price_source=true`を出す。
- valuation manifestに価格ソース情報を追加。
- 同一`valuation_date`再実行時に`holding_days`を増やさない。
- valuation output pathに`run_date`とrun idを含め、再実行上書きを回避。
- Unified Runnerの未接続market refreshをBLOCK化。
- operation log / manifest / blog reportで評価コンテキストを確認できるようにした。

## market refresh接続状況

今回、Unified Runner内でJ-Quants refreshとcanonical rebuildを直接接続する案Aは採用していない。

理由:

- 既存コード上、Unified Runnerはmarket refresh実行をfuture launchd profile扱いにしている。
- 安全に接続するには、J-Quants fetch、raw merge、canonical rebuild、feature refreshの順序と失敗時復旧を追加で設計する必要がある。
- 30営業日検証を壊さないため、今回は古い価格で進まないBLOCKを優先した。

採用:

```text
案B: market refresh未接続ならBLOCK
```

Unified Runnerで`allow_api_fetch=True`の場合:

```text
market_data_refresh: MARKET_DATA_REFRESH_NOT_CONNECTED_BLOCKED
blocked_reasons: market_data_refresh_not_connected_in_unified_runner
```

## stale source検出仕様

追加ステータス:

```text
LEDGER_VALUATION_STALE_SOURCE
```

判定項目:

```text
run_date
expected_valuation_date
valuation_date
quote_source_path
quote_source_max_date
stale_price_source
```

stale判定:

```text
valuation_date < expected_valuation_date
```

または

```text
quote_source_max_date < expected_valuation_date
```

stale時:

- `ledger_latest_updated=false`
- `latest.json`は更新しない
- `blocked_reasons`に理由を出す
- `status=LEDGER_VALUATION_STALE_SOURCE`

## manifest / operation log / blog report

Ledger Valuation manifestに追加:

```text
run_date
expected_valuation_date
valuation_date
quote_source_path
quote_source_max_date
stale_price_source
run_id
```

Unified Runner operation log / manifestには、`step_statuses.valuation_context`として追加:

```text
run_date
decision_for
data_target_date
valuation_date
quote_source_path
quote_source_max_date
stale_price_source
market_data_refresh_status
```

Blog Report v4には、サマリー部へ次を追加:

```text
valuation_date
quote_source_max_date
stale_price_source
```

## holding_days修正

`PositionSnapshot`に後方互換のフィールドを追加した。

```text
last_valuation_date
```

ルール:

- `last_valuation_date`が空なら初回評価として`holding_days + 1`
- `valuation_date > last_valuation_date`なら`holding_days + 1`
- `valuation_date <= last_valuation_date`なら`holding_days`据え置き
- stale source時はledgerを更新しないため、holding_daysも進まない

既存ledgerに`last_valuation_date`がない場合も、空文字として読み込める。

## output path修正

旧:

```text
.runtime/phase9/ledger_valuations/2026-06-16/
```

新:

```text
.runtime/phase9/ledger_valuations/run_date=<run_date>/valuation_date=<valuation_date>_<run_id>/
```

例:

```text
.runtime/phase9/ledger_valuations/run_date=2026-06-17/valuation_date=2026-06-16_aifundlab_daily_...
```

これにより、同じvaluation_dateを再実行しても過去のvaluation outputを上書きしない。

## 既存Ledger補正要否

結論:

```text
補正は必要
ただし今回の修正では本番ledgerを自動補正していない
```

理由:

- 2026-06-17 runで2026-06-16評価が再実行され、`holding_days`が不正に進んだ可能性が高い。
- 2026-06-17終値はローカルcanonical/raw/raw_normalizedに存在しないため、正しい2026-06-17評価額へ補正する材料がない。
- market value / unrealized_pnlは2026-06-16終値ベースのまま。

補正案:

1. `.runtime/phase9/ledger/backups/`に`latest.json`のバックアップを作成する。
2. 2026-06-17終値をJ-Quantsから取得し、canonicalを更新する。
3. 2026-06-17を`expected_valuation_date=2026-06-17`としてLedger Valuationを再実行する。
4. holding_daysは、2026-06-16再評価で重複加算された分を監査してから補正する。

注意:

```text
今回、本番ledgerの破壊的な書き換えは実施していない。
```

## 実行したテスト

対象テストのみ実行。

```bash
python3 -m pytest tests/paper_trading/test_phase9s_ledger_valuation.py
```

結果:

```text
5 passed
```

```bash
python3 -m pytest tests/paper_trading/test_phase9u_unified_daily_runner.py
```

結果:

```text
6 passed
```

```bash
python3 -m pytest tests/paper_trading/test_phase9t_blog_report_v2.py
```

結果:

```text
2 passed
```

フルpytestは実行していない。

## 30営業日検証の再開可否

現時点の判定:

```text
DO_NOT_CONTINUE_YET
```

理由:

- stale sourceでは止まるようになったが、market refreshの実接続はまだBLOCK扱い。
- 2026-06-17の正しい終値がローカルにない。
- 2026-06-17 ledgerの補正が未実施。

再開条件:

1. J-Quants market refreshとcanonical rebuildを運用前に実行できること。
2. canonical quotesの`quote_source_max_date`が対象run_date以上であること。
3. Ledger Valuationが`LEDGER_VALUATION_UPDATED`で、`stale_price_source=false`であること。
4. 2026-06-17 ledger補正方針を確定すること。
