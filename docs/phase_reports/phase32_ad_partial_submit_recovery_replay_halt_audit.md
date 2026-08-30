# Phase32-AD Partial Submit Recovery Replay HALT Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Target date: `2023-10-11`
- Audit mode: READ-ONLY, except this report creation
- Mutating operations not executed by Codex: recover, replay, resume, fresh-run, rollback, source/config/runtime-state edit

## Executive Summary

The scoped replay did not fail at Submit or Execution. It stopped at:

`2023-10-11:sell_planning`

Evidence:

- `run_state.next_job = 2023-10-11:sell_planning`
- `halted_at.job = sell_planning`
- `halted_at.exit_code = 20`
- replay `sell_planning/runtime_manifest.json`:
  - `final_state = REVIEW_REQUIRED`
  - `exit_code = 20`
  - `reason = historical_safety_temporal_authority_missing`
  - `final_safety_status = REVIEW_REQUIRED`
  - `component_reasons.safety = ["historical_safety_temporal_authority_missing"]`
  - `component_reasons.pending = ["pending_review_required"]`

First violated boundary:

`partial-submit recovery replay orchestration -> sell_planning entry/readiness guard`

The replay orchestration rewound to `morning`, regenerated a new Pending plan, then attempted `sell_planning`. The regenerated Pending is expectedly `REVIEW_REQUIRED` after Phase32-AA, but the replay path treats that state plus missing `.runtime/runtime_state/safety/latest_safety_decision.json` as batch-fatal at sell_planning. It never reaches replay Submit or Execution.

## Recovery Result

Phase32-AC recovery was actually applied:

- recovery id: `scoped-partial-submit-7fc8aca4bb8fef42`
- recovery classification: `PARTIAL_SUBMIT_SUCCESS_LATER_ITEM_BLOCK`
- `run_state_rewind_from = 2023-10-11:submit`
- `run_state_rewind_to = 2023-10-11:morning`
- preserved accepted item id:
  - `strategy-24ef30251cec051aac6a`
- preserved order id:
  - `b95f550a15c75dbb6de73a3ef5886b9c79d990825cc42ddddd756a4d356c8733`
- preserved broker evidence:
  - `.runtime/runtime_state/historical_broker/2023-10-11/d2fb9ea564f214cfe8737a1811a41780ad26c66a5083b3b296d9adb78cbe58bf.json`
- target-date recovery ledger counts:
  - orders: `1`
  - executions: `0`
  - positions: `0`
  - cash: `0`
  - events: `0`

92460 accepted evidence remained preserved after replay:

- current target-date order rows: `1`
- current target-date execution/position/cash/event rows: `0`
- current historical broker accepted evidence rows for `2023-10-11`: `1`
- preserved order id count: `1`
- duplicate order id count: `0`
- duplicate broker evidence count: `0`

## Replay Job Trace

| Job | Executed | Exit code | Final state | Evidence |
|---|---:|---:|---|---|
| `morning` | YES | `0` | `CURRENT_STATE_LOADED` | `daily/2023-10-11/morning/runtime_manifest.json` |
| `sell_planning` | YES | `20` | `REVIEW_REQUIRED` | `daily/2023-10-11/sell_planning/runtime_manifest.json` |
| `submit` | NO in scoped replay | N/A | N/A | existing artifact is pre-recovery `18:27` submit evidence |
| `execution` | NO | N/A | N/A | no `daily/2023-10-11/execution` directory |

The `daily/2023-10-11/submit/*` artifacts are from the original pre-recovery submit attempt (`2026-08-30T18:27...`), not the scoped replay. The scoped replay stopped earlier at sell_planning (`2026-08-30T21:36...`).

## 92460 Idempotency

92460 was not duplicated.

Current Ledger order row:

- `business_date = 2023-10-11`
- `pending_plan_id = pending-strategy-plan-historical-2023-10-11-f650d7dcd8b7c7d7`
- `pending_item_id = strategy-24ef30251cec051aac6a`
- `symbol = 92460`
- `side = SELL`
- `quantity = 100`
- `status = ACCEPTED`
- `order_id = b95f550a15c75dbb6de73a3ef5886b9c79d990825cc42ddddd756a4d356c8733`

