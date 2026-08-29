# Phase32-CP Post-CO Day-0 One-Lot Authority Actual-Path Trace

## Executive Summary

This is a READ-ONLY actual-path audit of:

`runtime-test-historical-extended-smoke-20260829T050706122946Z`

Business date:

`2022-10-03`

No Production code, config, thresholds, model, runtime state, fresh-run, resume, replay, or backtest was changed or executed.

The Post-CO run did not show a Day-0 holdings difference from Post-CJ because the minimum executable one-lot authority did not materialize for the actual reduced-quality sub-lot candidates. The BG/BF frontier path itself is active and healthy: the marginal authority accepted 39 NEW lot targets, BF aggregated them into 6 PS-boundary targets, PS consumed those 6 targets, Runtime planned them, and 6 BUY fills occurred.

For the required sub-lot symbols `33700`, `83060`, `92420`, `93600`, and `58200`, the first stopping boundary is earlier:

```text
PC lot-aware final reallocation
-> target_weight = 0
-> zero_weight_reason = lot_minimum_exceeds_quality_authorized_target
-> frontier diagnostic candidate
-> INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED
```

The `minimum_executable_one_lot_authority` field is empty in both PC lot resolution and frontier `pc_target_magnitude_authority`. Therefore actual-path CO activation is PARTIAL: the common frontier/BF consumer switch is active, but the CO one-lot authority producer/consumer migration does not reach the reduced-quality sub-lot rows before they are zeroed.

## Run Identity

