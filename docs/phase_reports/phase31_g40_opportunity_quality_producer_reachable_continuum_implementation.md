# Phase31-G40 — Opportunity Quality Producer / Reachable Continuum Implementation

## Scope

Task type: IMPLEMENTATION — EVIDENCE / STRUCTURAL SLICE.

G40 implemented only the first G39 migration slice in the existing
`MARGINAL_CAPITAL_VALUE_AUTHORITY` producer:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `tests/strategy/test_phase31_g40_opportunity_quality_continuum.py`

G40 did not activate true Cash competition, pre-final Risk Pacing economic
competition, CAUTIOUS / GRADUAL winner changes, Position Sizing changes, PM /
SELL / Safety changes, Runtime capital re-decision, config changes, threshold
tuning, fixture changes, fresh-run, resume, replay, Historical rerun, or long
Historical.

No new permanent architecture rule beyond G38 was required.

## Primary Judgment

`PHASE31_G40_OPPORTUNITY_QUALITY_REACHABLE_CONTINUUM_IMPLEMENTED_ACCEPTED`

The canonical Opportunity Quality continuum is implemented and reachable inside
the existing marginal capital value authority. Existing Portfolio Construction
economic behavior remains compatibility-mapped to the legacy
`marginal_capital_value_class` field, so G40 is evidence / structural only.

## Pre-G40 Classifier Inventory

Pre-G40 active branches in `marginal_capital_value.py`:

| Legacy class | Active branch before G40 |
| --- | --- |
| `ELIGIBLE_STRONG` | BUY_ADD complete positive ADD evidence; BUY_NEW full/allocation entry admission with rank. |
| `ELIGIBLE_COMPARABLE` | BUY_NEW with runtime opportunity score or rank but without explicit full-entry pass. |
| `ELIGIBLE_WEAK` | No active producer branch. |
| `COMPARISON_INSUFFICIENT` | BUY_ADD missing/non-pass ADD evidence; BUY_NEW without score/rank evidence. |
| `BLOCKED_OR_NOT_ELIGIBLE` | BUY_ADD weakening expected edge; BUY_NEW blocking entry admission; non-BUY increment candidate. |

`PRE_G40_CLASSIFIER_INVENTORY_COMPLETE = YES`

`PRE_G40_ELIGIBLE_WEAK_ACTIVE_BRANCH_COUNT = 0`

## Implementation Summary

G40 added one canonical continuum:

- `STRONG`
- `COMPARABLE_HIGH`
- `COMPARABLE_MARGINAL`
- `WEAK_VALID`
- `INSUFFICIENT`
- `BLOCKED`

The canonical producer function is:

```text
classify_opportunity_quality(row, business_date=None)
```

The existing `classify_candidate(row)` remains as a temporary one-way
compatibility alias for current consumers. It derives the legacy
`marginal_capital_value_class`, `comparison_sufficiency`, and reason codes from
the canonical Opportunity Quality evidence. The old classifier is not retained
as an independent authority.

`CANONICAL_OPPORTUNITY_QUALITY_CONTINUUM_IMPLEMENTED = YES`

`DUPLICATE_OPPORTUNITY_QUALITY_ENUM_COUNT = 0`

`OLD_CLASSIFIER_INDEPENDENT_AUTHORITY_COUNT = 0`

`TEMPORARY_COMPATIBILITY_ALIAS_COUNT = 3`

`TEMPORARY_COMPATIBILITY_ALIAS_SOURCE = CANONICAL_OPPORTUNITY_QUALITY_ONLY`

## Class Semantics

| Canonical class | Implemented meaning |
| --- | --- |
| `STRONG` | Explicit positive PIT evidence. BUY_NEW requires positive entry/quality evidence plus rank/score support; ADD requires PM/ADD worthiness plus expected-edge, incremental value, opportunity cost, and campaign evidence. |
| `COMPARABLE_HIGH` | Valid above-normal opportunity with complete enough evidence and positive support, but not explicit enough for canonical STRONG. |
| `COMPARABLE_MARGINAL` | Valid opportunity with mixed/reduced quality or caution semantics; Cash may later compete under weak Market Quality. |
| `WEAK_VALID` | Eligible, not hard blocked, not missing required evidence, but weakly supported enough that optionality may dominate later. |
| `INSUFFICIENT` | Required PIT comparison evidence is missing, stale, contradictory, or lineage-incomplete. |
| `BLOCKED` | Hard invalid or non-eligible cases; later Risk Pacing must not rescue. |

Rank existence alone does not produce canonical `STRONG`. The compatibility
alias may still preserve legacy economic behavior during G40.

`STRONG_REQUIRES_EXPLICIT_POSITIVE_EVIDENCE = YES`

