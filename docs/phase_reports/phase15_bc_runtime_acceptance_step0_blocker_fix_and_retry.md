# Phase15-BC Runtime Acceptance Step0 Blocker Fix and Evidence Retry

## 1. Executive Summary

Phase15-BC fixed the Phase15-BB Market Refresh regular-path contract error and re-ran Step0 Evidence without executing Morning.

Final judgment:

```text
STEP0_REVIEW_REQUIRED
```

The B1 implementation blocker is fixed: `--job market_refresh` no longer fails with:

```text
'RuntimeV2MarketRefreshResult' object has no attribute 'latest_expected_trading_date'
```

After the fix, the regular CLI path completed with exit code `20` and produced manifest / Market Evidence / latest pointer / report artifacts. It correctly classified the current evidence as `STALE` / `REVIEW_REQUIRED` rather than raising an implementation exception.

Step0 is not ready for Morning because Market / Quote, Broker Snapshot, Current Valuation, Safety, Feature Consumer Readiness, and Data Readiness still do not satisfy the Morning start conditions.

## 2. Scope and Safety Boundaries

Executed scope:

- Read
- Minimal Contract Fix
- Validate
- Evidence Retry
- Review

Not executed:

- Morning
- Submit
- Execution
- Broker Write
- Approval Apply
- Pending mutation
- Current Apply
- Notification Send
- launchd change
- Production Runtime mutation
- External API Fetch

`notification-mode=payload-only` was used for all Runtime CLI evidence commands.

## 3. Phase15-BB Blockers

| ID | Blocker | BC Status |
|---|---|---|
| B1 | Market Refresh regular path attribute error | `FIXED` |
| B2 | Market / Quote Evidence stale | `REMAINING` |
| B3 | Broker Snapshot missing | `REMAINING` |
| B4 | Current Temporal / Valuation stale | `REMAINING` |
| B5 | Safety `REVIEW_REQUIRED` | `REMAINING` |
| B6 | Feature Consumer Readiness review-required | `REMAINING` |

## 4. Root Cause Analysis

Root cause for B1:

```text
RuntimeV2MarketRefreshResult did not expose latest_expected_trading_date,
while the CLI manifest writer expected market_refresh_result.latest_expected_trading_date.
```

The inner Market / Quote Evidence producer already had the formal temporal fields:

- `runtime_business_date`
- `market_date`
- `latest_expected_trading_date`
- `latest_available_market_date`

The missing field was only in the outer `RuntimeV2MarketRefreshResult` contract returned by `run_runtime_v2_market_refresh_pipeline()`.

This was an implementation mismatch, not a design change.

## 5. Contract Review

Source of Truth:

- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/phase_reports/phase15_aw_market_quote_evidence_producer.md`

Contract conclusion:

- `latest_expected_trading_date` is calendar / temporal-resolution derived.
- `latest_available_market_date` is producer-derived.
- `market_date` is the date represented by the Market Evidence.
- `runtime_business_date` is the Runtime target business date.

Therefore, the correct fix is to expose `latest_expected_trading_date` on `RuntimeV2MarketRefreshResult` by propagating it from `MarketEvidenceProducerResult`. The fix does not treat old Market Evidence as fresh and does not collapse expected and available dates.

## 6. Code Changes

Changed:

- `src/ai_fund_lab_v2/runtime_v2/market_refresh/pipeline.py`
  - Added `latest_expected_trading_date` to `RuntimeV2MarketRefreshResult`.
  - Populated it from `market_evidence.latest_expected_trading_date`.

- `tests/runtime_v2/test_phase14e35_market_refresh_actual_feature_generation.py`
  - Added assertions for expected vs available market dates.
  - Updated the CLI fake result to satisfy the formal Market Evidence manifest contract.
  - Added Phase15-BC regression for stale evidence via regular CLI path.

No Safety 기준, freshness 기준, AI logic, trading policy, or architecture expansion was changed.

## 7. Regression Tests

Command:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase14e35_market_refresh_actual_feature_generation.py tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py
```

Result:

```text
14 passed
```

Regression added:

```text
test_phase15bc_cli_market_refresh_stale_evidence_exits_review_required_not_exception
```

Coverage:

- `--job market_refresh` regular CLI path
- process exit
- result object
- manifest temporal fields
- market evidence generation
- latest pointer generation
- stale handling
- expected date vs available date separation

## 8. Market / Quote Evidence Retry

