# Phase32-DW - DQ SHADOW Two-Stage Ranking / Structured Headroom / Executability Repair

## Scope

- Objective: repair DQ SHADOW diagnostic defects from Phase32-DV.
- Source run for analysis-only re-backfill: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Final DW backfill root: `reports/runtime_tests/analysis/phase32_dw_dq_shadow_backfill_20260903T000001`
- Window: `2022-10-03` through `2023-10-26`
- Production integration: none.
- Runtime/source-run mutation: none.
- Fresh-run/resume/recover/replay: none.
- Model 2: not enabled.
- Future outcome / later PnL usage: none.

## Repair Performed

Changed SHADOW-only DQ evaluator behavior in `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`.

Key changes:

- bumped unified SHADOW schema to `unified_marginal_capital_shadow.v2`
- removed generic JSON text scanning for concentration classification
- added per-security `structured_headroom`
- added per-security `lot_status_decomposition`
- added Stage-A `opportunity_strength_ranking`
- added Stage-B `executable_capital_ranking`
- preserved legacy-compatible `shadow_winner` as Stage-A opportunity-strength winner
- added Production comparison against both Stage-A and Stage-B
- kept `authoritative_consumer_count = 0` and all Production consumer flags false

Changed analysis summary support in `scripts/runtime_test.py`.

Key additions:

- Stage-A divergence counts
- Stage-B divergence counts
- two-stage divergence counts
- Stage-A/Stage-B winner counts
- ADD headroom state counts
- ADD lot-status counts
- Stage-B value/feasibility buckets

Focused tests updated/added in:

- `tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py`
- `tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py`

## Structured Headroom Contract

Security competitors now expose:

- current weight
- strategy single-name cap
- strategy-cap headroom
- safety hard cap
- safety-cap headroom
- desired post-increment weight
- one-lot post-trade weight
- strategy cap applied
- safety hard-cap applied
- actual structured block reason
- explicit `generic_cap_text_classification_used = False`

Headroom states:

- `HEADROOM_AVAILABLE`
- `LESS_THAN_ONE_LOT_HEADROOM`
- `STRATEGY_CAP_BLOCKED`
- `SAFETY_HARD_CAP_BLOCKED`
- `HEADROOM_UNKNOWN`

The old broad text scan, effectively `"CAP" in json.dumps(...)`, is no longer used for concentration/headroom classification.

## Two-Stage Ranking Contract

Stage A answers:

`Which opportunities appear intrinsically strongest using current PIT evidence?`

Stage A may preserve incomplete or currently infeasible opportunities for observability. This keeps "strong but not executable today" visible.

Stage B answers:

`Where can the next executable capital unit actually go now?`

Stage B excludes security competitors when any of these are true:

- evidence is incomplete
- execution feasibility is not `FEASIBLE`
- `next_executable_quantity <= 0`
- structured risk/headroom is not acceptable
- strategy/safety hard constraint blocks execution

Cash competes in Stage B only as complete, feasible, low-cost/acceptable optionality.

## Recompetition Semantics

Strong but infeasible opportunities remain materialized with:

- intrinsic strength
- current executability
- blocking reason
- campaign identity
- `ELIGIBLE_FOR_FRESH_NEXT_DAY_SHADOW_RECOMPETITION`

No reserved capital and no future-order promise are created. Fresh PIT evidence is required each day.

## Final DW Re-Backfill

