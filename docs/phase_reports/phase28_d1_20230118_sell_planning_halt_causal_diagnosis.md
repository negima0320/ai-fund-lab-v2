# Phase28-D1: 2023-01-18 Sell Planning HALT Causal Diagnosis

Task ID: `Phase28-D1`

Task Type: `READ_ONLY_DIAGNOSIS`

Status: `COMPLETE`

Primary Judgment: `PHASE28_D1_SELL_PLANNING_HALT_ROOT_CAUSE_CONFIRMED_PHASE28_C_UNRELATED`

Resume Decision: `FRESH_RUN_REQUIRED_AFTER_REPAIR`

Phase28-D Status: `RESTART_REQUIRED`

Implementation Changed: `false`

Resume Executed: `false`

Long Historical Executed: `false`

## Target Run

- run_id: `runtime-test-historical-smoke-20260805T124145808243Z`
- profile: `historical-smoke`
- planned window: `2023-01-04` through `2023-05-31`
- planned business days: `100`
- completed business days: `2023-01-04` through `2023-01-17`, 9 business days
- halt date: `2023-01-18`
- halt stage: `sell_planning`
- run_state status: `HALT`
- fresh-run result: `HALT`

## Direct Halt Cause

The direct halt cause is:

```text
sell planning pipeline review required: REVIEW_REQUIRED_REDUCE_PENDING_SELL_CONFLICT:76470
```

The direct authority producer is:

```text
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
```

The direct runtime consumer is:

```text
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
```

The direct failing condition is a same-symbol active pending SELL conflict for `76470` while Sell Planning attempted to process PM `REDUCE` intent for the same symbol.

Evidence:

- `daily/2023-01-18/sell_planning/cli_result.json`: exit code `20`
- `daily/2023-01-18/sell_planning/sell_planning_manifest.json`: final state `REVIEW_REQUIRED`
- `daily/2023-01-18/sell_planning/pending_continuity_evidence.json`: reason `REVIEW_REQUIRED_REDUCE_PENDING_SELL_CONFLICT:76470`
- `daily/2023-01-18/position_management/pm_decisions.json`: PM `REDUCE` for `76470`
- `daily/2023-01-18/morning/pending_generation_evidence.json`: morning already wrote pending plan `pending-strategy-plan-historical-2023-01-18-d265046edf12fe7d`

Code evidence:

- `sell_pipeline.py` generates `REVIEW_REQUIRED_REDUCE_PENDING_SELL_CONFLICT:<symbols>` when `_pending_sell_conflict(...)` detects an active same-symbol pending SELL.
- `run_daily_operation.py` maps `sell_result.status == "REVIEW_REQUIRED"` to exit code `20` and final state `REVIEW_REQUIRED`.
- `docs/02_architecture/position_management_reduce_quantity_contract.md` explicitly lists same-symbol active pending SELL conflict as a fail-closed `REVIEW_REQUIRED` condition.

## Affected Symbol and Side

- affected symbol: `76470`
- affected side: `SELL`
- PM decision: `REDUCE`
- PM reason code: `peak_drawdown_warning`
- PM quantity authority: delegated to Sell Planning
- existing quantity: `4100`
- current price: `26.0`
- market value: `106600.0`

## Causal Chain

1. Data Readiness for `2023-01-18` was `READY`.
2. Historical neutral safety authority was propagated and final safety was `PASS`.
3. Morning strategy planning produced a pending plan for `2023-01-18`.
4. That plan included SELL items for `76470`, `83060`, and `94320`, plus BUY_NEW `93180`.
5. PM then produced authoritative SELL-side decisions: ADD `83060`, HOLD `94320`, REDUCE `76470`.
6. Sell Planning selected the REDUCE decision for `76470`.
7. Sell Planning detected an already-active same-symbol pending SELL for `76470`.
8. Sell Planning fail-closed with `REVIEW_REQUIRED_REDUCE_PENDING_SELL_CONFLICT:76470`.
9. Runtime CLI stopped because `--stop-on-review-required` was active.

## First Abnormal State

There are two distinct abnormal layers:

- Earliest upstream review state: Strategy artifacts on `2023-01-18` are `DRAFT`, `human_review_status=REQUIRED`, with `SOURCE_LIFECYCLE_DRAFT` and `SOURCE_RUNTIME_CONSUMER_NOT_ELIGIBLE` on Portfolio Construction and Position Sizing.
- First causally stopping state: Sell Planning pending pipeline status `REVIEW_REQUIRED` with reason `REVIEW_REQUIRED_REDUCE_PENDING_SELL_CONFLICT:76470`.

The upstream strategy review state did not itself halt the run. The halt was produced by the Sell Planning pending conflict.

## BUY / SELL Independence Audit

No evidence shows that BUY-side `REVIEW_REQUIRED` directly halted Sell Planning.

