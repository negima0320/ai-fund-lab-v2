# Phase31-G90 — CASH_PREFERRED Aggregate Participation Resolver Repair

## PRIMARY_JUDGMENT

PHASE31_G90_CASH_PREFERRED_AGGREGATE_PARTICIPATION_RESOLVER_REPAIRED_ACCEPTED

## Scope

Implemented only the Portfolio Construction G86 boundary:

```text
cash_preferred_participation_deferral_resolution.v1
```

No Market Quality, Risk Pacing, Candidate ranking, BUY filter, Strategy threshold, fixed exposure, fixed position count, fixed aggregate percentage cap, Position Sizing quantity authority, Runtime priority logic, Submit, Execution, config, fresh-run, resume, replay, or long Historical behavior was changed.

## Repair Summary

G89 confirmed that the previous resolver over-bound this rule:

```text
same-quality-class non-frontier
-> CASH_PREFERRED_AGGREGATE_WEAK_TAIL_DEFERRAL
-> security = 0
```

G90 changes the contract so same-quality-class frontier is priority context, not exclusive admission. Non-frontier rows are no longer automatically deferred.

New behavior:

```text
same quality class
-> frontier is priority signal
-> row participation credibility evaluated per row
-> multiple credible CASH_PREFERRED rows may survive
-> weaker / contextually dominated rows defer
-> optional Cash remains explicit
```

The resolver still uses only existing same-date PIT evidence already available in PC:

- row evidence completeness
- entry admission action/state/sufficiency
- opportunity quality class
- relative strength / momentum context
- within-class relative priority evidence
- requested security increment
- same-day class confidence distribution
- ADD preservation evidence where applicable
- aggregate Cash-preferred set context

No new Historical score, fixed rank cutoff, fixed confidence cutoff, fixed score cutoff, fixed exposure target, fixed position count, or fixed aggregate cap was introduced.

## Implementation Details

Changed:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

Added:

- `tests/strategy/test_phase31_g90_cash_preferred_aggregate_resolver.py`

