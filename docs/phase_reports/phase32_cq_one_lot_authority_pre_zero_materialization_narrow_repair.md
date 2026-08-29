# Phase32-CQ One-Lot Authority Pre-Zero Materialization Narrow Repair

## Executive Summary

Phase32-CQ repaired the actual-path migration gap identified in Phase32-CP: reduced-quality NEW/REENTRY sub-lot rows with positive `quality_authorized_target_weight` were being zeroed by PC lot-aware handling before `minimum_executable_one_lot_authority.v1` could materialize.

The repair is narrow and preserves the CO decision policy. It does not loosen admission, add thresholds, tune rank/quality/opportunity, restore implicit rescue, change ADD, change Cash/budget, change PS arithmetic, or touch Runtime / REDUCE / EXIT.

The repaired flow is:

```text
normal:
one_lot_weight <= quality_authorized_target_weight
-> existing CH/CJ quality-bounded CC multi-lot path

sub-lot:
quality_authorized_target_weight > 0
and one_lot_weight > quality_authorized_target_weight
and PC target_weight was pre-zeroed by lot_minimum_exceeds_quality_authorized_target
-> minimum_executable_one_lot_authority.v1 evaluates from the pre-zero quality target
-> ADMIT_ONE_LOT / BLOCK / REVIEW_REQUIRED materializes
```

If the authority emits `ADMIT_ONE_LOT`, exactly one lot is carried into common frontier competition and can reach BF/PS only if accepted. If it emits `BLOCK` or `REVIEW_REQUIRED`, the row remains zero, but with explicit authority evidence instead of an empty `{}`.

No fresh-run, resume, replay, or backtest was executed.

## Inputs Reviewed

- `docs/phase_reports/phase32_cp_post_co_day0_one_lot_authority_actual_path_trace.md`
- `docs/phase_reports/phase32_co_bounded_minimum_executable_one_lot_authority_migration_implementation.md`
- `docs/phase_reports/phase32_cn_existing_one_lot_authority_policy_reuse_audit.md`
- `docs/phase_reports/phase32_cm_bounded_minimum_executable_one_lot_authority_design.md`
- `docs/phase_reports/phase32_cj_quality_deployable_lot_aware_boundary_narrow_repair.md`
- Existing PC / CC / BF / PS authority implementation and focused tests

## Root Cause

In actual Day-0 artifacts, rows such as `33700`, `83060`, `92420`, `93600`, and `58200` had:

```text
quality_authorized_target_weight > 0
one_lot_weight > quality_authorized_target_weight
target_weight = 0
zero_weight_reason = lot_minimum_exceeds_quality_authorized_target
minimum_executable_one_lot_authority = {}
```

The production-shaped frontier builder then read the already-zeroed `target_weight` and applied:

```text
effective_target_weight = min(target_weight, quality_authorized_target_weight)
```

Because `target_weight` was `0`, the positive quality target was erased before CO one-lot evaluation. The authority then degraded into `missing_pc_target_quantity_or_weight_authority` instead of producing `ADMIT_ONE_LOT`, `BLOCK`, or `REVIEW_REQUIRED`.

## Implementation

Changed files:

- `src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py`
- `tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py`
- `docs/phase_reports/phase32_cq_one_lot_authority_pre_zero_materialization_narrow_repair.md`

### Pre-Zero Quality Target Recognition

Added detection for the exact CQ shape:

```text
target_weight == 0
quality_authorized_target_weight > 0
quality ceiling enforced
zero reason includes lot_minimum_exceeds_quality_authorized_target
```

For only that shape, `_entry_target_magnitude_authority()` now uses the positive quality-authorized target as the authority evaluation basis instead of `min(0, quality_target)`.

This preserves CH/CJ semantics because it does not make the row deployable by itself. It only allows the explicit one-lot authority to decide.

### ADMIT Connection

When `minimum_executable_one_lot_authority.v1` emits `ADMIT_ONE_LOT`, `_entry_target_lot_candidates()` now carries an admissible one-lot target into the hypothetical candidate row so `_production_first_lot_admission()` does not re-block it on the stale zero target.

The ADMIT path still creates exactly one candidate:

```text
pc_target_executable_quantity = trading_unit
entry lot candidates = 1
second lot = forbidden
BF target = only if common frontier accepts the candidate
```

### Explicit BLOCK / REVIEW Visibility

When the explicit one-lot authority emits `BLOCK` or `REVIEW_REQUIRED`, the candidate remains non-deployable, but disposition now surfaces the explicit authority outcome:

- non-supportive one-lot evidence -> `INFEASIBLE_LOT`
- one-lot cap breach -> `INFEASIBLE_CAP_BLOCKED`
- missing/ambiguous authority evidence -> `REVIEW_REQUIRED`

This prevents explicit CQ decisions from being hidden under the older generic `INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED` label.

## Focused Actual-Shaped Tests

Added coverage:

| Test shape | Expected result |
| --- | --- |
| `83060`-style pre-zero reduced sub-lot | non-empty authority, `decision = BLOCK`, no BF/PS target |
| `33700` supportive pre-zero sub-lot | `decision = ADMIT_ONE_LOT`, exactly one candidate, BF target possible if it wins |
| `93600` cap-crossing pre-zero sub-lot | non-empty authority, `decision = BLOCK`, cap-block disposition |
| missing Cash evidence | non-empty authority, `decision = REVIEW_REQUIRED`, fail closed |
| normal >=1lot target | existing CH/CJ/CC path unchanged through existing regression coverage |

## Actual-Shaped Artifact Reproduction

A non-fresh, read-only reproduction was run against the Phase32-CP Day-0 PC/PS artifact shape:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260829T050706122946Z/daily/2022-10-03
```

Result after the repair:

| Metric | Result |
| --- | ---: |
| Materialized one-lot authority objects | 16 |
| `ADMIT_ONE_LOT` | 0 |
| `BLOCK` | 16 |
| `REVIEW_REQUIRED` | 0 |
| `INFEASIBLE_LOT` | 15 |
| `INFEASIBLE_CAP_BLOCKED` | 1 |
| BF one-lot targets | 0 |

Required symbol outcomes under unchanged CO policy:

| Symbol | Decision | Disposition | Primary reason |
| --- | --- | --- | --- |
| `33700` | `BLOCK` | `INFEASIBLE_LOT` | `minimum_one_lot_opportunity_quality_not_supportive:COMPARABLE_MARGINAL` |
| `83060` | `BLOCK` | `INFEASIBLE_LOT` | `minimum_one_lot_opportunity_quality_not_supportive:COMPARABLE_MARGINAL` |
| `92420` | `BLOCK` | `INFEASIBLE_LOT` | `minimum_one_lot_opportunity_quality_not_supportive:COMPARABLE_MARGINAL` |
| `93600` | `BLOCK` | `INFEASIBLE_CAP_BLOCKED` | `minimum_one_lot_exceeds_effective_single_name_cap`; also `COMPARABLE_MARGINAL` |
| `58200` | `BLOCK` | `INFEASIBLE_LOT` | `minimum_one_lot_opportunity_quality_not_supportive:COMPARABLE_MARGINAL` |

This explains why Day-0 holdings may still not change after CQ: actual evidence still blocks all 16 sub-lot rows under CO policy. The important change is that the block is now explicit and authority-owned instead of an empty authority migration gap.

## Verification

Focused CQ/CO/CH/CC tests:

```text
python3 -m pytest -q tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  -k 'phase32_cq or phase32_co_sub_lot or phase32_ch_named or phase32_cc_reentry_target_magnitude'
```

Result:

```text
10 passed, 42 deselected
```

Full marginal frontier authority suite:

```text
python3 -m pytest -q tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py
```

Result:

```text
52 passed
```

Nearby PC lot-aware regression subset:

```text
python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py \
  -k 'phase32_cj or phase29_l21s_one_lot or phase32_ch'
```

Result:

```text
5 passed, 119 deselected
```

Submit-feasibility one-lot compatibility subset:

```text
python3 -m pytest -q tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  -k 'phase32_co or minimum_executable_one_lot or pc_discrete_quantity_authority_future_information_flag_invalid'
```

Result:

```text
2 passed, 41 deselected
```

Compile:

```text
PYTHONPYCACHEPREFIX=/tmp/phase32_cq_pycache python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py \
  src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  src/ai_fund_lab_v2/strategy/position_sizing.py \
  src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py \
  src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py
```

Result:

```text
PASS
```

## Preservation

Preserved:

- CH/CJ Buy Quality target ceiling
- CO admission policy and opportunity-quality requirements
- normal NEW/REENTRY multi-lot path
- `ADMIT_ONE_LOT` as candidate permission, not forced deployment
- common NEW/REENTRY/ADD/Cash competition
- BZ ADD PASS-only / BF-only authority
- Strategy/Safety caps
- Risk Pacing
- Cash/budget conservation
- PS arithmetic ownership
- Runtime mapping
- REDUCE / EXIT
- legacy fallback zero
- PIT-only fields and no historical outcome use

No Architecture SoT update was required because CQ implements the already-defined CM/CO contract at the missing actual-path boundary.

## Final Judgments

PHASE32_CQ_PRE_ZERO_AUTHORITY_MATERIALIZED = YES

PHASE32_CQ_SUBLOT_EMPTY_AUTHORITY_ZERO = NO

PHASE32_CQ_ADMIT_BLOCK_REVIEW_REACHABLE = YES

PHASE32_CQ_CC_CONNECTION_PRESERVED = YES

PHASE32_CQ_QUALITY_SEMANTICS_PRESERVED = YES

PHASE32_CQ_BV_BZ_GUARDRAILS_PRESERVED = YES

PHASE32_CQ_REGRESSION_STATUS = PASS

PHASE32_CQ_SHORT_FRESH_VALIDATION_READY = YES

PHASE32_CQ_NEXT_STEP = User-operated short fresh validation from 2022-10-03 to confirm actual artifacts now show explicit `minimum_executable_one_lot_authority.v1` decisions for reduced-quality sub-lot rows; expect Day-0 holdings to remain unchanged if all actual rows continue to BLOCK under unchanged CO policy.
