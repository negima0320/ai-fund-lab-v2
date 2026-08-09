# Phase28-D4: Submit Exit Code 20 Root Cause Confirmation

Task ID: `Phase28-D4`

Task Type: `READ_ONLY DIAGNOSIS`

Status: `COMPLETE`

Implementation Changed: `false`

Resume Executed: `false`

Fresh Run Executed: `false`

Long Historical Executed: `false`

## Executive Summary

The first Runtime code location that returned exit code `20` for the Phase28-D post-D3 fresh 100BD run was:

```text
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:915-917
```

The CLI set:

```text
exit_code = EXIT_REVIEW_REQUIRED
```

because `run_submit_pipeline(...)` returned:

```text
status = REVIEW_REQUIRED
reason = submit completed with rejected/unknown/blocked items
```

The first authority producer that caused the submit item review was:

```text
runtime_v2_corporate_action_adjustment_authority
```

It flagged symbol `76920`, side `SELL`, pending item `strategy-3065ae70fb016c7cc2c9`, planning intent `SELL_EXIT`, source planning id `rp-2023-03-15-76920-sell_exit-b7a0cb7f9a04b8dd`.

The direct root cause is a corporate action adjustment authority review:

```text
corporate_action_event_not_resolved
corporate_action_type_unresolved
corporate_action_ledger_adjustment_missing
corporate_action_current_adjustment_missing
corporate_action_pending_quantity_stale
corporate_action_already_applied_not_confirmed
corporate_action_adjusted_quantity_missing
```

This is not directly caused by Phase28-C or Phase28-D3. Wi-Fi is not causal for this halt.

## Target Run

```text
run_id: runtime-test-historical-smoke-20260805T204551337825Z
halt date: 2023-03-15
halt stage: submit
Runtime CLI exit code: 20
```

Evidence:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260805T204551337825Z/daily/2023-03-15/submit/cli_result.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260805T204551337825Z/daily/2023-03-15/submit/runtime_manifest.json`
- `.runtime/runtime_state/corporate_action_adjustments/2023-03-15/76920.json`

## Exit Code 20 Trace

Code trace:

1. `run_daily_operation.py` defines `EXIT_REVIEW_REQUIRED = 20` at line `92`.
2. For job `submit`, it calls `run_submit_pipeline(...)` at lines `880-899`.
3. It appends stage `runtime_v2_submit_pipeline` at lines `903-909`.
4. If `submit_result.status == "REVIEW_REQUIRED"`, it sets `exit_code = EXIT_REVIEW_REQUIRED` at lines `915-917`.
5. It returns the process exit code at line `1153`.

The submit runtime manifest confirms:

```text
final_state = REVIEW_REQUIRED
exit_code = 20
reason = submit completed with rejected/unknown/blocked items
pending_item_count = 7
submitted_count = 6
blocked_count = 1
review_required = true
```

The first `REVIEW_REQUIRED` execution stage is:

```text
runtime_v2_submit_pipeline
```

with:

```text
submitted_count = 6
blocked_count = 1
pending_item_count = 7
```

## Affected Item

The affected submit guard item evidence is:

```text
symbol = 76920
side = SELL
pending_item_id = strategy-3065ae70fb016c7cc2c9
submit_feasibility_sequence_index = 3
submit_item_status = REVIEW_REQUIRED
violated_policy = corporate_action_adjustment_authority
violated_policy_source = .runtime/runtime_state/corporate_action_adjustments/2023-03-15/76920.json
should_have_been_blocked_at_planning = true
```

This is a `SELL_EXIT`, not `BUY_NEW`, `BUY_ADD`, or `REDUCE`.

Pending lineage:

```text
source_decision_type = SELL_EXIT
planning_authority_source = rp-2023-03-15-76920-sell_exit-b7a0cb7f9a04b8dd
source_pm_decision_id = ""
source_position_symbol = 76920
quantity = 100
price = 563.7
```

Strategy Runtime Planning lineage:

```text
planning_id = rp-2023-03-15-76920-sell_exit-b7a0cb7f9a04b8dd
planning_intent = SELL_EXIT
quantity_delta_candidate = -100
target_quantity_candidate = 0
reason_codes:
  - position_sizing_negative_quantity_delta_maps_to_sell_exit
  - position_sizing_quantity_candidate_resolved
