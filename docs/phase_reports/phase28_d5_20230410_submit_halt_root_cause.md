# Phase28-D5: 2023-04-10 Submit HALT Root Cause Diagnosis

Task ID: `Phase28-D5`

Task Type: `READ_ONLY DIAGNOSIS`

Status: `COMPLETE`

Implementation Changed: `false`

Resume Executed: `false`

Fresh Run Executed: `false`

Long Historical Executed: `false`

## Executive Summary

The `2023-04-10` submit halt in run
`runtime-test-historical-smoke-20260805T231619492537Z` is not the same
Corporate Action case diagnosed in Phase28-D4.

The first producer that created the item-level `REVIEW_REQUIRED` was:

```text
historical_simulated_broker_authority via Submit Guard broker_available_quantity check
```

The affected item was:

```text
symbol: 43880
side: SELL
intent: SELL_EXIT
pending_item_id: strategy-d3ca3c09c7e90609497b
decision/planning id: rp-2023-04-10-43880-sell_exit-721a37484a2e69ca
```

Direct reason:

```text
sell broker available quantity missing
```

The underlying direct evidence reason was:

```text
listed_info_missing
```

The pending payload for the two submitted SELL items (`83060`, `94320`)
contained `listed_info`, but the halted item (`43880`) had:

```text
listed_info: null
```

That missing `listed_info` prevented broker issue-code normalization for the
historical simulated broker authority. The Submit Guard therefore could not
materialize `broker_available_quantity`, even though Current quantity was
present and equal to the sell quantity (`100`).

## Target Run

```text
run_id: runtime-test-historical-smoke-20260805T231619492537Z
start_date: 2023-04-03
halt date: 2023-04-10
halt stage: submit
Runtime CLI exit code: 20
```

Evidence:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260805T231619492537Z/daily/2023-04-10/submit/cli_result.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260805T231619492537Z/daily/2023-04-10/submit/runtime_manifest.json`
- `.runtime/runtime_state/run_manifest/2023-04-10/runtime-v2-submit-2023-04-10-20260805T233007.599195+0000.json`

## Submit Result

The submit manifest recorded:

```text
final_state: REVIEW_REQUIRED
exit_code: 20
reason: submit completed with rejected/unknown/blocked items
pending_item_count: 3
submitted_count: 2
blocked_count: 1
review_required: true
broker_environment: historical_simulated
external_delivery: false
broker_write: false
```

The three item sequence was:

```text
idx 0: 83060 SELL SELL_EXIT PASS
idx 1: 94320 SELL SELL_EXIT PASS
idx 2: 43880 SELL SELL_EXIT REVIEW_REQUIRED
```

The first and only blocked item was:

```text
submit_feasibility_sequence_index: 2
submit_item_status: REVIEW_REQUIRED
guard_decision: BLOCKED
violated_policy: broker_available_quantity
violated_policy_source: historical_simulated_broker_authority
guard_reason: sell broker available quantity missing
blocked_at_submit_reason: sell broker available quantity missing
broker_available_quantity: null
broker_available_quantity_reason: listed_info_missing
current_quantity: 100.0
quantity: 100.0
```

## Code Trace

The CLI exit code path is:

1. `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:880-899`
   calls `run_submit_pipeline(...)`.
2. `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:381-418`
   evaluates each approved pending item.
3. In historical mode,
   `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:384-393`
   chooses `_historical_available_quantity_evidence(...)` for SELL items.
4. `_broker_issue_code_for_item(...)` at
   `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:1506-1511`
   calls `normalize_broker_issue_code(item.symbol, listed_info=item.listed_info)`.
5. `src/ai_fund_lab_v2/broker/issue_code_normalizer.py:50-60`
   raises `listed_info_missing` when `listed_info` is `None`.
6. `_historical_available_quantity_evidence(...)` at
   `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:1407-1414`
   returns `source=historical_simulated_broker_authority`,
   `checked=false`, and reason `listed_info_missing`.
7. `_sell_guard_evidence(...)` at
   `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:2303-2310`
   turns `broker_available_quantity is None` into:

```text
guard_decision: BLOCKED
submit_item_status: REVIEW_REQUIRED
violated_policy: broker_available_quantity
reason: sell broker available quantity missing
```

8. `_blocked_guard_evidence(...)` at
   `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:2347-2357`
   materializes the item-level `REVIEW_REQUIRED`.
9. Aggregate submit status becomes `REVIEW_REQUIRED` at
   `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:619-621`
   because submit completed with one blocked item.
10. `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:915-917`
    maps submit result `REVIEW_REQUIRED` to `EXIT_REVIEW_REQUIRED` (`20`).

## Pending Evidence

The submit run manifest pending payload confirms that `43880` lacked the
listed-info authority required by broker normalization:

```text
pending_item_id: strategy-d3ca3c09c7e90609497b
symbol: 43880
side: SELL
quantity: 100.0
source_decision_type: SELL_EXIT
source_pm_decision_id: ""
planning_authority_source: rp-2023-04-10-43880-sell_exit-721a37484a2e69ca
listed_info: null
quantity_contract.planning_intent: SELL_EXIT
quantity_contract.source_planning_id: rp-2023-04-10-43880-sell_exit-721a37484a2e69ca
```

By contrast, the two preceding PASS items (`83060`, `94320`) had populated
`listed_info` including `code`, `market`, `product_category`, `security_type`,
and `current_listed`.

## Corporate Action Check

This halt is not a Corporate Action block.

Submit guard evidence for `43880` recorded:

```text
corporate_action_adjustment_authority_status: PASS
corporate_action_adjustment_authority_reason: corporate_action_not_detected
corporate_action_event_status: PASS
corporate_action_event_type: UNKNOWN_ADJFACTOR_IMPACT
corporate_action_adjustment_factor: 1.0
corporate_action_reason_codes: []
double_adjustment_detected: false
```

Therefore the D5 halt is separate from the D4 `2023-03-15 / 76920` Corporate
Action authority case.

## Causality

Phase28-C direct causality: `false`

Reason: the affected item is `SELL_EXIT`, not `BUY_NEW` or `BUY_ADD`; the
blocked policy is `broker_available_quantity`, not canonical ADD allocation.

Phase28-D3 direct causality: `false`

Reason: D3 repaired runtime sell pending reconciliation. The D5 affected
pending item reached submit with `quantity_status=RESOLVED_EXECUTABLE`,
`planning_status=PASS`, `quantity_reconciliation_status=PASS`, and
Current quantity `100.0`. The direct failure is missing pending `listed_info`
needed by broker normalization, not pending conflict reconciliation.

Evaluation period change: `true`

Reason: changing the run start date to `2023-04-03` exposed a new
`2023-04-10 / 43880` submit case. It is a new occurrence in the changed period
and is not the previously diagnosed `2023-03-15 / 76920` Corporate Action case.

## Final Judgment

```text
exit20 Producer: historical_simulated_broker_authority via Submit Guard broker_available_quantity check
Direct Reason: sell broker available quantity missing; underlying reason listed_info_missing
Symbol: 43880
Side: SELL
Pending Item: strategy-d3ca3c09c7e90609497b
Decision ID: rp-2023-04-10-43880-sell_exit-721a37484a2e69ca
Intent: SELL_EXIT
Root Cause: SELL_EXIT pending item lacked listed_info, so broker issue-code normalization failed and historical simulated broker available quantity stayed null.
Corporate Action: false
Phase28-C Direct Causality: false
Phase28-D3 Direct Causality: false
Repair Required: true
Next Phase: Phase28-D6 historical SELL pending listed_info authority repair design
```
