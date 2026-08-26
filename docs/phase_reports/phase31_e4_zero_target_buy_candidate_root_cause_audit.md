# Phase31-E4 — Zero-Target BUY Candidate Root-Cause Audit

Status: COMPLETE
Task type: READ-ONLY PIT ROOT-CAUSE AUDIT

## PRIMARY_JUDGMENT

```text
PHASE31_E4_ZERO_TARGET_CASES_CANONICALLY_EXPLAINED_NO_ECONOMIC_BUY_LOSS_DEFECT
```

E4 audited the current run's `ADD_CANDIDATE + pm_action=NEW + target_membership=false + target_weight=0 + quantity=0` family using existing artifacts only. No implementation, B10 change, threshold/weight/ranking tuning, fresh-run, resume, replay, or long Historical execution was performed.

The 688 cases are not unexplained lost BUY intent. Every case has canonical PC target-weight evidence showing `reason = lot_aware_final_reallocation` and `resolved_weight = 0`. The zero targets are explained by explicit PIT policy/reentry/budget/lot reasons. The semantic state is still ambiguous and worth cleaning up, but E4 does not support a trading-behavior repair claim: changing labels alone should not change target weight, quantity, Pending, or Fill.

## RUN

```text
CURRENT_RUN_ID = runtime-test-historical-extended-smoke-20260820T120909096218Z
PRIMARY_WINDOW = 2022-08-10 through 2022-10-12
```