| Field | Value |
| --- | --- |
| Run ID | `runtime-test-historical-extended-smoke-20260829T050706122946Z` |
| Run state | `RUNNING` |
| Primary date | `2022-10-03` |
| Evidence root | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260829T050706122946Z/daily/2022-10-03` |
| Primary artifacts | `strategy/portfolio_construction.json`, `strategy/marginal_capital_frontier_authority.json`, `strategy/position_sizing.json`, `strategy/runtime_planning.json`, `morning/pending_generation_evidence.json`, `execution/fills.json` |

## Actual-Path Summary

| Boundary | Actual evidence |
| --- | --- |
| Candidate / PC rows | 50 `portfolio_members` |
| Frontier candidates | 84 total; 83 `NEW_FIRST_LOT`, 1 Cash |
| Frontier accepted targets | 39 `NEW_FIRST_LOT` lots |
| BF aggregated targets | 6 symbols |
| PS switched consumer status | `PASS`; `production_consumer_enabled = true`; `bf_only_target_authority = true` |
| Legacy fallback | `legacy_target_gap_fallback_used = false`; `legacy_zero_fallback_used = false` |
| Runtime plans | 22 plans; 6 BUY_NEW plans and 16 NO_ORDER rows among the traced set |
| Pending generation | `PASS`; pending plan written |
| Fills | 6 BUY fills |
| Review status | Runtime `human_review_status = REQUIRED` only for `SOURCE_LIFECYCLE_DRAFT`; not causal to one-lot collapse |

BF aggregated targets:

| Symbol | Final target quantity | Accepted lots | Accepted weight |
| --- | ---: | ---: | ---: |
| `33500` | 400 | 4 | 0.01652 |
| `37820` | 300 | 3 | 0.02040 |
| `67860` | 200 | 2 | 0.01600 |
| `76470` | 700 | 7 | 0.01890 |
| `89180` | 2100 | 21 | 0.01890 |
| `94340` | 200 | 2 | 0.02882 |

Actual fills match the 6 BF symbols: `89180`, `94340`, `67860`, `37820`, `76470`, `33500`.

## Sub-Lot Reduced-Quality Cohort

Day-0 has 16 reduced-quality sub-lot candidates where:

```text
quality_authorized_target_weight > 0
one_lot_weight > quality_authorized_target_weight
target_weight = 0
zero_weight_reason = lot_minimum_exceeds_quality_authorized_target
```

| Symbol | Rank | Quality target | One-lot weight | One-lot / target | PC final target | Entry / quality | First stop reason |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `93600` | 10 | 0.023228 | 0.19110 | 8.23x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `33700` | 17 | 0.021670 | 0.03410 | 1.57x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `83060` | 20 | 0.020607 | 0.06480 | 3.14x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `92420` | 21 | 0.020691 | 0.13750 | 6.65x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `58200` | 23 | 0.020120 | 0.17467 | 8.68x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `41920` | 24 | 0.019994 | 0.07880 | 3.94x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `45750` | 27 | 0.019314 | 0.06760 | 3.50x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `91070` | 30 | 0.018345 | 0.07100 | 3.87x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `70780` | 31 | 0.018359 | 0.11080 | 6.04x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `99840` | 32 | 0.018070 | 0.12453 | 6.89x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `50250` | 34 | 0.017501 | 0.09970 | 5.70x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `82540` | 35 | 0.017260 | 0.03020 | 1.75x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `45410` | 36 | 0.017051 | 0.04360 | 2.56x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `70690` | 38 | 0.016812 | 0.06325 | 3.76x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `96100` | 41 | 0.015850 | 0.01980 | 1.25x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |
| `44170` | 44 | 0.015373 | 0.17200 | 11.19x | 0.000000 | `BUY_NEW_REDUCED_ONLY` / `REDUCED_ALLOCATION_ONLY` | `lot_minimum_exceeds_quality_authorized_target` |

## Required Symbol Trace

All five required symbols share the same lineage shape:

```text
candidate_eligible = true
production_deployability_class = REDUCED_ALLOCATION_ONLY
entry_admission_action = BUY_NEW_REDUCED_ONLY
entry_admission_state = CONTINUATION_WITH_CAUTION
quality_action = REDUCED_ALLOCATION_ONLY
quality_band = MEDIUM
quality_target_upper_bound_enforced = true
PC lot-aware final target = 0
minimum_executable_one_lot_authority = {}
frontier disposition = INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED
BF target = none
PS target = 0
Runtime = NO_ORDER
Fill = 0
```

| Symbol | Buy Quality score | Rank / opportunity score | Quality target | One lot | Cap status | One-lot authority | Frontier disposition | BF / PS / Fill |
| --- | ---: | --- | ---: | ---: | --- | --- | --- | --- |
| `33700` | 0.644242 | rank 17 / -0.25322955 | 0.021670 | 0.03410 | feasible; effective cap 0.18 | absent `{}` | `INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED`; reasons include `pc_first_lot_target_weight_zero`, `pc_first_lot_zero_weight_reason_lot_minimum_exceeds_quality_authorized_target` | none / 0 / 0 |
| `83060` | 0.612652 | rank 20 / -0.29319864 | 0.020607 | 0.06480 | feasible; effective cap 0.18 | absent `{}` | same PC production-admission block | none / 0 / 0 |
| `92420` | 0.615140 | rank 21 / -0.29992208 | 0.020691 | 0.13750 | feasible; effective cap 0.18 | absent `{}` | same PC production-admission block | none / 0 / 0 |
| `93600` | 0.690580 | rank 10 / -0.20107329 | 0.023228 | 0.19110 | frontier feasibility `FAIL`, `cap_blocked`; effective cap 0.18 | absent `{}` | PC block plus cap block | none / 0 / 0 |
| `58200` | 0.598170 | rank 23 / -0.33497513 | 0.020120 | 0.17467 | feasible; effective cap 0.18 | absent `{}` | same PC production-admission block | none / 0 / 0 |

### 33700 Focused Regression vs Actual Evidence

The Phase32-CO focused regression proved that a supportive sub-lot case can emit `ADMIT_ONE_LOT`. Actual 2022-10-03 `33700` is not that supportive case:

- entry state is `CONTINUATION_WITH_CAUTION`
- entry action is `BUY_NEW_REDUCED_ONLY`
- Buy Quality action is `REDUCED_ALLOCATION_ONLY`
- opportunity score is negative at `-0.25322955`
- opportunity-quality class is `COMPARABLE_MARGINAL`
- one-lot weight is 1.57x the quality-authorized target

However, the actual artifact does not prove an explicit CO `BLOCK` decision for `33700`. The CO authority never materialized; PC lot-aware target resolution zeroed the row first.

## Authority Decision Metrics

| Metric | Count | Evidence |
| --- | ---: | --- |
| Sub-lot reduced-quality candidates | 16 | PC `portfolio_members` with positive quality target and one-lot weight above target |
| Materialized `ADMIT_ONE_LOT` | 0 | no non-empty `minimum_executable_one_lot_authority` in frontier candidates |
| Materialized `BLOCK` | 0 | no CO authority decision object materialized |
| Materialized `REVIEW_REQUIRED` | 0 | no CO authority decision object materialized |
| Pre-authority PC lot-minimum blocks | 16 | `lot_minimum_exceeds_quality_authorized_target` |
| ADMIT after CC candidate count | 0 | no admitted one-lot candidate reached CC/frontier as deployable |
| Admitted frontier accepted count | 0 | no admitted one-lot candidate exists |
| Cash defeat count for admitted one-lot | 0 | no admitted one-lot candidate exists |
| Other-security defeat count for admitted one-lot | 0 | no admitted one-lot candidate exists |
| BF one-lot target count | 0 | BF `aggregated_ps_targets` contain no one-lot authority |
| PS one-lot target count | 0 | PS consumed only six BF non-one-lot targets |
| Runtime/fill one-lot count | 0 | required symbols are `NO_ORDER`; fills are only the six BF symbols |

## First Divergence Boundary

The first divergence from intended CO actual-path semantics is:

```text
Portfolio Construction target magnitude / lot-aware final reallocation
```

Specific field evidence:

```text
target_weight_resolution.lot_aware_final_reallocation.blocker_reason
  = lot_minimum_exceeds_quality_authorized_target

