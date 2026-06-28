# Phase11 Safety Refinement Plan

作成日: 2026-06-28

## Status

```text
PHASE11_SAFETY_REFINEMENT_DESIGN_COMPLETE
IMPLEMENTATION_NOT_STARTED
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
PHASE11Z_FULL_5Y_REMAINS_ON_HOLD
```

## Purpose

Phase11 Safety Layer を、相場下落で買いを止める装置ではなく、主にシステム事故を止める装置として再定義した。

今回の作業は設計文書作成のみである。

```text
Broker API接続なし
WebSocket接続なし
Demo/Production発注なし
自動売却なし
自動復帰なし
AI再学習なし
5年full backtestなし
Runtime大規模変更なし
```

## Read Materials

- `docs/02_architecture/safety_layer_phase11_architecture.md`
- `docs/phase_reports/phase11z_fix_d_mainline_adapter.md`
- `reports/phase_reports/phase11z_fix_d_mainline_adapter.json`
- `src/ai_fund_lab_v2/safety_phase11/` の既存 guard / state / emergency 関連箇所

## New Safety Responsibility

Safety Layer の新しい責務:

- Duplicate Order を止める。
- Broker Divergence を止める。
- Position mismatch を止める。
- Cash / buying_power 異常を止める。
- Runtime state 不整合を止める。
- Order / Execution 状態不一致を止める。
- Quote / Broker Snapshot critical stale を止める。
- manual emergency stop を反映する。
- secret / raw response 保存疑いを重大事故として止める。
- unknown severe error を fail closed にする。

Safety Layer が主責務から外すもの:

- 市場全体の下落を理由にした緊急停止。
- 個別銘柄下落を理由にした緊急停止。
- daily loss を理由にした緊急停止。
- market crash guard を理由にした一律買い停止。

## Emergency Stopに残す条件

`SYSTEM_EMERGENCY_STOP` 対象:

- Duplicate active buy order。
- duplicate broker order risk。
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

## Emergency Stopから外す条件

原則 `SYSTEM_EMERGENCY_STOP` にしない条件:

- market crash。
- candidate universe drawdown。
- index decline。
- 個別銘柄下落。
- daily loss。
- volatility上昇。
- sector stress。

分類先:

```text
WARNING
MARKET_STRESS
BUY_REVIEW_REQUIRED
BUY_OPPORTUNITY_REVIEW
SELL_REVIEW_REQUIRED
HIGH_RISK_REVIEW
```

## State Design

追加 / 再定義候補:

```text
MARKET_STRESS
BUY_REVIEW_REQUIRED
BUY_OPPORTUNITY_REVIEW
SYSTEM_EMERGENCY_STOP
SELL_REVIEW_REQUIRED
HIGH_RISK_REVIEW
```

互換期:

- 既存 `EMERGENCY_STOP` は実装上残しつつ、意味を `SYSTEM_EMERGENCY_STOP` へ限定する。
- 既存 `BUY_STOP` は相場由来の停止には使わず、将来は `BUY_REVIEW_REQUIRED` / `BUY_OPPORTUNITY_REVIEW` へ移行する。
- 既存 interface が `ALLOW / BLOCK / REVIEW_REQUIRED / EMERGENCY_STOP` の間は、market stress 系は `REVIEW_REQUIRED` にマップする。

## Market Stress / Buy Review

Market Crash Guard の新しい扱い:

```text
Mild broad decline -> WARNING
Sharp broad decline -> MARKET_STRESS
AI buy during stress -> BUY_REVIEW_REQUIRED
AI buy into crash candidates -> BUY_OPPORTUNITY_REVIEW
```

原則:

- Emergency Stop にしない。
- 自動売却しない。
- 自動買い停止もしない。
- Human Review Queue へ送る。
- 暴落日は買い場候補になり得るため、Safety Layer は投資機会を破棄しない。

## Individual Crash

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

- 自動売却なし。
- Emergency Stopなし。
- Human Review対象。
- sell / hold / add / reduce の判断は人間確認へ残す。

ただし、個別下落と同時に position mismatch、execution mismatch、critical stale、duplicate order がある場合は system emergency とする。原因は価格下落ではなく、システム不整合である。

## Phase11-Z Redo Plan

Phase11-Z / Fix-D では、相場下落が `EMERGENCY_STOP` へ接続され、Safety ONで fills / closes が強く抑制された。

やり直し順:

1. Safety Guard分類だけを refined design に合わせる。
2. `MarketCrashGuard` を `WARNING / MARKET_STRESS / BUY_REVIEW_REQUIRED / BUY_OPPORTUNITY_REVIEW` へ変更する。
3. `IndividualCrashGuard` を `WARNING / SELL_REVIEW_REQUIRED / HIGH_RISK_REVIEW` へ変更する。
4. `DailyLossGuard` を emergency から review 系へ変更する。
5. `EmergencyStopEvaluator` の対象を system fault reason の allowlist へ限定する。
6. 短期 mainline adapter smoke を再実行する。
7. Safety ON/OFFで、system fault以外の相場要因が過剰停止していないことを確認する。
8. 1年 mainline smoke を実行する。
9. 5年fullはその後に判断する。

Phase11-Zの新しい評価観点:

- system fault は確実に止める。
- market stress は Human Review へ送る。
- crash day の buy opportunity を一律破棄しない。
- auto_sell_executed=false。
- auto_recovery_executed=false。
- live_order_executed=false。
- Safety / Audit result は AI 学習へ使わない。

## Implementation Candidates

実装する場合の最小候補:

- `SafetyState` の追加または互換details追加。
- `SafetyGuardName` / reason_code の分類変更。
- `MarketCrashGuard` の emergency escalation削除。
- `IndividualCrashGuard` の emergency candidate削除。
- `DailyLossGuard` の emergency escalation削除。
- `EmergencyStopEvaluator` を system fault reason allowlist に変更。
- Report / Review Queue に refined classification を追加。
- testsで market crash / individual crash が emergency stop にならないことを確認。

## No Implementation Confirmation

今回の作業では以下を実施していない。

- Broker API接続。
- WebSocket接続。
- Demo発注。
- Production発注。
- 自動売却。
- 自動復帰。
- AI再学習。
- 5年full backtest。
- Runtime本体の大規模変更。
- Broker Snapshot更新。
- Paper Ledger更新。

## Judgement

```text
PHASE11_SAFETY_REFINEMENT_PLAN_READY
PHASE11Z_REFINED_SAFETY_IMPLEMENTATION_REQUIRED_BEFORE_NEXT_LONG_BACKTEST
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
