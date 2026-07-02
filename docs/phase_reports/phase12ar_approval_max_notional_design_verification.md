# Phase12-AR Approval Max Notional Design Verification

## 目的

2026-07-02 Demo運用で `approval.max_notional=600000` により、23930 / 2393 日本ケアサプライが `remaining_approval_budget_insufficient` でItem単位BLOCKされた。

今回は実装変更を行わず、`approval.max_notional=600000` が設計どおりの値なのか、暫定値なのかを確認した。

Demo注文、Production注文、AI再学習、Backtest、コード変更は実施していない。

## 結論

`approval.max_notional=600000` は、現在のOperations auto approvalに入っている固定の運用上限値である。

由来は以下。

- `scripts/run_approval_prepare.py` の `--max-notional` default: `600000`
- `scripts/run_demo_daily_operation.py` の `--auto-approval-max-notional` default: `600000`
- `tools/launchd/com.aifundlab.operations.auto_approval.plist` の `--max-notional 600000`
- Phase12-O/P/S/W/Y以降のDemo wire retry系レポートで、単発Demo注文を通すためのApproval上限として `600000` が使われている

一方、Phase7 / Phase11 / Phase12設計全体では、資金配分や最大エクスポージャは資産に連動する方針であり、`600000` を恒久的な資産連動上限として定義した記述は確認できなかった。

したがって、`600000` はProduction-equivalentな最終設計値ではなく、Phase12 Demo auto approvalの暫定的な固定ガード値と見るのが妥当。

## 設計書で確認した内容

### Phase7 Capital Allocation

Capital Allocationの基本責務は「いくら買うか」を決めること。

基本設計では以下が明記されている。

- 最大保有数: 5銘柄
- 均等配分: 保有枠数で均等割り
- 資産100万円 / 最大保有5銘柄なら、1銘柄20万円
- Phase7-A default:
  - initial_total_assets: 1,000,000
  - cash_buffer_ratio: 0.05
  - max_position_weight: 0.20
- Phase7 final policy:
  - cash_buffer_ratio: 5%
  - max_position_weight: 20%

つまりPhase7側の設計では、1銘柄あたりの目安は資産の20%であり、資産に応じて増減する。

### Phase11 MAX_EXPOSURE

Phase11 Fix-H以降、MAX_EXPOSUREは固定85万円capではなく、equity-linked設計へ修正済み。

設計式:

```text
max_allowed_exposure = base_equity * max_total_exposure_ratio
max_total_exposure_ratio = 0.85
```

Demo / Productionでは、base equityはPaper Ledgerではなく、Broker actual equity / buying_power basisに接続する方針。

### Phase12 Operations

Operations runbookには以下がある。

```text
max_buy_orders_per_day=5
max_new_positions_per_day=5
max_positions=5
max_total_exposure_ratio=0.85
```

また、Operations daily planではCapital Allocation AIのfull接続はまだ deferred と明記されている。

```text
Capital Allocation AI is not fully connected to Operations daily plan yet.
full Capital Allocation AI connection is deferred to Phase13 or the next design phase.
```

## 現在の実装確認

### Approval Prepare

`run_approval_prepare(...)` は引数 `max_notional` をそのまま `approval.max_notional` に保存する。

```text
max_notional default = 0 in function
scripts/run_approval_prepare.py default = 600000
launchd auto_approval = --max-notional 600000
```

auto demo approvalでは、以下のチェックを行う。

- `max_notional <= 0` ならBLOCK
- 各BUY item notional > max_notional ならBLOCK
- total_buy_notional > max_notional ならBLOCK
- total_buy_notional > buying_power ならBLOCK

### Demo Submit

Submit時は `approval.max_notional` を累積予算として扱う。

```text
remaining_approval_budget = approval.max_notional
accepted BUY itemごとに remaining_approval_budget を減算
item expected_notional > remaining_approval_budget なら BLOCKED_ITEM
```

このため、2026-07-02の23930 blockは現在実装どおり。

## 2026-07-02 の23930 block評価

2026-07-02の値:

- approval.max_notional: 600,000円
- accepted先行3件: 45,600 + 60,000 + 199,000 = 304,600円
- 23930 expected_notional: 429,500円
- 23930直前の残Approval budget: 295,400円
- 23930を加えた場合: 734,100円
- 超過: 134,100円

したがって、現行実装では23930のBLOCKは設計どおり。

ただし、その「設計」とは、資産連動の最終Capital Allocation設計ではなく、固定600,000円のauto approval guardに基づく設計である。

## max_total_exposure_ratio=0.85 との関係

`max_total_exposure_ratio=0.85` は、総エクスポージャ上限である。

