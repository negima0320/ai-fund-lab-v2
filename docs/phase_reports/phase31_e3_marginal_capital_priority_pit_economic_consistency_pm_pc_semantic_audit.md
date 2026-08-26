# Phase31-E3 — Marginal Capital Priority PIT Economic Consistency / PM-PC Semantic Audit

Status: COMPLETE
Task type: READ-ONLY PIT / ARCHITECTURE AUDIT

## PRIMARY_JUDGMENT

```text
PHASE31_E3_B10_PRIORITY_REPRODUCIBLE_NO_FORMULA_DEFECT_PM_PC_SEMANTIC_CONTRACT_AMBIGUOUS
```

E3 audited current B10 marginal-capital priority and the `ADD_CANDIDATE + pm_action=NEW + zero quantity` family from existing artifacts and current implementation only. No implementation, B10 formula change, threshold/weight tuning, fresh-run, resume, replay, or long Historical execution was performed.

B10 priority is fully reproducible from the same PIT Portfolio Construction artifact. On 2022-08-10, all positive Runtime BUY rows were `ELIGIBLE_COMPARABLE`, so priority reduced to a deterministic PIT rank order: comparison class, input opportunity rank, fallback flag, then symbol. This is internally consistent with the implemented contract and does not show hidden BUY_NEW/BUY_ADD label priority, quantity distortion, notional distortion, missing-evidence advantage, or later-outcome use.

The supported design gap is semantic rather than formulaic: the authority is named marginal capital value, but for BUY_NEW rows without calibrated economic units it mostly produces an ordinal comparable class plus buy-rank ordering. That is reproducible and safe, but only partially an economic value scale. Separately, `ADD_CANDIDATE + pm_action=NEW + zero quantity` remains a family-wide PM/PC/PS semantic ambiguity: it is mathematically zero-sized and explicitly classified as `QUALITY_DEFERRED_TO_CASH`, but PC can carry `membership_intent=ADD_CANDIDATE` while `target_membership=false`, and PS then fills blank PM action as `NEW`.

## RUNS

```text
OLD_RUN_ID = runtime-test-historical-extended-smoke-20260818T015851711672Z
CURRENT_RUN_ID = runtime-test-historical-extended-smoke-20260820T120909096218Z
PRIMARY_DATE = 2022-08-10
SECONDARY_WINDOW = 2022-08-10 through 2022-10-12
```

## B10 FORMULA RECONSTRUCTION

Producer:

```text
EXACT_PRODUCER = src/ai_fund_lab_v2/strategy/marginal_capital_value.py
AUTHORITY_TYPE = MARGINAL_CAPITAL_VALUE_AUTHORITY
PRODUCER = strategy.marginal_capital_value
CONTRACT_ID = phase31_b10_marginal_capital_value_authority.v1
```

Canonical application points:

- PC calls `marginal_capital_value.apply_marginal_capital_priority(...)`.
- Runtime Planning sorts BUY plans by `canonical_marginal_capital_priority_index`.
- Pending order construction sorts BUY pending items by `canonical_marginal_capital_priority_index`.

Formula inputs:

- `membership_intent`
- `pm_action`
- `current_position`
- `target_weight`
- `current_weight`
- `accepted_incremental_weight`
- `requested_incremental_weight`
- `accepted_buy_new_weight`
- `requested_buy_new_weight`
- `lot_aware_accepted_incremental_weight`
- `lot_aware_accepted_buy_new_weight`
- `input_opportunity_rank` / `opportunity_rank` / `opportunity_buy_rank`
- `runtime_opportunity_score` as source evidence, not the final sort scalar
- `entry_admission_action`
- `entry_admission_state`
- ADD evidence fields when present: expected edge, incremental investment value, opportunity cost, add worthiness, campaign continuation

Classification and sort:

