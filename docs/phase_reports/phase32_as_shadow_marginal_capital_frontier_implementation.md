# Phase32-AS - Shadow Marginal Capital Frontier Implementation

## Executive Summary

Implemented the AR design as a shadow-only, non-authoritative Strategy module:

```text
src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py
```

Canonical artifact:

```text
canonical_marginal_capital_frontier.v1
```

The implementation builds a same-date Portfolio Construction-owned shadow frontier containing:

- `NEW_FIRST_LOT`
- `REENTRY_FIRST_LOT`
- `ADD_NEXT_LOT`
- `CASH_OPTIONALITY`

ADD is generated as repeated independent next-lot candidates:

```text
current quantity -> next lot #1
next lot #1 -> next lot #2
next lot #2 -> next lot #3
...
```

Each candidate preserves:

- stable candidate identity;
- desirability evidence;
- feasibility evidence;
- hard constraints;
- observability / fail-closed review states;
- PIT-safe lineage;
- hypothetical post-lot quantity / weight / Cash / headroom;
- strongest alternative and Cash comparison;
- shadow disposition.

The artifact is explicitly inert:

```text
artifact_mode = SHADOW_NON_AUTHORITATIVE
production_consumer_count = 0
feeds_position_sizing = false
feeds_runtime_planning = false
feeds_pending = false
feeds_orders = false
feeds_execution = false
feeds_safety_authority = false
production_behavior_changed = false
```

No production target weight, Position Sizing authority, Runtime Planning, Pending, Orders, Execution, Safety authority, PM behavior, PS behavior, Runtime behavior, Safety behavior, REDUCE, EXIT, Cash, Risk Pacing, MCC threshold, fresh run, resume, replay, or backtest was changed.

## Implementation

New module:

- `src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py`

Primary APIs:

| API | Purpose |
| --- | --- |
| `build_canonical_marginal_capital_frontier_payload()` | Builds the shadow artifact from existing decision-time payloads. |
| `write_canonical_marginal_capital_frontier_artifact()` | Writes a JSON artifact atomically. |
| `materialize_canonical_marginal_capital_frontier_for_day()` | Optional day-level artifact materializer under `diagnostic_shadow`. |
| `stable_payload_hash()` | Deterministic artifact hash. |
| `assert_shadow_frontier_not_production_consumer()` | Focused guard that the artifact is not wired as production authority. |

The implementation uses a structured partial-order representation rather than an opaque scalar score:

```text
comparison_representation = STRUCTURED_PARTIAL_ORDER
```

## Candidate Semantics

| Semantic type | Implementation |
| --- | --- |
| `NEW_FIRST_LOT` | Generated from non-held BUY_NEW / ADD_CANDIDATE evidence. |
| `REENTRY_FIRST_LOT` | Generated from non-held REENTRY evidence and preserves recovery/prior-exit context fields when present. |
| `ADD_NEXT_LOT` | Generated from held PM ADD rows as one object per executable lot. |
| `CASH_OPTIONALITY` | Always generated as a first-class frontier candidate. |

PM ADD remains evidence, not capital authority. Position Sizing remains the production quantity owner.

## Desirability / Feasibility Separation

Every security candidate has separate sections:

| Section | Meaning |
| --- | --- |
| `desirability` | Opportunity, rank, quality, continuation, recovery, incremental value, and Cash opportunity-cost evidence. |
| `risk_modifiers` | Current/post-lot weight, cap/headroom, market/risk context, downside context. |
| `feasibility` | Price, lot quantity, notional, available Cash, and cap feasibility. |
| `constraints` | Safety, Risk Pacing, cap, insufficient Cash, no-loss-averaging, campaign identity. |
| `observability` | Missing price, portfolio value, campaign identity, candidate/opportunity evidence. |

High desirability plus a hard block remains observable as high desirability plus infeasible/ineligible, not collapsed to low value.

## Repeated ADD / Diminishing Context

For ADD, the implementation recomputes hypothetical state per increment:

- `pre_quantity`
- `post_quantity`
- `pre_weight`
- `post_weight`
- `increment_weight`
- `cash_before`
- `cash_after`
- `headroom_before`
- `headroom_after`

The generation limit is recorded as:

