# Phase29-L21T-L Batch Review Coupling / BUY-SELL Independence Contract Audit

Task ID: `Phase29-L21T-L`

Mode: READ-ONLY audit only. No implementation, config/schema/threshold/model/Accepted Generation change, Production/Demo broker mutation, runtime/pending mutation, fresh-run, resume-run, 100BD, or long Historical run was performed.

## Primary Judgment

`PHASE29_L21T_L_BUY_SELL_AUTHORITY_COUPLING_DEFECT_CONFIRMED_BUY_BATCH_ATOMICITY_INTENDED_PARTIAL_APPROVAL_ARCHITECTURE_UNRESOLVED`

Required classification:

`C. BUY_SELL_AUTHORITY_COUPLING_DEFECT`

This is not classified as a confirmed regression. Historical lineage proves that whole-BUY-batch atomicity and `BLOCKED_BY_BATCH_REVIEW` are intentional Phase24-ID/IE behavior. The defect is narrower: existing Production-common architecture says `BUY_ITEM_SCOPED_REVIEW` may permit independent SELL continuation, but the current sell-planning composition boundary still treats absence of approved BUY ids as `active_buy_missing` and preserves the reviewed BUY pending without materializing the independently valid SELL.

## Executive Summary

For target halt `2023-05-16:sell_planning` in `runtime-test-historical-smoke-20260812T055747290953Z`:

- BUY item `30410` independently failed Planning Submit Feasibility with `estimated amount exceeds selected_position_amount`.
- BUY item `24350` independently passed item feasibility, but was secondarily marked `BLOCKED_BY_BATCH_REVIEW`.
- Top-level `approved_item_ids`, `approved_buy_item_ids`, and `approved_sell_item_ids` were intentionally empty under Phase24-ID/IE batch atomicity.
- Pending was correctly classified as `BUY_ITEM_SCOPED_REVIEW` with `sell_continuation_allowed=true`.
- Data Readiness recognized this as `buy_item_scoped_review_sell_continuation_ready`; Safety was READY/NEUTRAL and did not block SELL.
- SELL Planning independently generated and approved a `76010` REDUCE SELL item, quantity `100`, estimated amount `25,400`.
- The final sell-planning result became `REVIEW_REQUIRED` because composition required a preservable approved BUY pending. Since `approved_item_ids=[]`, `read_active_buy_pending()` returned `active_buy_missing`; the original BUY review pending was preserved and the valid SELL was not written to the current Pending slot.

Therefore:

- One invalid BUY currently invalidates every BUY in the same batch: YES, intended by Phase24-ID/IE batch atomicity.
- One invalid BUY should not automatically block SELL Planning: confirmed by Phase24-HV/IE and Data Readiness behavior.
- One invalid BUY should not block an otherwise valid SELL unless a global/shared blocker exists.
- BUY and SELL should remain separate authority lanes inside shared Pending.
- Partial BUY approval is not currently supported as an approved Production contract; it requires a new aggregate revalidation design before implementation.

## Mandatory Material Reviewed

Direct lineage:

- `docs/phase_reports/phase29_l21t_k_one_lot_pending_planning_submit_authority_propagation_repair.md`
- `docs/phase_reports/phase29_l21t_j_one_lot_authority_non_firing_and_batch_review_propagation_audit.md`
- `docs/phase_reports/phase29_l21t_i_canonical_capital_utilization_final_audit.md`
- `docs/phase_reports/phase29_l21t_h_one_lot_planning_submit_feasibility_authority_integration_repair.md`
- `docs/phase_reports/phase29_l21t_f_pending_buy_preservation_and_buy_sell_composition_repair.md`
- `docs/phase_reports/phase29_l21t_e_pending_submit_execution_continuity_audit_and_repair.md`

Architecture / earlier lineage:

