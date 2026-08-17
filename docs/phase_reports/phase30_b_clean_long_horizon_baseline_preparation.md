# Phase30-B Clean Long-Horizon Baseline Preparation

Primary Judgment:

```text
PHASE30_B_CLEAN_LONG_HORIZON_BASELINE_PREFLIGHT_READY_WITH_KNOWN_TEST_FIXTURE_GAP_USER_977BD_RUN_READY
```

Task ID: `Phase30-B`

Status:

```text
COMPLETE
PREFLIGHT / READINESS ONLY
NO STRATEGY / RUNTIME / CONFIG / MODEL / THRESHOLD CHANGE
NO FOUR-YEAR HISTORICAL EXECUTION BY CODEX
NO PERFORMANCE TUNING
```

## Scope

Phase30-B prepared the next user-operated clean long-horizon Historical
baseline after Phase30-A confirmed the clean 20BD measurement foundation.
No performance improvement, tuning, threshold change, model change, runtime
semantic change, or Historical long-run execution was performed.

Target operator window:

```text
Requested period: 2022-08-10 through 2026-08-09
Resolved canonical trading window: 2022-08-10 through 2026-08-07
Resolved business days: 977
Window resolution: PASS
Request conformance: PASS
```

The `2026-08-09` endpoint is a non-trading calendar endpoint for this request;
the current planner resolves the final trading day to `2026-08-07`.

## Authority Check

Authority chain for the user-operated long run:

```text
Profile alias: historical-extended-smoke
Profile file: config/runtime_tests/historical_extended_smoke_10bd.json
Mode: historical
Runtime root: .runtime
Broker environment: historical_simulated
External delivery: false
Broker write: false
Tachibana API: false
J-Quants fetch during runtime test: false
Job sequence:
  market_refresh
  data_readiness
  morning
  sell_planning
  submit
  execution
  current_valuation_refresh
  runtime_state_refresh
```

Closed contracts that must remain preserved:

```text
Production-common Runtime v2 path
Historical-only Strategy prohibition
BUY / SELL independence
PM ADD -> Runtime BUY_ADD continuity
BUY_WAIT as no Pending / no halt / next-day reevaluation
NO_SUBMISSION_REQUIRED / AUTHORIZED_NO_ORDER continuity
Discrete-lot REDUCE semantics
SELL continuation and Pending reconciliation
Valuation fail-closed
Price / quantity adjustment-basis compatibility
Runtime-owned Current basis metadata persistence
No Paper Ledger / PnL / selected-bought-test-result runtime learning input
```

Phase30-A evidence remains the clean measurement authority for entering this
preflight. The clean 20BD run
`runtime-test-historical-extended-smoke-20260815T030154161245Z` completed 20BD
from `2022-08-10` through `2022-09-07`; its final close status was
`REVIEW_REQUIRED` due to non-mutating Strategy Shadow review, not runtime
execution, accounting, trading state, Pending, valuation, Ledger, or Current
failure.

## Measurement Readiness

Phase30-A established the 20BD clean measurement foundation:

```text
Equity = Cash + sum(position market value): reconciled for all 20 completed days
Price / quantity basis: matched for all valued positions
Valuation contamination recurrence: not observed
Historical evaluation authority: PASS
Final close blocker: none from runtime accounting / valuation / trading state
```

Phase30-B dry-run/planner preflight:

```text
Command type: fresh-run --dry-run
Status: DRY_RUN
Exit code: 0
Mutation: none
Run directory created: no
Planner window status: PASS
Resolved business days: 977
Resolved date range: 2022-08-10 through 2026-08-07
```

This is sufficient to release the user-operated long-horizon baseline command
for research metrics, with residual limitations documented below.

## BUY Fill Lineage

Phase30-A reported a visible artifact limitation:

```text
existing_artifact_status: REVIEW_REQUIRED_PRE_REPAIR_ARTIFACT
existing_artifact_missing_lineage_count: 39
Affected direct artifacts: daily/*/execution/fills.json
Missing direct fields: pending_item_id, order_plan_item_id, quality_decision_id
```

Phase30-B investigated the current lineage path before releasing the long run.
The current close-time validation replays BUY fill lineage from
`run_scoped_execution_fills + run_scoped_submit_guard_item_evidence`.

Current 20BD close summary:

```text
buy_fill_lineage_validation.status: PASS
missing_lineage_count: 0
replayed_buy_fill_count: 39
replayed_missing_lineage: []
```

Code path checked:

```text
scripts/runtime_test.py::_buy_fill_lineage_validation
scripts/runtime_test.py::_collect_order_plan_items
scripts/runtime_test.py::_execution_source_decision
scripts/runtime_test.py::_build_fill_rows
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py
src/ai_fund_lab_v2/runtime_v2/planning/order_plan_builder.py
src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py
```

Judgment:

```text
CURRENT_BUY_FILL_LINEAGE_READY_FOR_NEW_LONG_RUN
```

