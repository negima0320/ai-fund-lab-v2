# Corporate Event Authority Design

作成日: 2026-07-27

## 1. 位置付け

Corporate Event Authorityは、Strategy Layerへ企業イベントのPoint-in-Time事実を提供するAuthorityである。

上位SoT:

```text
docs/02_architecture/strategy_architecture_v1.md
```

Corporate Event Authorityは投資判断を行わない。上場状態、上場廃止予定、決算予定、業績修正、配当修正、TOB、完全子会社化、株式交換、株式分割・併合などの事実を、PIT lineage付きで提供する。

## 2. Responsibility

責務:

- 企業イベントのPIT事実を提供する
- source artifact、source hash、coverage statusを記録する
- 決算予定変更履歴を保持する
- 決算発表予定時刻と発表済み状態を区別する
- 上場状態、監理銘柄、整理銘柄、最終売買日、effective dateをPITで保持する
- missing / coverage不足 / hash mismatchをfail-openしない

責務外:

- BUY判断
- SELL判断
- HOLD / ADD / REDUCE / EXIT判断
- Target Portfolio判断
- Portfolio weight判断
- Runtime判断
- Broker quantity / order condition判断

## 3. Event Coverage

対象候補:

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

## 4. Corporate Event Artifact

Schema候補:

```yaml
schema_version: corporate_event_authority.v1
business_date: 2026-07-27
as_of: 2026-07-27T08:30:00+09:00
symbol: "9432"
listed_status: LISTED
delisting_announced: false
delisting_status: NONE
supervision_status: NONE
liquidation_status: NONE
final_trading_date: null
scheduled_earnings_date: 2026-08-06
scheduled_earnings_time: AFTER_CLOSE
earnings_disclosed: false
days_to_earnings_business: 8
earnings_period: Q1
forecast_revision_status: NONE
dividend_revision_status: NONE
corporate_action_type: NONE
effective_date: null
coverage_status: AVAILABLE
artifact_lifecycle_status: DRAFT
source_authority_status: VALID
producer_result_status: PASS
runtime_consumer_eligibility: NOT_ELIGIBLE
source_artifacts:
  - jquants_listed_info
  - jquants_announcement_schedule
source_hashes: []
temporal_safety:
  point_in_time: true
  future_leakage_used: false
```

`authority_status: ACCEPTED` は使用しない。`ACCEPTED` はArtifact Acceptance Contract上のRegistry lifecycle statusとして予約される。

## 5. Earnings Contract

最低必須fields:

- `scheduled_earnings_date`
- `scheduled_earnings_time`
- `earnings_disclosed`
- `days_to_earnings_business`
- `earnings_period`
- `forecast_revision_status`
- `dividend_revision_status`
- `source_hashes`
- `source_artifacts`
- `coverage_status`
- `temporal_safety`

Rules:

- 決算予定変更履歴を保持する
- 発表後データを発表前へ使わない
- 決算発表日と決算発表時刻を区別する
- `earnings_disclosed=false` の時点で発表内容をfeatureとして使わない
- 決算日時不明は `REVIEW_REQUIRED`
- coverage不足を「決算イベントなし」と扱わない

## 6. Delisting Contract

最低必須fields:

- `listed_status`
- `delisting_announced`
- `delisting_status`
- `supervision_status`
- `liquidation_status`
- `final_trading_date`
- `corporate_action_type`
- `effective_date`
- `source_hashes`
- `source_artifacts`
- `coverage_status`
- `source_authority_status`

Rules:

- 上場廃止予定を未来へ先読みしない
- 監理銘柄、整理銘柄、最終売買日をPITで扱う
- 最終売買日超過は `BLOCK`
- listed status missingはsafe扱いしない
- coverage不足を「イベントなし」と扱わない

## 7. PIT Rules

必須:

- 決算予定変更履歴を保持する
- 発表後データを発表前へ使わない
- 決算発表時刻を区別する
- 将来公表情報を過去へ適用しない
- 上場廃止予定を未来へ先読みしない
- missingをsafe扱いしない
- coverage不足を「イベントなし」と扱わない
- source hash、source artifact、as_of、business_dateを記録する

禁止:

- Historical Run損益をCorporate Event補完に使う
- Backtest結果をevent risk labelとしてRuntime入力に使う
- 決算発表後のprice reactionを発表前featureにする
- 最新Listed masterを過去日にそのまま適用する
- delisting結果を過去日のCandidate除外に先読み使用する

## 8. Component Consumer Contract

| Component | Allowed Use | Prohibited Use |
|---|---|---|
| Candidate AI | 決算予定、企業イベント、上場状態を候補品質Evidenceとして使う | 決算だけで候補除外、上場廃止だけで売却決定 |
| Opportunity AI | 決算イベントrisk、post-earnings momentum、forecast revision、corporate actionをranking evidenceとして使う | 決算跨ぎ禁止、Portfolio weight決定 |
| Portfolio Policy Engine | 決算跨ぎを許容する市場/Portfolio posture、risk posture、cash postureを出す | 個別銘柄BUY/SELL、final target weight |
| Position Management AI | Corporate EventをHOLD/ADD/REDUCE/EXIT reasonとして使う | 新しいAction追加、Broker quantity決定 |
| Portfolio Construction | 新規BUY可否、Target Weight、Target Portfolio採用/除外をPortfolio全体で判断する | Broker quantity、lot rounding、Submit許可 |
| Capital Deployment | Event-aware Strategy Intentをnotional / quantity candidateへ変換する | Event riskを再評価しTarget Portfolioを変更 |
| Safety | 最終売買日超過、authority欠損、hash mismatch、trading禁止をBlock / Reviewする | Strategyを最適化する |
| Runtime | Authority検証、Execution、Pending、Submitを行う | 決算判断、上場廃止判断、企業イベント評価 |

## 9. PM Reason Codes

Position Management AIの正式Actionは、現時点では以下の4つに限定する。

```text
HOLD
ADD
REDUCE
EXIT
```

Corporate Eventはreasonとして利用する。

Reason候補:

- `EARNINGS_APPROACHING`
- `HOLD_THROUGH_EARNINGS_ALLOWED`
- `REDUCE_BEFORE_EARNINGS`
- `EXIT_BEFORE_EARNINGS`
- `POST_EARNINGS_MOMENTUM_CONFIRMED`
- `POST_EARNINGS_GAP_REVERSAL`
- `FORECAST_REVISION`
- `DIVIDEND_REVISION`
- `DELISTING_PENDING`

## 10. Failure Handling

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

## 11. Production / Demo / Historical Contract

Corporate Event AuthorityはProduction / Demo / Historical共通Strategy Contractとして扱う。

環境差はAdapterのみで吸収する。Historical専用のdelisting logic、earnings logic、profit logic、test-only fallbackは禁止する。

## 12. Open Decisions

| Decision | Owner | Status | 必要Evidence |
|---|---|---|---|
| earnings schedule source authority | Corporate Event Authority | OPEN_SOURCE_DECISION | J-Quants coverage / accepted source review |
| earnings release time precision | Corporate Event Authority | OPEN_SOURCE_DECISION | source timestamp coverage |
| TOB / merger event coverage | Corporate Event Authority | OPEN_SOURCE_DECISION | event source coverage |
| event risk thresholds | Portfolio Policy / PM / Portfolio Construction | OWNER_DECIDED_VALUE_OPEN | Phase23 controlled validation |
| final trading date emergency policy value | Safety | OWNER_DECIDED_VALUE_OPEN | Safety review |

