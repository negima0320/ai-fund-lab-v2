# Phase32-AY - 2023-10-11 Canonical Regeneration + Resume Acceptance

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T003243720082Z`
- Target boundary: `2023-10-11:sell_planning`
- Mode: canonical recovery/regeneration and same-run resume
- Fresh run: NOT executed
- Strategy/config/threshold/model changes: NONE

## Pre-Mutation Safety Proof

Before mutation, the run was HALT at `2023-10-11:sell_planning` with `next_job = 2023-10-11:sell_planning`.

The current Pending slot was a stale pre-AX plan:

- `pending_plan_id = pending-strategy-plan-historical-2023-10-11-049fca273c90bbe0`
- `state = REVIEW_REQUIRED`
- `review_scope = AUTHORITY_UNKNOWN_REVIEW`
- approved items: `[]`
- reviewed SELL: `50280`
- reviewed BUYs: `38560`, `76920`
- independent feasible SELL `92460` was blocked by batch review.

Target-date side-effect proof before recovery:

- `.runtime/persistent_ledger/orders.jsonl`: `0` rows for `2023-10-11`
- `.runtime/persistent_ledger/executions.jsonl`: `0` rows for `2023-10-11`
- `.runtime/persistent_ledger/positions.jsonl`: `0` rows for `2023-10-11`
- `.runtime/persistent_ledger/cash.jsonl`: `0` rows for `2023-10-11`
- `.runtime/persistent_ledger/events.jsonl`: `0` rows for `2023-10-11`
- `daily/2023-10-11/submit`: absent
- `daily/2023-10-11/execution`: absent

Therefore there was no submit artifact, execution artifact, broker/API side effect, or accepted same-day order requiring preservation.

## Canonical Regeneration Path Used

The existing supported command matched the target shape:

`recover-stale-pending`

This is the documented canonical path for:

- HALT at `<date>:sell_planning`
- same-day `REVIEW_REQUIRED` Pending
- no target-date Ledger rows

Dry-run command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py recover-stale-pending \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-extended-smoke-20260831T003243720082Z \
  --business-date 2023-10-11 \
  --rewind-to-job morning \
  --dry-run \
  --json
```

Dry-run result: `DRY_RUN`, exit code `0`, no errors.

Actual recovery command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py recover-stale-pending \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-extended-smoke-20260831T003243720082Z \
  --business-date 2023-10-11 \
  --rewind-to-job morning \
  --expected-pending-plan-id pending-strategy-plan-historical-2023-10-11-049fca273c90bbe0 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Actual recovery result: `PASS`, exit code `0`.

The recovery superseded the stale Pending and rewound run state from `2023-10-11:sell_planning` to `2023-10-11:morning`. Ledger/current-state hashes were unchanged except the Pending slot.

## Regeneration Scope

Scoped replay command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py replay-recovered-day \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-extended-smoke-20260831T003243720082Z \
  --business-date 2023-10-11 \
  --jobs morning,sell_planning \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Replay result: `PASS`, exit code `0`.

Executed jobs:

- `2023-10-11:morning`: exit `0`
- `2023-10-11:sell_planning`: exit `0`

This regenerated only the pre-submit boundary. Submit and execution were not run during scoped regeneration.

## Regenerated Pending Scope

Regenerated Pending:

- `pending_plan_id = pending-strategy-plan-historical-2023-10-11-84b153a169af27d4`
- `state = REVIEW_REQUIRED`
- `review_scope = MIXED_SELL_ITEM_SCOPED_REVIEW`
- `sell_continuation_allowed = true`
- `approved_item_ids = [strategy-63ee5549e637f6d247bc]`
- `approved_sell_item_ids = [strategy-63ee5549e637f6d247bc]`
- `review_required_sell_item_ids = [strategy-23fa7fa4d9acabff2823]`
- `review_required_buy_item_ids = [strategy-17b52bb1ef77d6312d14, strategy-7f7dbf5b074dc8f8ef12]`

Item outcomes:

| Symbol | Side | Quantity | Pending item | Final regenerated status |
|---|---:|---:|---|---|
| `50280` | SELL | `100` | `strategy-23fa7fa4d9acabff2823` | `REVIEW_REQUIRED`, feasibility `REVIEW_REQUIRED` |
| `92460` | SELL | `100` | `strategy-63ee5549e637f6d247bc` | `APPROVED`, feasibility `PASS` |
| `38560` | BUY | `100` | `strategy-17b52bb1ef77d6312d14` | `REVIEW_REQUIRED`, feasibility `REVIEW_REQUIRED` |
| `76920` | BUY | `400` | `strategy-7f7dbf5b074dc8f8ef12` | `REVIEW_REQUIRED`, feasibility `REVIEW_REQUIRED` |

Stale Corporate Action lineage check:

- `daily/2023-10-11/sell_planning/sell_planning_manifest.json`: no `20260830T081425790243Z` lineage string
- `daily/2023-10-11/sell_planning/runtime_manifest.json`: no `20260830T081425790243Z` lineage string
- current run id present on regenerated runtime evidence

Duplicate identity check before resume:

- target-date Ledger rows remained `0`
- `daily/2023-10-11/submit`: absent
- `daily/2023-10-11/execution`: absent

## Resume

Resume dry-run command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-extended-smoke-20260831T003243720082Z \
  --dry-run \
  --json
