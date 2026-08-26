# Phase31-E5 — B10 Retention / Reversion Architecture Decision Audit

Status: COMPLETE
Task type: READ-ONLY ARCHITECTURE / PIT DECISION AUDIT

## PRIMARY_JUDGMENT

```text
PHASE31_E5_KEEP_AND_CLARIFY_B10_REFINE_LATER_NO_REVERSION
```

E5 audited whether B10 `MARGINAL_CAPITAL_VALUE_AUTHORITY` should be kept, refined, deprecated, or reverted using architecture and PIT evidence only. No implementation, B10 removal/reversion, parameter/threshold/weight tuning, fresh-run, resume, replay, or long Historical execution was performed.

The recommended disposition is:

```text
RECOMMENDED_B10_DISPOSITION = KEEP_AND_CLARIFY + REFINE_LATER
```

B10 should not be reverted. The original B0-B9 problem remains valid: pre-B10 ordering can place weaker/comparable BUY_NEW capital before strong BUY_ADD capital, causing cash starvation under reserved-cash feasibility. B10 fixed the architectural ownership path by making PC produce a canonical BUY_NEW/BUY_ADD marginal priority and Runtime/Pending consume it. E1-E4 found no B10 formula defect, no reserved-cash defect, no hidden ADD-first/NEW-first policy, no quantity/notional distortion, and no B10-caused zero-target BUY loss.

The clarification is important: current B10 is not a true calibrated marginal economic value model. It is an ordinal PIT capital-priority authority. That is still architecturally valuable because it puts BUY_NEW and BUY_ADD into one auditable capital competition and protects strong ADD only when explicit PIT lifecycle evidence supports it.

## ORIGINAL B10 PROBLEM

```text
ORIGINAL_B10_PROBLEM = pre-B10 common BUY_NEW/BUY_ADD capital competition lacked an explicit lifecycle-aware marginal priority, allowing strong positive-increment ADD to be cash-starved by lower-canonical BUY_NEW processing order
ORIGINAL_B10_PROBLEM_CONFIRMED = YES
```

B0 established the initial defect without using future returns:

- BUY_NEW and BUY_ADD shared capital competition, but no explicit cross-lifecycle priority authority existed.
- 94320 had PIT-valid positive ADD attempts.
- On 2022-08-19 and 2022-08-24, prior BUY_NEW includes consumed reserved cash before 94320 BUY_ADD, then 94320 was pruned as `DEFERRED_INSUFFICIENT_RESERVED_CASH`.

B9 revalidated the structural gate:

- `STRONG_ADD_CANDIDATE_COUNT = 9`
- `STRONG_ADD_AHEAD_OF_NEW_PAIR_COUNT = 75`
- `ACTUAL_STRONG_ADD_STARVED_BY_WEAKER_NEW_COUNT = 2`
- `ACTUAL_STRONG_ADD_STARVED_BY_WEAKER_NEW_NOTIONAL = 120,360`
- `STRONG_NEW_STARVED_BY_WEAKER_ADD_COUNT = 0`
- no hidden ADD-first or NEW-first label priority.

B10 then implemented the narrow mutating authority:

- PC owns `MARGINAL_CAPITAL_VALUE_AUTHORITY`.
- Runtime consumes PC priority.
- Pending reserved-cash feasibility preserves the priority.
- PM ADD semantics, Expected Edge thresholds, Market Context, Strategy cap, Safety hard cap, Submit, Execution, and SELL logic were not changed.

## OLD PRIORITY AUTHORITY

```text
OLD_PRIORITY_AUTHORITY = construction_priority / quality_order / stable strategy order derived from Opportunity and PC/PS row order, then consumed by Runtime/Pending cash batch
```

Old priority inputs:

```text
OLD_PRIORITY_INPUTS = opportunity rank, construction_priority, quality-adjusted reallocation order, symbol/stable order, lot/materialization filtering
```

Old NEW/ADD semantics:

```text
OLD_NEW_ADD_SEMANTICS = BUY_NEW and BUY_ADD entered common capital and cash feasibility paths, but no explicit cross-side marginal value authority compared strong ADD against comparable NEW
```

```text
OLD_PRIORITY_REINTRODUCES_CONFIRMED_GAP = YES
```