Target artifacts:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260820T120909096218Z/daily/<date>/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260820T120909096218Z/daily/<date>/strategy/position_sizing.json`
- old run artifacts were used only for same symbol-date comparison.

## CLASSIFICATION

```text
TOTAL_CASE_COUNT = 688
LEGITIMATE_NOT_SELECTED_COUNT = 0
LEGITIMATE_POLICY_ZERO_COUNT = 484
LEGITIMATE_LOT_ZERO_COUNT = 204
SEMANTIC_ONLY_MISMATCH_COUNT = 0
LOST_VALID_BUY_INTENT_COUNT = 0
INSUFFICIENT_EVIDENCE_COUNT = 0
```

All 688 cases were classified from canonical PIT target-weight evidence:

```text
target_weight_resolution.reason = lot_aware_final_reallocation
target_weight_resolution.resolved_weight = 0
```

Zero-target reason breakdown:

| ZERO_TARGET_REASON | Count | Classification |
|---|---:|---|
| `reentry_opportunity_not_requalified` | 209 | LEGITIMATE_POLICY_ZERO |
| `insufficient_prior_exit_context` | 117 | LEGITIMATE_POLICY_ZERO |
| `incremental_budget_zero_allocation` | 95 | LEGITIMATE_POLICY_ZERO |
| `reentry_minimum_cooldown_not_satisfied` | 63 | LEGITIMATE_POLICY_ZERO |
| `minimum_lot_exceeds_remaining_budget` | 127 | LEGITIMATE_LOT_ZERO |
| `minimum_lot_exceeds_safety_hard_cap` | 77 | LEGITIMATE_LOT_ZERO |

The confusing labels are real, but the zero allocation itself is not label-only; it is explicitly produced by PC's lot-aware final reallocation authority.

## ZERO TARGET AUTHORITY

```text
ZERO_TARGET_AUTHORITY_OWNER = PORTFOLIO_CONSTRUCTION_LOT_AWARE_FINAL_REALLOCATION_TARGET_WEIGHT_AUTHORITY
```

Implementation evidence:

- PC first builds target candidate rows from Candidate, Opportunity, Entry, BUY Quality, PM, and portfolio policy evidence.
- PC computes selected target membership through `_select_target_members(...)`.
- PC then applies `apply_lot_aware_final_reallocation(...)`.
- The final zero-target cases carry `target_weight_resolution.reason = lot_aware_final_reallocation`.
- PS consumes the zero target and resolves `final_quantity_delta = 0`.

This means target zero is set before Runtime Planning and Pending. It is not introduced by B10, Pending, Submit, or Fill.

## B10 RELATIONSHIP

```text
B10_INPUT_ELIGIBLE_COUNT = 299
B10_PRIORITY_ASSIGNED_COUNT = 299
POSITIVE_TARGET_BEFORE_B10_COUNT = 299
ZERO_TARGET_BEFORE_B10_COUNT = 389
```

Interpretation:

- 299 rows were B10-input eligible from the PC pre-final allocation view and received canonical marginal-capital priority.
- 389 rows never received B10 priority and were already outside the B10 positive-priority input path.
- All 688 final rows ended with `target_weight=0` before PS/Runtime BUY.

```text
B10_DEFECT_CONFIRMED = NO
```

B10 did not erase these BUYs downstream. It either never saw them as priority candidates, or saw them before final PC lot-aware reallocation zeroed them for canonical policy/lot reasons.

## DIRECT OLD/CURRENT CONTROL

Same symbol-date comparison against old run:

```text
SAME_PIT_OLD_POSITIVE_CURRENT_ZERO_COUNT = 67
POSITIVE_BUY_REDUCTION_DIRECTLY_EXPLAINED_COUNT = 67 gross symbol-date rows
```

These 67 rows are same symbol-date cases where old had positive Runtime BUY while current belongs to the zero-target family. This is a gross control count, not a net 25-row proof. The total old/current positive Runtime BUY delta is 178 to 153, but other current-positive/old-zero rows offset part of the gross difference.

Crucially, the 67 current-zero rows still have explicit current PIT zero reasons. They are not evidence that current lost valid BUY intent through an unexplained semantic consumer defect.

## SEMANTIC CONTRACT

```text
SEMANTIC_STATE_CONTRACT = AMBIGUOUS
```

The state is arithmetically and behaviorally valid:

- `target_weight = 0`
- `target_membership = false`
- `final_quantity_delta = 0`
- no Runtime BUY, no Pending, no Fill expected

The state remains semantically awkward:

- PC can preserve `membership_intent = ADD_CANDIDATE` even when final `target_membership = false`.
- PS fills blank PM action as `NEW` when membership is `ADD_CANDIDATE`.
- The final row therefore reads like a BUY candidate while the canonical target-weight authority says no allocation.

That should be cleaned up for observability and contract clarity, not treated as a confirmed trading suppression defect.

## MATERIALITY

```text
SEMANTIC_ONLY_CASE_COUNT = 688
ECONOMIC_BUY_LOSS_CASE_COUNT = 0
SYSTEM_CAUSED_BUY_SUPPRESSION_CONFIRMED = NO
TRADING_BEHAVIOR_REPAIR_REQUIRED = NO
OBSERVABILITY_OR_SEMANTIC_REPAIR_REQUIRED = YES
```

`SEMANTIC_ONLY_CASE_COUNT = 688` means a semantic-label repair should leave trading behavior unchanged for these rows. It does not mean the canonical zero reasons are missing. They are present and explain why target and quantity are zero.

## REPAIR_CANDIDATES

PIT-supported family-wide repair candidates:

1. Normalize final zero-target non-held rows so they no longer surface as `ADD_CANDIDATE + pm_action=NEW` after `target_membership=false`.
2. Add an explicit canonical no-trade semantic such as `NOT_SELECTED_BUY_CANDIDATE`, `LOT_AWARE_ZERO_TARGET`, or equivalent, preserving the current zero target and zero quantity behavior.
3. Make PS consume PC final target membership when deriving display/action labels, so zero-target rows do not appear as executable NEW intent.
4. Add a contract check that `target_membership=false + target_weight=0 + final_quantity_delta=0` must carry a canonical zero reason from PC.

Not repair candidates from E4:

- B10 formula changes.
- Candidate ranking or threshold tuning.
- Trading behavior changes for this family.
- Treating old positive/current zero as automatically wrong based on later results.

## REQUIRED FLAGS

```text
FUTURE_INFORMATION_USED_FOR_DECISION_JUDGMENT = NO
OUTCOME_USED_FOR_PARAMETER_SELECTION = NO
IMPLEMENTATION_CHANGED = NO
LONG_HISTORICAL_EXECUTED = NO
```

## NEXT_TASK_RECOMMENDATION

```text
Do not claim performance repair from E4. Either perform a narrow observability/semantic cleanup, or move to the next return-degradation family.
```

## FINAL QUESTIONS

1. 688件はなぜtarget=0になったのか？

   PC `lot_aware_final_reallocation` が全件で `resolved_weight=0` を出したため。理由はpolicy/reentry/budget系484件、lot/cap系204件。

2. 688件のうち、本来positive BUYだったものは何件か？

   Current PIT authority上は0件。old比較では67 gross symbol-date rowsがold positive/current zeroだが、current側には明示的zero理由がある。

3. 単なるsemantic naming問題は何件か？

   Trading behavior上は688件すべてsemantic-only。分類上はcanonical policy/lot zeroで、economic BUY lossは0件。

4. currentのpositive BUY減少25件を直接説明できるのは何件か？

   Gross symbol-dateでは67件。ただしnet 25件とは一対一対応しない。

5. B10より前にBUY intentが消えていたのか？

   389件はB10 priority非付与。299件はB10 priority付与後、PC final lot-aware reallocationでzero。

6. システム都合で有効なBUY機会を消した証拠はあるか？

   No. 有効BUY意図が理由なく消えた証拠はない。

7. 修正すれば実際の売買が変わる問題なのか？

   No. E4で支持される修正はsemantic/observability cleanupで、売買挙動変更ではない。

8. E5で実装修正する価値があるか？

   Trading-behavior repairとしては低い。やるならE5ではなく、狭いsemantic/observability cleanupとして扱うべき。