Command:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job market_refresh --business-date 2026-07-10 --submit-enabled false --notification-mode payload-only --runtime-root .runtime --reports-root reports/runtime_v2 --public-reports-root reports/public/runtime_v2 --manifest-root .runtime/runtime_state/run_manifest --log-root .runtime/runtime_state/logs --feature-root .runtime/operations/feature_artifacts --market-refresh-allow-api-fetch false
```

Result:

```text
exit_code=20
final_state=REVIEW_REQUIRED
```

Manifest:

```text
.runtime/runtime_state/run_manifest/2026-07-10/runtime-v2-market_refresh-2026-07-10-20260710T232721.556990+0000.json
```

Evidence:

```text
.runtime/runtime_state/market/2026-07-08/market_evidence.json
.runtime/runtime_state/market/latest.json
```

Key fields:

| Field | Value |
|---|---|
| `runtime_business_date` | `2026-07-10` |
| `market_date` | `2026-07-08` |
| `latest_expected_trading_date` | `2026-07-10` |
| `latest_available_market_date` | `2026-07-08` |
| `market_status` | `STALE` |
| `market_freshness_status` | `STALE` |
| `quote_status` | `STALE` |
| `quote_count` | `0` |
| `publication_status` | `STALE_AFTER_PUBLICATION_WINDOW` |
| `provider_status` | `READY` |

Existing canonical / normalized data check:

```text
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
max target_date = 2026-07-08
```

API Fetch:

```text
not executed
```

Reason:

External API fetch requires explicit permission. Existing canonical / raw / normalized data cannot produce fresh `2026-07-10` Market / Quote Evidence.

## 9. Broker ReadOnly Evidence Review

Existing Broker ReadOnly artifacts:

```text
.runtime/runtime_state/broker_readonly/2026-07-08/tachibana_snapshot.json
.runtime/runtime_state/broker_readonly/2026-07-09/tachibana_snapshot.json
```

No `2026-07-10` broker readonly snapshot exists.

The formal CLI path found in current code is:

```text
--job execution
```

The connected function is:

```text
run_execution_readonly_pipeline()
```

Review result:

- It is a Broker ReadOnly ingestion path.
- It does not submit broker orders.
- However, it appends read-only-derived records to persistent ledger JSONL files.
- The job name and scope are `execution`.

Decision:

```text
Broker ReadOnly was not executed in Phase15-BC.
```

Reason:

Phase15-BC explicitly prohibits `Execution`. The available formal CLI path is not a broker-snapshot-only Step0 producer. Running it would exceed the minimal BC scope.

## 10. Feature Consumer Readiness

Artifact:

```text
.runtime/operations/feature_date_contract/2026-07-10.json
```

Status:

```text
REVIEW_REQUIRED
```

Key fields:

| Field | Value |
|---|---|
| `reason` | `carryover_stale` |
| `requested_feature_date` | `2026-07-10` |
| `selected_feature_date` | `2026-07-08` |
| `latest_available_market_date` | `2026-07-08` |
| `carryover_used` | `true` |
| `freshness_lag_business_days` | `2` |
| `freshness_limit_business_days` | `1` |
| `consumer_ready` | `false` |
| `candidate_schema_status` | `UNKNOWN` |
| `opportunity_schema_status` | `UNKNOWN` |
| `pm_schema_status` | `UNKNOWN` |

Conclusion:

This is not only a derivative symptom of the B1 attribute error. B1 is fixed, but Feature Consumer Readiness remains review-required because the available feature date is stale and consumer schema readiness is not proven for the Morning target.

AI inference was not executed.

## 11. Current Temporal / Valuation Retry

Commands:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job current_temporal_migration --business-date 2026-07-10 --submit-enabled false --notification-mode payload-only --runtime-root .runtime --reports-root reports/runtime_v2 --public-reports-root reports/public/runtime_v2 --manifest-root .runtime/runtime_state/run_manifest --log-root .runtime/runtime_state/logs

PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job current_valuation_refresh --business-date 2026-07-10 --submit-enabled false --notification-mode payload-only --runtime-root .runtime --reports-root reports/runtime_v2 --public-reports-root reports/public/runtime_v2 --manifest-root .runtime/runtime_state/run_manifest --log-root .runtime/runtime_state/logs
```

Artifacts:

```text
.runtime/runtime_state/current_migration/2026-07-10/current_temporal_migration.json
.runtime/runtime_state/current_valuation/2026-07-10/current_valuation_refresh.json
```

Current Temporal:

- `migration_status=LEGACY_DERIVED`
- `review_required=true`
- `apply_requested=false`
- `apply_executed=false`
- `legacy_as_of_used=true`

Current Valuation:

- `status=REVIEW_REQUIRED`
- `reason=current_valuation_review_required`
- `apply_requested=false`
- `apply_executed=false`
- `position_count=5`
- `valued_position_count=0`
- `position_state_as_of=2026-07-09`
- `valuation_as_of=2026-07-08`
- warning: `current_temporal_migration_required_before_valuation`

No Current Apply was performed. Position State, quantity, and average price were not changed by the no-apply valuation retry.

## 12. Safety Retry

Commands:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job safety_evaluation --business-date 2026-07-10 --submit-enabled false --notification-mode payload-only --runtime-root .runtime --reports-root reports/runtime_v2 --safety-reports-root reports --public-reports-root reports/public/runtime_v2 --manifest-root .runtime/runtime_state/run_manifest --log-root .runtime/runtime_state/logs

PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job safety_refresh --business-date 2026-07-10 --submit-enabled false --notification-mode payload-only --runtime-root .runtime --reports-root reports/runtime_v2 --public-reports-root reports/public/runtime_v2 --manifest-root .runtime/runtime_state/run_manifest --log-root .runtime/runtime_state/logs --safety-report-path reports/safety/phase11/2026-07-10_safety_report.json
```

Runtime Safety Decision:

```text
.runtime/runtime_state/safety/latest_safety_decision.json
```

Key fields:

| Field | Value |
|---|---|
| `decision` | `REVIEW_REQUIRED` |
| `block_buy` | `true` |
| `block_sell` | `true` |
| `block_submit` | `true` |
| `reason` | `BROKER_SNAPSHOT_MISSING; QUOTE_MISSING_FOR_MONITOR; POSITION_WITHOUT_BROKER_SNAPSHOT` |
| `generated_at` | `2026-07-10T23:27:49.381308+00:00` |
| `expires_at` | `2026-07-11T03:27:49.379628+00:00` |

Safety was not forced to `SAFE`.

## 13. Data Readiness Retry

Command:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job data_readiness --readiness-scope morning --business-date 2026-07-10 --submit-enabled false --notification-mode payload-only --runtime-root .runtime --reports-root reports/runtime_v2 --public-reports-root reports/public/runtime_v2 --manifest-root .runtime/runtime_state/run_manifest --log-root .runtime/runtime_state/logs --feature-root .runtime/operations/feature_artifacts --feature-date 2026-07-09 --capital-deployment-policy configs/runtime_v2/capital_deployment.json --candidate-model-path .runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl
```

Artifact:

```text
.runtime/runtime_state/data_readiness/2026-07-10/data_readiness.json
```

Status:

```text
overall_status=REVIEW_REQUIRED
```

Breakdown:

| Component | Status |
|---|---|
| Runtime State | `READY` |
| Pending | `READY` |
| Market | `REVIEW_REQUIRED` |
| Market Data | `STALE` |
| Quote | `REVIEW_REQUIRED` |
| Safety | `REVIEW_REQUIRED` |
| Current | `REVIEW_REQUIRED` |
| Current Position | `READY` |
| Current Valuation | `STALE` |
| Candidate Model | `READY` |
| Candidate | `REVIEW_REQUIRED` |
| Opportunity Model | `READY` |
| Opportunity | `REVIEW_REQUIRED` |
| Feature | `REVIEW_REQUIRED` |

Review reasons:

- `BROKER_SNAPSHOT_MISSING; QUOTE_MISSING_FOR_MONITOR; POSITION_WITHOUT_BROKER_SNAPSHOT`
- `candidate_pre_inference_not_ready`
- `consumer_schema_review_required:candidate,opportunity,pm`
- `current_stale`
- `market_evidence_stale_after_publication_window`
- `opportunity_pre_inference_not_ready`

Missing evidence:

- `broker_snapshot`
- `candidate_feature_schema`
- `opportunity_feature_schema`
- `quote_evidence`

## 14. Runtime Mutation Statement

Runtime evidence artifacts were refreshed in `.runtime` and `reports`.

No prohibited mutation was performed:

- Morning: not executed
- Submit: not executed
- Execution: not executed
- Broker Write: not executed
- Approval Apply: not executed
- Pending mutation: not executed; pending stayed `EMPTY`
- Current Apply: not executed; current temporal and valuation were no-apply
- Notification Send: not executed
- Production Runtime mutation: not executed

Code changes were limited to Market Refresh result contract and regression tests.

## 15. Remaining Blockers

1. Market / Quote Evidence remains stale:

```text
latest_expected_trading_date=2026-07-10
latest_available_market_date=2026-07-08
quote_count=0
```

2. Broker snapshot for `2026-07-10` is missing.

3. Broker ReadOnly snapshot-only Step0 CLI is not available; the available formal CLI route is `execution`, which was not executed.

4. Current Valuation remains `REVIEW_REQUIRED` / no-fill.

5. Runtime Safety Decision remains `REVIEW_REQUIRED`.

6. Feature Consumer Readiness remains `REVIEW_REQUIRED`.

7. Data Readiness Morning scope remains `REVIEW_REQUIRED`.

## 16. Step0 Final Judgment

```text
STEP0_REVIEW_REQUIRED
```

Reason:

The implementation blocker from Phase15-BB is fixed, so this is no longer `STEP0_BLOCKED` by the Market Refresh contract error. However, the refreshed Step0 Evidence does not prove that Morning can safely start. Market / Quote freshness, Broker Snapshot, Current Valuation, Safety Decision, Feature Consumer Readiness, and Data Readiness all still require review.

## 17. Recommended Next Prefix

```text
Phase15-BD Runtime Acceptance Step0 Remaining Blocker Resolution
```

Recommended minimal scope:

- Decide whether to permit external API fetch for missing `2026-07-10` market data, or provide fresh canonical data by another approved path.
- Add or identify a broker-snapshot-only ReadOnly Step0 producer that does not run `execution` or append persistent ledger records.
- Regenerate Market / Quote, Feature Consumer Readiness, Current Valuation, Safety, and Data Readiness evidence.
- Re-judge Step0 before any Step1 Morning attempt.
