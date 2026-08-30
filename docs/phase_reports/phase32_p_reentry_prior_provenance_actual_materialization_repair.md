# Phase32-P - REENTRY Prior Provenance Actual-Materialization Repair

Target evidence run: `runtime-test-historical-extended-smoke-20260830T032332732107Z`

This phase repaired the remaining Phase32-O mandatory blocker:
REENTRY prior provenance fields were not materialized in actual Historical Runtime Portfolio Construction artifacts.

Codex did not run fresh-run, resume, replay, or long Historical. No future price, future return, future regime, future MFE/MAE, later SELL result, final campaign outcome, Historical profitability, or hindsight evidence was used.

## Current Source / Baseline Identity

- Source commit: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Source dirty: YES, includes prior Phase32 repair work and this Phase32-P repair.
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py` sha256 after repair: `1ce974bf42f6ab88d40b1ed03926e8d5d2d2894edae4cebdf41d354a1a6b63ca`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py` sha256 after repair: `f4536a511e0b6b9e4cd1fdd3e4d689a36859c1642fb84a31609bd244c7f8e9d2`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` sha256 unchanged in Phase32-P: `3da7e3014eeb01770feca63655f9f3aa2bfed882cee050f633423bf85d4eab5a`

PM_REACCEPTANCE_REQUIRED: NO. Phase32-P did not modify PM producer code or PM accepted artifact authority. The repair is in Strategy shadow prior-state enrichment and Portfolio Construction member materialization.

## Root Cause

Root cause:

Portfolio Construction member materialization dropped upstream REENTRY prior provenance while preserving only prior EXIT date/reason fields.

Phase32-H/J/L made `_supply_prior_exit_state()` capable of resolving strict-prior PM EXIT evidence from:

- persistent ledger executions
- PM EXIT decision artifacts
- campaign identity carried on executions and PM artifacts

However, the active Historical morning path then passed the enriched opportunity rows into Portfolio Construction. In `portfolio_construction._member()`, observable fields were copied through `_phase29_l16_observable_fields()`. That field allowlist included:

- `prior_exit_business_date`
- `prior_exit_reason`
- `prior_exit_reason_codes`

but omitted:

- `prior_campaign_id`
- `prior_exit_campaign_id`
- `prior_exit_decision_type`
- `source_pm_decision_id`
- `source_decision_id`
- `prior_exit_provenance_status`
- `prior_exit_context`

Therefore `_semantic_reentry_evidence()` saw a row with date/reason present but no provenance IDs, and correctly emitted `prior_exit_provenance_status=REVIEW_REQUIRED`. This was not a campaign identity split and not a Strategy performance issue.

## First Loss Boundary

First confirmed loss boundary:

`portfolio_construction._member()` -> `_phase29_l16_observable_fields()`

The upstream opportunity row already contained complete strict-prior context. The loss occurred when the member row was built from candidate/opportunity/current/PM inputs.

Secondary hardened boundary:

`shadow_runtime._attach_prior_exit_to_summary()` previously treated any existing prior EXIT date as "already supplied". Actual run rows can already have date/reason while missing IDs. Phase32-P changed this to enrich date-only rows when the strict-prior canonical context is for the same prior EXIT business date and the row does not already have complete PASS provenance.

## Representative Actual-Path Evidence

Pre-repair Phase32-O observation from target run:

- REENTRY rows: 119
- `prior_campaign_id` non-empty: 0 / 119
- `source_pm_decision_id` non-empty: 0 / 119
- `source_decision_id` non-empty: 0 / 119
- `prior_exit_provenance_status=REVIEW_REQUIRED`: 119 / 119
- strict-prior date violations: 0

Post-repair actual entrypoint re-materialization, executed against copied target run evidence with no runtime mutation:

Case 33700, REENTRY evaluation on `2022-10-06`:

- prior EXIT date: `2022-10-05`
- prior campaign: `pc-878ea6968d1e7574-33700-0001`
- source PM decision: `pm-2022-10-05-33700-reduce`
- source decision: `rp-2022-10-05-33700-sell_exit-95bbd0210e1cda41`
- prior provenance status: `PASS`
- prior context status: `PASS`
- reentry semantic status: `FAIL_CLOSED`
- runtime mutation performed: `false`

Case 76470, REENTRY evaluation on `2022-10-17`:

- prior EXIT date: `2022-10-14`
- prior campaign: `pc-ec3672c4e51adeca-76470-0001`
- source PM decision: `pm-2022-10-14-76470-exit`
- source decision: `rp-2022-10-14-76470-sell_exit-084afc15fda747d9`
- prior provenance status: `PASS`
- prior context status: `PASS`
- reentry semantic status: `FAIL_CLOSED`
- runtime mutation performed: `false`

Rejected/blocked REENTRY status no longer controls provenance materialization. Provenance is preserved even when semantic REENTRY remains `FAIL_CLOSED`.

## Mandatory Questions

1. Does persistent ledger SELL/EXIT contain canonical source IDs?
   - YES for representative actual cases. Ledger rows contain Runtime Planning `source_decision_id`; PM source ID is available either directly or by PM evidence join.

2. Does closed campaign state contain canonical prior campaign ID?
   - YES for representative actual cases. Ledger and PM artifacts agree on `position_campaign_id`.

3. Does `_supply_prior_exit_state()` produce IDs in real Runtime path?
   - YES. Direct actual-run invocation produced full IDs/status/context before PC materialization.

4. Is the repaired resolver called by active Historical Strategy path?
   - YES. `generate_strategy_shadow_for_day()` calls `_supply_prior_exit_state(run_dir=..., runtime_root=...)` before downstream Strategy artifacts are produced.

5. Is a stale/parallel materializer overwriting the fields?
   - NO. The confirmed first loss was the PC member observable-field allowlist, not a stale separate materializer.

6. Are IDs present internally but omitted during PC serialization?
   - YES. IDs were present in the enriched opportunity row and absent from the PC member row before this repair.

7. Is schema normalization/defaulting replacing them?
   - NO direct schema defaulting was the first cause. PC semantic fallback to `REVIEW_REQUIRED` was downstream behavior after IDs had already been omitted.

8. Is Runtime using an artifact generated before repaired prior-state enrichment?
   - NO for the tested active entrypoint. Re-materialization through the current active entrypoint now emits the fields.

## Repair Performed

Changed `src/ai_fund_lab_v2/strategy/shadow_runtime.py`:

- Added complete prior-exit provenance detection.
- Changed `_attach_prior_exit_to_summary()` so date-only rows can be enriched when the canonical strict-prior context matches the same prior EXIT business date.
- Preserved strict-prior behavior and current-position skip behavior.

Changed `src/ai_fund_lab_v2/strategy/portfolio_construction.py`:

- Added prior provenance fields to `_phase29_l16_observable_fields()` so Portfolio Construction member materialization carries upstream provenance into `_semantic_reentry_evidence()` and final serialized PC rows.

Changed `tests/strategy/test_phase29_l21k_prior_exit_materialization.py`:

- Added a 33700/76470-shaped unit regression for date-only REENTRY rows.
- Added an actual Historical Strategy entrypoint regression that re-materializes `2022-10-06` from copied target evidence and confirms final serialized PC contains prior IDs even when REENTRY is rejected.

## Why This Is Canonical

This repair does not infer or regenerate provenance downstream. It only propagates the already resolved upstream strict-prior PM EXIT context through the existing Strategy shadow -> PC contract.

The canonical authority remains:

- persistent ledger execution history for closed campaign lifecycle
- strict-prior PM EXIT decision evidence for PM reason/provenance context
- explicit campaign identity on PM/execution artifacts

No hash bypass, fail-closed bypass, Strategy threshold change, candidate selection change, re-entry rule change, BUY_ADD change, Cash/Risk Pacing change, or G129 semantic change was made.

## Validation

Executed focused validation:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase29_l21k_prior_exit_materialization.py
```

