# Phase31-G86 — CASH_PREFERRED Participation-vs-Deferral Implementation

## PRIMARY_JUDGMENT

PHASE31_G86_CASH_PREFERRED_PARTICIPATION_DEFERRAL_IMPLEMENTED_ACCEPTED

## Scope

Implemented only the G85-confirmed Portfolio Construction boundary:

```text
market_candidate_cash_interaction
-> PC participation-vs-deferral resolution
-> portfolio_construction._canonical_multi_allocation_deployment_set()
```

No Market Quality, Risk Pacing, Portfolio Policy budget semantics, Candidate ranking, PM, SELL, Position Sizing quantity authority, Runtime priority logic, BUY filter, config, threshold, weight, model, or Historical-outcome parameter changed.

No fresh-run, resume, replay, or long Historical was executed.

## Implementation Summary

`interaction_result = CASH_PREFERRED` is now separated from final allocation action.

Portfolio Construction now exposes PC-owned resolution evidence:

```text
participation_deferral_resolution =
  CASH_PREFERRED_PARTICIPATION_VALID
  or
  CASH_PREFERRED_DEFER
```

Final artifacts preserve:

- `interaction_result`
- `participation_deferral_resolution`
- resolution owner and evidence lineage
- requested security increment
- authorized security increment
- Cash destination for deferred capital

Implementation details:

- Added PC-owned `cash_preferred_participation_deferral_resolution.v1` evidence.
- Preserved G83 bootstrap path as `CASH_PREFERRED_PARTICIPATION_VALID` under bootstrap preservation evidence.
- Added non-bootstrap reduced participation resolution for credible `CASH_PREFERRED` rows.
- Preserved weak-tail deferral as zero security allocation with lineage in `cash_preferred_security_deferrals[]`.
- Added aggregate participation resolution evidence so multiple reduced rows do not blindly recreate G80 weak-tail overdeployment.
- Propagated existing member PIT evidence into PC competitor records for resolution use; this does not create a new authority.

The implementation does not use fitted numeric thresholds such as rank > X, confidence < Y, or score < Z.

## Evidence Used

Existing same-date PIT evidence only:

- canonical opportunity quality class
- comparison sufficiency
- entry admission action/state/sufficiency
- momentum / relative strength context
- within-class relative priority evidence
- requested / accepted increment
- ADD eligibility evidence where applicable
- Risk Pacing / capital budget envelope / Cash state
- aggregate set of simultaneous `CASH_PREFERRED` rows

The resolution is categorical and relative to same-date PC evidence, not Historical-return fitted.

## Actual-Producer Normal Participation Regression

Added focused actual-artifact regression:

```text
tests/strategy/test_phase31_g86_cash_preferred_participation_deferral.py
```

Normal participation window uses post-G83 over-defensive actual artifacts:

```text
runtime-test-historical-extended-smoke-20260823T232301910860Z
2022-10-13
2022-10-14
2022-10-17
2022-10-18
```

Representative rows restored as positive reduced participation:

| Date | Symbol | Result |
| --- | --- | --- |
| 2022-10-13 | 94340 | `CASH_PREFERRED_PARTICIPATION_VALID` |
| 2022-10-14 | 94320 | `CASH_PREFERRED_PARTICIPATION_VALID` |
| 2022-10-17 | 94320 | `CASH_PREFERRED_PARTICIPATION_VALID` |
| 2022-10-18 | 94320 | `CASH_PREFERRED_PARTICIPATION_VALID` |

The regression confirms:

- positive security allocation exists
- high-quality participation-valid `CASH_PREFERRED` rows can survive
- post-G83 all-zero security collapse does not recur at PC/G61
- optional Cash still coexists
- no fixed historical exposure or position count assertion
- G61 lot-executable rows are positive

## Weak-Tail Regression

Weak-tail actual artifacts use:

```text
runtime-test-historical-extended-smoke-20260823T140946562431Z
2023-07-21
2023-07-24
2023-08-01
```

Representative G80/G84 weak-tail rows remain deferred:

| Date | Symbol | Result |
| --- | --- | --- |
| 2023-07-21 | 14390 | `CASH_PREFERRED_DEFER` |
| 2023-07-24 | 69320 | `CASH_PREFERRED_DEFER` |
| 2023-08-01 | 37600 | `CASH_PREFERRED_DEFER` |
| 2023-08-01 | 87500 | `CASH_PREFERRED_DEFER` |

The regression confirms:

- obvious weak-tail rows do not survive merely because `accepted_weight > 0`
- deferral lineage is preserved
- deferred capital returns to Cash
- no lower-priority promotion
- no residual security fallback

## Mixed-Day Regression

Added focused mixed-day case with:

- strong security
- participation-valid `CASH_PREFERRED` security
- weak-tail `CASH_PREFERRED` security
- optional Cash

Expected and observed:

- strong security allocated
- credible reduced participant allocated
- weak tail deferred
- Cash remains positive
- total allocation respects budget
- no forced budget fill

## No-Opportunity Regression

Added focused no-valid-opportunity case.

Expected and observed:

- Cash receives all incremental capital
- no synthetic BUY
- no fallback security
- no forced participation

## Required Acceptance

CASH_PREFERRED_INTERACTION_ACTION_SEPARATED = YES

PC_PARTICIPATION_DEFERRAL_AUTHORITY_IMPLEMENTED = YES

NORMAL_CASH_PREFERRED_REDUCED_PARTICIPATION_RESTORED = YES

WEAK_TAIL_CASH_PREFERRED_DEFERRAL_PRESERVED = YES

G83_BOOTSTRAP_PARTICIPATION_PRESERVED = YES

G81_WEAK_TAIL_PROTECTION_PRESERVED = YES

AGGREGATE_WEAK_TAIL_OVERDEPLOYMENT_PREVENTED = YES

OPTIONAL_CASH_FIRST_CLASS = YES

CAPITAL_BUDGET_REMAINS_MAXIMUM = YES

PROFIT_ENGINE_NORMAL_PARTICIPATION_PRESERVED = YES

MIXED_DAY_MULTI_DESTINATION_PARTITION = PASS

ADD_G74_PRESERVED = YES

LOT_PS_RUNTIME_BINDING_PRESERVED = YES

MARKET_QUALITY_CHANGED = NO

RISK_PACING_CHANGED = NO

CANDIDATE_RANKING_CHANGED = NO

NEW_NUMERIC_SCORE_CREATED = NO

HISTORICAL_THRESHOLD_CREATED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

## Test Results

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m pytest tests/strategy/test_phase31_g86_cash_preferred_participation_deferral.py
4 passed
```

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m pytest \
  tests/strategy/test_phase31_g86_cash_preferred_participation_deferral.py \
  tests/strategy/test_phase31_g81_opportunity_aware_security_cash_partition.py \
  tests/strategy/test_phase31_g83_bootstrap_cash_preference_partition.py \
  tests/strategy/test_phase31_g57_multi_allocation_shadow.py \
  tests/strategy/test_phase31_g59_within_class_allocation_evidence.py \
  tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py \
  tests/strategy/test_phase31_g62_position_sizing_g61_binding.py \
  tests/strategy/test_phase31_g63_runtime_executable_binding.py \
  tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py \
  tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_si_no_add_does_not_hard_block_positive_add_increment \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_99840_equivalent_si_no_add_does_not_hard_block_positive_add_increment \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_40520_equivalent_expected_edge_weakening_still_blocks_add
50 passed
```

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py
```

PASS:

```text
git diff --check -- src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase31_g86_cash_preferred_participation_deferral.py docs/02_architecture/portfolio_construction_and_position_sizing_contract.md docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md docs/02_architecture/strategy_architecture_v1.md docs/phase_reports/phase31_g86_cash_preferred_participation_vs_deferral_implementation.md
```

## Architecture SoT Updated

Updated permanent SoT:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`

The permanent contract now states:

```text
interaction_result != final allocation action
```

and:

```text
CASH_PREFERRED
-> PC participation-vs-deferral resolution
-> reduced participation OR Cash deferral
```

Bootstrap is explicitly separate.

## Not Executed

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

CURRENT_RUN_MODIFIED = NO

## Next

Do not resume failed pre-G86 runs.

Return focused acceptance results for review. After review, use only user-operated fresh validation.
