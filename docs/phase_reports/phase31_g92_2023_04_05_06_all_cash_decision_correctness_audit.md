# Phase31-G92 — 2023-04-05/06 All-Cash Decision Correctness Audit

## PRIMARY_JUDGMENT

PHASE31_G92_ALL_CASH_CORRECTNESS_AMBIGUOUS_SELECTED_G90_DEFERRALS_WEAK_TAIL_LIKE_BUT_FULL_OPPORTUNITY_SET_CONTAINS_CREDIBLE_UNSELECTED_ROWS

## Scope

READ-ONLY audit only.

Target run:

```text
runtime-test-historical-extended-smoke-20260824T055234719725Z
```

Target dates:

```text
2023-04-05
2023-04-06
```

No code, config, threshold, weight, run state, fresh-run, resume, replay, or Historical execution was changed or executed for G92. Future return, later performance, and symbol outcome were not used to classify production correctness.

## Executive Conclusion

The `2023-04-05` and `2023-04-06` all-Cash result is not safely classifiable as either fully correct or definitively over-defensive from G90 final partition evidence alone.

At the final G90 deferral boundary, the actual `CASH_PREFERRED` rows are weak-tail-like:

- all are `COMPARABLE_MARGINAL`
- all are `BUY_NEW`
- all have negative runtime opportunity scores
- final frontier rows are weak relative-strength rows
- selected deferral ranks are late (`31-43` on `2023-04-05`, `28-44` on `2023-04-06`)
- low-confidence rows dominate the actual deferred security weight

This means the final G90 decision to return those selected rows to optional Cash is economically plausible under same-date PIT evidence.

However, the full same-date PC opportunity set is mixed, not uniformly weak. Both dates contain higher-ranked, high-confidence rows with positive or materially better opportunity scores and reduced-participation evidence, but those rows do not become final positive security allocations. They are not primarily G90-deferred; they are left outside the selected/deferred final set by upstream PC context such as:

```text
REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION
REENTRY_BLOCK
VALID_SAFETY_RESERVE
```

Therefore:

```text
G90_FINAL_PARTITION_DEFECT_CONFIRMED = NO
WHOLE_DAY_ZERO_SECURITY_CORRECTNESS_PROVEN = NO
ALL_CASH_DECISION_DEFECT_CONFIRMED = PARTIAL
```

The narrow next boundary is not a G90 revert. It is the PC-selected competitor / residual reconsideration boundary that determines why stronger same-date PIT rows are excluded before the G90 final partition sees only weak-tail-like rows.

## Required Judgments

```text
ALL_CASH_DECISION_DEFECT_CONFIRMED = PARTIAL

2023_04_05_ALL_CASH_CORRECTNESS = AMBIGUOUS
2023_04_06_ALL_CASH_CORRECTNESS = AMBIGUOUS

WEAK_FRONTIER_ALL_CASH_IMPLICATION_VALID = PARTIAL

ABSOLUTE_PARTICIPATION_EVIDENCE_OVERRIDDEN_BY_RELATIVE_CONTEXT = PARTIAL

2023_04_05_OPPORTUNITY_SET = MIXED
2023_04_06_OPPORTUNITY_SET = MIXED

MARKET_QUALITY_DIRECT_CAUSE = NO
RISK_PACING_DIRECT_CAUSE = NO
CANDIDATE_WEAKNESS_CAUSE = PARTIAL
G90_FINAL_PARTITION_CAUSE = PARTIAL

ZERO_SECURITY_ARCHITECTURALLY_JUSTIFIED = PARTIAL

EXISTING_EVIDENCE_SUFFICIENT_FOR_SAFE_REPAIR = PARTIAL
REPAIR_REQUIRED = YES
```

## State Summary

### 2023-04-05

```text
existing exposure = 21.78%
positions = 1
available incremental budget = 0.522197
security_allocation_count = 0
cash_preferred_security_deferral_count = 4
authorized_cash_allocation = 0.522197
runtime_buy_plan_count = 0
runtime_add_plan_count = 0
```

### 2023-04-06

```text
existing exposure = 0.00%
positions = 0
available incremental budget = 0.740000
security_allocation_count = 0
cash_preferred_security_deferral_count = 6
authorized_cash_allocation = 0.740000
runtime_buy_plan_count = 0
runtime_add_plan_count = 0
```

Both days have positive Portfolio Policy budget. The direct zero-security result is downstream of capital budget authorization.

## Candidate-by-Candidate Final Deferral Audit

### 2023-04-05