Current broker evidence:

- `status = ACCEPTED`
- `pending_plan_id = pending-strategy-plan-historical-2023-10-11-f650d7dcd8b7c7d7`
- `pending_item_id = strategy-24ef30251cec051aac6a`
- `symbol = 92460`
- `side = SELL`
- `quantity = 100`
- `order_identity = b95f550a15c75dbb6de73a3ef5886b9c79d990825cc42ddddd756a4d356c8733`

However, replay did not actually prove Submit reconciliation on 92460, because replay never reached Submit. Also, regenerated Pending now contains a new 92460 pending item id:

- old accepted id: `strategy-24ef30251cec051aac6a`
- regenerated id: `strategy-d1be135b15c4cc97433a`

Therefore the AC replay assumption that replayed Pending would naturally regenerate the same id for accepted-item reconciliation did not hold on actual evidence. No duplicate occurred only because Submit was not reached.

## 50280 Phase32-AA Behavior

50280 behaved as Phase32-AA intended before Submit:

- regenerated pending item id: `strategy-3da5436ff9481d6af209`
- symbol: `50280`
- side: `SELL`
- quantity: `100`
- state: `REVIEW_REQUIRED`
- approved: `false`
- batch submit status: `ITEM_REVIEW_REQUIRED`
- feasibility status: `REVIEW_REQUIRED`
- item review reason: `corporate_action_event_not_resolved`
- source PM decision id: `pm-2023-10-11-50280-reduce`
- corporate-action status: `REVIEW_REQUIRED`
- adjustment factor: `0.3333333333333333`
- event status: `IMPACT_DETECTED`

This means Phase32-AA did work on the actual replay: 50280 did not remain `APPROVED` / `PASS_ITEM_SUBMITTABLE`; it was downgraded to `REVIEW_REQUIRED` before Submit.

The problem is that expected Pending review at this replay point became a sell_planning batch stop rather than allowing canonical handling of the already accepted 92460 order and unresolved 50280 review state.

## BUY Reviewed Items

Regenerated BUY items:

| Symbol | Pending item id | State | Reason |
|---|---|---|---|
| `38560` | `strategy-4e98c1cb77def51708c5` | `REVIEW_REQUIRED` | reserved notional exceeds dynamic cash capacity |
| `76920` | `strategy-c5d39910c741daebcd6d` | `REVIEW_REQUIRED` | corporate_action_event_not_resolved |

They remained BUY review items and were not submitted. They are not the first failing boundary. The replay stopped at sell_planning due the combined readiness guard:

- `historical_safety_temporal_authority_missing`
- `pending_review_required`

## Safety / Pending Readiness Findings

After replay morning:

- morning final safety status: `READY`
- morning final safety reason: `historical_neutral_no_event_safety_ready`
- morning safety source: `data_readiness_historical_temporal_authority`

But at replay sell_planning:

- `.runtime/runtime_state/safety/latest_safety_decision.json` does not exist
- sell_planning safety status: `SAFETY_MISSING`
- sell_planning final safety status: `REVIEW_REQUIRED`
- sell_planning reason: `historical_safety_temporal_authority_missing`
- Pending status: `REVIEW_REQUIRED`
- Pending review scope: `AUTHORITY_UNKNOWN_REVIEW`
- sell continuation allowed: `false`

The first canonical failure reported by the run is the safety temporal authority miss. The Pending review is a second batch-blocking reason. Both arise after replay regenerated a new mixed review Pending under current code and then invoked sell_planning in a context that lacked a durable latest safety artifact.

## Replay Contract Gap

Classification:

`replay-recovered-day orchestration gap`

Contributing gaps:

1. Replay job set begins at `morning` and then runs `sell_planning`, but it does not replay or persist a safety authority artifact that sell_planning accepts as durable.
2. AC recovery preserved old accepted 92460 evidence but did not provide a replay bridge from preserved accepted item identity to regenerated same-symbol SELL identity when morning generated a new `pending_plan_id` and new `pending_item_id`.
3. The replay path treats expected regenerated Pending `REVIEW_REQUIRED` as a fatal sell_planning batch condition, even though for this recovery shape the desired next step is preserving/consuming an already accepted order and leaving newly unresolved items in review.

