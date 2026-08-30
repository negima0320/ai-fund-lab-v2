# Phase32-Z - 2023-10-11 Submit HALT Root-Cause Audit

## Scope

Target run:

- `runtime-test-historical-extended-smoke-20260830T081425790243Z`

Audit mode:

- READ-ONLY root-cause audit.
- No code, config, Runtime state, Pending, Ledger, Current, Registry, Accepted Generation, replay, resume, fresh-run, or long Historical execution was performed.
- This report creation is the only file change.

Phase32-Y boundary:

- The completed measurement window through `2023-10-10` remains trusted unless this audit finds concrete contamination evidence.

## Run Identity And Halt Surface

Evidence:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T081425790243Z/fresh_run_summary.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T081425790243Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T081425790243Z/daily/2023-10-11/submit/cli_result.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T081425790243Z/daily/2023-10-11/submit/runtime_manifest.json`

Observed:

- Completed business days: `252`, through `2023-10-10`.
- Halted business date/job: `2023-10-11:submit`.
- Submit CLI exit code: `20`.
- Runtime-test final status: `HALT`, exit code `30`.
- Submit manifest stage `runtime_v2_submit_pipeline`: `REVIEW_REQUIRED`.
- Submit result summary: `submitted_count=1`, `accepted_count=1`, `blocked_count=1`, `unknown_count=0`, `rejected_count=0`.
- Halt summary root reason: `corporate_action_event_not_resolved`.

## First Canonical Failure

The first canonical failing item is the approved SELL for `50280`:

- Symbol: `50280`
- Action: `SELL`
- Quantity: `100`
- Pending/order item id: `strategy-b6716e1e95fc9cc0a9aa`
- Source decision id: `rp-2023-10-11-50280-sell_exit-9fcec5d3200f82ea`
- Source decision type: `SELL_EXIT`
- Pending state before submit: `APPROVED`
- Pending feasibility status: `PASS`
- Pending batch submit status: `PASS_ITEM_SUBMITTABLE`
- Submit preflight status: `BLOCKED`
- Submit status: `NOT_SUBMITTED`
- Submit rejection: `corporate_action_event_not_resolved`
- Violated policy: `corporate_action_adjustment_authority`
- Violated policy source: `.runtime/runtime_state/corporate_action_adjustments/2023-10-11/50280.json`

The direct authority artifact for `50280` says:

- `schema_version`: `runtime_v2_corporate_action_adjustment_authority_v1`
- `status`: `REVIEW_REQUIRED`
- `reason`: `corporate_action_event_type_or_adjustment_application_unresolved`
- `event_status`: `IMPACT_DETECTED`
- `event_type`: `UNKNOWN_ADJFACTOR_IMPACT`
- `adjustment_factor`: `0.3333333333333333`
- `source`: `jquants_raw_equities_bars_daily_adjfactor`
- `source_artifact_path`: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T081425790243Z/daily/2023-10-11/market_refresh/inputs/historical_asof/2023-10-11/raw/jquants/equities_bars_daily/data.parquet`
- `future_data_used`: `false`
- `pit_validation_status`: `PASS`
- `quantity_reconciliation_status`: `REVIEW_REQUIRED`
- `price_reconciliation_status`: `REVIEW_REQUIRED`
- `already_applied_status`: `UNKNOWN`
- `reason_codes`: `corporate_action_type_unresolved`, `corporate_action_already_applied_unknown`

This is not inferred from exit code alone. The submit item result and the corporate-action adjustment authority identify the exact blocked item and reason.

## Failure Path

Trace:

1. Strategy / PM
   - PM has `50280` as a sell-side deterioration decision:
   - `pm_decision_id=pm-2023-10-11-50280-reduce`
   - `position_campaign_id=pc-2c6fee062ad408d3-50280-0001`
   - `quantity_before=100`
   - PM reason includes `risk_increased_but_trend_not_broken`.

