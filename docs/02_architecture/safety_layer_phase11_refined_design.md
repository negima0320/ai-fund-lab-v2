# Phase11 Safety Layer Refined Design

作成日: 2026-06-28

## 1. Purpose

本書は Phase11 Safety Layer の責務を再定義する。

従来の Phase11 Safety Layer は、相場下落、個別急落、market crash、daily loss を強く `BUY_STOP` / `EMERGENCY_STOP` へ接続していた。これは「死なないための安全装置」としては保守的だが、運用システムとしては暴落日を一律停止扱いにしやすく、買い場候補や人間判断の余地を潰す。

Refined Design では Safety Layer を次のように再定義する。

```text
Safety Layer の主責務:

システム事故、発注事故、Broker不整合、データ永続化事故を止める。
相場下落そのものは止める対象ではなく、Human Reviewへ送る。
```

本書は設計文書であり、実装変更、Broker接続、発注、AI再学習、backtest再実行は行わない。

## 2. New Safety Responsibility

Safety Layer の責務:

- 発注前に、発注事故を検知する。
- Broker Source of Truth と Runtime / Ledger / Order Plan の不整合を検知する。
- duplicate order、position mismatch、execution mismatch、cash / buying power異常を止める。
- stale quote / stale broker snapshot を、発注事故につながる critical data fault として扱う。
- raw response / secret persistence 疑いを重大事故として扱う。
- unknown severe error は fail closed にする。
- 相場下落、個別銘柄下落、market crash、daily loss は Human Review に送る。
- 自動売却、自動復帰、自動発注再開は行わない。
- Safety result / Audit result / Broker Snapshot / Paper Ledger / PnL / portfolio / cash / order result / execution result は AI 学習に使わない。

Safety Layer がやらないこと:

- 相場の良し悪しを判断して投資機会を捨てること。
- market crash を理由に全発注を自動停止すること。
- 個別銘柄下落を理由に自動売却すること。
- daily loss を理由に自動で Production 全停止へ落とすこと。
- AIモデル、Capital Allocation、Order Planの収益ロジックを変更すること。

## 3. Refined State Model

既存状態:

```text
NORMAL
WARNING
BUY_STOP
EMERGENCY_STOP
RECOVERY_CANDIDATE
MANUAL_APPROVED
```

再定義 / 追加候補:

```text
NORMAL
WARNING
MARKET_STRESS
BUY_REVIEW_REQUIRED
BUY_OPPORTUNITY_REVIEW
SYSTEM_EMERGENCY_STOP
RECOVERY_CANDIDATE
MANUAL_APPROVED
```

互換性のため、既存実装の `EMERGENCY_STOP` は将来的に `SYSTEM_EMERGENCY_STOP` の意味へ寄せる。既存 `BUY_STOP` は廃止または限定利用とし、相場下落由来の新規買い抑制は `BUY_REVIEW_REQUIRED` / `BUY_OPPORTUNITY_REVIEW` へ移す。

### 3.1 NORMAL

通常状態。

意味:

- Broker Snapshot、Orders、Executions、Runtime state に重大なシステム不整合がない。
- Quote / Broker Snapshot freshness が発注判断に必要な範囲で有効。
- Safety pre-order check が通れば注文計画は次段階へ進める。

### 3.2 WARNING

軽度の注意状態。

例:

- 個別銘柄 -7% 程度。
- quote freshness がやや劣化しているが critical stale ではない。
- market summary に弱い下落シグナルがある。

扱い:

- 発注自体は Safety pre-order check を必須にして継続可能。
- Human Review Queue に載せる。
- 自動売却、自動復帰、自動停止はしない。

### 3.3 MARKET_STRESS

相場ストレス状態。

例:

- 市場全体の急落。
- candidate universe の広範な下落。
- sector / index 由来の stress。

扱い:

- Emergency Stop ではない。
- 原則として自動買い停止もしない。
- 新規買いは `BUY_REVIEW_REQUIRED` または `BUY_OPPORTUNITY_REVIEW` として人間確認へ送る。
- 暴落日は買い場候補になり得るため、Safety Layer は投資判断を破棄しない。

### 3.4 BUY_REVIEW_REQUIRED

新規買いに人間確認が必要な状態。

例:

- market stress 下で AI / CAP5 が buy を出した。
- daily loss が一定以上だが system fault はない。
- quote freshness が review level。

扱い:

- 自動的に `BLOCK` / `EMERGENCY_STOP` へ落とさない。
- Human Review Queue に `allowed_actions` / `blocked_actions` を明記する。
- Human approval があるまで実発注は進めない。

### 3.5 BUY_OPPORTUNITY_REVIEW

下落局面を買い場候補として確認する状態。

