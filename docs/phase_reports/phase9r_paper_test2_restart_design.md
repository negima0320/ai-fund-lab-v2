# Phase9R-A Paper Test 2 Restart Design

- status: DESIGN_COMPLETE
- created_at: 2026-06-27
- today: 2026-06-27 (Sat)
- paper_test1_cutoff_date: 2026-06-27
- paper_test2_start_date: 2026-06-29 (Mon)
- scope: design only

## 1. Boundary

This phase does not implement or execute runtime changes. It defines how to stop and archive Phase9 Paper Test 1, then start Paper Test 2 from the Tachibana demo read-only Broker Snapshot.

Prohibited actions remain prohibited:

- live buy / live sell
- Tachibana order, correction, cancel, second-password, or unlock_trade APIs
- destructive modification or deletion of Paper Test 1 artifacts
- Paper Ledger / Broker Snapshot / backtest outputs as AI training data
- backtest execution
- full pytest

Phase9R keeps Phase10 broker access read-only. Broker Snapshot is an observer and initialization source, not an order execution channel.

## 2. Current State Observed

Paper Test 1 latest ledger:

- path: `.runtime/phase9/ledger/latest.json`
- cash: 144,400 JPY
- positions_count: 7
- pending_orders_count: 0
- total_equity: 995,600 JPY
- last_execution_date: 2026-06-25
- last_valuation_date: 2026-06-26

Friday 2026-06-26 daily run:

- manifest: `.runtime/daily_operation/runs/2026-06-26/unified_daily_run_manifest.json`
- status: `UNIFIED_DAILY_RUNNER_COMPLETED`
- decision_for: 2026-06-26
- virtual_order_date: 2026-06-29
- virtual_execution_date: 2026-06-29
- next_candidate_count: 5
- candidate artifact: `.runtime/phase9/inference/2026-06-26/candidate_artifact.json`
- opportunity artifact: `.runtime/phase9/inference/2026-06-26/opportunity_artifact.json`
- order plan artifact: `.runtime/phase9/inference/2026-06-26/order_plan_artifact.json`

Tachibana demo Broker Snapshot:

- path: `.runtime/broker/tachibana/demo/latest_broker_snapshot.json`
- schema_version: `tachibana_broker_snapshot_v1`
- environment: `demo`
- account: PASS
- positions: PASS, count 0
- orders: PASS, count 0
- executions: SKIPPED_NO_ORDERS
- quotes: PASS_WITH_EMPTY_RESULT
- login/logout: PASS
- redaction_status: no raw response, no virtual URL, no auth identifier, no private secret, no plaintext account/customer id, no plaintext order/execution id
- normalized cash fields currently read as 0 JPY

Design implication: Paper Test 2 must not inherit Paper Test 1 holdings. If the startup snapshot still has zero positions and zero cash, Paper Test 2 starts cash-only with 0 JPY and Monday order registration must be blocked as `NO_AVAILABLE_CASH`.

## 3. Paper Test 1 Stop / Archive Policy

Paper Test 1 is frozen, not deleted.

Phase9R-B should create an archive manifest instead of moving or rewriting old artifacts:

- archive namespace: `.runtime/phase9/archive/paper_test1_2026-06-27/`
- manifest: `.runtime/phase9/archive/paper_test1_2026-06-27/archive_manifest.json`
- source ledger pointer: `.runtime/phase9/ledger/latest.json`
- source run manifest pointer: `.runtime/daily_operation/runs/2026-06-26/unified_daily_run_manifest.json`
- source reports pointer: `reports/public/phase9_daily/2026-06-26_blog_report_v4.md`
- cutoff_date: 2026-06-27
- archive_status: `STOPPED_READ_ONLY`

The archive manifest should record hashes, paths, and summary counts. It should not copy secrets, raw broker responses, or external credentials. Existing Paper Test 1 files stay readable for audit.

Scheduler handling:

- disable old Paper Test 1 launchd labels before enabling Paper Test 2 labels
- do not run the old unified daily runner on weekends
- keep Paper Test 1 reports immutable
- preserve old ledger backups and execution records

## 4. Paper Test 2 Namespace

Paper Test 2 should use a separate namespace to avoid accidental writes to Paper Test 1:

- test_id: `paper_test2_2026-06-29`
- runtime root: `.runtime/phase9/paper_test2/`
- ledger: `.runtime/phase9/paper_test2/ledger/latest.json`
- ledger history: `.runtime/phase9/paper_test2/ledger/history/`
- executions: `.runtime/phase9/paper_test2/ledger/executions/`
- pending orders: `.runtime/phase9/paper_test2/orders/pending/`
- initialization: `.runtime/phase9/paper_test2/initialization/`
- broker reconciliation: `.runtime/phase9/paper_test2/reconciliation/`
- tracker: `.runtime/phase9/paper_test2/tracker/`
- operation logs: `.runtime/phase9/paper_test2/operation_logs/`
- reports: `reports/phase9/paper_test2/daily/`
- public blog reports: `reports/public/phase9_paper_test2_daily/`