`RANK_ONLY_STRONG_CLASSIFICATION_COUNT = 0`

`COMPARABLE_HIGH_REACHABLE = YES`

`COMPARABLE_MARGINAL_REACHABLE = YES`

`WEAK_VALID_REACHABLE = YES`

`WEAK_VALID_IS_VALID_OPPORTUNITY = YES`

`WEAK_VALID_EQUIVALENT_TO_BLOCKED = NO`

`WEAK_VALID_EQUIVALENT_TO_INSUFFICIENT = NO`

`INSUFFICIENT_FAIL_CLOSED = YES`

`MISSING_EVIDENCE_DEFAULTS_TO_COMPARABLE = NO`

`BLOCKED_SEMANTICS_PRESERVED = YES`

## BUY_NEW / ADD / Re-entry

BUY_NEW classification now uses existing PIT evidence from entry admission,
entry state, evidence sufficiency, quality action / allocation bias, rank /
score support, selection quality, continuation quality, and downside risk
status when available.

ADD classification reuses PM ADD intent / worthiness, expected-edge
improvement, Incremental Investment Value, Opportunity Cost, and campaign /
temporal ADD evidence.

Eligible re-entry is not given a separate hierarchy; it uses the same BUY_NEW
Opportunity Quality semantics after symbol-local eligibility has admitted the
candidate into the BUY_NEW path.

`BUY_NEW_REFINED_CLASSIFICATION_IMPLEMENTED = YES`

`NEW_ALPHA_FEATURE_CREATED = NO`

`ADD_REFINED_CLASSIFICATION_IMPLEMENTED = YES`

`ADD_VALUE_EVIDENCE_REUSED = YES`

`REENTRY_USES_CANONICAL_OPPORTUNITY_QUALITY = YES`

## Evidence Schema

G40 materializes canonical evidence with:

- schema version,
- business date / as-of,
- authority owner,
- opportunity type,
- symbol,
- canonical quality class,
- reason codes,
- source evidence,
- source artifact paths / hashes when present,
- evidence completeness,
- entry admission state/action/sufficiency,
- BUY Quality action / allocation bias,
- rank / score evidence availability,
- ADD evidence summary,
- forbidden-input flags.

Forbidden outcome fields remain excluded from source evidence.

`OPPORTUNITY_QUALITY_PIT_CONTRACT = PASS`

`FUTURE_INPUT_COUNT = 0`

`HISTORICAL_OUTCOME_INPUT_COUNT = 0`

`PAPER_LEDGER_INPUT_COUNT = 0`

`AUDIT_RESULT_INPUT_COUNT = 0`

`OPPORTUNITY_QUALITY_EVIDENCE_SCHEMA_COMPLETE = YES`

`CANONICAL_OPPORTUNITY_QUALITY_REASON_CODES_IMPLEMENTED = YES`

## Compatibility Mapping

Temporary one-way alias:

| Canonical class | Legacy compatibility class |
| --- | --- |
| `STRONG` | `ELIGIBLE_STRONG` |
| `COMPARABLE_HIGH` | `ELIGIBLE_STRONG` |
| `COMPARABLE_MARGINAL` | `ELIGIBLE_COMPARABLE` |
| `WEAK_VALID` | `ELIGIBLE_COMPARABLE` |
| `INSUFFICIENT` | `COMPARISON_INSUFFICIENT` |
| `BLOCKED` | `BLOCKED_OR_NOT_ELIGIBLE` |

`COMPARABLE_HIGH -> ELIGIBLE_STRONG` preserves current G40 economic behavior
for legacy PC consumers where the old implementation treated full-entry
rank-supported BUY_NEW and positive ADD evidence as strong. G42/G43 should
remove this compatibility path when the new pre-final competition is activated.

`G40_PRODUCTION_BEHAVIOR_CHANGE_CLASS = EVIDENCE_ONLY_OR_STRUCTURAL_ONLY`

`CURRENT_PC_ECONOMIC_BINDING_ACTIVATED = NO`

`COMPATIBILITY_MAPPING_ONE_WAY = YES`

`LEGACY_CLASSIFIER_REEXECUTED = NO`

## Authority and Boundary Checks

`OPPORTUNITY_QUALITY_OWNER = MARGINAL_CAPITAL_VALUE_AUTHORITY`

`PC_OPPORTUNITY_QUALITY_AUTHORITY = NO`

`POSITION_SIZING_OPPORTUNITY_QUALITY_AUTHORITY = NO`

`RUNTIME_OPPORTUNITY_QUALITY_AUTHORITY = NO`

`POSITION_SIZING_AUTHORITY_CHANGED = NO`

`DISCRETE_QUANTITY_DECISION_CHANGE = NO`

`PM_SEMANTICS_CHANGED = NO`

