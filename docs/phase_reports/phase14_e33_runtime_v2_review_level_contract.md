# Phase14-E33 Runtime v2 Review Level Contract & E32 Reclassification

## Summary

Phase14-E33では、Runtime v2の今後のレビュー粒度を明確化した。

目的は、毎PhaseでFull Runtime E2Eを要求しない一方で、fixture / fake adapter / readonly snapshotを使ったComponent検証を、実Brokerを含むRuntime Flow成功として誤認しないことである。

コード変更、Submit、Production注文、Notification実送信、launchd変更は行っていない。

Final judgment: **PHASE14E33_REVIEW_LEVEL_CONTRACT_DEFINED**

## Review Level Contract

### Level 1: Component Review

対象変更範囲のInput / Output / Consumerを確認するレビュー。

許可:
- fixture
- fake adapter
- fake readonly snapshot
- saved artifact
- unit / lightweight integration test

禁止される表現:
- 本番Runtime成功
- Broker Demo Flow verified
- Full Daily Operation passed

完了表現:
- `LEVEL1_COMPONENT_REVIEW_PASS`
- `COMPONENT_IO_CONTRACT_COMPLETE`

### Level 2: Flow Review

BUY Flow / SELL Flow / Notification Flowなど、Flow単位で既存Runtime経路を確認するレビュー。

条件:
- fake adapter不可
- Broker Demo確認あり
- 通常Runtime entry / pipelineを使用
- テスト専用経路不可
- recovery-only経路不可

完了表現:
- `LEVEL2_FLOW_REVIEW_PASS`
- `BUY_FLOW_VERIFIED`
- `SELL_FLOW_VERIFIED`
- `NOTIFICATION_FLOW_VERIFIED`

### Level 3: Full Runtime Review

運用開始前または大きな接続変更後に実施するFull Runtime E2Eレビュー。

対象:
- Morning
- Submit
- Execution
- Current
- Report
- Notification Payload
- Audit

条件:
- Full Daily Operationの通常入口で実施
- fake adapter不可
- Submit有効化の可否を明示
- Notificationはpayload-onlyかsend-enabledかを明示
- Productionは禁止または別途Production Readinessで承認

完了表現:
- `LEVEL3_FULL_RUNTIME_REVIEW_PASS`
- `FULL_RUNTIME_E2E_VERIFIED`

## Required Reporting Rule

今後のPhase完了報告には必ず以下を含める。

- Review Level
- Verification boundary
- Fake / fixture / saved artifact使用有無
- Broker Demo確認有無
- Submit実行有無
- Notification実送信有無
- launchd変更有無
- Production到達有無
- 判定がRuntime全体成功を意味するか、Component成功を意味するか

## E32 Reclassification

Phase14-E32は、SELL Daily Operation IO ContractとComponent検証として有効である。

ただしE32では以下を使用した。

- fake submit adapter
- fake readonly snapshot
- fixture Current
- pytest integration

そのため、E32は次のように再分類する。

| Item | Classification |
| --- | --- |
| Review Level | Level 1 |
| Level 1 Result | PASS |
| Level 2 Result | NOT_YET_VERIFIED |
| Level 3 Result | NOT_APPLICABLE |
| Validity | SELL Component / IO Contract Complete |
| Not Valid As | Actual Demo Broker SELL Flow Success |
| Not Valid As | Full Daily Operation SELL E2E |

E32の正しい表現:

**SELL Component / IO Contract Complete**

E32で避けるべき表現:

**SELL Runtime Flow Complete**

## Remaining Tasks With Review Levels

| Task | Required Level | Purpose | Notes |
| --- | --- | --- | --- |
| SELL Flow Review | Level 2 | 実Demo Brokerを含むSELL Flow確認 | fake adapter不可。通常Runtime経路のみ。 |
| Notification Component Review | Level 1 | Payload schema / redaction / sender boundary確認 | 実送信なし。 |
| Notification Flow Review | Level 2 | payload-onlyからsender接続境界まで確認 | 実送信可否は別途承認。 |
| Full Runtime Review | Level 3 | Morning -> Submit -> Execution -> Current -> Report -> Notification Payload確認 | 運用開始前のみ。 |
| Production Readiness | Level 3 + Production Gate | Production endpoint / credential / Broker Writeの最終承認 | Phase14ではProduction注文禁止継続。 |

## Acceptance

- Review Level Contractを定義した。
- E32をLevel 1 PASS / Level 2 NOT_YET_VERIFIEDへ再分類した。
- 今後のPhase完了報告にReview Levelを必須化した。
- 残タスクをReview Level付きで整理した。
- コード変更なし。
- Submitなし。
- Production注文なし。
- Notification実送信なし。
- launchd変更なし。

## Final Judgment

**PHASE14E33_REVIEW_LEVEL_CONTRACT_DEFINED**