- `docs/phase_reports/phase24_ht_planning_submit_feasibility_contract.md`
- `docs/phase_reports/phase24_hv_buy_review_sell_continuation_contract.md`
- `docs/phase_reports/phase24_id_aggregate_portfolio_constraint_and_execution_reconciliation_contract.md`
- `docs/phase_reports/phase24_ie_aggregate_feasibility_buy_item_review_sell_continuation_contract.md`
- `docs/phase_reports/phase24_ie_aggregate_feasibility_buy_item_review_sell_continuation_implementation.md`
- `docs/phase_reports/phase28_d2_runtime_sell_planning_pending_conflict_repair_design.md`
- `docs/phase_reports/phase28_d3_runtime_sell_pending_reconciliation_implementation.md`
- `docs/phase_reports/phase28_d7_sell_pending_required_authority_merge_repair_design.md`
- `docs/phase_reports/phase28_d8_compatible_sell_pending_required_authority_merge_implementation.md`
- `docs/phase_reports/phase26_k_final_architecture_conformance_responsibility_fulfillment_and_closure_review.md`
- `docs/phase_reports/phase29_j3_runtime_planning_buy_review_sell_independence_root_cause_audit.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/01_requirements/phase_roadmap.md`

## Target Run

Target run:

`reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T055747290953Z`

Target halt:

`2023-05-16:sell_planning`

Run state:

- Completed through `2023-05-15`.
- Halted at `2023-05-16:sell_planning`.
- No resume was executed.

## Target-Date Item Reconstruction

Current pending evidence was read from the preserved current slot `.runtime/pending_order_plan/pending_order_plan.json` and matched the run manifests.

Top-level pending state:

| Field | Value |
| --- | --- |
| `pending_plan_id` | `pending-strategy-plan-historical-2023-05-16-5a3e91a3f6115622` |
| `state` / `plan_overall_status` | `REVIEW_REQUIRED` / `REVIEW_REQUIRED` |
| `buy_items_status` | `REVIEW_REQUIRED` |
| `sell_items_status` | `NOT_PRESENT` |
| `review_scope` | `BUY_ITEM_SCOPED_REVIEW` |
| `review_scope_source` | `phase24_ht_planning_submit_feasibility_v1` |
| `review_scope_reason` | `estimated amount exceeds selected_position_amount` |
| `sell_continuation_allowed` | `true` |
| `approved_item_ids` | `[]` |
| `approved_buy_item_ids` | `[]` |
| `approved_sell_item_ids` | `[]` |
| `review_required_buy_item_ids` | `["strategy-2d6618ea2a942fb23636"]` |
| `review_required_sell_item_ids` | `[]` |

Pending item table:

| pending_item_id | Symbol | Side | Semantic | Qty | Source decision | Item feasibility | Item review reason | Approved flag | Batch submit status | Individually executable | Blocked only by another item | Approved membership | Downstream effect |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `strategy-4123c260ac0c1af2deb4` | `24350` | BUY | BUY_NEW | 500 | Strategy Planning | PASS | `batch_submit_blocked_by_item_scoped_review` | false | `BLOCKED_BY_BATCH_REVIEW` | YES | YES | none | No Submit; contributes `active_buy_missing` because approved ids empty |
| `strategy-2d6618ea2a942fb23636` | `30410` | BUY | BUY_NEW | 100 | Strategy Planning | REVIEW_REQUIRED | `estimated amount exceeds selected_position_amount` | false | `ITEM_REVIEW_REQUIRED` | NO | NO | `review_required_buy_item_ids` | Blocks BUY batch; root item for review |

Planning Submit item evidence:

| Symbol | Status | Violated policy | Estimated amount | Selected position amount | Note |
| --- | --- | --- | ---: | ---: | --- |
| `24350` | PASS | none | 159,500 | 176,140.4 | Item-local PASS |
| `30410` | REVIEW_REQUIRED | `position_sizing` | 227,400 | 186,617.98 | Item-local failure before L21T-K repair |

## Failing, Passing, And Secondary-Blocked Items

Independently failing BUY items:

- `30410`, `strategy-2d6618ea2a942fb23636`, BUY_NEW, quantity `100`, estimated amount `227,400`, failed `position_sizing`.

Independently passing BUY items:

- `24350`, `strategy-4123c260ac0c1af2deb4`, BUY_NEW, quantity `500`, estimated amount `159,500`, Planning Submit Feasibility PASS.

Secondarily batch-blocked items:

- `24350`, not item-local invalid. It is blocked solely by Phase24-ID/IE whole-batch review coupling.

