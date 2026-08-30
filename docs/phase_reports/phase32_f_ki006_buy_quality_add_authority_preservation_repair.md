# Phase32-F - KI-006 Adaptive Buy Quality ADD Authority Preservation Repair

Target evidence run: `runtime-test-historical-extended-smoke-20260829T205402869666Z`  
Repair scope: `P31-KI-006 Adaptive Buy Quality target / ADD increment re-expansion`  
Task type: narrow correctness repair, not performance optimization.

## Root Cause Confirmation

Phase32-E found actual execution-path violations on:

- `2022-10-12 94320`
- `2022-11-04 94320`
- `2022-11-09 94320`

In those cases, Buy Quality produced `quality_action=BUY_WAIT` and `quality_allocation_adjustment=0.0`, but downstream artifacts still reached positive ADD execution:

```text
Buy Quality BUY_WAIT / adjustment 0.0
  -> Portfolio Construction positive accepted ADD increment
  -> Position Sizing quantity_delta_candidate = 100
  -> Runtime Planning BUY_ADD
  -> BUY_ADD fill 100
```

The current source confirmed the same root cause:

- `src/ai_fund_lab_v2/strategy/buy_quality.py` assigns `BUY_WAIT` a zero allocation adjustment.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py` had `_buy_wait_applies_to_member(...)` return `False` for non-`BUY_NEW` semantics / existing positions. That preserved the existing position, but it also allowed existing-position ADD incremental capital to continue.
- PC ADD bridge and lot-aware final reallocation could then preserve or recreate positive `requested_incremental_weight`, `accepted_incremental_weight`, and `lot_aware_accepted_incremental_weight`.
- `src/ai_fund_lab_v2/strategy/position_sizing.py` preserved existing-position baseline for PM ADD, then consumed positive accepted ADD increment without checking that Buy Quality had blocked incremental ADD.
- Runtime Planning only consumed positive PS delta; it did not re-rank or reauthorize BUY_ADD.

## Violated Authority Contract

The violated contract is:

```text
KEEP_EXISTING_POSITION != AUTHORIZE_ADDITIONAL_CAPITAL
```

For existing-position PM ADD:

- Buy Quality must never force the existing holding to zero.
- PM remains responsible for HOLD / REDUCE / EXIT authority.
- But if Buy Quality says `BUY_WAIT` or an explicit `quality_allocation_adjustment=0.0` applies to the ADD decision, incremental ADD authority is zero.
- Downstream PC / PS / Runtime must not resurrect positive incremental ADD capital.

## Exact First Violation Boundary

First violation boundary:

```text
Adaptive Buy Quality
  -> Portfolio Construction existing-position ADD target/increment
```

The secondary defensive boundary is:

```text
Portfolio Construction
  -> Position Sizing ADD transaction delta
