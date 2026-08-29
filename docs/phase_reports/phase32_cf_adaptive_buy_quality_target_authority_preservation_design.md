# Phase32-CF — Adaptive Buy Quality Target Authority Preservation Design

## Executive Summary

Phase32-CF defines a narrow Production repair design for the Phase32-CE target-weight semantic defect.

No production code, config, runtime state, thresholds, weights, model behavior, fresh run, resume, replay, or backtest was changed in this task.

Confirmed CE defect: Adaptive Buy Quality reduces allocation magnitude, but later PC stages can restore the pre-quality/base target weight. That makes `REDUCED_ALLOCATION_ONLY` visible in lineage while final deployable NEW size behaves like a full/base allocation.

Design conclusion: the final PC deployable target for NEW and REENTRY must be hard-bounded by the Buy Quality-authorized target magnitude before CC multi-lot expansion. Later budget reconciliation, lot-aware reallocation, Cash competition, cap, and Risk Pacing may reduce or partially use that magnitude, but may not re-expand beyond it unless a separate explicit PC authority is materialized with PIT lineage and reason codes.

## Inputs

Required source reports and architecture reviewed:

- `docs/phase_reports/phase32_ce_new_production_admission_quality_rank_semantic_audit.md`
- `docs/phase_reports/phase32_cc_new_reentry_target_magnitude_multilot_implementation.md`
- `docs/02_architecture/adaptive_buy_quality_authority.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

## Confirmed Defect

Phase32-CE found rows where Adaptive Buy Quality applied a reduced allocation, but final PC/lot target returned to the base target:

| Symbol | Base / PC target | Quality-adjusted target | Final / lot target | Defect |
|---|---:|---:|---:|---|
| 89180 | 3.3636% | 1.9686% | 3.3636% | Reduced target re-expanded |
| 76470 | 4.0000% | 2.4384% | 4.0000% | Reduced target re-expanded |
| 17570 | 3.8462% | 2.1632% | 3.8462% | Reduced target re-expanded |
| 37770 | 3.2258% | 1.6113% | 3.2258% | Reduced target re-expanded |

The defect is not that these rows remained candidates. The defect is that the later deployable target did not preserve the Buy Quality allocation authority.

## Design Goals

- Explicitly separate `candidate_eligible` from `production_deployable_new`.
- Preserve Adaptive Buy Quality as an allocation magnitude authority, not merely explanatory metadata.
- Preserve CC NEW/REENTRY multi-lot expansion, but bound it by the quality-authorized deployable target.
- Preserve BV zero-target admission blocking.
- Preserve BZ ADD PASS-only and BF-only authority.
- Preserve common NEW/REENTRY/ADD/Cash competition.
- Preserve Cash, budget, cap, Safety, Risk Pacing, PS arithmetic, Runtime, REDUCE, and EXIT behavior.
- Avoid new rank cutoffs, opportunity thresholds, quality tuning, fixed position counts, or historical outcome/PnL selection.

## Authority Model

### Candidate Eligibility

`candidate_eligible` means the symbol remains a valid decision-time opportunity row for evidence, review, ranking, explanation, and common-frontier observability.

It does not by itself authorize Production capital.

Required materialization:

```text
candidate_eligible: true | false
candidate_eligibility_authority
candidate_eligibility_reason_codes
```

### Production Deployability

`production_deployable_new` and `production_deployable_reentry` mean PC has authorized the row to compete for Production capital after all required admission and Buy Quality evidence is resolved.

Required materialization:

```text
production_deployable_new: true | false
production_deployable_reentry: true | false
production_deployability_class
production_deployability_authority
production_deployability_reason_codes
```

The frontier must not infer Production deployability from candidate presence alone.

### Buy Quality Target Authority

PC must materialize the quality-bounded target magnitude as a first-class target authority:

```text
pre_quality_base_target_weight
quality_action
quality_score
quality_band
quality_allocation_adjustment
quality_authorized_target_weight
quality_authorized_target_authority
quality_authorized_target_reason_codes
quality_target_upper_bound_enforced: true
```

Canonical relation:

```text
quality_authorized_target_weight =
    pre_quality_base_target_weight * quality_allocation_adjustment
