# Phase23-O: Historical Runtime Production-Equivalence and Accepted Generation Contract Clarification

## 1. 今何が起きているか

Phase23-Lで、business dateを指定したAccepted Generation Resolverは次を要求するようになりました。

```text
accepted_at <= business_date
effective_from <= business_date
```

現行Accepted Generationは1件だけです。

```text
generation_id: phase19_aq_accepted_generation_641e6e313543f013
accepted_at: 2026-07-20T00:00:00+09:00
effective_from: 2026-07-20T00:00:00+09:00
```

そのため、2026-07-20より前のHistorical business date、たとえば2022年や2026-07-06〜2026-07-10では、date-local rule上は使えるAccepted Generationがありません。

## 2. 10BDが止まる直接原因

10BDが止まる直接原因は、Historicalの日付をProductionの日次運用と同じく「そのbusiness date時点で承認済みだったGenerationだけ使う」と判定したためです。

このルールはProduction/Demoでは妥当です。2026-07-10の本番判断で、2026-07-20に承認されたAI成果物を使ってはいけません。

しかしHistorical評価に同じルールをそのまま当てると、AI Fund Lab v2が存在しなかった2022年は全日BLOCKします。

## 3. なぜAccepted Generationが関係するか

Accepted Generationは、AI売買判断に使うモデル一式について、人が確認して「この組み合わせなら運用で使ってよい」と承認した、モデル・前処理・検証結果・署名付き目録のセットです。

HistoricalでもProductionと同じCandidate / Opportunity、model、scaler、feature bindingを使うため、Accepted Generation consumerは必要です。問題は「どの時点で承認済みならHistoricalで選んでよいのか」です。

## 4. ProductionとHistoricalで共通であるべきもの

| 項目 | Production | Historical | 同一であるべきか |
|---|---|---|---|
| Runtime source code | normal Runtime v2 | normal Runtime v2 | Yes |
| Strategy | Production-common | Same | Yes |
| Candidate / Opportunity | Accepted manifest bound | Same consumer/binding | Yes |
| Portfolio Policy | Production-common | Same | Yes |
| Portfolio Construction | Production-common | Same | Yes |
| Position Management | Production-common | Same | Yes |
| Capital Deployment | Production-common | Same | Yes |
| Position Sizing | Production-common | Same | Yes |
| Runtime Planning | Production-common | Same | Yes |
| Pending | Production-common lifecycle | Same lifecycle | Yes |
| Safety | Production-common | Same | Yes |
| Submit Decision | Production guard/decision | Same guard/decision | Yes |
| Accepted Generation consumer | Resolver + hash/schema checks | Same consumer/checks | Yes |
| Failure handling | fail closed / review | Same classification | Yes |
| Observability | Runtime manifests/summaries | Same evidence semantics | Yes |

Production-commonとは、同じ関数を呼ぶだけではなく、判断経路、検証、失敗時の止まり方、記録の意味が同じであることです。

## 5. ProductionとHistoricalで異なってよいもの

| 項目 | Production | Historical | 差分可否 |
|---|---|---|---|
| Market data供給 | live/current operational data | historical business-date-bound as-of data | Yes |
| Feature input日付 | operational business date | historical business date | Yes |
| Broker Write | authorized Production write | disabled | Yes |
| Broker/Fills | real broker | Historical Simulated Broker | Yes |
| Ledger output | Production authority | Historical evidence only | Yes |

同じRuntime処理を使うことと、同じカレンダー時点の外部状態を再現することは同じ意味ではありません。Historicalは同じ処理を使いますが、入力はhistorical business dateに束縛された過去データです。

## 6. Phase23-Lは何を正しく直し、どこへ誤適用した可能性があるか

Phase23-Lが正しく直した点:

- Production/Demoでは、その日より後に承認されたGenerationを使わない。
- current pointerだけでなく、authority history / generation manifest directoryからbusiness-date時点の候補を探す。
- latest fallbackやfuture generationを拒否する。

誤適用の可能性:

- Historical性能評価を「現在承認済みAI成果物を固定し、過去データを日次入力として流す評価」と見る場合、Productionのdate-local acceptance ruleをそのまま使うと、評価が成立しません。

## 7. これまでの長期テストは何を使っていたか

実Evidence上、過去の長期HistoricalはAccepted Generation Authorityを迂回していません。

代表例:

| Run | Period | Status | Used Accepted Generation |
|---|---:|---|---|
| `runtime-test-historical-extended-smoke-20260726T023256813084Z` | 2022-09-01〜2022-09-07 | PASS | `phase19_aq_accepted_generation_641e6e313543f013` |
| `runtime-test-historical-extended-smoke-20260726T043951394342Z` | 2022-08-01〜2022-08-29 | PASS | `phase19_aq_accepted_generation_641e6e313543f013` |
| `runtime-test-historical-extended-smoke-20260726T053732539035Z` | 2022-09-01〜2023-08-30 | PASS | `phase19_aq_accepted_generation_641e6e313543f013` |
| `runtime-test-historical-smoke-20260728T042516796181Z` | 2026-07-06〜2026-07-10 | PASS | `phase19_aq_accepted_generation_641e6e313543f013` |

