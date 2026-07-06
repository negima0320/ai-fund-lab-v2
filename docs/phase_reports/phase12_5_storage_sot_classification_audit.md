# Phase12.5 Storage / SoT Classification Audit

作成日: 2026-07-04

## 判定

**BLOCK**

理由:

- 現在保有の設計上SoTは `broker_positions/YYYY-MM-DD/positions.json` だが、2026-07-03はBroker Orders上で5件 `全部約定` にもかかわらず `broker_positions=0`、`broker_executions=0`、`ledger.positions_count=0`。
- Demo日次リセット対策として `demo_ledger/` は存在するが、現状の永続状態は主に注文履歴・監視履歴であり、7/3の現在保有を再構成できるexecution/position履歴が入っていない。
- Approvalのcurrent exposureはBroker positionsが空の場合に `demo_ledger` / `submitted_orders` へfallbackするため、翌日Planで保有が完全に消えることは一部避けている。ただし、SELL候補生成・現在保有表示・Reconcileの正としてはBroker positions空が残る。
- Runtime Ledger (`ledger/YYYY-MM-DD`) はBroker read-onlyの派生日次集計であり、永続ポジション台帳ではない。`demo_ledger` と責務が近いが、どちらも現在保有の完全SoTにはなっていない。

## 読んだ対象

### Runtime artifact

- `.runtime/operations/demo_ledger/`
- `.runtime/operations/ledger/`
- `.runtime/operations/positions/`
- `.runtime/operations/broker_positions/`
- `.runtime/operations/broker_buying_power/`
- `.runtime/operations/broker_account_summary/`
- `.runtime/operations/order_plan/`
- `.runtime/operations/approval_artifact/`
- `.runtime/operations/submitted_orders/`
- `.runtime/operations/broker_snapshot/`
- `.runtime/operations/broker_orders/`
- `.runtime/operations/broker_executions/`
- `.runtime/operations/fill_events/`
- `.runtime/operations/reconciliation_result/`
- `.runtime/operations/reports/`
- `.runtime/operations/daily_report_refs/`
- `.runtime/operations/notifications/`

### コード / docs

- `src/ai_fund_lab_v2/operations/operations.py`
- `src/ai_fund_lab_v2/operations/demo_ledger.py`
- `src/ai_fund_lab_v2/operations/ledger.py`
- `src/ai_fund_lab_v2/operations/broker_readonly.py`
- `docs/operations/demo_daily_operation_runbook.md`
- Phase12 / Phase12.5関連SoTレポート

## 1. 永続状態として保持すべきもの

| 状態 | 現在の候補artifact | 現状分類 | 監査結果 |
|---|---|---|---|
| 現在保有 | Production: `broker_positions/YYYY-MM-DD/positions.json` / Demo補助: `demo_ledger/positions.jsonl` | 永続SoT未完成 | BLOCK。7/3はBroker Orders上は全部約定だがpositionsは0件。demo_ledgerにもposition履歴0件。 |
| 現金 / buying power | Production: `broker_buying_power/YYYY-MM-DD/buying_power.json`, fallback `broker_account_summary` / Demo評価資金: 100万円基準 | Broker日次SoT + Demo評価補正 | REVIEW_REQUIRED。7/3 buying_powerは `19,439,420`、Demo評価資金は100万円。用途分離はあるが、永続cash ledgerは薄い。 |
| 約定履歴 | Production: `broker_executions/YYYY-MM-DD/executions.json` / Demo補助: `demo_ledger/executions.jsonl` | 日次SoT + Demo横断履歴 | BLOCK。7/3 broker_executionsは0件、demo_ledger execution_history_countも0。Broker Orders fallbackを約定履歴SoTにはできない。 |
| 注文履歴 | `submitted_orders/YYYY-MM-DD`, `broker_orders/YYYY-MM-DD`, `demo_ledger/orders.jsonl` | 保持あり | PASS寄り。7/3 submitted_ordersは5件、broker_ordersも5件、demo_ledger order_history_count=5。 |
| lifecycle履歴 | `fill_events/YYYY-MM-DD`, `demo_ledger/events.jsonl`, `demo_ledger/order_status.jsonl` | 保持ありだが約定反映不足 | REVIEW_REQUIRED。7/3 fill_eventsは5件ACCEPTED、demo_ledger lifecycle_event_count=7。ただしFILLEDとしての永続反映はない。 |

## 2. 日次ログ / 証跡として保持するもの