The old 20BD daily fill artifacts remain pre-repair artifacts, but the current
replay validation resolves BUY fill lineage to PASS. This is not a STOP
condition for the new user-operated long run. The long run should still be
checked immediately after close for both direct artifact completeness and
replayed lineage completeness.

## Regression

Focused short regression was executed only for preflight. No four-year
Historical run was executed.

Passed batch:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase30b_pycache python3 -m pytest -q \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py \
  tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py \
  tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py \
  tests/runtime_v2/test_phase19_bi_empty_pending_no_action_contract.py \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py \
  tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py \
  tests/runtime_v2/test_phase20_j_performance_observability.py \
  tests/runtime_v2/test_phase25_a2_daily_evaluation_evidence.py

Result: 92 passed
```

Second batch:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase30b_pycache python3 -m pytest -q \
  tests/runtime_v2/test_phase18v_runtime_test_fresh_run.py \
  tests/runtime_v2/test_phase23_p_historical_evaluation_authority.py \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py \
  tests/runtime_v2/test_phase29_l9_historical_ca_quarantine_continuation.py \
  tests/runtime_v2/test_phase23_ab_no_order_submit_guard.py \
  tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py \
  tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py \
  tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py \
  tests/strategy/test_phase26_h_adaptive_buy_quality.py

Result: 97 passed, 1 failed
```

Observed failure:

```text
tests/runtime_v2/test_phase18v_runtime_test_fresh_run.py::test_phase18v_fresh_run_happy_path_reuses_normal_runtime_cli_and_closes
Expected: payload["status"] == "BLOCK"
Actual: payload["status"] == "VALIDATION_FAILURE"
```

Interpretation:

```text
KNOWN_TEST_FIXTURE_EXPECTATION_GAP
```

The failing test uses a mocked runtime CLI and asserts an older close/fresh-run
status contract. The real `fresh-run --dry-run` for the long window returned
`DRY_RUN` with exit code 0, and no runtime run directory was created. This
failure should be tracked as a test maintenance gap, but it is not evidence of
BUY lineage, valuation, Pending, ADD, REDUCE, Corporate Action quarantine, or
BUY/SELL independence failure.

## Evidence Sufficiency

The long run is sufficient for Phase30 research metrics if it completes and
passes close-time integrity checks:

```text
Portfolio equity / cash / exposure / drawdown
Deployed-capital return
BUY_NEW / BUY_WAIT / ADD / REENTRY attribution
Winner continuation and profit retention
SELL / REDUCE / EXIT outcome separation
Market regime and regime transition analysis
Corporate Action quarantine counts and affected-symbol limitations
Lineage completeness from Candidate / Buy Quality / Pending to filled BUY
```

Limits that remain:

```text
Profile is historical-extended-smoke / pre-continuity smoke profile.
Fill model has zero fees, zero tax, zero slippage, and no partial fills.
Historical evaluation authority can pass while training overlap means the run is
not strict OOS AI performance.
Close may return REVIEW_REQUIRED from non-mutating Strategy Shadow review.
Corporate Action quarantined symbols can create symbol-scoped limitations.
```

## Known Residual Risks

1. `strategy_shadow_review_required_non_blocking` may keep close status at
   `REVIEW_REQUIRED` even when runtime accounting is valid.
2. Corporate Action symbols may be quarantined with
   `COMPLETED_WITH_SYMBOL_QUARANTINE`; these are valid continuation limitations,
   not production weakening.
3. Direct daily fill artifact lineage should be rechecked on the new run even
   though current replay validation passes.
4. The fresh-run mocked happy-path regression has a stale expected status
   (`BLOCK` versus current `VALIDATION_FAILURE`).
5. The smoke fill model is research-grade for clean relative baseline analysis,
   not a live trading cost model.

## User Run Command

Do not append `--json`. Do not invent a run id before the command starts.

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src

python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --date-from 2022-08-10 \
  --date-to 2026-08-09 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Expected planner resolution:

```text
requested_start_date: 2022-08-10
requested_end_date: 2026-08-09
resolved_date_from: 2022-08-10
resolved_date_to: 2026-08-07
resolved_business_day_count: 977
```

## Early Health Check

After the command prints a real `run_id`, replace `<RUN_ID>` below:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py show --run-id <RUN_ID>
```

Check early evidence:

```bash
jq '{status, completed_business_days, halted_job, error}' \
  reports/runtime_tests/runs/<RUN_ID>/run_state.json
```

## Progress Check

During or after the run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py status
```

If a run id is available:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py show --run-id <RUN_ID>
```

## HALT Evidence Command

If the run halts or returns a non-PASS final state, collect the run-scoped
evidence before any repair:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py show --run-id <RUN_ID>

jq '{status, completed_business_days, halted_job, error, halt_summary}' \
  reports/runtime_tests/runs/<RUN_ID>/run_state.json
```

If `final_summary.json` exists:

```bash
jq '{status, final_judgment, close_authority_judgment, acceptance_gate_judgment, buy_fill_lineage_validation, historical_evaluation_authority}' \
  reports/runtime_tests/runs/<RUN_ID>/final_summary.json
```

## Next Step

```text
User executes long Historical.
```
