# Phase31-F1V - 2022-12-08 Submit HALT Actual-Artifact Root-Cause Audit

## PRIMARY_JUDGMENT

PHASE31_F1V_SUBMIT_HALT_CAUSED_BY_ITEM_SCOPED_BUY_REVIEW_WITH_PARTIAL_SUBMIT_SIDE_EFFECTS

## TARGET_RUN_ID

runtime-test-historical-extended-smoke-20260821T050423121340Z

## HALT_DATE

2022-12-08

## HALT_REASON

`submit completed with rejected/unknown/blocked items`

Direct item-scoped reason:

`76920 BUY strategy-dae988dcba6a12b37f97 = corporate_action_event_not_resolved`

## HALT_SYMBOLS

76920

## SUBMIT_FAILURE_BRANCH

BUY_ITEM_SCOPED_REVIEW_PARTIAL_PASS_SUBMISSION returned PASS for executable items, deferred 76920 BUY, submitted a subset of approved items, then final Runtime state remained REVIEW_REQUIRED because blocked_count = 1.

## PENDING_PLAN_ID

pending-order-plan-buy-review-sell-continuation-2022-12-08-9002066a3dd7

## PENDING_ITEM_COUNT

6

## PENDING_BUY_COUNT

2

## PENDING_SELL_COUNT

4

## APPROVAL_PENDING_BINDING_STATUS

PASS

The active pending plan ID matches `buy_review_sell_continuation_approval_artifact.json`, and the approved item set matches the active pending approved items. Hash fields are not materialized on the approval artifact, so this is an ID/item-set binding acceptance rather than a hash-field acceptance.

## PENDING_APPROVAL_ITEM_SET_STATUS

PASS

## SUBMIT_INPUT_ITEM_SET_STATUS

PASS

Submit guard input accepted the five approved/submittable items and excluded the one reviewed BUY item. Actual side-effect materialization is not fully equal to that input set; see Side-Effect Integrity.

## PREEXISTING_SUBMISSION_COUNT

4 in the halted state

The four existing 2022-12-08 submit side effects are:

| symbol | side | quantity | pending_item_id | order_id |
|---|---|---:|---|---|
| 61440 | BUY | 100 | strategy-9242cb1dda97a6433677 | 5b3e3b80c7cbbadb83008b168ee1917f4e83f4daaa347bf7cc30e39c928404bc |
| 82560 | SELL | 300 | strategy-8f700934de4464ffa4d5 | c107970e2a88a599d8f4feb8dfb1e61c30fecb73ca89989e4dfe68f989cd7d80 |
| 37790 | SELL | 100 | strategy-d869e35933dcd6215538 | ae7cd0e9abaafe4096ba75699a8e2a970499b8495a7308ff937d60506c3274db |
| 45910 | SELL | 100 | strategy-72c08989f99bb27f815a | 63ade0bdeb30ae84fd68b42aa93df4f1a6dcf1de3066e5ff2b488f3157358093 |

There is no 2022-12-08 broker/ledger order for approved SELL 34940.

## DUPLICATE_SUBMIT_RISK

YES

The pending plan remains unconsumed and its consume submitted/ledger order ID lists remain empty despite four submit side effects. A naive resume/retry can duplicate the already materialized four orders unless Submit first reconciles existing order side effects idempotently.

## BUY_SELL_SUBMIT_COMPOSITION

COMPOSITE

Pending composition:

- BUY 61440 quantity 100, approved/submittable
- BUY 76920 quantity 200, REVIEW_REQUIRED
- SELL 34940 quantity 100, approved/submittable
- SELL 82560 quantity 300, approved/submittable
- SELL 37790 quantity 100, approved/submittable
- SELL 45910 quantity 100, approved/submittable

## COMPOSITE_SUBMIT_CONTRACT_STATUS

PARTIAL

Submit guard supports the BUY + SELL composite input and item-scoped BUY review semantics, but the halted artifact shows partial side effects with an unconsumed pending plan and one approved/submittable item, 34940 SELL, not materialized as an order.

## BUY_QUANTITY_CONTRACT_STATUS

PASS

Both BUY rows had resolved quantities in Strategy Runtime Planning:

| symbol | quantity | status |
|---|---:|---|
| 61440 | 100 | RESOLVED_EXECUTABLE / submitted |
| 76920 | 200 | RESOLVED_EXECUTABLE / item-scoped REVIEW_REQUIRED at Submit feasibility due corporate action |

The 76920 blocker is not a quantity defect.

## SELL_QUANTITY_CONTRACT_STATUS

PASS

All four SELL rows had current positions sufficient for full EXIT:

| symbol | pending quantity | current holding as of 2022-12-07 | guard status |
|---|---:|---:|---|
| 34940 | 100 | 100 | PASS |
| 82560 | 300 | 300 | PASS |
| 37790 | 100 | 100 | PASS |
| 45910 | 100 | 100 | PASS |

## CASH_RESERVATION_STATUS

PASS

Cash authority:

- `.runtime/persistent_ledger/state.json`
- cash = 266,190
- as_of = 2022-12-07

BUY cash:

