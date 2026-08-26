# Phase31-A1 - 2022-09-16 Data Readiness HALT Root-Cause Audit

## PRIMARY_JUDGMENT

`PHASE31_A1_PENDING_LIFECYCLE_MIXED_BUY_REVIEW_SELL_CONTINUATION_CONSUMER_GAP_CONFIRMED`

The `2022-09-16:data_readiness` stop was not caused by Strategy performance,
BUY/SELL threshold quality, missing market data, missing feature data, or a
Historical Safety temporal mismatch. The first semantic non-pass layer was the
pre-Data-Readiness Pending lifecycle authority, which failed closed on a stale
mixed `BUY_ITEM_SCOPED_REVIEW` Pending plan created on `2022-09-15`.

The active Pending shape was:

- reviewed BUY items: `43550`, `70110`, `94320`
- approved executable SELL item: `78780`
- review scope: `BUY_ITEM_SCOPED_REVIEW`
- sell continuation: allowed
- target session date: `2022-09-15`

On `2022-09-15`, Submit correctly submitted only the executable SELL and did
not submit reviewed BUY items. Execution then filled the SELL, but left the
mixed Pending plan non-terminal. On `2022-09-16`, the pre-Data-Readiness
Pending lifecycle consumer could not terminalize that stale mixed shape and
returned `REVIEW_REQUIRED` with `buy_item_scoped_review_pending_shape_invalid`.

This is a focused Pending lifecycle producer/consumer semantic gap for
mixed BUY-review / SELL-continuation residual state. It is not evidence that
the Phase31 Strategy should be changed.

## TARGET_RUN

`runtime-test-historical-extended-smoke-20260817T232738846101Z`

User-operated command:

```text
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-08-10 \
  --business-days 500 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

## FAILURE_DATE

`2022-09-16`

## FAILURE_STAGE

`data_readiness`

Runtime CLI exit code at boundary: `20`

Outer `runtime_test.py` exit code: `30`

## FIRST_NON_PASS_LAYER

`runtime_v2.pending.lifecycle_runner.run_pending_lifecycle_review`

This was invoked by the Runtime CLI before the Data Readiness gate:

```text
pre_data_readiness_pending_lifecycle
```

The Runtime order matches the Phase30-AK9R31 real orchestration contract:

```text
pending_lifecycle_pre_data_readiness_when_required
-> runtime_data_readiness_gate
```

## DIRECT_PRODUCER

Direct producer:

```text
runtime_v2.pending.lifecycle_runner.run_pending_lifecycle_review
```

Direct sub-authority:

```text
_buy_item_scoped_review_no_submission_terminalization_authority
```

The sub-authority first called:

```text
_buy_item_scoped_review_pending_evidence
```

That evidence rejected the current Pending shape before Data Readiness itself
could run.

## DIRECT_ARTIFACT

Primary direct artifact:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260817T232738846101Z/daily/2022-09-16/data_readiness/runtime_manifest.json
```

CLI boundary artifact:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260817T232738846101Z/daily/2022-09-16/data_readiness/cli_result.json
```

Relevant prior-day artifacts:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260817T232738846101Z/daily/2022-09-15/sell_planning/runtime_manifest.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260817T232738846101Z/daily/2022-09-15/submit/runtime_manifest.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260817T232738846101Z/daily/2022-09-15/execution/runtime_manifest.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260817T232738846101Z/daily/2022-09-15/execution/pending_terminalization_evidence.json
```

## DIRECT_REASON

Exact direct reason:

```text
buy_item_scoped_review_pending_shape_invalid
```

Direct transition fields:

```text
previous_state = REVIEW_REQUIRED
new_state = REVIEW_REQUIRED
pending_lifecycle_status = REVIEW_REQUIRED
transition_reason = buy_item_scoped_review_pending_shape_invalid
submit_attempt_detected = true
unknown_submit_risk = true
```

The `buy_item_scoped_review_no_submission_terminalization.checks` field shows
the failing shape:

```text
all_items_buy = false
approved_item_ids_empty = false
pending_target_session_same_day = false
pending_review_scope_authority_no_submission = false
```

