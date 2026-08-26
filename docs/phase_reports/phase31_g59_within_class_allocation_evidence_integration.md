# Phase31-G59 — Within-Class Allocation Evidence Integration

## Primary Judgment

PHASE31_G59_WITHIN_CLASS_ALLOCATION_EVIDENCE_INTEGRATED_ACCEPTED

G58 report tail references to `PHASE31_G58_WITHIN_CLASS...` are superseded by
this canonical G59 task numbering.

## Summary

Integrated within-class differentiation evidence into the G57
`canonical_multi_allocation_deployment_set.v1` shadow payload.

The implementation keeps the payload SHADOW / NON-AUTHORITATIVE and does not
connect it to Position Sizing or Runtime orders. It preserves Market Quality as
capital pacing context and keeps the existing SINGLE path as the only
authoritative trading path.

## Implementation

Changed:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase31_g59_within_class_allocation_evidence.py`

Added to each capital competitor:

- `within_class_allocation_evidence`

Added to each shadow security allocation:

- `within_class_allocation_rank`
- `within_class_allocation_evidence`
- `within_class_priority_hash`

Added to the shadow multi-allocation payload:

- `within_class_differentiation_supported = True`
- `within_class_allocation_evidence_integrated = True`
- `stronger_edge_capital_priority_preserved`
- `comparable_marginal_equal_weight_collapse = False`
- `candidate_rank_authority_mutation = False`
- `candidate_rank_authority_mutation_count = 0`

## Evidence Inputs

The within-class evidence uses only existing decision-time fields already
present on PC members:

- canonical opportunity quality class
- canonical marginal capital priority index
- opportunity buy rank / input opportunity rank / candidate rank
- construction priority
- runtime opportunity score
- allocation quality score
- confidence

These inputs are carried as lineage and ordering evidence only. G59 does not
create a new candidate ranking authority, eligibility authority, production
allocation percentage, threshold, or Historical outcome-derived parameter.

## Behavioral Boundary

Unchanged:

- Candidate AI ranking authority
- Candidate eligibility authority
- Position Sizing behavior
- Runtime order behavior
- BUY / SELL independence
- Market Quality as pacing context only
- G57 shadow non-authoritative status
- Existing SINGLE authoritative trading path

## Focused Real-PIT Sanity

Rechecked the G58 `2022-10-03` through `2022-10-19` real-PIT window from:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260822T174358377089Z`

using existing `strategy_eod_shadow` PIT artifacts and in-memory G56/G57/G59
semantics.

Results:

- Dates evaluated: `12`
- Valid-opportunity dates: `12`
- Zero-security-allocation dates with valid opportunities: `0`
- Multi-security allocation dates: `12`
- Cash + security coexistence dates: `2`
- Shadow security allocation rows: `126`
- Rows with within-class evidence: `126`
- Rows with within-class priority hash: `126`
- Rows with within-class allocation rank: `126`
- Candidate rank / eligibility mutation count: `0`
- PS behavior change count: `0`
- Runtime order change count: `0`
- Future input count: `0`
- Historical outcome input count: `0`

Example rows:

- `2022-10-03`: `15` security allocations + `0.022519` Cash
- `2022-10-04`: `16` security allocations
- `2022-10-05`: `10` security allocations, including
  `COMPARABLE_HIGH: 1` and `COMPARABLE_MARGINAL: 9`

## Profit Engine Preservation

PASS.

The shadow multi-allocation payload continues to avoid valid-opportunity
zero-allocation collapse while now preserving relative investment value inside
coarse classes such as `COMPARABLE_MARGINAL`.

G59 does not suppress BUYs through Market Quality. It adds relative capital
priority evidence for simultaneously valid opportunities, including NEW_BUY and
ADD competitors, without mutating rank or eligibility.

## Acceptance

CANDIDATE_RANK_AUTHORITY_MUTATION = NO

WITHIN_CLASS_DIFFERENTIATION_SUPPORTED = YES

STRONGER_EDGE_CAPITAL_PRIORITY_PRESERVED = YES

COMPARABLE_MARGINAL_EQUAL_WEIGHT_COLLAPSE = NO

MULTI_SECURITY_SUPPORTED = YES

CASH_AND_SECURITY_COEXISTENCE_SUPPORTED = YES

MARKET_QUALITY_HARD_GATE = NO

CAPITAL_CONSERVATION = PASS

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_STRATEGY_INPUT_COUNT = 0

PS_BEHAVIOR_CHANGE_COUNT = 0

RUNTIME_ORDER_CHANGE_COUNT = 0

## Regression

Command:

```bash
python3 -m pytest tests/strategy/test_phase31_g59_within_class_allocation_evidence.py tests/strategy/test_phase31_g57_multi_allocation_shadow.py tests/strategy/test_phase31_g50_final_capital_winner_binding.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase31_g46_refined_capital_competition_integrated_acceptance.py tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py -q
```

Result:

```text
328 passed in 4.56s
```

## Compile / Diff Checks

Command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase31_g59_within_class_allocation_evidence.py
```

Result:

```text
PASS
```

Command:

```bash
git diff --check -- src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase31_g59_within_class_allocation_evidence.py
```

Result:

```text
PASS
```

## Constraints

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

AUTHORITATIVE_ACTIVATION = NO

POSITION_SIZING_CONNECTED = NO

RUNTIME_ORDERS_CONNECTED = NO

PRODUCTION_THRESHOLD_OR_WEIGHT_TUNING = NO

## Next

Do not activate authoritatively yet.

Next task: lot-aware / allocation-to-sizing compatibility and production
binding readiness.
