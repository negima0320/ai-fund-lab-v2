# Phase29-L21T-B - One-Lot Strategy Soft-Cap Authority Integration Repair

Task ID: `Phase29-L21T-B`  
Mode: focused implementation + short regression. No fresh-run, resume-run, long Historical run, Runtime/Pending manual mutation, Accepted Generation change, Model change, threshold tuning, Safety hard-cap relaxation, or Historical-only Strategy branch was performed.

## 1. Primary Judgment

```text
PHASE29_L21T_B_ONE_LOT_SOFT_CAP_AUTHORITY_INTEGRATION_REPAIRED_FOCUSED_REGRESSION_PASS
```

`L21T_FRESH_VALIDATION_READY = YES`

## 2. Before

L21T-A confirmed the `2022-08-24` halt chain:

```text
PC 78780 BUY_NEW one-lot target_weight=0.243189
-> above Strategy soft cap 0.18, below Safety hard cap 0.25
-> Position Sizing BLOCK target_weight_above_position_cap:3
-> Runtime Planning quantity_not_produced_due_to_upstream_block
-> Strategy Planning Authority strategy_plan_quantity_unresolved:78780
-> Morning REVIEW_REQUIRED / Runtime Test HALT
```

The issue was not missing historical Safety authority. It was PC/PS/RP authority mismatch around L21S one-lot capital expression.

## 3. Root Cause

PC had authority evidence for:

```text
ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP
```

but PS validation did not fully consume that authority for BUY_NEW / REENTRY new exposure. Runtime Planning then received no resolved quantity, and Strategy Planning Authority correctly refused to write Pending.

## 4. Authority Contract

Strategy `maximum_position_weight = 0.18` remains the normal allocation soft cap.

A target above 18% is accepted only when PC materializes coherent one-lot authority:

- `boundary_classification = DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX`
- `strategy_cap_overshoot_applied = true`
- `one_lot_fallback_applied = true`
- `one_lot_feasibility_status = PASS`
- `one_lot_quantity > 0`
- `final_allocated_quantity <= one_lot_quantity`
- `target_weight <= safety_hard_cap`
- `safety_hard_cap_preserved != false`
- `safety_margin_after_trade >= 0`
- accepted one-lot buy/new or add weight is positive

Unauthorized new-exposure overshoot is no longer silently capped in PS. It is preserved as invalid evidence and rejected by validation.

## 5. PC Producer

PC/L19/L21S evidence remains the producer. The repair did not add a parallel flag family. It consumes the existing `phase29_l19_lot_resolution` and lot-aware final reallocation evidence.

Existing PC L21S regression still passes, including:

- one-lot BUY_NEW fallback;
- cash shortfall block;
- Safety hard violation block;
- Buy Quality reject / severe capacity zero;
- REENTRY semantic preservation;
- BUY_ADD semantic preservation.

## 6. PS Consumer

Changed:

- `src/ai_fund_lab_v2/strategy/position_sizing.py`

PS now:

- emits `lot_aware_accepted_buy_new_weight` in position rows;
- validates lot-aware Strategy soft-cap overshoot from position output, not only from input rows;
- requires explicit one-lot authority and Safety-hard coherence;
- blocks malformed authority, missing authority, negative Safety margin, failed one-lot feasibility, and multi-lot abuse;
- preserves explicit zero Safety cap emergency handling;
- preserves existing-position ADD drift/reduce/exit protections.

## 7. Runtime Planning Resolution

Runtime Planning needed no production code change. Once PS emits resolved one-lot quantity, RP already maps:

```text
BUY_NEW + RESOLVED_CANDIDATE quantity_delta=100
-> planned_quantity=100
-> quantity_status=RESOLVED_EXECUTABLE
```

Added focused regression for the 78780-style BUY_NEW path.

## 8. Strategy Planning Authority Resolution

Strategy Planning Authority needed no production code change. Once RP has `planned_quantity > 0`, `activate_strategy_planning_authority` creates a pending item and does not emit `strategy_plan_quantity_unresolved`.

Added focused regression:

```text
78780 BUY_NEW planned_quantity=100
-> pending_item_count=1
-> pending item quantity=100
-> source_decision_type=BUY_NEW
```

## 9. Safety Hard Cap Preservation

Safety hard cap remains independent and hard:

- target above 25% still blocks;
- negative `safety_margin_after_trade` blocks;
- one-lot feasibility not `PASS` blocks;
- Safety hard cap is not converted into the normal allocation target.

## 10. 78780 Focused Regression

Added PS fixture:

```text
symbol = 78780
semantic_buy_type = BUY_NEW
normal target = 0.18
one-lot target = 0.243189
one_lot_quantity = 100
safety_hard_cap = 0.25
safety_margin_after_trade = 0.006811
```

Expected and observed:

- PS `producer_result_status=PASS`;
- `target_weight=0.243189`;
- `quantity_delta_candidate=100`;
- `quantity_status=RESOLVED_CANDIDATE`;
- RP `planning_intent=BUY_NEW`, `planned_quantity=100`;
- Strategy Planning Authority `status=PASS`, `pending_item_count=1`.

## 11. Negative Regressions

Added/updated negative coverage:

- target >18% without explicit one-lot authority: BLOCK;
- target >25%: BLOCK;
- `safety_margin_after_trade < 0`: BLOCK;
- `one_lot_feasibility_status != PASS`: BLOCK;
- multi-lot abuse via `final_allocated_quantity > one_lot_quantity`: BLOCK.

Existing L21S coverage preserves:

- Buy Quality reject: zero/no allocation;
- REENTRY qualification failure paths are not bypassed;
- severe capacity remains fail-closed.

## 12. BUY_NEW

BUY_NEW remains BUY_NEW. The repair only authorizes capital expression at the one-lot boundary when PC evidence is coherent.

## 13. REENTRY

REENTRY semantics remain REENTRY. One-lot authority does not convert REENTRY into ordinary BUY_NEW, and L21R3 capacity / prior-exit semantics remain intact.

## 14. BUY_ADD

BUY_ADD remains current-campaign ADD. The existing L21F BUY_ADD soft-cap path was preserved and tightened to carry one-lot authority evidence.

## 15. SELL Regression

SELL / REDUCE / EXIT code paths were not changed. The broad Strategy trio regression includes existing SELL/REDUCE/EXIT cases and passed. The repair does not introduce BUY unresolved coupling into SELL authority.

## 16. Historical Safety Secondary Gap Status

The L21T-A secondary gap remains intentionally out of scope for this implementation:

```text
historical safety_operation_guard latest-path observability split
```

No Production/Demo latest Safety fail-closed behavior was weakened. The current task repaired the direct halt cause, not the non-direct Safety guard observability issue.

## 17. Remaining Gaps

Remaining:

- User-operated fresh validation is still required for the original `2022-08-23` through `2022-09-16` window.
- Historical Safety guard reconciliation remains a later observability/authority cleanup.
- No aggregate capital utilization or PnL claim is made from short regression.

## 18. L21T Fresh Validation Readiness

```text
L21T_FRESH_VALIDATION_READY = YES
```

Validation run by Codex:

```text
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py -k 'phase29_l21t_b or phase29_l21f' -q
10 passed

PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_g_runtime_planning.py -k 'phase29_l21t_b or phase29_l21f' -q
2 passed

PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase23_i_strategy_planning_authority.py -k 'phase29_l21t_b or phase23_bo' -q
2 passed

PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -k 'phase29_l21s or phase29_l19 or phase28_d55_b or phase29_l21d or phase29_l16_sell_reduce_exit' -q
16 passed

PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py -q
215 passed

PYTHONPATH=src python3 -m pytest tests/strategy/test_phase29_l21k_prior_exit_materialization.py tests/strategy/test_phase22_qe_input_materialization.py -q
23 passed

PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase23_i_strategy_planning_authority.py -q
18 passed
```

Static:

```text
py_compile PASS
git diff --check PASS
```

Recommended user-operated fresh validation:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run \
  --profile historical-smoke \
  --start-date 2022-08-23 \
  --end-date 2022-09-16 \
  --fresh
```
