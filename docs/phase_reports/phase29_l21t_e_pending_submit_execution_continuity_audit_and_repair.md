# Phase29-L21T-E Pending / Submit / Execution Continuity Root Cause Audit

Task ID: `Phase29-L21T-E`

Mode: READ-ONLY audit. No fresh run, resume run, long Historical run, runtime mutation, threshold/config/model change, or BUY/SELL independence change was performed.

Target run:
`reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T023424133327Z`

Primary target: `2022-08-24 / 78780`

Secondary targets: `2022-09-14 / 94320 BUY_ADD`, `2022-09-15 / 94320 BUY_ADD`

## Primary Judgment

`PHASE29_L21T_E_PENDING_SUBMIT_EXECUTION_CONTINUITY_ROOT_CAUSE_CONFIRMED_REPAIR_REQUIRED`

The direct continuity break is after Strategy Planning Authority writes BUY pending and before Submit reads current pending. On `2022-08-24`, `78780` reaches Pending Generation with one approved BUY-intent item, but `sell_planning` subsequently writes an EMPTY current pending container to the same canonical path. Submit then correctly consumes the latest current slot as EMPTY and Execution correctly sees no active pending plan.

This is not a PC/PS/RP/Strategy Planning quantity bug. It is a pending-slot continuity / producer-consumer authority bug at the morning-to-sell-planning-to-submit boundary.

## Direct Root Cause

The runtime has a single canonical current Pending authority:
`.runtime/pending_order_plan/pending_order_plan.json`.

Strategy Planning Authority writes BUY pending to that path when `pending_commit_status == "COMMITTED_CURRENT"` (`src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:384-385`).

`sell_planning` then re-reads that same slot via `read_active_buy_pending` (`src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:331-336`). If no active approved BUY pending is detected and there are no SELL/ADD executable items, `_write_no_signal_pending` writes an EMPTY pending payload to the same path (`src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:742-824`).

For `2022-08-24`, the sell planning evidence reports:

- `status=NO_SIGNAL`
- `reason=NO_SIGNAL:exit_ai_no_sell_signal`
- `pending_path_written_by_sell_planning=true`
- `pending_plan_id=pending-order-plan-sell-no-signal-2022-08-24`
- `pending_composition_model=EMPTY_NO_EXISTING_BUY_PENDING`
- `pending_composition_status=active_buy_missing`
- `preserved_existing_buy_pending=false`

Therefore the direct root cause is: SELL Planning's no-signal branch failed to preserve the morning BUY pending and overwrote current Pending with an EMPTY no-order container.

## Producer/Consumer Authority Chain

- PC, PS, RP, and Strategy Planning Authority all authorize the recovered BUY.
- Morning writes current pending through the common pending writer.
- SELL Planning is the next writer to the same current pending slot.
- Submit is only a consumer of the latest current pending slot.
- Execution is downstream of Submit/current pending and cannot recover an item already removed from current authority.

The runner order confirms `morning -> sell_planning -> submit -> execution` for `2022-08-24`. Pending lifecycle is only conditionally run after `execution`; it is not the cause of the pre-submit disappearance.

## 78780 Lifecycle Trace

### PC

`2022-08-24 / 78780` is a valid one-lot BUY_NEW candidate after L21T-C/D:

- `target_weight=0.243189`
- `one_lot_quantity=100`
- `one_lot_notional=242000`
- `one_lot_feasibility_status=PASS`
- `strategy_cap_overshoot_applied=true`
- safety hard cap remains `0.25`

### PS

Position sizing materializes executable discrete quantity:

- `target_notional=241999.81`
- `target_quantity_candidate=100`
- `quantity_delta_candidate=100`
- `quantity_status=RESOLVED_CANDIDATE`
- `discrete_authorized_quantity=100`
- `one_lot_authority_consumed=true`

### RP

Runtime planning maps the positive quantity to BUY_NEW:

- `planning_intent=BUY_NEW`
- `planned_quantity=100`
- `quantity_delta_candidate=100`
- `quantity_status=RESOLVED_EXECUTABLE`
- reason includes `position_sizing_positive_quantity_delta_maps_to_buy_new`

### Strategy Planning Authority / Pending Generation