The existing code has several Phase9-default paths such as `.runtime/phase9/ledger/latest.json`, `.runtime/phase9/inference`, `.runtime/phase9/tracker`, and `reports/public/phase9_daily`. Phase9R-B should add injectable roots or wrappers rather than rewriting Paper Test 1 artifacts.

## 5. Initial Ledger From Broker Snapshot

Initialization source:

- input: `.runtime/broker/tachibana/demo/latest_broker_snapshot.json`
- required environment: `demo`
- required schema: `tachibana_broker_snapshot_v1`
- required redaction: PASS
- required health:
  - login PASS
  - account PASS
  - positions PASS
  - logout PASS
  - orders PASS or empty-safe
  - executions PASS_WITH_EMPTY_RESULT, SKIPPED_NO_ORDERS, or empty-safe
  - quotes PASS, PASS_WITH_EMPTY_RESULT, MARKET_CLOSED, or empty-safe

Initialization mapping:

- `account_summary.cash_available` -> preferred initial cash
- `buying_power.cash_available` -> fallback cash
- `buying_power.buying_power` -> fallback buying power only, not cash if cash is explicitly available
- `positions[]` -> initial ledger positions
- `orders[]` -> must be empty for a clean Paper Test 2 start
- `executions[]` -> ignored for initial ledger unless explicitly required by a later audit

If positions are empty, initialize with no positions. If all cash fields are zero, initialize with cash 0 and block Monday paper order registration with `NO_AVAILABLE_CASH`. Do not silently substitute Paper Test 1 cash.

The initial ledger metadata should include:

- source: `tachibana_demo_broker_snapshot`
- paper_test_id: `paper_test2_2026-06-29`
- broker_snapshot_path
- broker_snapshot_generated_at
- broker_snapshot_hash
- start_date: 2026-06-29
- broker_order_api_called: false
- unlock_trade_called: false
- model_retraining_executed: false

## 6. Friday Candidate Carryover To Monday

The 2026-06-26 candidate set is the input for 2026-06-29 morning order preparation.

Required frozen inputs:

- `.runtime/phase9/inference/2026-06-26/candidate_artifact.json`
- `.runtime/phase9/inference/2026-06-26/opportunity_artifact.json`
- `.runtime/phase9/inference/2026-06-26/allocation_artifact.json`
- `.runtime/phase9/inference/2026-06-26/order_plan_artifact.json`
- `.runtime/daily_operation/runs/2026-06-26/unified_daily_run_manifest.json`

Because the current order plan has zero items while the notification summary has five next candidates, Monday startup should reuse the candidate/opportunity artifacts and regenerate a Paper Test 2 order plan using the Paper Test 2 initial ledger. It must not retrain models and must not call live order APIs.

Candidate carryover manifest:

- source_decision_for: 2026-06-26
- target_order_date: 2026-06-29
- target_execution_date: 2026-06-29
- source artifact hashes
- source candidate_count and opportunity_count
- generated order_plan_count
- blocked reason when cash is zero or safety filters remove all items

## 7. Morning Order Registration Flow

Morning flow for 2026-06-29:

1. Verify business day using the J-Quants trading calendar.
2. Verify Paper Test 1 archive manifest exists and is read-only.
3. Verify Paper Test 2 initial ledger exists under the Paper Test 2 namespace.
4. Load frozen 2026-06-26 candidate/opportunity artifacts.
5. Refresh or validate market data freshness without backtest.
6. Build a Paper Test 2 order plan from the frozen candidates and the Paper Test 2 ledger.
7. Enforce cash, unit, duplicate, max position, and no-live-order guards.
8. Create Paper pending orders only under `.runtime/phase9/paper_test2/`.
9. Write an operation manifest and public-safe summary.

If available cash is zero, the flow should complete as `ORDER_REGISTRATION_BLOCKED_NO_AVAILABLE_CASH` and create no pending orders.

Every pending order should record:

- paper_test_id
- decision_for: 2026-06-26
- virtual_order_date: 2026-06-29
- virtual_execution_date: 2026-06-29
- source candidate artifact hash
- source broker snapshot hash
- live_order_allowed: false
- executable: false

## 8. Periodic Fill Check Flow

Daytime checks should remain paper-only:

- read Paper Test 2 pending orders
- refresh or read approved market data
- simulate fills using the established virtual fill policy
- write virtual execution records only in the Paper Test 2 namespace
- refresh Tachibana demo Broker Snapshot only as read-only reconciliation input

Recommended statuses:

- `NO_PENDING_ORDERS`
- `PAPER_FILL_SIMULATED`
- `PAPER_FILL_NO_PRICE`
- `BROKER_SNAPSHOT_RECONCILED`
- `BROKER_SNAPSHOT_DIVERGENCE`

Since no live Tachibana orders exist in Phase9R, broker orders and executions should normally remain empty. Any non-empty broker order, broker execution, or broker position is a reconciliation warning, not a ledger mutation trigger.

