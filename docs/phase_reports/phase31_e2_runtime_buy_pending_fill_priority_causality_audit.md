# Phase31-E2 — Runtime BUY → Pending / Fill Priority Causality Audit

Status: COMPLETE
Task type: READ-ONLY PIT / CONTRACT AUDIT

## PRIMARY_JUDGMENT

```text
PHASE31_E2_NORMAL_CAPITAL_COMPETITION_WITH_B10_PRIORITY_OBSERVABILITY_AND_PM_PC_SEMANTIC_GAPS
```

E2 reconstructed the Runtime BUY to Pending/Fill path from existing old/current run artifacts only. No implementation, Strategy/Runtime/PM/PC/PS change, B10 formula change, threshold tuning, fresh-run, resume, replay, or long Historical execution was performed.

The 2022-08-10 fill divergence is directly explained by cash-feasible batch construction under different priority authority. The current run consistently applies B10 marginal-capital priority through PC, Runtime Planning, and the cash-feasible Pending batch. No lower-priority cash preemption, double reservation, Submit loss, or Fill materialization defect was found for the control date.

The remaining contract risks are not the B10 formula itself. They are: a pending-side observability gap, because `pending_generation_evidence.rank_authority_lineage` still exposes opportunity-rank lineage while `planning_evidence.lineage.cash_feasible_buy_batch` carries B10 cash-priority evidence; and a material `ADD_CANDIDATE + pm_action=NEW + NO_POSITIVE_QUANTITY` semantic family that increased in current and reduces positive Runtime BUY supply before Pending.

## CONTROL_DATE

```text
CONTROL_DATE = 2022-08-10
OLD_RUN_ID = runtime-test-historical-extended-smoke-20260818T015851711672Z
CURRENT_RUN_ID = runtime-test-historical-extended-smoke-20260820T120909096218Z
SECONDARY_WINDOW = 2022-08-10 through 2022-10-12
```

Target artifacts:

- `reports/runtime_tests/runs/<run_id>/daily/2022-08-10/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/<run_id>/daily/2022-08-10/strategy/position_sizing.json`
- `reports/runtime_tests/runs/<run_id>/daily/2022-08-10/strategy/runtime_planning.json`
- `reports/runtime_tests/runs/<run_id>/daily/2022-08-10/morning/planning_evidence.json`
- `reports/runtime_tests/runs/<run_id>/daily/2022-08-10/morning/pending_generation_evidence.json`
- `reports/runtime_tests/runs/<run_id>/daily/2022-08-10/execution/submitted_order_authority.json`
- `reports/runtime_tests/runs/<run_id>/daily/2022-08-10/execution/fills.json`

## CONTROL_DATE_SUMMARY

```text
OLD_POSITIVE_RUNTIME_BUY_COUNT = 16
CURRENT_POSITIVE_RUNTIME_BUY_COUNT = 16
OLD_FILL_COUNT = 11
CURRENT_FILL_COUNT = 9
```

On 2022-08-10, both runs produced 16 positive-quantity Runtime BUY candidates from the same candidate/intelligence set. The fill difference is not caused by candidate discovery, Entry, BUY Quality, position sizing quantity, Submit, or execution loss. It is caused by which 16 BUYs were ordered into the cash-feasible batch first.

## CURRENT 2022-08-10 CASH BATCH

Current cash batch:

```text
starting_cash = 1,000,000
candidate_buy_count = 16
included_buy_count = 9
cash_pruned_count = 7
final_reserved_notional_total = 992,790
remaining_reserved_cash = 7,210
priority_order_preservation = PASS
status = PASS
```

| Priority | Symbol | Decision | Reserved notional | Reserved before | Remaining before | Remaining after | Fill |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | `94320` | INCLUDE | 59,640 | 0 | 1,000,000 | 940,360 | YES |
| 2 | `66590` | INCLUDE | 76,000 | 59,640 | 940,360 | 864,360 | YES |
| 3 | `93180` | INCLUDE | 290,500 | 135,640 | 864,360 | 573,860 | YES |
| 4 | `23700` | INCLUDE | 71,400 | 426,140 | 573,860 | 502,460 | YES |
| 5 | `23880` | INCLUDE | 61,200 | 497,540 | 502,460 | 441,260 | YES |
| 6 | `76470` | INCLUDE | 112,000 | 558,740 | 441,260 | 329,260 | YES |
| 7 | `94340` | INCLUDE | 60,150 | 670,740 | 329,260 | 269,110 | YES |
| 8 | `89180` | INCLUDE | 205,000 | 730,890 | 269,110 | 64,110 | YES |
| 9 | `47770` | PRUNE | 78,000 | 935,890 | 64,110 | 64,110 | NO |
| 10 | `99840` | PRUNE | 162,380 | 935,890 | 64,110 | 64,110 | NO |
| 11 | `95010` | INCLUDE | 56,900 | 935,890 | 64,110 | 7,210 | YES |
| 12 | `61980` | PRUNE | 43,000 | 992,790 | 7,210 | 7,210 | NO |
| 13 | `83060` | PRUNE | 85,920 | 992,790 | 7,210 | 7,210 | NO |
| 14 | `39950` | PRUNE | 61,500 | 992,790 | 7,210 | 7,210 | NO |
| 15 | `38410` | PRUNE | 96,700 | 992,790 | 7,210 | 7,210 | NO |
| 16 | `47840` | PRUNE | 52,800 | 992,790 | 7,210 | 7,210 | NO |

