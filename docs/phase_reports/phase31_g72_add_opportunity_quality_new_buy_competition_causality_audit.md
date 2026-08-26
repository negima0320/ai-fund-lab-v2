# Phase31-G72 — ADD Opportunity Quality & NEW_BUY Competition Causality Audit

## PRIMARY_JUDGMENT

PHASE31_G72_LOW_ADD_PARTIALLY_JUSTIFIED_WITH_MISSED_AMPLIFICATION_RISK

The running long Historical run was audited READ-ONLY using completed business
dates only. No run operation, fresh-run, resume, replay, code change, config
change, threshold change, weight change, or parameter tuning was performed.

```text
RUN_ID = runtime-test-historical-extended-smoke-20260823T140946562431Z
RUN_STATUS_AT_SNAPSHOT = RUNNING
RUN_NEXT_JOB_AT_SNAPSHOT = 2023-07-07:current_valuation_refresh
COMPLETED_BUSINESS_DATES = 188
AUDIT_WINDOW = 2022-10-03 through 2023-07-06
COMPLETION_EVIDENCE = daily/<date>/day_completion/day_completion_evidence.json status PASS
```

This audit uses later campaign outcome only to select the G70 top-winner cohort
for case-study inspection. All correctness judgments below use same-date PIT
PM / PC / Position Sizing / Runtime evidence only.

## Required Judgment

```text
PM_ADD_INTENT_SPARSITY_CAUSE =
  PM is intentionally narrow: HOLD-worthy evidence is not ADD action authority.
  Most existing positions remain HOLD/REDUCE/EXIT; only explicit PM ADD reason
  codes no_loss_averaging + opportunity_rank_still_high + strong_trend_continuation
  become ADD intent.

PC_ADD_COMPETITION_QUALITY =
  MIXED: many ADD losses are justified by same-date NEW_BUY superiority or weak
  ADD incremental evidence, but 2 same-date PIT cases show possible ADD semantic
  bias and 6 cap/zeroization cases are mechanical rather than economic.

NEW_BUY_SUPERIORITY_JUSTIFIED = PARTIAL
ADD_SEMANTIC_BIAS_EVIDENCE = YES
ADD_MECHANICAL_ZEROIZATION_MATERIAL = YES
WINNER_AMPLIFICATION_OPPORTUNITY_MISSED = UNPROVEN
MARKET_QUALITY_DIRECT_ADD_SUPPRESSION = NO
ADD_LOW_RATE_ECONOMICALLY_JUSTIFIED = PARTIAL
```

## PM ADD Intent Sparsity

Existing-position PM action counts:

```text
EXISTING_POSITION_EVALUATIONS = 1,734
PM_ADD_INTENTS = 68
PM_HOLD_COUNT = 1,081
PM_REDUCE_COUNT = 279
PM_EXIT_COUNT = 306
PM_ADD_RATE = 3.92%
```

Window breakdown:

```text
WINDOW                       TOTAL  ADD HOLD REDUCE EXIT ADD_RATE
2022-10_to_11                  379   47  235     50   47   12.40%
2022-12_to_2023-02             654    6  436     94  118    0.92%
2023-03-15_to_2023-04-06       134    4   77     22   31    2.99%
2023-04-07_onward              467   10  264     98   95    2.14%
other                          100    1   69     15   15    1.00%
```

The drop from 47 ADD intents in 2022-10/11 to 6 in 2022-12 through 2023-02 is
not caused by missing PM artifacts. It is caused by PM choosing HOLD / REDUCE /
EXIT instead of ADD. HOLD alone rises from 235 to 436 in the 2022-12 through
2023-02 window.

Top HOLD-not-ADD reason codes:

```text
structured_hold_worthiness_pass       1,081
trend_continuation                      796
downside_risk_contained                 635
positive_expected_edge                  130
hold_score_above_exit_threshold         126
profit_retention_break                   16
```

HOLD state evidence:

```text
HOLD_CANONICAL_SELL_STATE_HEALTHY_OR_RECOVERING = 1,065
HOLD_CANONICAL_SELL_STATE_EXIT_GRADE = 16
HOLD_ADD_WORTHINESS_STATUS_PASS = 1,081
HOLD_ADD_WORTHINESS_NOT_ACTION_AUTHORITY = 1,081
HOLD_CONTINUATION_QUALITY_STATUS_PASS = 1,081
HOLD_DOWNSIDE_RISK_STATUS_PASS = 1,081
```

Representative HOLD example:

```text
2022-12-01 94340
action = HOLD
reason_codes = downside_risk_contained, structured_hold_worthiness_pass
add_worthiness.status = PASS
add_worthiness.not_action_authority = true
hold_worthy_equals_add_worthy = false
current_campaign_relative_return = +3.08%
observed_giveback = 3.20%
```

Therefore, PM ADD sparsity is mainly semantic: PM continuation evidence
supports retaining the position, but it does not automatically authorize
incremental capital.

## PC ADD Competition

The 68 PM ADD intents all reached PC as ADD competitors.

```text
PC_ADD_INTENTS = 68
PC_ADD_ALLOCATED = 10
PC_ADD_NOT_ALLOCATED = 58
ADD_LOST_TO_NEW_BUY_RAW_REASON_COUNT = 54
ADD_LOST_TO_CASH_RAW_REASON_COUNT = 4
ADD_INSUFFICIENT_EVIDENCE_RAW_REASON_COUNT = 52
ADD_ZERO_DELTA_RAW_REASON_COUNT = 52
ADD_SAFETY_CAP_BOUND_RAW_REASON_COUNT = 6
```

Reason codes overlap within the same ADD row. To avoid double counting, the
58 non-allocated ADD rows were also classified with an exclusive causal order:
cap/zeroization first, then NEW_BUY superiority, then ADD weakness, then
semantic-bias candidate.

```text
LEGITIMATE_NEW_BUY_SUPERIOR = 36
LEGITIMATE_ADD_WEAK = 14
CAPITAL_CONSTRAINT_CORRECT_PRIORITY = 0
POSSIBLE_ADD_SEMANTIC_BIAS = 2
LOT_CAP_ZEROIZATION = 6
INSUFFICIENT_EVIDENCE_TO_JUDGE = 0
ALLOCATED_ADD = 10
```

### LEGITIMATE_NEW_BUY_SUPERIOR

36 ADD losses had same-date `opportunity_cost.comparison_result =
NEW_BUY_SUPERIOR` and best NEW_BUY score greater than ADD candidate score.

Representative examples:

```text
DATE        ADD_SYMBOL ADD_SCORE BEST_NEW_BUY_SCORE RESULT
2022-10-05  94340        0.2247             0.3656  NEW_BUY_SUPERIOR
2022-11-01  99840        0.0906             0.1359  NEW_BUY_SUPERIOR
2023-03-22  59350        0.1931             0.3413  NEW_BUY_SUPERIOR
2023-03-29  59350        0.2193             0.3059  NEW_BUY_SUPERIOR
2023-06-28  40520        0.2104             0.2569  NEW_BUY_SUPERIOR
```

These support `LOW ADD = CORRECT CAPITAL ALLOCATION` for that subset.

### LEGITIMATE_ADD_WEAK

14 ADD losses had ADD opportunity-cost PASS or not clearly inferior, but
canonical ADD incremental evidence was weak:

```text
incremental_investment_value.state = UNKNOWN
incremental_investment_value.status = FAIL_CLOSED
reason = ADD_INCREMENTAL_VALUE_UNKNOWN
proposed_incremental_target_weight = 0
```

Representative examples:

```text
DATE        ADD_SYMBOL ADD_SCORE BEST_NEW_BUY_SCORE OPP_COST  INCREMENTAL_VALUE
2022-10-07  94320        0.3634             0.0620  PASS      UNKNOWN/FAIL_CLOSED
2022-10-17  94340        0.2432             0.1656  PASS      UNKNOWN/FAIL_CLOSED
2022-10-24  94320        0.3965            -0.0058  PASS      UNKNOWN/FAIL_CLOSED
2023-06-20  40520        0.1548             0.1030  PASS      UNKNOWN/FAIL_CLOSED
```