```

For `FULL_ALLOCATION_ELIGIBLE`, `quality_allocation_adjustment = 1.0`.

For `REDUCED_ALLOCATION_ONLY`, the adjustment is the Buy Quality artifact adjustment and the quality-authorized target is a hard upper bound.

For `REVIEW_REQUIRED` and `REJECT`, the quality-authorized target is `0.0` unless a separate explicit PC review authority resolves the row to deployable.

## Deployability Classes

### FULL_ALLOCATION_ELIGIBLE

Semantics:

- Candidate may be Production deployable if other PC admission evidence passes.
- Quality upper bound equals the pre-quality/base PC target.
- Later PC budget, lot, Cash, cap, Safety, and Risk Pacing stages may reduce or partially allocate.
- Later stages may use the full quality-authorized upper bound but must not exceed it.

Contract:

```text
production_deployability_class = FULL_ALLOCATION_ELIGIBLE
quality_authorized_target_weight = pre_quality_base_target_weight
final_deployable_target_weight <= quality_authorized_target_weight
```

### REDUCED_ALLOCATION_ONLY

Semantics:

- Candidate may remain Production deployable, but only at reduced size.
- The quality-adjusted target is the hard upper bound for final PC deployable target.
- Later budget reconciliation and lot-aware final reallocation may trim the target, select fewer lots, or leave Cash.
- Later stages must not restore the pre-quality/base target.

Contract:

```text
production_deployability_class = REDUCED_ALLOCATION_ONLY
quality_authorized_target_weight =
    pre_quality_base_target_weight * quality_allocation_adjustment