Blocked executable BUY notional derivable from target:

- Secondary batch-blocked executable notional: `159,500` JPY.
- Independently invalid BUY notional: `227,400` JPY.

Run-wide occurrence within available target run artifacts:

- `BLOCKED_BY_BATCH_REVIEW` appears only for `2023-05-16` in run artifacts.
- Individually PASS BUY items later blocked by batch review: `1`.
- BUY_NEW affected count: `1` secondary blocked, `1` independently failed.
- BUY_ADD affected count: `0` derivable.
- REENTRY affected count: `0` derivable.
- Number of days affected before halt: `1` derivable.

## SELL Independence Reconstruction

Actual SELL / REDUCE / EXIT decision:

- YES. PM had two REDUCE decisions (`94340`, `76010`) in Strategy PM evidence.
- Sell Planning selected executable `76010` REDUCE.

SELL item generated by sell pipeline:

| Artifact | Value |
| --- | --- |
| `.runtime/runtime_state/sell_pipeline/2023-05-16/order_plan.json` | one SELL item |
| pending item id | `opi-sell-reduce-pm-76010-001` |
| symbol | `76010` |
| side | SELL |
| source decision | REDUCE |
| quantity | `100` |
| estimated amount | `25,400` |
| quantity contract status | PASS |
| sell approval artifact | `APPROVED`, approved item id `opi-sell-reduce-pm-76010-001` |

Prior-day Current comparison:

- `2023-05-15` EOD current holdings included `76010` quantity `500`, market value `127,000`.
- The planned `76010` REDUCE quantity `100` was within owned quantity.

Safety / readiness:

- `data_readiness/data_readiness.json` component pending reason: `buy_item_scoped_review_sell_continuation_ready`.
- `sell_planning/runtime_manifest.json`:
  - `data_readiness_status=READY`
  - `data_readiness_safety_status=READY`
  - `final_safety_status=READY`
  - `safety_block_buy=false`
  - `safety_block_sell=false`
  - `safety_block_submit=false`
  - `safety_halt_runtime=false`
  - `runtime_state_safety_state=BUY_REVIEW_REQUIRED`

Answer to SELL questions:

1. Actual SELL/REDUCE/EXIT existed: YES, `76010` REDUCE.
2. Quantity independently resolved: YES, quantity contract PASS, 100 shares.
3. Current SoT quantity valid: YES, prior EOD current had 500 shares.
4. Safety independently allowed SELL: YES, no sell block, no submit block, no halt.
5. BUY review prevented final Pending generation/Submit: YES, via sell-pipeline composition requiring approved BUY preservation and returning REVIEW_REQUIRED.
6. Runtime distinguishes `BUY REVIEW_REQUIRED`, `SELL REVIEW_REQUIRED`, and global review structurally in Pending and Data Readiness, but sell-pipeline composition does not fully consume that distinction.
7. `runtime_state_safety_state=BUY_REVIEW_REQUIRED` is observational here; Safety itself did not stop SELL.
8. Stop cause: pending composition / sell-pipeline return status, then runtime driver stop-on-review; not Safety.

## Producer / Consumer Lineage

Strategy producer:

```text
strategy/runtime_planning.json
-> strategy_planning_authority
-> .runtime/runtime_state/strategy_planning/2023-05-16/order_plan.json
-> approval_artifact.json
-> pending_order_plan/pending_order_plan.json
```

Planning evidence:

- `strategy_planning_authority_evidence.json`: `status=PASS`, `pending_commit_status=COMMITTED_CURRENT`, `pending_item_count=2`, selected symbols `["24350", "30410"]`.
- Strategy approval initially approved both BUY item IDs before Planning Submit Feasibility transformed the pending into scoped review.

Planning Submit lineage:

- `pending.promotion.link_approval_to_pending()` evaluates approved candidate items through `evaluate_planning_submit_feasibility()`.
- On non-PASS feasibility it calls `_review_scope_for_submit_feasibility()`.
- For BUY-only known policy failures, it sets `review_scope=BUY_ITEM_SCOPED_REVIEW`, `sell_continuation_allowed=true`, clears approved ids, and materializes `ITEM_REVIEW_REQUIRED` / `BLOCKED_BY_BATCH_REVIEW`.

