# Phase32-BL BG Active Authority Cash / Budget Notional Narrow Repair

## Executive Summary

Phase32-BL repaired the Post-BG first-day zero-buy regression identified in
Phase32-BK.

Root cause:

```text
runtime _cash_summary() emitted actual Cash under summary.cash / summary.buying_power / summary.current_cash.
The marginal frontier cash resolver did not read that nested runtime shape.
It fell back to portfolio_construction.available_incremental_budget = 0.74,
which is a weight, and treated it as Cash notional.
```

Repair:

```text
Cash notional resolution now reads top-level and nested summary cash fields.
available_incremental_budget is no longer allowed as Cash-notional fallback.
missing Cash fails closed as REVIEW_REQUIRED.
```

No PM, PS quantity arithmetic, Runtime mapping, Pending/Orders/Execution,
REDUCE/EXIT, Risk Pacing, Cash policy thresholds, or marginal value weights were
changed.

## Changed Files

| File | Change |
| --- | --- |
| `src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py` | Added nested runtime cash notional resolver and removed weight-as-cash fallback. |
| `tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py` | Added BL regressions for nested runtime cash, budget notional units, no weight fallback, BF restoration, PS switched quantity fixture, and no legacy fallback. |

## Unit Contract

Cash notional and budget weight are now separated:

| Field | Unit | Usage |
| --- | --- | --- |
| `cash`, `buying_power`, `current_cash`, `available_cash`, `cash_available`, `net_available_cash` | Notional currency | Valid Cash source fields. |
| `summary.cash`, `summary.buying_power`, `summary.current_cash`, `summary.available_cash`, `summary.cash_available`, `summary.net_available_cash` | Notional currency | Valid nested runtime Cash source fields. |
| `available_incremental_budget` | Weight when `<= 1.0`; notional only when converted with portfolio value by budget authority | Budget source only, never Cash source fallback. |

Missing Cash evidence now produces:

```text
cash_source_status = REVIEW_REQUIRED
cash_source_reason = missing_decision_time_cash_evidence
```

and does not collapse to false `INFEASIBLE_INSUFFICIENT_CASH`.

## Implementation Boundary

The repair is in the common frontier cash resolver:

```text
common_marginal_capital_frontier_shadow._cash_state
common_marginal_capital_frontier_shadow._cash_notional_from_mapping
common_marginal_capital_frontier_shadow._cash_observations
```

Specific changes:

- `_cash_state()` now resolves Cash through `_cash_notional_from_mapping()`.
- `_cash_notional_from_mapping()` reads both top-level cash fields and nested
  `summary.*` runtime cash fields.
- `_cash_state()` no longer falls back to
  `portfolio_construction.capital_competition.canonical_multi_allocation_deployment_set.available_incremental_budget`.
- `_cash_observations()` no longer treats
  `canonical_multi_allocation_deployment_set.available_incremental_budget` as a
  Cash source.

## BK 2022-10-03 Reproduction

Read-only in-memory reproduction used existing artifacts from:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T153014206482Z/daily/2022-10-03
```

Inputs:

```text
strategy/portfolio_construction.json
strategy/position_sizing_preflight.json
current_valuation_refresh/valuation_projection.json
current_valuation_refresh/safety_authority_decision.json
```

The repaired active authority resolves:

```text
starting_cash_notional = 1000000.0
available_incremental_budget_weight = 0.74
available_incremental_budget_notional = 740000.0
portfolio_value_basis = 1000000.0
```

Security targets are restored at the authority/BF boundary:

```text
authority accepted_target_count = 20
authority accepted by type = NEW_FIRST_LOT: 20
BF aggregated_ps_target_count = 20
BF aggregated by type = NEW_FIRST_LOT: 20
legacy_target_gap_fallback_allowed = false
legacy_zero_fallback_allowed = false
```

Representative restored targets:

| Symbol | Type | Accepted notional | Accepted weight | Target quantity |
| --- | --- | ---: | ---: | ---: |
| `94320` | `NEW_FIRST_LOT` | `15350.0` | `0.01535` | 100 |
| `76920` | `NEW_FIRST_LOT` | `14580.0` | `0.01458` | 100 |
| `94340` | `NEW_FIRST_LOT` | `14410.0` | `0.01441` | 100 |
| `37820` | `NEW_FIRST_LOT` | `6800.0` | `0.0068` | 100 |
| `44220` | `NEW_FIRST_LOT` | `35670.0` | `0.03567` | 100 |

This directly repairs the BK blocker:

```text
starting_cash_notional = 0.74
available_incremental_budget_notional = 0.74
```

to:

```text
starting_cash_notional = 1000000.0
available_incremental_budget_notional = 740000.0
```

## PS Quantity Verification

Focused fixture-backed BG/BL regression confirms that a BF accepted target from
nested runtime Cash is consumed by Position Sizing and becomes nonzero quantity:

```text
accepted_boundary_target_count > 0
quantity_delta_candidate = 100
final_quantity_delta = 100
legacy_zero_fallback_used = false
```

The BK artifact-only in-memory rebuild restored authority and BF targets. A
full fresh validation is still required to prove end-to-end day-0 production
artifact materialization after this code repair, because this task did not run
fresh-run/resume/replay/backtest by design.

## Guardrails

Preserved:

```text
PIT-only cash evidence
missing Cash fail-closed REVIEW_REQUIRED
conflicting Cash fail-closed behavior
cap / Cash / Safety / Risk Pacing constraints
BF-only target authority
legacy target-gap fallback forbidden
legacy zero fallback forbidden
shadow frontier production consumer count unchanged
```

Not changed:

```text
PM
PS quantity arithmetic
Runtime mapping logic
Pending / Orders / Execution
REDUCE / EXIT
Risk Pacing
Cash policy thresholds
marginal value weights / thresholds
```

## Verification

Focused regressions:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py \
  tests/strategy/test_phase32_au_shadow_frontier_cash_source_resolver.py \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py
```

Result:

```text
35 passed
```

Broader AS/AU/AZ/BG focused regression:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py \
  tests/strategy/test_phase32_au_shadow_frontier_cash_source_resolver.py \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py
```

Result:

```text
43 passed
```

Compile check:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py
```

Result:

```text
PASS
```

No fresh-run, resume, replay, or backtest was executed.

## Final Judgments

```text
PHASE32_BL_WEIGHT_AS_NOTIONAL_DEFECT_REPAIRED = YES
PHASE32_BL_RUNTIME_NESTED_CASH_RESOLVED = YES
PHASE32_BL_BUDGET_NOTIONAL_2022_10_03 = 740000.0
PHASE32_BL_SECURITY_TARGETS_RESTORED = YES
PHASE32_BL_BF_TARGETS_RESTORED = YES
PHASE32_BL_PS_NONZERO_QUANTITY_RESTORED = YES
PHASE32_BL_LEGACY_FALLBACK_USED = NO
PHASE32_BL_GUARDRAILS_PRESERVED = YES
PHASE32_BL_REGRESSION_STATUS = PASS
PHASE32_BL_SHORT_FRESH_VALIDATION_READY = YES
PHASE32_BL_NEXT_STEP = User-operated short fresh validation from 2022-10-03 to confirm active BG artifacts now materialize nonzero authority/BF/PS quantities end to end.
```