2. PC / PS / Runtime Planning
   - Runtime Planning materializes `SELL_EXIT` for `50280`.
   - `source_decision_id=rp-2023-10-11-50280-sell_exit-9fcec5d3200f82ea`
   - Quantity is executable at `100`.

3. Pending
   - Pending plan id: `pending-strategy-plan-historical-2023-10-11-f650d7dcd8b7c7d7`.
   - Plan state: `REVIEW_REQUIRED`, but scoped to BUY items.
   - Plan status: `APPROVED_WITH_BUY_ITEM_SCOPED_REVIEW`.
   - `sell_items_status=PASS`.
   - `buy_items_status=REVIEW_REQUIRED`.
   - `sell_continuation_allowed=true`.
   - Approved SELL item ids:
     - `strategy-b6716e1e95fc9cc0a9aa` (`50280`)
     - `strategy-24ef30251cec051aac6a` (`92460`)
   - Reviewed BUY item ids:
     - `strategy-4c1cff246933bff23312` (`38560`, cash capacity)
     - `strategy-a92ce60a05bb6b2c9cc4` (`76920`, corporate action unresolved)

4. Submit no-order / partial authority
   - `authority_type=BUY_ITEM_SCOPED_REVIEW_PARTIAL_PASS_SUBMISSION`
   - `status=PASS`
   - `reason=pass_buy_items_submit_review_buy_items_deferred`
   - `item_review_does_not_escalate_to_batch_failure=true`
   - `partial_pass_buy_submission_allowed=true`
   - `reviewed_buy_submitted=false`
   - `submitted_candidate_count=2`
   - This authority expects the two approved SELL items to be candidates for submission while reviewed BUYs are not submitted.

5. Submit item guard
   - `92460` SELL passed and was accepted.
   - `50280` SELL was blocked by item-level corporate-action adjustment authority before broker/adaptor submission.
   - `38560` and `76920` BUY rows remained not-submitted `REVIEW_REQUIRED` items, which is consistent with BUY item-scoped review.

6. Runtime-test halt
   - Submit pipeline returned `REVIEW_REQUIRED` because an item was blocked after one item had already been accepted.
   - Runtime-test runner stopped the run at `2023-10-11:submit` with CLI exit code `20`, mapped to run-level `HALT` / exit code `30`.

Relevant source path:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
  - Lines 388-395 build item-scoped BUY review evidence and separate reviewed BUY item results.
  - Lines 427-529 iterate approved items and run item-level submit guard.
  - Lines 2622-2645 fail closed for unresolved historical corporate-action quarantine/adjustment evidence.
  - Lines 799-826 return `REVIEW_REQUIRED` when any submitted batch also has blocked/rejected/unknown items.

## First Violated Boundary

First violated boundary:

`Strategy/Pending approved SELL authority -> Submit item-level corporate-action adjustment authority`

The narrow violation is that `50280` was approved into Pending as a submittable SELL under same-day planning evidence, while Submit later found a same-PIT J-Quants raw OHLCV `AdjFactor=0.3333333333333333` and could not prove event type, quantity adjustment, price adjustment, or already-applied state.

This is not a Strategy performance problem. It is an authority-readiness and lifecycle-boundary problem: the corporate-action adjustment authority that can block a SELL at Submit was not resolved before the SELL became an approved Pending candidate.

## Previous-Day State Audit

Canonical EOD / current state through `2023-10-10`:

- Cash: `816580`
- Buying power: `816580`
- Market value: `837970`
- Total equity: `1654550`
- Positions:
  - `66780`: `100`
  - `59660`: `100`
  - `50280`: `100`
  - `92460`: `100`
- `50280` on `2023-10-10`:
  - quantity `100`
  - current price `463.7`
  - market value `46370`
  - valuation price authority `PASS`
  - quantity basis `ADJUSTED`
  - corporate action ambiguity status `CLEAR`

