# Phase28-D25: PM Intent-Preserving SELL Authority Implementation

## Executive Summary

Primary Judgment:

```text
PHASE28_D25_PM_INTENT_PRESERVING_SELL_AUTHORITY_IMPLEMENTED_SHORT_VALIDATION_PASS
```

Supporting Judgments:

```text
PM_HOLD_TO_NO_SELL_CONFIRMED
PM_ADD_TO_BUY_ADD_CONFIRMED
PM_REDUCE_TO_SELL_REDUCE_CONFIRMED
PM_EXIT_TO_SELL_EXIT_CONFIRMED
PM_UNRESOLVED_TO_NO_SELL_EXIT_CONFIRMED
```

Fresh Test Entry Decision:

```text
READY
```

D25 implemented the D24 authority contract only:

```text
FULL_LIQUIDATION_ALLOWED =
PM_EXIT
OR
EXPLICIT_HIGHER_PRIORITY_LIQUIDATION_AUTHORITY
```

No config, schema, threshold, PM inference, PM threshold, Expected Edge, Incremental Investment Value, Opportunity Cost, re-entry, D21, hysteresis, cash reserve, target exposure, position count, BUY Quality, Safety policy, Corporate Action policy, Submit Guard, or Broker normalizer change was made. No resume, fresh run, or long historical run was executed.

## Scope

Implementation scope:

```text
src/ai_fund_lab_v2/strategy/runtime_planning.py
```

Test scope:

```text
tests/strategy/test_phase22_g_runtime_planning.py
tests/runtime_v2/test_phase23_i_strategy_planning_authority.py
```

The repair is one Authority Contract change, not a new SELL strategy.

## Accepted D24 Contract

D24 fixed the desired mapping:

| PM action | D25 behavior |
|---|---|
| HOLD | no implicit `SELL_EXIT` |
| ADD | `BUY_ADD` when executable; no `SELL_EXIT` from ADD alone |
| REDUCE | `SELL_REDUCE` when partial executable; no silent `SELL_EXIT` escalation |
| EXIT | `SELL_EXIT` preserved |
| UNRESOLVED | review/no-order/preserve; no implicit `SELL_EXIT` |

`target_quantity = 0` remains a derived quantity, not full liquidation authority.

## Pre-Implementation Authority Audit

The pre-D25 Runtime Planning mapping allowed:

```text
quantity_delta < 0
+
target_quantity == 0
→ SELL_EXIT
```

without checking whether the upstream action was PM `EXIT`.

Existing higher-priority sources were audited. Safety, Emergency, and Human Review code paths expose block/review/permission concepts, but no existing Runtime Planning input carries explicit full-liquidation authority from those sources. D25 therefore integrates only PM `EXIT` and does not invent a new higher-priority liquidation authority.

Corporate Action fact alone remains not a liquidation authority.

## Changed Files

```text
src/ai_fund_lab_v2/strategy/runtime_planning.py
tests/strategy/test_phase22_g_runtime_planning.py
tests/runtime_v2/test_phase23_i_strategy_planning_authority.py
```

## Full Liquidation Authority Contract

Runtime Planning now materializes per-plan provenance:

```text
source_pm_action
source_pm_decision_id
source_pm_reason_codes
full_liquidation_authority_present
full_liquidation_authority_source
```

The new helper:

```text
_full_liquidation_authority(...)
```

sets:

```text
full_liquidation_authority_present = true
full_liquidation_authority_source = PM_EXIT
```

only when the resolved source PM action is `EXIT`.

The guarded mapping is now:

```text
negative delta
+
target_quantity == 0
+
PM_EXIT authority
→ SELL_EXIT
```

```text
negative delta
+
target_quantity == 0
+
no PM_EXIT authority
→ UNRESOLVED / REVIEW_REQUIRED
```

## PM HOLD

Focused validation:

```text
test_phase28_d25_runtime_planning_blocks_target_zero_sell_exit_without_pm_exit_authority
```

Result:

```text
PASS
```

PM `HOLD` with target quantity zero and negative delta no longer emits `SELL_EXIT`. It becomes `UNRESOLVED` with:

```text
planning_conflict_review:full_liquidation_authority_missing:<symbol>
```

## PM ADD

Result:

```text
PASS
```

The existing D19 / Phase28-C chain remains intact:

```text
PM ADD
→ Strategy PM ADD
→ Portfolio Construction ADD/INCREASE
→ positive quantity delta
→ BUY_ADD
```

D25 does not create any ADD-to-SELL path.

## PM REDUCE

Focused validation:

```text
test_phase28_d25_runtime_planning_maps_pm_reduce_to_sell_reduce_not_exit
test_phase28_d25_pm_reduce_rounding_zero_does_not_silently_escalate_to_sell_exit
```

Result:

```text
PASS
```

PM `REDUCE` with positive remaining target quantity maps to `SELL_REDUCE`. PM `REDUCE` with target quantity zero does not silently escalate to `SELL_EXIT`; it becomes review-required unresolved.

## PM EXIT

Focused validation:

```text
test_phase28_d25_runtime_planning_preserves_pm_exit_to_sell_exit
```

Result:

```text
PASS
```

PM `EXIT` remains the normal full liquidation path:

```text
PM EXIT
→ target quantity zero
→ SELL_EXIT
```

## PM UNRESOLVED

Focused validation:

```text
test_phase28_d25_pm_unresolved_target_zero_does_not_generate_sell_exit
```

Result:

```text
PASS
```

`UNRESOLVED` is not a PM decision and is not treated as `EXIT`.

## Portfolio Construction

No Portfolio Construction implementation change was required in D25. The existing mapping remains:

```text
HOLD   -> RETAIN / MAINTAIN
ADD    -> RETAIN / INCREASE
REDUCE -> REDUCE_CANDIDATE / DECREASE
EXIT   -> REMOVE_CANDIDATE / REMOVE
```

D25 enforces the final full-liquidation authority at Runtime Planning so ordinary target-zero artifacts cannot become executable `SELL_EXIT` without PM `EXIT`.

## Position Sizing

No Position Sizing formula or threshold was changed. D25 does not make Position Sizing an EXIT authority.

Position Sizing may still produce target quantity and quantity delta, but Runtime Planning now requires PM `EXIT` before mapping a full negative delta to `SELL_EXIT`.

## Runtime Planning

Runtime Planning remains a pure mapper. The implemented change is the final `SELL_EXIT` guard:

```text
target_quantity == 0
and quantity_delta < 0
and full_liquidation_authority_present == false
→ UNRESOLVED / REVIEW_REQUIRED
```

## Higher-Priority Liquidation Authority

Status:

```text
PASS_NO_NEW_AUTHORITY_ADDED
```

D25 did not integrate Safety/Emergency/Human Review as full-liquidation sources because no existing Runtime Planning input provides explicit full-liquidation authority from those sources. They remain block/review/permission authorities outside this Strategy mapper.

## Valid Loss-Cut Preservation

Representative PM `EXIT` fixture remains:

```text
PM EXIT -> SELL_EXIT
```

Result:

```text
PASS
```

The D23 valid loss-cut7 semantics are preserved.

## D19 / Phase28-C Regression

Result:

```text
PASS
```

Covered:

- same-day PM ADD wiring
- Strategy PM ADD propagation
- Portfolio Construction ADD bridge
- Position Sizing positive quantity delta
- Runtime Planning `BUY_ADD`

## D14 / D16 / D8 / D3 Regression

Result:

```text
PASS
```

The D14 listed-info fixture was updated from PM `HOLD` to PM `EXIT` so it continues testing canonical Strategy SELL listed-info without depending on the now-forbidden HOLD-to-SELL_EXIT path.

D16/D8/D3 pending/listed-info regressions passed.

## BUY / SELL Independence

Result:

```text
PASS
```

BUY-side tests remain passing, and SELL validity now depends on sell-side PM authority. Opportunity no-buy reason still blocks BUY only; valid PM `EXIT` / `REDUCE` paths remain independent.

## Short Regression

Command:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_d25 python3 -m pytest -q tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase22_d_position_management.py tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_c_canonical_add_bridge_increases_existing_target_weight_when_incremental_evidence_passes tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_c_canonical_add_bridge_fails_closed_when_expected_edge_evidence_missing tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_target_weight_bridge_reaches_positive_quantity_delta tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_lot_rounding_zero_delta_is_explicit tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase28_d14_strategy_sell_30410_uses_canonical_listed_info_without_opportunity tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py
```

Result:

```text
97 passed
```

## Compile / JSON Validation

Compile:

```text
PASS
```

JSON validation:

```text
PASS
```

## Architecture Conformance

Runtime Authority violation:

```text
false
```

Performance semantics changed:

```text
false
```

No PM inference, thresholds, Expected Edge, re-entry, hysteresis, cash policy, Safety policy, Corporate Action policy, Submit Guard, or Broker behavior was changed.

## Open Gaps

- No fresh 100BD was executed in D25.
- Higher-priority liquidation sources beyond PM `EXIT` were not integrated because no existing Runtime Planning input carries explicit full-liquidation authority.
- The next fresh run must quantify PM `HOLD/ADD/REDUCE/EXIT` mappings and re-entry metrics.

## Fresh Test Contract

Fresh run must collect:

```text
PM HOLD -> SELL_EXIT
PM ADD -> SELL_EXIT
PM REDUCE -> SELL_EXIT
PM EXIT -> SELL_EXIT

PM ADD -> BUY_ADD
PM REDUCE -> SELL_REDUCE

Re-entry count
1BD re-entry count

avg cash ratio
avg invested ratio

total return
max drawdown
profit factor
```

## Final Judgment

```text
Primary Judgment:
PHASE28_D25_PM_INTENT_PRESERVING_SELL_AUTHORITY_IMPLEMENTED_SHORT_VALIDATION_PASS

Supporting Judgments:
PM_HOLD_TO_NO_SELL_CONFIRMED
PM_ADD_TO_BUY_ADD_CONFIRMED
PM_REDUCE_TO_SELL_REDUCE_CONFIRMED
PM_EXIT_TO_SELL_EXIT_CONFIRMED
PM_UNRESOLVED_TO_NO_SELL_EXIT_CONFIRMED

Fresh Test Entry Decision:
READY

Implemented Repair:
Runtime Planning Full Liquidation Authority guard requiring PM_EXIT before SELL_EXIT when target_quantity==0 and quantity_delta<0

Full Liquidation Authority Contract:
FULL_LIQUIDATION_ALLOWED = PM_EXIT OR EXPLICIT_HIGHER_PRIORITY_LIQUIDATION_AUTHORITY

Runtime Authority violation:
false

Performance semantics changed:
false

Config changed:
false

Schema changed:
false

Threshold changed:
false

Resume executed:
false

Fresh run executed:
false

Long Historical executed:
false
```

## Next Phase

Recommended next phase:

```text
Phase28-D26 Fresh Runtime Acceptance Audit
```

or user-run fresh 100BD acceptance evidence collection.

## Deliverables

```text
docs/phase_reports/phase28_d25_pm_intent_preserving_sell_authority_implementation.md
reports/phase_reports/phase28_d25_pm_intent_preserving_sell_authority_implementation.json
reports/phase28_d25_pm_intent_preserving_sell_authority_implementation/
```