例:

- market crash guard が強い下落を検出したが、Broker / Runtime / Order / Execution に事故はない。
- AI / CAP5 が下落銘柄を候補にしている。

扱い:

- 「止める」ではなく「見に行く」状態。
- Human Review で、買い増し、見送り、サイズ縮小、候補差し替えを判断する。
- 自動発注はしない。

### 3.6 SYSTEM_EMERGENCY_STOP

システム事故・発注事故・Broker不整合に限定した緊急停止状態。

発動条件:

- Duplicate Order。
- Broker Divergence。
- Position mismatch。
- Cash / buying_power 異常。
- Runtime state 不整合。
- Order / Execution 状態不一致。
- Quote / Broker Snapshot critical stale。
- manual emergency stop。
- secret / raw response 保存疑い。
- unknown severe error。

扱い:

- 新規買い禁止。
- 自動売却禁止。
- retry / resubmit / cancel / modify の自動実行禁止。
- Broker read-only sync、audit、report、Human Review のみ許可。
- 復旧は `RECOVERY_CANDIDATE -> MANUAL_APPROVED -> NORMAL` のみ。

### 3.7 RECOVERY_CANDIDATE / MANUAL_APPROVED

復旧候補 / 手動承認状態。

対象:

- `SYSTEM_EMERGENCY_STOP` からの復旧。
- 旧 `BUY_STOP` からの互換復旧。

扱い:

- 自動で `NORMAL` へ戻さない。
- latest Safety Check が system fault なしであること。
- Human approval があること。
- Safety Report / Review Queue に復旧根拠を残すこと。

## 4. Emergency Stop Scope

### 4.1 Emergency Stopに残す条件

以下は `SYSTEM_EMERGENCY_STOP` 対象とする。

- Duplicate active order。
- duplicate broker order risk。
- Broker divergence。
- Broker position と Runtime / Ledger position の mismatch。
- execution exists but position missing。
- filled order が position / ledger に反映されない。
- order state unknown / inconsistent。
- cash / buying_power / withdrawable cash / order notional の重大不整合。
- Runtime state machine 不整合。
- run lock / manifest / business day guard の重大矛盾。
- Quote critical stale。
- Broker Snapshot critical stale / missing。
- manual emergency stop。
- raw request / raw response / plaintext account id / plaintext order id / plaintext execution id / auth id / private key / virtual URL / second password の保存疑い。
- unknown severe error。

### 4.2 Emergency Stopから外す条件

以下は原則 `SYSTEM_EMERGENCY_STOP` にしない。

- 市場全体の下落。
- market crash。
- candidate universe drawdown。
- 個別銘柄下落。
- daily loss。
- model confidence低下。
- volatility上昇。
- sector stress。

これらは次へ分類する。

```text
WARNING
MARKET_STRESS
BUY_REVIEW_REQUIRED
BUY_OPPORTUNITY_REVIEW
SELL_REVIEW_REQUIRED
HIGH_RISK_REVIEW
```

## 5. Market Crash Guard Redesign

Market Crash Guard は system emergency を返さない。

出力候補:

```text
WARNING
MARKET_STRESS
BUY_REVIEW_REQUIRED
BUY_OPPORTUNITY_REVIEW
```

判定例:

- Mild broad decline -> `WARNING`
- Broad sharp decline -> `MARKET_STRESS`
- AI buy during market stress -> `BUY_REVIEW_REQUIRED`
- AI buy into crash candidates -> `BUY_OPPORTUNITY_REVIEW`

禁止:

- market crash だけで `EMERGENCY_STOP`。
- market crash だけで自動売却。
- market crash だけで恒久的な買い停止。
- market crash を AI 学習データへ混入。

Human Review へ渡す情報:

- index_return。
- candidate_universe_drawdown。
- extreme_down_ratio。
- stop_limit_candidate_ratio。
- affected candidates。
- proposed order sizes。
- recommended human actions。

## 6. Individual Crash Guard Redesign

旧分類:

```text
-7%  WARNING
-10% STOP_LOSS_CANDIDATE
-15% EMERGENCY_CANDIDATE
```

新分類:

```text
-7%  WARNING
-10% SELL_REVIEW_REQUIRED
-15% HIGH_RISK_REVIEW
```

扱い:

- 自動売却しない。
- system emergency にしない。
- Human Review Queue に送る。
- sell candidate / hold candidate / add review / hedge review などを人間判断に残す。

ただし、個別下落と同時に以下がある場合は system emergency の可能性がある。

- execution mismatch。
- position mismatch。
- quote critical stale。
- Broker Snapshot missing。
- order duplicate。
- cash / buying_power不整合。