初期資産100万円なら:

```text
max_allowed_exposure = 1,000,000 * 0.85 = 850,000円
```

一方、`approval.max_notional=600000` はApproval単位の累積発注許可額であり、MAX_EXPOSUREとは別の上限として機能している。

そのため、現状では以下の2段階ガードになっている。

```text
approval.max_notional = 600,000
max_allowed_exposure = 850,000
```

この構成では、MAX_EXPOSUREに余裕があっても、Approval予算で先に止まる。

## 初期資産100万円の場合の設計上の目安

設計思想ごとに値が異なる。

### Phase11 MAX_EXPOSURE基準

```text
total exposure cap = 850,000円
```

### Phase7 equal-weight / max_position_weight基準

```text
1銘柄上限 = 1,000,000 * 0.20 = 200,000円
5銘柄合計 = 1,000,000円
cash buffer 5%後の利用可能目安 = 950,000円
```

ただし、MAX_EXPOSURE 85%を同時に使うなら、総投資上限は850,000円。

### 推奨されるApproval Max

Approval Maxを「その日の全BUY累積上限」として使うなら、100万円開始時は以下が自然。

```text
min(
  broker/evaluation equity * max_total_exposure_ratio,
  buying_power,
  capital_allocation_total_buy_budget
)
= min(850,000, buying_power, capital_allocation_total_buy_budget)
```

Capital Allocationが未接続なら、少なくともDemo評価資産100万円を基準に `850,000円` を上限候補にする方が、Phase11 MAX_EXPOSURE設計とは整合する。

一方、1銘柄ごとのサイズはPhase7基準で `200,000円` 程度を目安にするのが自然。

## 資産増加時の考え方

固定600,000円のままだと、資産増加時に資金活用率が下がる。

| 評価資産 | MAX_EXPOSURE 85% | Phase7 1銘柄20% | 固定600,000の意味 |
| ---: | ---: | ---: | --- |
| 1,000,000 | 850,000 | 200,000 | exposure capの約70.6% |
| 1,500,000 | 1,275,000 | 300,000 | exposure capの約47.1% |
| 2,000,000 | 1,700,000 | 400,000 | exposure capの約35.3% |

将来のProduction-equivalent設計では、Approval Maxは固定600,000ではなく資産に応じて増えるべき。

## Capital Allocationとの整合

現状のOperations order_planは5候補を出すが、Capital Allocation AI full接続は未完了。

そのため、以下のズレが残っている。

- BUY候補数はProduction-equivalentに5件へ戻った
- ただし、各銘柄の資金配分はPhase7 Capital Allocationの20% weight設計に接続されていない
- Approval MaxはCapital Allocationの出力ではなくCLI/launchd固定値
- Submit時に正規化されたnotionalの累積が600,000を超えるとitem blockされる

23930のblockはこのズレが可視化されたもの。

## 判定

| 確認項目 | 判定 |
| --- | --- |
| `approval.max_notional=600000` の由来 | CLI / launchd / Phase12 Demo wire retryの固定値 |
| 設計どおりか | 現行実装どおり |
| 恒久設計か | いいえ。暫定ガード値 |
| MAX_EXPOSUREとの整合 | 不完全。600,000が85% capより先に効く |
| Capital Allocationとの整合 | 不完全。Capital Allocation full接続はdeferred |
| 23930 block | 現行固定Approval設計では正しい |
| 修正必要性 | 次フェーズで必要 |

## 推奨案

Phase12-AS以降で、実装前に以下を設計することを推奨する。

1. `approval.max_notional` を固定値ではなく日次動的値にする。
2. Demoでは、証券Demoの2,000万円ではなくPersistent Demo Ledger / evaluation equityの100万円基準を使う。
3. Productionでは、Broker actual equity / buying_powerを使う。
4. 日次Approval Maxは以下のように定義する。

```text
approval_max_notional =
min(
  equity_basis * max_total_exposure_ratio - current_exposure,
  buying_power_or_demo_cash,
  capital_allocation_total_buy_budget
)
```

5. 1銘柄あたりの上限はPhase7の `max_position_weight=0.20` を使う。
6. Capital Allocation未接続の間は、暫定ルールとして `max_position_weight` と `max_total_exposure_ratio` をOperations runtime configへ明示する。
7. Approval artifactには、固定/動的の区別、equity_basis、calculation_formula、capital_allocation_connectedを記録する。

## 禁止事項確認

- 実装変更: 未実施
- Demo注文: 未実施
- Production注文: 未実施
- LINE/Discord実送信: 未実施
- AI再学習: 未実施
- Backtest: 未実施
- raw request / raw response保存: 未実施
- secret保存: 未実施
