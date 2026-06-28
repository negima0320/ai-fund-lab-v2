# Phase11-A Safety Layer Architecture Design

作成日: 2026-06-28

## 1. Purpose

本書は Phase11-A として、Production / Demo 発注へ進む前に必要な Safety Layer architecture を定義する。

Phase11-A は設計のみである。

```text
Python実装なし
Runtime挙動変更なし
Broker API接続なし
Demo発注なし
Production発注なし
Broker Snapshot更新なし
Paper Ledger更新なし
テスト実行なし
```

Phase11 の目的は利益を増やすことではない。

```text
死なないための安全装置
```

として、大暴落、個別急落、発注重複、Broker乖離、stale quote、cash / exposure逸脱、daily loss、emergency stop、recovery、人間確認を扱う。

## 2. Preconditions

Phase10 は完了済みである。

```text
PHASE10_COMPLETE
PHASE11_READY_TO_START
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```

Phase10 で完成したもの:

- Tachibana demo read-only API
- Broker Snapshot integration
- Production Runtime Foundation
- Order Executor interface
- Demo / Production executor stub
- Fill Monitor mock lifecycle
- Demo order dry-run foundation

Phase10 時点の境界:

- Demo / Production の実発注は禁止。
- Production Runtime Foundation は Safety 判定ロジックを持たない。
- Safety Manager / Emergency Stop / Recovery は Phase11 の責務である。
- Broker Snapshot / Paper Ledger / PnL / cash / portfolio / Safety result は AI 学習に使わない。

## 3. Phase11 Responsibilities

Safety Layer の責務:

- AI判断の後段で、Order Plan / Runtime action の発注可否を判定する。
- Runtime と Broker の間に安全確認層として差し込む。
- Broker Runtime から分離された独立 subsystem として実装する。
- Broker を source of truth として扱う。
- Broker Snapshot、Realtime Quote、Orders、Executions、Runtime Manifest、Ledger参照を入力として安全判定する。
- Fail Closed を徹底する。
- Default Deny を徹底する。
- 不明、欠損、stale、不一致、分類不能は安全側に倒す。
- Human Review を優先する。
- Emergency 時は発注を止める。
- Phase11 では自動売却を実装しない。
- Safety Report と Human Review Queue に判断理由を出す。

Safety Layer がやらないこと:

- AIモデルの変更。
- AI学習データ生成。
- Broker read-only API 基盤の再実装。
- Runtime Foundation state machine の再設計。
- Demo / Production の実発注。
- 自動売却、無条件全売却。
- 訂正、取消、再発注、自動retry。
- Paper Ledger の勝手な更新。
- Broker Snapshot の勝手な更新。

## 4. Architecture Boundary

Phase11 の差し込み位置:

```text
Nightly AI / Order Plan
        ↓
Capital Allocation / Order Plan
        ↓
Safety Pre-Order Check
        ↓
Order Executor Interface
        ↓
Broker Runtime / Tachibana API
```

日中監視の差し込み位置:

```text
Broker Snapshot / Realtime Quote / Orders / Executions
        ↓
Hourly Position Monitor
        ↓
Safety Manager
        ↓
Safety State Machine
        ↓
Safety Report / Human Review Queue
```

Runtime は daily operation の順序を管理する。Safety Layer は、その各段階の前後で action を許可、停止、レビュー送り、緊急停止へ分類する。

Runtime が Safety から受け取るべき将来の結果:

```text
ALLOW
BLOCK
REVIEW_REQUIRED
EMERGENCY_STOP
```

Phase11-A では interface の設計に留め、Runtime package の実装変更は行わない。

## 5. Safety State Machine

Phase11 Safety State:

```text
NORMAL
WARNING
BUY_STOP
EMERGENCY_STOP
RECOVERY_CANDIDATE
MANUAL_APPROVED
```

### 5.1 NORMAL

意味:

- Safety guards が発注継続可能と判断している。
- Broker Snapshot、quote、orders、executions、runtime manifest に重大異常がない。

許可:

- read-only broker sync
- quote polling
- report
- approved order path の pre-order safety check
- Safety Report generation

禁止:

- Safety check を通らない発注
- approval なしの Demo / Production 発注
- Production readiness 未承認の production 発注

主な遷移:

- warning guard triggered -> `WARNING`
- market crash / buy stop condition -> `BUY_STOP`
- emergency condition -> `EMERGENCY_STOP`

