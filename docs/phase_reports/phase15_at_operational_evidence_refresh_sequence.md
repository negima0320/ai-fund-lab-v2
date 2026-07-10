# Phase15-AT Operational Evidence Refresh Sequence / Step0 Recovery Plan

## Purpose

Phase15-AT defines the Operational Evidence Refresh Sequence required to resume Step0 / Step1 Runtime Acceptance after Phase15-AS.

This phase did not execute Market Refresh, Broker API, Safety, Data Readiness, Morning, Submit, Execution, or any write-side operation. It only inspected code paths and existing artifacts to decide which regular Runtime producers must refresh evidence, in which order, and where execution must stop.

Final judgment:

```text
OPERATIONAL_EVIDENCE_PRODUCER_GAPS_FOUND
```

Completion string:

```text
PHASE15AT_OPERATIONAL_EVIDENCE_REFRESH_SEQUENCE_COMPLETE
```

## Current Blocker Matrix

Observed at repository time `2026-07-10` by read-only artifact inspection.

| Evidence | Current Path | Current Status | Required Producer | Regular CLI Job | Can Run Read-Only? | Dependency |
|---|---|---|---|---|---:|---|
| Market Evidence | `.runtime/runtime_state/market/2026-07-10/market_evidence.json` | MISSING | Not confirmed in regular Runtime producer | Gap | Yes, if producer exists | Market / quote data |
| Quote Evidence | Expected inside market evidence `quotes` / quote summary | MISSING | Not confirmed in regular Runtime producer | Gap | Yes, if producer exists | Market data |
| Feature Artifacts | `.runtime/operations/feature_artifacts/2026-07-10/*.parquet` | MISSING for 2026-07-10 | `run_runtime_v2_market_refresh_pipeline` via operations market/feature refresh | `market_refresh` | Yes, with API fetch if needed | J-Quants availability |
| Feature Consumer Readiness | `.runtime/operations/feature_consumer_readiness/2026-07-10.json` | MISSING | Feature date contract / consumer readiness writer | `market_refresh` | Yes | Feature artifacts |
| Broker ReadOnly Snapshot | `.runtime/runtime_state/broker_readonly/2026-07-10/tachibana_snapshot.json` | MISSING | Execution ReadOnly snapshot provider | `execution` | Yes, Broker API read-only | Broker API time window |
| Current SoT | `.runtime/persistent_ledger/state.json` | STALE, `as_of=2026-07-09`, expected `2026-07-10` | Runtime-owned fill projection only confirmed | `execution` only after accepted execution evidence | Partly | Broker snapshot, orders, executions |
| Runtime State | `.runtime/runtime_state/current_state.json` | STALE, `business_date=2026-07-09` | Runtime preflight / state writer path not confirmed as freshness producer | Gap / weak | Yes if connected | CLI preflight |
| Safety Report | `reports/safety/...` | Existing latest generated from stale/missing evidence | Runtime Safety evaluation | `safety_evaluation` | Yes | Market, Broker, Current, Orders, Executions, Runtime State |
| Runtime Safety Decision | `.runtime/runtime_state/safety/latest_safety_decision.json` | REVIEW_REQUIRED; reason `BROKER_SNAPSHOT_MISSING; QUOTE_MISSING_FOR_MONITOR; POSITION_WITHOUT_BROKER_SNAPSHOT`; expired or near-expired risk | Runtime Safety Decision producer | `safety_refresh` | Yes | Fresh Safety Report |
| Candidate Model | `.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl` | EXISTS | Formal Candidate model artifact | Not refreshed in AT | Yes, read-only validation only | None for Step0 |
| Opportunity Model | `reports/opportunity_ai/phase5p/models/opportunity_model.pkl` | EXISTS | Formal Opportunity model artifact | Not refreshed in AT | Yes, read-only validation only | None for Step0 |
| Pending Slot | `.runtime/pending_order_plan/pending_order_plan.json` | READY, `status=EMPTY`, `state=EMPTY` | Pending lifecycle runner | `pending_lifecycle` | Yes | Existing pending slot |

## Evidence Producer Matrix

