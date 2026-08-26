# Phase31-A3 — 2022-09-26 Submit HALT Root-Cause Audit

## PRIMARY_JUDGMENT

`PHASE31_A3_SUBMIT_REVIEW_REQUIRED_CAUSED_BY_HISTORICAL_CORPORATE_ACTION_QUARANTINE_PLANNING_CONSUMER_GAP`

The 2022-09-26 HALT is not the Phase31-A1 2022-09-16 Data Readiness boundary and is not direct evidence of an A2 regression. The target run passed 2022-09-16 and completed through 2022-09-22. The new boundary is Submit on 2022-09-26.

Submit correctly failed closed after submitting the valid executable subset, but one BUY item (`76920`, quantity `500`) reached Submit as executable even though the Historical corporate-action quarantine registry marked the symbol as unresolved. This is a producer/consumer gap between Planning/Pending eligibility and Submit guard revalidation. The materialized Runtime guard taxonomy did not type this item-scoped corporate-action review in `review_guard_classes` / `review_guard_codes`.

## Required Fields

| Field | Value |
| --- | --- |
| `TARGET_RUN` | `runtime-test-historical-extended-smoke-20260818T003032936578Z` |
| `FAILURE_DATE` | `2022-09-26` |
| `FAILURE_STAGE` | `submit` |
| `FIRST_NON_PASS_LAYER` | `runtime_v2_submit_pipeline` final causal non-PASS: `REVIEW_REQUIRED`. The earlier `safety_operation_guard` checkpoint was superseded by `historical_safety_authority` PASS / `final_safety_status=READY`. |
| `DIRECT_PRODUCER` | Runtime v2 Submit guard / canonical evidence revalidation with Historical corporate-action quarantine policy. |
| `DIRECT_ARTIFACT` | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T003032936578Z/daily/2022-09-26/submit/runtime_manifest.json` |
| `DIRECT_REASON` | `submit completed with rejected/unknown/blocked items`; direct blocked item reason: `corporate_action_event_not_resolved` for BUY `76920`. |
| `MATERIALIZED_GUARD_CLASS` | `[]` / none materialized in `review_guard_classes`; `review_guard_summary.review_guard_count=0`. |
| `SEMANTIC_GUARD_CLASS` | `DATA_INTEGRITY_SAFETY`, guard code `CORPORATE_ACTION_UNRESOLVED` by Phase30 AK9R29 taxonomy semantics. |
| `PENDING_REVIEW_SCOPE` | `BUY_ITEM_SCOPED_REVIEW`; reviewed BUY items were `44220`, `92710`, `93180`; executable items were `41920`, `76920`, `54010`, `41700`. |
| `QUANTITY_AUTHORITY_CONSISTENT` | Yes for the blocked item: `quantity=500`, `quantity_contract.selected_quantity=500`, `requested_quantity=500`, `quantity_status=RESOLVED_EXECUTABLE`, PC discrete quantity authority `final_allocated_quantity=500`, status `PASS`. Submit then set `quantity_reconciliation_status=REVIEW_REQUIRED` due to corporate-action quarantine, not arithmetic mismatch. |
| `CASH_AUTHORITY_CONSISTENT` | Yes. BUY `76920` had `cash=321160`, `buying_power=321160`, `reserved_notional=43600`, `post_buy_cash=277560`, `post_buy_buying_power=277560`. Cash was not the direct blocker for this item. |
| `VALID_PARTIAL_SUBMIT_AVAILABLE` | Yes. Submit accepted/submitted 3 orders: BUY `41920`, SELL `54010`, SELL `41700`. |
| `VALID_SELL_BLOCKED_BY_BUY` | No. SELL `54010` and `41700` had `sell_quantity_guard_status=PASS` and were submitted; `buy_sell_submit_independence_preserved=true`. |
| `STRATEGY_CAUSAL` | Not as investment logic. Strategy/PM/PC/PS produced an executable BUY for `76920`, but the direct non-PASS is Runtime guard consumption of Historical corporate-action quarantine, not Strategy alpha or sizing intent. |
| `RUNTIME_DEFECT` | Yes: Planning/Pending consumed the item as executable (`planning_submit_feasibility_pass`) while Submit later identified `should_have_been_blocked_at_planning=true` via `historical_corporate_action_symbol_quarantine`. |
| `LEGITIMATE_FAIL_CLOSED` | Yes. Submit did not send the quarantined BUY and ended `REVIEW_REQUIRED` instead of silently overriding the guard. |
| `PRODUCER_CONSUMER_GAP` | Yes. The quarantine authority is consumed at Submit but not early enough by Planning/Pending eligibility. |
| `PHASE30_ARCHITECTURE_REGRESSION` | Partial/no. Central cash/quantity and Pending review scope remain conformant; the gap is a missing corporate-action quarantine consumer and missing typed guard materialization for this Submit item. |
| `A2_REPAIR_ACTIVE_IN_CAUSAL_PATH` | Active only in the mixed BUY item-scoped review / SELL continuation path. It allowed executable SELLs and non-reviewed BUYs to proceed while reviewed BUYs stayed deferred. |
| `A2_REGRESSION` | No direct evidence. A2 behavior appears beneficial/expected: reviewed BUYs were not submitted, SELL continuation was not blocked by reviewed BUYs, and the new blocker is a separate corporate-action quarantine item. |
| `PASS_TO_HALT_DELTA` | A1 boundary `2022-09-16:data_readiness` passed; run completed through `2022-09-22`; next failure boundary is `2022-09-26:submit`. Delta is from Data Readiness/Pending lifecycle to Submit-time corporate-action quarantine. |
| `COMPLETED_DAY_EVIDENCE_USABLE` | Yes. `run_state.json` shows 30 completed business days, last `2022-09-22`, and includes `2022-09-16`. |
| `REPAIR_REQUIRED` | Yes. |
| `NEXT_TASK_RECOMMENDATION` | Phase31-A4: integrate Historical corporate-action quarantine authority into Planning/Pending executable membership before Submit, and materialize Submit corporate-action review through Runtime guard taxonomy (`DATA_INTEGRITY_SAFETY` / `CORPORATE_ACTION_UNRESOLVED`) with affected item ids and recoverability. |

## Evidence Trace

### Run Boundary

- `run_state.json`: `completed_business_days[-1] = 2022-09-22`; `2022-09-16` is present in completed days.
- `daily/2022-09-26/submit/cli_result.json`: Runtime CLI `returncode=20`; job `submit`; business date `2022-09-26`.
- Submit manifest: `final_state=REVIEW_REQUIRED`, `exit_code=20`, `reason="submit completed with rejected/unknown/blocked items"`, `pending_classification=VALID`, `pending_read_valid=true`, `submitted_count=3`, `blocked_count=1`.

### Strategy / PM / PC / PS

- `morning/strategy_planning_authority_evidence.json` marks pending item `strategy-ad09e6fee55afe67084d` / symbol `76920` with `source_submit_feasibility_status=PASS` and reason `planning_submit_feasibility_pass`.
- `sell_planning/runtime_manifest.json` carries the same item as approved BUY, quantity `500`, `feasibility_status=PASS`, `state=APPROVED`.
- The quantity contract is internally coherent: Strategy Runtime Planning selected quantity `500`, PS status `PASS`, PC discrete authority `PASS`, no legacy sizing/cash fallback.

### Pending Scope

- Submit `no_order_authority_evidence.pending_review_scope_authority` reports:
  - `review_scope=BUY_ITEM_SCOPED_REVIEW`
  - `reviewed_buy_item_ids`: 3 reviewed BUYs
  - `executable_item_ids`: 4 executable items
  - `partial_submit_allowed=true`
  - `sell_continuation_allowed=true`
  - `owns_cash_authority=false`
  - `owns_quantity_authority=false`
- This is architecturally consistent with A2: Pending scope owns membership only, not cash or quantity.

### Submit

- Submit item results:
  - Submitted: BUY `41920`, SELL `54010`, SELL `41700`
  - Deferred item-scoped review: BUY `44220`, `92710`, `93180`
  - Blocked/review: BUY `76920`, reason `corporate_action_event_not_resolved`
- Submit guard evidence for `76920`:
  - `manual_review_required=true`
  - `blocked_at_submit_reason=corporate_action_event_not_resolved`
  - `violated_policy=historical_corporate_action_symbol_quarantine`
  - `violated_policy_source=.runtime/runtime_state/corporate_action_quarantine/historical_symbol_registry.json`
  - `should_have_been_blocked_at_planning=true`

### Guard Taxonomy Gap

The top-level Submit manifest has:

```text
review_guard_classes=[]
review_guard_codes=[]
review_guard_summary.review_guard_count=0
```

However, the semantic reason `corporate_action_event_not_resolved` maps under the Runtime guard taxonomy to `DATA_INTEGRITY_SAFETY` with guard code `CORPORATE_ACTION_UNRESOLVED`. The absence of typed materialization is a reporting/consumer contract gap, not proof that the fail-closed behavior was wrong.

## Conclusion

The root cause is a Submit-discovered Historical corporate-action quarantine for `76920` that was not consumed by Planning/Pending executable membership. Submit’s fail-closed behavior was legitimate, A2 did not regress, and SELL continuation remained intact. The next repair should move the quarantine authority into the earlier executable-membership path and normalize the Submit guard evidence into AK9R29 typed guard fields.