Batch approval authority:

- Phase24-ID/IE aggregate reservation is active.
- `tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase24_id_planning_aggregate_cash_reservation_blocks_later_buy` explicitly asserts earlier PASS BUY items become `BLOCKED_BY_BATCH_REVIEW` and `approved_buy_item_ids == ()`.

SELL authority lineage:

```text
Position Management REDUCE
-> sell_pipeline quantity contract
-> sell order_plan.json
-> sell approval_artifact.json
-> pending sell reconciliation/composition
```

Composition lineage:

- `read_active_buy_pending()` returns `active_buy_missing` if no positive BUY item is in top-level `approved_item_ids`.
- Under `BUY_ITEM_SCOPED_REVIEW`, approved ids are intentionally empty.
- Sell reconciliation recognized `PENDING_SELL_NO_CONFLICT` for the new SELL item, but the later invalid-BUY guard preserved the original BUY review pending and returned `REVIEW_REQUIRED`.

Runtime state lineage:

- Data Readiness recognized `BUY_ITEM_SCOPED_REVIEW` as sell-continuation-ready.
- Runtime driver halted because `sell_planning` returned `REVIEW_REQUIRED`.

## Code Evidence

Key code locations:

- `src/ai_fund_lab_v2/runtime_v2/pending/promotion.py`
  - Lines 168-198: non-PASS planning feasibility clears `approved_item_ids`, `approved_buy_item_ids`, `approved_sell_item_ids`, sets scoped review fields.
  - Lines 348-379: `_review_scope_for_submit_feasibility()` creates `BUY_ITEM_SCOPED_REVIEW` and `sell_continuation_allowed`.
  - Lines 390-412: `_materialize_item_scoped_review_state()` assigns `ITEM_REVIEW_REQUIRED` or `BLOCKED_BY_BATCH_REVIEW`.
- `src/ai_fund_lab_v2/runtime_v2/pending/composition.py`
  - Lines 52-78: `read_active_buy_pending()` requires item membership in `approved_item_ids`.
  - Lines 363-381: sell reconciliation can preserve opposite side, but does not itself authorize BUY-item-scoped SELL continuation.
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
  - Lines 332-346: reads `existing_buy_pending` and active pending snapshot.
  - Lines 534-576: runs sell reconciliation.
  - Lines 577-625: if active pending has BUY items but no preservable approved BUY, returns `REVIEW_REQUIRED` and preserves original pending.
  - Lines 664-679: composite pending is only built with `existing_buy_pending`, which excludes `BUY_ITEM_SCOPED_REVIEW`.
- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
  - Lines 2245-2264 and 2450-2498: recognizes valid `BUY_ITEM_SCOPED_REVIEW` as `buy_item_scoped_review_sell_continuation_ready`.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
  - Lines 1718-1727: operation state labels review decisions as `BUY_REVIEW_REQUIRED`.

## Historical / Git Lineage

`BLOCKED_BY_BATCH_REVIEW` lineage:

- Introduced in commit `9e9b39d phase24 FIX`.
- Same commit added:
  - `phase24_ht_planning_submit_feasibility_contract.md`
  - `phase24_hv_buy_review_sell_continuation_contract.md`
  - `phase24_id_aggregate_portfolio_constraint_and_execution_reconciliation_contract.md`
  - `phase24_ie_aggregate_feasibility_buy_item_review_sell_continuation_contract.md`
  - `tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py`
  - `pending/promotion.py` scoped review materialization.

Original purpose:

- Prevent deterministic Submit-infeasible BUY batches from becoming APPROVED Pending.
- Preserve aggregate reservation across cash, buying power, exposure, and position count.
- Keep reviewed Pending batch atomic: no item from that reviewed batch crosses Submit.

Was it designed for BUY-only batches?

- The Phase24-ID/IE test and observed target behavior primarily cover BUY aggregate reservation.
- Phase24-HV/IE simultaneously define that BUY item-scoped review must not globally block independent SELL continuation.

Was it later reused when BUY and SELL began sharing Pending?

