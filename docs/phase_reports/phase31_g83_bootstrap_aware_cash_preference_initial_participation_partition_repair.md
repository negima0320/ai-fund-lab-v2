# Phase31-G83 — Bootstrap-Aware Cash Preference / Initial Participation Partition Repair

## PRIMARY_JUDGMENT

PHASE31_G83_BOOTSTRAP_AWARE_CASH_PREFERENCE_PARTITION_REPAIRED_ACCEPTED

## Scope

G82で確定したsemantic gapだけを修理した。

Primary boundary:

```text
market_candidate_cash_interaction
-> portfolio_construction._canonical_multi_allocation_deployment_set()
-> final security/Cash partition
```

No Market Quality, Risk Pacing, Candidate ranking, PM, SELL, Position Sizing quantity authority, Runtime priority semantics, threshold, weight, or config changes were made. No fresh-run, resume, replay, or long Historical was executed.

## Repair Summary

G81 remains valid for already-deployed weak-tail / residual optionality contexts:

```text
RESIDUAL_OPTIONALITY_CASH + CASH_PREFERRED
-> security authorized increment = 0
-> cash_preferred_security_deferrals[] preserved
-> deferred capital returns to optional Cash
```

G83 adds bootstrap-aware final partition binding:

```text
EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP
+ EXPLORATION_PARTICIPATION_RISK_PRESERVED
+ PROFIT_ENGINE_PRESERVATION_CONTEXT
+ selected valid opportunities
+ CASH_PREFERRED
-> existing reduced accepted security increment may materialize
-> Cash remains preferred for remaining budget
```

This uses existing Portfolio Policy / budget-envelope evidence only. It creates no new score, indicator, fixed BUY count, fixed exposure target, rank cutoff, confidence cutoff, share-price cutoff, or Historical-return-derived parameter.

## Code Changes

Updated `src/ai_fund_lab_v2/strategy/portfolio_construction.py`:

- Added `_bootstrap_cash_preferred_participation_allowed()`.
- In `_canonical_multi_allocation_deployment_set()`, `CASH_PREFERRED` rows are now context-aware:
  - bootstrap + exploration/profit-engine evidence: included as reduced-risk security allocation
  - residual / already-deployed context: G81 deferral retained
- Added final evidence fields:
  - `bootstrap_cash_preferred_participation_allowed`
  - `bootstrap_cash_preferred_participation_count`
  - row-level `bootstrap_reduced_risk_participation`
  - row-level `cash_preferred_context`

Updated tests:

- Added `tests/strategy/test_phase31_g83_bootstrap_cash_preference_partition.py`.
- Extended the existing actual 2022-10-03 producer-path regression in `tests/strategy/test_phase31_g66_publication_path_integration.py` with G83 bootstrap assertions.

Updated common architecture SoT:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`

## Actual 2022-10-03 Producer-Equivalent Acceptance

The mandatory actual-producer-equivalent path uses existing PIT artifacts from:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T135454942984Z/daily/2022-10-03/strategy
```

Path executed by focused regression:

```text
portfolio_construction_draft
-> position_sizing_preflight
-> _produce_lot_aware_final_portfolio_construction()
-> apply_lot_aware_final_reallocation()
-> promote_final_portfolio_construction_for_production()
-> Position Sizing
-> Runtime Planning
```

Observed in the repaired path:

```text
business_date = 2022-10-03
risk_pacing = CAUTIOUS_DEPLOYMENT
bootstrap_state = EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP
security_allocation_count = 9
bootstrap_cash_preferred_participation_count = 9
cash_preferred_security_deferral_count = 0
authorized_cash_allocation = 0.003286
G61 lot_executable_count = 9
PS positive quantity rows > 0
Runtime BUY_NEW plan count > 0
```

This repairs the post-G81 first-day zero-BUY causal chain without reverting G81.

## Plateau Weak-Tail Preservation

G81 plateau weak-tail regression remains passing:

```text
RESIDUAL_OPTIONALITY_CASH
+ CASH_PREFERRED weak-tail rows
-> security_allocations[] = []
-> cash_preferred_security_deferrals[] populated
-> optional Cash receives deferred budget
```

Therefore the G80/G81 weak-tail Cash protection is preserved.

## Required Judgments

BOOTSTRAP_PARTICIPATION_SEMANTIC_BOUND = YES

G81_WEAK_TAIL_CASH_PROTECTION_PRESERVED = YES

CASH_PREFERRED_CONTEXT_DIFFERENTIATED = YES

2022_10_03_BOOTSTRAP_SECURITY_GT_0 = YES

2022_10_03_OPTIONAL_CASH_GT_0 = YES

PLATEAU_WEAK_TAIL_SECURITY_ZERO = YES

FORCED_BOOTSTRAP_BUY = NO

FIXED_BOOTSTRAP_EXPOSURE = NO

CREDIBLE_MARGINAL_PARTICIPATION_PRESERVED = YES

ADD_G74_PRESERVED = YES

LOT_PS_RUNTIME_BINDING_PRESERVED = YES

MARKET_QUALITY_CHANGED = NO

CANDIDATE_RANKING_CHANGED = NO

NEW_THRESHOLD_CREATED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

## Test Results

PASS:

```text
python3 -m pytest tests/strategy/test_phase31_g83_bootstrap_cash_preference_partition.py tests/strategy/test_phase31_g81_opportunity_aware_security_cash_partition.py tests/strategy/test_phase31_g66_publication_path_integration.py::test_phase31_g66_actual_pit_publication_path_materializes_buy_plans
8 passed

python3 -m pytest tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py
16 passed

python3 -m pytest tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py tests/strategy/test_phase31_g62_position_sizing_g61_binding.py tests/strategy/test_phase31_g63_runtime_executable_binding.py
11 passed

python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_si_no_add_does_not_hard_block_positive_add_increment tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_99840_equivalent_si_no_add_does_not_hard_block_positive_add_increment tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_40520_equivalent_expected_edge_weakening_still_blocks_add
3 passed

python3 -m pytest tests/strategy/test_phase31_g57_multi_allocation_shadow.py tests/strategy/test_phase31_g59_within_class_allocation_evidence.py
9 passed

PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py
PASS

git diff --check
PASS
```

## Not Executed

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

CURRENT_POST_G81_RUN_RESUMED = NO

## Next

Do not resume the post-G81 failed run.

After ChatGPT review, proceed only with user-operated fresh Historical validation.