各runのmanifestには `accepted_bundle_id=phase19_aq_accepted_generation_641e6e313543f013` と `opportunity_model_version=phase19_aq...:opportunity:48f469...` が記録されています。`accepted_artifact_unchanged=true`、`broker_write_performed=false` も確認済みです。

ただし、これらは `accepted_at <= historical business date` の検査を通したものではありません。Run開始時点のcurrent accepted artifactを固定して、historical dataへ流していた形です。

## 8. 4年性能評価を成立させる条件

まず評価の種類を決める必要があります。

現在承認済みAI成果物を固定して過去データへ当てる評価なら、成立条件は次です。

- Run開始前にHuman Accepted済みのAI成果物を1つ固定する。
- Runtime chain、Strategy、AI consumer、model/scaler/schema bindingはProduction-commonにする。
- Market / financial / corporate event / featureは各historical business date時点までのものだけ使う。
- latest fallback、Historical専用Strategy、Historical専用判断は禁止する。
- その評価は「現在のAI成果物を過去相場に当てた挙動評価」と明記する。

ただし、現行Accepted Generationは以下のcutoffを持ちます。

```text
candidate_training_cutoff: 2024-12-02
opportunity_training_cutoff: 2024-12-02
calibration_cutoff: 2025-12-01
validation_cutoff: 2026-03-03
dataset_target_max_date: 2026-05-15
```

したがって、2022年期間を「純粋なout-of-sample性能」と呼ぶにはtraining cutoff契約が未整理です。2022評価期間が学習データ期間に含まれるためです。

## 9. 根本原因

分類:

| Pattern | Judgment | Reason |
|---|---|---|
| A | `SUPPORTED` | Phase23-LのProduction date-local ruleをHistorical evaluationへ適用した |
| B | `SUPPORTED` | Historical Accepted Generation選択が未定義 |
| C | `NOT_SUPPORTED` | 既存長期runはAccepted Generation consumerを通っていた |
| D | `SUPPORTED` | past-production replayとcurrent-artifact evaluationがprofile上で未分離 |
| E | `SUPPORTED` | training cutoffとHistorical performance claimの契約が未整理 |

Primary Judgment:

`PHASE23_O_EXPLANATION_COMPLETE_WITH_USER_DESIGN_DECISION_REQUIRED`

## 10. ユーザー判断が必要か

必要です。

設計書だけでは、2022 Historicalで次のどれを正式採用するかが決まっていません。

1. 現在承認済みAI成果物を固定して、過去データだけを日次入力として評価する。
2. historical business date時点で承認済みだったGenerationだけを使う。
3. walk-forwardで再学習・再承認を繰り返す別テストにする。

## 11. 必要な判断内容

質問:

```text
現在承認済みのAI成果物をRun開始時に固定し、
2022年以降の過去データだけを日次入力として使う方式を、
Historical性能評価の正式方式として採用しますか。
```

選択肢:

| 選択 | 評価できるもの | 4年テスト可否 |
|---|---|---|
| 採用する | 現在のAccepted Runtime / Strategyを過去相場へ当てた挙動・運用成立性 | Contract更新とdata materialization後に可能 |
| 採用しない | 過去当時の承認履歴replay | 現行authorityでは不可 |
| Walk-forwardを別定義 | 時点ごとの再学習・再承認プロセス | 大きな新設計が必要 |

推奨案は1です。ただし、training cutoff overlapを明示し、「純粋なout-of-sample性能」とは分ける必要があります。

## 12. 次に何を修正するか

次Task候補:

`Phase23-P: Historical Accepted Generation Evaluation Authority Contract Decision and Resolver Scope Repair`

修正範囲:

- Historical Evaluation AuthorityをProduction date-local Acceptance Authorityと分けて定義する。
- Run開始時に固定したAccepted Generation、model/scaler/schema hash、training cutoffをrun authorityとして記録する。
- 日次入力はhistorical business date PITを厳守する。
- Historical専用Strategy、Historical専用fallback、latest fallbackは禁止のまま維持する。
- 10BD/4Yは契約更新とtargeted validation後にする。

## Evidence

Evidence directory:

`reports/phase23_o_historical_runtime_production_equivalence_and_accepted_generation_contract_clarification/`

Machine report:

`reports/phase_reports/phase23_o_historical_runtime_production_equivalence_and_accepted_generation_contract_clarification.json`

## Not Performed

以下は実施していません。

```text
コード修正
設計書修正
Resolver変更
Manifest変更
Historical profile追加
Bootstrap追加
Accepted Generation追加
データmaterialization
10BD / 20BD / 1y / 3y / 4yテスト
Runtime Switch
Broker Write
```
