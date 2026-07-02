# Phase12-A Demo Full Operation Design / Preflight Plan

作成日: 2026-06-29

## Status

```text
PHASE12A_DEMO_FULL_OPERATION_DESIGN_COMPLETE
DESIGN_ONLY
NO_DEMO_ORDER_EXECUTION
NO_PRODUCTION_ORDER_EXECUTION
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED_FOR_PRODUCTION
```

## 1. Phase12の目的

Phase12 は `Demo Full Operation Validation` である。

目的は、Production Runtime と同じ運用フローを立花証券デモ環境で実際に回し、30営業日連続で安定稼働できることを確認することである。

Phase12-A の範囲は設計のみとする。Demo注文、Production注文、LINE実送信、Runtime変更、AI再学習、Full Backtest再実行は行わない。

Phase12全体の完了イメージ:

- Demo環境で Production Runtime 相当の state flow を運用する。
- Broker Snapshot / Positions / Orders / Executions を Broker Source of Truth として扱う。
- Safety Layer は投資判断ではなく System Guard として機能させる。
- Order Plan から Demo注文までの Approval Flow を実地運用する。
- Fill Monitor と Reconciliation を毎営業日行う。
- Blog / Public Report / LINE Payload を生成する。
- 30営業日の監査で PASS 条件を満たす。

## 2. Demo Runtime全体構成

Phase12 Demo Runtime は Production Runtime の rehearsal である。Productionとの差分は broker environment と発注先だけであり、運用順序、Safety、Approval、Reconciliation、Report の考え方は Production と同一に寄せる。

```text
J-Quants Market Data

↓

AI Inference

↓

Order Plan

↓

Broker Snapshot / Positions / Orders / Executions

↓

Safety Preflight

↓

Approval

↓

Demo Order

↓

Fill Monitor

↓

Demo Broker Snapshot

↓

Ledger

↓

Reconciliation

↓

Safety Report

↓

Blog

↓

Public Report

↓

LINE Payload
```

### Production Runtimeとの差分

| 項目 | Demo Runtime | Production Runtime |
|---|---|---|
| broker environment | 立花証券 demo | 立花証券 production |
| 注文 | Demo注文のみ許可 | 引き続き禁止 |
| production unlock | 禁止 | 禁止 |
| source of truth | Demo Broker | Production Broker |
| sizing | evaluation capital と demo buying_power の両方で制約 | broker actual cash / buying_power |
| Safety | 同一ロジック | 同一ロジック |
| Approval | Human Approval または Demo Approval 必須 | Production Approval 未解禁 |
| LINE | payload生成のみ | payload生成のみ |
| AI学習 | 禁止 | 禁止 |
| raw response保存 | 禁止 | 禁止 |

### Phase12で許可する操作

- Demo Broker Snapshot取得
- Demo Position取得
- Demo Order取得
- Demo Execution取得
- Demo注文送信
- Demo約定確認
- Fill Monitor
- Reconciliation
- Safety Check
- Approval Flow
- Blog生成
- Public Report生成
- LINE Payload生成

### Phase12で禁止する操作

- Production注文
- Production Unlock
- 信用取引
- 自動復帰
- 無条件自動売却
- LINE実送信
- AI再学習
- Full Backtest再実行
- Secrets平文保存
- Raw Response保存

## 3. 日次運用フロー

Phase12では、前営業日の引け後に翌営業日の候補と Order Plan を準備し、翌営業日寄付き前に Preflight / Safety / Approval / Demo注文を行う。

### 引け後 15:40-17:30

目的: 当日 broker state を確定し、翌営業日の計画入力を作る。

- Demo Broker Snapshot取得。
- Positions / Orders / Executions / Buying Power取得。
- Broker Snapshotを redacted normalized artifact として保存。
- Ledger更新候補を作成する。ただし Broker actual state と矛盾する更新は fail closed。
- Reconciliation preliminary check を実行する。
- J-Quants由来データだけを AI 推論入力として確認する。
- AI推論を実行する。
- Order Planを生成する。
- Order Planは `requires_approval=true`、`environment=demo`、`production_order_allowed=false` を必須にする。