```text
COMPARISON_CLASSES:
  ELIGIBLE_STRONG = 1
  ELIGIBLE_COMPARABLE = 2
  ELIGIBLE_WEAK = 3
  REVIEW_REQUIRED = 4
  BLOCKED_OR_NOT_ELIGIBLE = 5
  COMPARISON_INSUFFICIENT = 6

SORT_KEY:
  comparison_class_order
  input/opportunity/buy_rank
  fallback_only_flag
  symbol
```

Tie-break:

```text
TIE_BREAK = symbol after comparison class, rank, and fallback flag
STABLE_TIE_ORDER = stored in authority evidence but not the final sort key
```

BUY_NEW vs BUY_ADD semantics:

- BUY_NEW is inferred when `current_position=false` and `membership_intent=ADD_CANDIDATE`.
- BUY_ADD is inferred when `current_position=true` and `pm_action=ADD`.
- `buy_new_unconditional_priority=false`.
- `buy_add_unconditional_priority=false`.
- BUY_ADD can outrank BUY_NEW only through `ELIGIBLE_STRONG` explicit ADD lifecycle evidence, not by label alone.

Missing evidence semantics:

- BUY_NEW label alone becomes `COMPARISON_INSUFFICIENT`.
- BUY_ADD missing/non-pass lifecycle evidence becomes `COMPARISON_INSUFFICIENT`.
- In the audited current window, no insufficient row gained top priority.

## PRIORITY_REPRODUCIBLE

```text
PRIORITY_REPRODUCIBLE = YES
```

Recomputing `apply_marginal_capital_priority(...)` from current `portfolio_construction.json` produced zero mismatches against stored PC/runtime priority across the secondary window.

```text
CURRENT_WINDOW_PRIORITY_MISMATCH_COUNT = 0
CURRENT_WINDOW_B10_CANDIDATE_COUNT = 452
```

Class distribution:

```text
ELIGIBLE_COMPARABLE = 432
ELIGIBLE_STRONG = 20
COMPARISON_INSUFFICIENT = 0
```

Reason-code distribution:

```text
pit_new_opportunity_evidence_comparable = 432
explicit_pit_new_entry_evidence_positive = 13
explicit_pit_add_lifecycle_evidence_positive = 7
```

## 2022-08-10 PRIORITY TABLE

The table below covers the 16 positive Runtime BUY rows in the current cash batch. Non-executable B10 candidates such as `67310`, `66190`, and `45710` existed in the B10 order but had zero final quantity and were not positive Runtime BUY rows.

| B10 priority | Symbol | Candidate rank | Entry | BUY Quality | Expected Edge | PM action | Membership | Target weight | Current weight | Quantity | Reserved notional | Decision | B10 class |
|---:|---|---:|---|---|---|---|---|---:|---:|---:|---:|---|---|
| 1 | `94320` | 1 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.052632 | 0 | 300 | 59,640 | INCLUDE | ELIGIBLE_COMPARABLE |
| 2 | `66590` | 2 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.052632 | 0 | 500 | 76,000 | INCLUDE | ELIGIBLE_COMPARABLE |
| 3 | `93180` | 4 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.050000 | 0 | 8,300 | 290,500 | INCLUDE | ELIGIBLE_COMPARABLE |
| 4 | `23700` | 5 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.052632 | 0 | 700 | 71,400 | INCLUDE | ELIGIBLE_COMPARABLE |
| 5 | `23880` | 8 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.052632 | 0 | 300 | 61,200 | INCLUDE | ELIGIBLE_COMPARABLE |
| 6 | `76470` | 10 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.052632 | 0 | 2,000 | 112,000 | INCLUDE | ELIGIBLE_COMPARABLE |
| 7 | `94340` | 12 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.052632 | 0 | 300 | 60,150 | INCLUDE | ELIGIBLE_COMPARABLE |
| 9 | `89180` | 16 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.050000 | 0 | 5,000 | 205,000 | INCLUDE | ELIGIBLE_COMPARABLE |
| 10 | `47770` | 17 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.068400 | 0 | 100 | 78,000 | PRUNE | ELIGIBLE_COMPARABLE |
| 11 | `99840` | 20 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.132880 | 0 | 100 | 162,380 | PRUNE | ELIGIBLE_COMPARABLE |
| 12 | `95010` | 24 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.050000 | 0 | 100 | 56,900 | INCLUDE | ELIGIBLE_COMPARABLE |
| 13 | `61980` | 25 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.035600 | 0 | 100 | 43,000 | PRUNE | ELIGIBLE_COMPARABLE |
| 14 | `83060` | 30 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.071350 | 0 | 100 | 85,920 | PRUNE | ELIGIBLE_COMPARABLE |
| 15 | `39950` | 32 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.052800 | 0 | 100 | 61,500 | PRUNE | ELIGIBLE_COMPARABLE |
| 16 | `38410` | 33 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.080800 | 0 | 100 | 96,700 | PRUNE | ELIGIBLE_COMPARABLE |
| 18 | `47840` | 37 | BUY_NEW_REDUCED_ONLY | REDUCED_ALLOCATION_ONLY | UNCALIBRATED | blank | ADD_CANDIDATE | 0.045000 | 0 | 100 | 52,800 | PRUNE | ELIGIBLE_COMPARABLE |