`SELL_REDUCE_EXIT_SEMANTICS_CHANGED = NO`

`BUY_SELL_INDEPENDENCE_REGRESSION = NO`

`SAFETY_AUTHORITY_CHANGED = NO`

`MARKET_QUALITY_CHANGED = NO`

`RISK_PACING_PRODUCER_CHANGED = NO`

`RISK_PACING_BINDING_ACTIVATION_CHANGED = NO`

## G37 Defect Closure

G40 closes only the unreachable weak / graduated opportunity-quality portion of
G37.

`UNREACHABLE_WEAK_CLASS_DEFECT_REPAIRED = YES`

`TRUE_CASH_COMPETITOR_DEFECT_REPAIRED = NO_DEFERRED_TO_G41`

`PRE_FINAL_INTERACTION_DEFECT_REPAIRED = NO_DEFERRED_TO_G42`

`CAUTIOUS_GRADUAL_BINDING_DEFECT_REPAIRED = NO_DEFERRED_TO_G43`

## Legacy Classification Matrix

| Legacy name / behavior | G40 classification |
| --- | --- |
| `ELIGIBLE_STRONG` legacy field | KEEP_TEMPORARILY as one-way alias. |
| `ELIGIBLE_COMPARABLE` legacy field | KEEP_TEMPORARILY as one-way alias. |
| `ELIGIBLE_WEAK` legacy enum value | DEPRECATE; superseded by reachable `WEAK_VALID` / `COMPARABLE_MARGINAL`. |
| `COMPARISON_INSUFFICIENT` legacy field | KEEP_TEMPORARILY as one-way alias for canonical `INSUFFICIENT`. |
| `BLOCKED_OR_NOT_ELIGIBLE` legacy field | KEEP_TEMPORARILY as one-way alias for canonical `BLOCKED`. |
| late PC Risk Pacing binding on legacy class | KEEP_UNCHANGED in G40, REMOVE/MIGRATE in G42-G43. |

`G40_LEGACY_CLASSIFICATION_MATRIX_COMPLETE = YES`

## Validation

Focused regression:

```text
python3 -m pytest tests/strategy/test_phase31_g40_opportunity_quality_continuum.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py
```

Result:

```text
23 passed
```

Broader focused regression:

```text
python3 -m pytest tests/strategy/test_phase31_g40_opportunity_quality_continuum.py tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py tests/strategy/test_phase31_b6_marginal_capital_shadow_bridge.py tests/strategy/test_phase31_b8_pending_cash_causality_bridge.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase30_j_strategy_intelligence.py tests/strategy/test_phase31_g4_pm_severity_persistence.py tests/strategy/test_phase31_g8_pm_severity_action_mapping.py tests/strategy/test_phase22_j_position_sizing.py -k 'not real'
```

Result:

```text
273 passed, 9 deselected
```

The same broader focused command without `-k 'not real'` produced 279 passing
tests and 3 failures caused by missing local real-run fixture artifacts under:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z
```

Those failures were `FileNotFoundError` fixture availability failures, not G40
code-path assertion failures.

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/marginal_capital_value.py tests/strategy/test_phase31_g40_opportunity_quality_continuum.py
```

Result:

```text
PASS
```

`ALL_CANONICAL_CLASSES_REACHABILITY_TESTED = YES`

`ELIGIBILITY_AND_OPPORTUNITY_QUALITY_SEPARATED = YES`

`HARD_BLOCK_CANNOT_BECOME_WEAK_VALID = YES`

`MISSING_REQUIRED_EVIDENCE_CANNOT_BECOME_VALID_CLASS = YES`

`OUTCOME_DERIVED_CLASSIFICATION_THRESHOLD_COUNT = 0`

`G40_FOCUSED_REGRESSION = PASS`

`PY_COMPILE = PASS`

