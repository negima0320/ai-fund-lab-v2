# Phase32-AU - Shadow Frontier Cash Source Resolver Repair

## Executive Summary

Phase32-AU repaired the shadow-only Cash source gap identified in Phase32-AT.
`canonical_marginal_capital_frontier.v1` day-level materialization now resolves
decision-time Cash from same-day authoritative artifacts before building the
frontier.

The repair is narrow:

- changed only the shadow frontier materializer / payload builder;
- added focused AU regression coverage;
- documented the durable Cash resolver contract in the relevant Architecture
  SoT sections;
- did not connect the shadow artifact to production target weights, Position
  Sizing, Runtime Planning, Pending, Orders, Execution, Safety, REDUCE, EXIT,
  Cash policy, or thresholds.

Primary AT defect addressed:

```text
Top-level Portfolio Construction Cash absence no longer collapses broad shadow
materialization into false INFEASIBLE_INSUFFICIENT_CASH.
```

## Inherited AT Finding

Phase32-AT showed that the AS frontier became useful when Cash was manually
supplied from existing decision-time artifacts:

- `strategy/portfolio_policy.json`
- `current_valuation_refresh/valuation_projection.json`

Without that source adapter, broad characterization could treat missing top
level PC Cash as zero, making securities appear Cash-infeasible for the wrong
reason.

## Implementation

Changed:

- `src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py`

Added:

- `tests/strategy/test_phase32_au_shadow_frontier_cash_source_resolver.py`

Updated Architecture SoT:

- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

New public resolver:

```text
resolve_shadow_cash_state_for_day()
```

Day-level materialization now loads:

```text
daily/{date}/strategy/portfolio_policy.json
daily/{date}/current_valuation_refresh/valuation_projection.json
daily/{date}/strategy/portfolio_construction.json
```

and stores Cash source status / lineage in the shadow payload:

```text
cash_source_status
cash_source_lineage
cash_state_ref
```

## Cash Source Priority

Deterministic same-day priority:

| Priority | Source |
| ---: | --- |
| 1 | `strategy/portfolio_policy.json#current_cash_summary` |
| 2 | `strategy/portfolio_policy.json#portfolio_policy_allocation_authority.cash_context` |
| 3 | `strategy/portfolio_policy.json#portfolio_policy_allocation_authority.available_cash_context` |
| 4 | `current_valuation_refresh/valuation_projection.json` |
| 5 | `strategy/portfolio_policy.json#top_level` |
| 6 | `strategy/portfolio_construction.json#top_level` |
| 7 | `strategy/portfolio_construction.json#capital_competition.canonical_multi_allocation_deployment_set.available_incremental_budget` |

The selected source records:

- source role;
- source path;
- source content hash when available;
- source field;
- all observed Cash lineage.

Lower-priority observations are retained as lineage. They do not invalidate a
clean higher-priority source because valuation can represent a fallback stage,
not a coequal authority.

## Fail-Closed Behavior

Missing Cash evidence:

```text
cash_source_status = REVIEW_REQUIRED
cash_source_reason = missing_decision_time_cash_evidence
```

Conflicting evidence inside the selected priority tier:

```text
cash_source_status = REVIEW_REQUIRED
cash_source_reason = conflicting_decision_time_cash_evidence
```

When Cash source status is `REVIEW_REQUIRED`, security candidates and the Cash
optionality candidate also become `REVIEW_REQUIRED`. They are not converted into
`INFEASIBLE_INSUFFICIENT_CASH`, preventing false insufficient-cash collapse.

## Production Boundary

The artifact remains:

```text
artifact_mode = SHADOW_NON_AUTHORITATIVE
production_consumer_count = 0
feeds_position_sizing = false
feeds_runtime_planning = false
feeds_pending = false
feeds_orders = false
feeds_execution = false
feeds_safety_authority = false
production_target_weight_changed = false
production_behavior_changed = false
```

No production strategy behavior was changed.

## Verification

Focused AU / AS regression:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_au_shadow_frontier_cash_source_resolver.py \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py
```

Result:

```text
14 passed
```

Nearby shadow regressions:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_au_shadow_frontier_cash_source_resolver.py \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py \
  tests/strategy/test_phase31_g113_add_marginal_competition_shadow.py \
  -k 'not actual_76470'
```

Result:

```text
25 passed, 1 deselected
```

Compile check:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase32_au_shadow_frontier_cash_source_resolver.py
```

Result:

```text
PASS
```

Focused test coverage includes:

- portfolio_policy Cash resolves;
- valuation fallback resolves;
- conflicting same-priority Cash evidence fails closed;
- missing Cash fails closed;
- broad-day materialization avoids false insufficient-cash collapse;
- deterministic rerun;
- production consumer count remains zero.

## Run Artifact Note

No fresh-run, resume, replay, or backtest was executed. The Phase32-AT target run
directory was not present in the local workspace during AU verification, so AU
did not claim a new artifact-only characterization over that run. The executable
proof for AU is the focused fixture-backed day-level materialization regression.

## Repair Readiness

The repair is ready for broad shadow materialization. The next validation should
rerun the Phase32-AT style artifact-only characterization against an available
run and confirm that broad materialization resolves Cash through the artifact
lineage rather than through manual script injection.

## Final Judgments

PHASE32_AU_CASH_RESOLVER_REPAIRED = YES

PHASE32_AU_PIT_SAFE = YES

PHASE32_AU_FALSE_INSUFFICIENT_CASH_PREVENTED = YES

PHASE32_AU_PRODUCTION_CONSUMER_COUNT = 0

PHASE32_AU_PRODUCTION_BEHAVIOR_CHANGED = NO

PHASE32_AU_REGRESSION_STATUS = PASS

PHASE32_AU_READY_FOR_BROAD_SHADOW_MATERIALIZATION = YES

PHASE32_AU_PRODUCTION_ACTIVATION_READY = NO

PHASE32_AU_NEXT_STEP = Phase32-AV broad shadow materialization / characterization using the repaired Cash resolver.
