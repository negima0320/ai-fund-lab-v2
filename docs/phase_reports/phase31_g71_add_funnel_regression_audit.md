# Phase31-G71 — ADD Funnel Regression Audit

## PRIMARY_JUDGMENT

PHASE31_G71_ADD_FUNNEL_WEAK_BUT_AUTHORITY_CONNECTED

The running long Historical run was audited READ-ONLY using completed business
dates only. No run operation, fresh-run, resume, replay, code change, config
change, threshold change, weight change, or parameter tuning was performed.

```text
RUN_ID = runtime-test-historical-extended-smoke-20260823T140946562431Z
RUN_STATUS_AT_SNAPSHOT = RUNNING
RUN_NEXT_JOB_AT_SNAPSHOT = 2023-07-05:market_refresh
COMPLETED_BUSINESS_DATES = 186
AUDIT_WINDOW = 2022-10-03 through 2023-07-04
COMPLETION_EVIDENCE = daily/<date>/day_completion/day_completion_evidence.json status PASS
```

## Required Judgment

```text
ADD_FUNNEL_HEALTH = WEAK_BUT_CONNECTED
ADD_CAPABILITY_REGRESSION = NO
ADD_PRIMARY_DROP_STAGE = EXISTING_POSITION_TO_PM_ADD_INTENT
ADD_PRIMARY_DROP_REASON = PM_ADD_INTENT_IS_NARROW; THEN ADD_LOST_TO_NEW_BUY / ADD_INSUFFICIENT_EVIDENCE / ADD_NO_POSITIVE_DELTA
MARKET_QUALITY_DIRECT_ADD_SUPPRESSION = NO
CAPITAL_COMPETITION_ADD_STARVATION = YES
LOT_OR_CAP_ADD_STARVATION = YES
PS_RUNTIME_ADD_CONNECTIVITY = PASS
WINNER_ADD_OPPORTUNITY_CAPTURE = WEAK
PHASE29_ADD_CAPABILITY_PRESERVED = PARTIAL
CODE_CHANGED = NO
RUN_MODIFIED = NO
MARKET_QUALITY_CHANGED = NO
THRESHOLD_WEIGHT_TUNING = NO
FUTURE_INPUT_COUNT = 0
HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0
```

Interpretation:

- ADD capability has not disappeared from the authority chain. PM ADD intent,
  PC ADD competitor, G61/lot-aware compatibility, PS quantity, and Runtime
  BUY_ADD are all still present.
- The effective funnel is weak. Only 68 PM ADD intents were emitted from 1,721
  existing-position evaluations.
- After PM ADD intent, 10/68 reached positive PC allocation, PS positive ADD
  quantity, and Runtime BUY_ADD.
- Market Quality / Risk Pacing did not directly block ADD. The actual
  `risk_pacing_decision.blocks_deployment` evidence was false for ADD rows.
- The main post-intent losses are canonical PC competition / evidence outcomes:
  `ADD_LOST_TO_NEW_BUY`, `ADD_INSUFFICIENT_EVIDENCE`, and
  `ADD_NO_POSITIVE_DELTA`.

## ADD Funnel Counts

```text
EXISTING_POSITION_OPPORTUNITY_COUNT = 1,721
ADD_EVALUABLE_COUNT = 1,721
ADD_INTENT_COUNT = 68
PM_STRATEGY_ADD_COUNT = 68
PC_ADD_CANDIDATE_COUNT = 68
PC_ADD_ALLOCATED_COUNT = 10
ADD_REJECTED_BY_CAPITAL_BUDGET_COUNT = 54
ADD_REJECTED_OR_REDUCED_BY_MARKET_QUALITY_OR_RISK_PACING_COUNT = 0 direct blocks
ADD_BLOCKED_BY_CONCENTRATION_CAP_COUNT = 6
ADD_BLOCKED_BY_LOT_MIN_NOTIONAL_OR_ZERO_DELTA_COUNT = 52
PS_ADD_ROWS_COUNT = 68
PS_POSITIVE_ADD_DELTA_COUNT = 10
RUNTIME_BUY_NEW_COUNT = 606
RUNTIME_BUY_ADD_COUNT = 10
SUBMITTED_ADD_COUNT = NOT_DIRECTLY_CLASSIFIED
SUBMITTED_ADD_COUNT_SYMBOL_INFERRED = 7
FILLED_ADD_COUNT = NOT_DIRECTLY_CLASSIFIED
FILLED_ADD_COUNT_SYMBOL_INFERRED = 7
```

`execution/fills.json` stores ADD-origin BUY fills as `source_decision_type=BUY`
or `MISSING`, not as canonical `BUY_ADD`. Therefore submitted / filled ADD is
not directly measurable from execution lineage. Same-day Runtime BUY_ADD symbol
matching infers 7 filled ADDs, but 3 Runtime BUY_ADD plans did not match same-day
BUY fills by symbol.

## Window Breakdown