### 夜 19:00-21:00

目的: 人間が確認できる形で翌営業日の計画とレビュー材料を生成する。

- Safety preliminary check。
- Human Review Queue生成。
- Blog draft生成。
- Public Report生成。
- LINE Payload生成。
- LINE実送信は行わない。
- Approval候補を `.runtime/production_runtime/approvals/` 相当の Phase12 namespace に保存する。

### 翌営業日寄付き前 08:25-08:55

目的: 発注直前の broker state を正として、発注可否を最終判定する。

- Business Day Guard。
- Run Lock取得。
- Preopen Demo Broker Snapshot取得。
- Positions / Orders / Executions / Buying Power取得。
- stale snapshot / duplicate active order / position mismatch / cash violation / secret or raw persistence suspicion を確認。
- MAX_EXPOSUREを Demo Broker actual equity または buying_power basis で評価する。
- Safety Preflightを実行する。
- Approval artifactの有効性を検証する。
- Demo Approvalがない注文は送信しない。
- Safety `BLOCK` / `SYSTEM_EMERGENCY_STOP` は発注禁止。
- `NON_BLOCKING_REVIEW` は通知・レビュー対象に残すが、Human Approval済みで System fault がなければ Demo送信候補として扱う。

### 寄付き直前 08:50-09:00

目的: 承認済み・安全確認済みの注文だけを Demo 環境へ送信する。

- Demo-only guardを通過した注文だけ送信。
- 現物のみ。
- 信用取引は禁止。
- Production endpoint / Production credentials / Production second password は使用禁止。
- 注文結果は normalized / redacted のみ保存。
- plaintext order number、raw request、raw response、second password、account id は保存しない。

### 寄付き後 09:05-10:30

目的: 受付・約定・未約定を追跡する。

- Fill Monitorを実行する。
- Broker Orders / Order Detail / Executions / Positionsを確認する。
- `SUBMITTED / WAITING_FILL / PARTIALLY_FILLED / FILLED / REJECTED / EXPIRED / UNKNOWN_STATUS` を分類する。
- 不一致は自動再注文・自動取消・自動売却せず、Human Reviewへ送る。
- Unknown order state は fail closed。

### 日中 10:30 / 12:35 / 14:45

目的: 状態不一致の早期検知。

- Broker Orders / Executions / Positions polling。
- Safety Monitor。
- Duplicate active order check。
- Position mismatch check。
- Buying Power check。
- LINE Payload必要時のみ生成し、送信はしない。

### 引け後 15:40-17:30

目的: 日次確定。

- Close Demo Broker Snapshot取得。
- Orders / Executions / Positions / Buying Power取得。
- Ledger更新。
- Order Plan、Submitted Orders、Broker Orders、Executions、Positions、Buying Power、Ledger、Safety、Report の Reconciliation。
- Safety Report生成。
- Daily operation manifest生成。
- Blog / Public Report / LINE Payload更新。

## 4. Mac運用 / CLI責務設計

Phase12-Bで作る CLI は、Mac上で手動実行と launchd 実行の両方に対応する。Phase12-Aでは責務設計のみで、CLI実装は行わない。

```bash
python scripts/run_phase12_preflight.py
```

責務:

- business day / holiday / run lock確認。
- demo environment固定確認。
- production order disabled確認。
- required env vars存在確認。ただし secret値は出力しない。
- Broker Snapshot freshness確認。
- raw response / secret persistence audit。
- Safety preflight入力の存在確認。

```bash
python scripts/run_phase12_daily_plan.py
```

責務:

- J-Quants由来データだけで AI inference を実行。
- Broker Snapshot / Paper Ledger / Safety / PnL / selected / bought / affordable data を AI学習・推論特徴量へ混入しないことを監査。
- Order Plan生成。
- planは未承認状態で保存。

```bash
python scripts/run_phase12_approval_prepare.py
```

責務:

- Order Plan、Safety preliminary result、Broker Snapshot summaryを人間確認用にまとめる。
- Demo Approval request artifactを生成する。
- Production approval artifactは生成しない。

```bash
python scripts/run_phase12_demo_submit.py
```

責務:

- Demo Approval検証。
- Safety latest check検証。
- MAX_EXPOSURE / buying_power / duplicate order / position mismatch確認。
- Demo-only guard確認。
- Demo注文送信。
- redacted order result保存。

```bash
python scripts/run_phase12_fill_monitor.py
```

責務:

- Broker Orders / Order Detail / Executions / Positions取得。
- submitted orderとbroker orderを照合。
- fill eventを redacted normalized schema で保存。
- partial fill / unknown / mismatch を Human Reviewへ送る。

```bash
python scripts/run_phase12_reconcile.py
```

責務:

- Order Plan、Submitted Orders、Broker Orders、Executions、Positions、Buying Power、Ledger、Safety、Reportを照合。
- reconciliation resultを PASS / REVIEW_REQUIRED / BLOCK へ分類。
- System faultは fail closed。

```bash
python scripts/run_phase12_daily_report.py
```

責務:

- Safety Report生成。
- Blog draft生成。
- Public Report生成。
- LINE Payload生成。
- LINE実送信は行わない。

```bash
python scripts/run_phase12_audit.py
```

責務:

- 30営業日分の operation manifests を集計。
- no production order audit。
- secret audit。
- leakage audit。
- raw response audit。
- reconciliation pass rate集計。
- Phase12 final judgement材料を生成。

## 5. launchd運用案

Mac launchd では自動送信系も起動できるが、Phase12開始直後は `run_phase12_demo_submit.py` のみ手動運用から始める。5営業日以上の安定後に、Demo Approval済み注文だけ launchd 送信を許可する段階運用にする。

| 時刻 | CLI | 目的 | 初期運用 |
|---|---|---|---|
| 15:40 | `run_phase12_reconcile.py --close-snapshot` | 引け後Broker確定 / preliminary reconciliation | launchd |
| 19:00 | `run_phase12_daily_plan.py` | AI推論 / Order Plan生成 | launchd |
| 20:00 | `run_phase12_approval_prepare.py` | Approval package生成 | launchd |
| 20:30 | `run_phase12_daily_report.py --draft` | Blog / Public Report / LINE Payload draft | launchd |
| 08:25 | `run_phase12_preflight.py` | business day / broker / safety preflight | launchd |
| 08:40 | `run_phase12_approval_prepare.py --preopen-refresh` | Approval材料を寄付き前snapshotで更新 | launchd |
| 08:50 | `run_phase12_demo_submit.py` | Demo注文送信 | 初期は手動 |
| 09:05 | `run_phase12_fill_monitor.py` | 初回fill確認 | launchd |
| 09:20 | `run_phase12_fill_monitor.py` | 追加fill確認 | launchd |
| 10:30 | `run_phase12_reconcile.py --intraday` | 日中照合 | launchd |
| 12:35 | `run_phase12_reconcile.py --intraday` | 後場前後照合 | launchd |
| 14:45 | `run_phase12_reconcile.py --intraday` | 大引け前照合 | launchd |
| 15:40 | `run_phase12_reconcile.py --close` | 日次確定照合 | launchd |
| 20:00 | `run_phase12_daily_report.py --final` | Daily report確定 | launchd |

launchd運用ルール:

- jobごとに run lock を取得する。
- 同一 business_date / same job の二重起動は禁止。
- 前段 job が BLOCK の場合、後段 job は fail closed。
- stdout / stderr に secret、raw response、plaintext order id、plaintext execution idを出さない。
- launchd plistには secret値を書かない。

