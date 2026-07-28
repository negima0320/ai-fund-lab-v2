# Phase22-A Market Context Artifact Foundation

## Primary Judgment

```text
PHASE22_A_REVIEW_REQUIRED
```

Phase22-AのMarket Context Artifact foundationは実装済みである。ただし、Phase21-KでOpen Decisionとして残っているMarket Context threshold / window / source値をCodex判断で確定しなかったため、実J-Quants sourceに対するread-only生成結果は `producer_result_status=REVIEW_REQUIRED` とした。

Design Change Requestは不要である。Blocking gapはない。

## Task Scope

実装した範囲は以下に限定した。

- Market Context schema
- Production共通producer
- J-Quants PIT input resolver
- source lineage / source hash
- deterministic metric calculation foundation
- status taxonomy
- failure contract
- bootstrap contract
- read-only artifact generation
- fixture consumer
- produced-but-not-consumed detection
- short unit / schema / contract / no-leakage tests

Runtime switch、Portfolio Policy接続、PM接続、Ranking変更、Capital変更、Pending/Submit変更、Old Path削除は実施していない。

## Reviewed SoT

- `docs/phase_reports/phase21_k_final_design_freeze_phase21_closure_and_phase22_entry_approval.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/phase_reports/phase22_strategy_architecture_implementation_plan.md`
- `docs/03_ai_design/market_context_design.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- `docs/phase_reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit.md`
- `docs/phase_reports/phase21_j_legacy_retirement_authority_revocation_and_data_decommission_architecture.md`
- `reports/phase21_k_final_design_freeze_phase21_closure_and_phase22_entry_approval/*.json`
- `reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit/*.json`
- `reports/phase21_j_legacy_retirement_authority_revocation_and_data_decommission_architecture/*.json`

## Pre-implementation Investigation

### Existing PIT Input Authority

確認した主な実装経路:

- `src/ai_fund_lab_v2/runtime_v2/market_data_bootstrap.py`
- `src/ai_fund_lab_v2/runtime_v2/market_data_acquisition.py`
- `src/ai_fund_lab_v2/runtime_v2/market_refresh/`
- `src/ai_fund_lab_v2/runtime_v2/artifact_lookup.py`
- `src/ai_fund_lab_v2/data_store/market_data_store.py`
- `src/ai_fund_lab_v2/operations/market_calendar.py`

既存canonical sourceは `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet`、Listed Issuesは `.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet`、Trading Calendarは `.runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet` である。

Historical as-of境界は `runtime_v2/historical_support/asof.py` と `runtime_v2/market_refresh/pipeline.py` 側にある。Phase22-AではHistorical専用分岐を追加せず、Producerは渡されたPIT source pathを読む共通処理に限定した。

### Existing Artifact / Registry Pattern

確認した主な実装経路:

- `schemas/`
- `src/ai_fund_lab_v2/artifact_registry/`
- `src/ai_fund_lab_v2/ai_lifecycle/`
- `src/ai_fund_lab_v2/paper_trading/ai_artifact_adapter.py`
- `docs/02_architecture/artifact_acceptance_contract.md`

canonical hashは既存パターンに合わせ、JSONを `sort_keys=True` かつcompact separatorsでSHA-256化した。Acceptance Contract上、`ACCEPTED`は自動生成禁止のため、Phase22-A artifactは `artifact_lifecycle_status=DRAFT`、`runtime_consumer_eligibility=NOT_ELIGIBLE` に固定した。

### Legacy / Current User

Phase21-I/J evidenceと実コードを突き合わせた結果、Market Context Artifactは現行では `DESIGN_ONLY_NOT_IMPLEMENTED` である。現在の直接・間接consumerは、Opportunity featureのmarket/sector proxy、Runtime market evidence、feature date contract、data readiness、status/summarize readerであり、Phase22-Aではこれらを変更していない。

## Implemented Files

- `src/ai_fund_lab_v2/strategy/__init__.py`
- `src/ai_fund_lab_v2/strategy/market_context.py`
- `schemas/strategy/market_context.schema.json`
- `tests/strategy/test_phase22_a_market_context.py`
- `reports/phase22_a_market_context_artifact_foundation/phase22_a_market_context_artifact_foundation.json`
- `reports/phase22_a_market_context_artifact_foundation/phase22_a_evidence_20260727/*.json`
- `.runtime/strategy_artifacts/market_context/2026-07-14/market_context.json`

## Schema Summary

Schema version:

```text
strategy_market_context.v1
```

必須status taxonomy:

- `artifact_lifecycle_status`
- `source_authority_status`
- `producer_result_status`
- `runtime_consumer_eligibility`

Phase22-Aでは `artifact_lifecycle_status=DRAFT`、`runtime_consumer_eligibility=NOT_ELIGIBLE` をvalidatorで固定した。`authority_status: ACCEPTED` は追加していない。

## Producer Responsibility

Producerは以下のみを行う。

- `business_date`を受け取る
- J-Quants PIT source pathを解決する
- source hashを計算・検証する
- `feature_date <= business_date` とfuture row不使用を検証する
- market metrics foundationを計算する
- 明示threshold policyがある場合のみtaxonomyをPASS化する
- schema validationする
- read-only DRAFT artifactを書き出す

ProducerはBUY/SELL、HOLD/ADD/REDUCE/EXIT、Ranking、Portfolio weight、Capital allocation、Pending、Submit、Registry Accepted化を行わない。

## PIT / Hash / Lineage Contract

Artifactは以下を保持する。

- `business_date`
- `feature_date`
- `as_of`
- `source_artifacts`
- `source_hashes`
- `temporal_safety.point_in_time`
- `temporal_safety.future_leakage_used`
- `artifact_hash`

future row検出時は `producer_result_status=BLOCK` とし、正常artifactとして消費させない。

## Failure Contract

実装済み:

- missing required source -> `REVIEW_REQUIRED`
- threshold config missing -> `REVIEW_REQUIRED`
- source hash mismatch -> `BLOCK`
- future source row -> `BLOCK`
- invalid schema / enum / date / confidence / unsupported schema -> validator `BLOCK`相当の例外
- BLOCK artifact -> fixture consumer拒否

missing sourceをNEUTRALとしてPASSするfallback、hash mismatch warning化、fixed BULL/RANGE fallbackは実装していない。

## Bootstrap Contract

初回artifact不在やthreshold未確定を通常Production PASSとして扱わない。実J-Quants sourceに対する生成artifactは `DRAFT / REVIEW_REQUIRED / NOT_ELIGIBLE` であり、`reason_codes` に `market_context_threshold_config_required` を残す。

## Fixture Consumer

`load_market_context_fixture()` を追加した。Fixture consumerはschemaを読めるが、`for_production=True` では `NOT_ELIGIBLE` artifactを拒否する。Portfolio Policyや売買判断は行わない。

## Produced-but-not-consumed Evidence

`produced_but_not_consumed_evidence()` により、以下をmachine-readableに確認できる。

- `artifact_produced=true`
- `production_consumer_connected=false`
- `runtime_consumer_eligibility=NOT_ELIGIBLE`
- `legacy_authority_active=true`
- `runtime_switch_performed=false`

## Regression Preservation

Phase21-IのStep Gate I-SG-01に対応するproducer/consumer未接続検出を追加した。Phase21-JのRetirement planに従い、旧PathのAuthority revoke、quarantine、delete ready、deleteは行っていない。

## Tests Executed

PASS:

```text
python3 -m pytest tests/strategy/test_phase22_a_market_context.py
```

Result:

```text
5 passed
```

PASS:

```text
PYTHONPYCACHEPREFIX=.runtime/pycache_phase22a python3 -m compileall -q src/ai_fund_lab_v2/strategy
```

REVIEW_REQUIRED:

```text
python3 -m pytest tests/phase12/test_market_calendar.py tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py tests/artifact_registry/test_inventory_helpers.py
```

Result:

```text
10 passed, 1 failed
```

Failure reason:

```text
consumer_schema_review_required:pm
```

This failure occurs in the existing morning runtime fixture before the Phase22-A Market Context code path is imported or consumed.

## Tests Not Executed

Long Historical tests were not executed by Codex.

Not executed:

- 5BD Historical
- 20BD Historical
- 200BD Historical
- 1-year Historical
- 3-year Historical
- Production-equivalent long runtime smoke

## Design Freeze Compliance

No changes were made to Component ownership, Authority ownership, Producer / Consumer ownership, Runtime boundary, Safety boundary, Migration order, Runtime switch sequence, Retirement sequence, Rollback principle, Zombie Detection, or Safe Delete Gate.

## Prohibited-scope Non-modification Confirmation

Confirmed:

- Runtime switch: not performed
- Portfolio Policy production connection: not performed
- PM connection / behavior change: not performed
- Candidate / Opportunity ranking change: not performed
- Capital allocation change: not performed
- Pending / Submit / Approval / Execution / Ledger / Current change: not performed
- Old path deletion: not performed
- Artifact ACCEPTED promotion: not performed

## Legacy Authority Preservation

Legacy Runtime Authority remains active. Old consumers, readers, runtime_test lifecycle, historical adapters, LaunchAgent paths, recovery paths, status/summarize readers, Pending, Submit, Ledger, Current, and Artifact Registry history were not removed or revoked.

## Known Gaps

- Market Context threshold / window / source values remain Open Decisions.
- Actual Runtime connection is intentionally absent and must remain absent until later gates.
- One selected existing morning regression currently reaches `consumer_schema_review_required:pm`; this is recorded as REVIEW_REQUIRED regression evidence, not as Phase22-A code failure.

## Blocking Gaps

None.

## Next Gate Recommendation

```text
Phase22-AA entry ready: YES
Phase22-B entry ready: NO
Runtime switch ready: NO
Legacy retirement ready: NO
```

Phase22-B must not start before Phase22-AA Corporate Event Artifact Foundation is completed.

