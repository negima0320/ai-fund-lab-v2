# Phase12.5 Replacement Logic Audit

作成日: 2026-07-03

## Scope

今回は確認のみ。実装変更、Submit実行、Broker注文、Production接続、artifact削除・再生成、launchd変更、通知送信、AI再学習、フルバックテストは行っていない。

## 読んだコード・資料

- `src/ai_fund_lab_v2/operations/operations.py`
- `src/ai_fund_lab_v2/operations/exit_adapter.py`
- `src/ai_fund_lab_v2/operations/market_refresh.py`
- `src/ai_fund_lab_v2/operations/guards.py`
- `docs/operations/demo_daily_operation_runbook.md`
- `src/ai_fund_lab_v2/capital_allocation_ai/phase7e_strict_backtest.py` は `rg` 上でReplacement検証ロジックがあることのみ確認

## SELL候補生成ロジック

Operations Runtime本線のSELL候補は `run_daily_plan()` から `_generate_sell_items()` を呼び、`.runtime/operations/positions/YYYY-MM-DD/positions.json` を入力にして生成される。

生成関数:

- `run_daily_plan()`:
  - `_generate_sell_items(paths, trade_date)` を呼ぶ
  - BUY候補とSELL候補を同じ `order_plan.items` に結合する
- `_generate_sell_items()`:
  - `positions/YYYY-MM-DD/positions.json` がなければ空配列で `generate_sell_items_from_positions()` を呼ぶ
  - `positions` が不正なら `BLOCK`
  - 正常なら `generate_sell_items_from_positions()` に委譲
- `generate_sell_items_from_positions()`:
  - 各positionを正規化
  - `_classify_exit()` で `EXIT` / `REDUCE` / fallback stop / HOLD を判定

SELL理由:

- 明示的な `exit_action=EXIT` または `action=SELL`
- 明示的な `exit_action=REDUCE`
- fallback hard stop: `unrealized_return <= -0.08`
- 上記に該当しなければ `HOLD`

Position AI / Exit AI / Safety Guard / fallback の扱い:

- 現在のOperations本線では、SELL生成は `positions` artifactの `exit_action` / `action` / `exit_reason` とfallback hard stopで決まる。
- `exit_source` は `positions` artifact側の値または `"fallback"` が入る。
- Safety GuardはApproval/Submitのブロック条件として使われるが、Candidate比較によるSELL理由生成には使われていない。
- `ExitAdapterResult` には `ai_training_input_used=False` が明示されており、学習入力やPaper ledgerは使わない設計。

Daily PlanでSELL候補が出る条件:

- `positions/YYYY-MM-DD/positions.json` が存在し、各positionに必要な `code` / `quantity` / `current_price` / `entry_price` / `position_id` がある。
- そのpositionが明示Exit/Reduce、または `unrealized_return <= -8%` に該当する。

保有銘柄がない場合:

- `positions` artifactが存在しない、または `positions=[]` の場合、`sell_item_count=0` は正常。

## BUY候補生成ロジックとの関係

BUY候補は `load_feature_buy_candidates()` が `feature_refresh/YYYY-MM-DD/latest_features.json` の `candidate_feature_path` を読み、`candidate_features.parquet` から生成する。

BUY選定:

- `universe_eligible=True` で絞る
- `price_momentum_return_20d`, `price_momentum_return_5d`, `liquidity_avg_volume_20d` で降順ソート
- `max_buy_orders_per_day` と候補プール上限に従ってBUY item化
- その後、Daily Plan側の予算フィルタでlatest closeを使い、BUY notionalを `approval_max_notional` 内に収める

SELL候補とBUY候補の結合:

```text
combined_items = plan_items + feature_buy.buy_items + exit_result.sell_items
```

つまり通常経路ではBUY候補が先、SELL候補が後に並ぶ。

## Replacement判断の有無

結論: Operations Runtime本線には、保有銘柄と新規BUY候補を比較して「より良い候補があるから保有を売る」Replacement判断は実装されていない。

確認したこと:

- 保有銘柄のscoreと新規BUY候補のscoreを比較する処理はOperations本線にない。
- Candidate AI Top候補と現在保有銘柄を比較し、低スコア保有を売る処理はない。
- SELLはExit条件とfallback hard stopで生成され、BUY候補とは独立している。
- Phase7 / Capital Allocation側には `should_replace()` 等のReplacement検証コードが存在するが、Phase12.5 Operations Daily Planへは接続されていない。