Updated SoT:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`

Permanent contract added:

```text
same-quality-class frontier is a priority signal, not an exclusive admission gate.
multiple participation-valid CASH_PREFERRED rows may coexist when same-date PIT evidence and aggregate capital competition support them.
```

## January Normal Participation Regression

Actual-producer-equivalent artifacts from the post-G86 run were rebuilt through the current PC producer path.

Run:

```text
runtime-test-historical-extended-smoke-20260824T032350824281Z
```

### 2023-01-17

```text
security_allocations = 10
security_allocation_weight = 0.382657
cash_preferred_deferrals = 10
deferred_requested_weight = 0.270512
authorized_cash_allocation = 0.034138
```

Allocated symbols:

```text
93180, 43930, 59860, 98100, 65370, 67310, 29980, 38960, 42630, 65670
```

G89 representative rows `59860` and `65370` now survive as `CASH_PREFERRED_PARTICIPATION_VALID`.

### 2023-01-18

```text
security_allocations = 11
security_allocation_weight = 0.657993
cash_preferred_deferrals = 11
deferred_requested_weight = 0.376945
authorized_cash_allocation = 0.087321
```

Allocated symbols:

```text
65670, 43930, 59860, 65370, 98100, 42630, 67310, 94220, 70680, 91070, 61810
```

Multiple non-frontier participation-valid `CASH_PREFERRED` rows survive. Optional Cash remains positive.

### 2023-01-19

```text
security_allocations = 9
security_allocation_weight = 0.535163
cash_preferred_deferrals = 11
deferred_requested_weight = 0.472346
authorized_cash_allocation = 0.183471
```

Allocated symbols:

```text
61810, 42630, 65370, 98100, 29980, 67310, 38140, 94220, 21950
```

G89 representative rows `65370`, `29980`, and `38140` now survive as positive reduced participation.

## G80 Weak-Tail Preservation

Run:

```text
runtime-test-historical-extended-smoke-20260823T140946562431Z
```

### 2023-07-21

```text
security_allocations = 1
cash_preferred_deferrals = 6
authorized_cash_allocation = 0.264159
```

Known weak-tail row `14390` remains `CASH_PREFERRED_DEFER`.

### 2023-07-24

```text
security_allocations = 2
cash_preferred_deferrals = 2
authorized_cash_allocation = 0.268535
```

Known weak-tail row `69320` remains `CASH_PREFERRED_DEFER`.

### 2023-08-01

```text
security_allocations = 3
cash_preferred_deferrals = 2
authorized_cash_allocation = 0.202091
```

Known weak-tail rows `37600` and `87500` remain `CASH_PREFERRED_DEFER`.

## Bootstrap / Normal / ADD Preservation

Bootstrap:

- Existing actual `2022-10-03` post-G86 artifact still shows `security_allocation_count > 0`.
- Existing actual `2022-10-03` post-G86 artifact still shows positive `authorized_cash_allocation`.
- Rebuilt bootstrap path still shows `bootstrap_cash_preferred_participation_allowed = true` and positive security participation.

Normal early-period G86 cases:

- `2022-10-13`
- `2022-10-14`
- `2022-10-17`
- `2022-10-18`

All continue to preserve their expected representative normal participation rows.

ADD:

- G74-specific test file is not present in this worktree.
- Existing ADD/re-entry lot binding and pending ADD consumer regressions passed.
- G90 logic does not privilege ADD by action type. ADD still requires preserved ADD evidence and may lose to NEW_BUY or Cash.

## Required Acceptance

FRONTIER_ONLY_AGGREGATE_SUPPRESSION_REMOVED = YES

NON_FRONTIER_AUTOMATIC_DEFERRAL = NO

MULTIPLE_NORMAL_PARTICIPATION_ROWS_SUPPORTED = YES

JANUARY_UNDERDEPLOYMENT_REPAIR_ACCEPTED = YES

G80_WEAK_TAIL_DEFERRAL_PRESERVED = YES

OPTIONAL_CASH_FIRST_CLASS = YES

CAPITAL_BUDGET_REMAINS_MAXIMUM = YES

BOOTSTRAP_G83_PRESERVED = YES

NORMAL_G86_PARTICIPATION_PRESERVED = YES

ADD_G74_PRESERVED = YES

LOT_PS_RUNTIME_BINDING_PRESERVED = YES

MARKET_QUALITY_CHANGED = NO

RISK_PACING_CHANGED = NO

CANDIDATE_RANKING_CHANGED = NO

NEW_THRESHOLD_CREATED = NO

NEW_SCORE_CREATED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

## Test Results

PASS:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m pytest tests/strategy/test_phase31_g90_cash_preferred_aggregate_resolver.py
5 passed
```

PASS:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m pytest \
  tests/strategy/test_phase31_g90_cash_preferred_aggregate_resolver.py \
  tests/strategy/test_phase31_g86_cash_preferred_participation_deferral.py \
  tests/strategy/test_phase31_g83_bootstrap_cash_preference_partition.py \
  tests/strategy/test_phase31_g81_opportunity_aware_security_cash_partition.py \
  tests/strategy/test_phase31_g57_multi_allocation_shadow.py \
  tests/strategy/test_phase31_g59_within_class_allocation_evidence.py \
  tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py \
  tests/strategy/test_phase31_g62_position_sizing_g61_binding.py \
  tests/strategy/test_phase31_g63_runtime_executable_binding.py \
  tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py \
  tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py
52 passed
```

PASS:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py
122 passed
```

PASS:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m pytest \
  tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
34 passed
```

PASS:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  tests/strategy/test_phase31_g90_cash_preferred_aggregate_resolver.py
```

## Run Handling

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

CURRENT_RUN_MODIFIED = NO

## Next

Proceed to user-operated fresh validation only after the user chooses to run it. G90 itself does not execute Historical validation.