Relevant evidence:

- `runtime_state_safety_state`: `BUY_REVIEW_REQUIRED`
- final safety: `PASS`
- `safety_block_buy`: `false`
- `safety_block_sell`: `false`
- Sell Planning pipeline `preserved_existing_buy_pending`: `false`
- Sell Planning pipeline `pending_composition_model`: `EMPTY_NO_EXISTING_BUY_PENDING`
- direct reason code: `REVIEW_REQUIRED_REDUCE_PENDING_SELL_CONFLICT:76470`

However, the run does show a broader pending orchestration defect: morning strategy wrote mixed BUY and SELL pending items, then Sell Planning later treated the same-day SELL item for `76470` as an active conflict. This is a same-side SELL conflict, not a BUY-review-to-SELL propagation.

## Phase28-C Causality

Phase28-C is not directly causal.

On `2023-01-18`:

- PM ADD existed for `83060`.
- Portfolio Construction did not convert `83060` into an ADD target-weight increase.
- `83060` target_weight was `0.0`, with `membership_intent=UNRESOLVED`.
- Position Sizing emitted negative quantity_delta_candidate for `83060`, not positive ADD quantity.
- Runtime Planning emitted `SELL_EXIT` for `83060`, not `BUY_ADD`.
- No ADD submit or fill occurred.
- The direct halt symbol was `76470`, not `83060`.

Indirect Phase28-C trigger is also not confirmed. The direct conflict arose from existing Runtime/Sell Planning pending orchestration: a same-day pending SELL was already active when Sell Planning processed `76470` REDUCE. That orchestration is outside Phase28-C's changed files.

Final causality classification:

```text
UNRELATED_EXISTING_RUNTIME_DEFECT
```

## Safety and Data Readiness

Data Readiness was not the direct defect:

- `overall_status`: `READY`
- `review_required`: `false`
- `halt_required`: `false`
- `review_reasons`: `[]`
- `halt_reasons`: `[]`

Safety was not the direct defect:

- final safety status: `PASS`
- safety decision: `NEUTRAL`
- safety block buy: `false`
- safety block sell: `false`
- safety halt runtime: `false`

The manifest contains an earlier `safety_operation_guard` checkpoint with `SAFETY_MISSING`, but historical neutral safety authority later superseded it for this historical replay path. The direct halt reason remained Sell Planning pending conflict.

## Pending, Submit, Ledger, and Position State

2023-01-18 has no `submit/`, `execution/`, or `runtime_state_refresh/` directory in the run evidence. The run stopped at `sell_planning`.

Current runtime pending state after the halt is an empty sell no-signal plan:

```text
pending_plan_id = pending-order-plan-sell-no-signal-2023-01-18
state = PENDING_APPROVAL
items = []
```

This means the halted attempt partially mutated pending state by replacing the earlier morning mixed pending plan with an empty no-signal plan. No evidence shows 2023-01-18 submit, fills, ledger append, or position mutation after the halt.

## Resume Safety

Do not resume this run as-is.

Although `run_state.status=HALT` and `next_job=2023-01-18:sell_planning`, the pending state has already been changed by the halted Sell Planning attempt. A resume could proceed from a state that no longer contains the original morning pending conflict, which would mask the defect and break comparability.

Resume Decision:

```text
FRESH_RUN_REQUIRED_AFTER_REPAIR
```

## Required Repair Scope

Minimum repair scope is Runtime/Sell Planning pending orchestration, not Portfolio Construction or Position Sizing.

Repair should address the same-day interaction between:

- morning strategy pending generation
- mixed BUY/SELL pending payloads
- Sell Planning REDUCE/EXIT generation
- same-symbol active pending SELL conflict detection
- BUY/SELL independence and pending composition

Do not treat this as a Phase28-C ADD bridge repair.

## 100BD Comparability Impact

The current halted run is not reusable for Phase28-D comparison because:

- only 9 business days completed
- 2023-01-18 stopped before submit/execution/runtime_state_refresh
- pending state was partially overwritten during the halt
- the run contains a Runtime defect outside the Phase28-C performance change

After repair, Phase28-D should restart with a fresh 100BD After run. The repair must be documented separately from the Phase28-C performance change so the ADD bridge experiment remains interpretable.

## Open Gaps

No additional artifacts are required to identify the direct root cause.

Open non-blocking analysis gaps:

- exact pre-halt pending JSON is only available through manifest-embedded payload evidence, because `.runtime/pending_order_plan/pending_order_plan.json` now reflects the post-halt empty plan
- final summary is absent because the run halted before close
- performance report is absent because the run halted before 100BD completion

## Next Task

Recommended next Phase-prefixed task:

```text
Phase28-D2: Runtime Sell Planning Pending Conflict Repair Design
```