| Evidence | Producer Confirmed? | Producer / Module | CLI Job | Output | Gap |
|---|---:|---|---|---|---|
| Feature Artifacts | Yes | `runtime_v2.market_refresh.pipeline.run_runtime_v2_market_refresh_pipeline` -> `operations.market_refresh.run_operations_market_refresh` -> `paper_trading.feature_refresh.run_feature_refresh` | `market_refresh` | `.runtime/operations/feature_artifacts/<date>/*.parquet` | None for artifact generation, assuming J-Quants data available |
| Feature Consumer Readiness | Yes | `runtime_v2.market_refresh.feature_date_contract.resolve_feature_date_contract` and `write_feature_consumer_readiness` | `market_refresh` | `.runtime/operations/feature_consumer_readiness/<feature_date>.json` | None for validation; may still REVIEW_REQUIRED if generated schema is wrong |
| Market Evidence | No | Data Readiness expects `.runtime/runtime_state/market/<business_date>/market_evidence.json` | Not confirmed | Required by Data Readiness and Safety | `MARKET_EVIDENCE_PRODUCER_GAP` |
| Quote Evidence | No | Safety reads `market_evidence.json` `quotes` and market summary | Not confirmed | Required by Safety quote monitoring | `QUOTE_EVIDENCE_PRODUCER_GAP` |
| Broker ReadOnly Snapshot | Yes | `runtime_v2.execution.readonly_pipeline.run_execution_readonly_pipeline` via `broker.runtime_v2_readonly_adapter.run_runtime_v2_execution_readonly_snapshot` | `execution` | `.runtime/runtime_state/broker_readonly/<business_date>/tachibana_snapshot.json` | Name is execution job, but it is the regular read-only Broker snapshot path |
| Current SoT Freshness | Partial | `runtime_v2.asset.runtime_owned_fill_projection.project_runtime_owned_fills_to_current` called by execution ReadOnly pipeline when execution acceptance PASS | `execution` | `.runtime/persistent_ledger/state.json` | `CURRENT_FRESHNESS_PRODUCER_GAP` for no-fill / valuation-only day |
| Runtime State Freshness | Partial | CLI preflight consumes `runtime_state/current_state.json`; authoritative fresh producer not confirmed | Regular CLI preflight writes manifest, not clearly current_state | `.runtime/runtime_state/current_state.json` | `RUNTIME_STATE_PRODUCER_GAP` if Safety requires fresh runtime_state |
| Safety Report | Yes | `runtime_v2.safety.evaluation.run_runtime_safety_evaluation` | `safety_evaluation` | Phase11 Safety Report under reports root | Depends on fresh evidence |
| Runtime Safety Decision | Yes | `runtime_v2.safety.producer.produce_runtime_safety_decision` | `safety_refresh` | `.runtime/runtime_state/safety/latest_safety_decision.json` | Must run after Safety Report |
| Data Readiness | Yes | `runtime_v2.data_readiness.evaluate_runtime_data_readiness` | `data_readiness` | `.runtime/runtime_state/data_readiness/<business_date>/data_readiness.json` | Must run after all evidence refresh |
| Pending EMPTY | Yes | `runtime_v2.pending.lifecycle_runner.run_pending_lifecycle_review` | `pending_lifecycle` | `.runtime/pending_order_plan/pending_order_plan.json` | Currently READY / EMPTY |

## Refresh Dependency Graph

Do not skip steps. Do not run a downstream step until the previous step has been reviewed.

```text
Step A
Market / Feature Refresh
  - Generates feature artifacts and Feature Consumer Readiness.
  - Market Evidence / Quote Evidence producer is not confirmed.

Step A-Gate
Confirm:
  - candidate_features.parquet
  - opportunity_feature_input.parquet
  - position_feature_input.parquet
  - feature_consumer_readiness/<feature_date>.json
  - runtime_state/market/<business_date>/market_evidence.json
  - quote evidence inside market_evidence.json

If Market / Quote Evidence is still missing:
  STOP with MARKET_EVIDENCE_PRODUCER_GAP / QUOTE_EVIDENCE_PRODUCER_GAP.

Step B
Broker ReadOnly Refresh
  - Use regular execution job as read-only Broker snapshot producer.
  - No Submit, no Broker Write.

Step B-Gate
Confirm:
  - runtime_state/broker_readonly/<business_date>/tachibana_snapshot.json
  - positions / orders / executions / available quantity where applicable
  - broker environment and capability evidence

Step C
Current / Runtime State Freshness
  - Current direct edit is forbidden.
  - Confirm whether execution job produced runtime-owned fill projection.
  - If no fills and Current remains stale, STOP.

Step C-Gate
If `persistent_ledger/state.json as_of != business_date`:
  STOP with CURRENT_FRESHNESS_PRODUCER_GAP.

Step D
Safety Evaluation

Step E
Safety Refresh

Step F
Data Readiness

Step G
Step1 Morning Review
```