No evidence was found that completed `2023-10-10` or prior completed days are contaminated. The new unresolved factor appears at `2023-10-11` submit authority. The halt affects `2023-10-11` onward.

Target-date partial submit state:

- One order was accepted and written for `92460`:
  - record id `ledger-order-submit-eb4911bfbcb7f197`
  - pending item id `strategy-24ef30251cec051aac6a`
  - side `SELL`
  - quantity `100`
  - status `ACCEPTED`
- `.runtime/pending_order_plan/pending_order_plan.json` marks `92460` as `CONSUMED`.
- `50280` remains `APPROVED`.
- BUY items remain `REVIEW_REQUIRED`.

This means any same-run resume after repair must be idempotency-safe and must not resubmit the already accepted `92460` order.

## Root Cause Classification

Primary class:

- Planning/Pending/Submit authority mismatch.

Concrete root cause:

- Submit correctly fail-closed on `50280` because same-day PIT J-Quants raw OHLCV showed `AdjFactor=0.3333333333333333`, but the event type and adjustment-application state were unresolved.
- The mismatch is that upstream Strategy corporate-event evidence for the same symbols reported `KNOWN_NO_EVENT`, while Submit's corporate-action adjustment authority detected an adjustment-factor impact and blocked an already-approved SELL.
- Therefore the first invalid boundary is not cash, quantity, stale pending, duplicate idempotency, accepted artifact/hash, or strategy selection. It is unresolved corporate-action adjustment authority discovered too late in the lifecycle.

Expected fail-closed or defect:

- The Submit guard fail-closed decision itself is expected and should not be bypassed.
- The defect is lifecycle authority inconsistency: a SELL item can be approved into Pending without the same corporate-action adjustment authority that Submit will require for execution-time quantity/price correctness.

## Checked Root-Cause Classes

- Provenance/campaign identity: not root cause. `source_decision_id`, `pending_item_id`, and `order_plan_item_id` are present for the failing item. PM campaign identity exists upstream; empty `position_campaign_id` on SELL pending rows is a residual evidence gap but not the submit rejection, because `92460` has the same pending gap and passed.
- Planning/Pending/Submit authority mismatch: reproduced and root cause.
- Duplicate/idempotency conflict: not root cause. Existing submitted reconciliation exists for future resume safety, but the first block is `50280` corporate-action authority.
- Stale pending/order state: not root cause. Pending is target-date `2023-10-11` and same pending plan id is used through submit.
- Cash/reserved-cash inconsistency: not root cause for the HALT. `38560` BUY has a cash-capacity review, but it is correctly BUY item-scoped and not submitted.
- Position/reserved-share inconsistency: not root cause. `50280` broker/current available quantity is `100`, matching SELL quantity `100`.
- Lot/quantity inconsistency: not root cause. SELL quantity is executable at `100`.
- Accepted artifact/hash mismatch: no evidence.
- Safety/broker expected fail-closed: no broad Safety block. Historical safety authority is `PASS`/neutral; final safety status is `READY`.
- Other: corporate-action adjustment authority unresolved for `50280`.

## Regression Checks

- Phase32-C provenance: no concrete regression in the failure path.
- Phase32-L campaign identity: no concrete campaign split caused the submit HALT. Residual pending SELL `position_campaign_id` emptiness should remain observable, but it is not the rejection boundary.
- Phase32-P/Q REENTRY provenance: not involved; no REENTRY path in the failing item.
- Phase32-S ADD acceleration: not involved; no BUY_ADD/ADD order is in the failing submit path.
- Phase32-X Winner Retention: not directly involved. PM/sell-side decisions reached Runtime Planning, but the HALT is Submit corporate-action authority.
- G129 BUY_ADD: not involved; no BUY_ADD item.
- KI-004 Safety separation: no concrete regression. Safety/broker/corporate-action remain separated; the block is corporate-action authority, not Safety.
- KI-006 Buy Quality zero preservation: no concrete regression; no zero ADD resurrection observed.

## Measurement Boundary