Command executed:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-dw python3 scripts/runtime_test.py shadow-backfill-marginal-capital --source-run-id runtime-test-historical-extended-smoke-20260902T060955933565Z --start-date 2022-10-03 --end-date 2023-10-26 --output-root reports/runtime_tests/analysis/phase32_dw_dq_shadow_backfill_20260903T000001 --confirm --json
```

Result:

- status: `PASS`
- exit code: `0`
- business days: `264`
- output root: `reports/runtime_tests/analysis/phase32_dw_dq_shadow_backfill_20260903T000001`
- summary hash: `d5a1a5de22351eed4b91a330b0f5f975a545aa686a36153a91bfdfad9c9afad3`
- production change executed: false
- target run mutated: false
- runtime state mutated: false

An earlier same-code-path iteration was written to `phase32_dw_dq_shadow_backfill_20260903T000000`; this report uses `T000001` as the final DW evidence root.

## DT vs DW Repair Effect

Competitor counts are unchanged:

- BUY_ADD: 152
- BUY_NEW: 2,483
- REENTRY: 5,196
- CASH: 264

DT ADD risk buckets:

- `BLOCKED_BY_CONCENTRATION`: 152/152

DW ADD structured headroom:

- `HEADROOM_AVAILABLE`: 144
- `LESS_THAN_ONE_LOT_HEADROOM`: 3
- `SAFETY_HARD_CAP_BLOCKED`: 4
- `STRATEGY_CAP_BLOCKED`: 1

This removes the false all-ADD concentration block.

DW ADD lot-status decomposition:

- `NO_POSITIVE_DESIRED_INCREMENT`: 99
- `NO_ACCEPTED_CONTINUOUS_INCREMENT`: 22
- `EXECUTABLE_INCREMENT_AVAILABLE`: 19
- `BQ_BLOCKS_INCREMENT`: 9
- `SAFETY_HARD_CAP_BLOCK`: 3

This separates zero target, BQ block, accepted-positive executable increment, and true safety block. "Never reached lot resolution" is no longer treated as generic lot infeasible.

Stage-A winners:

- BUY_NEW: 152
- REENTRY: 80
- BUY_ADD: 31
- CASH: 1

Stage-B winners:

- BUY_NEW: 212
- REENTRY: 37
- BUY_ADD: 11
- CASH: 3
- NONE: 1

Stage-B Production comparison:

- `AGREEMENT`: 263
- `Production Cash / SHADOW NONE`: 1

Two-stage divergence highlights:

- `Production NEW_OR_REENTRY / Stage-A ADD / Stage-B NEW`: 19
- `Production NEW_OR_REENTRY / Stage-A ADD / Stage-B REENTRY`: 3
- `Production NEW_OR_REENTRY / Stage-A NEW / Stage-B NEW`: 148
- `Production NEW_OR_REENTRY / Stage-A REENTRY / Stage-B NEW`: 42
- `Production NEW_OR_REENTRY / Stage-A REENTRY / Stage-B REENTRY`: 31
- `Production agrees with Stage-B`: 14

Interpretation: the 22 DU "Production NEW/REENTRY vs SHADOW ADD" cases remain visible in Stage A as ADD attention cases, but Stage B correctly routes them to executable NEW/REENTRY because the ADD rows are incomplete and/or not executable.

## Clean Executable Strong ADD Inventory

Inventory definition:

`HIGH_VALUE + COMPLETE + FEASIBLE + ACCEPTABLE + HEADROOM_AVAILABLE`

DW result:

- clean executable strong ADD rows: 0

Complete/executable ADD rows exist, but none are `HIGH_VALUE`:

- complete/executable/headroom-available ADD rows: 21
- `MEDIUM_VALUE`: 17
- `LOW_VALUE`: 4
- Stage-B ADD winners among them: 11

Stage-B ADD winners:

- `2022-10-06` 94340
- `2022-10-11` 94340
- `2022-10-12` 94340
- `2022-10-13` 94340
- `2022-11-01` 94320
- `2023-02-13` 94320
- `2023-02-15` 54010
- `2023-02-22` 94320
- `2023-02-24` 94320
- `2023-03-15` 94320
- `2023-05-31` 59550

In all listed Stage-B ADD winner cases, Production also selected an ADD row for the same symbol/action family. This is the desired control behavior.

## 94320 Positive Control

94320 after DW:

- ADD rows: 50
- Stage-B ADD winners: 5
- complete/executable/headroom-available medium ADD: 9
- high-value evidence-incomplete ADD: 6
- dominant non-executable states: no positive desired increment, no accepted continuous increment, BQ block

94320 confirms:

- executable ADD remains eligible in Stage B
- zero/incomplete ADD remains visible but cannot win Stage B
- campaign identity remains preserved

`94320_TWO_STAGE_CONTROL = PASS`

## Failed-Graduation Controls

DW preserves distinct reasons:

- 99840: incomplete attention rows, safety-hard-cap blocks, less-than-one-lot-headroom rows, and no-positive-increment rows remain distinct.
- 94340: early executable medium ADD rows become Stage-B winners; later incomplete/zero rows remain Stage-A observable only.
- 83060: mostly no-positive-increment; one complete/executable medium row does not become Stage-B winner because stronger executable alternatives exist.
- 40520: high-value incomplete and low/no-positive-increment rows remain observable but not executable winners.

`FAILED_GRADUATION_REASON_PRESERVATION = PASS`

## Production Equivalence

DQ remains SHADOW only:

- `authoritative_consumer_count = 0`
- `production_allocation_consumer = False`
- `production_ordering_consumer = False`
- `production_sizing_consumer = False`
- `runtime_planning_consumer = False`

No Production allocation, target weight, Position Sizing, Pending, Runtime Planning, Submit, or Execution behavior was connected to the repaired DQ SHADOW output.

`PRODUCTION_OUTPUT_EQUIVALENCE = PASS`

## Focused Validation

Passed:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-dw python3 -m pytest -q tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py
```

