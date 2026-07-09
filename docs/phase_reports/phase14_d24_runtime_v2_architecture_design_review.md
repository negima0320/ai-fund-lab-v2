# Phase14-D24 Runtime v2 Architecture Design Review

作成日: 2026-07-07

## 最終判定

**PHASE14D24_ARCHITECTURE_REVIEW_GAP_FOUND**

分類: **MAJOR_GAP**

Phase13 Runtime Architecture v2は、Current SoT、Current / History / Derived分離、Pending-only Submit、Single Writer Rule、注文/約定/保有/資産分離、Legacy Runtime Isolationといった中核設計は強い。

一方で、Phase14-D20からD23までの実装・検証を踏まえると、Phase13設計そのものに「本番運用前に決めるべきだが、十分に具体化されていない事項」が残っている。

特に以下は設計gapである。

- Safety LayerをRuntime v2のPlanning / Approval / Submit / launchd運用にどう接続するか
- launchd / CLIの正規entry、停止条件、再開条件
- Restart / Reboot Recoveryの具体的な再開判定
- Manual Intervention / Broker手動操作の取り込み手順
- Position Driftの分類・修復・承認手順
- Long-running / Multi-day operationでの保存、監査、ローテーション、再同期ルール
- Production readiness / Production pilotの段階設計
- Blog / Public Report / Notification SendをRuntime v2にどこまで含めるか

今回はレビューのみであり、コード変更、Broker API呼び出し、Submit、Notification送信、launchd/plist変更は行っていない。

## D23からの前提

D23では以下の判定だった。

- Manual Demo Operation: READY
- Core Contracts: MOSTLY_READY
- launchd: NOT_READY
- Production: NOT_READY

D24では、この判定を「実装gap」ではなく「設計gap」へ分解する。

## Architecture Strengths

Phase13設計の強み:

1. Current SoTを中心に据えたこと
2. Current / History / Derivedを分けたこと
3. Submit sourceをPending Currentに限定したこと
4. Single Writer Ruleを明文化したこと
5. 注文、約定、保有、資産を分離したこと
6. `POST_SEND_UNKNOWN` 自動再送禁止を明文化したこと
7. Legacy RuntimeをRuntime v2本線に継承しない方針を明確化したこと
8. Demo / Productionをpathではなくmetadata / adapter / configで分ける思想を持ったこと
9. Report / Notification / AuditをDerived / Evidenceとして扱ったこと
10. Simulation Broker差し替え方針を定義したこと

これらはPhase14-D21/D22で実装上もかなり補強された。

## 30項目レビュー

