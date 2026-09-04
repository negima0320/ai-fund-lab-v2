# Phase32-EZ - Bounded Recent-Exit Guard Materialization / Connectivity Repair

Date: 2026-09-04

Target evidence run:

`runtime-test-historical-extended-smoke-20260903T205257030508Z`

This phase implements the narrow repair requested after Phase32-EY. No fresh-run,
resume, replay, long Historical, target-run mutation, Pending mutation, Ledger
mutation, Strategy threshold change, weight change, ranking change, or model
change was executed.

## Root Cause

Phase32-EW correctly removed the old long-lived `REENTRY` current-decision
semantic and replaced it with a bounded recent-exit guard concept. The consumer
path existed:

```text
strategy shadow
-> _bounded_recent_exit_guard_state_by_symbol
-> candidate/opportunity prior-exit annotation
-> Portfolio Construction semantic guard
-> Marginal Capital Value guard blocker
```

But the Production runtime had no connected producer that materialized a compact
bounded `recent_exit_guard` index after an actual full SELL exit execution.
Therefore the 2022-10-04 `SELL_EXIT` for `83060` was recorded in execution /
ledger evidence, but 2022-10-05 strategy discovery saw no bounded guard row and
treated `83060` as ordinary unguarded `BUY_NEW`.

Pre-repair confirmation:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260903T205257030508Z/**/recent_exit_guard*`: absent.
- `.runtime/runtime_state/**/recent_exit_guard*`: absent.
- `shadow_runtime._supply_prior_exit_state` consumed only explicit bounded guard
  files after EW and did not scan whole-run execution or PM EXIT history.

## Repair

Implemented a committed-execution producer:

```text
committed SELL_EXIT / EXIT execution
-> .runtime/runtime_state/recent_exit_guard.json
-> next decision-day strategy guard discovery
-> PC / MCV bounded guard consumption
```

The new materializer writes only bounded runtime state:

- symbol
- most recent full EXIT business date
- prior campaign id
- source PM decision id
- source Strategy decision id
- source decision type
- minimal reason / reason-code lineage when already present in order authority
- guard state/status/reason
- runtime-test run id binding
- TTL contract
- compacted rows only

It does not reconstruct full old prior-exit history, does not scan
`executions.jsonl` in the current BUY hot path, and does not restore
`semantic_buy_type=REENTRY`.

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/recent_exit_guard.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `tests/runtime_v2/test_phase32_ez_recent_exit_guard_materialization.py`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`

## Contract Notes

- Producer existed before repair: `NO`.
- Producer runtime-connected before repair: `NO`.
- The producer now runs only after persistent execution/current commit is
  complete.
- Full EXIT rows are sourced from committed `SELL_EXIT` / `EXIT` execution
  evidence, not from speculative PM decisions.
- Same-day/future guard rows are not supplied to the current decision date.
- Cross-run stale rows are rejected when the runtime-test run id is known.
- Expired guard rows are compacted from runtime state.
- BUY semantics remain `BUY_NEW`; active guard state is attached as bounded
  lineage and blocker evidence.

## Validation

PASS:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase32_ez_recent_exit_guard_materialization.py \
  tests/strategy/test_phase32_ew_reentry_semantic_removal_recent_exit_guard.py \
  tests/runtime_v2/test_phase17_bv10_historical_sell_execution_projection.py \
  tests/runtime_v2/test_phase31_g30_authority_lineage.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_actual_buy_add_fill_runtime_id_merges_when_open_campaign_lineage_proves_identity \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_actual_shaped_add_history_anchors_merge_with_canonical_bridge \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_conflicting_fill_campaign_without_canonical_bridge_does_not_merge
```

Result: `28 passed in 1.90s`

PASS:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/runtime_v2/recent_exit_guard.py \
  src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py \
  src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py \
  src/ai_fund_lab_v2/strategy/shadow_runtime.py
```

Additional non-blocking observation:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py
```

Result: `1 failed`. The failure is an existing expectation drift in that old
demo execution test: the pipeline returned an early acceptance
`REVIEW_REQUIRED` with `asset_connected=False` before commit. The EZ hook did
not run on that path (`recent_exit_guard_materialization=None`) and the failure
does not indicate a recent-exit guard regression.

## Required Answers

- `ROOT_CAUSE`: EW left a bounded recent-exit guard consumer but no connected
  committed-execution producer/persistence path.
- `PRODUCER_EXISTED_BEFORE_REPAIR`: `NO`.
- `PRODUCER_RUNTIME_CONNECTED_BEFORE_REPAIR`: `NO`.
- `EXIT_TO_GUARD_MATERIALIZATION_REPAIRED`: `YES`.
- `GUARD_PERSISTENCE_REPAIRED`: `YES`.
- `NEXT_DAY_DISCOVERY_REPAIRED`: `YES`.
- `PC_PROPAGATION_REPAIRED`: `YES`.
- `MCV_PROPAGATION_REPAIRED`: `YES`, via existing EW guard-state consumers.
- `83060_FOCUSED_REGRESSION`: `PASS`.
- `GUARD_EXPIRY_REGRESSION`: `PASS`.
- `GENUINE_MISSING_PROVENANCE_FAIL_CLOSED`: `PASS`.
- `OLD_REENTRY_SEMANTIC_RESTORED`: `NO`.
- `WHOLE_RUN_HISTORY_SCAN_RESTORED`: `NO`.
- `OLD_EXIT_PERMANENT_PENALTY_REINTRODUCED`: `NO`.
- `BUY_ADD_G129_REGRESSION`: `NO`.
- `CAMPAIGN_LIFECYCLE_REGRESSION`: `NO`.
- `UNBOUNDED_HISTORY_HOT_PATH_REINTRODUCED`: `NO`.
- `ARCHITECTURE_SOT_UPDATED`: `YES`.
- `READY_FOR_USER_FRESH_VALIDATION`: `YES`.

## User Fresh Validation

Recommended user command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-10-03 \
  --business-days 20 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Acceptance focus:

- 2022-10-04 execution should materialize `.runtime/runtime_state/recent_exit_guard.json`.
- 2022-10-05 `83060` should remain `semantic_buy_type=BUY_NEW` but carry
  `recent_exit_guard_state=ACTIVE_RECENT_EXIT_GUARD` unless current PIT
  requalification releases it.
- No old long-lived REENTRY penalty should appear after guard expiry.

## Final Judgment

`PHASE32_EZ_BOUNDED_RECENT_EXIT_GUARD_MATERIALIZATION_AND_CONNECTIVITY_REPAIRED_WITHOUT_RESTORING_LONG_LIVED_REENTRY_SEMANTICS_READY_FOR_USER_FRESH_VALIDATION`