final_deployable_target_weight <= quality_authorized_target_weight
```

If one trading lot would exceed the quality-authorized target, the row must not silently round up. It must either:

- become non-deployable with a reason such as `LOT_MINIMUM_EXCEEDS_QUALITY_AUTHORIZED_TARGET`, or
- carry an explicit separate PC exception authority with PIT lineage, reason codes, and `quality_target_reexpansion_authorized = true`.

The default is fail-closed; no implicit one-lot rescue is allowed for reduced rows.

### REJECT / Non-Deployable

Semantics:

- Candidate may remain visible for audit/explainability if upstream eligibility allows it.
- Production capital is not authorized.
- CC lot expansion emits no PS-consumable NEW/REENTRY lots.
- BF emits no target.

Contract:

```text
production_deployability_class = REJECT
production_deployable_new = false
quality_authorized_target_weight = 0.0
final_deployable_target_weight = 0.0
```

`REVIEW_REQUIRED` follows the same non-deployable behavior until resolved by explicit authority.

## Later Reallocation Contract

Every downstream PC stage that touches target magnitude must consume and preserve:

```text
quality_authorized_target_weight
quality_authorized_target_authority
quality_target_upper_bound_enforced
```

Allowed:

```text
final_deployable_target_weight < quality_authorized_target_weight
final_deployable_target_weight == quality_authorized_target_weight
accepted_lot_quantity below quality-authorized quantity due budget/Cash/cap
Cash wins residual capital
```

Forbidden without explicit authority:

```text
final_deployable_target_weight > quality_authorized_target_weight
lot-aware final reallocation restores pre_quality_base_target_weight
incremental budget reconciliation restores pre_quality_base_target_weight
budget exhaustion/availability is used as a reason to expand reduced target
fixed position count or forced deployment expands reduced target
```

If an expansion exception exists, it must be separately materialized:

```text
quality_target_reexpansion_authorized: true
quality_target_reexpansion_authority
quality_target_reexpansion_reason_codes
quality_target_reexpansion_pit_status = PASS
historical_outcome_used = false
future_information_used = false
```

No exception is implied by available Cash, unused budget, rank, low position count, or lot mechanics.

## CC / BF Integration

CC multi-lot expansion remains intact, but the expansion source changes from raw/base PC target magnitude to final quality-bounded deployable magnitude.

For NEW/REENTRY:

```text
PC production admission
-> Buy Quality target upper bound
-> final_deployable_target_weight
-> PS-compatible target quantity upper bound
-> deterministic lot #1/#2/#N expansion
-> common NEW/REENTRY/ADD/Cash competition
-> BF aggregate
-> PS
```

Hard bound:

```text
sum(entry_lot_incremental_quantity) <= quality_authorized_target_quantity
final_target_weight <= quality_authorized_target_weight
```

Lot #N+1 is absent once the quality-authorized target quantity is exhausted.

If `production_deployable_new = false` or `production_deployable_reentry = false`, the frontier may materialize a non-deployable explanatory row, but it must not create a BF/PS-consumable target.

## ADD Preservation

ADD is intentionally outside the NEW/REENTRY Buy Quality target preservation repair.

Preserved ADD contracts:

- PM ADD intent remains evidence, not target authority.
- `ADD_NEXT_LOT` requires authoritative ADD investment evidence `PASS`.
- `FAIL_CLOSED`, `WEAKENING`, `UNKNOWN`, `NEW_BUY_SUPERIOR`, or requalification failure cannot be overridden by rank, quality, or budget.
- BF-only ADD authority remains enforced.
- Multi-lot ADD, BR quantity progression, BT effective cap, Cash/budget conservation, and no legacy fallback remain unchanged.

## Fail-Closed Conditions

The repair must fail closed to `REVIEW_REQUIRED` or non-deployable target `0.0` for:

- missing Buy Quality decision where required;
- missing or ambiguous quality allocation adjustment;
- inconsistent `pre_quality_base_target_weight`, `quality_allocation_adjustment`, and `quality_authorized_target_weight`;
- final target above the quality-authorized upper bound without explicit expansion authority;
- lot rounding that would exceed the reduced target without explicit expansion authority;
- candidate/deployability class conflict;
- stale or non-PIT Buy Quality evidence;
- missing `future_information_used = false` or `historical_outcome_used = false` on the relevant authority lineage.

## Minimal Implementation Boundary

Expected narrow implementation scope for the next repair:

- PC target-weight resolution: materialize `quality_authorized_target_weight` and enforce it as the max deployable target.
- Incremental budget reconciliation: cap any reallocation output by `quality_authorized_target_weight`.
- Lot-aware final reallocation: forbid returning to pre-quality/base target unless explicit expansion authority exists.
- CC target magnitude resolver: use the final quality-bounded deployable quantity for NEW/REENTRY lot expansion.
- BF boundary validation: assert accepted NEW/REENTRY aggregate does not exceed the quality-authorized target quantity/weight.
- Tests: add focused reproductions for the CE examples and preservation regressions.

Non-scope:

- no rank cutoff;
- no opportunity threshold;
- no quality threshold tuning;
- no marginal value weight tuning;
- no fixed position count;
- no PS arithmetic change;
- no Runtime change;
- no PM/REDUCE/EXIT change;
- no Cash/Risk Pacing policy change.

## Focused Regression Design

Minimum test set for implementation acceptance:

- `REDUCED_ALLOCATION_ONLY`: 89180-style base 3.3636%, quality 1.9686%, final target cannot exceed 1.9686%.
- `REDUCED_ALLOCATION_ONLY`: 76470-style base 4.0000%, quality 2.4384%, final target cannot exceed 2.4384%.
- `REDUCED_ALLOCATION_ONLY`: 17570-style base 3.8462%, quality 2.1632%, final target cannot exceed 2.1632%.
- `REDUCED_ALLOCATION_ONLY`: 37770-style base 3.2258%, quality 1.6113%, final target cannot exceed 1.6113%.
- `FULL_ALLOCATION_ELIGIBLE`: 94340-style full target remains eligible up to base target.
- Candidate eligible but `REJECT` Buy Quality produces no BF/PS target.
- Candidate eligible but `REVIEW_REQUIRED` Buy Quality produces no BF/PS target.
- One-lot rounding above reduced quality bound fails closed unless explicit exception authority is present.
- CC NEW multi-lot expansion uses quality-bounded target quantity.
- CC REENTRY multi-lot expansion uses quality-bounded target quantity.
- BV zero-target NEW remains blocked.
- BZ ADD `FAIL_CLOSED` remains blocked.
- BZ BF-only ADD authority remains enforced.
- Cash/budget/cap/Risk Pacing guardrails remain active.
- Deterministic rerun produces identical lot identities and BF aggregation.
- Future/outcome fields are rejected or fail closed.

## Acceptance Criteria

The repair is accepted when:

- every positive NEW/REENTRY BF target has explicit production deployability authority;
- every reduced Buy Quality row has final deployable target at or below the quality-authorized target;
- no downstream PC stage re-expands reduced targets without explicit authority;
- CC multi-lot preserves target magnitude only up to the quality-bounded upper bound;
- ADD semantics from BZ remain unchanged;
- PS/Runtime consumers require no arithmetic or mapping change;
- legacy fallback remains zero;
- focused regressions pass.

## Recommendation

Proceed to a narrow implementation phase that enforces Buy Quality target authority inside PC target resolution and the CC/BF target-magnitude boundary.

This is a Production repair candidate because the defect is semantic-contract loss, not performance tuning: an existing PIT authority says allocation should be reduced, but final target materialization can erase that reduction.

## Final Judgments

PHASE32_CF_BUY_QUALITY_TARGET_AUTHORITY_DEFINED = YES

PHASE32_CF_REDUCED_TARGET_HARD_UPPER_BOUND = YES

PHASE32_CF_CANDIDATE_DEPLOYABILITY_SEPARATED = YES

PHASE32_CF_LATER_REALLOCATION_REEXPANSION_FORBIDDEN = YES

PHASE32_CF_CC_MULTI_LOT_PRESERVED = YES

PHASE32_CF_BV_BZ_PRESERVED = YES

PHASE32_CF_IMPLEMENTATION_READY = YES

PHASE32_CF_PRODUCTION_CHANGE_THIS_TASK = NO

PHASE32_CF_NEXT_STEP = Implement the narrow PC target-weight resolution repair: materialize the Buy Quality-authorized target upper bound, enforce it through incremental budget reconciliation and lot-aware final reallocation, and make CC/BF NEW/REENTRY lot expansion consume only the quality-bounded deployable target.
