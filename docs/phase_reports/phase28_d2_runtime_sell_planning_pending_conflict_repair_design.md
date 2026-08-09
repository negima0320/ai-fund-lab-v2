# Phase28-D2: Runtime Sell Planning Pending Conflict Repair Design

Task ID: `Phase28-D2`

Task Type: `DESIGN_ONLY`

Status: `COMPLETE`

Primary Judgment: `PHASE28_D2_PENDING_CONFLICT_REPAIR_DESIGN_COMPLETE_PHASE28_D3_READY`

Phase28-D3 Entry Decision: `APPROVED`

Implementation Changed: `false`

Resume Executed: `false`

Fresh Run Executed: `false`

Long Historical Executed: `false`

## 1. Executive Summary

Phase28-D1 confirmed that the Phase28-D After run halted because Morning Strategy Planning had already materialized a same-day SELL pending item for `76470`, and Sell Planning later processed PM `REDUCE` for the same symbol. Sell Planning treated this as an active pending SELL conflict and fail-closed with:

```text
REVIEW_REQUIRED_REDUCE_PENDING_SELL_CONFLICT:76470
```

Phase28-D2 designs the repair contract. The recommended Phase28-D3 repair is a single Runtime/Sell Planning pending reconciliation change:

```text
Before same-symbol active SELL pending is treated as REVIEW_REQUIRED,
classify existing SELL pending versus new Sell Planning intent by identity,
lineage, state, quantity authority, and submit/consume state.

If same or compatible, preserve/reconcile idempotently.
If truly conflicting or externally committed, fail closed while preserving the original pending plan.
No-signal must not overwrite active pending.
```

This is not a Phase28-C ADD bridge repair and must not change strategy, PM action thresholds, ADD eligibility, Portfolio Construction, Position Sizing, Runtime Planning mapping, Safety, Data Readiness, Submit semantics, or performance parameters.

## 2. Scope

In scope:

- Pending producer inventory
- Pending item identity contract
- Same-symbol SELL conflict classification
- REDUCE / EXIT priority with existing pending
- Quantity reconciliation contract
- No-signal preservation contract
- Idempotency contract
- Resume / retry contract
- BUY / SELL independence contract
- Phase28-D3 minimal repair and regression contract

Out of scope:

- implementation
- fresh-run / resume / 100BD execution
- Phase28-C ADD bridge changes
- strategy threshold changes
- PM REDUCE / EXIT decision criteria changes
- Safety, Data Readiness, Submit, Broker, Execution redesign

## 3. Phase28-D1 Root Cause Accepted

D1 root cause is accepted as the design input:

```text
Morning Strategy pending wrote SELL 76470
PM emitted REDUCE 76470
Sell Planning saw active same-symbol SELL pending
Sell Planning returned REVIEW_REQUIRED_REDUCE_PENDING_SELL_CONFLICT:76470
Runtime CLI stopped because stop-on-review-required was active
```

The defect is not the existence of fail-closed behavior itself. The defect is that Sell Planning has only a coarse same-symbol SELL conflict gate and does not first classify whether the existing pending item is the same canonical decision, a compatible update, or a true dangerous duplicate.

## 4. Documents Reviewed