`95010` is lower priority than `47770` and `99840`, but this is not lower-priority cash preemption. At the time `47770` and `99840` were evaluated, remaining cash was 64,110 and both required more than that. `95010` required 56,900 and was therefore feasible from residual cash after the higher-priority infeasible items were pruned.

## OLD 2022-08-10 CASH BATCH

Old cash batch:

```text
starting_cash = 1,000,000
candidate_buy_count = 16
included_buy_count = 11
cash_pruned_count = 5
final_reserved_notional_total = 943,520
remaining_reserved_cash = 56,480
priority_order_preservation = PASS
status = PASS
```

Old priority order was not B10 marginal-capital priority. It selected:

```text
23700, 23880, 38410, 39950, 47770, 47840, 61980, 66590, 76470, 83060, 89180
```

and pruned:

```text
93180, 94320, 94340, 95010, 99840
```

Thus old/current both performed normal cash batch selection, but under different priority authority.

## DIVERGENT CONTROLS

OLD fill / CURRENT no-fill:

| Symbol | Old cause | Current cause |
|---|---|---|
| `38410` | old priority 3, INCLUDE, filled | B10 priority 15, PRUNE, remaining cash 7,210 < 96,700 |
| `39950` | old priority 4, INCLUDE, filled | B10 priority 14, PRUNE, remaining cash 7,210 < 61,500 |
| `61980` | old priority 7, INCLUDE, filled | B10 priority 12, PRUNE, remaining cash 7,210 < 43,000 |
| `83060` | old priority 10, INCLUDE, filled | B10 priority 13, PRUNE, remaining cash 7,210 < 85,920 |

CURRENT fill / OLD no-fill:

| Symbol | Old cause | Current cause |
|---|---|---|
| `94320` | old priority 13, PRUNE, remaining cash 56,480 < 59,640 | B10 priority 1, INCLUDE, filled |
| `94340` | old priority 14, PRUNE, remaining cash 56,480 < 60,150 | B10 priority 7, INCLUDE, filled |
| `95010` | old priority 15, PRUNE, remaining cash 56,480 < 56,900 | B10 priority 11, INCLUDE, filled from residual 64,110 |
| `93180` | old priority 12, PRUNE, remaining cash 56,480 < 290,500 | B10 priority 3, INCLUDE, filled |

Direct cause:

```text
2022-08-10_DIRECT_CAUSE = DIFFERENT_CASH_BATCH_PRIORITY_AUTHORITY; CURRENT_B10_PRIORITY_REORDERED_THE_SAME_RUNTIME_BUY_SET
```

## PRIORITY ORDER

Current executable BUY order:

```text
PC_PRIORITY_ORDER = 94320, 66590, 93180, 23700, 23880, 76470, 94340, 89180, 47770, 99840, 95010, 61980, 83060, 39950, 38410, 47840
RUNTIME_PRIORITY_ORDER = 94320, 66590, 93180, 23700, 23880, 76470, 94340, 89180, 47770, 99840, 95010, 61980, 83060, 39950, 38410, 47840
PENDING_EVALUATION_ORDER = 94320, 66590, 93180, 23700, 23880, 76470, 94340, 89180, 47770, 99840, 95010, 61980, 83060, 39950, 38410, 47840
```

```text
PRIORITY_ORDER_CONSISTENCY = PASS
```

PC and Runtime also contain non-executable marginal-priority rows such as `67310`, `66190`, and `45710`; those are excluded from the executable cash-batch order above because the required audit target is positive-quantity Runtime BUY.

## RESERVED_CASH_CAUSALITY

For current 2022-08-10:

```text
RESERVED_CASH_CAUSALITY_RECONSTRUCTED_COUNT = 16
RESERVED_CASH_CAUSALITY_UNRESOLVED_COUNT = 0
LOWER_PRIORITY_CASH_PREEMPTION_COUNT = 0
DOUBLE_RESERVATION_COUNT = 0
```

