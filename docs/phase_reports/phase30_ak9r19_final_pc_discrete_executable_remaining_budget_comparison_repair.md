# Phase30-AK9R19 - Final-PC Discrete Executable Remaining-Budget Comparison Repair

## Primary Judgment

`FINAL_PC_DISCRETE_EXECUTABLE_REMAINING_BUDGET_COMPARISON_REPAIRED = YES`

The Phase30-AK9R18 2022-08-12 / 60310 equivalent case was reproduced and repaired in the Production-common Portfolio Construction final lot-aware reallocation path.

AK9R18 established that 60310 had:

- canonical discrete executable one-lot notional: `34,530`
- final residual strategy budget: `35,118.75`
- draft continuous target notional: `41,412`
- skip reason before repair: `minimum_lot_exceeds_remaining_budget`

The defect was that Final-PC compared remaining budget against the draft continuous allocation instead of the already-resolved canonical discrete executable lot requirement.

## Repair Scope

Implementation was limited to:

`Final-PC remaining-budget comparison using existing canonical discrete executable lot requirement`

Changed file:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

The repair adds `_canonical_discrete_executable_requirement_weight()` and uses it inside `apply_lot_aware_final_reallocation()` only when existing lot-resolution evidence is complete and internally consistent.

The canonical requirement is derived from existing fields only:

- `one_lot_weight`
- `one_lot_quantity`
- `final_allocated_quantity`, `executable_quantity_delta`, or `normal_lot_quantity`
- optional `post_trade_weight` consistency check

No quantity is recalculated from price, budget, score, rank, future outcome, or historical result.

## Final PC Behavior

When canonical discrete executable authority is present and coherent:

```text
required_weight = one_lot_weight * executable_lots
remaining_budget comparison uses required_weight
remaining_budget deduction uses required_weight
```

When canonical authority is missing, malformed, non-integral, safety-blocked, or post-trade-inconsistent:

```text
Final-PC keeps existing draft continuous allocation behavior / fail-closed behavior
```

Evidence now records:

- `budget_requirement_source`
- `canonical_discrete_executable_required_weight`

Draft continuous allocation evidence remains available as `requested_weight`, `draft_target_weight`, and lot-resolution continuous fields.

## Sentinel Coverage

Added focused tests in:

- `tests/strategy/test_phase22_e_portfolio_construction.py`

Sentinels:

- AK9R18 60310 equivalent passes when residual budget covers canonical one-lot requirement but not draft continuous target.
- True remaining-budget shortfall still fails closed.
- Missing canonical executable quantity falls back to draft continuous requirement.
- Tampered `post_trade_weight` fails closed to draft continuous requirement.
- Higher-priority candidate consumes discrete budget first; lower-priority candidate cannot bypass priority order.

## Preservation

No changes were made to:

- Strategy
- Candidate
- PM
- ranking / priority ordering
- deployable budget
- target gross exposure
- cash reserve
- Strategy cap value
- Safety hard-cap value
- residual recycling policy
- exposure target
- Historical run behavior

No new BUY filter or ADD filter was introduced. The repair only changes the required weight used by Final-PC when comparing and deducting remaining budget after discrete executable authority already exists.

## Required Judgments

```text
AK9R18_60310_EQUIVALENT_CASE_REPRODUCED = YES
DISCRETE_EXECUTABLE_BUDGET_AUTHORITY_CANONICAL = YES
EXISTING_CANONICAL_DISCRETE_REQUIREMENT_REUSED = YES
FINAL_PC_REMAINING_BUDGET_USES_DISCRETE_REQUIREMENT = YES
DRAFT_CONTINUOUS_ALLOCATION_EVIDENCE_PRESERVED = YES
PRIORITY_ORDERING_PRESERVED = YES
CAPITAL_CONSERVATION_CONTRACT_PRESERVED = YES
STRATEGY_CAP_AUTHORITY_PRESERVED = YES
SAFETY_HARD_CAP_PRESERVED = YES
GENUINE_LOT_INFEASIBILITY_PRESERVED = YES
RESIDUAL_RECYCLING_PRESERVED = YES
NO_NEW_STRANDED_CAPITAL_PATH_CREATED = YES
AK9R18_60310_EQUIVALENT_PASS = YES
TRUE_REMAINING_BUDGET_SHORTFALL_FAIL_CLOSED = YES
AK9R18_LEGITIMATE_21_CASES_PRESERVED = YES
SYSTEM_CAUSED_CASE_COUNT_AFTER_REPAIR = 0
NEW_BUY_FILTER_CREATED = NO
NEW_ADD_FILTER_CREATED = NO
FORCED_INVESTMENT_CREATED = NO
FIXED_EXPOSURE_TARGET_CREATED = NO
DEPLOYABLE_BUDGET_VALUE_CHANGED = NO
TARGET_GROSS_EXPOSURE_CHANGED = NO
STRATEGY_CAP_VALUE_CHANGED = NO
SAFETY_HARD_CAP_VALUE_CHANGED = NO
PRODUCTION_STRATEGY_CHANGED = NO
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO
FRESH_VALIDATION_BLOCKERS = []
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Tests

Executed:

```text
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m compileall -q src/ai_fund_lab_v2/strategy/portfolio_construction.py
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -k 'ak9r19 or phase29_l21s_one_lot_fallback or phase29_l19_residual_reallocation or phase29_l21d_lot_boundary'
python3 -m pytest tests/strategy/test_phase30_w_entry_one_lot_repair.py
python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py -k 'phase30_ak7r or discrete or one_lot or pc_positive_executable_quantity_authority'
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py
git diff --check
```

Results:

```text
compileall = PASS
focused PC sentinel subset = 10 passed
Phase30-W one-lot repair tests = 15 passed
Position Sizing discrete/one-lot subset = 15 passed
Portfolio Construction full file = 107 passed
git diff --check = PASS
```

Initial `python -m pytest ...` and initial `compileall` were not code failures:

- `python` command was unavailable in this environment; rerun with `python3`.
- default `compileall` attempted to write pycache under `/Users/negishi/Library/Caches/...`; rerun with `PYTHONPYCACHEPREFIX=.pytest_cache/pycache`.

## Historical

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

`Phase30-AK9R20 - User-Operated Fresh Validation / Remaining-Budget Deployment Confirmation`