| Symbol | Rank | Class | Score | Confidence | Momentum | Relative Strength | Requested | G90 Resolution | Correctness Read |
| --- | ---: | --- | ---: | ---: | --- | --- | ---: | --- | --- |
| 44270 | 31 | COMPARABLE_MARGINAL | -0.3984 | 0.40 | MIXED_OR_UNRESOLVED | WEAK | 0.026551 | CASH_PREFERRED_DEFER | CASH_ECONOMICALLY_DOMINANT |
| 76920 | 36 | COMPARABLE_MARGINAL | -0.4451 | 0.30 | MIXED_OR_UNRESOLVED | MIXED | 0.038769 | CASH_PREFERRED_DEFER | CASH_ECONOMICALLY_DOMINANT |
| 95560 | 42 | COMPARABLE_MARGINAL | -0.4888 | 0.18 | MIXED_OR_UNRESOLVED | MIXED | 0.229212 | CASH_PREFERRED_DEFER | CASH_ECONOMICALLY_DOMINANT |
| 83080 | 43 | COMPARABLE_MARGINAL | -0.5074 | 0.16 | MIXED_OR_UNRESOLVED | MIXED | 0.045109 | CASH_PREFERRED_DEFER | CASH_ECONOMICALLY_DOMINANT |

G90 reason-code pattern:

```text
CASH_PREFERRED_CLASS_FRONTIER_NOT_CREDIBLE_DEFERRAL = 1
CASH_PREFERRED_FRONTIER_ROW_NOT_CREDIBLE = 1
CASH_PREFERRED_RELATIVE_STRENGTH_WEAK_DEFERRAL = 1
CASH_PREFERRED_AGGREGATE_PRESSURE_AFTER_WEAK_TAIL_BOUNDARY = 3
CASH_PREFERRED_AGGREGATE_WEAK_TAIL_DEFERRAL = 3
CASH_PREFERRED_ROW_PARTICIPATION_EVIDENCE_COMPLETE = 4
PC_PARTICIPATION_DEFERRAL_AUTHORITY = 4
```

The final selected `CASH_PREFERRED` candidates resemble true weak-tail more than G84 normal reduced participation. Their G90 deferral is not by itself proven over-defensive.

### 2023-04-06

| Symbol | Rank | Class | Score | Confidence | Momentum | Relative Strength | Requested | G90 Resolution | Correctness Read |
| --- | ---: | --- | ---: | ---: | --- | --- | ---: | --- | --- |
| 44270 | 28 | COMPARABLE_MARGINAL | -0.3932 | 0.46 | MIXED_OR_UNRESOLVED | WEAK | 0.025826 | CASH_PREFERRED_DEFER | CASH_ECONOMICALLY_DOMINANT |
| 50320 | 29 | COMPARABLE_MARGINAL | -0.4016 | 0.44 | MIXED_OR_UNRESOLVED | MIXED | 0.200446 | CASH_PREFERRED_DEFER | AMBIGUOUS_TO_CASH_DOMINANT |
| 73180 | 30 | COMPARABLE_MARGINAL | -0.4044 | 0.42 | MIXED_OR_UNRESOLVED | MIXED | 0.017690 | CASH_PREFERRED_DEFER | AMBIGUOUS_TO_CASH_DOMINANT |
| 79970 | 38 | COMPARABLE_MARGINAL | -0.4439 | 0.26 | HEALTHY_CONTINUATION | SUPPORTIVE | 0.049990 | CASH_PREFERRED_DEFER | AMBIGUOUS |
| 95560 | 42 | COMPARABLE_MARGINAL | -0.4659 | 0.18 | MIXED_OR_UNRESOLVED | MIXED | 0.234719 | CASH_PREFERRED_DEFER | CASH_ECONOMICALLY_DOMINANT |
| 83080 | 44 | COMPARABLE_MARGINAL | -0.4860 | 0.14 | MIXED_OR_UNRESOLVED | MIXED | 0.044631 | CASH_PREFERRED_DEFER | CASH_ECONOMICALLY_DOMINANT |

G90 reason-code pattern:

```text
CASH_PREFERRED_CLASS_FRONTIER_NOT_CREDIBLE_DEFERRAL = 1
CASH_PREFERRED_FRONTIER_ROW_NOT_CREDIBLE = 1
CASH_PREFERRED_RELATIVE_STRENGTH_WEAK_DEFERRAL = 1
CASH_PREFERRED_AGGREGATE_PRESSURE_AFTER_WEAK_TAIL_BOUNDARY = 5
CASH_PREFERRED_AGGREGATE_WEAK_TAIL_DEFERRAL = 5
CASH_PREFERRED_ROW_PARTICIPATION_EVIDENCE_COMPLETE = 6
PC_PARTICIPATION_DEFERRAL_AUTHORITY = 6
```