- `docs/phase_reports/phase28_d1_20230118_sell_planning_halt_causal_diagnosis.md`
- `docs/phase_reports/phase28_c_canonical_add_allocation_bridge_implementation.md`
- `docs/phase_reports/phase28_b_incremental_investment_eligibility_and_canonical_add_allocation_design.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/position_management_reduce_quantity_contract.md`
- `docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md`
- `docs/02_architecture/position_management_decision_trace_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/01_requirements/phase_roadmap.md`
- `reports/phase28_d1_20230118_sell_planning_halt_causal_diagnosis/`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260805T124145808243Z/`

## 5. Current Pending Architecture

Runtime Architecture v2 fixes the submit target to:

```text
.runtime/pending_order_plan/pending_order_plan.json
```

The current code already has a single canonical pending slot and side-aware pending fields:

- `PendingOrderPlan.items`
- `approved_buy_item_ids`
- `approved_sell_item_ids`
- `review_required_buy_item_ids`
- `review_required_sell_item_ids`
- `buy_items_status`
- `sell_items_status`
- `review_scope`
- `sell_continuation_allowed`

The current repair gap is narrower:

- `compose_with_existing_buy_pending` handles active BUY preservation/composition.
- Sell Planning uses `_pending_sell_conflict(...)` as a coarse same-symbol SELL conflict gate.
- `_write_no_signal_pending(...)` can write an empty no-signal pending even when the reason is review/conflict.
- Existing pending SELL identity, lineage, and quantity compatibility are not classified before fail-closed.

## 6. Pending Producer Inventory

The following producers may generate, update, preserve, or transition pending:

| Producer | Authority | Output | Current gap |
|---|---|---|---|
| Morning Strategy Planning | Strategy Planning Authority / Pending Materialization | mixed BUY/SELL pending plan | May write same-day SELL before Sell Planning |
| Runtime Planning consumer | pure quantity-delta mapper output consumed by Strategy Planning | order plan candidates | Does not own pending conflict resolution |
| Sell Planning pipeline | PM REDUCE/EXIT/legacy ADD compatible SELL pending producer | sell order plan, approval, pending | Coarse same-symbol SELL conflict gate |
| REDUCE planner | deterministic quantity contract inside Sell Planning | SELL pending item | Must not own final duplicate resolution alone |
| EXIT planner | deterministic full-close quantity contract inside Sell Planning | SELL pending item | EXIT priority must interact with existing pending |
| Safety / Approval transition | Block/Review/Approval authority | pending state and item approval fields | Must preserve side scope |
| Retry / Resume path | runtime orchestration | re-entry to a stage | Must be idempotent and compare generation |
| Legacy compatibility ADD path | legacy-compatible ADD consumer | BUY/ADD pending candidates | Must not affect SELL conflict repair |
| No-signal writer | empty/no-action materializer | no-order pending evidence | Must not overwrite active pending on conflict |

## 7. Pending Authority Matrix

The executable authority must remain one:

```text
Approved PendingOrderPlan in .runtime/pending_order_plan/pending_order_plan.json
validated by Submit Guard immediately before broker write.
```

Authority boundaries:

- PM owns existing-position directional intent: `ADD`, `HOLD`, `REDUCE`, `EXIT`.
- Strategy / Runtime Planning owns canonical execution intent candidates.
- Pending Composition owns merge / preserve / replace / review classification.
- Approval owns item approval status.
- Submit Guard owns final pre-submit feasibility.
- Execution / Broker owns submitted/fill status.

No component may submit from historical order-plan files, approval artifacts, PM decisions, or daily strategy artifacts directly.

## 8. Pending Item Identity Contract

Minimum identity key:

```text
target_session_date
business_date
normalized_symbol
side
intent_class
position_campaign_id when available
source_decision_type
source_pm_decision_id or runtime_planning_id
source_order_plan_id / planning_authority_hash
quantity_contract_version
accepted_generation_id
```

Quantity is not part of the base identity because compatible updates may legitimately change quantity. Quantity is part of conflict classification.

Classifications:

| Classification | Meaning | Action |
|---|---|---|
| `SAME_INTENT_DUPLICATE` | Same symbol, side, business date, source lineage, intent class, and equivalent quantity | Preserve existing; no new item |
| `SAME_SYMBOL_COMPATIBLE_UPDATE` | Same symbol/side with newer compatible authority and safe quantity reconciliation | Merge or replace with evidence |
| `SAME_SYMBOL_CONFLICTING_INTENT` | Same symbol/side but REDUCE/EXIT/Strategy SELL lineage conflicts | Review unless priority contract resolves |
| `SAME_SYMBOL_CONFLICTING_QUANTITY` | Same identity but incompatible quantity authority | Review |
| `CROSS_DAY_STALE_PENDING` | Existing pending is from earlier date/session | Expire/cancel through lifecycle or review |
| `ALREADY_SUBMITTED` | Existing item was submitted or post-send unknown | Review; no replacement |
| `ALREADY_FILLED` | Fill/ledger consumed the item | Reconcile remaining quantity from Current before new intent |
| `UNKNOWN_IDENTITY` | Required key missing | Review |

## 9. Pending Composition Model

Recommended model for Phase28-D3:

```text
Option C: Existing plan reconciliation
```

Reason:

- It is the smallest repair scope.
- It fits the existing single pending slot.
- It preserves Runtime Architecture v2's one submit target.
- It can reuse existing side-aware Pending fields.
- It avoids a broader canonical composer rewrite.
- It is common to Historical, Demo, and Production.

Design:

```text
existing pending plan
+ new authoritative Sell Planning intent
-> classify each same-symbol SELL
-> preserve / merge / replace / review
-> write one composed pending plan only after classification passes
```

Longer term, Option A can be considered, but D3 should not implement a full canonical pending composer.

## 10. Same-symbol SELL Conflict Classification

Same-symbol active SELL is not automatically a fatal conflict. It must be classified:

| Case | Expected resolution |
|---|---|
| Same lineage REDUCE duplicate | `PENDING_SELL_IDEMPOTENT_DUPLICATE_PRESERVED` |
| Morning Strategy SELL and PM same REDUCE | `PENDING_SELL_COMPATIBLE_UPDATE_MERGED` if same date/symbol/side and quantity authority aligns |
| REDUCE -> EXIT | `PENDING_SELL_REDUCE_UPGRADED_TO_EXIT` when EXIT has current full-close authority and no submit attempt exists |
| EXIT -> REDUCE | `PENDING_SELL_EXIT_PRESERVED_OVER_REDUCE` or review if lineage ambiguous |
| Quantity differs but both derive from same Current and quantity contract | `PENDING_SELL_QUANTITY_RECONCILED` |
| Quantity differs with incompatible authority | `PENDING_SELL_CONFLICTING_QUANTITY_REVIEW` |
| Submitted / post-send unknown | `PENDING_SELL_ALREADY_SUBMITTED_REVIEW` |
| Partial fill | `PENDING_SELL_PARTIAL_FILL_REVIEW` or remaining-quantity reconcile only with execution authority |
| Previous-day stale pending | `PENDING_SELL_STALE_EXPIRED` through lifecycle, or review if expiry unsafe |
| Missing identity | `PENDING_SELL_IDENTITY_UNKNOWN` |

## 11. REDUCE / EXIT Priority

PM action priority remains:

```text
EXIT > REDUCE > HOLD > ADD
```

Priority with existing pending:

- existing REDUCE + new REDUCE same lineage: preserve existing.
- existing REDUCE + new REDUCE compatible same-date lineage: reconcile quantity and preserve one item.
- existing REDUCE + new EXIT: upgrade to EXIT only if no submit attempt, same campaign/current position, and quantity authority passes.
- existing EXIT + new REDUCE: preserve EXIT; do not downgrade silently.
- existing submitted SELL + new EXIT/REDUCE: review against broker/ledger status.
- existing partial fill + new EXIT/REDUCE: compute remaining quantity only from execution/current authority; otherwise review.

Quantity authority must remain with Sell Planning / Submit Guard, not PM.

## 12. Quantity Reconciliation

Quantity reconciliation must use authority, not max/min shortcuts.

Inputs:

- Current position quantity
- sellable quantity / broker availability when available
- existing pending quantity
- new Sell Planning quantity contract
- source decision type: REDUCE or EXIT
- submitted/fill/consume status
- remaining quantity after known fills

Rules:

- Same REDUCE lineage with same final quantity: preserve.
- Same REDUCE lineage with deterministic recomputed quantity from same Current: preserve or metadata refresh.
- REDUCE to EXIT: new quantity may increase up to current sellable quantity if upgrade is contract-valid.
- EXIT to REDUCE: do not reduce existing sell quantity silently.
- Submitted or post-send unknown: do not replace.
- Partial fill: reconcile only against execution authority and current remaining position; otherwise review.
- Unknown Current or sellable authority: review.

## 13. Pending State Transitions

State handling:

| State | Merge | Replace | Preserve | Review |
|---|---|---|---|---|
| `CREATED` | yes if identity known | yes | yes | if unknown |
| `PENDING_APPROVAL` | yes | yes if compatible | yes | if conflict |
| `APPROVED` | yes if same intent | compatible replace requires supersede evidence | yes | if quantity or identity conflict |
| `SUBMITTING` | no | no | yes | review |
| `SUBMITTED` | no | no | yes | review |
| `POST_SEND_UNKNOWN` | no | no | yes | review |
| `PARTIALLY_FILLED` | only through execution/remaining authority | no silent replace | yes | review by default |
| `FILLED` / `CONSUMED` | no active duplicate | new intent only after Current refresh | preserve history | review if stale current |
| `REJECTED` / `CANCELLED` / `EXPIRED` / `SUPERSEDED` | not active | new plan allowed | preserve history | if stale evidence |
| `REVIEW_REQUIRED` | no auto-merge | no | preserve original | manual repair/review |
| `EMPTY` | no active pending | new plan allowed | not applicable | no |

The code currently has no explicit `PARTIALLY_FILLED` pending state, but execution evidence has partial-fill concepts. D3 must treat partial-fill evidence as review unless a remaining-quantity authority is explicitly available.

## 14. No-signal Preservation

No-signal means no new executable signal. It must never mean "delete active pending."

Contract:

- Conflict review must preserve the original pending plan.
- Proposed replacement/no-signal must be written as a separate evidence artifact.
- Active pending must not be overwritten by empty no-signal when status is `REVIEW_REQUIRED` or `BLOCKED`.
- Empty no-signal may write the current slot only when the slot is already empty or inactive.
- Original pending hash, item IDs, side counts, and state must be recorded.
- Use compare-and-swap or generation/hash check before write.

Reason code:

```text
PENDING_PLAN_NO_SIGNAL_DID_NOT_OVERWRITE_ACTIVE
```

## 15. Idempotency

Idempotency key:

```text
pending_intent_key =
sha256(
  target_session_date,
  normalized_symbol,
  side,
  intent_class,
  source_decision_type,
  source_pm_decision_id or runtime_planning_id,
  position_campaign_id,
  quantity_contract_version,
  accepted_generation_id
)
```

Repeated sell_planning invocation with the same key must:

- preserve the existing item when equivalent
- not append a duplicate
- not create a new pending item ID unless compatible replacement is explicitly recorded
- not remove opposite-side pending
- record replay detection

Submitted, consumed, or post-send-unknown items are not idempotent-replay candidates for replacement. They require review or a new post-execution Current-derived intent.

## 16. Resume / Retry Safety

Checkpoint policy:

| Checkpoint | Policy |
|---|---|
| Before Sell Planning | retry safe if pending hash unchanged |
| Before pending write | retry safe; no state mutation yet |
| After pending write, before approval | retry only with same generation/hash |
| After approval, before submit | retry safe if approved pending unchanged |
| After submit started | no automatic retry; submit is non-idempotent |
| After submit accepted | rely on execution/ledger; no replacement |
| After partial fill | review or remaining-quantity authority required |
| Before runtime refresh | resume requires submit/execution state proof |
| After HALT with pending overwritten | fresh-run required |

For the D1 run, fresh-run remains required after repair because the halt partially overwrote pending state and could mask the original conflict on resume.

## 17. BUY / SELL Independence

Contract:

- BUY pending conflict does not directly stop valid SELL planning.
- SELL pending conflict does not remove BUY pending.
- Mixed pending plans must keep side-specific state and item IDs.
- One-side no-signal must not clear the other side.
- Global Safety `HALT` may stop both sides.
- Shared pending writes must preserve non-target side unless an explicit side-aware lifecycle transition says otherwise.

## 18. Fail-closed Conditions

Fail closed with original pending preserved when:

- identity is unknown
- quantity authority conflicts
- accepted generation differs without compatibility proof
- submitted / post-send-unknown status exists
- partial fill cannot be reconciled
- campaign or position identity mismatches
- stale pending cannot be safely expired
- broker/Current state is unknown
- source plan hash changed during write
- BUY/SELL side scope cannot be separated

## 19. Observability

D3 must materialize:

- existing pending plan id/hash/state
- existing pending item id
- new decision id
- identity classification
- conflict classification
- resolution action
- preserved / replaced / cancelled / new item IDs
- quantity before / after
- remaining quantity
- position quantity
- campaign id
- business date / target session date
- generation id
- reason codes
- review_required
- resume_safe
- no_signal_overwrite_prevented

Primary reason codes:

- `PENDING_SELL_IDEMPOTENT_DUPLICATE_PRESERVED`
- `PENDING_SELL_COMPATIBLE_UPDATE_MERGED`
- `PENDING_SELL_REDUCE_UPGRADED_TO_EXIT`
- `PENDING_SELL_EXIT_PRESERVED_OVER_REDUCE`
- `PENDING_SELL_QUANTITY_RECONCILED`
- `PENDING_SELL_ALREADY_SUBMITTED_REVIEW`
- `PENDING_SELL_PARTIAL_FILL_REVIEW`
- `PENDING_SELL_STALE_EXPIRED`
- `PENDING_SELL_IDENTITY_UNKNOWN`
- `PENDING_SELL_GENERATION_MISMATCH`
- `PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED`
- `PENDING_PLAN_NO_SIGNAL_DID_NOT_OVERWRITE_ACTIVE`

## 20. Phase28-D3 Minimal Repair

Implement one Runtime repair:

```text
Replace the coarse same-symbol SELL pending conflict gate with a Pending SELL
reconciliation classifier that preserves/reconciles same or compatible pending
and fail-closes only true conflicts while preserving original pending evidence.
```

Expected implementation boundary:

- likely in `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- may add a small helper module under `runtime_v2/pending/` if needed
- must use existing Pending model fields where possible
- must add focused tests only