```text
add_lot_generation_limit_type = SHADOW_ENGINEERING_OBSERVABILITY_BOUND_NOT_INVESTMENT_POLICY
```

This is not a production investment rule and does not authorize a fixed ADD quantity.

## Fail-Closed Conditions

Implemented explicit shadow dispositions include:

| Condition | Disposition |
| --- | --- |
| Safety block | `INELIGIBLE_SAFETY_BLOCKED` |
| Risk Pacing block | `INELIGIBLE_RISK_PACING_BLOCKED` |
| cap/headroom block | `INFEASIBLE_CAP_BLOCKED` |
| insufficient Cash | `INFEASIBLE_INSUFFICIENT_CASH` |
| missing price/lot quantity | `INFEASIBLE_LOT` |
| missing ADD campaign identity | `REVIEW_REQUIRED` |
| no-loss-averaging rejection | `INELIGIBLE_NO_LOSS_AVERAGING_REJECTION` |

Fail-open is not permitted.

## SoT Updates

Updated architecture notes:

- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

The updates only materialize the shadow artifact identity and preserve the non-authoritative boundary. They do not promote the artifact to production authority.

## Tests

New focused regression file:

```text
tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py
```

Coverage:

- NEW candidate generation;
- REENTRY candidate generation;
- ADD next-lot #1/#2/#3 generation;
- hypothetical post-lot state recomputation;
- diminishing headroom / Cash behavior;
- Cash wins;
- cap blocked;
- insufficient Cash;
- Safety block;
- Risk Pacing block;
- missing campaign identity fail-closed;
- stable IDs;
- deterministic rerun;
- forbidden future/outcome fields excluded from lineage;
- shadow artifact cannot become a production consumer.

Verification run:

```text
python3 -m pytest -q tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py
```

Result:

```text
8 passed
```

Compatibility checks:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py
```

Result:

```text
PASS
```

Nearby existing focused regressions:

```text
python3 -m pytest -q \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py \
  tests/strategy/test_phase31_g113_add_marginal_competition_shadow.py \
  -k 'not actual_76470'
```

Result:

```text
19 passed, 1 deselected
```

The deselected `actual_76470` test depends on a historical fixture path that is not present in this workspace:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T072702567342Z/daily/2022-12-06/strategy/portfolio_construction.json
```

Running the full G113 file without the deselection produced that local `FileNotFoundError`; the synthetic G113 tests passed.

## Production Boundary Verification

Repository grep after implementation shows `common_marginal_capital_frontier_shadow` references only in:

- the new module;
- the new focused test;
- the two SoT notes;
- this implementation report.

No production planning, Position Sizing, Pending, Submit, Execution, Runtime, or Safety consumer imports the new module.

## Ready State

AS is ready for shadow characterization. Production activation is not ready and was not attempted.

Recommended next task:

```text
Phase32-AT - Shadow Marginal Capital Frontier Artifact-Only Characterization
```

Scope should be artifact-only materialization/characterization on selected completed days, with no production consumers and no fresh-run/resume/replay/backtest.

## Final Judgments

```text
PHASE32_AS_SHADOW_FRONTIER_IMPLEMENTED = YES
PHASE32_AS_NEW_FIRST_LOT_IMPLEMENTED = YES
PHASE32_AS_REENTRY_FIRST_LOT_IMPLEMENTED = YES
PHASE32_AS_ADD_NEXT_LOT_IMPLEMENTED = YES
PHASE32_AS_REPEATED_ADD_IMPLEMENTED = YES
PHASE32_AS_CASH_CANDIDATE_IMPLEMENTED = YES

PHASE32_AS_DESIRABILITY_FEASIBILITY_SEPARATED = YES
PHASE32_AS_PIT_SAFE = YES
PHASE32_AS_DETERMINISTIC = YES
PHASE32_AS_PRODUCTION_CONSUMER_COUNT = 0
PHASE32_AS_PRODUCTION_BEHAVIOR_CHANGED = NO

PHASE32_AS_REGRESSION_STATUS = PASS
PHASE32_AS_READY_FOR_SHADOW_CHARACTERIZATION = YES
PHASE32_AS_PRODUCTION_ACTIVATION_READY = NO
PHASE32_AS_NEXT_STEP = Phase32-AT - Shadow Marginal Capital Frontier Artifact-Only Characterization
```
