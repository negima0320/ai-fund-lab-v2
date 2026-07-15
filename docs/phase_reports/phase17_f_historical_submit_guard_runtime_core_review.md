# Phase17-F Historical Submit Guard Runtime Core Review

## Current Guard Behavior
現行 `run_submit_preflight()` は `demo/demo` のみを許可する。直接条件は `src/ai_fund_lab_v2/runtime_v2/submit/guards.py:120-121` の `environment != "demo" or pending_plan.environment != "demo"` で、正式な `historical/historical` も `environment guard failure` になる。

## Historical Blocker Reproduction
- `demo/demo`: `approved`
- `historical/historical`: `environment guard failure`
- `production/production`: `environment guard failure`
- `demo/historical`: `environment guard failure`
- `historical/demo`: `environment guard failure`

## Guard Responsibility Analysis
Submit Guardの責務は、Environment判定とBroker capability判定を分けたうえで、Approval / Policy / Safety / Pending validity / Duplicate / Temporal / Cash / Quantityを通常どおり評価すること。HistoricalだけGuardを迂回する案は不採用。

## Environment Identity Analysis
- Demo: `runtime_environment=demo`, `pending_environment=demo`, `broker_environment=tachibana_demo`, Demo adapter。
- Historical: `runtime_environment=historical`, `pending_environment=historical`, `run_type=HISTORICAL`, `broker_environment=historical_simulated`, `adapter=HistoricalSubmitAdapter`, `broker_write=false`, `external_delivery=false`, explicit `business_date/evaluation_time`。
- Production: `runtime_environment=production`, `pending_environment=production`, `broker_environment=tachibana_production`。Phase17-Fでは緩和しない。

## Pending Environment Analysis
Historical Pendingは `pending.environment=historical` が正しい。`demo` 偽装、変換、書き換えは禁止。`promote_order_plan_to_pending()` はenvironmentを保持し、readerは `plan.environment == requested environment` を検証しているため、設計上は一貫可能。

## Compared Options
- Option A Allowed Environment Matrix: `ACCEPT_AS_BASE`
- Option B Guard Core + Environment Policy分離: `ACCEPT_AS_STRUCTURE`
- Option C Composition PreflightをGuard前に追加: `REJECT`。Guard bypass化する。
- Option D Historical Submitを5BDから外す: `REJECT`。Phase17目的を満たさない。

## Recommended Design
Option A+B。通常Submit Guardに明示的なEnvironment Matrixを導入し、共通Guard条件はそのまま維持する。単純な `environment in {"demo", "historical"}` ではなく、runtime/pending/broker/adapter/write/external/temporal identityをまとめてfail-closed検証する。

## Required Runtime Core Change
分類: `LIMITED_RUNTIME_CORE_AMENDMENT`

対象:
- `src/ai_fund_lab_v2/runtime_v2/submit/models.py`: Add an immutable SubmitEnvironmentGuardContext or equivalent fields carrying runtime_environment, pending_environment, broker_environment, adapter_type, run_type, broker_write, external_delivery, business_date, evaluation_time.
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`: Replace demo-only condition with fail-closed environment matrix validation. Keep all Approval/Policy/Safety/Pending/Duplicate/Temporal/Cash/Quantity checks unchanged.
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`: Build/pass environment guard context from mode and environment_composition; require HistoricalSubmitAdapter for historical; preserve demo path and production prohibition.
- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`: Expose composition manifest fields or adapter diagnostic sufficient for guard context; keep adapter isolated and broker_write=false.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`: Pass resolved composition metadata to Submit Pipeline; no alternate submit path.

## Explicit Unchanged Semantics
- Approval meaning and approved order condition matching
- Safety decision semantics and action block behavior
- Policy consistency and capital deployment semantics
- Duplicate/idempotency and post-send-unknown behavior
- Pending lifecycle and consume semantics
- Cash/quantity calculation meaning
- Production submit acceptance requirements
- Demo submit URL/base-url checks
- Execution Processor/Ledger/Current semantics

## Demo Regression Risk
Risk: `LOW`

Demo rowをEnvironment Matrix内に移すだけにし、既存 base_url / demo adapter / safety / policy / duplicate の意味を変えない。

## Production Regression Risk
Risk: `LOW_IF_MATRIX_FAILS_CLOSED`