- Shared side-aware Pending fields already existed by Phase28-D2/D3 design.
- Phase28-D3/D8 added SELL pending reconciliation and authority merge, but did not add a path that composes an independently valid new SELL with a `BUY_ITEM_SCOPED_REVIEW` pending whose approved BUY ids are empty.

Older implementation support for item-scoped approval:

- Human Approval and Submit iterate item ids, but Phase24-IE explicitly removed feasibility-PASS BUY ids from `approved_buy_item_ids` under aggregate review. That is not partial BUY approval; it is evidence-only item status under batch atomicity.

SELL continuation previously independent:

- Phase24-HV/IE architecture says YES.
- Data Readiness code implements YES for safety/readiness.
- Phase29-J3 fixture probe reported BUY review did not block SELL when SELL authority was complete.
- Current L21T-L target shows the remaining gap is composition/pending write authority, not PM/Safety/SELL quantity authority.

Regression determination:

- No regression claimed. The all-or-nothing BUY batch is intentional Phase24 behavior.
- The SELL continuation mismatch is a partial migration / implementation gap across Phase24-HV/IE and Phase28-D3/D8 composition, not proven as a prior working behavior that later regressed.

## Current Contract Vs Intended Contract

Current implementation:

- Any item-local BUY review makes the reviewed Pending plan non-submittable.
- All BUY ids are cleared.
- Feasibility-PASS BUY items are marked `BLOCKED_BY_BATCH_REVIEW`.
- Data Readiness may allow SELL planning to start.
- Sell Planning may generate a SELL item.
- Final composition still rejects because active BUY preservation requires approved BUY ids.

Intended Production-common contract from Architecture SoT:

- `BUY_ITEM_SCOPED_REVIEW` blocks BUY Submit.
- It must not automatically invalidate independent PM, SELL Planning, or approved SELL Submit when valid Current/Safety/SELL authority exists.
- Legacy `state=REVIEW_REQUIRED` must not be interpreted as global block without inspecting structured scope.
- Shared Pending may remain, but consumers must use side-specific status/approved/review ids.

## Option A-E Comparison

### Option A: Current All-Or-Nothing Batch

Safety benefit:

- Strong aggregate reservation safety.
- Prevents accidental partial BUY submit from an invalid batch.

Capital deployment cost:

- Unrelated valid BUYs are suppressed when one BUY fails.
- Target cost: `24350` valid BUY_NEW `159,500` JPY blocked.

SELL effect:

- Current implementation also blocks valid SELL continuation in this target, which is not supported by Phase24-HV/IE.

Design support:

- Supported for BUY batch atomicity.
- Not supported as a reason to block independent SELL.

### Option B: Item-Scoped BUY Approval

Safety:

- Not acceptable as a simple per-item pass-through. Independent item PASS does not prove aggregate batch safety.

Aggregate constraints:

- Must revalidate cash, buying power, exposure, position count, same-symbol conflicts, and one-lot/safety/corporate-action constraints.

Design support:

- Not currently approved. Phase24-IE explicitly keeps approved ids empty for reviewed batches.

### Option C: Two-Level Approval

Flow:

```text
item-local feasibility
-> remove item-scoped failures
-> aggregate revalidation of survivors
-> approve final BUY subset only if aggregate constraints pass
```

Safety:

- Production-grade candidate if partial BUY approval is desired.
- Requires new explicit contract and tests.

Design support:

- Best candidate for future partial BUY approval, but not current SoT.

### Option D: Separate BUY And SELL Authority Lanes In Shared Pending

Safety:

- Preserves BUY batch fail-closed while allowing independent SELL when global safety is READY.

Design support:

- Already implied by Phase24-HV/IE, Runtime Architecture v2, and existing side-specific fields.

Recommendation:

- YES for L21T-M repair boundary.

### Option E: Separate Pending Artifacts

Safety / complexity:

- Could isolate lanes physically, but increases orchestration and submit-source complexity.

Design support:

- Not required. Existing architecture explicitly supports shared Pending with side-specific fields.

Recommendation:

- NO for L21T-M unless future evidence proves shared Pending cannot express the contract.

## Critical Aggregate Safety Analysis

If item-scoped BUY approval is ever introduced, it must not mean:

```text
each item passed locally -> whole surviving batch is approved
```

Required safeguards:

- Available cash: re-reserve sequentially for survivors.
- Buying power: re-reserve sequentially for survivors.
- Gross exposure: recompute post-buy exposure.
- Single-name concentration: re-evaluate each survivor, including one-lot overshoot predicates.
- Max position count: recompute new-position slots.
- Aggregate reservation: preserve Phase24-ID reservation semantics after filtering.
- Duplicate symbol handling: reject or merge same-symbol BUY conflicts explicitly.
- BUY_NEW + BUY_ADD same-symbol conflict: fail closed unless one canonical authority resolves it.
- One-lot discrete overshoot: consume only formal PC/PS one-lot authority within Safety hard cap.
- Safety hard cap: never relax.
- Corporate Action blockers: remain item/global fail-closed according to scope.
- BQ blockers: block the item; do not authorize through planning-submit.
- REENTRY blockers: block the item; do not authorize unrelated semantics without revalidation.

For L21T-M, partial BUY approval should not be implemented unless this second aggregate validation contract is accepted.

## Capital Deployment Relevance

For target `2023-05-16`:

- Individually PASS BUY items later batch-blocked: `1`.
- Blocked executable BUY notional: `159,500` JPY.
- BUY_NEW affected by secondary block: `1`.
- BUY_ADD affected: `0`.
- REENTRY affected: `0`.
- Days affected before halt in available artifacts: `1`.
- Valid SELL generated but not carried to final Pending: `76010` REDUCE, estimated `25,400` JPY.

Wider underdeployment from this mechanism is NOT DERIVABLE from the halted target beyond the above because the run stops on `2023-05-16`.

## SELL Independence Determination

SELL independence contract:

- BUY and SELL are logically independent decisions.
- A BUY-local item review must not block risk-reducing SELL/REDUCE/EXIT unless there is a shared/global blocker.

Target determination:

- SELL decision existed and was independently valid.
- Current SoT quantity was valid.
- Safety allowed SELL.
- Data Readiness allowed sell continuation.
- Pending composition blocked runtime continuation because it required approved BUY preservation and did not carry the independent SELL lane through `BUY_ITEM_SCOPED_REVIEW`.

Therefore:

`SELL_LANE_INDEPENDENCE_CONTRACT_BROKEN_AT_PENDING_COMPOSITION = YES`

## Recommended Repair Boundary

Do not implement in L21T-L. For L21T-M:

### BUY Batch

Should valid BUY items survive another BUY item's local review?

`CONDITIONAL / NOT IN L21T-M MINIMAL SCOPE`

Current Phase24-ID/IE says NO for the reviewed batch. A future partial BUY approval design may allow it only with two-level approval and aggregate revalidation.

### SELL Lane

Should SELL / REDUCE / EXIT continue when BUY-only review exists?

`YES`, when:

- `review_scope=BUY_ITEM_SCOPED_REVIEW`
- `sell_continuation_allowed=true`
- `approved_buy_item_ids=[]`
- `review_required_sell_item_ids=[]`
- Data Readiness / Safety READY
- Current SoT position authority READY
- PM and SELL Planning authority PASS
- SELL quantity contract PASS
- pending temporal/session identity valid
- no global/shared blocker exists

### Global Safety

Conditions that legitimately block both BUY and SELL:

- broker state inconsistency
- corrupted or missing Current SoT
- unresolved owned/available SELL quantity
- global trading halt or emergency stop
- explicit Safety halt/block
- missing/corrupt/ambiguous authority affecting the full pending plan
- stale/future/mismatched temporal authority
- portfolio-scoped review that invalidates both sides
- corporate-action quarantine that applies to the SELL symbol or global trading state
- submit policy/source corruption

### Pending Artifact

Should shared Pending remain?

`YES`

Use side-specific lanes in the shared artifact. Avoid physical split unless later evidence proves shared Pending cannot preserve authority.

### Aggregate Revalidation

Is a second aggregate validation required after BUY filtering?

`YES` if partial BUY approval is implemented.

Not required for minimal L21T-M SELL continuation if no BUY from the reviewed batch is submitted and only independent SELL is carried.

## Exact L21T-M Entry Contract

Recommended implementation scope:

```text
BUY_ITEM_SCOPED_REVIEW current pending
+ independently valid SELL/REDUCE/EXIT pending
-> shared current Pending containing only approved SELL lane plus preserved BUY review evidence
-> BUY ids remain non-approved
-> SELL approved ids contain only SELL items
-> Submit sees SELL only as executable
-> reviewed BUY evidence remains visible and non-submittable
```

Forbidden for L21T-M:

- Promote `BLOCKED_BY_BATCH_REVIEW` BUY items to approved.
- Resurrect invalid BUY.
- Submit reviewed BUY.
- Treat all BUY reviews as SELL-pass.
- Ignore Safety/Data Readiness/Current authority.
- Split Pending artifacts without design approval.
- Disable stop-on-review globally.

Expected Primary Judgment if implemented successfully:

`PHASE29_L21T_M_BUY_ITEM_SCOPED_REVIEW_SELL_CONTINUATION_COMPOSITION_REPAIRED_FOCUSED_REGRESSION_PASS`

## Mandatory Regression Matrix For L21T-M

| # | Scenario | Expected Pending state / ids | Runtime / Submit expectation |
| ---: | --- | --- | --- |
| 1 | two valid BUY items | APPROVED, both in `approved_buy_item_ids` | BUY submit eligible after aggregate PASS |
| 2 | one valid BUY + one item-local invalid BUY | REVIEW_REQUIRED, `approved_buy_item_ids=[]`, invalid in `review_required_buy_item_ids`, valid marked `BLOCKED_BY_BATCH_REVIEW` | no BUY submit |
| 3 | two invalid BUY items | REVIEW_REQUIRED, both review-required or blocked per evidence, no approved ids | no BUY submit |
| 4 | valid BUY + valid SELL | COMPOSITE / APPROVED, BUY and SELL approved ids present | both eligible after aggregate/pass guards |
| 5 | invalid BUY + valid SELL | BUY review evidence preserved, SELL lane approved only, `approved_sell_item_ids` contains SELL, `approved_buy_item_ids=[]` | SELL submit eligible, BUY not submitted |
| 6 | valid BUY + invalid SELL | REVIEW_REQUIRED for SELL or global depending reason; BUY not silently resurrected | fail closed unless approved BUY can be proven unaffected by contract |
| 7 | global Safety block affecting both | REVIEW_REQUIRED/BLOCKED/HALT according to safety | no BUY or SELL submit |
| 8 | cash aggregate violation after partial filtering | survivors require second aggregate validation; fail if still violates | no unsafe BUY submit |
| 9 | position-count aggregate violation | second aggregate validation blocks BUY survivors if position slots exceeded | no unsafe BUY submit |
| 10 | same-symbol BUY conflict | fail closed or canonical merge only with explicit authority | no duplicate BUY |
| 11 | BUY_ADD + BUY_NEW conflict | fail closed unless canonical semantic resolver proves one authority | no ambiguous BUY submit |
| 12 | one-lot valid BUY plus unrelated invalid BUY | current Phase24 atomicity blocks BUY batch; future partial path requires revalidation | no blind one-lot submit |
| 13 | REENTRY invalid while unrelated BUY_NEW valid | current atomicity blocks BUY batch; future partial path requires revalidation | REENTRY not submitted |
| 14 | no SELL signal + BUY review | original BUY review pending preserved; no EMPTY overwrite; job may complete or review per explicit contract | no BUY submit |
| 15 | valid EXIT while BUY review exists | EXIT SELL lane approved when Safety/Current/quantity pass; BUY remains review | EXIT submit eligible |

## Final Decision

Current all-or-nothing BUY batch behavior:

`INTENDED_FOR_BUY_BATCH_ATOMICITY`

Current blocking of independent SELL under `BUY_ITEM_SCOPED_REVIEW`:

`BUY_SELL_AUTHORITY_COUPLING_DEFECT`

Partial BUY approval:

`ARCHITECTURE_GAP / FUTURE DESIGN REQUIRED`, not approved for immediate repair.

Recommended next task:

`Phase29-L21T-M` focused Production-common repair for SELL continuation through `BUY_ITEM_SCOPED_REVIEW` using shared Pending side lanes, with BUY batch atomicity preserved.