Morning evidence:

- `status=PASS`
- `pending_item_count=1`
- `pending_commit_status=COMMITTED_CURRENT`
- `pending_path=.runtime/pending_order_plan/pending_order_plan.json`
- `pending_path_written=true`
- `pending_plan_id=pending-strategy-plan-historical-2022-08-24-ac9fe8a20e205d17`
- lineage item: `security_code=78780`, `planning_intent=BUY_NEW`, `order_side_intent=BUY`, `pending_item_generated=true`

The corresponding strategy artifacts show item `strategy-a9cedaf7c46f234a7241`, `symbol=78780`, `side=BUY`, `quantity=100`, and approval artifact `approval-1121234d73577a69` approves that item.

### Sell Planning Boundary

`sell_planning` writes the same pending path after morning:

- `pending_path_written_by_sell_planning=true`
- `pending_plan_id=pending-order-plan-sell-no-signal-2022-08-24`
- `pending_composition_model=EMPTY_NO_EXISTING_BUY_PENDING`
- `pending_composition_status=active_buy_missing`
- `preserved_existing_buy_pending=false`

This is the continuity break.

### Submit

Submit sees the overwritten EMPTY container:

- `pending_classification=EMPTY`
- `pending_item_count=0`
- `pending_plan_present=false`
- `pending_active=false`
- `no_order_authority_status=PASS`
- `no_order_authority_reason=authorized_no_order_empty_container`
- `submit_action=NO_ACTION`

This behavior is locally correct for the payload Submit receives. The incorrect step is the prior overwrite/removal of BUY pending authority.

### Execution / Fill / Ledger / Campaign / Next-Day Current

Execution sees no active pending:

- `pending_classification=EMPTY`
- `pending_item_count=0`
- `pending_plan_present=false`
- `status=ALREADY_TERMINAL`
- `pending_consumed=false`
- `pending_mutated=false`

`fills.json` is empty, so no ledger/campaign/current-position effect occurs for `78780`.

## 94320 Cross-check

`2022-09-14 / 94320 BUY_ADD` reaches Strategy Planning Authority:

- `pending_item_count=1`
- `pending_commit_status=COMMITTED_CURRENT`
- lineage item: `security_code=94320`, `planning_intent=BUY_ADD`, `order_side_intent=BUY`, `pending_item_generated=true`

However, the same day `sell_planning` produces a SELL pending for `37820`:

- `pending_composition_model=SINGLE_PENDING_NO_EXISTING_BUY`
- `preserved_existing_buy_pending=false`
- `selected_symbols=["37820"]`

Submit on `2022-09-14` submits one SELL item (`37820`) and no `94320` BUY. This is the same continuity class, masked because Submit is VALID rather than EMPTY.

`2022-09-15 / 94320 BUY_ADD` is the positive cross-check:

- Strategy Planning Authority writes two BUY items (`94320`, `94340`).
- `sell_planning` reports `pending_composition_model=COMPOSITE_PENDING_PLAN`, `preserved_existing_buy_pending=true`, `composite_pending=true`.
- Composite pending contains BUY `94320`, BUY `94340`, and SELL `37820`.
- Execution fills `94320 BUY 100`, `94340 BUY 1200`, and `37820 SELL 100`.

This proves the downstream Submit/Execution/Fill path can handle composed BUY+SELL pending when the BUY pending is preserved.

## Pending Persistence Analysis

Current pending persistence is single-slot and last-writer-wins. The intended protection exists in code:

- `read_active_buy_pending` requires active state, same `plan_created_date`, same `target_session_date`, BUY side, positive quantity, and item ID present in `approved_item_ids` (`src/ai_fund_lab_v2/runtime_v2/pending/composition.py:52-78`).
- `_write_no_signal_pending` should preserve existing BUY pending if `existing_buy_pending is not None` (`src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:742-773`).

The observed failure is that `read_active_buy_pending` returned `active_buy_missing` for `2022-08-24`, so the preserve branch did not run and the EMPTY branch wrote current pending.