`79970` has `HEALTHY_CONTINUATION` and `SUPPORTIVE` evidence, but its rank, score, and confidence remain weak-tail-like (`rank=38`, `score=-0.4439`, `confidence=0.26`). This is not enough to prove over-defense without creating a new threshold.

## Full Opportunity-Set Context

### 2023-04-05

```text
competitors = 19
classes = COMPARABLE_MARGINAL 18, COMPARABLE_HIGH 1
interaction_results = FAIL_CLOSED 14, CASH_PREFERRED 4, BLOCKED 1
median rank = 26
score range = +0.2962 to -0.5074
median score = -0.3712
median confidence = 0.50
momentum = MIXED_OR_UNRESOLVED 14, HEALTHY_CONTINUATION 5
relative strength = MIXED 9, SUPPORTIVE 8, WEAK 2
```

Top same-date rows:

| Symbol | Rank | Score | Confidence | Momentum | Relative Strength | PC Status |
| --- | ---: | ---: | ---: | --- | --- | --- |
| 83060 | 2 | +0.2962 | 0.98 | MIXED_OR_UNRESOLVED | MIXED | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION |
| 59350 | 6 | +0.1610 | 0.90 | HEALTHY_CONTINUATION | SUPPORTIVE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION |
| 77760 | 7 | +0.0192 | 0.88 | MIXED_OR_UNRESOLVED | SUPPORTIVE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION |
| 44440 | 10 | -0.0595 | 0.82 | MIXED_OR_UNRESOLVED | SUPPORTIVE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION |

The selected final deferral rows are weak; the full opportunity set is mixed because higher-ranked reduced-participation candidates exist but do not become final selected security rows.

### 2023-04-06

```text
competitors = 26
classes = COMPARABLE_MARGINAL 26
interaction_results = FAIL_CLOSED 18, CASH_PREFERRED 6, BLOCKED 2
median rank = 24
score range = +0.3103 to -0.4860
median score = -0.3698
median confidence = 0.54
momentum = MIXED_OR_UNRESOLVED 19, HEALTHY_CONTINUATION 7
relative strength = SUPPORTIVE 17, MIXED 8, WEAK 1
```

Top same-date rows:

| Symbol | Rank | Score | Confidence | Momentum | Relative Strength | PC Status |
| --- | ---: | ---: | ---: | --- | --- | --- |
| 83060 | 2 | +0.3103 | 0.98 | MIXED_OR_UNRESOLVED | MIXED | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION |
| 59350 | 3 | +0.2584 | 0.96 | HEALTHY_CONTINUATION | SUPPORTIVE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION |
| 43880 | 4 | +0.2472 | 0.94 | HEALTHY_CONTINUATION | SUPPORTIVE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION |
| 67310 | 5 | +0.2091 | 0.92 | MIXED_OR_UNRESOLVED | SUPPORTIVE | VALID_SAFETY_RESERVE |
| 94340 | 7 | +0.0305 | 0.88 | MIXED_OR_UNRESOLVED | SUPPORTIVE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION |
| 77760 | 8 | +0.0301 | 0.86 | MIXED_OR_UNRESOLVED | SUPPORTIVE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION |

This day is not a uniformly weak opportunity set. The final G90 selected set is weak-tail-like, but the full same-date opportunity set contains credible reduced-participation evidence that does not reach final security allocation.

## Comparison To Known Cohorts

G84 normal reduced-participation `CASH_PREFERRED` rows:

```text
median rank = 18
rank >= 31 = 13.0%
median runtime opportunity score = -0.3543
score < -0.5 = 21.1%
median confidence = 0.66
confidence < 0.3 = 4.1%
```

G84 plateau weak-tail `CASH_PREFERRED` rows:

```text
median rank = 34
rank >= 31 = 60.6%
median runtime opportunity score = -0.4973
score < -0.5 = 48.6%
median confidence = 0.34
confidence < 0.3 = 39.4%
```

G92 final deferral rows:

```text
2023-04-05 selected deferral ranks = 31, 36, 42, 43
2023-04-05 selected deferral score range = -0.3984 to -0.5074
2023-04-05 selected deferral confidence range = 0.16 to 0.40

2023-04-06 selected deferral ranks = 28, 29, 30, 38, 42, 44
2023-04-06 selected deferral score range = -0.3932 to -0.4860
2023-04-06 selected deferral confidence range = 0.14 to 0.46
```

The final deferrals are closer to weak-tail than to G84 normal participation. This argues against a simple G90 over-defense conclusion for the rows that G90 actually deferred.

But the full same-date opportunity set includes rows that look closer to normal participation or at least credible reduced participation. That prevents a clean `CORRECT_ALL_CASH` classification for the whole daily decision path.

## Frontier Failure Audit

The frontier rows are:

```text
2023-04-05 44270 rank 31 score -0.3984 confidence 0.40 relative_strength WEAK
2023-04-06 44270 rank 28 score -0.3932 confidence 0.46 relative_strength WEAK
```

For the final selected `CASH_PREFERRED` set, weak frontier is a reasonable signal: non-frontier rows are not independently stronger in absolute score/confidence terms except for limited `79970` momentum/relative-strength context on `2023-04-06`.

However, weak frontier must not become a general architecture rule that all same-date securities lose to Cash. The full opportunity set contains higher-ranked candidates outside the selected final deferral set.

Therefore:

```text
WEAK_FRONTIER_ALL_CASH_IMPLICATION_VALID = PARTIAL
```

It is valid for the actual weak selected deferral subset, but not valid as a whole-day all-security implication.

## Absolute vs Relative Opportunity

For selected G90 deferrals:

```text
ABSOLUTE_PARTICIPATION_EVIDENCE_OVERRIDDEN_BY_RELATIVE_CONTEXT = NO_TO_PARTIAL
```

The selected rows have some reduced-participation evidence, but their absolute evidence is mostly weak.

For the full opportunity set:

```text
ABSOLUTE_PARTICIPATION_EVIDENCE_OVERRIDDEN_BY_RELATIVE_CONTEXT = PARTIAL
```

High-ranked rows with stronger same-date evidence are excluded before final G90 resolution rather than explicitly tested as participation-valid final allocations.

This is the key ambiguity.

## Market Context Interaction

Market Quality / Risk Pacing are context, not direct zero-security authorities.

Evidence:

```text
Market / Risk context = cautious / defensive deployment capacity
capital budget is positive on both dates
risk_pacing_directly_sets_quantity = false
risk_pacing_direct_exposure_percent_setter = false
candidate_rank_mutated_by_risk_pacing = false
Runtime cash winner redecision = false
Runtime BUY plan count = 0 because PC/PS lineage carries security_allocation_total = 0
```

The direct daily boundary is:

```text
Portfolio Policy positive budget
-> PC competitor selection / residual reconsideration
-> G90 final selected rows all deferred to Cash
-> PS sees no positive security allocation
-> Runtime plans no BUY
```

## Repair Readiness

Do not repair by reverting G90.

G90 final partition correctly preserves optional Cash for rows that resemble weak-tail. The confirmed missing semantic is narrower and upstream-adjacent:

```text
credible absolute participation evidence can remain outside the final selected security set,
while the selected set that reaches G90 contains only weak-tail-like rows,
causing the day-level result to become all-Cash.
```

The safest next task should audit/repair only this boundary:

```text
PC selected competitor / residual reconsideration
-> final CASH_PREFERRED participation/deferral resolution input set
```

The repair must preserve:

- weak-tail Cash dominance
- no forced deployment
- no fixed exposure or position count
- no future-return-derived thresholds
- no symbol-specific exception
- Market Quality as pacing context, not a hard BUY gate

## Integrity

```text
CODE_CHANGED = NO
CONFIG_CHANGED = NO
THRESHOLD_WEIGHT_TUNING = NO
RUN_MODIFIED = NO
FRESH_RUN_EXECUTED = NO
RESUME_EXECUTED = NO
REPLAY_EXECUTED = NO
LONG_HISTORICAL_EXECUTED = NO
FUTURE_INPUT_COUNT = 0
HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0
G90_REVERT_RECOMMENDED = NO
```

## Final Answer Shape

```text
AMBIGUOUS / PARTIAL DEFECT
```

The system did not simply miss a known winner. The selected G90 deferral rows on `2023-04-05` and `2023-04-06` are weak enough that optional Cash can plausibly dominate them. But the whole-day all-Cash decision is not proven correct, because stronger same-date PIT candidates existed and failed to reach final positive security allocation through the upstream PC selected-set / residual reconsideration path.
