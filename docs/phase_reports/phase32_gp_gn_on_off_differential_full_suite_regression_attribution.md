# Phase32-GP — GN ON/OFF Differential Full-Suite Regression Attribution

Status: READ-ONLY DIFFERENTIAL AUDIT

Production source/config/schema changes performed: NO

Runtime state / Pending / Ledger mutation performed: NO

Historical fresh-run/resume/replay/recover performed: NO

## Executive Judgment

The same current environment/test corpus was compared with GN BUY-priority
semantics ON and with only the GN semantic delta reconstructed OFF in an
isolated temp copy.

Result:

```text
GN ON : 87 failed, 882 passed, 2 skipped
GN OFF: 88 failed, 881 passed, 2 skipped
```

Failure-set comparison:

```text
FAIL_BOTH      = 86
FAIL_GN_ON_ONLY = 1
FAIL_GN_OFF_ONLY = 2
PASS_BOTH      = 880
```

The single GN-ON-only failure is the known intended legacy expectation change:
an old MCV shadow test expects strong ADD lifecycle evidence to outrank a
better-ranked NEW. GN intentionally changed BUY Investment Priority to Current
PIT Opportunity rank/evidence before NEW/ADD relationship materialization.

The two GN-OFF-only failures are the new GN contract tests, proving the OFF
reference really disables rank-first and accepted-increment-independent priority.

No unintended GN differential regression was found in SELL, Winner, Sizing,
Cash, ADD, G129, REENTRY, or Runtime.

## Safe Differential Method

SAFE_GN_DIFFERENTIAL_METHOD_DEFINED: YES

Method used:

1. Capture GN-ON full-suite result in the current working tree.
2. Create an isolated lean workspace under `/private/tmp`.
3. Copy source, tests, docs, configs, schemas, scripts, tools, models, and
   project metadata.
4. Do not copy bulky runtime reports; missing artifact dependencies therefore
   remain missing in both ON/OFF modes.
5. Patch only the GN semantic delta in the temp copy.
6. Run the same `tests/strategy` suite in the temp copy.
7. Compare exact failed test node IDs.

No Production flag, config flag, Runtime toggle, persistent rollback, accepted
generation rollback, or registry mutation was used.

## Exact GN Semantic Delta OFF

The GN-OFF reference reconstructed only these semantics:

- MCV `sort_key()` returns to comparison-class-before-rank ordering.
- MCV `apply_marginal_capital_priority()` again requires
  `accepted_increment(row) > 0` before including a BUY candidate.
- PC `_reconcile_incremental_budget()` restores the broad fallback to
  `construction_priority` whenever any MCV comparison is insufficient.
- PC `apply_lot_aware_final_reallocation()` restores the broad fallback to
  `quality_order` whenever any MCV comparison is insufficient.

Excluded from OFF:

- no Production rollback in the main worktree;
- no config toggle;
- no Runtime behavior change;
- no accepted-generation change;
- no Fresh Target SHADOW authority change.

## GN-OFF Reference Validation

GN_OFF_REFERENCE_VALIDATED: YES

Validation commands:

```text
python3 -m pytest tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py::test_phase31_b4_strong_add_can_outrank_comparable_new_only_with_explicit_pit_lifecycle_evidence -q
1 passed
```

This confirms the old ADD-quality-before-rank expectation returns in GN-OFF.

```text
python3 -m pytest \
  tests/strategy/test_phase31_g40_opportunity_quality_continuum.py::test_phase31_g40_apply_priority_uses_current_opportunity_order_before_quality_class \
  tests/strategy/test_phase31_g40_opportunity_quality_continuum.py::test_phase32_gn_buy_priority_does_not_require_accepted_increment -q
2 failed
```

This confirms GN-OFF disables the two central GN guarantees:

- Current Opportunity rank before ADD quality class;
- BUY priority without accepted increment.

## Full-Suite Differential

GN_ON_PASS_FAIL_COUNTS: `87 failed, 882 passed, 2 skipped`

GN_OFF_PASS_FAIL_COUNTS: `88 failed, 881 passed, 2 skipped`

FAIL_BOTH_COUNT: 86

FAIL_GN_ON_ONLY_COUNT: 1

FAIL_GN_OFF_ONLY_COUNT: 2

PASS_BOTH_COUNT: 880

GN-ON-only failure:

- `tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py::test_phase31_b4_strong_add_can_outrank_comparable_new_only_with_explicit_pit_lifecycle_evidence`

GN-OFF-only failures:

- `tests/strategy/test_phase31_g40_opportunity_quality_continuum.py::test_phase31_g40_apply_priority_uses_current_opportunity_order_before_quality_class`
- `tests/strategy/test_phase31_g40_opportunity_quality_continuum.py::test_phase32_gn_buy_priority_does_not_require_accepted_increment`

Interpretation:

- The ON-only failure is an intended GN expectation change.
- The OFF-only failures are expected because the GN tests assert the new
  semantic contract.
- All other failures are shared between ON and OFF and therefore are not caused
  by the GN BUY-priority semantic delta.

## GO 52 Unresolved Reattribution

GO_UNRESOLVED_52_REATTRIBUTED_COUNT: 52

STILL_UNRESOLVED_COUNT: 0_FOR_GN_CAUSALITY; 52_REMAIN_NON_GN_BASELINE_TRIAGE

All 52 GO-unresolved semantic failures fail in both GN-ON and GN-OFF.

Reattribution:

- GN-causal new failures: 0
- reconstructed baseline failures: 52
- still unresolved as GN differential: 0

They still need product-level/test-level triage, but they are no longer
unresolved for GN causality.

## Artifact Dependency Separation

