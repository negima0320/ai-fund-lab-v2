# Phase29-E Lot-First Capital Recycling Implementation

Status:

```text
IMPLEMENTED
SHORT REGRESSION BLOCKED BY EXISTING SELL REGRESSION
NO 100BD READY GATE
```

Primary Judgment:

```text
PHASE29_E_LOT_FIRST_CAPITAL_RECYCLING_IMPLEMENTED_SHORT_REGRESSION_BLOCKED_BY_EXISTING_SELL_REGRESSION
```

## 1. Scope

Phase29-E implemented the Phase29-D selected architecture:

```text
Design B - Lot-First Feasibility-Aware Rebatch
```

No fresh run, resume, 100BD, long Historical, config change, schema change,
investment policy change, concentration cap change, Runtime artifact mutation,
Pending mutation, Submit/Execution change, or SELL path change was performed.

Evidence:

```text
reports/phase29_e_lot_first_capital_recycling_implementation/implementation_summary.json
reports/phase29_e_lot_first_capital_recycling_implementation/changed_files.json
reports/phase29_e_lot_first_capital_recycling_implementation/regression_results.json
reports/phase29_e_lot_first_capital_recycling_implementation/invariant_results.json
reports/phase29_e_lot_first_capital_recycling_implementation/remaining_risks.json
```

## 2. Changed Files

Production:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
src/ai_fund_lab_v2/strategy/position_sizing.py
```

Tests:

```text
tests/strategy/test_phase22_e_portfolio_construction.py
tests/strategy/test_phase22_j_position_sizing.py
```

Docs/evidence:

```text
docs/phase_reports/phase29_e_lot_first_capital_recycling_implementation.md
reports/phase29_e_lot_first_capital_recycling_implementation/
docs/01_requirements/phase_roadmap.md
```

## 3. Implementation Summary

Position Sizing preflight now includes request-positive BUY-side participants
even when first-pass PC budget reconciliation trimmed their draft target to
zero. This is required because Phase29-C showed many BUY_NEW and ADD rows were
positive at request time but invisible to final lot-aware allocation after
first-pass trimming.

Additive preflight evidence now includes:

```text
requested_basis_notional
target_basis_notional
concentration_cap
concentration_headroom_weight
one_lot_post_trade_weight
lot_first_feasibility_classification
```

Portfolio Construction final lot-aware reallocation now treats original
request-positive ADD and BUY_NEW rows as common rebatch participants. It can
skip infeasible higher-priority rows and recycle deployable capital to later
eligible executable rows without expanding the candidate universe or lowering
quality floors.

Additive PC evidence now includes:

```text
rebatch_allocations
lot_first_rebatch_enabled
lot_first_rebatch_candidate_count
residual_cash_reason
capital_conservation
per-member lot_first_rebatch_* fields
```

## 4. Preserved Contracts

| Contract | Result |
|---|---|
| D61 current-baseline ADD increment | PRESERVED |
| D69 signed `target_weight_change` observability | PRESERVED |
| D55-A quality/Expected Edge/Incremental Value floor | PRESERVED |
| No forced ADD | PRESERVED |
| No forced BUY_NEW | PRESERVED |
| ADD/BUY_NEW common competition | IMPLEMENTED |
| 0.18 concentration cap | UNCHANGED |
| Market Context / target cash | UNCHANGED |
| Safety / Broker / Corporate Action gates | NOT WEAKENED |
| Pending / Submit / Execution boundary | UNCHANGED |
| SELL / REDUCE / EXIT path | CODE UNCHANGED |
| legacy `max_positions=5` / legacy max exposure | NOT REACTIVATED |
| Production-common behavior | YES |

## 5. New Focused Regression

Focused Phase29-E and related PC/PS regression:

```text
14 passed, 112 deselected
```

Covered:

```text
lot skip -> next good BUY_NEW
low-quality non-participant is not bought for cash deployment
ADD wins common competition when higher priority
BUY_NEW wins common competition when higher priority
concentration block recycles to another symbol
same-symbol concentration bypass prohibited
deterministic input-order behavior
request-positive zero-accepted BUY_NEW preflight
ADD concentration-headroom preflight classification
D55-B / D61 / D69 related PS behavior
```

## 6. Broad Short Regression

Executed broad short regression:

```text
tests/strategy/test_phase22_e_portfolio_construction.py
tests/strategy/test_phase22_j_position_sizing.py
tests/strategy/test_phase22_g_runtime_planning.py
tests/runtime_v2/test_phase23_i_strategy_planning_authority.py
tests/runtime_v2/test_phase23_ab_no_order_submit_guard.py
tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
tests/runtime_v2/test_phase17_bv9_historical_sell_quantity_authority.py
tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py
tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py
```

Result:

```text
229 passed
1 failed
```

Failing test:

```text
tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py::test_phase19_bt_reduce_pending_sell_conflict_review_required
```

Single-test reproduction:

```text
Expected: REVIEW_REQUIRED
Observed: PASS
```

Causality assessment:

```text
Phase29-E changed only Strategy Portfolio Construction, Strategy Position
Sizing, and related Strategy tests. It did not modify SELL Planning, Pending,
Submit, Execution, or Runtime v2 SELL code. Because Phase29-E explicitly
prohibits opportunistic SELL-path repair, this failure is recorded as an
unresolved mandatory regression blocker rather than repaired in this task.
```

## 7. Compile

```text
PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  src/ai_fund_lab_v2/strategy/position_sizing.py

PASS
```

## 8. Acceptance Result

| Criterion | Result |
|---|---|
| D61 preserved | PASS |
| D69 preserved | PASS |
| quality floor preserved | PASS |
| no forced investment | PASS |
| ADD/BUY_NEW common competition | PASS |
| lot skip capital recycling | PASS |
| 0.18 cap preserved | PASS |
| Safety preserved | PARTIAL PASS |
| Market Context preserved | PASS / unchanged |
| SELL path unchanged | CODE UNCHANGED |
| Mandatory SELL regression | FAIL |
| Capital conservation | PASS |
| Deterministic allocation | PASS |
| legacy max_positions not reactivated | PASS |
| Production-common only | PASS |

Because the mandatory SELL regression set is not green, Phase29-E must not be
classified as 100BD-ready yet.

## 9. Remaining Risks

1. Mandatory SELL regression blocker:
   `test_phase19_bt_reduce_pending_sell_conflict_review_required` fails in the
   existing SELL path. Resolve or explicitly waive this before user-operated
   100BD validation.
2. Long-run capital/risk effects remain unknown because Codex did not run
   fresh/resume/100BD/historical validation.
3. Lot-first rebatch is a moderate PC semantic change. Short PC/PS/Runtime
   tests pass, but 100BD evidence is still required for capital deployment,
   concentration, drawdown, and return attribution.

## 10. User-Operated Next Step

Do not run 100BD until the mandatory SELL regression blocker is handled.

Recommended next task:

```text
Phase29-E2 Mandatory SELL Regression Gate Repair or Waiver Before 100BD Validation
```