## 9. Nightly Valuation / Candidate Generation Flow

Nightly flow:

1. Refresh/validate market data for 2026-06-29.
2. Value Paper Test 2 ledger positions.
3. Generate Paper Test 2 daily performance report.
4. Run daily inference for the next business day using approved market features only.
5. Generate next-day candidate and opportunity artifacts.
6. Generate next-day Paper order plan in review/paper mode.
7. Write blog report and operation log.
8. Send notifications only after redaction passes.

Training boundary:

- Paper Test 2 ledger, broker snapshot, broker cash, broker positions, PnL, and backtest outputs must not be used as model training data.
- Candidate generation may use existing approved market-data features and trained models only.

## 10. Broker Snapshot Reconciliation

Broker Snapshot reconciliation is read-only and should compare:

- broker environment is `demo`
- broker positions vs Paper Test 2 ledger positions
- broker orders vs Paper Test 2 pending orders
- broker executions vs Paper Test 2 virtual executions
- broker cash/buying power vs Paper Test 2 cash as informational only

Expected Phase9R state:

- broker positions count: 0
- broker orders count: 0
- broker executions count: 0
- Paper Test 2 may have paper positions after virtual fills

This difference is not automatically wrong because Paper Test 2 is virtual. Reconciliation should classify it as:

- `EXPECTED_PAPER_ONLY_DIVERGENCE` when paper-only positions exist and broker has no live positions
- `UNEXPECTED_BROKER_ACTIVITY` when broker has orders/executions/positions that Paper Test 2 did not create
- `SNAPSHOT_STALE` when snapshot freshness fails
- `SNAPSHOT_REDACTION_FAILED` when redaction flags fail

No reconciliation step may update Broker Snapshot, Paper Test 1, or training datasets.

## 11. Blog Report Changes

Paper Test 2 public reports should use a separate output root:

- `reports/public/phase9_paper_test2_daily/`

Required visible labels:

- `Paper Test 2`
- `Tachibana demo read-only snapshot used for initialization/reconciliation`
- `No live orders were sent`
- `This is virtual operation`

Do not publish:

- raw broker response
- auth id
- virtual URL
- account/customer id
- plaintext broker order number or execution id
- secret path contents

If initial cash is zero and no orders are registered, the blog should say the run was blocked by no available paper cash rather than implying a system failure.

## 12. Launchd / Scheduler Redesign

Paper Test 1 launchd jobs should be disabled before Paper Test 2 jobs are enabled. Labels should include Paper Test 2 explicitly.

Proposed labels:

- `com.aifundlab.paper-test2.preopen`
- `com.aifundlab.paper-test2.morning-order-registration`
- `com.aifundlab.paper-test2.fill-check`
- `com.aifundlab.paper-test2.broker-snapshot-check`
- `com.aifundlab.paper-test2.nightly`

Proposed schedule in Asia/Tokyo:

- 08:20 preopen snapshot/readiness check
- 08:45 paper order registration
- 09:05 first fill check
- 10:30 periodic fill and broker snapshot check
- 12:35 periodic fill and broker snapshot check
- 14:45 final intraday fill and broker snapshot check
- 15:30 ledger valuation
- 16:30 nightly report and next-day candidate generation

Scheduler requirements:

- business-day guard before every job
- weekend/holiday runs return `NON_BUSINESS_DAY_SKIPPED`
- run lock per paper_test_id and date
- old Paper Test 1 jobs cannot write to Paper Test 2
- Paper Test 2 jobs cannot write to Paper Test 1
- no scheduler auto-registration during audit/design phases

## 13. Phase9R-B Implementation Steps

Recommended next implementation sequence:

1. Add Paper Test 1 archive manifest writer.
2. Add Paper Test 2 namespace configuration.
3. Add broker snapshot initial ledger importer.
4. Add candidate carryover manifest for 2026-06-26 -> 2026-06-29.
5. Add Paper Test 2 morning order registration wrapper.
6. Add periodic fill/reconciliation wrapper.
7. Add Paper Test 2 blog/report output root.
8. Add launchd plist templates but do not load them automatically.
9. Add audit test for no Paper Test 1 mutation and no live order API.

## 14. Acceptance Criteria

Paper Test 2 can begin on 2026-06-29 when:

- Paper Test 1 archive manifest exists.
- Paper Test 2 initial ledger exists in the new namespace.
- Initial ledger source is the Tachibana demo read-only Broker Snapshot.
- If broker positions are zero, initial positions are zero.
- If broker cash is zero, order registration is blocked safely.
- Friday 2026-06-26 candidate artifacts are frozen and referenced by hash.
- Morning order registration creates only Paper pending orders.
- Periodic fill checks remain virtual.
- Broker Snapshot reconciliation is read-only.
- Blog reports clearly state Paper Test 2 and no-live-order status.
- launchd labels are separated from Paper Test 1.

## 15. Result

Phase9R-A is ready for Phase9R-B implementation planning. No live broker order path is introduced, and Paper Test 1 remains preserved for audit.