## Exact Operator Command Runbook

Commands below are a plan only. Phase15-AT did not execute them.

Use one command at a time and review generated evidence before moving on.

### Step A: Market / Feature Refresh

Purpose: refresh J-Quants market data, feature artifacts, and Feature Consumer Readiness through the regular Runtime path.

Command:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job market_refresh \
  --business-date 2026-07-10 \
  --runtime-root .runtime \
  --reports-root reports/runtime_v2 \
  --public-reports-root reports/public/runtime_v2 \
  --manifest-root .runtime/runtime_state/run_manifest \
  --log-root .runtime/runtime_state/logs \
  --market-refresh-allow-api-fetch true
```

Expected exit code: `0` if market/feature refresh and consumer readiness pass; `20` if REVIEW_REQUIRED; `10` if blocked.

Generated Evidence:

- `.runtime/operations/feature_artifacts/2026-07-10/candidate_features.parquet`
- `.runtime/operations/feature_artifacts/2026-07-10/opportunity_feature_input.parquet`
- `.runtime/operations/feature_artifacts/2026-07-10/position_feature_input.parquet`
- `.runtime/operations/feature_consumer_readiness/2026-07-10.json`
- `.runtime/runtime_state/run_manifest/2026-07-10/runtime-v2-market_refresh-*.json`

Check fields:

- `feature_refresh_executed`
- `consumer_ready`
- `candidate_schema_status`
- `candidate_missing_columns`
- `opportunity_schema_status`
- `pm_schema_status`
- `generated_feature_artifacts`

PASS condition:

```text
consumer_ready=true
candidate_schema_status=READY
opportunity_schema_status=READY
pm_schema_status=READY
```

REVIEW_REQUIRED condition:

- Candidate 13 columns missing
- Opportunity double-prefix or schema mismatch
- PM input not ready
- Feature Refresh did not execute

Next step condition:

Proceed only if feature consumer readiness is READY and Market / Quote Evidence producer is confirmed or generated.

Stop condition:

If `.runtime/runtime_state/market/2026-07-10/market_evidence.json` is still missing, stop before Broker/Safety:

```text
MARKET_EVIDENCE_PRODUCER_GAP
```

### Step B: Broker ReadOnly Refresh

Purpose: obtain Tachibana Demo read-only snapshot for positions, orders, executions, cash/buying power, and SELL available quantity evidence.

Command:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job execution \
  --business-date 2026-07-10 \
  --submit-enabled false \
  --notification-mode payload-only \
  --runtime-root .runtime \
  --reports-root reports/runtime_v2 \
  --public-reports-root reports/public/runtime_v2 \
  --manifest-root .runtime/runtime_state/run_manifest \
  --log-root .runtime/runtime_state/logs
```

Expected exit code: `0` if read-only snapshot and execution acceptance pass; `20` if REVIEW_REQUIRED.

Generated Evidence:

- `.runtime/runtime_state/broker_readonly/2026-07-10/tachibana_snapshot.json`
- `.runtime/runtime_state/broker_readonly/2026-07-10/snapshot_report.json`
- `.runtime/persistent_ledger/orders.jsonl`
- `.runtime/persistent_ledger/executions.jsonl`
- `.runtime/persistent_ledger/positions.jsonl`
- `.runtime/persistent_ledger/cash.jsonl`

Check fields:

- `snapshot_status`
- `orders_count`
- `executions_count`
- `positions_count`
- `cash_present`
- `execution_acceptance_status`
- `asset_current_written`
- `runtime_owned_projection_status`
- `excluded_broker_position_symbols`

PASS condition:

- Broker snapshot exists
- Broker snapshot is from demo read-only adapter
- Broker-only positions are recorded as evidence, not copied into Current

REVIEW_REQUIRED condition:

- API unavailable
- snapshot missing
- cash/buying power missing
- broker response incomplete
- execution acceptance unavailable

Next step condition:

Proceed only after Broker error triage says error is not an unresolved API/time-window/capability issue.

### Step C: Current / Runtime State Freshness Gate

Purpose: decide whether Step0 can proceed without direct Current edit.