target_weight_resolution.resolved_weight
  = 0.0

phase29_l19_lot_resolution.minimum_executable_one_lot_authority
  = {}

marginal_capital_frontier_authority.frontier_candidates[].pc_target_magnitude_authority.status
  = REVIEW_REQUIRED

marginal_capital_frontier_authority.frontier_candidates[].pc_target_magnitude_authority.reason_codes
  = ["missing_pc_target_quantity_or_weight_authority"]

marginal_capital_frontier_authority.frontier_candidates[].shadow_disposition
  = INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED
```

This is not a Cash defeat and not a downstream PS/Runtime loss. PS and Runtime behave consistently with BF: rows without BF targets become zero-quantity `NO_ORDER`.

## No-Change Cause

Post-CO Day-0 holdings match Post-CJ because all Day-0 reduced-quality sub-lot rows are still stopped by the legacy/PC lot-aware quality ceiling before CO can emit explicit one-lot decisions.

Classification:

`C. CO authority producer/consumer migration gap`

With one additional nuance:

- The common frontier/BF/PS production consumer path is active.
- The CO one-lot authority path is not active for the actual sub-lot reduced-quality rows.

Therefore `CO_ACTUAL_PATH_ACTIVE = PARTIAL`.

## Defect / Repair Readiness

The artifact evidence supports a narrow repair, not threshold tuning:

- Preserve CH/CJ quality ceiling.
- Preserve CO policy semantics: `ADMIT_ONE_LOT` only gives a one-lot candidate access to common competition.
- Move or duplicate the minimum executable one-lot authority evaluation to the boundary where `quality_authorized_target_weight > 0` and `one_lot_weight > quality_authorized_target_weight` are still visible.
- Do not let PC lot-aware final reallocation collapse those rows to `target_weight = 0` before the explicit authority can emit `ADMIT_ONE_LOT`, `BLOCK`, or `REVIEW_REQUIRED`.
- If the authority emits `BLOCK`, the existing zero result is valid, but it must be explicit and observable.

Longer validation should wait until this actual-path materialization gap is repaired and a new user-operated fresh validation is available.

## Final Judgments

PHASE32_CP_SUBLOT_CANDIDATE_COUNT = 16

PHASE32_CP_ADMIT_ONE_LOT_COUNT = 0

PHASE32_CP_BLOCK_COUNT = 0

PHASE32_CP_REVIEW_REQUIRED_COUNT = 0

PHASE32_CP_ADMITTED_FRONTIER_ACCEPTED_COUNT = 0

PHASE32_CP_CASH_DEFEAT_COUNT = 0

PHASE32_CP_BF_ONE_LOT_TARGET_COUNT = 0

PHASE32_CP_PRIMARY_NO_CHANGE_CAUSE = CO authority producer/consumer migration gap: all reduced-quality sub-lot rows are zeroed by PC lot-aware `lot_minimum_exceeds_quality_authorized_target` before `minimum_executable_one_lot_authority.v1` materializes; no ADMIT/BLOCK/REVIEW_REQUIRED one-lot decision reaches CC/BF.

PHASE32_CP_CO_ACTUAL_PATH_ACTIVE = PARTIAL

PHASE32_CP_MIGRATION_GAP = YES

PHASE32_CP_PRODUCTION_REPAIR_REQUIRED = YES

PHASE32_CP_LONGER_VALIDATION_READY = NO

PHASE32_CP_NEXT_STEP = Narrow repair so reduced-quality sub-lot NEW/REENTRY rows with positive quality-authorized targets are evaluated by `minimum_executable_one_lot_authority.v1` before PC lot-aware zeroing; keep CH/CJ quality bounds, CO explicit authority, common frontier competition, and no legacy fallback.
