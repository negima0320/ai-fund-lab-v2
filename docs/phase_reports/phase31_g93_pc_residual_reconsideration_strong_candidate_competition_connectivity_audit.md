# Phase31-G93 — PC Residual Reconsideration / Strong Candidate Competition Connectivity Audit

## PRIMARY_JUDGMENT

PHASE31_G93_PC_RESIDUAL_RECONSIDERATION_CONNECTIVITY_DEFECT_CONFIRMED_REPAIR_REQUIRED

## Scope

READ-ONLY audit only.

Target run:

```text
runtime-test-historical-extended-smoke-20260824T055234719725Z
```

Primary dates:

```text
2023-04-05
2023-04-06
```

Representative candidates were selected from same-date PIT evidence only. No code, config, threshold, weight, run state, fresh-run, resume, replay, or Historical execution was changed or executed for G93. Future outcomes were not used.

## Executive Conclusion

G93 confirms an architecture connectivity defect at the PC residual reconsideration boundary.

The Architecture SoT says residual capital that appears usable by another valid competitor must trigger PC-owned reconsideration:

```text
REALLOCATABLE_RESIDUAL = capital appears usable by another valid competitor and must trigger reconsideration
target allocation -> discrete quantity -> unallocatable residual -> next competitor / ADD reconsideration -> legitimate residual Cash
```

The implementation exposes a `residual_reconsideration` artifact and marks the mechanism as implemented when lot-aware evidence exists, but actual representative rows with:

```text
REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION
```

become:

```text
COMPETITOR_REJECTED_RECONSIDERABLE
accepted_weight = 0
target_weight = 0
not in security_allocations[]
not in cash_preferred_security_deferrals[]
not consumed by PS / Runtime
```

In the target run, a scan of existing completed PC artifacts found `162` dates with `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION` rows and `0` cases where such a row itself became a positive final security allocation. That does not prove residual capital is unreconciled globally, but it proves this semantic is not a row-level path back into final positive allocation.

Therefore G90 receives an already-pruned weak subset on `2023-04-05` and `2023-04-06`. G90 should not be repaired to compensate for upstream credible candidates that never enter its final selected/deferrable input set.

## Required Judgments

```text
RESIDUAL_RECONSIDERATION_SEMANTIC_DEFINED = YES
RESIDUAL_RECONSIDERATION_CONSUMER_EXISTS = PARTIAL
RESIDUAL_RECONSIDERATION_TERMINAL_DEAD_END = YES
RESIDUAL_CAPITAL_DESTINATION_RECONCILED = YES

VALID_SAFETY_RESERVE_BEHAVIOR = CORRECT

G90_INPUT_SET_COMPLETE_FOR_CAPITAL_COMPETITION = NO

ALL_CREDIBLE_DESTINATIONS_ENTER_CANONICAL_COMPETITION = NO

LEGACY_SINGLE_ALLOCATION_SEMANTIC_CONFLICT = PARTIAL

IMPLEMENTATION_SOT_CONFORMANCE = PARTIAL

ARCHITECTURE_CONNECTIVITY_DEFECT_CONFIRMED = YES

REPAIR_REQUIRED = YES
```

## Canonical Semantic Definition

### REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION

Producer:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
_capital_constraint_reason_code()
build_capital_competition_framework()
apply_lot_aware_final_reallocation()
```

Artifact / field:

```text
strategy/portfolio_construction.json
capital_competition.competitors[].reason_codes[]
capital_competition.residual_reconsideration
```

SoT semantic:

```text
REALLOCATABLE_RESIDUAL = capital appears usable by another valid competitor and must trigger reconsideration.
Next-best valid competitors may be reconsidered only through PC-owned competition.
```

Authority owner:

```text
PORTFOLIO_CONSTRUCTION
```

Intended consumer:

```text
Portfolio Construction residual / infeasible allocation reconsideration
```

Terminality:

```text
Non-terminal by SoT.
```

Observed implementation behavior:

```text
The row is marked COMPETITOR_REJECTED_RECONSIDERABLE.
The row does not re-enter canonical_multi_allocation_deployment_set.security_allocations[].
The row does not appear in cash_preferred_security_deferrals[].
PS and Runtime correctly do not resurrect it.
```

### VALID_SAFETY_RESERVE

Producer:

```text
_capital_constraint_reason_code()
```

Primary source condition:

```text
canonical_sizing_evidence.constraint_reason_codes contains SAFETY_CAP_BOUND
or lot resolution indicates minimum executable lot exceeds Safety hard max.
```

Artifact / field:

```text
capital_competition.competitors[].reason_codes[]
lot_aware_final_reallocation.skipped[]
portfolio_members[].lot_first_rebatch_skip_reason
```

Semantic:

```text
Safety boundary prevents use.
```

Authority owner:

```text
Safety / PC as consumer of Safety boundary evidence.
```

Terminality:

```text
Terminal for current capital authority.
```

Observed behavior:

```text
Correct. It blocks allocation and returns capital to Cash / reserve without downstream resurrection.
```

## Consumer Connectivity

Observed production flow:

```text
apply_lot_aware_final_reallocation()
-> final member target_weight / lot_aware_final_target_weight
-> build_capital_competition_framework()
-> capital_competition.competitors[]
-> canonical_multi_allocation_deployment_set
-> Position Sizing
-> Runtime Planning
```

Connectivity result:

```text
RESIDUAL_RECONSIDERATION_CONSUMER_EXISTS = PARTIAL
```

There is a PC-owned function that performs lot-aware allocation and produces `residual_reconsideration.implemented = true`. It does reconsider lower-priority lot-feasible candidates in sorted order and can allocate to other securities. However, rows marked `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION` are not themselves later reconsidered into the canonical selected set. They become rejected reconsiderable evidence rows.

Observed terminality:

```text
RESIDUAL_RECONSIDERATION_TERMINAL_DEAD_END = YES
```

At the row level, `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION` is effectively terminal in the actual artifacts, despite the SoT saying it must trigger reconsideration.

## Representative Candidate Lineage

### 2023-04-05

| Symbol | Rank | Score | Confidence | Momentum | Relative Strength | PC Competitor Status | Reason | Final Allocation | Final Deferral | Runtime BUY |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |
| 83060 | 2 | +0.2962 | 0.98 | MIXED_OR_UNRESOLVED | MIXED | COMPETITOR_REJECTED_RECONSIDERABLE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | NO | NO | NO |
| 59350 | 6 | +0.1610 | 0.90 | HEALTHY_CONTINUATION | SUPPORTIVE | COMPETITOR_REJECTED_RECONSIDERABLE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | NO | NO | NO |
| 77760 | 7 | +0.0192 | 0.88 | MIXED_OR_UNRESOLVED | SUPPORTIVE | COMPETITOR_REJECTED_RECONSIDERABLE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | NO | NO | NO |
| 44440 | 10 | -0.0595 | 0.82 | MIXED_OR_UNRESOLVED | SUPPORTIVE | COMPETITOR_REJECTED_RECONSIDERABLE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | NO | NO | NO |

Final canonical deployment on `2023-04-05`:

```text
security_allocations = []
cash_preferred_security_deferrals = 44270, 76920, 95560, 83080
authorized_cash_allocation = 0.522197
security_allocation_total = 0
```

The representative stronger rows do not reach G90 final deferral resolution. G90 sees only the selected weak-tail-like subset.

### 2023-04-06

| Symbol | Rank | Score | Confidence | Momentum | Relative Strength | PC Competitor Status | Reason | Final Allocation | Final Deferral | Runtime BUY |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |
| 83060 | 2 | +0.3103 | 0.98 | MIXED_OR_UNRESOLVED | MIXED | COMPETITOR_REJECTED_RECONSIDERABLE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | NO | NO | NO |
| 59350 | 3 | +0.2584 | 0.96 | HEALTHY_CONTINUATION | SUPPORTIVE | COMPETITOR_REJECTED_RECONSIDERABLE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | NO | NO | NO |
| 43880 | 4 | +0.2472 | 0.94 | HEALTHY_CONTINUATION | SUPPORTIVE | COMPETITOR_REJECTED_RECONSIDERABLE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | NO | NO | NO |
| 67310 | 5 | +0.2091 | 0.92 | MIXED_OR_UNRESOLVED | SUPPORTIVE | COMPETITOR_REJECTED_TERMINAL | VALID_SAFETY_RESERVE | NO | NO | NO |
| 94340 | 7 | +0.0305 | 0.88 | MIXED_OR_UNRESOLVED | SUPPORTIVE | COMPETITOR_REJECTED_RECONSIDERABLE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | NO | NO | NO |
| 77760 | 8 | +0.0301 | 0.86 | MIXED_OR_UNRESOLVED | SUPPORTIVE | COMPETITOR_REJECTED_RECONSIDERABLE | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | NO | NO | NO |

Final canonical deployment on `2023-04-06`:

```text
security_allocations = []
cash_preferred_security_deferrals = 44270, 50320, 73180, 79970, 95560, 83080
authorized_cash_allocation = 0.740000
security_allocation_total = 0
```

`67310` is different from the other representative rows. It is terminal because one executable lot exceeds the Safety hard cap:

```text
lot_aware skip = minimum_lot_exceeds_safety_hard_cap
constraint reason = SAFETY_CAP_BOUND
classification = VALID_SAFETY_RESERVE
```

This is a legitimate Safety reserve and must not be weakened merely because the same-date candidate evidence looks strong.

## Residual Capital Reconciliation

The capital is reconciled at the aggregate level:

```text
2023-04-05 allocated_plus_cash_plus_residual = 0.522197
2023-04-05 authorized_cash_allocation = 0.522197
2023-04-05 unallocated_residual = 0

