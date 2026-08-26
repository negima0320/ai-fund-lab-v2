# Phase31-G80 - Weak-Opportunity Security/Cash Partition Root-Cause Audit

## PRIMARY_JUDGMENT

PHASE31_G80_WEAK_OPPORTUNITY_SECURITY_CASH_PARTITION_ROOT_CAUSE_CONFIRMED

Target run:

`runtime-test-historical-extended-smoke-20260823T140946562431Z`

Completed snapshot used:

- completed business days = `219`
- latest completed business date = `2023-08-22`

No code, config, threshold, weight, run state, fresh-run, resume, replay, or
Historical execution was changed or performed. G74 repair was not applied to
this running run.

## Executive Conclusion

WEAK_OPPORTUNITY_OVERDEPLOYMENT_FIRST_CAUSAL_BOUNDARY =
`portfolio_construction._canonical_multi_allocation_deployment_set()`
security/Cash materialization contract.

The first causal boundary is not Portfolio Policy budget production. Plateau
weak and strong opportunity subsets had similar budgets. The boundary is where
Portfolio Construction converts:

`market_candidate_cash_interaction.interaction_result = CASH_PREFERRED`

into:

positive `security_allocations[]` before calculating Cash as residual.

Code evidence:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:3007-3015`
  includes `CASH_PREFERRED` in the allowed interaction states for positive
  security allocation.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:3066-3075`
  calculates `security_total` first, then `cash_allocation` as the minimum of
  cash request and residual after securities.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:3148-3171`
  persists this as the final multi-allocation security/Cash partition.
- `tests/strategy/test_phase31_g57_multi_allocation_shadow.py:35-54`
  explicitly accepts cautious marginal `CASH_PREFERRED` securities remaining in
  `security_allocations`.

Therefore Cash is represented, but it is not a true per-increment economic
competitor at the final multi-allocation stage. It is a preference/diagnostic
and residual allocation after the selected security requests have consumed
budget.

## Representative Date Selection

Dates were selected using same-date evidence only:

- weak-opportunity / high-security cases: low top10 score, low Cash, high
  security or marginal security weight, rank `31+` BUY_NEW materialization.
- strong-opportunity / higher-Cash controls: higher top10 score, higher Cash,
  lower security or constrained security materialization.

Historical PnL was not used for date selection or correctness judgment.

### Selected Weak-Opportunity Cases

| Date | Top10 Score | MQ | Risk Pacing | Budget | Cash | Security Weight | Marginal Weight | Rank31+ Count / Weight |
|---|---:|---|---|---:|---:|---:|---:|---:|
| 2023-07-21 | -0.122 | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 29.86% | 1.71% | 28.15% | 25.12% | 3 / 12.59% |
| 2023-07-24 | -0.121 | RECOVERY_CONFIRMATION_INCOMPLETE | GRADUAL_REDEPLOYMENT | 35.42% | 4.28% | 31.14% | 23.36% | 3 / 15.69% |
| 2023-07-25 | -0.127 | RECOVERY_CONFIRMATION_INCOMPLETE | GRADUAL_REDEPLOYMENT | 31.99% | 1.30% | 30.69% | 28.12% | 2 / 5.78% |
| 2023-08-01 | -0.075 | RECOVERY_CONFIRMATION_INCOMPLETE | GRADUAL_REDEPLOYMENT | 36.44% | 3.04% | 33.40% | 33.40% | 2 / 17.17% |
| 2023-07-20 | -0.102 | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 24.11% | 7.41% | 16.69% | 16.69% | 2 / 11.61% |

### Selected Strong-Day Controls

| Date | Top10 Score | MQ | Risk Pacing | Budget | Cash | Security Weight | Marginal Weight | Strong-Day Explanation |
|---|---:|---|---|---:|---:|---:|---:|---|
| 2023-06-21 | +0.136 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 64.49% | 64.49% | 0.00% | 0.00% | concentration/no deployable final security |
| 2023-06-22 | +0.135 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 63.95% | 50.57% | 13.38% | 13.38% | one executable security; large residual Cash |
| 2023-06-23 | +0.122 | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 56.50% | 48.26% | 8.24% | 8.24% | cautious Cash preference plus limited executable security |
| 2023-06-26 | +0.129 | SHORT_TERM_BREADTH_BREAKDOWN | CAUTIOUS_DEPLOYMENT | 70.16% | 70.16% | 0.00% | 0.00% | no selected final security |
| 2023-06-27 | +0.142 | SHORT_TERM_BREADTH_BREAKDOWN | CAUTIOUS_DEPLOYMENT | 73.38% | 64.29% | 9.09% | 9.09% | concentration residual; only two small executable securities |

## End-to-End Boundary Trace

Observed chain:

1. Portfolio Policy produced an authoritative
   `incremental_capital_budget_envelope.v1`.
2. PC built capital competitors from existing member evidence.
3. `market_candidate_cash_interaction` correctly labeled many weak/marginal
   candidates as `CASH_PREFERRED`.
4. `_canonical_multi_allocation_deployment_set()` still admitted
   `CASH_PREFERRED` rows into `security_allocations[]`.
5. It filled security allocations in relative-priority order using each
   competitor's already positive `accepted_weight`.
6. Cash was calculated afterward as residual:
   `min(cash_evidence.remaining_cash_weight, available_budget - security_total)`.
7. Lot-aware compatibility preserved these allocations; it did not create the
   weak-tail exposure.
8. PS and Runtime consumed the resulting security set; no Runtime priority
   redecision was identified.

## Audit A - Budget Semantics

CAPITAL_BUDGET_IS_MAXIMUM = YES

Contractually, the budget is a maximum / envelope. The multi-allocation payload
conserves:

`security_allocation_total + authorized_cash_allocation + unallocated_residual`

within `available_incremental_budget`.

Operationally, however, PC converts all positive selected security competitors
into security allocations before Cash is applied. This produces behavior
equivalent to:

`deploy to positive selected securities first; Cash receives the remaining budget`

even when many selected securities are explicitly tagged `CASH_PREFERRED`.

H2_BUDGET_SECURITY_TARGET_PRESSURE = PARTIAL

Reason:

The budget itself is not a hard security target, because Cash can receive large
allocation when security requests are absent or constrained. But after selected
security competitors exist, the multi-allocation consumer behaves like a
security-first fill against budget.

## Audit B - Cash Competition Semantics

Required answers:

1. Is Cash an explicit capital competitor?
   YES. `cash_competitor_evidence.v1` and `CASH_OPTIONALITY` are present.
2. Does Cash have an economic priority / score?
   PARTIAL. It has `cash_preference_semantic` and reason codes, but no
   per-increment score comparable to candidate rank/confidence/quality.
3. Is Cash compared against each incremental security candidate?
   PARTIAL. `market_candidate_cash_interaction` labels candidates such as
   `CASH_PREFERRED`, but final allocation does not treat that label as
   eliminating or reducing the security increment to zero.
4. Can Cash beat a rank 31+ marginal candidate solely because its absolute
   investment value is weak?
   NO in the final multi-allocation materialization. Rank 31+ marginal rows
   with `CASH_PREFERRED` still receive positive allocation.
5. Or is Cash only whatever remains after security allocation?
   YES at `_canonical_multi_allocation_deployment_set()`.
6. At which exact function/contract is Cash weight determined?
   `_canonical_multi_allocation_deployment_set()`, after `security_total` is
   calculated.

CASH_IS_TRUE_INCREMENTAL_CAPITAL_COMPETITOR = PARTIAL

H3_CASH_RESIDUAL_NOT_TRUE_COMPETITOR = CONFIRMED

Reason:

Cash is a first-class artifact and can be the single pre-final winner, but in
the multi-allocation security/Cash partition it functions as residual. The
clearest artifact symptom is 2023-07-21: `capital_competition_winner_type =
CASH_OPTIONALITY`, yet all four final security allocations have
`interaction_result = CASH_PREFERRED` and positive allocation.

## Audit C - Absolute vs Relative Quality

Weak-tail rows carry absolute evidence:

- opportunity rank
- runtime opportunity score
- confidence
- quality score
- canonical opportunity quality class
- `CASH_PREFERRED` interaction reason codes

But final allocation consumes these primarily as relative ordering and broad
interaction class. The within-class evidence explicitly records
`WITHIN_CLASS_RELATIVE_PRIORITY_EVIDENCE_ONLY`, and `_multi_allocation_priority_sort_key()`
uses the priority sort key for ordering. There is no final authority that says:

`absolute weak value -> Cash beats this increment`

Observed examples:

| Date | Symbol | Rank | Confidence | Score | Class | Interaction | Requested | Authorized |
|---|---:|---:|---:|---:|---|---|---:|---:|
| 2023-07-21 | 14390 | 32 | 0.36 | -0.559 | COMPARABLE_MARGINAL | CASH_PREFERRED | 7.50% | 7.50% |
| 2023-07-21 | 47070 | 35 | 0.28 | -0.594 | COMPARABLE_MARGINAL | CASH_PREFERRED | 2.05% | 2.05% |
| 2023-07-24 | 69320 | 41 | 0.00 | -0.906 | COMPARABLE_MARGINAL | CASH_PREFERRED | 7.91% | 7.91% |
| 2023-07-25 | 45880 | 37 | 0.28 | -0.674 | COMPARABLE_MARGINAL | CASH_PREFERRED | 3.21% | 3.21% |
| 2023-08-01 | 37600 | 39 | 0.24 | -0.644 | COMPARABLE_MARGINAL | CASH_PREFERRED | 12.85% | 12.85% |
| 2023-08-01 | 87500 | 41 | 0.00 | -0.833 | COMPARABLE_MARGINAL | CASH_PREFERRED | 4.32% | 4.32% |

ABSOLUTE_OPPORTUNITY_QUALITY_REACHES_FINAL_ALLOCATION_AUTHORITY = PARTIAL

RELATIVE_PRIORITY_DOMINATES_ABSOLUTE_VALUE = YES

H1_RELATIVE_PRIORITY_ONLY = PARTIAL

H4_ABSOLUTE_QUALITY_AUTHORITY_LOSS = CONFIRMED

Reason:

Absolute evidence reaches the payload and appears in lineage, but it is not
authoritative for the final Cash-vs-security quantity partition. Once the row
has positive `accepted_weight`, relative ordering plus remaining budget is
enough to preserve positive allocation.

The contract/code semantics imply that if all stronger competitors were removed
while a weak candidate's own accepted weight remained positive, that weak
candidate would still receive allocation until budget is exhausted, unless
another constraint made it blocked or infeasible.

## Audit D - Aggregate Tail Exposure

Selected weak-day aggregate tail exposure:

| Date | Rank31+ Count | Rank31+ Weight | Low-Confidence Allocated Weight | Median Weak-Tail Weight | Cash Weight |
|---|---:|---:|---:|---:|---:|
| 2023-07-21 | 3 | 12.59% | 12.59% | 7.50% | 1.71% |
| 2023-07-24 | 3 | 15.69% | 15.69% | 7.91% | 4.28% |
| 2023-07-25 | 2 | 5.78% | 5.78% | 3.21% | 1.30% |
| 2023-08-01 | 2 | 17.17% | 17.17% | 8.59% | 3.04% |
| 2023-07-20 | 2 | 11.61% | 11.61% | 5.81% | 7.41% |

REDUCED_ONLY_AGGREGATE_TAIL_RISK = YES

H6_REDUCED_ONLY_AGGREGATE_TAIL_RISK = CONFIRMED

Reason:

`BUY_NEW_REDUCED_ONLY` / `CASH_PREFERRED` reduces or labels individual rows, but
does not cap aggregate weak-tail consumption. Several small or medium
allocations compound into material weak-tail exposure.

## Audit E - Lot / Residual

For selected weak cases:

- weak-tail positive allocation existed before the final lot compatibility
  payload.
- final compatibility states were `LOT_EXECUTABLE_COMPATIBLE`.
- `lower_priority_implicit_promotion_allowed = false`.
- `priority_inversion_after_compatibility = false`.
- `unallocated_residual = 0`.

WEAK_TAIL_ORIGINATES_PRE_LOT = YES

LOT_RESIDUAL_PROMOTION_CAUSE = NO

LOWER_PRIORITY_IMPLICIT_PROMOTION = NO

H5_LOT_RESIDUAL_WEAK_TAIL_PROMOTION = REJECTED

Reason:

Lot-aware final reallocation changed some Cash amounts and executable counts,
but the core weak-tail positive allocation comes from the PC security/Cash
partition accepting positive security competitors. This is not a G61/G63
priority inversion or residual promotion failure.

## Audit F - Strong-Day Higher-Cash Inversion Cause

STRONG_DAY_HIGHER_CASH_INVERSION_CAUSE =
FEWER_OR_CONSTRAINED_EXECUTABLE_SECURITY_REQUESTS_LEAVE_MORE_RESIDUAL_CASH

Strong-day controls retained more Cash because the security request set was
smaller or constrained:

- 2023-06-21: final security count `0`, Cash `64.49%`, reason codes include
  `CONCENTRATION_BLOCK` / `VALID_POLICY_RESERVE`.
- 2023-06-26: final security count `0`, Cash `70.16%`, reason codes include
  `NO_VALID_COMPETITOR`.
- 2023-06-27: final security count `2`, security `9.09%`, Cash `64.29%`,
  reason codes include `CONCENTRATION_BLOCK` / `CONCENTRATION_OPTIONALITY`.
- 2023-06-22 and 2023-06-23: only one/two small executable securities, leaving
  large residual Cash.

This inversion is therefore not because stronger days have a better
opportunity-set-sensitive Cash competitor. It occurs because final security
requests are fewer or constrained, so residual Cash is mechanically larger.
Weak days have more positive, lot-executable selected competitors, so they
consume budget before Cash is calculated.

## Plateau Aggregate CASH_PREFERRED Evidence

Across Plateau completed dates in the audit snapshot:

| Interaction Result in Final Security Allocations | Count | Authorized Weight |
|---|---:|---:|
| CASH_PREFERRED | 142 | 879.40% cumulative daily weight |
| DEPLOY_ELIGIBLE | 26 | 212.09% cumulative daily weight |
| SELECTIVE_COMPETITION | 16 | 111.68% cumulative daily weight |

Top observed dates by `CASH_PREFERRED` security weight:

| Date | Security Count | Cash | CASH_PREFERRED Count | CASH_PREFERRED Weight |
|---|---:|---:|---:|---:|
| 2023-07-06 | 7 | 0.49% | 7 | 46.33% |
| 2023-08-21 | 7 | 3.35% | 7 | 45.84% |
| 2023-08-09 | 8 | 3.02% | 7 | 39.62% |
| 2023-07-27 | 6 | 20.28% | 6 | 38.80% |
| 2023-08-01 | 5 | 3.04% | 5 | 33.40% |
| 2023-07-21 | 4 | 1.71% | 4 | 28.15% |
| 2023-07-25 | 5 | 1.30% | 4 | 28.12% |

This confirms the issue is structural, not a single-date anomaly.

## Required Root-Cause Classification

H1_RELATIVE_PRIORITY_ONLY = PARTIAL

H2_BUDGET_SECURITY_TARGET_PRESSURE = PARTIAL

H3_CASH_RESIDUAL_NOT_TRUE_COMPETITOR = CONFIRMED

H4_ABSOLUTE_QUALITY_AUTHORITY_LOSS = CONFIRMED

H5_LOT_RESIDUAL_WEAK_TAIL_PROMOTION = REJECTED

H6_REDUCED_ONLY_AGGREGATE_TAIL_RISK = CONFIRMED

## Required Judgment

WEAK_OPPORTUNITY_OVERDEPLOYMENT_FIRST_CAUSAL_BOUNDARY =
PORTFOLIO_CONSTRUCTION_CANONICAL_MULTI_ALLOCATION_SECURITY_CASH_PARTITION

CAPITAL_BUDGET_IS_MAXIMUM = YES

CASH_IS_TRUE_INCREMENTAL_CAPITAL_COMPETITOR = PARTIAL

ABSOLUTE_OPPORTUNITY_QUALITY_REACHES_FINAL_ALLOCATION_AUTHORITY = PARTIAL

RELATIVE_PRIORITY_DOMINATES_ABSOLUTE_VALUE = YES

REDUCED_ONLY_AGGREGATE_TAIL_RISK = YES

WEAK_TAIL_ORIGINATES_PRE_LOT = YES

LOT_RESIDUAL_PROMOTION_CAUSE = NO

LOWER_PRIORITY_IMPLICIT_PROMOTION = NO

STRONG_DAY_HIGHER_CASH_INVERSION_CAUSE =
FEWER_OR_CONSTRAINED_EXECUTABLE_SECURITY_REQUESTS_LEAVE_MORE_RESIDUAL_CASH

ARCHITECTURE_DEFECT_CONFIRMED = YES

REPAIR_REQUIRED = YES

CODE_CHANGED = NO

RUN_MODIFIED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

MARKET_QUALITY_CHANGED = NO

CANDIDATE_RANKING_CHANGED = NO

BUY_FILTER_CREATED = NO

CASH_TARGET_CREATED = NO

OPPORTUNITY_SET_QUALITY_FEATURE_CREATED = NO

NEW_INDICATOR_CREATED = NO

NEW_SCORE_CREATED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

## Highest-Value Next Action

Repair the existing PC security/Cash partition semantics at the confirmed
boundary only: make `CASH_PREFERRED` and absolute opportunity-quality evidence
binding for final incremental security allocation versus optional Cash, while
preserving no hard BUY filter, no blanket COMPARABLE_MARGINAL exclusion, no
fixed Cash target, no new score, no Market Quality semantic change, and no
Position Sizing quantity authority transfer.