| No | Review Target | 現設計で十分か | 曖昧な点 / 未定義な点 | 将来リスク | 追加すべきContract | 追加不要 | 分類 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Runtime全体アーキテクチャ | Core flowは十分 | 正規CLI/launchd entry、manual rehearsalから自動運用への昇格条件が粗い | 手動script群が正規入口化する | Runtime v2 Operation Entry Contract | Core component再設計は不要 | MAJOR_GAP |
| 2 | Current SoT設計 | D21/D22で十分に改善 | Current migration/backfillの正式手順が薄い | 過去per-run artifactを誤ってCurrent化する | Current Migration / Backfill Contract | Current fixed path再設計は不要 | MINOR_GAP |
| 3 | Current / History / Derived分類 | 概ね十分 | Blog/Public Report、manual review artifactの分類が未固定 | Derivedが運用判断sourceになる | Artifact Classification Registry | 大分類の再設計は不要 | MINOR_GAP |
| 4 | Single Writer Rule | 十分 | Multi-object commit失敗時のwriter順序と補正権限が粗い | stateとjsonlがずれる | Multi-object Commit / Repair Contract | Single Writer原則の変更不要 | MINOR_GAP |
| 5 | Pending Lifecycle | Submit周辺は十分 | EXPIRED/BLOCKED/REVIEW_REQUIREDからの再計画手順が薄い | 古いPendingが残る | Pending Terminal / Replan Contract | Pending model再設計不要 | MINOR_GAP |
| 6 | Approval設計 | 基本は十分 | Approval期限、再承認、承認者/根拠、manual override証跡が薄い | approval artifactの運用品質不足 | Approval Authority / Expiry / Override Contract | hash linkage再設計不要 | MINOR_GAP |
| 7 | Submit設計 | Demo guarded submitは十分 | Production submit段階、kill switch、partial submit不可条件が未設計 | 本番Pilotへ進めない | Submit Authority / Production Pilot Contract | RuntimeV2SubmitCommand再設計不要 | MAJOR_GAP |
| 8 | Broker Adapter設計 | Demo/Simulation境界は十分 | Production adapter、Cancel/訂正、ReadOnly failure policyが粗い | Broker固有挙動に引きずられる | Broker Capability Matrix Contract | Demo adapter再設計不要 | MAJOR_GAP |
| 9 | Ledger設計 | 基本は十分 | correction/migration/supersedeの厳密な台帳規則が薄い | 長期運用で修正履歴が曖昧 | Ledger Correction / Migration Contract | append-only思想は維持 | MINOR_GAP |
| 10 | Asset設計 | 現在資産構築は十分 | realized PnL、拘束資金、未約定注文の資産表示が粗い | Report/判断で資産解釈が揺れる | Asset Valuation / Cash Reservation Contract | Asset SoT再設計不要 | MINOR_GAP |
| 11 | Runtime State Machine | skeletonは十分 | 起動時復旧、停止からの再開、HALT解除条件が薄い | 再起動後に誤Submitする | Restart State Resolution Contract | 状態一覧の全面再設計不要 | MAJOR_GAP |
| 12 | Reconcile | 基本比較は十分 | drift severity、auto repair不可/可、人間判断条件が粗い | Divergence処理が属人的になる | Reconcile Severity / Repair Contract | 比較関数の思想変更不要 | MINOR_GAP |
| 13 | Report | Runtime report JSONは十分 | human-readable markdown/blogとの責務境界が設計のみ | Reportが見えにくく運用負荷増 | Runtime v2 Markdown Report Contract | ReportArtifact再設計不要 | MINOR_GAP |
| 14 | Notification | payload/delivery思想は十分 | 実送信、retry、unknown result、operator ackが未具体化 | 二重通知/通知漏れ | Notification Send / Ack Contract | payload生成再設計不要 | MAJOR_GAP |
| 15 | Audit | 基本は十分 | Audit findingからreview queueへの接続が未定義 | auditが読み物で終わる | Audit-to-Review Queue Contract | Audit model再設計不要 | MINOR_GAP |
| 16 | Runtime Mode設計 | D21で十分 | mode切替時のCurrent environment mismatch対応が薄い | demo/prod混在事故 | Runtime Mode Transition Contract | mode別path復活不要 | MINOR_GAP |
| 17 | Simulation設計 | Phase14-Cで十分 | Simulation結果のCurrent反映禁止、report分離の実装gateが薄い | simulation artifact混入 | Simulation Isolation Contract | Simulation専用Runtime不要 | MINOR_GAP |
| 18 | Demo運用設計 | BUY/SELL確認済み | demo特有の約定仕様、銘柄除外、外部取消の定常runbookが薄い | demo rehearsalsが不安定 | Demo Operation Runbook Contract | Demo core flow再設計不要 | MINOR_GAP |
| 19 | Production運用設計 | 禁止方針は十分 | 解除条件、Pilot段階、注文上限、停止条件が未設計 | 本番移行判断不能 | Production Readiness / Pilot Contract | 現時点でProduction実装不要 | MAJOR_GAP |
| 20 | launchd運用設計 | 禁止方針は十分 | 正規plist、schedule、manual gate、ログ/失敗時通知が未設計 | 自動化時に事故る | launchd Operation Contract | 旧plist継承不要 | MAJOR_GAP |
| 21 | Blog/Public Report設計 | D18で方向性あり | writer実装前のschema、公開範囲、秘匿情報除去が未確定 | 情報漏えい/公開品質不足 | Public Report Redaction Contract | Phase9 writer復活不要 | MAJOR_GAP |
| 22 | Safety Integration | Safety docsはある | Runtime v2のどのstate/transactionでSafety結果を読むか未固定 | Safety bypass | Safety Runtime Integration Contract | Safetyロジック再実装不要 | MAJOR_GAP |
| 23 | Failure Recovery | Transaction設計はある | 実運用runbook、review event lifecycle、operator action schemaが不足 | REVIEW_REQUIRED滞留 | Recovery Runbook / Review Queue Contract | rollback設計不要 | MAJOR_GAP |
| 24 | Restart/Reboot Recovery | restart観点は一部あり | process crash後、前回state別の再開ルールが未具体化 | 再起動後の二重Submit/停止漏れ | Reboot Recovery Matrix | State Machine全面変更不要 | MAJOR_GAP |
| 25 | Long-running Operation | 長期観点は弱い | log rotation、ledger compaction、stale current、daily close処理が未設計 | Current肥大/ stale判定不全 | Long-running Maintenance Contract | Core flow再設計不要 | MAJOR_GAP |
| 26 | Multi-day運用 | Phase14-G案はある | day boundary、holiday、unfilled carry、next-day pending expiryが未固定 | 翌営業日に誤判断 | Business Day / Carryover Contract | Multi-day専用Runtime不要 | MAJOR_GAP |
| 27 | Manual Intervention | 方針は一部あり | 誰が何を承認し、どのartifactへ記録するか未定義 | 手動補正が監査不能 | Manual Intervention Contract | 手動操作禁止ではなく記録化が必要 | MAJOR_GAP |
| 28 | Broker手動操作との整合 | D7で外部取消同期は確認 | 手動約定/取消/訂正/入出金の一般policyが未定義 | Broker画面操作とRuntimeが乖離 | External Broker Action Sync Contract | BrokerをRuntimeが上書きする設計は不要 | MAJOR_GAP |
| 29 | Position Drift対応 | Reconcileで検知可能 | drift分類、閾値、許容差、修復方法が未設計 | SELL guardやAssetが止まる | Position Drift Classification Contract | BrokerOrder fallback拡大不要 | MAJOR_GAP |
| 30 | Future Production拡張性 | Core separationは良い | scale、multiple accounts、tax/PnL、realized PnL、監視体制が未設計 | 拡張時にSoTが崩れる | Production Expansion Roadmap Contract | いま多口座実装は不要 | MINOR_GAP |

