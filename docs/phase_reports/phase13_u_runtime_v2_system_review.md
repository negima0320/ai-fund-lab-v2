# Phase13-U Runtime v2 System Review

## Status

SYSTEM_REVIEW

Phase13-LからPhase13-Tまでに作成されたRuntime v2 skeletonについて、Runtime v2全体として設計原則に沿って成立しているかをレビューした。

本レビューでは実装変更、Submit、Broker注文、Broker API呼び出し、Demo/Production注文、通知送信、launchd/plist操作、Backtest/Simulation実行は行っていない。

## Review Scope

- `src/ai_fund_lab_v2/runtime_v2/`
- `tests/runtime_v2/`
- Current State Runtime
- Runtime State Machine / Orchestrator
- Persistent Ledger / Asset Runtime
- Pending Order Plan Runtime
- Broker ReadOnly / Execution Reflection
- Reconcile Runtime
- Planning / Approval Runtime
- Report / Notification / Audit Runtime
- Architecture tests
- Phase13-L through Phase13-T reports
- `docs/02_architecture/runtime_architecture_v2.md`

## Architecture Principle Review

Runtime v2は、AI判断ロジックではなく、AIや周辺システムの判断をCurrent Stateと照合し、正しい順序で二重実行なく運用する制御層として実装されている。

確認結果:

- AI判断ロジックはRuntime v2へ混在していない。
- Runtime v2 planningはAI出力相当の入力を受け取り、Current Stateと制約を照合する責務に限定されている。
- Current / History / Derivedの分離は、Path Resolver、Current State Reader、Pending Reader、Report / Notification / Audit skeletonで維持されている。
- Currentは固定Pathを前提としており、日付別artifactからCurrentを推測するfallbackは確認されなかった。
- Submit対象は`pending_order_plan/pending_order_plan.json`を中心に設計され、`order_plan/YYYY-MM-DD`や`approval_artifact/YYYY-MM-DD`からSubmit対象を推測する流れは確認されなかった。
- 注文、約定、保有、資産はBroker ReadOnly models、Execution classifier、Ledger projection、Asset builderで分離されている。
- BrokerOrderだけを資産SoTにする実装は確認されなかった。
- Report / Notification payload / AuditはDerivedまたはEvidenceとして扱われ、Runtime Current入力にはなっていない。
- Runtimeが5銘柄固定制御を持つ実装は確認されなかった。
- 既存Runtime workflowを正規Runtime v2 flowとしてimportまたは継承する構造は確認されなかった。

## Component Dependency Review

設計上の流れは以下の責務境界で成立している。

```text
Current State
↓
Planning
↓
Approval
↓
Pending
↓
Broker ReadOnly / Execution
↓
Ledger
↓
Asset
↓
Reconcile
↓
Report
↓
Notification Payload
↓
Audit
```

確認結果:

- 循環importや不自然な逆依存は、レビュー対象コードとArchitecture tests上では確認されなかった。
- PlanningがLedgerを書かないことは、planning no-side-effect testsで確認されている。
- ApprovalがSubmitしないことは、approval linkageとplanning/approval no-side-effect testsで確認されている。
- ReportがCurrentを書かないことは、report builderとno-side-effect testsで確認されている。
- AuditがSubmit対象を選ばないことは、audit runtime testsで確認されている。
- Reconcileは差分・異常・review_requiredを返す責務であり、Current/Assetを直接書き換えない。
- Broker ReadOnly / Execution Reflectionはread-only ingestionとledger projectionに限定され、Broker Submitしない。
- Notificationはpayload generationとdelivery ledgerの重複防止に分離され、send実装は導入されていない。

## Current SoT Review

Current SoTは固定Pathとして分離されている。

| Current | Path | Review result |
| --- | --- | --- |
| Asset Current | `persistent_ledger/state.json` | 資産Currentの中心として扱われている |
| Submit Target Current | `pending_order_plan/pending_order_plan.json` | Submit対象Currentとして扱われている |
| Runtime State Current | `runtime_state/current_state.json` | State Machine Currentとして扱われている |
| Notification Delivery Current | `notification_delivery/delivery_ledger.jsonl` | 通知送信重複防止Currentとして扱われている |

