# Phase15-AW Market / Quote Evidence Producer Implementation

作成日: 2026-07-10

## 目的

Phase15-AWでは、Runtime Temporal / Freshness ContractとPhase15-AV Temporal Foundationに従い、Runtime v2通常経路でMarket Evidence / Quote Evidenceを生成するProducerを実装した。

Market EvidenceはAI Feature Artifactではない。Safety、Data Readiness、Current valuationが参照する運用証拠である。

## 実装概要

追加:

- `src/ai_fund_lab_v2/runtime_v2/market_refresh/evidence.py`
- `tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py`

更新:

- `src/ai_fund_lab_v2/runtime_v2/market_refresh/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
- `src/ai_fund_lab_v2/runtime_v2/safety/evaluation.py`
- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`

## Canonical Artifact

Producerは以下を生成する。

```text
.runtime/runtime_state/market/<market_date>/market_evidence.json
.runtime/runtime_state/market/latest.json
.runtime/runtime_state/market/history/<market_date>/<content_hash>.json
```

`latest.json` はpointerであり、History Artifactはcontent hash単位で保持する。同一contentの再実行は同じhistory pathへ収束する。

## Schema

Market Evidenceに以下を含めた。

```text
schema_version
runtime_business_date
business_date
market_date
latest_expected_trading_date
latest_available_market_date
generated_at
calendar_source
calendar_status
trading_day
market_status
market_freshness_status
quote_status
market_summary
candidate_universe_market_summary
quotes
data_provider
provider_status
data_not_yet_available
stale
fallback_used
production_equivalent
temporal_evidence
market_temporal_model
expected_publication_window
current_time
publication_status
monitored_symbols
missing_quote_symbols
quote_source
no_feature_artifact_price_derivation
fake_or_default_quote_generated
```

`runtime_business_date` と `market_date` は分離している。

## Quote Schema

Quoteには最低限以下を含める。

```text
symbol
price
price_type
market_date
observed_at
source
freshness_status
adjusted
```

Safety互換のため、以下も保持する。

```text
age_seconds
stale
```

価格はJ-Quants normalized daily quotesから取得する。Feature Artifactから価格を逆算しない。

## Temporal Foundation Integration

利用したFoundation:

- `resolve_temporal_context()`
- `evaluate_market_freshness()`
- `FreshnessStatus`
- `MarketTemporalState`
- `TemporalEvidence`

対応Status:

```text
READY
VALID_CARRYOVER
DATA_NOT_YET_AVAILABLE
STALE
MISSING
DATE_MISMATCH
REVIEW_REQUIRED
```

Publication Windowはハードコードしていない。Producer APIへ `PublicationWindow` が明示された場合のみ、配信前と猶予超過を判定する。

## Runtime Regular Path

`market_refresh` jobの一部としてProducerを接続した。

```text
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --job market_refresh
```

Demo専用job、Phase専用job、fake Runtime branchは作成していない。

## Data Readiness Integration

Data Readinessは正式Market Artifactを読むように更新した。

追加・反映対象:

```text
market_data_status
quote_status
market_summary_status
market_freshness_status
market_date
latest_expected_trading_date
latest_available_market_date
```

Safety理由文字列だけに依存せず、Market Artifactの `quote_status` を一次Evidenceとして扱う。

## Safety Consumer Compatibility

Safety Evaluationは `runtime_state/market/<business_date>/market_evidence.json` を優先し、存在しない場合は `runtime_state/market/latest.json` のpointerを読めるようにした。

正式Market Evidenceは既存Safetyが読む以下のfieldを保持する。

```text
market_summary
candidate_universe_market_summary
quotes
market_date
generated_at
freshness_status
```

Safetyロジック自体は変更していない。

## Report / Notification

Report / Notification payloadへMarket Evidence要約を追加した。

```text
market_evidence_status
market_evidence_reason
market_date
latest_expected_trading_date
latest_available_market_date
quote_count
missing_quote_count
publication_status
next_operator_action
```

Notification real sendは行っていない。

## Controlled Failure

以下をArtifactとして表現する。

| Case | Artifact behavior |
|---|---|
| Data not yet available | `market_status=DATA_NOT_YET_AVAILABLE`, `quotes={}`, `data_not_yet_available=true` |
| Stale | `market_status=STALE`, `stale=true` |
| API error / provider error | `market_status=REVIEW_REQUIRED`, `provider_status=API_ERROR` 等 |
| Missing monitored quote | `quote_status=REVIEW_REQUIRED`, `missing_quote_symbols` |
| Source empty/corrupt | `market_status=REVIEW_REQUIRED` |

Artifact missingと意図的な停止を区別できる。

## Regression

実行:

```text
python3 -m pytest tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py tests/runtime_v2/test_phase15av_runtime_temporal_contract_foundation.py
```

結果:

```text
18 passed
```

保持確認:

```text
python3 -m pytest tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py tests/runtime_v2/test_phase15av_runtime_temporal_contract_foundation.py tests/runtime_v2/test_phase15an_feature_consumer_readiness.py tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py
```

結果:

```text
41 passed
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase15aw python3 -m compileall src/ai_fund_lab_v2/runtime_v2/market_refresh src/ai_fund_lab_v2/runtime_v2/data_readiness.py src/ai_fund_lab_v2/runtime_v2/safety/evaluation.py src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py
```

結果:

```text
passed
```

追加で `tests/runtime_v2/test_phase15ad_runtime_safety_evaluation_regular_path.py` を含めた保持確認では、既存CLI Safety testの1件が `BROKER_SNAPSHOT_STALE` により失敗した。これはCLIが実時刻でBroker snapshot ageを評価する既存の時間依存挙動であり、AWのMarket / Quote Evidence欠落ではない。AWのSafety consumer互換は専用Regressionで確認済み。

## 非実施事項

このPhaseでは以下を行っていない。

- Current schema migration
- Current valuation refresh
- Runtime State Producer
- Safety実行の運用実行
- Morning
- SELL Planning
- Submit
- Execution
- Broker Write
- 注文
- Notification real send
- launchd変更
- Current編集
- Feature値からQuote生成
- mock price生成
- Demo専用Runtime分岐

## Acceptance

閉じたもの:

```text
Market / Quote Evidence Producer
↓
Canonical Artifact
↓
Data Readiness / Safety / Report / Notification Consumer Compatibility
```

未実施で残すもの:

```text
Current valuation refresh
Safety temporal dependency hash enforcement
Runtime State Producer
Full Runtime Acceptance execution
```

## 最終判定

```text
PHASE15AW_MARKET_QUOTE_EVIDENCE_PRODUCER_COMPLETE
```