These do not prove NEW_BUY superiority. They show ADD was not allowed to consume
capital because ADD-specific incremental evidence failed closed.

### POSSIBLE_ADD_SEMANTIC_BIAS

2 ADD losses had both:

```text
incremental_investment_value = POSITIVE/PASS
opportunity_cost = PASS
ADD candidate score > best NEW_BUY score
accepted_weight = 0
```

Cases:

```text
2022-10-21 94320 ADD_SCORE=0.4063 BEST_NEW_BUY_SCORE=0.0836
2022-11-10 99840 ADD_SCORE=0.2185 BEST_NEW_BUY_SCORE=0.1788
```

These are the clearest same-date PIT evidence of possible ADD semantic bias.
They are few, so they do not explain the entire low ADD rate, but they are real
enough to warrant a focused follow-up.

### LOT_CAP_ZEROIZATION

6 ADD losses had positive ADD evidence and opportunity-cost PASS, but safety /
cap reason codes suppressed incremental allocation:

```text
ADD_COMPETITOR_ELIGIBLE
ADD_SAFETY_CAP_BOUND
VALID_SAFETY_RESERVE
ADD_LOST_TO_NEW_BUY
```

Representative dates:

```text
2022-11-08 99840
2022-11-14 99840
2022-11-15 99840
2022-11-16 99840
2022-11-18 99840
2022-11-21 99840
```

These are mechanical/cap-driven, not pure economic competition losses.

## Zero Delta Separation

Among 58 non-allocated ADD rows:

```text
GENUINE_TARGET_UNCHANGED_OR_NO_POSITIVE_DELTA = 52
PROPOSED_INCREMENTAL_WEIGHT_ZERO = 52
ALREADY_AT_STRATEGY_OR_SAFETY_CAP = 6
SAFETY_CAP = 6
LOT_INFEASIBLE = 0 observed as primary reason
MINIMUM_NOTIONAL = 0 observed as primary reason
INSUFFICIENT_RESIDUAL_BUDGET = 0 primary
NEW_BUY_COMPETITION_CONSEQUENCE = 58 overlapping
OTHER = 0
```

Economic competition and mechanical zeroization are entangled in raw reason
codes. The exclusive classification above separates them: 36 NEW_BUY superior,
14 ADD weak, 6 cap/zeroization, 2 possible bias.

## Winner Cohort Diagnostic

The G70 top positive campaigns were inspected only for same-date ADD evidence.

```text
SYMBOL HELD_DATES PM_ADD_DATES PC_ALLOCATED RESULT
59350         23            4            0  ADD intent existed; NEW_BUY superior each ADD date
67310          3            0            0  no same-date PM ADD
44440          3            0            0  no same-date PM ADD
70720         21            0            0  no same-date PM ADD
71160         28            0            0  no same-date PM ADD
64240          4            0            0  no same-date PM ADD
49370          2            0            0  no same-date PM ADD
72140          4            0            0  no same-date PM ADD
93410         14            0            0  no same-date PM ADD
40520         13            7            0  ADD intent existed; mostly NEW_BUY superior / ADD weak
```

### 59350

```text
DATE        ADD_SCORE BEST_NEW_BUY_SCORE OPP_COST_RESULT   INCREMENTAL_VALUE  WINNER
2023-03-22    0.1931             0.3413  NEW_BUY_SUPERIOR UNKNOWN/FAIL_CLOSED NEW_BUY multi-allocation
2023-03-23    0.2166             0.3416  NEW_BUY_SUPERIOR UNKNOWN/FAIL_CLOSED NEW_BUY multi-allocation
2023-03-24    0.1638             0.2180  NEW_BUY_SUPERIOR UNKNOWN/FAIL_CLOSED NEW_BUY/Cash context
2023-03-29    0.2193             0.3059  NEW_BUY_SUPERIOR UNKNOWN/FAIL_CLOSED NEW_BUY multi-allocation
```

For 59350, same-date PC evidence supports not allocating ADD: the ADD candidate
was both incremental-value fail-closed and lower than best NEW_BUY by the
opportunity-cost comparator.