Reserved cash is internally consistent when interpreted as:

```text
reserved_cash_before_item = cumulative reserved notional before item
reserved_cash_after_item = remaining cash after item decision
```

For `INCLUDE`, `reserved_cash_after_item = starting_cash - reserved_cash_before_item - reserved_notional`.

For `PRUNE`, `reserved_cash_after_item = remaining_cash_before_item`.

## PENDING MATERIALIZATION

Control date:

```text
POSITIVE_RUNTIME_BUY_NO_FILL_BY_CAUSE = {
  PRUNED_FOR_CASH: 7
}
```

No current 2022-08-10 positive Runtime BUY was lost after Pending inclusion:

```text
INCLUDED_BUY_NO_EXECUTION_COUNT = 0
SUBMIT_BLOCKED_COUNT = 0
NO_EXECUTION_AFTER_INCLUDE_COUNT = 0
EVIDENCE_MISSING_COUNT = 0
```

The current `execution/fills.json` BUY count equals the cash-batch `included_buy_count` on the control date: 9.

## B10 CONSUMER ALIGNMENT

```text
B10_AUTHORITY_PRODUCED = YES
B10_RUNTIME_CONSUMED = YES
B10_PENDING_CONSUMED = YES
B10_RESERVED_CASH_CONSUMED = YES
B10_CONSUMER_ALIGNMENT = PARTIAL
```

Behavioral alignment is PASS for the executable 2022-08-10 cash batch: PC priority, Runtime priority, Pending evaluation order, selected symbols, and fills agree.

The reason the overall consumer-alignment judgment is PARTIAL is observability. `morning/planning_evidence.json` carries B10 cash-batch evidence, including `canonical_strategy_order_source = MARGINAL_CAPITAL_VALUE_AUTHORITY`, `canonical_marginal_capital_priority_index`, and embedded `marginal_capital_value_authority`. However, `morning/pending_generation_evidence.json` still reports `rank_authority = OPPORTUNITY_BUY_RANK_AUTHORITY` in `rank_authority_lineage` and does not independently expose the B10 cash-priority fields. That is an evidence/observability gap, not proof that the runtime consumed the wrong order.

## BROADER WINDOW

Current 2022-08-10 through 2022-10-12:

```text
POSITIVE_RUNTIME_BUY_COUNT = 153
PENDING_INCLUDE_COUNT = 73
BUY_FILL_COUNT = 73
NO_FILL_COUNT = 80
```

Cause breakdown:

```text
PRUNED_FOR_CASH = 52
REVIEW_REQUIRED = 28
INCLUDED_NO_EXECUTION = 0
EVIDENCE_MISSING = 0
```

Reserved cash checks across the current secondary window:

```text
RESERVED_CASH_CAUSALITY_RECONSTRUCTED_COUNT = 153
RESERVED_CASH_CAUSALITY_UNRESOLVED_COUNT = 0
LOWER_PRIORITY_CASH_PREEMPTION_COUNT = 0
DOUBLE_RESERVATION_COUNT = 0
```

Old comparison for context:

```text
OLD_POSITIVE_RUNTIME_BUY_COUNT_WINDOW = 178
OLD_PENDING_INCLUDE_COUNT_WINDOW = 79
OLD_BUY_FILL_COUNT_WINDOW = 79
OLD_NO_FILL_COUNT_WINDOW = 99
OLD_PRUNED_FOR_CASH = 73
OLD_REVIEW_REQUIRED = 26
```

The broader window supports normal Pending/Fill materialization for included BUYs: included BUY count equals BUY fill count in both runs.

## ADD_CANDIDATE + PM_ACTION NEW

E1 terminal-path count:

```text
OLD_ADD_CANDIDATE_PM_NEW_NO_POSITIVE_QUANTITY = 322
CURRENT_ADD_CANDIDATE_PM_NEW_NO_POSITIVE_QUANTITY = 389
DELTA = +67
```

Position-sizing row scan across the same window also shows this as a broad family, not a symbol-specific event:

```text
OLD_POSITION_SIZING_ROWS_WITH_ADD_CANDIDATE_PM_NEW_ZERO_DELTA = 669
CURRENT_POSITION_SIZING_ROWS_WITH_ADD_CANDIDATE_PM_NEW_ZERO_DELTA = 688
```

Judgment:

```text
ADD_CANDIDATE_PM_NEW_JUDGMENT = GAP
ADD_CANDIDATE_PM_NEW_MATERIALITY = MATERIAL
```