```

## Authority Producer

The authority producer is:

```text
runtime_v2_corporate_action_adjustment_authority
```

Artifact:

```text
.runtime/runtime_state/corporate_action_adjustments/2023-03-15/76920.json
```

The artifact records:

```text
status = REVIEW_REQUIRED
event_status = IMPACT_DETECTED
event_type = UNKNOWN_ADJFACTOR_IMPACT
adjustment_factor = 0.25
effective_date = 2023-03-15
reason = corporate_action_event_type_or_adjustment_application_unresolved
quantity_reconciliation_status = REVIEW_REQUIRED
price_reconciliation_status = REVIEW_REQUIRED
```

Its lineage identifies the producer and market evidence source:

```text
producer = runtime_v2_corporate_action_adjustment_authority
source = jquants_raw_equities_bars_daily_adjfactor
source_artifact_path = reports/runtime_tests/runs/runtime-test-historical-smoke-20260805T204551337825Z/daily/2023-03-15/market_refresh/inputs/historical_asof/2023-03-15/raw/jquants/equities_bars_daily/data.parquet
```

## Code Producer Path

The submit item guard calls:

```text
evaluate_corporate_action_adjustment_authority(...)
```

in:

```text
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:1702-1712
```

If the authority status is not `PASS`, Submit Guard returns blocked guard evidence:

```text
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:1714-1720
```

That evidence is materialized as:

```text
guard_decision = BLOCKED
manual_review_required = true
submit_item_status = REVIEW_REQUIRED
violated_policy = corporate_action_adjustment_authority
```

by:

```text
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:2347-2358
```

The corporate action authority is implemented at:

```text
src/ai_fund_lab_v2/runtime_v2/corporate_action_adjustment.py:117-242
```

It accepts an impacted submit only when Runtime-owned adjustment evidence proves event type, PIT binding, idempotency, and quantity reconciliation. For `76920`, it did not.

## Submit Aggregate Reason

Submit pipeline submitted six items and blocked/reviewed one item. Therefore it set:

```text
status = REVIEW_REQUIRED
reason = submit completed with rejected/unknown/blocked items
```

at:

```text
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:619-621
```

This aggregate reason is downstream of the first item-level producer. It is not the root cause.

## Classification

```text
Producer: Submit Guard item-level corporate action adjustment authority
Outcome: REVIEW_REQUIRED
Guard decision: BLOCKED
Submit aggregate: REVIEW_REQUIRED
Affected side: SELL
Affected intent: SELL_EXIT
Affected symbol: 76920
Affected pending item: strategy-3065ae70fb016c7cc2c9
Affected decision id: rp-2023-03-15-76920-sell_exit-b7a0cb7f9a04b8dd
```

## Phase28-C Causality

Phase28-C direct causality is `false`.

Reason:

- The affected item is `SELL_EXIT`.
- The halt is produced by corporate action adjustment authority at Submit.
- Phase28-C changed canonical ADD allocation bridge behavior in Portfolio Construction / Position Sizing.
- No evidence shows Phase28-C ADD bridge produced the `76920` corporate action adjustment review.

## Phase28-D3 Causality

Phase28-D3 direct causality is `false`.

Reason:

- D3 changed SELL pending reconciliation before submit.
- The D4 halted item reached Submit as approved pending.
- The first review producer is Submit Guard corporate action adjustment authority.
- The reason is unresolved corporate action adjustment for `76920`, not same-symbol SELL pending reconciliation.

Phase28-D3 is temporally before this run, but not the direct causal producer.

## Wi-Fi Causality

Wi-Fi causality is `false`.

Evidence:

- The submit command ran with `--mode historical` and `--broker-environment historical_simulated`.
- The submit command included `--market-refresh-allow-api-fetch false`.
- Runtime manifest records `broker_write=false`, `external_delivery=false`, `simulation=true`, `tachibana_demo_write=false`, `tachibana_production_write=false`.
- Subprocess trace records `status=COMPLETED`, `returncode=20`, `timed_out=false`, `killed_after_grace=false`, `stderr=""`.
- Historical environment composition rejects `external_delivery=true` and `broker_write=true` for historical mode at `historical_support/environment.py:701-706`.
- `HistoricalSubmitAdapter` returns `broker_api_called=false` and reason `historical submit adapter isolated; no external broker access` in preflight.
- Static code search under submit/historical/broker adapter paths found no `requests`, `socket`, DNS, or network exception path causing this review.

Therefore the Wi-Fi disconnection did not cause this submit exit code 20.

## Repair Required

Repair is required if Phase28-D should proceed through this date without manual review:

```text
Repair target: Corporate Action Adjustment Authority / planning-stage corporate action blocking for SELL_EXIT pending
```

The repair should not be Phase28-C ADD bridge or Phase28-D3 pending reconciliation. The immediate design question is how Runtime should handle `AdjFactor != 1` on the target submit date for SELL pending when event type and adjusted quantity are unresolved.

## Next Phase

Recommended next phase:

```text
Phase28-D5: Corporate Action Adjustment Authority Submit Review Diagnosis / Repair Design
```

D5 should remain scoped to corporate action adjustment authority and planning/submit alignment.

## Final Judgment

```text
exit20 Producer: runtime_v2_corporate_action_adjustment_authority via Submit Guard
exit20 Direct Reason: corporate_action_event_not_resolved / corporate_action_type_unresolved with unresolved adjusted quantity evidence
Affected Symbol: 76920
Affected Side: SELL
Affected Pending: strategy-3065ae70fb016c7cc2c9
Affected Decision: rp-2023-03-15-76920-sell_exit-b7a0cb7f9a04b8dd
Root Cause: Submit Guard corporate action adjustment authority fail-closed on AdjFactor 0.25 impact detected for SELL_EXIT
Phase28-C Direct Causality: false
Phase28-D3 Direct Causality: false
Wi-Fi Causality: false
Repair Required: true
Next Phase: Phase28-D5 Corporate Action Adjustment Authority repair design
```