### 40520

```text
DATE        ADD_SCORE BEST_NEW_BUY_SCORE OPP_COST_RESULT   INCREMENTAL_VALUE  WINNER
2023-06-20    0.1548             0.1030  PASS             UNKNOWN/FAIL_CLOSED NEW_BUY
2023-06-21    0.1380             0.4271  NEW_BUY_SUPERIOR UNKNOWN/FAIL_CLOSED Cash
2023-06-23    0.1782             0.4996  NEW_BUY_SUPERIOR UNKNOWN/FAIL_CLOSED NEW_BUY/Cash
2023-06-26    0.2081             0.5357  NEW_BUY_SUPERIOR UNKNOWN/FAIL_CLOSED Cash
2023-06-27    0.2281             0.5541  NEW_BUY_SUPERIOR UNKNOWN/FAIL_CLOSED NEW_BUY/Cash
2023-06-28    0.2104             0.2569  NEW_BUY_SUPERIOR UNKNOWN/FAIL_CLOSED NEW_BUY/Cash
2023-06-29    0.1924             0.2513  NEW_BUY_SUPERIOR UNKNOWN/FAIL_CLOSED NEW_BUY/Cash
```

40520 is mixed. Six dates support NEW_BUY superiority. On 2023-06-20,
opportunity cost passed because the ADD score exceeded best NEW_BUY, but
incremental value remained UNKNOWN/FAIL_CLOSED and proposed incremental target
weight was 0. That is not a clean NEW_BUY-superior case; it is ADD-specific
incremental evidence weakness.

## Market Quality

Market Quality / Risk Pacing was not an ADD-specific admission gate.

```text
MARKET_QUALITY_DIRECT_ADD_SUPPRESSION = NO
RISK_PACING_BLOCKS_DEPLOYMENT_FOR_ADD = 0
MARKET_QUALITY_SECURITY_ADMISSION_OWNER = NO
```

Successful BUY_ADD happened mostly during cautious states:

```text
CAUTIOUS_DEPLOYMENT BUY_ADD = 9
GRADUAL_REDEPLOYMENT BUY_ADD = 1
NORMAL_DEPLOYMENT BUY_ADD = 0
```

That pattern argues against a direct Market Quality ADD kill switch. Market
Quality affects available capital / cash competition context, but the actual
ADD drop is PM intent sparsity plus ADD incremental evidence / NEW_BUY
competition.

## Answer To Core Question

```text
LOW_ADD_CORRECT_CAPITAL_ALLOCATION = PARTIAL
LOW_ADD_MISSED_WINNER_AMPLIFICATION = UNPROVEN_BUT_POSSIBLE_IN_SMALL_SUBSET
```

Evidence supporting correct allocation:

- 36 non-allocated ADD rows had same-date NEW_BUY superiority.
- 14 had ADD incremental value UNKNOWN/FAIL_CLOSED.
- 6 were cap/safety constrained.
- Market Quality did not directly suppress ADD.

Evidence suggesting possible missed amplification:

- 2 rows had ADD incremental value PASS and opportunity-cost PASS but still
  accepted zero weight.
- Top winners rarely produced PM ADD intent; this is a PM semantic narrowness,
  not an outcome-based proof that ADD should have happened.
- 40520 on 2023-06-20 had ADD score above best NEW_BUY but failed on ADD
  incremental evidence.

## Highest-Value Next Action

Run a focused READ-ONLY contract audit of the two `POSSIBLE_ADD_SEMANTIC_BIAS`
rows and the 2023-06-20 40520 row:

```text
2022-10-21 94320
2022-11-10 99840
2023-06-20 40520
```

The next question should be narrow: why did ADD rows with same-date positive
incremental / opportunity-cost evidence, or opportunity-cost PASS but
incremental UNKNOWN, still publish `proposed_incremental_target_weight = 0` and
`ADD_NO_POSITIVE_DELTA`?

Do not change Market Quality, Risk Pacing, PM thresholds, or allocation
parameters before that causal contract is reconciled.
