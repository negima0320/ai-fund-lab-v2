# Phase21-FA Corporate Event Authority Design

## 1. Primary Judgment

```text
PHASE21_FA_CORPORATE_EVENT_AUTHORITY_DESIGN_COMPLETE
```

Supporting judgments:

```text
CORPORATE_EVENT_RESPONSIBILITY_DEFINED
EARNINGS_CONTRACT_DEFINED
DELISTING_CONTRACT_DEFINED
PIT_CONTRACT_DEFINED
```

Phase21-FAでは、Strategy ArchitectureへCorporate Event Authorityを追加した。Productionコード、Runtimeコード、Strategyコード、Config、Accepted Generation、Artifact Registry、Historical Run、Training、Calibrationは変更していない。

## 2. Scope

Corporate Event Authorityは、以下の企業イベントをPIT事実として提供する。

- 上場状態
- 上場廃止予定
- 監理銘柄
- 整理銘柄
- 最終売買日
- 決算発表予定日
- 決算発表予定時刻
- 決算発表済み
- 四半期決算
- 業績予想修正
- 配当予想修正
- TOB
- 完全子会社化
- 株式交換
- 株式分割・併合
- その他Corporate Action

Corporate Event Authorityは事実を提供するだけであり、投資判断は行わない。

## 3. Files Created

- `docs/03_ai_design/corporate_event_authority_design.md`
- `docs/phase_reports/phase21_fa_corporate_event_authority_design.md`
- `reports/phase21_fa_corporate_event_authority_design/phase21_fa_evidence.json`

## 4. Files Updated

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/03_ai_design/market_context_design.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/03_ai_design/capital_deployment_design.md`

## 5. Responsibility Decision

| Component | Corporate Event Use | Prohibited |
|---|---|---|
| Corporate Event Authority | PIT企業イベント事実を提供 | BUY/SELL、Portfolio、Runtime判断 |
| Candidate AI | 決算予定、企業イベント、上場状態を候補品質Evidenceとして使う | 決算だけで候補除外、上場廃止だけで売却決定 |
| Opportunity AI | 決算イベントrisk、post-earnings momentum、forecast revisionをranking evidenceとして使う | 決算跨ぎ禁止、Portfolio weight決定 |
| Portfolio Policy Engine | 決算跨ぎ許容、risk posture、cash postureを判断 | 個別銘柄BUY/SELL、Target Weight決定 |
| Position Management AI | Corporate EventをHOLD/ADD/REDUCE/EXIT reasonとして使う | 新しいAction追加、Broker quantity決定 |
| Portfolio Construction | 新規BUY可否、Target Weight、Target Portfolio採用/除外を判断 | Broker quantity、lot rounding、Submit許可 |
| Capital Deployment | Event-aware Strategy Intentをnotional / quantity candidateへ変換 | Corporate Event riskを再評価しTarget Portfolio変更 |
| Safety | 最終売買日超過、Authority欠損、hash mismatch、Trading禁止をBlock/Review | Strategy最適化 |
| Runtime | Authority検証、Pending、Submit、Execution | 決算判断、上場廃止判断、企業イベント評価 |

## 6. Earnings Contract

最低必須fields:

- `scheduled_earnings_date`
- `scheduled_earnings_time`
- `earnings_disclosed`
- `days_to_earnings_business`
- `forecast_revision_status`
- `dividend_revision_status`
- `source_hashes`
- `source_artifacts`
- `coverage_status`
- `temporal_safety`

Rules:

- 決算予定変更履歴を保持する
- 発表後データを発表前へ使わない
- 決算発表予定日と予定時刻を区別する
- 決算日時不明は `REVIEW_REQUIRED`
- coverage不足を「イベントなし」と扱わない

## 7. Delisting Contract

最低必須fields:

- `listed_status`
- `delisting_announced`
- `supervision_status`
- `liquidation_status`
- `final_trading_date`
- `corporate_action_type`
- `effective_date`
- `source_hashes`
- `source_artifacts`
- `source_authority_status`

Rules:

- 上場廃止予定を未来へ先読みしない
- 監理銘柄、整理銘柄、最終売買日をPITで扱う
- 最終売買日超過は `BLOCK`
- coverage不足を「イベントなし」と扱わない

## 8. PIT Contract

禁止:

- 発表後データを発表前へ使う
- 決算発表時刻を無視する
- 将来公表情報を過去へ適用する
- 上場廃止予定を未来へ先読みする
- missingをsafe扱いする
- coverage不足を「イベントなし」と扱う
- Historical Run損益、Backtest結果、Paper LedgerをCorporate Event補完に使う

## 9. Failure Contract

| Condition | Handling |
|---|---|
| Corporate Event source missing | `REVIEW_REQUIRED` |
| Corporate Event hash mismatch | `BLOCK` |
| Coverage不足 | `REVIEW_REQUIRED` |
| 決算日時不明 | `REVIEW_REQUIRED` |
| invalid schema | `BLOCK` |
| source authority conflict | `BLOCK` |
| final trading date exceeded | `BLOCK` |

fail-openは禁止する。

## 10. Runtime Boundary

Runtimeは以下を行う。

- Authority検証
- Pending
- Submit
- Execution
- Ledger / Current反映

Runtimeは以下を行わない。

- 決算判断
- 上場廃止判断
- 企業イベント評価
- Portfolio判断
- Strategy fallback

## 11. Open Decisions

Ownerは確定済みで、未確定なのはsource coverageやthresholdのみである。

| Decision | Owner | Status |
|---|---|---|
| earnings schedule source authority | Corporate Event Authority | OPEN_SOURCE_DECISION |
| earnings release time precision | Corporate Event Authority | OPEN_SOURCE_DECISION |
| TOB / merger event coverage | Corporate Event Authority | OPEN_SOURCE_DECISION |
| event risk thresholds | Portfolio Policy / PM / Portfolio Construction | OWNER_DECIDED_VALUE_OPEN |
| final trading date emergency policy value | Safety | OWNER_DECIDED_VALUE_OPEN |

## 12. Acceptance Result

| Acceptance | Result |
|---|---|
| Corporate Event Authority追加 | PASS |
| 上場廃止責務明確化 | PASS |
| 決算日責務明確化 | PASS |
| 各Component責務明確化 | PASS |
| PIT Contract追加 | PASS |
| Failure Contract追加 | PASS |
| Runtime責務維持 | PASS |
| Production / Demo / Historical共通Contract維持 | PASS |

## 13. Prohibited Operations Confirmation

| Item | Result |
|---|---|
| Production Code Changed | NO |
| Runtime Code Changed | NO |
| Strategy Code Changed | NO |
| Config Changed | NO |
| PM Threshold Changed | NO |
| Candidate / Opportunity Model Changed | NO |
| Position Sizing Formula Adopted | NO |
| Market Context Threshold Adopted | NO |
| Safety Threshold Changed | NO |
| Accepted Generation Changed | NO |
| Artifact Registry Changed | NO |
| Training Executed | NO |
| Calibration Executed | NO |
| Historical Run Executed | NO |
| Backtest Executed | NO |
| Phase22 Implementation Started | NO |

