# Phase31-G99 - G97 Reconsideration Lot Context Propagation Repair

## PRIMARY_JUDGMENT

`PHASE31_G99_G97_RECONSIDERATION_LOT_CONTEXT_PROPAGATION_REPAIRED_ACCEPTED`

G98で確定した G97 authoritative reconsideration row の

```text
PC final canonical allocation
-> G61 lot-aware compatibility
```

境界におけるlot context欠落のみを修理した。

## Repair Summary

変更点は既存canonical contextの伝播に限定した。

1. G95/G97 residual reconsideration shadow rowへ、元competitorが持つ既存 `lot_sizing_context` を保持するようにした。
2. G97 authoritative binding rowへ、shadow rowの `lot_sizing_context` をそのまま伝播するようにした。
3. G61 compatibility row作成時に、通常competitor contextだけでなく、final canonical allocation row側に保持された context も読むようにした。
4. `portfolio_value` basis は既存の `target_weight_authority.low_price_risk_allocation_authority.current_authoritative_portfolio_equity` から伝播した。

新しいlot authority、synthetic quantity、hardcoded lot policy、Market Quality / Risk Pacing / ranking / ADD / Safety semanticsの変更はない。

## Files Changed

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase31_g99_reconsideration_lot_context_propagation.py`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

## Existing Fresh-Run Producer-Equivalent Evaluation

Target run:

`runtime-test-historical-extended-smoke-20260824T121719329586Z`

Existing fresh-run artifacts were used read-only. No fresh-run/resume/replay/Historical was executed.

Before G99, G98 found persisted actual behavior:

```text
G97 positive authoritative rows = 142
final canonical allocation rows = 142
LOT_EXECUTABLE_COMPATIBLE = 0
INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED = 142
PS positive quantity = 0
Runtime BUY/ADD = 0
```

After G99 producer-equivalent re-evaluation on the same existing artifacts:

```text
G97 positive rows = 142
LOT_EXECUTABLE_COMPATIBLE = 88
INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED = 0
legitimate LOT/CAP infeasible = 54
PS theoretical nonzero = 88
remaining zero and reasons = 54 LOT_INFEASIBLE_RESIDUAL_REQUIRED
```

This proves the universal missing-context failure is repaired. Rows still remain zero when real lot/capital constraints make them infeasible.

## Mandatory Anchor Results

| Date | Symbol | Authorized weight | G61 result after G99 | Theoretical qty | Explanation |
|---|---:|---:|---|---:|---|
| 2023-03-22 | 94320 | 0.030303 | LOT_EXECUTABLE_COMPATIBLE | 200 | Context propagated; executable |
| 2023-04-07 | 83060 | 0.035238 | LOT_INFEASIBLE_RESIDUAL_REQUIRED | 0 | Real one-lot weight exceeds allocation |
| 2023-04-07 | 77760 | 0.035238 | LOT_INFEASIBLE_RESIDUAL_REQUIRED | 0 | Real one-lot weight exceeds allocation |
| 2023-04-07 | 44440 | 0.035238 | LOT_INFEASIBLE_RESIDUAL_REQUIRED | 0 | Real one-lot weight exceeds allocation |
| 2023-04-14 | 94320 | 0.011516 | LOT_EXECUTABLE_COMPATIBLE | 100 | Context propagated; executable |
| 2023-04-18 | 59350 | 0.050000 | LOT_INFEASIBLE_RESIDUAL_REQUIRED | 0 | Real one-lot weight exceeds allocation |

The 2023-04-07 and 2023-04-18 anchors no longer fail because G97 omitted context. They fail closed for legitimate lot infeasibility.

## Preservation Checks

```text
2023-04-05 reconsidered rows remain Cash = PASS
2023-04-06 reconsidered rows remain Cash = PASS
2023-04-06 67310 remains Safety terminal = PASS
known G80 weak-tail resurrection count = 0
ADD competition preserved = PASS
existing positive allocations preserved = PASS
no synthetic quantity = PASS
no PS/Runtime priority redecision = PASS
capital reconciliation = PASS
```

## SoT Update

Updated `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md` to make the permanent G99 contract explicit:

```text
RESIDUAL_RECONSIDERATION_LOT_CONTEXT_PROPAGATION_OWNER = PORTFOLIO_CONSTRUCTION
RESIDUAL_RECONSIDERATION_SYNTHETIC_LOT_CONTEXT = NO
```

G97 reconsideration rows that enter `canonical_multi_allocation_deployment_set.security_allocations[]` must carry the same existing canonical lot-sizing context as ordinary security allocations. Missing genuine context remains fail-closed.

## Focused Regression

Command run:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m pytest tests/strategy/test_phase31_g99_reconsideration_lot_context_propagation.py tests/strategy/test_phase31_g97_residual_reconsideration_authoritative_binding.py tests/strategy/test_phase31_g95_residual_reconsideration_shadow.py tests/strategy/test_phase31_g90_cash_preferred_aggregate_resolver.py tests/strategy/test_phase31_g86_cash_preferred_participation_deferral.py tests/strategy/test_phase31_g83_bootstrap_cash_preference_partition.py tests/strategy/test_phase31_g81_opportunity_aware_security_cash_partition.py tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py tests/strategy/test_phase31_g62_position_sizing_g61_binding.py tests/strategy/test_phase31_g63_runtime_executable_binding.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py tests/strategy/test_phase22_e_portfolio_construction.py
```

Result:

```text
176 passed
```

## Compile / Diff Check

```text
PY_COMPILE = PASS
GIT_DIFF_CHECK = PASS
```

## Required Final Judgment

```text
G97_RECONSIDERATION_LOT_CONTEXT_PROPAGATION_REPAIRED = YES
G90_CHANGED = NO
G97_SEMANTICS_CHANGED = NO
SAFETY_CHANGED = NO
PS_QUANTITY_AUTHORITY_CHANGED = NO
RUNTIME_PRIORITY_CHANGED = NO
SYNTHETIC_LOT_CONTEXT_CREATED = NO
AUTHORITATIVE_CAPITAL_RECONCILIATION = PASS
G80_WEAK_TAIL_RESURRECTION_COUNT = 0
G99_ACCEPTED = YES
```

## Run Handling

```text
FRESH_RUN_EXECUTED_BY_CODEX = NO
RESUME_EXECUTED_BY_CODEX = NO
REPLAY_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
FUTURE_INPUT_COUNT = 0
HISTORICAL_OUTCOME_INPUT_COUNT = 0
```