| artifact | 分類 | 現状 |
|---|---|---|
| `order_plan/YYYY-MM-DD` | 日次Plan証跡 / 次回注文候補SoT | 2026-07-03はBUY 2件。現在保有・本日Submit結果ではない。 |
| `approval_artifact/YYYY-MM-DD` | 日次Approval証跡 / Submit許可SoT | 2026-07-03まで存在。Submit時は前営業日Plan/Approval参照を含む。 |
| `submitted_orders/YYYY-MM-DD` | 本日Submit実績SoT / 注文履歴日次証跡 | 2026-07-03は5件。2026-07-06ディレクトリは空。 |
| `broker_snapshot/YYYY-MM-DD` | Broker read-only snapshot派生証跡 | 2026-07-03は存在。 |
| `broker_orders/YYYY-MM-DD` | Broker受付・注文状態SoT | 2026-07-03は5件、全件 `全部約定`。 |
| `broker_executions/YYYY-MM-DD` | Broker約定の優先SoT | 2026-07-03は0件。ここが空なので約定確定はREVIEW_REQUIRED。 |
| `broker_positions/YYYY-MM-DD` | 現在保有の優先SoT | 2026-07-03は0件。現在保有SoTとして実態を反映できていない。 |
| `fill_events/YYYY-MM-DD` | Runtime lifecycle日次証跡 | 2026-07-03は5件ACCEPTED。FILLEDではない。 |
| `reconciliation_result/YYYY-MM-DD` | 日次照合結果SoT | 2026-07-03はREVIEW_REQUIRED。 |

## 3. 派生レポート

| artifact | 分類 | 備考 |
|---|---|---|
| `reports/YYYY-MM-DD` | 派生レポート | SoTではない。Report/Notification SoT混同は別修正済みだが、既存7/3 artifactは未再生成。 |
| `daily_report_refs/YYYY-MM-DD` | Report生成参照・派生metadata | SoTではない。Reportの入力関係を説明する派生証跡。 |
| `notifications/YYYY-MM-DD` | 通知送信結果証跡 | SoTではない。HTTP送信結果であり端末到達確認ではない。 |

## 現在保有のSource of Truth

設計上:

```text
Production: broker_positions/YYYY-MM-DD/positions.json
Demo補助: demo_ledger/positions.jsonl
```

現状:

- `broker_positions/2026-07-03/positions.json`: `positions=[]`
- `ledger/2026-07-03/ledger_state.json`: `positions_summary.count=0`
- `demo_ledger/state.json`: `position_history_count=0`
- `broker_orders/2026-07-03/orders.json`: 5件 `全部約定`

結論:

現在保有の実質SoTが成立していない。Broker Orders上は全部約定だが、positions/executions/durable position historyへ反映されていないため、現在保有を問われると0件扱いになる。

## 現在現金のSource of Truth

設計上:

```text
Production: broker_buying_power/YYYY-MM-DD/buying_power.json
fallback: broker_account_summary/YYYY-MM-DD/account_summary.json
Demo評価表示: 100万円評価資金基準
```

2026-07-03現状:

- `broker_buying_power/2026-07-03/buying_power.json`: `buying_power=19439420`, `cash_available=19439420`
- `broker_account_summary/2026-07-03/account_summary.json`: `buying_power=19439420`, `cash_available=17896820`
- `ledger/2026-07-03/ledger_state.json`: `cash_or_buying_power_summary.buying_power=19439420`
- Demo評価資金は `DEMO_OPERATION_INITIAL_EQUITY=1000000`

結論:

Broker buying powerは存在し、日次ledgerにも反映されている。ただしDemoの投資評価基準100万円とBroker実口座2,000万円系残高は用途分離が必要で、現在はapproval/guard側でDemo評価cashを使う分岐がある。

## demo_ledgerの分類

`demo_ledger/` は **Demo専用の永続横断履歴**。

目的:

- Tachibana Demoの日次リセットをまたぐ注文・監視・cash履歴の保持
- Broker snapshotで全量上書きしない
- 9000番台Demo Special Fill Simulation等のDemo固有履歴保持

現状のファイル:

- `orders.jsonl`: 5行
- `order_status.jsonl`: 2行
- `cash_history.jsonl`: 2行
- `events.jsonl`: 7行
- `broker_reset_events.jsonl`: 1行
- `state.json`

不足:

- `executions.jsonl` が現状存在しない、または実行履歴0
- `positions.jsonl` が現状存在しない、またはposition履歴0
- 7/3の実保有を永続状態として再構成できない