2023-04-06 allocated_plus_cash_plus_residual = 0.740000
2023-04-06 authorized_cash_allocation = 0.740000
2023-04-06 unallocated_residual = 0
```

Therefore:

```text
RESIDUAL_CAPITAL_DESTINATION_RECONCILED = YES
```

But the destination is Cash, not reconsidered positive security allocation for the representative rows.

This distinction matters:

```text
capital accounting is reconciled
row-level reconsideration connectivity is defective
```

## Normal Date Comparison

The target run contains many dates where `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION` appears alongside positive security allocations to other symbols. That proves the broader day-level allocation engine can allocate securities after some rows are rejected.

However, scanning the run's existing completed PC artifacts found:

```text
dates with REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION rows = 162
dates where such a row itself appears in final positive security_allocations[] = 0
```

No normal date was found where a row carrying the reconsideration semantic itself successfully becomes positive final allocation. This is material evidence that the current semantic is not an actual row-level non-terminal state.

## G90 Interaction

G90 receives only the already-selected subset, not the full credible competitor set.

Evidence:

```text
2023-04-05 high-ranked rows 83060, 59350, 77760, 44440
-> COMPETITOR_REJECTED_RECONSIDERABLE
-> absent from security_allocations[]
-> absent from cash_preferred_security_deferrals[]

2023-04-06 high-ranked rows 83060, 59350, 43880, 94340, 77760
-> COMPETITOR_REJECTED_RECONSIDERABLE
-> absent from security_allocations[]
-> absent from cash_preferred_security_deferrals[]
```

Required judgment:

```text
G90_INPUT_SET_COMPLETE_FOR_CAPITAL_COMPETITION = NO
```

G90 must not be repaired to buy or preserve candidates it never receives as final competition rows.

## Multi-Allocation Interaction

The SoT now defines:

```text
GENERAL_CAPITAL_WINNER_CARDINALITY = MULTI_ALLOCATION
CAPITAL_ALLOCATION_PROBLEM_TYPE = HYBRID_MULTI_SECURITY_CAPITAL_BUDGET_ALLOCATION
CASH_PARTIAL_ALLOCATION_SUPPORTED = YES
CASH_WINNER_TAKES_ALL_REQUIRED = NO
MULTI_ALLOCATION_LOT_RECONSIDERATION_DEFINED = YES
```

The implementation partially conforms:

- multiple securities can be allocated on other dates
- Cash is first-class
- PS / Runtime do not redecide capital priority
- Safety reserve remains terminal

But `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION` behaves like a defeated row label rather than a true non-terminal reconsideration input. This looks like a partial legacy single-allocation semantic conflict: residual reconsideration can move capital to some later selected rows, but not all credible destinations enter the same canonical competition as first-class reconsideration candidates.

```text
LEGACY_SINGLE_ALLOCATION_SEMANTIC_CONFLICT = PARTIAL
```

## SoT Conformance

Passes:

- PC owns final capital winner.
- PS does not recreate defeated security quantities.
- Runtime does not reintroduce defeated securities.
- Cash remains a valid competitor.
- Safety hard cap is preserved.
- Residual capital is accounted for.

Fails / partial:

- SoT says usable residual must trigger reconsideration.
- Actual row-level `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION` does not re-enter final positive allocation.
- Stronger same-date PIT candidates can be excluded before canonical final G90 security/Cash partition.

Required judgment:

```text
IMPLEMENTATION_SOT_CONFORMANCE = PARTIAL
```

## Repair Boundary

Do not change:

- G90
- Market Quality
- Risk Pacing
- Candidate ranking
- PM / SELL
- PS / Runtime
- Safety hard cap behavior
- thresholds or weights

Narrow repair boundary:

```text
Portfolio Construction residual reconsideration / selected competitor connectivity
```

Specifically:

```text
REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION
must either:
  1. be actually reconsidered by PC into security / Cash with explicit final lineage, or
  2. be renamed / reclassified as terminal defeated evidence if no reconsideration is intended.
```

The preferred architecture-consistent repair is not to force high-ranked candidates to buy. It is to ensure every credible destination gets the canonical PC-owned capital competition process promised by the Architecture.

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
```
