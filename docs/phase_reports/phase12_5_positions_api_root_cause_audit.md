# Phase12.5 Positions API Root Cause Audit

作成日: 2026-07-04

## Summary

Unified Ledger / broker_orders fallback projection へ進む前に、2026-07-03 の Broker Positions API が本当に空なのか、または normalizer / parser が読めていないのかを確認した。

結論は `BLOCK`。

現時点の保存artifactだけでは、Broker Positions API の raw response が本当に空だったとは確定できない。`.runtime/operations/broker_readonly_source/2026-07-03/tachibana_demo_snapshot.json` は raw response ではなく、`normalize_cash_positions()` / `normalize_margin_positions()` 後の sanitized snapshot である。このため、API raw row に有効な銘柄コード・数量キーが存在したが normalizer が拾えなかった可能性を排除できない。

## 読んだコード

- `src/ai_fund_lab_v2/broker/client.py`
- `src/ai_fund_lab_v2/broker/request_builder.py`
- `src/ai_fund_lab_v2/broker/normalizer.py`
- `src/ai_fund_lab_v2/broker/tachibana_broker_snapshot.py`
- `src/ai_fund_lab_v2/operations/broker_readonly.py`
- `src/ai_fund_lab_v2/broker/tachibana_positions_smoke.py`
- `src/ai_fund_lab_v2/broker/tachibana_codec.py`
- `tests/broker/test_broker_normalizer.py`
- `tests/broker/test_tachibana_phase10c_session_foundation.py`

## 読んだ資料 / artifact

- `docs/02_architecture/tachibana_readonly_api_design.md`
- `docs/phase_reports/phase10f_tachibana_positions_readonly_smoke.md`
- `docs/phase_reports/phase9r_c_tachibana_demo_portfolio_verification.md`
- `.runtime/operations/broker_readonly_source/2026-07-03/tachibana_demo_snapshot.json`
- `.runtime/operations/broker_snapshot/2026-07-03/broker_snapshot.json`
- `.runtime/operations/broker_snapshot_summary/2026-07-03/broker_snapshot_summary.json`
- `.runtime/operations/broker_readonly_reports/2026-07-03/broker_readonly_snapshot_report.json`
- `.runtime/operations/broker_positions/2026-07-03/positions.json`

## 1. Broker Positions API は本当に空か

未確定。

確認できた事実:

- `tachibana_demo_snapshot.json` の `health.positions.status` は `PASS`。
- `health.positions.count` は `12`。
- snapshot内の positions は `12` 行。
- 内訳は `CLMGenbutuKabuList/cash = 8`、`CLMShinyouTategyokuList/margin = 4`。
- ただし、保存されている positions は normalizer 後の schema であり、raw API response ではない。
- 12行すべてで `issue_code=""`、`quantity=0`、`market_value=0`。
- `broker_positions/2026-07-03/positions.json` は writer filter 後に `positions=[]`。

したがって、現在のartifactから言えるのは「normalizer後のPositions snapshotは12行あるが全て空/ゼロ」ということまで。raw APIが空だったのか、raw APIには別キーで値があったのかは判断できない。

## 2. 保存済みsnapshotで存在するキー名

raw responseは保存されていないため、以下は raw key ではなく、保存済みの normalized snapshot row のキーである。

```json
{
  "candidate_keys_observed_in_saved_snapshot": [
    "account_type",
    "as_of",
    "available_quantity",
    "average_price",
    "broker",
    "issue_code",
    "issue_name",
    "market_price",
    "market_value",
    "quantity",
    "raw_clmid",
    "raw_method",
    "raw_result_code",
    "source",
    "unrealized_pnl",
    "warnings"
  ]
}
```

値が入っていたもの:

- `account_type`
- `as_of`
- `broker`
- `raw_clmid`
- `source`
- `warnings`

全行で空またはゼロだったもの:

- `issue_code`
- `issue_name`
- `quantity`
- `available_quantity`
- `average_price`
- `market_price`
- `market_value`
- `unrealized_pnl`

## 3. normalizer が読もうとしているキー

`normalize_cash_positions()` は `positions`, `aGenbutuKabuList`, `aCLMGenbutuKabuList` をリスト候補として読む。

`normalize_margin_positions()` は `positions`, `aShinyouTategyokuList`, `aCLMShinyouTategyokuList` をリスト候補として読む。

各position rowでは主に以下を読む。

| normalized field | candidate keys |
|---|---|
| `issue_code` | `issue_code`, `sIssueCode`, `sMeigaraCode` |
| `issue_name` | `issue_name`, `sIssueName`, `sMeigaraName` |
| `quantity` | `quantity`, `sQuantity`, `sZanKabuSuu` |
| `available_quantity` | `available_quantity`, `sAvailableQuantity`, `sUritukeKanouSuu` |
| `average_price` | `average_price`, `sAveragePrice`, `sBokaTanka`, `sHeikinTanka` |
| `market_price` | `market_price`, `sMarketPrice`, `sGenzaine`, `sGenzaichi` |
| `market_value` | `market_value`, `sMarketValue`, `sHyokaGaku`, `sHyoukaGaku` |
| `unrealized_pnl` | `unrealized_pnl`, `sUnrealizedPnl`, `sHyokaSoneki`, `sHyoukaSoneki` |