```

Dry-run result: `DRY_RUN`, exit code `0`, `resume_allowed = true`.

Actual resume command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-extended-smoke-20260831T003243720082Z \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Actual resume result:

- status: `HALT`
- exit code: `30`
- error: `resume stopped at 2023-10-11:current_valuation_refresh with exit code 20`

The run did not reach `2023-10-12`.

## 2023-10-11 Post-Resume Evidence

Completed after resume:

- `submit`: exit `0`
- `execution`: exit `0`
- `current_valuation_refresh`: exit `20`

Submit/execution outcome:

- `50280`: remained unsubmitted
- `38560`: remained unsubmitted
- `76920`: remained unsubmitted
- `92460`: submitted/executed once
- duplicate submit/execution observed: NO
- broker write / production access: NO

Ledger rows now present for `2023-10-11`:

- orders: `1`
- executions: `1`
- positions: `4`
- cash: `1`
- events: `0`

The order/execution rows are for the approved `92460` SELL:

- `pending_plan_id = pending-strategy-plan-historical-2023-10-11-84b153a169af27d4`
- `pending_item_id = strategy-63ee5549e637f6d247bc`
- `source_decision_id = rp-2023-10-11-92460-sell_exit-3a396b4dce6e273e`
- `source_pm_decision_id = pm-2023-10-11-92460-reduce`
- executed quantity: `100`
- average price: `3250.0`

The Pending slot after execution remains active review-scoped:

- `state = REVIEW_REQUIRED`
- `review_scope = MIXED_SELL_ITEM_SCOPED_REVIEW`
- `92460` item state: `CONSUMED`
- `50280`, `38560`, `76920`: still `REVIEW_REQUIRED`

## New HALT

First new failed boundary after successful regeneration and 92460 execution:

`2023-10-11:current_valuation_refresh`

Canonical failure evidence:

- `daily/2023-10-11/current_valuation_refresh/runtime_manifest.json`
- `daily/2023-10-11/current_valuation_refresh/safety_authority_decision.json`
- `daily/2023-10-11/current_valuation_refresh/valuation_apply_evidence.json`

Failure reason:

- `historical_safety_temporal_authority_missing`

Manifest details:

- `final_state = REVIEW_REQUIRED`
- `exit_code = 20`
- `component_reasons.safety = [historical_safety_temporal_authority_missing]`
- `component_reasons.pending = [pending_review_required]`
- `batch_blocking_review_guard_count = 2`
- `final_safety_status = REVIEW_REQUIRED`

Valuation did not apply:

- `valuation_apply_evidence.status = NOT_EXECUTED`
- `blocked_before_producer = true`
- `blocking_stage = runtime_data_readiness_gate`
- `blocking_reason = historical_safety_temporal_authority_missing`

External effects at current valuation:

- broker order API calls: `0`
- broker write: `false`
- notification delivery: `0`
- J-Quants fetch calls: `0`
- production access: `false`

## Acceptance Status

Canonical regeneration acceptance:

- `recover-stale-pending`: PASS
- scoped `morning,sell_planning` replay: PASS
- regenerated Pending uses `MIXED_SELL_ITEM_SCOPED_REVIEW`: PASS
- `50280` remains review-required and unapproved: PASS
- `92460` independently approved/executable: PASS
- reviewed BUYs remain blocked/unsubmitted: PASS
- stale `20260830T081425790243Z` CA lineage absent from regenerated sell_planning evidence: PASS
- no duplicate order/pending identity before resume: PASS

Resume acceptance:

- actual resume executed: YES
- `2023-10-11` submit passed: YES
- `2023-10-11` execution passed: YES
- `92460` executed once: YES
- `50280` remained unsubmitted: YES
- `2023-10-11` completed: NO
- `2023-10-12` reached: NO
- blocked by new `current_valuation_refresh` authority gap.

## Required Final Answers

- `CANONICAL_REGENERATION_PATH_USED`: `recover-stale-pending` followed by scoped `replay-recovered-day --jobs morning,sell_planning`.
- `REGENERATION_SCOPE`: `2023-10-11` pre-submit boundary only; no submit/execution during regeneration.
- `REGENERATED_PENDING_SCOPE`: `MIXED_SELL_ITEM_SCOPED_REVIEW`.
- `50280_FINAL_STATUS`: `REVIEW_REQUIRED`, not approved, not submitted.
- `92460_FINAL_STATUS`: approved after regeneration, submitted/executed once after resume, then Pending item `CONSUMED`.
- `STALE_CA_LINEAGE_PRESENT`: NO in regenerated sell_planning evidence.
- `DUPLICATE_SIDE_EFFECT_RISK`: no duplicate observed; submit/execution side effects are now present for `92460`, so further recovery must preserve/idempotently respect that row.
- `RESUME_EXECUTED`: YES.
- `2023_10_11_COMPLETED`: NO.
- `2023_10_12_REACHED`: NO.
- `CURRENT_RUN_STATUS`: `HALT` at `2023-10-11:current_valuation_refresh`, exit code `20`.
- `ANY_NEW_DEFECT`: YES, current valuation readiness blocks on `historical_safety_temporal_authority_missing` plus residual review Pending after mixed-sell execution.
- `FRESH_RUN_REQUIRED`: UNCONFIRMED; no evidence yet requires a fresh-run, but same-run continuation needs a canonical audit/repair for the current valuation boundary.
- `FINAL_JUDGMENT`: `PHASE32_AY_CANONICAL_REGENERATION_SUCCEEDED_RESUME_BLOCKED_AT_2023_10_11_CURRENT_VALUATION_REFRESH`