禁止確認:

- `order_plan/YYYY-MM-DD`からSubmit対象を推測していない。
- `approval_artifact/YYYY-MM-DD`からSubmit対象を推測していない。
- `broker_orders/YYYY-MM-DD`から現在保有を確定していない。
- `reports/YYYY-MM-DD`をRuntime Current入力にしていない。
- `demo_ledger`をRuntime v2本線SoTとして読んでいない。
- MissingやUnknownをConfirmed Emptyとして扱わないテストが存在する。

## Safety / Side Effect Review

Phase13-Uでは副作用は封印されている。

確認結果:

- Submit未実行。
- Broker注文未実行。
- Broker API未呼び出し。
- Demo注文未実行。
- Production注文未実行。
- Notification send未実装・未実行。
- launchd未再開。
- plist未削除・未作成。
- Backtest未実行。
- Simulation未実行。
- 既存Runtime entrypoint未呼び出し。

## Test Coverage Review

Phase13-LからPhase13-Tまでの`tests/runtime_v2/`を軽量実行した。

```text
python3 -m pytest -q tests/runtime_v2/
217 passed in 0.43s
```

確認済みの主要観点:

- mode/environment必須。
- default production fallback禁止。
- History fallback禁止。
- Derived fallback禁止。
- MissingをConfirmed Empty扱いしない。
- UnknownをEmpty扱いしない。
- Pending `CONSUMED`再Submit禁止。
- `POST_SEND_UNKNOWN`自動再送禁止。
- BrokerOrderだけからAssetを作らない。
- Production `broker_orders_fallback`禁止。
- Report is Derived。
- Notification payload generation only。
- Audit not submit source。
- Legacy runtime workflow import guard。
- No side effect guard。

## Findings

### Major

なし。

Runtime v2の安全性、Current SoT、副作用封印を壊す重大な問題は確認されなかった。

### Medium

なし。

Phase13-U時点のskeleton全体レビューとして、実装前または統合前に必ず修正しなければならない責務境界の破綻は確認されなかった。

### Minor

- `broker_orders_fallback`の扱いはstandalone policyとしてテストされている。今後、統合reconcile flowでsource contextを受け取る段階では、このpolicyを明示的に接続する追加テストが望ましい。
- Component依存は現状のscanとno-side-effect testsで成立している。今後、module数が増える段階ではimport graph / cycle guardを明示的なArchitecture testとして強化するとよい。
- Report / Notification / AuditはDerived / Evidenceとして成立している。今後、永続化形式を追加する段階では、Derived artifactをCurrent入力にしないschema-level testを追加するとよい。

## Unresolved Items

### Must Resolve Before Implementation

なし。

### Can Resolve During Implementation

- 統合reconcile flowにおける`broker_orders_fallback` policy接続。
- Component import graph / cycle guardの強化。
- Runtime v2 full orchestration skeleton testの追加。

### Future Enhancement

- Report / Notification / Auditの永続化artifact schema test。
- Runtime mode別のstorage namespace collision test拡張。
- Production readiness前のBroker API adapter contract test。

### Out of Scope

- Broker Submit実装。
- Notification send実装。
- launchd/plist移行。
- Backtest/Simulation実行。
- AI再学習。

## Go / No-Go

GO_WITH_MINOR_FIXES

理由:

- Runtime v2の中心原則であるCurrent / History / Derived分離、Current固定Path、Pending-only Submit source、注文・約定・保有・資産分離、副作用封印は成立している。
- Phase13-LからPhase13-Tまでのruntime_v2 testsは全件通過している。
- 重大または中程度の設計・実装境界問題は確認されなかった。
- 軽微な追加テストや統合時のpolicy接続強化は残るが、Runtime v2 skeleton全体の成立性を阻害しない。

## Acceptance Criteria Review

- 設計全体レビューは完了している。
- Current SoTレビューは完了している。
- Component依存レビューは完了している。
- Side Effect封印レビューは完了している。
- Architecture Test coverageレビューは完了している。
- GO / GO_WITH_MINOR_FIXES / REVIEW_REQUIRED / NO_GO 判定は完了している。
- 重大・中・軽微の修正提案は整理されている。
- 実装変更は行っていない。