This is not an AA regression. It is not a Submit idempotency duplicate. It is not a Strategy performance issue. It is a recovery/replay orchestration contract gap exposed by the actual post-AC replay.

## Current Run Safety

- Current run recoverable: YES, but not with the existing operator commands without additional tooling/orchestration repair.
- Current Pending safe: YES for non-submission; it has no approved items, and target-date execution/current rows remain absent.
- 92460 idempotency safe: currently YES, because there is still only one accepted order and one broker evidence row. It is not yet execution-completed.
- Another recovery required: YES, a scoped recovery/replay repair is required before continuing this same run.
- Fresh-run required: NO, not from current evidence.
- Completed 252BD through `2023-10-10` valid: YES. No evidence contaminates completed measurement through `2023-10-10`.

## Narrow Repair Direction

Do not change Strategy semantics.

Narrowest repair scope:

- Extend partial-submit recovery replay orchestration so it can resume from the applied AC recovery evidence after a replay sell_planning halt.
- Ensure replay has a durable Historical neutral safety authority acceptable to sell_planning, or include the correct pre-sell-planning readiness stage in the scoped replay contract.
- Preserve old accepted order identity and prevent Submit replay from relying on regenerated pending item id equality alone. The bridge must be explicit and evidence-backed: old accepted order row plus broker evidence plus source decision/provenance, not symbol-only inference.
- Define how already accepted same-day order rows are consumed by Execution exactly once when Submit is skipped, reconciled, or no-op due regenerated Pending review.
- Keep Phase32-AA behavior: 50280 must remain `REVIEW_REQUIRED` before Submit.

Required focused tests:

- AC recovery applied -> replay morning -> regenerated 50280 review -> sell_planning does not halt solely because the recovery replay has expected review items.
- Historical safety authority survives or is regenerated for scoped replay sell_planning.
- Preserved 92460 order is not duplicated even when regenerated Pending ids differ.
- Execution consumes the preserved accepted order exactly once.
- Re-running the repaired recovery/replay path is idempotent/fail-closed.
- Existing AC, AA, Submit idempotency, G129, KI-004, KI-006, Phase32-S/X focused tests remain PASS.

## Final Judgment Answers

1. `WHICH_REPLAY_JOB_FAILED`: `sell_planning`.
2. `WHAT_EXACTLY_CAUSED_THE_HALT`: sell_planning returned `REVIEW_REQUIRED` / exit code `20` because `historical_safety_temporal_authority_missing` was batch-blocking, with secondary `pending_review_required`.
3. `WAS_92460_DUPLICATED`: NO.
4. `DID_50280_BECOME_REVIEW_REQUIRED_BEFORE_SUBMIT`: YES.
5. `DID_PHASE32_AA_WORK_ON_ACTUAL_REPLAY`: YES.
6. `DID_PHASE32_AC_RECOVERY_STATE_WORK_AS_DESIGNED`: PARTIAL. It preserved accepted evidence and rewound the run, but actual replay regenerated new pending ids and stopped before Submit/Execution.
7. `IS_REPLAY_TOOLING_OR_ORCHESTRATION_REPAIR_REQUIRED`: YES.
8. `IS_ANOTHER_RECOVERY_REQUIRED`: YES, after a narrow tooling/orchestration repair; do not use existing commands blindly.
9. `IS_FRESH_RUN_REQUIRED`: NO.
10. `ARE_COMPLETED_252BD_STILL_VALID`: YES.
11. `WHAT_IS_THE_NEXT_SAFE_OPERATOR_ACTION`: Do not resume or replay again yet. Perform a narrow Phase32-AE repair for partial-submit replay orchestration, then dry-run the repaired recovery/replay path before any confirmed continuation.

## Final Judgment

`PHASE32_AD_PARTIAL_SUBMIT_RECOVERY_REPLAY_GAP_IDENTIFIED`