この場合、Emergency の原因は価格下落ではなく system fault である。

## 7. Daily Loss Guard Redesign

Daily loss は原則 system emergency にしない。

扱い:

- `WARNING`。
- `MARKET_STRESS`。
- `BUY_REVIEW_REQUIRED`。
- `SELL_REVIEW_REQUIRED`。

Daily loss は portfolio risk / performance context であり、発注事故そのものではない。したがって、Broker / Runtime / Order / Execution に不整合がない限り `SYSTEM_EMERGENCY_STOP` へ落とさない。

## 8. Decision Aggregation

新しい集約優先順位:

```text
SYSTEM_EMERGENCY_STOP
REVIEW_REQUIRED
BUY_REVIEW_REQUIRED
BUY_OPPORTUNITY_REVIEW
MARKET_STRESS
WARNING
ALLOW
```

ただし、現行 interface の `SafetyDecision` が `ALLOW / BLOCK / REVIEW_REQUIRED / EMERGENCY_STOP` の場合は、互換マッピングを使う。

互換マッピング案:

| Refined classification | Current decision compatibility | State candidate |
| --- | --- | --- |
| SYSTEM_EMERGENCY_STOP | EMERGENCY_STOP | EMERGENCY_STOP |
| BUY_REVIEW_REQUIRED | REVIEW_REQUIRED | WARNING or BUY_STOP-compatible |
| BUY_OPPORTUNITY_REVIEW | REVIEW_REQUIRED | WARNING |
| MARKET_STRESS | REVIEW_REQUIRED | WARNING |
| SELL_REVIEW_REQUIRED | REVIEW_REQUIRED | WARNING |
| HIGH_RISK_REVIEW | REVIEW_REQUIRED | WARNING |
| WARNING | REVIEW_REQUIRED or ALLOW with warning | WARNING |
| ALLOW | ALLOW | NORMAL |

## 9. Order Flow Placement

Refined Safety は発注前に system fault を確認する。

```text
AI / CAP5 / Order Plan
        ↓
Safety System Fault Check
        ↓
Market Stress / Buy Opportunity Review classification
        ↓
Human Review when required
        ↓
Order Executor Interface
```

`SYSTEM_EMERGENCY_STOP` のときだけ、発注事故防止として order flow を止める。

`MARKET_STRESS` / `BUY_OPPORTUNITY_REVIEW` は、収益機会の可能性を残すため、人間確認キューへ送る。

## 10. Phase11-Z Redo Policy

Phase11-Z / Fix-D では、相場下落が `EMERGENCY_STOP` へ接続され、取引数・cash recycling・closeがSafetyで強く抑制された。

Phase11-Z をやり直す場合は、以下の順で行う。

1. Safety guard の分類だけを refined design に合わせる。
2. Market crash / individual crash / daily loss を `REVIEW_REQUIRED` 系へ移す。
3. Duplicate / divergence / mismatch / critical stale / secret persistence を system emergency として残す。
4. mainline_paper_adapter profile で短期 smoke を再実行する。
5. Safety ON/OFF 比較で、system fault 以外の相場下落が過剰停止していないことを確認する。
6. 1年 mainline smoke を実行する。
7. その後に初めて 5年 full の再実行可否を判断する。

合格観点:

- 相場下落で `SYSTEM_EMERGENCY_STOP` が多発しない。
- Duplicate / divergence / mismatch / critical stale は確実に停止する。
- Human Review Queue に market stress / buy opportunity review が出る。
- 自動売却、自動復帰、実発注が発生しない。
- Safety結果はAI学習に使われない。

## 11. Implementation Notes for Later Phase

本設計に基づく将来実装は、最小変更で行う。

候補:

- `SafetyState` に `MARKET_STRESS` / `BUY_REVIEW_REQUIRED` / `SYSTEM_EMERGENCY_STOP` を追加。
- または互換期として `WARNING` と `REVIEW_REQUIRED` details に refined classification を持たせる。
- `MarketCrashGuard` の `EMERGENCY_STOP` / `BUY_STOP` 返却をやめる。
- `IndividualCrashGuard` の `EMERGENCY_CANDIDATE` を `HIGH_RISK_REVIEW` に変更。
- `DailyLossGuard` の emergency escalation を外す。
- `EmergencyStopEvaluator` の reason allowlist を system fault 系へ限定。
- Report / Review Queue に `market_stress`, `buy_opportunity_review`, `system_emergency_stop` を明示。

実装時も以下は禁止を維持する。

- Broker API接続。
- WebSocket接続。
- Demo / Production 発注。
- 自動売却。
- 自動復帰。
- AI再学習。
- Safety result の AI 学習利用。
- 5年 full backtest の先行実行。