- 61440 reserved_notional = 179,900
- 76920 reserved_notional = 39,600 but not submitted due item-scoped review

No cash insufficiency caused the HALT.

## SUBMIT_GUARD_STATUS

REVIEW_REQUIRED_AFTER_PARTIAL_PASS

## FIRST_FAILED_SUBMIT_GUARD

`BUY_ITEM_SCOPED_REVIEW_ITEM_NOT_SUBMITTED` for 76920 / `corporate_action_event_not_resolved`

The guard evidence says reviewed BUY items must not submit, approved/review sets are disjoint, batch_blocked = false, partial_submit_allowed = true, and sell_continuation_allowed = true.

## NO_ORDER_PATH_INVOLVED

NO

## NO_ORDER_AUTHORIZATION_STATUS

NOT_APPLICABLE

This was not an empty/no-order pending path. The manifest field name `no_order_authority_evidence` carries the item-scoped partial-submit authority, but the active pending was non-empty and composite.

## DUPLICATE_SIDE_EFFECT_COUNT

0

No duplicate order IDs or duplicate broker artifacts were observed for 2022-12-08. The issue is partial side effects without pending consumption/idempotency state, not duplicated side effects yet.

## HALTED_RUN_STATE_INTEGRITY

PARTIAL

PASS aspects:

- Target run halted at 2022-12-08:submit with exit code 20.
- Completed business days are through 2022-12-07.
- Active pending is same-date 2022-12-08 and structurally valid.
- 76920 remained unsubmitted as required by item-scoped review.
- No execution job after submit exists in the target run evidence.

PARTIAL / unsafe aspects:

- Four submit side effects exist in `.runtime/runtime_state/historical_broker/2022-12-08`.
- Four matching accepted order rows exist in `.runtime/persistent_ledger/orders.jsonl`.
- Active pending remains `consumed = false`.
- Active pending `consume.submitted_order_ids` and `consume.ledger_order_record_ids` remain empty.
- Approved/submittable SELL 34940 is marked submitted in submit guard/no-order authority evidence but has no corresponding historical broker artifact or accepted ledger order.

## ROOT_CAUSE_CLASSIFICATION

ITEM_SCOPED_BUY_REVIEW_PARTIAL_SUBMIT_TERMINALIZATION_AND_IDEMPOTENCY_GAP

Primary business blocker:

`76920 BUY corporate_action_event_not_resolved`

Integration defect exposed at Submit:

Partial pass submission can create accepted historical broker/order side effects and still return REVIEW_REQUIRED without consuming or recording submitted IDs on the pending plan. The halted state is therefore not resume-safe without an idempotent side-effect reconciliation repair.

## RELATION_TO_F1_REPAIRS

NEWLY_EXPOSED_BY_F1_REPAIRS

The HALT is not directly caused by F1F/F1I/F1L/F1O/F1R/F1T SELL repairs. Those repairs allowed the clean run to pass prior sell_planning edge cases and reach Submit. The 12/08 failure is a downstream Submit partial-submission/idempotency boundary exposed after SELL planning continuity was repaired.

## INTEGRATION_DEFECT_CONFIRMED

YES

The corporate-action review for 76920 is a genuine fail-closed item-scoped safety condition. The integration defect is the combination of:

- accepted side effects before the final REVIEW_REQUIRED exit
- unconsumed pending state
- empty pending consume submitted/ledger IDs
- approved 34940 marked submitted in guard evidence but missing from materialized order artifacts

## REPAIR_CANDIDATE

YES

Narrow repair candidate for Phase31-F1W:

- make Submit partial-pass terminalization idempotent for BUY_ITEM_SCOPED_REVIEW batches
- reconcile already materialized historical broker/order side effects by pending_item_id before creating new ones
- persist submitted_order_ids / ledger_order_record_ids or equivalent per-item terminal state for submitted approved items
- preserve reviewed item non-submission for 76920
- fail closed on any approved item whose guard says submitted but whose order side effect is missing, such as 34940, unless the repair deliberately replays that item idempotently under a verified no-duplicate contract

Do not weaken corporate-action quarantine or mark 76920 SAFE.

## IMPLEMENTATION_CHANGED

NO

## FRESH_RUN_EXECUTED_BY_CODEX

NO

## RESUME_EXECUTED_BY_CODEX

NO

## REPLAY_EXECUTED

NO

## LONG_HISTORICAL_EXECUTED

NO

## RESUME_AFTER_REPAIR_POSSIBLE

CONDITIONAL

Resume is possible only after F1W or equivalent Submit repair can prove that the four already accepted 2022-12-08 side effects are reconciled idempotently and not duplicated, and that the missing 34940 materialization is handled explicitly.

## NEXT_TASK_RECOMMENDATION

Phase31-F1W focused Submit integration repair.

Do not resume before F1V root cause is resolved.

## Evidence Detail

### Exact Submit HALT Evidence

