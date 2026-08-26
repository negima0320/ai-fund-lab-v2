# Phase31-G113 — Canonical ADD Marginal Capital Competition Shadow Implementation

## Judgment

PRIMARY_JUDGMENT = G113_ADD_MARGINAL_COMPETITION_SHADOW_IMPLEMENTED_READY_FOR_REVIEW

G113 implemented Portfolio Construction owned `canonical_add_marginal_capital_competition.v1` as SHADOW / NON-AUTHORITATIVE evidence.

AUTHORITATIVE_BEHAVIOR_CHANGED = NO

PS_CHANGED = NO

Runtime_CHANGED = NO

Submit_CHANGED = NO

Execution_CHANGED = NO

## Implementation

Added shadow evidence under:

```text
portfolio_construction.capital_competition.canonical_add_marginal_capital_competition
```

Schema:

```text
canonical_add_marginal_capital_competition.v1
```

The shadow evidence models ADD increments against:

- final eligible NEW_BUY frontier
- eligible ADD frontier
- Cash
- residual optionality

It does not feed Position Sizing, Runtime Planning, Submit, Execution, ledger, current projection, or Pending.

Permanent SoT updated:

```text
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
```

## Contract Semantics

The shadow contract separates:

```text
CASH_PREFERRED_PARTICIPATION_VALID
```

from:

```text
ADD_MARGINAL_CAPITAL_BEATS_CASH
```

`CASH_PREFERRED_PARTICIPATION_VALID` now remains visible as reduced participation evidence, but it does not imply that an ADD increment strictly beats Cash.

Each ADD candidate is expanded into executable marginal increments using canonical lot context. The shadow rows carry:

- pre_increment_quantity
- post_increment_quantity
- pre_increment_weight
- post_increment_weight
- remaining_strategy_headroom
- remaining_safety_headroom
- executable_lot_size
- one_lot_weight

No actual portfolio state is mutated.

## Primary 76470 Reconstruction

Target run:

```text
runtime-test-historical-extended-smoke-20260825T072702567342Z
```

Producer-equivalent reconstruction from existing artifacts:

| Date | Authoritative ADD block count | Authoritative ADD weight | 76470 shadow increments | ADD_MARGINAL_PREFERRED | COMPARABLE_MARGINAL | CASH_MARGINAL_PREFERRED | INSUFFICIENT_EVIDENCE |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2022-12-06 | 1 | 0.031250 | 13 | 0 | 13 | 0 | 0 |
| 2022-12-21 | 1 | 0.024667 | 10 | 0 | 10 | 0 | 0 |
| 2023-01-04 | 1 | 0.023871 | 9 | 0 | 9 | 0 | 0 |

Interpretation:

The existing authoritative ADD blocks remain unchanged. The new shadow evidence shows the ADD increments as observable lot-level decisions and classifies them as `COMPARABLE_MARGINAL` rather than treating `CASH_PREFERRED_PARTICIPATION_VALID` as proof that ADD beats Cash.

Later 76470 PnL was not used as a decision input.

## Aggregate Characterization

Production `strategy` artifact path, completed existing dates in target run:

| Metric | Count |
|---|---:|
| completed dates evaluated | 125 |
| ADD dates with shadow increments | 27 |
| AUTHORITATIVE_ADD_BLOCK_COUNT | 22 |
| SHADOW_INCREMENT_COUNT | 205 |
| SHADOW_ADD_MARGINAL_PREFERRED_COUNT | 13 |
| SHADOW_COMPARABLE_MARGINAL_COUNT | 125 |
| SHADOW_CASH_MARGINAL_PREFERRED_COUNT | 0 |
| SHADOW_SAFETY_TERMINAL_COUNT | 0 |
| SHADOW_LOT_INFEASIBLE_COUNT | 0 |
| SHADOW_INSUFFICIENT_EVIDENCE_COUNT | 67 |

Symbol coverage from production `strategy` path:

| Symbol | Shadow increments | ADD_MARGINAL_PREFERRED | COMPARABLE_MARGINAL | INSUFFICIENT_EVIDENCE |
|---|---:|---:|---:|---:|
| 76470 | 169 | 13 | 103 | 53 |
| 94320 | 20 | 0 | 15 | 5 |
| 94340 | 7 | 0 | 7 | 0 |
| 45940 | 9 | 0 | 0 | 9 |

`99840` was not present in the production `strategy` path for this run window. The same run's `strategy_eod_shadow` evidence was also evaluated to satisfy the 5-symbol generality requirement:

| Symbol | Shadow increments | Classification summary |
|---|---:|---|
| 76470 | 160 | 144 INSUFFICIENT_EVIDENCE, 16 COMPARABLE_MARGINAL |
| 94320 | 19 | 10 INSUFFICIENT_EVIDENCE, 9 COMPARABLE_MARGINAL |
| 99840 | 5 | 5 LOT_INFEASIBLE |
| 94340 | 6 | 4 COMPARABLE_MARGINAL, 2 INSUFFICIENT_EVIDENCE |
| 45940 | 9 | 9 INSUFFICIENT_EVIDENCE |

SHADOW_GENERAL_ACROSS_ADD = YES

## Multiple-ADD Frontier

Focused regression proves ADD-vs-ADD competition on a deterministic same-date PIT fixture with:

- two eligible ADD competitors
- one eligible NEW_BUY competitor
- Cash
- residual optionality

Actual run evidence also shows multiple ADD candidates in available shadow artifacts, including:

- 2022-10-12: 94320 / 94340
- 2022-11-01: 94320 / 99840 in `strategy_eod_shadow`

Some requested example dates in production `strategy` path had zero eligible ADD frontier after final PC selection:

- 2022-11-24
- 2023-03-08
- 2023-03-22

This is recorded as evidence shape, not as a G113 implementation failure.

## Preservation

G90_CHANGED = NO

G97_CHANGED = NO

G99_CHANGED = NO

G102_CHANGED = NO

G104_CHANGED = NO

G110_CHANGED = NO

PM_ADD_ELIGIBILITY_CHANGED = NO

NORMAL_BUY_CHANGED = NO

SELL_REDUCE_EXIT_CHANGED = NO

SAFETY_CHANGED = NO

PS_QUANTITY_AUTHORITY_CHANGED = NO

RUNTIME_PRIORITY_CHANGED = NO

SUBMIT_CHANGED = NO

EXECUTION_CHANGED = NO

G93_DEAD_END_RETURNED = NO

## Required Judgments

CANONICAL_ADD_MARGINAL_SHADOW_IMPLEMENTED = YES

AUTHORITATIVE_BEHAVIOR_CHANGED = NO

ADD_VS_ADD_FRONTIER_COMPLETE = YES

ADD_VS_NEW_BUY_FINAL_FRONTIER_COMPLETE = YES

CASH_FIRST_CLASS_IN_MARGINAL_FRONTIER = YES

RESIDUAL_CASH_ALLOWED = YES

MARGINAL_LOT_REEVALUATION_PRESENT = YES

POSITION_SIZE_AWARE_INCREMENT_STATE = YES

SAFETY_TERMINAL_RESURRECTION_COUNT = 0

CAP_INFEASIBLE_RESURRECTION_COUNT = 0

LOT_INFEASIBLE_RESURRECTION_COUNT = 0

FUTURE_INFORMATION_USED = NO

HISTORICAL_OUTCOME_USED = NO

SHADOW_GENERAL_ACROSS_ADD = YES

SHADOW_READY_FOR_AUTHORITATIVE_REVIEW = YES

## Tests

Focused G113 regression:

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g113_add_marginal_competition_shadow.py
```

Result:

```text
4 passed
```

Py compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase31_g113_add_marginal_competition_shadow.py
```

Result:

```text
PASS
```

ADD bridge / ADD investment evidence:

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py -k 'add_evidence or canonical_add_bridge or add_bridge or add'
```

Result:

```text
27 passed, 95 deselected
```

G104 / Submit discrete quantity consumer subset:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -k 'g104 or ak9r1b or ak9r21'
```

Result:

```text
20 passed, 20 deselected
```

Nearby PC regression batch:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase31_g90_cash_preferred_aggregate_resolver.py \
  tests/strategy/test_phase31_g95_residual_reconsideration_shadow.py \
  tests/strategy/test_phase31_g97_residual_reconsideration_authoritative_binding.py \
  tests/strategy/test_phase31_g99_reconsideration_lot_context_propagation.py \
  tests/strategy/test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py
```

Result:

```text
18 passed, 4 failed
```

The four failures are missing-artifact failures for older run ids not present in this workspace:

- runtime-test-historical-extended-smoke-20260824T121719329586Z
- runtime-test-historical-extended-smoke-20260824T203644021876Z

No assertion failure from G113 behavior was observed in that batch.

## Final Decision

G113_ADD_MARGINAL_COMPETITION_SHADOW_IMPLEMENTED_READY_FOR_REVIEW

