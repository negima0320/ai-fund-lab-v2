# Phase8-C7 moomoo SIMULATE Account Investigation

## 1. Purpose

This investigation checks whether moomoo JP / OpenD / OpenAPI can expose a SIMULATE account for Phase9 validation.

Scope is read-only investigation only.

Prohibited:

```text
live order
auto order
REAL order test
place_order
place_combo_order
modify_order
cancel_order
unlock_trade
trade unlock
OpenD automatic startup
automatic login/logout
secret persistence
raw response persistence
plain account id persistence
```

## 2. Sources Reviewed

Official sources:

```text
https://www.moomoo.com/jp/support/topic7_474
https://openapi.moomoo.com/moomoo-api-doc/jp/intro/intro.html
https://openapi.moomoo.com/moomoo-api-doc/en/intro/intro.html
```

Local SDK:

```text
moomoo-api 10.07.6708
moomoo.TrdEnv.REAL = REAL
moomoo.TrdEnv.SIMULATE = SIMULATE
moomoo.TrdMarket.JP = JP
OpenSecTradeContext(filter_trdmarket='HK', host='127.0.0.1', port=11111, ...)
```

Current sanitized runtime report:

```text
reports/phase_reports/phase8c_moomoo_readonly_smoke_result.json
```

## 3. Official Information Summary

The moomoo JP support page states that Moomoo API provides quote and trade APIs and that users must agree to the Moomoo API terms before using it. It also states that live trading and demo trading use the same trading API.

The Japanese OpenAPI introduction page lists trading capacity by market and account region. In that table:

```text
Japanese Market Stocks, ETFs, REITs
Paper Trading: X
Moomoo JP live trading: supported
```

The English OpenAPI introduction page shows the same structure:

```text
Japanese Market Stocks, ETFs, REITs
Paper Trading: X
Moomoo JP live trading: supported
```

The docs also state that the API supports simulated trading in multiple markets, but the trading capacity table is market-specific. For JP stocks / ETFs / REITs, the table indicates paper trading is not supported.

## 4. SDK Specification Summary

Observed SDK signatures:

```text
get_acc_list(self)
accinfo_query(self, trd_env='REAL', acc_id=0, acc_index=0, refresh_cache=False, currency='HKD', asset_category='N/A')
position_list_query(self, code='', ..., trd_env='REAL', acc_id=0, ..., currency='USD', ...)
order_list_query(self, ..., trd_env='REAL', acc_id=0, ...)
history_order_list_query(self, ..., trd_env='REAL', acc_id=0, ...)
```

Implications:

```text
TrdEnv.SIMULATE exists in the SDK.
Trade query methods can receive trd_env=SIMULATE.
SDK defaults are REAL, so AI Fund Lab must continue to pass trd_env explicitly.
get_acc_list has no trd_env argument, so SIMULATE discovery depends on what OpenD returns.
```

SDK examples include SIMULATE references:

```text
macd_strategy.py: trade_env = ft.TrdEnv.SIMULATE
stocksell_demo.py: trd_env = ft.TrdEnv.SIMULATE
```

No SDK example found in the installed package demonstrated a JP SIMULATE account with `OpenSecTradeContext(filter_trdmarket=JP)`.

## 5. Phase8-C7 Read-only Measurement

Command:

```text
AI_FUND_LAB_MOOMOO_READONLY_SMOKE=1 \
python3 scripts/smoke_moomoo_readonly_phase8c.py \
  --run-readonly-smoke \
  --trd-env SIMULATE \
  --runtime-dir .runtime \
  --reports-dir reports/phase_reports
```

Result:

```text
status = FAILED_READONLY_METHOD
selected_trd_env = SIMULATE
get_acc_list = SUCCESS
account_selection = FAILED
ret_code = NO_MATCHING_ACCOUNT
raw_payload_saved = false
secret_saved = false
snapshot_paths = []
```

Sanitized account discovery:

```text
row_count = 1
trd_env_counts = REAL: 1
account_type_counts = CASH: 1
selected_candidate_count = 0
selection_rule = require_explicit_trd_env_match
field_names include sim_acc_type
```

Interpretation:

```text
OpenD currently exposes only a REAL account in get_acc_list.
The presence of sim_acc_type is not enough to classify the account as SIMULATE.
AI Fund Lab correctly refused to treat the REAL account as SIMULATE.
No SIMULATE read-only query after account selection was executed.
No normalized SIMULATE snapshot was written.
```

## 6. Judgment

Classification:

```text
B. SIMULATE account/API appears available in the SDK, but JP stocks / ETFs / REITs appear outside the OpenAPI paper trading scope.
```

Rationale:

```text
Official OpenAPI trading capacity table marks Japanese Market Stocks, ETFs, REITs as Paper Trading = X.
Moomoo JP live trading for the same row is supported, which matches the successful REAL read-only sync.
SDK exposes TrdEnv.SIMULATE, but get_acc_list under JP context did not expose a SIMULATE account.
Read-only measurement showed only REAL/CASH.
```

Residual uncertainty:

```text
SIMULATE may still be usable through OpenAPI for non-JP markets such as US.
The official support page has app-level demo trading help entries, but this investigation did not confirm JP OpenAPI SIMULATE availability.
moomoo support confirmation is recommended before making Phase9 dependent on JP SIMULATE.
```

## 7. Phase9 Recommendation

Near-term Phase9 should not assume JP SIMULATE Broker Sync is available.

Recommended priority:

```text
1. Ask moomoo support whether moomoo JP OpenAPI supports SIMULATE for JP stocks / ETFs / REITs.
2. If unsupported, use AI Fund Lab paper ledger as the primary JP dry-run environment.
3. Optionally evaluate SIMULATE read-only for US market separately with filter_trdmarket=US.
4. Keep REAL usage read-only until SIMULATE or internal paper-ledger validation is sufficient.
```

Phase8-H completion status remains:

```text
Phase8 Order Manager: PASS
moomoo REAL read-only Broker Sync: PASS
moomoo SIMULATE Broker Sync: NOT_READY
Phase8 Overall: COMPLETE_WITH_SIMULATE_PENDING
```

## 8. Support Inquiry Draft

件名:

```text
moomoo OpenAPIにおけるSIMULATE / デモ取引口座の利用可否について
```

本文:

```text
moomoo証券サポートご担当者様

お世話になっております。
moomoo OpenD / moomoo OpenAPI（Python SDK）を利用した検証について確認させてください。

現在、OpenDにログインした状態で OpenSecTradeContext(filter_trdmarket=JP) を作成し、
get_acc_list / accinfo_query / position_list_query / order_list_query / history_order_list_query
のread-only APIを確認しています。

REAL口座では以下のread-only APIが正常に利用できることを確認済みです。
- get_acc_list
- accinfo_query
- position_list_query
- order_list_query
- history_order_list_query

一方、TrdEnv.SIMULATE を指定して検証したところ、get_acc_list の返却では trd_env=REAL の口座のみが表示され、
SIMULATE口座が見つからず、以降の照会は実行していません。

以下についてご教示いただけますでしょうか。

1. moomoo証券JPのOpenAPIで、SIMULATE / デモ取引口座は利用できますか？
2. 日本株・ETF・REITについて、TrdEnv.SIMULATEで注文・約定テストはできますか？
3. get_acc_listでSIMULATE口座を返すには、アプリまたはOpenD側で何らかの有効化手順が必要ですか？
4. OpenDの設定、ログイン状態、取引市場 filter_trdmarket などに必要な指定はありますか？
5. get_acc_listでREAL口座しか返らない場合、想定される原因は何でしょうか？
6. もし日本株・ETF・REITがOpenAPIのSIMULATE対象外の場合、米国株など別市場ではSIMULATE検証が可能でしょうか？

なお、現時点では実発注や取引ロック解除は行わず、read-only確認のみを行っています。

よろしくお願いいたします。
```