D3 must not change:

- Phase28-C ADD bridge
- Expected Edge
- PM action thresholds
- REDUCE / EXIT decision criteria
- Safety / Data Readiness
- Broker submit semantics
- cash / exposure / concentration rules
- BUY logic

## 21. Short Regression Contract

D3 must include focused tests:

1. same lineage REDUCE duplicate -> idempotent preserve
2. morning SELL + PM same REDUCE -> compatible reconcile
3. REDUCE -> EXIT -> safe upgrade
4. EXIT -> REDUCE -> EXIT preserve or review
5. conflicting quantity authority -> review
6. already submitted SELL -> review
7. partial fill -> remaining quantity review/reconcile
8. stale previous-day pending -> expire/review
9. no-signal does not overwrite active SELL
10. no-signal SELL does not remove BUY pending
11. SELL conflict does not remove BUY pending
12. BUY conflict does not stop valid SELL
13. repeated sell_planning invocation is idempotent
14. pending evidence preserved on review
15. Runtime Planning / PM responsibilities unchanged
16. Phase28-C ADD fixtures remain PASS

## 22. Fresh 100BD Restart Contract

After D3 repair:

```text
fresh 100BD required
```

Do not resume `runtime-test-historical-smoke-20260805T124145808243Z`.

Reasons:

- current run completed only 9 days
- 2023-01-18 stopped before submit/execution/runtime_state_refresh
- pending was partially overwritten
- resume could hide the original defect
- 100BD comparison would be contaminated

## 23. Architecture Conformance

This design conforms to Runtime Architecture v2 because it:

- preserves one canonical pending slot
- prevents duplicate submit
- treats submit as non-idempotent
- does not recalculate strategy decisions in Runtime
- keeps PM quantity boundaries intact
- keeps Submit Guard as final preflight authority
- applies to Historical, Demo, and Production common Runtime

## 24. Risks

- Existing pending items may lack enough lineage for SAME_INTENT classification. In that case D3 must classify as `UNKNOWN_IDENTITY` and preserve original pending under review.
- Partial-fill handling may require execution evidence not present in Pending. D3 should review by default unless remaining quantity authority is explicit.
- A too-broad compatible-update rule could hide real duplicate SELL risk. D3 must keep compatibility narrow.

## 25. Open Gaps

No blocking design gaps remain.

Non-blocking implementation risks:

- Current pending item IDs may not include stable idempotency keys.
- Historical D1 pre-halt pending was only recoverable from embedded manifest evidence after overwrite.
- Explicit partial-fill pending state is absent from `PendingPlanState`; D3 should treat partial-fill evidence as external execution authority.

## 26. Final Judgment

```text
PHASE28_D2_PENDING_CONFLICT_REPAIR_DESIGN_COMPLETE_PHASE28_D3_READY
```

## 27. Phase28-D3 Entry Decision

```text
APPROVED
```

D3 may implement the single Runtime pending conflict repair described above, followed by short regression only. A fresh 100BD After run is required after D3 completion and validation.
