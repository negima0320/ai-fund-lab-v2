# Phase32-BB Production Capital Allocation Budget / Acceptance Boundary Design

## Executive Summary

Phase32-BB is a design-only follow-up to Phase32-BA. No production code,
configuration, thresholds, model logic, runtime state, fresh-run, resume,
replay, backtest, or current-run control was changed.

Phase32-BA proved that:

```text
canonical_marginal_capital_frontier_authority.v1
```

can be generated from actual fresh-run artifacts, but its disabled acceptance
loop is too broad for immediate production consumption:

```text
50 characterized days
490 accepted authority targets
374 Production-zero / Authority-positive cases
```

BB design judgment:

```text
Do not invent a new deployment budget.
Reuse the existing Portfolio Policy incremental_capital_budget_envelope and PC
available_incremental_budget / canonical_multi_allocation_deployment_set budget
lineage as the budget source.

Add a PC-owned acceptance-boundary loop that allocates only the finite
decision-time deployment budget across NEW / REENTRY / ADD next-lot / Cash in
descending marginal capital value order.
```

## Required Inputs

Read:

- `docs/phase_reports/phase32_ba_marginal_capital_authority_dual_read_acceptance.md`
- `docs/phase_reports/phase32_az_production_shaped_marginal_capital_value_authority_implementation.md`
- `docs/phase_reports/phase32_ay_marginal_capital_frontier_production_migration_design.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `src/ai_fund_lab_v2/strategy/portfolio_policy.py`

Key existing authority facts:

- Portfolio Policy owns `incremental_capital_budget_envelope.v1`.
- Portfolio Construction owns allocation of that envelope across `NEW_BUY`,
  `ADD`, eligible re-entry-as-new, and Cash.
- Existing PC artifacts already expose `available_incremental_budget`,
  `incremental_budget_reconciliation`, and
  `capital_competition.canonical_multi_allocation_deployment_set`.
- Position Sizing remains target-to-quantity authority.
- Runtime remains a mapper and must not recompute capital priority.

## BA Problem Statement

The AZ authority builder currently accepts every feasible security target whose
bounded value exceeds Cash optionality.

That was useful for proving target-gap materialization, but it is not a
production allocation contract because it lacks a finite deployment budget
stop. On the BA actual path this produced:

| Metric | Count |
| --- | ---: |
| Authority accepted targets | 490 |
| Existing production target-gap match | 3 |
| Existing production target-gap divergence | 487 |
| Production gap `0` / Authority gap `>0` | 374 |
| Multi-lot ADD accepted targets | 94 |

The defect is not that the authority finds more opportunities than production.
Production is not assumed to be correct. The issue is that the acceptance loop
does not yet bind the common frontier to a PC-owned finite deployment envelope.

## Reusable Budget Authority

Existing budget authority is reusable in part.

Primary source:

```text
strategy/portfolio_policy.json#incremental_capital_budget_envelope
```

Owner:

```text
PORTFOLIO_POLICY
```

Relevant fields:

- `authority_status`
- `deployment_capacity_semantic`
- `risk_pacing_intent`
- `authorized_incremental_capital_basis`
- `existing_exposure_context`
- `cash_context`
- `available_cash_context`
- `pending_reserved_cash_context`
- `concentration_context`
- `evidence_completeness`
- `lineage`

PC allocation source:

```text
strategy/portfolio_construction.json#available_incremental_budget
strategy/portfolio_construction.json#incremental_budget_reconciliation
strategy/portfolio_construction.json#capital_competition.canonical_multi_allocation_deployment_set
```

The envelope is reusable as the maximum decision-time deployment budget and as
Risk Pacing / Cash / exposure lineage. It is not sufficient by itself as the
frontier acceptance boundary because it does not choose which marginal
candidate receives the next lot.

Therefore:

```text
Budget source = reusable / existing
Acceptance boundary = new PC-owned frontier allocator
```

## Proposed Production Contract

Add a PC-owned allocation boundary inside:

```text
canonical_marginal_capital_frontier_authority.v1
```

Recommended section:

```text
allocation_budget_authority
```

Required fields:

| Field | Meaning |
| --- | --- |
| `owner` | `PORTFOLIO_CONSTRUCTION` |
| `budget_envelope_owner` | `PORTFOLIO_POLICY` |
| `budget_envelope_schema_version` | `incremental_capital_budget_envelope.v1` |
| `budget_envelope_hash` | source hash / embedded envelope hash |
| `deployment_capacity_semantic` | existing Portfolio Policy semantic |
| `risk_pacing_intent` | existing Risk Pacing evidence |
| `available_incremental_budget_weight` | PC-resolved finite deployable budget |
| `available_incremental_budget_notional` | same budget in notional terms |
| `remaining_budget_weight` | recomputed after each accepted lot |
| `remaining_budget_notional` | recomputed after each accepted lot |
| `authorized_cash_allocation` | unallocated or intentionally deferred budget |
| `capital_conservation` | allocated + Cash + residual equals budget |
| `future_information_used` | `false` |
| `historical_outcome_used` | `false` |

Budget resolution priority:

1. Use `portfolio_construction.available_incremental_budget` when present,
   finite, PIT-safe, and reconciled.
2. Else use
   `capital_competition.canonical_multi_allocation_deployment_set.available_incremental_budget`
   when present and linked to an authoritative envelope.
3. Else derive from Portfolio Policy envelope:
   `min(resolved Cash capacity, target gross exposure headroom)` with existing
   envelope lineage.
4. If those sources disagree materially or are missing, fail closed as
   `REVIEW_REQUIRED`.

This reuses existing authority and avoids creating a new arbitrary budget.

## Acceptance Boundary Algorithm

The production allocator should replace AZ's broad loop with:

```text
1. Resolve allocation_budget_authority.
2. Build comparable NEW / REENTRY / ADD lot #1 / Cash candidates.
3. Remove or mark candidates blocked by hard guardrails:
   Safety, Risk Pacing, cap/headroom, Cash, lot infeasibility,
   no-loss-averaging, missing campaign identity, missing prior-exit context.
