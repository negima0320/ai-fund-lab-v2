# Phase23-N: Accepted Generation Design and Implementation Explanation Audit

## 1. 30秒で分かる説明

Accepted Generationとは、
「AI売買判断に使うモデル一式について、人が確認して『この組み合わせなら運用で使ってよい』と承認した、モデル・前処理・検証結果・署名付き目録のセット」
である。

たとえば今の `.runtime` には、`phase19_aq_accepted_generation_641e6e313543f013` というAccepted Generationが1つあります。これは「この候補抽出モデル、この機会評価モデル、このscaler、この特徴量順、この検証結果、このhashの組み合わせを使ってよい」という記録です。

ここでいう「Runtime」は日次運用プログラム、「Generation」はモデル世代、「Authority」は運用時に正とする証拠付き決定記録です。

## 2. Accepted Generationとは

Accepted GenerationはSource Codeではありません。Strategy実装コードでも、過去のプログラム版でも、日次の売買判断結果でも、候補銘柄一覧でも、バックテスト結果でもありません。

設計書では、Accepted DecisionがGeneration CandidateをRuntimeで使えるAccepted Generationへ昇格すると定義されています。Runtimeはtraining datasetやsplitを直接読まず、Accepted Generation Resolverが選んだものだけを使います。

根拠:

- `docs/02_architecture/ai_training_and_generation_lifecycle.md:54-56`
- `docs/02_architecture/ai_generation_artifact_contract.md:221-235`
- `docs/02_architecture/ai_generation_artifact_contract.md:256-264`

## 3. 何が入っているか

現行Manifest:

`.runtime/ai_lifecycle/generations/phase19_aq_accepted_generation_641e6e313543f013/accepted_generation_manifest.json`

| 項目 | 何を表すか | Runtimeが直接使うか | 必須 |
| --- | --- | --- | --- |
| `generation_id` | 承認済みモデルセットのID | Yes | Yes |
| `candidate_member` | 候補抽出モデル、scaler、calibration、特徴量順、hash | Yes | Yes |
| `opportunity_member` | 機会評価モデル、scaler、calibration、CandidateTop50依存、特徴量順、hash | Yes | Yes |
| `scaler_hashes` | 世代に固定されたscalerのhash | Yes | Yes |
| `schema_hashes` / `feature_order_hash` | 特徴量の形と順序 | Yes | Yes |
| `dataset_revision_ids` / `split_ids` | 学習・検証に使ったデータ版と分割 | No、検査・監査用 | Yes |
| `runtime_baseline_ref` | 運用監視用baseline | 主に検査用 | Yes |
| `accepted_decision_id/hash` | Human Acceptanceの決定記録 | 検査用 | Yes |
| `accepted_at` | 承認された時刻 | Yes | Yes |
| `effective_from` | 使い始めてよい時刻 | Yes | Yes |
| `effective_until` / `revoked_at` / `superseded_at` | 失効・取消・置換 | Yes if present | Optional |

Hashやschemaは「ファイル名がそれっぽいから使う」を防ぐためにあります。実装ではmodel/scaler/calibrationのhash、特徴量順、manifest hashを検査し、合わなければBUY側を止めます。

根拠:

- `src/ai_fund_lab_v2/runtime_v2/accepted_generation_consumer_adapter.py:70-110`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/generation_bound_inference.py:72-125`

## 4. どう作られ、どうAcceptされるか

既存設計の流れ:

```text
学習・生成
-> Generation Candidate
-> Human Review
-> Accepted Decision
-> Accepted Generation Manifest
-> Runtime Transition
-> Runtime利用可能
```

Generation Candidateは「候補」です。モデル、scaler、calibration、validation、dataset revision、split、policy、schema、lineage hashをまとめますが、この時点ではRuntimeが使ってよいものではありません。

Accepted Decisionは「人が確認して承認または保留にする決定」です。現行Artifactでは:

- reviewer: `user:negishi`
- reviewed_at: `2026-07-20T00:00:00+09:00`
- decision: `APPROVE`
- codex_is_reviewer: `false`

つまりCodexは証跡をmaterializeしていますが、Human Reviewerではありません。

実装:

- `src/ai_fund_lab_v2/ai_lifecycle/aq_authority_decision.py:313-354`
- `src/ai_fund_lab_v2/ai_lifecycle/aq_authority_decision.py:357-420`

## 5. Human Acceptanceとは

Human Acceptanceは、自動validationがPASSしただけで勝手に運用入りする仕組みではありません。

Phase19のAccepted Generation entryでは、少なくとも次の証跡が確認対象です。

- Candidate Corrective Re-evaluation PASS
- Opportunity Global Safety/Sanity Gate PASS
- Opportunity Selection Utility Gate PASS
- Dual Gate PASS
- Independent Review PASS
- Unified Generation binding PASS
- Schema PASS
- Hash PASS
- Runtime Baseline PASS
- Freshness Metadata PASS
- Accepted Materializer Compatibility PASS
- Authority History Path PASS

Accept後にAccepted DecisionとAccepted Generation Manifestはできます。ただし、それだけではRuntime Switch、BUY restart、Broker Writeは許可されません。現行Accepted Decisionにも `runtime_transition_authorized=false`、`buy_restart_authorized=false`、`broker_write_authorized=false` と記録されています。

## 6. accepted_at / effective_from

`accepted_at` は「承認された時刻」です。現行実装では `ACCEPTED_AT = 2026-07-20T00:00:00+09:00` がAccepted DecisionとAccepted Generation Manifestに記録されます。

`effective_from` は「このモデルセットを使い始めてよい時刻」です。設計上は `accepted_at` と別項目です。現行AQ実装では `effective_from` も `ACCEPTED_AT` と同じ値に設定されています。

違いの例:

```text
7月20日に人が承認する: accepted_at = 7月20日
7月21日の朝から使う指定にする: effective_from = 7月21日
```

このような分離は概念上はフィールドとして可能です。ただし現行AQ実装は別日指定の引数を持たず、同じ値を入れています。

## 7. Productionでの使い方

Productionの日次運用では、毎日新しいGenerationを作るわけではありません。毎日Human Acceptが必要なわけでもありません。

日次の流れ:

```text
朝のRuntime開始
-> Accepted Generation Resolver
-> 承認済みで、まだ有効なGenerationを選ぶ
-> model / scaler / schema / hashを検査
-> AI判断
-> Strategy
-> Planning
```

Dataset更新とAI Generation更新は別です。新しい市場データが入っても、すぐ新モデルになるとは限りません。既存のAccepted Generationは、freshness、drift、compatibility、safety gateが許す限り継続利用できます。

根拠:

- `docs/02_architecture/ai_training_and_generation_lifecycle.md:170-194`
- `docs/02_architecture/ai_training_and_generation_lifecycle.md:221-225`

## 8. business dateと比較する理由

Business Dateは「その運用日」です。たとえば2026-07-10の朝に運用するなら、その日にまだ承認されていないモデルセットを使ってはいけません。

そのため、business date付きResolverでは次を確認します。

```text
accepted_at <= business_date
effective_from <= business_date
```

もし2026-07-20に承認されたものを2026-07-10の運用判断に使うと、7月10日時点ではまだ存在しなかった承認を使ったことになります。これは未来情報の利用です。

実装:

- `src/ai_fund_lab_v2/runtime_v2/accepted_generation_resolver.py:652-668`

## 9. Historicalでの使い方

Historical Runtimeの目的は、単独のAI backtestではありません。Production/Demo/Paperと同じRuntime Contractを使い、外部Broker WriteだけをHistorical Simulated Brokerに置き換えて、accepted Runtime v2をhistorical dataで評価することです。

根拠:

- `docs/02_architecture/historical_runtime_test_contract.md:25-27`
- `docs/02_architecture/historical_runtime_test_contract.md:56-66`

ただし、HistoricalでAccepted Generationをどう選ぶかには未定義部分があります。

定義済み:

- Historical data / featuresはhistorical business dateに対して未来行を使ってはいけない。
- Runtimeが使うmodel/scaler/schemaはAccepted Manifestで固定される。
- Historicalの結果はProduction/Demoの取引Authorityにはならない。

未定義:

- 2022年Historicalで、2026年にHuman AcceptedされたGenerationを固定して評価してよいのか。
- 2022年当時にAcceptedされていたGenerationが必要なのか。
- 2022年時点のデータだけでGenerationを再生成するのか。

## 10. 2022年テストとの関係

2022年Historical Testについて、既存設計書から断言できるのは次だけです。

```text
現在のRuntime v2本線に近い形で、
historical dataを使い、
外部Broker Writeなしで、
長期運用の整合性を評価する。
```

一方で、Accepted Generationの選び方は未定義です。

Phase23-LのProduction date-local ruleをそのまま使うなら、2022年にはcanonical `.runtime` 上でeligibleなAccepted Generationがありません。現行Accepted Generationは `accepted_at/effective_from=2026-07-20` だからです。

## 11. Phase23-L / Mで何が問題になったか

Phase23-Lの修正:

```text
修正前:
現在のAccepted Generation pointer中心に検索していた