ARTIFACT_DEPENDENCY_FAILURES_SEPARATED: YES

The 33 artifact-dependent failures remain shared between GN-ON and GN-OFF.
They are caused by missing `reports/runtime_tests/runs/...` files, not by GN
BUY-priority semantics.

They were intentionally not repaired in this phase.

## Obsolete / Intended Expectations

GO had two non-baseline special cases:

- obsolete signature expectation:
  - `test_phase24_hy_rank_authority.py::test_portfolio_member_materializes_opportunity_rank_lineage`
  - fails in both ON and OFF;
  - not GN causal.
- intended GN expectation change:
  - `test_phase31_b4_marginal_capital_value_shadow.py::test_phase31_b4_strong_add_can_outrank_comparable_new_only_with_explicit_pit_lifecycle_evidence`
  - fails only in GN-ON;
  - passes in GN-OFF;
  - directly confirms the intended semantic difference.

GN_INTENDED_DIFFERENTIAL_COUNT: 1

GN_UNINTENDED_DIFFERENTIAL_REGRESSION_COUNT: 0

## Component Differential Searches

SELL_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

WINNER_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

SIZING_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

CASH_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

ADD_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

G129_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

REENTRY_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

RUNTIME_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

Evidence:

- No SELL / Winner / Sizing / Cash / ADD / G129 / REENTRY / Runtime test is
  GN-ON-only.
- All remaining non-BUY failures are FAIL_BOTH.
- Shared failures can still indicate baseline defects or obsolete tests, but
  the ON/OFF comparison proves they are not introduced by GN.

## REENTRY / Churn Differential

REENTRY failures are shared between GN-ON and GN-OFF.

No GN differential evidence shows:

- recent EXIT guard bypass;
- immediate re-buy allowance caused by GN;
- old EXIT penalty revival caused by GN;
- REENTRY / BUY_NEW classification regression caused by GN.

The REENTRY failures remain important, but GP reclassifies them as reconstructed
baseline failures for GN causality because the same tests fail with GN semantic
OFF.

## Churn Dynamic Validation Contract

CHURN_DYNAMIC_VALIDATION_CONTRACT_DEFINED: YES

Short post-GN dynamic validation must measure:

- BUY priority order preservation
- NEW/ADD parity
- history-caused priority inversion count
- EXIT -> BUY business-day distance
- BUY -> EXIT -> BUY cycle count
- repeated same-symbol cycle count
- recent EXIT guard activation count
- recent EXIT guard block count
- recent EXIT guard release count
- guard bypass count
- re-buy Current PIT re-strength evidence
- HOLD / REDUCE / EXIT exact regression
- Winner Protection exact regression
- Position Sizing exact regression
- Cash semantic exact regression
- ADD Safety exact regression
- G129 exact regression
- lot / cap / liquidity exact regression
- Runtime mapping exact regression

Historical PnL must not tune guard thresholds, rank cutoffs, quality cutoffs,
Cash percentages, BUY counts, or sizing formulas.

## No Persistent Mutation Audit

PERSISTENT_SOURCE_MUTATION: NO_FROM_GP

RUNTIME_STATE_MUTATION: NO

The only persistent repository artifact created by this GP phase is this report.
The GN-ON Production source state in the main working tree was not rolled back.
The GN-OFF changes were confined to `/private/tmp/phase32_gp_lean.6QpZWU`.

## Required Answers

SAFE_GN_DIFFERENTIAL_METHOD_DEFINED: YES

GN_OFF_REFERENCE_VALIDATED: YES

GN_ON_PASS_FAIL_COUNTS: 87_FAILED_882_PASSED_2_SKIPPED

GN_OFF_PASS_FAIL_COUNTS: 88_FAILED_881_PASSED_2_SKIPPED

FAIL_BOTH_COUNT: 86

FAIL_GN_ON_ONLY_COUNT: 1

FAIL_GN_OFF_ONLY_COUNT: 2

PASS_BOTH_COUNT: 880

GO_UNRESOLVED_52_REATTRIBUTED_COUNT: 52

STILL_UNRESOLVED_COUNT: 0_FOR_GN_CAUSALITY; 52_REMAIN_BASELINE_TRIAGE

GN_INTENDED_DIFFERENTIAL_COUNT: 1

GN_UNINTENDED_DIFFERENTIAL_REGRESSION_COUNT: 0

SELL_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

WINNER_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

SIZING_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

CASH_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

ADD_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

G129_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

REENTRY_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

RUNTIME_GN_DIFFERENTIAL_REGRESSION_COUNT: 0

ARTIFACT_DEPENDENCY_FAILURES_SEPARATED: YES

PERSISTENT_SOURCE_MUTATION: NO_FROM_GP

RUNTIME_STATE_MUTATION: NO

CHURN_DYNAMIC_VALIDATION_CONTRACT_DEFINED: YES

SHORT_DYNAMIC_VALIDATION_READY: YES_FOR_GN_CAUSALITY_AFTER_BASELINE_FAILURES_ARE_NOTED_AS_NON_GN

LONG_HORIZON_VALIDATION_READY: NO

DIRECT_PRODUCTION_PROMOTION_READY: NO

NEXT_STEP: run short actual-path post-GN dynamic validation with the churn/SELL/Winner/Sizing/Cash/ADD/G129/Runtime metrics defined here, while tracking the 52 reconstructed baseline failures and 33 missing-artifact tests separately from GN causality

## Final Judgment

Yes: the GN ON/OFF differential proves that GN's BUY-only history-neutral priority repair introduces no new unintended regression in SELL, Winner, Sizing, Cash, ADD, G129, REENTRY, or Runtime; the only GN-ON-only failure is the intended legacy BUY-priority expectation change.