The embedded canonical Pending Review Scope Authority itself was structurally
valid:

```text
contract_id = pending_review_scope_authority
contract_version = phase30_ak9r27_v1
structural_validity = PASS
review_scope = BUY_ITEM_SCOPED_REVIEW
batch_blocked = false
partial_submit_allowed = true
sell_continuation_allowed = true
reviewed_sell_item_ids = []
executable_sell_item_ids = ["strategy-bbf1a3d0f3c750f670c9"]
reviewed_buy_item_ids = [
  "strategy-5d8574a0843ff9b1d715",
  "strategy-106a32f7024933e3cd3f",
  "strategy-c50328b222ac9b21b1f4"
]
```

## GUARD_CLASS

`UNMAPPED_TYPED_GUARD_NOT_MATERIALIZED`

Semantic classification: `INTERNAL_SYSTEM_CONSISTENCY` is the closest Phase30
taxonomy class because the stop is a fail-closed unresolved lifecycle /
producer-consumer consistency issue, not market risk, execution cash/quantity
safety, item-level investment review, or missing PIT data.

However, the direct `pre_data_readiness_pending_lifecycle` artifact did not
materialize an AK9R29 typed `review_guard_result`. Therefore the exact
materialized guard class is unresolved and should be treated as a small
taxonomy/conformance concern in the focused repair task.

## LEGITIMATE_FAIL_CLOSED

`YES`

The fail-closed stop is operationally legitimate because the Runtime found a
stale active Pending plan with a submit attempt recorded and could not prove
safe terminalization. It correctly did not fail open, did not submit reviewed
BUY items, and did not continue the long run through an unresolved Pending
lifecycle state.

The underlying lifecycle gap still requires repair before long-horizon
performance characterization resumes.

## STRATEGY_CAUSAL

`NO`

The stop was not caused by Strategy thresholds, Expected Edge, Entry Quality,
SELL timing, exposure, or Re-entry behavior. It arose after valid mixed
Pending composition and partial SELL continuation.

## RUNTIME_DEFECT

`YES`

Focused Runtime/Pending lifecycle defect confirmed.

## TEMPORAL_AUTHORITY_DEFECT

`NO`

The observed temporal binding path did not fail. On `2022-09-15`, Data
Readiness reported:

```text
data_readiness_status = READY
safety_status = PASS
safety_decision = NEUTRAL
safety_reason = historical_neutral_no_event_safety_ready
review_guard_classes = []
review_guard_codes = []
```

The `2022-09-16` failure occurred before Data Readiness generated a new
`data_readiness.json`, because pre-Data-Readiness Pending lifecycle returned
`REVIEW_REQUIRED`.

## DATA_SOURCE_OR_MATERIALIZATION_GAP

`NO`

The `2022-09-16` market refresh completed and the CLI reached Data Readiness.
The direct failure evidence is Pending lifecycle state, not missing market,
feature, quote, model, or calendar evidence.

## PRODUCER_CONSUMER_GAP

`YES`

The producer side emitted a valid canonical mixed Pending Review Scope:
reviewed BUY items remained fail-closed and an executable SELL was allowed to
continue. Submit consumed that shape correctly by submitting only the SELL and
not submitting the reviewed BUY items.

The next-day lifecycle consumer then evaluated the stale mixed shape through a
terminalization path whose no-submission predicate expects an all-BUY /
no-approved-item shape. That consumer did not handle the valid mixed
SELL-submitted plus residual reviewed-BUY shape as a terminalizable residual
state.

## PHASE30_ARCHITECTURE_REGRESSION

`YES`

Narrow regression / uncovered edge confirmed:

- `BUY_ITEM_SCOPED_REVIEW` did not block the valid `SELL` on `2022-09-15`.
- Submit did not submit reviewed BUY items.
- Quantity and cash authority were not re-decided.
- Historical Safety temporal authority did not fail.
- Reason-string inference was not the primary active decision path.

But the lifecycle consumer failed to preserve the Phase30 intent for mixed
BUY-review / SELL-continuation residual Pending after the approved SELL was
executed. This is a lifecycle consumer conformance gap, not a rollback of the
whole Phase30 architecture.