Reverting to old priority would reintroduce the exact class of problem B0-B9 documented: processing-order dependence for mixed BUY_NEW/BUY_ADD capital under finite cash. The old path can be deterministic, but determinism is not the same as an explicit marginal-capital authority.

## CURRENT B10 VALUE

Current B10 evidence from E2-E4:

- B10 priority is behaviorally preserved PC -> Runtime -> Pending -> Fill.
- `LOWER_PRIORITY_CASH_PREEMPTION_COUNT = 0`
- `DOUBLE_RESERVATION_COUNT = 0`
- `INCLUDED_BUY_NO_EXECUTION_COUNT = 0`
- B10 priority is reproducible from PIT artifacts.
- `CURRENT_WINDOW_PRIORITY_MISMATCH_COUNT = 0`
- `CURRENT_WINDOW_B10_CANDIDATE_COUNT = 452`
- `ELIGIBLE_COMPARABLE = 432`
- `ELIGIBLE_STRONG = 20`
- `HIDDEN_NEW_FIRST = NO`
- `HIDDEN_ADD_FIRST = NO`
- `QUANTITY_DISTORTION = NO`
- `NOTIONAL_DISTORTION = NO`
- zero-target BUY candidate family was not B10-caused.

Architecture value:

1. It gives PC explicit ownership of marginal capital order.
2. It gives Runtime/Pending a canonical Strategy order to consume rather than infer.
3. It keeps BUY_NEW and BUY_ADD in one competition without unconditional side preference.
4. It preserves strong NEW protection and weak ADD protection.
5. It makes cash causality auditable.

## EFFECTIVE SEMANTICS

```text
B10_EFFECTIVE_SEMANTICS = ORDINAL_PRIORITY
```

Current B10 is not a true calibrated marginal economic value authority. Most BUY_NEW rows are `ELIGIBLE_COMPARABLE`, then ordered by candidate rank. Strong ADD rows can move above comparable NEW rows only when explicit PIT lifecycle evidence exists.

This makes B10 an ordinal PIT capital-priority authority: class first, rank second, fallback/missing evidence after sufficient evidence, then stable symbol tie-break.

## CANDIDATE RANK DUPLICATION

```text
B10_DUPLICATES_CANDIDATE_RANK = PARTIAL
B10_ADDS_UNIQUE_CAPITAL_ALLOCATION_VALUE = YES
```

B10 partially duplicates candidate rank for BUY_NEW rows because, without calibrated economic edge units, many BUY_NEW candidates share the `ELIGIBLE_COMPARABLE` class and then sort by rank.

It still adds unique architecture value because Candidate rank alone cannot compare positive BUY_ADD increments against BUY_NEW candidates. B10 adds:

- lifecycle intent normalization;
- ADD evidence gating;
- no label-only ADD/NEW priority;
- a single PC-owned priority for Runtime/Pending;
- explicit missing-evidence semantics;
- protection against strong ADD starvation by lower-value prior NEW items.

## ADD PROTECTION AND REVERSION RISK

```text
STRONG_ADD_STARVATION_REINTRODUCED_BY_REVERT = YES
```

The strongest gate against reversion is B0/B9 structural evidence. Reverting removes the canonical authority that placed strong ADD into the same priority order as BUY_NEW and allowed Runtime/Pending to preserve that order. That would reopen the known class of processing-order starvation.

This judgment does not use later returns. It uses only same-day PIT marginal evidence and reserved-cash ordering evidence.

## B10 DEFECT AND EDGE RELATIONSHIP

```text
B10_FORMULA_DEFECT_CONFIRMED = NO
CALIBRATED_EDGE_REQUIRED_FOR_TRUE_MARGINAL_VALUE = YES
```

E3 found B10 formula reproducible and internally consistent. The gap is semantic precision: to become true marginal economic value, B10 needs calibrated Expected Edge or equivalent comparable economic units. Current Expected Edge is often `UNCALIBRATED`, so B10 should be documented as ordinal priority now and refined later when calibrated edge evidence exists.

E5 does not authorize Expected Edge implementation or tuning.

## ARCHITECTURE ALTERNATIVES