Command:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job data_readiness \
  --readiness-scope morning \
  --business-date 2026-07-10 \
  --feature-date 2026-07-10 \
  --feature-root .runtime/operations/feature_artifacts \
  --runtime-root .runtime \
  --reports-root reports/runtime_v2 \
  --public-reports-root reports/public/runtime_v2 \
  --manifest-root .runtime/runtime_state/run_manifest \
  --log-root .runtime/runtime_state/logs \
  --capital-deployment-policy configs/runtime_v2/capital_deployment.json \
  --stop-on-review-required
```

Expected exit code: `0` only if Step0 evidence is ready. `20` is expected if Current remains stale.

Generated Evidence:

- `.runtime/runtime_state/data_readiness/2026-07-10/data_readiness.json`
- `.runtime/runtime_state/run_manifest/2026-07-10/runtime-v2-data_readiness-*.json`

Check fields:

- `current_actual_as_of`
- `current_expected_as_of`
- `current_status`
- `market_status`
- `quote_status`
- `safety_status`
- `pending_status`
- `pending_slot_status`

PASS condition:

```text
current_actual_as_of=2026-07-10
current_status=READY
```

Stop condition:

If Current remains `2026-07-09`, do not edit JSON. Stop:

```text
CURRENT_FRESHNESS_PRODUCER_GAP
```

### Step D: Safety Evaluation

Purpose: generate Phase11 Safety Report from fresh Runtime evidence.

Command:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job safety_evaluation \
  --business-date 2026-07-10 \
  --runtime-root .runtime \
  --reports-root reports/runtime_v2 \
  --safety-reports-root reports \
  --public-reports-root reports/public/runtime_v2 \
  --manifest-root .runtime/runtime_state/run_manifest \
  --log-root .runtime/runtime_state/logs
```

Expected exit code: `0` if Safety evaluation passes; `20` if evidence requires review; `30` if HALT.

Generated Evidence:

- Phase11 Safety Report
- `.runtime/runtime_state/run_manifest/2026-07-10/runtime-v2-safety_evaluation-*.json`

PASS condition:

- `safety_evaluation_status=PASS`
- no missing/stale Current/Broker/Market/Runtime State evidence

### Step E: Safety Refresh

Purpose: normalize the authoritative Safety Report into Runtime Safety Decision.

Command:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job safety_refresh \
  --business-date 2026-07-10 \
  --runtime-root .runtime \
  --reports-root reports/runtime_v2 \
  --safety-reports-root reports \
  --public-reports-root reports/public/runtime_v2 \
  --manifest-root .runtime/runtime_state/run_manifest \
  --log-root .runtime/runtime_state/logs \
  --safety-report-path <Phase11 Safety Report path from Step D>
```

Expected exit code: `0` if Runtime Safety Decision is ALLOW; `20` if REVIEW_REQUIRED; `30` if HALT.

Generated Evidence:

- `.runtime/runtime_state/safety/latest_safety_decision.json`

PASS condition:

```text
decision=ALLOW
review_required=false
block_buy=false
block_sell=false
block_submit=false
halt_runtime=false
expires_at not expired
```

### Step F: Data Readiness Recheck

Purpose: verify Step0 evidence after all producers have refreshed.

Command:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job data_readiness \
  --readiness-scope morning \
  --business-date 2026-07-10 \
  --feature-date 2026-07-10 \
  --feature-root .runtime/operations/feature_artifacts \
  --runtime-root .runtime \
  --reports-root reports/runtime_v2 \
  --public-reports-root reports/public/runtime_v2 \
  --manifest-root .runtime/runtime_state/run_manifest \
  --log-root .runtime/runtime_state/logs \
  --capital-deployment-policy configs/runtime_v2/capital_deployment.json \
  --stop-on-review-required
```

PASS condition:

```text
data_readiness_status=READY
readiness_scope=morning
candidate_schema_status=READY
opportunity_schema_status=READY
current_status=READY
market_status=READY
safety_status=READY
pending_status=READY
runtime_environment_status=READY
```

### Step G: Step1 Morning Review

Only after Step F PASS.

Command:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job morning \
  --business-date 2026-07-10 \
  --feature-date 2026-07-10 \
  --feature-root .runtime/operations/feature_artifacts \
  --submit-enabled false \
  --notification-mode payload-only \
  --runtime-root .runtime \
  --reports-root reports/runtime_v2 \
  --public-reports-root reports/public/runtime_v2 \
  --manifest-root .runtime/runtime_state/run_manifest \
  --log-root .runtime/runtime_state/logs \
  --capital-deployment-policy configs/runtime_v2/capital_deployment.json \
  --stop-on-review-required