This family is upstream of Pending: rows with `membership_intent = ADD_CANDIDATE`, `pm_action = NEW`, and zero delta do not become positive Runtime BUY. It plausibly contributes to the current reduction from 178 old positive Runtime BUY rows to 153 current rows. E2 does not change semantics, but the naming/ownership is internally suspicious: `ADD_CANDIDATE` implies an existing or continuation capital path, while `pm_action=NEW` and zero quantity produce no executable incremental investment.

## CONTRACT JUDGMENT

| Family | Judgment |
|---|---|
| 2022-08-10 cash competition | NORMAL_CAPITAL_COMPETITION |
| Current B10 PC to Runtime order | NORMAL_CAPITAL_COMPETITION |
| Current B10 Runtime to Pending cash-batch order | NORMAL_CAPITAL_COMPETITION |
| Current reserved cash arithmetic | NORMAL_CAPITAL_COMPETITION |
| Current Pending INCLUDE to Fill | NORMAL_CAPITAL_COMPETITION |
| Pending B10 lineage visibility | OBSERVABILITY_GAP |
| `ADD_CANDIDATE + pm_action=NEW + zero quantity` | PM_PC_SEMANTIC_GAP |

```text
PRIMARY_DOWNSTREAM_CAUSE = NORMAL_CAPITAL_COMPETITION_UNDER_B10_PRIORITY_WITH_OBSERVABILITY_AND_UPSTREAM_PM_PC_SEMANTIC_GAPS
CONTRACT_DEFECT_CONFIRMED = PARTIAL
B10_FORMULA_DEFECT_CONFIRMED = NO
```

The confirmed part is not a reserved-cash or Fill defect. It is the family-wide evidence/observability gap and the material PM/PC semantic gap. The control-date fill divergence itself is explained by normal capital competition under the current priority authority.

## REPAIR_CANDIDATES

PIT-supported repair/design candidates:

1. Make Pending generation evidence expose the canonical B10 priority authority used by the cash-feasible batch, not only opportunity-rank lineage.
2. Add a contract check that PC priority, Runtime priority, cash-batch evaluation order, selected symbols, and fills are aligned for positive-quantity BUYs.
3. Design a semantic repair for `ADD_CANDIDATE + pm_action=NEW + zero quantity`, clarifying whether this is stale membership, PM/PC intent mismatch, or a legitimate zero-sizing state that needs an explicit canonical reason.

Not repair candidates from E2:

- B10 formula tuning.
- Candidate AI threshold/rank tuning.
- Reserved-cash arithmetic.
- Submit/Fill materialization for included BUYs.

## REQUIRED FLAGS

```text
FUTURE_INFORMATION_USED_FOR_DECISION_JUDGMENT = NO
OUTCOME_USED_FOR_PARAMETER_SELECTION = NO
IMPLEMENTATION_CHANGED = NO
LONG_HISTORICAL_EXECUTED = NO
```

## NEXT_TASK_RECOMMENDATION

```text
Phase31-E3 focused repair/design for Pending B10 observability and ADD_CANDIDATE/pm_action semantic contract; do not change the B10 formula.
```

## FINAL QUESTIONS

1. 2022-08-10に同じRuntime BUYが違うFill結果になった直接原因は何か？

   Different cash-batch priority authority. Old used the pre-B10 order; current used B10 marginal-capital priority. Both then applied cash pruning normally.

2. B10 priorityはPendingまで正しく維持されているか？

   Behaviorally yes for the executable cash batch. Evidence visibility is partial because `pending_generation_evidence.rank_authority_lineage` still shows opportunity-rank authority while `planning_evidence` carries the B10 cash-priority authority.

3. lower-priority BUYがhigher-priority BUYのcashを奪っていないか？

   No. Count is 0. `95010` is included after higher-priority prunes only because those higher-priority orders were individually infeasible with the remaining cash.

4. reserved cashの二重計上はないか？

   No. Count is 0.

5. positive Runtime BUYのNO_FILLは正常なcapital competitionか、contract defectか？

   For 2022-08-10, normal capital competition. Across the window, NO_FILL is explained by `PRUNED_FOR_CASH` or `REVIEW_REQUIRED`; included BUYs match fills.

6. ADD_CANDIDATE + pm_action=NEW増加は問題か？

   Yes, material semantic gap. It is upstream of Pending and likely contributes to the current positive Runtime BUY reduction, but it is not the direct cause of the 2022-08-10 same-BUY fill divergence.

7. E3で修正すべき具体的なfamily-wide defectはあるか？

   Yes: Pending B10 observability/contract evidence, and the `ADD_CANDIDATE + pm_action=NEW + zero quantity` semantic contract. Do not repair by changing B10 formula or tuning candidate thresholds.