| Alternative | Judgment | Architecture consistency | ADD starvation risk | PIT safety | Migration impact |
|---|---|---|---|---|---|
| A. KEEP B10 AS-IS | Acceptable but incomplete | PASS | LOW | PASS | LOW |
| B. KEEP + CLARIFY | Recommended now | PASS | LOW | PASS | LOW |
| C. REFINE LATER | Recommended later | PASS if calibrated evidence exists | LOW | Depends on future evidence | MEDIUM |
| D. REVERT | Not recommended | FAILS known B0/B9 gap | HIGH | PASS but under weaker authority | HIGH |
| E. DEPRECATE | Not recommended now | Requires replacement authority | UNKNOWN/HIGH | UNKNOWN | HIGH |

Recommended combination:

```text
KEEP_AND_CLARIFY + REFINE_LATER
```

Clarify now that B10 is an ordinal PIT capital-priority authority, not a calibrated return predictor. Refine later only when Expected Edge or another canonical economic edge authority has comparable units.

## REASON

```text
REASON = B10 solves a confirmed architecture gap in mixed BUY_NEW/BUY_ADD capital competition; current audits found no B10 formula defect; revert would restore known strong-ADD starvation risk; current semantic gap is naming/calibration clarity, not a reason to remove the authority
```

## REVERSION SAFETY

Reversion would not be a simple delete. It would affect:

- PC marginal priority production.
- Runtime Planning canonical Strategy order.
- Pending item fields and reserved-cash evaluation order.
- cash-feasible batch evidence.
- diagnostic shadow paths.
- architecture documentation and tests.

Permanent legacy fallback is not recommended. If B10 were ever replaced, it should be replaced by a new explicit PC-owned capital-priority authority, not by silent old ordering.

## REQUIRED OUTPUT

```text
PRIMARY_JUDGMENT = PHASE31_E5_KEEP_AND_CLARIFY_B10_REFINE_LATER_NO_REVERSION
ORIGINAL_B10_PROBLEM = pre-B10 common BUY_NEW/BUY_ADD capital competition lacked explicit lifecycle-aware marginal priority and could starve strong ADD behind weaker/comparable NEW
ORIGINAL_B10_PROBLEM_CONFIRMED = YES
OLD_PRIORITY_AUTHORITY = construction_priority / quality_order / stable strategy order derived from Opportunity and PC/PS row order
OLD_PRIORITY_REINTRODUCES_CONFIRMED_GAP = YES
B10_EFFECTIVE_SEMANTICS = ORDINAL_PRIORITY
B10_DUPLICATES_CANDIDATE_RANK = PARTIAL
B10_ADDS_UNIQUE_CAPITAL_ALLOCATION_VALUE = YES
STRONG_ADD_STARVATION_REINTRODUCED_BY_REVERT = YES
B10_FORMULA_DEFECT_CONFIRMED = NO
CALIBRATED_EDGE_REQUIRED_FOR_TRUE_MARGINAL_VALUE = YES
RECOMMENDED_B10_DISPOSITION = KEEP_AND_CLARIFY + REFINE_LATER
TRADING_BEHAVIOR_CHANGE_AUTHORIZED = NO
OUTCOME_USED_FOR_ARCHITECTURE_DECISION = NO
FUTURE_INFORMATION_USED = NO
IMPLEMENTATION_CHANGED = NO
LONG_HISTORICAL_EXECUTED = NO
```

## NEXT_TASK_RECOMMENDATION

```text
Do not revert B10. If continuing Phase31-E, perform narrow documentation/observability cleanup: describe B10 as ordinal PIT capital priority, preserve current behavior, and separately decide whether to clean zero-target semantic labels. Move return-degradation investigation to the next non-B10 causal family if trading-behavior repair is the goal.
```

## FINAL QUESTIONS

1. B10は残すべきか？

   Yes. Keep it, clarify it, and refine later.

2. 旧priorityへ戻すべきか？

   No. Reversion reintroduces the confirmed B0/B9 strong-ADD starvation gap.

3. B10は本当にmarginal economic valueか？

   Not yet. It is an ordinal PIT capital-priority authority.

4. Candidate rankの重複ではないか？

   Partially for BUY_NEW, but not for mixed BUY_NEW/BUY_ADD capital competition.

5. Expected Edge calibrated化が必要か？

   Yes, if the goal is true marginal economic value. Not required to keep current ordinal priority.

6. E5で売買挙動変更を認めるか？

   No. E5 authorizes no trading behavior change.