The submit HALT affects only `2023-10-11` onward.

It does not provide concrete evidence that any completed day through `2023-10-10` is contaminated. Phase32-Y's completed-window measurement trust remains intact.

## Repair Gate

Repair required: YES.

Narrowest repair scope:

- Align Planning/Pending and Submit corporate-action adjustment authority for symbols that may submit orders, especially SELL orders with current position quantity.
- Before a SELL becomes an approved Pending item, the same PIT corporate-action adjustment authority required by Submit must be resolved or the item must be marked `REVIEW_REQUIRED` with a corporate-action reason.
- Do not bypass Submit fail-closed behavior.
- Do not treat `AdjFactor != 1` as safe without proving event type, quantity/price basis, and already-applied status.
- Do not change Strategy parameters, thresholds, weights, cash policy, candidate selection, ADD acceleration, or Winner Retention semantics.

Required focused tests:

- SELL item with same-day raw OHLCV `AdjFactor != 1` and unresolved adjustment application must not become approved Pending; it must fail closed or become explicit `REVIEW_REQUIRED` before Submit.
- Pending plan with BUY item-scoped reviews and approved SELL items remains partial-submittable when approved SELL corporate-action authority is `PASS`.
- Submit still fail-closes on a genuine unresolved corporate-action adjustment mismatch.
- Same-run resume/idempotency test: already accepted `92460` pending item is reconciled and not resubmitted; unresolved/repaired `50280` state is handled canonically.
- Regression tests for Phase32-C/L/P provenance and campaign identity, Phase32-S ADD acceleration, Phase32-X Winner Retention, G129 BUY_ADD, KI-004 separation, KI-006 zero preservation.

Strategy semantic change required: NO.

## Resume Readiness

- Repair required: YES.
- Same-run resume safe after repair: YES, conditional on focused idempotency validation for the already accepted `92460` order and canonical handling of the remaining `50280`/BUY reviewed items.
- Fresh-run required: NO, not from this evidence alone.
- Completed 252BD remain valid: YES.
- User should not resume before the narrow repair and idempotency validation are complete.

## Final Judgment

1. `WHAT_FAILED`
   - `2023-10-11:submit` blocked approved SELL `50280` because corporate-action adjustment authority was `REVIEW_REQUIRED` / `corporate_action_event_not_resolved`.

2. `FIRST_VIOLATED_BOUNDARY`
   - `Strategy/Pending approved SELL authority -> Submit item-level corporate-action adjustment authority`.

3. `EXPECTED_FAIL_CLOSED_OR_DEFECT`
   - Submit fail-closed is expected; the lifecycle authority mismatch that allowed the SELL to reach approved Pending without resolved submit-required corporate-action authority is a defect.

4. `ROOT_CAUSE`
   - Same-day PIT J-Quants raw OHLCV for `50280` had `AdjFactor=0.3333333333333333`; Runtime could not prove event type, quantity/price reconciliation, or already-applied adjustment status. Planning/Pending did not align with that corporate-action adjustment authority before approving the SELL.

5. `PHASE32_S_OR_X_INVOLVED`
   - NO. Phase32-S ADD acceleration and Phase32-X Winner Retention are not the concrete failing boundary.

6. `COMPLETED_252BD_STILL_VALID`
   - YES.

7. `REPAIR_REQUIRED`
   - YES.

8. `SAME_RUN_RESUME_SAFE_AFTER_REPAIR`
   - YES, conditional on focused idempotency validation because `92460` was already accepted and written as a submit ledger order.

9. `FRESH_RUN_REQUIRED`
   - NO, not required by the evidence in this audit.

10. `NEXT_ACTION`
    - Implement the narrow corporate-action authority alignment repair and focused idempotency/regression tests. Do not resume the run until that repair is accepted.

Final Judgment:

`PHASE32_Z_20231011_SUBMIT_HALT_ROOT_CAUSE_IDENTIFIED`