## PRIORITY INTERNAL CONSISTENCY

```text
PRIORITY_INTERNAL_CONSISTENCY = PASS
```

Checks:

- Higher marginal class is not lower priority: PASS.
- Missing evidence is not advantaged: PASS.
- BUY_NEW/BUY_ADD label-only ordering: PASS.
- Low price / large share count distortion: PASS.
- Notional size treated as economic value: PASS.
- Lot feasibility mixed into B10 value: PASS.
- Stale/default/fallback evidence gaining priority: PASS.

All 16 control-date positive Runtime BUY rows share the same B10 class and sufficiency, so order is by PIT candidate rank. That is exactly reproducible from the implementation.

## UPSTREAM EVIDENCE ALIGNMENT

```text
UPSTREAM_EVIDENCE_ALIGNMENT_COUNTS = {
  ALIGNED: 16,
  JUSTIFIED_REORDERING: 0,
  ECONOMIC_EVIDENCE_CONFLICT: 0,
  INSUFFICIENT_EVIDENCE: 0
}
```

The control date does not show a weak upstream candidate being promoted by B10 normalization alone. All positive Runtime BUY rows have buy-eligible Entry, reduced-allocation BUY Quality, and comparable PIT opportunity evidence. The priority order tracks candidate rank because no stronger calibrated economic evidence exists in the artifact.

## DIVERGENT SYMBOL EXPLANATIONS

### 93180_PRIORITY_EXPLANATION

```text
93180_PRIORITY_EXPLANATION = BUY_NEW; ELIGIBLE_COMPARABLE; candidate rank 4; entry BUY_NEW_REDUCED_ONLY; BUY Quality REDUCED_ALLOCATION_ONLY; comparable PIT opportunity evidence; rank 3 executable BUY absent from positive Runtime BUY batch; priority index 3 among positive executable BUYs
```

The 8,300 share quantity and 290,500 reserved notional do not determine 93180's B10 priority. B10 priority comes from class and candidate rank. 93180's large share count is a consequence of price/lot sizing after priority, not priority evidence.

### 38410_PRIORITY_EXPLANATION

```text
38410_PRIORITY_EXPLANATION = BUY_NEW; ELIGIBLE_COMPARABLE; candidate rank 33; entry BUY_NEW_REDUCED_ONLY; BUY Quality REDUCED_ALLOCATION_ONLY; comparable PIT opportunity evidence; priority index 16 among positive executable BUYs; PRUNE because remaining cash 7,210 < reserved notional 96,700
```

38410 is not blocked by Entry or BUY Quality on the control date. It is lower priority because the B10 sort uses class first and candidate rank second; its class ties with other positive BUY rows and its rank is lower.

## BUY_NEW VS BUY_ADD COMPETITION

Control date:

```text
BUY_NEW_COUNT = 19
BUY_ADD_COUNT = 0
MIXED_COMPETITION_COUNT = 0
NEW_ABOVE_ADD_COUNT = 0
ADD_ABOVE_NEW_COUNT = 0
```

Secondary window:

```text
BUY_NEW_COUNT = 445
BUY_ADD_COUNT = 7
MIXED_COMPETITION_DAYS = 7
NEW_ABOVE_ADD_PAIR_COUNT = 0
ADD_ABOVE_NEW_PAIR_COUNT = 63
```

```text
HIDDEN_NEW_FIRST = NO
HIDDEN_ADD_FIRST = NO
```

ADD can rank above NEW in mixed days, but only because explicit ADD lifecycle evidence produces `ELIGIBLE_STRONG`. The implementation sets both unconditional label-priority flags to false.

## SCALE AND DISTORTION

```text
MARGINAL_VALUE_SCALE_COMPARABLE = PARTIAL
QUANTITY_DISTORTION = NO
NOTIONAL_DISTORTION = NO
```

The scale is comparable as an ordinal control signal: class order and rank order are deterministic and PIT-safe. It is only partially comparable as an economic marginal value because most BUY_NEW rows are `ELIGIBLE_COMPARABLE` and then rank-ordered by uncalibrated relative opportunity rank rather than expected-return, JPY edge, or risk-adjusted marginal utility.

Quantity and notional are not part of the B10 sort key. They affect later cash feasibility, not B10 priority. The control table confirms that high-share-count names such as `93180` and `89180` are not prioritized because of share count, and large-notional names such as `99840` are not automatically promoted.

## B10 DEFECT JUDGMENT

```text
B10_FORMULA_DEFECT_SUPPORTED = NO
B10_DESIGN_GAP_SUPPORTED = PARTIAL
```

No formula defect is supported. The implementation is reproducible, PIT-safe, and consistent with its declared ordering rules.

The partial design gap is naming/semantic strength: the authority is called marginal capital value, but the dominant current evidence path is ordinal class plus candidate rank, not a calibrated marginal economic value. That does not justify formula repair by E3; it suggests a design clarification or future calibrated-edge authority if the system later requires true cross-candidate economic units.

## ADD_CANDIDATE + PM_ACTION NEW + ZERO QUANTITY

Current secondary-window counts:

```text
ADD_CANDIDATE_PM_NEW_CASE_COUNT = 688
LEGITIMATE_ZERO_COUNT = 0
SEMANTIC_MISMATCH_COUNT = 688
ZERO_QUANTITY_SEMANTIC_GAP_CONTRIBUTION_COUNT = 25
```

Structural breakdown:

```text
true_existing_holding = 0
no_existing_holding = 688
stale_membership = 0
NEW_semantic_but_ADD_membership_valid = 0
PM_PC_mismatch = 688
target_le_current = 688
lot_zero = 0
cap_zero = 0
legitimate_no_op = 0
evidence_missing = 0
unique_symbols = 118
```

Interpretation:

- Every current case has no existing holding and zero target/current quantity after PC/PS.
- PC evidence can show `membership_intent=ADD_CANDIDATE` while `target_membership=false`.
- PS derives `pm_action=NEW` when membership is `ADD_CANDIDATE` and PM action is blank.
- PS then resolves quantity to zero and classifies the row as `QUALITY_DEFERRED_TO_CASH`.

The zero quantity itself is not arithmetically wrong. The gap is semantic ownership: `ADD_CANDIDATE`, `target_membership=false`, implicit `pm_action=NEW`, and zero quantity coexist without a single explicit contract label such as `NOT_SELECTED_BUY_NEW_CANDIDATE` or `QUALITY_DEFERRED_NO_TARGET`.

## SEMANTIC OWNERSHIP

```text
PM_PC_SEMANTIC_CONTRACT = AMBIGUOUS
```

Ownership reading:

- PM owns existing-position actions such as ADD/HOLD/REDUCE/EXIT. For new candidates, PM action may be blank upstream.
- PC owns target membership, membership intent, target weight, and accepted incremental/new weight.
- PS owns concrete quantity and zero-delta resolution.

The current artifacts do not prove an invalid mutation, but they do leave an ambiguous cross-owner state. A non-held symbol with `target_membership=false` and `target_weight=0` should not need to remain semantically named `ADD_CANDIDATE` all the way into PS as implicit `pm_action=NEW`.

Materiality:

```text
OLD_POSITIVE_RUNTIME_BUY_COUNT = 178
CURRENT_POSITIVE_RUNTIME_BUY_COUNT = 153
POSITIVE_RUNTIME_BUY_REDUCTION = 25
ZERO_QUANTITY_SEMANTIC_GAP_CONTRIBUTION_COUNT = 25
```

The semantic family is large enough to cover the observed 25-row reduction in positive Runtime BUY supply. E3 does not claim a one-to-one symbol-level cause for every lost BUY, only that the family is structurally material and upstream of Pending.

## REPAIR_CANDIDATES

PIT-supported family-wide repair/design candidates:

1. Clarify PC membership semantics for unheld candidates that are not selected into target membership. Consider emitting an explicit non-target candidate state instead of carrying `ADD_CANDIDATE` with `target_membership=false`.
2. Clarify PS PM-action fallback semantics so blank PM action plus PC `ADD_CANDIDATE` does not silently become `pm_action=NEW` for zero-target rows without an explicit canonical reason.
3. Add a contract check that `membership_intent=ADD_CANDIDATE`, `target_membership=false`, `target_weight=0`, and `final_quantity_delta=0` is either explicitly valid with a canonical no-op reason or normalized to a non-buy membership state.
4. Document B10 as an ordinal PIT marginal-priority authority unless/until calibrated economic units are introduced.

Not repair candidates from E3:

- B10 formula change.
- B10 weight/threshold tuning.
- Candidate AI rank tuning.
- Using later returns to override priority.

## REQUIRED FLAGS

```text
FUTURE_INFORMATION_USED_FOR_PRIORITY_JUDGMENT = NO
OUTCOME_USED_FOR_PARAMETER_SELECTION = NO
IMPLEMENTATION_CHANGED = NO
LONG_HISTORICAL_EXECUTED = NO
```

## NEXT_TASK_RECOMMENDATION

```text
Phase31-E4 focused PM/PC/PS semantic repair; do not perform B10 formula repair.
```

## FINAL QUESTIONS

1. B10 priorityは同じPIT evidenceから完全に再現できるか？

   Yes. Recomputed priority matched stored current artifacts with zero mismatches.

2. priority順位はB10自身の設計思想に整合しているか？

   Yes for the implemented ordinal contract. It is only partial as true economic marginal value because calibrated edge units are not present.

3. 上流PIT evidenceと明確に矛盾する順位はあるか？

   No. Control-date alignment count is 16 aligned, 0 conflict.

4. BUY_NEW/BUY_ADDのhidden priorityはないか？

   No. Both unconditional label-priority flags are false. ADD outranks NEW only with explicit `ELIGIBLE_STRONG` ADD evidence.

5. 株価・株数・notionalでpriorityが歪んでいないか？

   No. Quantity and notional are not sort-key inputs; they affect later cash feasibility only.

6. 93180がpriority 3になった理由はPIT上合理的か？

   Yes under the implemented contract: BUY_NEW, comparable PIT evidence, candidate rank 4, and rank 3 absent from the positive executable BUY batch.

7. ADD_CANDIDATE + pm_action=NEW + zero quantityは正常か？

   Ambiguous. Quantity zero is resolved, but the cross-owner semantic state is not cleanly named or contract-closed.

8. E4で修正すべきfamily-wide defectは確認できたか？

   Yes. Focus E4 on PM/PC/PS semantic repair for zero-target `ADD_CANDIDATE` rows, plus documentation/contract clarification for B10 as ordinal PIT priority rather than calibrated economic value.
