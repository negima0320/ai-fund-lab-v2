# Phase32-BE Consumer Switch Dry-Run Validation

## Executive Summary

Phase32-BE performed a READ-ONLY / consumer-disabled dry-run validation for
the Phase32-BC budget-bounded authority:

```text
canonical_marginal_capital_frontier_authority.v1
```

Target run:

```text
runtime-test-historical-extended-smoke-20260828T000823285458Z
```

No production consumer switch, production code change, runtime state mutation,
fresh-run, resume, replay, or backtest was executed.

Primary result:

```text
PS dry-run target -> quantity projection PASS.
Runtime mapping lineage PASS.
Capital conservation PASS.
Production quantity divergence remains material.
Consumer switch readiness remains PARTIAL until legacy fallback/deprecation
and PS switch validation are implemented.
```

## Required Inputs

Read:

- `docs/phase_reports/phase32_bd_post_bc_budget_bounded_dual_read_acceptance.md`
- `docs/phase_reports/phase32_bc_budget_bounded_frontier_acceptance_implementation.md`
- `docs/phase_reports/phase32_ay_marginal_capital_frontier_production_migration_design.md`

Actual artifacts read in memory:

- `daily/{date}/strategy/portfolio_construction.json`
- `daily/{date}/strategy/position_sizing.json`
- `daily/{date}/strategy/portfolio_policy.json`
- `daily/{date}/current_valuation_refresh/valuation_projection.json`
- `daily/{date}/current_valuation_refresh/safety_authority_decision.json`
- `daily/{date}/morning/safety_decision.json`, fallback only

## Coverage

| Field | Value |
| --- | --- |
| Run id | `runtime-test-historical-extended-smoke-20260828T000823285458Z` |
| Characterized days | 50 |
| Coverage start | `2022-10-03` |
| Coverage end | `2022-12-14` |
| Consumer disabled | `YES` |

## Dry-Run Quantity Projection

BC accepted target rows:

| Type | Target count | Projected quantity |
| --- | ---: | ---: |
| `NEW_FIRST_LOT` | 182 | 38,800 |
| `REENTRY_FIRST_LOT` | 26 | 2,600 |
| `ADD_NEXT_LOT` | 93 | 9,300 |
| Total | 301 | 50,700 |

Validation:

| Check | Result |
| --- | ---: |
| Positive dry-run quantity rows | 301 / 301 |
| Zero quantity rows | 0 |
| Runtime/Pending lineage-compatible rows | 301 / 301 |
| Missing accepted candidate lineage | 0 |
| Missing ADD campaign lineage | 0 |
| Missing source decision lineage | 0 |

No lot-rounding zero was observed. All accepted targets already carry the
candidate increment quantity from the frontier candidate surface.

## Production Quantity Divergence

Existing production PS quantities were compared to BC dry-run projected
quantities.

| Metric | Count |
| --- | ---: |
| Same quantity | 111 |
| Different quantity | 190 |

Quantity divergence by type:

| Type | Divergent rows |
| --- | ---: |
| `NEW_FIRST_LOT` | 100 |
| `REENTRY_FIRST_LOT` | 24 |
| `ADD_NEXT_LOT` | 66 |
| Total | 190 |

Interpretation:

- Dry-run PS conversion is internally coherent.
- Production output would change materially if the consumer were switched.
- This is expected at dry-run stage and is not a behavior change because the
  consumer remains disabled.

## ADD Multi-Lot Quantity

Representative cumulative ADD dry-run quantity examples:

| Date | Symbol | Campaign | Lots | Cumulative dry-run qty |
| --- | --- | --- | --- | ---: |
| `2022-10-05` | `94340` | `pc-993d47f0f8d7e622-94340-0001` | `200->300`, `300->400`, `400->500` | 300 |
| `2022-10-07` | `94320` | `pc-e0c5da196f07ea55-94320-0001` | `200->300`, `300->400`, `400->500` | 300 |
| `2022-10-12` | `94320` | `pc-e0c5da196f07ea55-94320-0001` | `200->300`, `300->400`, `400->500` | 300 |
| `2022-10-12` | `94340` | `pc-993d47f0f8d7e622-94340-0001` | `300->400`, `400->500`, `500->600` | 300 |
| `2022-10-19` | `94320` | `pc-e0c5da196f07ea55-94320-0001` | `300->400`, `400->500`, `500->600` | 300 |

Important interpretation:

```text
ADD target_quantity is cumulative per accepted lot.
ADD accepted_incremental_quantity is the executable delta per step.
Runtime/PS migration must consume the acceptance sequence or aggregate per
symbol/campaign before emitting a final order quantity.
```

The per-row cumulative representation is compatible, but the consumer switch
must aggregate ADD rows by symbol/campaign to avoid treating lot #2/#3 as
independent current baselines.

## Cash / Budget Conservation

| Check | Result |
| --- | ---: |
| Budget authority PASS | 50 / 50 |
| Capital conservation PASS | 50 / 50 |
| Explicit Cash allocation days | 50 / 50 |
| Budget stop reason | `STOP_BUDGET_EXHAUSTED_TO_CASH` on 50 days |