### 5.2 WARNING

意味:

- 運用継続の余地はあるが、警戒すべき異常がある。
- 個別銘柄 -7% 警告など、即時停止ではないが人間確認対象を含む。

許可:

- read-only broker sync
- quote polling
- existing position monitoring
- report
- Human Review Queue 生成

条件付き許可:

- 新規買いは、triggered guard が buy stop を要求しない場合でも pre-order safety check を必須にする。

禁止:

- warning を無視した無条件発注
- warning を AI 学習へ渡すこと

主な遷移:

- warning 解消 -> `NORMAL`
- market crash / buy stop condition -> `BUY_STOP`
- emergency condition -> `EMERGENCY_STOP`

### 5.3 BUY_STOP

意味:

- 新規買いを停止する。
- 相場全体クラッシュ、daily loss、cash buffer、max exposure、broker divergence warning escalation などにより発動する。
- 既存保有の監視は継続する。

許可:

- read-only broker sync
- quote polling
- existing position monitoring
- fill monitoring
- report
- Human Review Queue 生成
- sell candidate generation

禁止:

- 新規買い
- pending buy の実発注化
- AI が出した BUY order の通過
- BUY_STOP を自動解除して発注再開すること

BUY_STOP 中の AI Buy は以下として扱う。

```text
result=BLOCK
reason=BUY_BLOCKED
```

主な遷移:

- recovery guard が改善候補を検出 -> `RECOVERY_CANDIDATE`
- emergency condition -> `EMERGENCY_STOP`

### 5.4 EMERGENCY_STOP

意味:

- Safety Layer が重大事故リスクを検知した状態。
- Runtime は fail closed とする。

許可:

- read-only broker sync
- quote polling
- audit
- report
- Human Review Queue 生成
- manual emergency review

禁止:

- 新規買い
- 新規売りの自動実行
- 訂正
- 取消
- 自動再発注
- 自動retry
- 自動復旧
- Runtime の通常進行

方針:

- 売りも原則自動実行しない。
- すべて Human Review へ送る。
- Phase11 では自動売却を実装しない。

主な遷移:

- emergency condition 解消候補 + recovery prerequisites -> `RECOVERY_CANDIDATE`
- manual approvalなしで `NORMAL` へ戻らない。

### 5.5 RECOVERY_CANDIDATE

意味:

- 暴落モードや emergency condition が解除候補になった状態。
- 底を当てるAIではなく、買い停止解除の候補検出である。
- 自動再開は禁止。

許可:

- read-only broker sync
- quote polling
- recovery evidence collection
- report
- Human Review Queue 生成

禁止:

- 自動的な新規買い再開
- Human Review なしの state unlock

主な遷移:

```text
RECOVERY_CANDIDATE
↓
Human Review
↓
MANUAL_APPROVED
↓
NORMAL
```

### 5.6 MANUAL_APPROVED

意味:

- Human Review により、NORMAL 復帰が承認された一時状態。
- 承認理由、承認者、承認時刻、対象 report、recovery evidence を監査可能にする。

許可:

- NORMAL 復帰 transition
- report
- audit

禁止:

- 承認情報なしの復帰
- stale report を根拠にした復帰

主な遷移:

- latest Safety Report が OK / acceptable warning かつ承認が有効 -> `NORMAL`
- 承認後に再度異常検知 -> `BUY_STOP` or `EMERGENCY_STOP`

## 6. State Transition Summary

```text
NORMAL -> WARNING
NORMAL -> BUY_STOP
NORMAL -> EMERGENCY_STOP

WARNING -> NORMAL
WARNING -> BUY_STOP
WARNING -> EMERGENCY_STOP

BUY_STOP -> RECOVERY_CANDIDATE
BUY_STOP -> EMERGENCY_STOP

EMERGENCY_STOP -> RECOVERY_CANDIDATE

RECOVERY_CANDIDATE -> MANUAL_APPROVED
MANUAL_APPROVED -> NORMAL

any state -> EMERGENCY_STOP
unknown state -> EMERGENCY_STOP
invalid transition -> current state is kept and REVIEW_REQUIRED
```

## 7. Safety Check Result

発注前 Safety Check は以下の判定を返す。

