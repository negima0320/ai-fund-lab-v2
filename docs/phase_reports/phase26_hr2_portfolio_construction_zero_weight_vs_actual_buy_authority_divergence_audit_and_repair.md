# Phase26-HR2 Implementation Report

Created: 2026-08-04T07:37:40.066521Z
Run: `runtime-test-historical-smoke-20260804T065614902857Z`

## Primary Root Cause

`runtime_test.py` generated post-runtime `strategy_shadow_generation` into the same `daily/<business_date>/strategy` directory used by morning Formal Strategy Planning Authority. After fills were projected, current positions contained the newly bought symbols; the later shadow materialization therefore emitted `target_weight: 0.0`, `membership_intent: UNRESOLVED`, and `weight_reason: member_not_selected` for those symbols. That artifact was not the planning-time BUY authority, but it overwrote the directory that analysts naturally inspect.

## Canonical BUY Authority

The canonical BUY producer/consumer edge for the four BUY fills is:

`buy_quality_decisions -> portfolio_construction -> position_sizing -> runtime_planning -> runtime_v2.planning.strategy_authority.activate_strategy_planning_authority -> pending_order_plan -> submit -> execution projection`

Morning evidence shows `planning_intent=BUY_NEW`, `order_side_intent=BUY`, and `pending_item_generated=true` for `93180`, `45960`, `94320` on 2022-07-01 and `94340` on 2022-07-04.

## Repair

- Formal morning strategy artifacts are explicitly classified as `FORMAL_PLANNING_AUTHORITY_INPUT` with `IMMUTABLE_MORNING_PLANNING_SNAPSHOT`.
- Post-runtime observability shadow artifacts are explicitly classified as `POST_RUNTIME_OBSERVABILITY_SHADOW` with `LATEST_RUNTIME_STATE_MATERIALIZATION`.
- Runtime Test post-runtime shadow generation now writes to `daily/<business_date>/strategy_eod_shadow`, leaving `daily/<business_date>/strategy` available for the formal morning planning snapshot.

## Runtime Boundary

Runtime decisions, BUY quality formula, scores, thresholds, position sizing, submit, safety, and execution projection behavior were not changed. The change is evidence materialization/classification only.

## Known Evidence Gap

The BUY fill normalization in this historical run records `pending_item_id=MISSING` and `order_plan_item_id=MISSING` for BUY fills. HR2 does not change that path. The bridge used here is run-scoped morning Strategy Planning Authority evidence by business date, symbol, side, and generated pending lineage.

## Validation

- Compile: PASS (`PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase26_hr2 python3 -m py_compile ...`)
- Shadow wiring: PASS (`12 passed`)
- Phase26-H / PC / PS / Runtime Planning: PASS (`105 passed`)
- Strategy Planning Authority / Pending / Submit Guard: PASS (`28 passed`)
- Closure / Observability / Strategy Authority Gate: PASS (`22 passed`)
- Report JSON validation: PASS
- fresh-run / resume / 1BD / 3BD / 10BD: not executed by Codex

## User Rerun Command

See `user_3bd_rerun_command.md`.

## Judgment

`PHASE26_HR2_SHADOW_PORTFOLIO_CONSTRUCTION_AUTHORITY_CLASSIFICATION_REPAIRED`

## Planning-Time Quality Evidence Correction

The overwritten `strategy/buy_quality_decisions.json` in the target run is not reliable as the immutable planning-time Quality snapshot. Submit guard `quantity_contract` is the surviving planning-time consumer evidence for actual submitted BUYs: `93180`, `45960`, and `94340` are `FULL_ALLOCATION_ELIGIBLE` with adjustment `1.0`; `94320` is `REDUCED_ALLOCATION_ONLY` with adjustment `0.769443`. This reinforces the same root cause: post-runtime strategy artifacts in the old evidence directory must not be treated as the morning authority snapshot.
