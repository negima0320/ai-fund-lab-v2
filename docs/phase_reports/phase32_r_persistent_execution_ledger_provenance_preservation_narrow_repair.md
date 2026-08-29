# Phase32-R Persistent Execution Ledger Provenance Preservation Narrow Repair

## Executive Summary

Phase32-R repaired the Phase32-Q mandatory defect narrowly: persistent execution ledger records now preserve source strategy/PM decision provenance when canonical order/planning lineage provides it.

The repair is additive and backward compatible. It does not change re-entry gates, PM/PC/MCC, Cash, Risk Pacing, position sizing economics, SELL logic, valuation/accounting semantics, or execution dedupe keys.

## Inherited Defect

Phase32-Q confirmed that PM detailed EXIT identity survived into runtime planning and daily execution artifacts, but was dropped before `.runtime/persistent_ledger/executions.jsonl`. That prevented Phase32-L's strict prior PM reason bridge from matching executed close rows to PM decisions, leaving prior-exit context as generic `EXIT`.

## Exact Repair Boundary

Repaired boundaries:

- `runtime_v2/ledger/models.py::LedgerExecutionRecord`
- `runtime_v2/broker_readonly/models.py::BrokerOrderSnapshot`
- `runtime_v2/broker_readonly/models.py::BrokerExecutionSnapshot`
- `runtime_v2/broker_readonly/normalizer.py`
- `runtime_v2/execution/readonly_pipeline.py::_execution_equivalent_records`
- `runtime_v2/execution/ledger_projection.py::project_execution_to_ledger_record`
- historical submit evidence/order payload handoff in `runtime_v2/historical_support/environment.py`
- submit command provenance handoff in `runtime_v2/submit/models.py` and `runtime_v2/submit/guards.py`

## Schema Changes

Added optional provenance fields to `LedgerExecutionRecord`:

- `source_decision_id`
- `source_pm_decision_id`
- `source_decision_type`
- `source_pm_business_date`
- `source_position_symbol`
- `position_campaign_id`

Also added the same optional fields to broker read-only order/execution snapshots so projections can preserve explicit source lineage without guessing.

## Projection Changes

Historical execution-equivalent projection now copies provenance from normalized filled orders into persistent execution rows.

Broker/detail execution projection now accepts an optional matched source order and uses only explicit execution/order/lineage provenance. It does not infer provenance from symbol/date/quantity alone.

Historical submit now carries pending item PM provenance into `RuntimeV2SubmitCommand`, historical submission evidence, broker readonly order snapshot payloads, normalized broker order snapshots, and finally ledger execution rows.

## Mode Parity

Historical actual path is fixed for execution-equivalent rows.

Demo/production parity is partially covered and safe: the shared execution ledger schema supports the fields, broker read-only snapshots preserve them, and detail execution projection can materialize them when a canonical order linkage is available. If broker execution payloads lack provenance and no explicit matched order is available, the fields remain empty; no guessed join is introduced.

## Backward Compatibility

Legacy ledger rows without the new fields remain valid because all new dataclass fields default to empty strings and existing Phase32-L fallback behavior is unchanged.

Phase32-L still uses `EXECUTION_ROW_FALLBACK` when a ledger row has no strict source decision identity, and wrong symbol/campaign/future evidence remains fail-closed through the existing bridge tests.

## Partial REDUCE / Final EXIT Safety

No re-entry or close-state logic changed. The existing Phase32-L resolver still forms prior-exit state only when the running ledger quantity reaches zero.

Verified by the existing Phase32-L tests:

- partial REDUCE remains open and does not form prior-exit state;
- final close after prior REDUCE uses the final close PM reason;
- wrong campaign, wrong symbol, and future PM evidence remain rejected.

## Idempotency

Execution dedupe keys are unchanged.

`_execution_transaction_id` uses `_record_dedup_keys(...)`, not full execution payload equality, so the additive provenance fields do not enter transaction identity. The focused retry test confirms the second execution pass appends zero additional execution rows and keeps the same dedupe keys.

## Focused Regressions

Added/covered regressions:

- PM EXIT identity to historical execution-equivalent to persistent ledger preservation.
- `source_decision_id` preserved.
- `source_decision_type` preserved.
- `position_campaign_id` preserved.
- broker readonly order identity equals persistent ledger identity for the actual writer path.
- daily fill source decision/type and campaign identity remain aligned with realized slices.
- dedupe/idempotency unchanged after provenance fields are present.
- broker/detail execution projection preserves explicit order provenance.
- Phase32-L strict bridge matches using the produced ledger row.
- existing partial REDUCE/final close/fail-closed Phase32-L tests still pass.

## Phase32-L Integration Proof

The new focused actual-pipeline test constructs:

PM detailed EXIT
-> pending/source PM identity
-> historical submit evidence
-> broker readonly snapshot
-> historical execution-equivalent ledger row
-> `_supply_prior_exit_state`
-> `STRICT_PRIOR_PM_DECISION_EVIDENCE`
-> `prior_exit_reason = trend_and_opportunity_broken`

The test does not assert REENTRY BUY; it only proves semantic prior-exit materialization on the actual writer path.

## Changed Files

- `docs/02_architecture/runtime_architecture_v2.md`
- `src/ai_fund_lab_v2/runtime_v2/broker_readonly/models.py`
- `src/ai_fund_lab_v2/runtime_v2/broker_readonly/normalizer.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/ledger_projection.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`
- `src/ai_fund_lab_v2/runtime_v2/ledger/models.py`
- `src/ai_fund_lab_v2/runtime_v2/ledger/performance_events.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/models.py`
- `tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py`
- `tests/runtime_v2/test_phase20_j_performance_observability.py`

## Commands Executed

- `PYTHONPYCACHEPREFIX=/private/tmp/phase32r_pycache python3 -m py_compile ...`
- `PYTHONPYCACHEPREFIX=/private/tmp/phase32r_pycache python3 -m pytest -q tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py -q`
- `PYTHONPYCACHEPREFIX=/private/tmp/phase32r_pycache python3 -m pytest -q tests/runtime_v2/test_phase20_j_performance_observability.py::test_phase20_j_writes_campaign_fills_realized_slices_and_pm_snapshot -q`
- `PYTHONPYCACHEPREFIX=/private/tmp/phase32r_pycache python3 -m pytest -q tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py -q`

All listed verification commands passed after the repair. A first `pytest` shell command failed only because `pytest` was not on PATH; `python3 -m pytest` was used successfully.

## Remaining REENTRY / Cash Issues

This phase did not change and did not validate:

- re-entry cooldown;
- re-entry rank/admission thresholds;
- buy quality;
- continuation/downside/churn gates;
- Cash/PC/MCC/Risk Pacing;
- ADD/NEW priority;
- sizing economics.

Those remain separate Phase32 findings and must not be inferred as fixed by this provenance repair.

## Fresh Validation Recommendation

Do not reuse `runtime-test-historical-extended-smoke-20260827T005331941551Z` as repair acceptance evidence. It was produced before this repair and remains invalid for Phase32-L actual-path acceptance.

Recommended next user action: start a new fresh validation run after accepting Phase32-R, then repeat the Phase32-P semantic actual-path audit against the new run.

## Final Judgments

PHASE32_R_LEDGER_PROVENANCE_DEFECT_REPAIRED = YES

PHASE32_R_SOURCE_DECISION_ID_PRESERVED = YES

PHASE32_R_SOURCE_DECISION_TYPE_PRESERVED = YES

PHASE32_R_POSITION_CAMPAIGN_ID_PRESERVED = YES

PHASE32_R_HISTORICAL_ACTUAL_PATH_FIXED = YES

PHASE32_R_DEMO_PRODUCTION_PARITY_SAFE = PARTIAL

PHASE32_R_LEGACY_LEDGER_COMPATIBLE = YES

PHASE32_R_DEDUPE_UNCHANGED = YES

PHASE32_R_IDEMPOTENCY_REGRESSION = PASS

PHASE32_R_PARTIAL_REDUCE_SAFE = YES

PHASE32_R_FINAL_CLOSE_IDENTITY_SAFE = YES

PHASE32_R_PHASE32_L_STRICT_MATCH_ACTUAL_PIPELINE_PASS = YES

PHASE32_R_REENTRY_THRESHOLDS_CHANGED = NO

PHASE32_R_CASH_LOGIC_CHANGED = NO
