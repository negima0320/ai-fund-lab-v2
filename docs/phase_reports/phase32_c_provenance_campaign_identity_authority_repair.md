# Phase32-C Provenance and Campaign Identity Authority Repair

## Final Judgment

`PHASE32_C_PROVENANCE_AND_CAMPAIGN_IDENTITY_AUTHORITY_REPAIRED`

## Scope

- Target evidence run: `runtime-test-historical-extended-smoke-20260829T181133963759Z`
- Current source commit before repair: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Source state: dirty workspace from Phase32-A/Phase32-B reports plus Phase32-C repair changes.
- Execution restrictions honored: no fresh-run, no resume, no replay, no long Historical.
- Phase32-only Strategy semantics excluded. No candidate selection, threshold, weight, rank, cash, risk pacing, or Strategy parameter logic was changed.

## Root Cause

P31-KI-002 and P31-KI-003 shared the same authority class failure: lifecycle identity was present in upstream decision artifacts, but Runtime lifecycle schemas and observability generation did not preserve it as a first-class contract.

P31-KI-002 direct root cause:

- `PendingOrderItem` carried only partial lineage (`source_decision_type`, `source_pm_decision_id`) and did not have first-class `source_decision_id`, `order_plan_item_id`, or `position_campaign_id`.
- Submit command, historical submit evidence, broker order snapshots, execution-equivalent ledger records, and persistent ledger models did not carry the complete provenance tuple.
- SELL/REDUCE/EXIT PM decisions kept `source_decision_id` in local decision objects or `quantity_contract`, but did not promote it consistently into common pending/submit/ledger fields.

P31-KI-003 direct root cause:

- Campaign evidence generation in `scripts/runtime_test.py` reconstructed campaign IDs from `run_id + symbol + sequence` instead of using the upstream execution/PM campaign identity when available.
- This created a second campaign authority family for the same symbol/campaign, visible as fill/PM IDs such as `pc-7c82...` and campaign artifact IDs such as `pc-0933...`.

## First Provenance Loss Boundary

- BUY_NEW / BUY_ADD: Runtime Planning -> Pending materialization. `planning_id` and nested campaign authority existed upstream, but pending did not materialize them as first-class provenance fields.
- REDUCE / EXIT: PM artifact -> `SellExitDecision` -> Pending. PM artifacts had `position_campaign_id`, but `SellExitDecision` did not carry it, and pending did not expose a common provenance contract.
- Persistent loss boundary: Submit/Execution/Ledger schemas did not include the full tuple, so even surviving partial values were dropped before durable ledger evidence.

## Campaign Identity Split Root Cause

The split was caused by a downstream reconstruction generator:

- old campaign artifact ID policy: `RUN_SCOPED_DETERMINISTIC_EXECUTION_REPLAY_SYMBOL_SEQUENCE`
- old implementation: `_position_campaign_id(run_id, symbol, sequence)`
- repaired behavior: use upstream `position_campaign_id` / `campaign_id` from execution rows first; missing or mismatched campaign IDs become explicit `REVIEW_REQUIRED` evidence rather than silent symbol-only identity authority.

## Canonical Authority Selected

Canonical identity authority is existing upstream decision-time lifecycle identity:

- BUY_NEW / REENTRY: Runtime pending materializes a new campaign ID once from the canonical Runtime Planning decision ID.
- BUY_ADD / HOLD / REDUCE / EXIT: inherit the existing `position_campaign_id` from pre-action campaign/PM/refined capital evidence.
- Submit, execution, fills, and ledger are consumers only; they must propagate the upstream tuple and must not regenerate it from symbol-only joins.

Canonical provenance tuple:

- `source_decision_id`
- `source_decision_type`
- `source_pm_decision_id`
- `pending_item_id`
- `order_plan_item_id`
- `position_campaign_id`
- `campaign_id` alias for compatibility

## Architecture Contract

Runtime preserves authority; it does not re-decide Strategy.

The repaired contract is:

`Strategy/PM decision -> Pending -> SubmitCommand -> HistoricalSubmitEvidence -> BrokerOrderSnapshot -> LedgerOrderRecord -> LedgerExecutionRecord -> fill/campaign observability`

If explicit pending fields and embedded `quantity_contract` disagree, submit command construction raises a fail-closed `ValueError` instead of silently choosing one value.

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/provenance.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/models.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`
- `src/ai_fund_lab_v2/runtime_v2/broker_readonly/models.py`
- `src/ai_fund_lab_v2/runtime_v2/broker_readonly/normalizer.py`
- `src/ai_fund_lab_v2/runtime_v2/ledger/models.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/ledger_projection.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/order_plan_builder.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `scripts/runtime_test.py`
- `tests/runtime_v2/test_phase31_g30_authority_lineage.py`
- `tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py`

## Migration / Backfill

No migration/backfill was performed.

Existing historical run artifacts remain immutable evidence of the pre-repair defect. The repair applies to newly generated pending/submit/execution/ledger/fill/campaign evidence. Old run evidence should not be rewritten.

## Focused Validation Results

PASS:

```text
python3 -m pytest tests/runtime_v2/test_phase31_g30_authority_lineage.py tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews
```

Result: `10 passed in 2.24s`

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase32c_pycache python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2 tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py tests/runtime_v2/test_phase31_g30_authority_lineage.py
```

Note: plain `compileall` without `PYTHONPYCACHEPREFIX` failed only because Python attempted to write bytecode under `/Users/negishi/Library/Caches`, which is outside the writable sandbox.

## Strategy Semantic Change

NO.

No Strategy parameter, threshold, weight, rank, candidate selection, cash policy, or risk pacing behavior was changed. The repair only preserves identity/provenance already decided upstream.

## G129 Regression

NO.

Existing G129 focused tests passed:

- `test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta`
- `test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews`

## Remaining Known Issues

Phase32-C repaired only:

- `P31-KI-002`
- `P31-KI-003`

The other Phase32-B known issue classifications remain out of scope for this repair.

## Exact Next User Action

Run a new user-operated Historical fresh-run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-10-03 \
  --business-days 300 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```