| Result | Meaning | Runtime treatment |
|---|---|---|
| `ALLOW` | 発注前Safetyを通過 | Executorへ進める候補 |
| `BLOCK` | 発注禁止 | Runtimeは発注へ進めない |
| `REVIEW_REQUIRED` | 人間確認必須 | Human Review Queueへ送る |
| `EMERGENCY_STOP` | 緊急停止 | Safety stateをEMERGENCY_STOPへ寄せる |

`ALLOW` は発注を保証しない。Approval、executor guard、broker guard、second password guard など別の条件も必要である。

## 8. Pre-Order Safety Check

Order Plan に対して、最低限以下の guard を評価する。

```text
Duplicate Order Guard
Cash Buffer Guard
Max Exposure Guard
Quote Stale Guard
Market Crash Guard
Broker Divergence Guard
Daily Loss Guard
Emergency Stop Guard
```

### 8.1 Duplicate Order Guard

入力:

- Order Plan
- Broker orders
- Runtime manifests
- Fill monitor result
- Pending order refs

判定:

- 同一銘柄、同一side、同一business_dateの active order が複数ある場合は `BLOCK`。
- Broker 側で重複疑いがある場合は `EMERGENCY_STOP` 候補。
- Runtime / Broker / Ledger の order state が一致しない場合は `REVIEW_REQUIRED`。

### 8.2 Cash Buffer Guard

入力:

- Order Plan notional
- evaluation cash
- broker actual cash / buying_power
- configured buffer
- existing exposure

判定:

- Demo rehearsal は evaluation cash を sizing 基準にする。
- Demo broker cash は上限確認にのみ使う。
- Production は broker actual cash / buying_power を正とする。
- buffer を割る order は `BLOCK`。
- cash / buying_power が取得不能なら `REVIEW_REQUIRED` または重大時 `EMERGENCY_STOP`。

### 8.3 Max Exposure Guard

入力:

- current broker positions
- proposed order
- configured max total exposure
- configured max single-name exposure
- configured max position count

判定:

- exposure cap 超過は `BLOCK`。
- 重大逸脱や想定外ポジションは `EMERGENCY_STOP`。

### 8.4 Quote Stale Guard

入力:

- realtime quote timestamp
- broker quote snapshot
- target issue code
- configured max age

判定:

- quote が stale なら `BLOCK`。
- 複数銘柄または market index quote が stale なら `BUY_STOP` または `EMERGENCY_STOP`。
- quote 欠損時は推測価格で発注しない。

### 8.5 Market Crash Guard

入力:

- TOPIX
- 日経平均
- グロース250
- 保有銘柄の平均下落率
- candidate universe の下落率
- 急落銘柄比率
- ストップ安候補比率

判定:

- market crash 検知時は `BUY_STOP` へ遷移する。
- AI が Buy を出しても `BUY_BLOCKED` として止める。
- crash 判定が激しい、または data / broker 異常と同時発生する場合は `EMERGENCY_STOP`。

### 8.6 Broker Divergence Guard

入力:

- Broker Snapshot
- Runtime state
- Ledger reference
- Orders
- Executions
- Positions

判定:

- Broker を source of truth とする。
- Paper Ledger や内部状態が Broker と違う場合は Broker 優先。
- 軽微または説明可能な一時差分は `REVIEW_REQUIRED`。
- positions、orders、executions、cash、buying_power の重大乖離は `EMERGENCY_STOP`。

### 8.7 Daily Loss Guard

入力:

- broker-derived portfolio valuation
- previous close valuation
- configured daily loss threshold
- drawdown threshold

判定:

- daily loss threshold 超過は `BUY_STOP`。
- emergency threshold 超過は `EMERGENCY_STOP`。
- PnL / valuation は Safety 判定と report だけに使い、AI 学習には使わない。

### 8.8 Emergency Stop Guard

入力:

- manual emergency stop flag
- latest safety state
- guard results
- broker availability
- runtime consistency

判定:

- manual emergency stop がある場合は `EMERGENCY_STOP`。
- unknown state、invalid state、unclassified severe error は `EMERGENCY_STOP`。

## 9. Individual Crash Guard

個別銘柄急落監視は Broker Position と Realtime Quote を使う。

入力:

- Broker Position
- broker average price or acquisition cost
- realtime quote
- quote timestamp
- position quantity
- runtime_id
- business_date

しきい値:

```text
-7%  : WARNING
-10% : STOP_LOSS_CANDIDATE
-15% : EMERGENCY_CANDIDATE
```

計算:

```text
drawdown_pct = (latest_price - reference_price) / reference_price
```