`GIT_DIFF_CHECK = PASS`

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G40_OPPORTUNITY_QUALITY_REACHABLE_CONTINUUM_IMPLEMENTED_ACCEPTED`

`PRE_G40_CLASSIFIER_INVENTORY_COMPLETE = YES`

`PRE_G40_ELIGIBLE_WEAK_ACTIVE_BRANCH_COUNT = 0`

`CANONICAL_OPPORTUNITY_QUALITY_CONTINUUM_IMPLEMENTED = YES`

`DUPLICATE_OPPORTUNITY_QUALITY_ENUM_COUNT = 0`

`OLD_CLASSIFIER_INDEPENDENT_AUTHORITY_COUNT = 0`

`TEMPORARY_COMPATIBILITY_ALIAS_COUNT = 3`

`STRONG_REQUIRES_EXPLICIT_POSITIVE_EVIDENCE = YES`

`RANK_ONLY_STRONG_CLASSIFICATION_COUNT = 0`

`COMPARABLE_HIGH_REACHABLE = YES`

`COMPARABLE_MARGINAL_REACHABLE = YES`

`WEAK_VALID_REACHABLE = YES`

`WEAK_VALID_IS_VALID_OPPORTUNITY = YES`

`WEAK_VALID_EQUIVALENT_TO_BLOCKED = NO`

`WEAK_VALID_EQUIVALENT_TO_INSUFFICIENT = NO`

`INSUFFICIENT_FAIL_CLOSED = YES`

`MISSING_EVIDENCE_DEFAULTS_TO_COMPARABLE = NO`

`BLOCKED_SEMANTICS_PRESERVED = YES`

`BUY_NEW_REFINED_CLASSIFICATION_IMPLEMENTED = YES`

`ADD_REFINED_CLASSIFICATION_IMPLEMENTED = YES`

`ADD_VALUE_EVIDENCE_REUSED = YES`

`REENTRY_USES_CANONICAL_OPPORTUNITY_QUALITY = YES`

`OPPORTUNITY_QUALITY_PIT_CONTRACT = PASS`

`FUTURE_INPUT_COUNT = 0`

`HISTORICAL_OUTCOME_INPUT_COUNT = 0`

`PAPER_LEDGER_INPUT_COUNT = 0`

`AUDIT_RESULT_INPUT_COUNT = 0`

`OPPORTUNITY_QUALITY_EVIDENCE_SCHEMA_COMPLETE = YES`

`CANONICAL_OPPORTUNITY_QUALITY_REASON_CODES_IMPLEMENTED = YES`

`ALL_CANONICAL_CLASSES_REACHABILITY_TESTED = YES`

`ELIGIBILITY_AND_OPPORTUNITY_QUALITY_SEPARATED = YES`

`HARD_BLOCK_CANNOT_BECOME_WEAK_VALID = YES`

`MISSING_REQUIRED_EVIDENCE_CANNOT_BECOME_VALID_CLASS = YES`

`OUTCOME_DERIVED_CLASSIFICATION_THRESHOLD_COUNT = 0`

`G40_PRODUCTION_BEHAVIOR_CHANGE_CLASS = EVIDENCE_ONLY_OR_STRUCTURAL_ONLY`

`CURRENT_PC_ECONOMIC_BINDING_ACTIVATED = NO`

`COMPATIBILITY_MAPPING_ONE_WAY = YES`

`LEGACY_CLASSIFIER_REEXECUTED = NO`

`OPPORTUNITY_QUALITY_OWNER = MARGINAL_CAPITAL_VALUE_AUTHORITY`

`PC_OPPORTUNITY_QUALITY_AUTHORITY = NO`

`POSITION_SIZING_OPPORTUNITY_QUALITY_AUTHORITY = NO`

`RUNTIME_OPPORTUNITY_QUALITY_AUTHORITY = NO`

`POSITION_SIZING_AUTHORITY_CHANGED = NO`

`DISCRETE_QUANTITY_DECISION_CHANGE = NO`

`PM_SEMANTICS_CHANGED = NO`

`SELL_REDUCE_EXIT_SEMANTICS_CHANGED = NO`

`BUY_SELL_INDEPENDENCE_REGRESSION = NO`

`SAFETY_AUTHORITY_CHANGED = NO`

`MARKET_QUALITY_CHANGED = NO`

`RISK_PACING_PRODUCER_CHANGED = NO`

`RISK_PACING_BINDING_ACTIVATION_CHANGED = NO`

`UNREACHABLE_WEAK_CLASS_DEFECT_REPAIRED = YES`

`TRUE_CASH_COMPETITOR_DEFECT_REPAIRED = NO_DEFERRED_TO_G41`

`PRE_FINAL_INTERACTION_DEFECT_REPAIRED = NO_DEFERRED_TO_G42`

`CAUTIOUS_GRADUAL_BINDING_DEFECT_REPAIRED = NO_DEFERRED_TO_G43`

`G40_LEGACY_CLASSIFICATION_MATRIX_COMPLETE = YES`

`G40_FOCUSED_REGRESSION = PASS`

`PY_COMPILE = PASS`

`GIT_DIFF_CHECK = PASS`

`CONFIG_CHANGE_EXECUTED = NO`

`THRESHOLD_CHANGE_EXECUTED = NO`

`PARAMETER_TUNING_EXECUTED = NO`

`FIXTURE_CHANGE_EXECUTED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`HISTORICAL_RERUN_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`NEXT_TASK_RECOMMENDATION = PHASE31_G41_TRUE_CASH_COMPETITOR_EVIDENCE_FRAMEWORK_IMPLEMENTATION`
