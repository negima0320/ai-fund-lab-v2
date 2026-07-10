# Phase15-AV Runtime Temporal Contract Foundation Implementation

作成日: 2026-07-10

## 目的

Phase15-AVでは、Phase15-AUで正式化した `Runtime Temporal / Freshness Contract` をRuntime v2全体で共通利用できる基盤として実装した。

このPhaseで実装したものはProducerではない。Market Refresh、Broker API、Current更新、Safety実行、Data Readiness実行、Morning、Submit、Executionには接続していない。

## 実装範囲

追加したFoundation:

- `src/ai_fund_lab_v2/runtime_v2/temporal/models.py`
- `src/ai_fund_lab_v2/runtime_v2/temporal/freshness.py`
- `src/ai_fund_lab_v2/runtime_v2/temporal/resolver.py`
- `src/ai_fund_lab_v2/runtime_v2/temporal/adapters.py`
- `src/ai_fund_lab_v2/runtime_v2/temporal/__init__.py`

追加したRegression:

- `tests/runtime_v2/test_phase15av_runtime_temporal_contract_foundation.py`

## TemporalContext

共通Contextとして以下を実装した。

- `runtime_business_date`
- `calendar_date`
- `trading_session_date`
- `latest_expected_trading_date`
- `latest_available_market_date`
- `runtime_timezone`
- `calendar_source`
- `publication_window`
- `grace_period`
- `runtime_mode`
- `broker_environment`

Resolverは `resolve_temporal_context()` に集約した。各Componentが独自に営業日、latest expected、latest available、runtime mode、broker environmentを解決する状態を避けるためのFoundationである。

## Freshness Status

正式Enum `FreshnessStatus` を追加した。

```text
READY
VALID_CARRYOVER
DATA_NOT_YET_AVAILABLE
STALE
MISSING
DATE_MISMATCH
EXPIRED
REVIEW_REQUIRED
HALT
NOT_REQUIRED
```

Status優先順位は以下で実装した。

```text
HALT > REVIEW_REQUIRED > EXPIRED > STALE > DATE_MISMATCH > MISSING > DATA_NOT_YET_AVAILABLE > VALID_CARRYOVER > READY > NOT_REQUIRED
```

## Temporal Comparison API

以下の共通APIを追加した。

- `evaluate_market_freshness()`
- `evaluate_current_position_freshness()`
- `evaluate_current_valuation_freshness()`
- `evaluate_feature_freshness()`
- `evaluate_pending_temporal_status()`
- `evaluate_safety_temporal_status()`
- `worst_freshness_status()`

各APIは `TemporalEvidence` を返す。

## Temporal Schema

共通Schema `TemporalEvidence` を追加した。

```text
expected_date
actual_date
generated_at
expires_at
status
reason
comparison_contract
source
artifact_path
```

これにより、単なる `as_of == business_date` 判定ではなく、「何と何を比較したのか」「なぜそのStatusになったのか」を共通形式で残せる。

## Temporal Models

Current用Model:

```text
position_state_as_of
valuation_as_of
last_execution_date
last_reconciled_at
source_market_date
```

Market用Model:

```text
market_date
latest_expected_trading_date
latest_available_market_date
publication_status
provider_status
```

Runtime State用Model:

```text
runtime_state_date
runtime_operation_state
runtime_state_status
```

## Component Adapter

将来接続用のAdapterを追加した。

- Market
- Feature
- Current
- Broker
- Safety
- Pending
- Data Readiness

これらは既存Producerを呼ばない。すでに読み込まれたpayloadをTemporal Evidenceへ変換するだけである。

## Regression

実施した確認:

```text
python3 -m pytest tests/runtime_v2/test_phase15av_runtime_temporal_contract_foundation.py
PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase15av python3 -m compileall src/ai_fund_lab_v2/runtime_v2/temporal tests/runtime_v2/test_phase15av_runtime_temporal_contract_foundation.py
```

結果:

```text
8 passed
compileall passed
```

確認済み:

- 営業日 market evidence -> `READY`
- 非営業日 previous trading-day evidence -> `VALID_CARRYOVER`
- 配信前 -> `DATA_NOT_YET_AVAILABLE`
- 配信予定時刻超過後 -> `STALE`
- Safety期限切れ -> `EXPIRED`
- Status優先順位 `HALT > REVIEW_REQUIRED > READY`
- Current Temporal Model field保持
- Temporal Resolver同一入力で同一結果

## 非実施事項

このPhaseでは以下を実施していない。

- Market Producer実装
- Quote Producer実装
- Current Migration
- Current Refresh
- Broker API接続
- Safety実行
- Market Refresh
- Feature Refresh
- Data Readiness実行
- Morning
- Submit
- Execution
- Broker Write
- Notification real send
- launchd変更

## Acceptance

このPhaseで閉じたもの:

```text
Runtime
↓
共通Temporal Contract Foundation
```

未接続で残すもの:

```text
Producer
↓
Temporal Foundation
↓
Data Readiness / Safety / Current / Report / Notification
```

これはPhase15-AUで示された後続実装対象である。

## 最終判定

```text
PHASE15AV_RUNTIME_TEMPORAL_CONTRACT_FOUNDATION_COMPLETE
```