Result: `11 passed`

Passed:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-dw python3 -m pytest -q tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase31_g63_runtime_executable_binding.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py
```

Result: `64 passed`

Passed:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-dw python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/strategy/marginal_capital_value.py
```

Result: PASS

## Required Final Answers

1. `GENERIC_CAP_TEXT_CLASSIFICATION_REMOVED = YES`
2. `STRUCTURED_HEADROOM_CONTRACT = PASS`
3. `FALSE_CONCENTRATION_BLOCK_ELIMINATED = PASS`
4. `OPPORTUNITY_STRENGTH_RANKING_PRESENT = YES`
5. `EXECUTABLE_CAPITAL_RANKING_PRESENT = YES`
6. `STRONG_INFEASIBLE_OPPORTUNITY_OBSERVABILITY = PASS`
7. `RECOMPETITION_USES_FRESH_PIT_ONLY = YES`
8. `ADD_ACTION_APPROPRIATE_EVIDENCE_CONTRACT = PASS`
9. `INCOMPLETE_SECURITY_CANNOT_WIN_EXECUTABLE_RANKING = PASS`
10. `LOT_STATUS_SEMANTIC_DECOMPOSITION = PASS`
11. `NEXT_EXECUTABLE_INCREMENT_CONTRACT = PASS`
12. `ZERO_INCREMENT_EXCLUDED_FROM_EXECUTABLE_WINNER = YES`
13. `CASH_EXECUTABLE_COMPARISON_CONTRACT = PASS`
14. `CASH_CALIBRATION_PIT_STRUCTURAL_ONLY = YES`
15. `PRODUCTION_VS_STAGE_A_AND_STAGE_B_COMPARISON = PASS`
16. `TWO_STAGE_DIVERGENCE_CLASSIFICATION = PASS`
17. `94320_TWO_STAGE_CONTROL = PASS`
18. `FALSE_CAP_STRING_MATCH_REGRESSION = PASS`
19. `FAILED_GRADUATION_REASON_PRESERVATION = PASS`
20. `PRODUCTION_OUTPUT_EQUIVALENCE = PASS`
21. `DW_ONE_YEAR_REBACKFILL_EXECUTED = YES`
22. `DT_VS_DW_REPAIR_EFFECT_SUMMARY = FALSE_ADD_CONCENTRATION_152_OF_152_REMOVED; STAGE_B_CREATED; STAGE_B_AGREEMENT_263_OF_264`
23. `CLEAN_EXECUTABLE_STRONG_ADD_INVENTORY = 0_HIGH_VALUE_ROWS; 21_COMPLETE_EXECUTABLE_ADD_ROWS; 11_STAGE_B_ADD_WINNERS`
24. `DQ_PRODUCTION_PROMOTION_EXECUTED = NO`
25. `MODEL2_ENABLED = NO`
26. `FUTURE_OUTCOME_USED = NO`
27. `PRODUCTION_CHANGE_EXECUTED = NO`
28. `TARGET_RUN_MUTATED = NO`
29. `RUNTIME_STATE_MUTATED = NO`
30. `NEXT_RECOMMENDED_STEP = PHASE32_DX_READ_ONLY_STAGE_B_NEUTRALITY_AND_CLEAN_ADD_INVENTORY_ACCEPTANCE`
31. `FINAL_JUDGMENT = PHASE32_DW_DQ_SHADOW_TWO_STAGE_EXECUTABLE_CAPITAL_REPAIRED_REBACKFILL_ACCEPTED_NO_PRODUCTION_PROMOTION`

## Final Judgment

`PHASE32_DW_DQ_SHADOW_TWO_STAGE_EXECUTABLE_CAPITAL_REPAIRED_REBACKFILL_ACCEPTED_NO_PRODUCTION_PROMOTION`