Evidence root:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T050423121340Z`

Submit evidence:

- `daily/2022-12-08/submit/cli_result.json`: exit_code 20
- `daily/2022-12-08/submit/runtime_manifest.json`: final_state REVIEW_REQUIRED
- top-level `fresh_run_summary.json`: status HALT, exit_code 30
- `run_state.json`: status HALT, next_job `2022-12-08:submit`

Submit manifest summary:

- reason = `submit completed with rejected/unknown/blocked items`
- blocked_count = 1
- submitted_count = 4
- pending_plan_present = true
- pending_classification = VALID
- pending_item_count = 6
- pending_slot_status = REVIEW_REQUIRED
- no_order_authority_status = PASS
- no_order_authority_reason = `pass_buy_items_submit_review_buy_items_deferred`
- batch_blocking_review_guard_count = 0
- system_defect_guard_count = 0

### Pending State

Active pending:

| item_id | symbol | side | qty | state | approved | source_decision_type | feasibility_status | batch_submit_status | review_reason |
|---|---|---:|---:|---|---|---|---|---|---|
| strategy-9242cb1dda97a6433677 | 61440 | BUY | 100 | APPROVED | true | BUY_NEW | PASS | PASS_ITEM_SUBMITTABLE | |
| strategy-dae988dcba6a12b37f97 | 76920 | BUY | 200 | REVIEW_REQUIRED | false | BUY_NEW | REVIEW_REQUIRED | ITEM_REVIEW_REQUIRED | corporate_action_event_not_resolved |
| strategy-5c7d2975b463ced32e60 | 34940 | SELL | 100 | APPROVED | true | SELL_EXIT | PASS | PASS_ITEM_SUBMITTABLE | |
| strategy-8f700934de4464ffa4d5 | 82560 | SELL | 300 | APPROVED | true | SELL_EXIT | PASS | PASS_ITEM_SUBMITTABLE | |
| strategy-d869e35933dcd6215538 | 37790 | SELL | 100 | APPROVED | true | SELL_EXIT | PASS | PASS_ITEM_SUBMITTABLE | |
| strategy-72c08989f99bb27f815a | 45910 | SELL | 100 | APPROVED | true | SELL_EXIT | PASS | PASS_ITEM_SUBMITTABLE | |

Pending metadata:

- state = REVIEW_REQUIRED
- plan_created_date = 2022-12-08
- target_session_date = 2022-12-08
- consumed = false
- submitted_order_ids = []
- ledger_order_record_ids = []

### Approval State

Relevant approval artifact:

`.runtime/runtime_state/sell_pipeline/2022-12-08/buy_review_sell_continuation_approval_artifact.json`

Approval:

- approval_id = `approval-4fcbbbe595a97ca9`
- status = APPROVED
- pending_plan_id = `pending-order-plan-buy-review-sell-continuation-2022-12-08-9002066a3dd7`
- approved_item_ids:
  - strategy-9242cb1dda97a6433677
  - strategy-5c7d2975b463ced32e60
  - strategy-8f700934de4464ffa4d5
  - strategy-d869e35933dcd6215538
  - strategy-72c08989f99bb27f815a

This matches the active pending approved item set and excludes reviewed 76920.

### Submit Set Comparison

Pending approved set:

`{61440 BUY, 34940 SELL, 82560 SELL, 37790 SELL, 45910 SELL}`

Approval approved set:

`{61440 BUY, 34940 SELL, 82560 SELL, 37790 SELL, 45910 SELL}`

Submit guard PASS item set:

`{61440 BUY, 34940 SELL, 82560 SELL, 37790 SELL, 45910 SELL}`

Materialized order side-effect set:

`{61440 BUY, 82560 SELL, 37790 SELL, 45910 SELL}`

Missing materialized approved item:

`34940 SELL strategy-5c7d2975b463ced32e60`

### Final Questions

1. 12/8のSubmitは何で止まったか？

76920 BUYがSubmit feasibilityで`corporate_action_event_not_resolved`になり、item-scoped reviewとして未提出になったため、最終stateがREVIEW_REQUIREDになった。

2. Pending自体は正常か？

構造は正常。REVIEW_REQUIRED stateで、5件approved/submittable、1件76920 reviewed。

3. ApprovalとPendingは完全一致しているか？

approved item setは一致。hash binding fieldsはapproval artifactに未記録。

4. Submit inputはApprovalと一致しているか？

Submit guard inputは一致。ただし実際にmaterializeされたorder side-effect setは34940を欠く。

5. duplicate submit/orderは存在するか？

重複は未発生。ただし4件の既存side effectがあり、pending未消費なのでresume時の重複リスクは高い。

6. BUY+SELL composite Submitが原因か？

単純なcomposition不対応ではない。compositeはguard上処理されたが、partial-pass review terminalization/idempotencyが未完。

7. cash/position/quantity contractに不整合はあるか？

数量・cash・SELL current positionはいずれも主要原因ではない。

8. no-order authorization問題か？

No. non-empty composite pendingであり、empty/no-order pathではない。

9. F1系SELL修理が直接原因なのか、新しく露出した下流欠陥なのか？

直接原因ではない。F1修理によりSubmitまで到達して露出した下流Submit defect。

10. 最小修正後にresumeできるか？

Conditional yes. 既存4件のside effectをpending_item_idでidempotently reconcileし、34940欠落を明示処理できる修理が必要。