修正後:
business dateが指定されたら、履歴とmanifest directoryも見て、
その日までに承認済み・有効なGenerationを選ぶ
```

これはProduction/Demoの「その日にはまだ承認されていないモデルを使わない」という用途では正しいです。

Phase23-MのGap:

```text
本番で使うGenerationの選び方
```

と、

```text
現在のStrategyを過去相場で評価するときのGenerationの選び方
```

が、同じルールでよいのか未定義でした。

## 12. 設計と実装の対応

| 概念 | 設計書 | 実装ファイル | Runtime Artifact | 説明 |
|---|---|---|---|---|
| Generation Candidate | `ai_generation_artifact_contract.md:221-223` | `ap_runtime_materialization.py`, `aq_authority_decision.py` | `.runtime/ai_lifecycle/generations/phase19_al_unified_generation_.../generation_manifest.json` | Review対象。Runtime用ではない |
| Accepted Decision | `ai_generation_artifact_contract.md:225-235` | `aq_authority_decision.py:313-354` | `accepted_decision.json` | Human承認/保留の決定 |
| Accepted Generation | `ai_generation_artifact_contract.md:256-284` | `aq_authority_decision.py:357-420` | `accepted_generation_manifest.json` | Runtimeが使えるモデルセット |
| `accepted_at` | `ai_generation_artifact_contract.md:284` | `aq_authority_decision.py:13-15,327-330,375` | pointer / decision / manifest | 承認時刻 |
| `effective_from` | `ai_generation_artifact_contract.md:266-284` | `aq_authority_decision.py:406` | pointer / manifest | 使用開始可能時刻 |
| Resolver | `ai_training_and_generation_lifecycle.md:223-225` | `accepted_generation_resolver.py:77-89,284-380` | pointer / history / manifest | 使う世代を選ぶ |
| Human Review | `ai_generation_artifact_contract.md:221-235` | `aq_authority_decision.py:327-350` | `accepted_decision.json` | reviewerは人、Codexではない |
| Revocation | Security/Integrity + resolver closure | `accepted_generation_resolver.py:672-688`, `rollback_revoke.py` | 現行revoked artifactなし | 取消時に選ばないための契約 |
| Supersede | Security/Integrity + resolver closure | `accepted_generation_resolver.py:672-688` | 現行superseded artifactなし | 置換済みなら選ばない |
| Bootstrap | `ai_training_and_generation_lifecycle.md:88-118` | `bootstrap_generation.py`, `aq_authority_decision.py` | current manifest `previous_generation_ref=null` | 最初のAccepted Generation作成流れ |

## 13. 不明・未定義事項

- Historical 2022で使うAccepted Generation選択ルール。
- Production Acceptance TimeとHistorical Evaluation Timeを分けるかどうか。
- `accepted_at` と `effective_from` は設計上別だが、現行AQ実装では同値固定。
- 設計書の保存先例は `.runtime/ai_lifecycle/accepted_generations/<id>/` だが、現行canonical実体は `.runtime/ai_lifecycle/generations/<id>/accepted_generation_manifest.json`。
- Revoked / Supersededの拒否ロジックはあるが、現行canonicalにrevoked/superseded generation実体は確認できない。

## Evidence

Evidence directory:

`reports/phase23_n_accepted_generation_design_and_implementation_explanation_audit/`

Machine report:

`reports/phase_reports/phase23_n_accepted_generation_design_and_implementation_explanation_audit.json`

## Not Performed

以下は実施していません。

```text
コード修正
設計変更
Historical Authority Scope決定
Resolver変更
Manifest Schema変更
Bootstrap実装
データmaterialization
10BD / 20BD / 1y / 3y / 4yテスト
Runtime Switch
Broker Write
Production Submit
Demo Submit
```
