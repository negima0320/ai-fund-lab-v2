# Phase29-L21T-F Pending BUY Preservation / BUY+SELL Composition Repair

Task ID: `Phase29-L21T-F`

Primary Judgment:

```text
PHASE29_L21T_F_PENDING_BUY_PRESERVATION_AND_BUY_SELL_COMPOSITION_REPAIRED_FOCUSED_REGRESSION_PASS
```

Mode: focused Production/Demo/Historical common runtime repair. No fresh-run, resume-run, long Historical run, threshold/config/model change, Historical-only rescue, BUY/SELL decision-authority merge, or Production safety fail-closed weakening was performed.

## Root Cause

L21T-E isolated the break to the current Pending slot between Strategy Planning Authority and Submit:

```text
Strategy Planning Authority writes BUY pending
-> SELL Planning reads the same single current pending slot
-> SELL Planning can write EMPTY or SELL-only pending
-> Submit consumes the latest slot and never sees the BUY
```

The payload-level reason observed in L21T-E was `active_buy_missing`. `read_active_buy_pending` intentionally treats a BUY as valid only when the current pending is active, same-date, unconsumed, positive quantity, BUY side, and the item ID is present in top-level `approved_item_ids`.

Before this repair, if a current pending was active but not valid as preservable BUY, the SELL no-signal path could continue to EMPTY. In the executable SELL path, an active but non-preservable BUY could also be displaced by SELL-only output. That erased fail-closed pending evidence and caused Submit/Execution continuity loss.

## Repair

Changed Production-common runtime files:

- `src/ai_fund_lab_v2/runtime_v2/pending/composition.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`

Added/updated focused tests:

- `tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py`

### Behavior After Repair

Valid same-day approved BUY pending + SELL no-signal:

- current pending remains `APPROVED`
- BUY item remains present
- `pending_composition_model=PRESERVE_EXISTING_BUY_PENDING`
- Submit can see and submit the BUY item

Valid same-day approved BUY pending + executable SELL:

- current pending becomes `COMPOSITE_PENDING_PLAN`
- BUY item is preserved
- SELL item is added
- top-level and approval `approved_item_ids` cover all composed items

Active but invalid/non-preservable BUY pending:

- SELL Planning does not blindly carry it as valid BUY
- SELL Planning also does not erase it with EMPTY or SELL-only pending
- original current pending is preserved and the result becomes `REVIEW_REQUIRED`
- reason includes the non-preservable cause, for example `active_buy_missing`

Inactive/terminal pending remains terminal behavior; the repair does not revive consumed, expired, cancelled, superseded, rejected, or EMPTY plans as valid BUY authority.

## Pre-Sell Snapshot Evidence

Added `pre_sell_pending_snapshot` to `SellPlanningPipelineResult.to_stage_details()`, and writes:

```text
.runtime/runtime_state/sell_pipeline/<business_date>/pre_sell_pending_snapshot_evidence.json
```

The snapshot records:

- pending read classification
- state
- `approved_item_ids`
- approved BUY/SELL item IDs
- item IDs
- side
- quantity
- item approved flag
- `approved_by_top_level`
- `plan_created_date`
- `target_session_date`
- consumed state
- active/same-date flags
- `active_buy_pending_reason`

This directly closes the L21T-E evidence gap around why `active_buy_missing` occurred.

## BUY/SELL Independence

Preserved.

BUY Planning remains the producer of BUY pending. SELL Planning still owns only SELL decision and SELL quantity materialization. The shared Pending Composition layer preserves or composes independently-authorized items into the single current slot. SELL Planning does not write BUY quantities, reinterpret BUY intent, or resurrect invalid BUY as executable authority.

## Production Fail-Closed

Preserved and tightened.

Invalid active pending is no longer converted into authorized no-order EMPTY. It remains visible as original pending and returns `REVIEW_REQUIRED`, which is safer than erasure. Valid BUY still preserves/composes; invalid BUY does not become executable.

## Focused Regression Results

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -q
```

Result:

```text
17 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py -q
```

Result:

```text
22 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py -q
```

Result:

```text
23 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase23_i_strategy_planning_authority.py -q
```

Result:

```text
18 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py -k 'phase29_l21t_c or phase29_l21t_b or phase29_l21f or phase29_l21s or phase29_l19 or BUY_ADD or REENTRY' tests/strategy/test_phase22_g_runtime_planning.py -k 'phase29_l21t_b or phase29_l21f or sell_reduce_exit or sell or BUY_ADD or REENTRY' -q
```

Result:

```text
23 passed, 114 deselected
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase29_l21k_prior_exit_materialization.py tests/strategy/test_phase22_qe_input_materialization.py -q
```

Result:

```text
23 passed
```

Static:

```text
py_compile PASS
git diff --check PASS
```

Note: initial `py_compile` without `PYTHONPYCACHEPREFIX` failed due macOS user cache permission outside the sandbox. Re-run with `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache` passed.

## Focused Fresh-Run Command For User

Codex did not run this. User-operated validation command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-smoke --start-date 2022-08-23 --end-date 2022-09-16 --confirm --yes-i-understand-this-mutates-trading-state
```

Expected validation focus:

- `2022-08-24 / 78780`: BUY pending survives SELL no-signal and reaches Submit/Execution.
- `2022-09-14 / 94320`: BUY_ADD is not displaced by `37820` SELL; expected composite or fail-closed evidence instead of silent SELL-only overwrite.
- `2022-09-15 / 94320`: existing composite path remains PASS.

## Completion

L21T-F is complete at focused-regression scope.

```text
L21T_FRESH_VALIDATION_READY = YES
```