## Missing Contracts

本番運用前に追加すべきContract:

1. Runtime v2 Operation Entry Contract
2. Current Migration / Backfill Contract
3. Artifact Classification Registry
4. Multi-object Commit / Repair Contract
5. Pending Terminal / Replan Contract
6. Approval Authority / Expiry / Override Contract
7. Submit Authority / Production Pilot Contract
8. Broker Capability Matrix Contract
9. Ledger Correction / Migration Contract
10. Asset Valuation / Cash Reservation Contract
11. Restart State Resolution Contract
12. Reconcile Severity / Repair Contract
13. Runtime v2 Markdown Report Contract
14. Notification Send / Ack Contract
15. Audit-to-Review Queue Contract
16. Runtime Mode Transition Contract
17. Simulation Isolation Contract
18. Demo Operation Runbook Contract
19. Production Readiness / Pilot Contract
20. launchd Operation Contract
21. Public Report Redaction Contract
22. Safety Runtime Integration Contract
23. Recovery Runbook / Review Queue Contract
24. Reboot Recovery Matrix
25. Long-running Maintenance Contract
26. Business Day / Carryover Contract
27. Manual Intervention Contract
28. External Broker Action Sync Contract
29. Position Drift Classification Contract
30. Production Expansion Roadmap Contract

## Ambiguous Contracts

設計が存在するが曖昧なもの:

- Safety結果をどのRuntime stateで必須入力にするか
- Report / Blog / Public Reportの責務境界
- Notification送信失敗時のretry条件
- Manual migration applyの承認権限
- REVIEW_REQUIREDの解除条件
- Broker ReadOnlyが部分失敗した場合のasset update可否
- Production pilotの最小単位
- Pending expirationと翌営業日carryover
- realized PnLのLedger / Report反映条件
- external broker actionの同期頻度

## Future Risks

将来的に問題になりそうな点:

1. 手動scriptが増え、正規CLI entryが曖昧になる
2. REVIEW_REQUIREDが蓄積し、解除/棚卸しができなくなる
3. Broker手動操作がRuntime Currentに遅れて反映される
4. Position Driftを検知しても修復基準がなく運用停止が長引く
5. Notification send接続時に二重送信/未送信の境界が曖昧になる
6. Public Reportで秘匿情報や過度な詳細を出すリスク
7. Multi-day運用で未約定/失効/pending expiryが曖昧になる
8. Production pilot時にDemoで許したfallbackが混入する
9. 長期運用でJSONL肥大、stale current、log retentionが問題化する
10. Restart後に前回状態を誤って再実行する

## Required Before launchd

launchd前に設計完了が必要:

1. Runtime v2 Operation Entry Contract
2. launchd Operation Contract
3. Safety Runtime Integration Contract
4. Reboot Recovery Matrix
5. Recovery Runbook / Review Queue Contract
6. Business Day / Carryover Contract
7. Manual Intervention Contract
8. External Broker Action Sync Contract
9. Position Drift Classification Contract
10. Notification mode decision: payload-only or send-enabled
11. Long-running Maintenance Contract
12. Demo Operation Runbook Contract

## Required Before Production

Production前に設計完了が必要:

1. Production Readiness / Pilot Contract
2. Submit Authority / Production Pilot Contract
3. Broker Capability Matrix Contract
4. Safety Runtime Integration Contract
5. Public Report Redaction Contract
6. Notification Send / Ack Contract
7. Position Drift Classification Contract
8. Asset Valuation / Cash Reservation Contract
9. Ledger Correction / Migration Contract
10. Manual Intervention Contract
11. External Broker Action Sync Contract
12. Production Expansion Roadmap Contract

## Recommendations

推奨する次フェーズ:

1. **Phase14-D25: Runtime v2 Operation Design Gap Closure**
   - D24で列挙したmissing contractsを優先度付けする。

2. **Phase14-D26: Safety Runtime Integration Design**
   - SafetyをPlanning / Approval / Submit / launchd gateへどう接続するか決める。

3. **Phase14-D27: Restart / Manual Intervention / Broker External Action Runbook**
   - Reboot Recovery Matrix、Manual Intervention、External Broker Action Syncをまとめる。

4. **Phase14-D28: launchd / CLI Entry Design**
   - 正規CLI、dry-run/preflight、payload-only通知、REVIEW_REQUIRED stopを定義する。

5. **Phase14-D29: Multi-day Demo Operation Design**
   - business day boundary、pending carryover、unfilled orders、stale currentを定義する。

6. **Phase14-D30: Production Readiness Architecture Review**
   - Production pilot条件、broker adapter、Safety、notification、public reportを本番前提で再設計する。

## 追加不要と判断するもの

現時点では不要:

- Runtime v2本体の二重実装
- Simulation専用Runtime
- Phase9 writerの直接復活
- mode別Current pathの復活
- BrokerOrder fallbackのProduction許可
- 自動再SubmitによるPOST_SEND_UNKNOWN解消
- launchdの旧plist継承
- Production実注文の即時解禁

## Acceptance Criteria

| Criteria | 判定 |
| --- | --- |
| Phase13設計を網羅的にレビューしている | PASS |
| D23監査結果を踏まえている | PASS |
| 実装ではなく設計レビューになっている | PASS |
| 新たなContract不足があれば列挙している | PASS |
| launchd前に必要な設計を整理している | PASS |
| production前に必要な設計を整理している | PASS |
| コード変更していない | PASS |
| Broker API呼び出ししていない | PASS |
| Submitしていない | PASS |
| Notification送信していない | PASS |
| launchd/plist変更していない | PASS |

## 結論

Phase13 Runtime Architecture v2は、Core Runtimeの安全性を支える設計としては十分に強い。

しかし、Phase14でDemo BUY/SELL、Current SoT write/read-backまで進んだ現在の視点では、日次運用・自動運用・本番移行に必要な運用設計Contractが不足している。

したがってD24は **PHASE14D24_ARCHITECTURE_REVIEW_GAP_FOUND** と判定する。