ProductionはPhase17-Fで緩和しない。productionにHistorical adapterを注入したらHALT。

## Contract Amendment Draft
正式改定は今回行わない。Draft points:
- Define Submit Guard environment matrix for demo/historical/production.
- Define Historical Pending identity as pending.environment=historical.
- Define broker_write=false as no external broker write, not no internal Runtime state transition.
- Bind HistoricalSubmitAdapter to broker_environment=historical_simulated and formal composition only.
- State environment mismatch and adapter mismatch are HALT.
- State Demo/Production semantics remain unchanged and no cross-adapter composition is allowed.

## Implementation Scope
Phase17-Gで、SubmitEnvironmentGuardContext相当、Environment Matrix validation、Pipelineからcomposition metadataの受け渡し、Historical adapter binding検証、関連テストを実装する。

## Regression Test Plan
- demo/demo normal Submit Guard still allows approved MARKET order
- demo pending environment mismatch still HALT/BLOCK
- historical/historical with formal composition reaches HistoricalSubmitAdapter.preflight
- historical without HistoricalSubmitAdapter HALT
- historical with broker_write=true HALT
- historical with external_delivery=true HALT
- historical with missing business_date/evaluation_time HALT
- historical with Tachibana demo/production adapter HALT
- production without explicit production acceptance remains blocked
- production with HistoricalSubmitAdapter HALT
- duplicate submit behavior unchanged
- post-send-unknown auto resubmit unchanged
- safety blocked submit never calls adapter
- policy mismatch blocks before adapter
- approval/order condition mismatch blocks before adapter

## Acceptance Gates
- `HISTORICAL_GUARD_REQUIREMENT_UNDERSTOOD`: `PASS`
- `DEMO_ONLY_GUARD_ORIGIN_IDENTIFIED`: `PASS`
- `SAFE_ENVIRONMENT_MATRIX_DEFINED`: `PASS`
- `HISTORICAL_PENDING_IDENTITY_DEFINED`: `PASS`
- `HISTORICAL_ADAPTER_BINDING_DEFINED`: `PASS`
- `BROKER_WRITE_FALSE_SEMANTICS_DEFINED`: `PASS`
- `SAFETY_APPROVAL_POLICY_UNCHANGED`: `PASS`
- `DEMO_SEMANTICS_UNCHANGED`: `PASS`
- `PRODUCTION_SEMANTICS_UNCHANGED`: `PASS`
- `NO_GUARD_BYPASS`: `PASS`
- `NO_ALTERNATE_SUBMIT_PATH`: `PASS`
- `REGRESSION_PLAN_COMPLETE`: `PASS`
- `ROLLBACK_DEFINED`: `PASS`

## Rollback
Revert the limited environment matrix/context changes and restore demo-only guard. Because changes are confined to Submit Guard context/matrix and pipeline metadata plumbing, rollback should not touch Pending, Approval, Policy, Safety, Ledger, Current, or adapters.

## Blocking Findings
なし。レビューとしては限定Runtime Core改定方針を確定可能。

## Non-blocking Findings
- `implementation_pending`: Phase17-F is review-only; implementation is deferred to Phase17-G.
- `contract_formal_amendment_pending`: Contract amendment draft is included; formal edit is deferred.

## 作成・更新ファイル
- `docs/phase_reports/phase17_f_historical_submit_guard_runtime_core_review.md`
- `reports/phase_reports/phase17_f_historical_submit_guard_runtime_core_review.json`

## 実行した検証
- isolated current environment matrix reproduction: `PASS`
- existing targeted regression tests: `PASS` (27 passed in 3.74s)
- test inventory: `PASS`

## 実行していない操作
- `Submit Guard変更`
- `Submit Pipeline変更`
- `Pending変更`
- `Historical Adapter実装`
- `Execution Provider実装`
- `Contract正式改定`
- `Trading State reset`
- `Current/Ledger/Pending/Runtime State mutation`
- `Historical Submit`
- `Historical Execution`
- `5BD実行`
- `Tachibana API`
- `Demo submit`
- `Production access`
- `Feature生成`
- `Canonical更新`
- `AI再学習`

## Final Judgment
`PHASE17_F_LIMITED_RUNTIME_CORE_AMENDMENT_ACCEPTED`

## Recommended Next Prefix
`Phase17-G` - Historical Submit Guard and Minimal Fill Model Implementation
