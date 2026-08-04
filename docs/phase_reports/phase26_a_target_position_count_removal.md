# Phase26-A target_position_count Removal

## Judgment

PHASE26_A_TARGET_POSITION_COUNT_REMOVED

## Root Cause

Production Strategy still treated `target_position_count` as a BUY admission and allocation limiter. In BEAR evidence this could materialize as `target_position_count = 1`, then downstream consumers limited target members, zeroed sizing, or blocked new BUYs once current holdings reached that fixed count.

## Producer / Consumer Classification

- Producer / deprecated metadata: `strategy.dynamic_position_count`, `strategy.portfolio_policy`
- Decision consumers repaired: `strategy.portfolio_construction`, `strategy.position_sizing`, `runtime_v2.position_count_authority`, `runtime_v2.planning_submit_feasibility`, `runtime_v2.planning.morning_pipeline`
- Schema compatibility: `strategy.position_sizing` validation no longer requires `target_position_count`
- Config: `configs/strategy/position_sizing.json` no longer describes base allocation as divided by target count
- Observability only: `strategy.observability`, `strategy.shadow_runtime`, `runtime_v2.performance_evaluation.capital_trace`, runtime reports
- Test / fixture only: existing Phase22/23/26 fixture fields remain for compatibility
- Documentation only: historical phase reports and architecture documents still describe previous phase behavior

## Deleted Decision Paths

- `PortfolioConstruction`: removed top-N target member window based on `target_position_count`
- `PortfolioConstruction`: removed `target_position_count == 0` no-investable-capacity zeroing
- `PositionSizing`: removed `target_position_count` unresolved from production decision resolution
- `PositionSizing`: removed `target_count <= 0` zero allocation path
- `Runtime PositionCountAuthority`: removed `selected_dynamic_position_count - current_position_count` as BUY slot authority
- `PlanningSubmitFeasibility`: removed `post_position_count > selected_dynamic_position_count` block
- `MorningPlanning`: removed `len(selected_rows) >= effective_order_limit` candidate loop break
- `PortfolioPolicy`: removed `target_position_count <= 0` from deployment posture

## Preserved Constraints

The repair does not change Candidate Eligibility, Opportunity, Expected Edge, Downside Risk, Market Context, Target Cash Ratio, Single-name Weight Cap, Buying Power, Pending Reservation, Lot Size, Concentration, Safety Hard Maximum, BUY/SELL separation, Accepted Generation Binding, or Temporal Authority.

Safety Hard Maximum remains active and is the only remaining count-style BUY stop. It is not used as a normal target member count.

## Schema Compatibility

`target_position_count` remains readable and observable as deprecated metadata where older artifacts/tests still carry it. It is no longer required by `validate_position_sizing_artifact` and is not consumed as decision authority.

## Changed Files

- `configs/strategy/position_sizing.json`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/portfolio_policy.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/runtime_v2/position_count_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `tests/strategy/test_phase22_j_position_sizing.py`
- `tests/runtime_v2/test_phase26_step2_dynamic_position_count_authority.py`
- `tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py`
- `tests/runtime_v2/test_phase26_step6_submit_guard_authority.py`

## Regression

Compile:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/position_sizing.py src/ai_fund_lab_v2/strategy/portfolio_policy.py src/ai_fund_lab_v2/runtime_v2/position_count_authority.py src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py tests/runtime_v2/test_phase26_step2_dynamic_position_count_authority.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py
```

Result: PASS

Unit / short regression:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase26_step2_dynamic_position_count_authority.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py
```

Result: `82 passed in 2.58s`

Forbidden pattern check:

```bash
rg -n "target_count <= 0|actual_target_position_count_zero|no_investable_capacity|dynamic_position_count_slots_unavailable|BUY would exceed selected_dynamic_position_count|current_holdings_at_or_above_target|\\[:target_member_count\\]|len\\(selected_rows\\) >= effective_order_limit" src tests docs
```

Result: only historical `docs/phase_reports/phase24_b...` documentation references remain.

## Required Case Coverage

- Case 1: Existing holding count equal to `target_position_count` no longer blocks a new eligible BUY. Covered by `test_phase26_step2_current_holdings_at_target_position_count_do_not_block_buy`.
- Case 2: No eligible BUY candidates still produces no purchase. Existing portfolio construction/morning no-signal paths remain; no fill-to-count path was added.
- Case 3: Safety Hard Maximum still blocks new BUY. Covered by `test_phase26_a_safety_hard_maximum_still_blocks_new_buy`.
- Case 4: Cash, exposure, lot size, pending reservation, and single-name cap regressions remain covered by `test_phase24_ht_planning_submit_feasibility.py`, `test_phase22_j_position_sizing.py`, and submit guard tests.

## Residual References

Residual `target_position_count` references are classified as:

- `SCHEMA_COMPATIBILITY_ONLY`: `strategy.position_sizing`, `strategy.portfolio_construction`, `strategy.portfolio_policy`, `runtime_v2.position_count_authority`
- `DEPRECATED_METADATA_ONLY`: `strategy.dynamic_position_count`, `strategy.portfolio_policy`, `strategy.portfolio_construction`, runtime quantity-contract evidence fields
- `OBSERVABILITY_ONLY`: `strategy.dynamic_cash_exposure`, `strategy.observability`, `strategy.shadow_runtime`, `runtime_v2.performance_evaluation.capital_trace`, `scripts/runtime_test.py`
- `TEST_ONLY`: Phase22/23/26 tests and fixtures
- `DOCUMENTATION_ONLY`: historical architecture/phase reports
- `INVALID_DECISION_CONSUMER`: none

## Fresh-run Command For User

Codex did not run fresh-run or multi-day Historical tests.

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --date-from 2023-01-18 \
  --business-days 1 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```
