# Phase32-DA - 94320 ADD Blocked-Class Acceptance Exact Trace

## Executive Summary

Read-only audit of `runtime-test-historical-extended-smoke-20260829T082306780474Z` confirms a production authority inconsistency on `2022-10-21` for `94320` ADD lot #1/#2/#3.

The three lots were accepted by `canonical_marginal_capital_frontier_authority.v1` even though their decision-time opportunity-quality evidence was classified as blocked:

- `authority_disposition = ACCEPTED_INCREMENTAL_TARGET`
- `comparison_class = BLOCKED`
- `marginal_capital_value_class = BLOCKED_OR_NOT_ELIGIBLE`
- reason includes `opportunity_quality_add_hard_block`
- `desirability.status = REVIEW_REQUIRED`
- `add_admission_authority.status = PASS`
- `final_add_eligibility = PASS`

Primary diagnosis: **MIXED, with the first defect in Portfolio Construction marginal-frontier acceptance**. ADD admission PASS was treated as sufficient for comparison, while the separate marginal value / opportunity-quality blocked class was ignored. BF, PS, Runtime Planning, Pending, and Fill then consumed the contradictory accepted target and did not re-block it.

No production code/config/state was changed. No fresh-run, resume, replay, or backtest was executed.

## Run Identity

| Field | Value |
| --- | --- |
| Run | `runtime-test-historical-extended-smoke-20260829T082306780474Z` |
| Primary date | `2022-10-21` |
| Symbol | `94320` |
| Campaign | `pc-cc82d38e0defd9eb-94320-0001` |
| Artifact root | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260829T082306780474Z` |

## 94320 Lot Trace

| Boundary | Lot #1 | Lot #2 | Lot #3 | Authority / consumer interpretation |
| --- | ---: | ---: | ---: | --- |
| PM | `ADD` | `ADD` | `ADD` | PM intent allowed ADD consideration. Reasons: `no_loss_averaging`, `opportunity_rank_still_high`, `strong_trend_continuation`. |
| ADD evidence | `PASS` | `PASS` | `PASS` | `add_investment_evidence.final_add_eligibility = PASS`. |
| ADD admission authority | `PASS` | `PASS` | `PASS` | BZ gate passed. This is necessary but not sufficient for final capital allocation. |
| Frontier candidate id | `cmcf-f91b08b0b51013c4a23481d5` | `cmcf-f62e896a75cba494fb1de3c3` | `cmcf-557b39af3dfed102596dfaee` | Stable candidate ids. |
| `comparison_class` | `BLOCKED` | `BLOCKED` | `BLOCKED` | Marginal opportunity-quality classifier blocked all three. |
| Reason | `opportunity_quality_add_hard_block` | same | same | Produced from ADD worthiness / opportunity-quality logic. |
| Raw MCV class | `BLOCKED_OR_NOT_ELIGIBLE` | same | same | Propagated from `marginal_capital_value_authority`. |
| Desirability status | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | Not honored by authority availability. |
| Frontier capital value | `0.6674047409` | `0.6584402257` | `0.6494757106` | Positive bounded value was computed despite blocked class. |
| Frontier decision step | 1 accepted | 2 accepted | 3 accepted | All accepted under remaining allocation budget. |
| Accepted quantity | +100 | +100 | +100 | Aggregated to +300. |
| BF aggregate |  | +300 net |  | `final_target_quantity = 700`, `target_gap = 0.0484083819`. |
| PS |  | +300 |  | Consumed BF target: `BG_BF_AGGREGATED_TARGET_AUTHORITY_CONSUMED_BY_PS`. |
| Runtime Planning |  | `BUY_ADD 300` |  | Kept `marginal_capital_value_class = BLOCKED_OR_NOT_ELIGIBLE`, but planned the positive quantity. |
| Morning submit feasibility |  | `INCLUDE` |  | `planning_submit_feasibility_pass` despite blocked MCV class. |
| Fill |  | BUY 300 |  | Execution fill reached ledger with `source_decision_id = MISSING`. |

## Exact Acceptance Sequence

`strategy/marginal_capital_frontier_authority.json` accepted the three lots first:

| Step | Candidate | Value | Next alternative | Cash value | Decision |
| ---: | --- | ---: | --- | ---: | --- |
| 1 | 94320 ADD #1 | `0.6674047409` | NEW value `0.5342230878` | `0.05` | `ACCEPT_INCREMENTAL_TARGET` |
| 2 | 94320 ADD #2 | `0.6584402257` | NEW value `0.5342230878` | `0.05` | `ACCEPT_INCREMENTAL_TARGET` |
| 3 | 94320 ADD #3 | `0.6494757106` | NEW value `0.5342230878` | `0.05` | `ACCEPT_INCREMENTAL_TARGET` |

Budget and cash were not the blocker:

- `available_incremental_budget_weight = 0.474368`
- `available_incremental_budget_notional = 474481.849186`
- `starting_cash_notional = 554500.0`
- each lot notional = `16140.0`
- capital conservation = `PASS`

## First Failing Boundary

The first failing boundary is:

```text
Portfolio Construction
canonical_marginal_capital_frontier_authority.v1
frontier candidate availability / bounded value / budget-bounded acceptance
```

Evidence from implementation:

- `_bounded_value()` in `src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py` computes a positive `capital_value` after ADD admission PASS. It does not reject `comparison_class = BLOCKED` or `desirability.status = REVIEW_REQUIRED`.
- `_available()` only checks ADD admission, `constraints.status`, `feasibility.status`, and `observability.status`. It does not check `desirability.status`, `comparison_class`, or `marginal_capital_value_class`.
- `_budget_bounded_acceptance()` builds its pool from `_available(row)` and accepts the top positive-value candidate above Cash.

This makes `final_add_eligibility = PASS` override a separate blocked opportunity-quality class in practice.

## Ownership Interpretation

| Question | Finding |
| --- | --- |
| Is `comparison_class = BLOCKED` production-authoritative? | Yes for capital comparison semantics. Architecture defines blocked/non-eligible marginal value classes, and BC says a security lot is accepted only while valid under comparison and guard constraints. |
| Is `opportunity_quality_add_hard_block` a hard blocker? | Yes semantically. It maps to `BLOCKED` / `BLOCKED_OR_NOT_ELIGIBLE`, not to a neutral diagnostic. |
| Which wins between ADD admission PASS and blocked value class? | They currently conflict. Correct ownership should be: ADD admission PASS permits entry into ADD consideration; marginal value/comparison class still owns whether the candidate is comparable/acceptable on the common capital frontier. |
| Why did frontier accept it? | Positive bounded value was computed from components and the acceptance pool ignored blocked/desirability state. |
| Should BF/PS reject blocked-class rows? | BF/PS should not recompute capital value, but the BF boundary should fail closed if accepted source candidates are internally blocked. PS correctly consumed the BF row it was given, but lacks a defensive invariant. |
| Is Runtime `BLOCKED_OR_NOT_ELIGIBLE` plus BUY_ADD normal? | No. Runtime consumed a positive PS quantity while carrying a blocked class. This is a downstream consumer gap, secondary to the poisoned BF/PS target. |

## Scope Expansion

Across the 61BD available coverage:

| Metric | Count |
| --- | ---: |
| Accepted frontier candidates | 2741 |
| Accepted candidates with `comparison_class = BLOCKED` | 3 |
| Accepted ADD lots | 17 |
| Accepted ADD lots affected | 3 |
| Other affected symbols/days | 0 |

Accepted ADD lots by day:

| Date | Symbol | Accepted lots | Class |
| --- | --- | ---: | --- |
| 2022-10-06 | 94340 | 3 | `COMPARABLE_MARGINAL` / `ELIGIBLE_COMPARABLE` |
| 2022-10-11 | 94340 | 3 | `COMPARABLE_MARGINAL` / `ELIGIBLE_COMPARABLE` |
| 2022-10-12 | 94320 | 3 | `COMPARABLE_MARGINAL` / `ELIGIBLE_COMPARABLE` |
| 2022-10-13 | 94340 | 1 | `COMPARABLE_MARGINAL` / `ELIGIBLE_COMPARABLE` |
| 2022-10-21 | 94320 | 3 | `BLOCKED` / `BLOCKED_OR_NOT_ELIGIBLE` |
| 2022-10-28 | 94320 | 3 | `COMPARABLE_MARGINAL` / `ELIGIBLE_COMPARABLE` |
| 2022-11-01 | 94320 | 1 | `COMPARABLE_MARGINAL` / `ELIGIBLE_COMPARABLE` |

The defect is therefore not broad across all ADDs, but it is a real systematic invariant gap because any future candidate with PASS feasibility and positive components can pass through even when its comparison class is blocked.

## Defect Classification

Classification among the requested alternatives:

- **A. Authoritative BLOCK ignored by consumer:** YES, but the first ignore occurs inside the PC frontier authority before the PS consumer.
- **B. Stale/non-authoritative diagnostic label:** NO. The label is supported by `marginal_capital_value_authority`, `opportunity_quality_evidence`, and architecture.
- **C. ADD admission PASS and value-class authority ownership conflict:** YES. ADD evidence says "ADD may be considered"; MCV says "blocked/non-eligible"; the current code lets ADD admission dominate.
- **D. BF/PS aggregation bug:** PARTIAL. BF aggregates accepted rows as designed, but should fail closed on accepted-source blocked-class invariants.
- **E. MIXED:** YES. Primary PC authority bug, secondary BF/PS/runtime defensive guard gaps.

## Repair Readiness

Minimal repair boundary should remain narrow:

1. In `canonical_marginal_capital_frontier_authority.v1`, fail closed / exclude candidates where:
   - `comparison_class in {BLOCKED, INSUFFICIENT}` where semantically non-comparable,
   - `marginal_capital_value_class = BLOCKED_OR_NOT_ELIGIBLE`,
   - or `desirability.status != PASS` for security lots.
2. Preserve `final_add_eligibility = PASS` as necessary but not sufficient.
3. Add BF boundary invariant: accepted source candidate ids must not point to blocked/non-eligible/review-required capital-value classes.
4. Add runtime/submit defensive invariant: positive BUY quantity with `marginal_capital_value_class = BLOCKED_OR_NOT_ELIGIBLE` should be review-required unless an explicit separate authority says the class is diagnostic-only.

Do not change ADD thresholds, PM behavior, PS arithmetic, runtime mapping, Cash, Risk Pacing, REDUCE, or EXIT.

## Final Judgments

PHASE32_DA_BLOCKED_CLASS_AUTHORITATIVE = YES

PHASE32_DA_94320_ADD_ACCEPTANCE_VALID = NO

PHASE32_DA_ADD_AUTHORITY_OWNERSHIP_CONFLICT = YES

PHASE32_DA_BF_PS_BLOCKING_GAP = PARTIAL

PHASE32_DA_RUNTIME_BLOCKED_CLASS_CONSUMER_GAP = PARTIAL

PHASE32_DA_OTHER_AFFECTED_ADD_ROWS = 3 lots, all `2022-10-21` `94320`; 0 other symbols/days observed in 61BD coverage

PHASE32_DA_PRODUCTION_REPAIR_REQUIRED = YES

PHASE32_DA_LONG_VALIDATION_CONTINUE = YES, for characterization only; do not use this run as final ADD acceptance until the blocked-class invariant is repaired

PHASE32_DA_NEXT_STEP = Implement a narrow PC frontier blocked-class/desirability-status acceptance guard plus BF/runtime defensive invariant tests; then run focused non-fresh reproductions before user-operated fresh validation.
