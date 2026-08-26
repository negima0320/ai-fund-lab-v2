# Phase31-G81 — Opportunity-Aware Security/Cash Partition Repair

## PRIMARY_JUDGMENT

PHASE31_G81_OPPORTUNITY_AWARE_SECURITY_CASH_PARTITION_REPAIRED_ACCEPTED

## Scope

G80で確定した境界だけを修理した。

- Primary boundary: `portfolio_construction._canonical_multi_allocation_deployment_set()`
- Repaired semantic: `market_candidate_cash_interaction.interaction_result = CASH_PREFERRED` is binding at final security/Cash partition
- Strategy parameters, Candidate ranking, Market Quality, Risk Pacing, Portfolio Policy budget semantics, PM, SELL, Position Sizing quantity authority, and Runtime priority semantics were not changed by G81.
- No fresh-run, resume, replay, or long Historical was executed.

## Contract Reconciliation

`DEPLOY_ELIGIBLE` remains eligible for positive security allocation.

`SELECTIVE_COMPETITION` remains eligible for positive security allocation under the existing Market Candidate Cash Interaction contract.

`CASH_PREFERRED` is no longer treated as a positive security allocation state in final multi-allocation materialization. The requested increment remains visible as diagnostic/lineage evidence in `cash_preferred_security_deferrals[]`, but `authorized_allocation_weight = 0.0` for the security side. Deferred budget is returned to optional Cash instead of being consumed by weak-tail security rows.

This is not a blanket `COMPARABLE_MARGINAL` exclusion. `COMPARABLE_MARGINAL` rows still receive positive allocation when their canonical interaction is `DEPLOY_ELIGIBLE`.

## Implementation

Updated `src/ai_fund_lab_v2/strategy/portfolio_construction.py`:

- Removed `CASH_PREFERRED` from the final positive security allocation allow-list.
- Added `cash_preferred_security_deferrals[]` and `cash_preferred_security_deferral_count`.
- Preserved original competitor, opportunity quality, within-class evidence, and interaction reason codes for deferred rows.
- Returned deferred security budget to `authorized_cash_allocation`.
- Exposed explicit contract flags:
  - `cash_preferred_binding_at_final_allocation = True`
  - `cash_is_residual_only = False`
  - `weak_tail_positive_allocation_preserved_when_cash_preferred = False`

Updated architecture SoT:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`

Added/updated focused regressions:

- `tests/strategy/test_phase31_g81_opportunity_aware_security_cash_partition.py`
- `tests/strategy/test_phase31_g57_multi_allocation_shadow.py`
- `tests/strategy/test_phase31_g59_within_class_allocation_evidence.py`

## Focused Acceptance Evidence

G81 weak-opportunity / Cash-preferred fixture:

- 2023-07-21-style all-CASH_PREFERRED tail: final `security_allocations[] = []`
- Deferrals preserve weak-tail evidence for `14910`, `71270`, `94340`
- `authorized_cash_allocation = available_incremental_budget`
- no unallocated residual
- no hidden security fallback

G81 aggregate tail fixture:

- Strong security remains allocated.
- CASH_PREFERRED weak-tail rows are deferred to Cash.
- No lower-priority implicit promotion is introduced.

Profit Engine preservation fixture:

- NORMAL `COMPARABLE_MARGINAL` rows remain positive security allocations.
- Multi-security participation remains possible.
- Security + Cash coexistence remains possible.

ADD preservation fixture:

- Strong ADD and NEW_BUY under `SELECTIVE_COMPETITION` remain positive allocations.
- G74 ADD authority regressions continue to pass.

## Required Acceptance

SECURITY_CASH_PARTITION_AUTHORITY_REPAIRED = YES

CASH_PREFERRED_BINDING_AT_FINAL_ALLOCATION = YES

CASH_IS_RESIDUAL_ONLY = NO

WEAK_TAIL_POSITIVE_ALLOCATION_PRESERVED_WHEN_CASH_PREFERRED = NO

REDUCED_ONLY_AGGREGATE_TAIL_RISK_REPAIRED = YES

CAPITAL_BUDGET_REMAINS_MAXIMUM = YES

OPTIONAL_CASH_PRESERVED = YES

CREDIBLE_MARGINAL_PARTICIPATION_PRESERVED = YES

PROFIT_BURST_STYLE_PARTICIPATION_PRESERVED = YES

SELECTIVE_COMPETITION_PRESERVED = YES

ADD_G74_AUTHORITY_PRESERVED = YES

LOT_AWARE_PRIORITY_PRESERVED = YES

PS_QUANTITY_AUTHORITY_PRESERVED = YES

RUNTIME_PRIORITY_REDECISION = NO

MARKET_QUALITY_CHANGED = NO

CANDIDATE_RANKING_CHANGED = NO

NEW_FEATURE_CREATED = NO

NEW_THRESHOLD_CREATED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

## Test Results

PASS:

```text
python3 -m pytest tests/strategy/test_phase31_g81_opportunity_aware_security_cash_partition.py
4 passed

python3 -m pytest tests/strategy/test_phase31_g57_multi_allocation_shadow.py tests/strategy/test_phase31_g59_within_class_allocation_evidence.py
9 passed

python3 -m pytest tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py tests/strategy/test_phase31_g62_position_sizing_g61_binding.py tests/strategy/test_phase31_g63_runtime_executable_binding.py
11 passed

python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_si_no_add_does_not_hard_block_positive_add_increment tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_99840_equivalent_si_no_add_does_not_hard_block_positive_add_increment tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_40520_equivalent_expected_edge_weakening_still_blocks_add
3 passed

python3 -m pytest tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py
16 passed

PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py
PASS

git diff --check
PASS
```

Initial plain `python3 -m py_compile ...` failed because macOS attempted to write pycache under `/Users/negishi/Library/Caches/com.apple.python/...`, outside the sandbox. Re-running with `PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache` passed.

## Not Executed

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

CURRENT_RUN_MODIFIED = NO

## Git Diff Check

GIT_DIFF_CHECK = PASS

The worktree contains many pre-existing modified/untracked Phase31 files from earlier tasks. G81 intentionally touched only the PC security/Cash partition boundary, focused regressions, and architecture/report documentation.

## Next

Do not resume the current pre-G81 Historical run.

Proceed to user-operated fresh Historical validation only after this focused G81 acceptance is reviewed.