```

Do not run Submit or Execution as part of Step1 Morning Acceptance.

## API Error Triage

When Broker API errors occur, classify in this order before calling it a Runtime bug:

1. API利用可能時間外
2. ログイン可能時間外
3. Demo環境リセット
4. 9000番台銘柄制約
5. Demo口座状態
6. 認証期限
7. endpoint / mode mismatch
8. network / broker maintenance
9. Runtime implementation error

Manifest fields to preserve where possible:

```text
broker_environment
broker_capability
connection_time_window
error_classification
retry_allowed
operator_action
```

Demo restrictions must remain Broker Capability / Broker Evidence. They must not create demo-only Runtime logic.

## Current Freshness Producer Judgment

Question:

```text
Current as_ofを2026-07-10へ更新する正規経路が存在するか
```

Judgment:

```text
CURRENT_FRESHNESS_PRODUCER_GAP
```

Evidence:

- Data Readiness expects `persistent_ledger/state.json as_of == business_date`.
- Existing Current is `as_of=2026-07-09`.
- Execution ReadOnly pipeline can write Current only after accepted execution evidence and runtime-owned fill projection.
- Broker positions/cash are explicitly not copied directly into Current.
- No confirmed regular CLI job updates Current freshness for a no-fill / valuation-only day.

Required follow-up:

Define or implement a regular Runtime-owned Current freshness / valuation producer before Step0 can be declared READY for 2026-07-10.

Forbidden workaround:

- Editing `.runtime/persistent_ledger/state.json`
- Copying broker snapshot into Current
- Changing only `as_of`
- Creating demo-only Current

## Runtime State Producer Judgment

Question:

```text
Safetyが必要とする Runtime State の authoritative producer が接続済みか
```

Judgment:

```text
RUNTIME_STATE_PRODUCER_GAP
```

Evidence:

- Safety evaluation reads `.runtime/runtime_state/current_state.json`.
- Existing runtime state is dated `2026-07-09`.
- CLI preflight records run manifest stages, but a regular producer refreshing `runtime_state/current_state.json` for Safety was not confirmed.
- Phase15-AS suppresses optional legacy preflight warning, but Safety still treats runtime_state freshness as evidence.

Required follow-up:

Clarify whether `runtime_state/current_state.json` is authoritative Safety input. If yes, connect a regular producer. If no, remove it from Safety required evidence or downgrade it explicitly with design evidence.

## Step0 Resume Criteria

Do not try to make Data Readiness READY until all are true:

```text
Market / Quote Evidence fresh
Feature Consumer Readiness ready
Candidate / Opportunity model ready
Current fresh
Safety ALLOW and unexpired
Pending EMPTY
Runtime Environment ready
Broker Evidence present if Safety depends on it
```

## Step1 Resume Criteria

Morning Acceptance may resume only when Data Readiness says:

```text
data_readiness_status=READY
readiness_scope=morning
candidate_schema_status=READY
opportunity_schema_status=READY
current_status=READY
market_status=READY
safety_status=READY
pending_status=READY
runtime_environment_status=READY
```

Even then:

- Submit remains forbidden.
- Execution for order lifecycle remains outside Step1.
- Notification real send remains forbidden.

## Stop Conditions

Stop before Step1 if any is true:

- `MARKET_EVIDENCE_PRODUCER_GAP`
- `QUOTE_EVIDENCE_PRODUCER_GAP`
- `CURRENT_FRESHNESS_PRODUCER_GAP`
- `RUNTIME_STATE_PRODUCER_GAP`
- Feature Consumer Readiness is REVIEW_REQUIRED
- Safety Decision is REVIEW_REQUIRED / HALT / expired
- Pending is not EMPTY before Morning
- Broker API error is untriaged
- Broker snapshot is missing when Safety requires Broker evidence
- Demo restriction is handled by Runtime branch instead of Broker Evidence
- Any operator is tempted to edit Current, Pending, or artifact dates manually

## Prohibited Actions Confirmation

Phase15-AT did not execute:

- Market Refresh
- Feature Refresh
- Broker API connection
- Safety Evaluation / Refresh
- Data Readiness rerun
- Morning
- SELL Planning
- Submit
- Execution
- Broker Write
- Orders
- Notification real send
- launchd change
- Current edit
- Pending edit
- Artifact date rewrite / copy