```text
WINDOW                       EXISTING  PM_ADD  PC_ALLOC  PS_POS  RT_BUY_ADD  FILLED_ADD*
2022-10_to_11                     379      47         9       9          9          6
2022-12_to_2023-02                654       6         0       0          0          0
2023-03-15_to_2023-04-06          134       4         0       0          0          0
2023-04-07_onward                 454      10         1       1          1          1
other                             100       1         0       0          0          0
```

`FILLED_ADD*` is symbol-inferred because execution artifacts do not preserve
canonical BUY_ADD classification.

The 2022-10/11 period proves ADD participation still exists. The 2022-12
through 2023-02 period is the sharpest disappearance: 654 existing-position
evaluations produced only 6 PM ADD intents and zero positive ADD quantity.

## Stage Losses

Largest loss points:

```text
LOSS_POINT                                      COUNT  REPRESENTATIVE_DATES
PM_ACTION_HOLD_NOT_ADD                         1,074  2022-10-04, 2022-10-05
PM_ACTION_EXIT_NOT_ADD                           304  2022-10-04, 2022-10-05
PM_ACTION_REDUCE_NOT_ADD                         275  2022-10-04, 2022-10-05
ADD_LOST_TO_NEW_BUY / opportunity-cost loss       54  2022-10-05, 2022-10-07, 2023-05-31, 2023-06-28
ADD_NO_POSITIVE_DELTA / target unchanged          52  2022-10-05, 2022-10-07, 2023-05-31, 2023-06-28
```

Reason-code evidence frequently overlaps inside the same ADD row. For example,
a rejected ADD can simultaneously carry `ADD_INSUFFICIENT_EVIDENCE`,
`ADD_LOST_TO_NEW_BUY`, and `ADD_NO_POSITIVE_DELTA`.

Top repeated reason codes observed in ADD-related losses:

```text
ADD_LOST_TO_NEW_BUY
ADD_INSUFFICIENT_EVIDENCE
ADD_NO_POSITIVE_DELTA
ADD_TARGET_WEIGHT_UNCHANGED
NO_POSITIVE_QUANTITY_DELTA
ADD_NOT_AVAILABLE
ADD_SAFETY_CAP_BOUND
VALID_SAFETY_RESERVE
ADD_LOST_TO_CASH
STRATEGY_CAP_BOUND
```

## Authority Preservation

Phase31-G27 / G44 contracts remain visible in the actual artifacts:

```text
PM_ADD_INTENT_OWNER = POSITION_MANAGEMENT
ADD_CAPITAL_COMPETITION_OWNER = PORTFOLIO_CONSTRUCTION
ADD_DISCRETE_QUANTITY_OWNER = POSITION_SIZING
ADD_CAN_WIN_CAPITAL_COMPETITION = YES
PM_ADD_INTENT_IMPLIES_EXECUTION = NO
PC_COMPETES_NEW_BUY_ADD_CASH = YES
POSITION_SIZING_AUTHORITY_CHANGED = NO
RUNTIME_CAPITAL_PRIORITY_REDECISION_COUNT = 0
MARKET_QUALITY_SECURITY_ADMISSION_OWNER = NO
```

G71 did not find an authority-owner migration regression. The weakness is
effective selectivity / throughput, not a missing ADD producer.

## PC / PS / Runtime Connectivity

Positive ADD path rows:

```text
DATE        SYMBOL  PS_ADD_QTY  RUNTIME_BUY_ADD_QTY
2022-10-06  94340        300                  300
2022-10-11  94340        200                  200
2022-10-12  94320        100                  100
2022-10-12  94340        100                  100
2022-10-13  94340        100                  100
2022-10-28  94320        200                  200
2022-11-01  94320        200                  200
2022-11-04  94320        200                  200
2022-11-09  94320        200                  200
2023-05-31  30410        100                  100
```

```text
PS_POSITIVE_ADD_DELTA_COUNT = 10
RUNTIME_BUY_ADD_COUNT = 10
PS_RUNTIME_ADD_CONNECTIVITY = PASS
```

Execution lineage caveat:

```text
RUNTIME_BUY_ADD_WITH_SAME_DAY_SYMBOL_MATCHED_BUY_FILL = 7
RUNTIME_BUY_ADD_WITH_NO_SAME_DAY_SYMBOL_MATCHED_BUY_FILL = 3
REPRESENTATIVE_DATES = 2022-10-06, 2022-10-11, 2022-10-28
```

This is not the primary cause of low ADD count, because the funnel is already
thin before execution. It is still a separate observability / submit-execution
lineage follow-up: pending/planning can contain BUY_ADD while execution fills
do not retain BUY_ADD classification.

## Market Quality Interaction

Market Quality distribution for PM ADD intent and BUY_ADD:

```text
MARKET_QUALITY_STATE                         ADD_INTENT  PC_ALLOC  BUY_ADD  FILLED_ADD*
CONFLICTED_MARKET_STRUCTURE                         25         4        4          2
SHORT_TERM_BREADTH_BREAKDOWN                        12         5        5          5
RECOVERY_CONFIRMATION_INCOMPLETE                     9         1        1          0
HEALTHY_EXPANSION                                   17         0        0          0
SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH            5         0        0          0
```