```

Runtime Planning was not the source of the defect. It correctly maps a positive current-position PS delta to `BUY_ADD`; therefore the repair prevents invalid positive delta before Runtime receives it.

## Repair Design

The repair adds an explicit incremental ADD quality gate:

- In Portfolio Construction:
  - existing-position PM ADD with `quality_action=BUY_WAIT` / `TEMPORARY_BUY_INELIGIBLE` or explicit `quality_allocation_adjustment=0.0` now preserves the existing baseline weight and sets incremental ADD request/accepted weights to zero.
  - ADD bridge returns `BUY_QUALITY_BLOCKS_INCREMENTAL_ADD` and does not evaluate later ADD investment evidence as a source of positive increment.
  - lot-aware final reallocation no longer treats such rows as BUY_ADD participants.
- In Position Sizing:
  - if an upstream artifact still presents positive ADD increment while Buy Quality explicitly blocks the ADD increment, PS zeros `accepted_incremental_weight`, `lot_aware_accepted_incremental_weight`, `transaction_delta_weight`, `quantity_delta_candidate`, and `final_quantity_delta`.
  - existing quantity is preserved; no REDUCE or EXIT is synthesized.
- Runtime Planning remains unchanged:
  - valid positive PS ADD deltas still map to `BUY_ADD`.
  - zero current-position deltas map to `NO_ACTION`.

The gate deliberately does not treat missing Buy Quality fields as a new Phase32-F block. This keeps the repair narrow and avoids changing older missing-evidence behavior outside the confirmed defect.

## Reduced-Allocation Handling

`REDUCED_ALLOCATION_ONLY` with `0 < quality_allocation_adjustment < 1` remains eligible for positive incremental ADD when PC/PS authorize it. Phase32-F does not introduce a new formula, threshold, or weight. It only prevents zero-authority ADD from being re-expanded.

## Files Changed

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `tests/strategy/test_phase22_j_position_sizing.py`
- `tests/strategy/test_phase22_g_runtime_planning.py`
- `docs/phase_reports/phase32_f_ki006_buy_quality_add_authority_preservation_repair.md`

## Existing-Position Baseline Handling

Existing-position baseline is preserved. The repair changes only incremental ADD authority:

- `target_membership` remains true for the held position.
- current/baseline quantity is not liquidated.
- no REDUCE/EXIT authority is created from Buy Quality.
- PM remains the authority for sell-side lifecycle actions.

## Incremental ADD Authority Handling

For explicit `BUY_WAIT` or explicit zero quality adjustment on existing-position ADD:

- PC accepted ADD increment is zero.
- Lot-aware ADD participant type becomes `NONE`, not `BUY_ADD`.
- PS transaction delta is zero even if stale/conflicting accepted increment fields are present.
- Runtime receives zero delta and emits `NO_ACTION`, not `BUY_ADD`.

## PM Artifact Re-Acceptance Status

PM artifact re-acceptance required: `NO`.

Phase32-F did not change `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` or other PM accepted-current-path source. The repair is in Strategy PC/PS authority preservation only, so Phase32-D PM Runtime authority registry/index/checkpoint synchronization is not required.

## Focused Validation Results

Phase32-F focused tests:

```text
python3 -m pytest \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase32_f_buy_wait_existing_add_preserves_baseline_and_blocks_increment \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase32_f_reduced_existing_add_remains_positive_when_quality_authorizes_increment \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase32_f_buy_wait_existing_add_does_not_resurrect_positive_delta \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase32_f_reduced_existing_add_preserves_positive_authorized_delta \
  tests/strategy/test_phase22_g_runtime_planning.py::test_phase32_f_runtime_does_not_resurrect_buy_wait_add_when_ps_delta_zero
```

Result: `5 passed`.

Focused G129 / Phase32-C / PC-PS consistency:

```text
python3 -m pytest \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_actual_buy_add_fill_runtime_id_merges_when_open_campaign_lineage_proves_identity \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_actual_shaped_add_history_anchors_merge_with_canonical_bridge \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_conflicting_fill_campaign_without_canonical_bridge_does_not_merge \
  tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py \
  tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py
```

Result: `16 passed`.

Edited-file regression sweep:

```text
python3 -m pytest \
  tests/strategy/test_phase22_e_portfolio_construction.py \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase22_g_runtime_planning.py
```

Result: `281 passed`.

Known artifact-availability limitation:

An attempted broader G129 bundle that included `tests/strategy/test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py` produced 2 `FileNotFoundError` failures for old run artifacts:

- `runtime-test-historical-extended-smoke-20260824T203644021876Z/daily/2023-03-22/strategy/portfolio_construction.json`
- `runtime-test-historical-extended-smoke-20260824T055234719725Z/daily/2023-04-07/strategy/portfolio_construction.json`

The G129 report already identified this class of missing historical fixture artifact. These failures are not Phase32-F code regressions.

Static diff check:

```text
git diff --check -- src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/position_sizing.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py
```

Result: `PASS`.

## Regression Judgments

- Phase32-C regression: `NO`.
  - Phase32-C provenance/campaign tests passed.
- G129 regression: `NO`.
  - G129 order-increment submit and BUY_ADD campaign materialization tests passed.
- Strategy semantic change: `NO`.
  - PM ADD, BUY Quality thresholds/features, ranking, Expected Edge, Cash, Risk Pacing, Safety, caps, and Re-entry semantics were not changed.
- Parameter/threshold/weight change: `NO`.
  - No config or numeric Strategy parameter was changed.

## Remaining ADD Issue

`ADD_TARGET_WEIGHT_UNCHANGED` remains. Phase32-E observed that most PM ADD intents still resolve to no incremental capital at PC/PS. Phase32-F does not treat that as a defect and does not optimize ADD frequency or winner capitalization.

## Remaining Known Issue

`P31-KI-001` remains outside this repair. Prior EXIT semantic information loss into later REENTRY evaluation was not addressed by Phase32-F.

## Exact Next User Action

Run the user-operated Historical fresh-run validation:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-10-03 \
  --business-days 300 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Codex did not run this command.

## Final Judgment

`PHASE32_F_KI006_BUY_QUALITY_ADD_AUTHORITY_PRESERVATION_REPAIRED`