## max_positions / 現金余力 / SELL予定の扱い

`max_positions=5` はOperations runtime configとFeature BUY adapter metadataに存在する。

ただし、Daily Plan本線で以下を直接計算してBUY数を制御する処理は確認できない。

```text
current_positions_count - planned_sell_count + planned_buy_count <= max_positions
```

現状の制御:

- BUY件数は `max_buy_orders_per_day=5` が主制約。
- BUY notionalはDaily Plan budget filterとApproval/Submitで制約される。
- SELL予定額はBUY予算に加算しない。
- SELL予定による「枠空け」をBUY候補数に反映する明示処理はない。
- Submit時はBroker buying powerとApproval残枠でBUYをブロックするため、SELL未約定の資金を前提にBUYすることはない。

## BUYとSELLの実行関係

現在の共通Submitは `order_plan.items` を順に処理する。

通常Daily Planでは `BUY候補 + SELL候補` の順で `combined_items` を作るため、SELL先行Submitではない。

ただし、BUY資金計算はSELL予定額に依存していないため、SELLが未約定でもSELL予定資金を使ったBUYが出る設計ではない。

## ケース別挙動

### ケースA

条件:

- 5銘柄保有
- 現金ほぼなし
- 新規候補に高スコア銘柄が出た

現状挙動:

- 既存銘柄を「高スコア新規候補があるから」という理由では売らない。
- Exit条件に該当する保有がなければSELL候補は出ない。
- BUY候補は候補生成上は出る可能性があるが、Daily Plan budget / Approval / Submitの買付余力で除外またはBLOCKされる。
- 実運用上は何も買えない、またはBUY候補0/縮小になる可能性が高い。

### ケースB

条件:

- 5銘柄保有
- 1銘柄がExit条件に該当
- 新規候補がある

現状挙動:

- Exit条件に該当した1銘柄はSELL候補になる。
- BUY候補も独立に生成される。
- ただしSELL予定額はBUY予算に加算しない。
- SELL約定後の資金を同日BUYに使う二段階Replacementはない。
- BUYは当日朝Submit時点のBroker buying power / Approval残枠で通る場合のみ実行される。売却資金反映後の買い替えは最短でも翌営業日以降のartifact/ledger反映を待つ扱い。

### ケースC

条件:

- 3銘柄保有
- 現金あり
- 新規候補がある

現状挙動:

- BUY候補は出る。
- BUY件数は `max_buy_orders_per_day=5` と予算制約で選ばれる。
- ただし `現在3保有なので最大2件だけ買う` という `max_positions=5` 由来の直接制御は確認できない。
- Broker buying powerとApproval上限の範囲内で複数BUYが出る可能性がある。

## 現状の結論

該当分類:

```text
SELLはExit条件のみで、Replacement判断は未実装
BUY/SELLは独立しており、「良い候補があるから売る」は未実装
```

一部補足:

- Phase7 / Capital Allocation AIにはReplacement検証・バックテストコードが存在する。
- しかしPhase12.5 Operations RuntimeのDaily Planには接続されていない。
- Phase12.5のProduction Equivalent Runtime Acceptanceとしては、「Replacement未実装」を既知制約として明示するのが妥当。

## Phase12.5で直すべきか

原則としてPhase13以降の課題にするべき。

理由:

- Replacementは新しい売買判断ロジックであり、Phase12.5の目的であるProduction Equivalent Runtime Acceptanceを超える。
- SELL_FIRST_BUY_AFTER_FILL、約定後Broker buying power再取得、max_positions、turnover制約、minimum holding days、replacement edge marginなどをまとめて設計する必要がある。
- Phase12.5で入れるなら、実装ではなくReport/Audit上の明示が適切。

Phase12.5中に必要な最小対応候補:

- Daily Plan / Report / Auditで「Replacement比較は未接続」と明示する。
- `max_positions` がmetadataのみで、現在保有数ベースのBUY件数制御ではないことをReview項目にする。

## 今回は修正していないこと

- コード修正なし
- Submit実行なし
- Broker注文なし
- Production接続・Production注文なし
- artifact削除・再生成なし
- launchd変更なし
- notification送信なし
- AI再学習なし
- フルバックテストなし