## 6. Approval設計

Approval は Order Plan から Demo注文までに2段階設ける。

### Human Review Approval

対象:

- Order Plan全体。
- market stress / buy opportunity / individual drawdown 等の `NON_BLOCKING_REVIEW`。
- position replacement / sell-first-buy-after-fill。
- unusually large order。

役割:

- 投資判断として、注文を実行するか、サイズ縮小するか、見送るかを決める。
- Safety Layerの代替ではない。

### Demo Execution Approval

対象:

- 実際に Demo環境へ送る個別注文。

必須条件:

- `environment=demo`。
- `production_order_allowed=false`。
- `demo_order_allowed=true`。
- latest Safety Checkが `ALLOW` または承認済み `NON_BLOCKING_REVIEW`。
- `BLOCK` / `SYSTEM_EMERGENCY_STOP` ではない。
- MAX_EXPOSURE PASS。
- buying_power PASS。
- duplicate active orderなし。
- position mismatchなし。
- cash equity only。
- second password は secret loader 経由でのみ扱い、保存しない。

Approval artifactに保存するもの:

- approval id。
- approver label。
- approved_at。
- business_date。
- plan id。
- item ids。
- allowed sides。
- max notional。
- expiry。
- safety result hash。
- broker snapshot hash。
- redaction check result。

保存しないもの:

- secret。
- plaintext broker order id。
- raw broker response。
- account id。
- second password。

## 7. MAX_EXPOSURE設計

Phase11で確定した仕様を Phase12 Demo Broker basis へ接続する。

```text
max_total_exposure_ratio = 0.85
max_total_exposure_absolute_cap = null
exposure_basis = broker_actual_equity_or_buying_power
```

Demo Runtimeでは Paper Ledger equity を使わない。基準は次の優先順とする。

1. Broker actual equity相当が安全に正規化できる場合は、それを `base_equity` とする。
2. Broker actual equityが未定義または信頼不能の場合は、buying_power を上限側の基準として使う。
3. どちらも取得不能、stale、矛盾ありの場合は fail closed。

判定:

```text
current_exposure = broker_position_market_value
projected_exposure = current_exposure + new_buy_order_value
max_allowed_exposure = base_equity * 0.85

if side == BUY and projected_exposure > max_allowed_exposure:
    BLOCK / MAX_EXPOSURE_EXCEEDED
else:
    ALLOW
```

追加ルール:

- SELL / exposure reducing order は MAX_EXPOSURE では止めない。
- buying_power hard violation は BUY を止める。
- Demo broker actual cashが十分でも、evaluation capitalを超える過大サイズは禁止。
- Broker Snapshot、Position、Buying Power は AI学習へ使わない。

## 8. Reconciliation設計

毎営業日、以下を照合する。

| 対象 | 照合内容 | Fail Closed条件 |
|---|---|---|
| Order Plan | approved itemのみ送信対象か | 未承認item送信候補 |
| Submitted Orders | local submitted recordとapprovalの一致 | approval hash不一致 |
| Broker Orders | broker order stateとsubmitted recordの一致 | unknown / duplicate / missing |
| Executions | filled quantity / price / timestamp正規化 | detail合計とsummary不一致 |
| Positions | execution後の保有数量 | filled反映不能 / mismatch |
| Buying Power | order notionalと余力 | hard violation |
| Ledger | broker stateから更新された内部記録 | brokerとledgerの数量差 |
| Safety | latest preflight / monitor result | BLOCK / SYSTEM_EMERGENCY_STOP |
| Report | Blog / Public / LINE payloadのredaction | secret/raw/plaintext id混入 |

Reconciliation result:

```text
PASS
REVIEW_REQUIRED
BLOCK
SYSTEM_EMERGENCY_STOP
```

扱い:

- `PASS`: 次工程へ進める。
- `REVIEW_REQUIRED`: 自動注文、再注文、取消、売却は行わず、人間確認へ送る。
- `BLOCK`: Demo注文を止める。
- `SYSTEM_EMERGENCY_STOP`: read-only sync / audit / report のみ許可。

## 9. Phase12終了時の監査 / PASS条件

Phase12 は30営業日の安定稼働で判定する。

PASS条件:

- 30営業日分の daily manifest が存在する。
- Demo Broker Snapshot取得成功。
- Demo Position取得成功。
- Demo Order取得成功。
- Demo Execution取得成功、または注文なし日として妥当な empty classification。
- Demo注文成功日が1日以上ある。
- Fill Monitor成功。
- LedgerがBroker Source of Truthと一致、または差分が全てHuman Reviewで説明済み。
- Reconciliation PASS率が運用許容範囲内で、BLOCKは原因説明済み。
- Safety PASSまたは適切な REVIEW / BLOCK 分類。
- Blog生成成功。
- Public Report生成成功。
- LINE Payload生成成功。
- LINE実送信なし。
- no production order audit PASS。
- production unlock audit PASS。
- secret audit PASS。
- raw response audit PASS。
- leakage audit PASS。
- AI training contamination audit PASS。
- Broker Snapshot / Paper Ledger / Safety Result / Audit Result / cash / portfolio / PnL / selected / bought / affordable data が AI学習へ混入していない。
- 信用取引なし。
- 自動復帰なし。
- 無条件自動売却なし。

失敗条件:

- Production注文の痕跡。
- raw broker response保存。
- secret平文保存。
- plaintext order id / execution id のreport混入。
- Broker Source of Truthを無視したLedger更新。
- Safety `BLOCK` を無視した送信。
- ApprovalなしのDemo注文。
- AI再学習実行。
- Full Backtest再実行。
- LINE実送信。

## 10. Phase12-B実装計画

Phase12-Bでは最小実装に絞る。目的はDemo Full Operationを開始できる最小の運用線を作ることであり、Production Unlockは扱わない。

優先順位:

1. Phase12 runtime namespace / artifact schema
   - daily manifest、approval、submitted order、fill event、reconciliation result、report refsを定義する。
2. `run_phase12_preflight.py`
   - demo固定、production禁止、business day、run lock、secret/raw audit、broker snapshot freshness、Safety入力確認。
3. Broker actual equity / buying_power basis adapter
   - MAX_EXPOSURE 0.85 を Demo Broker equity / buying_powerへ接続する。
4. `run_phase12_daily_plan.py`
   - 既存AI / Order Plan生成をPhase12 namespaceへ接続し、AI学習禁止・特徴量混入禁止を監査する。
5. Approval artifact / validator
   - Human Review Approval と Demo Execution Approvalを分ける。
6. `run_phase12_demo_submit.py`
   - Demo-only guard、現物のみ、Approval必須、Safety必須、redacted result保存。
7. `run_phase12_fill_monitor.py`
   - Orders / Details / Executions / Positionsのredacted normalized monitoring。
8. `run_phase12_reconcile.py`
   - Order PlanからReportまでの毎日照合。
9. `run_phase12_daily_report.py`
   - Safety Report、Blog、Public Report、LINE Payload生成。LINE実送信は禁止。
10. launchd plist samples
   - 初期は submit 手動、その他をlaunchd候補にする。
11. Phase12 30営業日 audit
   - no production order、secret、raw response、leakage、AI contamination、reconciliation集計。

## Forbidden Actions Confirmation

- demo_order_executed: false
- production_order_executed: false
- production_unlock_executed: false
- line_send_executed: false
- runtime_changed: false
- implementation_changed: false
- ai_retraining_executed: false
- one_year_backtest_rerun: false
- five_year_backtest_rerun: false
- raw_response_saved: false
- plaintext_secret_saved: false