Risk Pacing distribution:

```text
RISK_PACING_STATE       ADD_INTENT  PC_ALLOC  BUY_ADD  FILLED_ADD*
CAUTIOUS_DEPLOYMENT             42         9        9          7
GRADUAL_REDEPLOYMENT             9         1        1          0
NORMAL_DEPLOYMENT               17         0        0          0
```

This does not support a direct Market Quality hard ADD gate. Most successful
ADD rows occurred under `CAUTIOUS_DEPLOYMENT`, while `NORMAL_DEPLOYMENT` ADD
intents lost for ADD evidence / competition reasons. Market Quality is present
as capital pacing context, not as ADD admission authority.

## Winner Cohort Check

G70 top positive contributors were checked only for same-date PIT ADD evidence.
This does not say they should have been added after the fact.

```text
SYMBOL HELD_DATES PM_ADD_DATES PC_ALLOC PS_POS RT_ADD FILLED_ADD* RESULT
59350         23            4        0      0      0          0  ADD intent existed, lost at PC
67310          3            0        0      0      0          0  no same-date PM ADD
44440          3            0        0      0      0          0  no same-date PM ADD
70720         21            0        0      0      0          0  no same-date PM ADD
71160         28            0        0      0      0          0  no same-date PM ADD
64240          4            0        0      0      0          0  no same-date PM ADD
49370          2            0        0      0      0          0  no same-date PM ADD
72140          4            0        0      0      0          0  no same-date PM ADD
93410         14            0        0      0      0          0  no same-date PM ADD
40520         13            7        0      0      0          0  ADD intent existed, lost at PC
```

For 59350 and 40520, PM did emit ADD intent, but same-date PC ADD competitor
evidence failed closed with reasons such as:

```text
ADD_INSUFFICIENT_EVIDENCE
ADD_LOST_TO_NEW_BUY
ADD_NO_POSITIVE_DELTA
ADD_EXPECTED_EDGE_WEAKENING
ADD_OPPORTUNITY_COST_FAIL
```

Therefore:

```text
WINNER_ADD_OPPORTUNITY_CAPTURE = WEAK
```

The weakness is partly PM intent sparsity and partly PC's stricter
same-date incremental value / opportunity-cost checks after PM ADD appears.

## Regression / Preservation Conclusion

```text
ADD_AUTHORITY_OWNER_CHANGED = NO
ADD_OPPORTUNITY_PRODUCER_LOST = NO
LEGACY_NEW_PATH_ADD_CONSUMER_DISCONNECTED = NO for PC/PS/Runtime
MARKET_QUALITY_BECAME_ADD_SECURITY_ADMISSION_AUTHORITY = NO
NEW_BUY_ADD_SHARED_BUDGET_COMPETITION_PRESENT = YES
ADD_ALWAYS_LOSES_TO_NEW_BUY = NO
EXISTING_WINNER_INCREMENTAL_PRIORITY_PRESERVED = PARTIAL
LOT_CAP_RESIDUAL_ZEROIZATION_PRESENT = YES
PS_POSITIVE_ADD_BINDS_RUNTIME = YES
SUBMIT_EXECUTION_ADD_LINEAGE_COMPLETE = NO
```

`ADD_CAPABILITY_REGRESSION = NO` because the authority chain is present and
positive ADD still reaches Runtime. `PHASE29_ADD_CAPABILITY_PRESERVED = PARTIAL`
because the runtime planning capability is preserved, but actual run evidence
shows weak effective participation and incomplete ADD classification at
submit/execution evidence.

## Highest-Value Next Investigation

1. PM ADD intent sparsity.
   The biggest drop is 1,721 existing-position evaluations to 68 PM ADD intents.
   The next causal audit should inspect PM same-date continuation / winner
   evidence for HOLD vs ADD, especially 2022-12 through 2023-02 and the top
   positive winner cohort.

2. PC ADD fail-closed reasons after PM ADD.
   58/68 PM ADD candidates did not allocate. The dominant same-row reasons are
   `ADD_LOST_TO_NEW_BUY`, `ADD_INSUFFICIENT_EVIDENCE`, and
   `ADD_NO_POSITIVE_DELTA`.

3. ADD opportunity-cost comparison against NEW_BUY.
   Current design explicitly allows stronger NEW_BUY to beat ADD. The next
   audit should determine whether this is economically appropriate in actual
   PIT cases, without using future returns for tuning.

4. ADD zero-delta / lot-cap semantics.
   52 ADD rows show zero-delta / target-unchanged / lot-min-notional style
   outcomes. This should be separated from true capital competition loss.

5. Runtime-to-submit/execution ADD lineage.
   PS positive ADD and Runtime BUY_ADD match 10/10, but execution artifacts do
   not preserve BUY_ADD classification, and 3 Runtime BUY_ADD plans had no
   same-day symbol-matched BUY fill.

G71 makes no repair recommendation and performs no implementation.
