# Phase32-CH — Adaptive Buy Quality Target Authority Preservation Implementation

## Executive Summary

Phase32-CH implemented the narrow semantic preservation repair requested by Phase32-CF/CG: Adaptive Buy Quality reduced allocation is now an authoritative hard upper bound for NEW/REENTRY deployable target weight and for CC multi-lot expansion.

The repaired contract is:

```text
candidate_eligible != production_deployable_new/reentry
final_deployable_target_weight <= quality_authorized_target_weight
CC entry lot expansion <= quality-authorized executable quantity
```

This is not a rank cutoff, opportunity threshold, quality threshold, marginal-value tuning, fixed position-count rule, or historical-performance selection. It preserves the existing PIT Buy Quality authority and prevents later PC budget reconciliation / lot-aware expansion from restoring pre-quality base target magnitude.

## Scope

Changed implementation:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py`
- `src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py`

Changed focused tests:

- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py`

No fresh-run, resume, replay, or backtest was executed.

## Implementation

Portfolio Construction now materializes NEW/REENTRY deployability and Buy Quality target authority fields:

- `candidate_eligible`
- `production_deployable_new`
- `production_deployable_reentry`
- `production_deployability_class`
- `pre_quality_base_target_weight`
- `quality_allocation_adjustment`
- `quality_authorized_target_weight`
- `quality_target_upper_bound_enforced`
- `final_deployable_target_weight`

For `REDUCED_ALLOCATION_ONLY`, `target_weight` is reduced immediately to:

```text
pre_quality_base_target_weight * quality_allocation_adjustment
```

For `FULL_ALLOCATION_ELIGIBLE`, the quality upper bound is the base target. For `REJECT`, `BUY_WAIT`, and `REVIEW_REQUIRED`, production deployable target remains zero.

The common marginal frontier entry target magnitude resolver now:

- reads `quality_authorized_target_weight`
- treats a lower quality-authorized target as binding even on legacy-shaped artifacts where the explicit enforcement boolean is absent
- caps PC/PS executable quantity sources to the quality-authorized target floor
- derives NEW/REENTRY lot expansion from the capped quantity
- prevents implicit one-lot rescue when a reduced target is smaller than one trading lot

The production-shaped authority mapper preserves the existing BV zero-target admission classification when PC production admission blocks a row.

## Focused Reproductions

The exact CH reduced-target examples are covered by `test_phase32_ch_named_reduced_targets_cannot_reexpand_to_base_weight`:

| Symbol | Base target | Quality target | Result |
| --- | ---: | ---: | --- |
| 89180 | 3.3636% | 1.9686% | BF accepted weight remains <= 1.9686% |
| 76470 | 4.0000% | 2.4384% | BF accepted weight remains <= 2.4384% |
| 17570 | 3.8462% | 2.1632% | BF accepted weight remains <= 2.1632% |
| 37770 | 3.2258% | 1.6113% | BF accepted weight remains <= 1.6113% |
| 94340 | FULL-equivalent 5.0000% | 5.0000% | Full target remains available |

Additional focused checks cover:

- reduced NEW lot expansion bounded by quality target
- reduced REENTRY lot expansion bounded by quality target
- reduced target below one trading lot does not receive implicit one-lot rescue
- BV zero-target NEW remains blocked
- BZ FAIL_CLOSED ADD remains blocked
- ADD PASS multi-lot remains preserved
- BF aggregation remains PS-compatible

## Verification

Commands run:

```text
python3 -m pytest tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py
```

Result: `45 passed`

```text
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py
```

Result: `147 passed`

```text
PYTHONPYCACHEPREFIX=/tmp/phase32_ch_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py
```

Result: PASS

## Preservation

Preserved:

- CC NEW/REENTRY multi-lot machinery
- BV zero-target admission block
- BZ ADD PASS-only / BF-only authority
- common NEW/REENTRY/ADD/Cash competition
- BR ADD quantity progression
- BT effective Strategy/Safety cap path
- Cash/budget conservation
- Risk Pacing guardrails
- PS arithmetic
- Runtime mapping
- REDUCE/EXIT behavior
- legacy fallback zero policy
- PIT-only / deterministic authority fields

No threshold, marginal-value weight, Cash policy, Risk Pacing, PS arithmetic, Runtime, REDUCE, or EXIT logic was changed.

## Final Judgments

PHASE32_CH_BUY_QUALITY_TARGET_AUTHORITY_IMPLEMENTED = YES

PHASE32_CH_REDUCED_TARGET_REEXPANSION_BLOCKED = YES

PHASE32_CH_CANDIDATE_DEPLOYABILITY_SEPARATED = YES

PHASE32_CH_CC_QUALITY_BOUNDED_MULTI_LOT = YES

PHASE32_CH_REENTRY_QUALITY_BOUND_PRESERVED = YES

PHASE32_CH_BV_BZ_GUARDRAILS_PRESERVED = YES

PHASE32_CH_LEGACY_FALLBACK_ZERO = YES

PHASE32_CH_REGRESSION_STATUS = PASS

PHASE32_CH_FRESH_VALIDATION_READY = YES

PHASE32_CH_NEXT_STEP = User-operated short fresh validation from 2022-10-03 to confirm actual-path NEW/REENTRY target magnitude remains quality-bounded while ADD/BF/BG guardrails remain intact.