## Runtime Ledgerとdemo_ledgerの責務重複

### Runtime Ledger

`ledger/YYYY-MM-DD` は `write_operations_ledger_from_broker_readonly()` により、Broker read-only artifactsから作る **日次派生集計**。

特徴:

- source: `broker_readonly_snapshot`
- `broker_source_of_truth=true`
- AI training input禁止
- 日付フォルダ配下で日次完結

### demo_ledger

`demo_ledger/` は日付フォルダ外にある **Demo専用永続履歴**。

特徴:

- jsonl append型
- Demo resetをまたぐ
- Broker snapshotで上書きしない

### 重複評価

責務は理論上分かれているが、実装上は次の重複・穴がある。

- Runtime Ledgerも注文/約定/保有/cash summaryを持つ。
- demo_ledgerも注文/約定/保有/cash履歴を持つ設計。
- しかし7/3の現在保有はどちらにも入っていない。
- Approval current exposureは `broker_positions -> demo_ledger -> submitted_orders` のfallbackを使い、保有SoTとは別の推定経路を持つ。

結論:

重複よりも、**現在保有の永続正規状態がどこにも確定していない**ことが大きい。

## 日付フォルダだけで翌日Planの保有が消えるリスク

リスクあり。

根拠:

- `broker_positions/YYYY-MM-DD` は日次snapshotであり、Demoでは日次リセットやAPI parse不整合で0件になり得る。
- `ledger/YYYY-MM-DD` も日次派生で、Broker positionsが0ならpositions_count=0。
- `demo_ledger` は横断履歴だが、7/3時点ではposition/execution履歴がない。
- Approval exposureだけはsubmitted_orders fallbackで買い建て相当を拾えるが、SELL候補生成・保有表示・position quantity guardには十分でない。

つまり、翌日Planで「保有がない」扱いになる経路が残る。

## Production本番でSoTにすべき状態

Productionでは以下をSoTにすべき。

| 対象 | Production SoT |
|---|---|
| 現在保有 | Broker Positions API -> `broker_positions/YYYY-MM-DD/positions.json` |
| 現金 / 買付余力 | Broker Buying Power / Account Summary -> `broker_buying_power`, `broker_account_summary` |
| 注文履歴 | Submit artifact + Broker Orders。最終的なBroker状態はBroker Orders |
| 約定履歴 | Broker Executions API -> `broker_executions/YYYY-MM-DD/executions.json` |
| lifecycle履歴 | `fill_events` はRuntime解釈。Broker SoTを上書きしない |
| 日次Ledger | Broker read-onlyからの派生集計。永続正規台帳ではなく監査・表示用 |

Productionでは `demo_ledger` を現在保有・現金のSoTにしてはいけない。

## Demo固有補正が本線Ledgerに混ざっていないか

一部混ざるリスクあり。

- `ledger/YYYY-MM-DD` 自体はBroker read-only派生で、Demo補正を直接混ぜていない。
- しかしDaily ReportではDemo表示用に同日filled orderからsynthetic positionを作る処理がある。
- ApprovalではDemo時に `demo_evaluation_cash`、`persistent_demo_ledger`、`submitted_accepted_buy_exposure` fallbackを使う。
- Demo Special Fill Simulationは `demo_ledger` に入り、performance metrics excludedを明示している。

結論:

本線Ledger自体への混入は限定的。ただし、approval exposure・report表示・demo_ledger履歴でDemo補正が横断的に使われるため、責務境界をもっと明文化しないとProduction Equivalentの監査で誤解を招く。

## 最小修正候補

今回は修正していないが、BLOCK解消には最低限以下が必要。

1. Broker Orders fallbackを使う場合でも、`broker_executions`とは別分類で永続的な `review_required_position_state` または `demo_ledger` position projectionを残す。
2. `demo_ledger` に現在保有を再構成できるposition stateを持たせる。ただしProduction SoTとは明確に分離する。
3. SELL候補生成・Report・Approval exposureが参照する「Demo current holdings projection」を明示し、Broker positionsが空の場合にただ0件扱いしない。
4. Productionでは必ずBroker Positions / Executionsを正とし、Demo fallbackは無効化または明示的にDemo専用分類へ閉じる。
5. `ledger/YYYY-MM-DD` は日次派生集計、`demo_ledger/` はDemo永続履歴という責務をschemaに明記する。

## 今回修正していないこと

- 実装変更なし
- artifact削除なし
- artifact再生成なし
- Submit実行なし
- Broker注文なし
- Production接続なし
- notification送信なし
