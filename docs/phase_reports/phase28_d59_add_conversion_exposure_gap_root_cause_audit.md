# Phase28-D59 ADD Conversion Funnel / Exposure Gap Root Cause Audit

## Primary Judgment

```text
PHASE28_D59_MULTI_CAUSAL_EXPOSURE_GAP_CONFIRMED
```

Target run:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260809T010010445473Z
```

This was a read-only audit. No implementation, config, schema, threshold, runtime artifact, resume, fresh run, or long historical execution was performed.

## Evidence Scope

The audit used existing artifacts only:

- `daily/*/strategy/portfolio_construction.json`
- `daily/*/strategy/position_sizing.json`
- `daily/*/strategy/runtime_planning.json`
- `daily/*/morning/planning_evidence.json`
- `daily/*/execution/fills.json`
- `daily/*/position_management/pm_decisions.json`

The run directory contains daily directories through `2023-07-25`; the final directory does not contain strategy PC evidence, so funnel counts are based on existing Portfolio Construction artifacts.

## ADD Funnel

Observed from active Runtime evidence:

| Stage | Count |
| --- | ---: |
| PM ADD rows visible in active Portfolio Construction | 142 |
| D55-A final ADD eligibility PASS | 69 |
| D55-A final ADD eligibility FAIL / fail-closed | 73 |
| D55-A PASS with requested incremental weight > 0 | 23 |
| Budget accepted > 0 | 23 |
| Lot-aware accepted > 0 | 11 |
| PC final target > current for existing-position ADD | 11 |
| PS positive BUY_ADD quantity delta | 4 |
| Runtime BUY_ADD plan | 4 |
| Runtime BUY_ADD fill | 3 |

The user-provided expectation was `136 / 66 / 10 / 3`. Existing artifacts in the target run show `142 / 69 / 11 / 4`, with 3 BUY_ADD fills. The difference is evidence-scope based, not a new execution.

## D55-A PASS Classification

For the 69 D55-A PASS rows:

| Class | Meaning | Count |
| --- | --- | ---: |
| A | target/current collision; requested increment is 0 | 46 |
| B | requested and budget accepted > 0, but lot-aware/final target returns to current | 12 |
| C | PC positive final target, but PS quantity delta is 0 | 7 |
| D | PS positive but Runtime BUY_ADD not formed | 0 |
| E | Runtime BUY_ADD formed but no BUY fill | 1 |
| F | Runtime BUY_ADD formed and filled | 3 |

D55-A itself is not the main residual blocker after D58. The confirmed post-D55 bottlenecks are dynamic target/current-position collision, lot-aware incremental conversion loss, and a smaller PC-to-PS quantity conversion loss.

## Dynamic Target vs Existing Weight Collision

Confirmed.

`46 / 69` D55-A PASS rows have:

```text
requested_incremental_weight = 0
target_weight = current_weight
runtime_planning_intent = NO_ACTION
```

Representative cases:

- `94320 / 2023-04-05`: current `0.127320`, target `0.127320`, request `0`
- `76470 / 2023-05-09`: current `0.182409`, target `0.182409`, request `0`

This means ADD eligibility can pass while the active target-weight contract still produces no incremental exposure request.

## Lot-Aware Increment Loss

Confirmed.

`12 / 69` D55-A PASS rows have:

```text
requested_incremental_weight > 0
accepted_incremental_weight > 0
lot_aware_accepted_incremental_weight = 0
target_weight = current_weight
```

Required examples:

- `30410 / 2023-05-24`: request `0.025235`, accepted `0.025235`, lot-aware `0`
- `30410 / 2023-05-25`: request `0.055501`, accepted `0.055501`, lot-aware `0`
- `30410 / 2023-05-29`: request `0.033250`, accepted `0.033250`, lot-aware `0`
- `30410 / 2023-05-30`: request `0.010781`, accepted `0.010781`, lot-aware `0`
- `76470 / 2023-05-08`: request `0.006543`, accepted `0.006543`, lot-aware `0`
- `76470 / 2023-07-12`: request `0.005470`, accepted `0.005470`, lot-aware `0`

`94320` also appears in lot-aware-zero cases, but the dominant `94320` pattern is request-zero collision.

## PC Positive to PS Zero

Confirmed.

`7 / 69` D55-A PASS rows survive PC with a positive final target but produce zero PS transaction quantity. Representative:

```text
21340 / 2023-06-08
current_weight = 0.065571
target_weight = 0.112141
lot_aware_accepted_incremental_weight = 0.046570
PS quantity_delta_candidate = 0
Runtime = NO_ACTION
```

This is downstream of PC and distinct from D55-A evidence availability.

## Runtime BUY_ADD and Fill

Runtime BUY_ADD was formed 4 times:

- `94320 / 2023-04-17`: planned `300`, filled `300`
- `59550 / 2023-06-19`: planned `600`, filled `0`
- `59550 / 2023-06-20`: planned `500`, filled `500`
- `76470 / 2023-07-20`: planned `2400`, filled `2400`

Submit/fill is not the primary ADD exposure gap. Three of four Runtime BUY_ADD plans filled; one did not have a BUY fill in `execution/fills.json`.

## Adaptive Buy Quality

Adaptive Buy Quality is present in the chain, but the existing evidence does not support it as the primary over-suppression cause.

For D55-A PASS rows, request-zero and lot-aware-zero cases occur under both `REDUCED_ALLOCATION_ONLY` and `FULL_ALLOCATION_ELIGIBLE`. For example, `30410 / 2023-05-24` is `FULL_ALLOCATION_ELIGIBLE` but still lot-aware zeroes the accepted increment.

Judgment:

```text
ADAPTIVE_QUALITY_OVER_SUPPRESSION_NOT_PRIMARY_CONFIRMED_BY_EXISTING_EVIDENCE
```

## BUY_NEW Comparison

BUY_NEW path behaves materially differently:

| BUY_NEW Stage | Count |
| --- | ---: |
| ADD_CANDIDATE rows | 115 |
| requested_buy_new_weight > 0 | 115 |
| lot_aware_accepted_buy_new_weight > 0 | 28 |
| Runtime BUY_NEW | 23 |
| BUY_NEW fill | 19 |

Unlike ADD, BUY_NEW always begins with a positive request in this run. It still has lot-aware attrition, but it does not suffer the same dominant target/current collision.

## Root Cause

The exposure gap is multi-causal:

1. D58 made ADD baseline supply effective enough for D55-A to pass in 69 rows.
2. Most passing ADD rows never request incremental exposure because current weight already collides with the active target-weight output.
3. A second group requests and accepts incremental budget but is zeroed by lot-aware conversion before PS.
4. A smaller group remains positive through PC but is converted to zero quantity in PS.
5. Runtime Planning, Pending, Submit, and Fill are not the dominant loss producers for ADD in this evidence set.

## D58 Relation

D58 is effective but not sufficient. It repairs the same-campaign baseline supply path and allows D55-A PASS rows to exist. D59 shows the next loss points are downstream capital conversion and target/lot/quantity realization.

## Minimal Next Scope

```text
Phase28-D60
```

D60 should design the minimal production-common repair for ADD capital conversion after D58, focusing on:

- dynamic target/current-position collision semantics for ADD
- lot-aware incremental conversion semantics
- PC-positive to PS-zero quantity conversion

It should not change thresholds, broker eligibility, Submit Guard, SELL planning, or D55-A evidence semantics.

## Deliverables

- `reports/phase28_d59_add_conversion_exposure_gap_root_cause_audit/add_conversion_funnel_summary.json`
- `reports/phase28_d59_add_conversion_exposure_gap_root_cause_audit/add_event_classification_full.json`
- `reports/phase28_d59_add_conversion_exposure_gap_root_cause_audit/d55a_pass_classification.json`
- `reports/phase28_d59_add_conversion_exposure_gap_root_cause_audit/daily_exposure_gap_attribution.json`
- `reports/phase28_d59_add_conversion_exposure_gap_root_cause_audit/lot_aware_zeroing_audit.json`
- `reports/phase28_d59_add_conversion_exposure_gap_root_cause_audit/adaptive_buy_quality_impact.json`
- `reports/phase28_d59_add_conversion_exposure_gap_root_cause_audit/buy_new_comparison.json`
- `reports/phase28_d59_add_conversion_exposure_gap_root_cause_audit/representative_case_traces.json`
- `reports/phase28_d59_add_conversion_exposure_gap_root_cause_audit/object_lineage_manifest.json`
- `reports/phase_reports/phase28_d59_add_conversion_exposure_gap_root_cause_audit.json`

## Execution Flags

```text
Implementation changed = NO
Config changed = NO
Schema changed = NO
Threshold changed = NO
Runtime mutated = NO
Resume executed = NO
Fresh executed = NO
Long Historical executed = NO
```
