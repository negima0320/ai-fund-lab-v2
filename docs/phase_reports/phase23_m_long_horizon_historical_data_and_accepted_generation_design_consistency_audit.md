# Phase23-M: Long-Horizon Historical Data and Accepted Generation Design Consistency Audit

## Primary Judgment

`PHASE23_M_LONG_HORIZON_HISTORICAL_ACCEPTED_GENERATION_AUTHORITY_SCOPE_GAP_CONFIRMED`

Phase23-Lで実装された `accepted_at <= business_date` / `effective_from <= business_date` のPIT選択は、Production / DemoのAccepted Generation Authorityとしては妥当です。

ただし、それをそのままLong-Horizon Historical Runtimeへ適用すると、canonical `.runtime` 上のAccepted Generationが `2026-07-20` 以降にしか存在しないため、2022〜2026のHistorical Testは成立しません。これは、過去Phaseで明文化された「accepted Runtime v2 control systemをJuly 2021 onwardのhistorical dataで評価する」設計と衝突します。

したがってPhase23-Mでは、コード修正は行わず、Historical Accepted GenerationのAuthority Scopeを設計判断待ちとして止めます。

## Secondary Judgments

- `ACCEPTED_GENERATION_IS_RUNTIME_CONSUMABLE_MODEL_GENERATION_AUTHORITY_NOT_SOURCE_CODE`
- `PRODUCTION_PIT_ACCEPTANCE_RULE_IS_VALID`
- `PHASE23_L_IS_PRODUCTION_PIT_CONSISTENT_BUT_HISTORICAL_LONG_HORIZON_INCOMPLETE_OR_MISAPPLIED`
- `NO_CANONICAL_PIT_ELIGIBLE_ACCEPTED_GENERATION_EXISTS_BEFORE_2026_07_20`
- `LONG_HORIZON_HISTORICAL_DESIGN_EXISTS`
- `HISTORICAL_GENERATION_AUTHORITY_SCOPE_REQUIRES_DESIGN_DECISION`
- `LONG_HISTORY_AI_DATA_EXISTS_BUT_COMMON_RUNTIME_OHLCV_IS_SHORT`
- `NO_CODE_FIX_APPLIED`
- `NO_RUNTIME_SWITCH`
- `NO_BROKER_WRITE`
- `NO_LONG_RUNTIME_TEST`

## Accepted Generationの設計定義

Accepted GenerationはSource Codeではありません。Runtimeが読んでよいモデル世代を、Human Review / Accepted Decision、component hash、dataset revision、split policy、feature schema、calibration、validation、runtime baseline、generation-bound scalerで束ねたRuntime Authorityです。

根拠:

- `docs/02_architecture/ai_training_and_generation_lifecycle.md:54`: Accepted DecisionがGeneration CandidateをRuntime消費可能なAccepted Generationへ昇格する。
- `docs/02_architecture/ai_training_and_generation_lifecycle.md:56`: Runtimeはtrainせず、Dataset Revision/Splitを直接読まず、Accepted Generation Resolver Authorityだけを消費する。
- `docs/02_architecture/ai_generation_artifact_contract.md:264`: Accepted Generation Manifestが唯一のRuntime-consumable generation artifact family。
- `docs/02_architecture/ai_generation_artifact_contract.md:389`: Authority解決/検証不能時はfail closed。

## Production Authority Contract

Production / Demoでは、Accepted Generationはoperational timeに対する正式なHuman Acceptance Authorityです。`accepted_at` と `effective_from` が対象Business Dateより未来の世代を使うことはできません。

この意味で、Phase23-LのProduction PIT修正は正しいです。latest fallback、Promotion Candidate fallback、legacy component fallbackは不可です。

## Historical Runtime Authority Contract

Historical RuntimeはProduction-common Runtime Contractを使います。独自backtest engineではなく、normal Runtime root / normal CLI / normal mainlineを使い、外部Broker WriteだけをHistorical Simulated Brokerに置き換えます。

根拠:

- `docs/02_architecture/historical_runtime_test_contract.md:27`: Historical RuntimeはProduction/Demo/Paperと同じaccepted Canonical Data Contract、Feature Producer、Feature Schema、AI Artifact、AI Decision Contract、Runtime v2 Mainlineを消費する。
- `docs/02_architecture/historical_runtime_test_contract.md:64`: July 2021 onwardのhistorical dataでaccepted Runtime v2 control systemを評価する。

一方で、`docs/02_architecture/autonomous_ai_operations_architecture.md:806` は、Historical Runtimeがfuture Production accepted generationをpast business dateに適用してはならない、と明記しています。

ここが現在の設計衝突点です。

## 2022〜2026年の長期Historical設計

長期Historical自体は設計されています。Phase22計画にも `2022-09-01` 開始の5BD例があり、Phase20 handoffには2022起点の5BD/20BD/245BD関連証跡が記録されています。