reference_price は broker average price / acquisition cost を第一候補とする。取得できない場合は推測せず `REVIEW_REQUIRED` とする。

Phase11 の扱い:

- 自動売却しない。
- Safety Event 化する。
- Safety Report に出す。
- Human Review 対象にする。
- -15% は Emergency Candidate であり、自動売却指示ではない。

分類:

| Drawdown | Event | Safety state effect |
|---|---|---|
| `<= -7%` | `INDIVIDUAL_DRAWDOWN_WARNING` | `WARNING` |
| `<= -10%` | `STOP_LOSS_CANDIDATE` | `BUY_STOP` or `REVIEW_REQUIRED` |
| `<= -15%` | `EMERGENCY_CANDIDATE` | `EMERGENCY_STOP` candidate |

## 10. Market Crash Guard

Market Crash Guard は Phase11 の正式スコープである。

監視候補:

- TOPIX
- 日経平均
- グロース250
- 保有銘柄の平均下落率
- candidate universe の下落率
- 急落銘柄比率
- ストップ安候補比率

初期判定方針:

- 単一指数だけでなく、複数シグナルの組み合わせで `BUY_STOP` を出す。
- data quality / quote stale がある場合は安全側に倒す。
- candidate universe 全体の下落率や急落銘柄比率が悪化した場合、AI Buy を止める。
- crash 中も既存保有の監視は継続する。

出力:

```text
market_crash_status
triggered_signals
buy_stop_required
emergency_candidate
review_required
```

## 11. Market Recovery Guard

Recovery Guard は底を当てるAIではない。

目的:

```text
暴落モード解除候補の検出
```

入力候補:

- 指数が数営業日連続で安定。
- 急落銘柄比率が低下。
- candidate universe の下落率が改善。
- stop-limit / extreme down candidate 比率が低下。
- realtime quote stale がない。
- Broker Snapshot が正常。
- Broker Divergence がない。
- Daily Loss / drawdown が許容範囲へ戻る。
- Human Review が承認している。

遷移:

```text
BUY_STOP or EMERGENCY_STOP
↓
RECOVERY_CANDIDATE
↓
Human Review
↓
MANUAL_APPROVED
↓
NORMAL
```

禁止:

- 自動再開。
- Human Review なしの NORMAL 復帰。
- recovery candidate を AI 学習ラベルとして使うこと。

## 12. Hourly Position Monitor

日中監視は Phase11-C 以降の実装対象として設計する。

対象:

- Broker Position
- Realtime Quote
- Orders
- Executions
- Broker Snapshot

検知:

- 個別銘柄急落
- 約定後ポジション不一致
- 注文残異常
- 約定未反映
- quote stale
- broker snapshot stale
- market crash
- duplicate order risk
- runtime state inconsistency

出力:

- Safety Event
- Safety Report
- Human Review Queue

推奨スケジュール:

```text
09:05 post-open first monitor
09:30 early session monitor
10:30 broker reconciliation
12:35 post-lunch monitor
14:45 near-close monitor
15:20 final intraday order status
hourly fallback monitor during market hours
```

制約:

- 監視は read-only。
- 自動売却しない。
- 自動取消しない。
- 自動訂正しない。
- API unavailable / stale / unknown は fail closed。

## 13. Broker Divergence Guard

Production では Broker を source of truth とする。

```text
Broker
↓
Snapshot
↓
Runtime
↓
Ledger
↓
Report
```

Paper Ledger や Runtime 内部状態が Broker と異なる場合:

- Broker を正とする。
- Ledger を勝手に書き換えない。
- mismatch を Safety Event として記録する。
- Human Review へ送る。

乖離時の判定:

| Divergence | Result |
|---|---|
| cash / buying_power mismatch | `REVIEW_REQUIRED` or `EMERGENCY_STOP` |
| position quantity mismatch | `EMERGENCY_STOP` |
| unknown broker position | `EMERGENCY_STOP` |
| order status mismatch | `REVIEW_REQUIRED` |
| duplicate active order | `EMERGENCY_STOP` |
| execution reflected but position missing | `REVIEW_REQUIRED` or `EMERGENCY_STOP` |
| broker snapshot stale | `REVIEW_REQUIRED` or `EMERGENCY_STOP` |

## 14. Emergency Stop

Emergency Stop 発動候補:

- 個別銘柄 -15%以上急落。
- 相場全体クラッシュ。
- Broker Snapshot 取得不能。
- Runtime State 不整合。
- Duplicate order risk。
- Cash / Exposure 重大逸脱。
- 約定・注文状態の重大乖離。
- manual emergency stop file / flag。
- secret / raw response / account id の保存疑い。
- Production order boundary violation。
- unknown severe error。

Emergency Stop 中:

- 新規買い禁止。
- 売りも原則自動実行しない。
- すべて Human Review へ送る。
- Runtime は fail closed。
- read-only broker sync / quote polling / report / audit は許可。
- 自動復旧は禁止。

Emergency Stop は損失上限ではない。ギャップダウンやストップ安では閾値より大きな損失が起き得る。Phase11 の Emergency Stop は、危険検知と自動進行停止の仕組みである。

## 15. Safety Event

Safety Event の候補 schema:

```json
{
  "event_id": "safety_event_x",
  "runtime_id": "runtime_x",
  "business_date": "YYYY-MM-DD",
  "environment": "demo",
  "state_before": "NORMAL",
  "state_after": "BUY_STOP",
  "guard": "MARKET_CRASH_GUARD",
  "severity": "HALT",
  "result": "BLOCK",
  "issue_code": "7203",
  "reason_code": "BUY_BLOCKED",
  "message": "Market crash guard blocked new buy order.",
  "requires_human_review": true,
  "auto_trade_executed": false,
  "raw_response_saved": false
}
```

保存禁止:

- raw response
- raw request
- plaintext account id
- plaintext order id
- plaintext execution id
- auth id
- private key
- virtual URL
- second password

## 16. Safety Report

Safety Report は以下へ出力する設計とする。

```text
reports/safety/phase11/
```

含める内容:

- current safety state
- triggered guards
- blocked orders
- review required items
- emergency candidates
- market crash status
- recovery candidate status
- broker snapshot freshness
- quote freshness
- divergence summary
- recommended human actions
- allowed actions
- blocked actions
- no-live-order confirmation
- secret / raw response persistence confirmation

Safety Report は監査成果物であり、AI 学習入力ではない。

## 17. Human Review

Human Review Queue に送る対象:

- STOP_LOSS_CANDIDATE
- EMERGENCY_CANDIDATE
- BUY_STOP transition
- RECOVERY_CANDIDATE
- Broker divergence
- duplicate order risk
- stale quote / stale snapshot
- rejected / expired / canceled / unknown order state
- position mismatch

Human Review で必要な情報:

- event id
- safety report path
- triggered guard
- severity
- affected issue code
- broker snapshot ref
- quote freshness
- recommended action
- allowed / blocked actions

Human Review は発注を自動的に許可しない。承認後も pre-order safety check と executor approval が必要である。

## 18. Data Use Constraints

AI学習に使ってはいけないもの:

- Backtest outcome
- Paper Ledger
- Broker Snapshot
- PnL
- Portfolio state
- Cash
- selected / bought / affordable data
- Order result
- Execution result
- Safety result
- Audit result
- PM multiplier imitation

AI学習に使ってよいもの:

- J-Quants由来データ
- 予測時点で利用可能な特徴量

Safety Layer は AI 学習データを作るものではない。Runtime の安全判定をする subsystem である。

## 19. Artifact Policy

Phase11 Safety artifacts:

```text
reports/safety/phase11/
.runtime/safety/phase11/events/
.runtime/safety/phase11/state/
.runtime/safety/phase11/review_queue/
.runtime/safety/phase11/audit/
```

Phase11-A では `.runtime` への書き込みは行わない。上記は後続実装フェーズの保存先設計である。

## 20. Phase11-A Acceptance Criteria

Phase11-A 完了条件:

- Safety Layer の責務が明確。
- Runtime / Broker との境界が明確。
- Safety State Machine が定義済み。
- Individual Crash Guard が定義済み。
- Market Crash Guard が正式スコープ化されている。
- Market Recovery Guard が定義済み。
- Pre-Order Safety Check が定義済み。
- Hourly Position Monitor が定義済み。
- Broker Divergence Guard が source of truth 方針と整合している。
- Emergency Stop が定義済み。
- Safety Report 出力内容が定義済み。
- AI学習データ利用制約が明記済み。
- 実装、API接続、発注、Runtime変更を行っていない。

判定:

```text
PHASE11A_DESIGN_COMPLETE
PHASE11B_READY_FOR_SAFETY_RUNTIME_DESIGN
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
