# Phase32-BC Budget-Bounded Frontier Acceptance Implementation

## Executive Summary

Phase32-BC implemented budget-bounded acceptance inside:

```text
canonical_marginal_capital_frontier_authority.v1
```

The implementation remains consumer-disabled. No Position Sizing, Runtime,
Pending, Orders, Execution, Safety, PM, REDUCE, EXIT, Cash policy, Risk
Pacing, threshold, config, model, fresh-run, resume, replay, or backtest path
was changed.

Added authority sections:

- `allocation_budget_authority`
- `frontier_acceptance_sequence`
- `authorized_cash_allocation`
- `capital_conservation`
- `budget_stop_reasons`

The previous AZ broad loop accepted every individually feasible security whose
value exceeded Cash optionality. BC replaces that with a finite-budget loop:

```text
existing PC/Portfolio Policy budget
-> common NEW / REENTRY / ADD / Cash frontier
-> accept one lot at a time in marginal value order
-> recompute remaining budget/Cash/headroom
-> send residual budget to explicit Cash
```

## Required Inputs

Read:

- `docs/phase_reports/phase32_bb_production_capital_allocation_budget_acceptance_boundary_design.md`
- `docs/phase_reports/phase32_ba_marginal_capital_authority_dual_read_acceptance.md`
- `docs/phase_reports/phase32_az_production_shaped_marginal_capital_value_authority_implementation.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

## Implementation

Changed module:

```text
src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py
```

Budget source priority:

```text
1. portfolio_construction.available_incremental_budget
2. portfolio_construction.capital_competition.canonical_multi_allocation_deployment_set.available_incremental_budget
3. portfolio_construction.incremental_budget_reconciliation.available_incremental_budget
4. embedded Portfolio Policy incremental_capital_budget_envelope gross exposure headroom
```

Primary production-shaped source remains existing authority, not a new
arbitrary budget. Missing or conflicting top-priority budget evidence fails
closed as `REVIEW_REQUIRED`.

## Acceptance Sequence

`frontier_acceptance_sequence[]` records each allocation step:

- `step_index`
- `remaining_budget_before`
- `remaining_budget_notional_before`
- `remaining_cash_before`
- `candidate_pool_hash`
- `candidate_pool_count`
- `top_candidate_id`
- `top_candidate_type`
- `top_candidate_value`
- `cash_candidate_id`
- `cash_value`
- `next_alternative_id`
- `next_alternative_value`
- `decision`
- `accepted_incremental_weight`
- `accepted_incremental_notional`
- `remaining_budget_after`
- `remaining_budget_notional_after`
- `remaining_cash_after`
- `reason_codes`

Security acceptance stops when:

- the top security cannot beat Cash optionality;
- the next security value is ambiguous;
- the next executable lot exceeds remaining allocation budget;
- no feasible security candidate remains;
- the budget is exhausted.

## ADD Recompetition

ADD remains lot-by-lot. Later lots must re-enter common competition:

```text
ADD #1 accepted
-> remaining budget/Cash/headroom recomputed
-> ADD #2 can enter the next candidate pool
-> ADD #2 accepted only if it wins that next step
```

BC does not add fixed ADD lot count, fixed ADD multiplier, fixed share count,
or fixed position count. The engineering generation limit inherited from AS/AZ
remains non-investment observability scaffolding.

## Explicit Cash / Conservation

Any unallocated budget is emitted as:

```text
authorized_cash_allocation
```

`capital_conservation` verifies:

```text
security_allocation + authorized_cash_allocation = available_incremental_budget
```

This keeps Cash first-class. It is not treated as unexplained residual.

## Architecture SoT Updates

Updated:

- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

The SoT now records BC's budget-bounded authority sections, budget source
priority, explicit Cash allocation, capital conservation, and consumer-disabled
boundary.

## Focused Regression

Command:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py tests/strategy/test_phase32_au_shadow_frontier_cash_source_resolver.py
```

Result:

```text
28 passed in 0.13s
```

Compile check:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py
```

Result: PASS.

Covered cases:

- finite budget narrows multiple feasible candidates;
- ADD #1 accepted then ADD #2 re-enters competition;
- budget exhaustion;
- Cash wins residual allocation;
- capital conservation PASS;
- conflicting budget source fail-closed;
- missing budget authority fail-closed;
- deterministic rerun;
- PS-compatible target gaps;
- production consumer count remains 0;
- AS/AU shadow and Cash resolver regressions still pass.

## Read-Only Actual-Artifact Characterization

The builder was applied in memory only to the BA run:

```text
runtime-test-historical-extended-smoke-20260828T000823285458Z
```

No files were written to the run directory.

Coverage:

| Metric | Value |
| --- | ---: |
| Characterized days | 50 |
| Coverage start | `2022-10-03` |
| Coverage end | `2022-12-14` |
| Authority generation PASS | 50 |
| Allocation budget PASS | 50 |
| Capital conservation PASS | 50 |
| Determinism mismatches | 0 |
| Forbidden future/outcome fields | 0 |

Accepted target comparison:

| Metric | BA pre-BC | BC budget-bounded |
| --- | ---: | ---: |
| Accepted targets | 490 | 301 |
| `NEW_FIRST_LOT` targets | 262 | 182 |
| `REENTRY_FIRST_LOT` targets | 134 | 26 |
| `ADD_NEXT_LOT` targets | 94 | 93 |

ADD accepted lots:

| Lot | Accepted |
| --- | ---: |
| lot #1 | 32 |
| lot #2 | 31 |
| lot #3 | 30 |

Budget stop / Cash:

| Metric | Value |
| --- | ---: |
| Acceptance sequence rows | 351 |
| `ACCEPT_INCREMENTAL_TARGET` steps | 301 |
| `STOP_BUDGET_EXHAUSTED_TO_CASH` steps | 50 |
| Days with explicit Cash allocation | 50 |
| Average authorized Cash weight | 0.0284101313 |
| Average available budget weight | 0.1708745689 |

Guardrails on the actual artifact sample:

| Guardrail | Count |
| --- | ---: |
| Cap blocked candidates | 279 |
| Cash blocked candidates | 426 |
| Safety blocked candidates | 0 |
| Risk Pacing blocked candidates | 0 |
| No-loss-averaging blocked candidates | 0 |

The actual 50BD sample confirms that BC materially narrows BA's over-broad
target surface using a finite budget boundary while preserving ADD
materialization, Cash allocation, and capital conservation.

## Production Boundary

The artifact remains disabled:

```text
production_consumer_enabled = false
production_consumer_count = 0
feeds_position_sizing = false
feeds_runtime_planning = false
feeds_pending = false
feeds_orders = false
feeds_execution = false
feeds_safety_authority = false
production_behavior_changed = false
```

## Final Judgments

```text
PHASE32_BC_ALLOCATION_BUDGET_AUTHORITY_IMPLEMENTED = YES
PHASE32_BC_FRONTIER_ACCEPTANCE_SEQUENCE_IMPLEMENTED = YES
PHASE32_BC_EXPLICIT_CASH_ALLOCATION = YES
PHASE32_BC_CAPITAL_CONSERVATION = PASS
PHASE32_BC_MULTI_LOT_RECOMPETITION = PASS
PHASE32_BC_GUARDRAILS_PRESERVED = YES
PHASE32_BC_PRODUCTION_CONSUMER_ENABLED = NO
PHASE32_BC_REGRESSION_STATUS = PASS
PHASE32_BC_READY_FOR_DUAL_READ = YES
PHASE32_BC_PRODUCTION_BEHAVIOR_CHANGED = NO
PHASE32_BC_NEXT_STEP = Run READ-ONLY dual-read acceptance on fresh artifacts to compare BC budget-bounded target gaps against existing Production PC/PS, with consumers still disabled.
```