Result: `26 passed`

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py
```

Result: `16 passed`

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -k 'reentry or broker or corporate_action'
```

Result: `7 passed, 117 deselected`

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase26_h_adaptive_buy_quality.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py::test_phase30_s_ps_consumes_pc_buy_quality_reason_code_without_rethresholding
```

Result: `25 passed`

```bash
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews
```

Result: `2 passed`

```bash
git diff --check
```

Result: PASS

## Strict-Prior Confirmation

The repair does not alter temporal selection. `_supply_prior_exit_state()` still resolves executions and PM EXIT artifacts only where source business date is strictly less than the REENTRY decision business date. Existing same-day/future exclusion tests remain passing.

## Strategy Semantic Change

NO.

The change preserves provenance fields. It does not change Strategy parameters, thresholds, weights, candidate selection, ranking, REENTRY cooldown/recovery logic, Cash policy, Risk Pacing, ADD policy, PM semantics, or G129 BUY_ADD semantics.

## G129 Regression

NO.

Focused G129 BUY_ADD tests passed.

## Remaining Known Issues

No remaining Phase32-O blocker is left for prior EXIT provenance materialization in the active Strategy -> PC path.

Historical actual-path acceptance still requires a user-operated fresh-run or continued run evidence to prove the repaired fields are present in newly generated canonical run artifacts beyond focused re-materialization.

## Exact Next User Action

Run a user-operated Historical fresh-run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-extended-smoke --start-date 2022-10-03 --business-days 100 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state
```

## Final Judgment

`PHASE32_P_REENTRY_PRIOR_PROVENANCE_ACTUAL_MATERIALIZATION_REPAIRED`
