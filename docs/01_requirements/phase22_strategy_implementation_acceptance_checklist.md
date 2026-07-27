# Phase22 Strategy Implementation Acceptance Checklist

## 1. Purpose

本チェックリストは、Phase22でStrategy Architecture v1を段階実装する際の共通受入条件を定義する。

Phase22の全タスクは、以下を満たすまで完了扱いにしない。

- Runtime Contractを壊さない
- Authority Contractを曖昧にしない
- Safety Contractを弱体化しない
- Production / Demo / Historicalで別実装にしない
- Future Leakageを発生させない
- Performance改善を事後Evidenceとしてのみ扱う

## 2. Common Status Labels

| Status | Meaning |
|---|---|
| PASS | Contract、Evidence、Regressionが成立 |
| REVIEW_REQUIRED | 証跡不足または判断保留。ただしRuntime破壊なし |
| BLOCK | Authority、Safety、PIT、Accepted Artifact、またはRuntime Contract違反 |

## 3. Architecture Checklist

| Check | Acceptance |
|---|---|
| Strategy Architecture v1準拠 | `docs/02_architecture/strategy_architecture_v1.md`と矛盾しない |
| Runtime boundary | Runtimeは環境差をHistorical Adapterへ閉じ込める |
| Authority boundary | Market Context、Portfolio Policy、Capital Deployment、PM、SafetyのAuthorityが明示されている |
| Safety separation | Strategy targetとSafety hard limitが分離されている |
| Common implementation | Production / Demo / Historicalで同じRuntime pathを使う |
| No fail-open | missing authority、hash mismatch、invalid artifactはBLOCKまたはREVIEW_REQUIRED |
| Rollback | previous accepted artifactまたはprevious common pathへ戻せる |

## 4. Data Checklist

| Check | Acceptance |
|---|---|
| PIT source | J-Quants PITまたはRuntime current authorityのみ |
| Source lineage | business_date、feature_date、source_hash、source memberを記録 |
| No future leakage | future return、future corporate action、future ranking、post-run PnLをRuntime入力にしない |
| Missing data | fallback生成ではなく明示的にREVIEW_REQUIREDまたはBLOCK |
| Run scoped evidence | Historical diagnosticはrun_id scopedで扱う |
| Post-hoc separation | Performance分析はTraining / Calibration / Runtime入力にしない |

## 5. Implementation Checklist

| Check | Acceptance |
|---|---|
| Scope | 各Phase22 taskは1責務変更を基本にする |
| No unrelated refactor | 周辺整理を理由にRuntime behaviorを変えない |
| No config drift | max exposure、max positions、cash bufferなど既存制限を暗黙変更しない |
| Idempotency | rerunでArtifactやOrdersが重複しない |
| Duplicate guard | Pending Composition / ADD Consumerの重複防止を維持 |
| Error mode | authority missing、schema invalid、hash mismatchをテストする |

## 6. Artifact Checklist

| Check | Acceptance |
|---|---|
| Schema | Artifact schema、version、required fieldsが定義されている |
| Source acceptance | Production source変更時はAccepted Generation refreshを行う |
| Registry | Accepted Artifact Registry / checkpointが最新source hashを参照 |
| Direct edit禁止 | accepted artifactを手編集しない |
| Member hash | accepted source member hashをEvidenceへ記録 |
| Compatibility | downstream consumerが新旧version boundaryを明示 |

## 7. Test Checklist

| Check | Acceptance |
|---|---|
| Unit tests | schema、authority、missing input、PIT、negative caseを含む |
| Regression tests | 既存Runtime、Phase21-B/C関連、Submit guardを含む |
| Compile/import | 変更対象packageがimport可能 |
| Equivalence | trace-only変更では既存behavior互換を確認 |
| Failure tests | fail-openしないことを確認 |
| Long run | Codexは実行しない。ユーザー実行結果をEvidenceとしてレビューする |

## 8. User-run Validation Checklist

| Check | Acceptance |
|---|---|
| Command ownership | 5BD、20BD、245BD、1年、複数年Runはユーザーが実行 |
| Run scope | run_id、start date、business days、artifact refsを記録 |
| Runtime validation | Lifecycle / Authority / Safety / Pending / SubmitがPASS |
| Performance validation | return、drawdown、cash、exposure、position count、turnover、benchmarkを分解 |
| Decision | PASS、REVIEW_REQUIRED、BLOCKのいずれかで判定 |

## 9. Performance Checklist

| Check | Acceptance |
|---|---|
| Return only禁止 | 年率換算だけで採用しない |
| Risk | drawdown、loss distribution、profit givebackを確認 |
| Deployment | cash utilization、exposure、position count、unfilled opportunityを確認 |
| PM attribution | HOLD / ADD / REDUCE / EXITごとに寄与を確認 |
| Ranking attribution | Candidate / Opportunity rankingの通過率と棄却理由を確認 |
| Regime | Bull / Range / Bear / volatileの最低分解を行う |
| Benchmark | TOPIX等のAuthorityが定義されるまで暫定扱い |
| Out-of-period | Phase23で対象外期間Validationを必須にする |

## 10. Task-specific Minimum Gates

| Task | Minimum Gate |
|---|---|
| Phase22-A | Market Context schema、PIT lineage、missing source test PASS |
| Phase22-B | Portfolio Policy schema、target fields、Safety separation PASS |
| Phase22-C | Capital Deployment責務分離、existing behavior compatibility PASS |
| Phase22-D | dynamic position count reason_codes、zero-candidate behavior PASS |
| Phase22-E | target cash / exposureとSafety floor分離 PASS |
| Phase22-F | sizing evidence、weight validation、lot viability PASS |
| Phase22-G | PM context lineage、trace-only equivalenceまたはaccepted drift PASS |
| Phase22-H | HOLD / ADD / REDUCE / EXIT policy reasons、cooldown/min-hold decision trace PASS |
| Phase22-I | Target Portfolio idempotency、duplicate order防止 PASS |
| Phase22-J | Benchmark / Sector source authority、coverage、missing policy PASS |
| Phase22-K | Performance Evaluation Artifact、metric status、post-hoc separation PASS |
| Phase22-L | 全Phase22 artifact / regression / user-run evidence closure PASS |

## 11. Reject Conditions

以下のいずれかがある場合、そのTaskはREJECTまたはBLOCKにする。

- Future Leakage
- Historical-only logic
- Production / Demo / Historicalの別実装
- Safety hard limitの弱体化
- accepted artifactの手編集
- hash check回避
- long Historical RunをCodexが実行
- Runtime入力へpost-hoc PnLを混入
- 特定Run IDや特定期間への最適化