## PASS_TO_HALT_DELTA

`2022-09-14`:

- `data_readiness` exited `0`.
- Pre-Data-Readiness lifecycle was invoked for an elapsed Pending but returned
  `NOOP`.
- `submit_attempt_detected = false`.
- `unknown_submit_risk = false`.

`2022-09-15`:

- `data_readiness` exited `0`.
- Pending slot was `EMPTY` at morning Data Readiness.
- Sell Planning created a mixed composite Pending plan:
  `pending-order-plan-buy-review-sell-continuation-2022-09-15-da72b6e18223`.
- Pending contained reviewed BUY items and one approved SELL item.
- Submit passed and submitted only the SELL, with reason
  `submitted_with_reviewed_buy_items_not_submitted`.
- Execution filled one SELL, but
  `execution/pending_terminalization_evidence.json` reported:

```text
pending_plan_present = true
pending_classification = VALID
pending_consumed = false
pending_mutated = false
status = NOT_REQUIRED
```

`2022-09-16`:

- The stale `2022-09-15` mixed Pending was still active at pre-Data-Readiness.
- `pre_data_readiness_pending_lifecycle_requirement.status =
  PENDING_LIFECYCLE_REQUIRED`.
- The lifecycle authority returned `REVIEW_REQUIRED` with
  `buy_item_scoped_review_pending_shape_invalid`.
- Runtime CLI stopped with exit code `20`.

Smallest relevant state transition:

```text
2022-09-15 mixed BUY_ITEM_SCOPED_REVIEW + executable SELL Pending
-> SELL-only submit/fill
-> Pending left non-terminal
-> 2022-09-16 pre-Data-Readiness lifecycle cannot terminalize mixed residual
-> REVIEW_REQUIRED / exit 20
```

## COMPLETED_DAY_EVIDENCE_USABLE

`YES_WITH_LIMITATIONS`

The clean completed days through `2022-09-15` remain usable for descriptive
evidence and runtime behavior analysis. They must not be treated as a completed
500BD or completed long-horizon performance result. Phase31 long-horizon
performance characterization remains paused until the Pending lifecycle
integrity gap is repaired or otherwise resolved.

## REPAIR_REQUIRED

`YES`

Do not implement in Phase31-A1.

Narrow repair design direction:

Create a focused Pending lifecycle repair for next-session terminalization of
mixed `BUY_ITEM_SCOPED_REVIEW` / SELL-continuation Pending plans where:

- canonical Pending Review Scope Authority is structurally valid;
- reviewed BUY items remain unsubmitted and unfilled;
- reviewed SELL items are absent;
- executable SELL items were submitted and reached terminal execution/ledger
  evidence;
- no unknown broker-write or post-send uncertainty remains after execution
  evidence is reconciled;
- residual reviewed BUY items expire fail-closed for BUY execution;
- the Pending slot becomes terminal/empty without auto-approving reviewed BUY;
- valid SELL independence remains preserved.

The repair should also ensure the direct REVIEW_REQUIRED path is normalized into
the Phase30-AK9R29 typed guard taxonomy when it remains fail-closed.

The repair must preserve:

- Production / Demo / Historical common contract;
- fail-closed Safety;
- canonical Pending Review Scope Authority;
- canonical Historical Safety Temporal Authority;
- BUY / SELL independence;
- Runtime guard taxonomy;
- quantity authority lineage;
- cash semantic separation;
- no future leakage.

## NEXT_TASK_RECOMMENDATION

`focused repair task`

Recommended next task:

```text
Phase31-A2 - Mixed BUY_ITEM_SCOPED_REVIEW / SELL Continuation Pending Lifecycle Terminalization Repair
```

Scope should be focused implementation plus short regression only. Do not run a
fresh long Historical run in Codex.

## READ-ONLY AUDIT NOTES

This audit read existing documentation, source, tests, and target-run artifacts.
It did not run a fresh-run, replay, resume, long Historical run, Strategy
implementation, Runtime repair, threshold change, schema change, fixture change,
or test modification.
