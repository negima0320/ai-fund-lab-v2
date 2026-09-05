# Phase32-GV - Pre-GN Current-PIT BUY Judgment + GN History-Neutral Guards Minimal Repair SHADOW / Differential Validation

## Executive Judgment

OPTION_C_SHADOW_IMPLEMENTED: `YES`

Option C was implemented only as a focused test-local SHADOW diagnostic in `tests/strategy/test_phase31_g40_opportunity_quality_continuum.py`. No production source, config, schema, runtime state, Pending, Ledger, replay, resume, recover, fresh-run, or Historical run was changed in this phase.

The SHADOW comparator exactly follows the GU minimal repair contract:

```text
MCV Current-PIT class
-> Current Opportunity rank
-> insufficiency
-> symbol
```

It preserves GN's correct guards:

- no accepted-increment prerequisite
- priority before held/flat relationship materialization
- NEW/ADD relationship after priority
- old ownership/campaign/prior ADD/old EXIT/average cost/realized PnL excluded from priority
- bounded Recent Exit Guard remains separate from priority
- zero production authority leak

## Validation Evidence

Focused command:

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g40_opportunity_quality_continuum.py
```

Result:

```text
16 passed in 0.06s
```

Direct `pytest` was unavailable on PATH, so module invocation was used.

## Shadow Implementation Scope

The GV SHADOW helper is test-local:

- `_option_c_shadow_priority()` at `tests/strategy/test_phase31_g40_opportunity_quality_continuum.py`
- `_option_c_priority_tuple()` at `tests/strategy/test_phase31_g40_opportunity_quality_continuum.py`

The helper consumes the existing `marginal_capital_value.classify_opportunity_quality()` and `COMPARISON_CLASSES`; it does not create a new production module, authority, schema family, numeric score, weighting, threshold, or runtime consumer.

## Focused Bundle Coverage

| Case | Evidence | Result |
|---|---|---|
| Option C comparator | class -> rank -> insufficiency -> symbol SHADOW tuple | PASS |
| 50250 golden case | rank 23 `ELIGIBLE_STRONG` outranks rank 1 `ELIGIBLE_COMPARABLE` in SHADOW, while current GN production remains rank-first | PASS |
| Rank-quality conflict | rank 3 strong before rank 5 strong before rank 1 comparable before rank 2 comparable | PASS |
| Within-class rank | same MCV class preserves lower Current Opportunity rank first | PASS |
| NEW/ADD parity | same symbol/class/rank/sufficiency has identical pre-symbol priority tuple for BUY_NEW and BUY_ADD | PASS |
| Accepted-zero | zero target/accepted/requested increment still receives SHADOW priority when BUY intent exists | PASS |
| History exclusion | old campaign, closed campaign, prior ADD count, old EXIT, average cost, realized PnL do not alter priority tuple | PASS |
| Recent Exit | no guard bypass introduced by SHADOW comparator | PASS |
| ADD/G129 | zero ADD Safety bypass and zero G129 regression flags | PASS |
| SELL/PM/Winner | zero SELL, PM, Winner authority change flags | PASS |
| Sizing/Cash | zero sizing/cash authority change flags | PASS |
| PS/Runtime isolation | authoritative consumer count is zero; production BUY changed is false | PASS |

## Differential Matrix

| Case | Pre-GN existing | Current GN | Option C SHADOW |
|---|---|---|---|
| 50250 rank 23 strong vs rank 1 comparable | class-first lifts 50250 | rank-first keeps rank 1 first | 50250 first, matching pre-GN Current-PIT judgment |
| rank1 comparable vs rank3 strong | strong can outrank comparable | rank1 wins | rank3 strong wins |
| rank3 strong vs rank5 strong | rank3 wins within class | rank3 wins if ranked higher | rank3 wins within class |
| rank1 strong vs rank2 comparable | rank1 strong wins | rank1 strong wins | rank1 strong wins |
| held vs flat same evidence | possible relationship risk | relationship flagged out | same pre-symbol priority tuple; relationship after priority |
| accepted increment zero | pre-GN could exclude | GN includes by intent | included by intent |
| old campaign | contamination risk insufficiently flagged | explicitly excluded | explicitly excluded |
| prior ADD | contamination risk insufficiently flagged | explicitly excluded | explicitly excluded |
| old EXIT | contamination risk except bounded guard | explicitly excluded except bounded guard | explicitly excluded except bounded guard |
| recent EXIT | guard is bounded exception | guard remains separate | no priority penalty or bypass |
| ADD Safety block | downstream safety owns block | unchanged | unchanged, no bypass |
| lot infeasible | downstream lot/PS owns skip | unchanged | unchanged, no priority rewrite |

## Required Answers

- OPTION_C_SHADOW_IMPLEMENTED: `YES`
- OPTION_C_EXACT_GU_COMPARATOR_USED: `YES`

- PRE_GN_CURRENT_PIT_COMPARATOR_EQUIVALENCE_RATE: `100%`
- WITHIN_CLASS_RANK_ORDER_PRESERVATION_RATE: `100%`

- HISTORY_CAUSED_PRIORITY_INVERSION_COUNT: `0`
- RELATIONSHIP_PRIORITY_VIOLATION_COUNT: `0`
- ACCEPTED_INCREMENT_PRIORITY_DEPENDENCY_COUNT: `0`
- HIDDEN_RERANKING_COUNT: `0`

- 50250_GOLDEN_CASE_PASS: `YES`
- RANK_QUALITY_CONFLICT_CASES_PASS: `YES`

- NEW_ADD_PARITY_PASS: `YES`
- HISTORY_NEUTRALITY_PASS: `YES`
- ACCEPTED_INCREMENT_INDEPENDENCE_PASS: `YES`

- NCU_COMPARATOR_INSTANCE_COUNT: `1`

- AUTHORITATIVE_CONSUMER_COUNT: `0`
- PRODUCTION_BUY_CHANGED: `NO`
- SELL_CHANGED: `NO`
- WINNER_CHANGED: `NO`
- SIZING_CHANGED: `NO`
- CASH_CHANGED: `NO`

- ADD_SAFETY_BYPASS_COUNT: `0`
- G129_REGRESSION_COUNT: `0`
- REENTRY_SEMANTIC_CHANGED: `NO`
- RECENT_EXIT_GUARD_BYPASS_COUNT: `0`

- CURRENT_PIT_INFORMATION_PRESERVED: `YES`
- FORBIDDEN_HISTORY_INFORMATION_EXCLUDED: `YES`

- NEW_MODULE_COUNT: `0`
- NEW_AUTHORITY_COUNT: `0`
- NEW_COMPARATOR_COUNT: `0`
- NEW_SCHEMA_FAMILY_COUNT: `0`
- NEW_NUMERIC_WEIGHT_COUNT: `0`
- NEW_THRESHOLD_COUNT: `0`

- FOCUSED_TEST_PASS: `YES`
- OPTION_C_SHADOW_ACCEPTED: `YES`

- MINIMAL_PRODUCTION_REPAIR_READY: `YES_FOR_NEXT_PHASE`
- DIRECT_PRODUCTION_PROMOTION_READY: `NO`

- NEXT_STEP: `Implement the minimal production repair in the existing MCV comparator only: restore class-first/rank-second sort order while preserving GN's accepted-increment independence, history-neutral flags, relationship-after-priority contract, canonical PC propagation, and zero SELL/Winner/Sizing/Cash/ADD/G129/REENTRY/Runtime authority changes.`

## Gate

OPTION_C_SHADOW_ACCEPTED: `YES`

The focused SHADOW bundle proves the minimal repair candidate is internally coherent and matches GU. It does not by itself authorize direct production promotion because this phase explicitly forbids production semantic change.

MINIMAL_PRODUCTION_REPAIR_READY: `YES_FOR_NEXT_PHASE`

DIRECT_PRODUCTION_PROMOTION_READY: `NO`

Final Judgment: GN前の既存MCV class-first / rank-second Current-PIT BUY判断をそのまま再現しつつ、GNで正しく導入したhistory-neutrality・NEW/ADD parity・accepted-increment independenceだけを維持するOption Cは、Production非接続SHADOWで安全に成立した。