ただし、現行canonical Accepted Generation Authorityを厳密にbusiness-date-local acceptanceとして解釈すると、2026-07-20以前は全日 `NO_ACCEPTED_GENERATION_EXISTED_AS_OF_DATE` になります。

## 過去データ設計

ローカル棚卸し結果:

| Component | Status |
| --- | --- |
| Common Runtime OHLCV | `.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet` は `2026-06-01`〜`2026-06-26` の20営業日 |
| Listed Issues PIT snapshots | `2021-07-16`〜`2026-07-15`、1221 snapshots |
| Trading Calendar | `2021-07-16`〜`2026-07-15` |
| Long-history candidate features | `2021-06-14`〜`2026-06-12` |
| Long-history candidate dataset | `2021-06-14`〜`2026-05-15` |
| AI lifecycle opportunity dataset | `2021-09-08`〜`2026-05-15` |
| Canonical Accepted Generation | 1件のみ、`accepted_at/effective_from=2026-07-20T00:00:00+09:00` |

つまり、学習・長期特徴データは存在するが、4年Historical Runtimeをそのまま走らせるためのcommon Runtime OHLCVとdaily operational featuresは未完了です。

## ユーザーの過去懸念への設計回答

懸念は妥当です。

「2026-07-20以前にAccepted Generationがないなら2022〜4年Historicalは不可能ではないか」という問いに対して、現時点の答えは次です。

- Phase23-LのProduction PIT契約をそのままHistoricalに適用するなら、4年テストは不可能。
- 過去PhaseのHistorical設計どおり、accepted Runtime artifactをrun-level authorityとしてhistorical dataに当てるなら、4年テストは概念上可能。
- ただし、その場合も「future Production accepted generation禁止」と矛盾しないHistorical Evaluation Authorityの明文化が必要。

## Phase23-Lとの整合性

分類:

`B_PLUS_E_WITH_C_MATERIALIZATION_GAP`

| Pattern | Judgment | Reason |
| --- | --- | --- |
| A: true accepted history required | `PARTIALLY_SUPPORTED` | AE-4はfuture Production accepted generation禁止を明記 |
| B: Phase23-LがProduction Acceptance契約をHistoricalへ誤適用 | `SUPPORTED` | 既存Historical設計はaccepted Runtimeをhistorical dataで評価する意図 |
| C: 設計あり、materialization欠損 | `SUPPORTED` | Bootstrap/Accepted Generation設計はあるが、過去日付のauthority履歴はない |
| D: dataあり、runtime未接続 | `PARTIALLY_SUPPORTED` | Listed/AI dataはあるがcommon Runtime OHLCVは短い |
| E: design gap | `SUPPORTED` | Production Acceptance TimeとHistorical Evaluation Timeが未分離 |

## 4年テスト成立可否

| Scenario | Feasibility |
| --- | --- |
| Phase23-Lのdate-local `accepted_at/effective_from`契約 | `NOT_FEASIBLE` |
| Historical run-level accepted artifact evaluation契約を正式化 | `CONDITIONALLY_FEASIBLE` |
| 過去日付ごとのHuman Acceptance履歴をbackfill | `NOT_CURRENTLY_AVAILABLE` |
| latest fallbackで実行 | `PROHIBITED` |

現時点のGateは `NOT_READY_FOR_4Y` です。

## Implementation Gap

コード修正は行っていません。

理由は、Production-commonな修正を一意に決めるには、次の設計判断が必要だからです。

```text
Historical RuntimeのAccepted Generation Authorityは、
Production Acceptance Timeに対するdate-local authorityなのか、
それともHuman Accepted済みRuntime artifactをHistorical Evaluation Timeで評価するrun-level authorityなのか。
```

この判断なしにresolverへHistorical専用ifやlatest fallbackを入れることは禁止事項に触れます。

## Evidence

Evidence directory:

`reports/phase23_m_long_horizon_historical_data_and_accepted_generation_design_consistency_audit/`

Machine:

`reports/phase_reports/phase23_m_long_horizon_historical_data_and_accepted_generation_design_consistency_audit.json`

## Short Tests

実施:

```text
JSON validation for Phase23-M evidence/report files
```

Runtime tests are not run.

## Not Run

以下は実施していません。

```text
10BD
20BD
1y
3y
4y
Production Submit
Demo Submit
Broker Write
Runtime Switch
```

## Recommended Next Task

`Phase23-N: Historical Accepted Generation Evaluation Authority Design Decision`

決めるべきこと:

- Historical Evaluation AuthorityをProduction Acceptance Authorityと分離して定義するか。
- 分離する場合、Accepted Generation Manifestに `historical_evaluation_authority` / `evaluation_effective_range` / `artifact_acceptance_time` / `replay_business_date_scope` を追加するか。
- 分離しない場合、2022〜2026 long-horizon Historicalは正式に不可とし、過去日付ごとのAccepted Generation履歴materializationを要求するか。