一致率:

- raw responseとの一致率: 不明。raw key namesが保存されていないため。
- saved normalized snapshotとのkey presence: `issue_code` / `quantity` は 12/12 行で存在。
- saved normalized snapshotとのvalid value率: `issue_code` は 0/12、`quantity > 0` は 0/12。

重要なのは、`_items()` が top-level list key だけを見る実装であり、row内部の候補キーも固定列挙であること。Tachibana APIが別名キー、ネスト構造、またはcodec未登録キーで返した場合、現在のsnapshotではそれが失われる。

## 4. DemoではPositions APIが保有を返さない仕様か

コード・資料から確定できるのは以下。

- `request_builder.py` は現物保有に `CLMGenbutuKabuList`、信用建玉に `CLMShinyouTategyokuList` を使う。
- `tachibana_readonly_api_design.md` でも同CLMIDを Positions read-only endpoint として設計している。
- Phase10-Fでは、Demo positions smokeで response object は取得できたが positions list は空、raw responseは保存していない。
- Phase9r-cでは、Demo positions APIが7行の normalized rows を返したが全て empty placeholders だったと記録されている。

ただし、これらは「過去の初期状態または検証時にDemo Positionsが空/placeholderだった」根拠であり、「2026-07-03の約定後でもDemo Positions APIは保有を返さない仕様」とまでは確定できない。

今回のDay1では注文5件がWeb画面上で全部約定しているため、約定後にPositions APIがどう返すべきかは別問題。現artifactには raw key diagnosis がなく、仕様断定はできない。

## 5. positions=0 の原因分類

現時点の分類:

```text
BLOCK: normalizer / key mapping / API placeholder の切り分け不能
```

より細かい評価:

| 層 | 判定 | 根拠 |
|---|---|---|
| API仕様 | 未確定 | 過去資料ではDemo positions empty/placeholder実績あり。ただしDay1約定後も空仕様とは断定不可。 |
| API一時不具合 | 未確定 | `health.positions=PASS` で通信失敗ではないが、空placeholderを返した理由は不明。 |
| parser | REVIEW_REQUIRED | raw responseから normalized snapshotになる前のkey診断がない。 |
| normalizer | REVIEW_REQUIRED | candidate keyが限定され、raw key不一致を検出できない。 |
| key mapping | REVIEW_REQUIRED | raw key namesが保存されず、一致率を測れない。 |
| writer | 主原因ではない | writerは normalized row の `issue_code` と `quantity` を見て0件にfilterしており、現在の入力に対する挙動は妥当。 |
| broker_readonly | REVIEW_REQUIRED | `broker_readonly_source` という名前だが実体は normalized snapshot。raw-safe key diagnosisがfetch直後にない。 |
| Runtime | REVIEW_REQUIRED | `broker_positions=0` を現在保有0として扱うと、約定済み実態を消す危険がある。 |

## 6. Unified Ledgerへ進む前の判定

先に直すべきなのは Unified Ledger ではなく、Positions API / normalizer 境界の診断とkey mappingである。

理由:

- Broker Orders fallback projection は、Positions APIが本当に空である場合の補助策としては有効。
- しかし、API raw responseに有効なposition情報があるのに normalizer が落としているだけなら、fallback projectionは根本原因を隠す。
- Production Equivalent Runtimeでは Broker Positions / Broker Executions が正規SoTであり、Orders fallbackを本線SoTに昇格させる前に、Positions read-only pipelineを確定させる必要がある。

最小の次アクション:

1. `run_tachibana_broker_snapshot()` の `cash_response` / `margin_response` 取得直後、raw valueは保存せず、raw top-level keys、position list key hit、row key names、candidate key presence/countだけを safe diagnosis として保存する。
2. normalizer候補キーとraw row key namesの一致率をartifact化する。
3. 2026-07-03相当の約定後Demo口座で、Positions APIが本当に空placeholderを返すのかを再確認する。
4. raw keyが存在するのに未対応なら normalizer key mapping を修正する。
5. raw keyも値も無いことが確認できてから、Demo用 broker_orders fallback projection を review_required 付き補助経路として扱う。

## 今回修正していないこと

- 実装変更なし。
- Submit実行なし。
- Broker注文なし。
- Production接続なし。
- Production注文なし。
- artifact削除なし。
- notification送信なし。
- secret出力なし。
- raw response保存なし。

## 判定

`BLOCK`

理由:

2026-07-03 Day1の現在保有SoTが確定できていない。Broker Positions APIが本当に空なのか、normalizer/key mappingで落としているのかを現artifactから判定できないため、Unified Ledger / broker_orders fallback projection を本線実装へ進めると、Broker Positions pipelineの不具合を隠すリスクがある。