4. Sort remaining candidates by bounded marginal capital value.
5. Compare the top security candidate to Cash optionality and the next
   available alternative.
6. Accept the top security lot only if:
   - value is strictly above Cash optionality;
   - value is not ambiguous versus the next alternative;
   - remaining budget covers the executable lot;
   - post-lot Cash, exposure, weight, and headroom remain valid;
   - capital conservation remains PASS.
7. Recompute remaining budget, Cash, weight, headroom, and concentration.
8. For accepted ADD, generate/evaluate only the next ADD lot for that same
   symbol/campaign; it must re-enter competition against NEW, REENTRY, other
   ADD lots, and Cash.
9. Stop when the next marginal candidate loses to Cash, is ambiguous, violates
   budget/guardrails, or no feasible security lot remains.
10. Allocate remaining budget to explicit Cash optionality.
```

No fixed target count, fixed ADD lot count, fixed position count, fixed share
count, fixed ADD multiplier, or Historical-outcome-selected threshold is
introduced.

## Stop Conditions

The allocator must stop security acceptance and preserve Cash when any of the
following is true:

| Stop condition | Required output |
| --- | --- |
| Top security value `<=` Cash value | `CASH_OPTIONALITY_ACCEPTED` |
| Top security and next alternative are tied within tolerance | `REVIEW_REQUIRED` |
| Remaining budget cannot fund the next executable lot | `BUDGET_EXHAUSTED_TO_CASH` or lot infeasible |
| Remaining Cash below reserve / envelope bound | Cash wins remaining budget |
| Post-lot weight exceeds cap/headroom | candidate blocked |
| Safety hard block | candidate/day blocked |
| Risk Pacing hard block | candidate/day blocked |
| Missing/ambiguous Cash evidence | `REVIEW_REQUIRED` |
| Missing ADD campaign identity | `REVIEW_REQUIRED` |
| Missing REENTRY prior-exit/recovery evidence | not eligible / review per REENTRY contract |
| Capital conservation fails | `REVIEW_REQUIRED` |

## How BA's 374 Divergences Should Be Controlled

The 374 Production-zero / Authority-positive rows should not be reduced by
forcing production-like behavior. They should be controlled by the new budget
boundary:

1. Only candidates that fit inside the finite `available_incremental_budget`
   can receive accepted target gaps.
2. Multiple candidates compete for the same shared budget, so a lower-value
   candidate cannot remain positive just because it is individually feasible.
3. ADD #2/#3+ only materialize after ADD #1 wins and after recomputed remaining
   budget/headroom still supports the next lot.
4. Cash receives all budget not justified by the next marginal security lot.
5. Position count becomes an output of accepted executable lots, not a
   selection input.

This specifically targets BA's over-breadth mode:

```text
feasible individually -> accepted
```

and replaces it with:

```text
feasible under remaining shared budget AND better than Cash/alternative -> accepted
```

## Cash Contract

Cash remains first-class, not residual-only.

Cash roles:

- competes with the next marginal security lot;
- receives deferred budget when security value is weak, ambiguous, or budget
  exhausted;
- preserves existing Cash preference / participation-deferral semantics;
- carries source lineage from the AU resolver and Portfolio Policy envelope;
- may be the full-day allocation when no security lot is justified.

The allocator must not treat unallocated budget as unexplained leftover. It
must publish explicit `authorized_cash_allocation` and capital conservation.

## Multi-Lot ADD Contract

ADD remains lot-by-lot:

```text
PM ADD intent
-> ADD_NEXT_LOT #1
-> common competition
-> if accepted, recompute state
-> ADD_NEXT_LOT #2 enters common competition
-> repeat until stopped
```

Later ADD lots must never inherit acceptance from an earlier ADD lot. Each lot
must beat NEW / REENTRY / other ADD / Cash under the updated state.

## Artifact Shape

Recommended additions to `canonical_marginal_capital_frontier_authority.v1`:

```text
allocation_budget_authority
frontier_acceptance_sequence[]
accepted_incremental_targets[]
authorized_cash_allocation
capital_conservation
budget_exhaustion_or_stop_reason
consumer_switch_eligibility
```

Each `frontier_acceptance_sequence[]` item should contain:

- `step_index`
- `remaining_budget_before`
- `remaining_cash_before`
- `candidate_pool_hash`
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
- `remaining_cash_after`
- `reason_codes`

## Consumer Switch Readiness

Implementation can proceed, but production switch should remain disabled until
dual-read proves:

- `allocation_budget_authority.status = PASS`;
- capital conservation PASS on every accepted day;
- no missing/ambiguous budget or Cash sources;
- production-shaped target rows are PS-compatible;
- Safety, Risk Pacing, cap, Cash, lot, no-loss-averaging blocks are preserved;
- BA-style over-breadth materially collapses because of budget competition, not
  because of fixed target count or production-result matching;
- Cash allocation is explicit on every day;
- deterministic rerun hashes match.

## Non-Goals

This design does not:

- tune thresholds;
- use future returns, realized PnL, fills, or winner labels;
- force ADD, NEW, REENTRY, or Cash to win;
- target the current production count;
- introduce fixed 200/300 shares;
- introduce fixed ADD multipliers;
- introduce fixed position count;
- change PM, PS, Runtime, Pending, Orders, Execution, REDUCE, EXIT, Safety, or
  Risk Pacing ownership.

## Implementation Readiness

Readiness is `PARTIAL`.

Ready:

- existing budget authority source is identified;
- acceptance loop semantics are defined;
- stop conditions are explicit;
- artifact fields are defined;
- migration boundary is clear.

Remaining design-to-code details:

- exact tolerance for budget-source reconciliation;
- exact representation of budget weight/notional conversion;
- whether `available_incremental_budget` remains weight-primary or publishes a
  required paired notional;
- formal test fixtures for budget exhaustion, Cash allocation, and capital
  conservation;
- dual-read report format for post-implementation BB acceptance.

## Final Judgments

```text
PHASE32_BB_EXISTING_BUDGET_AUTHORITY_REUSABLE = PARTIAL
PHASE32_BB_PC_ALLOCATION_BUDGET_DEFINED = YES
PHASE32_BB_ACCEPTANCE_BOUNDARY_DEFINED = YES
PHASE32_BB_CROSS_TYPE_COMPETITION_PRESERVED = YES
PHASE32_BB_MULTI_LOT_ADD_PRESERVED = YES
PHASE32_BB_CASH_OPTIONALITY_PRESERVED = YES
PHASE32_BB_GUARDRAILS_PRESERVED = YES
PHASE32_BB_HISTORICAL_PARAMETER_SELECTION_USED = NO
PHASE32_BB_IMPLEMENTATION_READY = PARTIAL
PHASE32_BB_PRODUCTION_CHANGE_THIS_TASK = NO
PHASE32_BB_NEXT_STEP = Implement the allocation_budget_authority and frontier_acceptance_sequence inside canonical_marginal_capital_frontier_authority.v1 with consumers still disabled, then rerun READ-ONLY dual-read to verify budget-bounded breadth, explicit Cash allocation, capital conservation, and PS-compatible target gaps.
```