Cash remains first-class and receives all unallocated budget after accepted
security lots.

## Guardrails

| Guardrail | Count |
| --- | ---: |
| Cap blocked candidates | 279 |
| Cash blocked candidates | 426 |
| Safety blocked candidates | 0 |
| Risk Pacing blocked candidates | 0 |
| No-loss-averaging blocked candidates | 0 |

Safety and Risk Pacing did not fire in this sample; they were not bypassed.

## Determinism / PIT

| Check | Result |
| --- | --- |
| Deterministic rerun hash | PASS, 50 / 50 |
| Stable payload hash | PASS, 50 / 50 |
| Future/outcome forbidden field scan | PASS, 0 findings |
| Historical outcome parameter selection | NO |

## Runtime Mapping Compatibility

Runtime mapping is compatible in dry-run form because each accepted target
contains:

- `symbol`
- `semantic_type`
- `accepted_incremental_quantity`
- `accepted_incremental_weight`
- `target_gap`
- `accepted_frontier_candidate_ids`
- `source_candidate_id` or `source_pm_decision_id`
- `position_campaign_id` for ADD
- `remaining_budget_before/after`
- `remaining_cash_before/after`

The only required migration caveat is ADD aggregation. Runtime must receive one
net quantity delta per symbol/side after PC/PS aggregation, not one independent
order per cumulative ADD target row unless the future implementation explicitly
chooses staged lot orders.

## Legacy Path Classification

| Existing path | Classification after switch | Notes |
| --- | --- | --- |
| PM ADD intent producer | KEEP | Evidence producer only. |
| Candidate / quality / rank evidence | KEEP | PIT evidence only. |
| `canonical_marginal_capital_frontier.v1` | KEEP | Shadow diagnostic, production consumer count must remain 0. |
| `canonical_marginal_capital_frontier_authority.v1` | MIGRATE | Future PC target-gap authority once consumer switch is accepted. |
| Existing PC target-gap builder | MIGRATE | Must consume accepted BC authority targets or host equivalent logic. |
| Existing ADD allocation bridge / zero-gap path | DEPRECATE | Must not remain as fallback zero after switch. |
| Existing `canonical_multi_allocation_deployment_set` | MIGRATE | Should carry budget-bounded accepted increments and Cash allocation. |
| Existing PS target-to-quantity conversion | KEEP | Quantity authority remains PS. |
| Runtime Planning | KEEP | Maps PS quantity deltas only. |
| Pending / Submit / Orders / Execution | KEEP | No capital priority redecision. |
| Safety / Risk Pacing / REDUCE / EXIT | KEEP | Authority unchanged. |
| Legacy fallback to old target-gap path | REMOVE for switched rows | Fail closed instead of falling back. |

## No-Fallback Judgment

Current artifacts still contain the old production PC / multi-allocation path:

```text
old_multi_allocation_present = 50 / 50
production_consumer_connected = 50 / 50
legacy_authority_active = 0 / 50
```

This is expected before the switch. It means no-fallback-after-switch is not
yet proven in production wiring. The migration requirement is clear:

```text
After switch, old ADD compression / target-gap zero path must not silently
override BC accepted targets. Missing or invalid BC authority must fail closed
to REVIEW_REQUIRED instead of falling back.
```

## Consumer Switch Readiness

Ready:

- target -> quantity projection;
- multi-lot ADD quantity examples;
- NEW / REENTRY quantity;
- campaign/source lineage;
- Runtime/Pending lineage shape;
- explicit Cash allocation;
- capital conservation;
- PIT/determinism/future-field scan.

Not fully ready:

- production quantity divergence remains material: 190 rows;
- ADD cumulative rows require aggregation semantics at PC/PS switch boundary;
- legacy fallback removal is specified but not implemented/proven;
- no switched-row dry-run validator exists yet at the PC -> PS artifact
  boundary.

## Final Judgments

```text
PHASE32_BE_PS_DRY_RUN_PASS = YES
PHASE32_BE_MULTI_LOT_QUANTITY_PASS = YES
PHASE32_BE_RUNTIME_MAPPING_COMPATIBLE = YES
PHASE32_BE_LINEAGE_COMPLETE = YES
PHASE32_BE_CAPITAL_CONSERVATION = PASS
PHASE32_BE_GUARDRAILS_PRESERVED = YES
PHASE32_BE_LEGACY_FALLBACK_ZERO_AFTER_SWITCH = PARTIAL
PHASE32_BE_CONSUMER_SWITCH_READY = PARTIAL
PHASE32_BE_PRODUCTION_BEHAVIOR_CHANGED = NO
PHASE32_BE_NEXT_STEP = Implement a consumer-disabled PC-to-PS switch validator that aggregates accepted BC targets by symbol/campaign, proves no legacy zero fallback for switched rows, and compares final net quantity deltas before enabling the production consumer.
```
