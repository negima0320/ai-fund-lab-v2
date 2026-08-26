# Phase31-G115 — ADD Marginal Competition Staged Authoritative Binding

## PRIMARY_JUDGMENT

G115_ADD_MARGINAL_STAGED_AUTHORITATIVE_BINDING_ACCEPTED

## Scope

Implemented the G114-approved `OPTION_B_WITH_OPTION_C_FRONTIER_GUARD + STAGED_PARTIAL_BINDING` boundary in Portfolio Construction.

No fresh-run, resume, replay, or long Historical execution was performed.

## Implementation Summary

- Added `canonical_add_marginal_capital_competition_authority.v1`.
- Preserved G113 `canonical_add_marginal_capital_competition.v1` as shadow evidence.
- Added PC-owned authoritative staged rows with:
  - `authority_status = AUTHORITATIVE_STAGED_PC_BINDING`
  - `frontier_iteration`
  - `increment_id`
  - `symbol`
  - `classification`
  - pre/post quantity and weight
  - lot size and one-lot weight
  - budget before/after
  - Cash/residual semantics
  - `authorized`
  - future/Historical input flags
- Bound actual lot-aware final reallocation so `BUY_ADD` requested blocks are reduced to one executable ADD increment before PS consumption.
- Preserved PC as marginal frontier / capital allocation owner.
- Preserved PM as ADD intent and eligibility owner.
- Preserved PS as discrete quantity owner.
- Preserved Runtime as consumer only.

## Acceptance Results

ADD_MARGINAL_STAGED_AUTHORITY_SCHEMA = YES

CANONICAL_ADD_MARGINAL_CAPITAL_COMPETITION_AUTHORITY = YES

AUTHORITY_STATUS = AUTHORITATIVE_STAGED_PC_BINDING

PM_ADD_INTENT_OWNER_PRESERVED = YES

PC_MARGINAL_FRONTIER_OWNER = YES

PS_QUANTITY_AUTHORITY_PRESERVED = YES

RUNTIME_PRIORITY_REDECISION = NO

SUBMIT_ROLE = FEASIBILITY_REVALIDATION_ONLY

NEW_BUY_MARGINAL_NORMALIZATION = PRESENT

ADD_REQUESTED_BLOCK_AUTHORIZATION = NO

ADD_MARGINAL_PREFERRED_ONE_INCREMENT = YES

COMPARABLE_MARGINAL_RESIDUAL_SHOULDER_PARTICIPATION = YES

INSUFFICIENT_EVIDENCE_FAIL_CLOSED = YES

SAFETY_TERMINAL_RESURRECTION_COUNT = 0

LOT_INFEASIBLE_RESURRECTION_COUNT = 0

G90_CHANGED = NO

G97_SEMANTICS_CHANGED = NO

G99_CHANGED = NO

G102_CHANGED = NO

G104_CHANGED = NO

G110_CHANGED = NO

MARKET_QUALITY_CHANGED = NO

RISK_PACING_CHANGED = NO

CANDIDATE_RANKING_CHANGED = NO

ADD_EVIDENCE_PRODUCER_CHANGED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_INPUT_COUNT = 0

## Focused Regression

PASS:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py \
  tests/strategy/test_phase31_g113_add_marginal_competition_shadow.py \
  tests/strategy/test_phase31_g95_residual_reconsideration_shadow.py \
  tests/strategy/test_phase31_g97_residual_reconsideration_authoritative_binding.py \
  tests/strategy/test_phase31_g90_cash_preferred_aggregate_resolver.py \
  tests/strategy/test_phase31_g86_cash_preferred_participation_deferral.py \
  tests/strategy/test_phase31_g83_bootstrap_cash_preference_partition.py \
  tests/strategy/test_phase31_g81_opportunity_aware_security_cash_partition.py \
  tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py \
  tests/strategy/test_phase31_g62_position_sizing_g61_binding.py \
  tests/strategy/test_phase31_g63_runtime_executable_binding.py \
  tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py
```

Result:

```text
51 passed
```

G115 direct regression:

```text
tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py
4 passed
```

G113 compatibility:

```text
tests/strategy/test_phase31_g113_add_marginal_competition_shadow.py
4 passed
```

Artifact-dependent nearby tests:

```text
tests/strategy/test_phase31_g99_reconsideration_lot_context_propagation.py
tests/strategy/test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py
```

were attempted as part of a broader command. Four failures were `FileNotFoundError` for missing historical run artifacts under `reports/runtime_tests/runs/...`; no behavioral assertion failed in those cases.

## Compile / Hygiene

PY_COMPILE = PASS

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py
```

GIT_DIFF_CHECK = PASS

```text
git diff --check
```

## SoT Update

Updated:

```text
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
```

The SoT now records the G115 staged ADD marginal authority boundary:

- `canonical_add_marginal_capital_competition_authority.v1`
- PC owns ADD marginal frontier and staged increment authorization.
- PM owns ADD intent and eligibility.
- PS owns discrete quantity.
- Runtime must not re-decide capital priority.
- Submit remains feasibility/equality validation only.

## Final Required Fields

G115_ADD_MARGINAL_STAGED_AUTHORITATIVE_BINDING_ACCEPTED = YES

AUTHORITATIVE_SCHEMA_IMPLEMENTED = YES

STAGED_PARTIAL_BINDING = YES

ADD_MARGINAL_PREFERRED_AUTHORIZES_EXACTLY_ONE_INCREMENT_PER_BINDING_STEP = YES

COMPARABLE_MARGINAL_FULL_BLOCK_FORBIDDEN = YES

INSUFFICIENT_EVIDENCE_ADD_INCREMENT_BLOCKED_HOLD_PRESERVED = YES

NEW_BUY_COMPETITION_PRESERVED = YES

OPTIONAL_CASH_PRESERVED = YES

PS_QUANTITY_AUTHORITY_CHANGED = NO

RUNTIME_PRIORITY_CHANGED = NO

SUBMIT_CHANGED = NO

SAFETY_CHANGED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

## NEXT

Proceed to user-operated fresh long Historical validation. Do not apply G115 semantics into an already-running historical validation mid-run.