The target run does not preserve a run-scoped snapshot of the exact current pending payload between morning and sell_planning. Therefore the precise sub-reason for `active_buy_missing` needs a focused repair/test pass: either the morning pending payload lacked top-level `approved_item_ids`, the item approval state did not survive materialization/readback, or another pre-sell-planning mutation changed the slot. The available evidence uniquely establishes the boundary and writer, but the payload-level invariant needs direct regression capture.

## Submit Authority Analysis

Submit reads current pending via the canonical reader. If it receives an EMPTY payload with `active_pending=false`, `_empty_pending_result` returns `authorized_no_order_empty_container` (`src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:680-699`).

For `2022-08-24`, Submit did exactly that. No evidence indicates Submit dropped `78780`; Submit never saw it.

For `2022-09-14`, Submit saw a valid one-item SELL pending and submitted `37820`; it did not see the morning `94320` BUY.

## Execution/Fill Analysis

Execution follows Submit/current pending:

- `2022-08-24`: no pending, no fills, no ledger/campaign update for `78780`.
- `2022-09-14`: valid SELL flow for `37820`; no `94320` BUY.
- `2022-09-15`: valid composite BUY+SELL flow; `94320` BUY fills.

Execution is not the direct root cause.

## Historical vs Production-common Classification

Classification: Production-common pending composition / current-slot authority bug, observed in Historical orchestration.

The affected code is under common runtime pending and sell planning modules, not a Historical-only strategy shortcut. Historical replay exposes the issue because `morning`, `sell_planning`, and `submit` are run as separate jobs against the same current slot.

Any repair must preserve production fail-closed behavior: if the existing pending is invalid, stale, consumed, unapproved, or conflictful, SELL Planning must not blindly carry it forward. But for a valid same-day approved BUY pending, no-signal SELL Planning must not write EMPTY over it.

## BUY/SELL Independence Judgment

BUY/SELL independence is not inherently broken by the desired behavior. The correct contract is:

- BUY Planning owns BUY item production.
- SELL Planning owns SELL item production and SELL quantity authority.
- A shared Pending Composition authority preserves or composes independently-authorized BUY/SELL items into the single current slot.
- SELL no-signal cannot erase valid BUY authority.
- BUY submit guards and SELL submit guards remain item-scoped.

The current failure is an implementation gap in preserving/composing existing BUY pending, not a reason to merge BUY and SELL decision authority.

## Residual Capital Impact

L21T-D attributed recovered planned notional that did not materially affect valuation:

- `78780 BUY_NEW 100`: `242,000` JPY planned notional on `2022-08-24`
- `94320 BUY_ADD 100`: `15,510` JPY planned notional on `2022-09-14`
- total recovered planned BUY notional at risk: `257,510` JPY

Because these did not reliably survive into Submit/Execution, average invested/cash ratios remain effectively unchanged despite PC/PS/RP improvements.

## Repair Performed

NO.

This task remained READ-ONLY. A repair is required, but the payload-level invariant that causes `active_buy_missing` should be captured with a focused regression before editing production code.

## Changed Files

Only this audit report was added:

- `docs/phase_reports/phase29_l21t_e_pending_submit_execution_continuity_audit_and_repair.md`

No runtime code, tests, configs, thresholds, or model artifacts were changed.

## Regression Results

No fresh/resume/long Historical validation was run.

Required final hygiene:

- `git diff --check`: PASS

## Remaining Gaps

1. Add a focused unit/integration regression that builds a same-day approved BUY pending, enters SELL Planning with no SELL signal, and asserts current pending remains the BUY pending rather than EMPTY.
2. Add/extend a run-scoped evidence snapshot for pre-sell-planning current pending readback, including `state`, `approved_item_ids`, item IDs, side counts, and read classification. This would remove the current evidence gap around the exact `active_buy_missing` subcondition.
3. Validate the mixed case where SELL Planning has an executable SELL and an existing same-day approved BUY: expected output is `COMPOSITE_PENDING_PLAN`, as observed successfully on `2022-09-15`.
4. Re-run a focused historical smoke slice only after repair, then evaluate whether 100BD validation is ready.

## 100BD Validation Ready

NO.

The PC/PS/RP/Strategy Planning repair is effective, but Pending/Submit/Execution continuity still requires a focused pending preservation/composition repair before 100BD validation.
